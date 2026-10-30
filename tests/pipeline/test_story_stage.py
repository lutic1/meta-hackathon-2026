"""Story mode (amended 29 Oct 2026): the story stage writes each Room's own wizard lines at build time (AD-2, AD-3, AD-7, AD-16).

One `chat` call through the `storyteller` role's port over a story brief
(counts, area labels and scenery labels, never a solution, a target, an
evidence attribute or a code); a reply that fails the line rules is sent back
once with its fixed reasons, then each line still refused takes its slot's fixed
template line, filled from the Room. The build never fails because of the story.
"""

import json
import re
from dataclasses import replace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.wiring import ROLE_CALLS
from src.council.storyteller import FILLER_WORDS, LINE_MAX, SYSTEM, StoryBrief, build_story_prompt
from src.domain.redact import to_play_view
from src.domain.schema import JobState, Room, Story, StoryResponse
from src.domain.validator import gives_away, validate
from src.infra.clocks import BuildClock
from src.pipeline.author import PUZZLES, assemble_provenance, puzzles_key
from src.pipeline.build import STAGES, Build
from src.pipeline.ports import room_key
from src.pipeline.scene import scene_stage
from src.pipeline.story import (
    read_story,
    run_story,
    story_brief,
    story_reasons,
    story_stage,
    tell_story,
    template_story,
)
from src.providers.base import ProviderError
from src.providers.cache import GuardedCalls
from src.providers.meta_api import CHAT_MODEL, MetaModelProvider
from src.providers.mock import ChatCall, MockProvider, MockScript
from src.providers.spend import SpendLedger
from tests.api.test_app import make_app
from tests.fixtures.rooms import (
    IX,
    PZ,
    SENTINEL_CODE,
    SENTINEL_IX,
    with_sentinel_solutions,
)
from tests.pipeline.test_author_stage import store_interactables
from tests.providers.replay import load
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

HOST = "api.meta.ai"
JOB = f"job_{'0' * 26}"

GOOD: dict[str, Any] = {
    "architect_welcome": "Thank you for the photos. I measured every corner twice and grumbled only once.",
    "architect_welcome_visitor": "Welcome to someone's home. I measured every corner of it twice.",
    "trickster_trap": "Oh no, you seem to be trapped! I locked the way out and gave the key to the Riddler.",
    "riddler_entrance": "Don't mind him; he thinks a locked room is a party. Answer my five riddles, one at a time.",
    "guide_chest": "Stuck? I keep two hints for the whole house. Choose your moment.",
    "riddles": [{"opening": f"Riddle the {n}th, if you please.", "solved": "Well done. The house noticed."}
                for n in ("first", "second", "third", "fourth")]
               + [{"opening": "Riddle the last, if you please.", "solved": "Well done. The way out is open."}],
    "trickster_closing": "Fine. Out you go. I'll lock it again for the next guest.",
    "riddler_closing": "Clever mind. I'll write harder ones next time.",
    "guide_closing_no_hints": "Not a single hint. I'm almost offended.",
    "guide_closing_hints": "You let me help a little. I enjoyed every word.",
}
"""A story for the four-lock room (five riddles) that passes every line rule."""


def story_reply(**changes: Any) -> str:
    return json.dumps({**GOOD, **changes})


def storyteller(*texts: str) -> MockProvider:
    return MockProvider("storyteller", MockScript(chat=list(texts)))


class Failing(MockProvider):
    """The `storyteller` port when the model service does not answer."""

    def chat(self, messages, **kwargs) -> Any:
        self.calls.append(ChatCall(list(messages), [], kwargs.get("response_schema"), "low", None))
        raise ProviderError(503, "unavailable", "the service did not answer")


@pytest.fixture
def ledger() -> MemoryLedgerStore:
    return MemoryLedgerStore()


def store_puzzles(artifacts, state: JobState, room: Room) -> None:
    artifacts.put(puzzles_key(state.room_id), PUZZLES.dump_json(room.puzzles))


