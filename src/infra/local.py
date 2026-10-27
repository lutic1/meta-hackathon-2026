"""Local-mode disk adapters (AD-7, AD-9): the `ArtifactStore` under `rooms/`, the JSON `JobStore` and `SessionStore`, the in-process `JobRunner`, the jsonl `LedgerStore` and the disk `Cache`.

`DiskArtifactStore` maps a key to a file under its root (`rooms/`) and
refuses any key that resolves outside it. `JsonJobStore` keeps one JSON
file per job under `rooms/jobs/`, has no build quota and never refuses a
Build; `JsonSessionStore` keeps one per session
under `rooms/sessions/`; neither holds job or session state in a process
variable, so every instance over the same directory reads the same state,
and a restarted process reads exactly what the stopped one last wrote.
`ThreadJobRunner.start(job_id)` runs the stage runner wiring hands it on a
daemon thread and returns at once, so no request blocks on a stage; the
runner it calls rereads the job from the store and resumes after the last
persisted stage (AD-7). No adapter here deletes a Room, a photo, a job or
a cache entry: the only deletion is `SessionStore.delete`, which Local mode
never calls.

`JsonlLedgerStore` appends one JSON line per entry to `spend/ledger.jsonl`
under an exclusive file lock, outside `.cache/`, so the running total
survives a restart and clearing the cache never touches the record of
spend. The file holds two kinds of line: an entry, and the epoch marker
`{"epoch": "<date>"}` that `start_epoch` writes (`scripts/ledger.py reset`);
`append` stamps each entry with the current epoch (`None` before the first
marker) and `entries` returns the current epoch's entries in append order,
so `SpendLedger` counts exactly what the store returns. `export_ledger`
writes the current epoch's entries and totals to `spend/exports/ledger-<date>.json`,
the committed daily record of spend; `scripts/ledger.py export` wraps it and
API wiring calls it at startup and after every build. `DiskCache` keeps
one JSON file per key under `.cache/`, written whole and renamed into
place.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, TextIO

from pydantic import ConfigDict, Field, TypeAdapter

from src.domain.ledger import LedgerEntry, running_total_usd
from src.domain.schema import Event, JobId, JobState, Model, Room, RoomId, SessionId
from src.pipeline.ports import ROOM_FILE

ROOMS_ROOT = Path("rooms")
"""Every local build artifact, git-ignored; the `ArtifactStore` refuses a key outside it."""
LEDGER_PATH = Path("spend/ledger.jsonl")
"""The live ledger, git-ignored; `spend/exports/` beside it holds the committed daily exports."""
EXPORTS_ROOT = Path("spend/exports")
"""The dated exports, committed with each day's work; an earlier export is never rewritten."""
CACHE_ROOT = Path(".cache")
"""The model-call cache, git-ignored; deleting it never touches `spend/`."""
EVENTS = TypeAdapter(list[Event])

def _replace(path: Path, data: bytes) -> None:
    """Write `data` beside `path` and move it into place, so a reader never sees a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


class DiskArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if Path(key).is_absolute() or path == self.root or not path.is_relative_to(self.root):
            raise ValueError(f"artifact key {key!r} resolves outside {self.root.name}/")
        return path

    def put(self, key: str, data: bytes) -> None:
        _replace(self._path(key), data)

    def read(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError:
            raise KeyError(key) from None

    def list_rooms(self) -> list[Room]:
        """Every stored Room, newest `created` first."""
        rooms = [Room.model_validate_json(path.read_bytes()) for path in self.root.rglob(ROOM_FILE)]
        return sorted(rooms, key=lambda room: room.created, reverse=True)

    def is_demo_room(self, room_id: str) -> bool:
        """Never: Local mode has no Demo rooms, so every local start gets the First-room welcome."""
        return False

    def deleted_room(self, id_: str) -> RoomId | None:
        """None: Local mode deletes no Room and keeps no deletion record (AD-8)."""
        return None


def _json_name(kind: str, id_: str) -> str:
    """`<id>.json` for a store keyed one file per id; an id that is not a plain file name is refused."""
    if not id_ or Path(id_).name != id_:
        raise ValueError(f"{kind} id {id_!r} is not a file name")
    return f"{id_}.json"


class JsonJobStore:
    """`JobStore` over one JSON file per job under `rooms/jobs/`; `put` writes the whole state and replaces the file."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _path(self, job_id: str) -> Path:
        return self.directory / _json_name("job", job_id)

    def put(self, state: JobState) -> None:
        _replace(self._path(state.id), state.model_dump_json().encode())

    def read(self, job_id: JobId) -> JobState:
        try:
            return JobState.model_validate_json(self._path(job_id).read_bytes())
        except FileNotFoundError:
            raise KeyError(job_id) from None

    def list_ids(self) -> list[JobId]:
        if not self.directory.is_dir():
            return []
        return sorted(path.stem for path in self.directory.glob("*.json"))

    def reserve_build(self, job_id: JobId) -> None:
        """Local mode has no build quota: every Build is accepted and nothing is written."""

    def builds_left(self) -> int | None:
        """No quota, so no count."""
        return None


