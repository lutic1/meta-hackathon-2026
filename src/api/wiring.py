"""`Settings` to adapters: the one place an adapter is chosen (AD-5, AD-9, AD-14).

`hint_phraser` resolves the `HintPhraser` from `GUIDE` alone; no other
setting selects a phraser. `artifact_store` builds the local disk store and
`session_store` the JSON session log under it; `MODE` joins with the first
hosted story, so only the local adapters exist and no setting selects them.
`session_clock` is the one place `DEMO_TIMESCALE` reaches a clock (AD-10).
The per-role `ModelProvider` resolution, the ledger store and the cache are
wired by the stories that consume them.
"""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.infra.clocks import SessionClock
from src.infra.local import ROOMS_ROOT, DiskArtifactStore, JsonSessionStore
from src.pipeline.ports import ArtifactStore, SessionStore
from src.providers.base import HintPhraser
from src.providers.verbatim import VerbatimPhraser

NO_OLLAMA_ADAPTER = (
    "GUIDE=ollama has no adapter in this build; run with GUIDE=verbatim "
    "(Rungs and the Greeting are shown as written)."
)

SESSIONS_DIR = "sessions"
"""Session logs live under `rooms/sessions/` (AD-9)."""


def hint_phraser(settings: Settings) -> HintPhraser:
    """The Guide adapter `GUIDE` names; `GUIDE=ollama` fails at startup until the Ollama adapter exists."""
    if settings.guide == "verbatim":
        return VerbatimPhraser()
    raise ValueError(NO_OLLAMA_ADAPTER)


def artifact_store(root: Path = ROOMS_ROOT) -> ArtifactStore:
    """The local disk store under `rooms/` (AD-7); tests pass a temporary root."""
    return DiskArtifactStore(root)


def session_store(root: Path = ROOMS_ROOT) -> SessionStore:
    """The JSON session log under `rooms/sessions/` (AD-4); tests pass a temporary root."""
    return JsonSessionStore(root / SESSIONS_DIR)


def session_clock(settings: Settings) -> SessionClock:
    """The session clock at `DEMO_TIMESCALE`: unscaled `t_ms`, scaled thresholds (AD-10)."""
    return SessionClock(settings.demo_timescale)
