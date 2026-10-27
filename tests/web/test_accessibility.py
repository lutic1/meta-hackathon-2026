"""NFR-14, UX-DR69 to UX-DR72, UX-DR6, UX-DR11, UX-DR23: the accessibility floor on Scenes and locks.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the floor is checked in
Chrome against the fixture rooms. The API check posts the lock inputs whose outcomes the live region announces.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX
from tests.web.design import WEB_SRC, css_rules, design_text, source_css, source_ts
from tests.web.test_contrast import PROPS, _hex, _over, contrast
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def test_the_floor_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["showAllObjects"] == "Show all objects"
    assert strings["showAllTip"] == "Tip: 'Show all objects' in the top bar outlines everything you can click."
    assert strings["lockNotThis"].format(n=2, count=1) == "Puzzle 2: not this, 1."
    assert strings["lockOpen"].format(n=3) == "Puzzle 3: open."


def test_hotspots_are_in_tab_order_by_polygon_centroid_top_to_bottom_then_left_to_right():
    layer, geometry = _ts("scene/hotspots.ts"), _ts("scene/geometry.ts")
    assert ".sort((a, b) => readingOrder(a.interactable.polygons ?? [], b.interactable.polygons ?? []))" in layer
    # Every Hotspot is a tabindex 0 element, so the order they are appended in is the Tab order.
    assert layer.index(".sort((a, b) => readingOrder(") < layer.index("svg.append(hotspot)")
    order = geometry.split("export function readingOrder(", 1)[1].split("\n}\n", 1)[0]
    assert "const [ax, ay] = centroid(a)" in order and "return ay - by || ax - bx" in order
    # The area-weighted centroid of the union, every instance counted whichever way it is wound.
    center = geometry.split("export function centroid(", 1)[1].split("\n}\n", 1)[0]
    assert "const sign = signedArea(polygon) < 0 ? -1 : 1" in center
    assert "return [cx / (3 * area), cy / (3 * area)]" in center


def test_keyboard_focus_traces_the_ring_and_holds_the_label_chip_until_blur_and_enter_clicks():
    layer = _ts("scene/hotspots.ts")
    assert "hotspot.setAttribute('role', 'button')" in layer and "hotspot.setAttribute('aria-label', interactable.label)" in layer
    assert "if (event.key === 'Enter') handlers.onActivate(interactable)" in layer
    assert "if (hotspot.matches(':focus-visible')) showChip(interactable, interactable.label)" in layer
    assert "hotspot.addEventListener('blur', () => hide?.())" in layer
    chip = layer.split("function showChip(", 1)[1].split("\n  }\n", 1)[0]
    # Focused, the chip neither times out nor follows the pointer; otherwise it fades after 2 s or on pointer leave.
    held = chip.index("if (document.activeElement === hotspot && hotspot.matches(':focus-visible')) return")
    assert held < chip.index("timer = setTimeout(() => hide?.(), CHIP_MS)")
    assert held < chip.index("hotspot.addEventListener('pointerleave', done)")
    assert "chip.setAttribute('aria-hidden', 'true')" in layer  # the label is already the accessible name
    rules = _rules("scene/scene.css")
    assert rules[".hotspot:focus-visible .hotspot-halo"] == {"stroke": "var(--focus-ring)", "stroke-width": "8px"}
    assert rules[".hotspot:focus-visible .hotspot-outline"]["stroke"] == "var(--focus-ring-inner)"


def test_show_all_objects_is_a_pressed_toggle_in_the_top_bar_controls():
    play, shell = _ts("play.ts"), _ts("shell.ts")
    toggle = play.split("return toggleButton({", 1)[1].split("})", 1)[0]
    assert "label: strings.showAllObjects" in toggle and "state: 'pressed'" in toggle
    assert "onToggle: (on) => sceneColumn.classList.toggle('is-showing-all', on)" in toggle
    assert "const showAll = showAllToggle(sceneColumn)" in play and "frame.controls.append(showAll)" in play
    assert "showAll.remove()" in play
    assert "controls: bar.controls" in shell and "controls: HTMLElement" in play
    # The shared toggle announces its pressed state and holds the pressed fill and 2 px lamp border.
    button = _ts("components/button.ts")
    assert "const attribute = state === 'pressed' ? 'aria-pressed' : 'aria-expanded'" in button
    assert "element.setAttribute(attribute, String(on))" in button
    pressed = _rules("components/button.css")[".button-secondary[aria-pressed='true'],\n.button-secondary[aria-expanded='true']"]
    assert pressed["background"] == "var(--lamp-hover-fill)" and pressed["border"] == "2px solid var(--lamp)"



def test_the_completion_top_bar_keeps_show_all_objects_in_place_and_inert():
    play, shell = _code(_ts("play.ts")), _code(_ts("shell.ts"))
    behind = play.split("export function mountPlayBehind(", 1)[1]
    assert "controls: HTMLElement" in behind.split("{", 1)[0]
    assert "const showAll = showAllToggle(sceneColumn)" in behind and "controls.append(showAll)" in behind
    assert "showAll.remove()" in behind
    assert "mountPlayBehind(sceneColumn, sideColumn, session, controls)" in _ts("completion.ts")
    assert "mountCompletion(element, sceneColumn, sideColumn, session, profile, bar.controls)" in shell
    # Unpressed (the toggle's default) and taking no input: the shell holds the whole top bar inert on #/done.
    assert "on:" not in play.split("return toggleButton({", 1)[1].split("})", 1)[0]
    assert "bar.element.inert = done" in shell


def test_show_all_draws_a_2px_dashed_outline_with_halo_no_fill_and_no_label_across_scene_changes():
    rules = _rules("scene/scene.css")
    rest = ".is-showing-all .hotspot:not(:hover, :focus-visible)"
    assert rules[f"{rest} .hotspot-reveal"] == {"opacity": "1"}
    assert rules[f"{rest} .hotspot-glow"] == {"opacity": "0"}  # no fill
    outline = rules[f"{rest} .hotspot-outline"]
    assert outline["stroke"] == "var(--hotspot-show-all)" and "stroke-dasharray" in outline
    assert rules[".hotspot-outline"]["stroke-width"] == "2px"
    assert rules[".hotspot-halo"] == {"fill": "none", "stroke": "var(--hotspot-halo)", "stroke-width": "4px"}
    assert "showAllStroke: '2px dashed {colors.hotspot-show-all}'" in design_text()
    # The class lives on the Scene column, which outlives every photo switch; the toggle never shows a label.
    play = _ts("play.ts")
    assert "sceneColumn.classList.toggle('is-showing-all', on)" in play
    assert "showLabel" not in _code(play) and "showChip" not in _code(play)


def test_the_first_room_welcome_shows_its_plain_tip_on_the_scrim_under_the_card():
    welcome = _ts("welcome.ts")
    assert "tip.className = 'greeting-tip body-sm'" in welcome and "tip.textContent = strings.showAllTip" in welcome
    assert "overlay.element.append(tip)" in welcome  # the scrim, outside the dialog card
    rules = _rules("components/greeting-overlay.css")
    assert rules[".greeting-tip"] == {"margin": "0", "color": "var(--text-muted)"}
    scrim = rules[".greeting-scrim"]
    assert scrim["flex-direction"] == "column" and scrim["gap"] == "var(--spacing-4)"
    overlay = design_text().split("  greeting-overlay:\n", 1)[1].split("\n  leave-room-confirmation:", 1)[0]
    assert "tip: '{typography.body-sm}'" in overlay and "tipColor: '{colors.text-muted}'" in overlay


def test_exactly_one_polite_live_region_and_only_the_welcome_sign_off_and_lock_outcomes_write_to_it():
    sources = {path: _code(text) for path, text in source_ts().items() if "/types/" not in path}
    assert sum(text.count("aria-live") for text in sources.values()) == 1
    writers = {path for path, text in sources.items() if "announce(" in text and not path.endswith("live-region.ts")}
    assert writers == {"web/src/welcome.ts", "web/src/completion.ts", "web/src/lock-outcomes.ts"}
    # The sign-off is a Guide line, so it is heard with its speaker prefix.
    assert "announce(`${strings.speakerGuide} ${said}`)" in sources["web/src/completion.ts"]
    assert "parts.push(held.render, notes.render, lockOutcomes(view, latest))" in _ts("play.ts")


def test_lock_outcomes_are_announced_once_each_never_checking_and_nothing_again_on_reload():
    outcomes = _ts("lock-outcomes.ts")
    assert "if (count > (heard.wrong_attempts[puzzle.id] ?? 0)) outcomes.push(fill(strings.lockNotThis, { n, count }))" in outcomes
    assert "if (state.locks_open.includes(puzzle.id) && !heard.locks_open.includes(puzzle.id)) {" in outcomes
    assert "outcomes.push(fill(strings.lockOpen, { n }))" in outcomes
    assert "const n = place + 1" in outcomes and "room.puzzles.flatMap((puzzle, place) => {" in outcomes
    # The first state is only heard: a reload, which starts from the stored state, announces nothing.
    assert "let heard = first" in outcomes and "heard = state" in outcomes
    assert "if (lines.length > 0) announce(lines.join(' '))" in outcomes
    # Read from server state only; "Checking" never reaches the region.
    assert "checking" not in _code(outcomes).lower() and "addEventListener" not in outcomes and ".post(" not in outcomes
    for name in ("components/code-field.ts", "components/wizard-notes.ts", "scene/hotspots.ts", "scene/index.ts"):
        assert "announce(" not in _code(_ts(name)), name


def test_keyboard_order_follows_the_page_and_there_are_no_single_key_shortcuts():
    shell, play, scene = _ts("shell.ts"), _ts("play.ts"), _ts("scene/index.ts")
    # Top bar, then the Scene column (Scene frame, Thumbnail strip, Inventory), then the side column (Wizard notes).
    assert "show(...(banner === null ? [] : [banner]), bar.element, body.element)" in shell
    assert "element.append(sceneColumn, sideColumn)" in shell
    assert "root.append(frame)" in scene and "sceneColumn.append(stripRow)" in play
    assert "stripRow.prepend(strip.element)" in scene and "stripRow.append(held.element)" in play
    assert "sideColumn.append(notes.element)" in play
    # The Inventory and the Wizard notes are Tab stops of their own, in that order after the strip.
    assert "element.tabIndex = 0" in _ts("components/inventory.ts")
    assert "element.tabIndex = 0" in _ts("components/wizard-notes.ts")
    # No positive tabindex anywhere, so the DOM order is the Tab order.
    for path, text in source_ts().items():
        code = _code(text)
        assert not re.search(r"tabIndex = [1-9]|'tabindex', '[1-9]", code), path
        assert "accessKey" not in code and "accesskey" not in code, path
        keys = set(re.findall(r"event\.key [!=]== '([^']+)'", code))
        assert keys <= {"Enter", "Tab", "Escape"}, f"{path} listens for {keys}"


def test_every_surface_control_keeps_the_two_tone_focus_ring():
    focus = _rules("tokens.css")[":focus-visible"]
    assert focus == {"outline": "2px solid var(--focus-ring)", "outline-offset": "2px",
                     "box-shadow": "0 0 0 2px var(--focus-ring-inner)"}
    for path, text in source_css().items():
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        assert not re.search(r"outline:\s*(none|0)", code), f"{path} removes the focus outline"


def test_every_fade_is_instant_under_reduced_motion():
    tokens = (WEB_SRC / "tokens.css").read_text()
    reduced = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", tokens, flags=re.DOTALL).group(1)
    for token in ("--motion-hover: 0ms;", "--motion-state: 0ms;", "--motion-overlay: 0ms;",
                  "transition-duration: 0ms !important;"):
        assert token in reduced
    for name in ("scene/scene.css", "components/greeting-overlay.css", "components/inventory.css",
                 "components/wizard-notes.css", "components/button.css"):
        for selector, declarations in _rules(name).items():
            for value in (v for k, v in declarations.items() if k.startswith("transition")):
                assert re.fullmatch(r"(?:[\w-]+ var\(--motion-\w+\) var\(--motion-ease\),? ?)+", value), (name, selector)


def test_the_new_pairs_meet_aa_and_every_state_carries_a_word():
    halo = _hex(PROPS["hotspot-halo"])[0]
    assert contrast(_hex(PROPS["hotspot-show-all"])[0], halo) >= 3  # the dashed outline over its halo (non-text)
    chrome = _hex(PROPS["chrome"])[0]
    pressed = _over("lamp-hover-fill", chrome)
    assert contrast(_hex(PROPS["lamp"])[0], pressed) >= 4.5  # the pressed toggle's label on its held fill
    assert contrast(_hex(PROPS["lamp"])[0], chrome) >= 3  # its 2 px lamp border (non-text)
    scrim = _over("scrim", _hex(PROPS["canvas"])[0])
    assert contrast(_hex(PROPS["text-muted"])[0], scrim) >= 4.5  # the tip on the scrim
    assert contrast(_hex(PROPS["ink"])[0], _hex(PROPS["parchment"])[0]) >= 4.5  # the label chip
    # The states are words, never color alone.
    strings = _strings()
    assert (strings["notThis"].split(" ·")[0], strings["open"], strings["current"]) == ("Not this", "Open", "Current")
    notes = _ts("components/wizard-notes.ts")
    assert "current.textContent = strings.current" in notes and "opened.textContent = strings.open" in notes
    assert "fill(strings.notThis, { n: attempts })" in notes


def test_the_outcomes_the_region_announces_come_from_the_server_state(client: TestClient, four_lock_room: Room):
    view = client.get(f"/api/rooms/{four_lock_room.id}").json()
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    clock = view["puzzles"][1]["id"]
    wrong = client.post(events, json={"type": "lock_input", "input": {"type": "code", "puzzle_id": clock, "code": "000"}})
    assert wrong.json()["wrong_attempts"][clock] == 1 and clock not in wrong.json()["locks_open"]  # Puzzle 2: not this, 1.
    found = client.post(events, json={"type": "click", "interactable_id": IX["key"]}).json()
    assert found["locks_open"] == [view["puzzles"][0]["id"]]  # Puzzle 1: open.
    opened = client.post(events, json={"type": "lock_input", "input": {"type": "code", "puzzle_id": clock, "code": "415"}})
    assert opened.json()["locks_open"][-1] == clock and opened.json()["wrong_attempts"][clock] == 1  # Puzzle 2: open.
    # A reload reads the same state, which the client only hears.
    assert client.get(f"/api/sessions/{session['id']}").json()["locks_open"] == opened.json()["locks_open"]
