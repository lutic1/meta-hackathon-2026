"""Stories 1.10, 2.5 and 2.11: the disk `ArtifactStore` under `rooms/`, the JSON `JobStore` under `rooms/jobs/` with the in-process `JobRunner`, the JSON `SessionStore` under `rooms/sessions/`, the jsonl `LedgerStore` under a file lock outside `.cache/`, and the disk `Cache` under `.cache/` (AD-7, AD-9)."""

import fcntl
import inspect
import json
import shutil
import threading
import time
from datetime import date
from pathlib import Path

import pytest

from src.domain.ledger import SEED_USD, LedgerEntry, SpendCapExceeded, running_total_usd
from src.domain.schema import (
    ClickEvent,
    CodeInput,
    Event,
    IdleTickEvent,
    JobState,
    LockInputEvent,
    Room,
    StageRecord,
)
from src.infra import local as local_module
from src.infra.clocks import BuildClock
from src.infra.local import (
    CACHE_ROOT,
    EXPORTS_ROOT,
    LEDGER_PATH,
    DiskArtifactStore,
    DiskCache,
    JsonJobStore,
    JsonlLedgerStore,
    JsonSessionStore,
    LedgerExport,
    ThreadJobRunner,
    export_ledger,
    export_path,
)
from src.pipeline.build import STAGES, TERMINAL, Build
from src.pipeline.ports import (
    ROOM_FILE,
    ArtifactStore,
    JobRunner,
    JobStore,
    SessionStore,
)
from src.providers.base import ChatMessage, ChatResponse
from src.providers.cache import GuardedCalls, cache_key
from src.providers.spend import SpendLedger
from tests.fixtures.rooms import IX, PZ
from tests.infra.test_clocks import Ticker
from tests.pipeline.test_build import (
    ARCHITECT_ROW,
    SENT_BACK,
    Doubles,
    RunnerDied,
    StageResult,
)
from tests.pipeline.uploads import make_uploads
from tests.providers.test_cache import Provider
from tests.providers.test_spend import JOB, settled

# --- The artifact store under rooms/ and the session store under rooms/sessions/ ---


SESSION_A = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SESSION_B = "sess_01BX5ZZKBKACTAV9WEVGEMMVRZ"


def _events() -> list[Event]:
    return [
        ClickEvent(type="click", interactable_id=IX["key"], t_ms=1200),
        LockInputEvent(type="lock_input", input=CodeInput(type="code", puzzle_id=PZ["clock_code"], code="415"), t_ms=4800),
        IdleTickEvent(type="idle_tick", t_ms=9900),
    ]


def _store_room(store: DiskArtifactStore, room: Room, partition: str) -> dict[str, bytes]:
    """Put the Room and its photos the way a build would, returning each key's bytes."""
    written = {f"{partition}/{room.id}/{ROOM_FILE}": room.model_dump_json().encode()}
    for index, photo in enumerate(room.photos):
        written[f"{partition}/{room.id}/photos/{index}.jpg"] = Path(photo.downscaled_path).read_bytes()
    for key, data in written.items():
        store.put(key, data)
    return written


def test_the_fixture_room_and_its_photos_round_trip_under_rooms(tmp_path, four_lock_room):
    root = tmp_path / "rooms"
    store: ArtifactStore = DiskArtifactStore(root)
    written = _store_room(store, four_lock_room, "local")
    for key, data in written.items():
        assert store.read(key) == data
        assert (root / key).read_bytes() == data
    assert all(path.is_relative_to(root) for path in tmp_path.rglob("*") if path.is_file())
    assert Room.model_validate_json(store.read(f"local/{four_lock_room.id}/{ROOM_FILE}")) == four_lock_room


def test_list_rooms_returns_the_stored_rooms_newest_first(tmp_path, four_lock_room, code_and_find_room):
    store = DiskArtifactStore(tmp_path / "rooms")
    assert store.list_rooms() == []
    older = four_lock_room.model_copy(update={"created": four_lock_room.created.replace(year=2025)})
    _store_room(store, older, "local")
    _store_room(store, code_and_find_room, "demo")
    store.put("sessions/sess_01ARZ3NDEKTSV4RRFFQ69G5FAV.json", b"[]")
    assert store.list_rooms() == [code_and_find_room, older]


