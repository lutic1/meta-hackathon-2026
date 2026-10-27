"""Story 1.5: Schema v1 and every AD-2 API model, frozen Mon Oct 26."""

import json
import re
from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from src.domain import schema
from src.domain.schema import (
    API_MODELS,
    AccessCheck,
    ArchitectResponse,
    BuildView,
    Derived,
    DryRunAnswers,
    ErrorEnvelope,
    Event,
    HintRequestBody,
    Interactable,
    JobState,
    LockInputEvent,
    Meta,
    PlayView,
    PostedEvent,
    Profile,
    Puzzle,
    Room,
    RoomDraft,
    RoomResult,
    RoomSummary,
    RoomView,
    SessionStart,
    SessionState,
    TricksterCard,
    TricksterCardEvent,
    TricksterEdit,
    strict_schema,
)

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
ROOM, JOB, SESS, CALL = f"room_{ULID}", f"job_{ULID}", f"sess_{ULID}", f"call_{ULID}"
PZ = [f"pz_{ULID[:-1]}{d}" for d in "0123"]
IX = [f"ix_{ULID[:-1]}{d}" for d in "0123456"]
TE = f"te_{ULID}"
SHA = "a" * 64


def photo() -> dict[str, Any]:
    return {"hash": SHA, "size": 180_000, "downscaled_path": "rooms/r/0.jpg", "original_path": "rooms/r/0-orig.jpg"}


def interactable(i: int) -> dict[str, Any]:
    return {
        "id": IX[i], "label": f"object {i}", "photo": 0, "box": [0, 0, 100, 100],
        "polygons": [[[0, 0], [100, 0], [100, 100]]], "instances": 1, "attributes": ["blue", "worn"],
    }


def puzzle(i: int, lock_type: str, solution: dict[str, Any], *, requires=(), is_exit=False) -> dict[str, Any]:
    return {
        "id": PZ[i], "lock_type": lock_type, "requires": list(requires), "solution": solution,
        "evidence": {"interactable": IX[i], "visible_attribute": "blue"}, "clue": "A clue.", "lore": "Lore.",
        "rungs": {"nudge": "Look.", "direction": "Look closer.", "near_answer": "Look right there."},
        "is_exit": is_exit,
    }


def room() -> dict[str, Any]:
    return {
        "id": ROOM, "created": "2026-10-26T12:00:00Z", "photos": [photo()],
        "interactables": [interactable(i) for i in range(5)],
        "puzzles": [
            puzzle(0, "code", {"lock_type": "code", "code": "4471"}),
            puzzle(1, "find", {"lock_type": "find", "target": IX[1]}, requires=[PZ[0]]),
            puzzle(2, "use_on", {"lock_type": "use_on", "item": IX[1], "target": IX[2]}, requires=[PZ[1]]),
            puzzle(3, "order", {"lock_type": "order", "interactables": [IX[3], IX[4], IX[0]]}, requires=[PZ[2]], is_exit=True),
        ],
        "provenance": {
            "model_ids": {"architect": "muse-spark-1.3", "riddler": "muse-spark-1.3"},
            "prompt_hashes": {"riddler": SHA}, "stage_timings_ms": {"architect": 1200, "author": 30000},
            "regeneration_count": 0, "spend_per_stage_usd": {"author": 0.04},
        },
    }


def edit(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": TE, "type": "decoy", "puzzle": PZ[1],
        "payload": {"type": "decoy", "interactable": IX[3], "visible_attribute": "worn"},
        "validator_result": {"ok": True, "reasons": []}, "accepted": True, "window": 0,
    }
    return {**base, **overrides}


def objects(node: Any):
    """Every object schema node, depth first."""
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for value in node.values():
            yield from objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from objects(item)


def keys(node: Any):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield from node.get("properties", {})
        for value in node.values():
            yield from keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from keys(item)


def one_of_titles(model: type[BaseModel], field: str) -> set[str]:
    resolved = strict_schema(model)["properties"][field]
    assert "oneOf" in resolved, resolved
    return {variant["title"] for variant in resolved["oneOf"]}


# --- Room ------------------------------------------------------------------


