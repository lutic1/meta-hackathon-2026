"""Verbatim Guide adapter: the Rung as written and the Greeting template (AD-3, AD-5).

`VerbatimPhraser` is what `GUIDE=verbatim` selects and what the Ollama
adapter falls back to. `phrase` returns the Rung text byte for byte and
`greet` the Greeting template chosen by the Derived block (UX contract,
Greeting template), both reported as not phrased. It opens no connection
and reads no clock beyond the latency it reports.
"""

from __future__ import annotations

from time import perf_counter_ns

from src.domain.schema import Derived

from .base import HintPhraser, PhraserResponse

GREETING_NEVER_ASKED = "Welcome back. Last time you never asked me once; let's see what this room makes of you."
GREETING_KEPT_GOING = "Welcome back. Last time you kept going long past my first nudge; let's see what this room makes of you."
GREETING_HELD_OUT = "Welcome back. Last time you held out a good while before asking; let's see what this room makes of you."
GREETING_ASKED_EARLY = (
    "Welcome back. Last time you held out just long enough to get your bearings before asking; "
    "let's see what this room makes of you."
)
GREETING_TEMPLATES = (GREETING_NEVER_ASKED, GREETING_KEPT_GOING, GREETING_HELD_OUT, GREETING_ASKED_EARLY)


def greeting_template(derived: Derived) -> str:
    """The template chosen in order: never asked, then `persistence` rounded to two decimals against the bands."""
    if derived.time_to_first_hint_s is None:
        return GREETING_NEVER_ASKED
    persistence = round(derived.persistence, 2)
    if persistence >= 0.34:
        return GREETING_KEPT_GOING
    if persistence <= -0.34:
        return GREETING_ASKED_EARLY
    return GREETING_HELD_OUT


class VerbatimPhraser(HintPhraser):
    name = "verbatim"
    guide_model = None

    def phrase(self, rung_text: str, derived: Derived) -> PhraserResponse:
        return self._as_written(rung_text, perf_counter_ns())

    def greet(self, derived: Derived) -> PhraserResponse:
        return self._as_written(greeting_template(derived), perf_counter_ns())

    @staticmethod
    def _as_written(text: str, started_ns: int) -> PhraserResponse:
        return PhraserResponse(text=text, phrased=False, latency_ms=(perf_counter_ns() - started_ns) // 1_000_000)
