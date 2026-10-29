"""Story mode (owner decision Oct 29): photo areas, start photos and evidence held back in the play projection (AD-2, AD-3).

A Photo carries the area it shows and its left-to-right `pan` there; a Room
stored before story mode reads as one area, "room", with no pan. Each
`PlayPuzzle` names the photo its riddle starts on, never an object, and its
evidence cards stay empty until its lock is open, and then hold only the real
card.
"""

import pytest
from pydantic import ValidationError

from src.domain.edits import apply_edit
from src.domain.redact import to_play_view
from src.domain.schema import (
    DEFAULT_AREA,
    DecoyPayload,
    Photo,
    Room,
    TricksterEdit,
    ValidatorResult,
)
from tests.fixtures.rooms import IX, PZ

HASH = "0" * 64


def test_a_photo_stored_before_story_mode_is_in_the_one_area_room_with_no_pan():
    photo = Photo.model_validate({"hash": HASH, "size": 1, "downscaled_path": "a", "original_path": "b"})
    assert (photo.area, photo.pan) == (DEFAULT_AREA, None) == ("room", None)


@pytest.mark.parametrize("area", ["", "x" * 25, "Front hall", " lounge"])
def test_an_area_is_1_to_24_lowercase_characters_trimmed(area: str):
    with pytest.raises(ValidationError):
        Photo(hash=HASH, size=1, downscaled_path="a", original_path="b", area=area, pan=0)


def test_the_play_view_serves_each_photos_area_and_pan(code_and_find_room: Room):
    photos = [p.model_copy(update={"area": "front hall" if i < 2 else "lounge", "pan": i % 2}) for i, p in enumerate(code_and_find_room.photos)]
    view = to_play_view(code_and_find_room.model_copy(update={"photos": photos}))
    assert [(p.area, p.pan) for p in view.photos][:3] == [("front hall", 0), ("front hall", 1), ("lounge", 0)]
    assert [(p.area, p.pan) for p in to_play_view(code_and_find_room).photos] == [("room", None)] * len(code_and_find_room.photos)


def test_each_riddle_starts_on_the_photo_of_its_target_or_for_code_and_order_its_evidence(four_lock_room: Room):
    starts = {p.id: p.start_photo for p in to_play_view(four_lock_room).puzzles}
    assert starts == {
        PZ["find_key"]: 0,  # find: the key's photo
        PZ["clock_code"]: 2,  # code: the clock the evidence names
        PZ["shelf_order"]: 3,  # order: the candle the evidence names
        PZ["key_on_chest"]: 1,  # use_on: the chest it is used on
        PZ["door_code"]: 4,
    }


def test_the_room_view_holds_back_every_evidence_card(four_lock_room: Room):
    assert all(p.evidence_cards == [] for p in to_play_view(four_lock_room).puzzles)


def test_an_open_puzzle_shows_its_real_card_and_never_a_decoy(four_lock_room: Room):
    decoy = TricksterEdit(
        id="te_" + "0" * 25 + "1", type="decoy", puzzle=PZ["clock_code"],
        payload=DecoyPayload(type="decoy", interactable=IX["rug"], visible_attribute="woven"),
        validator_result=ValidatorResult(ok=True, reasons=[]), accepted=True, window=0,
    )
    effective = apply_edit(four_lock_room, decoy)
    cards = {p.id: p.evidence_cards for p in to_play_view(effective, opened=[PZ["clock_code"]]).puzzles}
    clock = next(p for p in four_lock_room.puzzles if p.id == PZ["clock_code"])
    assert cards[PZ["clock_code"]] == [clock.evidence]
    assert all(cards[pid] == [] for pid in cards if pid != PZ["clock_code"])
