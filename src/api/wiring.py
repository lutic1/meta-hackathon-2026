"""`Settings` to adapters: the one place an adapter is chosen (AD-5, AD-7, AD-9, AD-14).

`model_providers` resolves one `ModelProvider` per council role (`architect`,
`riddler`, `dryrun`, `storyteller`, `trickster`, `image`) from that role's
`PROVIDER_<ROLE>`, which `Settings` defaults to `MODEL_PROVIDER`, so setting
one role's key replaces that role's provider and no other. Every hosted
adapter shares the process's one `SpendLedger` and the disk cache through
its own `GuardedCalls` (AD-6); the mock touches neither. A paid adapter
(`meta`, `openai_compatible`) is built on its role's first call and reused
after (`LazyProvider`, decisions 61 and 63): a keyless checkout starts,
lists and plays its Rooms with none built, and a setting the adapter refuses
(the fallback's base URL or key unset) fails only the call that needs it,
as a `ProviderError` naming the setting, before any spend is reserved; it is
never replaced by the mock. An unknown `PROVIDER_<ROLE>` is refused at once.
`hint_phraser` resolves the `HintPhraser` from `GUIDE` alone; no other setting selects a
phraser, and the Ollama adapter is built only for `GUIDE=ollama`, at
`OLLAMA_HOST`, over the verbatim adapter it falls back to (the hosted app
never builds it: `Settings` refuses `MODE=hosted` with `GUIDE=ollama`).
An `openai_compatible` role calls the model id its `MODEL_<ROLE>` names
when that is set away from `muse-spark-1.3`, the Meta id no fallback host
serves; left at it, the adapter's own default (Muse Spark Open on Baseten).
So `PROVIDER_TRICKSTER=openai_compatible` on Fireworks takes the confirmed
Fireworks id from `MODEL_TRICKSTER`, and no other role moves.

`wire(settings)` is where `MODE` selects the adapters (AD-9) and the one
mode branch in `src/api`: under `MODE=local` the disk adapters below; under
`MODE=hosted` the Dict and Volume adapters of `src/infra/modal.py` over the
handles `src/api/modal_app.py` passes. It also returns what else differs
between the modes, so `create_app` holds no mode branch of its own: the
hosted app serves no profile route, greets no returning player, runs no
local ledger export and resumes no job in process, it serves
`POST /access/check`, and its `guard` is the hosted `access_guard`. The
hosted `JobRunner` spawns `run_build` with the job id (`handles.spawn`), so
no stage runs in the web container, and the web side's job reads run the
watchdog over `handles.poll` (AD-7). `run_hosted_build` is the body of the
spawned `run_build`: the remaining stages of one Judge build over the
runner's own hosted stores, whose job reads run no watchdog, with the
providers' Cache behind the build's `CacheKeyLog` (AD-8).

`artifact_store`, `job_store`, `session_store`, `ledger_store` and
`model_cache` build the local disk adapters.
`job_runner` runs `Build.run` on the in-process runner and calls its
`on_terminal` hook once the job reaches a terminal status; `resume_jobs`
starts every job a stopped process left `queued` or `running`; and
`ledger_export` is the 2.6 export the API runs at startup and after every
terminal Build (AD-9). `session_clock` is the one place `DEMO_TIMESCALE`
reaches a clock and `build_clock` never sees it (AD-10).

`trickster_source` resolves the Trickster's proposal source from
`DEMO_TRICKSTER` through the source table `trickster_sources` (AD-15), over
the proposals folder (`DEMO_PROPOSALS_DIR`, else `proposals/` at the repo
root, beside `src/`): `scripted` replays the recorded-proposals artifact and
`authored` (cut 1) the pre-authored file, each read when a window asks, and
each refused at startup, naming the file, when it is missing, so a demo
never opens windows it cannot fill; `live` is the live source on the
`trickster` role's provider, and `record` the same source with the recorder
behind it, writing each proposal into the recorded-proposals artifact
(`Settings` refuses `record` in Hosted mode). `wire` builds the per-role
providers once, over the process's one cache and `SpendLedger`, so the
Build and the live Trickster share them.

`access_guard` is the hosted access check on `POST /builds`,
`GET /builds/<job_id>/room` and `POST /access/check` (AD-9): in hosted mode
it first counts the attempt against `ACCESS_ATTEMPTS`, refusing one past the
limit with `TooManyAttempts` (429 `too_many_attempts` with `Retry-After`)
before the code is compared, then compares against `ACCESS_CODE` from
`Settings` in constant time, refusing every code when none is set; a guarded
route refuses a missing or wrong `X-Access-Code` with `AccessDenied` (403
`access_denied`), while the check route answers `ok: false`. The attempts
live in the hosted `AttemptStore`, never in process memory. In Local mode
it counts nothing and lets every request through. The
build quota is the `JobStore`'s own: the hosted store refuses the 21st
slot claim with `BuildQuotaExceeded` and the local store never refuses, so
no route handler reads the mode; `wire` passes `hosted` per mode, and the
hosted `AttemptStore` with it.

`build_stages` maps each stage after ingest to its function over the
providers, the artifact store and the ledger store. Architect and segment
(2.15) run on the `architect` role's provider, the one that finds the
objects in the photos; author (2.20) runs on the `riddler` role's provider
and validate reads the ledger for provenance; scene (2.22) writes the Room
with its provenance from the ledger. With `DRY_RUN=on` the dryrun stage
(2.24) runs on the `dryrun` role's provider and reads the ledger for the
attempt's Room; with `DRY_RUN=off` (cut 4) the slot records every Puzzle
`skipped` and makes no call. The story stage runs on the `storyteller`
role's provider and reads the ledger for the attempt's Room.
"""

