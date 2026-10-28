"""FR-19, UX-DR43, UX-DR7, UX-DR71, UX-DR8: the Card log, a modal dialog that reopens every Card of the play-through
from the session state's `cards[]`, opened from the top bar or from the Hint area's "{n} more in the Card log" link.

The client has no test runner, so the checks read the TypeScript and the stylesheets; `npm run build` and
`tsc --noEmit` prove they compile, and the criteria are checked in Chrome against the fixture rooms. The API check
reads the polled state the Card log is built from.
"""

import re
from pathlib import Path

from src.domain.schema import Room
from tests.api.test_sessions import Ticker, click, code, start
from tests.api.test_trickster_route import (
    app_client,
    open_window,
    proposals_dir,
    state_of,
    trickster,
)
from tests.web.design import WEB_SRC, css_rules, design_text, source_ts
from tests.web.test_contrast import PROPS, _hex, contrast
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _token() -> str:
    return design_text().split("  card-log:\n", 1)[1].split("\n  completion-sheet:", 1)[0]


def _opened() -> str:
    """The body of the Card log's `open`."""
    return _code(_ts("card-log.ts")).split("function open(opener: HTMLElement): void {", 1)[1].split("\n  frame.play", 1)[0]


# --- Opening it ------------------------------------------------------------------------------------


def test_the_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["cardLog"] == "Card log"
    assert strings["cardLogEmpty"] == "No cards yet in this play-through."
    assert strings["closeCardLog"] == "Close"
    assert strings["moreInCardLog"].format(n=3) == "3 more in the Card log"


def test_the_top_bar_button_sits_between_show_all_objects_and_leave_room_and_opens_the_log():
    play = _code(_ts("play.ts"))
    assert "frame.controls.append(showAll, cardLog.button, leaveRoom.button)" in play
    log = _code(_ts("card-log.ts"))
    assert "const button = secondaryButton({ label: strings.cardLog, onActivate })" in log
    assert "button.setAttribute('aria-haspopup', 'dialog')" in log
    assert "const button = cardLogButton(() => open(button))" in log
    # Gone with the Play screen, and with a missing Room, whose card replaces the body.
    assert play.count("cardLog.unmount()") == 2
    assert "cardLog.unmount()" in play.split("function roomMissing(gone: RoomGone): void {", 1)[1].split("\n  }\n", 1)[0]


def test_the_hint_area_link_opens_the_log_and_takes_focus_back():
    hint = _code(_ts("components/hint-area.ts"))
    assert "openCardLog: (opener: HTMLElement) => void," in hint
    assert "const more = document.createElement('button')" in hint and "more.type = 'button'" in hint
    assert "more.setAttribute('aria-haspopup', 'dialog')" in hint
    assert "more.addEventListener('click', () => openCardLog(more))" in hint
    assert "hints = hintArea(view, play, frame.guide, notes.openedRungs, cardLog.open, () => triggers.reveal())" in _code(_ts("play.ts"))
    # A link on dark: lamp, underlined, no button chrome, hidden with the count when no Card is behind it.
    more = _rules("components/hint-area.css")[".hint-more"]
    assert more["color"] == "var(--lamp)" and more["text-decoration"] == "underline"
    assert more["background"] == "transparent" and more["border"] == "0" and "display" not in more


def test_the_dialog_is_360px_chrome_at_most_480px_scrolling_under_the_card_log_button_over_the_scrim():
    token = _token()
    rules = _rules("components/card-log.css")
    log = rules[".card-log"]
    assert "width: 360px" in token and log["width"] == "360px"
    assert log["max-height"] == "min(480px, calc(100% - 2 * var(--spacing-2)))" and log["overflow-y"] == "auto"
    assert "background: '{colors.chrome}'" in token and log["background"] == "var(--chrome)"
    assert log["color"] == "var(--text)"
    assert "radius: '{rounded.lg}'" in token and log["border-radius"] == "var(--rounded-lg)"
    assert "shadow: '{elevation.overlay}'" in token and log["box-shadow"] == "var(--elevation-overlay)"
    # Anchored: just under the top bar, its right edge lined up with the button's, measured on open and on resize.
    assert log["position"] == "absolute" and log["top"] == "var(--spacing-2)"
    opened = _opened()
    assert "frame.body.getBoundingClientRect().right - button.getBoundingClientRect().right" in opened
    assert "dialog.dialog.style.right = `${Math.max(0, right)}px`" in opened
    assert "window.addEventListener('resize', anchor)" in opened and "window.removeEventListener('resize', anchor)" in opened
    # The scrim covers the page body only, so the Disclosure banner and the top bar stay undimmed.
    scrim = rules[".card-log-scrim"]
    assert "scrim: '{colors.scrim}'" in token and scrim["background"] == "var(--scrim)"
    assert scrim["position"] == "absolute" and scrim["inset"] == "0"
    assert _rules("shell.css")[".play-layout"]["position"] == "relative"
    assert "frame.body.append(dialog.element)" in opened and "body: frame.body" in _code(_ts("play.ts"))


