"""Story 4.8: the live Trickster source, its prompt over the `RoomView` and the Game-state summary, and the recorder (FR-18, FR-25, AD-3, AD-6, AD-15)."""

import json
import re
from pathlib import Path
from typing import Any, get_type_hints

import httpx
import pytest

from src.config import Settings
from src.council.trickster import (
    RECORDED_PROPOSALS,
    SOURCES,
    SYSTEM,
    LiveSource,
    TricksterPrompt,
    TricksterProposal,
    build_trickster_prompt,
    load_proposals,
    parse_proposal,
    record_proposal,
)
from src.domain.ledger import spark_cost_usd
from src.domain.redact import to_prompt_view
from src.domain.schema import Derived, Profile, Room, RoomView, strict_schema
from src.domain.session import GameStateSummary
from src.domain.validator import BOUNDS_MESSAGE, RULES
from src.providers.base import ProviderError
from src.providers.cache import GuardedCalls, cache_key
from src.providers.meta_api import CHAT_MODEL, MetaModelProvider
from src.providers.mock import ChatCall, MockProvider, MockScript
from src.providers.spend import SpendLedger
from tests.council.test_trickster import FIRST, FIXTURE_FILE, SECOND, window_outcomes
from tests.fixtures.rooms import (
    IX,
    PZ,
    ROOM_IDS,
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)
from tests.providers.replay import load
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore, settled

REPLY = load("muse-spark-1.3/chat-trickster")
"""The SIT-15 recording: window 0 over the four-lock room, any valid proposal; a test that needs a known one scripts FIRST."""
RECORDED = parse_proposal(REPLY.body["choices"][0]["message"]["content"])
ROOM_ID_PATTERN = re.compile(r"\b(?:ix|pz)_[0-9A-HJKMNP-TV-Z]{26}\b")
SUMMARY = GameStateSummary(locks_open=[PZ["find_key"], PZ["clock_code"]], elapsed_ms=754_000, rungs_used=3)
SENTINEL_DERIVED = Derived(
    sessions=9731, persistence=0.4173, time_to_first_hint_s=137.9, mean_rung_per_lock_type={"code": 2.71}
)
"""A non-default Derived block: none of its keys or values may reach a Trickster prompt."""
PROFILE_FIELDS = {"derived", "profile", *Derived.model_fields, *Profile.model_fields}
REASON_TEXTS = {rule.message for rule in RULES.values()} | {BOUNDS_MESSAGE}
EDIT_TYPES = {"decoy", "merge", "loosen", "shortcut"}
MERGE = json.loads(FIXTURE_FILE.read_text())["proposals"][1]
"""The 4.3 fixture file's window 1: a Merge that rule 1 rejects."""


def scripted(*replies: dict[str, Any]) -> MockProvider:
    return MockProvider("trickster", script=MockScript(chat=[json.dumps(reply) for reply in replies]))


def assert_proposal_on_the_four_lock_room(proposal: TricksterProposal | None) -> None:
    """What any valid recording satisfies: one of the four edits, every id one the four-lock room has."""
    assert proposal is not None and proposal.type in EDIT_TYPES and proposal.payload.type == proposal.type
    assert set(ROOM_ID_PATTERN.findall(proposal.model_dump_json())) <= set(IX.values()) | set(PZ.values())


def assert_no_solution_or_profile_field(text: str) -> None:
    """The AD-3 sentinel test over any text a Trickster call sends."""
    assert SENTINEL_CODE not in text and "solution" not in text
    assert json.dumps(SENTINEL_ORDER)[1:-1] not in text and ", ".join(SENTINEL_ORDER) not in text
    assert SENTINEL_PAIR[0] not in text and SENTINEL_PAIR[1] not in text
    assert SENTINEL_FIND not in text and all(ix not in text for ix in SENTINEL_IX)
    assert not [field for field in PROFILE_FIELDS if field in text]
    derived = SENTINEL_DERIVED.model_dump(mode="json")
    assert all(str(value) not in text for value in (derived["sessions"], derived["persistence"], derived["time_to_first_hint_s"], 2.71))
    assert not [reason for reason in REASON_TEXTS if reason in text]


# --- The prompt ----------------------------------------------------------------------


