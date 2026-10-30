"""FR-16, UX-DR33, UX-DR80, UX-DR84, NFR-14: "How hints work", which says how the chest's hints work and why each
Rung arrived, in player words (owner decision Oct 29: it replaced the "Triggers ({n})" toggle and its header; story
mode moved it into the Card log with one plain line).

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


def test_the_how_hints_work_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["howHintsWork"] == "How hints work"
    assert strings["hintsExplained"] == ("The chest holds 2 hints for the whole game. Each one opens the next hint for "
                                         "the riddle you're on. Nothing opens on its own.")
    assert "thresholdDerived" not in strings and "noHintsYet" not in strings
    row = strings["hintRow"].format(n=2, k=1, cause=strings["afterThreeWrongTries"])
    assert row == "Puzzle 2, hint 1, after three wrong tries"
    quiet = strings["hintRow"].format(n=2, k=1, cause=strings["afterQuietSeconds"].format(s=92))
    assert f"{quiet}, {strings['wordedOnThisMac']}" == "Puzzle 2, hint 1, after 92 quiet seconds, worded on this Mac"
    assert (strings["whenYouAsked"], strings["openedByTrickster"]) == ("when you asked", "opened early by the Trickster")


def test_how_hints_work_sits_in_the_card_log_under_the_cards_with_its_one_plain_line():
    panel, log, dialog = _ts(PANEL), _ts("card-log.ts"), _ts("components/card-log.ts")
    code = _code(panel)
    assert "auto" not in code and "disclosure" not in code
    assert "header.textContent = strings.hintsExplained" in panel and "element.append(header, rows)" in panel
    assert "hintsHeading.textContent = strings.howHintsWork" in dialog
    assert "dialog.append(head, list, empty, hintsHeading, hints.element)" in dialog
    # Drawn when the log opens and from every state while it shows.
    assert "cardLogDialog(room, howHintsWork(room, frame.play.id, currentPlace().profile))" in log
    assert "dialog.hints(frame.play.state())" in log and "shown.dialog.hints(state)" in log
    assert "triggers" not in _code(_ts("play.ts"))  # nothing of it is left on the play screen


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
    # The shapes select_rung writes: 3 wrong attempts (plus the event that met the spacing), a lone Loosen card, a lone
    # Hint request (an ask opens its Rung alone), or Idle as (event,) or (anchor, event), whatever type the event is.
    assert "if (named.length >= 3 || tick === undefined) return strings.afterThreeWrongTries" in cause
    assert "if (named.length === 1 && tick.type === 'trickster_card') return strings.openedByTrickster" in cause
    assert "if (named.length === 1 && tick.type === 'hint_request') return strings.whenYouAsked" in cause
    assert "named.some(" not in cause
    assert "const from = named.length === 2 ? (named[0]?.t_ms ?? 0) : 0" in cause
    assert cause.rstrip().endswith("return fill(strings.afterQuietSeconds, { s: Math.round((tick.t_ms - from) / 1000) })")


def test_each_row_names_the_puzzle_the_hint_number_the_cause_and_where_it_was_worded_never_its_text():
    row = _function(_ts(PANEL), "triggersRow")
    assert "const row = fill(strings.hintRow, { n, k: change.rung, cause: triggerCause(change, events) })" in row
    assert "return change.phrased ? `${row}, ${strings.wordedOnThisMac}` : row" in row
    code = _code(_ts(PANEL))
    assert "change.text" not in code and ".text" not in code.replace("textContent", "")
    assert "solution" not in code


def test_rows_are_body_sm_with_mono_sm_numbers_newest_last_in_text_capped_and_kept_in_view():
    panel = _ts(PANEL)
    assert "row.className = 'triggers-row body-sm'" in panel and "header.className = 'triggers-header body-sm'" in panel
    assert "...state.rung_changes.map((change) => {" in panel  # session order: newest last
    assert "rows.scrollTop = rows.scrollHeight" in panel and "rows.hidden = drawn === 0" in panel
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


def test_under_cut_5_the_card_log_opens_it_in_a_second_window_polling_the_same_session():
    router, panel, window = _ts("router.ts"), _ts(PANEL), _ts("triggers-window.ts")
    assert "export const CUT_5: boolean = false" in router
    assert r"const SESSION_ROUTE = /^\/(play|done|triggers)\/([\w-]+)$/" in router
    opened = panel.split("export function howHintsWork(", 1)[1]
    assert "if (!CUT_5) return list" in opened
    assert "placeHref({ route: { name: 'triggers', sessionId }, profile })" in opened
    assert "window.open(href, `triggers-${sessionId}`, 'popup,width=1024,height=480')" in opened
    # The second window draws the same header and rows, from GET /sessions/<id> every 2000 ms.
    assert "list = triggersList(room)" in window and "list?.render(state)" in window
    assert "ticker.postMessage(POLL_MS)" in window and "getSession(session.id)" in window
    assert "export const POLL_MS = 2000" in _ts("play.ts")
    shell = _ts("shell.ts")
    assert "return { element, mount: () => mountTriggersWindow(element, session) }" in shell
    assert "if (route.name === 'view' || route.name === 'triggers') return null" in shell


def test_the_panel_takes_no_focus_and_every_panel_pair_is_in_the_contrast_table():
    assert "tabIndex" not in _code(_ts(PANEL))
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in (("text", "chrome"), ("text-muted", "chrome"), ("text-muted", "chrome-raised"), ("text", "chrome-raised")):
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"


def test_reveal_scrolls_only_the_rows_so_the_opening_lines_never_clip():
    """Replay Oct 29: at 1024 x 768 the open panel scrolled itself 28 px, hiding the start of its first line."""
    reveal = _code(_ts(PANEL)).split("function reveal(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "rows.scrollTop = rows.scrollHeight" in reveal
    assert "element.scrollTop" not in reveal
