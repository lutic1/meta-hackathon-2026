#!/usr/bin/env python3
"""Hand-correct a Demo room's outlines on the hosted `keyframe-data` Volume (AD-7, AD-11, AD-12).

    uv run scripts/patch_demo_room.py --room <room_id> --patch <file> --dry-run
    uv run scripts/patch_demo_room.py --env main --room <room_id> --patch ops/patches/<room_id>.json

The patch file is a JSON object: a `reason` line saying why, and
`interactables`, a list of `{id, polygons}` entries with each polygon's
points in the pixel space of the Interactable's stored downscaled photo.
Everything is read and checked through the remote Volume calls
(`read_file`) before anything is written: the Room under
`rooms/demo/<room_id>/room.json` (an id that is not a Demo room, a Judge
room included, refuses the run) and the stored bytes of each photo the
patch touches, whose header gives the frame. An id not in the Room, a
polygon with fewer than 3 points or a point outside its photo's frame
refuses the run; so does a patched Room the validator refuses (rules 1 to
8, AD-12). Each entry replaces that Interactable's `polygons`, sets
`instances` to their number and `box` to their bounding box; the client
never reads `box` (AD-11), and nothing else in the Room changes.

`--dry-run` prints, per entry, the old and new bounds and polygon counts
and the validator verdict, and writes nothing. A real run overwrites
`room.json` alone in one `batch_upload(force=True)`, reads it back and
checks it equals what was written: `job.json` keeps the pipeline's own
receipts and Mask preview as built, and no photo, Session or Cache entry
is touched. Every refusal exits 1 with nothing written. The Volume is
resolved in the Environment `--env` names (default `main`), never the
CLI's active one, and needs a Modal token.
"""

from __future__ import annotations

