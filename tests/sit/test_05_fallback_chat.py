"""SIT-11: one Riddler `chat` call through the `openai_compatible` adapter on the host `.env` names (Baseten or Fireworks)."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.council.riddler import PUZZLE_KEYS, build_author_prompt
from src.domain.redact import to_prompt_view
from src.providers.openai_compatible import RIDDLER_BUDGET_S
from tests.fixtures.rooms import write_fixtures

if TYPE_CHECKING:
    from scripts.sit import Sit

FIXTURE = "chat-riddler-author"


def run(sit: Sit) -> str:
    """`CACHE=off`, `json_schema` mode: the strict schema travels as `response_format` and the reply parses into it."""
    with tempfile.TemporaryDirectory() as scratch:
        room, _ = write_fixtures(Path(scratch))  # synthetic scenes outside the repo; no photo is sent
    prompt = build_author_prompt(to_prompt_view(room))
    provider = sit.openai_compatible(kind="riddler", json_mode="json_schema", cache=False)

    started = time.monotonic()
    reply = provider.chat(prompt.messages(), response_schema=prompt.response_schema, reasoning_effort=prompt.reasoning_effort)
    latency = time.monotonic() - started
    sit.record(FIXTURE, model=reply.model.rsplit("/", 1)[-1])
    draft = prompt.response_schema.model_validate_json(reply.text)
    puzzles = [key for key in PUZZLE_KEYS if getattr(draft, key) is not None]
    overrun = f"; over the {RIDDLER_BUDGET_S:.0f} s budget" if latency > RIDDLER_BUDGET_S else ""
    return f"{reply.model}: {len(puzzles)} puzzles in {latency:.1f} s{overrun}; {reply.usage.get('completion_tokens', '?')} out"
