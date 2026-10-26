"""Story 7.1: the hosted stores on the `keyframe-jobs`, `keyframe-sessions` and `keyframe-ledger` Dicts and the `keyframe-data` Volume (AD-7, AD-9, AR-12, AR-32).

No test reaches Modal: the handles are plain dicts, a temporary directory
and a stub Volume that records `commit` and `reload`, and refuses a
`reload` while any file under the mount is open, as Modal's "volume busy" does.
"""

import ast
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Self

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from src.api.app import room_routes, session_routes
from src.api.errors import ApiError, handle_api_error, handle_validation_error
from src.domain.ledger import LedgerEntry, running_total_usd
from src.domain.schema import Derived, Event, OpeningLineEvent, Profile, Room
from src.domain.session import SessionStateMachine
from src.infra import modal as modal_module
from src.infra.clocks import SessionClock
from src.infra.modal import (
    CACHE_DIR,
    EPOCH_KEY,
    JOBS_DICT,
    LEDGER_DICT,
    MOUNT,
    SESSIONS_DICT,
    VOLUME,
    VOLUME_LOCK,
    DictJobStore,
    DictLedgerStore,
    DictSessionStore,
    HostedStores,
    ModalHandles,
    VolumeArtifactStore,
    VolumeCache,
    VolumeFiles,
    hosted_stores,
)
from src.pipeline.ports import (
    ROOM_FILE,
    ArtifactStore,
    Cache,
    JobStore,
    LedgerStore,
    SessionStore,
    photo_key,
    room_key,
)
from src.providers.spend import SpendLedger
from src.providers.verbatim import VerbatimPhraser
from tests.api.test_app import store_room
from tests.api.test_sessions import Ticker, click, code
from tests.infra.test_local import (
    JOB_A,
    JOB_B,
    SESSION_A,
    SESSION_B,
    _events,
    _job_state,
)

# --- Doubles -------------------------------------------------------------------


class RecordingDict(dict):
    """A plain dict standing in for a `modal.Dict` that logs every item write."""

    def __init__(self) -> None:
        super().__init__()
        self.writes: list[tuple[Any, Any]] = []

    def __setitem__(self, key: Any, value: Any) -> None:
        self.writes.append((key, value))
        super().__setitem__(key, value)


class OpenFiles:
    """Every file under `root` opened through `io.open` (which `Path.read_bytes` and `write_bytes` use) until it is closed."""

    def __init__(self, root: Path, log: list[str]) -> None:
        self.root = root.resolve()
        self.log = log
        self.open: set[object] = set()
        self.closed_without_lock: list[str] = []
        self._real = io.open

    def __call__(self, file: Any, *args: Any, **kwargs: Any) -> Any:
        handle = self._real(file, *args, **kwargs)
        if not isinstance(file, (str, Path)) or not Path(file).resolve().is_relative_to(self.root):
            return handle
        return _Tracked(handle, self, Path(file).resolve().relative_to(self.root).as_posix())


class _Tracked:
    def __init__(self, handle: Any, files: OpenFiles, rel: str) -> None:
        self.handle, self.files, self.rel = handle, files, rel
        files.open.add(self)
        files.log.append(f"open {rel}")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if not VOLUME_LOCK.locked():
            self.files.closed_without_lock.append(self.rel)
        self.handle.close()
        self.files.open.discard(self)
        self.files.log.append(f"close {self.rel}")

    def __getattr__(self, name: str) -> Any:
        return getattr(self.handle, name)


class StubVolume:
    """`commit` and `reload` recorded in one log with the file opens; `reload` fails while a file is open."""

    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.files: OpenFiles | None = None

    def commit(self) -> None:
        self.log.append("commit")

    def reload(self) -> None:
        if self.files is not None and self.files.open:
            raise RuntimeError("volume busy")
        self.log.append("reload")


@pytest.fixture
def log() -> list[str]:
    return []


@pytest.fixture
def volume(log: list[str]) -> StubVolume:
    return StubVolume(log)


