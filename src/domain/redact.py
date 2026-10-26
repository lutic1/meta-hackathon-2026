"""Projections that keep solutions and edit payloads on the server (AD-3).

`to_prompt_view` is the only shape a prompt builder accepts, `to_play_view`
the only shape a play route returns and `to_card_view` the public card;
`to_build_view` follows in its own story. Each view keeps exactly the fields
its model declares, so a new `Room` field stays on the server until a view
names it. Every function is pure and returns new values.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .schema import (
    Evidence,
    InteractableView,
    Model,
    PhotoView,
    PlayInteractable,
    PlayPuzzle,
    PlayView,
    Puzzle,
    PuzzleView,
    Room,
    RoomView,
    TricksterCard,
    TricksterCardEvent,
    TricksterEdit,
)


def _narrow(source: Model, view: type[Model]) -> dict[str, Any]:
    """`source` dumped to the fields `view` declares; every other field is dropped."""
    return source.model_dump(include=set(view.model_fields))


def to_prompt_view(room: Room) -> RoomView:
    """The prompt shape: labels, attributes and puzzle text; never a solution, evidence, photo or mask."""
    return RoomView(
        id=room.id,
        interactables=[InteractableView.model_validate(_narrow(ix, InteractableView)) for ix in room.interactables],
        puzzles=[PuzzleView.model_validate(_narrow(puzzle, PuzzleView)) for puzzle in room.puzzles],
    )


def _card_rank(room_id: str, puzzle_id: str, card: Evidence) -> str:
    """A card's place in `evidence_cards`: a digest seeded by the room id, so no position marks the real card."""
    seed = f"{room_id}\n{puzzle_id}\n{card.interactable}\n{card.visible_attribute}"
    return hashlib.sha256(seed.encode()).hexdigest()


def _evidence_cards(room: Room, puzzle: Puzzle) -> list[Evidence]:
    """The real card and the puzzle's decoys in one stable order; nothing marks which is false."""
    decoys = [
        Evidence(interactable=decoy.interactable, visible_attribute=decoy.visible_attribute)
        for decoy in room.decoys
        if decoy.puzzle == puzzle.id
    ]
    return sorted([puzzle.evidence, *decoys], key=lambda card: _card_rank(room.id, puzzle.id, card))


def to_play_view(room: Room) -> PlayView:
    """The client shape: masks, photo hashes and evidence cards; never a solution, a Rung, a decoy mark or a path."""
    return PlayView(
        id=room.id,
        created=room.created,
        name=room.name,
        photos=[PhotoView.model_validate(_narrow(photo, PhotoView)) for photo in room.photos],
        interactables=[PlayInteractable.model_validate(_narrow(ix, PlayInteractable)) for ix in room.interactables],
        puzzles=[
            PlayPuzzle.model_validate({**_narrow(puzzle, PlayPuzzle), "evidence_cards": _evidence_cards(room, puzzle)})
            for puzzle in room.puzzles
        ],
    )


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
