"""Storage ports the pipeline and the adapters share (AD-1, AD-9).

Each port is a Protocol over domain models only; `src/infra` implements it
per mode (`MODE=local|hosted`) and wiring injects the adapter. `ArtifactStore`,
`SessionStore` and the `Clock` re-export land with 1.10; `JobStore` and
`JobRunner` with the stories that need them.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.domain.ledger import LedgerEntry


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
