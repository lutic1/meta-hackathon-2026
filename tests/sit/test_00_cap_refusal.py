"""SIT-07: a cap refusal in which the provider is never called and no entry is appended."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ledger import SpendCapExceeded
from src.providers.base import ChatMessage
from src.providers.spend import SpendLedger

if TYPE_CHECKING:
    from scripts.sit import Sit

ARCHITECT_BUDGET_S = 15.0


def run(sit: Sit) -> str:
    """Guard one `CACHE=off` chat call behind a cap set to the current running total, so the next estimate passes it."""
    total = sit.running_total_usd()
    capped = SpendLedger(sit.store, cap_usd=total)
    provider = sit.meta("vision", ARCHITECT_BUDGET_S, cache=False, ledger=capped)
    entries, responses = len(sit.store.entries()), len(sit.transport.responses)
    try:
        provider.chat([ChatMessage(role="user", content="Say ok.")])
    except SpendCapExceeded as error:
        assert error.cap_usd == total and error.running_total_usd == total, error
    else:
        raise AssertionError(f"the call was made under a {total:.4f} USD cap")
    assert len(sit.store.entries()) == entries, "the refused call appended an entry"
    assert len(sit.transport.responses) == responses, "the refused call reached the provider"
    return f"refused at cap {total:.4f} USD, no entry, no request"
