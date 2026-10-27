"""Hosted-mode adapters over Modal Dicts and the `keyframe-data` Volume (AD-7, AD-9): the Dict `JobStore` and its watchdog, the spawn `JobRunner`, the Dict `AttemptStore`, `SessionStore` and `LedgerStore`, and the Volume `ArtifactStore` and `Cache`.

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
build. `DictAttemptStore` keeps the access attempts of each client (AD-9)
in the same Dict, one key per client holding the Unix milliseconds of its
recent attempts, so the per-IP limit survives a restart and no count lives
in process memory. `DictSessionStore` keeps one key per session id holding its
events in append order, and its header under that id plus `HEADER_SUFFIX`; `DictLedgerStore` keeps one key per `call_` ULID, so
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
`rooms/demo/` alone, so no Judge room is ever listed; `is_demo_room(room_id)`
is true only for a Room under `rooms/demo/`, `is_judge_room(room_id)` only
for one under `rooms/judge/`, and `deleted_room(id_)` reads
the deletion records under `rooms/deleted/` for one naming that room id or
job id, so a route answers a deleted Judge room with 410. Cache entries live at
`/data/cache/<key>.json`. `run_build` runs a Judge build
through `run_judge_build`, with a `CacheKeyLog` as the providers' Cache: the
log adds each key to `rooms/judge/<room_id>/cache-keys.json`, committed,
before the Build first reads or writes its entry, so no entry a runner
stored is ever unlisted, even when the runner is killed, and the purge
finds them all (AD-8).

Retention (AD-8, AD-9) is two hosted-only functions that Local mode never
calls. `delete_judge_room(handles, room_id, today=...)` deletes a Judge
room together: its Sessions (`SessionStore.list_ids` and `read_all`, then
`delete`), every Cache entry its `cache-keys.json` lists, and its folder
under `rooms/judge/` (Room, photos, originals), committing the Volume; only
then does it write the ids-only `DeletionRecord` to
`rooms/deleted/<room_id>.json`, and after it remove the folder's final
record and pop the job keys in `keyframe-jobs`. It refuses a Demo room id,
and a Room whose job may still be running, deleting nothing. Every step
skips what an earlier, failed attempt already removed, and whatever names
the job (the final record, the Dict entry, or the deletion record) outlives
the step that needs it, so an error before the record raises with none
written, and a rerun after any error completes the deletion. A Session
belongs to a Room when one of its events names one of the Room's
interactables or puzzles; a Session holding only its opening line, idle
ticks and hints with no puzzle names none and is left to the sweep, which
takes it within `SESSION_TTL_MS` of its last event.
`sweep_sessions(handles, now=...)` deletes every Session whose last event
is more than `SESSION_TTL_MS` old, the last event's wall time being the
Session's `sess_` ULID mint time plus that event's `t_ms` (unscaled
milliseconds since the start, AD-10).

The hosted app hands `run_build.spawn` and the watchdog's call poll in on
`ModalHandles` (`spawn`, `poll`), so this module still never imports
`modal`. `export_hosted_ledger(handles, day)`, which the daily
`ledger_export` Cron runs, writes the current epoch's ledger entries, one
JSON line each, to `/data/spend/hosted-<date>.jsonl` and commits (AD-9).
"""

from __future__ import annotations

import json
import logging
import posixpath
import re
import shutil
import threading
import time
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Protocol

from pydantic import ConfigDict, TypeAdapter, ValidationError

from src.domain.ledger import LedgerEntry
from src.domain.schema import (
    ClickEvent,
    ErrorDetail,
    Event,
    HintRequestEvent,
    JobId,
    JobState,
    JobStatus,
    LockInputEvent,
    Model,
    Room,
    RoomId,
    RungChangeEvent,
    SessionId,
    TricksterCardEvent,
    UseOnInput,
)
from src.domain.session import SessionHeader
from src.pipeline.ports import (
    ROOM_FILE,
    ArtifactStore,
    BuildQuotaExceeded,
    Cache,
    room_key,
)