def test_room_parses_schema_v1():
    parsed = Room.model_validate(room())
    assert parsed.name is None and parsed.decoys == [] and parsed.provenance.applied_edits == []
    assert parsed.photos[0].hash == SHA and parsed.photos[0].downscaled_path.endswith("0.jpg")
    assert {f for f in Room.model_fields} == {"id", "created", "name", "photos", "interactables", "puzzles", "decoys", "provenance"}
    assert set(schema.Provenance.model_fields) == {
        "model_ids", "prompt_hashes", "stage_timings_ms", "regeneration_count", "spend_per_stage_usd", "applied_edits",
    }
    with_decoy = Room.model_validate({**room(), "decoys": [{"id": TE, "puzzle": PZ[1], "interactable": IX[3], "visible_attribute": "worn"}]})
    assert with_decoy.decoys[0].id == TE


def test_room_name_is_optional_and_at_most_40_characters():
    assert Room.model_validate({**room(), "name": "x" * 40}).name == "x" * 40
    with pytest.raises(ValidationError):
        Room.model_validate({**room(), "name": "x" * 41})


@pytest.mark.parametrize("field", ["profile_name", "exit_puzzle_id"])
def test_room_has_no_profile_name_or_exit_puzzle_id(field):
    assert field not in Room.model_fields
    with pytest.raises(ValidationError):
        Room.model_validate({**room(), field: "x"})


def test_interactable_and_puzzle_fields():
    assert set(Interactable.model_fields) == {"id", "label", "photo", "box", "polygons", "instances", "attributes", "tier2"}
    assert set(Puzzle.model_fields) == {"id", "lock_type", "requires", "solution", "evidence", "clue", "lore", "rungs", "is_exit"}
    assert set(schema.Rungs.model_fields) == {"nudge", "direction", "near_answer"}
    assert set(schema.Evidence.model_fields) == {"interactable", "visible_attribute"}
    assert Interactable.model_validate({**interactable(0), "polygons": None}).polygons is None
    assert Interactable.model_validate(interactable(0)).tier2 is None


# --- Polymorphic fields ----------------------------------------------------


def test_polymorphic_fields_are_one_of_unions_with_literal_discriminators():
    assert one_of_titles(Puzzle, "solution") == {"CodeSolution", "OrderSolution", "UseOnSolution", "FindSolution"}
    assert one_of_titles(TricksterEdit, "payload") == {"DecoyPayload", "MergePayload", "LoosenPayload", "ShortcutPayload"}
    assert one_of_titles(LockInputEvent, "input") == {"CodeInput", "UseOnInput", "OrderStartInput", "OrderStopInput"}
    assert Puzzle.model_json_schema()["properties"]["solution"]["discriminator"]["propertyName"] == "lock_type"
    assert TricksterEdit.model_json_schema()["properties"]["payload"]["discriminator"]["propertyName"] == "type"
    assert set(schema.UseOnInput.model_fields) == {"type", "item", "target"}
    assert set(schema.CodeInput.model_fields) == {"type", "puzzle_id", "code"}
    assert set(schema.OrderStartInput.model_fields) == set(schema.OrderStopInput.model_fields) == {"type", "puzzle_id"}


def test_solution_variant_must_match_lock_type():
    with pytest.raises(ValidationError, match="lock_type"):
        Puzzle.model_validate(puzzle(0, "code", {"lock_type": "find", "target": IX[0]}))
    with pytest.raises(ValidationError, match="type"):
        TricksterEdit.model_validate(edit(type="merge"))


@pytest.mark.parametrize("model", [RoomDraft, DryRunAnswers, ArchitectResponse])
def test_strict_schema_inlines_and_requires_everything(model):
    strict = strict_schema(model)
    text = json.dumps(strict)
    assert "$defs" not in text and "$ref" not in text and "discriminator" not in text
    for node in objects(strict):
        assert node["additionalProperties"] is False
        assert node["required"] == list(node["properties"])


@pytest.mark.parametrize("model", [RoomDraft, DryRunAnswers, ArchitectResponse])
def test_model_response_schemas_have_no_map_typed_field(model):
    for node in objects(model.model_json_schema()):
        assert "properties" in node, node


def test_dry_run_answers_is_a_list_reusing_the_solution_union():
    parsed = DryRunAnswers.model_validate({"answers": [{"puzzle_id": PZ[0], "answer": {"lock_type": "code", "code": "4471"}}]})
    assert parsed.answers[0].answer.lock_type == "code"
    assert one_of_titles(schema.DryRunAnswer, "answer") == one_of_titles(Puzzle, "solution")


