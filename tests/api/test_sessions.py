"""Stories 1.12 and 3.1: the session routes start a play-through, append events under one lock per session, replay the state with idle ticks and compute the result (AD-4, AD-13, AR-22).

Since 1.13 every session start appends the First-room welcome at `t_ms` 0, so each log here opens with one `opening_line`;
since 5.6 the state also reports the `Derived.fresh()` thresholds these starts carry;
4.2 checks that wiring hands the machine the Trickster window divided by `DEMO_TIMESCALE`.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient

from src.api.app import (
    FIRST_ROOM_WELCOME,
    IDLE_TICK_MS,
    OpenSessions,
    new_session_id,
    trigger_events,
)
from src.api.wiring import session_store
from src.config import Settings
from src.domain.schema import (
    ULID,
    Derived,
    Event,
    OpeningLineEvent,
    Room,
    RoomResult,
    RungChangeEvent,
    SessionStart,
    SessionState,
    Thresholds,
    TricksterCardEvent,
)
from src.domain.session import SessionStateMachine
from tests.api.test_app import ROOM_NOT_FOUND, UNKNOWN, make_app
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import (
    IX,
    PZ,
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)

UNKNOWN_SESSION = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SESSION_NOT_FOUND = {"error": {"code": "session_not_found", "message": ANY, "stage": None}}
INVALID_REQUEST = {"error": {"code": "invalid_request", "message": ANY, "stage": None}}


class Ticker:
    """A session clock the tests advance by hand."""

    def __init__(self) -> None:
        self.ms = 0

    def now_ms(self) -> int:
        return self.ms

    def advance(self, ms: int) -> None:
        self.ms += ms


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def client(tmp_path: Path, code_and_find_room: Room, four_lock_room: Room, ticker: Ticker) -> TestClient:
    return TestClient(make_app(tmp_path, code_and_find_room, four_lock_room, clock=ticker))


def start(client: TestClient, room: Room, **body: Any) -> str:
    response = client.post("/api/sessions", json={"room_id": room.id, **body})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def click(name: str) -> dict[str, Any]:
    return {"type": "click", "interactable_id": IX[name]}


def code(name: str, text: str) -> dict[str, Any]:
    return {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ[name], "code": text}}


def order(kind: str, name: str) -> dict[str, Any]:
    return {"type": "lock_input", "input": {"type": f"order_{kind}", "puzzle_id": PZ[name]}}


def use_on(item: str, target: str) -> dict[str, Any]:
    return {"type": "lock_input", "input": {"type": "use_on", "item": IX[item], "target": IX[target]}}


def post(client: TestClient, session_id: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/api/sessions/{session_id}/events", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def stored(tmp_path: Path, session_id: str) -> list[Event]:
    """The session's log as the JSON store under `rooms/sessions/` holds it."""
    try:
        return session_store(tmp_path / "rooms").read_all(session_id)
    except KeyError:
        return []


WELCOME = OpeningLineEvent(type="opening_line", kind="welcome", text=FIRST_ROOM_WELCOME, t_ms=0)
"""The event every session start appends first (1.13)."""
FRESH_THRESHOLDS = Thresholds(
    nudge_threshold_ms=90_000, nudge_threshold_base_ms=90_000, rung_spacing_ms=90_000, rung_spacing_base_ms=90_000, source="fresh"
)
"""What a `Derived.fresh()` start reports at `DEMO_TIMESCALE=1` (5.6)."""


def welcomed(room: Room) -> SessionStateMachine:
    """The machine a fresh start opens: the welcome, and the `Derived.fresh()` thresholds."""
    return SessionStateMachine(room, opening="welcome", thresholds=FRESH_THRESHOLDS)


# --- POST /sessions ------------------------------------------------------------


