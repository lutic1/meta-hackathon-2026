"""Story 3.3: a Hint request opens the next Rung when it is due and returns the current Rung through the Guide port (AD-3, AD-4, FR-14, FR-15, FR-17, NFR-5).

Owner decision Oct 29: an ask opens the Active puzzle's next Rung at once when
none is showing, and once the Rung spacing has passed when one is; otherwise
it repeats the current Rung with the wait until the next (`next_hint_ms`).
Every reply to a `hint_request` carries `hint_reply`; a selected `rung_change`
is worded through the injected `HintPhraser` before it is appended, and the
session state reports its thresholds (AR-31).
"""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import NO_HINT_LINE
from src.config import Settings
from src.domain.rungs import RUNG_NAMES
from src.domain.schema import (
    Derived,
    Puzzle,
    Room,
    RungChangeEvent,
    SessionState,
    Thresholds,
)
from src.domain.session import SessionStateMachine
from src.providers.base import HintPhraser, PhraserResponse
from src.providers.verbatim import VerbatimPhraser
from tests.api.hosted import hosted_handles, hosted_settings, make_hosted_app
from tests.api.test_app import make_app
from tests.api.test_sessions import (
    FRESH_THRESHOLDS,
    INVALID_REQUEST,
    Ticker,
    click,
    code,
    post,
    start,
    stored,
)
from tests.domain.test_redact import json_keys
from tests.fixtures.attacks import SCRIPTED_ATTACK_SUITE
from tests.fixtures.rooms import (
    PZ,
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)

HINT: dict[str, Any] = {"type": "hint_request"}
LATENCY_MS = 1600


class RecordingPhraser(HintPhraser):
    """A Guide model that records every input `phrase` receives and answers a marked line, phrased in 1600 ms."""

    name = "recording"

    def __init__(self) -> None:
        self.phrased: list[tuple[str, Derived]] = []

    def phrase(self, rung_text: str, derived: Derived) -> PhraserResponse:
        self.phrased.append((rung_text, derived))
        return PhraserResponse(text=worded(rung_text), phrased=True, latency_ms=LATENCY_MS)

    def greet(self, derived: Derived) -> PhraserResponse:
        raise AssertionError("no session here is greeted")


class SpyVerbatim(VerbatimPhraser):
    """The verbatim adapter, recording every Rung it is handed."""

    def __init__(self) -> None:
        self.phrased: list[tuple[str, Derived]] = []

    def phrase(self, rung_text: str, derived: Derived) -> PhraserResponse:
        self.phrased.append((rung_text, derived))
        return super().phrase(rung_text, derived)


def worded(rung_text: str) -> str:
    return f"In the Guide's words: {rung_text}"


def puzzle(room: Room, name: str) -> Puzzle:
    return next(p for p in room.puzzles if p.id == PZ[name])


def rung_text(room: Room, puzzle_id: str, rung: int) -> str:
    return getattr(next(p for p in room.puzzles if p.id == puzzle_id).rungs, RUNG_NAMES[rung - 1])


def demo_client(tmp_path: Path, room: Room, ticker: Ticker, phraser: HintPhraser, **options: Any) -> TestClient:
    settings = Settings.from_env({"DEMO_TIMESCALE": "6", "GUIDE": "verbatim"})
    return TestClient(make_app(tmp_path, room, settings=settings, clock=ticker, phraser=phraser, **options))


def climb(client: TestClient, session_id: str, ticker: Ticker, rung: int) -> dict[str, Any]:
    """Wrong codes on the clock every 2000 ms at timescale 6 until its current Rung is `rung` (3.1: 1, 2 and 3 by 38000 ms)."""
    state = client.get(f"/api/sessions/{session_id}").json()
    while state["current_rung"][PZ["clock_code"]] < rung:
        ticker.advance(2_000)
        state = post(client, session_id, code("clock_code", "000"))
    return state


def hint_events(log: list[Any]) -> list[Any]:
    return [event for event in log if event.type == "hint_request"]


