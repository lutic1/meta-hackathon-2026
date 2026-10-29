"""Stories 1.5, 1.7 and 2.27: the public card, prompt, play and Build view projections (AD-3)."""

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from src.domain import redact
from src.domain.redact import to_build_view, to_card_view, to_play_view, to_prompt_view
from src.domain.schema import (
    BuildView,
    Derived,
    DryRunAnswer,
    DryRunAnswers,
    InteractableView,
    JobState,
    PlayView,
    PuzzleView,
    Room,
    RoomView,
    TricksterCard,
    TricksterCardEvent,
)
from src.domain.validator import BUILD_RULES, RULES
from tests.fixtures.rooms import IX, PZ

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
PZ_A, PZ_B = f"pz_{ULID[:-1]}A", f"pz_{ULID[:-1]}B"
IX_DECOY = f"ix_{ULID[:-1]}D"
TE_1, TE_2 = f"te_{ULID[:-1]}1", f"te_{ULID[:-1]}2"
SENTINEL = "ZQXJV-SENTINEL-9731"
DECOY_ATTRIBUTE = "faded-brass-plaque"


def card_event(**fields: Any) -> TricksterCardEvent:
    return TricksterCardEvent.model_validate({"type": "trickster_card", "t_ms": 123_456, **fields})


def edit(edit_id: str, payload: dict[str, Any], *, puzzle: str = PZ_A, ok: bool = True, reasons=()) -> dict[str, Any]:
    return {
        "id": edit_id, "type": payload["type"], "puzzle": puzzle, "payload": payload,
        "validator_result": {"ok": ok, "reasons": list(reasons)}, "accepted": ok, "window": 0,
    }


ACCEPTED_DECOY = card_event(
    edit_id=TE_1, puzzle_id=PZ_A, accepted=True, reason=None, room_revision=1,
    edit=edit(TE_1, {"type": "decoy", "interactable": IX_DECOY, "visible_attribute": DECOY_ATTRIBUTE}),
)
REJECTED = card_event(
    edit_id=TE_2, puzzle_id=PZ_B, accepted=False, reason=9, room_revision=1,
    edit=edit(
        TE_2, {"type": "decoy", "interactable": IX_DECOY, "visible_attribute": SENTINEL}, puzzle=PZ_B, ok=False,
        reasons=[{"rule": 9, "puzzle_id": PZ_B, "field": "visible_attribute", "message": "A false clue breaks the decoy rules."}],
    ),
)
SKIPPED = card_event(edit_id=None, edit=None, puzzle_id=None, accepted=False, reason="provider_unavailable", room_revision=1)


def test_accepted_decoy_projects_to_a_card_without_its_payload():
    card = to_card_view(ACCEPTED_DECOY)
    assert card == TricksterCard(
        edit_id=TE_1, accepted=True, edit_type="decoy", puzzle_id=PZ_A, related_puzzle_id=None,
        room_revision=1, reason=None, message=None, t_ms=123_456,
    )


def test_rejected_card_reads_the_rule_number_and_the_fixed_message():
    card = to_card_view(REJECTED)
    assert card.accepted is False and card.reason == 9 and card.edit_type == "decoy" and card.puzzle_id == PZ_B
    assert card.message == "A false clue breaks the decoy rules."


def test_skipped_card_has_null_edit_fields():
    card = to_card_view(SKIPPED)
    assert card.edit_id is None and card.edit_type is None and card.puzzle_id is None
    assert card.reason == "provider_unavailable" and card.message is None and card.t_ms == 123_456


