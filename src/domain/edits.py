"""Trickster edits (AD-12): the bounds check, the edit itself and the Effective room folded from the session log.

`validate_edit(room, state, edit)` checks the Trickster's limits: the
window first, then the per-type payload bounds, each refusal a structured
reason with the bounds row's fixed message from the Validator table.
`apply_edit(room, edit)` returns a new Room with the edit folded in and its
id in `provenance.applied_edits`; the input Room is never changed, so the
stored build Room shared across Sessions keeps empty `applied_edits` and
`decoys`. An edit is accepted only when `check_edit` passes: the bounds,
then `validate(apply_edit(room, edit))` over rules 1 to 9, with no Dry run.

The session log is the only home of an edit: each `trickster_card` carries
its full `TricksterEdit`, and the Effective room is `apply_edit` folded over
the accepted ones in log order. Every function is pure and nothing here
reaches `ArtifactStore`; this module imports only the standard library,
pydantic and the domain (AD-1).
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import reduce

from .rungs import RUNG_NAMES
from .schema import (
    Decoy,
    DecoyPayload,
    Event,
    LoosenPayload,
    MergePayload,
    Room,
    SessionState,
    ShortcutPayload,
    TricksterCardEvent,
    TricksterEdit,
    ValidatorReason,
    ValidatorResult,
)
from .validator import BOUNDS_MESSAGE, BOUNDS_RULE, validate


def _window_bounds(state: SessionState, edit: TricksterEdit) -> list[tuple[str | None, str]]:
    """The edit belongs to the session's open window (pending while its source runs)."""
    window = state.trickster_window
    return [(None, "window")] if window.state == "closed" or window.index != edit.window else []


def _payload_bounds(room: Room, edit: TricksterEdit) -> list[tuple[str | None, str]]:
    """The per-type limits: the Puzzles, edge and Rung exist, and a Decoy goes to a non-exit Puzzle with none yet."""
    by_id = {puzzle.id: puzzle for puzzle in room.puzzles}
    found: list[tuple[str | None, str]] = []
    if edit.puzzle not in by_id:
        found.append((edit.puzzle, "puzzle"))
    match edit.payload:
        case DecoyPayload():
            target = by_id.get(edit.puzzle)
            if target is not None and target.is_exit:
                found.append((edit.puzzle, "puzzle"))
            if any(decoy.puzzle == edit.puzzle for decoy in room.decoys):
                found.append((edit.puzzle, "puzzle"))
        case MergePayload(puzzle_a=puzzle_a, puzzle_b=puzzle_b):
            found += [(pid, field) for field, pid in (("puzzle_a", puzzle_a), ("puzzle_b", puzzle_b)) if pid not in by_id]
            if edit.puzzle not in (puzzle_a, puzzle_b):
                found.append((edit.puzzle, "puzzle"))
        case LoosenPayload(puzzle=puzzle_id, rung=rung):
            if puzzle_id not in by_id or puzzle_id != edit.puzzle:
                found.append((puzzle_id, "puzzle"))
            if rung not in RUNG_NAMES:
                found.append((puzzle_id, "rung"))
        case ShortcutPayload(puzzle=puzzle_id, requires=requires):
            puzzle = by_id.get(puzzle_id)
            if puzzle is None or puzzle_id != edit.puzzle:
                found.append((puzzle_id, "puzzle"))
            if puzzle is not None and requires not in puzzle.requires:
                found.append((puzzle_id, "requires"))
    return found


def validate_edit(room: Room, state: SessionState, edit: TricksterEdit) -> ValidatorResult:
    """The Trickster's limits over the Effective room: the window bound first, and only inside it the payload bounds."""
    found = _window_bounds(state, edit) or _payload_bounds(room, edit)
    reasons = [
        ValidatorReason(rule=BOUNDS_RULE, puzzle_id=puzzle_id, field=field, message=BOUNDS_MESSAGE)
        for puzzle_id, field in dict.fromkeys(found)
    ]
    return ValidatorResult(ok=not reasons, reasons=reasons)


def apply_edit(room: Room, edit: TricksterEdit) -> Room:
    """A new Room with the edit folded in and its id in `provenance.applied_edits`; `room` is left as it was.

    A `merge` makes `puzzle_b` require `puzzle_a`, a `shortcut` removes one
    `requires` edge, a `decoy` appends one `decoys[]` entry, and a `loosen`
    leaves the Puzzles as they are (`SessionStateMachine.apply` opens its Rung).
    """
    edited = room.model_copy(deep=True)
    by_id = {puzzle.id: puzzle for puzzle in edited.puzzles}
    match edit.payload:
        case MergePayload(puzzle_a=puzzle_a, puzzle_b=puzzle_b):
            waiting = by_id.get(puzzle_b)
            if waiting is not None and puzzle_a not in waiting.requires:
                waiting.requires.append(puzzle_a)
        case ShortcutPayload(puzzle=puzzle_id, requires=requires):
            freed = by_id.get(puzzle_id)
            if freed is not None and requires in freed.requires:
                freed.requires.remove(requires)
        case DecoyPayload(interactable=interactable, visible_attribute=visible_attribute):
            edited.decoys.append(
                Decoy(id=edit.id, puzzle=edit.puzzle, interactable=interactable, visible_attribute=visible_attribute)
            )
        case LoosenPayload():
            pass
    edited.provenance.applied_edits.append(edit.id)
    return edited


def check_edit(room: Room, state: SessionState, edit: TricksterEdit) -> ValidatorResult:
    """The verdict on a proposal: the bounds, then rules 1 to 9 over `apply_edit(room, edit)`; never a Dry run."""
    bounds = validate_edit(room, state, edit)
    return validate(apply_edit(room, edit)) if bounds.ok else bounds


def accepted_edit(event: Event) -> TricksterEdit | None:
    """The `TricksterEdit` an accepted `trickster_card` carries, else None."""
    if isinstance(event, TricksterCardEvent) and event.accepted:
        return event.edit
    return None


def effective_room(room: Room, events: Iterable[Event]) -> Room:
    """The stored Room with every accepted edit in the log folded in, in log order; a rejected or skipped card adds nothing."""
    edits = [edit for event in events if (edit := accepted_edit(event)) is not None]
    return reduce(apply_edit, edits, room)