from __future__ import annotations

import json
import logging
import math
import secrets
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import get_args

import httpx
from pydantic import ValidationError

from src.api.errors import AccessDenied, TooManyAttempts
from src.config import MUSE_SPARK, Settings
from src.council.trickster import PROPOSAL_FILES, RECORDED_PROPOSALS, SOURCES, LiveSource, TricksterSource
from src.domain.ledger import CallKind
from src.domain.schema import JobId, JobState, Role, Stage
from src.infra.clocks import BuildClock, SessionClock
from src.infra.local import (
    CACHE_ROOT,
    EXPORTS_ROOT,
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
from src.infra.modal import CacheKeyLog, ModalHandles, ModalJobRunner, hosted_stores, run_judge_build, wall_ms
from src.pipeline.architect import architect_stage
from src.pipeline.author import author_stage, validate_stage
from src.pipeline.build import TERMINAL, Build, StageFn
from src.pipeline.dryrun import dry_run_stage
from src.pipeline.ports import ArtifactStore, AttemptStore, Cache, JobRunner, JobStore, LedgerStore, SessionStore
from src.pipeline.scene import scene_stage, skipped_dry_run_stage
from src.pipeline.segment import segment_stage
from src.pipeline.story import story_stage
from src.providers.base import HintPhraser, ModelProvider
from src.providers.cache import GuardedCalls
from src.providers.lazy import LazyProvider
from src.providers.meta_api import DEFAULT_BASE_URL, IMAGE_BUDGET_S, MetaModelProvider
from src.providers.mock import MockProvider
from src.providers.ollama import OllamaPhraser
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.spend import SpendLedger
from src.providers.verbatim import VerbatimPhraser

JOBS_DIR = "jobs"
"""Job records live under `rooms/jobs/` (AD-7)."""
SESSIONS_DIR = "sessions"
"""Session logs live under `rooms/sessions/` (AD-9)."""
PROPOSALS_DIR = Path(__file__).resolve().parents[2] / "proposals"
"""The proposals folder the Trickster source table reads when `DEMO_PROPOSALS_DIR` is unset: `proposals/` at the repo root, beside `src/`."""

ROLES: tuple[Role, ...] = get_args(Role)
ROLE_CALLS: dict[Role, tuple[CallKind, float]] = {
    "architect": ("vision", 15.0),
    "riddler": ("riddler", 45.0),
    "dryrun": ("dryrun", 30.0),
    "storyteller": ("storyteller", 30.0),
    "trickster": ("trickster", 30.0),
    "image": ("image", IMAGE_BUDGET_S),
}
"""Per role: the ledger kind its chat calls are priced as, and the budget a retry wait must fit in.

Architect 15 s, Riddler 45 s and Dry run 30 s are the `budgets.md` rows; the
storyteller has no row and takes the Dry run's 30 s; the Trickster has no row and takes its 30 s window; the image role makes no chat
call, so it carries the portrait budget of the Meta adapter.
"""


ACCESS_HEADER = "X-Access-Code"
"""The header carrying the hosted access code on the guarded routes (AD-9)."""


@dataclass(frozen=True)
class AttemptLimit:
    """At most `attempts` access attempts per client in any `window_ms`; `key` is a client's store key, formatted with its IP."""

    attempts: int
    window_ms: int
    key: str


ACCESS_ATTEMPTS = AttemptLimit(attempts=10, window_ms=10 * 60 * 1000, key="attempts:{ip}")
"""AD-9: more than 10 access attempts from one client IP in 10 minutes, right code or wrong, answer 429 `too_many_attempts`."""

log = logging.getLogger("keyframe.builds")


class AccessGuard:
    """One app's access check (AD-9): `check` counts the attempt, then compares the code; calling the guard refuses a wrong one.

    `expected` is `None` in Local mode, which counts nothing and accepts
    every code; hosted, it is `ACCESS_CODE`, empty when none is set, which
    refuses every code. Without an attempt store nothing is counted. The
    lock keeps one process's read and write of a client's attempts together.
    """

    def __init__(self, expected: bytes | None, attempts: AttemptStore | None, now_ms: Callable[[], int]) -> None:
        self.expected = expected
        self.attempts = attempts
        self.now_ms = now_ms
        self._lock = threading.Lock()

    def check(self, code: str | None, client: str) -> bool:
        """Whether `code` is the access code, once the attempt from `client` is counted; past the limit, `TooManyAttempts` and no comparison."""
        if self.expected is None:
            return True
        self._count(client)
        return bool(self.expected) and code is not None and secrets.compare_digest(code.encode(), self.expected)

    def __call__(self, code: str | None, client: str) -> None:
        """A guarded route's check of its `X-Access-Code` (`None` when absent): returns, or raises `AccessDenied`."""
        if not self.check(code, client):
            raise AccessDenied()

    def _count(self, client: str) -> None:
        """Store this attempt beside the client's others in the window; a refused attempt is not stored, so the wait ends."""
        if self.attempts is None:
            return
        key = ACCESS_ATTEMPTS.key.format(ip=client)
        with self._lock:
            now = self.now_ms()
            recent = [t for t in self.attempts.read(key) if now - t < ACCESS_ATTEMPTS.window_ms]
            if len(recent) >= ACCESS_ATTEMPTS.attempts:
                wait_ms = min(recent) + ACCESS_ATTEMPTS.window_ms - now
                raise TooManyAttempts(max(1, math.ceil(wait_ms / 1000)))
            self.attempts.write(key, [*recent, now])


def access_guard(
    settings: Settings, *, hosted: bool, attempts: AttemptStore | None = None, now_ms: Callable[[], int] = wall_ms
) -> AccessGuard:
    """The access check: hosted, the attempt limit then the `ACCESS_CODE` comparison; local, none (AD-9)."""
    if not hosted:
        return AccessGuard(None, None, now_ms)
    return AccessGuard((settings.access_code or "").encode(), attempts, now_ms)


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
            settings.model_api_key,
            base_url,
            calls=calls(httpx.URL(base_url or DEFAULT_BASE_URL).host),
            chat_kind=chat_kind,
            budget_s=budget_s,
        )
    if kind == "openai_compatible":
        base_url = settings.openai_compatible_base_url
        model: str = getattr(settings, f"model_{role}")
        return OpenAICompatibleProvider(
            settings.openai_compatible_api_key,
            base_url,
            calls(httpx.URL(base_url).host if base_url else ""),
            model=None if model == MUSE_SPARK else model,
            kind=chat_kind,
            budget_s=budget_s,
        )
    raise ValueError(f"Unknown PROVIDER_{role.upper()} {kind!r}. Use 'mock', 'meta' or 'openai_compatible'.")


