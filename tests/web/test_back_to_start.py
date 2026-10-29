"""UX-DR7, UX-DR8, UX-DR46: every screen has a way back to the start (owner report Oct 29: "theres no back buttons if
they want to exit the build modes or other ones as well").

The top bar's wordmark links to `#/` on every screen, through the Leave room confirmation on the Play screen; the
Hosted Capture screen has its own route, `#/build-your-own`, and "Back to the three cards"; the Build progress screen
has "Back to the start", which asks first while the Build still runs.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the paths are walked in
Chrome against the fixture rooms.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import EXPERIENCE, _strings, _voice_and_tone


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", _ts(name), flags=re.DOTALL)


def _experience() -> str:
    return EXPERIENCE.read_text()


# --- The wordmark ---------------------------------------------------------------------------------------------------


def test_the_wordmark_is_a_link_to_the_start_on_every_screen():
    bar = _code("components/top-bar.ts")
    assert "const wordmark = document.createElement('a')" in bar
    assert "wordmark.href = placeHref({ route: { name: 'home' }, profile: meta.profile })" in bar
    assert "wordmark.setAttribute('aria-label', strings.wordmarkLink)" in bar
    assert "wordmark.textContent = strings.wordmark" in bar
    assert "return { element, wordmark, timer, controls, showPlayed }" in bar
    assert _strings()["wordmarkLink"] == "Keyframe, back to the start"
    # A link in the bar's own text colour, no underline at rest; the shared focus ring draws on it unchanged.
    rule = css_rules(_ts("components/top-bar.css"))
    assert rule[".top-bar-wordmark"]["text-decoration"] == "none"
    assert rule[".top-bar-wordmark:hover"]["text-decoration"] == "underline"
    assert "outline" not in rule[".top-bar-wordmark"] and ".top-bar-wordmark:focus-visible" not in rule


def test_on_the_completion_screen_only_the_play_controls_are_inert_so_the_wordmark_goes_home():
    shell = _code("shell.ts")
    assert "bar.controls.inert = done" in shell
    assert "bar.element.inert" not in shell


def test_on_the_play_screen_the_wordmark_asks_the_leave_room_confirmation():
    play = _code("play.ts")
    assert "wordmark: frame.wordmark," in play.split("const leaveRoom = mountLeaveRoom({", 1)[1].split("\n  })\n", 1)[0]
    leave = _code("leave-room.ts")
    assert "wordmark: HTMLAnchorElement" in leave
    ask = leave.split("const onWordmark = (event: MouseEvent): void => {", 1)[1].split("\n  }\n", 1)[0]
    assert "event.preventDefault()" in ask and "open(() => frame.wordmark.focus())" in ask
    assert "frame.wordmark.addEventListener('click', onWordmark)" in leave
    assert "frame.wordmark.removeEventListener('click', onWordmark)" in leave
    shell = _code("shell.ts")
    assert "wordmark: bar.wordmark" in shell


# --- The Hosted Capture screen: its own route and "Back to the three cards" ---------------------------------------


def test_the_hosted_capture_screen_has_its_own_route():
    router = _code("router.ts")
    assert "| { name: 'buildYourOwn' }" in router
    assert "if (path === '/build-your-own') return { route: { name: 'buildYourOwn' }, profile }" in router
    assert "route.name === 'buildYourOwn' ? '/build-your-own'" in router
    shell = _code("shell.ts")
    render = shell.split("async function render()", 1)[1].split("\n  }\n", 1)[0]
    on_accepted = render.split("const onAccepted = (): void => {", 1)[1].split("\n      }\n", 1)[0]
    assert "location.hash = placeHref({ route: { name: 'buildYourOwn' }, profile: place.profile })" in on_accepted
    assert "void render()" not in on_accepted  # the hash change renders it, and the browser's Back returns to `#/`
    # No Access code held (Local mode, or a reloaded tab): `#/` in place, adding no history entry.
    assert "const buildsLeft = place.route.name === 'buildYourOwn' ? await judgeBuildsLeft() : null" in render
    fallback = render.split("if (place.route.name === 'buildYourOwn' && buildsLeft === null) {", 1)[1].split("\n    }\n", 1)[0]
    assert "place = { route: { name: 'home' }, profile: place.profile }" in fallback
    assert "history.replaceState(history.state, '', placeHref(place))" in fallback
    assert "requestCapture" not in shell and "takeCaptureRequest" not in shell


def test_hosted_start_over_and_add_photos_reopen_the_capture_route():
    build = _code("build-progress.ts")
    start_over = build.split("function startOver(): void {", 1)[1].split("\n      }\n", 1)[0]
    assert "const capture: Route = mode === 'hosted' ? { name: 'buildYourOwn' } : { name: 'home' }" in start_over
    assert "location.hash = placeHref({ route: capture, profile })" in start_over
    assert "requestCapture" not in build and "requestCapture" not in _code("build-photos.ts")


def test_the_hosted_capture_screen_offers_back_to_the_three_cards_at_the_top_of_its_column():
    capture = _code("capture.ts")
    assert ("const back = typeof below === 'number' ? backButton(strings.backToCards, () => goHome(profile)) : null"
            in capture)
    assert "left.append(...(back === null ? [] : [back]), banners, controls)" in capture
    # Disabled with "Choose photos" while an upload is pending, so the accepted Build never follows a judge who left.
    render = capture.split("function render(uploading = false): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "if (back !== null) back.disabled = uploading" in render
    assert "location.hash = placeHref({ route: { name: 'home' }, profile })" in _code("capture.ts")
    assert _strings()["backToCards"] == "Back to the three cards"
    rule = css_rules(_ts("shell.css"))[".capture-back"]
    assert rule["align-self"] == "flex-start"


# --- The Build progress screen: "Back to the start" -----------------------------------------------------------------


def test_the_build_screen_offers_back_to_the_start_above_its_banners():
    build = _code("build-progress.ts")
    assert "const back = backButton(strings.backToStart, () => backToStart())" in build
    assert ("left.append(back, banners, actions, stages.element, ...(mode === 'hosted' ? [hostedLines()] : []), maskSlot, "
            "traySlot, picker)") in build
    assert _strings()["backToStart"] == "Back to the start"


def test_while_the_build_runs_back_to_the_start_asks_first_and_once_it_ends_leaves_at_once():
    build = _code("build-progress.ts")
    back = build.split("function backToStart(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "if (status !== null && status !== 'queued' && status !== 'running') return goHome(profile)" in back
    assert "if (asking !== undefined) return" in back
    assert "asking = askToLeave(frame, leaveRoomConfirmation(LEAVE_PAGE), stay, () => goHome(profile))" in back
    assert "asking = undefined\n      back.focus()" in back
    assert "const frame = { body: page.body, held: [page.topBar, left, right] }" in build
    assert "status = job.status" in build.split("function apply(job: JobState): void {", 1)[1].split("\n      }\n", 1)[0]
    assert "asking?.()" in build.split("return () => {", 1)[1]
    shell = _code("shell.ts")
    assert "const page = { body: element, topBar: bar.element }" in shell
    assert "buildScreen(jobId, profile, mode, retention, page, (gone) =>" in shell
    strings = _strings()
    assert strings["leavePageQuestion"] == "Your room keeps building. Leave this page?"
    assert strings["leavePageBody"] == "This page's address brings you back."
    assert strings["stay"] == "Stay" and strings["leave"] == "Leave"


def test_the_build_confirmation_is_the_leave_room_card_with_its_focus_handling():
    card = _code("components/leave-room-confirmation.ts")
    assert "export function leaveRoomConfirmation(copy: ConfirmationCopy = LEAVE_ROOM): LeaveRoomConfirmation {" in card
    assert "heading.textContent = copy.question" in card and "sentence.textContent = copy.sentence" in card
    assert "const stay = button('button-primary', copy.stay)" in card
    assert "const leave = button('button-secondary', copy.leave)" in card
    build = _code("build-progress.ts")
    copy = build.split("const LEAVE_PAGE: ConfirmationCopy = {", 1)[1].split("}", 1)[0]
    assert "question: strings.leavePageQuestion" in copy and "sentence: strings.leavePageBody" in copy
    assert "stay: strings.stay" in copy and "leave: strings.leave" in copy
    leave = _code("leave-room.ts")
    # One focus handling for both: the trap, the inert frame, Escape as Stay.
    assert "export function askToLeave(" in leave
    assert leave.count("document.addEventListener('keydown', trap, true)") == 1
    assert "close = askToLeave(frame, leaveRoomConfirmation(), keep, frame.leave)" in leave
    assert "confirmation.stay.focus()" in leave and "for (const element of frame.held) element.inert = true" in leave


# --- The contract ---------------------------------------------------------------------------------------------------


def test_experience_md_records_every_way_back():
    voice = _voice_and_tone()
    assert '"Keyframe, back to the start"' in voice
    assert '"Back to the start"' in voice
    assert "\"Your room keeps building. Leave this page? This page's address brings you back.\"" in voice
    assert 'Buttons "Leave" / "Stay"' in voice
    assert "`#/build-your-own`" in _experience().split("### Navigation rules", 1)[1].split("\n## ", 1)[0]
    surfaces = _experience().split("### Surface map", 1)[1].split("### Navigation rules", 1)[0]
    assert "wordmark" in surfaces
    assert "wordmark" in design_text().split("2. **Top bar**", 1)[1].split("\n", 1)[0]
