#!/usr/bin/env python3
"""Promote a Judge room on the hosted `keyframe-data` Volume to the Demo partition, with its name and final job record (AD-7, AD-9).

    uv run scripts/promote_room.py --room <room_id> "<name>"
    uv run scripts/promote_room.py --env main --room <room_id> "<name>"

The Demo room is a Judge room built on the judge URL, copied on the Volume
from `rooms/judge/<room_id>/` to `rooms/demo/<room_id>/` with `Room.name`
set; nothing comes from this machine. Everything is read and checked
through the remote Volume calls (`read_file`, `listdir`) before anything is
written: the stored Room, its downscaled photos, the Clue cards 7.4 stored
for it (the files under its folder keyed by one of its `pz_` ids, when
there are any) and the `done` job record at `job.json`. The checks are the
seed script's own (`scripts/seed_rooms.py`): a name the schema refuses
(more than 40 characters), a record that is missing or not `done`, or one
without stage timings, call rows, validator and Dry run verdicts and a
build time refuses the run; so does a Room with no photos or a photo
missing from the Volume.

The files then go up in one `batch_upload(force=True)`, laid out as a
seeded room is (Room, `photos/<i>.jpg`, the cards at the same keys,
`job.json`), so a second promotion overwrites the earlier files and the
hosted `ArtifactStore` lists the room while `GET /builds/<job_id>` falls
through to its record (AD-7). The originals and `cache-keys.json` are
never copied: they stay under `rooms/judge/<room_id>/` and go with the
Nov 10 purge, which leaves the Demo copy, holding the downscaled photos
only, in place. The Judge copy is never deleted or changed. The Volume is
resolved in the Environment `--env` names (default `main`), never the
CLI's active one, and needs a Modal token.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Protocol

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` and `scripts` import from any working directory

from scripts.seed_rooms import (
    DEMO_PREFIX,
    ENVIRONMENT,
    Batch,
    Seed,
    SeedRefused,
    checked,
    demo_files,
    named,
    open_volume,
    seed,
)
from src.domain.schema import JobState, Room
from src.infra.modal import JOB_FILE, JUDGE_PARTITION, ROOMS_DIR
from src.pipeline.ports import photo_key, room_key

if TYPE_CHECKING:
    from modal.volume import FileEntry

JUDGE_PREFIX = f"/{ROOMS_DIR}/{JUDGE_PARTITION}"
"""Where every hosted Build lands on the Volume, the partition the Nov 10 purge empties."""


class Volume(Protocol):
    """The three remote `modal.Volume` calls the script makes from outside a container."""

    def listdir(self, path: str, *, recursive: bool = False) -> Sequence[FileEntry]: ...

    def read_file(self, path: str) -> Iterable[bytes]: ...

    def batch_upload(self, force: bool = False) -> AbstractContextManager[Batch]: ...


def read(volume: Volume, key: str) -> bytes:
    """The bytes of the Judge artifact at `key`; `KeyError(key)` when the Volume holds none."""
    from modal.exception import NotFoundError

    try:
        return b"".join(volume.read_file(f"{JUDGE_PREFIX}/{key}"))
    except (FileNotFoundError, NotFoundError):
        raise KeyError(key) from None


def judge_room(volume: Volume, room_id: str) -> Room:
    """The Room stored under `rooms/judge/<room_id>/`."""
    try:
        return Room.model_validate_json(read(volume, room_key(room_id)))
    except (KeyError, ValueError):
        raise SeedRefused(f"{room_id}: no Judge room is stored under {JUDGE_PREFIX}/") from None


def final_job(volume: Volume, room_id: str) -> JobState:
    """The `done` job record beside the Judge room, holding everything the Build view reads."""
    key = f"{room_id}/{JOB_FILE}"
    try:
        job = JobState.model_validate_json(read(volume, key))
    except (KeyError, ValueError):
        raise SeedRefused(f"{room_id}: no done job record is stored at {JUDGE_PREFIX}/{key}") from None
    if job.room_id != room_id or job.status != "done":
        raise SeedRefused(f"{room_id}: no done job record names this Room; {JUDGE_PREFIX}/{key} is {job.status} for {job.room_id}")
    return checked(job)


def card_keys(volume: Volume, room: Room) -> list[str]:
    """The artifact keys under the Judge room's folder whose file name is one of the Room's `pz_` ids: its Clue cards (7.4)."""
    from modal.volume import FileEntryType

    puzzle_ids = {puzzle.id for puzzle in room.puzzles}
    entries = volume.listdir(f"{JUDGE_PREFIX}/{room.id}", recursive=True)
    paths = sorted(PurePosixPath(entry.path.lstrip("/")) for entry in entries if entry.type == FileEntryType.FILE)
    return [path.relative_to(JUDGE_PREFIX.lstrip("/")).as_posix() for path in paths if path.stem in puzzle_ids]


def plan(volume: Volume, room_id: str, name: str) -> Seed:
    """Read and check the Judge room; any refusal raises `SeedRefused` and nothing is written."""
    room = named(judge_room(volume, room_id), name)
    job = final_job(volume, room.id)
    if not room.photos:
        raise SeedRefused(f"{room.id}: the Room has no photos")
    artifacts: dict[str, bytes] = {}
    for index in range(len(room.photos)):
        try:
            artifacts[photo_key(room.id, index)] = read(volume, photo_key(room.id, index))
        except KeyError:
            raise SeedRefused(f"{room.id}: photo {index} is not stored under {JUDGE_PREFIX}/{room.id}/") from None
    for key in card_keys(volume, room):
        artifacts[key] = read(volume, key)
    return Seed(room=room, job=job, files=demo_files(room, job, artifacts))


def promote(volume: Volume, item: Seed) -> None:
    """Upload the Demo copy in one batch that may overwrite an earlier promotion; the Judge copy stays."""
    seed(volume, [item])


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Promote a Judge room on the keyframe-data Volume to the Demo partition.")
    parser.add_argument("--room", nargs=2, required=True, metavar=("ROOM_ID", "NAME"), help="the Judge room and the name it is promoted with")
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment (default {ENVIRONMENT})")
    args = parser.parse_args(argv)
    room_id, name = args.room
    volume = open_volume(args.env)
    try:
        item = plan(volume, room_id, name)
    except SeedRefused as refusal:
        print(f"refused, nothing written: {refusal}", file=sys.stderr)
        return 1
    promote(volume, item)
    print(
        f"promoted {item.room.id} {item.room.name!r} with {item.job.id}: {len(item.files)} files under {DEMO_PREFIX}/ in {args.env}; "
        f"the originals and cache keys stay under {JUDGE_PREFIX}/{item.room.id}/, untouched"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
