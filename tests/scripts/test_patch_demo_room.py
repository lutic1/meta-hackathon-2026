"""`scripts/patch_demo_room.py` hand-corrects a Demo room's outlines on the Volume: room.json only, checked against each photo's frame and the validator, read back after the write.

No test reaches Modal: the Volume is the promote tests' stand-in over a
temporary mount, whose batch lands only when its block exits.
"""

import importlib.util
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, get_args

import pytest

from src.domain.schema import Room, Story
from src.pipeline.ports import room_key
from src.pipeline.story import template_story
from tests.scripts.test_promote_room import JudgeVolume
from tests.scripts.test_seed_rooms import demo_copy, full_job, snapshot

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/patch_demo_room.py"
DEMO_ROOM = "room_01M61TZ74F0FP3X9HHTMXGTPB9"
VENT = "ix_01M61V1ACGZFANRYAX39W29673"
PILLOWS = "ix_01M61V1ACGTGK2QA16BZP494AC"
CLOCK = "ix_01M61V1ACGDJP2ARZ8E0ZGYEN5"
TRAY = "ix_01M61V1ACGP7FT9JZY9Y22P8JR"
DOOR = "ix_01M61V1ACGVQQTEZ4D9S1PYPJM"


def _load():
    spec = importlib.util.spec_from_file_location("patch_demo_room_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


patcher = _load()

KEY = "ix_00000000000000000000000002"  # the wooden chest, alone on photo 1 (1280 x 960)
TWO = [[[400, 500], [600, 500], [600, 700]], [[700, 600], [880, 600], [880, 800], [700, 800]]]


class UploadLog(JudgeVolume):
    """A Volume that records every path its batches put."""

    def __init__(self, mount: Path) -> None:
        super().__init__(mount)
        self.removed: list[str] = []
        self.uploaded: list[str] = []

    @contextmanager
    def batch_upload(self, force: bool = False) -> Iterator[Any]:
        with super().batch_upload(force) as batch:
            put = batch.put_file
            batch.put_file = lambda local, remote: (self.uploaded.append(remote), put(local, remote))[1]
            yield batch


@pytest.fixture
def mount(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def volume(mount: Path) -> JudgeVolume:
    volume = JudgeVolume(mount)
    volume.removed = []
    return volume


@pytest.fixture
def demo(mount: Path, code_and_find_room: Room) -> Room:
    """A promoted Demo room: the named Room, its photos and the pipeline's `job.json`."""
    room = demo_copy(code_and_find_room)
    folder = mount / "rooms/demo" / room.id
    (folder / "photos").mkdir(parents=True)
    (folder / "room.json").write_bytes(room.model_dump_json().encode())
    for index, photo in enumerate(code_and_find_room.photos):
        (folder / f"photos/{index}.jpg").write_bytes(Path(photo.downscaled_path).read_bytes())
    (folder / "job.json").write_bytes(full_job(room).model_dump_json().encode())
    return room


def write_patch(tmp_path: Path, *entries: tuple[str, Any]) -> Path:
    path = tmp_path / "patch.json"
    body = {"reason": "Hand-corrected in a test.", "interactables": [{"id": ix_id, "polygons": polygons} for ix_id, polygons in entries]}
    path.write_text(json.dumps(body))
    return path


def write_move(tmp_path: Path, ix_id: str, photo: int, polygons: Any) -> Path:
    path = tmp_path / "move.json"
    path.write_text(json.dumps({"reason": "Moved in a test.", "interactables": [{"id": ix_id, "photo": photo, "polygons": polygons}]}))
    return path


def stored(mount: Path, room: Room) -> Room:
    return Room.model_validate_json((mount / "rooms/demo" / room_key(room.id)).read_bytes())


def run(monkeypatch, volume: JudgeVolume, room_id: str, patch: Path, *flags: str) -> int:
    monkeypatch.setattr(patcher, "open_volume", lambda environment: volume)
    return patcher.main(["--room", room_id, "--patch", str(patch), *flags])


# --- The write ------------------------------------------------------------------


def test_a_real_run_rewrites_room_json_only_with_the_polygons_their_count_and_their_bounds_and_reads_it_back(monkeypatch, tmp_path, volume, mount, demo, capsys):
    before = snapshot(mount / "rooms/demo" / demo.id)
    assert run(monkeypatch, volume, demo.id, write_patch(tmp_path, (KEY, TWO))) == 0
    after = snapshot(mount / "rooms/demo" / demo.id)
    assert {path for path in after if after[path] != before[path]} == {"room.json"} and after.keys() == before.keys()
    assert volume.forces == [True] and volume.commits == 1 and volume.removed == []
    room = stored(mount, demo)
    chest = next(ix for ix in room.interactables if ix.id == KEY)
    assert chest.polygons == [[tuple(map(float, point)) for point in polygon] for polygon in TWO]
    assert chest.instances == 2 and chest.box == (400, 500, 880, 800)
    assert room == demo.model_copy(update={"interactables": [chest if ix.id == KEY else ix for ix in demo.interactables]})
    out = capsys.readouterr().out
    assert f"patched {demo.id} in main" in out and "read back equal" in out


def test_job_json_and_the_photos_are_never_written(monkeypatch, tmp_path, mount, demo):
    volume = UploadLog(mount)
    job_before = (mount / "rooms/demo" / demo.id / "job.json").read_bytes()
    assert run(monkeypatch, volume, demo.id, write_patch(tmp_path, (KEY, TWO))) == 0
    assert volume.uploaded == [f"/rooms/demo/{demo.id}/room.json"]
    assert (mount / "rooms/demo" / demo.id / "job.json").read_bytes() == job_before


def test_a_write_that_does_not_read_back_equal_exits_1(monkeypatch, tmp_path, volume, mount, demo, capsys):
    real_read = volume.read_file
    writes = iter([False, True])  # the room is read once before the write, then once to check it

    def stale_read(path: str):
        if path.endswith("/room.json") and next(writes, False):
            yield demo.model_dump_json().encode()
            return
        yield from real_read(path)

    monkeypatch.setattr(volume, "read_file", stale_read)
    assert run(monkeypatch, volume, demo.id, write_patch(tmp_path, (KEY, TWO))) == 1
    assert "read back" in capsys.readouterr().err


# --- A move ------------------------------------------------------------------------

PORTRAIT = [[[100, 900], [500, 900], [500, 1200], [100, 1200]]]  # inside photo 2's 960 x 1280 frame, not photo 1's 1280 x 960


def test_an_entry_with_a_photo_moves_the_interactable_there_with_its_polygons_count_and_bounds(monkeypatch, tmp_path, volume, mount, demo):
    assert run(monkeypatch, volume, demo.id, write_move(tmp_path, KEY, 2, PORTRAIT)) == 0
    chest = next(ix for ix in stored(mount, demo).interactables if ix.id == KEY)
    assert chest.photo == 2 and chest.instances == 1 and chest.box == (100, 900, 500, 1200)
    assert chest.polygons == [[tuple(map(float, point)) for point in polygon] for polygon in PORTRAIT]
    old = next(ix for ix in demo.interactables if ix.id == KEY)
    assert chest.model_dump(exclude={"photo", "box", "polygons", "instances"}) == old.model_dump(exclude={"photo", "box", "polygons", "instances"})


def test_the_dry_run_prints_the_move(monkeypatch, tmp_path, volume, mount, demo, capsys):
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, demo.id, write_move(tmp_path, KEY, 2, PORTRAIT), "--dry-run") == 0
    assert f"{KEY} 'wooden chest' on photo 1 -> 2: box [380.0, 480.0, 900.0, 820.0] -> [100.0, 900.0, 500.0, 1200.0]" in capsys.readouterr().out
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


@pytest.mark.parametrize(
    ("photo", "polygons", "message"),
    [
        (6, PORTRAIT, "no photo 6 in this Room"),
        (2, [[[100, 900], [1000, 900], [500, 1200]]], "outside photo 2's 960 x 1280 frame"),
    ],
    ids=["photo the room lacks", "point off the new photo"],
)
@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_a_move_to_a_photo_the_room_lacks_or_off_its_frame_is_refused(monkeypatch, tmp_path, volume, mount, demo, capsys, photo, polygons, message, flags):
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, demo.id, write_move(tmp_path, KEY, photo, polygons), *flags) == 1
    err = capsys.readouterr().err
    assert "refused, nothing written" in err and message in err
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


