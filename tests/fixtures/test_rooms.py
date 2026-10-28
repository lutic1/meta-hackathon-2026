"""Story 1.6: the synthetic fixture rooms and the scenes drawn for them."""

from pathlib import Path

from PIL import Image

from src.domain.schema import Room
from src.domain.validator import validate
from tests.fixtures.rooms import INTERACTABLES, LONG_EDGE, write_fixtures

IGNORED_FOLDERS = {"rooms", "photos", "captures", "uploads"}
REPO = Path(__file__).resolve().parents[2]


def test_generator_writes_six_synthetic_jpeg_scenes_with_one_portrait(tmp_path):
    four_lock, _ = write_fixtures(tmp_path / "out")
    paths = [Path(photo.downscaled_path) for photo in four_lock.photos]
    assert len(paths) == 6 and all(path.parent == tmp_path / "out" for path in paths)
    sizes = []
    for path, photo in zip(paths, four_lock.photos, strict=True):
        with Image.open(path) as image:
            assert image.format == "JPEG"
            sizes.append(image.size)
        assert photo.size == path.stat().st_size and photo.original_path == str(path)
    assert all(max(size) == LONG_EDGE for size in sizes)
    assert any(height > width for width, height in sizes)


def _dark_pixels(path: str, box: tuple[int, int, int, int], below: int) -> int:
    with Image.open(path) as image:
        crop = image.convert("L").crop(box)
    return sum(count for count, grey in crop.getcolors(crop.width * crop.height) if grey < below)


def test_code_scenes_draw_the_evidence_the_clues_point_at(four_lock_room: Room):
    """The clock face carries hands and numerals and the door carries digits above its frame (Story 2.24, SIT-14)."""
    _, clock_photo, (x0, y0, x1, y1), _ = INTERACTABLES["clock"]
    inside_the_outline = (x0 + 24, y0 + 24, x1 - 24, y1 - 24)  # the label alone leaves a few hundred dark pixels
    assert _dark_pixels(four_lock_room.photos[clock_photo].downscaled_path, inside_the_outline, 128) > 2000
    _, door_photo, (x0, y0, x1, _), _ = INTERACTABLES["door"]
    assert _dark_pixels(four_lock_room.photos[door_photo].downscaled_path, (x0, 0, x1, y0), 160) > 500


def test_output_sits_outside_every_ignored_folder_and_the_repo(fixture_dir, four_lock_room):
    for photo in four_lock_room.photos:
        path = Path(photo.downscaled_path).resolve()
        assert path.is_relative_to(fixture_dir.resolve()) and not path.is_relative_to(REPO)
        assert IGNORED_FOLDERS.isdisjoint(path.relative_to(fixture_dir.resolve()).parts)


def test_four_lock_room_covers_every_lock_type_with_one_exit(four_lock_room: Room):
    assert len(four_lock_room.photos) == 6
    assert len(four_lock_room.interactables) >= 5
    assert all(ix.polygons and all(len(polygon) >= 3 for polygon in ix.polygons) for ix in four_lock_room.interactables)
    assert 4 <= len(four_lock_room.puzzles) <= 6
    assert {puzzle.lock_type for puzzle in four_lock_room.puzzles} == {"code", "order", "use_on", "find"}
    assert sum(puzzle.is_exit for puzzle in four_lock_room.puzzles) == 1


def test_code_and_find_room_uses_only_code_and_find_locks(code_and_find_room: Room):
    assert {puzzle.lock_type for puzzle in code_and_find_room.puzzles} == {"code", "find"}
    assert 4 <= len(code_and_find_room.puzzles) <= 6
    assert sum(puzzle.is_exit for puzzle in code_and_find_room.puzzles) == 1


def test_both_rooms_validate_clean(four_lock_room, code_and_find_room):
    assert validate(four_lock_room).reasons == []
    assert validate(code_and_find_room).reasons == []
    assert validate(four_lock_room).ok and validate(code_and_find_room).ok


def test_fixture_copies_are_fresh_per_test(four_lock_room, fixture_rooms):
    assert four_lock_room == fixture_rooms[0] and four_lock_room is not fixture_rooms[0]