@pytest.fixture
def seeded(jobs, artifacts, ticker, doubles, uploads, four_lock_room) -> JobState:
    """A job whose photos are ingested and whose Interactables and Puzzles are the four-lock room's, ready for `run_story`."""
    runner = Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=doubles.stages(), regen_max=2)
    state = runner.submit(uploads)
    store_interactables(artifacts, state, four_lock_room)
    store_puzzles(artifacts, state, four_lock_room)
    return state


@pytest.fixture
def build(jobs, artifacts, ticker, doubles, four_lock_room, ledger):
    """A Build whose doubles store the four-lock room's Interactables and Puzzles, then the real story and scene stages."""
    doubles.hooks["segment"] = lambda state: store_interactables(artifacts, state, four_lock_room)
    doubles.hooks["author"] = lambda state: store_puzzles(artifacts, state, four_lock_room)

    def make(provider) -> Build:
        stages = doubles.stages()
        stages["story"] = story_stage(provider, artifacts, ledger)
        stages["scene"] = scene_stage(artifacts, ledger)
        return Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=0)

    return make


def stored_room(artifacts, state: JobState) -> Room:
    return Room.model_validate_json(artifacts.read(room_key(state.room_id)))


def lines(story: Story) -> list[str]:
    scalars = [value for key, value in story.model_dump().items() if key != "riddles"]
    return [*scalars, *(line for riddle in story.riddles for line in (riddle.opening, riddle.solved))]


# --- The stage order and the stored story ----------------------------------------


def test_story_runs_after_the_dry_run_and_before_the_scene():
    assert STAGES[-3:] == ("dryrun", "story", "scene")


def test_the_stage_writes_the_models_story_and_scene_puts_it_on_the_room(build, uploads, artifacts, four_lock_room):
    provider = storyteller(story_reply())
    runner = build(provider)
    done = runner.run(runner.submit(uploads).id)
    assert done.status == "done" and done.error is None
    record = next(record for record in done.stages if record.stage == "story")
    assert record.model == "mock-chat-1" and record.count == 9 + 2 * len(four_lock_room.puzzles)
    room = stored_room(artifacts, done)
    assert room.story is not None and room.story == read_story(done.room_id, artifacts)
    assert room.story.architect_welcome == GOOD["architect_welcome"]
    assert room.story.trickster_trap.startswith("Oh no, you seem to be trapped!")
    # One riddle per Puzzle, keyed by its id, the exit last.
    assert {riddle.puzzle_id for riddle in room.story.riddles} == {puzzle.id for puzzle in room.puzzles}
    exit_id = next(puzzle.id for puzzle in room.puzzles if puzzle.is_exit)
    assert room.story.riddles[-1].puzzle_id == exit_id
    rows = [row for row in done.calls if row.role == "storyteller"]
    assert len(rows) == 1 and (rows[0].model, rows[0].host) == ("mock-chat-1", "mock")
    assert room.provenance.model_ids["storyteller"] == "mock-chat-1"
    assert "story" in room.provenance.stage_timings_ms


def test_the_call_is_tagged_with_the_job_and_the_story_stage(seeded, artifacts, ledger):
    provider = storyteller(story_reply())
    run_story(seeded, provider=provider, artifacts=artifacts, ledger=ledger)
    call = provider.calls[0]
    assert isinstance(call, ChatCall)
    assert (call.job_id, call.stage, call.attempt) == (seeded.id, "story", 0)
    assert call.response_schema is StoryResponse and call.images == []


# --- What the model is given ------------------------------------------------------


def test_the_brief_carries_counts_and_scenery_labels_only(four_lock_room):
    brief = story_brief(four_lock_room)
    assert brief == StoryBrief(room_name=None, areas=("room",), photos=6, things=8, riddles=5, hints=2,
                         scenery=("woven rug",))


