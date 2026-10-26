"""SIT-06: a repeated identical text-only call is served from the cache with the running total unchanged."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.providers.base import ChatMessage
from src.providers.meta_api import CHAT_MODEL

if TYPE_CHECKING:
    from scripts.sit import Sit

ARCHITECT_BUDGET_S = 15.0
FIXTURE = "chat-sit-ok"


def run(sit: Sit) -> str:
    """Make one cheap chat call twice with `CACHE=on`; the date in the prompt gives each day one billed first call."""
    provider = sit.meta("vision", ARCHITECT_BUDGET_S, cache=True)
    messages = [ChatMessage(role="user", content=f"Reply with the single word ok. Today is {date.today().isoformat()}.")]
    responses = len(sit.transport.responses)

    first = provider.chat(messages)
    assert first.text.strip(), "an empty reply"
    recorded = len(sit.transport.responses) > responses
    if recorded:
        sit.record(FIXTURE, model=CHAT_MODEL)
    total, entries, responses = sit.running_total_usd(), len(sit.store.entries()), len(sit.transport.responses)

    second = provider.chat(messages)
    assert second.text == first.text, "the repeat was not the cached reply"
    assert len(sit.transport.responses) == responses, "the repeat reached the provider"
    assert len(sit.store.entries()) == entries, "the repeat appended an entry"
    assert sit.running_total_usd() == total, "the repeat changed the running total"
    return f"first call {'billed and recorded' if recorded else 'already cached'}, repeat served from the cache at {total:.4f} USD"
