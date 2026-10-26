"""Hosted-mode adapters over Modal Dicts and the `keyframe-data` Volume (AD-7, AD-9): the Dict `JobStore` and its watchdog, the spawn `JobRunner`, the Dict `SessionStore` and `LedgerStore`, and the Volume `ArtifactStore` and `Cache`.

`hosted_stores(handles)` builds all five over injected handles
(`ModalHandles`): the Dicts `keyframe-jobs`, `keyframe-sessions` and
`keyframe-ledger` and the Volume `keyframe-data` mounted at `/data`. The
module never imports `modal`, so constructing an adapter contacts no Modal
service. Each adapter uses only the surface a plain `dict` shares with
`modal.Dict` (`get`, item assignment, `in`, `pop`, `keys`, `items`), the
conditional `put(key, value, skip_if_exists=True)` the build quota claims
slots with, and the two Volume calls `commit` and `reload`, so the offline
tests pass dicts, a temporary directory and a stub Volume. Nothing is kept
in process memory: every value is read from its Dict or file on each call.

Dict values are plain JSON (`model_dump(mode="json")`), written whole on
every change. `DictJobStore` keeps one key per job id and holds in-flight
job state only; the `done` record is also written beside its Room on the
Volume (`rooms/judge/<room_id>/job.json`) and committed, and a read falls
through Dict then the final records of both partitions, so a finished job,
a seeded Demo room's included, outlives its Dict entry.
`ModalJobRunner.start(job_id)` spawns the stage runner with the job id only
and stores the `FunctionCall` id under its own key `call:<job_id>`; the
runner then owns the job's record. A job store given a `poll` (the web
side's) runs the watchdog on every read of a `queued` or `running` job: it
marks the job `failed`, keeping the stage it reached, once its call has
ended, once a `queued` job has no call key after `ORPHAN_S`, or once a call
state that stays unknown passes `DEADLINE_S`; that mark is the only write
besides the runner's. The runner's own store has no `poll`, so a restarted
runner never fails the job it resumes. The judge build quota (AD-9) is
`BUILD_QUOTA` slot keys `build:1` to `build:20` in the same Dict:
`reserve_build` claims the first free one with
`put(key, job_id, skip_if_exists=True)`, so two claimers never share a
slot and no count is read, changed and written back; with all 20 taken it
raises `BuildQuotaExceeded` and writes nothing. No slot is ever released,
so every accepted Build counts whatever its end status (A-25), and
`builds_left` counts the free slots in the Dict, so a restart keeps the
count; a slot key can still expire after 7 idle days, which only frees a
build. `DictSessionStore` keeps one key per session id holding its
events in append order; `DictLedgerStore` keeps one key per `call_` ULID, so
settling a call replaces its reserved entry under the same key (the only
rewrite), returns every current-epoch entry so the total is summed on read,
and keeps the epoch marker (AD-9) under the reserved key `EPOCH_KEY`. Dict
entries expire after 7 idle days; no retention rule relies on that expiry
(AD-8).

`VolumeFiles` is the one Volume adapter the `ArtifactStore` and the `Cache`
share: every write ends with `Volume.commit()`, every read begins with
`Volume.reload()`, all Volume I/O in the process goes through the one
`VOLUME_LOCK`, and each file is read fully and closed before the lock is
released, so no file is open when `reload()` runs (a `reload()` fails with
"volume busy" while one is). Rooms live in two partitions (AD-9): Demo
rooms at `/data/rooms/demo/<room_id>/`, which only `scripts/seed_rooms.py`
writes, and Judge rooms at `/data/rooms/judge/<room_id>/`. The artifact
store writes every key of the port (`<room_id>/room.json`,
`<room_id>/photos/<i>.jpg`, `<room_id>/originals/<i>.jpg`, ...) under
`rooms/judge/`, reads a key from `rooms/demo/` first and then
`rooms/judge/`, so a Judge room plays by its id, and `list_rooms()` lists
`rooms/demo/` alone, so no Judge room is ever listed. Cache entries live at
`/data/cache/<key>.json`; the stage runner reads and writes them through a
`CacheKeyLog`, and `run_judge_build` writes the keys it saw to
`rooms/judge/<room_id>/cache-keys.json` when the Build ends, whatever its
status, so the purge can find them (AD-8).
"""

