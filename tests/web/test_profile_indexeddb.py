"""FR-20, FR-22, AR-11, AD-8: the IndexedDB backend of `web/profile`, one database per `?profile=` name.

The profile module runs as it ships in headless Chromium (Node strips its types; the page is served by a request route,
so nothing leaves the machine): the 5.1 behavior tests run there unchanged on IndexedDB in place of the in-memory
backend, and the browser is reloaded and restarted on the same user data to show the results survive both. The
wiring (the database name, who opens it) is checked by reading the TypeScript, as the other web tests do.
"""

import inspect
import json
import re
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

import pytest

from src.domain.schema import Derived
from tests.web import test_player_profile as behavior
from tests.web.design import REPO, WEB_SRC, source_ts
from tests.web.test_player_profile import FIXTURE, PROFILE, puzzle, result, room_id

# Each visit loads the page afresh and runs its steps against a fresh import of web/profile; between visits the page is
# reloaded ("reload") or the browser closed and launched again on the same user data ("restart"). Every visit answers
# its steps in order, what its watchers heard, and every IndexedDB database the origin holds, read directly.
BROWSER = r"""
const { chromium } = require('playwright')
const { mkdtempSync, readFileSync, rmSync } = require('node:fs')
const { stripTypeScriptTypes } = require('node:module')
const { tmpdir } = require('node:os')
const path = require('node:path')

const ORIGIN = 'http://keyframe.test'
const [profileDir] = process.argv.slice(1)
const modules = Object.fromEntries(['index.ts', 'derive.ts'].map((name) => [
  `/profile/${name}`, stripTypeScriptTypes(readFileSync(path.join(profileDir, name), 'utf8')),
]))

async function visit(steps) {
  const profile = await import('/profile/index.ts')
  const derive = await import('/profile/derive.ts')
  const answers = []
  const heard = []
  for (const [call, ...args] of steps) {
    if (call === 'put') answers.push(await profile.putResult(...args) ?? null)
    else if (call === 'results') answers.push(await profile.getResults(...args))
    else if (call === 'derived') answers.push(await profile.getDerived(...args))
    else if (call === 'start') answers.push(await profile.sessionStart(...args))
    else if (call === 'derive') answers.push(derive.derive(...args))
    else if (call === 'watch') answers.push(profile.watchResults(args[0], (results) => heard.push(results.length)) && null)
    else throw new Error(`unknown call ${call}`)
  }
  const request = (step) => new Promise((resolve, reject) => {
    step.onsuccess = () => resolve(step.result)
    step.onerror = () => reject(step.error)
  })
  const databases = {}
  for (const { name, version } of await indexedDB.databases()) {
    const db = await request(indexedDB.open(name))
    const stores = {}
    for (const store of db.objectStoreNames) {
      const read = db.transaction(store).objectStore(store)
      stores[store] = { key: read.keyPath, records: await request(read.getAll()) }
    }
    db.close()
    databases[name] = { version, stores }
  }
  return { answers, heard, databases }
}

async function launch(userData) {
  const context = await chromium.launchPersistentContext(userData)
  await context.route(`${ORIGIN}/**`, (route) => {
    const { pathname } = new URL(route.request().url())
    if (pathname === '/') return route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>profile</title>' })
    if (pathname in modules) return route.fulfill({ contentType: 'text/javascript', body: modules[pathname] })
    return route.fulfill({ status: 404, body: '' })
  })
  const page = context.pages()[0] ?? (await context.newPage())
  page.on('pageerror', (error) => { throw error })
  await page.goto(`${ORIGIN}/`)
  return { context, page }
}

const plan = JSON.parse(readFileSync(0, 'utf8'))
const userData = mkdtempSync(path.join(tmpdir(), 'profile-'))
;(async () => {
  let { context, page } = await launch(userData)
  const visits = []
  try {
    for (const step of plan) {
      if (step === 'reload') await page.reload()
      else if (step === 'restart') {
        await context.close()
        ;({ context, page } = await launch(userData))
      } else visits.push(await page.evaluate(visit, step))
    }
  } finally {
    await context.close()
    rmSync(userData, { recursive: true, force: true })
  }
  process.stdout.write(JSON.stringify(visits))
})()
"""


