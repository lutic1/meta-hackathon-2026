"""Storage ports the pipeline and the adapters share (AD-1, AD-9).

Each port is a Protocol over domain models only; `src/infra` implements it
per mode (`MODE=local|hosted`) and wiring injects the adapter. `Clock` is
declared in `src/domain/clock.py` and re-exported here.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.domain.clock import Clock
from src.domain.ledger import LedgerEntry
from src.domain.schema import Event, JobId, JobState, Room, RoomId, SessionId
from src.domain.session import SessionHeader

__all__ = [
    "ROOM_FILE",
    "ArtifactStore",
    "AttemptStore",
    "BuildQuotaExceeded",
    "Cache",
    "Clock",
    "JobRunner",
    "JobStore",
    "LedgerStore",
    "SessionStore",
    "photo_key",
    "room_key",
]

ROOM_FILE = "room.json"
"""A Room's key ends in this name, under its own `<room_id>/` folder, so `list_rooms` can find every Room."""


def room_key(room_id: str) -> str:
    """The stored Room: `<room_id>/room.json`."""
    return f"{room_id}/{ROOM_FILE}"


def photo_key(room_id: str, index: int) -> str:
    """The stored downscaled JPEG of photo `index`: `<room_id>/photos/<index>.jpg`."""
    return f"{room_id}/photos/{index}.jpg"


class ArtifactStore(Protocol):
    """Build artifacts (AD-7): local, files under `rooms/`; hosted, the `keyframe-data` Volume.

    A key is a relative path such as `demo/<room_id>/room.json` or
    `<room_id>/photos/0.jpg`; one that resolves outside the store is refused
    with `ValueError`, and `read` of a missing key raises `KeyError`. Bytes
    round-trip unchanged: the store re-encodes nothing.

    `is_demo_room` tells whether a stored `room_id` is a Demo room (AD-9):
    hosted, one seeded under `rooms/demo/`; local, never. `POST /sessions`
    picks the welcome from it. `is_judge_room` tells whether it is a Judge
    room: hosted, one stored under `rooms/judge/`; local, never. The session
    state's `judge_room` flag is read from it (the Completion screen's
    deletion line).

    `deleted_room` names the Room an ids-only deletion record holds for a
    room id, a job id or a session id the deletion took (AD-9): hosted, a
    record under `rooms/deleted/`; local, none, since Local mode deletes no
    Room. A route asks it only
    after the Room or job is not found, to answer 410 rather than 404.
    """

    def put(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...

    def list_rooms(self) -> list[Room]: ...

    def is_demo_room(self, room_id: str) -> bool: ...

    def is_judge_room(self, room_id: str) -> bool: ...

    def deleted_room(self, id_: str) -> RoomId | None: ...


class BuildQuotaExceeded(Exception):
    """Every judge build slot is taken (AD-9, AD-13): `JobStore.reserve_build` refuses the Build and writes nothing."""

    def __init__(self, quota: int) -> None:
        super().__init__(f"all {quota} judge builds are used")
        self.quota = quota


class JobStore(Protocol):
    """Job state (AD-7): local, JSON under `rooms/`; hosted, the `keyframe-jobs` Dict.

    The stage runner is the one writer: it `put`s the whole `JobState` after
    every stage and `read`s it back on entry, so a restarted runner resumes
    where the last one stopped. `read` raises `KeyError` for an unknown id;
    `list_ids` returns every stored job id, so wiring can restart the jobs
    left `queued` or `running`. No job state lives in a process variable.

    The store also keeps the judge build quota (AD-9, FR-32):
    `reserve_build` claims one build slot for a job, or raises
    `BuildQuotaExceeded` when none is left; a claimed slot stays claimed
    whatever status the job ends in (A-25), though a hosted slot key can
    expire after 7 idle days, which only frees a build. `builds_left` reads the slots
    still free without claiming one, `None` for a store with no quota. The
    local store has none and never refuses a Build.
    """

    def put(self, state: JobState) -> None: ...

    def read(self, job_id: JobId) -> JobState: ...

    def list_ids(self) -> list[JobId]: ...

    def reserve_build(self, job_id: JobId) -> None: ...

    def builds_left(self) -> int | None: ...


class AttemptStore(Protocol):
    """Recent access attempts per client (AD-9): hosted, keys in the `keyframe-jobs` Dict; Local mode counts none.

    `read` returns the Unix milliseconds of the attempts stored under `key`,
    oldest first, and `[]` for a key never written; `write` replaces them
    whole. The limit itself is the API's: the store only keeps the times,
    so a restart keeps the count.
    """

    def read(self, key: str) -> list[int]: ...

    def write(self, key: str, times: list[int]) -> None: ...


class JobRunner(Protocol):
    """Runs a stored job's remaining stages (AD-7): local, an in-process thread; hosted, `run_build.spawn(job_id)`.

    `start` returns before any stage completes, so no request blocks on a
    stage; the job it names already holds its ingest record in `JobStore`.
    """

    def start(self, job_id: JobId) -> None: ...


class SessionStore(Protocol):
    """The append-only session log (AD-4): local, JSON under `rooms/sessions/`; hosted, the `keyframe-sessions` Dict.

    `read_all` returns a session's events in append order and `list_ids`
    every stored session id; `read_all` and `delete` raise `KeyError` for an
    unknown id. Beside the log, `put_header` stores the session's
    `SessionHeader` once at its start and `read_header` returns it, raising
    `KeyError` for a session stored without one; `delete` removes both, and
    `list_ids` never lists a header. No session state lives in a process
    variable, so a restarted process reopens a session from these two.
    """

    def append(self, session_id: SessionId, event: Event) -> None: ...

    def read_all(self, session_id: SessionId) -> list[Event]: ...

    def list_ids(self) -> list[SessionId]: ...

    def delete(self, session_id: SessionId) -> None: ...

    def put_header(self, session_id: SessionId, header: SessionHeader) -> None: ...

    def read_header(self, session_id: SessionId) -> SessionHeader: ...


class LedgerStore(Protocol):
    """The append-only spend ledger (AD-6): local `spend/ledger.jsonl`, hosted the `keyframe-ledger` Dict.

    The store owns the epoch marker (AD-9): `append` stores the entry under
    the current epoch and `entries` returns the current epoch's entries in
    append order, so `SpendLedger` counts exactly what the store returns.
    """

    def append(self, entry: LedgerEntry) -> None: ...

    def entries(self) -> list[LedgerEntry]: ...


class Cache(Protocol):
    """Model-call responses under their AD-6 key: local `.cache/`, hosted the `keyframe-data` Volume.

    `providers/cache.py` computes the key and encodes each response as one
    JSON object, so the store only maps a key to an object; `get` returns
    `None` on a miss. The cache never holds a ledger entry (AD-6).
    """

    def get(self, key: str) -> dict[str, Any] | None: ...

    def put(self, key: str, value: dict[str, Any]) -> None: ...