def test_the_prompt_never_carries_a_solution_target_evidence_or_code(four_lock_room):
    text = json.dumps([message.content for message in build_story_prompt(story_brief(four_lock_room)).messages()])
    named = {ix.label for ix in four_lock_room.interactables if ix.label != "woven rug"}
    for token in (*named, *(p.evidence.visible_attribute for p in four_lock_room.puzzles), "415", "7342"):
        assert token not in text
    room = with_sentinel_solutions(four_lock_room)
    text = json.dumps([message.content for message in build_story_prompt(story_brief(room)).messages()])
    assert all(token not in text for token in (SENTINEL_CODE, *SENTINEL_IX, *IX.values(), *PZ.values()))
    for voice in ("observes", "teases", "encourages", "most fun"):
        assert voice in build_story_prompt(story_brief(four_lock_room)).system


def test_the_prompt_gives_each_wizard_a_personality_style_examples_and_the_counts(four_lock_room):
    prompt = build_story_prompt(story_brief(four_lock_room))
    for personality in ("proud and precise", "gleeful and mischievous", "arch and teasing", "warm and dry"):
        assert personality in prompt.system
    for example in ("Wicked of me, I know.", "Don't mind him; he thinks a locked room is a party.",
                    "Choose your moment.", "I notice everything. Mostly mugs.", "The way out is yours.",
                    "Not a single hint. I'm almost offended.", "Welcome to someone's"):
        assert example in prompt.system, example
    assert '"architect_welcome_visitor"' in prompt.system and f"at most {LINE_MAX} characters" in prompt.system
    assert LINE_MAX == 160 and all(word in prompt.system for word in FILLER_WORDS)
    brief = json.loads(prompt.user[0])
    assert (brief["riddles"], brief["hints"]) == (5, 2)


def test_the_prompt_names_the_exit_only_as_the_way_out_and_no_lockable_hidden_or_carried_thing():
    rule = ('- The exit is only ever "the way out", never named by what it is (door, gate, window, hatch). Name nothing\n'
            '  that might be locked, hidden or carried; only the scenery labels given may be named.')
    assert rule in SYSTEM


EXAMPLE_ROOMS = ["four_lock_room", "code_and_find_room", "front_hall_room"]
"""Every fixture Room the story tests build: the four-lock room, the code-and-find room and the Demo-shaped front hall."""


@pytest.mark.parametrize("room_name", EXAMPLE_ROOMS)
def test_no_example_line_in_the_prompt_holds_a_word_the_check_refuses(room_name, request):
    room: Room = request.getfixturevalue(room_name)
    brief = story_brief(room)
    shown = (*brief.areas, *((brief.room_name,) if brief.room_name else ()))
    # Every quoted phrase of the prompt, its placeholders dropped: the JSON keys and slot names hold no space.
    examples = [re.sub(r"\{\w+\}", "", quoted) for quoted in re.findall(r'"([^"]*)"', SYSTEM) if " " in quoted]
    assert len(examples) > 15
    assert [example for example in examples if gives_away(example, room, shown)] == []


@pytest.mark.parametrize("room_name", EXAMPLE_ROOMS)
def test_every_template_line_passes_the_story_check_on_every_fixture_room(room_name, request):
    room: Room = request.getfixturevalue(room_name)
    story = template_story(room)
    riddles = [{"opening": riddle.opening, "solved": riddle.solved} for riddle in story.riddles]
    reply = StoryResponse.model_validate({**story.model_dump(exclude={"riddles"}), "riddles": riddles})
    assert story_reasons(reply, room) == []


def test_scenery_holding_a_word_the_check_would_refuse_is_left_out_of_the_brief(front_hall_room):
    data = front_hall_room.model_dump()
    rug = next(ix for ix in data["interactables"] if ix["id"] == IX["rug"])
    data["interactables"] += [{**rug, "id": f"ix_{n:026d}", "label": label}
                              for n, label in ((97, "front hall mirror"), (98, "brass lamp"), (99, "entryway rug"))]
    find_key = next(puzzle for puzzle in data["puzzles"] if puzzle["id"] == PZ["find_key"])
    find_key["evidence"]["visible_attribute"] = "hangs in the entryway"
    # "brass" and "entryway" are evidence words; "front" and "hall" are the room's own words, which the player sees.
    assert story_brief(Room.model_validate(data)).scenery == ("woven rug", "front hall mirror")