@pytest.fixture
def handles(tmp_path: Path, volume: StubVolume) -> ModalHandles:
    return ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=volume, root=tmp_path / "data")


@pytest.fixture
def stores(handles: ModalHandles) -> HostedStores:
    return hosted_stores(handles)


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch, handles: ModalHandles, volume: StubVolume, log: list[str]) -> OpenFiles:
    files = OpenFiles(handles.root, log)
    volume.files = files
    monkeypatch.setattr(io, "open", files)
    return files


# --- Construction over injected handles ---------------------------------------


def test_the_hosted_names_are_the_ad9_names():
    assert (JOBS_DICT, SESSIONS_DICT, LEDGER_DICT, VOLUME, MOUNT) == (
        "keyframe-jobs", "keyframe-sessions", "keyframe-ledger", "keyframe-data", Path("/data"),
    )
    assert ModalHandles(jobs={}, sessions={}, ledger={}, volume=StubVolume([])).root == Path("/data")


def test_each_store_sits_on_its_own_dict_and_the_artifacts_and_cache_share_one_volume_adapter(handles, stores):
    assert isinstance(stores.jobs, DictJobStore) and stores.jobs.jobs is handles.jobs
    assert isinstance(stores.sessions, DictSessionStore) and stores.sessions.sessions is handles.sessions
    assert isinstance(stores.ledger, DictLedgerStore) and stores.ledger.ledger is handles.ledger
    assert isinstance(stores.artifacts, VolumeArtifactStore) and isinstance(stores.cache, VolumeCache)
    assert stores.artifacts.files is stores.cache.files
    assert stores.artifacts.files.volume is handles.volume and stores.artifacts.files.root == handles.root.resolve()
    ports: list[tuple[object, type]] = [
        (stores.jobs, JobStore), (stores.sessions, SessionStore), (stores.ledger, LedgerStore),
        (stores.artifacts, ArtifactStore), (stores.cache, Cache),
    ]
    for adapter, port in ports:
        missing = {name for name in vars(port) if not name.startswith("_")} - set(dir(adapter))
        assert not missing, f"{type(adapter).__name__} lacks {missing}"


