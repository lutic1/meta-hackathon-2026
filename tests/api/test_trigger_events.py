"""Story 3.5: the session state serves the type and `t_ms` of each event a Rung change names, for the Triggers panel
(FR-16, AD-3, AD-10).

The panel's cause is read off these: "Idle {s} s" is the triggering `idle_tick`'s `t_ms` minus the `t_ms` of the
other event `triggered_by` names (or 0), "3 wrong attempts" names the lock inputs, and "Loosen card" names a
Trickster Card. Every `t_ms` is the session clock's, which the Demo timescale never scales.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import trigger_events
from src.domain.schema import Room, ValidatorResult
from tests.api.test_app import make_app
from tests.api.test_sessions import (
    FRESH_THRESHOLDS,
    WELCOME,
    Ticker,
    code,
    demo_client,
    post,
    start,
    stored,
    welcomed,
)
from tests.domain.test_edits import card, loosen
from tests.fixtures.rooms import PZ


def named(state: dict, change: dict) -> list[dict]:
    return [state["trigger_events"][str(position)] for position in change["triggered_by"]]


def test_a_stall_nudge_at_timescale_6_on_a_fresh_profile_names_its_tick_at_real_seconds(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = demo_client(tmp_path, code_and_find_room, ticker)
    session_id = start(client, code_and_find_room)
    state = client.get(f"/api/sessions/{session_id}").json()
    assert state["thresholds"]["nudge_threshold_ms"] == 15_000 and state["thresholds"]["source"] == "fresh"
    while not state["rung_changes"]:
        ticker.advance(2_000)
        state = client.get(f"/api/sessions/{session_id}").json()
    change = state["rung_changes"][0]
    # Idle counts from the session start (the welcome is no activity): the tick alone, at the real 18 s on the clock.
    assert named(state, change) == [{"type": "idle_tick", "t_ms": ticker.ms}]
    idle_ms = named(state, change)[-1]["t_ms"] - 0
    assert 15_000 <= idle_ms == ticker.ms == 18_000  # never 15 s x 6, never 18 s / 6
    # A reload serves the same events: the panel's rows never move.
    ticker.advance(1_000)
    assert client.get(f"/api/sessions/{session_id}").json()["trigger_events"] == state["trigger_events"]


def test_a_stall_after_activity_names_the_event_idle_counts_from_and_the_tick(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, code_and_find_room, clock=ticker))
    session_id = start(client, code_and_find_room)
    ticker.advance(4_000)
    post(client, session_id, {"type": "hint_request"})
    state: dict = {"rung_changes": []}
    while not state["rung_changes"]:
        ticker.advance(5_000)
        state = client.get(f"/api/sessions/{session_id}").json()
    anchor, tick = named(state, state["rung_changes"][0])
    assert anchor == {"type": "hint_request", "t_ms": 4_000} and tick["type"] == "idle_tick"
    assert tick["t_ms"] - anchor["t_ms"] >= FRESH_THRESHOLDS.nudge_threshold_ms


def test_three_wrong_codes_name_three_lock_inputs(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, code_and_find_room, clock=ticker))
    session_id = start(client, code_and_find_room)
    for _ in range(3):
        ticker.advance(1_000)
        state = post(client, session_id, code("clock_code", "000"))
    change = state["rung_changes"][-1]
    assert [event["type"] for event in named(state, change)] == ["lock_input"] * 3
    # Only the named events are served, with their type and t_ms and nothing of their payload (AD-3).
    assert set(state["trigger_events"]) == {str(position) for position in change["triggered_by"]}
    assert all(set(event) == {"type", "t_ms"} for event in state["trigger_events"].values())
    log = stored(tmp_path, session_id)
    assert all(log[position].type == "lock_input" for position in change["triggered_by"])


def test_a_loosen_card_names_the_trickster_card_it_was_triggered_by(code_and_find_room: Room):
    edit = loosen(1, "clock_code", "nudge")
    log = [WELCOME, card(edit, ValidatorResult(ok=True, reasons=[]), 1, 5_000)]
    state = welcomed(code_and_find_room).replay("sess_01ARZ3NDEKTSV4RRFFQ69G5FAV", log)
    (change,) = state.rung_changes
    assert (change.puzzle_id, change.rung, change.triggered_by) == (PZ["clock_code"], 1, [1])
    events = trigger_events(state, log)
    assert {i: (event.type, event.t_ms) for i, event in events.items()} == {1: ("trickster_card", 5_000)}


def test_a_state_with_no_rung_change_names_nothing_and_replay_never_writes_the_field(code_and_find_room: Room):
    state = welcomed(code_and_find_room).replay("sess_01ARZ3NDEKTSV4RRFFQ69G5FAV", [WELCOME])
    assert trigger_events(state, [WELCOME]) == {} and state.trigger_events == {}