from __future__ import annotations

import json
import posixpath
import re
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Protocol

from pydantic import TypeAdapter

from src.domain.ledger import LedgerEntry
from src.domain.schema import ErrorDetail, Event, JobId, JobState, JobStatus, Room, SessionId
from src.pipeline.ports import ROOM_FILE, BuildQuotaExceeded, Cache

JOBS_DICT = "keyframe-jobs"
SESSIONS_DICT = "keyframe-sessions"
LEDGER_DICT = "keyframe-ledger"
VOLUME = "keyframe-data"
MOUNT = Path("/data")
"""The AD-9 names: three Dicts and the Volume, mounted at `/data`."""

ROOMS_DIR = "rooms"
DEMO_PARTITION = "demo"
"""Demo rooms live under `rooms/demo/`: `scripts/seed_rooms.py` writes them and `list_rooms()` lists them."""
JUDGE_PARTITION = "judge"
"""Judge rooms live under `rooms/judge/`: every hosted Build writes there, and nothing lists them."""
CACHE_KEYS_FILE = "cache-keys.json"
"""Every Cache key a Judge build read or wrote, beside its originals at `rooms/judge/<room_id>/cache-keys.json` (AD-8)."""
CACHE_DIR = "cache"
"""Cache entries live under `/data/cache/`, one JSON file per key."""
EPOCH_KEY = "epoch"
"""The reserved `keyframe-ledger` key holding the current epoch (AD-9); never a `call_` id."""
EVENTS = TypeAdapter(list[Event])

JOB_FILE = "job.json"
"""The final job record, beside its Room at `rooms/<partition>/<room_id>/job.json` (AD-7)."""
ORPHAN_S = 60
"""AD-7: a `queued` job with no `call:<job_id>` key this long after it was minted was never spawned."""
DEADLINE_S = 900 + 300
"""AD-7: the runner's 900 s timeout plus margin; past it a call state that stays unknown counts as dead."""
IN_FLIGHT: frozenset[JobStatus] = frozenset({"queued", "running"})
"""The statuses the watchdog checks; every other status is terminal."""
CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
BUILD_QUOTA = 20
"""AD-9: the judge builds the hosted app accepts; the 21st is refused with `BuildQuotaExceeded`."""

type RunnerState = Literal["running", "finished", "timed_out", "crashed", "expired", "unknown"]
"""A spawned call as Modal reports it without waiting: still going, ended (four ways), or not known because the poll failed."""
type Poll = Callable[[str], RunnerState]
"""The state of the `FunctionCall` a `call:<job_id>` key names; the hosted app wraps `FunctionCall.from_id(id).get(timeout=0)`."""
ENDED: frozenset[RunnerState] = frozenset({"finished", "timed_out", "crashed", "expired"})
"""Modal has reported that the call ended, so its runner can no longer write the job."""

VOLUME_LOCK = threading.Lock()
"""Every Volume read and write in this process holds it, so `reload()` never runs while a file is open."""


class DictLike(Protocol):
    """The `modal.Dict` surface the adapters use; a plain `dict` with a `put` satisfies it."""

    def get(self, key: Any, default: Any = None, /) -> Any: ...

    def __setitem__(self, key: Any, value: Any, /) -> None: ...

    def __contains__(self, key: Any, /) -> bool: ...

    def pop(self, key: Any, /) -> Any: ...

    def put(self, key: Any, value: Any, /, *, skip_if_exists: bool = False) -> bool: ...

    def keys(self) -> Iterable[Any]: ...

    def items(self) -> Iterable[tuple[Any, Any]]: ...


class VolumeLike(Protocol):
    """The `modal.Volume` calls the adapters make inside a container that mounts it."""

    def commit(self) -> None: ...

    def reload(self) -> None: ...


