"""Storage ports the pipeline and the adapters share (AD-1, AD-9).

Each port is a Protocol over domain models only; `src/infra` implements it
per mode (`MODE=local|hosted`) and wiring injects the adapter. `ArtifactStore`,
`SessionStore` and the `Clock` re-export land with 1.10; `Cache`, `JobStore`
and `JobRunner` with the stories that need them.
"""

from __future__ import annotations

from typing import Protocol

from src.domain.ledger import LedgerEntry


class LedgerStore(Protocol):
    """The append-only spend ledger (AD-6): local `spend/ledger.jsonl`, hosted the `keyframe-ledger` Dict.

    The store owns the epoch marker (AD-9): `append` stores the entry under
    the current epoch and `entries` returns the current epoch's entries in
    append order, so `SpendLedger` counts exactly what the store returns.
    """

    def append(self, entry: LedgerEntry) -> None: ...

    def entries(self) -> list[LedgerEntry]: ...