log = logging.getLogger("keyframe.hosted")

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
DELETED_PARTITION = "deleted"
"""Ids-only deletion records live under `rooms/deleted/<room_id>.json` (AD-9); nothing else is written there."""
CACHE_KEYS_FILE = "cache-keys.json"
"""Every Cache key a Judge build read or wrote, beside its originals at `rooms/judge/<room_id>/cache-keys.json` (AD-8)."""
CACHE_DIR = "cache"
"""Cache entries live under `/data/cache/`, one JSON file per key."""
SPEND_DIR = "spend"
"""The daily hosted ledger snapshots live under `/data/spend/` (AD-9)."""
EPOCH_KEY = "epoch"
"""The reserved `keyframe-ledger` key holding the current epoch (AD-9); never a `call_` id."""
EVENTS = TypeAdapter(list[Event])
CACHE_KEYS = TypeAdapter(list[str])
ROOM_ID = TypeAdapter(RoomId)

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
HEADER_SUFFIX = ":header"
"""A session's `SessionHeader` sits in `keyframe-sessions` under its id plus this suffix; `list_ids` never lists it."""
SESSION_TTL_MS = 24 * 60 * 60 * 1000
"""AD-8: a hosted Session is deleted once its last event is more than 24 h old."""

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
    spawn: Spawn | None = None
    """`run_build.spawn`, which the hosted `JobRunner` starts each Build with; the runner and the Cron functions never read it."""
    poll: Poll | None = None
    """The web side's watchdog poll of a spawned call; the runner ignores it, since `run_hosted_build` builds its stores without `poll`."""


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

    def exists(self, rel: str) -> bool:
        """Reload, then whether a file or folder is at `rel`."""
        path = self._path(rel)
        with VOLUME_LOCK:
            self.volume.reload()
            return path.exists()

    def remove(self, *rels: str) -> None:
        """Delete each file or folder (with everything under it) that is still there, then commit once; one already gone is skipped."""
        paths = [self._path(rel) for rel in rels]
        with VOLUME_LOCK:
            for path in paths:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink(missing_ok=True)
            self.volume.commit()

    def names(self, rel: str) -> list[str]:
        """Reload, then the sorted names of the entries in the folder at `rel`; none when it is absent."""
        path = self._path(rel)
        with VOLUME_LOCK:
            self.volume.reload()
            return sorted(child.name for child in path.iterdir()) if path.is_dir() else []

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

    def is_demo_room(self, room_id: str) -> bool:
        """Whether the Room is stored under `rooms/demo/<room_id>/`, after one reload; a Judge room or an unknown id is not."""
        return self.files.exists(f"{self.demo}/{self._clean(room_key(room_id))}")

    def is_judge_room(self, room_id: str) -> bool:
        """Whether the Room is stored under `rooms/judge/<room_id>/`, after one reload; a Demo room or an unknown id is not."""
        return self.files.exists(f"{self.judge}/{self._clean(room_key(room_id))}")

    def deleted_room(self, id_: str) -> RoomId | None:
        """The Room id of the deletion record under `rooms/deleted/` that names `id_` as its room id or job id, after one reload; `None` when none does."""
        records = map(DeletionRecord.model_validate_json, self.files.read_glob(f"{ROOMS_DIR}/{DELETED_PARTITION}/*.json"))
        return next((record.room_id for record in records if id_ in (record.room_id, record.job_id)), None)


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
        keys = list(self.jobs.keys())  # a snapshot: `modal.Dict` offers `keys()`, not iteration, and writes may land mid-read
        ids = {key for key in keys if isinstance(key, str) and key.startswith("job_")}
        return sorted(ids | {state.id for state in self._final_records()})

    def job_of(self, room_id: str) -> JobId | None:
        """The id of the job that built `room_id`, from the Dict or a final record; `None` when neither names the Room."""
        keys = list(self.jobs.keys())  # a snapshot: `modal.Dict` offers `keys()`, not iteration, and writes may land mid-read
        values = [self.jobs.get(key) for key in keys if isinstance(key, str) and key.startswith("job_")]
        in_flight = [JobState.model_validate(value) for value in values if value is not None]  # a job may finish between keys() and get()
        return next((state.id for state in [*in_flight, *self._final_records()] if state.room_id == room_id), None)

    def reserve_build(self, job_id: JobId) -> None:
        """Claim the first free slot for `job_id`, one conditional write per slot; with every slot taken raise `BuildQuotaExceeded`, having written nothing."""
        for n in range(1, BUILD_QUOTA + 1):
            if self.jobs.put(slot_key(n), job_id, skip_if_exists=True):
                return
        raise BuildQuotaExceeded(BUILD_QUOTA)

    def builds_left(self) -> int:
        """`BUILD_QUOTA` minus the slots present in the Dict; reads only, so it claims nothing."""
        keys = list(self.jobs.keys())  # a snapshot: `modal.Dict` offers `keys()`, not iteration, and writes may land mid-read
        return BUILD_QUOTA - sum(1 for key in keys if key in SLOT_KEYS)

    def _final_records(self) -> list[JobState]:
        """The final records of both partitions: the seeded Demo rooms' and the Judge builds'.

        A record that does not parse is logged and skipped, so one corrupt
        file on the Volume never hides every other job.
        """
        patterns = [f"{ROOMS_DIR}/{partition}/*/{JOB_FILE}" for partition in (DEMO_PARTITION, JUDGE_PARTITION)]
        records: list[JobState] = []
        for data in self.files.read_glob(*patterns):
            try:
                records.append(JobState.model_validate_json(data))
            except ValidationError as exc:
                log.warning(json.dumps({"event": "job_unreadable", "error": f"{exc.error_count()} errors"}))
        return records

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