PAID_PROVIDERS = frozenset({"meta", "openai_compatible"})
"""The `PROVIDER_<ROLE>` values whose adapter calls a paid host, so it is built only when its role first calls."""


def role_provider(settings: Settings, role: Role, calls: Callable[[str], GuardedCalls]) -> ModelProvider:
    """`model_provider` for `role`, a paid adapter deferred to its first call; the mock, or the refusal of an unknown value, at once."""
    kind: str = getattr(settings, f"provider_{role}")
    if kind not in PAID_PROVIDERS:
        return model_provider(settings, role, calls)
    return LazyProvider(kind, lambda: model_provider(settings, role, calls))


def model_providers(settings: Settings, cache: Cache, ledger: SpendLedger) -> dict[Role, ModelProvider]:
    """One provider per council role, each its own instance, paid ones built on first call; the hosted ones share `cache` and `ledger` (`CACHE=off` skips the cache)."""
    enabled = settings.cache == "on"

    def calls(host: str) -> GuardedCalls:
        return GuardedCalls(cache, ledger, host=host, enabled=enabled)

    return {role: role_provider(settings, role, calls) for role in ROLES}


def build_stages(
    providers: Mapping[Role, ModelProvider], artifacts: ArtifactStore, ledger: LedgerStore, *, dry_run: bool = True
) -> dict[Stage, StageFn]:
    """The function for each stage after ingest over the per-role providers, in stage order.

    `dry_run` is `DRY_RUN=on`; off (cut 4), the dryrun slot records every Puzzle `skipped` and makes no call.
    """
    return {
        "architect": architect_stage(providers["architect"], artifacts),
        "segment": segment_stage(providers["architect"], artifacts),
        "author": author_stage(providers["riddler"], artifacts),
        "validate": validate_stage(artifacts, ledger),
        "dryrun": dry_run_stage(providers["dryrun"], artifacts, ledger) if dry_run else skipped_dry_run_stage(artifacts),
        "story": story_stage(providers["storyteller"], artifacts, ledger),
        "scene": scene_stage(artifacts, ledger),
    }


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


