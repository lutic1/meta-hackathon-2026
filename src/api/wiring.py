"""`Settings` to adapters: the one place an adapter is chosen (AD-5, AD-7, AD-9, AD-14).

`model_providers` resolves one `ModelProvider` per council role (`architect`,
`riddler`, `dryrun`, `trickster`, `image`) from that role's
`PROVIDER_<ROLE>`, which `Settings` defaults to `MODEL_PROVIDER`, so setting
one role's key replaces that role's provider and no other. Every hosted
adapter shares the process's one `SpendLedger` and the disk cache through
its own `GuardedCalls` (AD-6); the mock touches neither. `hint_phraser`
resolves the `HintPhraser` from `GUIDE` alone; no other setting selects a
phraser, and the Ollama adapter is built only for `GUIDE=ollama`, at
`OLLAMA_HOST`, over the verbatim adapter it falls back to (the hosted app
never builds it: `Settings.mode` refuses `GUIDE=ollama` in 7.2).

`artifact_store`, `job_store`, `session_store`, `ledger_store` and
`model_cache` build the local disk adapters; `MODE` joins `Settings` with
the first hosted story (7.2), so only the local adapters exist, no setting
selects them, and `MODE` is the constant `local` that `GET /meta` reports.
`job_runner` runs `Build.run` on the in-process runner and calls its
`on_terminal` hook once the job reaches a terminal status; `resume_jobs`
starts every job a stopped process left `queued` or `running`; and
`ledger_export` is the 2.6 export the API runs at startup and after every
terminal Build (AD-9). `session_clock` is the one place `DEMO_TIMESCALE`
reaches a clock and `build_clock` never sees it (AD-10).

`access_guard` is the hosted access check on `POST /builds` and
`GET /builds/<job_id>/room` (AD-9): in hosted mode it refuses a missing or
wrong `X-Access-Code` with `AccessDenied` (403 `access_denied`), comparing
against `ACCESS_CODE` from `Settings` in constant time and refusing every
code when none is set; in Local mode it lets every request through. The
build quota is the `JobStore`'s own: the hosted store refuses the 21st
slot claim with `BuildQuotaExceeded` and the local store never refuses, so
no route handler reads the mode. Until 7.2 adds `Settings.mode`, the
`hosted` flag `create_app` receives stands in for it.

`build_stages` maps each stage after ingest to its function over the
providers, the artifact store and the ledger store. Architect and segment
(2.15) run on the `architect` role's provider, the one that finds the
objects in the photos; author (2.20) runs on the `riddler` role's provider
and validate reads the ledger for provenance; scene (2.22) writes the Room
with its provenance from the ledger. With `DRY_RUN=off` (cut 4) the dryrun
slot records every Puzzle `skipped` and makes no call; with `DRY_RUN=on`
it lands with its story (2.24), and until then the slot raises
`StageNotBuilt`, so a Build ends `failed` there rather than pretending to
run.
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path
from typing import Literal, get_args

import httpx
from pydantic import ValidationError

from src.api.errors import AccessDenied
from src.config import Settings
from src.domain.ledger import CallKind
from src.domain.schema import JobId, JobState, Role, Stage
from src.infra.clocks import BuildClock, SessionClock
from src.infra.local import (
    CACHE_ROOT,
    LEDGER_PATH,
    ROOMS_ROOT,
    DiskArtifactStore,
    DiskCache,
    JsonJobStore,
    JsonlLedgerStore,
    JsonSessionStore,
    LedgerExport,
    ThreadJobRunner,
    export_ledger,
)
from src.pipeline.architect import architect_stage
from src.pipeline.author import author_stage, validate_stage
from src.pipeline.build import STAGES, TERMINAL, Build, StageFn, StageResult
from src.pipeline.ports import ArtifactStore, Cache, JobRunner, JobStore, LedgerStore, SessionStore
from src.pipeline.scene import scene_stage, skipped_dry_run_stage
from src.pipeline.segment import segment_stage
from src.providers.base import HintPhraser, ModelProvider
from src.providers.cache import GuardedCalls
from src.providers.meta_api import DEFAULT_BASE_URL, IMAGE_BUDGET_S, MetaModelProvider
from src.providers.mock import MockProvider
from src.providers.ollama import OllamaPhraser
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.spend import SpendLedger
from src.providers.verbatim import VerbatimPhraser

MODE: Literal["local"] = "local"
"""The running mode: only the local adapters exist until 7.2 adds `Settings.mode`."""

JOBS_DIR = "jobs"
"""Job records live under `rooms/jobs/` (AD-7)."""
SESSIONS_DIR = "sessions"
"""Session logs live under `rooms/sessions/` (AD-9)."""

ROLES: tuple[Role, ...] = get_args(Role)
ROLE_CALLS: dict[Role, tuple[CallKind, float]] = {
    "architect": ("vision", 15.0),
    "riddler": ("riddler", 45.0),
    "dryrun": ("dryrun", 30.0),
    "trickster": ("trickster", 30.0),
    "image": ("image", IMAGE_BUDGET_S),
}
"""Per role: the ledger kind its chat calls are priced as, and the budget a retry wait must fit in.

