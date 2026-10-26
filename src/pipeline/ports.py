"""Storage ports the pipeline and the adapters share (AD-1, AD-9).

Each port is a Protocol over domain models only; `src/infra` implements it
per mode (`MODE=local|hosted`) and wiring injects the adapter. `Clock` is
declared in `src/domain/clock.py` and re-exported here; `JobStore` and
`JobRunner` land with the stories that need them.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.domain.clock import Clock
from src.domain.ledger import LedgerEntry
from src.domain.schema import Event, Room, SessionId

__all__ = ["ROOM_FILE", "ArtifactStore", "Cache", "Clock", "LedgerStore", "SessionStore"]

ROOM_FILE = "room.json"
"""A Room's key ends in this name, under its own `<room_id>/` folder, so `list_rooms` can find every Room."""


class ArtifactStore(Protocol):
    """Build artifacts (AD-7): local, files under `rooms/`; hosted, the `keyframe-data` Volume.

    A key is a relative path such as `demo/<room_id>/room.json` or
    `<room_id>/photos/0.jpg`; one that resolves outside the store is refused
    with `ValueError`, and `read` of a missing key raises `KeyError`. Bytes
    round-trip unchanged: the store re-encodes nothing.
    """

    def put(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...

    def list_rooms(self) -> list[Room]: ...


class SessionStore(Protocol):
    """The append-only session log (AD-4): local, JSON under `rooms/sessions/`; hosted, the `keyframe-sessions` Dict.

    `read_all` returns a session's events in append order and `list_ids`
    every stored session id; `read_all` and `delete` raise `KeyError` for an
    unknown id. No session state lives in a process variable.
    """

    def append(self, session_id: SessionId, event: Event) -> None: ...

    def read_all(self, session_id: SessionId) -> list[Event]: ...

    def list_ids(self) -> list[SessionId]: ...

    def delete(self, session_id: SessionId) -> None: ...


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