# --- Line rules, the one retry and the templates -----------------------------------


@pytest.mark.parametrize(("changes", "slot"), [
    ({"architect_welcome": "I hung the brass things where you'd least expect them."}, "architect_welcome"),
    ({"guide_chest": "I keep two hints in my wooden box."}, "guide_chest"),
    ({"riddler_entrance": "My riddles stopped at a telling hour."}, "riddler_entrance"),
    ({"riddler_closing": "Riddle 4 was my favourite."}, "riddler_closing"),
    ({"riddler_closing": "Clever mind!"}, "riddler_closing"),
    ({"trickster_closing": "As an AI model, I let you go."}, "trickster_closing"),
    ({"guide_chest": "x" * (LINE_MAX + 1)}, "guide_chest"),
    ({"guide_closing_hints": "  "}, "guide_closing_hints"),
])
def test_a_line_that_breaks_a_rule_is_named_by_its_slot(four_lock_room, changes, slot):
    reasons = story_reasons(StoryResponse.model_validate_json(story_reply(**changes)), four_lock_room)
    assert len(reasons) == 1 and reasons[0].startswith(f"{slot}: ")


def test_a_good_story_passes_and_only_the_trap_keeps_its_exclamation_mark(four_lock_room):
    assert story_reasons(StoryResponse.model_validate_json(story_reply()), four_lock_room) == []


@pytest.mark.parametrize(("changes", "reason"), [
    ({"guide_chest": "I keep hints here to last through your stay. Open them whenever the moment feels right."},
     "guide_chest: the line does not say there are two hints for the whole house."),
    ({"riddler_entrance": "To escape, you must meet my riddles in turn and answer with care."},
     "riddler_entrance: the line does not say there are five riddles."),
    ({"riddles": [*GOOD["riddles"][:4], {"opening": "The last one.", "solved": "Charming work, you kept pace."}]},
     "riddle 5, solved: the line does not say the way out is open."),
    ({"riddler_closing": "Here the mood deepens and lingers softly nearby."},
     "riddler_closing: the line uses filler (drift, linger, sway, gently, softly); say something plain and concrete."),
    ({"architect_welcome_visitor": "Thanks for the photos, I have shaped them into this room for you."},
     "architect_welcome_visitor: the visitor sent no photos; welcome them without thanking them for any."),
])
def test_the_counts_the_way_out_plain_words_and_the_visitor_welcome_are_checked(four_lock_room, changes, reason):
    assert story_reasons(StoryResponse.model_validate_json(story_reply(**changes)), four_lock_room) == [reason]


def test_a_count_word_that_is_also_an_evidence_word_is_still_a_count(code_and_find_room):
    # Four riddles, and "four" is in the clock's and the door's evidence; the codes' digits keep "4" refused.
    assert len(code_and_find_room.puzzles) == 4
    riddles = [{"opening": "Next one.", "solved": "Well done."}] * 3 + [{"opening": "Last.", "solved": "Way out open."}]
    words = story_reply(riddles=riddles, riddler_entrance="Answer my four riddles, one at a time.")
    assert story_reasons(StoryResponse.model_validate_json(words), code_and_find_room) == []
    digits = story_reply(riddles=riddles, riddler_entrance="Answer my 4 riddles, one at a time.")
    assert story_reasons(StoryResponse.model_validate_json(digits), code_and_find_room) == [
        "riddler_entrance: the line gives part of an answer away."]
    # Elsewhere the word stays refused.
    four = story_reply(riddles=riddles, riddler_entrance="Answer my four riddles.", riddler_closing="Four cheers.")
    assert story_reasons(StoryResponse.model_validate_json(four), code_and_find_room) == [
        "riddler_closing: the line gives part of an answer away."]


