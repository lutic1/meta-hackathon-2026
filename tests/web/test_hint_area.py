"""FR-14, UX-DR29 to UX-DR32, UX-DR65, UX-DR70, UX-DR82: the Hint area, where the player asks the Guide and reads the
Rung line, and the opened Rungs it hands to the Wizard notes.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the criteria are checked
in Chrome against the fixture rooms. The API checks post the exact body the client sends.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import NO_HINT_LINE
from src.domain.rungs import RUNG_NAMES
from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import _strings

HINT_TEXT = "just tell me the answer"


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n  }\n", 1)[0]


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def test_the_hint_area_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["hintPlaceholder"] == "Stuck? Ask the Guide for a hint"
    assert strings["askTheGuide"] == "Ask the Guide" and strings["asking"] == "Asking"
    assert strings["hintFieldLabel"].format(n=2) == "Ask the Guide for a hint on Puzzle 2"
    assert strings["hintHelper"] == "Your words stay in this browser. The Guide only hears that you asked."
    assert strings["thinkingOnThisMac"] == "thinking on this Mac"
    labels = [strings[key].format(n=3) for key in ("puzzleHeading", "rungNudge", "rungDirection", "rungNearAnswer")]
    assert labels == ["Puzzle 3", "Puzzle 3 · Nudge", "Puzzle 3 · Direction", "Puzzle 3 · Near-answer"]
    assert strings["hintArea"] == "Hint area"


def test_the_rung_labels_follow_the_rung_numbers_the_server_counts():
    hint = _ts("components/hint-area.ts")
    # Rung n is RUNG_NAMES[n - 1]; rung 0 (no Rung open) is the No-hint line, labelled with its Puzzle alone.
    assert RUNG_NAMES == ("nudge", "direction", "near_answer")
    assert "const RUNG_LABELS = [strings.puzzleHeading, strings.rungNudge, strings.rungDirection, strings.rungNearAnswer]" in hint
    assert "return fill(RUNG_LABELS[rung] ?? strings.puzzleHeading, { n })" in hint


def test_the_tray_is_chrome_raised_up_to_hint_area_max_pinned_under_the_wizard_notes():
    play = _ts("play.ts")
    rules = _rules("components/hint-area.css")
    tray = rules[".hint-area"]
    assert tray["background"] == "var(--chrome-raised)" and tray["color"] == "var(--text)"
    # Up to hint-area-max, and on a short window no further than leaves the Wizard notes notes-min.
    assert tray["max-height"] == (
        "min(var(--spacing-hint-area-max), calc(100% - var(--spacing-notes-min) - var(--spacing-5)))"
    )
    assert tray["flex"] == "none"
    assert tray["padding"] == "var(--spacing-4)" and tray["border-radius"] == "var(--rounded-lg)"
    assert "--spacing-hint-area-max: 320px;" in _ts("tokens.css")
    # The upper part scrolls inside the tray; the lower part, the hint controls, never does.
    assert rules[".hint-upper"]["overflow-y"] == "auto" and rules[".hint-upper"]["min-height"] == "0"
    assert rules[".hint-lower"]["flex"] == "none" and "overflow" not in " ".join(rules[".hint-lower"])
    # Pinned under the notes, in the side column, after them in the page and in the Tab order.
    built = play.split("const notes = wizardNotes(view, play)", 1)[1]
    assert built.index("sideColumn.append(notes.element)") < built.index("sideColumn.append(hints.element)")
    assert "hints = hintArea(view, play, frame.guide, notes.openedRungs)" in play
    assert "parts.push(hints.render)" in play
    assert _rules("components/wizard-notes.css")[".wizard-notes"]["min-height"] == "var(--spacing-notes-min)"


def test_the_lower_part_holds_the_field_ask_the_guide_the_permanent_helper_line_and_the_triggers_slot():
    hint = _ts("components/hint-area.ts")
    assert "field.placeholder = strings.hintPlaceholder" in hint
    assert "primaryButton({ label: strings.askTheGuide, pendingLabel: strings.asking, onActivate: request })" in hint
    assert "helper.textContent = strings.hintHelper" in hint and "field.setAttribute('aria-describedby', helper.id)" in hint
    assert "lower.append(ask, helper, triggers)" in hint and "triggers.className = 'hint-triggers'" in hint
    assert "element.append(upper, lower)" in hint
    rules = _rules("components/hint-area.css")
    field = rules[".hint-field"]
    assert field["height"] == "44px" and field["background"] == "var(--chrome)"
    assert field["border"] == "1px solid var(--hairline)" and field["border-radius"] == "var(--rounded-md)"
    assert "field.className = 'hint-field body-sm'" in hint and "helper body-sm" in hint
    assert rules[".hint-field::placeholder"]["color"] == "var(--text-muted)"
    assert rules[".hint-helper"]["color"] == "var(--text-muted)"
    assert rules[".hint-ask"]["display"] == "flex"  # the field and the button side by side


def test_enter_or_the_button_posts_one_hint_request_with_no_puzzle_id_and_never_the_typed_text():
    hint = _code(_ts("components/hint-area.ts"))
    assert hint.count(".post(") == 1 and "play.post({ type: 'hint_request' })" in hint
    assert "puzzle_id:" not in hint.split("async function request(", 1)[1]
    # Enter clicks the button, which ignores every activation while its request is in flight.
    keydown = hint.split("field.addEventListener('keydown', (event) => {", 1)[1].split("})", 1)[0]
    assert "if (event.key !== 'Enter') return" in keydown and "button.click()" in keydown
    button = _ts("components/button.ts")
    assert "if (pending) return" in button and "element.textContent = pendingLabel" in button
    # The typed text is never read: the field's value is only cleared, it has no name and sits in no form.
    assert re.findall(r"field\.value[^\n]*", hint) == ["field.value = ''"]
    assert "field.name" not in hint and "<form" not in hint and "'form'" not in hint
    # An empty field still sends: nothing checks what was typed before posting.
    assert "trim()" not in _function(hint, "request") and "length" not in _function(hint, "request")


def test_while_in_flight_the_field_is_read_only_with_the_text_and_clears_when_the_reply_lands():
    request = _function(_ts("components/hint-area.ts"), "request")
    assert request.index("field.readOnly = true") < request.index("await play.post(")
    assert request.index("await play.post(") < request.index("field.value = ''")
    assert "} finally {\n      field.readOnly = false" in request
    # A request that never reached the server keeps the words in the field.
    assert "} catch {\n      think(false)" in request


def test_the_server_answers_the_clients_body_for_the_active_puzzle_and_refuses_typed_text(client, four_lock_room):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    reply = client.post(events, json={"type": "hint_request"}).json()
    assert reply["hint_reply"] == {"puzzle_id": reply["active_puzzle_id"], "rung": 0, "text": NO_HINT_LINE}
    assert reply["active_puzzle_id"] == four_lock_room.puzzles[0].id  # the entry the Wizard notes mark "Current"
    # A body carrying the typed words is malformed: nothing typed can ever count.
    refused = client.post(events, json={"type": "hint_request", "text": HINT_TEXT})
    assert refused.status_code == 422
    assert HINT_TEXT not in client.get(f"/api/sessions/{session['id']}").text


def test_three_wrong_codes_release_a_rung_change_whose_text_the_rung_line_shows(client, four_lock_room):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    clock = four_lock_room.puzzles[1].id
    for _ in range(3):
        state = client.post(events, json={"type": "lock_input", "input": {"type": "code", "puzzle_id": clock, "code": "000"}}).json()
    change = state["rung_changes"][-1]
    assert (change["puzzle_id"], change["rung"]) == (clock, 1)  # "Puzzle 2 · Nudge"
    asked = client.post(events, json={"type": "hint_request"}).json()
    assert asked["hint_reply"] == {"puzzle_id": clock, "rung": 1, "text": change["text"]}
    # A reload reads the same words from rung_changes[]; PlayView carries no Rung text at all.
    assert client.get(f"/api/sessions/{session['id']}").json()["rung_changes"] == state["rung_changes"]
    assert change["text"] not in client.get(f"/api/rooms/{four_lock_room.id}").text


def test_the_rung_line_is_the_guide_portrait_the_lamp_label_and_the_wizard_line_with_no_verbatim_badge():
    hint = _ts("components/hint-area.ts")
    assert "const portrait = wizardPortrait('guide', 48)" in hint
    assert "paragraph('rung-label label')" in hint and "paragraph('rung-text wizard-line')" in hint
    assert "said.replaceChildren(speakerPrefix('guide'), line.text)" in hint
    rules = _rules("components/hint-area.css")
    assert rules[".rung-line"]["grid-template-columns"] == "48px minmax(0, 1fr)"
    assert rules[".rung-label"]["color"] == "var(--lamp)"
    # Phrased and verbatim Rungs look identical: nothing here reads `phrased` or names a badge.
    code = _code(hint)
    assert "phrased" not in code and "verbatim" not in code.lower() and "badge" not in code.lower()
    assert "alt = ''" in _ts("wizards/portrait.ts")  # the portrait is decorative


def test_every_new_line_fades_the_shown_one_out_and_in_and_a_reply_never_glows():
    hint = _ts("components/hint-area.ts")
    present = _function(hint, "present")
    assert "words.classList.add('is-leaving')" in present and "setTimeout(swap, fade)" in present
    assert "fadeIn(words)" in present and "if (arrived) glow()" in present
    assert "const fade = rungLine.hidden ? 0 : stateFadeMs()" in present
    assert "getPropertyValue('--motion-state')" in hint and "value.endsWith('ms') ? 1 : 1000" in hint
    request = _function(hint, "request")
    assert "present(replyLine(reply), false)" in request  # the player asked: no glow
    assert "announce(`${strings.speakerGuide} ${reply.text}`)" in request  # announced again, even a repeat
    rules = _rules("components/hint-area.css")
    assert rules[".rung-line-words"]["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".rung-line-words.is-leaving,\n.rung-line-words.is-arriving"] == {"opacity": "0"}


def test_a_rung_change_from_the_server_shows_its_own_text_with_one_glow_and_one_announcement():
    hint = _ts("components/hint-area.ts")
    render = _function(hint, "render")
    assert "const arrived = state.rung_changes.slice(heard)" in render and "heard = state.rung_changes.length" in render
    assert "announce(arrived.map((change) => `${strings.speakerGuide} ${change.text}`).join(' '))" in render
    assert "present(changeLine(newest), true)" in render
    assert "text: change.text" in hint  # the words rung_changes[] carries, never PlayView
    # The client never computes a Rung or reads the clock for hint timing.
    code = _code(hint)
    for banned in ("Date", "performance.now", "thresholds", "nudge_threshold", "current_rung", "rungs_used"):
        assert banned not in code, banned
    assert "export const GLOW_MS = 150" in hint and "export const GLOW_REDUCED_MS = 2000" in hint
    glow = _function(hint, "glow")
    assert "matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS" in glow
    assert "element.classList.add('is-glowing')" in glow and "element.classList.remove('is-glowing'), hold)" in glow
    rules = _rules("components/hint-area.css")
    assert rules[".hint-area"]["transition"] == "box-shadow var(--motion-hover) var(--motion-ease)"
    assert rules[".hint-area.is-glowing"]["box-shadow"] == "var(--elevation-lamp-glow)"
    ring = rules[".hint-area.is-glowing .rung-line .wizard-portrait"]
    assert ring == {"border-color": "var(--lamp)", "box-shadow": "var(--elevation-lamp-glow)"}
    assert "--elevation-lamp-glow: 0 0 16px #E9A94B40;" in _ts("tokens.css")
    assert "--motion-hover: 150ms;" in _ts("tokens.css")  # lit for 150 ms, faded 150 ms each way: 300 ms in all


def test_the_thinking_state_shows_only_for_ollama_as_a_static_lamp_ring_and_a_pending_label():
    hint = _ts("components/hint-area.ts")
    assert "if (guide === 'ollama') think(true)" in _function(hint, "request")
    assert "thinking.textContent = strings.thinkingOnThisMac" in hint and "paragraph('rung-thinking label')" in hint
    rules = _rules("components/hint-area.css")
    assert rules[".rung-thinking"]["color"] == "var(--pending)"  # pending-ink is for paper only
    assert rules[".rung-line.is-thinking .wizard-portrait"] == {"border-color": "var(--lamp)"}
    # A rung_change from the poll has no thinking state before it, and nothing pulses.
    assert "think(true)" not in _function(hint, "render")
    css = (WEB_SRC / "components/hint-area.css").read_text()
    assert not re.search(r"animation|@keyframes", css)
    assert "guide: Meta['guide']" in hint and "frame.guide" in _ts("play.ts")


def test_the_first_state_is_only_read_so_a_reload_rebuilds_the_rungs_and_announces_nothing():
    hint = _ts("components/hint-area.ts")
    assert "let heard = latest.rung_changes.length" in hint
    start = hint.split("  render(latest)\n", 1)[1]
    assert "const last = latest.rung_changes.at(-1)" in start
    assert "if (last !== undefined) draw(changeLine(last))" in start
    assert "else if (play.openingLine !== null) draw({ label: null, text: play.openingLine, shown: null })" in start
    # draw never fades, glows or announces.
    draw = _function(hint, "draw")
    assert "announce(" not in draw and "glow(" not in draw and "fadeIn(" not in draw


def test_the_opening_line_sits_as_the_first_guide_line_after_begin_never_announced():
    play, hint = _ts("play.ts"), _ts("components/hint-area.ts")
    begin = play.split("[frame.topBar, sceneColumn, sideColumn], (line) => {", 1)[1].split("\n      })", 1)[0]
    assert "hints?.opening(line)" in begin
    opening = _function(hint, "opening")
    assert "if (rungLine.hidden) present({ label: null, text: line, shown: null }, false)" in opening
    assert "announce(" not in opening
    # Empty: the controls only, the Rung line hidden until a line arrives.
    assert "rungLine.hidden = true" in hint
    assert _rules("components/hint-area.css")[".rung-line[hidden]"] == {"display": "none"}


def test_the_line_the_rung_line_gives_up_moves_into_its_puzzles_opened_rungs():
    hint, notes = _ts("components/hint-area.ts"), _ts("components/wizard-notes.ts")
    assert "onOpened(openedRungs(latest.rung_changes, line.shown))" in _function(hint, "draw")
    opened = hint.split("export function openedRungs(", 1)[1].split("\n}\n", 1)[0]
    assert "change.puzzle_id !== shown.puzzle_id || change.rung !== shown.rung" in opened
    # The No-hint line and the opening line are no Rung, so they keep nothing back.
    assert "const shown = puzzle_id !== null && rung > 0 ? { puzzle_id, rung } : null" in hint
    # Each entry draws its own Puzzle's opened Rungs: Guide portrait, label and the rung_changes[] words.
    assert "const mine = lines.filter((line) => line.puzzle_id === puzzle.id)" in notes
    assert "wizardPortrait('guide', 32)" in notes and "rungLabel(n, line.rung)" in notes
    assert "paragraph('wizard-line', speakerPrefix('guide'), line.text)" in notes
    assert "made.rungs(opened)" in notes and "for (const made of entries.values()) made.rungs(lines)" in notes
    rules = _rules("components/wizard-notes.css")
    assert rules[".notes-rung"]["grid-template-columns"] == "32px minmax(0, 1fr)"
    assert rules[".notes-rung-label"]["color"] == "var(--ink-muted)"


def test_the_field_is_labelled_for_the_active_puzzle_and_every_line_goes_to_the_one_live_region():
    hint = _ts("components/hint-area.ts")
    render = _function(hint, "render")
    assert "const n = place(state.active_puzzle_id)" in render
    assert "fill(strings.hintFieldLabel, { n })" in render
    assert "aria-live" not in _code(hint) and "from '../live-region.ts'" in hint
    region = _ts("live-region.ts")
    assert "liveRegion().textContent = queued.join(' ')" in region  # lines drawn together are heard together
    # Reachable by Tab: a native input and button, no tabindex games.
    assert "document.createElement('input')" in hint and "tabIndex" not in hint


def test_every_hint_area_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    # The label and the line on the tray, the thinking label (pending = text-muted), the field and its placeholder,
    # the helper line, and an opened Rung on the parchment.
    pairs = {("text", "chrome-raised"), ("lamp", "chrome-raised"), ("text-muted", "chrome-raised"),
             ("text", "chrome"), ("text-muted", "chrome"), ("ink", "parchment"), ("ink-muted", "parchment"),
             ("on-lamp", "lamp")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
