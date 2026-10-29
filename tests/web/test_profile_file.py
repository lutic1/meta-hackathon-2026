"""Story 5.4, FR-20, UX-DR20, UX-DR44, UX-DR84, AD-8: under cut 2 the Player profile is a file on this computer.

`web/profile`'s file backend runs in Node as it ships, its `/api/profile/<name>` answered in the runner (see
`tests/web/test_player_profile.py`) with the status the real Local-mode route gives each body, and every request it
makes recorded; the bodies it writes are put through the real route. The two controls are checked by reading the
TypeScript and the stylesheets, as the other web tests do; `npm run build` and `tsc --noEmit` prove they compile.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.domain.schema import Derived, Profile
from tests.api.test_app import make_app
from tests.web.design import REPO, WEB_SRC, css_rules, design_text, source_ts
from tests.web.test_contrast import _color, contrast
from tests.web.test_player_profile import (
    FIXTURE,
    SESSION_1,
    SESSION_2,
    needs_node,
    puzzle,
    result,
    room_id,
    run_profile,
)
from tests.web.test_strings import _strings

COMPONENTS = WEB_SRC / "components"
PROFILE_ROUTE = "/api/profile/dev"


def _code(name: str) -> str:
    """TypeScript with its comments removed, so a doc comment may quote a line it explains."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]


@pytest.fixture
def route(tmp_path: Path) -> TestClient:
    """The real app in Local mode, whose `PUT /profile/<name>` gives each body its status."""
    return TestClient(make_app(tmp_path))


@pytest.fixture
def fresh_json() -> dict[str, Any]:
    return json.loads(Derived.fresh().model_dump_json())


def profile_text(*results: dict[str, Any], derived: dict[str, Any]) -> str:
    """A profile file shaped as "Save profile file" writes it: every result keyed by `room_id`, then the Derived block."""
    return json.dumps({"results": {r["room_id"]: r for r in results}, "derived": derived})


ROOM_1 = FIXTURE[0]
ON_DISK = profile_text(ROOM_1, derived={"sessions": 1, "persistence": 0.5, "time_to_first_hint_s": 50.0,
                                         "mean_rung_per_lock_type": {"code": 1.0, "find": 1.0}})


def _profile_requests(requests: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(r["method"], r["url"]) for r in requests]


# --- The file backend: no read or write before "Open profile file" ----------------------------------------------------


@needs_node
def test_until_a_file_is_opened_the_profile_lives_in_the_page_and_nothing_is_read_or_written(fresh_json: dict[str, Any]):
    out = run_profile([["seed", "dev", ON_DISK], ["results", "dev"], ["derived", "dev"], ["start", room_id(7), "dev", "local"],
                       ["put", "dev", FIXTURE[1]], ["results", "dev"], ["file", "dev"]])
    assert out["answers"][1:4] == [[], fresh_json, {"room_id": room_id(7), "derived": fresh_json}]
    assert out["answers"][4] is None and out["answers"][5] == [FIXTURE[1]]  # the result is recorded, in the page
    assert out["answers"][6]["results"] == {FIXTURE[1]["room_id"]: FIXTURE[1]}  # and "Save profile file" downloads it
    assert out["requests"] == []  # no GET or PUT /profile/<name> before the player opens the file (decision 27, 48)
    assert out["files"] == {"dev": ON_DISK}  # the stored file is untouched
    # And no IndexedDB: under cut 2 the file backend stands in front of the 5.2 database, which nothing else opens.
    assert "export const CUT_2: boolean = true" in _code("profile/index.ts")
    assert "const storage = CUT_2 ? memoryStorage() : browserStorage(name)" in _code("profile/index.ts")
    for path, text in source_ts().items():
        if path != "web/src/profile/index.ts":
            assert "indexedDB" not in text and "IDBDatabase" not in text, path