@dataclass(frozen=True)
class ModalHandles:
    """The AD-9 handles; Modal's are lazy, so holding them contacts nothing."""

    jobs: DictLike
    """`keyframe-jobs`."""
    sessions: DictLike
    """`keyframe-sessions`."""
    ledger: DictLike
    """`keyframe-ledger`."""
    volume: VolumeLike
    """`keyframe-data`."""
    root: Path = MOUNT
    """The Volume's mount path; tests pass a temporary directory."""


# --- The Volume: one adapter, one lock ---------------------------------------


class VolumeFiles:
    """Files under the Volume's mount: reload before every read, commit after every write, all under `VOLUME_LOCK`."""

    def __init__(self, volume: VolumeLike, root: Path) -> None:
        self.volume = volume
        self.root = root.resolve()

    def _path(self, rel: str) -> Path:
        path = (self.root / rel).resolve()
        if Path(rel).is_absolute() or path == self.root or not path.is_relative_to(self.root):
            raise ValueError(f"volume path {rel!r} resolves outside {self.root}")
        return path

    def write(self, rel: str, data: bytes) -> None:
        """Write the file whole and close it, then commit, so nothing is visible elsewhere before the commit."""
        path = self._path(rel)
        with VOLUME_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.volume.commit()

    def read(self, rel: str, *fallbacks: str) -> bytes:
        """Reload once, then read the first of `rel` and `fallbacks` that exists fully and close it before the lock is released.

        When none exists, `KeyError(rel)` is raised.
        """
        paths = [self._path(name) for name in (rel, *fallbacks)]
        with VOLUME_LOCK:
            self.volume.reload()
            for path in paths:
                try:
                    return path.read_bytes()
                except FileNotFoundError:
                    continue
            raise KeyError(rel)

    def read_glob(self, *patterns: str) -> list[bytes]:
        """Reload once, then read every file matching each pattern under the root fully, in path order per pattern, before the lock is released."""
        with VOLUME_LOCK:
            self.volume.reload()
            return [path.read_bytes() for pattern in patterns for path in sorted(self.root.glob(pattern)) if path.is_file()]


class VolumeArtifactStore:
    """`ArtifactStore` over the two room partitions (AD-9): writes go to `rooms/judge/`, reads try `rooms/demo/` then `rooms/judge/`, and only `rooms/demo/` is listed.

    A key that resolves outside its partition (absolute, empty, or climbing
    out with `..`) is refused with `ValueError`, so no key reaches
    `rooms/demo/` through `put` and no read crosses into another directory.
    """

    def __init__(self, files: VolumeFiles) -> None:
        self.files = files
        self.demo = f"{ROOMS_DIR}/{DEMO_PARTITION}"
        self.judge = f"{ROOMS_DIR}/{JUDGE_PARTITION}"

    @staticmethod
    def _clean(key: str) -> str:
        """The key normalized; one that does not stay inside the partition it is joined to is refused."""
        rel = posixpath.normpath(key)
        if PurePosixPath(key).is_absolute() or rel in (".", "..") or rel.startswith("../"):
            raise ValueError(f"artifact key {key!r} resolves outside its partition under {ROOMS_DIR}/")
        return rel

    def put(self, key: str, data: bytes) -> None:
        """Write under `rooms/judge/`: every hosted Build is a Judge build, and only the seed script writes Demo rooms."""
        self.files.write(f"{self.judge}/{self._clean(key)}", data)

    def read(self, key: str) -> bytes:
        """The key's bytes from the Demo partition, else the Judge partition, after one reload; a key in neither raises `KeyError`."""
        rel = self._clean(key)
        try:
            return self.files.read(f"{self.demo}/{rel}", f"{self.judge}/{rel}")
        except KeyError:
            raise KeyError(key) from None

    def list_rooms(self) -> list[Room]:
        """Every Room under `rooms/demo/<room_id>/`, newest `created` first, and none under `rooms/judge/`; the route maps each to its `RoomSummary`."""
        rooms = [Room.model_validate_json(data) for data in self.files.read_glob(f"{self.demo}/*/{ROOM_FILE}")]
        return sorted(rooms, key=lambda room: room.created, reverse=True)


