"""FR-21, UX-DR45, UX-DR64, UX-DR74, UX-DR70, UX-DR17: the First-room welcome card before the first Scene.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the card is checked in
Chrome against the fixture rooms. The API check serves the welcome the way the Play screen reads it on a reload.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import FIRST_ROOM_WELCOME
from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX
from tests.web.design import WEB_SRC, css_rules, design_text


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def test_the_play_screen_shows_the_card_for_a_served_welcome_until_play_has_begun():
    play = _ts("play.ts")
    assert "if (opening !== null) {" in play
    assert "if (opening.text !== null && playHasBegun(session)) play.openingLine = opening.text" in play
    assert "mountWelcome(session.id, frame.mode, frame.guide, opening, frame.body, [frame.topBar, sceneColumn, sideColumn], (line) => {" in play
    assert "unmountWelcome = welcome.close" in play and "unmountWelcome?.()" in play
    # The shell hands the Play screen its body, the whole top bar, its controls slot (Story 1.25) and the `guide`
    # setting of `GET /meta`.
    shell = _ts("shell.ts")
    assert "content = { name, session: state, guide: meta.guide, mode: meta.mode, profile: place.profile }" in shell
    assert "const frame = { body: element, topBar: bar.element, controls: bar.controls, guide: content.guide, mode: content.mode }" in shell


def test_the_card_is_a_560px_parchment_sheet_over_the_scrim_that_fades_in_over_300ms():
    rules = _rules("components/greeting-overlay.css")
    card = rules[".greeting-overlay"]
    assert card["width"] == "560px" and card["background"] == "var(--parchment)" and card["color"] == "var(--ink)"
    assert card["border-radius"] == "var(--rounded-lg)" and card["box-shadow"] == "var(--elevation-overlay)"
    assert card["transition"] == "opacity var(--motion-overlay) var(--motion-ease)"
    assert rules[".greeting-overlay.is-arriving"] == {"opacity": "0"}
    assert rules[".greeting-scrim"]["background"] == "var(--scrim)"
    overlay = design_text().split("  greeting-overlay:\n", 1)[1].split("\n  leave-room-confirmation:", 1)[0]
    assert "width: 560px" in overlay and "background: '{colors.parchment}'" in overlay
    assert "line: '{typography.wizard-line-lg}'" in overlay and "portrait: 96px" in overlay
    assert "show: () => fadeIn(card)" in _ts("components/greeting-overlay.ts")
    # Reduced motion makes the fade instant.
    reduced = (WEB_SRC / "tokens.css").read_text().split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "--motion-overlay: 0ms;" in reduced.split("}", 1)[0]


def test_the_scrim_covers_the_body_only_so_the_top_bar_and_its_timer_stay_undimmed():
    scrim = _rules("components/greeting-overlay.css")[".greeting-scrim"]
    assert scrim["position"] == "absolute" and scrim["inset"] == "0"
    # The scrim's box is the Play layout (the body under the Disclosure banner and the top bar), never the page.
    assert _rules("shell.css")[".play-layout"]["position"] == "relative"
    assert "body.append(overlay.element)" in _ts("welcome.ts")


def test_the_card_holds_the_guides_introduction_the_served_line_the_voice_line_and_begin():
    overlay = _ts("components/greeting-overlay.ts")
    assert "const portrait = wizardPortrait('guide', 96)" in overlay and "intro.append(portrait, name)" in overlay
    assert "heading.className = 'greeting-heading display-sm'" in overlay and "heading.textContent = strings.guide" in overlay
    assert "paragraph('greeting-role body-sm', role)" in overlay
    assert "paragraph('greeting-line wizard-line-lg', speakerPrefix('guide'), line)" in overlay
    assert "paragraph('greeting-voice wizard-line', speakerPrefix('guide'), strings.guideVoice)" in overlay
    assert "begin.className = 'button-primary'" in overlay and "begin.textContent = strings.begin" in overlay
    rules = _rules("components/greeting-overlay.css")
    assert rules[".greeting-role"]["color"] == "var(--ink-muted)"
    assert rules[".greeting-intro"]["grid-template-columns"] == "96px minmax(0, 1fr)"
    assert rules[".greeting-actions"]["display"] == "flex"  # "Begin" left-aligned under the voice line
    # The role line follows the mode and the `guide` setting of `GET /meta`: Hosted is always shown as written.
    welcome = _ts("welcome.ts")
    assert "return mode === 'local' && guide === 'ollama' ? strings.guideRoleLocal : strings.guideRoleWritten" in welcome


def test_only_a_first_room_welcome_teaches_the_game_in_three_steps_between_the_line_and_the_voice_line():
    overlay, welcome = _code(_ts("components/greeting-overlay.ts")), _code(_ts("welcome.ts"))
    # A returning player's Greeting has played before; the First-room welcome (every Hosted session) has not.
    assert "const overlay = greetingOverlay(role, opening.kind === 'welcome')" in welcome
    # The served line (or the thinking label it replaces) first, then the steps, then the voice line and "Begin".
    assert "card.append(intro, thinking, ...(howToPlay ? [steps()] : []), voice)" in overlay
    steps = overlay.split("function steps(", 1)[1].split("\n}\n", 1)[0]
    assert "document.createElement('ol')" in steps and "list.className = 'greeting-steps body-md'" in steps
    assert "for (const step of [strings.howToPlay1, strings.howToPlay2, strings.howToPlay3])" in steps
    rules = _rules("components/greeting-overlay.css")
    assert rules[".greeting-steps"]["color"] == "var(--ink)" and rules[".greeting-steps"]["list-style"] == "decimal"
    assert rules[".greeting-steps li + li"] == {"margin-top": "var(--spacing-2)"}
    card = design_text().split("  greeting-overlay:\n", 1)[1].split("\n  leave-room-confirmation:", 1)[0]
    assert "steps: '{typography.body-md}'" in card and "stepsColor: '{colors.ink}'" in card


def test_the_line_is_rendered_as_served_never_worded_in_the_client():
    for name in ("play.ts", "welcome.ts", "components/greeting-overlay.ts", "strings.ts"):
        assert FIRST_ROOM_WELCOME not in _ts(name) and "Find what doesn't belong" not in _ts(name), name


def test_begin_is_the_only_control_and_the_only_way_out_with_focus_trapped_on_it():
    overlay, welcome = _code(_ts("components/greeting-overlay.ts")), _code(_ts("welcome.ts"))
    assert overlay.count("document.createElement('button')") == 1
    assert "Escape" not in welcome and "Escape" not in overlay  # Escape does nothing
    assert "begin.focus()" in welcome
    assert "const target = (): HTMLElement => (line === null ? heading : begin)" in welcome
    assert "document.addEventListener('mousedown', keepFocus, true)" in welcome  # a scrim click keeps focus on it
    keep = welcome.split("const keepFocus = (event: MouseEvent): void => {", 1)[1].split("\n  }\n", 1)[0]
    assert "else event.preventDefault()" in keep
    trap = welcome.split("const trap = ", 1)[1].split("\n  }\n", 1)[0]
    assert "if (event.key !== 'Tab') return" in trap and "event.preventDefault()" in trap and "target().focus()" in trap
    # The only listener that closes the card is "Begin"'s click; teardown removes every document listener.
    assert welcome.count("    close()\n") == 1 and "begin.addEventListener('click', () => {" in welcome
    assert "document.removeEventListener('mousedown', keepFocus, true)" in welcome
    assert "document.removeEventListener('keydown', trap, true)" in welcome


def test_a_pointer_press_on_begin_refocuses_it_by_pointer_so_the_first_hotspot_shows_no_focus_reveal():
    """Replay Oct 29: after a mouse click on "Begin" the first Hotspot showed its outline and label chip, though the
    pointer was elsewhere. "Begin" was focused by script, so Chromium carried :focus-visible over to the script focus
    of the first Hotspot. A press on "Begin" now lets the pointer focus it again (Chromium ignores
    `focus({ focusVisible: false })`), so the focus reveal follows a keyboard "Begin" only."""
    welcome = _code(_ts("welcome.ts"))
    keep = welcome.split("const keepFocus = (event: MouseEvent): void => {", 1)[1].split("\n  }\n", 1)[0]
    assert "if (event.target instanceof Node && begin.contains(event.target)) begin.blur()" in keep
    assert keep.index("begin.blur()") < keep.index("else event.preventDefault()")


def test_the_dialog_is_labelled_by_its_heading_only():
    overlay = _ts("components/greeting-overlay.ts")
    assert "card.setAttribute('role', 'dialog')" in overlay
    assert "card.setAttribute('aria-labelledby', HEADING_ID)" in overlay and "heading.id = HEADING_ID" in overlay
    assert "aria-describedby" not in overlay and "aria-label'" not in overlay


def test_the_scene_hotspots_and_top_bar_are_inert_while_the_card_shows():
    welcome = _ts("welcome.ts")
    assert "for (const element of held) element.inert = true" in welcome
    assert "for (const element of held) element.inert = false" in welcome


def test_the_introduction_is_written_to_the_one_live_region_once():
    welcome, region, shell = _ts("welcome.ts"), _ts("live-region.ts"), _ts("shell.ts")
    assert _code(welcome).count("announce(") == 1
    assert ("announce(fill(strings.guideIntroduction, { 'role line': role, 'opening line': served, "
            "'voice line': strings.guideVoice }))") in welcome
    assert "region.setAttribute('aria-live', 'polite')" in region and "document.body.append(region)" in region
    assert "liveRegion() // in the page before anything is written to it" in shell
    # Exactly one region in the client.
    assert sum(_code(_ts(str(p.relative_to(WEB_SRC)))).count("aria-live") for p in WEB_SRC.rglob("*.ts")) == 1
    # `fill` takes the spaced placeholders the Component Patterns line names.
    assert r"/\{(\w+(?: \w+)*)\}/g" in _ts("strings.ts")


def test_begin_keeps_the_line_for_the_hint_area_and_focuses_the_first_hotspot():
    play = _ts("play.ts")
    begin = play.split("[frame.topBar, sceneColumn, sideColumn], (line) => {", 1)[1].split("\n      })", 1)[0]
    assert "play.openingLine = line" in begin and "unfocus = focusFirstHotspot(sceneColumn)" in begin
    assert "openingLine: null," in play and "openingLine: string | null" in play
    focus = play.split("function focusFirstHotspot(", 1)[1].split("\n}\n", 1)[0]
    assert "sceneColumn.querySelector<SVGElement>('.hotspot')" in focus and "live.focus()" in focus
    # Nothing announces the line again: the Play screen writes only the reconnecting line (1.24) and a reply's feedback line.
    assert re.findall(r"announce\(([^)]*)\)", _code(play)) == ["strings.reconnectingPlay", "`${strings.speakerGuide} ${line}`"]


def test_a_reload_once_play_has_begun_does_not_show_the_card_again():
    welcome = _ts("welcome.ts")
    begun = welcome.split("export function playHasBegun(", 1)[1].split("\n}\n", 1)[0]
    for trace in ("begunHere(state.id)", "state.locks_open.length > 0", "state.inventory.length > 0",
                  "Object.values(state.wrong_attempts).some((count) => count > 0)",
                  "(state.order_buffer.puzzle_id ?? null) !== null", "state.rungs_used > 0", "state.rung_changes.length > 0",
                  "state.cards.length > 0"):
        assert trace in begun, trace
    assert "markBegun(sessionId)" in welcome and "sessionStorage.setItem(BEGUN_KEY + sessionId, '1')" in welcome
    assert welcome.count("try {") == 2  # storage that throws never breaks the card


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
