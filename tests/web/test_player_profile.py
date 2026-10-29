"""FR-20, FR-21, FR-22, FR-13, UX-DR12, UX-DR44, UX-DR82, AD-8: `web/profile`, the Player profile's only writer.

The profile module and its Derived block have no DOM and no CSS, so Node (which strips the types) runs them as they
ship, on the backend they ship with (cut 2's file backend, its `/api/profile/<name>` answered in the runner and every
request it makes recorded), against Room results built and validated by the server's pydantic models; the Derived
block it computes is validated by the server's `Derived`. The wiring around it (the Completion screen recording, the
Session starts, the mode indicator) is checked by reading the TypeScript, as the other web tests do; `npm run build`
and `tsc --noEmit` prove it compiles.
"""

import json
import random
import re
import shutil
import subprocess
from typing import Any

import pytest

from src.domain.schema import Derived, PuzzleResult, RoomResult
from tests.web.design import REPO, WEB_SRC, source_ts
from tests.web.test_strings import _strings

PROFILE = WEB_SRC / "profile"
LOCK_TYPES = ("code", "order", "use_on", "find")

# Runs one scenario against a fresh import of web/profile: each step is a call, and its answer is printed in order.
# `fetch` answers `/api/profile/<name>` as the Local-mode route does, from the files `seed` puts there: a GET of no file
# is 404 (after `lose`, every file is gone by the time a GET reads it), a PUT stores its body and echoes it unless the
# `open` step names the status the real route gave that body (and any PUT after it), or `fail` made the next PUT a 503.
# A `put` is in Local mode unless it names the mode, comes from a Session later than every earlier `put`'s unless it
# names one, and from a Completion screen that followed the Exit in this page load unless it says `true` (reopened); it
# answers null, or the name of the error it threw.
RUNNER = """
import { readFileSync } from 'node:fs'
const files = new Map()
const requests = []
const verdicts = []
let lost = false
let sessions = 0
const nextSession = () => `sess_${String(++sessions).padStart(26, '0')}`
const answer = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const refusal = (status, code) => answer(status, { error: { code, message: code, stage: null } })
globalThis.fetch = async (url, init = {}) => {
  const method = init.method ?? 'GET'
  const body = init.body === undefined ? null : init.body instanceof Blob ? await init.body.text() : init.body
  requests.push({ url, method, body })
  const name = decodeURIComponent(/^[/]api[/]profile[/]([^/?]+)$/.exec(url)?.[1] ?? '')
  if (name === '') return refusal(404, 'not_found')
  if (method === 'GET' && lost) files.delete(name)
  if (method === 'GET') return files.has(name) ? answer(200, JSON.parse(files.get(name))) : refusal(404, 'profile_not_found')
  const status = verdicts.shift() ?? 200
  if (status !== 200) return refusal(status, 'invalid_profile')
  files.set(name, body)
  return answer(200, JSON.parse(body))
}
const [profile, derive] = await Promise.all(process.argv.slice(1).map((url) => import(url)))
const answers = []
const heard = []
for (const [call, ...args] of JSON.parse(readFileSync(0, 'utf8'))) {
  if (call === 'put') {
    const put = profile.putResult(args[0], args[1], args[2] ?? 'local', args[3] ?? nextSession(), args[4] ?? false)
    answers.push(await put.then(() => null, (error) => error.name))
  }
  else if (call === 'seed') answers.push(files.set(args[0], args[1]) && null)
  else if (call === 'lose') answers.push((lost = true) && null)
  else if (call === 'fail') answers.push(verdicts.push(503) && null)
  else if (call === 'save') answers.push(await profile.saveProfileFile(...args).then(() => null, (error) => error.name))
  else if (call === 'temporary') answers.push(await profile.profileTemporary(...args))
  else if (call === 'open') {
    verdicts.push(...(args.length > 2 ? args.slice(2) : [200]))
    answers.push(await profile.openProfileFile(args[0], new Blob([args[1]])).then(() => null, (error) => error.status ?? error.name))
  }
  else if (call === 'file') answers.push(await profile.profileFile(...args))
  else if (call === 'results') answers.push(await profile.getResults(...args))
  else if (call === 'derived') answers.push(await profile.getDerived(...args))
  else if (call === 'start') answers.push(await profile.sessionStart(...args))
  else if (call === 'derive') answers.push(derive.derive(...args))
  else if (call === 'watch') answers.push(profile.watchResults(args[0], (results) => heard.push(results.length)) && null)
  else throw new Error(`unknown call ${call}`)
}
process.stdout.write(JSON.stringify({ answers, heard, requests, files: Object.fromEntries(files) }))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs web/profile as it ships")


def run_profile(steps: list[list[Any]]) -> dict[str, Any]:
    """The scenario's `answers`, what the listeners `heard`, every request web/profile made and the `files` left."""
    modules = [(PROFILE / name).as_uri() for name in ("index.ts", "derive.ts")]
    result = subprocess.run(
        ["node", "--input-type=module", "-e", RUNNER, *modules],
        input=json.dumps(steps), cwd=REPO, capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _run(steps: list[list[Any]]) -> tuple[list[Any], list[int]]:
    out = run_profile(steps)
    return out["answers"], out["heard"]


def _derive(results: list[dict[str, Any]]) -> dict[str, Any]:
    return _run([["derive", results]])[0][0]


def _code(name: str) -> str:
    """TypeScript with its comments removed, so a doc comment may quote a line it explains."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]


def room_id(n: int) -> str:
    return f"room_{n:026d}"


def puzzle(n: int, lock_type: str = "code", *, rungs: int = 0, first_hint_s: float | None = None, solved: bool = True,
           nudge: bool = False, asked: bool = False, early: bool = False) -> dict[str, Any]:
    return PuzzleResult(
        puzzle_id=f"pz_{n:026d}", lock_type=lock_type, attempts=1, wrong_attempts=0, rungs_used=rungs,
        time_to_first_hint=None if first_hint_s is None else int(first_hint_s * 1000), solved=solved,
        time_spent_ms=120000, nudge_fired=nudge, hint_requested=asked or early, early_ask=early,
    ).model_dump(mode="json")


def result(n: int, puzzles: list[dict[str, Any]], *, demo: bool = False, elapsed_ms: int = 480000) -> dict[str, Any]:
    return RoomResult(
        room_id=room_id(n), demo=demo, elapsed_ms=elapsed_ms, rungs_used=sum(p["rungs_used"] for p in puzzles),
        wrong_attempts=0, puzzles=puzzles,
    ).model_dump(mode="json")


# Two Puzzles solved after their nudge fired with no Hint request on them, one with an Early ask, one with neither;
# times to first hint of 40, 60 and 100 s and one Puzzle with no hint; two `code` Puzzles that used 1 and 3 Rungs.
FIXTURE = [
    result(1, [puzzle(1, "code", rungs=1, first_hint_s=40, nudge=True), puzzle(2, "find", rungs=1, first_hint_s=60, early=True)]),
    result(2, [puzzle(3, "code", rungs=3, first_hint_s=100, nudge=True), puzzle(4, "order")]),
]


@pytest.fixture
def fresh_json() -> dict[str, Any]:
    """The JSON `Derived.fresh()` serializes to, generated from the server model."""
    return json.loads(Derived.fresh().model_dump_json())


# --- Recording: once per Room, keyed by room_id, the Derived block in the same step -----------------------------------


@needs_node
def test_a_result_is_put_once_keyed_by_room_id_and_the_derived_block_is_recomputed_in_the_same_step():
    first = FIXTURE[0]
    answers, heard = _run([
        ["watch", "dev"], ["derived", "dev"],
        ["put", "dev", first], ["results", "dev"], ["derived", "dev"],
        # A reload of #/done/<session_id> puts the same result again.
        ["put", "dev", first], ["results", "dev"], ["derived", "dev"],
    ])
    assert answers[1] == Derived.fresh().model_dump(mode="json")
    assert answers[3] == [first] and answers[6] == [first]
    assert answers[4] == _derive([first]) and answers[4]["sessions"] == 1
    assert answers[7] == answers[4]
    assert heard == [1, 1]  # the mode indicator hears each record at once


@needs_node
def test_a_later_result_replaces_the_rooms_stored_one_except_a_demo_result_over_a_counted_one():
    counted, demo = result(1, [puzzle(1, rungs=1)]), result(1, [puzzle(1, rungs=3)], demo=True)
    replay = result(1, [puzzle(1, rungs=2)], elapsed_ms=300000)
    answers, heard = _run([
        ["watch", "dev"],
        ["put", "dev", counted], ["put", "dev", demo], ["results", "dev"],  # demo never replaces non-demo
        ["put", "dev", replay], ["results", "dev"],  # a later non-demo result replaces the earlier one
        ["put", "dev", result(2, [puzzle(2)], demo=True)], ["put", "dev", result(2, [puzzle(3)], demo=True)],
        ["put", "dev", result(2, [puzzle(4)])], ["results", "dev"],  # demo over demo, then non-demo over demo
        ["derived", "dev"],
    ])
    assert answers[3] == [counted]
    assert answers[5] == [replay]
    assert answers[9] == [replay, result(2, [puzzle(4)])]
    assert answers[10]["sessions"] == 2
    assert heard == [1, 1, 2, 2, 2]  # the ignored demo result records nothing


SESSION_1, SESSION_2 = (f"sess_01M61TZ74F0FP3X9HHTMXGTP{n}0" for n in (1, 2))


@needs_node
def test_a_completion_is_recorded_once_per_session():
    first, other = FIXTURE[0], result(1, [puzzle(1, rungs=3)])
    answers, heard = _run([
        ["watch", "dev"], ["put", "dev", first, "local", SESSION_1],
        # The same Session's Done page mounted again, even with another result for its Room, records nothing.
        ["put", "dev", first, "local", SESSION_1], ["put", "dev", other, "local", SESSION_1], ["results", "dev"],
    ])
    assert answers[4] == [first] and heard == [1]


@needs_node
def test_reopening_an_older_sessions_done_page_never_overwrites_a_newer_result():
    older, newer = result(1, [puzzle(1, rungs=3)]), result(1, [puzzle(1, rungs=0)], elapsed_ms=200000)
    answers, heard = _run([
        ["watch", "dev"], ["put", "dev", older, "local", SESSION_1], ["put", "dev", newer, "local", SESSION_2],
        ["put", "dev", older, "local", SESSION_1], ["results", "dev"], ["derived", "dev"],
    ])
    assert answers[4] == [newer] and answers[5] == _derive([newer])
    assert heard == [1, 1]  # the reopened older page recorded nothing


@needs_node
def test_a_reopened_done_page_fills_an_empty_room_and_follows_the_session_order_of_this_page_load():
    older, newer = result(1, [puzzle(1, rungs=3)]), result(1, [puzzle(1, rungs=0)], elapsed_ms=200000)
    answers, heard = _run([
        ["watch", "dev"], ["put", "dev", older, "local", SESSION_1, True], ["put", "dev", newer, "local", SESSION_2, True],
        ["put", "dev", older, "local", SESSION_1, True], ["results", "dev"],
    ])
    assert answers[4] == [newer] and heard == [1, 1]


@needs_node
def test_profiles_never_mix():
    answers, _ = _run([["put", "demo", FIXTURE[0]], ["results", "playtest"], ["derived", "playtest"], ["results", "demo"]])
    assert answers[1] == [] and answers[2] == Derived.fresh().model_dump(mode="json") and answers[3] == [FIXTURE[0]]


# --- The Derived block ------------------------------------------------------------------------------------------------


@needs_node
def test_the_fixture_profile_derives_persistence_0_25_a_60_s_median_and_2_rungs_on_code():
    derived = _derive([*FIXTURE, result(3, [puzzle(5, "code", rungs=3, first_hint_s=1, early=True)], demo=True)])
    assert Derived.model_validate(derived)
    assert derived["sessions"] == 2
    assert derived["persistence"] == 0.25  # the A-19 mean of +1, +1, -1 and 0
    assert derived["time_to_first_hint_s"] == 60
    assert derived["mean_rung_per_lock_type"] == {"code": 2.0, "find": 1.0, "order": 0.0}


@needs_node
def test_no_hint_gives_a_null_time_and_no_qualifying_puzzle_gives_persistence_0():
    unhinted = _derive([result(1, [puzzle(1, rungs=0), puzzle(2, "find", solved=False)])])
    assert unhinted["time_to_first_hint_s"] is None and unhinted["persistence"] == 0
    # Solved before any nudge, or asked after a Rung opened: neither counts either way.
    neutral = _derive([result(1, [puzzle(1, rungs=1, first_hint_s=30, nudge=True, asked=True), puzzle(2, nudge=False)])])
    assert neutral["persistence"] == 0
    assert _derive([result(1, [])]) == {"sessions": 1, "persistence": 0, "time_to_first_hint_s": None, "mean_rung_per_lock_type": {}}


@needs_node
def test_any_input_keeps_persistence_within_minus_1_to_1_and_every_lock_type_within_0_to_3():
    rng = random.Random(51)
    profiles = []
    for _ in range(200):
        results = []
        for n in range(rng.randint(0, 4)):
            puzzles = [
                puzzle(rng.randint(1, 10**6), rng.choice(LOCK_TYPES), rungs=rng.randint(0, 3),
                       first_hint_s=rng.choice([None, rng.uniform(0, 900)]), solved=rng.random() < 0.8,
                       nudge=rng.random() < 0.5, asked=rng.random() < 0.3, early=rng.random() < 0.2)
                for _ in range(rng.randint(0, 6))
            ]
            results.append(result(n + 1, puzzles, demo=rng.random() < 0.2))
        profiles.append(results)
    answers, _ = _run([["derive", results] for results in profiles])
    for results, derived in zip(profiles, answers, strict=True):
        Derived.model_validate(derived)  # the server's bounds: 422 outside them
        assert -1 <= derived["persistence"] <= 1
        assert all(0 <= value <= 3 for value in derived["mean_rung_per_lock_type"].values())
        assert derived["sessions"] == sum(not r["demo"] for r in results)


@needs_node
def test_only_the_non_demo_result_counts(fresh_json: dict[str, Any]):
    counted, demo = FIXTURE[0], result(9, [puzzle(9, "order", rungs=3, first_hint_s=5, early=True)], demo=True)
    derived = _derive([counted, demo])
    assert derived["sessions"] == 1 and derived == _derive([counted])
    assert derived != fresh_json


@needs_node
def test_a_profile_of_demo_results_only_gives_the_json_derived_fresh_serializes_to(fresh_json: dict[str, Any]):
    demos = [result(1, FIXTURE[0]["puzzles"], demo=True), result(2, FIXTURE[1]["puzzles"], demo=True)]
    answers, _ = _run([["put", "dev", demos[0]], ["put", "dev", demos[1]], ["derived", "dev"], ["derive", []]])
    assert answers[2] == fresh_json and answers[3] == fresh_json


def test_the_derived_block_is_computed_from_the_generated_types_only():
    derive, profile = (PROFILE / "derive.ts").read_text(), (PROFILE / "index.ts").read_text()
    assert "import type { Derived, PuzzleResult, RoomResult } from '../../types'" in derive
    assert "import type { Derived, Meta, Profile, RoomResult, SessionStart } from '../../types'" in profile
    assert "import type { Profile, RoomResult } from '../../types'" in (PROFILE / "file.ts").read_text()
    for path, text in source_ts().items():
        assert not re.search(r"\b(interface|type)\s+(Derived|RoomResult|PuzzleResult)\b", text), path


# --- The Session start ------------------------------------------------------------------------------------------------


@needs_node
def test_a_local_session_start_is_exactly_room_id_and_derived(fresh_json: dict[str, Any]):
    room = room_id(7)
    answers, _ = _run([
        ["start", room, "dev", "local"],  # a fresh profile sends the fresh block
        ["put", "dev", result(1, FIXTURE[0]["puzzles"], demo=True)], ["start", room, "dev", "local"],
        ["put", "dev", FIXTURE[1]], ["start", room, "dev", "local"], ["derived", "dev"],
    ])
    assert answers[0] == {"room_id": room, "derived": fresh_json}
    assert answers[2] == {"room_id": room, "derived": fresh_json}  # demo results only
    assert answers[4] == {"room_id": room, "derived": answers[5]} and answers[5]["sessions"] == 1


@needs_node
def test_a_hosted_session_start_always_sends_derived_fresh(fresh_json: dict[str, Any]):
    answers, _ = _run([*[["put", "dev", r] for r in FIXTURE], ["start", room_id(7), "dev", "hosted"], ["derived", "dev"]])
    assert answers[2] == {"room_id": room_id(7), "derived": fresh_json} and answers[3]["sessions"] == 2


def test_every_session_start_posts_the_profiles_session_start_body():
    starts = {path: text for path, text in source_ts().items() if "startSession(" in re.sub(r"//[^\n]*", "", text)}
    assert sorted(starts) == ["web/src/api/index.ts", "web/src/build-progress.ts", "web/src/play.ts", "web/src/stored-rooms.ts"]
    calls = {path: re.findall(r"startSession\((.*)\)\n", _code(path.removeprefix("web/src/"))) for path in starts}
    assert calls["web/src/stored-rooms.ts"] == ["await sessionStart(room.room_id, profile, mode)"]
    assert calls["web/src/build-progress.ts"] == ["await sessionStart(roomId, profile, mode)"]
    assert calls["web/src/play.ts"] == ["await sessionStart(session.room_id, currentPlace().profile, frame.mode)"]
    # The mode each start follows is GET /meta's, passed down from the shell.
    shell = _code("shell.ts")
    assert shell.count("mode: meta.mode") == 6 and "mode: content.mode" in shell
    # web/profile alone builds the body; no other module names a Derived block or the fresh one.
    for path, text in source_ts().items():
        if path.startswith("web/src/profile/"):
            continue
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)
        assert not re.search(r"\bderived\b|freshDerived|\bderive\(", code), path


def test_no_request_carries_a_room_result_or_anything_else_from_the_profile_but_the_cut_2_profile_file():
    api = _code("api/index.ts")
    # The bodies naming a profile type are the Session start and, cut 2's one exception, the whole profile file that
    # `PUT /profile/<name>` writes to the local server; a RoomResult otherwise only ever arrives, by GET.
    assert re.findall(r"export function (\w+)\([^)]*\b(?:SessionStart|Profile)\b", api) == ["startSession", "putProfile"]
    assert re.findall(r"\bRoomResult\b", api) == ["RoomResult", "RoomResult", "RoomResult"]  # import, return, getJson
    assert "return getJson<RoomResult>(`/sessions/${encodeURIComponent(sessionId)}/result`)" in api
    assert "return getJson<Profile>(`/profile/${encodeURIComponent(name)}`)" in api
    assert "return putJson<Profile>(`/profile/${encodeURIComponent(name)}`, body)" in api
    # web/profile makes no request of its own: only its file backend calls the client, for the profile route alone.
    for name in ("profile/index.ts", "profile/derive.ts", "profile/file.ts"):
        assert not re.search(r"\bfetch\b|XMLHttpRequest|sendBeacon|WebSocket|['`]/api", _code(name)), name
    imports = {name: re.findall(r"^import (?!type )[^\n]*", _code(name), flags=re.MULTILINE)
               for name in ("profile/index.ts", "profile/derive.ts", "profile/file.ts")}
    assert imports == {
        "profile/index.ts": ["import { derive, freshDerived } from './derive.ts'", "import { type FileStorage, fileStorage } from './file.ts'"],
        "profile/derive.ts": [],
        "profile/file.ts": ["import { getProfile, putProfile, RequestFailed } from '../api/index.ts'", "import { derive } from './derive.ts'"],
    }
    for path in source_ts():
        if path not in ("web/src/profile/file.ts", "web/src/api/index.ts"):
            assert not re.search(r"\b(getProfile|putProfile)\b", _code(path.removeprefix("web/src/"))), path


# --- The only writer --------------------------------------------------------------------------------------------------


def test_web_profile_is_the_only_writer_and_others_read_through_its_exports():
    users = {}
    for path, text in source_ts().items():
        if path.startswith("web/src/profile/"):
            continue
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)
        assert "profile/derive.ts" not in code, path
        imported = re.search(r"import \{ ([^}]*) \} from '\./profile/index\.ts'", code)
        if imported:
            users[path] = sorted(imported.group(1).split(", "))
    assert users == {
        "web/src/build-progress.ts": ["sessionStart"],
        "web/src/capture.ts": ["CUT_2", "FileNotSaved", "openProfileFile", "saveProfileFile"],
        "web/src/completion.ts": ["CUT_2", "profileFile", "profileTemporary", "putResult", "saveProfileFile"],
        "web/src/play.ts": ["sessionStart"],
        "web/src/shell.ts": ["getResults", "watchResults"],
        "web/src/stored-rooms.ts": ["sessionStart"],
    }


def test_the_completion_screen_records_the_returned_result_once_and_nothing_while_it_fails():
    load = _function(_code("completion.ts"), "load")
    failed, returned = load.split("} catch (error) {", 1)[1].split("\n    }\n", 1)
    assert "putResult" not in failed and "retry = setTimeout(() => void load(), RESULT_RETRY_MS)" in failed
    assert returned.count("putResult(") == 1 and "const recorded = putResult(profile, result, mode, session.id, !endedOnPlay(session.id))" in returned
    assert returned.index("if (!mounted) return") < returned.index("putResult(") < returned.index("show(result)")


def test_leaving_the_room_records_nothing():
    for name in ("leave-room.ts", "components/leave-room-confirmation.ts", "play.ts"):
        assert not re.search(r"putResult|getResult\b|/result", _code(name)), name


def test_no_surface_offers_a_profile_viewer_export_or_delete_control_beyond_cut_2s_open_and_save():
    profile_lines = {key for key, value in _strings().items() if "profile" in value.lower()}
    assert profile_lines == {"modeProfile", "privacyLine", "openProfileFile", "saveProfileFile", "profileFileLine", "profileFileRefused",
                             "profileNotSaved", "profileNameRefused", "profileNameRefusedBody", "useDevProfile"}
    # Cut 2's "Open profile file" and "Save profile file" are the only profile controls, in their component and the
    # web/profile exports behind them; nothing anywhere views, exports, deletes, clears or resets the profile.
    cut_2 = {"web/src/components/profile-file.ts", "web/src/profile/index.ts", "web/src/capture.ts", "web/src/completion.ts",
             "web/src/strings.ts"}
    for path, text in {**source_ts(), "web/index.html": (REPO / "web/index.html").read_text()}.items():
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)
        assert not re.search(r"(export|delete|clear|reset|view)\w*\W{0,3}(the\W)?(player\W)?profile", code, re.IGNORECASE), path
        if path not in cut_2:
            assert not re.search(r"(open|save)\w*\W{0,3}(the\W)?(player\W)?profile", code, re.IGNORECASE), path
    exports = re.findall(r"^export (?:async )?(?:function|interface) (\w+)", (PROFILE / "index.ts").read_text(), re.MULTILINE)
    assert exports == ["ProfileStorage", "memoryStorage", "getResults", "getDerived", "profileTemporary", "putResult",
                       "openProfileFile", "saveProfileFile", "profileFile", "watchResults", "sessionStart"]
    assert "export { FileNotSaved } from './file.ts'" in (PROFILE / "index.ts").read_text()


def test_the_storage_interface_is_get_results_and_put_result_with_an_in_memory_backend():
    profile = _code("profile/index.ts")
    interface = profile.split("export interface ProfileStorage {", 1)[1].split("\n}", 1)[0]
    assert [line.strip() for line in interface.strip().splitlines()] == [
        "getResults(): Promise<RoomResult[]>", "putResult(result: RoomResult): Promise<void>"]
    # Cut 2 keeps the Room results in the page behind the same interface until the player opens the file; without it a
    # browser opens the profile's IndexedDB database (5.2), and memory stands where there is no IndexedDB, as under
    # Node here, or where it fails.
    assert "const file = CUT_2 ? fileStorage(name) : null" in profile
    assert "const storage = CUT_2 ? memoryStorage() : browserStorage(name)" in profile
    assert "return typeof indexedDB === 'undefined' ? memoryStorage() : indexedDbStorage(name)" in profile
    assert "export interface FileStorage {" in _code("profile/file.ts")
    assert "results.set(result.room_id, result)" in _function(profile, "memoryStorage")


# --- The mode indicator -----------------------------------------------------------------------------------------------


def test_the_mode_indicator_counts_the_profiles_room_results_and_follows_each_record():
    bar = _code("components/top-bar.ts")
    text = _function(bar, "modeIndicatorText")
    assert "if (meta.mode === 'hosted') return strings.modeHosted" in text
    assert "const rooms = played === 1 ? strings.oneRoomPlayed : fill(strings.roomsPlayed, { k: played })" in text
    assert "[strings.modeLocal, cache, fill(strings.modeProfile, { name: meta.profile }), rooms].join(strings.modeSeparator)" in text
    assert "mode.textContent = modeIndicatorText(meta, count)" in bar
    shell = _code("shell.ts")
    render = shell.split("async function render(): Promise<void> {", 1)[1].split("\n  }\n", 1)[0]
    assert "const played = (await getResults(place.profile)).length" in render
    assert render.index("const played") < render.index("if (mine !== generation) return\n    const banner")
    assert "const bar = topBar(meta, played)" in render
    assert "const unwatch = watchResults(place.profile, (results) => bar.showPlayed(results.length))" in render
    assert "unwatch()" in render
    # Still plain text: never focusable, never a control, never a Disclosure.
    assert not re.search(r"tabIndex|addEventListener|button|disclosure", bar)


def test_the_mode_indicator_reads_the_experience_lines():
    strings = _strings()
    local = strings["modeSeparator"].join(
        [strings["modeLocal"], strings["cacheOff"], strings["modeProfile"].format(name="demo"), strings["oneRoomPlayed"]])
    assert local == "Local mode · Cache off · profile demo · 1 room played"
    assert strings["roomsPlayed"].format(k=0) == "0 rooms played" and strings["roomsPlayed"].format(k=3) == "3 rooms played"
    assert strings["modeHosted"] == "Hosted mode"
