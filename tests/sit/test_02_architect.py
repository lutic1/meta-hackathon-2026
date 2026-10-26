"""SIT-01: one Architect `chat` call with two photos, parsed into `ArchitectResponse` and recorded."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.council.architect import build_architect_prompt
from src.providers.meta_api import CHAT_MODEL

if TYPE_CHECKING:
    from scripts.sit import Sit

ARCHITECT_BUDGET_S = 15.0
"""`budgets.md`, the Architect row; an overrun is noted, never a fail (NFR-1)."""
FIXTURE = "chat-architect-two-photos"
"""Read by the segment case for its known-present label."""


def run(sit: Sit) -> str:
    """`CACHE=off`: every run makes the vision call, priced from the returned usage."""
    provider = sit.meta("vision", ARCHITECT_BUDGET_S, cache=False)
    prompt = build_architect_prompt(sit.photos(2))
    started = time.monotonic()
    response = prompt.send(provider)
    latency = time.monotonic() - started
    assert response.candidates, "the Architect listed no object"
    sit.record(FIXTURE, model=CHAT_MODEL)
    usage = sit.transport.responses[-1][1].get("usage", {})
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", "?")
    overrun = f"; over the {ARCHITECT_BUDGET_S:.0f} s budget" if latency > ARCHITECT_BUDGET_S else ""
    return f"{len(response.candidates)} candidates in {latency:.1f} s{overrun}; {usage.get('prompt_tokens', '?')} in, {usage.get('completion_tokens', '?')} out, {reasoning} reasoning"