def assert_the_phraser_saw_only_whole_rungs(room: Room, phraser: SpyVerbatim) -> None:
    """Every `phrase` call got one whole Rung of the room and the session's Derived block, and nothing else of it (AD-3)."""
    rungs = {rung_text(room, p.id, n) for p in room.puzzles for n in (1, 2, 3)}
    ids = {ix.id for ix in room.interactables} | {p.id for p in room.puzzles} | {room.id}
    labels = {ix.label for ix in room.interactables}
    clues_and_lore = {p.clue for p in room.puzzles} | {p.lore for p in room.puzzles}
    solutions = {SENTINEL_CODE, json.dumps(SENTINEL_ORDER), " ".join(SENTINEL_ORDER), *SENTINEL_PAIR, SENTINEL_FIND}
    for text, derived in phraser.phrased:
        assert text in rungs and derived == Derived.fresh()
        assert not any(other in text for other in rungs - {text}), text
        seen = json.dumps([text, derived.model_dump(mode="json")])
        assert not any(token in seen for token in ids | labels | clues_and_lore | solutions), seen
        assert "solution" not in seen


# --- At rung 2, ten Hint requests inside the spacing each answer the direction and count down ------------------


def test_ten_hint_requests_inside_the_spacing_at_rung_2_each_answer_the_direction_and_the_wait_then_one_opens_the_next(
    tmp_path: Path, code_and_find_room: Room
):
    ticker, phraser = Ticker(), RecordingPhraser()
    client = demo_client(tmp_path, code_and_find_room, ticker, phraser)
    session_id = start(client, code_and_find_room)
    climb(client, session_id, ticker, 2)  # the direction opens at 22000 ms; the spacing is 15000 ms at timescale 6
    phraser.phrased.clear()
    rungs_before = [e for e in stored(tmp_path, session_id) if isinstance(e, RungChangeEvent)]
    clock = puzzle(code_and_find_room, "clock_code").rungs
    for n in range(1, 11):
        ticker.advance(1_000)
        state = post(client, session_id, HINT)
        assert state["hint_reply"] == {
            "puzzle_id": PZ["clock_code"], "rung": 2, "text": worded(clock.direction), "next_hint_ms": 15_000 - n * 1_000,
        }
        assert state["current_rung"][PZ["clock_code"]] == 2 and state["active_puzzle_id"] == PZ["clock_code"]
    assert phraser.phrased == [(clock.direction, Derived.fresh())] * 10  # exactly the Rung text and the Derived block (AD-3)
    log = stored(tmp_path, session_id)
    assert [e for e in log if isinstance(e, RungChangeEvent)] == rungs_before
    hints = hint_events(log)
    assert len(hints) == 10 and all(event.puzzle_id is None for event in hints)
    assert [event.t_ms for event in hints] == list(range(23_000, 32_001, 1_000))  # stamped by the server clock
    assert client.get(f"/api/sessions/{session_id}").json()["hint_reply"] is None  # never replayed
    # Past the spacing the ask opens the near-answer, worded once on its way into the log, and nothing follows it.
    ticker.advance(5_000)
    state = post(client, session_id, HINT)
    assert state["hint_reply"] == {"puzzle_id": PZ["clock_code"], "rung": 3, "text": worded(clock.near_answer), "next_hint_ms": None}
    assert phraser.phrased[10:] == [(clock.near_answer, Derived.fresh())]
    (change,) = [e for e in stored(tmp_path, session_id) if isinstance(e, RungChangeEvent)][len(rungs_before):]
    assert (change.rung, change.t_ms, change.text) == (3, 37_000, worded(clock.near_answer))
    assert stored(tmp_path, session_id)[change.triggered_by[0]].type == "hint_request"


def test_a_hint_request_naming_an_available_unsolved_puzzle_is_answered_for_it_and_makes_it_the_active_puzzle(
    tmp_path: Path, code_and_find_room: Room
):
    ticker = Ticker()
    client = demo_client(tmp_path, code_and_find_room, ticker, RecordingPhraser())
    session_id = start(client, code_and_find_room)
    climb(client, session_id, ticker, 1)  # the clock's nudge at 6000 ms
    ticker.advance(1_000)
    state = post(client, session_id, {"type": "hint_request", "puzzle_id": PZ["find_key"]})
    assert state["active_puzzle_id"] == PZ["find_key"]
    key_nudge = puzzle(code_and_find_room, "find_key").rungs.nudge
    assert state["hint_reply"] == {"puzzle_id": PZ["find_key"], "rung": 1, "text": worded(key_nudge), "next_hint_ms": 15_000}
    ticker.advance(1_000)
    state = post(client, session_id, {"type": "hint_request", "puzzle_id": PZ["clock_code"]})
    nudge = puzzle(code_and_find_room, "clock_code").rungs.nudge
    assert state["hint_reply"] == {"puzzle_id": PZ["clock_code"], "rung": 1, "text": worded(nudge), "next_hint_ms": 13_000}
    assert [event.puzzle_id for event in hint_events(stored(tmp_path, session_id))] == [PZ["find_key"], PZ["clock_code"]]