def test_a_session_starts_fresh_with_a_sess_id_and_the_initial_state(client: TestClient, code_and_find_room: Room):
    response = client.post("/api/sessions", json={"room_id": code_and_find_room.id})
    assert response.status_code == 200
    state = response.json()
    assert re.fullmatch(f"sess_{ULID}", state["id"])
    assert state == welcomed(code_and_find_room).replay(state["id"], [WELCOME]).model_dump(mode="json")
    assert state["room_id"] == code_and_find_room.id and state["active_puzzle_id"] == PZ["find_key"]
    assert (state["locks_open"], state["inventory"], state["cards"], state["disclosure"]) == ([], [], [], [])
    assert state["thresholds"] == FRESH_THRESHOLDS.model_dump()


def test_derived_fresh_and_an_explicit_block_start_the_same_state(client: TestClient, code_and_find_room: Room):
    assert set(SessionStart.model_fields) == {"room_id", "derived"}
    fresh = client.post("/api/sessions", json={"room_id": code_and_find_room.id}).json()
    explicit = client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": Derived.fresh().model_dump()})
    assert explicit.status_code == 200
    # The second session on the Room adds the earlier-builds Disclosure line (6.2); nothing else differs.
    assert {**fresh, "id": None, "disclosure": None} == {**explicit.json(), "id": None, "disclosure": None}
    assert fresh["id"] != explicit.json()["id"]


@pytest.mark.parametrize("derived", [
    {"sessions": 0, "persistence": 1.5, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}},
    {"sessions": -1, "persistence": 0, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}},
    {"sessions": 0, "persistence": 0, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {"code": 4}},
])
def test_a_derived_block_outside_its_bounds_answers_422_in_the_envelope_and_creates_no_session(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, derived: dict[str, Any]
):
    response = client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": derived})
    assert response.status_code == 422
    assert response.json() == INVALID_REQUEST
    assert "id" not in response.json() and not (tmp_path / "rooms" / "sessions").exists()


def test_an_unknown_room_answers_404_room_not_found(client: TestClient):
    response = client.post("/api/sessions", json={"room_id": UNKNOWN})
    assert response.status_code == 404 and response.json() == ROOM_NOT_FOUND


@pytest.mark.parametrize("body", [
    {"room_id": "{room_id}", "profile": "demo"},
    {"room_id": "{room_id}", "derived": None, "t_ms": 0},
    {"derived": None},
    {"room_id": "not a room id"},
])
def test_a_body_with_any_field_other_than_room_id_and_derived_answers_422(client: TestClient, code_and_find_room: Room, body: dict[str, Any]):
    body = {k: (v.format(room_id=code_and_find_room.id) if isinstance(v, str) else v) for k, v in body.items()}
    response = client.post("/api/sessions", json=body)
    assert response.status_code == 422 and response.json() == INVALID_REQUEST


# --- POST /sessions/<id>/events ------------------------------------------------


def test_a_click_and_a_lock_input_are_stamped_appended_and_applied(client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker):
    ticker.advance(1_000)
    session_id = start(client, code_and_find_room)
    ticker.advance(2_500)
    state = post(client, session_id, click("key"))
    assert state["locks_open"] == [PZ["find_key"]] and state["inventory"] == []  # found: no use_on in this room needs the key
    ticker.advance(700)
    state = post(client, session_id, code("clock_code", "nope"))
    assert state["wrong_attempts"][PZ["clock_code"]] == 1
    log = stored(tmp_path, session_id)
    assert [(event.type, event.t_ms) for event in log] == [("opening_line", 0), ("click", 2_500), ("lock_input", 3_200)]
    assert state == welcomed(code_and_find_room).replay(session_id, log).model_dump(mode="json")


