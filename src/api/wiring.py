"""`Settings` to adapters: the one place an adapter is chosen (AD-5, AD-9, AD-14).

`hint_phraser` resolves the `HintPhraser` from `GUIDE` alone; no other
setting selects a phraser. `artifact_store` builds the local disk store;
`MODE` joins with the first hosted story, so only the local adapter exists
and no setting selects it. The per-role `ModelProvider` resolution, the
session store, the clocks, the ledger store and the cache are wired by the
stories that consume them.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.infra.local import ROOMS_ROOT, DiskArtifactStore
from src.pipeline.ports import ArtifactStore
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


def artifact_store(root: Path = ROOMS_ROOT) -> ArtifactStore:
    """The local disk store under `rooms/` (AD-7); tests pass a temporary root."""
    return DiskArtifactStore(root)