def test_constructing_the_stores_touches_no_dict_and_no_volume_and_the_module_never_imports_modal(handles, log, tmp_path):
    hosted_stores(handles)
    assert log == [] and not handles.root.exists()
    assert all(d == {} and d.writes == [] for d in (handles.jobs, handles.sessions, handles.ledger))
    tree = ast.parse(Path(modal_module.__file__).read_text())
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {(node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert "modal" not in imported


# --- The Volume: commit after every write, reload before every read, one lock ---


def test_every_write_ends_with_commit_and_every_read_begins_with_reload(stores, opened, log, four_lock_room):
    room = four_lock_room.model_dump_json().encode()
    stores.artifacts.put(room_key(four_lock_room.id), room)
    stores.cache.put("abc", {"text": "hi"})
    assert stores.artifacts.read(room_key(four_lock_room.id)) == room
    assert stores.cache.get("abc") == {"text": "hi"}
    assert stores.cache.get("missing") is None
    assert stores.artifacts.list_rooms() == [four_lock_room]
    rel = f"rooms/demo/{four_lock_room.id}/{ROOM_FILE}"
    assert log == [
        f"open {rel}", f"close {rel}", "commit",
        f"open {CACHE_DIR}/abc.json", f"close {CACHE_DIR}/abc.json", "commit",
        "reload", f"open {rel}", f"close {rel}",
        "reload", f"open {CACHE_DIR}/abc.json", f"close {CACHE_DIR}/abc.json",
        "reload",
        "reload", f"open {rel}", f"close {rel}",
    ]
    assert opened.closed_without_lock == [] and not opened.open


def test_concurrent_reads_and_writes_never_reload_while_a_file_is_open(stores, opened, log, four_lock_room):
    stores.artifacts.put(room_key(four_lock_room.id), four_lock_room.model_dump_json().encode())

    def work(n: int) -> None:
        for i in range(15):
            stores.cache.put(f"k{n}-{i}", {"n": n, "i": i})
            assert stores.cache.get(f"k{n}-{i}") == {"n": n, "i": i}
            stores.artifacts.put(photo_key(four_lock_room.id, n), bytes([n]) * 4096)
            assert stores.artifacts.read(photo_key(four_lock_room.id, n)) == bytes([n]) * 4096
            assert stores.artifacts.list_rooms() == [four_lock_room]

    with ThreadPoolExecutor(8) as pool:
        for future in [pool.submit(work, n) for n in range(8)]:
            future.result()
    assert log.count("reload") == 8 * 15 * 3 and log.count("commit") == 1 + 8 * 15 * 2
    assert opened.closed_without_lock == [] and not opened.open


def test_every_volume_files_instance_in_the_process_shares_the_one_lock(tmp_path):
    held: list[bool] = []

    class Probe:
        def commit(self) -> None:
            held.append(VOLUME_LOCK.locked())

        def reload(self) -> None:
            held.append(VOLUME_LOCK.locked())

    first, second = VolumeFiles(Probe(), tmp_path), VolumeFiles(Probe(), tmp_path)
    first.write("a", b"1")
    assert second.read("a") == b"1" and second.read_glob("*") == [b"1"]
    assert held == [True, True, True]
    assert not [v for v in (*vars(first).values(), *vars(second).values()) if isinstance(v, type(VOLUME_LOCK))]


# --- Rooms under /data/rooms/demo/<room_id>/ ------------------------------------


def test_rooms_and_photos_live_under_rooms_demo_and_round_trip_through_a_new_store(handles, stores, four_lock_room):
    store_room(stores.artifacts, four_lock_room)
    folder = handles.root / "rooms" / "demo" / four_lock_room.id
    assert Room.model_validate_json((folder / ROOM_FILE).read_bytes()) == four_lock_room
    assert sorted(p.name for p in (folder / "photos").iterdir()) == [f"{i}.jpg" for i in range(len(four_lock_room.photos))]
    assert all(p.is_relative_to(handles.root / "rooms" / "demo") for p in handles.root.rglob("*") if p.is_file())
    again = hosted_stores(handles).artifacts
    assert Room.model_validate_json(again.read(room_key(four_lock_room.id))) == four_lock_room
    assert again.read(photo_key(four_lock_room.id, 2)) == Path(four_lock_room.photos[2].downscaled_path).read_bytes()


def test_list_rooms_returns_every_demo_room_newest_first_and_nothing_outside_the_demo_partition(handles, stores, four_lock_room, code_and_find_room):
    assert stores.artifacts.list_rooms() == []
    older = four_lock_room.model_copy(update={"created": four_lock_room.created.replace(year=2025)})
    store_room(stores.artifacts, older)
    store_room(stores.artifacts, code_and_find_room)
    elsewhere = handles.root / "rooms" / "judge" / "room_x" / ROOM_FILE
    elsewhere.parent.mkdir(parents=True)
    elsewhere.write_bytes(four_lock_room.model_copy(update={"id": "room_" + "9" * 26}).model_dump_json().encode())
    stores.cache.put("k", {"v": 1})
    assert stores.artifacts.list_rooms() == [code_and_find_room, older]


@pytest.mark.parametrize("key", ["../x", "../judge/room_x/room.json", "a/../../x", "/etc/passwd", "", "."])
def test_a_key_outside_rooms_demo_is_refused_and_nothing_is_written_or_committed(handles, stores, log, key):
    with pytest.raises(ValueError, match="outside rooms/demo/"):
        stores.artifacts.put(key, b"x")
    with pytest.raises(ValueError, match="outside rooms/demo/"):
        stores.artifacts.read(key)
    assert log == [] and not handles.root.exists()


def test_reading_a_missing_artifact_raises_key_error_after_a_reload(stores, log):
    with pytest.raises(KeyError):
        stores.artifacts.read(room_key("room_missing"))
    assert log == ["reload"]


# --- The ledger: one Dict key per call_ ULID, summed on read --------------------


def test_two_spend_ledgers_over_one_dict_keep_every_entry_under_its_own_call_id(handles):
    web, runner = SpendLedger(DictLedgerStore(handles.ledger), cap_usd=100), SpendLedger(DictLedgerStore(handles.ledger), cap_usd=100)
    a = web.guard("vision")
    b = runner.guard("sam")
    runner.settle(b, 0.005)
    web.settle(a, 0.04)
    c = runner.guard("riddler")

    store = DictLedgerStore(handles.ledger)
    entries = store.entries()
    assert set(handles.ledger) == {a, b, c} == {entry.call_id for entry in entries}
    assert all(handles.ledger[entry.call_id] == entry.model_dump(mode="json") for entry in entries)
    assert running_total_usd(entries) == pytest.approx(0.04 + 0.005 + 0.03)
    assert web.running_total_usd() == runner.running_total_usd() == pytest.approx(0.075)
    by_key: dict[str, list[str]] = {}
    for key, value in handles.ledger.writes:
        by_key.setdefault(key, []).append(value["status"])
    assert by_key == {a: ["reserved", "settled"], b: ["reserved", "settled"], c: ["reserved"]}


def test_concurrent_appends_from_two_ledgers_lose_no_entry(handles):
    ledgers = [SpendLedger(DictLedgerStore(handles.ledger), cap_usd=1_000) for _ in range(2)]

    def calls(ledger: SpendLedger) -> list[str]:
        ids = []
        for _ in range(40):
            call_id = ledger.guard("sam")
            ledger.settle(call_id, 0.0025)
            ids.append(call_id)
        return ids

    with ThreadPoolExecutor(2) as pool:
        ids = [call_id for future in [pool.submit(calls, ledger) for ledger in ledgers] for call_id in future.result()]
    entries = DictLedgerStore(handles.ledger).entries()
    assert len(set(ids)) == 80 and {entry.call_id for entry in entries} == set(ids)
    assert all(entry.status == "settled" for entry in entries)
    assert running_total_usd(entries) == pytest.approx(80 * 0.0025)


def test_entries_follow_the_epoch_marker_and_the_store_keeps_no_state_or_lock_of_its_own(handles):
    store = DictLedgerStore(handles.ledger)
    before = LedgerEntry(call_id="call_01ARZ3NDEKTSV4RRFFQ69G5FAV", kind="vision", status="settled", usd=0.03)
    store.append(before)
    assert store.epoch() is None and store.entries() == [before]
    store.start_epoch("2026-11-05")
    after = LedgerEntry(call_id="call_01BX5ZZKBKACTAV9WEVGEMMVRZ", kind="sam", status="reserved", usd=0.0025)
    store.append(after)
    assert handles.ledger[EPOCH_KEY] == "2026-11-05"
    assert store.entries() == [after.model_copy(update={"epoch": "2026-11-05"})]
    assert vars(store) == {"ledger": handles.ledger}


# --- Sessions and jobs on their Dicts ----------------------------------------------


def _play(room: Room) -> list[Event]:
    """The welcome, then the clicks and codes that open every lock of the code-and-find room."""
    bodies = [click("key"), code("clock_code", "nope"), code("clock_code", "415"), click("lantern"), code("door_code", "7342")]
    adapter = TypeAdapter(Event)
    welcome = OpeningLineEvent(type="opening_line", kind="welcome", text="Welcome.", t_ms=0)
    return [welcome, *(adapter.validate_python({**body, "t_ms": 10_000 * (n + 1)}) for n, body in enumerate(bodies))]


def test_a_session_replays_in_append_order_to_the_live_state(handles, code_and_find_room):
    store = DictSessionStore(handles.sessions)
    machine = SessionStateMachine(code_and_find_room)
    live = machine.replay(SESSION_A, [])
    for event in _play(code_and_find_room):
        store.append(SESSION_A, event)
        live = machine.apply(live, event)
    replayed = DictSessionStore(handles.sessions).read_all(SESSION_A)
    assert replayed == _play(code_and_find_room)
    assert machine.replay(SESSION_A, replayed) == live and live.locks_open
    assert json.loads(json.dumps(handles.sessions[SESSION_A])) == [e.model_dump(mode="json") for e in replayed]


def test_session_ids_are_listed_and_deleted_one_at_a_time(handles):
    store = DictSessionStore(handles.sessions)
    for event in _events():
        store.append(SESSION_A, event)
    store.append(SESSION_B, _events()[0])
    assert store.list_ids() == [SESSION_A, SESSION_B]
    store.delete(SESSION_A)
    assert store.list_ids() == [SESSION_B] and store.read_all(SESSION_B) == _events()[:1]
    with pytest.raises(KeyError):
        store.read_all(SESSION_A)
    with pytest.raises(KeyError):
        store.delete(SESSION_A)
    assert vars(store) == {"sessions": handles.sessions}


def test_a_job_reads_back_unchanged_and_the_dict_holds_only_its_in_flight_state(handles):
    first = DictJobStore(handles.jobs)
    first.put(_job_state(JOB_A))
    first.put(_job_state(JOB_B))
    handles.jobs[f"call:{JOB_A}"] = "fc-1"
    second = DictJobStore(handles.jobs)
    assert second.read(JOB_A) == _job_state(JOB_A) and second.list_ids() == [JOB_A, JOB_B]
    assert handles.jobs[JOB_A] == _job_state(JOB_A).model_dump(mode="json")
    done = _job_state(JOB_A).model_copy(update={"status": "done", "stage": None})
    second.put(done)
    assert first.read(JOB_A) == done
    with pytest.raises(KeyError):
        first.read("job_01CX5ZZKBKACTAV9WEVGEMMVRZ")
    assert vars(first) == {"jobs": handles.jobs}


# --- No Derived block or profile field anywhere the adapters wrote ----------------------


SENTINEL_DERIVED = Derived(sessions=86421, persistence=-0.73125, time_to_first_hint_s=6543.21875, mean_rung_per_lock_type={"code": 2.71875})
SENTINELS = ("86421", "-0.73125", "6543.21875", "2.71875")
PROFILE_FIELDS = {*Profile.model_fields, *Derived.model_fields, "profile", "profile_name", "profile_id"}


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {str(k) for k in value} | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _never_spawned(task: Any) -> None:
    raise AssertionError("a hosted session start is never greeted")


def test_a_hosted_session_writes_no_derived_value_or_profile_field_to_any_dict_or_volume_file(handles, stores, code_and_find_room):
    store_room(stores.artifacts, code_and_find_room)
    app = FastAPI()
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    ticker = Ticker()
    app.include_router(room_routes(stores.artifacts, stores.jobs))
    app.include_router(
        session_routes(
            stores.artifacts,
            stores.sessions,
            ticker,
            SessionClock(1),
            VerbatimPhraser(),
            _never_spawned,
            demo=False,
            hosted=True,
            disclosure=[],
        )
    )
    client = TestClient(app)

    started = client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": SENTINEL_DERIVED.model_dump(mode="json")})
    assert started.status_code == 200, started.text
    session_id = started.json()["id"]
    for body in (click("key"), code("clock_code", "415"), click("lantern"), code("door_code", "7342")):
        ticker.advance(10_000)
        assert client.post(f"/api/sessions/{session_id}/events", json=body).status_code == 200
    result = client.get(f"/api/sessions/{session_id}/result")
    assert result.status_code == 200 and all(p["solved"] for p in result.json()["puzzles"])

    assert list(handles.sessions) == [session_id]
    written = [json.dumps(value) for d in (handles.jobs, handles.sessions, handles.ledger) for value in d.values()]
    written += [path.read_text() for path in handles.root.rglob("*") if path.is_file() and path.suffix == ".json"]
    for text in written:
        assert all(sentinel not in text for sentinel in SENTINELS)
        assert not (_keys(json.loads(text)) & PROFILE_FIELDS)
    assert "derived" not in json.dumps(handles.sessions[session_id]) and "profile" not in json.dumps(handles.sessions[session_id])