@needs_node
def test_once_opened_each_stored_result_writes_the_whole_profile_the_real_route_accepts(route: TestClient):
    replay = result(2, [puzzle(9, "order", rungs=2, first_hint_s=30, nudge=True)])
    out = run_profile([["open", "dev", ON_DISK, 200], ["put", "dev", replay], ["derived", "dev"]])
    assert _profile_requests(out["requests"]) == [("PUT", PROFILE_ROUTE), ("GET", PROFILE_ROUTE), ("PUT", PROFILE_ROUTE)]
    written = json.loads(out["requests"][2]["body"])
    # GET|PUT carries the stored RoomResult entries and the Derived block (the cut-2 exception), keyed by room_id.
    assert written == {"results": {ROOM_1["room_id"]: ROOM_1, replay["room_id"]: replay}, "derived": out["answers"][2]}
    assert route.put(PROFILE_ROUTE, json=written).status_code == 200


@needs_node
def test_a_session_start_still_sends_only_room_id_and_derived():
    out = run_profile([["put", "dev", ROOM_1], ["start", room_id(7), "dev", "local"], ["derived", "dev"]])
    assert out["answers"][1] == {"room_id": room_id(7), "derived": out["answers"][2]}
    assert _code("api/index.ts").count("startSession(body: SessionStart)") == 1


@needs_node
def test_hosted_mode_sends_nothing_from_the_profile(fresh_json: dict[str, Any]):
    out = run_profile([["put", "dev", ROOM_1, "hosted"], ["results", "dev"], ["start", room_id(7), "dev", "hosted"]])
    assert out["requests"] == []  # no profile route in Hosted mode, so no RoomResult is ever sent there
    assert out["answers"][1] == [ROOM_1] and out["answers"][2] == {"room_id": room_id(7), "derived": fresh_json}


# --- Opening merges: the file's results are never dropped -------------------------------------------------------------


@needs_node
def test_opening_merges_the_files_results_with_the_ones_this_page_recorded(route: TestClient):
    # Rooms 1 and 2 were played in an earlier page load; this one finished Room 3 before "Open profile file".
    room_3 = result(3, [puzzle(9, "order", rungs=2, first_hint_s=30, nudge=True)])
    on_disk = profile_text(ROOM_1, FIXTURE[1], derived=json.loads(ON_DISK)["derived"])
    out = run_profile([["watch", "dev"], ["put", "dev", room_3], ["open", "dev", on_disk, 200], ["results", "dev"]])
    assert _profile_requests(out["requests"]) == [("PUT", PROFILE_ROUTE), ("GET", PROFILE_ROUTE), ("PUT", PROFILE_ROUTE)]
    written = json.loads(out["files"]["dev"])
    assert written["results"] == {ROOM_1["room_id"]: ROOM_1, FIXTURE[1]["room_id"]: FIXTURE[1], room_3["room_id"]: room_3}
    assert written["derived"] == run_profile([["derive", [ROOM_1, FIXTURE[1], room_3]]])["answers"][0]
    assert out["answers"][3] == [ROOM_1, FIXTURE[1], room_3] and out["heard"] == [1, 3]
    assert route.put(PROFILE_ROUTE, json=written).status_code == 200


@needs_node
def test_a_result_this_page_recorded_replaces_the_files_except_a_demo_result_over_a_counted_one():
    counted, demo = result(1, [puzzle(1, rungs=1)]), result(1, [puzzle(1, rungs=3)], demo=True)
    out = run_profile([["put", "dev", demo], ["open", "dev", profile_text(counted, derived=json.loads(ON_DISK)["derived"]), 200]])
    assert json.loads(out["files"]["dev"])["results"] == {counted["room_id"]: counted}
    assert [r["method"] for r in out["requests"]] == ["PUT", "GET"]  # nothing changed, so nothing more is written
    out = run_profile([["put", "dev", counted], ["open", "dev", profile_text(demo, derived=json.loads(ON_DISK)["derived"]), 200]])
    assert json.loads(out["files"]["dev"])["results"] == {counted["room_id"]: counted}