class VolumeCache:
    """`Cache` over `/data/cache/`, one JSON file per key, through the same Volume adapter as the artifacts."""

    def __init__(self, files: VolumeFiles) -> None:
        self.files = files

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            return json.loads(self.files.read(f"{CACHE_DIR}/{key}.json"))
        except KeyError:
            return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.files.write(f"{CACHE_DIR}/{key}.json", json.dumps(value).encode())


# --- The Dicts ---------------------------------------------------------------


def call_key(job_id: JobId) -> str:
    """The `keyframe-jobs` key holding the job's `FunctionCall` id, apart from the record the runner owns (AD-7)."""
    return f"call:{job_id}"


def slot_key(n: int) -> str:
    """The `keyframe-jobs` key of build quota slot `n`, 1 to `BUILD_QUOTA`; its value is the job that claimed it."""
    return f"build:{n}"


SLOT_KEYS = frozenset(slot_key(n) for n in range(1, BUILD_QUOTA + 1))


def minted_ms(prefixed_id: str) -> int:
    """The Unix milliseconds in a prefixed ULID's first ten characters: when the server minted the id (AD-18)."""
    value = 0
    for char in prefixed_id.partition("_")[2][:10]:
        value = value * 32 + CROCKFORD_BASE32.index(char)
    return value


def wall_ms() -> int:
    """Unix milliseconds now, the clock a job's age is read against."""
    return time.time_ns() // 1_000_000


class DictJobStore:
    """`JobStore` over `keyframe-jobs`, with the `done` record also on the Volume beside its Room (AD-7).

    With a `poll`, every read of a `queued` or `running` job runs the
    watchdog; a job's age is the time since its `job_` ULID was minted,
    read on `now_ms`.
    """

    def __init__(self, jobs: DictLike, files: VolumeFiles, *, poll: Poll | None = None, now_ms: Callable[[], int] = wall_ms) -> None:
        self.jobs = jobs
        self.files = files
        self.poll = poll
        self.now_ms = now_ms

    def put(self, state: JobState) -> None:
        """Write the whole state to the Dict; a `done` record goes to the Volume first, under `rooms/judge/`, and is committed."""
        if state.status == "done" and state.room_id is not None:
            self.files.write(_final_record(state.room_id), state.model_dump_json().encode())
        self.jobs[state.id] = state.model_dump(mode="json")

    def read(self, job_id: JobId) -> JobState:
        """The stored state, after the watchdog when this store has a `poll`; an unknown id raises `KeyError`."""
        state = self.stored(job_id)
        if self.poll is None or state.status not in IN_FLIGHT:
            return state
        return self._watch(state, self.poll)

    def stored(self, job_id: JobId) -> JobState:
        """The Dict entry, else the final record on the Volume, without the watchdog."""
        raw = self.jobs.get(job_id)
        if raw is not None:
            return JobState.model_validate(raw)
        for state in self._final_records():
            if state.id == job_id:
                return state
        raise KeyError(job_id)

    def list_ids(self) -> list[JobId]:
        """Every job id in the Dict or in a final record; any other key the hosted app adds to the Dict is not a `job_` id."""
        keys = self.jobs.keys()  # `modal.Dict` offers `keys()`, not iteration
        ids = {key for key in keys if isinstance(key, str) and key.startswith("job_")}
        return sorted(ids | {state.id for state in self._final_records()})

    def reserve_build(self, job_id: JobId) -> None:
        """Claim the first free slot for `job_id`, one conditional write per slot; with every slot taken raise `BuildQuotaExceeded`, having written nothing."""
        for n in range(1, BUILD_QUOTA + 1):
            if self.jobs.put(slot_key(n), job_id, skip_if_exists=True):
                return
        raise BuildQuotaExceeded(BUILD_QUOTA)

    def builds_left(self) -> int:
        """`BUILD_QUOTA` minus the slots present in the Dict; reads only, so it claims nothing."""
        keys = self.jobs.keys()  # `modal.Dict` offers `keys()`, not iteration
        return BUILD_QUOTA - sum(1 for key in keys if key in SLOT_KEYS)

    def _final_records(self) -> list[JobState]:
        """The final records of both partitions: the seeded Demo rooms' and the Judge builds'."""
        patterns = [f"{ROOMS_DIR}/{partition}/*/{JOB_FILE}" for partition in (DEMO_PARTITION, JUDGE_PARTITION)]
        return [JobState.model_validate_json(data) for data in self.files.read_glob(*patterns)]

    def _watch(self, state: JobState, poll: Poll) -> JobState:
        """Leave a live job as it is; mark one whose runner has ended, or that a backstop has caught, `failed` at the stage it reached."""
        age_s = (self.now_ms() - minted_ms(state.id)) / 1000
        call_id = self.jobs.get(call_key(state.id))
        if call_id is None:  # the spawn is not recorded, yet or ever
            dead = age_s > (ORPHAN_S if state.status == "queued" else DEADLINE_S)
        else:
            runner = poll(call_id)
            dead = runner in ENDED or (runner == "unknown" and age_s > DEADLINE_S)
        if not dead:
            return state
        fresh = self.stored(state.id)  # the runner may have written a terminal record meanwhile
        if fresh.status not in IN_FLIGHT:
            return fresh
        stage = fresh.stage or (fresh.stages[-1].stage if fresh.stages else None)
        failed = fresh.model_copy(update={"status": "failed", "stage": stage})
        self.jobs[state.id] = failed.model_dump(mode="json")
        return failed