def test_the_builder_is_typed_on_the_room_view_and_the_summary_and_accepts_no_room():
    hints = get_type_hints(build_trickster_prompt)
    assert hints == {"room_view": RoomView, "summary": GameStateSummary, "return": TricksterPrompt}
    assert Room not in hints.values()


@pytest.mark.parametrize("fixture", ["four_lock_room", "code_and_find_room"])
def test_the_rendered_prompt_holds_no_solution_derived_key_profile_field_or_reason_text(fixture: str, request):
    room = with_sentinel_solutions(request.getfixturevalue(fixture))
    assert SENTINEL_CODE in json.dumps(room.model_dump(mode="json"))
    prompt = build_trickster_prompt(to_prompt_view(room), SUMMARY)
    text = json.dumps([[m.role, m.content] for m in prompt.messages])
    assert_no_solution_or_profile_field(text)
    user = prompt.messages[1].content
    assert all(ix.id in user for ix in room.interactables)
    assert all(pz.id in user for pz in room.puzzles if pz.id not in SUMMARY.locks_open)
    assert f"Locks open: {PZ['find_key']}, {PZ['clock_code']}" in user
    assert "Time in the room: 12 min 34 s" in user and "Hints used: 3" in user


def test_the_puzzles_listed_are_only_those_still_locked_and_the_exit_keeps_its_marking(four_lock_room: Room):
    # Live playtest Oct 29: an edit on an open Puzzle changes nothing, so the model is never shown one.
    user = build_trickster_prompt(to_prompt_view(four_lock_room), SUMMARY).messages[1].content
    listed = json.loads(user.split("Puzzles:\n", 1)[1].split("\n\nGame state:", 1)[0])
    locked = [pz.id for pz in four_lock_room.puzzles if pz.id not in SUMMARY.locks_open]
    assert [puzzle["id"] for puzzle in listed] == locked and len(locked) == len(four_lock_room.puzzles) - 2
    assert [puzzle["id"] for puzzle in listed if puzzle["is_exit"]] == [PZ["door_code"]]


def test_the_prompt_carries_the_fixed_menu_at_reasoning_low():
    empty = RoomView(id=ROOM_IDS["four_lock"], interactables=[], puzzles=[])
    prompt = build_trickster_prompt(empty, SUMMARY)
    assert [m.role for m in prompt.messages] == ["system", "user"] and prompt.messages[0].content == SYSTEM
    assert all(f'"{edit_type}"' in SYSTEM for edit_type in EDIT_TYPES)
    assert prompt.response_schema is TricksterProposal and prompt.reasoning_effort == "low"
    fresh = build_trickster_prompt(empty, GameStateSummary(locks_open=[], elapsed_ms=0, rungs_used=0))
    assert "Locks open: none" in fresh.messages[1].content and "Time in the room: 0 min 0 s" in fresh.messages[1].content


# --- The response schema --------------------------------------------------------------


def test_the_response_schema_passes_strict_schema_and_allows_only_the_four_edits_with_their_payloads():
    schema = strict_schema(TricksterProposal)
    assert schema["additionalProperties"] is False and schema["required"] == ["type", "puzzle", "payload"]
    assert set(schema["properties"]["type"]["enum"]) == EDIT_TYPES
    branches = schema["properties"]["payload"]["oneOf"]
    assert {branch["properties"]["type"]["const"] for branch in branches} == EDIT_TYPES and len(branches) == 4
    fields = {branch["properties"]["type"]["const"]: branch["required"] for branch in branches}
    assert fields == {
        "decoy": ["type", "interactable", "visible_attribute"],
        "merge": ["type", "puzzle_a", "puzzle_b"],
        "loosen": ["type", "puzzle", "rung"],
        "shortcut": ["type", "puzzle", "requires"],
    }
    assert all(branch["additionalProperties"] is False for branch in branches)


def test_the_recording_is_one_of_the_four_edits_naming_only_ids_the_four_lock_room_has():
    assert REPLY.model == CHAT_MODEL and REPLY.status == 200
    assert_proposal_on_the_four_lock_room(RECORDED)
    assert RECORDED.puzzle in PZ.values()


# --- One call per window ----------------------------------------------------------------


def test_the_live_source_makes_exactly_one_chat_call_at_low_with_the_window_as_attempt(four_lock_room: Room):
    provider = scripted(FIRST)
    view = to_prompt_view(four_lock_room)
    proposal = LiveSource(provider).propose(four_lock_room.id, 3, view, SUMMARY)
    assert proposal is not None and proposal.model_dump() == FIRST
    prompt = build_trickster_prompt(view, SUMMARY)
    assert provider.calls == [ChatCall(prompt.messages, [], TricksterProposal, "low", None, attempt=3)]


