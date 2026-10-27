"""Projections that keep solutions and edit payloads on the server (AD-3).

`to_prompt_view` is the only shape a prompt builder accepts, `to_play_view`
the only shape a play route returns, `to_build_view` the Build view over a
Room and its final job record, and `to_card_view` the public card. Each view
keeps exactly the fields its model declares, so a new `Room` field stays on
the server until a view names it. Every function is pure and returns new values.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from .masks import box_polygon
from .schema import (
    BuildView,
    CallRow,
    Evidence,
    Interactable,
    InteractableView,
    JobState,
    MaskOverlay,
    Model,
    ModelRow,
    OrderSolution,
    PhotoMasks,
    PhotoView,
    PlayInteractable,
    PlayPuzzle,
    PlayView,
    Puzzle,
    PuzzleNode,
    PuzzleView,
    Role,
    Room,
    RoomView,
    Stage,
    StageRecord,
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


def _sequence_length(puzzle: Puzzle) -> int | None:
    """How many clicks an `order` Puzzle's sequence takes, the pips the client draws; None for any other lock type."""
    return len(puzzle.solution.interactables) if isinstance(puzzle.solution, OrderSolution) else None


def to_play_view(room: Room) -> PlayView:
    """The client shape: masks, photo hashes and evidence cards; never a solution, a Rung, a decoy mark or a path."""
    return PlayView(
        id=room.id,
        created=room.created,
        name=room.name,
        photos=[PhotoView.model_validate(_narrow(photo, PhotoView)) for photo in room.photos],
        interactables=[PlayInteractable.model_validate(_narrow(ix, PlayInteractable)) for ix in room.interactables],
        puzzles=[
            PlayPuzzle.model_validate({
                **_narrow(puzzle, PlayPuzzle),
                "evidence_cards": _evidence_cards(room, puzzle),
                "sequence_length": _sequence_length(puzzle),
            })
            for puzzle in room.puzzles
        ],
    )


ROLE_STAGES: dict[Role, tuple[Stage, ...]] = {
    "architect": ("architect", "segment"),
    "riddler": ("author",),
    "dryrun": ("dryrun",),
}
"""The stages whose done row a role's Model table row counts; segment's SAM calls run under the `architect` role."""
DONE_ROWS: dict[Stage, str] = {
    "architect": "found {n} object{s}",
    "segment": "outlined {n} object{s}",
    "author": "wrote {n} puzzle{s}",
    "dryrun": "tried {n} puzzle{s} blind",
}
"""The provenance count a stage's done row reads as in the Model table's "what it did" column."""


def _polygons(ix: Interactable) -> list[list[tuple[float, float]]]:
    """The Interactable's polygons; its box rectangle when it has none (AD-11)."""
    return [list(poly) for poly in ix.polygons] if ix.polygons is not None else [box_polygon(ix.box)]


def _photo_masks(room: Room) -> list[PhotoMasks]:
    """Per photo, in upload order, each Interactable's polygons with its label."""
    return [
        PhotoMasks(
            photo=index,
            masks=[
                MaskOverlay(interactable_id=ix.id, label=ix.label, polygons=_polygons(ix))
                for ix in room.interactables
                if ix.photo == index
            ],
        )
        for index in range(len(room.photos))
    ]


def _summary(role: Role, model: str, stages: list[StageRecord]) -> str:
    """The provenance count behind a Model table row: the role's latest counted done row run by `model`, else ""."""
    matched = [
        record for record in stages
        if record.stage in ROLE_STAGES.get(role, ()) and record.count is not None and record.model == model
    ]
    if not matched:
        return ""
    record = matched[-1]
    return DONE_ROWS[record.stage].format(n=record.count, s="" if record.count == 1 else "s")


def _model_rows(job: JobState) -> list[ModelRow]:
    """One row per role, model and host that ran, in call order, with its cached and billed counts (AD-16)."""
    groups: dict[tuple[Role, str, str], list[CallRow]] = {}
    for row in job.calls:
        groups.setdefault((row.role, row.model, row.host), []).append(row)
    return [
        ModelRow(
            role=role,
            model=model,
            host=host,
            cached=sum(row.cached for row in rows),
            billed=sum(not row.cached for row in rows),
            summary=_summary(role, model, job.stages),
        )
        for (role, model, host), rows in groups.items()
    ]


def to_build_view(room: Room, job: JobState, *, disclosure: Sequence[str] = ()) -> BuildView:
    """The Build view: masks, the puzzle graph, verdicts, regenerations, the Model table and call rows.

    Never a solution, evidence, Clue text, Dry run answer or Clue-to-answer
    pairing; `disclosure` is the Room's list as given (AD-15).
    """
    if job.room_id != room.id:
        raise ValueError(f"{job.id} built {job.room_id}, not {room.id}")
    recorded = job.model_dump(include={"validator", "dry_run", "regeneration_count", "regen_max", "sent_back", "calls"})
    return BuildView.model_validate({
        **recorded,
        "room_id": room.id,
        "job_id": job.id,
        "name": room.name,
        "built_at": room.created,
        "build_time_ms": job.build_time_ms if job.build_time_ms is not None else sum(s.duration_ms for s in job.stages),
        "photos": _photo_masks(room),
        "puzzles": [_narrow(puzzle, PuzzleNode) for puzzle in room.puzzles],
        "models": _model_rows(job),
        "disclosure": list(disclosure),
    })


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