def _has_playwright() -> bool:
    if shutil.which("node") is None:
        return False
    found = subprocess.run(["node", "-e", "require.resolve('playwright')"], cwd=REPO, capture_output=True, check=False)
    return found.returncode == 0


needs_browser = pytest.mark.skipif(not _has_playwright(), reason="headless Chromium through Playwright runs IndexedDB")

Steps = list[list[Any]]
Visit = dict[str, Any]


def _browse(plan: list[Steps | str]) -> list[Visit]:
    """Runs each visit of `plan` in Chromium, with "reload" and "restart" between them, and answers every visit."""
    out = subprocess.run(
        ["node", "--no-warnings", "-e", BROWSER, str(PROFILE)],
        input=json.dumps(plan), cwd=REPO, capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def _run_on_indexeddb(steps: Steps) -> tuple[list[Any], list[int]]:
    """5.1's runner, on IndexedDB: one visit on a fresh browser profile."""
    (visit,) = _browse([steps])
    named = {args[1] if call == "start" else args[0] for call, *args in steps if call != "derive"}
    assert named <= set(visit["databases"]), "a profile ran without its IndexedDB database"
    return visit["answers"], visit["heard"]


def _records(visit: Visit, name: str) -> list[dict[str, Any]]:
    return visit["databases"][name]["stores"]["results"]["records"]


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


# --- The 5.1 behavior, unchanged, on IndexedDB ------------------------------------------------------------------------

BEHAVIOR: list[Callable[..., None]] = [
    behavior.test_a_result_is_put_once_keyed_by_room_id_and_the_derived_block_is_recomputed_in_the_same_step,
    behavior.test_a_later_result_replaces_the_rooms_stored_one_except_a_demo_result_over_a_counted_one,
    behavior.test_profiles_never_mix,
    behavior.test_the_fixture_profile_derives_persistence_0_25_a_60_s_median_and_2_rungs_on_code,
    behavior.test_no_hint_gives_a_null_time_and_no_qualifying_puzzle_gives_persistence_0,
    behavior.test_any_input_keeps_persistence_within_minus_1_to_1_and_every_lock_type_within_0_to_3,
    behavior.test_only_the_non_demo_result_counts,
    behavior.test_a_profile_of_demo_results_only_gives_the_json_derived_fresh_serializes_to,
    behavior.test_a_local_session_start_is_exactly_room_id_and_derived,
    behavior.test_a_hosted_session_start_always_sends_derived_fresh,
]


@needs_browser
@pytest.mark.parametrize("test", BEHAVIOR, ids=lambda test: test.__name__.removeprefix("test_"))
def test_the_5_1_behavior_tests_pass_unchanged_on_indexeddb(test: Callable[..., None], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(behavior, "_run", _run_on_indexeddb)
    fixtures = {"fresh_json": json.loads(Derived.fresh().model_dump_json())}
    test(**{name: fixtures[name] for name in inspect.signature(test).parameters})


# --- One database per profile name ------------------------------------------------------------------------------------


@needs_browser
def test_the_profile_opens_the_indexeddb_database_of_its_name_one_record_per_room_id():
    first, replay = FIXTURE[0], result(1, [puzzle(1, rungs=2)], elapsed_ms=300000)
    (visit,) = _browse([[["put", "playtest", first], ["put", "playtest", first], ["put", "playtest", replay],
                         ["put", "playtest", FIXTURE[1]], ["derived", "dev"]]])
    assert sorted(visit["databases"]) == ["dev", "playtest"]
    assert visit["databases"]["playtest"]["stores"]["results"]["key"] == "room_id"
    assert _records(visit, "playtest") == [replay, FIXTURE[1]]
    assert _records(visit, "dev") == []  # opening a fresh profile writes nothing


@needs_browser
def test_profiles_never_mix_across_a_reload():
    demo, room = [*FIXTURE, result(3, [puzzle(5)], demo=True)], room_id(7)
    looks = [["results", "{0}"], ["derived", "{0}"], ["start", room, "{0}", "local"]]
    visits = _browse([
        [["put", "demo", r] for r in demo],
        "reload",
        [[call, *(arg.format(name) for arg in args)] for name in ("playtest", "dev", "demo") for call, *args in looks],
    ])
    fresh, answers = Derived.fresh().model_dump(mode="json"), visits[1]["answers"]
    for at in (0, 3):  # playtest, then dev
        assert answers[at:at + 3] == [[], fresh, {"room_id": room, "derived": fresh}]
    assert answers[6] == demo and answers[7]["sessions"] == 2 and answers[8] == {"room_id": room, "derived": answers[7]}
    assert _records(visits[1], "demo") == demo
    assert _records(visits[1], "playtest") == _records(visits[1], "dev") == []


# --- Results survive a reload and a browser restart -------------------------------------------------------------------


@needs_browser
def test_a_recorded_result_and_its_derived_block_survive_a_reload_and_a_browser_restart():
    room, looks = room_id(7), [["results", "demo"], ["derived", "demo"], ["start", room_id(7), "demo", "local"]]
    visits = _browse([
        [["put", "demo", FIXTURE[0]], *looks],
        "reload",
        # The reload of #/done/<session_id> puts the same result again: still one record.
        [*looks, ["put", "demo", FIXTURE[0]], *looks],
        "restart",
        looks,
    ])
    before = visits[0]["answers"][1:]
    assert before[0] == [FIXTURE[0]] and before[1]["sessions"] == 1 and before[2] == {"room_id": room, "derived": before[1]}
    assert visits[1]["answers"][:3] == before and visits[1]["answers"][4:] == before
    assert visits[2]["answers"] == before
    assert all(_records(visit, "demo") == [FIXTURE[0]] for visit in visits)


# --- The wiring -------------------------------------------------------------------------------------------------------


def test_the_database_is_named_by_the_profile_and_opened_only_by_web_profile():
    profile = _code((PROFILE / "index.ts").read_text())
    assert "const storage = typeof indexedDB === 'undefined' ? memoryStorage() : indexedDbStorage(name)" in profile
    assert "indexedDB.open(name, 1)" in profile
    assert "createObjectStore(RESULTS, { keyPath: 'room_id' })" in profile
    assert "store.put(result)" in profile and "store.getAll()" in profile
    assert not re.search(r"store\.(delete|clear)\(|deleteDatabase", profile)  # no delete control (5.4 adds it under cut 2)
    sources = {**source_ts(), "web/index.html": (REPO / "web/index.html").read_text()}
    openers = sorted(path for path, text in sources.items() if re.search(r"indexedDB|IDB\w+", _code(text)))
    assert openers == ["web/src/profile/index.ts"]


def test_the_name_in_use_is_the_one_get_meta_echoes_and_the_mode_indicator_shows():
    shell = _code((WEB_SRC / "shell.ts").read_text())
    # One name per render: the `?profile=` place (default dev) names GET /meta, the stored results and their watcher.
    assert "getMeta(place.profile)" in shell
    assert "const played = (await getResults(place.profile)).length" in shell
    assert "watchResults(place.profile, " in shell
    router = (WEB_SRC / "router.ts").read_text()
    assert "export const DEFAULT_PROFILE = 'dev'" in router
    # The indicator shows the name GET /meta echoes.
    assert "fill(strings.modeProfile, { name: meta.profile })" in (WEB_SRC / "components/top-bar.ts").read_text()