class DictAttemptStore:
    """`AttemptStore` over `keyframe-jobs`: the API's per-client key (`attempts:<ip>`) holds that client's recent attempt times."""

    def __init__(self, jobs: DictLike) -> None:
        self.jobs = jobs

    def read(self, key: str) -> list[int]:
        return list(self.jobs.get(key) or [])

    def write(self, key: str, times: list[int]) -> None:
        self.jobs[key] = list(times)


class DictSessionStore:
    """`SessionStore` over `keyframe-sessions`: one key per session id holding its events in append order, its header beside it."""

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
        keys = self.sessions.keys()
        return sorted(key for key in keys if not key.endswith(HEADER_SUFFIX))

    def delete(self, session_id: SessionId) -> None:
        if session_id not in self.sessions:
            raise KeyError(session_id)
        self.sessions.pop(session_id)
        if session_id + HEADER_SUFFIX in self.sessions:
            self.sessions.pop(session_id + HEADER_SUFFIX)

    def put_header(self, session_id: SessionId, header: SessionHeader) -> None:
        self.sessions[session_id + HEADER_SUFFIX] = header.model_dump(mode="json")

    def read_header(self, session_id: SessionId) -> SessionHeader:
        header = self.sessions.get(session_id + HEADER_SUFFIX)
        if header is None:
            raise KeyError(session_id)
        return SessionHeader.model_validate(header)


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
        items = list(self.ledger.items())  # a snapshot: another container's append may land mid-read
        rows = [LedgerEntry.model_validate(value) for key, value in items if key != EPOCH_KEY]
        return sorted((row for row in rows if row.epoch == epoch), key=lambda row: row.call_id)

    def epoch(self) -> str | None:
        """The date of the last reset; `None` before the first."""
        return self.ledger.get(EPOCH_KEY)

    def start_epoch(self, epoch: str) -> None:
        """Write the epoch marker: every entry appended after it carries `epoch` and the earlier ones stop counting."""
        self.ledger[EPOCH_KEY] = epoch


# --- The daily ledger snapshot (AD-9) --------------------------------------------