@pytest.mark.parametrize("key", ["../x", "a/../../x", "/etc/passwd", "", "."])
def test_a_key_outside_rooms_is_refused_and_nothing_is_written(tmp_path, key):
    root = tmp_path / "rooms"
    store = DiskArtifactStore(root)
    with pytest.raises(ValueError, match="outside rooms/"):
        store.put(key, b"x")
    with pytest.raises(ValueError, match="outside rooms/"):
        store.read(key)
    assert not (tmp_path / "x").exists() and not root.exists()


def test_a_symlink_that_points_outside_rooms_is_refused(tmp_path):
    root = tmp_path / "rooms"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="outside rooms/"):
        DiskArtifactStore(root).put("escape/x", b"x")


def test_reading_a_missing_key_raises_key_error(tmp_path):
    with pytest.raises(KeyError):
        DiskArtifactStore(tmp_path / "rooms").read("local/missing/room.json")


def test_events_append_in_order_to_two_sessions_under_rooms_sessions(tmp_path):
    directory = tmp_path / "rooms" / "sessions"
    store: SessionStore = JsonSessionStore(directory)
    assert store.list_ids() == []
    a, b = _events(), _events()[:1]
    for event in a:
        store.append(SESSION_A, event)
    for event in b:
        store.append(SESSION_B, event)
    assert store.read_all(SESSION_A) == a and store.read_all(SESSION_B) == b
    assert store.list_ids() == [SESSION_A, SESSION_B]
    assert sorted(p.name for p in directory.iterdir()) == [f"{SESSION_A}.json", f"{SESSION_B}.json"]
    assert json.loads((directory / f"{SESSION_A}.json").read_text()) == [e.model_dump(mode="json") for e in a]


def test_delete_removes_one_session_and_leaves_the_other(tmp_path):
    store = JsonSessionStore(tmp_path / "rooms" / "sessions")
    store.append(SESSION_A, _events()[0])
    store.append(SESSION_B, _events()[0])
    store.delete(SESSION_A)
    assert store.list_ids() == [SESSION_B]
    with pytest.raises(KeyError):
        store.read_all(SESSION_A)
    with pytest.raises(KeyError):
        store.delete(SESSION_A)


def test_a_new_instance_over_the_same_directory_reads_the_same_events(tmp_path):
    directory = tmp_path / "rooms" / "sessions"
    first = JsonSessionStore(directory)
    for event in _events():
        first.append(SESSION_A, event)
    second = JsonSessionStore(directory)
    assert second.read_all(SESSION_A) == _events()
    second.append(SESSION_A, IdleTickEvent(type="idle_tick", t_ms=15000))
    assert first.read_all(SESSION_A)[-1].t_ms == 15000
    assert not [v for v in vars(first).values() if isinstance(v, (list, dict))]


def test_a_session_id_that_is_not_a_file_name_is_refused(tmp_path):
    store = JsonSessionStore(tmp_path / "rooms" / "sessions")
    with pytest.raises(ValueError, match="not a file name"):
        store.append("../x", _events()[0])
    assert not (tmp_path / "rooms" / "x.json").exists()


# --- The JSON job store under rooms/jobs/ and the in-process runner ---------------


JOB_A = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
JOB_B = "job_01BX5ZZKBKACTAV9WEVGEMMVRZ"


def _job_state(job_id: str = JOB_A) -> JobState:
    """A job left running at segment with everything the state can carry after architect."""
    return JobState(
        id=job_id,
        status="running",
        stage="segment",
        room_id="room_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        stages=[StageRecord(stage="ingest", duration_ms=0, count=6), StageRecord(stage="architect", duration_ms=4_000, count=9, model="muse-spark-1.3")],
        regen_max=2,
        sent_back=[SENT_BACK],
        calls=[ARCHITECT_ROW],
        build_time_ms=4_000,
    )


def _build(jobs: JobStore, root: Path, doubles: Doubles, ticker: Ticker) -> Build:
    return Build(jobs=jobs, artifacts=DiskArtifactStore(root), clock=BuildClock(monotonic_ns=ticker), stages=doubles.stages(), regen_max=2)


def _wait_terminal(jobs: JobStore, job_id: str, timeout_s: float = 5.0) -> JobState:
    """The job's state once the store holds it terminal: the only way a test learns that a background stage finished."""
    deadline = time.monotonic() + timeout_s
    while (state := jobs.read(job_id)).status not in TERMINAL:
        assert time.monotonic() < deadline, f"{job_id} still {state.status} at {state.stage}"
        time.sleep(0.01)
    return state