def test_it_enters_with_a_300ms_fade_that_is_instant_under_reduced_motion():
    rules = _rules("components/card-log.css")
    assert rules[".card-log"]["transition"] == "opacity var(--motion-overlay) var(--motion-ease)"
    assert rules[".card-log.is-arriving"] == {"opacity": "0"}
    assert "show: () => fadeIn(dialog)" in _code(_ts("components/card-log.ts"))
    opened = _opened()
    assert opened.index("frame.body.append(dialog.element)") < opened.index("dialog.show()")
    # No layout read between the append and the fade, or the dialog is drawn opaque and never fades: anchor first.
    assert opened.index("anchor()") < opened.index("frame.body.append(dialog.element)")
    tokens = _ts("tokens.css")
    assert "--motion-overlay: 300ms;" in tokens and "--motion-overlay: 0ms;" in tokens


# --- What it lists -----------------------------------------------------------------------------------


def test_it_lists_every_entry_of_cards_oldest_first_and_takes_the_cards_a_later_state_brings():
    opened = _opened()
    assert "const cards = frame.play.state().cards" in opened and "dialog.add(cards)" in opened
    log = _code(_ts("card-log.ts"))
    # The Hint area's dismissals never reach it: it reads the server's cards[] alone.
    assert "frame.play.onState((state) => {" in log
    assert "shown.dialog.add(state.cards.slice(shown.listed))" in log and "shown.listed = state.cards.length" in log
    assert "dismiss" not in log
    dialog = _code(_ts("components/card-log.ts"))
    assert "list.append(...cards.map((card) => row(room, card)))" in dialog
    assert "const list = document.createElement('ol')" in dialog


def test_each_row_is_built_from_the_card_fields_alone_with_no_introduction():
    dialog = _code(_ts("components/card-log.ts"))
    row = dialog.split("function row(room: PlayView, card: TricksterCard): HTMLLIElement {", 1)[1].split("\n}\n", 1)[0]
    assert "const text = cardText(room, card)" in row  # the same words as the Card, from the projection (1.5)
    assert "paragraph('card-log-sentence wizard-line', speakerPrefix('trickster'), text.sentence)" in row
    assert "paragraph('card-log-outcome label', text.label)" in row
    assert "paragraph('card-log-refusal body-sm', text.refusal.proposed)" in row
    assert "paragraph('card-log-refusal body-sm', text.refusal.reason)" in row
    assert "paragraph('card-log-time mono-sm', formatElapsed(card.t_ms))" in row
    assert "element.append(wizardPortrait('trickster', 24), words)" in row
    assert set(re.findall(r"(?<![\w-])card\.(\w+)", row)) == {"t_ms"}
    for intro in ("tricksterRole", "tricksterVoice", "strings.trickster)", "first"):
        assert intro not in row, intro
    order = [row.index(part) for part in ("text.sentence", "text.label", "text.refusal.proposed", "card.t_ms")]
    assert order == sorted(order)
    token = _token()
    for line in ("sentence: '{typography.wizard-line}'", "outcome: '{typography.label}'", "time: '{typography.mono-sm}'",
                 "portrait: 24px"):
        assert line in token, line


def test_with_no_cards_it_reads_the_empty_line_in_text_muted():
    dialog = _code(_ts("components/card-log.ts"))
    assert "const empty = paragraph('card-log-empty body-sm', strings.cardLogEmpty)" in dialog
    assert "list.hidden = list.children.length === 0" in dialog and "empty.hidden = !list.hidden" in dialog
    rules = _rules("components/card-log.css")
    assert rules[".card-log-time,\n.card-log-empty"]["color"] == "var(--text-muted)"
    assert rules[".card-log-empty[hidden]"] == {"display": "none"} and rules[".card-log-list[hidden]"] == {"display": "none"}


def test_the_rows_are_ruled_apart_with_the_portrait_beside_the_words():
    rules = _rules("components/card-log.css")
    assert rules[".card-log-row"]["grid-template-columns"] == "24px minmax(0, 1fr)"
    assert rules[".card-log-row + .card-log-row"]["border-top"] == "1px solid var(--hairline)"
    assert rules[".card-log-list"]["list-style"] == "none"


# --- Keyboard and modality -----------------------------------------------------------------------------


def test_it_is_exposed_as_a_modal_dialog_named_card_log_with_a_close_control():
    dialog = _code(_ts("components/card-log.ts"))
    assert "dialog.setAttribute('role', 'dialog')" in dialog and "dialog.setAttribute('aria-modal', 'true')" in dialog
    assert "dialog.setAttribute('aria-label', strings.cardLog)" in dialog
    assert "close.type = 'button'" in dialog and "close.setAttribute('aria-label', strings.closeCardLog)" in dialog
    assert "dialog.append(head, list, empty)" in dialog and "head.append(close)" in dialog
    close = _rules("components/card-log.css")[".card-log-close"]
    assert close["width"] == "32px" and close["height"] == "32px" and "outline" not in close  # the shared focus ring
    head = _rules("components/card-log.css")[".card-log-head"]
    assert head["position"] == "sticky" and head["top"] == "0" and head["background"] == "var(--chrome)"