def test_a_count_may_be_digits_but_never_a_codes_digit(four_lock_room):
    data = four_lock_room.model_dump()
    for puzzle in data["puzzles"]:
        if puzzle["lock_type"] == "code":
            puzzle["solution"]["code"] = "999"
    no_codes = Room.model_validate(data)
    counted = {"guide_chest": "Stuck? I keep 2 hints for the whole house.", "riddler_entrance": "Answer my 5 riddles."}
    assert story_reasons(StoryResponse.model_validate_json(story_reply(**counted)), no_codes) == []
    # The four-lock room's codes are 415 and 7342: their digits stay refused, counts or not.
    assert story_reasons(StoryResponse.model_validate_json(story_reply(**counted)), four_lock_room) == [
        "riddler_entrance: the line gives part of an answer away.",
        "guide_chest: the line gives part of an answer away.",
    ]


def test_a_story_with_the_wrong_number_of_riddles_is_refused(four_lock_room):
    reasons = story_reasons(StoryResponse.model_validate_json(story_reply(riddles=GOOD["riddles"][:3])), four_lock_room)
    assert reasons == ["riddles: write exactly 5 riddles."]


@pytest.fixture
def front_hall_room(four_lock_room) -> Room:
    """The four-lock room shaped like the Demo room: named for its front hall and lounge, a lock's target the double front door."""
    data = four_lock_room.model_dump()
    data["name"] = "The front hall and the lounge"
    for n, photo in enumerate(data["photos"]):
        photo["area"] = "front hall" if n < 2 else "lounge"
    for ix in data["interactables"]:
        if ix["id"] == IX["chest"]:
            ix["label"] = "double front door"
    return Room.model_validate(data)


def slot_reasons(room: Room, slot: str, line: str) -> list[str]:
    reasons = story_reasons(StoryResponse.model_validate_json(story_reply(**{slot: line})), room)
    return [reason for reason in reasons if reason.startswith(f"{slot}: ")]


def test_the_area_labels_and_the_room_name_are_not_spoilers(front_hall_room):
    assert story_brief(front_hall_room).areas == ("front hall", "lounge")
    assert slot_reasons(front_hall_room, "architect_welcome",
                        "Thank you for the photos. I built your front hall and lounge from them.") == []
    assert slot_reasons(front_hall_room, "guide_chest", "Stuck? I keep two hints in the front hall and the lounge.") == []


@pytest.mark.parametrize("line", ["I hid the way out behind the front door.", "Mind the door on your way in.",
                                  "Something double waits for you."])
def test_a_word_only_in_an_answer_still_refuses_the_line(front_hall_room, line):
    assert slot_reasons(front_hall_room, "architect_welcome", line) == ["architect_welcome: the line gives part of an answer away."]


def test_rule_5_still_refuses_a_clue_naming_an_area_word_of_its_answer(front_hall_room):
    data = front_hall_room.model_dump()
    puzzle = next(puzzle for puzzle in data["puzzles"] if puzzle["id"] == PZ["key_on_chest"])
    puzzle["clue"] = "What hangs on the hook opens something at the front."
    reasons = validate(Room.model_validate(data)).reasons
    assert (5, PZ["key_on_chest"], "clue") in {(reason.rule, reason.puzzle_id, reason.field) for reason in reasons}


def good_story(room: Room, **changes: Any) -> Story:
    """`GOOD` (with `changes`) as the Room's `Story`, each riddle keyed by its Puzzle in riddle order."""
    data = {**GOOD, **changes}
    exit_last = sorted(room.puzzles, key=lambda puzzle: puzzle.is_exit)
    riddles = [{"puzzle_id": puzzle.id, **lines} for puzzle, lines in zip(exit_last, data["riddles"], strict=True)]
    return Story.model_validate({**data, "riddles": riddles})


