"""FR-13, UX-DR44, UX-DR66, UX-DR78, UX-DR8: the Completion screen with its stats and "Build another room".

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The API check plays the
code-and-find fixture room to its Exit and reads the result the sheet draws.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX, PZ
from tests.web.design import WEB_SRC, css_rules, design_text, source_ts
from tests.web.test_strings import _strings


def _code(name: str) -> str:
    """TypeScript with its comments removed, so a doc comment may quote a line it explains."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]


def _rules() -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / "completion.css").read_text())


@pytest.fixture
def client(tmp_path: Path, code_and_find_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, code_and_find_room))


# --- Copy -------------------------------------------------------------------------------------------------------------


def test_the_completion_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["roomOpen"] == "The room is open."
    assert strings["signOffNoHints"] == "Not a single hint. I'm almost offended."
    assert strings["signOffSomeHints"] == "You let me help a little. I enjoyed every word."
    assert strings["signOffManyHints"] == "We solved it together, and I'd do it again."
    labels = [strings[k] for k in ("statTime", "statHints", "statWrong", "timePerPuzzle")]
    assert labels == ["Time", "Hints used", "Wrong attempts", "Time per puzzle"]
    assert strings["buildAnotherRoom"] == "Build another room"
    assert strings["resultLoadFailed"] == "Keyframe couldn't load the result. Retrying."
    assert strings["puzzleHeading"].format(n=3) == "Puzzle 3" and strings["speakerGuide"] == "The Guide:"


def test_the_sign_off_is_chosen_from_the_rungs_used_alone():
    sign_off = _function(_code("completion.ts"), "signOff")
    assert "if (rungsUsed === 0) return strings.signOffNoHints" in sign_off
    assert "return rungsUsed <= 3 ? strings.signOffSomeHints : strings.signOffManyHints" in sign_off
    assert "const said = signOff(result.rungs_used)" in _code("completion.ts")


# --- Routing ----------------------------------------------------------------------------------------------------------


def test_the_play_screen_routes_to_done_when_the_exit_puzzles_open_state_ends():
    play = _code("play.ts")
    assert "import { OPEN_HOLD_MS, wizardNotes } from './components/wizard-notes.ts'" in play
    assert "const exit = view.puzzles.find((puzzle) => puzzle.is_exit)" in play
    leave = _function(play, "leaveOnExit")
    assert "if (leaving !== undefined || !state.locks_open.includes(exitId)) return" in leave
    assert "placeHref({ route: { name: 'done', sessionId: session.id }, profile: currentPlace().profile })" in leave
    # The Exit's Open chip holds as long as every lock's (UX-DR38); an Exit open at mount has no Open state to wait for.
    # The route replaces the Play route and its Back guard (test_leave_room), so Back leaves the Completion screen.
    assert "setTimeout(() => leaveRoom.exit(done), session.locks_open.includes(exitId) ? 0 : OPEN_HOLD_MS)" in leave
    assert "clearTimeout(leaving)" in play


def test_the_done_route_draws_the_completion_screen_from_the_session_state():
    shell = _code("shell.ts")
    assert "if (place.route.name === 'play' || place.route.name === 'done' || place.route.name === 'triggers')" in shell
    assert "if (state !== null) content = { name, session: state, guide: meta.guide, mode: meta.mode, profile: place.profile }" in shell
    assert "mount: () => mountCompletion(element, sceneColumn, sideColumn, session, profile, mode, bar.controls)" in shell
    assert "return getJson<RoomResult>(`/sessions/${encodeURIComponent(sessionId)}/result`)" in _code("api/index.ts")


def test_build_another_room_is_the_one_primary_action_and_goes_home_with_the_profile():
    completion = _code("completion.ts")
    assert completion.count("primaryButton(") == 1 and "secondaryButton" not in completion
    assert "label: strings.buildAnotherRoom" in completion
    assert "location.hash = placeHref({ route: { name: 'home' }, profile })" in completion
    # Present from the start, before and whatever the result request does.
    mount = _function(completion, "mountCompletion")
    assert mount.index("sheet.append(heading, signature, stats, times, failed, actions)") < mount.index("void load()")