# --- The dry run ------------------------------------------------------------------


def test_the_dry_run_prints_the_old_and_new_bounds_and_counts_and_the_verdict_and_writes_nothing(monkeypatch, tmp_path, volume, mount, demo, capsys):
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, demo.id, write_patch(tmp_path, (KEY, TWO)), "--dry-run") == 0
    out = capsys.readouterr().out
    assert f"{KEY} 'wooden chest' on photo 1: box [380.0, 480.0, 900.0, 820.0] -> [400.0, 500.0, 880.0, 800.0], polygons 1 -> 2" in out
    assert "validator: rules 1 to 8 pass" in out and "dry run: nothing written" in out
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


# --- Refusals: exit 1, nothing written --------------------------------------------


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (("ix_01JBDEM0R00M00000000000000", TWO), "no Interactable ix_01JBDEM0R00M00000000000000"),
        ((KEY, [[[400, 500], [600, 500]]]), "fewer than 3 points"),
        ((KEY, [[[400, 500], [600, 500], [1281, 700]]]), "outside photo 1's 1280 x 960 frame"),
        ((KEY, [[[400, 500], [600, -1], [600, 700]]]), "outside photo 1's 1280 x 960 frame"),
    ],
)
@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_an_unknown_id_a_short_polygon_or_a_point_outside_the_frame_is_refused(monkeypatch, tmp_path, volume, mount, demo, capsys, entry, message, flags):
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, demo.id, write_patch(tmp_path, entry), *flags) == 1
    err = capsys.readouterr().err
    assert "refused, nothing written" in err and message in err
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


