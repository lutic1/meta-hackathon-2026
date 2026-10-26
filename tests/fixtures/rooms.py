"""Synthetic fixture rooms: scenes drawn with Pillow, never a real room photo, and two valid Rooms.

`write_fixtures(out_dir)` writes six 1280 px JPEG scenes (one portrait) into
`out_dir`, which callers keep outside `rooms/`, `photos/`, `captures/` and
`uploads/` (pytest's tmp path), and returns the four-lock room and the
code-and-find room built over them. Run as `python -m tests.fixtures.rooms <out_dir>`.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.domain.schema import Box, Room

LONG_EDGE = 1280
SCENES: tuple[tuple[int, int, str], ...] = (
    (1280, 960, "#d9c6a5"),
    (1280, 960, "#b7a98a"),
    (960, 1280, "#cfd6dc"),  # portrait
    (1280, 960, "#a8b59a"),
    (1280, 960, "#c9b7b0"),
    (1280, 960, "#bfc8a0"),
)


def _id(prefix: str, n: int) -> str:
    return f"{prefix}_{n:026d}"


IX = {name: _id("ix", n) for n, name in enumerate(("key", "chest", "clock", "candle", "lantern", "hourglass", "door", "rug"), 1)}
PZ = {name: _id("pz", n) for n, name in enumerate(("find_key", "clock_code", "shelf_order", "key_on_chest", "door_code", "find_lantern"), 1)}
ROOM_IDS = {"four_lock": _id("room", 1), "code_and_find": _id("room", 2)}
CREATED = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)

# label, photo index, box in frame pixels, attributes as the vision call would report them
INTERACTABLES: dict[str, tuple[str, int, Box, list[str]]] = {
    "key": ("brass key", 0, (540, 300, 620, 430), ["brass", "small", "hangs on a hook"]),
    "chest": ("wooden chest", 1, (380, 480, 900, 820), ["wooden", "iron bands", "closed lid", "sits on the floor"]),
    "clock": ("wall clock", 2, (280, 200, 680, 600), ["round white face", "stopped at a quarter past four", "brass hands"]),
    "candle": ("wax candle", 3, (160, 360, 300, 640), ["half burnt", "white wax", "left end of the shelf"]),
    "lantern": ("iron lantern", 3, (540, 300, 740, 640), ["glass sides", "middle of the shelf", "soot on the glass"]),
    "hourglass": ("sand hourglass", 3, (980, 380, 1120, 640), ["sand run out", "right end of the shelf", "wooden frame"]),
    "door": ("painted door", 4, (420, 80, 860, 900), ["painted green", "four brass digits above the frame", "heavy"]),
    "rug": ("woven rug", 5, (200, 600, 1080, 900), ["woven", "faded red", "lies by the door"]),
}
FILLS = {"key": "#c9a227", "chest": "#6b4423", "clock": "#f4f1e8", "candle": "#f7f3e3",
         "lantern": "#3b3b3b", "hourglass": "#8c6d3f", "door": "#4f7a4a", "rug": "#a0413a"}


def _polygon(box: Box) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = box
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _draw_scene(index: int) -> Image.Image:
    width, height, background = SCENES[index]
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, height * 0.72, width, height), fill="#7d6b57")  # floor
    for name, (label, photo, box, _) in INTERACTABLES.items():
        if photo != index:
            continue
        draw.rectangle(box, fill=FILLS[name], outline="#222222", width=4)
        draw.text((box[0] + 8, box[1] + 8), label, fill="#111111")
    return image


def _puzzle(key: str, lock_type: str, requires: list[str], solution: dict[str, Any], evidence: tuple[str, str],
            clue: str, lore: str, rungs: tuple[str, str, str], *, is_exit: bool = False) -> dict[str, Any]:
    return {
        "id": PZ[key], "lock_type": lock_type, "requires": [PZ[r] for r in requires],
        "solution": {"lock_type": lock_type, **solution},
        "evidence": {"interactable": IX[evidence[0]], "visible_attribute": evidence[1]},
        "clue": clue, "lore": lore,
        "rungs": {"nudge": rungs[0], "direction": rungs[1], "near_answer": rungs[2]},
        "is_exit": is_exit,
    }


FIND_KEY = _puzzle(
    "find_key", "find", [], {"target": IX["key"]}, ("key", "hangs on a hook"),
    "Something small waits where coats would hang.",
    "Every guest of this house left a little of themselves on the hooks by the door. One of them left more than a coat.",
    ("Look by the hooks.",
     "Something small and metal hangs where a coat would.",
     "Take the small metal thing hanging from the hook by the door."),
)
CLOCK_CODE = _puzzle(
    "clock_code", "code", [], {"code": "415"}, ("clock", "stopped at a quarter past four"),
    "The clock stopped at a telling hour.",
    "The house keeps its own time, and it stopped keeping it the night the last tenant left.",
    ("Check the time.",
     "The clock on the wall stopped long ago; read what its hands still say.",
     "Read the hour and the minutes the stopped hands show and type them in that order."),
)
SHELF_ORDER = _puzzle(
    "shelf_order", "order", ["clock_code"],
    {"interactables": [IX["candle"], IX["lantern"], IX["hourglass"]]}, ("candle", "half burnt"),
    "Three keepers of time stand on the shelf; wake them as the clock would.",
    "Wax, oil and grains each measure an evening in their own way. The tenant lit them in turn.",
    ("Study the shelf.",
     "The three things on the shelf each measure time in their own way.",
     "Begin with the candle, then what burns oil, then what runs out of grains."),
)
KEY_ON_CHEST = _puzzle(
    "key_on_chest", "use_on", ["find_key"], {"item": IX["key"], "target": IX["chest"]}, ("chest", "closed lid"),
    "What hangs by the door opens what sits on the floor.",
    "The chest has not been opened since the tenant packed it. Its lock is small, like the thing that fits it.",
    ("You carry something now.",
     "Something you picked up fits a lock somewhere in this room.",
     "Use the small thing from the hook on the wooden chest by the far wall."),
)
DOOR_CODE = _puzzle(
    "door_code", "code", ["shelf_order", "key_on_chest"], {"code": "7342"}, ("door", "four brass digits above the frame"),
    "The way out wears its own number.",
    "Whoever painted the door left the way out in plain sight, for anyone patient enough to read it.",
    ("The door is the way out.",
     "The painted door carries its own number above the frame.",
     "Type the digits painted above the door frame into the lock, left to right."),
    is_exit=True,
)
FIND_LANTERN = _puzzle(
    "find_lantern", "find", ["find_key"], {"target": IX["lantern"]}, ("lantern", "glass sides"),
    "Once the key is yours, find what would light the shelf.",
    "The shelf was lit every evening by one thing with glass sides and a soot-black top.",
    ("Look at the shelf.",
     "Something on the shelf would light the way for you.",
     "Pick up the lamp with the glass sides from the middle of the shelf."),
)
CUT6_DOOR_CODE = {**DOOR_CODE, "requires": [PZ["clock_code"], PZ["find_lantern"]]}


def _provenance() -> dict[str, Any]:
    stages = ("ingest", "architect", "segment", "author", "validate", "dryrun", "scene")
    roles = ("architect", "riddler", "dryrun")
    return {
        "model_ids": dict.fromkeys(roles, "mock"),
        "prompt_hashes": dict.fromkeys(roles, "0" * 64),
        "stage_timings_ms": dict.fromkeys(stages, 0),
        "regeneration_count": 0,
        "spend_per_stage_usd": dict.fromkeys(stages, 0.0),
    }


def _room(room_id: str, photos: list[dict[str, Any]], puzzles: list[dict[str, Any]]) -> Room:
    interactables = [
        {"id": IX[name], "label": label, "photo": photo, "box": box, "polygons": [_polygon(box)],
         "instances": 1, "attributes": attributes}
        for name, (label, photo, box, attributes) in INTERACTABLES.items()
    ]
    return Room.model_validate({
        "id": room_id, "created": CREATED, "photos": photos,
        "interactables": interactables, "puzzles": puzzles, "provenance": _provenance(),
    })


def write_scenes(out_dir: Path) -> list[dict[str, Any]]:
    """Write the six synthetic JPEG scenes and return their Photo records."""
    out_dir.mkdir(parents=True, exist_ok=True)
    photos = []
    for index in range(len(SCENES)):
        path = out_dir / f"scene-{index}.jpg"
        _draw_scene(index).save(path, "JPEG", quality=85)
        data = path.read_bytes()
        photos.append({"hash": hashlib.sha256(data).hexdigest(), "size": len(data),
                       "downscaled_path": str(path), "original_path": str(path)})
    return photos


def write_fixtures(out_dir: Path) -> tuple[Room, Room]:
    """The four-lock room and the code-and-find room (cut 6, video v0) over scenes written to `out_dir`."""
    photos = write_scenes(out_dir)
    four_lock = _room(ROOM_IDS["four_lock"], photos, [FIND_KEY, CLOCK_CODE, SHELF_ORDER, KEY_ON_CHEST, DOOR_CODE])
    code_and_find = _room(ROOM_IDS["code_and_find"], photos, [FIND_KEY, CLOCK_CODE, FIND_LANTERN, CUT6_DOOR_CODE])
    return four_lock, code_and_find


if __name__ == "__main__":
    for room in write_fixtures(Path(sys.argv[1])):
        print(room.id, len(room.photos), "photos", len(room.puzzles), "puzzles")
