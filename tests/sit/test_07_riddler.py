"""SIT-13: one Riddler `chat` call on Meta at medium over the 2.19 prompt, mapped to `pz_` ids and judged by the Validator."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.council.riddler import build_author_prompt
from src.domain.validator import validate
from src.pipeline.author import (
    RIDDLER_BUDGET_MS,
    map_draft,
    parse_draft,
    prompt_view,
    rule_verdicts,
)
from src.providers.meta_api import CHAT_MODEL
from tests.fixtures.rooms import write_fixtures

if TYPE_CHECKING:
    from scripts.sit import Sit

FIXTURE = "chat-riddler-author"
"""Replayed offline by the author stage tests."""
RIDDLER_BUDGET_S = RIDDLER_BUDGET_MS / 1000
ATTEMPT = 0
"""The Regeneration count of a first draft."""


def run(sit: Sit) -> str:
    """`CACHE=off`: the reply parses into a `RoomDraft`, its `ix_` ids match exactly, and the verdicts are reported, not asserted."""
    with tempfile.TemporaryDirectory() as scratch:
        room, _ = write_fixtures(Path(scratch))  # synthetic scenes outside the repo; no photo is sent
    prompt = build_author_prompt(prompt_view(room.id, room.interactables))
    provider = sit.meta("riddler", RIDDLER_BUDGET_S, cache=False)

    started = time.monotonic()
    reply = provider.chat(
        prompt.messages(), response_schema=prompt.response_schema, reasoning_effort=prompt.reasoning_effort, attempt=ATTEMPT
    )
    latency = time.monotonic() - started
    sit.record(FIXTURE, model=CHAT_MODEL)
    puzzles = map_draft(parse_draft(reply.text, prompt.response_schema), {ix.id for ix in room.interactables})
    verdicts = rule_verdicts(validate(room.model_copy(update={"puzzles": puzzles})))
    passed = sum(verdict.passed for verdict in verdicts)
    overrun = f"; over the {RIDDLER_BUDGET_S:.0f} s budget" if latency > RIDDLER_BUDGET_S else ""
    return (
        f"{len(puzzles)} puzzles in {latency:.1f} s{overrun}; rules {passed} of {len(verdicts)} passed; "
        f"{reply.usage.get('completion_tokens', '?')} out"
    )