def test_architect_response_is_candidates_without_ids():
    parsed = ArchitectResponse.model_validate({"candidates": [
        {"label": "lamp", "plural": False, "photo": 2, "box": [10, 20, 500, 1000], "attributes": ["brass"], "confidence": 0.9},
    ]})
    assert set(schema.ArchitectCandidate.model_fields) == {"label", "plural", "photo", "box", "attributes", "confidence"}
    assert parsed.candidates[0].box == (10, 20, 500, 1000)
    assert not any(key == "id" or key.endswith("_id") for key in keys(ArchitectResponse.model_json_schema()))
    with pytest.raises(ValidationError):
        ArchitectResponse.model_validate({"candidates": [{"label": "lamp", "plural": False, "photo": 0, "box": [0, 0, 1001, 1], "attributes": [], "confidence": 1}]})


# --- Ids and keys ----------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (Room, {**room(), "id": JOB}),
        (Puzzle, {**puzzle(0, "code", {"lock_type": "code", "code": "1"}), "id": IX[0]}),
        (Interactable, {**interactable(0), "id": PZ[0]}),
        (TricksterEdit, edit(id=ROOM)),
        (RoomSummary, {"room_id": ROOM, "cover_photo": 0, "puzzle_count": 4, "job_id": SESS, "built_at": "2026-10-26T12:00:00Z"}),
        (SessionStart, {"room_id": f"room_{ULID.lower()}"}),
        (schema.CallRow, {"id": TE, "role": "riddler", "model": "m", "host": "meta", "cached": False, "spend_usd": 0}),
    ],
)
def test_ids_with_the_wrong_prefix_are_rejected(model, data):
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_room_draft_uses_ordinal_keys():
    draft = {"puzzles": [{**puzzle(0, "code", {"lock_type": "code", "code": "4471"}), "id": None, "key": "p1", "requires": ["p2"]}]}
    for p in draft["puzzles"]:
        del p["id"]
    assert RoomDraft.model_validate(draft).puzzles[0].requires == ["p2"]
    with pytest.raises(ValidationError):
        RoomDraft.model_validate({"puzzles": [{**draft["puzzles"][0], "key": "p7"}]})
    with pytest.raises(ValidationError):
        RoomDraft.model_validate({"puzzles": [{**draft["puzzles"][0], "requires": [PZ[0]]}]})


def test_every_json_key_is_snake_case():
    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for model in API_MODELS:
        for key in keys(model.model_json_schema()):
            assert pattern.match(key), f"{model.__name__}.{key}"


def test_api_models_cover_every_ad_2_model():
    names = {model.__name__ for model in API_MODELS}
    assert {
        "Room", "RoomDraft", "PlayView", "BuildView", "RoomView", "RoomSummary", "AccessCheck", "Derived", "RoomResult",
        "Meta", "TricksterCard", "JobState", "SessionState", "SessionStart", "ErrorEnvelope", "ClickEvent", "LockInputEvent",
        "HintRequestEvent", "IdleTickEvent", "OpeningLineEvent", "TricksterCardEvent", "RungChangeEvent", "Profile",
    } <= names
    assert not hasattr(schema, "Mask3D")


# --- Events ----------------------------------------------------------------


