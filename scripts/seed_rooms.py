#!/usr/bin/env python3
"""Seed the Demo rooms onto the hosted `keyframe-data` Volume, each with its name and final job record (AD-7, AD-9).

    uv run scripts/seed_rooms.py --room <room_id> "<name>" [--room ...]
    uv run scripts/seed_rooms.py --env main --rooms rooms --room ...

Each `--room` names a Room built locally under the git-ignored `rooms/` and
the `Room.name` it is seeded with. Everything is read and checked before
anything is written: the stored Room, its downscaled photos, the Clue cards
7.4 stored for it (the files under `<room_id>/` keyed by one of its `pz_`
ids, when there are any) and the `done` job record under `rooms/jobs/` that
names it. A name the schema refuses (more than 40 characters), a Room with
no `done` record, or a record without stage timings, call rows, validator
and Dry run verdicts and a build time refuses the whole run, and the
Volume is never opened. The originals are not seeded: play reads the
downscaled photos only.

The files then go up in one `batch_upload(force=True)`, so a reseed
overwrites the earlier files, and the batch is committed to the Volume
when the block exits: the Room with its name at
`rooms/demo/<room_id>/room.json`, its photos at
`rooms/demo/<room_id>/photos/<i>.jpg`, its Clue cards at the same keys
under `rooms/demo/`, and the job record at `rooms/demo/<room_id>/job.json`,
where the hosted `JobStore` falls through to it once the Dict holds no
entry (AD-7). The local stores are only read, so nothing under `rooms/` or
`.cache/` changes; no Dict is touched, so the hosted `LedgerStore` gains
no entry. The Volume is resolved in the Environment `--env` names
(default `main`), never the CLI's active one, and needs a Modal token.
"""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from pydantic import ValidationError

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from src.api.wiring import artifact_store, job_store
from src.domain.schema import JobState, Room
from src.infra.local import ROOMS_ROOT
from src.infra.modal import DEMO_PARTITION, JOB_FILE, ROOMS_DIR, VOLUME
from src.pipeline.ports import photo_key, room_key

ENVIRONMENT = "main"
"""The Modal Environment the judge app is deployed in, passed to `from_name` explicitly."""
DEMO_PREFIX = f"/{ROOMS_DIR}/{DEMO_PARTITION}"
"""Where every seeded file lands on the Volume, the partition the hosted `ArtifactStore` lists."""


class SeedRefused(Exception):
    """A Demo room that cannot be seeded; raised before anything is written."""


class Batch(Protocol):
    """The `put_file` of the context `modal.Volume.batch_upload` yields."""

    def put_file(self, local_file: BinaryIO, remote_path: str) -> None: ...


class Volume(Protocol):
    """The one `modal.Volume` call the script makes from outside a container."""

    def batch_upload(self, force: bool = False) -> AbstractContextManager[Batch]: ...


@dataclass(frozen=True)
class DemoRoom:
    """A `--room` argument: the stored Room and the name it is seeded with."""

    room_id: str
    name: str


@dataclass(frozen=True)
class Seed:
    """One Demo room ready to upload: the named Room, its job record and every Volume path with its bytes."""

    room: Room
    job: JobState
    files: dict[str, bytes]


def named(room: Room, name: str) -> Room:
    """The Room with `name` set, revalidated so the schema's bound (at most 40 characters) decides."""
    try:
        return Room.model_validate({**room.model_dump(), "name": name})
    except ValidationError:
        raise SeedRefused(f"{room.id}: the name {name!r} is longer than 40 characters") from None


def final_job(root: Path, room_id: str) -> JobState:
    """The `done` job record that names the Room, holding everything the Build view reads."""
    jobs = job_store(root)
    done = [job for job in map(jobs.read, jobs.list_ids()) if job.room_id == room_id and job.status == "done"]
    if not done:
        raise SeedRefused(f"{room_id}: no done job record names this Room under {root}/")
    return checked(done[-1])


