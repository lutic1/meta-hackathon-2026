"""FR-13, UX-DR44, UX-DR66, UX-DR78, UX-DR8: the Completion screen with its stats and "Build another room".

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The API check plays the
code-and-find fixture room to its Exit and reads the result the sheet draws.
"""

import json
import re
import shutil
import subprocess
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
    # Only an Exit that opened on this screen ends the Session in this page load; one open at mount ended earlier.
    assert "if (!session.locks_open.includes(exitId)) exited.add(session.id)" in leave
    assert "const exited = new Set<string>()" in play and "return exited.has(sessionId)" in _function(play, "endedOnPlay")
    assert "clearTimeout(leaving)" in play


def test_the_done_route_draws_the_completion_screen_from_the_session_state():
    shell = _code("shell.ts")
    assert "if (place.route.name === 'play' || place.route.name === 'done' || place.route.name === 'triggers')" in shell
    assert "if (state !== null) content = { name, session: state, guide: meta.guide, mode: meta.mode, profile: place.profile }" in shell
    assert "mount: () => mountCompletion(element, sceneColumn, sideColumn, session, profile, mode, bar.controls)" in shell
    assert "return getJson<RoomResult>(`/sessions/${encodeURIComponent(sessionId)}/result`)" in _code("api/index.ts")


def test_build_another_room_is_the_one_primary_action_and_goes_home_with_the_profile():
    completion = _code("completion.ts")
    # "Copy your result", and "Try again" on a profile file that failed to save.
    assert completion.count("primaryButton(") == 1 and completion.count("secondaryButton(") == 2
    assert "label: strings.buildAnotherRoom" in completion
    assert "location.hash = placeHref({ route: { name: 'home' }, profile })" in completion
    # Present from the start, before and whatever the result request does.
    mount = _function(completion, "mountCompletion")
    assert mount.index("sheet.append(heading, signature, stats, filmstrip, times, wizards, failed, actions, copied, kept)") < mount.index("void load()")


# --- The sheet --------------------------------------------------------------------------------------------------------


def test_the_sheet_holds_the_heading_sign_off_three_stats_and_the_time_per_puzzle_table():
    completion = _code("completion.ts")
    assert "heading.className = 'completion-heading display-lg'" in completion
    assert "signature.append(wizardPortrait('guide', 48), line)" in completion and "line.className = 'wizard-line'" in completion
    assert "line.replaceChildren(speakerPrefix('guide'), said)" in completion
    assert "stats.append(time.element, hints.element, wrong.element)" in completion
    assert "value.className = 'completion-stat-value mono-timer is-pending'" in completion
    assert "{ stat: time, final: Math.floor(result.elapsed_ms / 1000), format: (s) => formatElapsed(s * 1000) }" in completion
    assert "{ stat: hints, final: result.rungs_used, format: String }" in completion
    assert "{ stat: wrong, final: result.wrong_attempts, format: String }" in completion


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
    assert (scrim["position"], scrim["inset"], scrim["background"]) == ("absolute", "0", "var(--scrim-soft)")
    assert scrim["overflow-y"] == "auto"  # a short body scrolls the scrim, never the page
    assert rules[".completion-layout"]["position"] == "relative"
    # The scrim is a child of the page body, so the top bar above it and the Disclosure footer under it are never dimmed.
    assert "body.append(scrim)" in _code("completion.ts")
    assert "show(bar.element, body.element, ...(banner === null ? [] : [banner]))" in _code("shell.ts")


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
    assert "if (!mounted) return\n    const recorded = putResult(profile, result, mode, session.id, !endedOnPlay(session.id))\n    show(result)" in load
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


# --- The celebration (owner decision, Oct 29) -------------------------------------------------------------------------