@pytest.mark.parametrize("body", [
    {"type": "click", "interactable_id": IX["key"], "t_ms": 12},
    {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["clock_code"], "code": "415"}, "t_ms": 0},
    {"type": "hint_request", "puzzle_id": None, "t_ms": 5},
    {"type": "idle_tick"},
    {"type": "idle_tick", "t_ms": 5000},
    {"type": "opening_line", "kind": "welcome", "text": "Welcome."},
    {"type": "trickster_card", "edit_id": None, "edit": None, "puzzle_id": None, "accepted": False, "reason": None, "room_revision": 0},
    {"type": "rung_change", "puzzle_id": PZ["find_key"], "rung": 1, "triggered_by": [], "phrased": False, "phrasing_ms": None, "text": "x"},
    {"type": "click"},
    {"interactable_id": IX["key"]},
])
def test_a_client_timestamp_or_a_server_event_type_answers_422_and_appends_nothing(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, body: dict[str, Any]
):
    session_id = start(client, code_and_find_room)
    post(client, session_id, click("rug"))
    response = client.post(f"/api/sessions/{session_id}/events", json=body)
    assert response.status_code == 422 and response.json() == INVALID_REQUEST
    assert [event.type for event in stored(tmp_path, session_id)] == ["opening_line", "click"]


def test_an_unknown_session_answers_404_on_every_session_route(client: TestClient, tmp_path: Path):
    responses = [
        client.post(f"/api/sessions/{UNKNOWN_SESSION}/events", json=click("key")),
        client.get(f"/api/sessions/{UNKNOWN_SESSION}"),
        client.get(f"/api/sessions/{UNKNOWN_SESSION}/result"),
    ]
    assert [r.status_code for r in responses] == [404] * 3
    assert all(r.json() == SESSION_NOT_FOUND for r in responses)
    assert stored(tmp_path, UNKNOWN_SESSION) == []


# --- One lock per session id -------------------------------------------------------


def test_twenty_concurrent_events_all_land_in_append_order_with_strictly_increasing_t_ms(
    tmp_path: Path, code_and_find_room: Room, ticker: Ticker
):
    app = make_app(tmp_path, code_and_find_room, clock=ticker)
    session_id = start(TestClient(app), code_and_find_room)
    body = code("clock_code", "wrong")

    def one(n: int) -> dict[str, Any]:
        return TestClient(app).post(f"/api/sessions/{session_id}/events", json=body).json()

    with ThreadPoolExecutor(max_workers=20) as pool:
        replies = list(pool.map(one, range(20)))

    log = stored(tmp_path, session_id)
    # The third Wrong attempt opens the nudge (3.1): its `rung_change` lands right after it, with its `t_ms`.
    posted = [event for event in log if event.type != "rung_change"]
    assert log[0] == WELCOME and len(posted) == 21 and all(event.type == "lock_input" for event in posted[1:])
    assert [event.type for event in log].index("rung_change") == 4 and len(log) == 22 and log[4].t_ms == log[3].t_ms
    stamps = [event.t_ms for event in posted]
    assert stamps == sorted(stamps) and len(set(stamps)) == 21
    # Each reply carries the state that includes its own event and every earlier one.
    assert sorted(reply["wrong_attempts"][PZ["clock_code"]] for reply in replies) == list(range(1, 21))
    final = TestClient(app).get(f"/api/sessions/{session_id}").json()
    assert final["wrong_attempts"][PZ["clock_code"]] == 20
    replayed = welcomed(code_and_find_room).replay(session_id, log)
    assert final == replayed.model_copy(update={"trigger_events": trigger_events(replayed, log)}).model_dump(mode="json")


def test_a_different_session_id_never_waits_on_this_sessions_lock(code_and_find_room: Room):
    sessions = OpenSessions()
    machine = SessionStateMachine(code_and_find_room)
    a = sessions.open(new_session_id(), machine, 0, [], Derived.fresh())
    b = sessions.open(new_session_id(), machine, 0, [], Derived.fresh())
    with a.lock:
        assert b.lock.acquire(timeout=1)
        b.lock.release()
        assert not a.lock.acquire(blocking=False)
    assert a.lock.acquire(blocking=False)