def test_focus_starts_on_close_is_trapped_and_the_scene_hotspots_and_top_bar_are_inert():
    play = _code(_ts("play.ts"))
    assert "mountCardLog({ body: frame.body, held: [frame.topBar, sceneColumn, sideColumn], room, play })" in play
    opened = _opened()
    assert "for (const element of frame.held) element.inert = true" in opened
    assert "for (const element of frame.held) element.inert = false" in opened
    assert opened.index("dialog.show()") < opened.rindex("dialog.close.focus()")
    trap = opened.split("const trap = (event: KeyboardEvent): void => {", 1)[1].split("\n    }\n", 1)[0]
    assert "if (event.key !== 'Tab') return" in trap and "dialog.close.focus()" in trap
    assert "document.addEventListener('keydown', trap, true)" in opened
    assert "document.removeEventListener('keydown', trap, true)" in opened
    # A pointer press outside the dialog never moves focus out of it.
    assert "if (!(event.target instanceof Node) || !dialog.dialog.contains(event.target)) event.preventDefault()" in opened
    assert "document.addEventListener('mousedown', keepFocus, true)" in opened


def test_escape_or_the_close_control_closes_it_and_returns_focus_to_the_opener():
    opened = _opened()
    escape = opened.split("if (event.key === 'Escape') {", 1)[1].split("}", 1)[0]
    assert "event.preventDefault()" in escape and "event.stopPropagation()" in escape and "shut()" in escape
    shut = opened.split("function shut(): void {", 1)[1].split("\n    }\n", 1)[0]
    assert "close?.()" in shut and "opener.focus()" in shut
    assert "dialog.close.addEventListener('click', shut)" in opened
    assert "dialog.element.remove()" in opened


def test_it_never_opens_over_another_modal_and_no_modal_opens_over_it():
    log = _code(_ts("card-log.ts"))
    assert "if (close !== undefined || room === undefined) return" in log
    play = _code(_ts("play.ts"))
    # The Leave room confirmation (its button or the browser Back button) asks first.
    assert "modalOpen: () => welcoming || cardLog.isOpen()" in play
    assert "isOpen: () => close !== undefined" in log
    # Under the First-room welcome and the Leave room confirmation, the top bar and the link's column are inert.
    welcome = _code(_ts("welcome.ts"))
    assert "for (const element of held) element.inert = true" in welcome
    assert "[frame.topBar, sceneColumn, sideColumn]" in play.split("mountWelcome(", 1)[1].split("\n", 1)[0]
    assert "held: [frame.topBar, sceneColumn, sideColumn]" in play
    # The Completion screen keeps the button in place under its inert top bar.
    behind = play.split("export function mountPlayBehind(", 1)[1]
    assert "const log = cardLogButton(() => undefined)" in behind and "controls.append(showAll, log, leave)" in behind
    assert "bar.element.inert = done" in _code(_ts("shell.ts"))
    users = {path for path, text in source_ts().items() if "mountCardLog(" in _code(text)}
    assert users == {"web/src/play.ts", "web/src/card-log.ts"}


def test_opening_or_closing_it_writes_nothing_to_the_live_region():
    for name in ("card-log.ts", "components/card-log.ts"):
        assert "announce" not in _code(_ts(name)) and "aria-live" not in _code(_ts(name)), name


def test_after_a_reload_the_cards_are_only_in_the_log():
    # The Hint area stacks only cards[] entries after its first state; the log reads the whole list.
    hint = _code(_ts("components/hint-area.ts"))
    assert "let cardsHeard = latest.cards.length" in hint
    assert "const cards = frame.play.state().cards" in _opened()


def test_every_text_pair_meets_aa_and_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    for pair in ("| `text` | `chrome` #1E1812 |", "| `text-muted` | `chrome` |", "| `lamp` | `chrome-raised` |"):
        assert pair in table, pair
    chrome = _hex(PROPS["chrome"])[0]
    assert contrast(_hex(PROPS["text"])[0], chrome) >= 4.5  # sentence, label, refusal lines, close control
    assert contrast(_hex(PROPS["text-muted"])[0], chrome) >= 4.5  # session time, empty line
    assert contrast(_hex(PROPS["lamp"])[0], _hex(PROPS["chrome-raised"])[0]) >= 4.5  # the Hint area link
    assert contrast(_hex(PROPS["focus-ring"])[0], chrome) >= 3


# --- The state it is built from -------------------------------------------------------------------------


def test_the_polled_state_lists_every_card_oldest_first_with_its_session_time(tmp_path: Path, four_lock_room: Room):
    ticker = Ticker()
    client = app_client(tmp_path, ticker, four_lock_room, proposals_dir=proposals_dir(tmp_path))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    trickster(client, session_id)
    open_window(client, ticker, session_id, code("clock_code", "415"), 1)
    trickster(client, session_id)
    cards = state_of(client, session_id)["cards"]  # what a reload reads
    assert [card["accepted"] for card in cards] == [True, False]
    times = [card["t_ms"] for card in cards]
    assert times == sorted(times) and all(isinstance(t, int) and t > 0 for t in times)