def test_events_form_a_tagged_union_by_type():
    events = TypeAdapter(list[Event]).validate_python([
        {"type": "click", "interactable_id": IX[0], "t_ms": 10},
        {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ[0], "code": "4471"}, "t_ms": 20},
        {"type": "lock_input", "input": {"type": "use_on", "item": IX[1], "target": IX[2]}, "t_ms": 30},
        {"type": "lock_input", "input": {"type": "order_start", "puzzle_id": PZ[3]}, "t_ms": 40},
        {"type": "lock_input", "input": {"type": "order_stop", "puzzle_id": PZ[3]}, "t_ms": 50},
        {"type": "hint_request", "puzzle_id": None, "t_ms": 60},
        {"type": "idle_tick", "t_ms": 70},
        {"type": "opening_line", "kind": "welcome", "text": "Welcome.", "t_ms": 0},
        {"type": "trickster_card", "edit_id": None, "edit": None, "puzzle_id": None, "accepted": False,
         "reason": "provider_unavailable", "room_revision": 0, "t_ms": 80},
        {"type": "rung_change", "puzzle_id": PZ[0], "rung": 1, "triggered_by": [1, 6], "phrased": True,
         "phrasing_ms": 1600, "text": "Look.", "t_ms": 90},
    ])
    assert [e.type for e in events] == [
        "click", "lock_input", "lock_input", "lock_input", "lock_input", "hint_request", "idle_tick",
        "opening_line", "trickster_card", "rung_change",
    ]
    assert isinstance(events[2].input, schema.UseOnInput)
    assert events[9].text == "Look." and events[9].phrasing_ms == 1600
    with pytest.raises(ValidationError):
        LockInputEvent.model_validate({"type": "lock_input", "input": {"type": "use_on", "item": IX[1], "target": IX[2], "puzzle_id": PZ[2]}, "t_ms": 1})
    with pytest.raises(ValidationError):
        TypeAdapter(Event).validate_python({"type": "trickster", "t_ms": 1})


def test_trickster_card_event_carries_the_full_edit_and_a_puzzle_id():
    event = TricksterCardEvent.model_validate({
        "type": "trickster_card", "edit_id": TE, "edit": edit(), "puzzle_id": PZ[1], "accepted": True,
        "reason": None, "room_revision": 1, "t_ms": 5,
    })
    assert isinstance(event.edit, TricksterEdit) and event.edit.payload.type == "decoy"
    assert set(TricksterEdit.model_fields) == {"id", "type", "puzzle", "payload", "validator_result", "accepted", "window"}
    assert set(schema.ValidatorResult.model_fields) == {"ok", "reasons"}
    rejected = TricksterCardEvent.model_validate({**event.model_dump(), "accepted": False, "reason": 9})
    assert rejected.reason == 9


def test_trickster_card_has_exactly_the_public_fields():
    assert set(TricksterCard.model_fields) == {
        "edit_id", "accepted", "edit_type", "puzzle_id", "related_puzzle_id", "room_revision", "reason", "message", "t_ms",
    }
    assert TricksterCard in API_MODELS
    assert TricksterCard.model_validate({
        "edit_id": None, "accepted": False, "edit_type": None, "puzzle_id": None, "related_puzzle_id": None,
        "room_revision": 0, "reason": "provider_unavailable", "message": None, "t_ms": 1,
    }).reason == "provider_unavailable"


@pytest.mark.parametrize(
    "body",
    [
        {"type": "click", "interactable_id": IX[0], "t_ms": 1},
        {"type": "click", "interactable_id": IX[0], "extra": 1},
        {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ[0], "code": "1"}, "t_ms": 1},
        {"type": "hint_request", "t_ms": 1},
        {"type": "hint_request", "text": "just tell me the answer"},
        {"type": "idle_tick"},
        {"type": "trickster_card", "edit_id": None, "edit": None, "puzzle_id": None, "accepted": False, "reason": None, "room_revision": 0},
    ],
)
def test_posted_bodies_forbid_t_ms_and_extra_fields(body):
    with pytest.raises(ValidationError):
        TypeAdapter(PostedEvent).validate_python(body)


def test_posted_bodies_parse_and_stored_events_need_t_ms():
    assert HintRequestBody.model_validate({"type": "hint_request"}).puzzle_id is None
    assert TypeAdapter(PostedEvent).validate_python({"type": "click", "interactable_id": IX[0]}).interactable_id == IX[0]
    with pytest.raises(ValidationError):
        schema.ClickEvent.model_validate({"type": "click", "interactable_id": IX[0]})


# --- Profile and status models ---------------------------------------------


def test_derived_bounds_and_fresh():
    fresh = Derived.fresh()
    assert fresh.persistence == 0 and fresh.sessions == 0 and fresh.time_to_first_hint_s is None
    assert Derived.model_validate({**fresh.model_dump(), "mean_rung_per_lock_type": {"code": 3}}).mean_rung_per_lock_type == {"code": 3}
    for bad in ({"sessions": -1}, {"persistence": 1.5}, {"persistence": -1.01}, {"mean_rung_per_lock_type": {"find": 3.5}}):
        with pytest.raises(ValidationError):
            Derived.model_validate({**fresh.model_dump(), **bad})