def test_a_concurrent_read_that_appends_an_idle_tick_runs_under_the_same_lock(
    tmp_path: Path, code_and_find_room: Room, ticker: Ticker
):
    app = make_app(tmp_path, code_and_find_room, clock=ticker)
    session_id = start(TestClient(app), code_and_find_room)
    ticker.advance(IDLE_TICK_MS)
    calls = [lambda: TestClient(app).get(f"/api/sessions/{session_id}").json()] * 5
    calls += [lambda: TestClient(app).post(f"/api/sessions/{session_id}/events", json=click("rug")).json()] * 5
    with ThreadPoolExecutor(max_workers=10) as pool:
        replies = list(pool.map(lambda call: call(), calls))
    log = stored(tmp_path, session_id)
    # A read that wins the lock first appends the one idle tick; a click that wins it first resets the
    # idle window, so no read does. Either way nothing is lost or interleaved and at most one tick lands.
    types = [event.type for event in log]
    assert types.count("click") == 5 and types.count("idle_tick") <= 1 and len(types) == 6 + types.count("idle_tick")
    stamps = [event.t_ms for event in log]
    assert stamps == sorted(stamps) and len(set(stamps)) == len(log)
    assert all(SessionState.model_validate(reply) for reply in replies)


# --- GET /sessions/<id> ---------------------------------------------------------------


def test_the_state_is_replayed_from_the_log_with_the_fields_this_story_declares(client: TestClient, code_and_find_room: Room):
    session_id = start(client, code_and_find_room)
    post(client, session_id, click("key"))
    post(client, session_id, code("clock_code", "415"))
    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    state = response.json()
    assert state["room_id"] == code_and_find_room.id
    assert state["locks_open"] == [PZ["find_key"], PZ["clock_code"]] and state["active_puzzle_id"] == PZ["find_lantern"]
    assert (state["cards"], state["disclosure"], state["thresholds"]) == ([], [], FRESH_THRESHOLDS.model_dump())
    assert not {"events", "log", "edit", "edits", "solution"} & json_keys(state)


def test_a_fresh_sessions_active_puzzle_is_the_earliest_available_unsolved_one(client: TestClient, four_lock_room: Room):
    session_id = start(client, four_lock_room)
    assert client.get(f"/api/sessions/{session_id}").json()["active_puzzle_id"] == PZ["find_key"]


def test_an_idle_tick_is_appended_at_5000_ms_since_the_last_event_and_not_at_4999(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker
):
    session_id = start(client, code_and_find_room)
    ticker.advance(1_000)
    post(client, session_id, click("rug"))
    ticker.advance(IDLE_TICK_MS - 1)
    assert client.get(f"/api/sessions/{session_id}").status_code == 200
    assert [event.type for event in stored(tmp_path, session_id)] == ["opening_line", "click"]
    ticker.advance(1)
    state = client.get(f"/api/sessions/{session_id}").json()
    assert [(event.type, event.t_ms) for event in stored(tmp_path, session_id)[1:]] == [("click", 1_000), ("idle_tick", 6_000)]
    assert state["locks_open"] == [] and state["inventory"] == []
    # The tick is now the last event, so the next read within 5000 ms appends nothing.
    ticker.advance(IDLE_TICK_MS - 1)
    client.get(f"/api/sessions/{session_id}")
    assert len(stored(tmp_path, session_id)) == 3
    ticker.advance(1)
    client.get(f"/api/sessions/{session_id}")
    assert [event.t_ms for event in stored(tmp_path, session_id)] == [0, 1_000, 6_000, 11_000]


def test_an_idle_tick_on_a_fresh_log_counts_from_the_session_start(client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker):
    ticker.advance(40_000)
    session_id = start(client, code_and_find_room)
    ticker.advance(IDLE_TICK_MS - 1)
    client.get(f"/api/sessions/{session_id}")
    assert stored(tmp_path, session_id) == [WELCOME]
    ticker.advance(1)
    client.get(f"/api/sessions/{session_id}")
    assert [(event.type, event.t_ms) for event in stored(tmp_path, session_id)] == [("opening_line", 0), ("idle_tick", IDLE_TICK_MS)]


