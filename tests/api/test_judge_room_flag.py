"""Story 7.21: the server sets the session state's `judge_room` flag, true only for a Room under `rooms/judge/` (FR-33, UX-DR44).

The Completion screen draws its "Deleted Tue Nov 10" strip from this flag alone.
No test reaches Modal: the hosted app runs over plain dicts and a temporary
Volume directory, a Demo room is landed as `scripts/seed_rooms.py` lands it
and a Judge room is put through the hosted `ArtifactStore`, as a Build does.
"""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.domain.schema import Derived, Room
from src.infra.modal import ModalHandles, hosted_stores
from tests.api.hosted import hosted_handles, make_hosted_app
from tests.api.test_app import make_app, store_room
from tests.api.test_sessions import Ticker, click, play_to_the_exit, post


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def handles(tmp_path: Path) -> ModalHandles:
    return hosted_handles(tmp_path)


@pytest.fixture
def hosted(tmp_path: Path, handles: ModalHandles, code_and_find_room: Room, four_lock_room: Room, ticker: Ticker) -> TestClient:
    """The hosted app with `four_lock_room` seeded as a Demo room and `code_and_find_room` stored as a Judge room."""
    app = make_hosted_app(tmp_path, handles, four_lock_room, clock=ticker)
    store_room(hosted_stores(handles).artifacts, code_and_find_room)
    return TestClient(app)


def begin(client: TestClient, room: Room) -> dict[str, Any]:
    response = client.post("/api/sessions", json={"room_id": room.id, "derived": Derived.fresh().model_dump(mode="json")})
    assert response.status_code == 200, response.text
    return response.json()


def test_a_judge_room_session_carries_judge_room_true_on_every_state_it_serves(hosted: TestClient, code_and_find_room: Room):
    state = begin(hosted, code_and_find_room)
    assert state["judge_room"] is True
    assert hosted.get(f"/api/sessions/{state['id']}").json()["judge_room"] is True
    assert post(hosted, state["id"], click("key"))["judge_room"] is True
    assert hosted.post(f"/api/sessions/{state['id']}/trickster").json()["judge_room"] is True


def test_a_demo_room_session_carries_judge_room_false(hosted: TestClient, four_lock_room: Room):
    state = begin(hosted, four_lock_room)
    assert state["judge_room"] is False
    assert hosted.get(f"/api/sessions/{state['id']}").json()["judge_room"] is False


def test_a_judge_room_played_to_its_exit_still_carries_the_flag_on_the_state_the_completion_screen_reads(
    hosted: TestClient, code_and_find_room: Room, ticker: Ticker
):
    """The Completion screen reads `GET /sessions/<id>` after the Exit opens: a Judge room's state still says so."""
    session_id = begin(hosted, code_and_find_room)["id"]
    play_to_the_exit(hosted, session_id, ticker)
    state = hosted.get(f"/api/sessions/{session_id}").json()
    assert state["locks_open"] and state["judge_room"] is True


def test_every_local_room_session_carries_judge_room_false(tmp_path: Path, code_and_find_room: Room):
    client = TestClient(make_app(tmp_path, code_and_find_room))
    state = begin(client, code_and_find_room)
    assert state["judge_room"] is False
    assert client.get(f"/api/sessions/{state['id']}").json()["judge_room"] is False