def snapshot_path(day: date) -> str:
    """The Volume path of the hosted ledger snapshot taken on `day`: `spend/hosted-<date>.jsonl`."""
    return f"{SPEND_DIR}/hosted-{day.isoformat()}.jsonl"


def export_hosted_ledger(handles: ModalHandles, day: date) -> list[LedgerEntry]:
    """Write every current-epoch `keyframe-ledger` entry as one JSON line to `spend/hosted-<day>.jsonl`, commit, and return the entries.

    The entries are the hosted `LedgerStore`'s own, so the snapshot sums to
    the total it returns; an empty ledger writes an empty file. The file is
    written whole and replaces any earlier snapshot of the same day.
    """
    entries = DictLedgerStore(handles.ledger).entries()
    lines = "".join(entry.model_dump_json() + "\n" for entry in entries)
    VolumeFiles(handles.volume, handles.root).write(snapshot_path(day), lines.encode())
    return entries


# --- Construction --------------------------------------------------------------


@dataclass(frozen=True)
class HostedStores:
    """The six hosted adapters; `jobs` and `attempts` share the `keyframe-jobs` Dict, `artifacts` and `cache` one `VolumeFiles`."""

    jobs: DictJobStore
    attempts: DictAttemptStore
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
        attempts=DictAttemptStore(handles.jobs),
        sessions=DictSessionStore(handles.sessions),
        ledger=DictLedgerStore(handles.ledger),
        artifacts=VolumeArtifactStore(files),
        cache=VolumeCache(files),
    )


# --- The Judge build's cache keys (AD-8) ----------------------------------------


class CacheKeyLog:
    """`Cache` over another that lists every key read or written, in first-use order, in a Judge build's `cache-keys.json` (AD-8).

    The record is write-ahead: a key's first `get` or `put` adds it to
    `rooms/judge/<room_id>/cache-keys.json` through the artifact store,
    which commits, before the call reaches the Cache, so a runner killed
    at any point leaves no Cache entry unlisted. The keys an earlier runner
    of the same Build listed are kept. The segment stage's threads share
    one log, so the record is kept under its own lock.
    """

    def __init__(self, cache: Cache, artifacts: ArtifactStore, room_id: str) -> None:
        self.cache = cache
        self.artifacts = artifacts
        self.key = cache_keys_key(room_id)
        self._listed: dict[str, None] | None = None
        self._lock = threading.Lock()

    def _load(self) -> dict[str, None]:
        """The keys already listed, read once; a missing or unreadable file lists none."""
        if self._listed is None:
            try:
                earlier = CACHE_KEYS.validate_json(self.artifacts.read(self.key))
            except (KeyError, ValueError):
                earlier = []
            self._listed = dict.fromkeys(earlier)
        return self._listed

    def _note(self, key: str) -> None:
        with self._lock:
            listed = self._load()
            if key not in listed:
                listed[key] = None
                self._write(listed)

    def _write(self, listed: dict[str, None]) -> None:
        self.artifacts.put(self.key, json.dumps(list(listed)).encode())

    def get(self, key: str) -> dict[str, Any] | None:
        self._note(key)
        return self.cache.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self._note(key)
        self.cache.put(key, value)

    def write(self) -> None:
        """Write the listing whole, so the file exists even for a Build that makes no Cache call."""
        with self._lock:
            self._write(self._load())

    def keys(self) -> list[str]:
        """Every key listed so far, an earlier runner's included, each once."""
        with self._lock:
            return list(self._load())


def cache_keys_key(room_id: str) -> str:
    """The artifact key of a Build's `cache-keys.json`, which the artifact store writes at `rooms/judge/<room_id>/cache-keys.json`."""
    return f"{room_id}/{CACHE_KEYS_FILE}"


