"""Story 5.7: the Greeting card and the adaptive thresholds in play (FR-21, UX-DR45, UX-DR64, UX-DR33).

The client has no test runner (a runner is added only through bmad-correct-course), so the card's checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the card and the Triggers
header are checked in Chrome against the fixture rooms. The API checks serve the states the Play screen reads: the
Greeting while it is phrased and once its line lands, and the thresholds the Triggers header prints, read through the
same strings and the same seconds rule as `triggersHeader`.
"""

import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.domain.schema import Derived, Room
from src.providers.base import PhraserResponse
from src.providers.verbatim import greeting_template
from tests.api.hosted import hosted_handles, make_hosted_app
from tests.api.test_app import make_app
from tests.api.test_greeting_path import PHRASED, RETURNING, Later, SpyPhraser, begin
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n  }\n", 1)[0]


OVERLAY = "components/greeting-overlay.ts"


# --- The card while the Greeting is phrased ---------------------------------------------------------------------


def test_a_greeting_still_being_phrased_opens_the_card_in_the_thinking_state():
    play = _code(_ts("play.ts"))
    # Any served opening line opens the card, a pending Greeting (text null) included; only a reload once play has
    # begun skips it, and a line still being phrased has no play to have begun.
    assert "if (opening !== null) {" in play
    assert "if (opening.text !== null && playHasBegun(session)) play.openingLine = opening.text" in play
    overlay = _ts(OVERLAY)
    assert "export function greetingOverlay(role: string, howToPlay: boolean): GreetingOverlay {" in overlay
    assert "portrait.classList.add('is-thinking')" in overlay
    assert "const thinking = paragraph('greeting-thinking label', strings.thinkingOnThisMac)" in overlay
    # The introduction, then the thinking label where the line will go, then the voice line; no "Begin" yet.
    assert "card.append(intro, thinking, ...(howToPlay ? [steps()] : []), voice)" in overlay
    assert _code(overlay).count("card.append(actions)") == 1 and "card.append(actions)" in _function(overlay, "arrive")


def test_the_thinking_state_is_a_static_lamp_ring_and_the_label_in_pending_ink():
    rules = css_rules((WEB_SRC / "components/greeting-overlay.css").read_text())
    assert rules[".greeting-intro .wizard-portrait.is-thinking"] == {"border-color": "var(--lamp)"}
    assert rules[".greeting-thinking"] == {"margin": "var(--spacing-5) 0 0", "color": "var(--pending-ink)"}
    # Nothing loops: no animation anywhere on the card.
    assert "animation" not in (WEB_SRC / "components/greeting-overlay.css").read_text()
    assert _strings()["thinkingOnThisMac"] == "thinking on this Mac"


def test_while_thinking_focus_is_held_on_the_heading_with_no_begin():
    overlay, welcome = _ts(OVERLAY), _code(_ts("welcome.ts"))
    assert "heading.tabIndex = -1" in overlay
    assert "const target = (): HTMLElement => (line === null ? heading : begin)" in welcome
    assert "if (line === null) heading.focus()" in welcome
    # A pointer press keeps focus where it is, and Tab returns to the heading until "Begin" exists.
    assert "document.addEventListener('mousedown', keepFocus, true)" in welcome
    trap = welcome.split("const trap = ", 1)[1].split("\n  }\n", 1)[0]
    assert "target().focus()" in trap


def test_the_role_line_follows_the_mode_and_the_guide_setting():
    strings = _strings()
    assert strings["guideRoleLocal"] == (
        "Reads how you play; offers one hint at a time, never the answer, worded by Llama 3.2 3B on this Mac.")
    assert strings["guideRoleWritten"] == "Reads how you play; offers one hint at a time, never the answer, shown as written."
    assert strings["guideVoice"] == "Ask as often as you like. I'll help, a little at a time."
    assert "return mode === 'local' && guide === 'ollama' ? strings.guideRoleLocal : strings.guideRoleWritten" in _ts("welcome.ts")
    assert "const overlay = greetingOverlay(role, opening.kind === 'welcome')" in _ts("welcome.ts")