def test_a_leaking_line_is_sent_back_once_then_only_that_slot_takes_its_template_line(seeded, artifacts, ledger, four_lock_room):
    leak = story_reply(architect_welcome="I hung the brass things where you'd least expect them.")
    provider = storyteller(leak, leak)
    result = run_story(seeded, provider=provider, artifacts=artifacts, ledger=ledger)
    assert len(provider.calls) == 2
    retry = provider.calls[1]
    assert isinstance(retry, ChatCall) and retry.attempt == 1
    sent = retry.messages[-1].content
    assert "architect_welcome: " in sent and "brass" not in sent
    story = read_story(seeded.room_id, artifacts)
    template = template_story(four_lock_room)
    assert story == good_story(four_lock_room, architect_welcome=template.architect_welcome)
    assert result.model == "mock-chat-1" and result.count == 9 + 2 * len(four_lock_room.puzzles)
    assert [row.role for row in result.calls] == ["storyteller", "storyteller"]


def test_the_retry_keeps_its_passing_lines_and_names_the_slots_it_filled(four_lock_room):
    told = tell_story(four_lock_room, storyteller(story_reply(guide_chest=""), story_reply(riddler_closing="Clever mind!")), JOB)
    template = template_story(four_lock_room)
    assert (told.attempt, told.model, told.filled) == (1, "mock-chat-1", ["riddler_closing"])
    assert told.story == good_story(four_lock_room, riddler_closing=template.riddler_closing)
    assert [refused.attempt for refused in told.refused] == [0, 1]


def test_a_refused_riddle_opening_takes_that_riddles_template_opening(four_lock_room):
    riddles = [*GOOD["riddles"][:3], {"opening": "Mind the brass.", "solved": "Well done."}, GOOD["riddles"][4]]
    leak = story_reply(riddles=riddles)
    told = tell_story(four_lock_room, storyteller(leak, leak), JOB)
    assert (told.attempt, told.model, told.filled) == (1, "mock-chat-1", ["riddle 4, opening"])
    assert told.story.riddles[3].opening == template_story(four_lock_room).riddles[3].opening == "You must answer this."
    assert told.story.riddles[3].solved == "Well done."
    assert told.story == good_story(four_lock_room, riddles=[*riddles[:3], {**riddles[3], "opening": "You must answer this."},
                                                             riddles[4]])


def test_a_retry_with_the_wrong_riddle_count_falls_back_to_the_first_reply_line_by_line(four_lock_room):
    first = story_reply(guide_chest="I keep two hints in my wooden box.")
    told = tell_story(four_lock_room, storyteller(first, story_reply(riddles=GOOD["riddles"][:3])), JOB)
    template = template_story(four_lock_room)
    assert (told.attempt, told.model, told.filled) == (0, "mock-chat-1", ["guide_chest"])
    assert told.story == good_story(four_lock_room, guide_chest=template.guide_chest)


def every_slot(story: Story) -> list[str]:
    scalars = [slot for slot in story.model_dump() if slot != "riddles"]
    return [*scalars, *(f"riddle {n}, {part}" for n in range(1, len(story.riddles) + 1) for part in ("opening", "solved"))]


def test_no_usable_reply_leaves_the_full_templates_with_no_model(four_lock_room):
    short = story_reply(riddles=GOOD["riddles"][:3])
    told = tell_story(four_lock_room, storyteller("Not JSON.", short), JOB)
    template = template_story(four_lock_room)
    assert (told.story, told.attempt, told.model) == (template, None, None)
    assert told.filled == every_slot(template) and len(told.calls) == 2


def test_a_call_that_raises_leaves_the_full_templates_even_after_a_usable_first_reply(four_lock_room):
    # The script holds one reply: the retry's call raises.
    told = tell_story(four_lock_room, storyteller(story_reply(guide_chest="")), JOB)
    template = template_story(four_lock_room)
    assert (told.story, told.attempt, told.model, told.filled) == (template, None, None, every_slot(template))
    assert len(told.calls) == 1 and [refused.attempt for refused in told.refused] == [0]


def test_a_reply_that_passes_whole_keeps_every_line_and_fills_none(four_lock_room):
    provider = storyteller(story_reply())
    told = tell_story(four_lock_room, provider, JOB)
    assert (told.story, told.attempt, told.filled, told.refused) == (good_story(four_lock_room), 0, [], [])
    assert len(provider.calls) == 1