# --- GET /sessions/<id>/result ---------------------------------------------------------


def play_to_the_exit(client: TestClient, session_id: str, ticker: Ticker) -> None:
    for body in (click("key"), code("clock_code", "nope"), code("clock_code", "415"), click("lantern"), code("door_code", "7342")):
        ticker.advance(10_000)
        post(client, session_id, body)


def test_the_result_is_computed_from_the_log_once_the_exit_has_opened(client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker):
    session_id = start(client, code_and_find_room)
    play_to_the_exit(client, session_id, ticker)
    response = client.get(f"/api/sessions/{session_id}/result")
    assert response.status_code == 200
    result = RoomResult.model_validate(response.json())
    log = stored(tmp_path, session_id)
    assert result == SessionStateMachine(code_and_find_room).result(session_id, log, demo=False)
    assert (result.room_id, result.demo, result.elapsed_ms, result.wrong_attempts) == (code_and_find_room.id, False, 50_000, 1)
    assert all(puzzle.solved for puzzle in result.puzzles)


@pytest.mark.parametrize("env, demo", [({}, False), ({"DEMO_TIMESCALE": "1"}, False), ({"DEMO_TIMESCALE": "2"}, True), ({"DEMO_TIMESCALE": "6"}, True)])
def test_demo_is_true_exactly_when_the_timescale_is_above_1(tmp_path: Path, code_and_find_room: Room, env: dict[str, str], demo: bool):
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, code_and_find_room, settings=Settings.from_env(env), clock=ticker))
    session_id = start(client, code_and_find_room)
    play_to_the_exit(client, session_id, ticker)
    assert client.get(f"/api/sessions/{session_id}/result").json()["demo"] is demo


# --- One JSON log line per appended event (AR-22) ----------------------------------


def test_every_appended_event_logs_one_json_line_with_session_id_type_and_duration(
    client: TestClient, code_and_find_room: Room, ticker: Ticker, caplog: pytest.LogCaptureFixture
):
    caplog.set_level("INFO", logger="keyframe.sessions")
    session_id = start(client, code_and_find_room)
    ticker.advance(1_000)
    post(client, session_id, click("key"))
    ticker.advance(1_000)
    post(client, session_id, code("clock_code", "415"))
    ticker.advance(IDLE_TICK_MS)
    client.get(f"/api/sessions/{session_id}")
    client.get(f"/api/sessions/{session_id}")
    client.get(f"/api/sessions/{session_id}/result")
    lines = [json.loads(record.getMessage()) for record in caplog.records if record.name == "keyframe.sessions"]
    assert lines == [
        {"session_id": session_id, "event": "opening_line", "duration_ms": 0},
        {"session_id": session_id, "event": "click", "duration_ms": 0},
        {"session_id": session_id, "event": "lock_input", "duration_ms": 0},
        {"session_id": session_id, "event": "idle_tick", "duration_ms": 0},
    ]
    assert all(record.getMessage().count("\n") == 0 for record in caplog.records)


# --- No solution and no sentinel in any session response -------------------------------


def _play_every_session_route(client: TestClient, room: Room) -> list[Any]:
    """Every session route's response: start, each event kind, the refusals, the state and the result."""
    responses = [client.post("/api/sessions", json={"room_id": room.id})]
    session_id = responses[0].json()["id"]
    bodies = [
        click("key"), click("clock"), code("clock_code", "415"), code("clock_code", "wrong"), order("start", "shelf_order"),
        click("candle"), order("stop", "shelf_order"), use_on("key", "chest"), {"type": "hint_request"},
        {"type": "click", "interactable_id": IX["key"], "t_ms": 1}, {"type": "idle_tick"},
    ]
    responses += [client.post(f"/api/sessions/{session_id}/events", json=body) for body in bodies]
    responses += [client.get(f"/api/sessions/{session_id}"), client.get(f"/api/sessions/{session_id}/result")]
    responses += [client.post("/api/sessions", json={"room_id": UNKNOWN}), client.get(f"/api/sessions/{UNKNOWN_SESSION}")]
    return responses