def test_the_pending_greeting_takes_its_line_from_the_play_screens_2000ms_poll():
    play = _code(_ts("play.ts"))
    assert "export const POLL_MS = 2000" in play and "ticker.postMessage(POLL_MS)" in play
    assert "if (opening.text === null) parts.push((state) => {" in play
    assert "const line = state.opening_line?.text ?? null" in play and "if (line !== null) welcome.arrive(line)" in play
    # The card never polls on its own.
    assert "getSession" not in _code(_ts("welcome.ts")) and "getSession" not in _code(_ts(OVERLAY))


# --- The line arrives ---------------------------------------------------------------------------------------------


def test_the_line_lands_in_wizard_line_lg_and_begin_appears_and_takes_focus():
    arrive = _function(_ts(OVERLAY), "arrive")
    assert "portrait.classList.remove('is-thinking')" in arrive
    assert "thinking.replaceWith(paragraph('greeting-line wizard-line-lg', speakerPrefix('guide'), line))" in arrive
    welcome = _function(_code(_ts("welcome.ts")), "arrive")
    assert "if (!open || line !== null) return" in welcome  # every later poll brings the same line: drawn once
    assert welcome.index("overlay.arrive(served)") < welcome.index("begin.focus()") < welcome.index("announce(")
    assert "begin.className = 'button-primary'" in _ts(OVERLAY)


def test_the_introduction_is_announced_once_with_the_dialog_labelled_by_its_heading_only():
    welcome = _code(_ts("welcome.ts"))
    assert welcome.count("announce(") == 1 and "announce(" in _function(welcome, "arrive")
    assert ("announce(fill(strings.guideIntroduction, { 'role line': role, 'opening line': served, "
            "'voice line': strings.guideVoice }))") in welcome
    assert _strings()["guideIntroduction"] == "The Guide. {role line} {opening line} {voice line}"
    overlay = _ts(OVERLAY)
    assert "card.setAttribute('aria-labelledby', HEADING_ID)" in overlay and "aria-describedby" not in overlay


def test_a_template_line_looks_identical_with_no_fallback_notice():
    for name in ("welcome.ts", OVERLAY, "play.ts"):
        code = _code(_ts(name))
        for trace in ("phrased", "phraser_fallback", "fallback", "template"):
            assert trace not in code, f"{name} reads {trace!r}"


def test_a_served_line_never_shows_the_thinking_state_and_only_a_welcome_has_the_tip():
    welcome = _code(_ts("welcome.ts"))
    assert welcome.index("if (opening.text !== null) arrive(opening.text)") < welcome.index("overlay.show()")
    assert "if (opening.kind === 'welcome') {" in welcome and "tip.textContent = strings.showAllTip" in welcome


# --- Dismissal ----------------------------------------------------------------------------------------------------


def test_only_begin_dismisses_and_the_line_moves_to_the_hint_area_unannounced():
    welcome, play = _code(_ts("welcome.ts")), _code(_ts("play.ts"))
    assert "Escape" not in welcome and "Escape" not in _code(_ts(OVERLAY))
    assert welcome.count("    close()\n") == 1
    click = welcome.split("begin.addEventListener('click', () => {", 1)[1].split("\n  })", 1)[0]
    assert "markBegun(sessionId)" in click and "onBegin(line)" in click
    begin = play.split("[frame.topBar, sceneColumn, sideColumn], (line) => {", 1)[1].split("\n      })", 1)[0]
    assert "play.openingLine = line" in begin and "hints?.opening(line)" in begin
    # The Play screen writes only the reconnecting line and a reply's feedback line, never the opening line again.
    assert re.findall(r"announce\(([^)]*)\)", play) == ["strings.reconnectingPlay", "`${strings.speakerGuide} ${line}`"]


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


def _seconds(ms: int) -> str:
    """`seconds` in triggers-panel.ts: whole, or with one decimal when the server's value has one."""
    value = round(ms / 100) / 10
    return str(int(value)) if value == int(value) else str(value)


def triggers_header(thresholds: dict[str, Any]) -> tuple[str, str]:
    """`triggersHeader` in triggers-panel.ts, over the same strings: what the Triggers header prints."""
    strings = _strings()

    def one_x(ms: int, base: int) -> str:
        return "" if ms == base else " " + strings["atOneX"].format(s=_seconds(base))

    nudge = strings["triggersNudge"].format(threshold=_seconds(thresholds["nudge_threshold_ms"]))
    spacing = strings["triggersSpacing"].format(spacing=_seconds(thresholds["rung_spacing_ms"]))
    timing = (f"{nudge}{one_x(thresholds['nudge_threshold_ms'], thresholds['nudge_threshold_base_ms'])} "
              f"{spacing}{one_x(thresholds['rung_spacing_ms'], thresholds['rung_spacing_base_ms'])}")
    source = strings["thresholdFresh"] if thresholds["source"] == "fresh" else strings["thresholdDerived"]
    return timing, source


