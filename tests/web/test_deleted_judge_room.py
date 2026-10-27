"""FR-33, UX-DR47, UX-DR44, UX-DR78, UX-DR81: the Deleted Judge room notice, the unknown-room card and the
"Deleted Tue Nov 10" strip below a Judge room's Completion sheet.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The server side of the strip,
the session state's `judge_room` flag, is tested in tests/api/test_judge_room_flag.py.
"""

import re

from src.api.errors import RoomDeleted, RoomNotFound
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_contrast import PROPS, _hex, contrast
from tests.web.test_strings import _section, _strings


def _code(name: str) -> str:
    """TypeScript with its comments removed, so a doc comment may quote a line it explains."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _token(name: str, following: str) -> str:
    return design_text().split(f"  {name}:\n", 1)[1].split(f"\n  {following}:", 1)[0]


# --- Copy -------------------------------------------------------------------------------------------------------------


def test_the_deletion_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["deletedOn"] == "Deleted Tue Nov 10"  # verbatim, FR-33
    assert strings["roomDeleted"] == "This room is gone"
    assert strings["roomDeletedBody"] == "This room was deleted on Tue Nov 10, as promised."
    assert strings["goToDemoRooms"] == "Go to the demo rooms"
    assert strings["roomNotFound"] == "Keyframe can't find this room"
    assert strings["roomNotFoundBody"] == "Check the link, or start from the beginning."
    assert strings["buildARoom"] == "Build a room"
    voice = _section("Voice and Tone")
    assert '| Judge room | plain, below the sheet | "Deleted Tue Nov 10" (verbatim, FR-33) |' in voice
    assert 'Heading "This room is gone". Body "This room was deleted on Tue Nov 10, as promised." Button "Go to the demo rooms"' in voice


# --- The strip: drawn from the server's judge_room flag alone ---------------------------------------------------------


def test_the_strip_is_drawn_from_the_session_states_judge_room_flag_alone():
    completion = _code("completion.ts")
    assert completion.count("judge_room") == 1
    assert "if (session.judge_room === true) scrim.append(deletionLine())" in completion
    # Never inferred by the client: no mode, Room id or listing decides it.
    line = completion.split("scrim.append(sheet)\n", 1)[1].split("\n", 1)[0]
    assert "mode" not in line and "room_id" not in line and "listRooms" not in line


def test_the_strip_sits_directly_below_the_sheet_off_the_paper_as_plain_text():
    completion, line = _code("completion.ts"), _code("components/deletion-line.ts")
    assert "scrim.append(sheet)\n  if (session.judge_room === true) scrim.append(deletionLine())\n  body.append(scrim)" in completion
    assert "const line = document.createElement('p')" in line
    assert "line.className = 'deletion-line body-sm'" in line and "line.textContent = strings.deletedOn" in line
    # Plain text where it stands: no role, no live region, no focus stop, no portrait.
    assert not re.search(r"tabIndex|setAttribute|aria-|wizardPortrait|focus\(", line)


def test_the_strip_is_the_deletion_line_token_on_chrome_raised_never_parchment():
    token = _token("deletion-line", "greeting-overlay")
    assert "background: '{colors.chrome-raised}'" in token and "foreground: '{colors.text}'" in token
    assert "typography: '{typography.body-sm}'" in token and "radius: '{rounded.md}'" in token
    rule = _rules("components/deletion-line.css")[".deletion-line"]
    assert rule["background"] == "var(--chrome-raised)" and rule["color"] == "var(--text)"
    assert rule["border-radius"] == "var(--rounded-md)"
    assert rule["width"] == "720px" and rule["max-width"] == "100%"  # as wide as the sheet above it
    assert "parchment" not in (WEB_SRC / "components/deletion-line.css").read_text()
    # The sheet keeps no bottom margin above the strip, so the two sit together, centered on the scrim.
    assert _rules("completion.css")[".completion-sheet:has(+ .deletion-line)"]["margin-bottom"] == "0"


def test_a_demo_room_and_every_local_room_show_no_deletion_line():
    """The server sets the flag only for a Room under `rooms/judge/`; the local store never names a Judge room."""
    local = (WEB_SRC.parent.parent / "src/infra/local.py").read_text()
    judge = local.split("def is_judge_room(self, room_id: str) -> bool:", 1)[1].split("\n\n", 1)[0]
    assert "return False" in judge
    assert '"judge_room": session.judge_room' in (WEB_SRC.parent.parent / "src/api/app.py").read_text()


# --- The cards: a deleted Judge room and an unknown room ---------------------------------------------------------------


def test_410_room_deleted_and_404_room_not_found_are_the_two_refusals_the_cards_key_on():
    gone = _code("room-gone.ts")
    assert (RoomDeleted.status, RoomDeleted.code) == (410, "room_deleted")
    assert (RoomNotFound.status, RoomNotFound.code) == (404, "room_not_found")
    assert "if (error.status === 410 && error.code === 'room_deleted') return 'room_deleted'" in gone
    assert "if (error.status === 404 && error.code === 'room_not_found') return 'room_not_found'" in gone


def test_the_card_copy_follows_the_refusal_and_the_mode():
    gone = _code("room-gone.ts")
    assert "const deleted = gone === 'room_deleted'" in gone
    assert "heading: deleted ? strings.roomDeleted : strings.roomNotFound" in gone
    assert "sentence: deleted ? strings.roomDeletedBody : strings.roomNotFoundBody" in gone
    # "Go to the demo rooms" for a deleted room and for an unknown one in Hosted mode; "Build a room" in Local mode.
    assert "label: deleted || mode === 'hosted' ? strings.goToDemoRooms : strings.buildARoom" in gone
    assert "location.hash = placeHref({ route: { name: 'home' }, profile })" in gone  # the Hosted landing in Hosted mode


def test_the_card_is_the_whole_body_focused_on_its_heading_with_no_scrim_and_no_fade():
    gone, card = _code("room-gone.ts"), _code("components/notice-card.ts")
    assert "body.className = 'shell-body notice-layout'" in gone
    assert "body.replaceChildren(card.element)\n  card.heading.focus()" in gone
    assert "heading.tabIndex = -1" in card and "primaryButton({" in card
    sheet = re.sub(r"/\*.*?\*/", "", (WEB_SRC / "components/notice-card.css").read_text(), flags=re.DOTALL)
    for text in (gone, card, sheet):
        assert not re.search(r"fadeIn|reveal\(|transition|animation|scrim", text)
    rule = _rules("components/notice-card.css")[".notice-card"]
    assert rule["width"] == "480px" and rule["background"] == "var(--chrome-raised)" and rule["color"] == "var(--text)"
    assert _rules("shell.css")[".notice-layout"]["place-items"] == "center"


def test_both_build_routes_show_the_card_when_the_room_is_gone():
    shell, view, progress = _code("shell.ts"), _code("build-view.ts"), _code("build-progress.ts")
    # #/build/<job_id>/view: the gone state of the one load, shown as the card in place of the Build view.
    assert "return gone === null ? { name: 'failed' } : { name: 'gone', gone }" in view
    assert "if (state.name === 'gone') {" in shell and "showRoomGone(element, state.gone, meta.mode, profile)" in shell
    # #/build/<job_id>: a refused poll or session start that names a gone Room.
    assert "buildScreen(jobId, profile, mode, retention, (gone) => showRoomGone(element, gone, mode, profile))" in shell
    poll = progress.split("async function poll(): Promise<void> {", 1)[1].split("\n      }\n", 1)[0]
    assert "const gone = roomGone(error)\n            if (gone !== null) onGone(gone)" in poll
    start = progress.split("async function start(roomId: string): Promise<void> {", 1)[1].split("\n      }\n", 1)[0]
    assert "if (mounted) onGone(gone)" in start


def test_the_play_and_completion_screens_show_the_card_on_a_room_keyed_refusal():
    play, completion = _code("play.ts"), _code("completion.ts")
    assert play.count("const gone = roomGone(error)") == 3  # the Room, "Start again" and the Room behind the sheet
    assert "showRoomGone(frame.body, gone, frame.mode, currentPlace().profile)" in play
    assert "showRoomGone(body, gone, mode, profile)" in completion


# --- Contrast and focus --------------------------------------------------------------------------------------------


def test_every_pair_the_cards_and_the_strip_draw_is_in_the_contrast_table_and_passes():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in {("text", "chrome-raised"), ("on-lamp", "lamp")}:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    assert contrast(_hex(PROPS["text"])[0], _hex(PROPS["chrome-raised"])[0]) >= 4.5
    assert contrast(_hex(PROPS["on-lamp"])[0], _hex(PROPS["lamp"])[0]) >= 4.5
    # The two-tone ring around "Go to the demo rooms" sits on chrome-raised: 3:1 for non-text.
    assert contrast(_hex(PROPS["focus-ring"])[0], _hex(PROPS["chrome-raised"])[0]) >= 3


# --- Gone sessions and unknown builds ---------------------------------------------------------------------------------


def test_an_unknown_build_shows_the_unknown_room_card():
    from src.api.errors import JobNotFound

    assert (JobNotFound.status, JobNotFound.code) == (404, "job_not_found")
    progress = _code("build-progress.ts")
    poll = progress.split("async function poll(): Promise<void> {", 1)[1].split("\n      }\n", 1)[0]
    # #/build/<job_id> for an id no record names: the unknown-room card, never the pending Stage list left polling.
    assert "else if (error instanceof RequestFailed && error.code === 'job_not_found') onGone('room_not_found')" in poll


def test_a_session_the_server_no_longer_holds_shows_the_session_gone_state_with_start_again():
    from src.api.errors import SessionNotFound

    assert (SessionNotFound.status, SessionNotFound.code) == (404, "session_not_found")
    shell = _code("shell.ts")
    render = shell.split("async function render()", 1)[1].split("\n  }\n", 1)[0]
    # A cold load of #/play/<id> or #/done/<id> the server refuses: the Session-gone line with "Start again", which
    # goes to #/ since the refusal names no Room to start again; the second Triggers window stays empty.
    assert "else if (name !== 'triggers') content = { name: 'gone', profile: place.profile }" in render
    body = shell.split("if (content.name === 'gone') {", 1)[1].split("\n  }\n", 1)[0]
    assert "element.classList.add('session-gone-layout')" in body
    assert "playEnded(() => {" in body and "location.hash = placeHref({ route: { name: 'home' }, profile })" in body
    assert _rules("shell.css")[".session-gone-layout"]["position"] == "relative"
