"""Story 7.15: a Demo room welcomes the judge as a visitor, a Judge room with the First-room welcome (FR-31, AR-31, UX-DR45, AD-4).

No test reaches Modal: the hosted app runs over plain dicts and a temporary
Volume directory, a Demo room is landed as `scripts/seed_rooms.py` lands it
and a Judge room is put through the hosted `ArtifactStore`, as a Build does.
"""

import ast
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import DEMO_ROOM_WELCOME, FIRST_ROOM_WELCOME
from src.domain.schema import Derived, Event, OpeningLineEvent, Room
from src.infra.modal import DictSessionStore, ModalHandles, hosted_stores
from tests.api.hosted import hosted_handles, make_hosted_app
from tests.api.test_app import store_room
from tests.api.test_greeting_path import Later, SpyPhraser
from tests.api.test_sessions import Ticker, click, post

REPO = Path(__file__).resolve().parents[2]
DEMO_LINE = {"kind": "welcome", "text": "Welcome to someone else's room. Read a riddle, then click the thing it means."}
FIRST_ROOM_LINE = {"kind": "welcome", "text": "Welcome to your own room. Read a riddle, then click the thing it means."}
RETURNING = Derived(sessions=1, persistence=0.4173, time_to_first_hint_s=137.9, mean_rung_per_lock_type={"code": 2.71})


@pytest.fixture
def handles(tmp_path: Path) -> ModalHandles:
    return hosted_handles(tmp_path)


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def spy() -> SpyPhraser:
    return SpyPhraser()


@pytest.fixture
def later() -> Later:
    return Later()


@pytest.fixture
def client(
    tmp_path: Path, handles: ModalHandles, code_and_find_room: Room, four_lock_room: Room, ticker: Ticker, spy: SpyPhraser, later: Later
) -> TestClient:
    """The hosted app with `code_and_find_room` seeded as a Demo room and `four_lock_room` stored as a Judge room."""
    app = make_hosted_app(tmp_path, handles, code_and_find_room, clock=ticker, phraser=spy, spawn=later)
    store_room(hosted_stores(handles).artifacts, four_lock_room)
    return TestClient(app)


def begin(client: TestClient, room: Room, derived: Derived | dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"room_id": room.id}
    if derived is not None:
        body["derived"] = derived.model_dump(mode="json") if isinstance(derived, Derived) else derived
    response = client.post("/api/sessions", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def opening(state: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    return state["opening_line"], state["phrasing"]


def logged(handles: ModalHandles, session_id: str) -> list[Event]:
    return DictSessionStore(handles.sessions).read_all(session_id)


# --- The two welcome lines -------------------------------------------------------------


def test_both_welcome_lines_are_the_fixed_strings():
    assert DEMO_ROOM_WELCOME == DEMO_LINE["text"]
    assert FIRST_ROOM_WELCOME == FIRST_ROOM_LINE["text"]


def test_both_welcome_lines_live_in_one_place_beside_each_other_and_never_in_the_client():
    for line in (FIRST_ROOM_WELCOME, DEMO_ROOM_WELCOME):
        holders = sorted(
            path.relative_to(REPO).as_posix()
            for root, suffixes in ((REPO / "src", (".py",)), (REPO / "web" / "src", (".ts", ".tsx", ".js", ".html", ".css")))
            for path in root.rglob("*")
            if path.suffix in suffixes and line in path.read_text()
        )
        assert holders == ["src/api/app.py"]
        assert (REPO / "src" / "api" / "app.py").read_text().count(line) == 1
    body = ast.parse((REPO / "src" / "api" / "app.py").read_text()).body
    assigned = [
        node.targets[0].id
        for node in body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    ]
    first = assigned.index("FIRST_ROOM_WELCOME")
    assert assigned[first + 1] == "DEMO_ROOM_WELCOME"


# --- A Demo room: the visitor's welcome, appended at once -------------------------------


def test_a_demo_room_start_returns_the_demo_welcome_unphrased_and_appends_it_at_once(
    client: TestClient, handles: ModalHandles, code_and_find_room: Room, ticker: Ticker
):
    ticker.advance(12_345)
    state = begin(client, code_and_find_room, Derived.fresh())
    assert opening(state) == (DEMO_LINE, False)
    assert logged(handles, state["id"]) == [OpeningLineEvent(type="opening_line", t_ms=0, **DEMO_LINE)]


def test_a_judge_room_start_in_hosted_mode_gets_the_first_room_welcome(
    client: TestClient, handles: ModalHandles, four_lock_room: Room
):
    state = begin(client, four_lock_room, Derived.fresh())
    assert opening(state) == (FIRST_ROOM_LINE, False)
    assert logged(handles, state["id"]) == [OpeningLineEvent(type="opening_line", t_ms=0, **FIRST_ROOM_LINE)]


# --- Hosted mode never greets ------------------------------------------------------------


@pytest.mark.parametrize("sessions", [1, 3, 40])
@pytest.mark.parametrize("demo", [True, False])
def test_a_returning_block_still_gets_a_welcome_and_the_greeting_path_is_never_taken(
    client: TestClient, handles: ModalHandles, code_and_find_room: Room, four_lock_room: Room,
    spy: SpyPhraser, later: Later, sessions: int, demo: bool,
):
    room, line = (code_and_find_room, DEMO_LINE) if demo else (four_lock_room, FIRST_ROOM_LINE)
    state = begin(client, room, RETURNING.model_copy(update={"sessions": sessions}))
    assert opening(state) == (line, False)
    assert spy.greeted == [] and later.tasks == []
    assert [event.type for event in logged(handles, state["id"])] == ["opening_line"]


@pytest.mark.parametrize("derived", [
    {"sessions": -1, "persistence": 0, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}},
    {"sessions": 2, "persistence": 1.5, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}},
    {"sessions": 2, "persistence": -1.01, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}},
    {"sessions": 2, "persistence": 0, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {"code": 3.5}},
])
def test_a_derived_block_outside_its_bounds_is_refused_with_422_and_no_session_is_created(
    client: TestClient, handles: ModalHandles, code_and_find_room: Room, spy: SpyPhraser, later: Later, derived: dict[str, Any]
):
    response = client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": derived})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert handles.sessions == {} and spy.greeted == [] and later.tasks == []


# --- A reload replays the one opening line ----------------------------------------------


def test_a_reload_returns_the_same_demo_welcome_with_no_second_opening_line(
    client: TestClient, handles: ModalHandles, code_and_find_room: Room, ticker: Ticker
):
    session_id = begin(client, code_and_find_room)["id"]
    for _ in range(3):
        assert opening(client.get(f"/api/sessions/{session_id}").json()) == (DEMO_LINE, False)
    ticker.advance(1_000)
    assert opening(post(client, session_id, click("rug"))) == (DEMO_LINE, False)
    for _ in range(3):
        ticker.advance(6_000)
        assert opening(client.get(f"/api/sessions/{session_id}").json()) == (DEMO_LINE, False)
    types = [event.type for event in logged(handles, session_id)]
    assert types.count("opening_line") == 1 and types[0] == "opening_line"
    assert types.count("idle_tick") == 3 and types.count("click") == 1