def test_a_patched_room_the_validator_refuses_is_refused(monkeypatch, tmp_path, volume, mount, demo, capsys):
    broken = demo.model_copy(update={"puzzles": [p.model_copy(update={"is_exit": True}) for p in demo.puzzles]})
    (mount / "rooms/demo" / room_key(demo.id)).write_bytes(broken.model_dump_json().encode())
    before = snapshot(mount / "rooms/demo")  # every Puzzle an exit: rule 7 refuses, whatever the outlines
    assert run(monkeypatch, volume, demo.id, write_patch(tmp_path, (KEY, TWO))) == 1
    err = capsys.readouterr().err
    assert "refused, nothing written" in err and "the validator refuses the patched Room" in err and "rule 7" in err
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


@pytest.mark.parametrize("room_id", ["room_01JBDEM0R00M00000000000000", "../judge/x", "not-a-room"])
def test_an_id_that_is_not_a_demo_room_is_refused(monkeypatch, tmp_path, volume, mount, demo, capsys, room_id):
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, room_id, write_patch(tmp_path, (KEY, TWO))) == 1
    assert "refused, nothing written" in capsys.readouterr().err
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


def test_a_judge_room_is_not_a_demo_room(monkeypatch, tmp_path, volume, mount, code_and_find_room, capsys):
    folder = mount / "rooms/judge" / code_and_find_room.id
    folder.mkdir(parents=True)
    (folder / "room.json").write_bytes(code_and_find_room.model_dump_json().encode())
    assert run(monkeypatch, volume, code_and_find_room.id, write_patch(tmp_path, (KEY, TWO))) == 1
    assert "no Demo room" in capsys.readouterr().err
    assert volume.forces == [] and (folder / "room.json").read_bytes() == code_and_find_room.model_dump_json().encode()


