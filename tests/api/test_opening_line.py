"""Story 1.13: every session start appends the fixed First-room welcome once, worded in one place on the server (FR-21, AD-4, AD-5).

Since 5.6 a Local start with `sessions` >= 1 is greeted instead (tests/api/test_greeting_path.py), so the
welcome cases here carry `sessions` 0.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import FIRST_ROOM_WELCOME
from src.domain.schema import Derived, Room
from tests.api.test_app import make_app
from tests.api.test_sessions import Ticker, click, post, start, stored

REPO = Path(__file__).resolve().parents[2]
WELCOME_LINE = {"kind": "welcome", "text": "Welcome to your own room. Read a riddle, then click the thing it means."}


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def client(tmp_path: Path, code_and_find_room: Room, ticker: Ticker) -> TestClient:
    return TestClient(make_app(tmp_path, code_and_find_room, clock=ticker))


def opening(state: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    return state["opening_line"], state["phrasing"]


def test_the_welcome_is_the_fixed_first_room_line():
    assert FIRST_ROOM_WELCOME == WELCOME_LINE["text"]


def test_a_session_start_appends_the_welcome_at_once_and_returns_it_unphrased(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker
):
    ticker.advance(12_345)
    response = client.post("/api/sessions", json={"room_id": code_and_find_room.id})
    assert response.status_code == 200
    state = response.json()
    assert opening(state) == (WELCOME_LINE, False)
    log = stored(tmp_path, state["id"])
    assert [event.model_dump(mode="json") for event in log] == [{"type": "opening_line", "t_ms": 0, **WELCOME_LINE}]


@pytest.mark.parametrize("derived", [
    Derived.fresh().model_dump(),
    {"sessions": 0, "persistence": 0.5, "time_to_first_hint_s": 42.0, "mean_rung_per_lock_type": {"code": 1.5}},
    {"sessions": 0, "persistence": -1, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}},
])
def test_every_first_room_start_gets_the_welcome_whatever_else_its_derived_block_carries(
    client: TestClient, code_and_find_room: Room, derived: dict[str, Any]
):
    response = client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": derived})
    assert response.status_code == 200
    assert opening(response.json()) == (WELCOME_LINE, False)


def test_the_replayed_state_carries_the_same_opening_line_before_and_after_other_events(
    client: TestClient, code_and_find_room: Room, ticker: Ticker
):
    session_id = start(client, code_and_find_room)
    assert opening(client.get(f"/api/sessions/{session_id}").json()) == (WELCOME_LINE, False)
    ticker.advance(1_000)
    assert opening(post(client, session_id, click("key"))) == (WELCOME_LINE, False)
    ticker.advance(6_000)
    state = client.get(f"/api/sessions/{session_id}").json()
    assert opening(state) == (WELCOME_LINE, False) and state["locks_open"] == [code_and_find_room.puzzles[0].id]


def test_a_reload_never_appends_a_second_opening_line(client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker):
    session_id = start(client, code_and_find_room)
    for _ in range(5):
        assert client.get(f"/api/sessions/{session_id}").status_code == 200
    ticker.advance(1_000)
    post(client, session_id, click("rug"))
    for _ in range(5):
        ticker.advance(6_000)
        assert client.get(f"/api/sessions/{session_id}").status_code == 200
    types = [event.type for event in stored(tmp_path, session_id)]
    assert types.count("opening_line") == 1 and types[0] == "opening_line"
    assert types.count("idle_tick") == 5 and types.count("click") == 1


def test_an_unknown_room_or_a_refused_derived_block_appends_no_welcome(client: TestClient, tmp_path: Path, code_and_find_room: Room):
    refused = [
        client.post("/api/sessions", json={"room_id": "room_01ARZ3NDEKTSV4RRFFQ69G5FAV"}),
        client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": {"sessions": -1}}),
    ]
    assert [response.status_code for response in refused] == [404, 422]
    assert not (tmp_path / "rooms" / "sessions").exists()


def test_the_welcome_text_is_worded_once_on_the_server_and_never_in_the_client():
    holders = sorted(
        path.relative_to(REPO).as_posix()
        for root, suffixes in ((REPO / "src", (".py",)), (REPO / "web" / "src", (".ts", ".tsx", ".js", ".html", ".css")))
        for path in root.rglob("*")
        if path.suffix in suffixes and FIRST_ROOM_WELCOME in path.read_text()
    )
    assert holders == ["src/api/app.py"]
    assert Path(REPO / "src" / "api" / "app.py").read_text().count(FIRST_ROOM_WELCOME) == 1
