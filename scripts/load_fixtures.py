#!/usr/bin/env python3
"""Store the two synthetic fixture rooms under `rooms/` so `GET /rooms` lists them, and the four-lock recording beside them (AD-7, AD-9, AD-15).

    uv run scripts/load_fixtures.py               # stores under rooms/
    uv run scripts/load_fixtures.py <rooms_root>  # stores under another root

The scenes are drawn into a temporary directory, never a real room photo,
and each Room is stored through the local `ArtifactStore` only after
`validate` returns no reasons: its downscaled photos under
`<room_id>/photos/<i>.jpg` (the keys the room routes read; the synthetic
scene is its own original), then the Room itself last, so a run that
stopped early is completed by the next. A `done` job record with a fixed
id is written under `rooms/jobs/` beside each, since `RoomSummary.job_id`
and the Build view read it: the record the mock build the Room's provenance
describes leaves (stage records, one zero-spend call row per role on the
mock host, the Validator's verdict on every rule, a Dry run pass per
Puzzle) with `regen_max` from the settings. A Room already stored is left
alone, so a second run stores no duplicate; only its job record is
rewritten, and only when it is missing or is the thin record loaders
before this one wrote (no Validator verdicts or no call rows), so a
`rooms/` loaded earlier shows a complete Build view after one more run.

The four-lock recording (`tests/fixtures/proposals/four_lock.json`, bound to
the stored four-lock Room) is written under `<rooms_root>/proposals/`, the
git-ignored folder beside the rooms and never the repo's own `proposals/`,
which holds the real recording; the script prints the env line that makes
`DEMO_TRICKSTER=scripted` replay it in local play (AD-12, AD-15).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` and the fixture module import from any working directory

from src.api.wiring import artifact_store, job_store
from src.config import Settings
from src.council.trickster import RECORDED_PROPOSALS, RecordedProposals, load_proposals
from src.domain.schema import (
    CallRow,
    DryRunVerdict,
    JobId,
    JobState,
    Photo,
    Room,
    Stage,
    StageRecord,
)
from src.domain.validator import ValidatorResult, validate
from src.infra.local import ROOMS_ROOT
from src.pipeline.author import STAGE_ROLES, rule_verdicts
from src.pipeline.build import STAGES, new_id
from src.pipeline.ports import ArtifactStore, JobStore, photo_key, room_key
from src.providers.mock import MockProvider
from tests.fixtures.rooms import ROOM_IDS, write_fixtures

JOB_IDS = {ROOM_IDS["four_lock"]: "job_" + "0" * 25 + "1", ROOM_IDS["code_and_find"]: "job_" + "0" * 25 + "2"}
"""One fixed job id per fixture room, so a reload names the same record."""
FIXTURE_PROPOSALS = REPO / "tests/fixtures/proposals/four_lock.json"
"""The 4.3 recording for the four-lock room: window 0's Decoy passes, window 1's Merge fails rule 1."""
PROPOSALS_DIR = Path("proposals")
"""Where the recording is installed under the rooms root, for `DEMO_PROPOSALS_DIR`."""


def is_stored(store: ArtifactStore, room: Room) -> bool:
    try:
        store.read(room_key(room.id))
    except KeyError:
        return False
    return True


def has_complete_job(jobs: JobStore, job_id: JobId) -> bool:
    try:
        job = jobs.read(job_id)
    except KeyError:
        return False
    return bool(job.validator and job.calls)


def done_job(room: Room, job_id: JobId, result: ValidatorResult, regen_max: int) -> JobState:
    """The final record of the mock build the Room's provenance describes: its timings, models and spend, nothing more."""
    provenance = room.provenance
    counts: dict[Stage, int | None] = {
        "ingest": len(room.photos),
        "architect": len(room.interactables),
        "segment": len(room.interactables),
        "author": len(room.puzzles),
        "validate": None,
        "dryrun": len(room.puzzles),
        "scene": len(room.photos),
    }
    models = {stage: provenance.model_ids.get(role) for stage, role in STAGE_ROLES.items()}
    stages = [
        StageRecord(stage=stage, duration_ms=provenance.stage_timings_ms.get(stage, 0), count=counts[stage], model=models.get(stage))
        for stage in STAGES
    ]
    calls = [
        CallRow(
            id=new_id("call"),
            role=STAGE_ROLES[stage],
            model=model,
            host=MockProvider.name,
            cached=False,
            spend_usd=provenance.spend_per_stage_usd.get(stage, 0.0),
        )
        for stage, model in models.items()
        if model is not None
    ]
    return JobState(
        id=job_id,
        status="done",
        room_id=room.id,
        stages=stages,
        regeneration_count=provenance.regeneration_count,
        regen_max=regen_max,
        validator=rule_verdicts(result),
        dry_run=[DryRunVerdict(puzzle_id=puzzle.id, verdict="pass") for puzzle in room.puzzles],
        calls=calls,
        build_time_ms=sum(record.duration_ms for record in stages),
    )


def store_room(store: ArtifactStore, room: Room) -> Room:
    """Store each downscaled photo under its key, then the Room pointing at those keys; returns the stored Room."""
    photos: list[Photo] = []
    for index, photo in enumerate(room.photos):
        key = photo_key(room.id, index)
        store.put(key, Path(photo.downscaled_path).read_bytes())
        photos.append(photo.model_copy(update={"downscaled_path": key, "original_path": key}))
    stored = room.model_copy(update={"photos": photos})
    store.put(room_key(room.id), stored.model_dump_json().encode())
    return stored


def install_proposals(root: Path, store: ArtifactStore) -> Path:
    """Write the four-lock recording at `<root>/proposals/recorded.json`, once it loads and names a Room `store` holds; returns the path."""
    recording: RecordedProposals = load_proposals(FIXTURE_PROPOSALS)
    try:
        store.read(room_key(recording.room_id))
    except KeyError:
        raise ValueError(f"{FIXTURE_PROPOSALS} is bound to {recording.room_id}, which is not stored under {root}/") from None
    path = root / PROPOSALS_DIR / RECORDED_PROPOSALS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(recording.model_dump_json(indent=2) + "\n")
    return path


def load_fixtures(store: ArtifactStore, jobs: JobStore, scenes_dir: Path, *, regen_max: int) -> list[Room]:
    """Store every fixture room not stored yet, each once validated, and complete a stored room's thin job record; returns the Rooms this run stored."""
    loaded: list[Room] = []
    for room in write_fixtures(scenes_dir):
        result = validate(room)
        if result.reasons:
            raise ValueError(f"fixture room {room.id} fails validation: " + "; ".join(r.message for r in result.reasons))
        if is_stored(store, room):
            if not has_complete_job(jobs, JOB_IDS[room.id]):
                jobs.put(done_job(room, JOB_IDS[room.id], result, regen_max))
            continue
        jobs.put(done_job(room, JOB_IDS[room.id], result, regen_max))
        loaded.append(store_room(store, room))
    return loaded


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else ROOMS_ROOT
    store = artifact_store(root)
    with tempfile.TemporaryDirectory() as scenes:
        loaded = load_fixtures(store, job_store(root), Path(scenes), regen_max=Settings.from_env().regen_max)
    for room in loaded:
        print(f"stored {room.id} ({len(room.puzzles)} puzzles) under {root}/")
    if not loaded:
        print(f"both fixture rooms are already stored under {root}/")
    installed = install_proposals(root, store)
    print(f"installed the four-lock recording at {installed}; to replay it in local play:")
    print(f"  DEMO_TRICKSTER=scripted DEMO_PROPOSALS_DIR={root / PROPOSALS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
