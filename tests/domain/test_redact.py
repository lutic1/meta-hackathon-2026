"""Story 1.5: `to_card_view`, the public card projection (AD-3)."""

import json
from typing import Any

from src.domain.redact import to_card_view
from src.domain.schema import TricksterCard, TricksterCardEvent

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
