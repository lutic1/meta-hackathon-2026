"""Story 2.23: the Dry run prompt is built only from what a player sees (AD-3, AD-12)."""

import inspect
import json
from pathlib import Path
from typing import Any

from src.council.dryrun import (
    REASONING_EFFORT,
    SYSTEM,
    DryRunPrompt,
    build_dry_run_prompt,
)
from src.domain.redact import to_prompt_view
from src.domain.schema import (
    Derived,
    DryRunAnswer,
    DryRunAnswers,
    Puzzle,
    Room,
    RoomView,
    strict_schema,
)
from src.providers.base import ChatMessage
from src.providers.mock import ChatCall, MockProvider, MockScript
from tests.fixtures.rooms import (
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)

HIDDEN_KEYS = ("solution", "evidence", "lore", "attributes", "instances", "requires", "is_exit", "derived")
SENTINEL_DERIVED = Derived(sessions=7319, persistence=0.731, time_to_first_hint_s=97.31,
                           mean_rung_per_lock_type={"code": 2.73})


def prompt_text(prompt: DryRunPrompt) -> str:
    return "\n".join(message.content for message in prompt.messages)


def with_marked_hidden_fields(view: RoomView) -> RoomView:
    """The view with a unique sentinel in every field the Dry run must not render."""
    data = view.model_dump()
    for n, ix in enumerate(data["interactables"]):
        ix["attributes"] = [f"ATTRIBUTE-SENTINEL-{n}"]
        ix["instances"] = 7_000 + n
    for n, puzzle in enumerate(data["puzzles"]):
        puzzle["lore"] = f"LORE-SENTINEL-{n}"
    return RoomView.model_validate(data)