# --- The sheet --------------------------------------------------------------------------------------------------------


def test_the_sheet_holds_the_heading_sign_off_three_stats_and_the_time_per_puzzle_table():
    completion = _code("completion.ts")
    assert "heading.className = 'completion-heading display-lg'" in completion
    assert "signature.append(wizardPortrait('guide', 48), line)" in completion and "line.className = 'wizard-line'" in completion
    assert "line.replaceChildren(speakerPrefix('guide'), said)" in completion
    assert "stats.append(time.element, hints.element, wrong.element)" in completion
    assert "value.className = 'completion-stat-value mono-timer is-pending'" in completion
    assert "time.show(formatElapsed(result.elapsed_ms))" in completion
    assert "hints.show(String(result.rungs_used))" in completion and "wrong.show(String(result.wrong_attempts))" in completion


def test_the_time_table_has_a_puzzle_n_row_per_puzzle_no_header_row_and_no_exit_mark():
    completion = _code("completion.ts")
    rows = _function(completion, "timeRows")
    assert "name.scope = 'row'" in rows and "name.className = 'body-sm'" in rows
    assert "fill(strings.puzzleHeading, { n: index + 1 })" in rows
    assert "time.className = 'mono-sm'" in rows and "formatElapsed(puzzle.time_spent_ms)" in rows
    assert "is_exit" not in completion and "thead" not in completion and "'col'" not in completion
    assert "table.setAttribute('aria-labelledby', timesLabel.id)" in completion


def test_a_failed_result_says_so_and_retries_every_2000_ms_with_the_stats_pending():
    completion = _code("completion.ts")
    assert "export const RESULT_RETRY_MS = 2000" in completion
    load = _function(completion, "load")
    assert "result = await getResult(session.id)" in load
    assert "failed.hidden = false" in load and "retry = setTimeout(() => void load(), RESULT_RETRY_MS)" in load
    assert "failed.textContent = strings.resultLoadFailed" in completion
    assert "const PENDING = '…'" in completion and "stats.setAttribute('aria-busy', 'true')" in completion
    assert "clearTimeout(retry)" in completion


def test_the_sheet_is_720px_parchment_with_48px_padding_over_a_scrim_on_the_body_only():
    rules = _rules()
    sheet = rules[".completion-sheet"]
    assert (sheet["width"], sheet["max-width"], sheet["padding"]) == ("720px", "100%", "var(--spacing-7)")
    assert (sheet["background"], sheet["color"]) == ("var(--parchment)", "var(--ink)")
    assert (sheet["border-radius"], sheet["box-shadow"]) == ("var(--rounded-lg)", "var(--elevation-overlay)")
    token = design_text().split("  completion-sheet:\n", 1)[1].split("\n  deletion-line:", 1)[0]
    assert "width: 720px" in token and "padding: '{spacing.7}'" in token and "guidePortrait: 48px" in token
    scrim = rules[".completion-scrim"]
    assert (scrim["position"], scrim["inset"], scrim["background"]) == ("absolute", "0", "var(--scrim)")
    assert scrim["overflow-y"] == "auto"  # a short body scrolls the scrim, never the page
    assert rules[".completion-layout"]["position"] == "relative"
    # The scrim is a child of the page body, so the Disclosure banner and the top bar above it are never dimmed.
    assert "body.append(scrim)" in _code("completion.ts")
    assert "show(...(banner === null ? [] : [banner]), bar.element, body.element)" in _code("shell.ts")