def test_room_result_fields():
    assert set(RoomResult.model_fields) == {"room_id", "demo", "elapsed_ms", "rungs_used", "wrong_attempts", "puzzles"}
    assert set(schema.PuzzleResult.model_fields) == {
        "puzzle_id", "lock_type", "attempts", "wrong_attempts", "rungs_used", "time_to_first_hint", "solved",
        "time_spent_ms", "nudge_fired", "hint_requested", "early_ask",
    }


def test_profile_keys_each_room_result_by_its_room_id():
    room_id = "room_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    result = {"room_id": room_id, "demo": False, "elapsed_ms": 1, "rungs_used": 0, "wrong_attempts": 0, "puzzles": []}
    profile = Profile.model_validate({"results": {room_id: result}, "derived": Derived.fresh().model_dump()})
    assert set(Profile.model_fields) == {"results", "derived"} and Profile in API_MODELS
    assert isinstance(profile.results[room_id], RoomResult) and profile.derived == Derived.fresh()
    other = "room_01BX5ZZKBKACTAV9WEVGEMMVRZ"
    for bad in (
        {"results": {other: result}, "derived": Derived.fresh().model_dump()},
        {"results": {room_id: result}, "derived": {**Derived.fresh().model_dump(), "persistence": 1.5}},
        {"results": {room_id: {"room_id": room_id}}, "derived": Derived.fresh().model_dump()},
        {"results": {room_id: result}},
    ):
        with pytest.raises(ValidationError):
            Profile.model_validate(bad)


def test_meta_has_exactly_its_fields():
    assert set(Meta.model_fields) == {"mode", "guide", "guide_model", "trickster", "demo_timescale", "cache", "profile", "disclosure", "retention"}
    assert set(schema.GuideModel.model_fields) == {"id", "host"}
    meta = Meta.model_validate({
        "mode": "hosted", "guide": "verbatim", "guide_model": None, "trickster": "cut1", "demo_timescale": 1,
        "cache": "on", "profile": "dev", "disclosure": [], "retention": "r",
    })
    assert meta.guide_model is None
    with pytest.raises(ValidationError):
        Meta.model_validate({**meta.model_dump(), "trickster": "record"})


def test_room_view_and_play_view_declare_no_solution_or_profile_field():
    assert set(schema.InteractableView.model_fields) == {"id", "label", "attributes", "instances", "photo"}
    assert set(schema.PuzzleView.model_fields) == {"id", "lock_type", "requires", "is_exit", "clue", "lore", "rungs"}
    assert set(schema.PlayPuzzle.model_fields) == {
        "id", "lock_type", "requires", "is_exit", "clue", "lore", "evidence_cards", "sequence_length"}
    forbidden = {"solution", "evidence", "provenance", "decoys", "derived", "persistence", "sessions", "profile"}
    for view in (RoomView, PlayView):
        assert forbidden.isdisjoint(keys(view.model_json_schema())), view
    play_keys = set(keys(PlayView.model_json_schema()))
    assert "rungs" not in play_keys and "nudge" not in play_keys and "decoy" not in play_keys
    assert set(schema.Evidence.model_fields) == {"interactable", "visible_attribute"}


# --- Models later stories fill in ------------------------------------------


def test_job_state_statuses_and_fields():
    assert set(JobState.model_fields) >= {"id", "status", "stage", "stages", "sent_back", "calls", "build_time_ms", "mask_preview"}
    queued = JobState.model_validate({"id": JOB, "status": "queued", "regen_max": 2})
    assert queued.stage is None and queued.calls == [] and queued.mask_preview == []
    running = JobState.model_validate({**queued.model_dump(), "status": "running", "stage": "segment",
        "mask_preview": [{"id": IX[0], "label": "lamp", "photo": 0, "polygons": [[[0, 0], [1, 0], [1, 1]]]}]})
    assert running.mask_preview[0].label == "lamp"
    assert "solution" not in set(keys(JobState.model_json_schema()))
    for status in ("done", "failed", "needs_more_photos", "needs_recapture"):
        assert JobState.model_validate({**queued.model_dump(), "status": status}).status == status
    with pytest.raises(ValidationError):
        JobState.model_validate({**queued.model_dump(), "status": "running"})
    with pytest.raises(ValidationError):
        JobState.model_validate({**queued.model_dump(), "status": "cancelled"})