def run_judge_build[T](run: Callable[[JobId], T], job_id: JobId, *, keys: CacheKeyLog) -> T:
    """Run a Judge build's remaining stages through `keys`, leaving its `cache-keys.json` whatever its end status (AD-8).

    `run` is the stage runner's `Build.run` over the hosted stores, its
    providers reading the Cache through `keys`, which lists each key before
    its entry is touched. The listing is written first, so the file exists,
    committed, before any stage runs, even for a Build that makes no Cache
    call or whose runner is killed.
    """
    keys.write()
    return run(job_id)


# --- Retention: the Judge room deletion and the Session sweep (AD-8, AD-9) ------


class DeletionRecord(Model):
    """What a deleted Judge room leaves at `rooms/deleted/<room_id>.json` (AD-9): ids and the date only, no label, Clue, name or photo.

    `job_id` is `None` only when no job record names the Room any more.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    room_id: RoomId
    job_id: JobId | None
    deleted_on: date


def deletion_record_path(room_id: str) -> str:
    """Where the Volume keeps a deleted Judge room's ids-only record."""
    return f"{ROOMS_DIR}/{DELETED_PARTITION}/{room_id}.json"


def delete_judge_room(handles: ModalHandles, room_id: str, *, today: date) -> DeletionRecord:
    """Delete a Judge room with its Sessions, listed Cache entries and job keys, commit, and return its ids-only record (AD-8, AD-9).

    A Demo room id is refused with `ValueError` before anything is deleted,
    and so is a Room whose job is `queued` or `running` and younger than
    `DEADLINE_S`, since its runner may still write. The Sessions and Cache
    entries go while the Room and `cache-keys.json` remain, then everything
    in the folder but its final record, which still names the job when the
    Dict entry has expired. Only then is the record written, before the
    final record and the job keys go, so a failure before it raises with no
    record written, and one after it leaves the record naming the job. Each
    step skips what an earlier attempt already removed, so a rerun deletes
    what is left: an id that names no Judge folder and no job pops the job
    keys its record names and returns that record, rewritten and committed,
    and raises `KeyError` when it has none. Cache entries not listed in
    `cache-keys.json`, every Demo room's included, are never touched.
    """
    ROOM_ID.validate_python(room_id)
    files = VolumeFiles(handles.volume, handles.root)
    folder = f"{ROOMS_DIR}/{JUDGE_PARTITION}/{room_id}"
    if files.exists(f"{ROOMS_DIR}/{DEMO_PARTITION}/{room_id}"):
        raise ValueError(f"{room_id} is a Demo room; only Judge rooms are deleted")
    jobs = DictJobStore(handles.jobs, files)
    job_id = jobs.job_of(room_id)
    if job_id is None and not files.exists(folder):
        return _finish_deleted(handles.jobs, files, room_id)
    if job_id is not None:
        state = jobs.stored(job_id)
        if state.status in IN_FLIGHT and wall_ms() - minted_ms(job_id) <= DEADLINE_S * 1000:
            raise ValueError(f"{room_id} has a {state.status} job {job_id}; delete it once the job has ended")
    room = _judge_room(files, folder)
    if room is not None:
        _delete_room_sessions(DictSessionStore(handles.sessions), room)
    files.remove(*(f"{CACHE_DIR}/{key}.json" for key in _listed_cache_keys(files, folder)))
    files.remove(*(f"{folder}/{name}" for name in files.names(folder) if name != JOB_FILE))
    record = _stored_record(files, room_id) or DeletionRecord(room_id=room_id, job_id=job_id, deleted_on=today)
    files.write(deletion_record_path(room_id), record.model_dump_json().encode())
    files.remove(folder)
    _pop_job_keys(handles.jobs, record.job_id)
    return record


def _stored_record(files: VolumeFiles, room_id: str) -> DeletionRecord | None:
    """The record a deletion already wrote; `None` when there is none."""
    try:
        return DeletionRecord.model_validate_json(files.read(deletion_record_path(room_id)))
    except KeyError:
        return None


