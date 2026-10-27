"""UX-DR46, UX-DR7, UX-DR8, UX-DR71: "Leave room" and the browser Back button on the Play screen ask the Leave room
confirmation; it traps focus, holds the Scene, Hotspots and top bar inert, and never stacks on another modal.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the criteria are checked in
Chrome against the fixture rooms.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text, source_ts
from tests.web.test_contrast import PROPS, _hex, _over, contrast


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _token(name: str, following: str) -> str:
    return design_text().split(f"  {name}:\n", 1)[1].split(f"\n  {following}:", 1)[0]


def test_leave_room_sits_right_of_show_all_objects_in_the_play_top_bar():
    play = _code(_ts("play.ts"))
    assert "frame.controls.append(showAll, leaveRoom.button)" in play
    assert "held: [frame.topBar, sceneColumn, sideColumn]" in play
    leave = _code(_ts("leave-room.ts"))
    assert "secondaryButton({ label: strings.leaveRoom, onActivate: () => open(() => button.focus()) })" in leave
    # Gone with the Play screen, and with a missing Room, whose card replaces the body.
    assert play.count("leaveRoom.unmount()") == 2
    assert "leaveRoom.unmount()" in play.split("function roomMissing(): void {", 1)[1].split("\n  }\n", 1)[0]


def test_the_card_is_a_plain_480px_chrome_raised_sheet_over_the_scrim_that_fades_in_over_300ms():
    rules = _rules("components/leave-room-confirmation.css")
    card = rules[".leave-room-confirmation"]
    token = _token("leave-room-confirmation", "build-view-header")
    assert "width: 480px" in token and card["width"] == "480px" and card["max-width"] == "100%"
    assert "background: '{colors.chrome-raised}'" in token and card["background"] == "var(--chrome-raised)"
    assert "foreground: '{colors.text}'" in token and card["color"] == "var(--text)"
    assert "radius: '{rounded.lg}'" in token and card["border-radius"] == "var(--rounded-lg)"
    assert "shadow: '{elevation.overlay}'" in token and card["box-shadow"] == "var(--elevation-overlay)"
    assert card["transition"] == "opacity var(--motion-overlay) var(--motion-ease)"
    assert rules[".leave-room-confirmation.is-arriving"] == {"opacity": "0"}
    assert "parchment" not in str(rules)
    # The scrim covers the page body only: the Play layout, under the Disclosure banner and the top bar.
    scrim = rules[".leave-room-scrim"]
    assert "scrim: '{colors.scrim}'" in token and scrim["background"] == "var(--scrim)"
    assert scrim["position"] == "absolute" and scrim["inset"] == "0" and scrim["place-items"] == "center"
    assert _rules("shell.css")[".play-layout"]["position"] == "relative"
    assert "frame.body.append(confirmation.element)" in _ts("leave-room.ts") and "body: frame.body" in _ts("play.ts")


def test_the_card_holds_the_question_the_sentence_keep_playing_then_leave_room():
    ts = _code(_ts("components/leave-room-confirmation.ts"))
    assert "heading.className = 'leave-room-heading display-sm'" in ts and "heading.textContent = strings.leaveRoomQuestion" in ts
    assert "sentence.className = 'leave-room-sentence body-md'" in ts and "sentence.textContent = strings.leaveRoomBody" in ts
    assert "const keepPlaying = button('button-primary', strings.keepPlaying)" in ts
    assert "const leave = button('button-secondary', strings.leaveRoom)" in ts
    assert "actions.append(keepPlaying, leave)" in ts and "card.append(heading, sentence, actions)" in ts
    assert "card.setAttribute('role', 'dialog')" in ts and "card.setAttribute('aria-modal', 'true')" in ts
    assert "card.setAttribute('aria-labelledby', HEADING_ID)" in ts and "card.setAttribute('aria-describedby', SENTENCE_ID)" in ts
    assert "show: () => fadeIn(card)" in ts


def test_focus_starts_on_keep_playing_is_trapped_and_the_scene_hotspots_and_top_bar_are_inert():
    leave = _code(_ts("leave-room.ts"))
    opened = leave.split("function open(refocus: () => void): void {", 1)[1].split("\n  const guard", 1)[0]
    assert "for (const element of frame.held) element.inert = true" in opened
    assert "for (const element of frame.held) element.inert = false" in opened
    assert opened.index("confirmation.show()") < opened.index("keepPlaying.focus()")
    # Tab and Shift+Tab cycle the two buttons; a pointer press never moves focus out of the card.
    assert "const order = [keepPlaying, leave]" in opened and "event.preventDefault()" in opened
    assert "const step = event.shiftKey ? order.length - 1 : 1" in opened
    assert "order[at === -1 ? 0 : (at + step) % order.length].focus()" in opened
    assert "document.addEventListener('mousedown', keepFocus, true)" in opened
    assert "document.addEventListener('keydown', trap, true)" in opened
    assert "document.removeEventListener('keydown', trap, true)" in opened


def test_escape_or_keep_playing_closes_and_returns_focus_to_leave_room_or_the_first_hotspot_after_back():
    leave = _code(_ts("leave-room.ts"))
    assert "if (event.key === 'Escape') {" in leave and "keep()" in leave
    assert "keepPlaying.addEventListener('click', keep)" in leave
    keep = leave.split("function keep(): void {", 1)[1].split("\n    }\n", 1)[0]
    assert "close?.()" in keep and "refocus()" in keep
    assert "open(() => button.focus())" in leave and "open(frame.focusScene)" in leave
    play = _code(_ts("play.ts"))
    assert "unfocus = focusFirstHotspot(sceneColumn)" in play.split("focusScene: () => {", 1)[1].split("},", 1)[0]


def test_confirming_goes_home_and_records_no_room_result():
    leave = _code(_ts("leave-room.ts"))
    assert "leave.addEventListener('click', () => {\n      close?.()\n      frame.leave()\n    })" in leave
    play = _code(_ts("play.ts"))
    gone = play.split("leave: () => {", 1)[1].split("\n    },", 1)[0]
    assert "location.hash = placeHref({ route: { name: 'home' }, profile: currentPlace().profile })" in gone
    # Only the Completion screen records a Room result; neither the Play screen nor the confirmation posts one.
    for name in ("play.ts", "leave-room.ts", "components/leave-room-confirmation.ts"):
        code = _code(_ts(name))
        assert "getResult" not in code and "/result" not in code and "profile.record" not in code.lower(), name


def test_back_on_the_play_screen_is_caught_by_a_guard_entry_and_asks_the_same_confirmation():
    leave = _code(_ts("leave-room.ts"))
    assert "const guard = (): void => history.pushState({ [GUARD]: true }, '')" in leave
    assert "if (!isGuard(history.state)) guard()" in leave  # a reload already stands on its guard
    on_back = leave.split("const onBack = (): void => {", 1)[1].split("\n  }\n", 1)[0]
    # A hash the client changed itself (Leave, Start again, the Exit) is a route change, never Back.
    assert "if (isGuard(history.state) || location.hash !== playHash) return" in on_back
    assert on_back.index("guard()") < on_back.index("open(frame.focusScene)")
    assert "window.addEventListener('popstate', onBack)" in leave
    assert "window.removeEventListener('popstate', onBack)" in leave
    # The shell routes on hashchange only, so a popped guard (same URL) never re-renders the Play screen.
    shell = _code(_ts("shell.ts"))
    assert "popstate" not in shell and "window.addEventListener('hashchange', () => void render())" in shell


def test_modals_never_stack():
    leave = _code(_ts("leave-room.ts"))
    assert "if (close !== undefined || frame.modalOpen()) return" in leave
    play = _code(_ts("play.ts"))
    assert "modalOpen: () => welcoming" in play
    welcome = play.split("const welcome = session.opening_line", 1)[1]
    assert welcome.index("welcoming = true") < welcome.index("mountWelcome(") < welcome.index("welcoming = false")
    # Only the Play screen opens it: the Completion screen's "Leave room" is held inert with its top bar.
    users = {path for path, text in source_ts().items() if "mountLeaveRoom(" in _code(text)}
    assert users == {"web/src/play.ts", "web/src/leave-room.ts"}


def test_every_color_pair_on_the_card_meets_aa_and_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in (("text", "chrome-raised"), ("lamp", "chrome-raised"), ("on-lamp", "lamp")):
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    raised = _hex(PROPS["chrome-raised"])[0]
    assert contrast(_hex(PROPS["text"])[0], raised) >= 4.5
    assert contrast(_hex(PROPS["lamp"])[0], raised) >= 4.5  # "Leave room", secondary
    assert contrast(_hex(PROPS["on-lamp"])[0], _hex(PROPS["lamp"])[0]) >= 4.5  # "Keep playing", primary
    assert contrast(_hex(PROPS["focus-ring"])[0], raised) >= 3  # the focus ring around either button
    # The card stands out from the dimmed Play screen around it.
    assert contrast(raised, _over("scrim", _hex(PROPS["canvas"])[0])) > 1