def test_related_puzzle_is_the_second_puzzle_of_a_merge_or_shortcut():
    merge = card_event(edit_id=TE_1, puzzle_id=PZ_A, accepted=True, reason=None, room_revision=1,
                       edit=edit(TE_1, {"type": "merge", "puzzle_a": PZ_A, "puzzle_b": PZ_B}))
    shortcut = card_event(edit_id=TE_1, puzzle_id=PZ_B, accepted=True, reason=None, room_revision=2,
                          edit=edit(TE_1, {"type": "shortcut", "puzzle": PZ_B, "requires": PZ_A}, puzzle=PZ_B))
    loosen = card_event(edit_id=TE_1, puzzle_id=PZ_A, accepted=True, reason=None, room_revision=0,
                        edit=edit(TE_1, {"type": "loosen", "puzzle": PZ_A, "rung": "direction"}))
    assert (to_card_view(merge).puzzle_id, to_card_view(merge).related_puzzle_id) == (PZ_B, PZ_A)
    assert to_card_view(shortcut).related_puzzle_id == PZ_A
    assert to_card_view(loosen).related_puzzle_id is None


@pytest.mark.parametrize("named", [PZ_A, PZ_B])
def test_a_merge_card_names_the_waiting_puzzle_first_whichever_the_proposal_named(named: str):
    # The proposal may name either Puzzle of the pair; the Card's `puzzle_id` is the one that now waits (`puzzle_b`).
    for accepted in (True, False):
        merge = card_event(edit_id=TE_1, puzzle_id=named, accepted=accepted, reason=None if accepted else 1,
                           room_revision=int(accepted), edit=edit(TE_1, {"type": "merge", "puzzle_a": PZ_B, "puzzle_b": PZ_A},
                                                                   puzzle=named, ok=accepted))
        card = to_card_view(merge)
        assert (card.puzzle_id, card.related_puzzle_id) == (PZ_A, PZ_B)


def test_serialized_cards_leak_neither_the_decoy_nor_the_sentinel():
    cards = json.dumps([to_card_view(e).model_dump() for e in (ACCEPTED_DECOY, REJECTED, SKIPPED)])
    assert IX_DECOY not in cards and DECOY_ATTRIBUTE not in cards and SENTINEL not in cards
    for key in ("payload", "interactable", "visible_attribute", "rung", "edit"):
        assert f'"{key}"' not in cards
    assert '"edit_type": "decoy"' in cards and '"reason": 9' in cards


# --- Story 1.7: `to_prompt_view` and `to_play_view` -------------------------

SENTINEL_CODE = "ZQXJV-9731"
SENTINEL_IX = [f"ix_{ULID[:-2]}Q{n}" for n in range(1, 5)]
SENTINEL_ORDER = SENTINEL_IX[:3]
SENTINEL_PAIR = (SENTINEL_IX[0], SENTINEL_IX[1])
SENTINEL_FIND = SENTINEL_IX[3]
PROFILE_FIELDS = {"derived", *Derived.model_fields}
DERIVED_KEYS = set(Derived.model_fields)
ROOM_ONLY_KEYS = ("solution", "evidence", "provenance", "downscaled_path", "original_path", "box", "tier2", "validator_result")


def schema_keys(model: type) -> set[str]:
    """Every property name declared anywhere in the model's JSON schema."""
    keys: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            keys.update(node.get("properties", {}))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(model.model_json_schema())
    return keys


def json_keys(data: Any) -> set[str]:
    if isinstance(data, dict):
        return set(data) | {key for value in data.values() for key in json_keys(value)}
    if isinstance(data, list):
        return {key for item in data for key in json_keys(item)}
    return set()


def with_sentinel_solutions(room: Room) -> Room:
    """The room with one sentinel solution per lock type; the ids appear nowhere else in it."""
    by_type = {
        "code": {"code": SENTINEL_CODE},
        "order": {"interactables": SENTINEL_ORDER},
        "use_on": {"item": SENTINEL_PAIR[0], "target": SENTINEL_PAIR[1]},
        "find": {"target": SENTINEL_FIND},
    }
    data = room.model_dump()
    for puzzle in data["puzzles"]:
        puzzle["solution"] = {"lock_type": puzzle["lock_type"], **by_type[puzzle["lock_type"]]}
    return Room.model_validate(data)


def with_decoys(room: Room, *decoys: tuple[str, str, str]) -> Room:
    data = room.model_dump()
    data["decoys"] = [
        {"id": f"te_{ULID[:-1]}{n}", "puzzle": PZ[puzzle], "interactable": IX[ix], "visible_attribute": attribute}
        for n, (puzzle, ix, attribute) in enumerate(decoys, 1)
    ]
    return Room.model_validate(data)


