"""FR-21, UX-DR70, UX-DR17: the opening line a Session serves, which the Play screen reads on a reload.

Story mode (owner decision Oct 29) retired the First-room welcome card: the story intro opens every Session
(tests/web/test_story_intro.py). The API check serves the welcome the way the Play screen reads it on a reload.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import FIRST_ROOM_WELCOME
from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX
from tests.web.design import design_text


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def test_every_welcome_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("ink", "parchment"), ("ink-muted", "parchment"), ("focus-ring-inner", "parchment")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"


def test_a_reload_reads_the_welcome_from_the_session_and_play_traces_once_play_has_events(
    client: TestClient, four_lock_room: Room
):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    assert session["opening_line"] == {"kind": "welcome", "text": FIRST_ROOM_WELCOME} and session["phrasing"] is False
    fresh = client.get(f"/api/sessions/{session['id']}").json()
    assert fresh["opening_line"] == session["opening_line"]
    assert not (fresh["locks_open"] or fresh["inventory"] or any(fresh["wrong_attempts"].values()) or fresh["cards"])
    client.post(f"/api/sessions/{session['id']}/events", json={"type": "click", "interactable_id": IX["key"]})
    played = client.get(f"/api/sessions/{session['id']}").json()
    assert played["opening_line"] == session["opening_line"] and played["inventory"] == [IX["key"]]
