"""Story mode (owner decision Oct 29): the Architect names each photo's area and order, and the segment stage copies them onto the Room's photos (AD-2, AD-7).

The answer is checked in the pipeline, not by a Validator rule: every photo
named once, at most 4 areas, each label trimmed and lowercased to 1 to 24
characters, each pan 0 or more. On any failure every photo is in the one
area "room" with no pan, one ring in upload order.
"""

from typing import Any

import pytest

from src.council.architect import SYSTEM, build_architect_prompt
from src.domain.schema import ArchitectPhoto, ArchitectResponse, Photo, strict_schema
from src.pipeline.ingest import read_photos
from src.pipeline.segment import MAX_AREAS, photo_areas
from tests.pipeline.stages import Segmenter, architect_mock, build_over, labels, square

HASH = "0" * 64
PHOTOS = [Photo(hash=HASH, size=1, downscaled_path=f"p/{i}.jpg", original_path=f"o/{i}.jpg") for i in range(4)]
GOOD = [
    {"photo": 0, "area": " Front Hall ", "pan": 0},
    {"photo": 1, "area": "front hall", "pan": 1},
    {"photo": 2, "area": "LOUNGE", "pan": 1},
    {"photo": 3, "area": "lounge", "pan": 0},
]
FALLBACK = [("room", None)] * 4


def answer(entries: list[dict[str, Any]]) -> list[ArchitectPhoto]:
    return [ArchitectPhoto.model_validate(entry) for entry in entries]


def areas(photos: list[Photo]) -> list[tuple[str, int | None]]:
    return [(photo.area, photo.pan) for photo in photos]


def test_the_prompt_asks_for_each_photos_room_and_its_left_to_right_order():
    assert "name the room each photo shows, in 1 to 3 plain words, the same words for the same room" in SYSTEM
    assert "order each room's photos left to right as if turning on the spot" in SYSTEM
    assert build_architect_prompt([b"jpeg"]).messages[0].content == SYSTEM


def test_the_response_schema_asks_for_a_photos_list_never_a_map():
    schema = strict_schema(ArchitectResponse)
    assert schema["required"] == ["candidates", "photos"]
    item = schema["properties"]["photos"]["items"]
    assert item["type"] == "object" and item["required"] == ["photo", "area", "pan"]
    assert ArchitectResponse.model_validate({"candidates": []}).photos == []  # a reply stored before story mode


def test_a_good_answer_is_copied_on_with_labels_trimmed_and_lowercased():
    assert areas(photo_areas(PHOTOS, answer(GOOD))) == [("front hall", 0), ("front hall", 1), ("lounge", 1), ("lounge", 0)]
    assert [p.hash for p in photo_areas(PHOTOS, answer(GOOD))] == [p.hash for p in PHOTOS]


@pytest.mark.parametrize("entries", [
    [],
    GOOD[:3],  # photo 3 has no area
    [*GOOD[:3], {**GOOD[3], "photo": 2}],  # photo 2 twice
    [*GOOD, {"photo": 4, "area": "attic", "pan": 0}],  # no photo 4
    [{**GOOD[0], "area": "   "}, *GOOD[1:]],
    [{**GOOD[0], "area": "x" * 25}, *GOOD[1:]],
    [{**GOOD[0], "pan": -1}, *GOOD[1:]],
])
def test_any_gap_puts_every_photo_in_the_one_area_room_with_no_pan(entries: list[dict[str, Any]]):
    assert areas(photo_areas(PHOTOS, answer(entries))) == FALLBACK


def test_four_areas_are_allowed_and_five_are_not():
    assert MAX_AREAS == 4
    four = [{**entry, "area": name} for entry, name in zip(GOOD, ["a", "b", "c", "d"], strict=True)]
    assert areas(photo_areas(PHOTOS, answer(four))) == [("a", 0), ("b", 1), ("c", 1), ("d", 0)]
    photos = [*PHOTOS, PHOTOS[0]]
    five = [*four, {"photo": 4, "area": "e", "pan": 0}]
    assert areas(photo_areas(photos, answer(five))) == [("room", None)] * 5


def test_the_segment_stage_copies_the_areas_onto_the_rooms_photos(jobs, artifacts, ticker, doubles, uploads):
    named = [{"photo": i, "area": "front hall" if i < 2 else "lounge", "pan": i if i < 2 else 5 - i} for i in range(6)]
    candidates = labels(6)
    segmenter = Segmenter({c["label"]: [square(130, 100, 380, 285)] for c in candidates})
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect_mock(candidates, photos=named), segmenter=segmenter)
    done = build.run(build.submit(uploads).id)
    assert done.status == "done"
    assert areas(read_photos(done.room_id, artifacts)) == [
        ("front hall", 0), ("front hall", 1), ("lounge", 3), ("lounge", 2), ("lounge", 1), ("lounge", 0),
    ]


def test_an_architect_reply_without_areas_builds_one_ring_in_upload_order(jobs, artifacts, ticker, doubles, uploads):
    candidates = labels(6)
    segmenter = Segmenter({c["label"]: [square(130, 100, 380, 285)] for c in candidates})
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect_mock(candidates, photos=[]), segmenter=segmenter)
    done = build.run(build.submit(uploads).id)
    assert areas(read_photos(done.room_id, artifacts)) == [("room", None)] * 6
