"""FR-38, UX-DR19, UX-DR44, UX-DR51, UX-DR52, UX-DR55, UX-DR71, UX-DR84: the verdict table, the Dry run rows, the build
JSON pane and the "How this room was built" links.

As in test_build_view_surface.py, these checks read the TypeScript and the stylesheets (the client has no test runner);
`npm run build` and `tsc --noEmit` prove they compile. The wire values the client keys on (the rule names and fixed
messages, the cut 4 verdict) are checked against the server, and the sentinel check builds the `BuildView` the page
renders from a Room with sentinel solutions.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import get_args

import pytest

from src.domain.redact import to_build_view
from src.domain.schema import DryRunVerdict, Room
from src.domain.validator import BUILD_RULES, DECOY_RULE, RULES, validate
from src.pipeline.author import rule_verdicts
from tests.domain.test_redact import done_job
from tests.fixtures.rooms import SENTINEL_CODE, SENTINEL_IX, with_sentinel_solutions
from tests.web.design import WEB_SRC, source_css
from tests.web.test_build_view_surface import COMPONENTS, _code, _css, _ts
from tests.web.test_contrast import PROPS, _hex, contrast
from tests.web.test_strings import _strings, _voice_and_tone

VERDICTS = (COMPONENTS / "verdict-table.ts").read_text()
JSON_PANE = (COMPONENTS / "build-view-json.ts").read_text()


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]


# --- Verdict table -----------------------------------------------------------------------------------------------


def test_the_verdict_table_is_a_real_table_under_its_caption_with_header_cells():
    strings = _strings()
    assert strings["verdictCaption"] == ("The Validator is code, not a model. It checks rules 1 to 8 on every draft; "
                                         "a failed rule sends the draft back to the Riddler. Rule 9 checks the "
                                         "Trickster's false evidence during play, so a build has none to check.")
    assert [strings[k] for k in ("verdictRule", "verdictCheck", "verdictVerdict")] == ["Rule", "Check", "Verdict"]
    panel = _function(VERDICTS, "panel")
    assert "document.createElement('table')" in panel and "table.tabIndex = 0" in panel
    assert "document.createElement('caption')" in panel and "table.append(title, head, body)" in panel
    assert "th.scope = 'col'" in panel and "text('th', heading, 'label')" in panel
    table = _function(VERDICTS, "verdictTable")
    assert "panel(strings.verdictCaption, [strings.verdictRule, strings.verdictCheck, strings.verdictVerdict]" in table
    assert "[...view.validator.map(ruleRow), decoyRow()]" in table
    rules = _css("components/verdict-table.css")
    assert rules[".verdict-table"]["caption-side"] == "top"
    assert rules[".verdict-table-panel"]["background"] == "var(--chrome)"
    assert rules[".verdict-table thead th"]["border-bottom"] == "1px solid var(--hairline)"
    assert rules[".verdict-table thead th"]["color"] == "var(--text-muted)"
    assert rules[".verdict-table-caption"]["color"] == "var(--text-muted)"


def test_one_row_per_rule_with_its_number_name_and_verdict_word_and_the_message_on_fail_only():
    row = _function(VERDICTS, "ruleRow")
    assert "text('th', String(rule), 'mono-sm verdict-table-number')" in row and "number.scope = 'row'" in row
    assert "text('td', name, 'body-sm')" in row
    assert "if (!passed && message !== undefined) check.append(text('div', message, 'verdict-table-message body-sm'))" in row
    assert "verdictCell(passed ? 'pass' : 'fail')" in row
    assert "text('div', verdict, `verdict-word verdict-word-${verdict} label`)" in _function(VERDICTS, "verdictCell")


def test_the_check_names_and_fixed_messages_are_the_validators_and_the_experience_lines():
    strings = _strings()
    table = _voice_and_tone().split("| Rule | Check name (pass) | Fixed message (fail) |", 1)[1]
    for number in BUILD_RULES:
        rule = RULES[number]
        assert strings[f"rule{number}Failed"] == rule.message
        assert f"| {number} | \"{rule.name}\" | \"{rule.message}\" |" in table
        assert f"{number}: strings.rule{number}Failed," in VERDICTS
    # A build's verdicts are the base checks, rules 1 to 8; rule 9 (Decoys) never fails on a build, so no fail line.
    assert "rule9Failed" not in strings and list(BUILD_RULES) == list(range(1, 9))


def test_rule_9_shows_apart_as_not_applicable_and_the_rules_line_counts_the_base_checks_only(four_lock_room: Room):
    # Owner decision 29: rule 9 is the Decoy check, shown as not applicable on a build, which holds no Decoy.
    strings = _strings()
    assert strings["rule9Name"] == RULES[DECOY_RULE].name and strings["notApplicable"] == "not applicable"
    row = _function(VERDICTS, "decoyRow")
    assert "text('th', String(DECOY_RULE), 'mono-sm verdict-table-number')" in row and "number.scope = 'row'" in row
    assert "text('td', strings.rule9Name, 'body-sm')" in row
    assert "text('div', strings.notApplicable, 'verdict-word verdict-word-skipped label')" in row
    assert "const DECOY_RULE = 9" in VERDICTS
    assert '"not applicable"' in _voice_and_tone()
    # The "Rules: {passed} of {total} passed" line and the Model table's "checked 8 rules" count the build's verdicts,
    # which are the base checks alone, so rule 9 never enters an "8 of 8".
    assert [verdict.rule for verdict in rule_verdicts(validate(four_lock_room))] == list(BUILD_RULES)
    stages = _ts("build-stages.ts")
    assert "fill(strings.rulesPassed, { passed, total: validator.length })" in stages
    assert _strings()["validatorDid"] == f"checked {len(BUILD_RULES)} rules"


def test_the_verdict_markers_are_8px_in_the_graph_colors_and_the_table_fits_the_1280_right_third():
    rules = _css("components/verdict-table.css")
    marker = rules[".verdict-word::before"]
    assert marker["width"] == "8px" and marker["height"] == "8px" and marker["background"] == "currentColor"
    assert rules[".verdict-word-pass"]["color"] == "var(--graph-pass)"
    assert rules[".verdict-word-fail"]["color"] == "var(--graph-fail)"
    assert rules[".verdict-word-skipped"]["color"] == "var(--graph-skipped)"
    assert rules[".verdict-word-skipped::before"]["border"] == "1.5px solid currentColor"
    assert rules[".verdict-table"]["width"] == "100%"
    assert rules[".verdict-table th, .verdict-table td"]["overflow-wrap"] == "break-word"
    assert "nowrap" not in (COMPONENTS / "verdict-table.css").read_text()
    number, word = int(rules[".verdict-table .verdict-table-number"]["width"][:-2]), 88
    right_third = (1280 - 2 * 24 - 24) / 3
    assert right_third - 2 * 16 - number - word > 160, "the check column keeps room for its wrapped name"


# --- Dry run rows ------------------------------------------------------------------------------------------------


def test_the_dry_run_rows_are_one_per_puzzle_under_their_caption():
    strings = _strings()
    assert strings["dryRunCaption"] == ("A separate muse-spark-1.3 call saw only the clues, hints and object names, never "
                                        "the answers, and tried every puzzle.")
    assert [strings[k] for k in ("dryRunPuzzle", "dryRunLockType", "verdictVerdict")] == ["Puzzle", "Lock type", "Verdict"]
    rows = VERDICTS.split("export function dryRunRows(", 1)[1]
    assert "view.puzzles.map((puzzle, index) =>" in rows
    assert "text('th', String(index + 1), 'mono-sm verdict-table-number')" in rows
    assert "text('td', puzzle.lock_type, 'mono-sm')" in rows
    assert "const words = view.puzzles.map((puzzle) => verdicts.get(puzzle.id) ?? DRY_RUN_OFF)" in rows
    assert "verdictCell(words[index])" in rows
    assert "panel(caption, [strings.dryRunPuzzle, strings.dryRunLockType, strings.verdictVerdict], rows)" in rows


def test_under_cut_4_every_row_reads_skipped_and_the_cut_4_caption_replaces_the_usual_one():
    strings = _strings()
    assert strings["dryRunOffCaption"] == "The test run was switched off for this build, so no puzzle was tried blind."
    rows = VERDICTS.split("export function dryRunRows(", 1)[1]
    assert "const off = words.length > 0 && words.every((word) => word === DRY_RUN_OFF)" in rows
    assert "const caption = off ? strings.dryRunOffCaption : strings.dryRunCaption" in rows
    assert "const DRY_RUN_OFF: Word = 'skipped'" in VERDICTS
    assert set(get_args(DryRunVerdict.model_fields["verdict"].annotation)) == {"pass", "fail", "skipped"}


# --- Build JSON pane ---------------------------------------------------------------------------------------------


def test_the_json_pane_is_collapsed_behind_its_toggle_and_shows_the_response_as_served():
    strings = _strings()
    assert strings["showBuildJson"] == "Show the build JSON"
    assert strings["buildJsonCaption"] == ("Everything this page receives. It holds no answers; a sentinel test checks "
                                           "every build for them.")
    assert "label: strings.showBuildJson," in JSON_PANE and "state: 'expanded'," in JSON_PANE
    assert "controls: PANE_ID," in JSON_PANE and "pane.hidden = true" in JSON_PANE
    assert "pane.hidden = !open" in JSON_PANE
    assert "caption.textContent = strings.buildJsonCaption" in JSON_PANE and "pane.append(caption, data)" in JSON_PANE
    assert "data.textContent = JSON.stringify(view, null, 2)" in JSON_PANE
    assert "data.className = 'build-view-json-data mono-sm'" in JSON_PANE
    # A focusable, scrollable region named by its caption.
    assert "data.tabIndex = 0" in JSON_PANE and "data.setAttribute('role', 'region')" in JSON_PANE
    assert "data.setAttribute('aria-labelledby', CAPTION_ID)" in JSON_PANE
    rules = _css("components/build-view-json.css")
    assert rules[".build-view-json-data"]["max-height"] == "360px" and rules[".build-view-json-data"]["overflow"] == "auto"
    assert rules[".build-view-json"]["background"] == "var(--chrome)"
    assert rules[".build-view-json-caption"]["color"] == "var(--text-muted)"
    assert rules[".build-view-json-pane[hidden]"]["display"] == "none"
    # The toggle is the shared secondary toggle, announcing its expanded state.
    button = _ts("components/button.ts")
    assert "const attribute = state === 'pressed' ? 'aria-pressed' : 'aria-expanded'" in button


def test_the_json_pane_sits_under_the_mask_overlays():
    view = _ts("build-view.ts")
    assert "left.append(puzzleGraph(state.view), maskOverlays(state.view), buildViewJson(state.view))" in view


# --- No answer anywhere ------------------------------------------------------------------------------------------


def test_the_build_view_of_a_sentinel_room_holds_no_answer_pairing_or_repeated_clue(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    served = to_build_view(room, done_job(room)).model_dump_json()
    # The JSON pane prints this response; the tables and the graph draw only fields of it.
    for sentinel in (SENTINEL_CODE, *SENTINEL_IX):
        assert sentinel not in served
    for puzzle in room.puzzles:
        for text in (puzzle.clue, puzzle.lore, puzzle.rungs.nudge, puzzle.rungs.direction, puzzle.rungs.near_answer):
            assert text not in served, "no Clue, Lore or Rung is repeated on the Build view"
    data = json.loads(served)
    assert {"solution", "clue", "answers"}.isdisjoint(data) and all("solution" not in p for p in data["puzzles"])
    for path, text in {"verdict-table.ts": VERDICTS, "build-view-json.ts": JSON_PANE}.items():
        code = _code(text)
        assert not re.search(r"solution|answer|clue", code, re.IGNORECASE), path
        assert not re.search(r"\b(getRoom|listRooms|getSession|startSession|fetch)\b", code), f"{path} requests"


# --- Tab order ---------------------------------------------------------------------------------------------------


def test_tab_runs_title_back_model_table_in_play_verdicts_dry_run_graph_chips_then_the_json_toggle():
    view = _ts("build-view.ts")
    assert "right.append(modelTable(state.view, meta), inPlayBlock(meta), verdictTable(state.view), dryRunRows(state.view))" in view
    assert "columns.append(right, left)" in view
    assert "return { children: [header.element, columns], focus: () => header.title?.focus() }" in view
    # Each table is one Tab stop; the toggle comes before the pane it opens.
    assert "table.tabIndex = 0" in VERDICTS
    assert "panel.append(toggle, pane)" in JSON_PANE
    assert "tabIndex = -1" not in _code(VERDICTS) + _code(JSON_PANE)


# --- Entry links -------------------------------------------------------------------------------------------------


def test_the_link_opens_the_build_view_of_that_job_and_cut_0_drops_every_one():
    strings, router, view = _strings(), _ts("router.ts"), _ts("build-view.ts")
    assert strings["howBuilt"] == "How this room was built"
    assert "export const CUT_0: boolean = false" in router
    assert "return placeHref({ route: { name: 'view', jobId }, profile })" in router
    link = _function(view, "buildViewLink")
    assert link.split("{\n", 1)[1].lstrip().startswith("if (CUT_0) return null")
    assert "secondaryLink({ label: strings.howBuilt, href: buildViewHref(jobId, profile), onParchment })" in link
    button = _ts("components/button.ts")
    assert "document.createElement('a')" in button and "element.className = 'button-secondary'" in button
    assert _css("components/button.css")[".button-secondary"]["text-decoration"] == "none"
    # Every link to the Build view goes through `buildViewLink`, so cut 0 drops them all.
    for path, text in {"components/stored-room-row.ts": _ts("components/stored-room-row.ts"),
                       "build-progress.ts": _ts("build-progress.ts"), "completion.ts": _ts("completion.ts")}.items():
        code = _code(text)
        assert "buildViewLink(" in code and "if (CUT_0)" not in code and "/view" not in code, path


# Imports the shipped router with CUT_0 set as given and prints where each hash resolves.
ROUTER_RUNNER = """
const { parsePlace } = await import(process.argv[1])
const hashes = JSON.parse(process.argv[2])
process.stdout.write(JSON.stringify(hashes.map((hash) => parsePlace(hash, '').route)))
"""
HASHES = ["#/build/job_01ABC/view?profile=demo", "#/build/job_01ABC?profile=demo", "#/nowhere?profile=demo"]


def _routes_under(cut_0: bool, tmp_path: Path) -> list[dict[str, str]]:
    source = (WEB_SRC / "router.ts").read_text()
    assert "export const CUT_0: boolean = false" in source
    router = tmp_path / "router.ts"
    router.write_text(source.replace("export const CUT_0: boolean = false",
                                     f"export const CUT_0: boolean = {'true' if cut_0 else 'false'}"))
    result = subprocess.run(["node", "--input-type=module", "-e", ROUTER_RUNNER, router.as_uri(), json.dumps(HASHES)],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's router")
def test_under_cut_0_the_direct_build_view_route_is_an_unknown_route_and_reads_nothing(tmp_path: Path):
    # Owner decision 45: cut 0 guards the direct route too, with the view an unknown route gets.
    view, capture, unknown = _routes_under(True, tmp_path)
    assert view == unknown == {"name": "home"} and capture == {"name": "build", "jobId": "job_01ABC"}
    # Without cut 0 the hash still opens the Build view.
    assert _routes_under(False, tmp_path)[0] == {"name": "view", "jobId": "job_01ABC"}
    # The shell reads GET /builds/<job_id>/view only on the view route, so under cut 0 nothing is fetched.
    shell = _code(_ts("shell.ts"))
    assert shell.count("loadBuildView(") == 1 and shell.count("getBuildView(") == 0
    assert "if (place.route.name === 'view') {\n      const state = await loadBuildView(place.route.jobId)" in shell


def test_the_stored_room_row_links_its_summarys_job_after_play():
    row = _ts("components/stored-room-row.ts")
    assert row.index("secondaryButton({ label: strings.play, onActivate: onPlay })") < row.index(
        "const link = buildViewLink(room.job_id, profile)")
    assert "if (link !== null) row.append(link)" in row


def test_a_done_build_shows_the_link_live_or_reopened():
    done = _function(_code(_ts("build-progress.ts")), "done")
    assert done.index("const link = buildViewLink(jobId, profile)") < done.index("if (live) {")
    live = done.split("if (live) {", 1)[1].split("void start(roomId)", 1)[0]
    # A Build seen finishing shows the link while its Session starts, so a refused start still reaches the Build view.
    assert "if (link !== null) {" in live and "actions.replaceChildren(link)" in live
    assert "actions.hidden = false" in live
    assert "actions.replaceChildren(play, ...(link === null ? [] : [link]))" in done


def test_the_completion_sheet_links_the_build_view_of_the_rooms_job_on_parchment():
    completion = _ts("completion.ts")
    job = _function(completion, "roomJob")
    assert "const opened = sessionJob(session.id)" in job
    assert "(await listRooms()).find((room) => room.room_id === session.room_id)?.job_id ?? null" in job
    assert "buildViewLink(jobId, profile, true)" in completion
    assert "if (mounted && link !== null) copy.after(link)" in completion  # after "Build another room" and "Copy your result"
    timer = _ts("capture-timer.ts")
    assert "return run !== null && run.sessionId === sessionId ? run.jobId : null" in timer


def test_back_on_the_build_view_returns_to_where_the_link_was_followed():
    render = _ts("shell.ts").split("async function render()", 1)[1]
    assert "if (navigated) history.back()" in render
    assert "navigated = true" in _ts("shell.ts")


# --- Accessibility floor -----------------------------------------------------------------------------------------


def test_every_control_and_region_keeps_the_global_focus_ring_and_text_meets_aa_on_chrome():
    for path, text in source_css().items():
        if any(name in path for name in ("verdict-table", "build-view-json")):
            assert "outline" not in text and "box-shadow" not in text, f"{path} keeps the global focus ring"
            assert not re.search(r"transition|animation|@keyframes", text), path
    chrome = _hex(PROPS["chrome"])[0]
    for token in ("text", "text-muted", "graph-pass", "graph-fail", "graph-skipped", "lamp"):
        assert contrast(_hex(PROPS[token])[0], chrome) >= 4.5, token
    parchment = _hex(PROPS["parchment"])[0]
    assert contrast(_hex(PROPS["lamp-ink"])[0], parchment) >= 4.5  # the Completion sheet's link