def test_job_state_written_by_one_store_is_read_back_identically_by_a_second(tmp_path):
    directory = tmp_path / "rooms" / "jobs"
    first: JobStore = JsonJobStore(directory)
    assert first.list_ids() == []
    state = _job_state()
    first.put(state)

    second: JobStore = JsonJobStore(directory)
    assert second.read(JOB_A) == state and second.list_ids() == [JOB_A]
    assert [p.name for p in directory.iterdir()] == [f"{JOB_A}.json"]
    assert json.loads((directory / f"{JOB_A}.json").read_text()) == state.model_dump(mode="json")
    assert not [v for v in vars(first).values() if isinstance(v, (list, dict, JobState))]
    assert not [v for v in vars(second).values() if isinstance(v, (list, dict, JobState))]


def test_put_replaces_the_stored_state_and_list_ids_returns_every_job(tmp_path):
    directory = tmp_path / "rooms" / "jobs"
    store = JsonJobStore(directory)
    store.put(_job_state(JOB_A))
    store.put(_job_state(JOB_B))
    done = _job_state(JOB_A).model_copy(update={"status": "done", "stage": None})
    store.put(done)
    assert store.read(JOB_A) == done and store.read(JOB_B) == _job_state(JOB_B)
    assert store.list_ids() == [JOB_A, JOB_B] == JsonJobStore(directory).list_ids()
    assert sorted(p.name for p in directory.iterdir()) == [f"{JOB_A}.json", f"{JOB_B}.json"]


def test_reading_an_unknown_job_raises_key_error_and_a_bad_id_is_refused(tmp_path):
    store = JsonJobStore(tmp_path / "rooms" / "jobs")
    with pytest.raises(KeyError):
        store.read(JOB_A)
    with pytest.raises(ValueError, match="not a file name"):
        store.read("../x")
    assert not (tmp_path / "rooms").exists()


def test_start_returns_before_a_held_stage_completes_and_the_stage_runs_in_the_background(tmp_path):
    jobs = JsonJobStore(tmp_path / "rooms" / "jobs")
    doubles = Doubles(Ticker())
    entered, release = threading.Event(), threading.Event()
    doubles.hooks["architect"] = lambda _state: (entered.set(), release.wait(5))
    build = _build(jobs, tmp_path / "rooms", doubles, doubles.ticker)
    runner: JobRunner = ThreadJobRunner(build.run)
    queued = build.submit(make_uploads(6))

    runner.start(queued.id)

    assert entered.wait(5) and doubles.calls == ["architect"]
    held = jobs.read(queued.id)
    assert (held.status, held.stage) == ("running", "architect")
    thread = next(t for t in threading.enumerate() if t.name == f"build-{queued.id}")
    assert thread.is_alive() and thread.daemon and thread is not threading.current_thread()
    release.set()
    done = _wait_terminal(jobs, queued.id)
    assert done.status == "done" and doubles.calls == list(STAGES[1:])
    thread.join(5)
    assert not thread.is_alive()


def test_a_restarted_process_resumes_at_segment_and_never_runs_architect_again(tmp_path):
    directory = tmp_path / "rooms" / "jobs"
    first_doubles = Doubles(Ticker())
    first_doubles.results["architect"] = StageResult(count=9, model="muse-spark-1.3", calls=[ARCHITECT_ROW])
    first_doubles.raises["segment"] = RunnerDied()
    first = _build(JsonJobStore(directory), tmp_path / "rooms", first_doubles, first_doubles.ticker)
    queued = first.submit(make_uploads(6))
    with pytest.raises(RunnerDied):
        first.run(queued.id)
    persisted = (directory / f"{queued.id}.json").read_bytes()
    assert first_doubles.calls == ["architect", "segment"]

    jobs = JsonJobStore(directory)
    before = jobs.read(queued.id)
    assert before == JobState.model_validate_json(persisted)
    assert (before.status, before.stage) == ("running", "segment")
    assert [record.stage for record in before.stages] == ["ingest", "architect"] and before.calls == [ARCHITECT_ROW]
    second_doubles = Doubles(Ticker())
    second = _build(jobs, tmp_path / "rooms", second_doubles, second_doubles.ticker)
    ThreadJobRunner(second.run).start(queued.id)

    done = _wait_terminal(jobs, queued.id)
    assert second_doubles.calls == ["segment", "author", "validate", "dryrun", "scene"]
    assert "architect" not in second_doubles.calls and done.calls == [ARCHITECT_ROW]
    assert second_doubles.seen["segment"] == before
    assert [record.stage for record in done.stages] == list(STAGES) and done.status == "done"
    assert JsonJobStore(directory).read(queued.id) == done