def _played_twice() -> tuple[dict[str, Any], dict[str, Any], str]:
    """Room 1 played twice, older then newer, and the profile file holding the newer result (decision record, item 54)."""
    older, newer = result(1, [puzzle(1, rungs=3)]), result(1, [puzzle(1, rungs=0)], elapsed_ms=200000)
    return older, newer, profile_text(newer, derived=run_profile([["derive", [newer]]])["answers"][0])


@needs_node
def test_a_reopened_done_pages_older_result_never_replaces_the_files_newer_one(route: TestClient):
    # A fresh page load mounts the older Session's Done page (a reload, a bookmark, history), then opens the file.
    older, newer, on_disk = _played_twice()
    out = run_profile([["put", "dev", older, "local", SESSION_1, True], ["open", "dev", on_disk, 200], ["results", "dev"]])
    assert out["answers"][1] is None and out["answers"][2] == [newer]
    assert json.loads(out["files"]["dev"])["results"] == {newer["room_id"]: newer}
    assert [r["method"] for r in out["requests"]] == ["PUT", "GET"]  # the file kept its result, so nothing is written back
    # Opened first, the older Done page reopened after it records nothing over the file's result, and writes nothing.
    out = run_profile([["open", "dev", on_disk, 200], ["put", "dev", older, "local", SESSION_1, True], ["results", "dev"]])
    assert out["answers"][2] == [newer] and [r["method"] for r in out["requests"]] == ["PUT", "GET"]
    assert json.loads(out["files"]["dev"])["results"] == {newer["room_id"]: newer}


@needs_node
def test_a_reopened_done_page_fills_a_room_the_file_lacks_and_a_session_ended_here_replaces_the_files():
    older, newer, on_disk = _played_twice()
    room_3 = result(3, [puzzle(9, "order", rungs=2)])
    out = run_profile([["put", "dev", room_3, "local", SESSION_1, True], ["open", "dev", on_disk, 200], ["results", "dev"]])
    assert out["answers"][2] == [newer, room_3]
    assert json.loads(out["files"]["dev"])["results"] == {newer["room_id"]: newer, room_3["room_id"]: room_3}
    # The Completion screen that followed the Exit in this page load is the latest play, so the file takes its result.
    out = run_profile([["put", "dev", older, "local", SESSION_2, False], ["open", "dev", on_disk, 200], ["results", "dev"]])
    assert out["answers"][2] == [older] and json.loads(out["files"]["dev"])["results"] == {older["room_id"]: older}


@needs_node
def test_a_file_gone_by_the_read_is_an_empty_file_the_pages_results_are_written_to():
    out = run_profile([["put", "dev", ROOM_1], ["lose"], ["open", "dev", ON_DISK, 200], ["results", "dev"],
                       ["start", room_id(7), "dev", "local"]])
    assert [r["method"] for r in out["requests"]] == ["PUT", "GET", "PUT"] and out["answers"][3] == [ROOM_1]
    assert json.loads(out["files"]["dev"])["results"] == {ROOM_1["room_id"]: ROOM_1}
    assert out["answers"][4]["derived"] == run_profile([["derive", [ROOM_1]]])["answers"][0]


# --- A save that fails keeps the progress and can be tried again ------------------------------------------------------


@needs_node
def test_a_failed_save_keeps_the_result_in_the_page_and_try_again_writes_it():
    out = run_profile([["open", "dev", ON_DISK, 200], ["fail"], ["put", "dev", FIXTURE[1]], ["results", "dev"],
                       ["save", "dev"], ["results", "dev"]])
    assert out["answers"][2] == "FileNotSaved" and out["answers"][3] == [ROOM_1, FIXTURE[1]]  # progress is still here
    assert out["answers"][4] is None and out["answers"][5] == [ROOM_1, FIXTURE[1]]
    assert [r["method"] for r in out["requests"]] == ["PUT", "GET", "PUT", "PUT"]
    assert json.loads(out["files"]["dev"])["results"] == {ROOM_1["room_id"]: ROOM_1, FIXTURE[1]["room_id"]: FIXTURE[1]}


