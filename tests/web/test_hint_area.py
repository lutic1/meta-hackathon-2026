"""FR-14, UX-DR29 to UX-DR32, UX-DR65, UX-DR70, UX-DR82: the Hint area, where the player asks the Guide and reads the
Rung line, and the opened Rungs it hands to the Wizard notes. Owner decision Oct 29: one button, "Get a hint for
Puzzle {n}", replaced the hint field; it counts down "Next hint in m:ss" while the next hint is not due.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the criteria are checked
in Chrome against the fixture rooms. The API checks post the exact body the client sends.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.rungs import RUNG_NAMES
from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import _strings

HINT_TEXT = "just tell me the answer"
PLAY_VIEW = ("play.ts", "components/hint-area.ts", "components/triggers-panel.ts", "components/wizard-notes.ts")


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
    assert strings["getHint"].format(n=2) == "Get a hint for Puzzle 2"
    assert strings["nextHintIn"].format(time="1:12") == "Next hint in 1:12"
    assert strings["guideThinking"] == "The Guide is thinking" and strings["askTheGuide"] == "Ask the Guide"
    assert strings["thinkingOnThisMac"] == "thinking on this Mac"
    labels = [strings[key].format(n=3) for key in ("puzzleHeading", "rungNudge", "rungDirection", "rungNearAnswer")]
    assert labels == ["Puzzle 3", "Puzzle 3 · Nudge", "Puzzle 3 · Direction", "Puzzle 3 · Near-answer"]
    assert strings["hintArea"] == "Hint area"
    for gone in ("hintPlaceholder", "hintFieldLabel", "hintHelper", "asking"):
        assert gone not in strings


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
    # The upper part scrolls inside the tray; the lower part, the hint controls, never does: its bands are the tray's
    # own flex items (display: contents), each flex none, 16 px under the upper part.
    assert rules[".hint-upper"]["overflow-y"] == "auto" and rules[".hint-upper"]["min-height"] == "0"
    assert rules[".hint-lower,\n.hint-triggers"] == {"display": "contents"}
    assert rules[".hint-ask"]["flex"] == "none"
    assert rules[".hint-area"]["gap"] == "var(--spacing-2)" and rules[".hint-upper"]["margin-bottom"] == "var(--spacing-2)"
    assert "overflow" not in " ".join(rules[".hint-ask"])
    # Pinned under the notes, in the side column, after them in the page and in the Tab order.
    built = play.split("const notes = wizardNotes(view, play)", 1)[1]
    assert built.index("sideColumn.append(notes.element)") < built.index("sideColumn.append(hints.element)")
    assert "hints = hintArea(view, play, frame.guide, notes.openedRungs, cardLog.open, () => triggers.reveal())" in play
    assert "parts.push(hints.render)" in play
    assert _rules("components/wizard-notes.css")[".wizard-notes"]["min-height"] == "var(--spacing-notes-min)"


def test_the_lower_part_holds_one_hint_button_across_the_tray_and_the_how_hints_work_slot():
    hint = _ts("components/hint-area.ts")
    assert "primaryButton({ label: askLabel, pendingLabel: strings.guideThinking, onActivate: request })" in hint
    assert "ask.append(button)" in hint
    assert "lower.append(ask, triggers)" in hint and "triggers.className = 'hint-triggers'" in hint
    assert "element.append(upper, lower)" in hint
    # No text field, no helper line: nothing typed exists to leave the browser.
    code = _code(hint)
    assert "createElement('input')" not in code and "placeholder" not in code and "hint-helper" not in code
    rules = _rules("components/hint-area.css")
    assert ".hint-field" not in rules and ".hint-helper" not in rules
    assert rules[".hint-ask"]["display"] == "flex" and rules[".hint-ask > .button-primary"]["flex"] == "1 1 auto"
    # The primary button re-reads a label function each time its request settles.
    button = _ts("components/button.ts")
    assert "label: string | (() => string)" in button
    assert "const settled = (): string => (typeof label === 'string' ? label : label())" in button
    assert "element.textContent = settled()" in button


def test_the_button_posts_one_hint_request_with_no_puzzle_id():
    hint = _code(_ts("components/hint-area.ts"))
    assert hint.count(".post(") == 1 and "play.post({ type: 'hint_request' })" in hint
    assert "puzzle_id:" not in hint.split("async function request(", 1)[1]
    button = _ts("components/button.ts")
    assert "if (pending) return" in button and "element.textContent = pendingLabel" in button


def test_while_in_flight_the_button_reads_the_guide_is_thinking_and_the_guides_ring_glows():
    request = _function(_ts("components/hint-area.ts"), "request")
    assert request.index("element.classList.add('is-asking')") < request.index("await play.post(")
    assert "} finally {\n      element.classList.remove('is-asking')" in request
    assert "} catch {\n      think(false)" in request
    # The Guide pulse: the lit ring, held with no animation, on the tray's transition tokens.
    rules = _rules("components/hint-area.css")
    ring = rules[".hint-area.is-glowing .rung-line .wizard-portrait,\n.hint-area.is-asking .rung-line .wizard-portrait"]
    assert ring == {"border-color": "var(--lamp)", "box-shadow": "var(--elevation-lamp-glow)"}
    assert "box-shadow var(--motion-hover) var(--motion-ease)" in rules[".rung-line .wizard-portrait"]["transition"]


def test_the_label_names_the_active_puzzle_and_counts_down_the_servers_wait():
    hint = _ts("components/hint-area.ts")
    label = _function(hint, "askLabel")
    assert "const n = place(latest.active_puzzle_id)" in label and "if (n === null) return strings.askTheGuide" in label
    assert "if (wait.seconds > 0 && wait.puzzleId === latest.active_puzzle_id) {" in label
    assert "return fill(strings.nextHintIn, { time: countdown(wait.seconds) })" in label
    assert label.rstrip().endswith("return fill(strings.getHint, { n })")
    # Counted down by the second from the reply's next_hint_ms, never from a clock reading.
    count = _function(hint, "countDown")
    assert "wait = { puzzleId: reply.puzzle_id, seconds: Math.ceil((reply.next_hint_ms ?? 0) / 1000) }" in count
    assert "setInterval(" in count and "}, 1000)" in count and "wait.seconds -= 1" in count
    assert "countDown(reply)" in _function(hint, "request")
    # m:ss: 90 s reads "1:30", 72 s "1:12", 5 s "0:05".
    assert "return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`" in hint
    for seconds, shown in ((90, "1:30"), (72, "1:12"), (5, "0:05")):
        assert f"{seconds // 60}:{seconds % 60:02d}" == shown
    # Every state relabels it (a solve moves the Active puzzle); a request in flight keeps "The Guide is thinking".
    assert "relabel()" in _function(hint, "render")
    assert "if (!button.hasAttribute('aria-busy')) button.textContent = askLabel()" in _function(hint, "relabel")


def test_no_triggers_or_nudge_after_text_in_the_default_play_view():
    strings = _strings()
    assert not any("Triggers" in value or "Nudge after" in value or "Idle {" in value for value in strings.values())
    for name in PLAY_VIEW:
        code = _code(_ts(name))
        assert "Triggers (" not in code and "Nudge after" not in code, name


def test_the_server_answers_the_clients_body_for_the_active_puzzle_with_a_real_hint_and_refuses_typed_text(client, four_lock_room):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    reply = client.post(events, json={"type": "hint_request"}).json()
    first = four_lock_room.puzzles[0]
    assert reply["active_puzzle_id"] == first.id  # the entry the Wizard notes mark "Current", the Puzzle the button names
    assert {k: reply["hint_reply"][k] for k in ("puzzle_id", "rung", "text")} == {
        "puzzle_id": first.id, "rung": 1, "text": first.rungs.nudge}  # asked at once: a real hint, never the No-hint line
    assert 0 < reply["hint_reply"]["next_hint_ms"] <= 90_000
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
    assert {k: asked["hint_reply"][k] for k in ("puzzle_id", "rung", "text")} == {"puzzle_id": clock, "rung": 1, "text": change["text"]}
    assert 0 < asked["hint_reply"]["next_hint_ms"] <= 90_000  # inside the spacing: the nudge again, and the wait
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
    fade = _ts("fade.ts")
    assert "return motionMs('--motion-state')" in fade and "value.endsWith('ms') ? 1 : 1000" in fade
    assert "import { fadeIn, stateFadeMs } from '../fade.ts'" in hint
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
    ring = rules[".hint-area.is-glowing .rung-line .wizard-portrait,\n.hint-area.is-asking .rung-line .wizard-portrait"]
    assert ring == {"border-color": "var(--lamp)", "box-shadow": "var(--elevation-lamp-glow)"}
    assert "--elevation-lamp-glow: 0 0 16px #E9A94B40;" in _ts("tokens.css")
    assert "--motion-hover: 150ms;" in _ts("tokens.css")  # lit for 150 ms, faded 150 ms each way: 300 ms in all


def test_a_rung_the_players_own_ask_opens_is_drawn_and_announced_once_by_the_reply_and_never_glows():
    # play.post hands the reply state to render() before request() reads it: while the ask is in flight, render
    # only counts the arrived rung_changes, so the reply alone announces "The Guide: ..." and presents with no glow.
    hint = _ts("components/hint-area.ts")
    request = _function(hint, "request")
    assert request.index("asking = true") < request.index("await play.post({ type: 'hint_request' })")
    assert "finally {\n      element.classList.remove('is-asking')\n      asking = false" in request
    render = _function(hint, "render")
    held_back = "if (newest === undefined || asking) return"
    assert render.index("heard = state.rung_changes.length") < render.index(held_back)
    assert render.index(held_back) < render.index("announce(") < render.index("present(changeLine(newest), true)")
    # The only arrived=true presentation is render's, so an ask never adds is-glowing.
    code = _code(hint)
    assert len(re.findall(r"(?<!function )glow\(\)", code)) == 1 and code.count(", true)") == 1


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
    assert "if (last !== undefined && !solved) draw(changeLine(last))" in start
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
    assert "onOpened(openedRungs(latest.rung_changes, line.shown, latest.trigger_events))" in _function(hint, "draw")
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


def test_the_button_is_named_for_the_active_puzzle_and_every_line_goes_to_the_one_live_region():
    hint = _ts("components/hint-area.ts")
    assert "fill(strings.getHint, { n })" in _function(hint, "askLabel")
    assert "aria-live" not in _code(hint) and "from '../live-region.ts'" in hint
    region = _ts("live-region.ts")
    assert "liveRegion().textContent = queued.join(' ')" in region  # lines drawn together are heard together
    # Reachable by Tab: a native button, no tabindex games.
    assert "tabIndex" not in hint


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


def test_a_reload_draws_the_newest_rung_only_while_its_puzzle_is_still_locked():
    """Replay Oct 29: after a reload the Rung line showed "Puzzle 2 · Direction" next to Puzzle 2 Solved, until a new
    Rung arrived. In live play the unlock aside replaces that line, so a reload leaves the line empty instead, and the
    solved Puzzle's Rungs stay in its Wizard notes entry."""
    hint = _code(_ts("components/hint-area.ts"))
    tail = hint.split("\n  render(latest)\n", 1)[1].split("\n  return {", 1)[0]
    assert "const solved = last !== undefined && latest.locks_open.includes(last.puzzle_id)" in tail
    assert "if (last !== undefined && !solved) draw(changeLine(last))" in tail
    # Nothing on the line: every Rung change goes to the notes, and the line stays hidden.
    assert "onOpened(openedRungs(latest.rung_changes, null, latest.trigger_events))" in tail
    assert tail.index("if (last !== undefined && !solved)") < tail.index("else if (play.openingLine !== null)")
