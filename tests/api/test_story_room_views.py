"""Story mode (owner decision Oct 29): the play routes hold evidence back until a lock opens (AD-3, AD-12).

`GET /rooms/<room_id>` serves no evidence card for any Puzzle, and
`GET /sessions/<id>/room` serves the real card of each Puzzle open in that
Session alone; both name each riddle's start photo and each photo's area.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.api.test_sessions import Ticker, code, post, start
from tests.fixtures.rooms import PZ


def test_the_room_route_serves_no_evidence_and_each_riddles_start_photo(tmp_path: Path, four_lock_room: Room):
    view = TestClient(make_app(tmp_path, four_lock_room)).get(f"/api/rooms/{four_lock_room.id}").json()
    assert all(puzzle["evidence_cards"] == [] for puzzle in view["puzzles"])
    assert [puzzle["start_photo"] for puzzle in view["puzzles"]] == [0, 2, 3, 1, 4]
    assert {(photo["area"], photo["pan"]) for photo in view["photos"]} == {("room", None)}


def test_the_session_room_serves_the_real_card_of_each_open_puzzle_alone(tmp_path: Path, four_lock_room: Room):
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, four_lock_room, clock=ticker))
    session_id = start(client, four_lock_room)

    def cards() -> dict[str, list[dict[str, str]]]:
        view = client.get(f"/api/sessions/{session_id}/room").json()
        return {puzzle["id"]: puzzle["evidence_cards"] for puzzle in view["puzzles"]}

    assert all(shown == [] for shown in cards().values())
    ticker.advance(1_000)
    post(client, session_id, code("clock_code", "415"))
    clock = next(p for p in four_lock_room.puzzles if p.id == PZ["clock_code"]).evidence
    shown = cards()
    assert shown[PZ["clock_code"]] == [clock.model_dump()]
    assert all(cards_ == [] for pid, cards_ in shown.items() if pid != PZ["clock_code"])