@needs_node
def test_a_merge_that_fails_to_save_still_shows_the_merged_profile():
    out = run_profile([["put", "dev", FIXTURE[1]], ["open", "dev", ON_DISK, 200, 503], ["results", "dev"], ["save", "dev"]])
    assert out["answers"][1] == "FileNotSaved" and out["answers"][2] == [ROOM_1, FIXTURE[1]]
    assert out["answers"][3] is None
    assert json.loads(out["files"]["dev"])["results"] == {ROOM_1["room_id"]: ROOM_1, FIXTURE[1]["room_id"]: FIXTURE[1]}


@needs_node
def test_saving_before_a_file_is_opened_writes_nothing():
    out = run_profile([["put", "dev", ROOM_1], ["save", "dev"]])
    assert out["answers"][1] is None and out["requests"] == []


# --- "Open profile file" ---------------------------------------------------------------------------------------------


@needs_node
def test_opening_a_file_puts_it_then_reads_it_back_and_the_count_follows_at_once(route: TestClient):
    assert route.put(PROFILE_ROUTE, content=ON_DISK).status_code == 200
    out = run_profile([
        ["watch", "dev"], ["open", "dev", ON_DISK, 200], ["results", "dev"], ["derived", "dev"],
        ["put", "dev", FIXTURE[1]], ["results", "dev"],
    ])
    # The chosen bytes go as they are, then GET reads the file the route wrote; then every write is the whole file.
    assert _profile_requests(out["requests"]) == [("PUT", PROFILE_ROUTE), ("GET", PROFILE_ROUTE), ("PUT", PROFILE_ROUTE)]
    assert out["requests"][0]["body"] == ON_DISK
    assert out["answers"][1] is None and out["answers"][2] == [ROOM_1]
    assert out["answers"][3] == run_profile([["derive", [ROOM_1]]])["answers"][0]  # recomputed from the results
    assert out["answers"][5] == [ROOM_1, FIXTURE[1]]
    assert out["heard"] == [1, 2]  # the mode indicator hears the opened file at once
    assert set(json.loads(out["files"]["dev"])["results"]) == {ROOM_1["room_id"], FIXTURE[1]["room_id"]}


@pytest.mark.parametrize("text", [
    "not a profile {",
    profile_text(ROOM_1, derived={"sessions": 1, "persistence": 1.5, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}}),
    profile_text(ROOM_1, derived={"sessions": 1, "persistence": 0, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {"code": 4}}),
    json.dumps({"results": {room_id(1): {"room_id": room_id(1)}}, "derived": Derived.fresh().model_dump(mode="json")}),
], ids=["unparseable", "persistence-1.5", "rung-4", "result-unparseable"])
@needs_node
def test_a_refused_file_leaves_the_current_profile_unchanged(route: TestClient, text: str):
    status = route.put(PROFILE_ROUTE, content=text).status_code
    assert status == 422
    out = run_profile([
        ["watch", "dev"], ["put", "dev", ROOM_1], ["derived", "dev"],
        ["open", "dev", text, status], ["results", "dev"], ["derived", "dev"], ["start", room_id(7), "dev", "local"],
        ["put", "dev", FIXTURE[1]],
    ])
    assert out["answers"][3] == 422
    assert out["answers"][4] == [ROOM_1] and out["answers"][5] == out["answers"][2]
    assert out["answers"][6]["derived"] == out["answers"][2]  # no Session starts from the refused file
    assert out["heard"] == [1, 2]
    assert [r["method"] for r in out["requests"]] == ["PUT"]  # nothing read after the refusal, and still nothing written
    assert out["files"] == {}


# --- "Save profile file" ---------------------------------------------------------------------------------------------