def test_a_leaking_line_fixed_on_the_retry_keeps_the_models_story(seeded, artifacts, ledger):
    provider = storyteller(story_reply(guide_chest="Two hints live in my wooden box."), story_reply())
    result = run_story(seeded, provider=provider, artifacts=artifacts, ledger=ledger)
    story = read_story(seeded.room_id, artifacts)
    assert story is not None and story.guide_chest == GOOD["guide_chest"] and result.model == "mock-chat-1"


def test_an_unreadable_reply_is_sent_back_then_the_templates_stand(seeded, artifacts, ledger, four_lock_room):
    provider = storyteller("Once upon a time.", "Still not JSON.")
    result = run_story(seeded, provider=provider, artifacts=artifacts, ledger=ledger)
    assert "The reply did not follow the response shape." in provider.calls[1].messages[-1].content
    assert read_story(seeded.room_id, artifacts) == template_story(four_lock_room)
    assert result.model is None and result.count == 9 + 2 * len(four_lock_room.puzzles)


def test_the_templates_fill_from_the_room(four_lock_room):
    story = template_story(four_lock_room)
    assert story.architect_welcome == (
        "Thank you for your photos. I built your room from them: 6 angles, 8 things worth a closer look.")
    assert story.architect_welcome_visitor == (
        "Welcome to someone's room. I built it from their photos: 6 angles, 8 things worth a closer look.")
    assert story.trickster_trap == (
        "Oh no, you seem to be trapped! I locked the way out and gave the key to the Riddler. Wicked of me, I know.")
    # The counts are written in words: a count's word is no spoiler in its slot, a code's digit always is.
    assert story.riddler_entrance == ("Don't mind him; he thinks a locked room is a party. To escape, you must answer "
                                      "my riddles: five of them, one at a time.")
    assert story.guide_chest == "Stuck? I keep two hints for the whole house. Choose your moment."
    solved = {riddle.puzzle_id: riddle.solved for riddle in story.riddles}
    by_id = {puzzle.id: puzzle for puzzle in four_lock_room.puzzles}
    reactions = {by_id[pid].lock_type if not by_id[pid].is_exit else "exit": line for pid, line in solved.items()}
    # The key is found and kept for the chest; the shelf is an order lock; the clock a code; the door the exit.
    find = next(line for pid, line in solved.items() if by_id[pid].lock_type == "find")
    assert find == "Well found. Keep hold of that; this house isn't finished with it."
    assert reactions["use_on"] == "The right thing in the right place. The house approves."
    assert reactions["code"] == "The numbers agree with you. They rarely agree with anyone."
    assert reactions["order"] == "In order at last. Someone here will be thrilled."
    assert reactions["exit"] == "Every riddle, every answer. The way out is yours."
    assert all(riddle.opening == "You must answer this." for riddle in story.riddles)
    assert (story.trickster_closing, story.riddler_closing) == (
        "Fine. Out you go. I'll lock it again for the next guest.", "Clever mind. I'll write harder ones next time.")
    assert (story.guide_closing_no_hints, story.guide_closing_hints) == (
        "Not a single hint. I'm almost offended.", "You let me help a little. I enjoyed every word.")


def test_a_find_not_kept_for_later_reads_the_plain_reaction(code_and_find_room):
    story = template_story(code_and_find_room)
    by_id = {puzzle.id: puzzle for puzzle in code_and_find_room.puzzles}
    finds = {by_id[r.puzzle_id].solution.target: r.solved for r in story.riddles if by_id[r.puzzle_id].lock_type == "find"}
    assert finds[IX["lantern"]] == "Well found. The house noticed you noticing."


def test_named_areas_fill_the_welcome(four_lock_room):
    brief = replace(story_brief(four_lock_room), areas=("front hall", "lounge"))
    assert template_story(four_lock_room, brief).architect_welcome.startswith(
        "Thank you for your photos. I built your front hall and lounge from them")


# --- A failed call never fails the build ----------------------------------------


