"""Projections that keep solutions and edit payloads on the server (AD-3).

`to_card_view` lands here with Schema v1; `to_prompt_view`, `to_play_view`
and `to_build_view` follow in their own stories. Every function is pure.
"""

from __future__ import annotations

from .schema import TricksterCard, TricksterCardEvent, TricksterEdit


def _related_puzzle(edit: TricksterEdit) -> str | None:
    """The second puzzle of a `merge` or `shortcut`, else None."""
    payload = edit.payload
    if payload.type == "merge":
        return payload.puzzle_b if payload.puzzle_a == edit.puzzle else payload.puzzle_a
    if payload.type == "shortcut":
        return payload.requires
    return None


def _fixed_message(event: TricksterCardEvent) -> str | None:
    """The Validator's fixed message for the failing rule on a rejected card, else None."""
    if event.accepted or event.edit is None:
        return None
    reasons = event.edit.validator_result.reasons
    for reason in reasons:
        if reason.rule == event.reason:
            return reason.message
    return reasons[0].message if reasons else None


def to_card_view(event: TricksterCardEvent) -> TricksterCard:
    """The public card: ids, type, outcome, reason and fixed message; never the payload."""
    edit = event.edit
    return TricksterCard(
        edit_id=event.edit_id,
        accepted=event.accepted,
        edit_type=None if edit is None else edit.type,
        puzzle_id=event.puzzle_id,
        related_puzzle_id=None if edit is None else _related_puzzle(edit),
        room_revision=event.room_revision,
        reason=event.reason,
        message=_fixed_message(event),
        t_ms=event.t_ms,
    )
