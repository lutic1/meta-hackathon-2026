#!/usr/bin/env python3
"""Store the two synthetic fixture rooms under `rooms/` so `GET /rooms` lists them (AD-7, AD-9).

    uv run scripts/load_fixtures.py               # stores under rooms/
    uv run scripts/load_fixtures.py <rooms_root>  # stores under another root

The scenes are drawn into a temporary directory, never a real room photo,
and each Room is stored through the local `ArtifactStore` only after
`validate` returns no reasons: its downscaled photos under
`<room_id>/photos/<i>.jpg` (the keys the room routes read; the synthetic
scene is its own original), then the Room itself last, so a run that
stopped early is completed by the next. A `done` job record with a fixed
id is written under `rooms/jobs/` beside each, since `RoomSummary.job_id`
reads it. A Room already stored is left alone, so a second run stores no
duplicate.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` and the fixture module import from any working directory

from src.api.wiring import artifact_store, job_store
from src.domain.schema import JobState, Photo, Room
from src.domain.validator import validate
from src.infra.local import ROOMS_ROOT
from src.pipeline.ports import ArtifactStore, JobStore, photo_key, room_key
from tests.fixtures.rooms import ROOM_IDS, write_fixtures

JOB_IDS = {ROOM_IDS["four_lock"]: "job_" + "0" * 25 + "1", ROOM_IDS["code_and_find"]: "job_" + "0" * 25 + "2"}
"""One fixed job id per fixture room, so a reload names the same record."""


def is_stored(store: ArtifactStore, room: Room) -> bool:
    try:
        store.read(room_key(room.id))
    except KeyError:
        return False
    return True


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


def load_fixtures(store: ArtifactStore, jobs: JobStore, scenes_dir: Path) -> list[Room]:
    """Store every fixture room not stored yet, each once validated; returns the Rooms this run stored."""
    loaded: list[Room] = []
    for room in write_fixtures(scenes_dir):
        result = validate(room)
        if result.reasons:
            raise ValueError(f"fixture room {room.id} fails validation: " + "; ".join(r.message for r in result.reasons))
        if is_stored(store, room):
            continue
        jobs.put(JobState(id=JOB_IDS[room.id], status="done", room_id=room.id, regen_max=0, build_time_ms=0))
        loaded.append(store_room(store, room))
    return loaded


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else ROOMS_ROOT
    with tempfile.TemporaryDirectory() as scenes:
        loaded = load_fixtures(artifact_store(root), job_store(root), Path(scenes))
    for room in loaded:
        print(f"stored {room.id} ({len(room.puzzles)} puzzles) under {root}/")
    if not loaded:
        print(f"both fixture rooms are already stored under {root}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
