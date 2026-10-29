"""Spend arithmetic (AD-6): pricing, estimates, running totals and the cap check.

Every function is pure and returns new values. The cap is an argument,
never read here: `SPEND_CAP_USD` is a per-store, per-call ceiling set by
configuration only, and the entries passed in are the ones the caller
counts (the current epoch's, AD-9). Prices and seeds come from
`budgets.md`; `SpendLedger` (`providers/spend.py`) owns the lock and the
store and calls into this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import ConfigDict, Field

from .schema import CallId, JobId, Model, SessionId, Stage

CallKind = Literal["vision", "sam", "riddler", "dryrun", "storyteller", "trickster", "image", "reconstruct3d"]
EntryStatus = Literal["reserved", "settled"]

SPARK_INPUT_USD_PER_M = 1.25
SPARK_CACHED_INPUT_USD_PER_M = 0.15
SPARK_OUTPUT_USD_PER_M = 4.25
"""`muse-spark-1.3`, standard tier; reasoning tokens are part of the output."""
SAM_USD_PER_IMAGE = 2.50 / 1000
"""`sam-3.1`: $2.50 per 1,000 images."""
IMAGE_USD_PER_IMAGE = 0.01
"""`muse-image-1.0`: $0.01 per returned image."""

SEED_USD: dict[CallKind, float] = {
    "vision": 0.03,
    "sam": 0.0025,
    "riddler": 0.03,
    "dryrun": 0.03,
    "storyteller": 0.03,
    "trickster": 0.01,
    "image": 0.01,
    "reconstruct3d": 0.02,
}
"""The per-kind estimate before any cost of that kind has been observed."""


class LedgerEntry(Model):
    """One priced call: `reserved` with its estimate, then `settled` with its observed cost."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    call_id: CallId
    kind: CallKind
    status: EntryStatus
    usd: float = Field(ge=0)
    epoch: str | None = None
    """The last reset the entry belongs to; `None` before the first (AD-9)."""
    job_id: JobId | None = None
    stage: Stage | None = None
    session_id: SessionId | None = None


# --- Pricing from returned usage -------------------------------------------


def spark_cost_usd(usage: Mapping[str, Any]) -> float:
    """Price a `muse-spark-1.3` call from its Chat Completions `usage`.

    Cached prompt tokens bill at the cached rate, the rest of the prompt at
    the input rate; `completion_tokens` already includes reasoning tokens
    and bills at the output rate.
    """
    prompt = int(usage["prompt_tokens"])
    completion = int(usage["completion_tokens"])
    cached = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
    fresh = prompt - cached
    return (
        fresh * SPARK_INPUT_USD_PER_M
        + cached * SPARK_CACHED_INPUT_USD_PER_M
        + completion * SPARK_OUTPUT_USD_PER_M
    ) / 1_000_000


def sam_cost_usd(images: int) -> float:
    """Price a `sam-3.1` call that sent `images` images."""
    return images * SAM_USD_PER_IMAGE


def image_cost_usd(images: int) -> float:
    """Price a `muse-image-1.0` call that returned `images` images."""
    return images * IMAGE_USD_PER_IMAGE


# --- Estimates, folding, totals and the cap check --------------------------


def fold(entries: Iterable[LedgerEntry]) -> list[LedgerEntry]:
    """One entry per `call_` id, in first-seen order; a settled entry replaces a reserved one."""
    by_id: dict[str, LedgerEntry] = {}
    for entry in entries:
        current = by_id.get(entry.call_id)
        if current is None or current.status == "reserved" or entry.status == "settled":
            by_id[entry.call_id] = entry
    return list(by_id.values())


def estimate_usd(kind: CallKind, entries: Iterable[LedgerEntry]) -> float:
    """The last observed cost of `kind` among `entries`, or its seed before any.

    A settlement at 0 USD (a call that failed before it was sent) is no
    observed price, so it never seeds the estimate.
    """
    observed = [e.usd for e in fold(entries) if e.kind == kind and e.status == "settled" and e.usd > 0]
    return observed[-1] if observed else SEED_USD[kind]


def running_total_usd(entries: Iterable[LedgerEntry]) -> float:
    """Settled plus reserved spend, each `call_` id counted once."""
    return sum(e.usd for e in fold(entries))


def would_exceed(entries: Iterable[LedgerEntry], estimate: float, cap: float) -> bool:
    """Whether the running total plus one more call at `estimate` passes `cap`."""
    return running_total_usd(entries) + estimate > cap


def settle(entry: LedgerEntry, usd: float) -> LedgerEntry:
    """The settled entry for a reserved one: same `call_` id, the observed cost."""
    return LedgerEntry.model_validate({**entry.model_dump(), "status": "settled", "usd": usd})


class SpendCapExceeded(Exception):
    """A call whose estimate would pass the cap (AD-13); raised by the guard before the call is made."""

    def __init__(self, cap_usd: float, running_total_usd: float) -> None:
        super().__init__(f"spend cap {cap_usd:.2f} USD would be passed: running total {running_total_usd:.2f} USD")
        self.cap_usd = cap_usd
        self.running_total_usd = running_total_usd