@needs_node
def test_save_gives_the_current_profile_with_the_result_just_recorded(route: TestClient):
    out = run_profile([["put", "dev", ROOM_1], ["put", "dev", FIXTURE[1]], ["file", "dev"], ["derived", "dev"]])
    saved = out["answers"][2]
    assert saved == {"results": {ROOM_1["room_id"]: ROOM_1, FIXTURE[1]["room_id"]: FIXTURE[1]}, "derived": out["answers"][3]}
    Profile.model_validate(saved)
    assert route.put(PROFILE_ROUTE, json=saved).status_code == 200  # the saved file opens again


def test_save_downloads_the_profile_as_name_json():
    save = _function(_code("components/profile-file.ts"), "saveProfileControl")
    assert "label: strings.saveProfileFile" in save and "onParchment: true" in save
    assert "new Blob([JSON.stringify(current, null, 2)], { type: 'application/json' })" in save
    assert "link.download = `${name}.json`" in save and "link.click()" in save
    assert "URL.revokeObjectURL(url)" in save


# --- The controls, under cut 2 only -----------------------------------------------------------------------------------


def test_cut_2_is_taken_and_gates_both_controls_and_the_line():
    assert "export const CUT_2: boolean = true" in _code("profile/index.ts")
    assert "const file = CUT_2 ? fileStorage(name) : null" in _code("profile/index.ts")
    # The line and both controls live in one component, used only behind CUT_2 in Local mode.
    users = {path for path, text in source_ts().items() if re.search(r"strings\.(openProfileFile|saveProfileFile|profileFileLine)", text)}
    assert users == {"web/src/components/profile-file.ts", "web/src/capture.ts"}
    capture, completion = _code("capture.ts"), _code("completion.ts")
    assert "openProfileControl(" in _function(capture, "openProfile").split("\n", 1)[1]
    assert _function(capture, "openProfile").split("\n", 2)[1].strip() == "if (!CUT_2 || mode !== 'local') return null"
    offer = completion.split("function offerSave(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert offer.strip().startswith("if (!mounted || !CUT_2 || mode !== 'local') return")
    for path, text in source_ts().items():
        if path not in ("web/src/components/profile-file.ts", "web/src/capture.ts", "web/src/completion.ts"):
            assert not re.search(r"\b(openProfileControl|saveProfileControl)\b", text), path
    assert capture.count("openProfileControl(") == 1 and completion.count("saveProfileControl(") == 1


def test_the_strings_are_the_cut_2_placeholder_lines():
    strings = _strings()
    assert strings["openProfileFile"] == "Open profile file" and strings["saveProfileFile"] == "Save profile file"
    assert strings["profileFileLine"] == "Your player profile is a file on this computer; Keyframe reads it only when you open it."
    assert strings["privacyLine"] == "the player profile stays on your machine."  # unchanged under cut 2


def test_open_profile_file_sits_below_the_unchanged_privacy_line_and_the_tray_stays_expanded():
    summary = _code("components/retention-summary.ts")
    assert "summary.append(heading, text, label, privacy)\n  if (profileFile !== null) summary.append(profileFile)" in summary
    assert "privacy.textContent = strings.privacyLine" in summary
    control = _function(_code("components/profile-file.ts"), "openProfileControl")
    assert "input.type = 'file'" in control and "input.accept = '.json,application/json'" in control and "input.hidden = true" in control
    assert "secondaryButton({ label: strings.openProfileFile, onActivate: choose })" in control
    assert "element.append(secondaryButton({ label: strings.openProfileFile, onActivate: choose }), profileFileLine(), input)" in control
    line = _function(_code("components/profile-file.ts"), "profileFileLine")
    assert "line.className = 'profile-file-line body-sm'" in line and "line.textContent = strings.profileFileLine" in line
    rules = css_rules((COMPONENTS / "profile-file.css").read_text())
    assert rules[".profile-file-line"]["color"] == "var(--text-muted)"
    assert rules[".profile-file-line.on-parchment"]["color"] == "var(--ink-muted)"
    for rule in rules.values():
        assert not {"overflow", "max-height", "height", "text-overflow", "-webkit-line-clamp", "white-space"} & set(rule)
    # Before and during a Build the right column takes the control, its refusals going to that surface's banner slot.
    assert "right: captureColumn(retention, profile, mode, banners)" in _code("build-progress.ts")


def test_a_refused_file_shows_the_error_banner_which_takes_focus_and_a_good_one_clears_it():
    opener = _function(_code("capture.ts"), "openProfile")
    assert "void openProfileFile(profile, file).then(cleared, (error: unknown) => {" in opener
    assert "if (refusal?.isConnected) showBanner(banners, null)" in opener
    assert "const action = { label: strings.openProfileFile, onActivate: control.choose }" in opener
    assert "refusal = showBanner(banners, { variant: 'error', heading: strings.profileFileRefused, actions: [action] })" in opener
    # A file opened and merged whose write then failed is not a refusal: the warning offers "Try again", which writes it.
    assert "if (error instanceof FileNotSaved) return notSaved()" in opener
    assert "const action = { label: strings.tryAgain, onActivate: () => void saveProfileFile(profile).then(cleared, () => {}) }" in opener
    assert "refusal = showBanner(banners, { variant: 'warning', heading: strings.profileNotSaved, actions: [action] })" in opener
    assert _strings()["profileFileRefused"] == "Keyframe couldn't read this profile file."
    assert "slot.replaceChildren(element)\n  element.focus()" in (COMPONENTS / "error-banner.ts").read_text()


def test_save_profile_file_sits_with_the_completion_actions_once_the_result_is_recorded():
    completion = _code("completion.ts")
    load = completion.split("async function load(): Promise<void> {", 1)[1].split("\n  }\n", 1)[0]
    assert "const recorded = putResult(profile, result, mode, session.id, !endedOnPlay(session.id))" in load
    # Saved or not, the result is recorded in the page, so "Save profile file" is offered either way.
    assert load.split("void recorded.then(", 1)[1].count("offerSave()") == 2
    offer = completion.split("function offerSave(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "const save = saveProfileControl(profile, () => profileFile(profile))" in offer
    assert "actions.append(save.button)" in offer and "copied.after(save.line)" in offer
    # "Build another room", then "How this room was built", then "Save profile file".
    assert "actions.append(buildAnother, copy)" in completion and "copy.after(link)" in completion


# --- Keyboard and contrast --------------------------------------------------------------------------------------------


def test_both_controls_are_native_buttons_in_tab_order_with_the_focus_ring_and_aa_contrast():
    component = _code("components/profile-file.ts")
    assert component.count("secondaryButton(") == 2 and "tabIndex" not in component and "role" not in component
    assert not re.search(r"outline:\s*(none|0)", (COMPONENTS / "profile-file.css").read_text())
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    # Label and border: lamp on chrome-raised (Retention summary), lamp-ink on parchment (Completion sheet); the line in
    # text-muted and ink-muted on the same surfaces.
    for fg, bg in (("lamp", "chrome-raised"), ("lamp-ink", "parchment"), ("text-muted", "chrome-raised"), ("ink-muted", "parchment"),
                   ("focus-ring-inner", "parchment")):
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    for fg, bg, floor in (("lamp", "chrome-raised", 4.5), ("lamp-ink", "parchment", 4.5), ("text-muted", "chrome-raised", 4.5),
                          ("ink-muted", "parchment", 4.5), ("focus-ring", "chrome-raised", 3.0)):
        assert contrast(_color(f"`{fg}`"), _color(f"`{bg}`")) >= floor, f"{fg} on {bg}"


# --- The README -------------------------------------------------------------------------------------------------------


def test_the_readme_states_the_hosted_profile_behavior_under_cut_2():
    readme = (REPO / "README.md").read_text()
    shipped = readme.split("\n## Cuts shipped\n", 1)[1].split("\n## ", 1)[0]
    sentence = ("In Hosted mode there is no `/profile/<name>` route, every Session start sends `Derived.fresh()`, "
                "and hosted rooms show the First-room welcome.")
    assert sentence in shipped and "Cut 2" in shipped
