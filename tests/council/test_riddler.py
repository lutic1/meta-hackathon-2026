"""Story 2.19: the Riddler prompt, its response schema and the regeneration variant (AD-3, AD-5, UX-DR76)."""

import inspect
import json
from typing import Any

import pytest
from pydantic import ValidationError

from src.council.riddler import (
    CUT6_LOCK_TYPES,
    LOCK_TYPES,
    RiddlerPrompt,
    build_author_prompt,
    build_regeneration_prompt,
    response_schema,
)
from src.domain.redact import to_prompt_view
from src.domain.schema import Derived, InteractableView, Room, RoomDraft, RoomView, ValidatorReason, strict_schema
from src.domain.validator import LORE_MAX_WORDS, RULES
from src.providers.base import ChatMessage
from tests.fixtures.rooms import IX

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
SENTINEL_CODE = "ZQXJV-9731"
SENTINEL_IX = [f"ix_{ULID[:-2]}Q{n}" for n in range(1, 5)]
SENTINEL_ORDER = SENTINEL_IX[:3]
SENTINEL_PAIR = (SENTINEL_IX[0], SENTINEL_IX[1])
SENTINEL_FIND = SENTINEL_IX[3]
SENTINEL_DERIVED = Derived(
    sessions=9731, persistence=0.4173, time_to_first_hint_s=137.9, mean_rung_per_lock_type={"code": 2.71}
)
PROFILE_FIELDS = {"derived", "profile", *Derived.model_fields}
PUZZLE_FIELDS = {"lock_type", "is_exit", "requires", "clue", "lore", "rungs", "evidence", "solution"}
SOLUTION_KEYS = {"code": {"code"}, "order": {"interactables"}, "use_on": {"item", "target"}, "find": {"target"}}
IX_PATTERN = "^ix_[0-9A-HJKMNP-TV-Z]{26}$"
PZ_1 = f"pz_{ULID[:-1]}1"


def with_sentinel_solutions(room: Room) -> Room:
    """The room with one sentinel solution per lock type; the ids and the code appear nowhere else in it."""
    by_type = {
        "code": {"code": SENTINEL_CODE},
        "order": {"interactables": SENTINEL_ORDER},
        "use_on": {"item": SENTINEL_PAIR[0], "target": SENTINEL_PAIR[1]},
        "find": {"target": SENTINEL_FIND},
    }
    data = room.model_dump()
    for puzzle in data["puzzles"]:
        puzzle["solution"] = {"lock_type": puzzle["lock_type"], **by_type[puzzle["lock_type"]]}
    return Room.model_validate(data)


def objects_in(prompt: RiddlerPrompt) -> list[dict[str, Any]]:
    """The JSON list the user text renders."""
    return json.loads(prompt.user[prompt.user.index("[") : prompt.user.rindex("]") + 1])


def puzzle_schema(model: type) -> dict[str, Any]:
    return strict_schema(model)["properties"]["p1"]


def map_typed(node: Any) -> list[dict[str, Any]]:
    """Every object node whose keys are open: no fixed `properties`, or additional or pattern properties."""
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        is_object = node.get("type") == "object" or "properties" in node
        if is_object and ("properties" not in node or node.get("additionalProperties") or "patternProperties" in node):
            found.append(node)
        for value in node.values():
            found += map_typed(value)
    elif isinstance(node, list):
        for item in node:
            found += map_typed(item)
    return found


def draft(**puzzle: Any) -> dict[str, Any]:
    base = {
        "lock_type": "find", "is_exit": True, "requires": [], "clue": "A clue.", "lore": "Some lore.",
        "rungs": {"nudge": "Look.", "direction": "Look there.", "near_answer": "Look there and click it."},
        "evidence": {"interactable": IX["key"], "visible_attribute": "brass"},
        "solution": {"lock_type": "find", "target": IX["key"]},
    }
    return {**base, **puzzle}


# --- The authoring prompt ----------------------------------------------------