def test_no_session_response_carries_a_solution_key_or_a_sentinel(tmp_path: Path, four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    responses = _play_every_session_route(TestClient(make_app(tmp_path, room, clock=Ticker())), room)
    assert [r.status_code for r in responses] == [200, *[200] * 9, 422, 422, 200, 200, 404, 404]
    sentinels = [SENTINEL_CODE, json.dumps(SENTINEL_ORDER)[1:-1], *SENTINEL_PAIR, SENTINEL_FIND, *SENTINEL_IX]
    for response in responses:
        assert b"solution" not in response.content
        assert all(sentinel.encode() not in response.content for sentinel in sentinels)
        assert "solution" not in json_keys(response.json())


# --- Rung changes appended live (Story 3.1) ------------------------------------------------

DEMO_6 = Thresholds(
    nudge_threshold_ms=15_000, nudge_threshold_base_ms=90_000, rung_spacing_ms=15_000, rung_spacing_base_ms=90_000, source="fresh"
)
"""What a `Derived.fresh()` start reports at `DEMO_TIMESCALE=6`."""


def demo_client(tmp_path: Path, room: Room, ticker: Ticker) -> TestClient:
    return TestClient(make_app(tmp_path, room, settings=Settings.from_env({"DEMO_TIMESCALE": "6"}), clock=ticker))


def stored_rungs(log: list[Event]) -> list[RungChangeEvent]:
    return [event for event in log if isinstance(event, RungChangeEvent)]


def test_at_timescale_6_a_wrong_code_every_2000_ms_appends_rungs_1_2_and_3_by_38000_ms(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = demo_client(tmp_path, code_and_find_room, ticker)
    session_id = start(client, code_and_find_room)
    while ticker.ms < 40_000:
        ticker.advance(2_000)
        state = post(client, session_id, code("clock_code", "000"))
    log = stored(tmp_path, session_id)
    rungs = stored_rungs(log)
    assert [(r.puzzle_id, r.rung, r.t_ms) for r in rungs] == [(PZ["clock_code"], 1, 6_000), (PZ["clock_code"], 2, 22_000),
                                                              (PZ["clock_code"], 3, 38_000)]
    # `t_ms` stamps are unscaled, and each Rung lands right after the Wrong attempt that triggered it, with its `t_ms`.
    assert [event.t_ms for event in log if event.type == "lock_input"] == list(range(2_000, 40_001, 2_000))
    for r in rungs:
        trigger = log.index(r) - 1
        assert r.triggered_by[-1] == trigger and log[trigger].t_ms == r.t_ms and len(r.triggered_by) in (3, 4)
    assert state["rung_changes"] == [r.model_dump(mode="json") for r in rungs]
    assert state["current_rung"][PZ["clock_code"]] == 3 and state["rungs_used"] == 3


def test_at_timescale_6_with_the_2000_ms_poll_each_idle_rung_lands_on_the_first_tick_past_its_condition(
    tmp_path: Path, code_and_find_room: Room
):
    ticker = Ticker()
    client = demo_client(tmp_path, code_and_find_room, ticker)
    session_id = start(client, code_and_find_room)
    while len(stored_rungs(stored(tmp_path, session_id))) < 3 and ticker.ms < 120_000:
        ticker.advance(2_000)
        client.get(f"/api/sessions/{session_id}")
    log = stored(tmp_path, session_id)
    # Nominally 15, 30 and 45 s (FR-24); a tick needs 5000 ms since the last event and the poll comes every 2000 ms,
    # so each Rung lands on the first tick at or past its condition: these are the real times.
    assert [event.t_ms for event in log if event.type == "idle_tick"] == list(range(6_000, 54_001, 6_000))
    rungs = stored_rungs(log)
    assert [(r.puzzle_id, r.rung, r.t_ms) for r in rungs] == [(PZ["find_key"], 1, 18_000), (PZ["find_key"], 2, 36_000),
                                                              (PZ["find_key"], 3, 54_000)]
    for r in rungs:
        tick = log.index(r) - 1
        assert log[tick].type == "idle_tick" and log[tick].t_ms == r.t_ms and r.triggered_by[-1] == tick
    # Reads within the tick gap replay the log and append nothing: no Rung change is ever duplicated.
    for _ in range(2):
        ticker.advance(2_000)
        state = client.get(f"/api/sessions/{session_id}").json()
    assert stored(tmp_path, session_id) == log
    replayed = SessionStateMachine(code_and_find_room, opening="welcome", thresholds=DEMO_6).replay(session_id, log)
    # The demo Disclosure line (AD-15) and the events the Rungs name are served on top.
    assert {**state, "disclosure": []} == replayed.model_copy(update={"trigger_events": trigger_events(replayed, log)}).model_dump(mode="json")
    assert state["rung_changes"] == [r.model_dump(mode="json") for r in rungs]


@pytest.mark.parametrize("persistence, threshold", [(1, 135_000), (-1, 60_000)])
def test_the_session_starts_derived_block_sets_the_idle_nudge_threshold(
    tmp_path: Path, code_and_find_room: Room, persistence: float, threshold: int
):
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, code_and_find_room, clock=ticker))
    derived = Derived(sessions=2, persistence=persistence, time_to_first_hint_s=None, mean_rung_per_lock_type={})
    session_id = start(client, code_and_find_room, derived=derived.model_dump())
    while ticker.ms < threshold - IDLE_TICK_MS:
        ticker.advance(IDLE_TICK_MS)
        client.get(f"/api/sessions/{session_id}")
    assert stored_rungs(stored(tmp_path, session_id)) == []
    ticker.advance(IDLE_TICK_MS)
    state = client.get(f"/api/sessions/{session_id}").json()
    assert [(r.rung, r.t_ms) for r in stored_rungs(stored(tmp_path, session_id))] == [(1, threshold)]
    assert state["current_rung"][PZ["find_key"]] == 1