Architect 15 s, Riddler 45 s and Dry run 30 s are the `budgets.md` rows; the
Trickster has no row and takes its 30 s window; the image role makes no chat
call, so it carries the portrait budget of the Meta adapter.
"""


ACCESS_HEADER = "X-Access-Code"
"""The header carrying the hosted access code on the guarded routes (AD-9)."""

type AccessGuard = Callable[[str | None], None]
"""Given a request's `X-Access-Code` (`None` when absent), returns, or raises `AccessDenied`."""

log = logging.getLogger("keyframe.builds")


class StageNotBuilt(Exception):
    """A stage whose story has not landed yet: the Build ends `failed` there with code `stage_not_built`."""

    def __init__(self, stage: Stage) -> None:
        super().__init__(f"the {stage} stage is not built yet")


def access_guard(settings: Settings, *, hosted: bool) -> AccessGuard:
    """The access check on the guarded routes: hosted, the `ACCESS_CODE` comparison; local, none (AD-9)."""
    if not hosted:
        return lambda code: None
    expected = (settings.access_code or "").encode()

    def guard(code: str | None) -> None:
        if not expected or code is None or not secrets.compare_digest(code.encode(), expected):
            raise AccessDenied()

    return guard


def hint_phraser(settings: Settings) -> HintPhraser:
    """The Guide adapter `GUIDE` names: the verbatim adapter, or the Ollama adapter at `OLLAMA_HOST` falling back to it."""
    verbatim = VerbatimPhraser()
    if settings.guide == "verbatim":
        return verbatim
    return OllamaPhraser(settings.ollama_host, fallback=verbatim)


def model_provider(settings: Settings, role: Role, calls: Callable[[str], GuardedCalls]) -> ModelProvider:
    """The adapter `PROVIDER_<ROLE>` names for `role`; `calls(host)` is the guarded path for a hosted adapter (AD-6)."""
    kind: str = getattr(settings, f"provider_{role}")
    chat_kind, budget_s = ROLE_CALLS[role]
    if kind == "mock":
        return MockProvider(role)
    if kind == "meta":
        base_url = settings.meta_model_api_base_url
        return MetaModelProvider(
            settings.meta_model_api_key,
            base_url,
            calls=calls(httpx.URL(base_url or DEFAULT_BASE_URL).host),
            chat_kind=chat_kind,
            budget_s=budget_s,
        )
    if kind == "openai_compatible":
        base_url = settings.openai_compatible_base_url
        return OpenAICompatibleProvider(
            settings.openai_compatible_api_key,
            base_url,
            calls(httpx.URL(base_url).host if base_url else ""),
            kind=chat_kind,
            budget_s=budget_s,
        )
    raise ValueError(f"Unknown PROVIDER_{role.upper()} {kind!r}. Use 'mock', 'meta' or 'openai_compatible'.")


def model_providers(settings: Settings, cache: Cache, ledger: SpendLedger) -> dict[Role, ModelProvider]:
    """One provider per council role, each its own instance; the hosted ones share `cache` and `ledger` (`CACHE=off` skips the cache)."""
    enabled = settings.cache == "on"

    def calls(host: str) -> GuardedCalls:
        return GuardedCalls(cache, ledger, host=host, enabled=enabled)

    return {role: model_provider(settings, role, calls) for role in ROLES}


