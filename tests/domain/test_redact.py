"""Stories 1.5 and 1.7: the public card, prompt and play projections (AD-3)."""

import json
from typing import Any

from src.domain.redact import to_card_view, to_play_view, to_prompt_view
from src.domain.schema import (
    Derived,
    InteractableView,
    PlayView,
    PuzzleView,
    Room,
    RoomView,
    TricksterCard,
    TricksterCardEvent,
)
from src.domain.validator import RULES
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
    assert to_card_view(merge).related_puzzle_id == PZ_B
    assert to_card_view(shortcut).related_puzzle_id == PZ_A
    assert to_card_view(loosen).related_puzzle_id is None


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
    assert [photo.model_dump() for photo in view.photos] == [{"hash": p.hash, "size": p.size} for p in named.photos]
    for got, ix in zip(view.interactables, named.interactables, strict=True):
        assert got.polygons == ix.polygons and got.id == ix.id and got.label == ix.label
    for got, puzzle in zip(view.puzzles, named.puzzles, strict=True):
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


def test_play_view_merges_decoys_into_unflagged_evidence_cards_in_a_stable_order(four_lock_room: Room):
    room = with_decoys(
        four_lock_room,
        ("clock_code", "rug", "faded red"),
        ("door_code", "rug", "lies by the door"),
        ("find_key", "candle", "white wax"),
    )
    view = to_play_view(room)
    cards = {puzzle.id: puzzle.evidence_cards for puzzle in view.puzzles}
    assert len(cards[PZ["clock_code"]]) == 2 and len(cards[PZ["door_code"]]) == 2 and len(cards[PZ["find_key"]]) == 2
    assert len(cards[PZ["shelf_order"]]) == 1 and len(cards[PZ["key_on_chest"]]) == 1
    for puzzle in room.puzzles:
        assert puzzle.evidence in cards[puzzle.id]
        assert all(set(card.model_dump()) == {"interactable", "visible_attribute"} for card in cards[puzzle.id])
    real_first = [cards[puzzle.id][0] == puzzle.evidence for puzzle in room.puzzles if len(cards[puzzle.id]) > 1]
    assert True in real_first and False in real_first  # no position marks the real card
    assert to_play_view(room) == view
    text = json.dumps(view.model_dump(mode="json"))
    assert "te_" not in text and '"decoys"' not in text