def test_the_runner_keeps_no_job_state_and_runs_each_start_on_its_own_thread(tmp_path):
    started: list[tuple[str, str]] = []
    runner = ThreadJobRunner(lambda job_id: started.append((job_id, threading.current_thread().name)))
    runner.start(JOB_A)
    runner.start(JOB_B)
    for thread in [t for t in threading.enumerate() if t.name.startswith("build-job_")]:
        thread.join(5)
    assert sorted(started) == [(JOB_A, f"build-{JOB_A}"), (JOB_B, f"build-{JOB_B}")]
    assert not [v for v in vars(runner).values() if isinstance(v, (list, dict, set, JobState))]
    assert "threading.Thread" in inspect.getsource(ThreadJobRunner)


# --- The ledger file and the disk cache --------------------------------------------


REPLY = ChatResponse(text='{"ok": true}', model="muse-spark-1.3", usage={"prompt_tokens": 10, "completion_tokens": 5}, raw={"id": "x"})
KEY = cache_key("muse-spark-1.3", messages=[ChatMessage(role="user", content="Write four puzzles.")])


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A repository root: the ledger at `spend/ledger.jsonl`, the cache under `.cache/`."""
    return tmp_path


def ledger_store(root: Path) -> JsonlLedgerStore:
    return JsonlLedgerStore(root / LEDGER_PATH)


def lines(root: Path) -> list[dict]:
    return [json.loads(line) for line in (root / LEDGER_PATH).read_text().splitlines()]


# --- The ledger file: one line per entry, under a file lock, outside .cache/ ----


def test_entries_are_appended_one_per_line_to_spend_ledger_jsonl_outside_the_cache(root):
    store = ledger_store(root)
    first, second = settled(0.5), settled(0.25, "sam")
    store.append(first)
    store.append(second)

    assert (root / "spend" / "ledger.jsonl").is_file()
    assert LEDGER_PATH == Path("spend/ledger.jsonl") and CACHE_ROOT == Path(".cache")
    assert not LEDGER_PATH.is_relative_to(CACHE_ROOT) and not (root / ".cache").exists()
    assert lines(root) == [first.model_dump(), second.model_dump()]
    assert store.entries() == [first, second]
    assert (root / LEDGER_PATH).read_text().endswith("\n")


def test_a_missing_file_reads_as_no_entries(root):
    assert ledger_store(root).entries() == []


def test_two_concurrent_writers_leave_every_entry_intact_one_per_line(root):
    writers = [ledger_store(root) for _ in range(2)]
    batches = [[settled(0.001 * i, "trickster") for i in range(200)] for _ in writers]
    start = threading.Barrier(len(writers))

    def write(store: JsonlLedgerStore, batch: list[LedgerEntry]) -> None:
        start.wait()
        for entry in batch:
            store.append(entry)

    threads = [threading.Thread(target=write, args=(w, b)) for w, b in zip(writers, batches)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    rows = lines(root)
    assert len(rows) == 400
    assert {row["call_id"] for row in rows} == {e.call_id for batch in batches for e in batch}
    assert sorted(ledger_store(root).entries(), key=lambda e: e.call_id) == sorted((e for b in batches for e in b), key=lambda e: e.call_id)


def test_an_append_waits_for_the_file_lock_held_by_another_writer(root):
    store = ledger_store(root)
    store.append(settled(0.1))
    appended = threading.Event()

    with (root / LEDGER_PATH).open("a") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX)
        thread = threading.Thread(target=lambda: (store.append(settled(0.2)), appended.set()))
        thread.start()
        assert not appended.wait(0.2)
        assert len(lines(root)) == 1
        fcntl.flock(held.fileno(), fcntl.LOCK_UN)
    thread.join(timeout=5)
    assert appended.is_set() and len(lines(root)) == 2
    assert "fcntl.flock" in inspect.getsource(local_module)


def test_append_stores_under_the_current_epoch_and_entries_returns_only_that_epoch(root):
    store = ledger_store(root)
    before = settled(1.0)
    store.append(before)
    with (root / LEDGER_PATH).open("a") as file:
        file.write(json.dumps({"epoch": "2026-11-05"}) + "\n")
    after = settled(0.5)
    store.append(after)

    stamped = LedgerEntry.model_validate({**after.model_dump(), "epoch": "2026-11-05"})
    assert lines(root)[-1] == stamped.model_dump() and lines(root)[0]["epoch"] is None
    assert store.entries() == [stamped]
    assert SpendLedger(store, cap_usd=60).running_total_usd() == pytest.approx(0.5)


def test_start_epoch_writes_the_marker_so_the_total_and_the_guard_count_only_the_new_epoch(root):
    store = ledger_store(root)
    store.append(settled(59.0))
    assert store.epoch() is None

    store.start_epoch("2026-11-05")

    assert lines(root)[-1] == {"epoch": "2026-11-05"} and store.epoch() == "2026-11-05"
    assert store.entries() == []
    guard = SpendLedger(store, cap_usd=5)
    assert guard.running_total_usd() == 0
    guard.settle(guard.guard("vision"), 0.5)  # 59 before the reset would have refused it
    assert [e.epoch for e in store.entries()] == ["2026-11-05", "2026-11-05"] and guard.running_total_usd() == pytest.approx(0.5)


# --- The dated export -------------------------------------------------------------


def test_export_ledger_writes_the_current_epoch_entries_and_the_totals_to_the_dated_file(root):
    store = ledger_store(root)
    first, second = settled(0.5), settled(0.25, "sam")
    store.append(first)
    store.append(second)

    export = export_ledger(store, root / EXPORTS_ROOT, date(2026, 10, 26), ceiling_usd=80)

    path = root / "spend" / "exports" / "ledger-2026-10-26.json"
    assert export_path(EXPORTS_ROOT, date(2026, 10, 26)) == Path("spend/exports/ledger-2026-10-26.json")
    assert path.is_file() and not path.is_relative_to(root / CACHE_ROOT)
    assert [entry.name for entry in path.parent.iterdir()] == [path.name], "the export is moved into place, no temp file left"
    assert LedgerExport.model_validate_json(path.read_text()) == export
    assert export.entries == [first, second] and export.epoch is None and export.date == "2026-10-26"
    assert (export.local_total_usd, export.hosted_total_usd, export.total_usd, export.ceiling_usd) == (0.75, 0.0, 0.75, 80.0)
    assert export.total_usd == pytest.approx(running_total_usd(store.entries()))


def test_a_reader_never_sees_a_partial_export_while_it_is_rewritten(root):
    store = ledger_store(root)
    for _ in range(50):
        store.append(settled(0.01))
    path = export_path(root / EXPORTS_ROOT, date(2026, 10, 26))
    export_ledger(store, root / EXPORTS_ROOT, date(2026, 10, 26), ceiling_usd=80)
    stop = threading.Event()

    def rewrite() -> None:
        while not stop.is_set():
            export_ledger(store, root / EXPORTS_ROOT, date(2026, 10, 26), ceiling_usd=80)

    writer = threading.Thread(target=rewrite)
    writer.start()
    try:
        for _ in range(300):
            assert len(LedgerExport.model_validate_json(path.read_bytes()).entries) == 50
    finally:
        stop.set()
        writer.join()


def test_an_empty_ledger_exports_a_valid_file_with_a_total_of_0(root):
    export = export_ledger(ledger_store(root), root / EXPORTS_ROOT, date(2026, 10, 26), ceiling_usd=80)
    written = json.loads((root / EXPORTS_ROOT / "ledger-2026-10-26.json").read_text())
    assert written["entries"] == [] and written["total_usd"] == 0.0 and written["local_total_usd"] == 0.0
    assert export.total_usd == 0 and not (root / LEDGER_PATH).read_text()


def test_the_export_after_a_reset_holds_only_the_new_epoch_and_the_earlier_export_is_untouched(root):
    store = ledger_store(root)
    store.append(settled(30.0))
    earlier = export_ledger(store, root / EXPORTS_ROOT, date(2026, 11, 4), ceiling_usd=80)
    earlier_bytes = (root / EXPORTS_ROOT / "ledger-2026-11-04.json").read_bytes()
    store.start_epoch("2026-11-05")
    store.append(settled(0.5))

    later = export_ledger(store, root / EXPORTS_ROOT, date(2026, 11, 5), ceiling_usd=25)

    assert [e.epoch for e in later.entries] == ["2026-11-05"] and later.epoch == "2026-11-05"
    assert (later.total_usd, later.ceiling_usd) == (0.5, 25.0)
    assert earlier.total_usd == 30.0 and [e.epoch for e in earlier.entries] == [None]
    assert (root / EXPORTS_ROOT / "ledger-2026-11-04.json").read_bytes() == earlier_bytes


# --- The total survives a restart ---------------------------------------------


def test_a_new_spend_ledger_over_the_same_file_sees_the_total_and_enforces_the_cap_against_it(root):
    ledger = SpendLedger(ledger_store(root), cap_usd=1.0)
    ledger.settle(ledger.guard("vision", job_id=JOB, stage="ingest"), 0.5)
    ledger.settle(ledger.guard("riddler", job_id=JOB, stage="author"), 0.45)
    pending = ledger.guard("trickster")
    total = ledger.running_total_usd()
    assert total == pytest.approx(0.95 + SEED_USD["trickster"])

    restarted = SpendLedger(ledger_store(root), cap_usd=1.0)
    assert restarted.running_total_usd() == pytest.approx(total)
    assert running_total_usd(restarted._store.entries()) == pytest.approx(total)
    with pytest.raises(SpendCapExceeded) as info:
        restarted.guard("riddler", job_id=JOB, stage="author")  # 0.96 + 0.45 > 1.0
    assert info.value.running_total_usd == pytest.approx(total)
    assert restarted.settle(pending, 0.004).usd == 0.004
    assert restarted.running_total_usd() == pytest.approx(0.954)
    assert len(lines(root)) == 6


# --- The disk cache -------------------------------------------------------------


def test_a_put_response_is_returned_by_a_new_cache_over_the_same_root(root):
    cache = DiskCache(root / CACHE_ROOT)
    assert cache.get(KEY) is None
    value = {"text": REPLY.text, "model": REPLY.model, "usage": REPLY.usage, "raw": REPLY.raw}
    cache.put(KEY, value)

    assert DiskCache(root / CACHE_ROOT).get(KEY) == value
    assert sorted(p.name for p in (root / ".cache").iterdir()) == [f"{KEY}.json"]
    assert not (root / "spend").exists()


def test_a_put_replaces_the_previous_value_under_the_key(root):
    cache = DiskCache(root / CACHE_ROOT)
    cache.put(KEY, {"text": "first"})
    cache.put(KEY, {"text": "second"})
    assert cache.get(KEY) == {"text": "second"}
    assert [p.name for p in (root / ".cache").iterdir()] == [f"{KEY}.json"]


def test_deleting_the_cache_leaves_the_ledger_and_exports_unchanged_and_the_next_call_is_priced_again(root):
    export = root / "spend" / "exports" / "ledger-2026-10-26.json"
    export.parent.mkdir(parents=True)
    export.write_text('{"total_usd": 0.0}')
    ledger = SpendLedger(ledger_store(root), cap_usd=60)
    calls = GuardedCalls(DiskCache(root / CACHE_ROOT), ledger, host="api.meta.ai")
    provider = Provider((REPLY, 0.0125), (REPLY, 0.0125))

    billed = calls.chat(KEY, "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")[1]
    hit = calls.chat(KEY, "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")[1]
    assert (billed.cached, hit.cached, provider.calls) == (False, True, 1)
    ledger_bytes = (root / LEDGER_PATH).read_bytes()
    total = ledger.running_total_usd()

    shutil.rmtree(root / CACHE_ROOT)

    assert (root / LEDGER_PATH).read_bytes() == ledger_bytes
    assert export.read_text() == '{"total_usd": 0.0}'
    assert ledger.running_total_usd() == pytest.approx(total) == pytest.approx(0.0125)
    response, again = calls.chat(KEY, "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")
    assert response == REPLY and (again.cached, again.spend_usd, provider.calls) == (False, 0.0125, 2)
    assert ledger.running_total_usd() == pytest.approx(0.025)
    assert [e["status"] for e in lines(root)] == ["reserved", "settled", "reserved", "settled"]
    assert DiskCache(root / CACHE_ROOT).get(KEY) is not None
