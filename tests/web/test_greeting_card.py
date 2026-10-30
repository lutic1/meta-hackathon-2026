"""Story 5.7: the Greeting and the adaptive thresholds in play (FR-21, UX-DR64, UX-DR33).

Story mode (owner decision Oct 29) retired the Greeting card: a returning player's Greeting is the Guide's line on the
story intro's Guide beat (tests/web/test_story_intro.py). The API checks serve the states the Play screen reads: the
Greeting while it is phrased and once its line lands, and the waits the server still keeps.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.domain.schema import Derived, Room
from src.providers.base import PhraserResponse
from src.providers.verbatim import greeting_template
from tests.api.test_app import make_app
from tests.api.test_greeting_path import PHRASED, RETURNING, Later, SpyPhraser, begin
from tests.web.design import WEB_SRC, design_text
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


# --- The served states --------------------------------------------------------------------------------------------


class FallbackPhraser(SpyPhraser):
    """A Guide model that is unreachable: the Greeting composer falls back to the template."""

    def greet(self, derived: Derived) -> PhraserResponse:
        raise ConnectionError("Ollama is not running")


@pytest.mark.parametrize("phraser", [SpyPhraser(), FallbackPhraser()], ids=["phrased", "template"])
def test_the_play_screen_reads_a_pending_greeting_then_its_line_with_the_same_shape(
    tmp_path: Path, code_and_find_room: Room, phraser: SpyPhraser
):
    later = Later()
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=phraser, spawn=later))
    session_id = begin(client, code_and_find_room)["id"]
    pending = client.get(f"/api/sessions/{session_id}").json()
    assert pending["opening_line"] == {"kind": "greeting", "text": None} and pending["phrasing"] is True
    later.run()
    landed = client.get(f"/api/sessions/{session_id}").json()
    assert landed["phrasing"] is False and landed["opening_line"]["kind"] == "greeting"
    assert set(landed["opening_line"]) == {"kind", "text"}  # nothing tells a template from a phrased line
    expected = greeting_template(RETURNING) if isinstance(phraser, FallbackPhraser) else PHRASED
    assert landed["opening_line"]["text"] == expected


def test_how_hints_work_reads_no_threshold():
    """Story mode: under the chest no idle wait opens a hint, so "How hints work" says the chest line alone and never
    reads the thresholds session state still reports."""
    panel = _code(_ts("components/triggers-panel.ts"))
    assert "header.textContent = strings.hintsExplained" in panel and "thresholds" not in panel
    assert "thresholdDerived" not in _strings()


@pytest.mark.parametrize(("persistence", "nudge"), [(0, 90), (1, 135), (-1, 60)])
def test_the_servers_wait_still_follows_a_returning_players_profile(
    tmp_path: Path, code_and_find_room: Room, persistence: float, nudge: int
):
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=SpyPhraser(), spawn=Later()))
    session_id = begin(client, code_and_find_room, RETURNING.model_copy(update={"sessions": 1, "persistence": persistence}))["id"]
    state = client.get(f"/api/sessions/{session_id}").json()
    assert state["thresholds"]["nudge_threshold_ms"] == nudge * 1000  # the server's wait follows the profile


def test_at_demo_timescale_6_the_server_keeps_the_scaled_wait(tmp_path: Path, code_and_find_room: Room):
    settings = Settings(demo_timescale=6, guide="verbatim")
    client = TestClient(make_app(tmp_path, code_and_find_room, settings=settings, phraser=SpyPhraser(), spawn=Later()))
    returning = RETURNING.model_copy(update={"sessions": 1, "persistence": 0})
    state = client.get(f"/api/sessions/{begin(client, code_and_find_room, returning)['id']}").json()
    assert (state["thresholds"]["nudge_threshold_ms"], state["thresholds"]["nudge_threshold_base_ms"]) == (15_000, 90_000)


def test_the_panel_shows_only_what_session_state_reports():
    panel = _code(_ts("components/triggers-panel.ts"))
    assert "thresholds" not in panel
    for path in WEB_SRC.rglob("*.ts"):
        code = _code(path.read_text())
        assert "persistence" not in code or path.relative_to(WEB_SRC).parts[0] == "profile", path
        assert "nudge_threshold" not in code, path


# --- Accessibility floor ------------------------------------------------------------------------------------------


def test_the_parchment_colors_meet_aa_and_overlays_are_instant_under_reduced_motion():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    for fg in ("ink", "ink-muted", "pending-ink", "focus-ring-inner"):
        assert re.search(rf"\| `{fg}` [^|]*\| `parchment`[^|]*\| [\d.]+ \|[^|]*\| pass \|", table), fg
    reduced = (WEB_SRC / "tokens.css").read_text().split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "--motion-overlay: 0ms;" in reduced.split("}", 1)[0]