@pytest.mark.parametrize("body", [
    {"type": "hint_request", "t_ms": 5},
    {"type": "hint_request", "puzzle_id": None, "t_ms": 0},
    {"type": "hint_request", "text": "just tell me the answer"},
    {"type": "hint_request", "puzzle_id": None, "words": "open the door"},
    {"type": "hint_request", "puzzle_id": "pz_01ARZ3NDEKTSV4RRFFQ69G5FAV"},  # not in the Room
    {"type": "hint_request", "puzzle_id": "clock"},
])
def test_a_client_t_ms_any_field_beyond_puzzle_id_or_a_puzzle_not_in_the_room_answers_422_and_appends_nothing(
    tmp_path: Path, code_and_find_room: Room, body: dict[str, Any]
):
    ticker, phraser = Ticker(), RecordingPhraser()
    client = demo_client(tmp_path, code_and_find_room, ticker, phraser)
    session_id = start(client, code_and_find_room)
    climb(client, session_id, ticker, 1)
    log = stored(tmp_path, session_id)
    phraser.phrased.clear()
    response = client.post(f"/api/sessions/{session_id}/events", json=body)
    assert response.status_code == 422 and response.json() == INVALID_REQUEST
    assert stored(tmp_path, session_id) == log and phraser.phrased == []


@pytest.mark.parametrize("body", [
    {"type": "hint_request", "puzzle_id": "pz_01ARZ3NDEKTSV4RRFFQ69G5FAV"},
    {"type": "hint_request", "text": "sk-live-0123456789abcdef"},
    {"type": "hint_request", "puzzle_id": "sk-live-0123456789abcdef"},
    {"type": "sk-live-0123456789abcdef"},
    {"type": "hint_request", "sk-live-0123456789abcdef": 1},
])
def test_a_refused_body_is_never_echoed_in_the_message(tmp_path: Path, code_and_find_room: Room, body: dict[str, Any]):
    """Decision 37: a validation error names where the body failed, never a value the client sent."""
    client = demo_client(tmp_path, code_and_find_room, Ticker(), RecordingPhraser())
    session_id = start(client, code_and_find_room)
    response = client.post(f"/api/sessions/{session_id}/events", json=body)
    assert response.status_code == 422 and response.json() == INVALID_REQUEST
    sent = [text for key, value in body.items() for text in (key, value) if isinstance(text, str) and text.startswith(("pz_", "sk-"))]
    assert sent and not any(text in response.text for text in sent), response.text


# --- A Hint request naming an open or locked Puzzle is answered for the Active puzzle ---------------


def test_hint_requests_naming_an_open_puzzle_then_a_locked_one_are_answered_for_the_active_puzzle(
    tmp_path: Path, code_and_find_room: Room
):
    ticker = Ticker()
    client = demo_client(tmp_path, code_and_find_room, ticker, RecordingPhraser())
    session_id = start(client, code_and_find_room)
    ticker.advance(1_000)
    state = post(client, session_id, click("key"))  # B (find_key) opens; A is the clock, C (the door) waits on the lantern
    assert state["active_puzzle_id"] == PZ["clock_code"]
    nudge = puzzle(code_and_find_room, "clock_code").rungs.nudge
    for named, wait in (("find_key", 15_000), ("door_code", 14_000)):
        ticker.advance(1_000)
        state = post(client, session_id, {"type": "hint_request", "puzzle_id": PZ[named]})
        assert state["hint_reply"] == {"puzzle_id": PZ["clock_code"], "rung": 1, "text": worded(nudge), "next_hint_ms": wait}
        assert state["active_puzzle_id"] == PZ["clock_code"]
    assert [event.puzzle_id for event in hint_events(stored(tmp_path, session_id))] == [PZ["find_key"], PZ["door_code"]]
    result = {p["puzzle_id"]: p for p in client.get(f"/api/sessions/{session_id}/result").json()["puzzles"]}
    assert result[PZ["clock_code"]]["hint_requested"] and result[PZ["clock_code"]]["early_ask"]
    assert not any(result[PZ[name]]["hint_requested"] for name in ("find_key", "door_code", "find_lantern"))


