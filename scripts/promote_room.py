#!/usr/bin/env python3
"""Promote a Judge room on the hosted `keyframe-data` Volume to the Demo partition, with its name and final job record (AD-7, AD-9).

    uv run scripts/promote_room.py --room <room_id> "<name>"
    uv run scripts/promote_room.py --env main --room <room_id> "<name>"

The Demo room is a Judge room built on the judge URL, moved on the Volume
from `rooms/judge/<room_id>/` to `rooms/demo/<room_id>/` with `Room.name`
set; nothing comes from this machine, and a Demo room is never a Judge
room. Everything is read and checked through the remote Volume calls
(`read_file`, `listdir`) before anything is written: the stored Room,
its downscaled photos, the Clue cards 7.4 stored for it (the files under
its folder keyed by one of its `pz_` ids, when there are any) and the `done` job record at `job.json`. The checks are the
seed script's own (`scripts/seed_rooms.py`): a name the schema refuses
(more than 40 characters), a record that is missing or not `done`, or one
without stage timings, call rows, validator and Dry run verdicts and a
build time refuses the run; so does a Room with no photos, a photo
missing from the Volume, or a Demo copy referencing any file the copy
would not hold (the seed script's manifest check: each photo's
`original_path` is rewritten to its downscaled key, and every remaining
reference must be a file about to go up).

The files then go up in one `batch_upload(force=True)`, laid out as a
seeded room is (Room, `photos/<i>.jpg`, the cards at the same keys,
`job.json`), so the hosted `ArtifactStore` lists the room while
`GET /builds/<job_id>` falls through to its record (AD-7); a Demo copy an
earlier promotion left that already holds exactly these files is not
uploaded again, and one that differs is overwritten. The originals and
`cache-keys.json` are never copied. Once the Demo copy reads back (its
Room parses and every file it references is there), the Judge copy is
removed whole with one `remove_file`, which a remote call persists with no
commit; a Demo copy that does not read back keeps the Judge copy. No
deletion record is written, and no Dict is opened, so the quota slot the
Build claimed stays claimed and no Session or Cache entry is touched. Run
again once the Judge copy is gone, it reports the room already promoted and
exits 0. The Volume is resolved in the Environment `--env` names (default
`main`), never the CLI's active one, and needs a Modal token.
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
    demo_copy,
    demo_files,
    named,
    open_volume,
    referenced,
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
    """The four remote `modal.Volume` calls the script makes from outside a container."""

    def listdir(self, path: str, *, recursive: bool = False) -> Sequence[FileEntry]: ...

    def read_file(self, path: str) -> Iterable[bytes]: ...

    def remove_file(self, path: str, recursive: bool = False) -> None: ...

    def batch_upload(self, force: bool = False) -> AbstractContextManager[Batch]: ...


def read(volume: Volume, key: str, prefix: str = JUDGE_PREFIX) -> bytes:
    """The bytes of the artifact at `key` under `prefix` (the Judge partition by default); `KeyError(key)` when the Volume holds none."""
    from modal.exception import NotFoundError

    try:
        return b"".join(volume.read_file(f"{prefix}/{key}"))
    except (FileNotFoundError, NotFoundError):
        raise KeyError(key) from None


def judge_copy_left(volume: Volume, room_id: str) -> bool:
    """Whether anything is still under `rooms/judge/<room_id>/`."""
    from modal.exception import NotFoundError

    try:
        return bool(volume.listdir(f"{JUDGE_PREFIX}/{room_id}"))
    except (FileNotFoundError, NotFoundError):
        return False


def demo_room(volume: Volume, room_id: str) -> Room | None:
    """The Room the Demo partition stores under `room_id`; `None` when there is none or it does not parse."""
    try:
        return Room.model_validate_json(read(volume, room_key(room_id), DEMO_PREFIX))
    except (KeyError, ValueError):
        return None


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
    room = demo_copy(named(judge_room(volume, room_id), name))
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


def holds(volume: Volume, item: Seed) -> bool:
    """Whether the Volume already holds every file of the Demo copy, byte for byte."""
    try:
        return all(read(volume, path.removeprefix(f"{DEMO_PREFIX}/"), DEMO_PREFIX) == data for path, data in item.files.items())
    except KeyError:
        return False


def promote(volume: Volume, item: Seed) -> bool:
    """Upload the Demo copy unless the Volume holds it already, check it reads back, then remove the Judge copy; True when it was uploaded.

    A Demo copy that does not read back raises `SeedRefused` with the Judge copy kept.
    """
    uploaded = not holds(volume, item)
    if uploaded:
        seed(volume, [item])
    room = demo_room(volume, item.room.id)
    missing = ["room.json"] if room is None else [key for key in referenced(room) if not _stored(volume, key)]
    if missing:
        raise SeedRefused(f"{item.room.id}: the Demo copy does not read back ({', '.join(missing)}); the Judge copy is kept")
    volume.remove_file(f"{JUDGE_PREFIX}/{item.room.id}", recursive=True)
    return uploaded


def _stored(volume: Volume, key: str) -> bool:
    """Whether the Demo partition holds a file at `key`."""
    try:
        read(volume, key, DEMO_PREFIX)
    except KeyError:
        return False
    return True


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Promote a Judge room on the keyframe-data Volume to the Demo partition.")
    parser.add_argument("--room", nargs=2, required=True, metavar=("ROOM_ID", "NAME"), help="the Judge room and the name it is promoted with")
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment (default {ENVIRONMENT})")
    args = parser.parse_args(argv)
    room_id, name = args.room
    volume = open_volume(args.env)
    if not judge_copy_left(volume, room_id) and demo_room(volume, room_id) is not None:
        print(f"already promoted: {room_id} is under {DEMO_PREFIX}/ in {args.env} and no Judge copy is left under {JUDGE_PREFIX}/")
        return 0
    try:
        item = plan(volume, room_id, name)
    except SeedRefused as refusal:
        print(f"refused, nothing written: {refusal}", file=sys.stderr)
        return 1
    try:
        uploaded = promote(volume, item)
    except SeedRefused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    copied = f"{len(item.files)} files under {DEMO_PREFIX}/" if uploaded else f"the Demo copy under {DEMO_PREFIX}/ already matched"
    print(
        f"promoted {item.room.id} {item.room.name!r} with {item.job.id}: {copied} in {args.env}; "
        f"removed the Judge copy under {JUDGE_PREFIX}/{item.room.id}/"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