def test_main_resolves_the_volume_in_the_named_environment(monkeypatch, tmp_path, volume, demo):
    environments: list[str] = []

    def open_volume(environment: str) -> JudgeVolume:
        environments.append(environment)
        return volume

    monkeypatch.setattr(patcher, "open_volume", open_volume)
    assert patcher.main(["--env", "dev", "--room", demo.id, "--patch", str(write_patch(tmp_path, (KEY, TWO))), "--dry-run"]) == 0
    assert environments == ["dev"]


# --- The committed patch for the Demo room ------------------------------------------


def test_the_committed_patch_reoutlines_the_vent_and_both_pillow_pairs_in_the_960_by_1280_frame():
    patch = patcher.load_patch(REPO / "ops/patches" / f"{DEMO_ROOM}.json")
    assert patch.reason.startswith("Hand-corrected 29 Oct 2026:") and "job.json keeps the pipeline's original output" in patch.reason
    entries = {entry.id: entry.polygons for entry in patch.interactables}
    assert list(entries) == [VENT, PILLOWS, CLOCK, TRAY, DOOR]
    assert entries[VENT] == [[(200, 1084), (253, 1071), (233, 1176), (168, 1190)]]
    corner, left = entries[PILLOWS]  # the corner-bend pair the riddle points at first: the Evidence card crops it
    assert corner[0] == (648, 725) and left[0] == (299, 669)
    for polygons in entries.values():
        assert all(len(polygon) >= 3 and all(0 <= x <= 960 and 0 <= y <= 1280 for x, y in polygon) for polygon in polygons)


def test_the_committed_patch_seeds_the_front_hall_and_the_lounge_with_their_left_to_right_order():
    """Story mode (SPEC section 7): front hall [0, 1], lounge [3, 4, 5, 2, 6, 7]; the left pillow pair hand-traced."""
    patch = patcher.load_patch(REPO / "ops/patches" / f"{DEMO_ROOM}.json")
    assert [(entry.photo, entry.area, entry.pan) for entry in patch.photos] == [
        (0, "front hall", 0), (1, "front hall", 1), (2, "lounge", 3), (3, "lounge", 0),
        (4, "lounge", 1), (5, "lounge", 2), (6, "lounge", 4), (7, "lounge", 5),
    ]
    _, left = dict((entry.id, entry.polygons) for entry in patch.interactables)[PILLOWS]
    assert left == [(299, 669), (335, 656), (352, 666), (380, 660), (391, 670), (408, 700), (365, 710), (347, 706),
                    (320, 717), (309, 705)]


def test_the_committed_patch_moves_the_clock_and_the_tray_to_photo_2_and_the_door_to_photo_0():
    """Where players look for them: the clock and the tray show in the riddle 1 view, the door head-on in the entryway."""
    patch = patcher.load_patch(REPO / "ops/patches" / f"{DEMO_ROOM}.json")
    assert "moved" in patch.reason
    moves = {entry.id: entry.photo for entry in patch.interactables}
    assert moves == {VENT: None, PILLOWS: None, CLOCK: 2, TRAY: 2, DOOR: 0}
    entries = {entry.id: entry.polygons for entry in patch.interactables}
    assert entries[DOOR] == [[(333, 479), (682, 479), (682, 899), (343, 948)]]
    assert entries[CLOCK][0][0] == (567, 493) and entries[TRAY][0][0] == (420, 800)


def write_areas(tmp_path: Path, photos: list[dict[str, Any]]) -> Path:
    path = tmp_path / "areas.json"
    path.write_text(json.dumps({"reason": "Areas seeded in a test.", "interactables": [], "photos": photos}))
    return path


def test_a_patch_naming_every_photo_sets_each_photos_area_and_pan(monkeypatch, tmp_path, volume, mount, demo):
    photos = [{"photo": i, "area": "hall" if i < 2 else "study", "pan": i % 2} for i in range(len(demo.photos))]
    assert run(monkeypatch, volume, demo.id, write_areas(tmp_path, photos)) == 0
    room = stored(mount, demo)
    assert [(photo.area, photo.pan) for photo in room.photos] == [(entry["area"], entry["pan"]) for entry in photos]
    assert room.interactables == demo.interactables and room.puzzles == demo.puzzles