def test_the_mirror_follows_the_header_code():
    header = _ts("components/triggers-panel.ts")
    assert "return String(Math.round(ms / 100) / 10)" in header
    assert "return [timing, thresholds.source === 'fresh' ? strings.thresholdFresh : strings.thresholdDerived]" in header


DERIVED_SOURCE = "Set by how you played last time (kept in this browser)"


@pytest.mark.parametrize(("persistence", "nudge"), [(0, 90), (1, 135), (-1, 60)])
def test_the_header_shows_the_threshold_how_the_player_played_last_time(
    tmp_path: Path, code_and_find_room: Room, persistence: float, nudge: int
):
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=SpyPhraser(), spawn=Later()))
    session_id = begin(client, code_and_find_room, RETURNING.model_copy(update={"sessions": 1, "persistence": persistence}))["id"]
    state = client.get(f"/api/sessions/{session_id}").json()
    assert triggers_header(state["thresholds"]) == (
        f"Nudge after {nudge} s idle or 3 wrong attempts · next hint no sooner than 90 s", DERIVED_SOURCE)


def test_a_fresh_profile_shows_the_default_for_a_first_room(tmp_path: Path, code_and_find_room: Room):
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=SpyPhraser(), spawn=Later()))
    state = client.get(f"/api/sessions/{begin(client, code_and_find_room, Derived.fresh())['id']}").json()
    assert triggers_header(state["thresholds"]) == (
        "Nudge after 90 s idle or 3 wrong attempts · next hint no sooner than 90 s", "Default for a first room")


def test_every_hosted_session_shows_the_default_for_a_first_room(tmp_path: Path, code_and_find_room: Room):
    app = make_hosted_app(tmp_path, hosted_handles(tmp_path), code_and_find_room, phraser=SpyPhraser(), spawn=Later())
    client = TestClient(app)
    returning = RETURNING.model_copy(update={"sessions": 1, "persistence": 1})
    state = client.get(f"/api/sessions/{begin(client, code_and_find_room, returning)['id']}").json()
    assert triggers_header(state["thresholds"])[1] == "Default for a first room"


def test_at_demo_timescale_6_every_number_comes_from_session_state(tmp_path: Path, code_and_find_room: Room):
    settings = Settings(demo_timescale=6, guide="verbatim")
    client = TestClient(make_app(tmp_path, code_and_find_room, settings=settings, phraser=SpyPhraser(), spawn=Later()))
    returning = RETURNING.model_copy(update={"sessions": 1, "persistence": 0})
    state = client.get(f"/api/sessions/{begin(client, code_and_find_room, returning)['id']}").json()
    assert triggers_header(state["thresholds"]) == (
        "Nudge after 15 s idle (90 s at 1×) or 3 wrong attempts · next hint no sooner than 15 s (90 s at 1×)",
        DERIVED_SOURCE,
    )


def test_the_header_shows_only_what_session_state_reports():
    panel = _code(_ts("components/triggers-panel.ts"))
    assert "const thresholds = state.thresholds ?? null" in panel
    for path in WEB_SRC.rglob("*.ts"):
        code = _code(path.read_text())
        assert "persistence" not in code or path.relative_to(WEB_SRC).parts[0] == "profile", path
        assert "nudge_threshold" not in code or path.name == "triggers-panel.ts", path


# --- Accessibility floor ------------------------------------------------------------------------------------------


def test_the_cards_colors_meet_aa_on_parchment_and_the_fade_is_skipped_under_reduced_motion():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    for fg in ("ink", "ink-muted", "pending-ink", "focus-ring-inner"):
        assert re.search(rf"\| `{fg}` [^|]*\| `parchment`[^|]*\| [\d.]+ \|[^|]*\| pass \|", table), fg
    reduced = (WEB_SRC / "tokens.css").read_text().split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "--motion-overlay: 0ms;" in reduced.split("}", 1)[0]
    assert "show: () => fadeIn(card)" in _ts(OVERLAY)