def checked(job: JobState) -> JobState:
    """The `done` record once it holds everything the Build view reads; one missing a part refuses the run."""
    missing = [
        field
        for field, absent in (
            ("stage timings", not job.stages),
            ("call rows", not job.calls),
            ("validator verdicts", not job.validator),
            ("Dry run verdicts", not job.dry_run),
            ("build time", job.build_time_ms is None),
        )
        if absent
    ]
    if missing:
        raise SeedRefused(f"{job.room_id}: job record {job.id} has no " + ", ".join(missing))
    return job


def card_keys(root: Path, room: Room) -> list[str]:
    """The artifact keys under `<room_id>/` whose file name is one of the Room's `pz_` ids: its Clue cards (7.4)."""
    puzzle_ids = {puzzle.id for puzzle in room.puzzles}
    folder = root / room.id
    paths = sorted(path for path in folder.rglob("*") if path.is_file() and path.stem in puzzle_ids) if folder.is_dir() else []
    return [path.relative_to(root).as_posix() for path in paths]


def plan(root: Path, demo_rooms: Sequence[DemoRoom]) -> list[Seed]:
    """Read and check every Demo room; any refusal raises `SeedRefused` and nothing is written."""
    ids = [demo.room_id for demo in demo_rooms]
    if not ids:
        raise SeedRefused("name at least one Demo room with --room <room_id> <name>")
    if len(set(ids)) != len(ids):
        raise SeedRefused("a Demo room is named twice")
    store = artifact_store(root)
    seeds: list[Seed] = []
    for demo in demo_rooms:
        try:
            stored = Room.model_validate_json(store.read(room_key(demo.room_id)))
        except (KeyError, ValueError):
            raise SeedRefused(f"{demo.room_id}: no Room is stored under {root}/") from None
        room = named(stored, demo.name)
        job = final_job(root, room.id)
        keys = [photo_key(room.id, index) for index in range(len(room.photos))] + card_keys(root, room)
        seeds.append(Seed(room=room, job=job, files=demo_files(room, job, {key: store.read(key) for key in keys})))
    return seeds


def demo_files(room: Room, job: JobState, artifacts: Mapping[str, bytes]) -> dict[str, bytes]:
    """Every Volume path of one Demo room with its bytes: the photos and Clue cards in `artifacts` by key, the named Room and its job record."""
    files = {f"{DEMO_PREFIX}/{key}": data for key, data in artifacts.items()}
    files[f"{DEMO_PREFIX}/{room_key(room.id)}"] = room.model_dump_json().encode()
    files[f"{DEMO_PREFIX}/{room.id}/{JOB_FILE}"] = job.model_dump_json().encode()
    return files


def seed(volume: Volume, seeds: Sequence[Seed]) -> None:
    """Upload every file in one batch that may overwrite an earlier seed; the Volume commits when the block exits."""
    with volume.batch_upload(force=True) as batch:
        for item in seeds:
            for path, data in item.files.items():
                batch.put_file(io.BytesIO(data), path)


def open_volume(environment: str) -> Volume:
    """`keyframe-data` in `environment`; no `create_if_missing`, so a wrong Environment fails instead of seeding an empty Volume."""
    import modal

    return modal.Volume.from_name(VOLUME, environment_name=environment)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Seed the Demo rooms onto the keyframe-data Volume.")
    parser.add_argument("--room", nargs=2, action="append", default=[], metavar=("ROOM_ID", "NAME"), help="a stored Room and its name")
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment (default {ENVIRONMENT})")
    parser.add_argument("--rooms", type=Path, default=ROOMS_ROOT, help=f"the local rooms root (default {ROOMS_ROOT})")
    args = parser.parse_args(argv)
    try:
        seeds = plan(args.rooms, [DemoRoom(room_id, name) for room_id, name in args.room])
    except SeedRefused as refusal:
        print(f"refused, nothing written: {refusal}", file=sys.stderr)
        return 1
    seed(open_volume(args.env), seeds)
    for item in seeds:
        print(f"seeded {item.room.id} {item.room.name!r} with {item.job.id}: {len(item.files)} files under {DEMO_PREFIX}/ in {args.env}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