class ThreadJobRunner:
    """`JobRunner` over a daemon thread per `start`: `run` is the stage runner's `run(job_id)`, injected by wiring."""

    def __init__(self, run: Callable[[JobId], object]) -> None:
        self._run = run

    def start(self, job_id: JobId) -> None:
        """Run the job's remaining stages in the background and return before any of them completes."""
        threading.Thread(target=self._run, args=(job_id,), name=f"build-{job_id}", daemon=True).start()


class JsonSessionStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _path(self, session_id: str) -> Path:
        return self.directory / _json_name("session", session_id)

    def append(self, session_id: SessionId, event: Event) -> None:
        path = self._path(session_id)
        events = EVENTS.validate_json(path.read_bytes()) if path.exists() else []
        events.append(event)
        _replace(path, EVENTS.dump_json(events))

    def read_all(self, session_id: SessionId) -> list[Event]:
        try:
            return EVENTS.validate_json(self._path(session_id).read_bytes())
        except FileNotFoundError:
            raise KeyError(session_id) from None

    def list_ids(self) -> list[SessionId]:
        if not self.directory.is_dir():
            return []
        return sorted(path.stem for path in self.directory.glob("*.json"))

    def delete(self, session_id: SessionId) -> None:
        try:
            self._path(session_id).unlink()
        except FileNotFoundError:
            raise KeyError(session_id) from None


def _read_ledger(file: TextIO) -> tuple[list[LedgerEntry], str | None]:
    """Every entry in the file, and the epoch its last marker line names."""
    rows: list[LedgerEntry] = []
    epoch: str | None = None
    for line in file:
        if not line.strip():
            continue
        record = json.loads(line)
        if "call_id" in record:
            rows.append(LedgerEntry.model_validate(record))
        else:
            epoch = record["epoch"]
    return rows, epoch


class JsonlLedgerStore:
    """`LedgerStore` over one jsonl file; every read and append holds the file's exclusive lock."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _locked(self) -> Iterator[TextIO]:
        """The file opened for append and read, locked for the block; the lock is released after a flush."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            try:
                file.seek(0)
                yield file
                file.flush()
            finally:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)

    def append(self, entry: LedgerEntry) -> None:
        """Write the entry as one line under the current epoch."""
        with self._locked() as file:
            _, epoch = _read_ledger(file)
            stamped = LedgerEntry.model_validate({**entry.model_dump(), "epoch": epoch})
            file.seek(0, os.SEEK_END)
            file.write(stamped.model_dump_json() + "\n")

    def entries(self) -> list[LedgerEntry]:
        """The current epoch's entries in append order."""
        with self._locked() as file:
            rows, epoch = _read_ledger(file)
        return [row for row in rows if row.epoch == epoch]

    def epoch(self) -> str | None:
        """The date of the last reset; `None` before the first."""
        with self._locked() as file:
            return _read_ledger(file)[1]

    def start_epoch(self, epoch: str) -> None:
        """Write the epoch marker: every entry appended after it carries `epoch` and the earlier ones stop counting."""
        with self._locked() as file:
            file.seek(0, os.SEEK_END)
            file.write(json.dumps({"epoch": epoch}) + "\n")


class LedgerExport(Model):
    """One day's record of spend: the current epoch's entries and the totals read against the combined ceiling."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    date: str
    epoch: str | None
    entries: list[LedgerEntry]
    local_total_usd: float = Field(ge=0)
    hosted_total_usd: float = Field(ge=0)
    """0 until the hosted snapshot merge lands (7.9)."""
    total_usd: float = Field(ge=0)
    ceiling_usd: float = Field(ge=0)


def export_path(exports_root: Path, today: date) -> Path:
    """`spend/exports/ledger-<date>.json` for `today`."""
    return exports_root / f"ledger-{today.isoformat()}.json"


def export_ledger(store: JsonlLedgerStore, exports_root: Path, today: date, ceiling_usd: float) -> LedgerExport:
    """Write today's export from the store's current epoch and return it; an empty ledger exports a total of 0.

    The file is replaced whole, so a reader (or `git add`) never sees a partial export.
    """
    entries = store.entries()
    local_total = running_total_usd(entries)
    export = LedgerExport(
        date=today.isoformat(),
        epoch=store.epoch(),
        entries=entries,
        local_total_usd=local_total,
        hosted_total_usd=0.0,
        total_usd=local_total,
        ceiling_usd=ceiling_usd,
    )
    _replace(export_path(exports_root, today), (export.model_dump_json(indent=2) + "\n").encode())
    return export


class DiskCache:
    """`Cache` over one JSON file per key under `root`."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            return json.loads(self._path(key).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        """Write the object to a temporary file in `root`, then rename it over the key's file."""
        self.root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=self.root, prefix=f"{key}.", suffix=".tmp", delete=False, encoding="utf-8") as file:
            json.dump(value, file)
        os.replace(file.name, self._path(key))