# --- The Trickster window from the session clock (Story 4.2) ---------------------------------


def test_at_timescale_6_wiring_opens_a_trickster_window_30_s_after_start_and_after_the_last_card(
    tmp_path: Path, four_lock_room: Room, ticker: Ticker
):
    client = demo_client(tmp_path, four_lock_room, ticker)
    session_id = start(client, four_lock_room)
    ticker.advance(29_999)
    assert post(client, session_id, code("clock_code", "415"))["trickster_window"] == {"state": "closed", "index": None}
    ticker.advance(1)
    assert post(client, session_id, click("key"))["trickster_window"] == {"state": "open", "index": 0}  # 180000 / 6
    skipped = TricksterCardEvent(type="trickster_card", edit_id=None, edit=None, puzzle_id=None, accepted=False,
                                 reason="provider_unavailable", room_revision=0, t_ms=31_000)
    session_store(tmp_path / "rooms").append(session_id, skipped)  # the 4.4 route's skipped card, written directly
    ticker.advance(30_999)
    state = post(client, session_id, use_on("key", "chest"))
    assert state["trickster_calls"] == 1 and state["trickster_window"] == {"state": "closed", "index": None}
    ticker.advance(1)
    post(client, session_id, order("start", "shelf_order"))
    for name in ("candle", "lantern", "hourglass"):
        state = post(client, session_id, click(name))
    assert PZ["shelf_order"] in state["locks_open"] and state["trickster_window"] == {"state": "open", "index": 1}
    log = [event for event in stored(tmp_path, session_id) if not isinstance(event, RungChangeEvent)]
    assert [event.t_ms for event in log] == [0, 29_999, 30_000, 31_000, 60_999, 61_000, 61_001, 61_002, 61_003]
