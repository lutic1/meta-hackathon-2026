"""Story mode (owner decision Oct 29): the treasure chest's hints, server-enforced (AD-4, AD-13, AD-14).

Under the default `HINT_POLICY=chest` a Session holds `HINT_CAP` (2) hints:
each ask opens the Active puzzle's next Rung at once, an ask with none left is
refused 409 `hint_cap_reached` before anything is appended, idle time opens
nothing, and the Trickster's `decoy` and `loosen` are refused. A session
stored before story mode reopens under the ladder it was played with.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.app import CHEST_NO_HINT_LINE
from src.api.wiring import session_store
from src.config import Settings
from src.domain.schema import Room, RungChangeEvent
from src.domain.session import SessionHeader
from tests.api.test_app import make_app
from tests.api.test_hints import HINT, RecordingPhraser, puzzle, worded
from tests.api.test_sessions import Ticker, click, post, start, stored
from tests.api.test_trickster_route import open_window, proposals_dir, trickster
from tests.fixtures.rooms import PZ

CAP_REACHED = {"error": {"code": "hint_cap_reached", "message": "The chest is empty.", "stage": None}}


def chest_client(tmp_path: Path, room: Room, ticker: Ticker, **env: str) -> TestClient:
    settings = Settings.from_env({"GUIDE": "verbatim", "DEMO_TRICKSTER": "scripted", **env})
    return TestClient(make_app(tmp_path, room, settings=settings, clock=ticker, phraser=RecordingPhraser(),
                               proposals_dir=proposals_dir(tmp_path)))


def rung_changes(tmp_path: Path, session_id: str) -> list[RungChangeEvent]:
    return [event for event in stored(tmp_path, session_id) if isinstance(event, RungChangeEvent)]


def test_the_settings_default_to_the_chest_with_2_hints_and_read_both_keys():
    default, set_ = Settings.from_env({}), Settings.from_env({"HINT_POLICY": "ladder", "HINT_CAP": "3"})
    assert (default.hint_policy, default.hint_cap) == ("chest", 2)
    assert (set_.hint_policy, set_.hint_cap) == ("ladder", 3)
    with pytest.raises(ValidationError):
        Settings.from_env({"HINT_POLICY": "free"})


def test_two_asks_open_the_nudge_then_the_direction_at_once_and_a_third_is_refused_with_nothing_appended(
    tmp_path: Path, code_and_find_room: Room
):
    ticker = Ticker()
    client = chest_client(tmp_path, code_and_find_room, ticker)
    session_id = start(client, code_and_find_room)
    assert client.get(f"/api/sessions/{session_id}").json()["hints_left"] == 2
    rungs = puzzle(code_and_find_room, "find_key").rungs
    ticker.advance(1_000)
    state = post(client, session_id, HINT)
    assert state["hints_left"] == 1
    assert state["hint_reply"] == {
        "puzzle_id": PZ["find_key"], "rung": 1, "text": worded(rungs.nudge), "next_hint_ms": 0, "hints_left": 1,
    }
    ticker.advance(1_000)  # well inside the Rung spacing: an asked Rung no longer waits for it
    state = post(client, session_id, HINT)
    assert state["hint_reply"] == {
        "puzzle_id": PZ["find_key"], "rung": 2, "text": worded(rungs.direction), "next_hint_ms": None, "hints_left": 0,
    }
    log = stored(tmp_path, session_id)
    ticker.advance(1_000)
    response = client.post(f"/api/sessions/{session_id}/events", json=HINT)
    assert response.status_code == 409 and response.json() == CAP_REACHED
    assert stored(tmp_path, session_id) == log
    assert client.get(f"/api/sessions/{session_id}").json()["hints_left"] == 0


def test_the_cap_holds_for_the_whole_session_across_puzzles(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = chest_client(tmp_path, code_and_find_room, ticker)
    session_id = start(client, code_and_find_room)
    for body in (HINT, click("key"), HINT):
        ticker.advance(1_000)
        state = post(client, session_id, body)
    assert state["hint_reply"]["puzzle_id"] == PZ["clock_code"] and state["hint_reply"]["rung"] == 1
    assert state["hints_left"] == 0
    assert client.post(f"/api/sessions/{session_id}/events", json=HINT).json() == CAP_REACHED


def test_an_ask_once_the_near_answer_is_open_answers_the_no_hint_line_and_spends_nothing(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = chest_client(tmp_path, code_and_find_room, ticker, HINT_CAP="4")
    session_id = start(client, code_and_find_room)
    for _ in range(3):
        ticker.advance(1_000)
        post(client, session_id, HINT)
    ticker.advance(1_000)
    state = post(client, session_id, HINT)
    assert state["hint_reply"] == {
        "puzzle_id": PZ["find_key"], "rung": 0, "text": CHEST_NO_HINT_LINE, "next_hint_ms": None, "hints_left": 1,
    }
    assert CHEST_NO_HINT_LINE == "A fair ask. That one is all I had for this riddle; look once more."
    assert len(rung_changes(tmp_path, session_id)) == 3


def test_idle_time_and_wrong_codes_open_no_rung_under_the_chest(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = chest_client(tmp_path, code_and_find_room, ticker)
    session_id = start(client, code_and_find_room)
    for _ in range(5):
        ticker.advance(60_000)
        post(client, session_id, {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["clock_code"], "code": "000"}})
        ticker.advance(60_000)
        client.get(f"/api/sessions/{session_id}")
    log = stored(tmp_path, session_id)
    assert any(event.type == "idle_tick" for event in log)  # still appended: the Trickster window reads them
    assert rung_changes(tmp_path, session_id) == []


def test_the_header_records_the_policy_and_cap_and_an_old_header_reopens_under_the_ladder(tmp_path: Path, code_and_find_room: Room):
    ticker = Ticker()
    client = chest_client(tmp_path, code_and_find_room, ticker, HINT_CAP="3")
    session_id = start(client, code_and_find_room)
    sessions = session_store(tmp_path / "rooms")
    header = sessions.read_header(session_id)
    assert (header.hint_policy, header.hint_cap) == ("chest", 3)
    # A header written before story mode has neither key: a new process reopens it under the ladder.
    old = {k: v for k, v in json.loads(header.model_dump_json()).items() if k not in {"hint_policy", "hint_cap"}}
    sessions.put_header(session_id, SessionHeader.model_validate(old))
    reopened = TestClient(make_app(tmp_path, code_and_find_room, settings=Settings.from_env({"GUIDE": "verbatim"}),
                                   clock=ticker, phraser=RecordingPhraser()))
    assert reopened.get(f"/api/sessions/{session_id}").json()["hints_left"] == 2  # the ladder's default cap
    ticker.advance(100_000)
    reopened.get(f"/api/sessions/{session_id}")  # past the 90 s nudge threshold: the ladder opens the nudge on idle
    assert [(c.puzzle_id, c.rung) for c in rung_changes(tmp_path, session_id)] == [(PZ["find_key"], 1)]


def test_the_trickster_decoy_is_refused_under_the_chest_with_its_fixed_reason(tmp_path: Path, four_lock_room: Room):
    ticker = Ticker()
    client = chest_client(tmp_path, four_lock_room, ticker)
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    (card,) = trickster(client, session_id)["cards"]
    assert (card["accepted"], card["edit_type"], card["reason"], card["message"]) == (
        False, "decoy", "edit_bounds", "Evidence is hidden until a lock opens."
    )