def test_session_state_fields():
    state = SessionState.model_validate({
        "id": SESS, "room_id": ROOM, "locks_open": [], "inventory": [], "current_rung": {PZ[0]: 0}, "wrong_attempts": {PZ[0]: 0},
        "rungs_used": 0, "order_buffer": {"puzzle_id": None, "clicks": []}, "active_puzzle_id": PZ[0],
        "opening_line": {"kind": "greeting", "text": None}, "phrasing": True, "rung_changes": [],
        "trickster_window": {"state": "pending", "index": 0}, "trickster_calls": 0, "cards": [], "room_revision": 0,
        "disclosure": [],
    })
    assert state.judge_room is False and state.thresholds is None and state.hint_reply is None and state.cards == []
    assert set(SessionState.model_fields) == {
        "id", "room_id", "locks_open", "inventory", "current_rung", "wrong_attempts", "rungs_used", "order_buffer",
        "active_puzzle_id", "opening_line", "phrasing", "rung_changes", "trickster_window", "trickster_calls", "cards",
        "room_revision", "disclosure", "judge_room", "thresholds", "hint_reply",
    }
    assert set(schema.HintReply.model_fields) == {"puzzle_id", "rung", "text"}
    assert set(schema.Thresholds.model_fields) == {
        "nudge_threshold_ms", "nudge_threshold_base_ms", "rung_spacing_ms", "rung_spacing_base_ms", "source",
    }
    assert SessionState.model_fields["cards"].annotation == list[TricksterCard]
    for forbidden in ("edit", "payload", "events", "log"):
        assert forbidden not in set(keys(SessionState.model_json_schema()))
    with pytest.raises(ValidationError):
        SessionState.model_validate({**state.model_dump(), "current_rung": {PZ[0]: 4}})
    with pytest.raises(ValidationError):
        SessionState.model_validate({**state.model_dump(), "trickster_calls": 7})


def test_room_summary_access_check_session_start_and_error_envelope():
    assert set(RoomSummary.model_fields) == {"room_id", "name", "cover_photo", "puzzle_count", "job_id", "built_at"}
    assert AccessCheck.model_validate({"ok": False, "builds_left": None}).builds_left is None
    assert AccessCheck.model_validate({"ok": True, "builds_left": 19}).builds_left == 19
    with pytest.raises(ValidationError):
        AccessCheck.model_validate({"ok": False, "builds_left": 3})
    start = SessionStart.model_validate({"room_id": ROOM})
    assert start.derived == Derived.fresh()
    with pytest.raises(ValidationError):
        SessionStart.model_validate({"room_id": ROOM, "derived": {**Derived.fresh().model_dump(), "persistence": 1.5}})
    assert set(ErrorEnvelope.model_fields) == {"error"}
    assert set(schema.ErrorDetail.model_fields) == {"code", "message", "stage", "status"}
    not_ready = ErrorEnvelope.model_validate({"error": {"code": "build_not_ready", "message": "m", "stage": None, "status": "running"}})
    assert not_ready.error.status == "running"
    assert not_ready.model_dump(mode="json") == {"error": {"code": "build_not_ready", "message": "m", "stage": None, "status": "running"}}
    other = ErrorEnvelope.model_validate({"error": {"code": "photo_count", "message": "m", "stage": "ingest"}})
    assert other.error.status is None and other.model_dump(mode="json") == {"error": {"code": "photo_count", "message": "m", "stage": "ingest"}}
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate({"error": {"code": "photo_count", "message": "m", "stage": "ingest", "status": "failed"}})
    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate({"error": {"code": "build_not_ready", "message": "m", "stage": None}, "status": "running"})


def test_build_view_fields_carry_no_solution():
    assert set(BuildView.model_fields) == {
        "room_id", "job_id", "name", "built_at", "build_time_ms", "photos", "puzzles", "validator", "dry_run",
        "regeneration_count", "regen_max", "sent_back", "models", "calls", "disclosure",
    }
    assert {"solution", "answer", "clue", "rungs"}.isdisjoint(keys(BuildView.model_json_schema()))