def spend_ledger(settings: Settings, store: LedgerStore) -> SpendLedger:
    """The process's one `SpendLedger`, capped at the running mode's allocation `SPEND_CAP_USD` (AD-6)."""
    return SpendLedger(store, cap_usd=settings.spend_cap_usd)


def ledger_export(
    settings: Settings, store: JsonlLedgerStore, exports_root: Path, today: Callable[[], date] = date.today
) -> Callable[[], LedgerExport]:
    """The 2.6 export of the current epoch to `spend/exports/ledger-<date>.json`, one run at a time, against the combined ceiling."""
    lock = threading.Lock()
    caps = (settings.spend_cap_usd, settings.hosted_spend_cap_usd, settings.hosted_spend_cap_source)

    def export() -> LedgerExport:
        with lock:
            return export_ledger(store, exports_root, today(), *caps)

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


def trickster_sources(provider: ModelProvider) -> dict[str, Callable[[Path], TricksterSource]]:
    """Every `DEMO_TRICKSTER` value to its source over the proposals folder: the replay values, then the live source on `provider` (AD-15).

    `live` never records; `record` writes each live proposal into the
    recorded-proposals artifact in the folder, after the same call.
    """
    return {
        **SOURCES,
        "live": lambda folder: LiveSource(provider),
        "record": lambda folder: LiveSource(provider, recording=folder / RECORDED_PROPOSALS),
    }