def build_stages(
    providers: Mapping[Role, ModelProvider], artifacts: ArtifactStore, ledger: LedgerStore, *, dry_run: bool = True
) -> dict[Stage, StageFn]:
    """The function for each stage after ingest over the per-role providers; a stage whose story has not landed raises `StageNotBuilt`.

    `dry_run` is `DRY_RUN=on`; off (cut 4), the dryrun slot records every Puzzle `skipped` and makes no call.
    """

    def not_built(stage: Stage) -> StageFn:
        def run(state: JobState) -> StageResult:
            raise StageNotBuilt(stage)

        return run

    stages = {stage: not_built(stage) for stage in STAGES[1:]}
    stages["architect"] = architect_stage(providers["architect"], artifacts)
    stages["segment"] = segment_stage(providers["architect"], artifacts)
    stages["author"] = author_stage(providers["riddler"], artifacts)
    stages["validate"] = validate_stage(artifacts, ledger)
    if not dry_run:
        stages["dryrun"] = skipped_dry_run_stage(artifacts)
    stages["scene"] = scene_stage(artifacts, ledger)
    return stages


def artifact_store(root: Path = ROOMS_ROOT) -> ArtifactStore:
    """The local disk store under `rooms/` (AD-7); tests pass a temporary root."""
    return DiskArtifactStore(root)


def job_store(root: Path = ROOMS_ROOT) -> JobStore:
    """The JSON job records under `rooms/jobs/` (AD-7); tests pass a temporary root."""
    return JsonJobStore(root / JOBS_DIR)


def session_store(root: Path = ROOMS_ROOT) -> SessionStore:
    """The JSON session log under `rooms/sessions/` (AD-4); tests pass a temporary root."""
    return JsonSessionStore(root / SESSIONS_DIR)


def ledger_store(path: Path = LEDGER_PATH) -> JsonlLedgerStore:
    """The local ledger `spend/ledger.jsonl` (AD-6, AD-9); tests pass a temporary path."""
    return JsonlLedgerStore(path)


def model_cache(root: Path = CACHE_ROOT) -> Cache:
    """The model-call cache under `.cache/` (AD-6); tests pass a temporary root."""
    return DiskCache(root)


def spend_ledger(settings: Settings, store: JsonlLedgerStore) -> SpendLedger:
    """The process's one `SpendLedger`, capped at the Local allocation `SPEND_CAP_USD` (AD-6)."""
    return SpendLedger(store, cap_usd=settings.spend_cap_usd)


def ledger_export(
    settings: Settings, store: JsonlLedgerStore, exports_root: Path, today: Callable[[], date] = date.today
) -> Callable[[], LedgerExport]:
    """The 2.6 export of the current epoch to `spend/exports/ledger-<date>.json`, one run at a time, against the combined ceiling."""
    lock = threading.Lock()
    ceiling = settings.spend_cap_usd + settings.hosted_spend_cap_usd

    def export() -> LedgerExport:
        with lock:
            return export_ledger(store, exports_root, today(), ceiling)

    return export


def job_runner(build: Build, on_terminal: Callable[[], object]) -> JobRunner:
    """The in-process runner over `build.run`; `on_terminal` runs once the job reaches a terminal status."""

    def run(job_id: JobId) -> JobState:
        state = build.run(job_id)
        on_terminal()
        return state

    return ThreadJobRunner(run)


def resume_jobs(jobs: JobStore, runner: JobRunner) -> list[JobId]:
    """Start every job left `queued` or `running` when the API last stopped; each resumes after its last persisted stage (AD-7).

    A job file that does not parse is logged and skipped, so one corrupt record never stops the API from starting.
    """
    left: list[JobId] = []
    for job_id in jobs.list_ids():
        try:
            status = jobs.read(job_id).status
        except ValidationError as exc:
            log.warning(json.dumps({"job_id": job_id, "event": "job_unreadable", "error": f"{exc.error_count()} errors"}))
            continue
        if status not in TERMINAL:
            runner.start(job_id)
            left.append(job_id)
    return left


def session_clock(settings: Settings) -> SessionClock:
    """The session clock at `DEMO_TIMESCALE`: unscaled `t_ms`, scaled thresholds (AD-10)."""
    return SessionClock(settings.demo_timescale)


def build_clock() -> BuildClock:
    """The build clock for stage timings: real milliseconds, never scaled (AD-10)."""
    return BuildClock()
