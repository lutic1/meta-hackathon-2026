"""Story 2.14: the Architect prompt is one pure request over the stored photos (AD-3, AD-5, AD-18)."""

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from src.council import architect
from src.council.architect import (
    ArchitectPrompt,
    build_architect_prompt,
    fixed_prefix,
    prompt_hash,
)
from src.domain.schema import ArchitectCandidate, ArchitectResponse, Room, strict_schema
from src.domain.validator import validate
from src.providers.mock import ChatCall, MockProvider, MockScript

PINNED_PREFIX_HASH = "747a628a9844e35d99396b5d991d3b6b44824ce314a4f057fc4c20fde9cd2b83"
OTHER_PHOTOS = [bytes([0xFF, 0xD8, n]) * 40 for n in range(10)]
CANDIDATE = {"label": "brass key", "plural": False, "photo": 2, "box": [100, 200, 300, 400], "attributes": ["1947"], "confidence": 0.9}


@pytest.fixture
def photos(four_lock_room: Room) -> list[bytes]:
    """The six stored fixture JPEGs, as bytes in upload order."""
    return [Path(p.downscaled_path).read_bytes() for p in four_lock_room.photos]


def test_one_request_carries_every_photo_as_bytes_in_upload_order(photos):
    mock = MockProvider("architect", MockScript(chat=[json.dumps({"candidates": [CANDIDATE]})]))
    prompt = build_architect_prompt(photos)
    assert prompt.send(mock)[0] == ArchitectResponse(candidates=[ArchitectCandidate.model_validate(CANDIDATE)])
    assert len(mock.calls) == 1
    call = mock.calls[0]
    assert isinstance(call, ChatCall)
    assert call.images == photos
    assert call.reasoning_effort == "low"
    assert call.response_schema is ArchitectResponse
    assert [m.role for m in call.messages] == ["system", "user"]
    assert all(isinstance(m.content, str) for m in call.messages)
    assert call.messages[1].content.startswith("6 photos follow in upload order, indexed 0 to 5.")


def test_the_instructions_ask_for_every_field_of_a_candidate():
    system = build_architect_prompt(OTHER_PHOTOS).messages[0].content
    for phrase in ("label", "plural", "several like objects", "photo", "most clearly", "box", "0 to 1000 grid",
                   "attributes", "exactly as it appears", "confidence"):
        assert phrase in system, phrase
    assert "ids" in system and "list position" in system


def test_the_instructions_ask_for_visible_descriptive_attributes_and_bound_them():
    """A real room has few readable markings, so attributes are short visible descriptions a player can confirm (rule 4)."""
    system = build_architect_prompt(OTHER_PHOTOS).messages[0].content.lower()
    for phrase in ("two to four", "confirm by looking", "colour", "material", "shape", "size", "count", "sits or hangs",
                   "exactly as it appears", "character for character", "at most four words", "lower case",
                   "never guess", "brand", "person"):
        assert phrase in system, phrase
    assert "empty list" not in system


def test_validate_passes_over_a_draft_whose_evidence_cites_a_visible_attribute(four_lock_room: Room):
    attributes = {ix.id: ix.attributes for ix in four_lock_room.interactables}
    cited = [p.evidence.visible_attribute for p in four_lock_room.puzzles]
    assert all(attribute in attributes[p.evidence.interactable] for p, attribute in zip(four_lock_room.puzzles, cited))
    assert all(attribute.islower() and not any(c.isdigit() for c in attribute) for attribute in cited)
    assert validate(four_lock_room).ok
    data = four_lock_room.model_dump()
    for ix in data["interactables"]:
        ix["attributes"] = []
    unread = validate(Room.model_validate(data))
    assert {(r.rule, r.puzzle_id) for r in unread.reasons} == {(4, p.id) for p in four_lock_room.puzzles}


def _nodes(node: Any):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _nodes(item)


def test_response_schema_has_no_id_and_no_map_and_strict_schema_accepts_it():
    assert set(ArchitectCandidate.model_fields) == {"label", "plural", "photo", "box", "attributes", "confidence"}
    assert list(ArchitectResponse.model_fields) == ["candidates", "photos"]  # photos: story mode, a list, never a map
    schema = strict_schema(ArchitectResponse)
    objects = [n for n in _nodes(schema) if isinstance(n, dict) and n.get("type") == "object"]
    assert objects and all(n["additionalProperties"] is False and n["required"] == list(n["properties"]) for n in objects)
    assert all("id" not in n["properties"] for n in objects)
    assert not any(isinstance(n, dict) and "additionalProperties" in n and n["additionalProperties"] is not False for n in _nodes(schema))
    assert schema["properties"]["candidates"]["type"] == "array"


def test_the_fixed_prefix_is_byte_identical_across_photo_sets_and_pinned(photos):
    one, two = build_architect_prompt(photos), build_architect_prompt(OTHER_PHOTOS)
    assert one.messages[0] == two.messages[0]
    assert one.messages[0].content == fixed_prefix()
    assert hashlib.sha256(fixed_prefix().encode()).hexdigest() == PINNED_PREFIX_HASH == prompt_hash()


def test_the_builder_accepts_photos_only_and_renders_the_same_prompt_for_the_same_input(photos):
    params = inspect.signature(build_architect_prompt).parameters
    assert list(params) == ["photos"] and params["photos"].annotation == "list[bytes]"
    assert not {"Room", "RoomView", "Derived"} & set(vars(architect))
    assert set(ArchitectPrompt.__dataclass_fields__) == {"messages", "images", "response_schema", "reasoning_effort"}
    assert build_architect_prompt(photos) == build_architect_prompt(list(photos))
    rendered = "\n".join(m.content for m in build_architect_prompt(photos).messages).lower()
    assert not any(word in rendered for word in ("clue", "solution", "puzzle", "profile", "derived", "rung"))


def test_an_empty_photo_set_is_refused():
    with pytest.raises(ValueError, match="at least one photo"):
        build_architect_prompt([])
