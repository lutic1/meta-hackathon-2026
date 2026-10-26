"""`Settings` to adapters: the one place an adapter is chosen (AD-5, AD-14).

`hint_phraser` resolves the `HintPhraser` from `GUIDE` alone; no other
setting selects a phraser. The per-role `ModelProvider` resolution and the
storage adapters land with their own stories.
"""

from __future__ import annotations

from src.config import Settings
from src.providers.base import HintPhraser
from src.providers.verbatim import VerbatimPhraser

NO_OLLAMA_ADAPTER = (
    "GUIDE=ollama has no adapter in this build; run with GUIDE=verbatim "
    "(Rungs and the Greeting are shown as written)."
)


def hint_phraser(settings: Settings) -> HintPhraser:
    """The Guide adapter `GUIDE` names; `GUIDE=ollama` fails at startup until the Ollama adapter exists."""
    if settings.guide == "verbatim":
        return VerbatimPhraser()
    raise ValueError(NO_OLLAMA_ADAPTER)