def _final_record(room_id: str) -> str:
    """Where a hosted Build's `done` record goes: beside its Room in the Judge partition."""
    return f"{ROOMS_DIR}/{JUDGE_PARTITION}/{room_id}/{JOB_FILE}"


class SpawnedCall(Protocol):
    """What `Function.spawn` returns, as far as the runner reads it."""

    @property
    def object_id(self) -> str: ...


type Spawn = Callable[[JobId], SpawnedCall]
"""`run_build.spawn`: takes the job id only and returns at once."""


class ModalJobRunner:
    """`JobRunner` over `run_build.spawn(job_id)` (AD-7): the spawned runner, not this process, runs the stages."""

    def __init__(self, store: DictJobStore, spawn: Spawn) -> None:
        self.store = store
        self.spawn = spawn

    def start(self, job_id: JobId) -> None:
        """Spawn the runner with the job id and store the call id under `call:<job_id>`; the job stays `queued` until the runner's first stage write.

        A spawn that raises marks the job `failed` at stage `ingest` with
        the error's class name in snake_case (AD-13) and re-raises, so the
        route can answer with the error envelope.
        """
        try:
            call = self.spawn(job_id)
        except Exception as exc:
            code = re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()
            error = ErrorDetail(code=code, message=str(exc), stage="ingest")
            self.store.put(self.store.stored(job_id).model_copy(update={"status": "failed", "stage": "ingest", "error": error}))
            raise
        self.store.jobs[call_key(job_id)] = call.object_id


class DictSessionStore:
    """`SessionStore` over `keyframe-sessions`: one key per session id holding its events in append order."""

    def __init__(self, sessions: DictLike) -> None:
        self.sessions = sessions

    def append(self, session_id: SessionId, event: Event) -> None:
        """Read the log, add the event and write the whole value back (a Dict change needs a put-back)."""
        events = self.sessions.get(session_id) or []
        self.sessions[session_id] = [*events, event.model_dump(mode="json")]

    def read_all(self, session_id: SessionId) -> list[Event]:
        events = self.sessions.get(session_id)
        if events is None:
            raise KeyError(session_id)
        return EVENTS.validate_python(events)

    def list_ids(self) -> list[SessionId]:
        return sorted(self.sessions.keys())

    def delete(self, session_id: SessionId) -> None:
        if session_id not in self.sessions:
            raise KeyError(session_id)
        self.sessions.pop(session_id)


