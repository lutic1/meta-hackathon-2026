"""Ollama Guide adapter: Llama 3.2 3B on the Mac rewords a Rung or greets, else verbatim answers (AD-3, AD-5).

`OllamaPhraser` is what `GUIDE=ollama` selects in Local mode; the hosted app
never constructs it (`Settings.mode` refuses `GUIDE=ollama` once it lands,
7.2). Each call is one `/api/generate` request to `llama3.2:3b` at
`OLLAMA_HOST` with `keep_alive=-1`, so the model stays resident between
hints. The prompt is `PREFIX`, byte-identical for `phrase` and `greet`,
followed by exactly the Rung text and the Derived block (`greet`: the
Derived block only); it stays under 400 tokens and the output is capped
near 40. Past `TIMEOUT_S`, or at once when Ollama is unreachable or answers
an error, the injected verbatim adapter answers instead, reported as not
phrased, and one `phraser_fallback` JSON line is logged with its cause.
The adapter reads no environment: wiring passes `OLLAMA_HOST` (AD-14).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from time import perf_counter_ns
from typing import Literal

import httpx
import ollama

from src.domain.schema import Derived, GuideModel

from .base import HintPhraser, PhraserResponse

GUIDE_MODEL = "llama3.2:3b"
"""Llama 3.2 3B Instruct, Q4_K_M (the tag's quantization); `scripts/doctor.py` reads this line."""
DEFAULT_HOST = "http://127.0.0.1:11434"
"""Where Ollama.app listens when `OLLAMA_HOST` is unset."""
KEEP_ALIVE = -1
"""Sent on every call, so the model stays resident without `OLLAMA_KEEP_ALIVE` in the app's environment."""
TIMEOUT_S = 5.0
"""NFR-2: past this the verbatim adapter answers; httpx applies it to the connect and to the reply."""
NUM_PREDICT = 48
"""About 40 tokens out: one or two short sentences, with a little room before the cut."""
PROMPT_TOKEN_LIMIT = 400
"""What a recorded fixture's `prompt_eval_count` must stay under (NFR-2)."""

PREFIX = (
    "You are the Guide, the game master of a puzzle room built from the player's own photos. "
    "You speak warmly and a little wryly, and you never scold.\n"
    "When a line is given below, reword it only and never add content: no new object, number, step or answer, "
    "nothing the line does not already say, never a solution. Keep every fact the line holds. "
    "Keep it no longer than the line.\n"
    "When no line is given, greet a returning player from their play record alone, in one or two sentences: "
    "wry, warm and specific about how they play; never about an object or an answer; "
    "nothing that sounds like surveillance; nothing beyond the play record.\n"
    "Answer with the line only: no preface, no label, no quotation marks.\n"
)
"""The fixed prefix: reword, never add content, and the Greeting brief (AD-5, UX contract)."""

FallbackCause = Literal["timeout", "unreachable", "error"]

log = logging.getLogger(__name__)


def derived_block(derived: Derived) -> str:
    """The Derived block as the model reads it: its JSON, nothing added or dropped."""
    return derived.model_dump_json()


def render_phrase_prompt(rung_text: str, derived: Derived) -> str:
    return f"{PREFIX}\nLine:\n{rung_text}\n\nPlay record:\n{derived_block(derived)}\n"


def render_greet_prompt(derived: Derived) -> str:
    return f"{PREFIX}\nPlay record:\n{derived_block(derived)}\n"


def fallback_cause(exc: Exception) -> FallbackCause:
    """`timeout` past `TIMEOUT_S`, `unreachable` when no connection opened, `error` for everything else."""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, ConnectionError | httpx.ConnectError):  # the client turns httpx.ConnectError into ConnectionError
        return "unreachable"
    return "error"


class OllamaPhraser(HintPhraser):
    name = "ollama"

    def __init__(self, host: str | None, fallback: HintPhraser, *, transport: httpx.BaseTransport | None = None) -> None:
        """`host` is `OLLAMA_HOST` (`DEFAULT_HOST` when unset); `fallback` is the verbatim adapter that answers when the model cannot."""
        self.host = host or DEFAULT_HOST
        self.guide_model = GuideModel(id=GUIDE_MODEL, host=self.host)
        self.fallback = fallback
        self.client = ollama.Client(host=self.host, timeout=TIMEOUT_S, transport=transport)

    def phrase(self, rung_text: str, derived: Derived) -> PhraserResponse:
        prompt = render_phrase_prompt(rung_text, derived)
        return self._generate("phrase", prompt, lambda: self.fallback.phrase(rung_text, derived))

    def greet(self, derived: Derived) -> PhraserResponse:
        return self._generate("greet", render_greet_prompt(derived), lambda: self.fallback.greet(derived))

    def _generate(self, call: str, prompt: str, fallback: Callable[[], PhraserResponse]) -> PhraserResponse:
        """One generate call; on any failure the fallback answers and the cause is logged, never raised."""
        started = perf_counter_ns()
        try:
            reply = self.client.generate(
                model=GUIDE_MODEL, prompt=prompt, options={"num_predict": NUM_PREDICT}, keep_alive=KEEP_ALIVE
            )
            text = (reply.response or "").strip()
            if not text:
                raise ollama.ResponseError("the model answered an empty line")
        except (ConnectionError, httpx.HTTPError, ollama.RequestError, ollama.ResponseError, ValueError) as exc:
            elapsed_ms = (perf_counter_ns() - started) // 1_000_000
            self._log_fallback(call, fallback_cause(exc), elapsed_ms, exc)
            return fallback()
        return PhraserResponse(text=text, phrased=True, latency_ms=(perf_counter_ns() - started) // 1_000_000)

    @staticmethod
    def _log_fallback(call: str, cause: FallbackCause, elapsed_ms: int, exc: Exception) -> None:
        line = {
            "event": "phraser_fallback",
            "call": call,
            "cause": cause,
            "duration_ms": elapsed_ms,
            "error": f"{type(exc).__name__}: {exc}",
        }
        log.warning(json.dumps(line))