def test_the_stats_are_three_across_in_mono_timer_under_the_parchment_rule_with_ink_muted_labels():
    rules = _rules()
    stats = rules[".completion-stats"]
    assert stats["grid-template-columns"] == "repeat(3, minmax(0, 1fr))"
    assert stats["border-top"] == "1px solid var(--parchment-rule)"
    assert rules[".completion-stat-label"]["color"] == "var(--ink-muted)"
    assert rules[".completion-stat-value.is-pending"]["color"] == "var(--pending-ink)"
    assert rules[".completion-times td"]["text-align"] == "right"
    assert rules[".completion-signoff"]["grid-template-columns"] == "48px minmax(0, 1fr)"
    assert rules[".completion-signoff[hidden]"]["display"] == "none"


# --- The frame and the accessibility floor ----------------------------------------------------------------------------


def test_the_top_bar_stays_in_place_but_inert_and_the_timer_frozen():
    shell = _code("shell.ts")
    assert "const done = content.name === 'done'" in shell and "bar.element.inert = done" in shell
    assert "mountTimer(bar.timer, owns, done)" in shell
    timer = _code("capture-timer.ts")
    assert "if (shown?.stoppedAt === null && !frozen) ticking ??= setInterval(render, TICK_MS)" in timer


def test_the_dimmed_play_screen_is_inert_and_never_polls_or_posts():
    completion = _code("completion.ts")
    assert "sceneColumn.inert = true" in completion and "sideColumn.inert = true" in completion
    behind = _function(_code("play.ts"), "mountPlayBehind")
    assert "Worker" not in behind and "getSession" not in behind and "postEvent" not in behind
    assert "mountScene(sceneColumn, stripRow, play, room, lastShownPhoto(session.id))" in behind
    assert "shownPhoto.set(play.id, index)" in _code("scene/index.ts")


def test_the_heading_takes_focus_and_the_sign_off_is_announced_once():
    completion = _code("completion.ts")
    assert "heading.tabIndex = -1" in completion and "heading.focus()" in completion
    show = _function(completion, "show")
    assert show.count("announce(") == 1 and "announce(`${strings.speakerGuide} ${said}`)" in show
    load = _function(completion, "load")
    assert "if (!mounted) return\n    const recorded = putResult(profile, result, mode)\n    show(result)" in load
    assert load.count("show(") == 1  # drawn, and announced, once it returns
    # One polite live region for the page, outside #app so no route change replaces it.
    regions = [path for path, text in source_ts().items() if "aria-live" in text]
    assert regions == ["web/src/live-region.ts"]
    assert "liveRegion()" in _code("shell.ts")


def test_every_completion_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in (("ink", "parchment"), ("ink-muted", "parchment"), ("pending-ink", "parchment"),
                   ("on-lamp", "lamp"), ("focus-ring-inner", "parchment")):
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"


# --- The result the sheet reads ---------------------------------------------------------------------------------------


def test_the_result_lists_every_puzzle_in_room_order_with_its_time(client: TestClient, code_and_find_room: Room):
    session = client.post("/api/sessions", json={"room_id": code_and_find_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    for body in (
        {"type": "click", "interactable_id": IX["key"]},
        {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["clock_code"], "code": "999"}},
        {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["clock_code"], "code": "415"}},
        {"type": "click", "interactable_id": IX["lantern"]},
        {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["door_code"], "code": "7342"}},
    ):
        assert client.post(events, json=body).status_code == 200
    exit_id = next(puzzle.id for puzzle in code_and_find_room.puzzles if puzzle.is_exit)
    assert exit_id in client.get(f"/api/sessions/{session['id']}").json()["locks_open"]
    result = client.get(f"/api/sessions/{session['id']}/result").json()
    assert [puzzle["puzzle_id"] for puzzle in result["puzzles"]] == [puzzle.id for puzzle in code_and_find_room.puzzles]
    assert result["rungs_used"] == 0 and result["wrong_attempts"] == 1
    assert all(puzzle["solved"] and puzzle["time_spent_ms"] >= 0 for puzzle in result["puzzles"])
    assert result["elapsed_ms"] >= 0