SHARE_RUNNER = """
import { readFileSync } from 'node:fs'
const { shareLine, countedAt } = await import(process.argv[1])
const { lines, counts } = JSON.parse(readFileSync(0, 'utf8'))
process.stdout.write(JSON.stringify({
  lines: lines.map((line) => shareLine(line)),
  counts: counts.map(([final, t]) => countedAt(final, t)),
}))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's pure modules")


def test_the_celebration_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["copyResult"] == "Copy your result"
    assert strings["resultCopied"] == "Result copied. Gloat gently."
    assert strings["resultNotCopied"] == "Keyframe couldn't copy it. Here it is: {line}"
    assert strings["builtBy"] == "Built by"
    assert strings["filmstripLabel"] == "Your room, with everything you solved outlined"
    assert strings["shareLine"] == "Keyframe - {room} - {locks} - {time} - {hints} - {wrong} - {url}"
    assert (strings["locksCount"], strings["oneLock"]) == ("{n} locks", "1 lock")
    assert (strings["hintsCount"], strings["oneHint"]) == ("{n} hints", "1 hint")
    assert strings["wrongCount"] == "{n} wrong"


@needs_node
def test_the_share_line_names_the_room_its_locks_the_time_hints_and_wrong_attempts_and_the_url():
    url = "https://keyframe.example/"
    base = {"room": "The front hall and the lounge", "locks": 4, "time": "3:28", "hints": 2, "wrong": 0, "url": url}
    lines = [base, {**base, "locks": 1, "hints": 1, "wrong": 1}]
    counts = [[208, 0], [208, 1], [208, 0.5], [0, 0.7], [3, 0.999]]
    result = subprocess.run(
        ["node", "--input-type=module", "-e", SHARE_RUNNER, (WEB_SRC / "completion-line.ts").as_uri()],
        input=json.dumps({"lines": lines, "counts": counts}), capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["lines"] == [
        f"Keyframe - The front hall and the lounge - 4 locks - 3:28 - 2 hints - 0 wrong - {url}",
        f"Keyframe - The front hall and the lounge - 1 lock - 3:28 - 1 hint - 1 wrong - {url}",
    ]
    # The count rises from 0 to the final value, easing out, and lands on it exactly.
    start, end, middle, zero, almost = out["counts"]
    assert (start, end, zero) == (0, 208, 0) and 104 < middle < 208 and almost == 3


def test_the_share_line_holds_no_solution_text():
    line = _code("completion-line.ts")
    for banned in ("label", "clue", "interactable", "solution", "target"):
        assert banned not in line, banned


def test_the_stats_count_up_once_on_arrival_on_the_count_token_and_at_once_under_reduced_motion():
    completion = _code("completion.ts")
    count = _function(completion, "countUp")
    assert "const ms = motionMs('--motion-count')" in count and "requestAnimationFrame(" in count
    # Read as the page resolves it: the build writes "800ms" as ".8s".
    assert "(value.endsWith('ms') ? 1 : 1000)" in _code("fade.ts")
    assert "countedAt(" in count
    show = _function(completion, "show")
    assert "countUp(" in show and show.count("countUp(") == 1
    assert "stat.show(format(countedAt(final, t)))" in count  # a number change only, landing on the final value
    assert "stats.removeAttribute('aria-busy')" in completion
    tokens = (WEB_SRC / "tokens.css").read_text()
    assert "--motion-count: 800ms;" in tokens
    reduced = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", tokens, flags=re.S).group(1)
    assert "--motion-count: 0ms;" in reduced  # instant: the first frame shows the final values


def test_the_exit_photo_shows_brighter_under_the_soft_scrim():
    assert _rules()[".completion-scrim"]["background"] == "var(--scrim-soft)"
    props = (WEB_SRC / "tokens.css").read_text()
    assert "--scrim-soft: #0A080680;" in props
    assert "scrim-soft: '#0A080680'" in design_text()


def test_the_filmstrip_lights_only_the_objects_the_player_solved():
    strip = re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / "components/filmstrip.ts").read_text(), flags=re.DOTALL)
    assert "photoUrl(roomId, index)" in strip and "hotspotPath(" in strip
    assert "solved.has(interactable.id)" in strip and "interactable.photo === index" in strip
    assert "image.alt = ''" in strip and "strings.filmstripLabel" in strip
    assert ".label" not in strip  # no object name is drawn
    css = css_rules((WEB_SRC / "components/filmstrip.css").read_text())
    assert css[".filmstrip-outline"]["stroke"] == "var(--lamp)"
    assert css[".filmstrip-halo"]["stroke"] == "var(--hotspot-halo)"
    completion = _code("completion.ts")
    # The solved objects: every find target in the final Inventory, plus each unlock moment's target seen in this tab.
    assert "new Set([...session.inventory, ...solvedTargets(session.id)])" in completion
    scene = _code("scene/index.ts")
    assert "solved.keep(play.id, target)" in _function(scene, "bloom")
    assert "const solved = tabTargets('keyframe-solved:')" in scene  # kept for the tab, so a reload stays lit


def test_the_built_by_row_names_the_four_wizards_with_their_portraits():
    completion = _code("completion.ts")
    built = _function(completion, "builtBy")
    assert "strings.builtBy" in built
    assert "(['architect', 'riddler', 'guide', 'trickster'] as const)" in built
    assert "wizardPortrait(wizard, 32)" in built and "WIZARD_NAMES[wizard]" in built


def test_copy_your_result_copies_one_line_and_confirms_in_the_live_region():
    completion = _code("completion.ts")
    assert "label: strings.copyResult" in completion and "onParchment: true" in completion
    # Out of the row until the result and the Room's title are known (a button's inline-flex would beat `hidden`).
    assert "copy.hidden = true" in completion and _rules()[".completion-actions > [hidden]"] == {"display": "none"}
    copy = _function(completion, "copyResult")
    assert "await navigator.clipboard.writeText(line)" in copy
    assert "fill(strings.resultNotCopied, { line })" in copy and "strings.resultCopied" in copy
    assert "copied.textContent = said" in copy and "announce(said)" in copy
    assert "copied.scrollIntoView({ block: 'nearest' })" in copy  # in view even where the scrim scrolls
    assert "url: location.origin + location.pathname" in completion
    assert "room: view.name || buildTime(view.created)" in completion


# --- Where the result is kept (decision record Oct 29, items 27 and 54) ----------------------------------------------


def test_the_result_is_recorded_once_per_session_and_a_failed_save_or_temporary_profile_says_so():
    completion = _code("completion.ts")
    load = _function(completion, "load")
    # The Session is the completion's identity: web/profile records it once, and never an older one over a newer one.
    # A Completion screen that did not follow the Exit on the Play screen in this page load is a reopened one.
    assert "putResult(profile, result, mode, session.id, !endedOnPlay(session.id))" in load
    assert "import { endedOnPlay, mountPlayBehind } from './play.ts'" in completion
    kept = load.split("void recorded.then(", 1)[1]
    succeeded, failed = kept.split("\n      () => {\n", 1)
    assert "offerSave()" in succeeded and "if (await profileTemporary(profile)) note(strings.progressTemporary)" in succeeded
    assert "offerSave()" in failed  # the result is still in the page, so it can still be downloaded
    assert "note(strings.profileNotSaved, { label: strings.tryAgain, onActivate: () => void saveAgain() })" in failed
    again = _function(completion, "saveAgain")
    assert "await saveProfileFile(profile)" in again and "if (mounted) kept.hidden = true" in again
    note = _function(completion, "note")
    assert "line.className = 'completion-kept-line body-sm'" in note
    assert "secondaryButton({ ...action, onParchment: true })" in note and "kept.hidden = false" in note
    assert "sheet.append(heading, signature, stats, filmstrip, times, wizards, failed, actions, copied, kept)" in completion
    rules = css_rules((WEB_SRC / "completion.css").read_text())
    assert rules[".completion-kept-line"]["color"] == "var(--ink)"  # ink on parchment, as the copied line
    strings = _strings()
    assert strings["profileNotSaved"] == "Progress is still here, but the profile file wasn't saved. Try again."
    assert strings["progressTemporary"] == "This browser won't keep your progress, so it lasts until you close this page."