def trickster_source(
    settings: Settings, provider: ModelProvider, folder: Path | None = None
) -> Callable[[], TricksterSource | None]:
    """The source `DEMO_TRICKSTER` names in the source table, built over the proposals folder each time a window asks (AD-15).

    The folder is `folder`, else `DEMO_PROPOSALS_DIR`, else `PROPOSALS_DIR`.
    A replay value whose file is missing is refused here, at startup,
    naming the file (the fail-fast shape of `MODE_REFUSED`).
    """
    if folder is None:
        folder = settings.demo_proposals_dir if settings.demo_proposals_dir is not None else PROPOSALS_DIR
    file = PROPOSAL_FILES.get(settings.demo_trickster)
    if file is not None and not (folder / file).is_file():
        raise ValueError(
            f"DEMO_TRICKSTER={settings.demo_trickster} replays {folder / file}, which does not exist: "
            "run `uv run scripts/load_fixtures.py` and set DEMO_PROPOSALS_DIR as it prints, "
            "or record one with DEMO_TRICKSTER=record"
        )
    source = trickster_sources(provider)[settings.demo_trickster]
    return lambda: source(folder)


def session_clock(settings: Settings) -> SessionClock:
    """The session clock at `DEMO_TIMESCALE`: unscaled `t_ms`, scaled thresholds (AD-10)."""
    return SessionClock(settings.demo_timescale)


def build_clock() -> BuildClock:
    """The build clock for stage timings: real milliseconds, never scaled (AD-10)."""
    return BuildClock()


# --- MODE: the adapters and what differs between the modes (AD-9) -------------


def do_nothing() -> None:
    """A hook the running mode has nothing to do in."""


@dataclass(frozen=True)
class Wiring:
    """The adapters `MODE` selects and everything else `create_app` serves differently per mode."""

    artifacts: ArtifactStore
    jobs: JobStore
    sessions: SessionStore
    build: Build
    runner: JobRunner
    on_terminal: Callable[[], object]
    """After a Build ends: locally the 2.6 ledger export; hosted nothing, the daily snapshot is a Modal Cron (7.8)."""
    startup: Callable[[], object]
    """When the app starts: locally the export, then `resume_jobs`; hosted nothing, the spawned runner owns its job (AD-7)."""
    guard: AccessGuard
    """The `access_guard` of the running mode: open locally, the attempt limit and the `ACCESS_CODE` check hosted."""
    access_check: bool
    """Whether `POST /access/check` is served: Hosted mode only."""
    profiles: bool
    """Whether `GET|PUT /profile/<name>` are served: Local mode, cut 2 only (AD-8)."""
    greets: bool
    """Whether a returning Derived block is greeted: Local mode only; every hosted start gets the welcome and `Derived.fresh()`."""
    trickster: ModelProvider
    """The `trickster` role's provider the live source calls, over the same `SpendLedger` as the Build's.

    Locally it shares the Build's cache too. Hosted it runs with the cache
    off (AD-6: guarded and priced, never stored): a live window on a Judge
    room would otherwise write that room's ids into `/data/cache/` under a
    key no `cache-keys.json` lists, which the Nov 10 purge never deletes
    (AD-8). Nothing is lost, since the prompt's `elapsed_ms` makes a
    window's key never repeat.
    """