def test_prompt_view_keeps_only_the_prompt_fields(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    assert isinstance(view, RoomView) and view.id == four_lock_room.id
    assert len(view.interactables) == len(four_lock_room.interactables)
    assert set(InteractableView.model_fields) == {"id", "label", "attributes", "instances", "photo"}
    assert set(PuzzleView.model_fields) == {"id", "lock_type", "requires", "is_exit", "clue", "lore", "rungs"}
    for got, ix in zip(view.interactables, four_lock_room.interactables, strict=True):
        assert got.model_dump() == ix.model_dump(include=set(InteractableView.model_fields))
    for got, puzzle in zip(view.puzzles, four_lock_room.puzzles, strict=True):
        assert got.model_dump() == puzzle.model_dump(include=set(PuzzleView.model_fields))
    keys = json_keys(view.model_dump(mode="json"))
    assert keys.isdisjoint((*ROOM_ONLY_KEYS, "photos", "hash", "polygons", "decoys"))


def test_play_view_keeps_evidence_polygons_and_the_name_but_no_solution_provenance_or_rungs(four_lock_room: Room):
    named = Room.model_validate({**four_lock_room.model_dump(), "name": "The tenant's room"})
    view = to_play_view(named)
    assert isinstance(view, PlayView) and view.id == named.id and view.created == named.created
    assert view.name == "The tenant's room"
    assert [photo.model_dump() for photo in view.photos] == [
        {"hash": p.hash, "size": p.size, "area": "room", "pan": None} for p in named.photos
    ]
    for got, ix in zip(view.interactables, named.interactables, strict=True):
        assert got.polygons == ix.polygons and got.id == ix.id and got.label == ix.label
    opened = to_play_view(named, opened=[puzzle.id for puzzle in named.puzzles])
    for got, puzzle in zip(opened.puzzles, named.puzzles, strict=True):
        assert got.evidence_cards == [puzzle.evidence]
        assert (got.id, got.lock_type, got.requires, got.is_exit, got.clue, got.lore) == (
            puzzle.id, puzzle.lock_type, puzzle.requires, puzzle.is_exit, puzzle.clue, puzzle.lore)
    keys = json_keys(view.model_dump(mode="json"))
    assert keys.isdisjoint(("solution", "provenance", "rungs", "nudge", "direction", "near_answer", "decoys"))
    assert keys.isdisjoint(("downscaled_path", "original_path", "box", "validator_result"))


def test_neither_view_declares_a_solution_or_a_profile_field():
    for model in (RoomView, PlayView):
        keys = schema_keys(model)
        assert "solution" not in keys
        assert keys.isdisjoint(PROFILE_FIELDS)


def test_both_views_leave_the_room_untouched(four_lock_room: Room):
    room = with_decoys(four_lock_room, ("clock_code", "rug", "faded red"))
    before = room.model_copy(deep=True)
    to_prompt_view(room)
    to_play_view(room)
    assert room == before


def test_serialized_views_leak_no_sentinel_solution_derived_key_or_reason_text(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    assert SENTINEL_CODE in json.dumps(room.model_dump(mode="json"))  # the sentinels are in the room
    for view in (to_prompt_view(room), to_play_view(room)):
        text = json.dumps(view.model_dump(mode="json"))
        assert SENTINEL_CODE not in text
        assert json.dumps(SENTINEL_ORDER)[1:-1] not in text
        assert SENTINEL_PAIR[0] not in text and SENTINEL_PAIR[1] not in text
        assert SENTINEL_FIND not in text
        assert all(ix not in text for ix in SENTINEL_IX)
        keys = json_keys(view.model_dump(mode="json"))
        assert keys.isdisjoint(DERIVED_KEYS) and "derived" not in keys
        assert keys.isdisjoint(("reasons", "rule", "message", "validator_result"))
        assert all(rule.message not in text for rule in RULES.values())


def test_play_view_serves_no_decoy_and_the_real_card_only_once_its_lock_is_open(four_lock_room: Room):
    """Story mode (amended 29 Oct 2026): the decoy merge is replaced; evidence waits for the lock."""
    room = with_decoys(
        four_lock_room,
        ("clock_code", "rug", "faded red"),
        ("door_code", "rug", "lies by the door"),
        ("find_key", "candle", "white wax"),
    )
    assert all(puzzle.evidence_cards == [] for puzzle in to_play_view(room).puzzles)
    view = to_play_view(room, opened=[PZ["clock_code"], PZ["find_key"]])
    cards = {puzzle.id: puzzle.evidence_cards for puzzle in view.puzzles}
    by_id = {puzzle.id: puzzle for puzzle in room.puzzles}
    assert cards[PZ["clock_code"]] == [by_id[PZ["clock_code"]].evidence]
    assert cards[PZ["find_key"]] == [by_id[PZ["find_key"]].evidence]
    assert cards[PZ["door_code"]] == [] and cards[PZ["shelf_order"]] == []
    text = json.dumps(view.model_dump(mode="json"))
    assert "te_" not in text and '"decoys"' not in text


# --- Story 2.27: `to_build_view` --------------------------------------------

JOB_ID = f"job_{ULID}"
ARCHITECT, SAM, RIDDLER, FALLBACK = "muse-spark-1.3", "sam-3.1", "muse-spark-1.3", "muse-spark-open"
DISCLOSURE = ["Demo mode: the clock runs faster.", "Cached calls were served from earlier builds."]


def call(n: int, role: str, model: str, *, host: str = "meta", cached: bool = False) -> dict[str, Any]:
    return {"id": f"call_{n:026d}", "role": role, "model": model, "host": host, "cached": cached,
            "spend_usd": 0.0 if cached else 0.01}


def stage(name: str, duration_ms: int, count: int | None = None, model: str | None = None) -> dict[str, Any]:
    return {"stage": name, "duration_ms": duration_ms, "count": count, "model": model}


def done_job(room: Room, **fields: Any) -> JobState:
    """The final job record of `room`: one Regeneration after a validate send-back, the Riddler's retry on a fallback."""
    puzzles = [puzzle.id for puzzle in room.puzzles]
    data: dict[str, Any] = {
        "id": JOB_ID, "status": "done", "room_id": room.id, "regen_max": 2, "regeneration_count": 1,
        "stages": [
            stage("ingest", 900, len(room.photos)), stage("architect", 8_000, 8, ARCHITECT),
            stage("segment", 12_000, 8, SAM), stage("author", 30_000, 4, RIDDLER), stage("validate", 10),
            stage("author", 25_000, 5, FALLBACK), stage("validate", 10), stage("dryrun", 9_000, 5, "muse-spark-1.3"),
            stage("scene", 80, len(room.photos)),
        ],
        "validator": [{"rule": n, "name": RULES[n].name, "passed": True} for n in BUILD_RULES],
        "dry_run": [{"puzzle_id": pz, "verdict": "fail" if n == 2 else "pass"} for n, pz in enumerate(puzzles)],
        "sent_back": [{"attempt": 0, "stage": "validate", "messages": [RULES[2].message]}],
        "calls": [
            call(1, "architect", ARCHITECT, cached=True),
            *(call(n, "architect", SAM, cached=n < 4) for n in range(2, 8)),
            call(8, "riddler", RIDDLER),
            call(9, "riddler", FALLBACK, host="openai_compatible"),
            call(10, "dryrun", "muse-spark-1.3"),
        ],
        "build_time_ms": 91_000,  # the runner's wall time, not the sum of the stage durations (85_000)
    }
    return JobState.model_validate({**data, **fields})


def test_build_view_holds_masks_graph_verdicts_regenerations_and_build_time(four_lock_room: Room):
    room, job = four_lock_room, done_job(four_lock_room)
    view = to_build_view(room, job)
    assert isinstance(view, BuildView)
    assert (view.room_id, view.job_id, view.name, view.built_at) == (room.id, job.id, room.name, room.created)
    assert view.build_time_ms == 91_000
    assert [photo.photo for photo in view.photos] == list(range(len(room.photos)))
    for photo in view.photos:
        expected = [ix for ix in room.interactables if ix.photo == photo.photo]
        assert [(m.interactable_id, m.label, m.polygons) for m in photo.masks] == [
            (ix.id, ix.label, ix.polygons) for ix in expected]
    assert len(view.photos[3].masks) == 3
    assert [node.model_dump() for node in view.puzzles] == [
        {"id": p.id, "lock_type": p.lock_type, "requires": p.requires, "is_exit": p.is_exit} for p in room.puzzles]
    assert [(v.rule, v.name) for v in view.validator] == [(n, RULES[n].name) for n in BUILD_RULES]
    assert all(v.passed for v in view.validator)
    assert view.dry_run == job.dry_run and {v.verdict for v in view.dry_run} == {"pass", "fail"}
    assert (view.regeneration_count, view.regen_max) == (1, 2)
    assert view.sent_back == job.sent_back and view.sent_back[0].messages == [RULES[2].message]
    assert view.calls == job.calls


def test_segmented_outlines_reach_the_view_exactly_as_recorded(four_lock_room: Room):
    data = four_lock_room.model_dump()
    x0, y0, x1, y1 = data["interactables"][0]["box"]
    outlines = [[(x0, y1), ((x0 + x1) / 2, y0), (x1, y1)], [(x0 + 1, y0 + 1), (x0 + 5, y0 + 2), (x0 + 3, y0 + 6)]]
    data["interactables"][0].update(polygons=outlines, instances=2)
    room = Room.model_validate(data)
    masks = {m.interactable_id: m for photo in to_build_view(room, done_job(room)).photos for m in photo.masks}
    assert masks[room.interactables[0].id].polygons == outlines


def test_build_time_falls_back_to_the_sum_of_the_stage_durations(four_lock_room: Room):
    job = done_job(four_lock_room, build_time_ms=None)
    assert to_build_view(four_lock_room, job).build_time_ms == sum(s.duration_ms for s in job.stages) == 85_000


def test_a_box_fallback_reaches_the_view_as_a_polygon(four_lock_room: Room):
    data = four_lock_room.model_dump()
    data["interactables"][0]["polygons"] = None
    room = Room.model_validate(data)
    ix = room.interactables[0]
    x0, y0, x1, y1 = ix.box
    masks = {m.interactable_id: m for photo in to_build_view(room, done_job(room)).photos for m in photo.masks}
    assert masks[ix.id].polygons == [[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]
    assert masks[room.interactables[1].id].polygons == room.interactables[1].polygons


def test_model_rows_count_cached_and_billed_per_role_and_model_and_name_the_fallback_that_ran(four_lock_room: Room):
    rows = [row.model_dump() for row in to_build_view(four_lock_room, done_job(four_lock_room)).models]
    assert rows == [
        {"role": "architect", "model": ARCHITECT, "host": "meta", "cached": 1, "billed": 0, "summary": "found 8 objects"},
        {"role": "architect", "model": SAM, "host": "meta", "cached": 2, "billed": 4, "summary": "outlined 8 objects"},
        {"role": "riddler", "model": RIDDLER, "host": "meta", "cached": 0, "billed": 1, "summary": "wrote 4 puzzles"},
        {"role": "riddler", "model": FALLBACK, "host": "openai_compatible", "cached": 0, "billed": 1,
         "summary": "wrote 5 puzzles"},
        {"role": "dryrun", "model": "muse-spark-1.3", "host": "meta", "cached": 0, "billed": 1,
         "summary": "tried 5 puzzles blind"},
    ]


def test_a_single_count_reads_in_the_singular(four_lock_room: Room):
    job = done_job(four_lock_room, stages=[stage("architect", 10, 1, ARCHITECT)], calls=[call(1, "architect", ARCHITECT)])
    assert to_build_view(four_lock_room, job).models[0].summary == "found 1 object"


def test_a_model_with_no_done_row_of_its_own_reads_no_count(four_lock_room: Room):
    job = done_job(four_lock_room, stages=[stage("author", 30_000, 4, RIDDLER)],
                   calls=[call(1, "riddler", RIDDLER), call(2, "riddler", FALLBACK, host="openai_compatible")])
    assert [row.summary for row in to_build_view(four_lock_room, job).models] == ["wrote 4 puzzles", ""]


def test_dry_run_off_projects_every_puzzle_skipped(four_lock_room: Room):
    skipped = [{"puzzle_id": puzzle.id, "verdict": "skipped"} for puzzle in four_lock_room.puzzles]
    job = done_job(four_lock_room, dry_run=skipped, calls=[call(1, "architect", ARCHITECT)])
    view = to_build_view(four_lock_room, job)
    assert [v.puzzle_id for v in view.dry_run] == [puzzle.id for puzzle in four_lock_room.puzzles]
    assert all(v.verdict == "skipped" for v in view.dry_run)


def test_regen_max_1_reads_1_with_the_recorded_dry_run_verdicts(four_lock_room: Room):
    job = done_job(four_lock_room, regen_max=1)
    view = to_build_view(four_lock_room, job)
    assert view.regen_max == 1
    assert [(v.puzzle_id, v.verdict) for v in view.dry_run] == [(v.puzzle_id, v.verdict) for v in job.dry_run]


def test_disclosure_holds_exactly_the_given_lines(four_lock_room: Room):
    job = done_job(four_lock_room)
    assert to_build_view(four_lock_room, job, disclosure=DISCLOSURE).disclosure == DISCLOSURE
    assert to_build_view(four_lock_room, job).disclosure == []


def test_a_job_of_another_room_is_refused(four_lock_room: Room, code_and_find_room: Room):
    with pytest.raises(ValueError):
        to_build_view(code_and_find_room, done_job(four_lock_room))


def test_serialized_build_view_leaks_no_solution_answer_pairing_or_clue(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    answers = DryRunAnswers(answers=[DryRunAnswer(puzzle_id=p.id, answer=p.solution) for p in room.puzzles])
    assert SENTINEL_CODE in json.dumps(room.model_dump(mode="json"))  # the sentinels are in the room
    assert {ix.id for ix in room.interactables}.isdisjoint(SENTINEL_IX)  # and nowhere else in it
    view = to_build_view(room, done_job(room), disclosure=DISCLOSURE)
    data = view.model_dump(mode="json")
    text = json.dumps(data)
    assert "solution" not in json_keys(data) and "solution" not in schema_keys(BuildView)
    assert json_keys(data).isdisjoint(("answer", "answers", "evidence", "clue", "lore", "rungs", "code", "item", "target"))
    assert SENTINEL_CODE not in text and all(ix not in text for ix in SENTINEL_IX)
    assert json.dumps(SENTINEL_ORDER)[1:-1] not in text
    for answer in answers.answers:
        assert json.dumps(answer.answer.model_dump(mode="json")) not in text
    for puzzle in room.puzzles:
        assert puzzle.clue not in text and puzzle.lore not in text
        assert puzzle.evidence.visible_attribute not in text


def test_build_view_leaves_its_inputs_unchanged(four_lock_room: Room):
    room, job = with_sentinel_solutions(four_lock_room), done_job(four_lock_room)
    room_before, job_before = room.model_copy(deep=True), job.model_copy(deep=True)
    view = to_build_view(room, job, disclosure=DISCLOSURE)
    view.photos[0].masks[0].polygons[0].append((0.0, 0.0))
    view.calls[0].cached = False
    view.validator.clear()
    assert room == room_before and job == job_before


def test_redact_imports_only_the_standard_library_pydantic_and_the_domain():
    tree = ast.parse(Path(redact.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in sys.stdlib_module_names for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                assert node.level == 1 and node.module in ("schema", "masks")
            else:
                assert (node.module or "").split(".")[0] in {*sys.stdlib_module_names, "pydantic"}
