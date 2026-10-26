"""The scene stage (AD-7, AD-12, AD-16): the Room written once, then immutable, and the Dry run skipped under cut 4.

The runner reaches scene only after `validate` passed and, unless
`DRY_RUN=off`, the Dry run passed on the same attempt. `run_scene` assembles
the Room from the stored photos, Interactables and mapped Puzzles with its
provenance (model ids, prompt hashes, stage timings, the Regeneration count,
spend per stage from the ledger) and writes it through `ArtifactStore` under
`<room_id>/room.json`, the one `room` artifact play routes read. A Room
already stored under that key is left as it is, so a runner restarted after
scene never rewrites it. Its done row is the scene count, one scene per
photo ("Setting the scene"), and the runner then persists the job `done`,
the job's final record beside the Room. A job that ends any other way never
reaches scene, so it has no `room` artifact. The 10 s budget (`budgets.md`)
is measured by the runner's stage timing, never enforced.

With `DRY_RUN=off` (cut 4) wiring puts `run_skipped_dry_run` in the `dryrun`
slot: it makes no call, so no ledger entry, records every Puzzle's Dry run
verdict as `skipped`, and the Validator's pass alone lets scene write the Room.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.domain.schema import DryRunVerdict, JobState, Room, RoomId
from src.pipeline.author import assemble_provenance, prompt_hashes, prompt_view, read_puzzles
from src.pipeline.build import StageFn, StageResult
from src.pipeline.ingest import read_photos
from src.pipeline.ports import ArtifactStore, LedgerStore, room_key
from src.pipeline.segment import read_interactables

SCENE_BUDGET_MS = 10_000
"""`budgets.md`: the scene build's 10 s, measured through the stage timing, never enforced."""


def _room_id(state: JobState) -> RoomId:
    if state.room_id is None:
        raise ValueError(f"{state.id} names no room")
    return state.room_id


def _stored(key: str, artifacts: ArtifactStore) -> bool:
    try:
        artifacts.read(key)
    except KeyError:
        return False
    return True


def run_scene(state: JobState, *, artifacts: ArtifactStore, ledger: LedgerStore) -> StageResult:
    """The Room written once under `<room_id>/room.json`, never over a stored one; the done row counts its scenes."""
    room_id = _room_id(state)
    photos = read_photos(room_id, artifacts)
    key = room_key(room_id)
    if not _stored(key, artifacts):
        interactables = read_interactables(room_id, artifacts)
        room = Room(
            id=room_id,
            created=datetime.now(UTC),
            photos=photos,
            interactables=interactables,
            puzzles=read_puzzles(room_id, artifacts),
            provenance=assemble_provenance(state, ledger.entries(), prompt_hashes(prompt_view(room_id, interactables))),
        )
        artifacts.put(key, room.model_dump_json().encode())
    return StageResult(count=len(photos))


def run_skipped_dry_run(state: JobState, *, artifacts: ArtifactStore) -> StageResult:
    """`DRY_RUN=off`: no call and no ledger entry; every Puzzle of the draft that passed `validate` recorded `skipped`."""
    puzzles = read_puzzles(_room_id(state), artifacts)
    return StageResult(dry_run=[DryRunVerdict(puzzle_id=puzzle.id, verdict="skipped") for puzzle in puzzles])


def scene_stage(artifacts: ArtifactStore, ledger: LedgerStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `scene`."""
    return lambda state: run_scene(state, artifacts=artifacts, ledger=ledger)


def skipped_dry_run_stage(artifacts: ArtifactStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `dryrun` under `DRY_RUN=off` (cut 4)."""
    return lambda state: run_skipped_dry_run(state, artifacts=artifacts)
