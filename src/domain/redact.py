"""Projections that keep solutions and edit payloads on the server (AD-3).

`to_prompt_view` is the only shape a prompt builder accepts, `to_play_view`
the only shape a play route returns, `to_build_view` the Build view over a
Room and its final job record, and `to_card_view` the public card. The play
view holds evidence back (amended 29 Oct 2026, story mode): a Puzzle's cards
are empty until it is among the `opened` ones, and then hold its real card
alone, never a decoy. Each view
keeps exactly the fields its model declares, so a new `Room` field stays on
the server until a view names it. Every function is pure and returns new values.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any

from .masks import box_polygon
from .schema import (
    BuildView,
    CallRow,
    Evidence,
    FindSolution,
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
    UseOnSolution,
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


def _evidence_cards(puzzle: Puzzle, opened: Collection[str]) -> list[Evidence]:
    """The real card once the Puzzle's lock is open, else none; a decoy is never served."""
    return [puzzle.evidence] if puzzle.id in opened else []


def _start_photo(room: Room, puzzle: Puzzle) -> int:
    """The photo of the riddle's target (`find`, `use_on`) or of its evidence (`code`, `order`); photo 0 for an id the Room lacks."""
    solution = puzzle.solution
    named = solution.target if isinstance(solution, FindSolution | UseOnSolution) else puzzle.evidence.interactable
    return next((ix.photo for ix in room.interactables if ix.id == named), 0)


def _sequence_length(puzzle: Puzzle) -> int | None:
    """How many clicks an `order` Puzzle's sequence takes, the pips the client draws; None for any other lock type."""
    return len(puzzle.solution.interactables) if isinstance(puzzle.solution, OrderSolution) else None


def to_play_view(room: Room, *, opened: Collection[str] = ()) -> PlayView:
    """The client shape: masks, photo hashes and areas, start photos, the evidence of the `opened` Puzzles and the story; never a solution, a Rung, a decoy or a path."""
    return PlayView(
        id=room.id,
        created=room.created,
        name=room.name,
        photos=[PhotoView.model_validate(_narrow(photo, PhotoView)) for photo in room.photos],
        interactables=[PlayInteractable.model_validate(_narrow(ix, PlayInteractable)) for ix in room.interactables],
        puzzles=[
            PlayPuzzle.model_validate({
                **_narrow(puzzle, PlayPuzzle),
                "evidence_cards": _evidence_cards(puzzle, opened),
                "sequence_length": _sequence_length(puzzle),
                "start_photo": _start_photo(room, puzzle),
            })
            for puzzle in room.puzzles
        ],
        story=room.story,
    )


ROLE_STAGES: dict[Role, tuple[Stage, ...]] = {
    "architect": ("architect", "segment"),
    "riddler": ("author",),
    "dryrun": ("dryrun",),
    "storyteller": ("story",),
}
"""The stages whose done row a role's Model table row counts; segment's SAM calls run under the `architect` role."""
DONE_ROWS: dict[Stage, str] = {
    "architect": "found {n} object{s}",
    "segment": "outlined {n} object{s}",
    "author": "wrote {n} puzzle{s}",
    "dryrun": "tried {n} puzzle{s} blind",
    "story": "wrote {n} story line{s}",
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


def _card_puzzles(event: TricksterCardEvent) -> tuple[str | None, str | None]:
    """The Card's `puzzle_id` and `related_puzzle_id`: the event's puzzle and the second of a `merge` or `shortcut`.

    A `merge` proposal may name either Puzzle of its pair, so the Card names
    the one that now waits (`puzzle_b`) first and the one it waits on second,
    whichever the proposal named.
    """
    edit = event.edit
    if edit is None:
        return event.puzzle_id, None
    payload = edit.payload
    if payload.type == "merge":
        return payload.puzzle_b, payload.puzzle_a
    if payload.type == "shortcut":
        return event.puzzle_id, payload.requires
    return event.puzzle_id, None


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
    puzzle_id, related_puzzle_id = _card_puzzles(event)
    return TricksterCard(
        edit_id=event.edit_id,
        accepted=event.accepted,
        edit_type=None if edit is None else edit.type,
        puzzle_id=puzzle_id,
        related_puzzle_id=related_puzzle_id,
        room_revision=event.room_revision,
        reason=event.reason,
        message=_fixed_message(event),
        t_ms=event.t_ms,
    )