class DictLedgerStore:
    """`LedgerStore` over `keyframe-ledger`: one key per `call_` id, the epoch marker under `EPOCH_KEY`.

    The guard stays per process (AD-6): a web container and a runner
    container each hold their own `SpendLedger` lock over this one Dict,
    so concurrent containers can overshoot the cap by the estimates of the
    calls in flight. No atomic store is built here (AR-32); `max_containers=1`
    on the web function stands in for one.
    """

    def __init__(self, ledger: DictLike) -> None:
        self.ledger = ledger

    def append(self, entry: LedgerEntry) -> None:
        """Store the entry under its `call_` id, stamped with the current epoch; a settled entry replaces its reserved one."""
        self.ledger[entry.call_id] = {**entry.model_dump(mode="json"), "epoch": self.epoch()}

    def entries(self) -> list[LedgerEntry]:
        """The current epoch's entries in `call_` ULID order, which is the order they were minted in."""
        epoch = self.epoch()
        rows = [LedgerEntry.model_validate(value) for key, value in self.ledger.items() if key != EPOCH_KEY]
        return sorted((row for row in rows if row.epoch == epoch), key=lambda row: row.call_id)

    def epoch(self) -> str | None:
        """The date of the last reset; `None` before the first."""
        return self.ledger.get(EPOCH_KEY)

    def start_epoch(self, epoch: str) -> None:
        """Write the epoch marker: every entry appended after it carries `epoch` and the earlier ones stop counting."""
        self.ledger[EPOCH_KEY] = epoch


# --- Construction --------------------------------------------------------------


@dataclass(frozen=True)
class HostedStores:
    """The five hosted adapters; `artifacts` and `cache` share one `VolumeFiles`."""

    jobs: DictJobStore
    sessions: DictSessionStore
    ledger: DictLedgerStore
    artifacts: VolumeArtifactStore
    cache: VolumeCache


def hosted_stores(handles: ModalHandles, *, poll: Poll | None = None) -> HostedStores:
    """Build every hosted adapter over `handles`; nothing here reads or writes a Dict or the Volume.

    The web side passes `poll`, so its job reads run the watchdog; the
    stage runner passes none.
    """
    files = VolumeFiles(handles.volume, handles.root)
    return HostedStores(
        jobs=DictJobStore(handles.jobs, files, poll=poll),
        sessions=DictSessionStore(handles.sessions),
        ledger=DictLedgerStore(handles.ledger),
        artifacts=VolumeArtifactStore(files),
        cache=VolumeCache(files),
    )


# --- The Judge build's cache keys (AD-8) ----------------------------------------


class CacheKeyLog:
    """`Cache` over another that records every key read or written, in first-use order, for a Judge build's `cache-keys.json` (AD-8).

    The stage runner builds one per Build over the Volume cache and hands it
    to the providers; the segment stage's threads share it, so the record is
    kept under its own lock.
    """

    def __init__(self, cache: Cache) -> None:
        self.cache = cache
        self._seen: dict[str, None] = {}
        self._lock = threading.Lock()

    def _note(self, key: str) -> None:
        with self._lock:
            self._seen.setdefault(key, None)

    def get(self, key: str) -> dict[str, Any] | None:
        self._note(key)
        return self.cache.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self._note(key)
        self.cache.put(key, value)

    def keys(self) -> list[str]:
        """Every key read or written so far, each once."""
        with self._lock:
            return list(self._seen)


def cache_keys_key(room_id: str) -> str:
    """The artifact key of a Build's `cache-keys.json`, which the artifact store writes at `rooms/judge/<room_id>/cache-keys.json`."""
    return f"{room_id}/{CACHE_KEYS_FILE}"


def run_judge_build[T](run: Callable[[JobId], T], job_id: JobId, *, stores: HostedStores, keys: CacheKeyLog) -> T:
    """Run a Judge build's remaining stages, then write its `cache-keys.json`, whatever its end status (AD-8).

    `run` is the stage runner's `Build.run` over `stores`, its providers
    reading the Cache through `keys`. When `run` returns or raises, the keys
    it saw join any a restarted runner already listed, and the file is
    written beside the Build's originals and committed.
    """
    room_id = stores.jobs.stored(job_id).room_id
    try:
        return run(job_id)
    finally:
        if room_id is not None:
            try:
                earlier: list[str] = json.loads(stores.artifacts.read(cache_keys_key(room_id)))
            except KeyError:
                earlier = []
            listed = list(dict.fromkeys([*earlier, *keys.keys()]))
            stores.artifacts.put(cache_keys_key(room_id), json.dumps(listed).encode())