def test_on_meta_the_one_request_goes_to_muse_spark_1_3_at_low_with_the_proposal_schema(four_lock_room: Room):
    requests: list[httpx.Request] = []

    def host(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(REPLY.status, json=REPLY.body)

    provider = meta(host)
    proposal = LiveSource(provider).propose(four_lock_room.id, 0, to_prompt_view(four_lock_room), SUMMARY)
    assert_proposal_on_the_four_lock_room(proposal)
    assert proposal == RECORDED
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert (body["model"], body["reasoning_effort"]) == (CHAT_MODEL, "low") == ("muse-spark-1.3", "low")
    assert body["response_format"]["json_schema"]["name"] == "TricksterProposal"


def test_ids_are_kept_exactly_as_written_and_never_matched_by_label_or_case(four_lock_room: Room):
    absent = {**FIRST, "puzzle": f"pz_{'7' * 26}", "payload": {**FIRST["payload"], "interactable": f"ix_{'7' * 26}"}}
    assert parse_proposal(json.dumps(absent)).model_dump() == absent  # parsed, so the Validator rejects it
    for written in (IX["rug"].lower().replace("ix_", "IX_"), " " + IX["rug"], "woven rug"):
        with pytest.raises(ProviderError) as raised:
            parse_proposal(json.dumps({**FIRST, "payload": {**FIRST["payload"], "interactable": written}}))
        assert raised.value.code == "invalid_proposal"


@pytest.mark.parametrize("text", ["[mock trickster] a canned line", "{}", json.dumps({**FIRST, "type": "merge"}),
                                  json.dumps({**FIRST, "payload": {**FIRST["payload"], "type": "swap"}})])
def test_a_reply_that_is_no_proposal_is_a_provider_error(text: str, four_lock_room: Room):
    provider = MockProvider("trickster", script=MockScript(chat=[text]))
    with pytest.raises(ProviderError):
        LiveSource(provider).propose(four_lock_room.id, 0, to_prompt_view(four_lock_room), SUMMARY)


# --- The cache key and the Ledger (AD-6) ---------------------------------------------------


def meta(host: Any, cache: MemoryCache | None = None, store: MemoryLedgerStore | None = None, *, enabled: bool = True) -> MetaModelProvider:
    calls = GuardedCalls(cache or MemoryCache(), SpendLedger(store or MemoryLedgerStore(), cap_usd=60), host="api.meta.ai", enabled=enabled)
    return MetaModelProvider("test-key", calls=calls, chat_kind="trickster", budget_s=30.0, transport=httpx.MockTransport(host))


def test_two_windows_with_the_same_prompt_get_two_keys_and_a_replayed_window_is_a_cache_hit_with_no_ledger_entry(
    four_lock_room: Room,
):
    requests: list[httpx.Request] = []

    def host(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(REPLY.status, json=REPLY.body)

    cache = MemoryCache()
    store = MemoryLedgerStore(settled(0.022, "riddler"))  # another kind's observed cost never prices the Trickster
    source = LiveSource(meta(host, cache, store))
    view = to_prompt_view(four_lock_room)
    for window in (0, 1):
        source.propose(four_lock_room.id, window, view, SUMMARY)

    prompt = build_trickster_prompt(view, SUMMARY)
    keys = [cache_key(CHAT_MODEL, messages=prompt.messages, response_schema=TricksterProposal, reasoning_effort="low", attempt=window)
            for window in (0, 1)]
    assert keys[0] != keys[1] and set(cache.rows) == set(keys) and len(requests) == 2
    trickster = [entry for entry in store.rows if entry.kind == "trickster"]
    reserved = [entry for entry in trickster if entry.status == "reserved"]
    observed = next(entry for entry in trickster if entry.status == "settled").usd
    assert [entry.usd for entry in reserved] == [0.01, observed]  # the seed until a Trickster call was observed
    assert observed == pytest.approx(spark_cost_usd(REPLY.body["usage"]))

    before = list(store.rows)
    again = source.propose(four_lock_room.id, 0, view, SUMMARY)
    assert_proposal_on_the_four_lock_room(again)
    assert again == RECORDED
    assert len(requests) == 2 and store.rows == before  # served from the Cache: no request, no Ledger entry


def test_with_the_cache_off_every_window_passes_the_guard(four_lock_room: Room):
    store = MemoryLedgerStore()
    source = LiveSource(meta(lambda request: httpx.Response(REPLY.status, json=REPLY.body), store=store, enabled=False))
    for _ in range(2):
        source.propose(four_lock_room.id, 0, to_prompt_view(four_lock_room), SUMMARY)
    assert [entry.status for entry in store.rows] == ["reserved", "settled"] * 2


# --- The recorder (FR-25, AD-15) ---------------------------------------------------------


def test_the_recorder_writes_each_windows_live_proposal_in_window_order_with_no_verdict_for_scripted_to_replay(
    tmp_path: Path, four_lock_room: Room
):
    live = LiveSource(scripted(FIRST, MERGE))
    view = to_prompt_view(four_lock_room)
    path = tmp_path / RECORDED_PROPOSALS
    for window in (0, 1):
        proposal = live.propose(four_lock_room.id, window, view, SUMMARY)
        assert proposal is not None
        record_proposal(path, four_lock_room.id, window, proposal)

    text = path.read_text()
    assert "validator_result" not in text and "accepted" not in text
    recording = load_proposals(path)
    assert recording.room_id == four_lock_room.id and [p.model_dump() for p in recording.proposals] == [FIRST, MERGE]

    replay = SOURCES[Settings.from_env({"DEMO_TRICKSTER": "scripted"}).demo_trickster](tmp_path)
    replayed = [replay.propose(four_lock_room.id, window, view, SUMMARY) for window in (0, 1)]
    assert [p.model_dump() if p else None for p in replayed] == [FIRST, MERGE]
    results = window_outcomes(four_lock_room, recording)  # the live Validator decides each Card again
    assert [result.ok for result in results] == [True, False] and results[1].reasons[0].rule == 1


def test_a_fresh_window_0_restarts_the_recording_and_another_room_replaces_it(tmp_path: Path):
    path = tmp_path / RECORDED_PROPOSALS
    first, second = TricksterProposal.model_validate(FIRST), TricksterProposal.model_validate(SECOND)
    record_proposal(path, ROOM_IDS["four_lock"], 0, first)
    record_proposal(path, ROOM_IDS["four_lock"], 1, second)
    assert [p.type for p in load_proposals(path).proposals] == ["decoy", "loosen"]
    record_proposal(path, ROOM_IDS["four_lock"], 0, second)
    assert [p.type for p in load_proposals(path).proposals] == ["loosen"]
    record_proposal(path, ROOM_IDS["code_and_find"], 1, first)
    replaced = load_proposals(path)
    assert replaced.room_id == ROOM_IDS["code_and_find"] and [p.type for p in replaced.proposals] == ["decoy"]


def test_live_never_calls_the_recorder_and_a_recording_live_source_calls_it_once_per_window(
    tmp_path: Path, monkeypatch, four_lock_room: Room
):
    calls: list[tuple[Path, str, int]] = []
    monkeypatch.setattr("src.council.trickster.record_proposal", lambda path, room_id, window, proposal: calls.append((path, room_id, window)))
    view = to_prompt_view(four_lock_room)
    for window in (0, 1):
        LiveSource(scripted(FIRST)).propose(four_lock_room.id, window, view, SUMMARY)
    assert calls == []
    recording = LiveSource(scripted(FIRST, SECOND), recording=tmp_path / RECORDED_PROPOSALS)
    for window in (0, 1):
        recording.propose(four_lock_room.id, window, view, SUMMARY)
    assert calls == [(tmp_path / RECORDED_PROPOSALS, four_lock_room.id, 0), (tmp_path / RECORDED_PROPOSALS, four_lock_room.id, 1)]


def test_a_failed_call_records_nothing(tmp_path: Path, four_lock_room: Room):
    source = LiveSource(MockProvider("trickster", script=MockScript(chat=["not json"])), recording=tmp_path / RECORDED_PROPOSALS)
    with pytest.raises(ProviderError):
        source.propose(four_lock_room.id, 0, to_prompt_view(four_lock_room), SUMMARY)
    assert not (tmp_path / RECORDED_PROPOSALS).exists()
