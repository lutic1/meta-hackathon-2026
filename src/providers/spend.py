"""`SpendLedger`: the per-process cap guard over the `LedgerStore` port (AD-6).

One instance per process. `guard` runs the 2.2 arithmetic under a lock, so
reserved plus settled spend never passes the cap, and appends a `reserved`
entry under a fresh `call_` ULID; `settle` replaces it with the observed
cost under the same id after the call, or with 0 USD when the call provably
never left (every attempt failed to connect); any other failure keeps the
reserved estimate. A refused call raises
`SpendCapExceeded` and is never made. Hosted adapters call `guard` only on
a cache miss, inside `src/providers`; the mock provider never touches it.
The cap is injected from `Settings.spend_cap_usd` (AD-14), a per-store,
per-call ceiling with no date logic here.
"""

from __future__ import annotations

import threading

from src.domain.ledger import (
    CallKind,
    LedgerEntry,
    SpendCapExceeded,
    estimate_usd,
    fold,
    running_total_usd,
    settle,
    would_exceed,
)
from src.domain.schema import CallId, JobId, SessionId, Stage
from src.pipeline.ports import LedgerStore
from src.providers.base import new_ulid


def new_call_id() -> CallId:
    """A fresh `call_` ULID from the one minter (AD-18)."""
    return f"call_{new_ulid()}"


class SpendLedger:
    def __init__(self, store: LedgerStore, cap_usd: float) -> None:
        self._store = store
        self.cap_usd = cap_usd
        self._lock = threading.Lock()

    def running_total_usd(self) -> float:
        """Settled plus reserved spend of the current epoch, each `call_` id counted once."""
        with self._lock:
            return running_total_usd(self._store.entries())

    def guard(
        self,
        kind: CallKind,
        *,
        job_id: JobId | None = None,
        stage: Stage | None = None,
        session_id: SessionId | None = None,
    ) -> CallId:
        """Reserve one paid call of `kind` at its current estimate, or refuse it before it is made."""
        with self._lock:
            entries = self._store.entries()
            estimate = estimate_usd(kind, entries)
            if would_exceed(entries, estimate, self.cap_usd):
                raise SpendCapExceeded(self.cap_usd, running_total_usd(entries))
            reserved = LedgerEntry(
                call_id=new_call_id(),
                kind=kind,
                status="reserved",
                usd=estimate,
                job_id=job_id,
                stage=stage,
                session_id=session_id,
            )
            self._store.append(reserved)
            return reserved.call_id

    def settle(self, call_id: CallId, usd: float) -> LedgerEntry:
        """Replace the reserved entry for `call_id` with its observed cost, under the same id."""
        with self._lock:
            reserved = next((e for e in fold(self._store.entries()) if e.call_id == call_id), None)
            if reserved is None:
                raise KeyError(f"no reserved entry for {call_id}")
            settled = settle(reserved, usd)
            self._store.append(settled)
            return settled