def test_a_failed_provider_call_falls_back_and_the_build_ends_done(build, uploads, artifacts, four_lock_room):
    provider = Failing("storyteller")
    runner = build(provider)
    done = runner.run(runner.submit(uploads).id)
    assert done.status == "done" and done.error is None
    assert stored_room(artifacts, done).story == template_story(four_lock_room)
    record = next(record for record in done.stages if record.stage == "story")
    assert record.model is None and not [row for row in done.calls if row.role == "storyteller"]


# --- Receipts, spend and the cache ----------------------------------------------


def meta_reply(request: httpx.Request) -> httpx.Response:
    body = load("muse-spark-1.3/chat-three-objects").body
    choice = {**body["choices"][0], "message": {"role": "assistant", "content": story_reply()}}
    return httpx.Response(200, json={**body, "choices": [choice]})


def test_the_call_row_carries_its_receipt_and_the_ledger_sums_its_spend(build, uploads, ledger):
    calls = GuardedCalls(MemoryCache(), SpendLedger(ledger, cap_usd=60.0), host=HOST)
    kind, budget_s = ROLE_CALLS["storyteller"]
    assert kind == "storyteller"
    meta = MetaModelProvider("test-key", calls=calls, chat_kind=kind, budget_s=budget_s, transport=httpx.MockTransport(meta_reply))
    runner = build(meta)

    first = runner.run(runner.submit(uploads).id)
    assert first.status == "done", first.error
    rows = [row for row in first.calls if row.role == "storyteller"]
    assert len(rows) == 1 and rows[0].model == CHAT_MODEL and rows[0].host == HOST
    assert not rows[0].cached and rows[0].spend_usd > 0
    entries = ledger.entries()
    assert {(entry.kind, entry.job_id, entry.stage) for entry in entries} == {("storyteller", first.id, "story")}
    assert assemble_provenance(first, entries, {}).spend_per_stage_usd["story"] > 0

    second = runner.run(runner.submit(uploads).id)
    cached = [row for row in second.calls if row.role == "storyteller"]
    assert len(cached) == 1 and cached[0].cached and cached[0].spend_usd == 0
    assert ledger.entries() == entries


# --- The mock, old rooms and the play projections --------------------------------


@pytest.mark.parametrize("room_name", ["four_lock_room", "code_and_find_room"])
def test_the_mock_writes_a_deterministic_story_for_the_fixture_rooms(room_name, request, jobs, artifacts, ticker, doubles, uploads, ledger):
    room: Room = request.getfixturevalue(room_name)
    stories = []
    for _ in range(2):
        runner = Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=doubles.stages(), regen_max=2)
        state = runner.submit(uploads)
        store_interactables(artifacts, state, room)
        store_puzzles(artifacts, state, room)
        result = run_story(state, provider=MockProvider("storyteller"), artifacts=artifacts, ledger=ledger)
        assert result.model == "mock-chat-1"
        stories.append(read_story(state.room_id, artifacts))
    assert stories[0] == stories[1] and stories[0] != template_story(room)
    assert all(line.strip() for line in lines(stories[0]))


def test_an_old_room_without_a_story_still_parses_and_serves_null(four_lock_room):
    data = four_lock_room.model_dump(mode="json")
    data.pop("story", None)
    room = Room.model_validate(data)
    assert room.story is None and to_play_view(room).story is None


def test_a_story_stored_before_the_visitor_welcome_still_parses_with_it_null(four_lock_room):
    data = template_story(four_lock_room).model_dump(mode="json")
    del data["architect_welcome_visitor"]
    assert Story.model_validate(data).architect_welcome_visitor is None


def test_both_play_projections_carry_the_story(tmp_path, four_lock_room):
    room = four_lock_room.model_copy(update={"story": template_story(four_lock_room)})
    assert to_play_view(room).story == room.story
    client = TestClient(make_app(tmp_path, room))
    served = room.story.model_dump(mode="json")
    assert client.get(f"/api/rooms/{room.id}").json()["story"] == served
    session = client.post("/api/sessions", json={"room_id": room.id}).json()
    assert client.get(f"/api/sessions/{session['id']}/room").json()["story"] == served