def wire(
    settings: Settings,
    *,
    handles: ModalHandles | None = None,
    stages: Mapping[Stage, StageFn] | None = None,
    rooms_root: Path = ROOMS_ROOT,
    ledger_path: Path = LEDGER_PATH,
    exports_root: Path = EXPORTS_ROOT,
    cache_root: Path = CACHE_ROOT,
    today: Callable[[], date] = date.today,
    access_clock: Callable[[], int] = wall_ms,
) -> Wiring:
    """The app's adapters for `settings.mode`; `stages` replaces the stage functions built over the per-role providers.

    `MODE=hosted` needs the Modal `handles`; the paths and `today` are the
    local adapters' and are not read in Hosted mode. `access_clock`, Unix
    milliseconds, times the hosted access attempts.
    """
    if settings.mode == "hosted":
        if handles is None or handles.spawn is None or handles.poll is None:
            raise ValueError(
                "MODE=hosted runs on Modal: deploy src/api/modal_app.py, which passes the handles, run_build.spawn and the watchdog poll"
            )
        hosted = hosted_stores(handles, poll=handles.poll)
        ledger = spend_ledger(settings, hosted.ledger)
        providers = model_providers(settings, hosted.cache, ledger)
        build = _build(settings, hosted.artifacts, hosted.jobs, providers, hosted.ledger, stages)
        uncached = role_provider(
            settings, "trickster", lambda host: GuardedCalls(hosted.cache, ledger, host=host, enabled=False)
        )
        return Wiring(
            hosted.artifacts, hosted.jobs, hosted.sessions, build, ModalJobRunner(hosted.jobs, handles.spawn),
            on_terminal=do_nothing, startup=do_nothing,
            guard=access_guard(settings, hosted=True, attempts=hosted.attempts, now_ms=access_clock),
            access_check=True, profiles=False, greets=False, trickster=uncached,
        )
    ledger = ledger_store(ledger_path)
    export = ledger_export(settings, ledger, exports_root, today)
    artifacts, jobs = artifact_store(rooms_root), job_store(rooms_root)
    providers = model_providers(settings, model_cache(cache_root), spend_ledger(settings, ledger))
    build = _build(settings, artifacts, jobs, providers, ledger, stages)
    runner = job_runner(build, on_terminal=export)

    def startup() -> None:
        """Export the ledger, then restart every job a stopped process left `queued` or `running`."""
        export()
        resume_jobs(jobs, runner)

    return Wiring(
        artifacts, jobs, session_store(rooms_root), build, runner,
        on_terminal=export, startup=startup, guard=access_guard(settings, hosted=False), access_check=False, profiles=True, greets=True,
        trickster=providers["trickster"],
    )


def run_hosted_build(
    settings: Settings, handles: ModalHandles, job_id: JobId, *, stages: Mapping[Stage, StageFn] | None = None
) -> JobState:
    """The spawned `run_build`: run the job's remaining stages as the one writer of its record, and return its last state (AD-7).

    The runner's stores carry no poll, so it never fails the job it runs;
    the providers read the Cache through the build's `CacheKeyLog`, which
    lists every key in `cache-keys.json` before its entry is touched (AD-8).
    `stages` replaces the stage functions, as in `wire`.
    """
    stores = hosted_stores(handles)
    room_id = stores.jobs.stored(job_id).room_id
    if room_id is None:
        raise ValueError(f"job {job_id} names no room")
    keys = CacheKeyLog(stores.cache, stores.artifacts, room_id)
    providers = model_providers(settings, keys, spend_ledger(settings, stores.ledger))
    build = _build(settings, stores.artifacts, stores.jobs, providers, stores.ledger, stages)
    return run_judge_build(build.run, job_id, keys=keys)


def _build(
    settings: Settings,
    artifacts: ArtifactStore,
    jobs: JobStore,
    providers: Mapping[Role, ModelProvider],
    ledger: LedgerStore,
    stages: Mapping[Stage, StageFn] | None,
) -> Build:
    if stages is None:
        stages = build_stages(providers, artifacts, ledger, dry_run=settings.dry_run == "on")
    return Build(jobs=jobs, artifacts=artifacts, clock=build_clock(), stages=stages, regen_max=settings.regen_max)