@pytest.mark.parametrize("named", [[0], [0, 1, 2, 3, 4, 5, 99], [0, 0, 1, 2, 3, 4, 5]], ids=["missing", "unknown", "twice"])
def test_a_patch_that_does_not_name_every_photo_once_is_refused(monkeypatch, tmp_path, volume, mount, demo, capsys, named):
    assert len(demo.photos) == 6
    photos = [{"photo": index, "area": "hall", "pan": 0} for index in named]
    assert run(monkeypatch, volume, demo.id, write_areas(tmp_path, photos)) == 1
    assert "names every photo once" in capsys.readouterr().err and stored(mount, demo) == demo


def test_each_photos_frame_is_read_from_its_stored_bytes(volume, demo):
    assert patcher.frame_sizes(volume, demo, {1, 2}) == {1: (1280, 960), 2: (960, 1280)}


# --- A story line ------------------------------------------------------------------

CHEST_LINE = "Stuck? I keep two hints for the whole house. Choose your moment."


@pytest.fixture
def storied(mount: Path, demo: Room) -> Room:
    """The Demo room with its stored story, the Guide's chest line the one the live replay heard."""
    story = template_story(demo).model_copy(update={"guide_chest": "Stuck, I keep two hints for the whole house, so choose your moment."})
    room = demo.model_copy(update={"story": story})
    (mount / "rooms/demo" / room_key(room.id)).write_bytes(room.model_dump_json().encode())
    return room


def write_story(tmp_path: Path, story: dict[str, Any], interactables: list[dict[str, Any]] | None = None) -> Path:
    path = tmp_path / "story.json"
    path.write_text(json.dumps({"reason": "Story line set in a test.", "interactables": interactables or [], "story": story}))
    return path


def test_the_story_slots_a_patch_may_set_are_the_storys_single_lines():
    assert set(get_args(patcher.StorySlot.__value__)) == set(Story.model_fields) - {"riddles"}


def test_a_story_line_replaces_its_slot_alone_and_the_rest_of_the_story_survives(monkeypatch, tmp_path, volume, mount, storied, capsys):
    assert run(monkeypatch, volume, storied.id, write_story(tmp_path, {"guide_chest": CHEST_LINE})) == 0
    room = stored(mount, storied)
    assert room.story == storied.story.model_copy(update={"guide_chest": CHEST_LINE})
    assert room == storied.model_copy(update={"story": room.story})
    assert "guide_chest" in capsys.readouterr().out


def test_the_dry_run_prints_each_story_slots_old_and_new_line_and_writes_nothing(monkeypatch, tmp_path, volume, mount, storied, capsys):
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, storied.id, write_story(tmp_path, {"guide_chest": CHEST_LINE}), "--dry-run") == 0
    out = capsys.readouterr().out
    assert f"story guide_chest: {storied.story.guide_chest!r} -> {CHEST_LINE!r}" in out
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


@pytest.mark.parametrize(
    ("slot", "line", "reason"),
    [
        ("guide_chest", "Stuck? I keep hints for the whole house. Choose your moment.", "does not say there are two hints"),
        ("riddler_entrance", "To escape, you must answer my riddles, one at a time.", "does not say there are four riddles"),
        ("guide_chest", "Stuck? Two hints for the whole house. Choose well!", "exclamation mark"),
        ("trickster_closing", "Fine. The lantern stays. Out you go.", "gives part of an answer away"),
        ("trickster_closing", "Fine. Out you go, and the clock code was 415.", "gives part of an answer away"),
        ("riddler_closing", "Clever mind. Let the answers linger a while.", "filler"),
        ("riddler_closing", "Clever mind. Even the AI could not stop you.", "AI, models or the API"),
        ("architect_welcome_visitor", "Welcome. Thank you for visiting this house.", "without thanking them"),
        ("guide_closing_hints", "x" * 161, "longer than 160 characters"),
        ("guide_closing_no_hints", "   ", "the line is empty"),
    ],
    ids=["hint count", "riddle count", "exclamation", "label", "code", "filler", "off story", "visitor thanks", "long", "empty"],
)
@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_a_story_line_the_storys_line_rules_refuse_is_refused_with_its_slot_and_reason(monkeypatch, tmp_path, volume, mount, storied, capsys, slot, line, reason, flags):
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, storied.id, write_story(tmp_path, {slot: line}), *flags) == 1
    err = capsys.readouterr().err
    assert "refused, nothing written" in err and f"story {slot}: " in err and reason in err
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