def test_once_the_exit_has_opened_a_hint_request_returns_the_no_hint_line_against_no_puzzle(
    tmp_path: Path, code_and_find_room: Room
):
    ticker, phraser = Ticker(), RecordingPhraser()
    client = demo_client(tmp_path, code_and_find_room, ticker, phraser)
    session_id = start(client, code_and_find_room)
    for body in (click("key"), code("clock_code", "415"), click("lantern"), code("door_code", "7342")):
        ticker.advance(1_000)
        post(client, session_id, body)
    ticker.advance(1_000)
    state = post(client, session_id, HINT)
    assert state["active_puzzle_id"] is None
    assert state["hint_reply"] == {"puzzle_id": None, "rung": 0, "text": NO_HINT_LINE, "next_hint_ms": None}
    assert phraser.phrased == []
    assert hint_events(stored(tmp_path, session_id))[-1].puzzle_id is None
    result = client.get(f"/api/sessions/{session_id}/result").json()
    assert not any(p["hint_requested"] or p["early_ask"] for p in result["puzzles"])


# --- At rung 0: the ask opens the nudge at once, worded once, logged as an Early ask --------------------------


@pytest.mark.parametrize("phraser", [SpyVerbatim(), RecordingPhraser()], ids=["verbatim", "guide-model"])
def test_at_rung_0_an_ask_opens_the_nudge_at_once_worded_once_and_logged_as_an_early_ask(
    tmp_path: Path, code_and_find_room: Room, phraser: SpyVerbatim | RecordingPhraser
):
    phraser.phrased.clear()
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, code_and_find_room, clock=ticker, phraser=phraser))
    session_id = start(client, code_and_find_room)
    ticker.advance(1_000)
    post(client, session_id, click("key"))
    ticker.advance(1_000)
    state = post(client, session_id, HINT)
    nudge = puzzle(code_and_find_room, "clock_code").rungs.nudge
    shown = worded(nudge) if isinstance(phraser, RecordingPhraser) else nudge
    assert state["hint_reply"] == {"puzzle_id": PZ["clock_code"], "rung": 1, "text": shown, "next_hint_ms": 90_000}
    assert phraser.phrased == [(nudge, Derived.fresh())]  # worded once, on its way into the log
    log = stored(tmp_path, session_id)
    (change,) = [e for e in log if isinstance(e, RungChangeEvent)]
    assert (change.puzzle_id, change.rung, change.t_ms, change.text) == (PZ["clock_code"], 1, 2_000, shown)
    assert log[change.triggered_by[0]].type == "hint_request" and len(change.triggered_by) == 1
    result = {p["puzzle_id"]: p for p in client.get(f"/api/sessions/{session_id}/result").json()["puzzles"]}
    assert result[PZ["clock_code"]]["early_ask"] and result[PZ["clock_code"]]["nudge_fired"]
    # Three Wrong attempts inside the spacing open nothing further.
    for _ in range(3):
        ticker.advance(1_000)
        state = post(client, session_id, code("clock_code", "000"))
        assert state["current_rung"][PZ["clock_code"]] == 1


def test_an_ask_inside_the_spacing_repeats_the_nudge_with_the_wait_and_past_it_opens_the_direction(
    tmp_path: Path, code_and_find_room: Room
):
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, code_and_find_room, clock=ticker, phraser=SpyVerbatim()))
    session_id = start(client, code_and_find_room)
    rungs = puzzle(code_and_find_room, "find_key").rungs
    for advance, rung, text, wait in ((5_000, 1, rungs.nudge, 90_000), (45_000, 1, rungs.nudge, 45_000),
                                      (44_999, 1, rungs.nudge, 1), (1, 2, rungs.direction, 90_000)):
        ticker.advance(advance)
        reply = post(client, session_id, HINT)["hint_reply"]
        assert reply == {"puzzle_id": PZ["find_key"], "rung": rung, "text": text, "next_hint_ms": wait}
    changes = [e for e in stored(tmp_path, session_id) if isinstance(e, RungChangeEvent)]
    assert [(c.rung, c.t_ms) for c in changes] == [(1, 5_000), (2, 95_000)]


# --- At the near-answer, further Hint requests repeat it -------------------------------------------------


