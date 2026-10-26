"""`Settings` to adapters: the one place an adapter is chosen (AD-5, AD-9, AD-14).

`hint_phraser` resolves the `HintPhraser` from `GUIDE` alone; no other
setting selects a phraser, and the Ollama adapter is built only for
`GUIDE=ollama`, at `OLLAMA_HOST`, over the verbatim adapter it falls back
to (the hosted app never builds it: `Settings.mode` refuses `GUIDE=ollama`
in 7.2). `artifact_store` builds the local disk store, `job_store` the JSON
job records and `session_store` the JSON session log under it; `MODE` joins
`Settings` with the first hosted story (7.2), so only the local adapters
exist, no setting selects them, and `MODE` is the constant `local` that
`GET /meta` reports.
`session_clock` is the one place `DEMO_TIMESCALE` reaches a clock (AD-10).
The per-role `ModelProvider` resolution, the ledger store and the cache are
wired by the stories that consume them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from src.config import Settings
from src.infra.clocks import SessionClock
from src.infra.local import (
    ROOMS_ROOT,
    DiskArtifactStore,
    JsonJobStore,
    JsonSessionStore,
)
from src.pipeline.ports import ArtifactStore, JobStore, SessionStore
from src.providers.base import HintPhraser
from src.providers.ollama import OllamaPhraser
from src.providers.verbatim import VerbatimPhraser

MODE: Literal["local"] = "local"
"""The running mode: only the local adapters exist until 7.2 adds `Settings.mode`."""

JOBS_DIR = "jobs"
"""Job records live under `rooms/jobs/` (AD-7)."""
SESSIONS_DIR = "sessions"
"""Session logs live under `rooms/sessions/` (AD-9)."""


def hint_phraser(settings: Settings) -> HintPhraser:
    """The Guide adapter `GUIDE` names: the verbatim adapter, or the Ollama adapter at `OLLAMA_HOST` falling back to it."""
    verbatim = VerbatimPhraser()
    if settings.guide == "verbatim":
        return verbatim
    return OllamaPhraser(settings.ollama_host, fallback=verbatim)


def artifact_store(root: Path = ROOMS_ROOT) -> ArtifactStore:
    """The local disk store under `rooms/` (AD-7); tests pass a temporary root."""
    return DiskArtifactStore(root)


def job_store(root: Path = ROOMS_ROOT) -> JobStore:
    """The JSON job records under `rooms/jobs/` (AD-7); tests pass a temporary root."""
    return JsonJobStore(root / JOBS_DIR)


def session_store(root: Path = ROOMS_ROOT) -> SessionStore:
    """The JSON session log under `rooms/sessions/` (AD-4); tests pass a temporary root."""
    return JsonSessionStore(root / SESSIONS_DIR)


def session_clock(settings: Settings) -> SessionClock:
    """The session clock at `DEMO_TIMESCALE`: unscaled `t_ms`, scaled thresholds (AD-10)."""
    return SessionClock(settings.demo_timescale)
