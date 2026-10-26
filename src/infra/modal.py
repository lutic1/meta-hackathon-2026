"""Hosted-mode adapters over Modal Dicts and the `keyframe-data` Volume (AD-7, AD-9): the Dict `JobStore`, `SessionStore` and `LedgerStore`, and the Volume `ArtifactStore` and `Cache`.

`hosted_stores(handles)` builds all five over injected handles
(`ModalHandles`): the Dicts `keyframe-jobs`, `keyframe-sessions` and
`keyframe-ledger` and the Volume `keyframe-data` mounted at `/data`. The
module never imports `modal`, so constructing an adapter contacts no Modal
service. Each adapter uses only the surface a plain `dict` shares with
`modal.Dict` (`get`, item assignment, `in`, `pop`, `keys`, `items`) and the
two Volume calls `commit` and `reload`, so the offline tests pass plain
dicts, a temporary directory and a stub Volume. Nothing is kept in process
memory: every value is read from its Dict or file on each call.

Dict values are plain JSON (`model_dump(mode="json")`), written whole on
every change. `DictJobStore` keeps one key per job id and holds in-flight
job state only; `DictSessionStore` keeps one key per session id holding its
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
"volume busy" while one is). Rooms live at `/data/rooms/demo/<room_id>/`:
the artifact store maps the port's keys (`<room_id>/room.json`,
`<room_id>/photos/<i>.jpg`) under `rooms/demo/`, and `list_rooms()` lists
that partition (7.14 adds `rooms/judge/`). Cache entries live at
`/data/cache/<key>.json`.
"""

from __future__ import annotations

import json
import posixpath
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from pydantic import TypeAdapter

from src.domain.ledger import LedgerEntry
from src.domain.schema import Event, JobId, JobState, Room, SessionId
from src.pipeline.ports import ROOM_FILE

JOBS_DICT = "keyframe-jobs"
SESSIONS_DICT = "keyframe-sessions"
LEDGER_DICT = "keyframe-ledger"
VOLUME = "keyframe-data"
MOUNT = Path("/data")
"""The AD-9 names: three Dicts and the Volume, mounted at `/data`."""

ROOMS_DIR = "rooms"
DEMO_PARTITION = "demo"
"""Demo rooms live under `rooms/demo/`, the only partition this story stores and lists."""
CACHE_DIR = "cache"
"""Cache entries live under `/data/cache/`, one JSON file per key."""
EPOCH_KEY = "epoch"
"""The reserved `keyframe-ledger` key holding the current epoch (AD-9); never a `call_` id."""
EVENTS = TypeAdapter(list[Event])

VOLUME_LOCK = threading.Lock()
"""Every Volume read and write in this process holds it, so `reload()` never runs while a file is open."""


class DictLike(Protocol):
    """The `modal.Dict` surface the adapters use; a plain `dict` satisfies it."""

    def get(self, key: Any, default: Any = None, /) -> Any: ...

    def __setitem__(self, key: Any, value: Any, /) -> None: ...

    def __contains__(self, key: Any, /) -> bool: ...

    def pop(self, key: Any, /) -> Any: ...

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

    def read(self, rel: str) -> bytes:
        """Reload, then read the file fully and close it before the lock is released; a missing file raises `KeyError`."""
        path = self._path(rel)
        with VOLUME_LOCK:
            self.volume.reload()
            try:
                return path.read_bytes()
            except FileNotFoundError:
                raise KeyError(rel) from None

    def read_glob(self, pattern: str) -> list[bytes]:
        """Reload, then read every file matching `pattern` under the root fully, in path order, before the lock is released."""
        with VOLUME_LOCK:
            self.volume.reload()
            return [path.read_bytes() for path in sorted(self.root.glob(pattern)) if path.is_file()]


class VolumeArtifactStore:
    """`ArtifactStore` over `/data/rooms/demo/`; a key that resolves outside that partition is refused with `ValueError`."""

    def __init__(self, files: VolumeFiles) -> None:
        self.files = files
        self.prefix = f"{ROOMS_DIR}/{DEMO_PARTITION}"

    def _rel(self, key: str) -> str:
        rel = posixpath.normpath(f"{self.prefix}/{key}")
        if PurePosixPath(key).is_absolute() or not rel.startswith(f"{self.prefix}/"):
            raise ValueError(f"artifact key {key!r} resolves outside {self.prefix}/")
        return rel

    def put(self, key: str, data: bytes) -> None:
        self.files.write(self._rel(key), data)

    def read(self, key: str) -> bytes:
        try:
            return self.files.read(self._rel(key))
        except KeyError:
            raise KeyError(key) from None

    def list_rooms(self) -> list[Room]:
        """Every Room under `rooms/demo/<room_id>/`, newest `created` first; the route maps each to its `RoomSummary`."""
        rooms = [Room.model_validate_json(data) for data in self.files.read_glob(f"{self.prefix}/*/{ROOM_FILE}")]
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


class DictJobStore:
    """`JobStore` over `keyframe-jobs`: one key per job id holding the whole `JobState`; in-flight state only (AD-7)."""

    def __init__(self, jobs: DictLike) -> None:
        self.jobs = jobs

    def put(self, state: JobState) -> None:
        self.jobs[state.id] = state.model_dump(mode="json")

    def read(self, job_id: JobId) -> JobState:
        raw = self.jobs.get(job_id)
        if raw is None:
            raise KeyError(job_id)
        return JobState.model_validate(raw)

    def list_ids(self) -> list[JobId]:
        """Every job id in the Dict; any other key the hosted app adds there is not a `job_` id."""
        keys = self.jobs.keys()  # `modal.Dict` offers `keys()`, not iteration
        return sorted(key for key in keys if isinstance(key, str) and key.startswith("job_"))


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


def hosted_stores(handles: ModalHandles) -> HostedStores:
    """Build every hosted adapter over `handles`; nothing here reads or writes a Dict or the Volume."""
    files = VolumeFiles(handles.volume, handles.root)
    return HostedStores(
        jobs=DictJobStore(handles.jobs),
        sessions=DictSessionStore(handles.sessions),
        ledger=DictLedgerStore(handles.ledger),
        artifacts=VolumeArtifactStore(files),
        cache=VolumeCache(files),
    )
