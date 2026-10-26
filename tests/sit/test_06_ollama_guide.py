"""SIT-05: `phrase` and `greet` on `llama3.2:3b` at `OLLAMA_HOST` with keep-alive -1, then `phrase` again with Ollama unreachable."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.providers.ollama import PROMPT_TOKEN_LIMIT, TIMEOUT_S
from tests.fixtures.guide import BENCHMARK_DERIVED, longest_rung
from tests.fixtures.rooms import write_fixtures

if TYPE_CHECKING:
    from scripts.sit import Sit

FIXTURE_MODEL = "llama3.2-3b"
"""The fixture folder: the model tag with its colon replaced, so the path stays plain."""
UNREACHABLE_HOST = "http://127.0.0.1:1"
"""A closed port: the connection is refused at once, which is the `unreachable` leg."""


def _rate(count: int, duration_ns: int) -> float:
    """Tokens per second from Ollama's count and nanosecond duration."""
    return count / duration_ns * 1e9 if duration_ns else 0.0


def run(sit: Sit) -> str:
    """The longest Rung of the fixture Room with the widest Derived block: the prompt the offline suite bounds every other by."""
    with tempfile.TemporaryDirectory() as scratch:
        room, _ = write_fixtures(Path(scratch))  # synthetic scenes outside the repo; no photo is sent
    rung = longest_rung(room)
    phraser = sit.ollama()

    reply = phraser.phrase(rung, BENCHMARK_DERIVED)
    assert reply.phrased, (
        f"phrase fell back to the verbatim Rung after {reply.latency_ms} ms: Ollama past {TIMEOUT_S:.0f} s is an NFR-2 miss, "
        "else it was unreachable or erroring (see the phraser_fallback log line)"
    )
    _, body = sit.transport.responses[-1]
    assert body["prompt_eval_count"] < PROMPT_TOKEN_LIMIT, f"prompt_eval_count {body['prompt_eval_count']} is not under {PROMPT_TOKEN_LIMIT}"
    sit.record("generate-phrase-longest", model=FIXTURE_MODEL)
    prefill = _rate(body["prompt_eval_count"], body.get("prompt_eval_duration", 0))
    decode = _rate(body["eval_count"], body.get("eval_duration", 0))

    greeting = phraser.greet(BENCHMARK_DERIVED)
    assert greeting.phrased, f"greet fell back to the template after {greeting.latency_ms} ms"
    sit.record("generate-greet", model=FIXTURE_MODEL)

    started = time.monotonic()
    again = sit.ollama(host=UNREACHABLE_HOST).phrase(rung, BENCHMARK_DERIVED)
    unreachable_ms = (time.monotonic() - started) * 1000
    assert again.text == rung and not again.phrased, "the unreachable leg did not answer with the verbatim Rung"
    return (
        f"{body['eval_count']} tokens out in {reply.latency_ms} ms from {body['prompt_eval_count']} in; "
        f"prefill {prefill:.0f} tok/s, decode {decode:.0f} tok/s; greeting {greeting.latency_ms} ms; "
        f"unreachable leg {unreachable_ms:.0f} ms"
    )
