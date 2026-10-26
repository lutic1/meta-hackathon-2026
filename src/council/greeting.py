"""The Greeting composer: the returning player's opening line over `HintPhraser.greet` (AD-3, AD-5, AD-8).

`compose_greeting(phraser, derived)` is the only caller of `greet` in
`src/` (a boundary test keeps it so). Its input is exactly the Derived
block: no room id, label, Clue, Rung or solution reaches it, so the
Greeting can name no object or solution. The adapter `GUIDE` selected
decides the wording: the Ollama adapter phrases the line under the
Greeting brief and answers with the fixed template when it falls back
(past 5 s, unreachable or erroring); the verbatim adapter answers with
the template and runs no Guide model. The composer reports which path
answered and why, so the session start can record `phraser_fallback`
when the Guide model fell back and nothing when there is none.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.domain.schema import Derived
from src.providers.base import HintPhraser

GreetingPath = Literal["phrased", "template"]
GreetingReason = Literal["guide_model", "no_guide_model", "phraser_fallback"]
"""Why the path answered: the Guide model worded it; none runs (`GUIDE=verbatim`); it fell back to the template."""


@dataclass(frozen=True)
class Greeting:
    """The opening line with the path that answered and why, for the caller to record."""

    text: str
    reason: GreetingReason
    latency_ms: int

    @property
    def path(self) -> GreetingPath:
        return "phrased" if self.reason == "guide_model" else "template"


def compose_greeting(phraser: HintPhraser, derived: Derived) -> Greeting:
    """One `greet(derived)` call; the template answers when no Guide model runs or the Guide model fell back."""
    reply = phraser.greet(derived)
    reason: GreetingReason
    if reply.phrased:
        reason = "guide_model"
    elif phraser.guide_model is None:
        reason = "no_guide_model"
    else:
        reason = "phraser_fallback"
    return Greeting(text=reply.text, reason=reason, latency_ms=reply.latency_ms)