def test_author_prompt_renders_only_the_interactables_at_medium(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    prompt = build_author_prompt(view)
    assert prompt.reasoning_effort == "medium"
    assert prompt.response_schema is response_schema()
    assert prompt.messages() == [ChatMessage("system", prompt.system), ChatMessage("user", prompt.user)]
    objects = objects_in(prompt)
    assert objects == [ix.model_dump() for ix in view.interactables]
    assert all(set(obj) == {"id", "label", "attributes", "instances", "photo"} for obj in objects)
    assert set(InteractableView.model_fields) == {"id", "label", "attributes", "instances", "photo"}
    text = prompt.system + prompt.user
    for puzzle in view.puzzles:
        assert puzzle.id not in text and puzzle.clue not in text and puzzle.lore not in text
        assert all(rung not in text for rung in puzzle.rungs.model_dump().values())
    assert "pz_" not in text and '"photos"' not in text and "polygons" not in text and "hash" not in text


def test_author_prompt_is_pure_and_the_same_for_the_same_view(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    before = view.model_copy(deep=True)
    assert build_author_prompt(view) == build_author_prompt(view)
    assert view == before


# --- The response schema (AD-2, AD-18) ---------------------------------------


def test_response_schema_keys_puzzles_p1_to_p6_with_p5_and_p6_optional():
    schema = response_schema().model_json_schema()
    assert list(schema["properties"]) == ["p1", "p2", "p3", "p4", "p5", "p6"]
    assert schema["required"] == ["p1", "p2", "p3", "p4"]
    puzzle = puzzle_schema(response_schema())
    assert set(puzzle["properties"]) == PUZZLE_FIELDS and set(puzzle["required"]) == PUZZLE_FIELDS
    assert puzzle["properties"]["requires"]["items"]["enum"] == ["p1", "p2", "p3", "p4", "p5", "p6"]
    assert puzzle["properties"]["is_exit"]["type"] == "boolean"
    assert set(puzzle["properties"]["rungs"]["properties"]) == {"nudge", "direction", "near_answer"}
    evidence = puzzle["properties"]["evidence"]["properties"]
    assert set(evidence) == {"interactable", "visible_attribute"}
    assert evidence["interactable"]["pattern"] == IX_PATTERN and evidence["visible_attribute"]["type"] == "string"


def test_solution_is_a_tagged_union_naming_ix_ids_for_every_type_but_code():
    solution = puzzle_schema(response_schema())["properties"]["solution"]
    variants = {next(iter(v["properties"]["lock_type"].values())): v["properties"] for v in solution["oneOf"]}
    assert set(variants) == set(LOCK_TYPES)
    for lock_type, properties in variants.items():
        assert set(properties) == {"lock_type"} | SOLUTION_KEYS[lock_type]
    assert variants["code"]["code"]["type"] == "string" and "pattern" not in variants["code"]["code"]
    assert variants["order"]["interactables"]["items"]["pattern"] == IX_PATTERN
    assert variants["use_on"]["item"]["pattern"] == IX_PATTERN and variants["use_on"]["target"]["pattern"] == IX_PATTERN
    assert variants["find"]["target"]["pattern"] == IX_PATTERN


def test_response_schema_has_no_map_typed_field_and_strict_schema_accepts_it():
    for lock_types in (LOCK_TYPES, CUT6_LOCK_TYPES):
        model = response_schema(lock_types)
        assert map_typed(model.model_json_schema()) == []
        assert map_typed(strict_schema(model)) == []
        assert {"$ref", "$defs"}.isdisjoint(json.dumps(strict_schema(model)).replace('"', "").split())


def test_response_schema_validates_a_draft_and_refuses_a_mismatched_solution():
    model = response_schema()
    parsed = model.model_validate({"p1": draft(), "p2": draft(), "p3": draft(), "p4": draft()})
    assert parsed.p5 is None and parsed.p6 is None and parsed.p1.solution.target == IX["key"]
    with pytest.raises(ValidationError):
        model.model_validate({"p1": draft(), "p2": draft(), "p3": draft()})
    with pytest.raises(ValidationError):
        model.model_validate({"p1": draft(lock_type="code"), "p2": draft(), "p3": draft(), "p4": draft()})
    with pytest.raises(ValidationError):
        model.model_validate({"p1": draft(requires=["p7"]), "p2": draft(), "p3": draft(), "p4": draft()})


def test_lock_types_default_to_all_four_and_cut_6_passes_only_code_and_find():
    assert puzzle_schema(response_schema())["properties"]["lock_type"]["enum"] == list(LOCK_TYPES)
    cut6 = puzzle_schema(response_schema(CUT6_LOCK_TYPES))
    assert cut6["properties"]["lock_type"]["enum"] == ["code", "find"]
    tags = {v["properties"]["lock_type"]["const"] for v in cut6["properties"]["solution"]["oneOf"]}
    assert tags == {"code", "find"}
    with pytest.raises(ValidationError):
        response_schema(CUT6_LOCK_TYPES).model_validate({"p1": draft(
            lock_type="order", solution={"lock_type": "order", "interactables": [IX["key"], IX["chest"], IX["clock"]]},
        ), "p2": draft(), "p3": draft(), "p4": draft()})
    empty = RoomView(id=f"room_{ULID}", interactables=[], puzzles=[])
    assert build_author_prompt(empty, CUT6_LOCK_TYPES).response_schema is response_schema(CUT6_LOCK_TYPES)
    for bad in ((), ("code", "guess")):
        with pytest.raises(ValueError):
            response_schema(bad)  # type: ignore[arg-type]


def test_instructions_name_the_allowed_lock_types_and_exactly_one_exit(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    system = build_author_prompt(view).system
    assert "Exactly one puzzle" in system and '"is_exit": true' in system
    assert '"lock_type" is one of: code, order, use_on, find.' in system
    cut6 = build_author_prompt(view, CUT6_LOCK_TYPES).system
    assert '"lock_type" is one of: code, find.' in cut6
    assert '"order"' not in cut6 and '"use_on"' not in cut6
    for rule in RULES.values():
        assert f"{rule.number}. {rule.name}." in system
        assert rule.message not in system


# --- The fixed prefix: generated-line voice rules (UX-DR76) ------------------


def test_fixed_prefix_carries_the_voice_rules(four_lock_room: Room):
    system = build_author_prompt(to_prompt_view(four_lock_room)).system
    assert "Riddler's voice" in system and '"clue"' in system and '"lore"' in system
    assert f"at most {LORE_MAX_WORDS} words" in system
    assert "Guide's voice" in system and '"rungs"' in system
    nudge, direction, near = (system.index(f'"{rung}"') for rung in ("nudge", "direction", "near_answer"))
    assert nudge < direction < near
    assert '"nudge" says where to look. It is the shortest' in system
    assert '"direction" says what to notice there. It is longer than the nudge.' in system
    assert '"near_answer" says how to use what was noticed. It is the longest, and still at most two sentences.' in (
        system
    )
    assert "Lengths increase from nudge to direction to near-answer." in system
    assert 'Never write "the answer is", "the code is" or anything like it.' in system
    assert "No clue, lore line or rung holds a solution token" in system


def test_fixed_prefix_is_the_same_for_every_room(four_lock_room: Room, code_and_find_room: Room):
    one = build_author_prompt(to_prompt_view(four_lock_room)).system
    two = build_author_prompt(to_prompt_view(code_and_find_room)).system
    assert one == two
    assert build_regeneration_prompt(to_prompt_view(four_lock_room), []).system == one


# --- The regeneration variant ------------------------------------------------

SENTINEL_DRAFT = RoomDraft.model_validate({"puzzles": [
    {
        "key": "p1", "lock_type": "code", "requires": [], "is_exit": True,
        "solution": {"lock_type": "code", "code": SENTINEL_CODE},
        "evidence": {"interactable": IX["door"], "visible_attribute": "painted green"},
        "clue": "CLUE-SENTINEL-XJQ the door wears its number",
        "lore": "LORE-SENTINEL-XJQ the door remembers",
        "rungs": {"nudge": "NUDGE-SENTINEL-XJQ", "direction": "DIRECTION-SENTINEL-XJQ",
                  "near_answer": "NEAR-SENTINEL-XJQ"},
    },
    {
        "key": "p2", "lock_type": "find", "requires": [], "is_exit": False,
        "solution": {"lock_type": "find", "target": SENTINEL_FIND},
        "evidence": {"interactable": IX["key"], "visible_attribute": "brass"},
        "clue": "CLUE-SENTINEL-TWO", "lore": "LORE-SENTINEL-TWO",
        "rungs": {"nudge": "NUDGE-TWO", "direction": "DIRECTION-TWO", "near_answer": "NEAR-TWO"},
    },
]})
REASONS = [
    ValidatorReason(rule=5, puzzle_id=PZ_1, field="near_answer", message=RULES[5].message),
    ValidatorReason(rule=6, puzzle_id=PZ_1, field="lore", message=RULES[6].message),
    ValidatorReason(rule=7, puzzle_id=None, field="is_exit", message=RULES[7].message),
]


def test_regeneration_variant_carries_the_reasons_only(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    author = build_author_prompt(view)
    prompt = build_regeneration_prompt(view, REASONS)
    assert prompt.reasoning_effort == "medium" and prompt.response_schema is author.response_schema
    assert prompt.user.startswith(author.user) and objects_in(prompt) == objects_in(author)
    assert "refused" in prompt.user and "not shown" in prompt.user
    assert f"- rule 5, puzzle {PZ_1}, field near_answer: {RULES[5].message}" in prompt.user
    assert f"- rule 6, puzzle {PZ_1}, field lore: {RULES[6].message}" in prompt.user
    assert f"- rule 7, field is_exit: {RULES[7].message}" in prompt.user
    assert "None" not in prompt.user
    assert list(inspect.signature(build_regeneration_prompt).parameters) == ["view", "reasons", "lock_types"]


def test_regeneration_variant_shows_nothing_of_the_refused_draft(four_lock_room: Room):
    prompt = build_regeneration_prompt(to_prompt_view(four_lock_room), REASONS)
    text = prompt.system + prompt.user
    for puzzle in SENTINEL_DRAFT.puzzles:
        assert puzzle.clue not in text and puzzle.lore not in text
        assert all(rung not in text for rung in puzzle.rungs.model_dump().values())
    assert SENTINEL_CODE not in text and SENTINEL_FIND not in text
    assert "SENTINEL" not in text and '"key"' not in text and '"puzzles"' not in text


# --- Sentinel solutions, Derived keys and profile fields (AD-3) -------------


@pytest.mark.parametrize("fixture", ["four_lock_room", "code_and_find_room"])
def test_neither_prompt_leaks_a_sentinel_solution_derived_key_or_profile_field(fixture: str, request):
    room = with_sentinel_solutions(request.getfixturevalue(fixture))
    assert SENTINEL_CODE in json.dumps(room.model_dump(mode="json"))  # the sentinels are in the room
    assert all(ix not in json.dumps([i.model_dump() for i in room.interactables]) for ix in SENTINEL_IX)
    view = to_prompt_view(room)
    lock_types = CUT6_LOCK_TYPES if fixture == "code_and_find_room" else LOCK_TYPES
    prompts = (build_author_prompt(view, lock_types), build_regeneration_prompt(view, REASONS, lock_types))
    derived = SENTINEL_DERIVED.model_dump(mode="json")
    for prompt in prompts:
        text = prompt.system + prompt.user
        assert SENTINEL_CODE not in text
        assert json.dumps(SENTINEL_ORDER)[1:-1] not in text and ", ".join(SENTINEL_ORDER) not in text
        assert SENTINEL_PAIR[0] not in text and SENTINEL_PAIR[1] not in text
        assert SENTINEL_FIND not in text and all(ix not in text for ix in SENTINEL_IX)
        assert all(field not in text for field in PROFILE_FIELDS)
        values = (derived["sessions"], derived["persistence"], derived["time_to_first_hint_s"], 2.71)
        assert all(str(value) not in text for value in values)
        assert all("solution" not in obj and "evidence" not in obj for obj in objects_in(prompt))