import argparse
import io
import sys
from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` and `scripts` import from any working directory

from scripts.promote_room import demo_room, read
from scripts.seed_rooms import DEMO_PREFIX, ENVIRONMENT, Batch, open_volume
from src.domain.schema import Box, InteractableId, Model, Polygon, Room, RoomId
from src.domain.validator import BUILD_RULES, validate
from src.pipeline.ports import room_key
from src.pipeline.segment import frame_size


class PatchRefused(Exception):
    """A patch that cannot be applied; raised before anything is written."""


class Volume(Protocol):
    """The two remote `modal.Volume` calls the script makes from outside a container."""

    def read_file(self, path: str) -> Iterable[bytes]: ...

    def batch_upload(self, force: bool = False) -> AbstractContextManager[Batch]: ...


class OutlinePatch(Model):
    """One Interactable's hand-drawn outlines: one polygon per instance."""

    id: InteractableId
    polygons: list[Polygon]


class RoomPatch(Model):
    """A patch file: why the outlines were corrected, and the corrected Interactables."""

    reason: str
    interactables: list[OutlinePatch]


def load_patch(path: Path) -> RoomPatch:
    """The patch file at `path`; one that is missing or does not parse refuses the run."""
    try:
        return RoomPatch.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as error:
        raise PatchRefused(f"the patch file {path} does not load: {error}") from None


def frame_sizes(volume: Volume, room: Room, photos: set[int]) -> dict[int, tuple[int, int]]:
    """Width and height of each named photo, from the header of its bytes stored under the Demo partition."""
    sizes: dict[int, tuple[int, int]] = {}
    for index in sorted(photos):
        try:
            sizes[index] = frame_size(read(volume, room.photos[index].downscaled_path, DEMO_PREFIX))
        except KeyError:
            raise PatchRefused(f"{room.id}: photo {index} is not stored under {DEMO_PREFIX}/{room.id}/") from None
    return sizes


def bounding_box(polygons: list[Polygon]) -> Box:
    """`[x0, y0, x1, y1]` around every point of `polygons`."""
    xs = [x for polygon in polygons for x, _ in polygon]
    ys = [y for polygon in polygons for _, y in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def patched(room: Room, patch: RoomPatch, sizes: dict[int, tuple[int, int]]) -> Room:
    """The Room with each entry's outlines in place; an unknown id, a short polygon, a point off its frame or a validator refusal raises `PatchRefused`."""
    by_id = {ix.id: ix for ix in room.interactables}
    replaced = dict(by_id)
    for entry in patch.interactables:
        ix = by_id.get(entry.id)
        if ix is None:
            raise PatchRefused(f"{room.id}: no Interactable {entry.id} in this Room")
        if not entry.polygons or any(len(polygon) < 3 for polygon in entry.polygons):
            raise PatchRefused(f"{room.id}: {entry.id} has a polygon with fewer than 3 points")
        width, height = sizes[ix.photo]
        if any(not (0 <= x <= width and 0 <= y <= height) for polygon in entry.polygons for x, y in polygon):
            raise PatchRefused(f"{room.id}: {entry.id} has a point outside photo {ix.photo}'s {width} x {height} frame")
        replaced[ix.id] = ix.model_copy(update={"polygons": entry.polygons, "instances": len(entry.polygons), "box": bounding_box(entry.polygons)})
    result = Room.model_validate({**room.model_dump(), "interactables": [replaced[ix.id].model_dump() for ix in room.interactables]})
    reasons = [reason for reason in validate(result).reasons if reason.rule in BUILD_RULES]
    if reasons:
        listed = "; ".join(f"rule {r.rule} ({r.puzzle_id or 'room'}: {r.field})" for r in reasons)
        raise PatchRefused(f"{room.id}: the validator refuses the patched Room: {listed}")
    return result


def plan(volume: Volume, room_id: str, patch: RoomPatch) -> tuple[Room, Room]:
    """The stored Demo room and its patched copy, every check made; any refusal raises `PatchRefused` and nothing is written."""
    try:
        TypeAdapter(RoomId).validate_python(room_id)
    except ValidationError:
        raise PatchRefused(f"{room_id!r} is not a room id") from None
    room = demo_room(volume, room_id)
    if room is None:
        raise PatchRefused(f"{room_id}: no Demo room is stored under {DEMO_PREFIX}/")
    by_id = {ix.id: ix for ix in room.interactables}
    photos = {by_id[entry.id].photo for entry in patch.interactables if entry.id in by_id}
    return room, patched(room, patch, frame_sizes(volume, room, photos))


def write(volume: Volume, room: Room) -> None:
    """Overwrite `room.json` alone, then check it reads back equal; one that does not raises `PatchRefused`."""
    data = room.model_dump_json().encode()
    with volume.batch_upload(force=True) as batch:
        batch.put_file(io.BytesIO(data), f"{DEMO_PREFIX}/{room_key(room.id)}")
    try:
        back = read(volume, room_key(room.id), DEMO_PREFIX)
    except KeyError:
        back = b""
    if back != data:
        raise PatchRefused(f"{room.id}: {DEMO_PREFIX}/{room_key(room.id)} does not read back as written")


def changes(before: Room, after: Room, patch: RoomPatch) -> list[str]:
    """One line per entry: the Interactable, its old and new bounds and its old and new polygon counts."""
    old = {ix.id: ix for ix in before.interactables}
    new = {ix.id: ix for ix in after.interactables}

    def box(value: Box) -> str:
        return "[" + ", ".join(f"{v:.1f}" for v in value) + "]"

    return [
        f"{entry.id} {old[entry.id].label!r} on photo {old[entry.id].photo}: box {box(old[entry.id].box)} -> {box(new[entry.id].box)}, "
        f"polygons {len(old[entry.id].polygons or [])} -> {len(new[entry.id].polygons or [])}"
        for entry in patch.interactables
    ]


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Hand-correct a Demo room's outlines on the keyframe-data Volume.")
    parser.add_argument("--room", required=True, metavar="ROOM_ID", help="the Demo room to patch")
    parser.add_argument("--patch", required=True, type=Path, help="the patch file: a reason and the corrected Interactables")
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment (default {ENVIRONMENT})")
    parser.add_argument("--dry-run", action="store_true", help="print what would change and the validator verdict; write nothing")
    args = parser.parse_args(argv)
    try:
        patch = load_patch(args.patch)
        volume = open_volume(args.env)
        before, after = plan(volume, args.room, patch)
    except PatchRefused as refusal:
        print(f"refused, nothing written: {refusal}", file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n".join(changes(before, after, patch)))
        print("validator: rules 1 to 8 pass")
        print(f"dry run: nothing written to {DEMO_PREFIX}/{room_key(after.id)} in {args.env}")
        return 0
    try:
        write(volume, after)
    except PatchRefused as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return 1
    ids = ", ".join(entry.id for entry in patch.interactables)
    print(
        f"patched {after.id} in {args.env}: re-outlined {len(patch.interactables)} Interactables ({ids}); "
        f"{DEMO_PREFIX}/{room_key(after.id)} read back equal; job.json and the photos untouched"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
