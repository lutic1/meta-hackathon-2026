"""FR-16, UX-DR33, UX-DR80, UX-DR84, NFR-14: the Triggers panel, which shows why each Rung arrived.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the criteria are checked
in Chrome against the fixture rooms. tests/api/test_trigger_events.py checks the events the rows are read from.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]


PANEL = "components/triggers-panel.ts"


def test_the_triggers_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["triggers"].format(n=2) == "Triggers (2)"
    header = f"{strings['triggersNudge'].format(threshold=90)} {strings['triggersSpacing'].format(spacing=90)}"
    assert header == "Nudge after 90 s idle or 3 wrong attempts · next hint no sooner than 90 s"
    scaled = (f"{strings['triggersNudge'].format(threshold=15)} {strings['atOneX'].format(s=90)} "
              f"{strings['triggersSpacing'].format(spacing=15)} {strings['atOneX'].format(s=90)}")
    assert scaled == "Nudge after 15 s idle (90 s at 1×) or 3 wrong attempts · next hint no sooner than 15 s (90 s at 1×)"
    assert strings["thresholdDerived"] == "Set by how you played last time (kept in this browser)"
    assert strings["thresholdFresh"] == "Default for a first room"
    row = " · ".join([strings["rungNudge"].format(n=2), strings["idleSeconds"].format(s=92),
                      strings["wordedOnThisMac"].format(s="1.6")])
    assert row == "Puzzle 2 · Nudge · Idle 92 s · worded on this Mac · 1.6 s"
    assert (strings["threeWrongAttempts"], strings["loosenCard"], strings["asWritten"]) == (
        "3 wrong attempts", "Loosen card", "as written")
    assert strings["noHintChanges"] == "No hint changes yet."


def test_the_toggle_sits_under_the_hint_controls_collapsed_unless_a_disclosure_is_active():
    panel, play = _ts(PANEL), _ts("play.ts")
    assert "const open = !CUT_5 && session.disclosure.length > 0" in panel
    assert "toggleButton({\n        label: '',\n        state: 'expanded',\n        on: open,\n        controls: LIST_ID," in panel
    assert "list.element.hidden = !open" in panel and "list.element.hidden = !on" in panel
    # "Triggers ({n})" with n the number of Rung changes, its count in mono-sm, redrawn from every state.
    render = panel.split("  function render(state: SessionState): void {\n    const label", 1)[1].split("\n  }\n", 1)[0]
    assert "label.append(...withNumbers(fill(strings.triggers, { n: state.rung_changes.length })))" in render
    assert "toggle.replaceChildren(label)" in render
    assert "number.className = 'mono-sm'" in panel
    # In the Hint area's pinned lower part, after the helper line, drawn from every state the Play screen receives.
    assert "lower.append(ask, helper, triggers)" in _ts("components/hint-area.ts")
    assert "hints.triggers.append(triggers.element)" in play and "parts.push(triggers.render)" in play
    assert "triggersPanel(view, latest, currentPlace().profile, (open) => area.triggersOpen(open))" in play
    assert "element.classList.toggle('is-triggers-open', open)" in _ts("components/hint-area.ts")
    rules = _rules("components/triggers-panel.css")
    assert rules[".triggers-toggle"]["align-self"] == "flex-start"


def test_open_the_hint_area_may_grow_until_the_wizard_notes_reach_notes_min():
    rules = _rules("components/hint-area.css")
    grown = "calc(100% - var(--spacing-notes-min) - var(--spacing-5))"
    assert rules[".hint-area"]["max-height"] == f"min(var(--spacing-hint-area-max), {grown})"
    assert rules[".hint-area.is-triggers-open,\n.hint-area:has(> .hint-upper > .hint-cards:not([hidden]))"] == {"max-height": grown}
    assert _rules("shell.css")[".side-column"]["gap"] == "var(--spacing-5)"
    # Short of room the panel gives way first, to its newest row inside its padding (scrolled to), and only then does
    # the upper part scroll; the pinned controls never leave the tray, and the rows are never squeezed, so a wrapped
    # newest row stays whole.
    panel = _rules("components/triggers-panel.css")
    assert panel[".triggers"] == {"display": "contents"} and rules[".hint-lower,\n.hint-triggers"] == {"display": "contents"}
    assert rules[".hint-upper"]["flex"] == "1 1 auto" and rules[".hint-upper"]["min-height"] == "0"
    assert rules[".hint-area .triggers-panel"]["flex-shrink"] == "1000"
    assert rules[".hint-area .triggers-panel"]["min-height"] == "calc(1.45 * 14px)"
    assert panel[".triggers-toggle"]["flex"] == "none" and panel[".triggers-header,\n.triggers-empty"]["flex"] == "none"
    assert panel[".triggers-rows"]["flex"] == "none" and "min-height" not in panel[".triggers-rows"]
    assert "--spacing-notes-min: 280px;" in _ts("tokens.css")


def test_the_header_reads_the_servers_effective_values_with_their_1x_values_and_the_source():
    header = _function(_ts(PANEL), "triggersHeader")
    assert "seconds(thresholds.nudge_threshold_ms)" in header and "seconds(thresholds.rung_spacing_ms)" in header
    assert "oneX(thresholds.nudge_threshold_ms, thresholds.nudge_threshold_base_ms)" in header
    assert "oneX(\n    thresholds.rung_spacing_ms,\n    thresholds.rung_spacing_base_ms,\n  )" in header
    assert "(ms === base ? '' : ` ${fill(strings.atOneX, { s: seconds(base) })}`)" in header
    assert "thresholds.source === 'fresh' ? strings.thresholdFresh : strings.thresholdDerived" in header
    assert "[timing.textContent, source.textContent] = triggersHeader(thresholds)" in _ts(PANEL)


def test_no_web_module_computes_a_threshold_or_a_spacing():
    for path in WEB_SRC.rglob("*.ts"):
        code = _code(path.read_text())
        # `freshDerived()` writes `persistence: 0` into a session start; nothing reads it back for timing.
        for banned in (".persistence", "90000", "90_000", "135000", "60000", "demo_timescale /", "/ demo_timescale"):
            assert banned not in code, f"{path} holds {banned!r}"
    # The panel reads the timescale nowhere: a 1× value shows wherever the server's effective value differs from it.
    assert "demo_timescale" not in _code(_ts(PANEL))


def test_the_cause_is_read_off_the_events_triggered_by_names():
    cause = _function(_ts(PANEL), "triggerCause")
    assert "change.triggered_by.map((position) => events[position])" in cause
    # The shapes select_rung writes: 3 wrong attempts (plus the event that met the spacing), a lone Loosen card, or
    # Idle as (event,) or (anchor, event), whatever type the event is; a card that only met the spacing is not a cause.
    assert "if (named.length >= 3 || tick === undefined) return strings.threeWrongAttempts" in cause
    assert "if (named.length === 1 && tick.type === 'trickster_card') return strings.loosenCard" in cause
    assert "named.some(" not in cause
    assert "const from = named.length === 2 ? (named[0]?.t_ms ?? 0) : 0" in cause
    assert cause.rstrip().endswith("return fill(strings.idleSeconds, { s: Math.round((tick.t_ms - from) / 1000) })")


def test_each_row_names_the_puzzle_the_rung_the_cause_and_where_it_was_worded_never_its_text():
    row = _function(_ts(PANEL), "triggersRow")
    assert "fill(strings.wordedOnThisMac, { s: (change.phrasing_ms / 1000).toFixed(1) })" in row
    assert "change.phrased && change.phrasing_ms !== null" in row and ": strings.asWritten" in row
    assert "[rungLabel(n, change.rung), triggerCause(change, events), worded].join(strings.modeSeparator)" in row
    code = _code(_ts(PANEL))
    assert "change.text" not in code and ".text" not in code.replace("textContent", "")
    assert "solution" not in code


def test_rows_are_body_sm_with_mono_sm_numbers_newest_last_in_text_capped_and_kept_in_view():
    panel = _ts(PANEL)
    assert "row.className = 'triggers-row body-sm'" in panel and "header.className = 'triggers-header body-sm'" in panel
    assert "...state.rung_changes.map((change) => {" in panel  # session order: newest last
    assert "rows.scrollTop = rows.scrollHeight" in panel and "if (on) list.reveal()" in panel
    # Opened on load, the list is still detached when it first renders, so the Play screen reveals it once attached.
    assert "return { element, render, reveal: list.reveal }" in panel
    play = _ts("play.ts")
    attached = play.index("sideColumn.append(hints.element)")
    assert play.index("triggers.reveal()", attached) < play.index("holdInputs()", attached)
    assert "empty.textContent = strings.noHintChanges" in panel and "empty.hidden = drawn > 0" in panel
    rules = _rules("components/triggers-panel.css")
    assert rules[".triggers-rows"]["max-height"] == "var(--spacing-triggers-panel-max)"
    assert rules[".triggers-rows"]["overflow-y"] == "auto"
    assert rules[".triggers-row"]["color"] == "var(--text-muted)" and rules[".triggers-row:last-child"]["color"] == "var(--text)"
    assert rules[".triggers-panel"]["background"] == "var(--chrome)" and rules[".triggers-panel"]["color"] == "var(--text-muted)"
    assert rules[".triggers-panel"]["border-radius"] == "var(--rounded-md)"
    assert "--spacing-triggers-panel-max: 160px;" in _ts("tokens.css")


def test_rows_never_read_the_browser_clock_and_are_never_written_to_the_live_region():
    for name in (PANEL, "triggers-window.ts"):
        code = _code(_ts(name))
        for banned in ("Date", "performance", "announce(", "live-region", "aria-live"):
            assert banned not in code, f"{name} holds {banned!r}"


def test_under_cut_5_the_toggle_opens_a_second_window_polling_the_same_session():
    router, panel, window = _ts("router.ts"), _ts(PANEL), _ts("triggers-window.ts")
    assert "export const CUT_5: boolean = false" in router
    assert r"const SESSION_ROUTE = /^\/(play|done|triggers)\/([\w-]+)$/" in router
    assert "placeHref({ route: { name: 'triggers', sessionId: session.id }, profile })" in panel
    assert "window.open(href, `triggers-${session.id}`, 'popup,width=1024,height=480')" in panel
    assert "element.append(toggle, ...(CUT_5 ? [] : [list.element]))" in panel
    # The second window draws the same header and rows, from GET /sessions/<id> every 2000 ms.
    assert "list = triggersList(room)" in window and "list?.render(state)" in window
    assert "ticker.postMessage(POLL_MS)" in window and "getSession(session.id)" in window
    assert "export const POLL_MS = 2000" in _ts("play.ts")
    shell = _ts("shell.ts")
    assert "return { element, mount: () => mountTriggersWindow(element, session) }" in shell
    assert "if (route.name === 'view' || route.name === 'triggers') return null" in shell


def test_the_toggle_meets_the_accessibility_floor_and_every_panel_pair_is_in_the_contrast_table():
    button = _ts("components/button.ts")
    # A native button: reachable by Tab with the global focus ring, Enter and Space toggle it, aria-expanded says so.
    assert "const attribute = state === 'pressed' ? 'aria-pressed' : 'aria-expanded'" in button
    assert "element.setAttribute('aria-controls', controls)" in button and "tabIndex" not in _code(_ts(PANEL))
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in (("text", "chrome"), ("text-muted", "chrome"), ("lamp", "chrome-raised")):
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
