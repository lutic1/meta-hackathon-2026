"""A session survives a server restart: a second app over the same `SessionStore` reopens it from the stored log and its header (AD-4, AD-9, FR-11).

Each test starts a session on one app and plays it, then builds a second app
over the same `rooms/` directory (Local mode) or the same Dicts and Volume
(Hosted mode) with a fresh session clock, as a restarted process would have.
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import IDLE_TICK_MS
from src.api.meta import EARLIER_BUILD_LINE
from src.domain.schema import Derived, Room
from tests.api.hosted import hosted_handles, make_hosted_app
from tests.api.test_app import make_app
from tests.api.test_sessions import (
    UNKNOWN_SESSION,
    Ticker,
    click,
    code,
    post,
    start,
    stored,
)


def replayed(client: TestClient, session_id: str) -> dict[str, Any]:
    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200, response.text
    return response.json()


def play_and_restart(before: FastAPI, after: FastAPI, room: Room, **body: Any) -> tuple[TestClient, str, dict[str, Any]]:
    """Start a session on `before`, play two events 3 s apart, and return a client on `after` with the last state served."""
    ticker = before.state.ticker
    first = TestClient(before)
    session_id = start(first, room, **body)
    ticker.advance(3_000)
    post(first, session_id, click("key"))
    ticker.advance(3_000)
    last = post(first, session_id, code("clock_code", "nope"))
    return TestClient(after), session_id, last


def local_app(tmp_path: Path, room: Room) -> FastAPI:
    ticker = Ticker()
    app = make_app(tmp_path, room, clock=ticker, spawn=lambda task: task())
    app.state.ticker = ticker
    return app


def test_a_local_session_is_replayed_by_a_restarted_app_and_its_clock_resumes_after_the_last_event(
    tmp_path: Path, code_and_find_room: Room
):
    before, after = local_app(tmp_path, code_and_find_room), local_app(tmp_path, code_and_find_room)
    client, session_id, last = play_and_restart(before, after, code_and_find_room)
    assert replayed(client, session_id) == last
    after.state.ticker.advance(1_000)
    state = post(client, session_id, click("lantern"))
    assert state["id"] == session_id
    assert [event.t_ms for event in stored(tmp_path, session_id)] == [0, 3_000, 6_000, 7_000]


def test_a_restarted_app_counts_the_idle_tick_from_its_own_start_not_across_the_downtime(
    tmp_path: Path, code_and_find_room: Room
):
    before, after = local_app(tmp_path, code_and_find_room), local_app(tmp_path, code_and_find_room)
    after.state.ticker.advance(600_000)  # the new process's clock reads far past the session's last event
    client, session_id, last = play_and_restart(before, after, code_and_find_room)
    assert replayed(client, session_id) == last
    after.state.ticker.advance(IDLE_TICK_MS)
    replayed(client, session_id)
    assert [(event.type, event.t_ms) for event in stored(tmp_path, session_id)][-1] == ("idle_tick", 6_000 + IDLE_TICK_MS)


def test_a_greeted_session_keeps_its_greeting_and_its_derived_thresholds_after_a_restart(
    tmp_path: Path, code_and_find_room: Room
):
    derived = Derived(sessions=2, persistence=1, time_to_first_hint_s=None, mean_rung_per_lock_type={})
    before, after = local_app(tmp_path, code_and_find_room), local_app(tmp_path, code_and_find_room)
    client, session_id, last = play_and_restart(before, after, code_and_find_room, derived=derived.model_dump())
    state = replayed(client, session_id)
    assert state == last
    assert state["opening_line"]["kind"] == "greeting" and state["thresholds"]["source"] == "derived"
    assert state["thresholds"]["nudge_threshold_base_ms"] == 135_000


def test_every_session_route_answers_for_a_session_a_restarted_app_never_opened(tmp_path: Path, code_and_find_room: Room):
    before, after = local_app(tmp_path, code_and_find_room), local_app(tmp_path, code_and_find_room)
    client, session_id, _ = play_and_restart(before, after, code_and_find_room)
    assert client.get(f"/api/sessions/{session_id}/room").status_code == 200
    assert client.get(f"/api/sessions/{session_id}/result").status_code == 200
    assert client.post(f"/api/sessions/{session_id}/trickster").status_code == 200
    assert client.get(f"/api/sessions/{UNKNOWN_SESSION}").status_code == 404


def test_a_session_started_before_a_restart_is_an_earlier_session_for_the_disclosure_list(
    tmp_path: Path, code_and_find_room: Room
):
    before, after = local_app(tmp_path, code_and_find_room), local_app(tmp_path, code_and_find_room)
    client, session_id, last = play_and_restart(before, after, code_and_find_room)
    earlier = EARLIER_BUILD_LINE.format(date=code_and_find_room.created.strftime("%a %b %-d"))
    assert earlier not in last["disclosure"]
    assert earlier in replayed(client, start(client, code_and_find_room))["disclosure"]  # before the old one is reopened
    assert replayed(client, session_id)["disclosure"] == last["disclosure"]


def test_a_hosted_session_is_replayed_by_a_restarted_container(tmp_path: Path, code_and_find_room: Room):
    handles = hosted_handles(tmp_path)
    tickers = Ticker(), Ticker()
    apps = [make_hosted_app(tmp_path, handles, *rooms, clock=ticker) for rooms, ticker in zip(([code_and_find_room], []), tickers, strict=True)]
    for app, ticker in zip(apps, tickers, strict=True):
        app.state.ticker = ticker
    client, session_id, last = play_and_restart(*apps, code_and_find_room)
    assert replayed(client, session_id) == last
    tickers[1].advance(1_000)
    post(client, session_id, click("lantern"))
    assert [event["t_ms"] for event in handles.sessions[session_id]] == [0, 3_000, 6_000, 7_000]