def _finish_deleted(jobs: DictLike, files: VolumeFiles, room_id: str) -> DeletionRecord:
    """Pop the job keys a deleted room's record names, then write and commit that record again in case its first commit failed; `KeyError` when there is none."""
    record = _stored_record(files, room_id)
    if record is None:
        raise KeyError(room_id)
    _pop_job_keys(jobs, record.job_id)
    files.write(deletion_record_path(room_id), record.model_dump_json().encode())
    return record


def _pop_job_keys(jobs: DictLike, job_id: JobId | None) -> None:
    """Pop the job's state and `call:` keys from `keyframe-jobs`, skipping any already gone; its quota slot stays claimed."""
    if job_id is None:
        return
    for key in (job_id, call_key(job_id)):
        if key in jobs:
            jobs.pop(key)


def _judge_room(files: VolumeFiles, folder: str) -> Room | None:
    """The stored Room; `None` for a Build that ended without one or a folder already deleted."""
    try:
        return Room.model_validate_json(files.read(f"{folder}/{ROOM_FILE}"))
    except KeyError:
        return None


def _listed_cache_keys(files: VolumeFiles, folder: str) -> list[str]:
    """The keys in the folder's `cache-keys.json`, none when it is absent; one that is not a plain file name is refused with `ValueError`."""
    try:
        keys = CACHE_KEYS.validate_json(files.read(f"{folder}/{CACHE_KEYS_FILE}"))
    except KeyError:
        return []
    for key in keys:
        if not key or PurePosixPath(key).name != key or key in (".", ".."):
            raise ValueError(f"cache key {key!r} in {folder}/{CACHE_KEYS_FILE} is not a file name")
    return keys


def _named_ids(event: Event) -> set[str]:
    """The Room ids an event names: the interactable clicked or paired, or the puzzle targeted."""
    if isinstance(event, ClickEvent):
        return {event.interactable_id}
    if isinstance(event, LockInputEvent):
        if isinstance(event.input, UseOnInput):
            return {event.input.item, event.input.target}
        return {event.input.puzzle_id}
    if isinstance(event, HintRequestEvent | TricksterCardEvent | RungChangeEvent) and event.puzzle_id is not None:
        return {event.puzzle_id}
    return set()


def _on_room(sessions: DictSessionStore, session_id: SessionId, room_id: str) -> bool:
    """Whether the Session's stored header names the Room; False when it has none (a start before headers were stored)."""
    try:
        return sessions.read_header(session_id).room_id == room_id
    except KeyError:
        return False


def _delete_room_sessions(sessions: DictSessionStore, room: Room) -> None:
    """Delete every Session whose header names the Room or whose events name one of its interactables or puzzles, whatever its age."""
    ids = {ix.id for ix in room.interactables} | {pz.id for pz in room.puzzles}
    for session_id in sessions.list_ids():
        with suppress(KeyError):  # another sweep may have deleted it meanwhile
            if _on_room(sessions, session_id, room.id) or any(_named_ids(event) & ids for event in sessions.read_all(session_id)):
                sessions.delete(session_id)


def last_event_ms(session_id: SessionId, events: list[Event]) -> int:
    """Unix milliseconds of the Session's last event: its `sess_` ULID mint time plus the event's `t_ms` (AD-10, AD-18)."""
    return minted_ms(session_id) + (events[-1].t_ms if events else 0)


def sweep_sessions(handles: ModalHandles, *, now: datetime) -> list[SessionId]:
    """Delete every Session whose last event is more than `SESSION_TTL_MS` before `now` and return their ids (AD-8, hourly)."""
    sessions = DictSessionStore(handles.sessions)
    now_ms = int(now.timestamp() * 1000)
    swept: list[SessionId] = []
    for session_id in sessions.list_ids():
        with suppress(KeyError):  # deleted meanwhile, by a Judge room deletion or another sweep
            if now_ms - last_event_ms(session_id, sessions.read_all(session_id)) > SESSION_TTL_MS:
                sessions.delete(session_id)
                swept.append(session_id)
    return swept