def objects(node: Any) -> list[dict[str, Any]]:
    found = []
    if isinstance(node, dict):
        if node.get("type") == "object":
            found.append(node)
        for value in node.values():
            found.extend(objects(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(objects(item))
    return found


def test_prompt_renders_ids_labels_clues_and_rungs_and_nothing_else(four_lock_room: Room):
    view = with_marked_hidden_fields(to_prompt_view(four_lock_room))
    prompt = build_dry_run_prompt(view, DryRunAnswers)
    assert [message.role for message in prompt.messages] == ["system", "user"]
    assert prompt.messages[0].content == SYSTEM
    assert prompt.reasoning_effort == REASONING_EFFORT == "low" and prompt.response_schema is DryRunAnswers
    task = prompt.messages[1].content
    for ix in view.interactables:
        assert f"- {ix.id}: {ix.label}" in task
    for puzzle in view.puzzles:
        assert f"Puzzle {puzzle.id}" in task and f"Clue: {puzzle.clue}" in task
        assert f"1. {puzzle.rungs.nudge}" in task
        assert f"2. {puzzle.rungs.direction}" in task
        assert f"3. {puzzle.rungs.near_answer}" in task
    text = prompt_text(prompt)
    assert "ATTRIBUTE-SENTINEL" not in text and "LORE-SENTINEL" not in text
    assert all(str(ix.instances) not in text for ix in view.interactables)
    assert all(key not in text for key in HIDDEN_KEYS)
    assert view.id not in text


def test_answers_are_asked_by_the_ix_ids_given_in_the_prompt(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    text = prompt_text(build_dry_run_prompt(view, DryRunAnswers))
    assert "Name objects only by the ids listed, never by label." in text
    assert all(ix.id in text for ix in view.interactables)
    assert "ix_" in text and "pz_" in text and "{puzzle_id, answer}" in text


def test_dry_run_answers_is_a_list_reusing_the_solution_union_that_strict_schema_accepts():
    assert DryRunAnswers.model_fields["answers"].annotation == list[DryRunAnswer]
    assert set(DryRunAnswer.model_fields) == {"puzzle_id", "answer"}
    answer, solution = DryRunAnswer.model_fields["answer"], Puzzle.model_fields["solution"]
    assert answer.annotation == solution.annotation and answer.discriminator == solution.discriminator
    strict = strict_schema(DryRunAnswers)
    assert strict["properties"]["answers"]["type"] == "array"
    for node in objects(strict):
        assert "properties" in node and node["additionalProperties"] is False  # a map would open an object
    assert "$defs" not in json.dumps(strict)
    assert DryRunAnswers.model_validate_json(json.dumps(strict_answers_example())).answers[0].answer.lock_type == "code"


def strict_answers_example() -> dict[str, Any]:
    return {"answers": [{"puzzle_id": f"pz_{'1' * 26}", "answer": {"lock_type": "code", "code": "4471"}}]}


def test_sentinel_room_leaks_no_solution_lore_evidence_derived_or_profile_field(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    room_json = json.dumps(room.model_dump(mode="json"))
    assert SENTINEL_CODE in room_json and all(ix in room_json for ix in SENTINEL_IX)
    assert set(SENTINEL_IX).isdisjoint(ix.id for ix in room.interactables)
    assert room_json.count(SENTINEL_CODE) == sum(puzzle.lock_type == "code" for puzzle in room.puzzles)

    text = prompt_text(build_dry_run_prompt(to_prompt_view(room), DryRunAnswers))
    assert SENTINEL_CODE not in text
    assert ", ".join(SENTINEL_ORDER) not in text and json.dumps(SENTINEL_ORDER)[1:-1] not in text
    assert SENTINEL_PAIR[0] not in text and SENTINEL_PAIR[1] not in text
    assert SENTINEL_FIND not in text and all(ix not in text for ix in SENTINEL_IX)
    assert all(puzzle.lore not in text for puzzle in room.puzzles)
    assert all(key not in text for key in HIDDEN_KEYS)
    assert all(field not in text for field in Derived.model_fields)
    derived = SENTINEL_DERIVED.model_dump(mode="json")
    assert all(str(value) not in text for value in (derived["sessions"], derived["persistence"],
                                                     derived["time_to_first_hint_s"], 2.73))
    assert list(inspect.signature(build_dry_run_prompt).parameters) == ["room_view", "response_schema"]


def test_the_same_view_twice_gives_identical_prompts_and_leaves_the_input_unchanged(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    before = view.model_copy(deep=True)
    first = build_dry_run_prompt(view, DryRunAnswers)
    second = build_dry_run_prompt(view, DryRunAnswers)
    assert first == second and first is not second and first.messages is not second.messages
    assert view == before
    assert first == build_dry_run_prompt(before, DryRunAnswers)


def test_photos_reach_the_call_as_bytes_through_the_adapter(four_lock_room: Room):
    view = to_prompt_view(four_lock_room)
    prompt = build_dry_run_prompt(view, DryRunAnswers)
    photos = [Path(photo.downscaled_path).read_bytes() for photo in four_lock_room.photos]
    reply = DryRunAnswers(answers=[DryRunAnswer(puzzle_id=p.id, answer=p.solution) for p in four_lock_room.puzzles])
    provider = MockProvider("dryrun", script=MockScript(chat=[reply.model_dump_json()]))

    response = provider.chat(prompt.messages, images=photos, response_schema=prompt.response_schema,
                             reasoning_effort=prompt.reasoning_effort)

    call = provider.calls[0]
    assert isinstance(call, ChatCall) and len(provider.calls) == 1
    assert call.images == photos and all(isinstance(image, bytes) and image for image in call.images)
    assert call.messages == [ChatMessage("system", SYSTEM), prompt.messages[1]]
    assert call.response_schema is DryRunAnswers and call.reasoning_effort == "low"
    assert all(isinstance(message.content, str) for message in call.messages)  # the photos are never prompt text

    parsed = DryRunAnswers.model_validate_json(response.text)
    ids = {ix.id for ix in view.interactables}
    named = {
        value for answer in parsed.answers
        for value in answer.answer.model_dump().values() if isinstance(value, str) and value.startswith("ix_")
    } | {ix for answer in parsed.answers for ix in getattr(answer.answer, "interactables", [])}
    assert named and named <= ids
    assert {answer.puzzle_id for answer in parsed.answers} == {puzzle.id for puzzle in view.puzzles}