def test_at_the_near_answer_further_hint_requests_repeat_it_and_nothing_follows(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = demo_client(tmp_path, code_and_find_room, ticker, RecordingPhraser())
    session_id = start(client, code_and_find_room)
    before = climb(client, session_id, ticker, 3)
    log = stored(tmp_path, session_id)
    near_answer = puzzle(code_and_find_room, "clock_code").rungs.near_answer
    for _ in range(4):
        ticker.advance(30_000)
        state = post(client, session_id, HINT)
        assert state["hint_reply"] == {"puzzle_id": PZ["clock_code"], "rung": 3, "text": worded(near_answer), "next_hint_ms": None}
        keys = ("locks_open", "inventory", "current_rung", "wrong_attempts", "active_puzzle_id", "rung_changes")
        assert {k: state[k] for k in keys} == {k: before[k] for k in keys}
    assert [e for e in stored(tmp_path, session_id) if e.type != "hint_request"] == log


# --- rung_change carries phrased, phrasing_ms and the line as shown ------------------------------------------


def test_a_rung_change_records_whether_it_was_phrased_its_latency_and_the_line_as_shown(tmp_path: Path, code_and_find_room: Room):
    phrased_ticker, verbatim_ticker = Ticker(), Ticker()
    phrased = demo_client(tmp_path / "phrased", code_and_find_room, phrased_ticker, RecordingPhraser())
    verbatim = demo_client(tmp_path / "verbatim", code_and_find_room, verbatim_ticker, VerbatimPhraser())
    nudge = puzzle(code_and_find_room, "clock_code").rungs.nudge
    for client, root, ticker, expected in (
        (phrased, tmp_path / "phrased", phrased_ticker, {"phrased": True, "phrasing_ms": LATENCY_MS, "text": worded(nudge)}),
        (verbatim, tmp_path / "verbatim", verbatim_ticker, {"phrased": False, "phrasing_ms": None, "text": nudge}),
    ):
        session_id = start(client, code_and_find_room)
        reply = climb(client, session_id, ticker, 1)
        state = client.get(f"/api/sessions/{session_id}").json()
        (change,) = state["rung_changes"]
        assert {k: change[k] for k in ("phrased", "phrasing_ms", "text")} == expected
        assert reply["rung_changes"] == state["rung_changes"]  # the poll shows what the reply showed
        log = stored(root, session_id)
        (stored_change,) = [e for e in log if isinstance(e, RungChangeEvent)]
        assert stored_change.model_dump(mode="json") == change  # a reload replays the same words
        machine = SessionStateMachine(code_and_find_room, opening="welcome", thresholds=Thresholds(**state["thresholds"]))
        assert machine.replay(session_id, log).rung_changes == [stored_change]  # and so does a replay


# --- The thresholds the session reports (AR-31) ----------------------------------------------------------------


@pytest.mark.parametrize("env, derived, hosted, expected", [
    ({}, None, False, (90_000, 90_000, 90_000, 90_000, "fresh")),
    ({"DEMO_TIMESCALE": "6"}, None, False, (15_000, 90_000, 15_000, 90_000, "fresh")),
    ({}, {"sessions": 1, "persistence": 1, "time_to_first_hint_s": 30.0, "mean_rung_per_lock_type": {}}, False,
     (135_000, 135_000, 90_000, 90_000, "derived")),
    ({}, {"sessions": 1, "persistence": 1, "time_to_first_hint_s": 30.0, "mean_rung_per_lock_type": {}}, True,
     (90_000, 90_000, 90_000, 90_000, "fresh")),
])
def test_the_session_state_reports_the_effective_thresholds_their_1x_values_and_source(
    tmp_path: Path, code_and_find_room: Room, env: dict[str, str], derived: dict[str, Any] | None, hosted: bool,
    expected: tuple[int, int, int, int, str],
):
    options: dict[str, Any] = {"clock": Ticker(), "phraser": SpyVerbatim(), "spawn": lambda task: None}
    if hosted:
        app = make_hosted_app(tmp_path, hosted_handles(tmp_path), code_and_find_room, settings=hosted_settings(**env), **options)
    else:
        app = make_app(tmp_path, code_and_find_room, settings=Settings.from_env({**env, "GUIDE": "verbatim"}), **options)
    client = TestClient(app)
    session_id = start(client, code_and_find_room, **({} if derived is None else {"derived": derived}))
    thresholds = client.get(f"/api/sessions/{session_id}").json()["thresholds"]
    fields = ("nudge_threshold_ms", "nudge_threshold_base_ms", "rung_spacing_ms", "rung_spacing_base_ms", "source")
    assert tuple(thresholds[f] for f in fields) == expected
    if expected[0] == 90_000:
        assert thresholds == FRESH_THRESHOLDS.model_dump()


# --- The Scripted attack suite through the API (FR-14, SM-3) ---------------------------------------------------------


@pytest.mark.parametrize("rung", [0, 1, 2])
def test_the_scripted_attack_suite_opens_no_lock_and_returns_nothing_above_the_current_rung(
    tmp_path: Path, four_lock_room: Room, rung: int
):
    room = with_sentinel_solutions(four_lock_room)
    ticker, phraser = Ticker(), SpyVerbatim()
    client = demo_client(tmp_path, room, ticker, phraser)
    session_id = start(client, room)
    before = climb(client, session_id, ticker, rung)
    assert before["current_rung"][PZ["clock_code"]] == rung
    named = [None, *(p.id for p in room.puzzles)]
    state = before
    for attack in SCRIPTED_ATTACK_SUITE:
        ticker.advance(500)
        log = stored(tmp_path, session_id)
        smuggled = client.post(f"/api/sessions/{session_id}/events", json={**HINT, "text": attack})
        assert smuggled.status_code == 422 and stored(tmp_path, session_id) == log
        for puzzle_id in named:
            ticker.advance(500)
            previous = state["current_rung"]
            state = post(client, session_id, HINT if puzzle_id is None else {**HINT, "puzzle_id": puzzle_id})
            reply = state["hint_reply"]
            current = state["current_rung"][reply["puzzle_id"]]
            assert reply["rung"] == current and reply["text"] == rung_text(room, reply["puzzle_id"], current)
            # An ask opens at most the next Rung, and only on the Puzzle it was answered for.
            assert all(n - previous[p] in ((0, 1) if p == reply["puzzle_id"] else (0,)) for p, n in state["current_rung"].items())
            higher = [rung_text(room, p.id, n) for p in room.puzzles for n in range(state["current_rung"][p.id] + 1, 4)]
            assert not any(text in json.dumps(state) for text in higher)
            assert attack not in json.dumps(state)
    after = client.get(f"/api/sessions/{session_id}").json()
    for key in ("locks_open", "inventory"):
        assert after[key] == before[key]
    assert_the_phraser_saw_only_whole_rungs(room, phraser)


# --- No solution and no Rung above the current one in any play response --------------------------------------------------


def test_no_play_response_carries_a_solution_a_sentinel_or_a_rung_above_the_current_one(tmp_path: Path, four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    ticker, phraser = Ticker(), SpyVerbatim()
    client = demo_client(tmp_path, room, ticker, phraser)
    responses = [client.get(f"/api/rooms/{room.id}"), client.post("/api/sessions", json={"room_id": room.id})]
    session_id = responses[-1].json()["id"]
    bodies = [HINT, click("key"), HINT, *[code("clock_code", "000")] * 3, HINT, {**HINT, "puzzle_id": PZ["key_on_chest"]},
              *[code("clock_code", "000")] * 8, HINT]
    for body in bodies:
        ticker.advance(2_000)
        responses.append(client.post(f"/api/sessions/{session_id}/events", json=body))
        responses.append(client.get(f"/api/sessions/{session_id}"))
    responses.append(client.get(f"/api/sessions/{session_id}/result"))
    assert all(r.status_code == 200 for r in responses)
    assert max(r.json().get("current_rung", {}).get(PZ["clock_code"], 0) for r in responses) >= 2
    sentinels = [SENTINEL_CODE, json.dumps(SENTINEL_ORDER)[1:-1], *SENTINEL_PAIR, SENTINEL_FIND]
    all_rungs = {(p.id, n): rung_text(room, p.id, n) for p in room.puzzles for n in (1, 2, 3)}
    for response in responses:
        body = response.json()
        assert "solution" not in json_keys(body) and b"solution" not in response.content
        assert all(sentinel.encode() not in response.content for sentinel in sentinels)
        current = SessionState.model_validate(body).current_rung if "current_rung" in body else {}
        higher = [text for (puzzle_id, n), text in all_rungs.items() if n > current.get(puzzle_id, 0)]
        assert not any(text.encode() in response.content for text in higher), response.request.url
    # Every Rung the Guide port saw: each appended rung_change once (a Rung an ask opened is answered in those words),
    # and each Hint request that repeated a Rung already open, and nothing else (AD-3).
    log = stored(tmp_path, session_id)
    rung_changes = [e for e in log if isinstance(e, RungChangeEvent)]
    answered = [r.json()["hint_reply"] for r in responses if r.request.method == "POST" and r.json().get("hint_reply")]
    asked_open = sum(change.triggered_by == [i] and log[i].type == "hint_request"
                     for i in range(len(log)) for change in rung_changes)
    assert rung_changes and asked_open and any(reply["rung"] > 0 for reply in answered)
    assert len(phraser.phrased) == len(rung_changes) + sum(reply["rung"] > 0 for reply in answered) - asked_open
    assert_the_phraser_saw_only_whole_rungs(room, phraser)