def test_the_trickster_trap_keeps_its_exclamation_mark(monkeypatch, tmp_path, volume, mount, storied):
    assert run(monkeypatch, volume, storied.id, write_story(tmp_path, {"trickster_trap": "Trapped! The way out is locked."})) == 0
    assert stored(mount, storied).story.trickster_trap == "Trapped! The way out is locked."


def test_a_word_of_the_rooms_name_is_shown_and_no_leak(monkeypatch, tmp_path, volume, mount, storied):
    named = storied.model_copy(update={"name": "The lantern room"})
    (mount / "rooms/demo" / room_key(named.id)).write_bytes(named.model_dump_json().encode())
    line = "Welcome to the lantern room. I built it from someone's photos."
    assert run(monkeypatch, volume, named.id, write_story(tmp_path, {"architect_welcome_visitor": line})) == 0
    assert stored(mount, named).story.architect_welcome_visitor == line


def test_a_story_line_on_a_room_with_no_story_is_refused(monkeypatch, tmp_path, volume, mount, demo, capsys):
    assert demo.story is None
    before = snapshot(mount / "rooms/demo")
    assert run(monkeypatch, volume, demo.id, write_story(tmp_path, {"guide_chest": CHEST_LINE})) == 1
    err = capsys.readouterr().err
    assert "refused, nothing written" in err and "no story" in err
    assert volume.forces == [] and snapshot(mount / "rooms/demo") == before


@pytest.mark.parametrize("slot", ["riddles", "guide_hint", "riddle 1, opening"])
def test_a_slot_that_is_not_a_single_story_line_does_not_load(monkeypatch, tmp_path, volume, mount, storied, capsys, slot):
    assert run(monkeypatch, volume, storied.id, write_story(tmp_path, {slot: CHEST_LINE})) == 1
    assert "does not load" in capsys.readouterr().err and stored(mount, storied) == storied


def test_reapplying_a_patch_the_room_already_has_changes_nothing_and_prints_no_change(monkeypatch, tmp_path, volume, mount, storied, capsys):
    photos = [{"photo": i, "area": "hall" if i < 2 else "study", "pan": i % 2} for i in range(len(storied.photos))]
    path = tmp_path / "full.json"
    path.write_text(json.dumps({
        "reason": "Everything at once in a test.",
        "interactables": [{"id": KEY, "photo": 2, "polygons": PORTRAIT}],
        "photos": photos,
        "story": {"guide_chest": CHEST_LINE},
    }))
    assert run(monkeypatch, volume, storied.id, path) == 0
    once = (mount / "rooms/demo" / room_key(storied.id)).read_bytes()
    capsys.readouterr()
    assert run(monkeypatch, volume, storied.id, path, "--dry-run") == 0
    out = capsys.readouterr().out
    assert f"{KEY} 'wooden chest' on photo 2: unchanged" in out and "story guide_chest: unchanged" in out and "->" not in out
    assert run(monkeypatch, volume, storied.id, path) == 0
    assert (mount / "rooms/demo" / room_key(storied.id)).read_bytes() == once


def test_the_committed_patch_sets_the_guides_chest_line_to_the_template_line():
    patch = patcher.load_patch(REPO / "ops/patches" / f"{DEMO_ROOM}.json")
    assert patch.story == {"guide_chest": CHEST_LINE} and "guide_chest" in patch.reason
