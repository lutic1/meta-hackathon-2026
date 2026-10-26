"""Stories 1.11, 1.12, 1.14, 2.12, 2.22, 3.2, 3.7 and 7.2: wiring is the one module that builds an adapter; one `ModelProvider` per council role, `PROVIDER_<ROLE>` replacing only its own; `GUIDE` alone selects the `HintPhraser`, and only `GUIDE=ollama` builds the Ollama adapter; `MODE` selects the local or the hosted adapters (AD-5, AD-7, AD-9, AD-14)."""

import ast
import json
import threading
from pathlib import Path

import pytest

from src.api import wiring
from src.api.errors import AccessDenied
from src.api.wiring import (
    JOBS_DIR,
    ROLE_CALLS,
    SESSIONS_DIR,
    StageNotBuilt,
    artifact_store,
    build_clock,
    build_stages,
    hint_phraser,
    job_runner,
    job_store,
    ledger_store,
    model_cache,
    model_providers,
    resume_jobs,
    session_clock,
    session_store,
    spend_ledger,
)
from src.config import Settings
from src.domain.schema import GuideModel, JobId, JobState, Role, Stage
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
    ThreadJobRunner,
)
from src.infra.modal import (
    DictJobStore,
    DictLedgerStore,
    DictSessionStore,
    VolumeArtifactStore,
    VolumeCache,
    call_key,
)
from src.pipeline.build import STAGES, Build, StageFn, StageResult
from src.pipeline.ports import room_key
from src.providers.base import HintPhraser, ModelProvider
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import ChatCall, MockProvider, MockScript, SegmentCall
from src.providers.ollama import DEFAULT_HOST, OllamaPhraser
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.verbatim import VerbatimPhraser
from tests.api.hosted import hosted_handles, hosted_settings
from tests.infra.test_clocks import Ticker
from tests.pipeline.stages import labels
from tests.pipeline.test_author_stage import reply, riddler, store_interactables
from tests.pipeline.test_build import MemoryJobStore
from tests.pipeline.test_segment_stage import INSIDE
from tests.pipeline.uploads import make_uploads

SRC = Path(__file__).resolve().parents[2] / "src"
ADAPTERS = (
    DiskArtifactStore, JsonJobStore, ThreadJobRunner, JsonSessionStore, JsonlLedgerStore, DiskCache, SessionClock, BuildClock,
    VerbatimPhraser, OllamaPhraser, MockProvider, MetaModelProvider, OpenAICompatibleProvider,
)
"""Every class under `src/infra` and `src/providers` that implements a port."""


def test_guide_verbatim_gives_the_verbatim_adapter():
    phraser = hint_phraser(Settings(guide="verbatim"))
    assert type(phraser) is VerbatimPhraser and isinstance(phraser, HintPhraser)


def test_meta_reports_guide_verbatim_with_no_guide_model():
    settings = Settings(guide="verbatim")
    assert (settings.guide, hint_phraser(settings).guide_model) == ("verbatim", None)
    assert hint_phraser(settings).name == settings.guide


@pytest.mark.parametrize("env", [
    {"GUIDE": "verbatim", "MODEL_PROVIDER": "meta", "PROVIDER_RIDDLER": "openai_compatible"},
    {"GUIDE": "verbatim", "OLLAMA_HOST": "http://127.0.0.1:11434", "CACHE": "off", "DRY_RUN": "off"},
    {"GUIDE": "verbatim", "DEMO_TRICKSTER": "authored", "ACCESS_CODE": "secret"},
])
def test_no_other_setting_selects_a_phraser(env):
    assert type(hint_phraser(Settings.from_env(env))) is VerbatimPhraser


@pytest.mark.parametrize(("env", "host"), [
    ({}, DEFAULT_HOST),
    ({"GUIDE": "ollama"}, DEFAULT_HOST),
    ({"GUIDE": "ollama", "OLLAMA_HOST": "http://127.0.0.1:11435"}, "http://127.0.0.1:11435"),
])
def test_guide_ollama_gives_the_ollama_adapter_at_ollama_host_over_the_verbatim_one(env, host):
    settings = Settings.from_env(env)
    assert settings.guide == "ollama"
    phraser = hint_phraser(settings)
    assert type(phraser) is OllamaPhraser and isinstance(phraser, HintPhraser)
    assert phraser.host == host and type(phraser.fallback) is VerbatimPhraser
    assert (phraser.name, phraser.guide_model) == ("ollama", GuideModel(id="llama3.2:3b", host=host))


def _never(*args, **kwargs):
    raise AssertionError("the Ollama adapter was constructed under GUIDE=verbatim")


@pytest.mark.parametrize("env", [{"GUIDE": "verbatim"}, {"GUIDE": "verbatim", "OLLAMA_HOST": "http://127.0.0.1:11434"}])
def test_guide_verbatim_never_constructs_the_ollama_adapter(env, monkeypatch):
    monkeypatch.setattr(wiring, "OllamaPhraser", _never)
    phraser = hint_phraser(Settings.from_env(env))
    assert type(phraser) is VerbatimPhraser and phraser.guide_model is None


def test_the_offline_suite_sets_guide_verbatim_explicitly():
    settings = Settings.from_env()
    assert settings.guide == "verbatim"
    assert type(hint_phraser(settings)) is VerbatimPhraser


def _constructed(path: Path) -> set[str]:
    """The adapter classes a module calls by name."""
    names = {adapter.__name__ for adapter in ADAPTERS}
    called: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name in names:
                called.add(name)
    return called


def test_wiring_is_the_only_module_that_constructs_an_adapter():
    constructors = {path.relative_to(SRC).as_posix(): _constructed(path) for path in SRC.rglob("*.py") if _constructed(path)}
    assert constructors == {"api/wiring.py": {
        "DiskArtifactStore", "JsonJobStore", "ThreadJobRunner", "JsonSessionStore", "JsonlLedgerStore", "DiskCache",
        "SessionClock", "BuildClock", "VerbatimPhraser", "OllamaPhraser", "MockProvider", "MetaModelProvider",
        "OpenAICompatibleProvider",
    }}


def test_artifact_store_is_the_disk_store_under_rooms(tmp_path):
    store = artifact_store()
    assert type(store) is DiskArtifactStore and store.root == ROOMS_ROOT.resolve()
    assert artifact_store(tmp_path / "rooms").root == tmp_path / "rooms"


def test_job_store_is_the_json_records_under_rooms_jobs(tmp_path):
    store = job_store()
    assert type(store) is JsonJobStore and store.directory == ROOMS_ROOT / "jobs"
    assert JOBS_DIR == "jobs" and job_store(tmp_path).directory == tmp_path / "jobs"


def test_session_store_is_the_json_log_under_rooms_sessions(tmp_path):
    store = session_store()
    assert type(store) is JsonSessionStore and store.directory == ROOMS_ROOT / "sessions"
    assert SESSIONS_DIR == "sessions" and session_store(tmp_path).directory == tmp_path / "sessions"


@pytest.mark.parametrize("env, timescale", [({}, 1), ({"DEMO_TIMESCALE": "6"}, 6)])
def test_session_clock_takes_the_timescale_from_settings(env, timescale):
    clock = session_clock(Settings.from_env(env))
    assert type(clock) is SessionClock and clock.timescale == timescale


# --- One ModelProvider per council role (Story 2.12) ------------------------

ROLES: tuple[Role, ...] = ("architect", "riddler", "dryrun", "trickster", "image")
FALLBACK = {"OPENAI_COMPATIBLE_BASE_URL": "https://inference.baseten.co/v1", "OPENAI_COMPATIBLE_API_KEY": "test-fallback-key"}


def _providers(tmp_path: Path, env: dict[str, str]) -> dict[Role, ModelProvider]:
    settings = Settings.from_env(env)
    return model_providers(settings, model_cache(tmp_path / CACHE_ROOT), spend_ledger(settings, ledger_store(tmp_path / LEDGER_PATH)))


def test_model_provider_mock_gives_each_role_its_own_mock(tmp_path):
    providers = _providers(tmp_path, {"MODEL_PROVIDER": "mock"})
    assert list(providers) == list(ROLES)
    assert all(type(p) is MockProvider and p.role == role for role, p in providers.items())
    assert len({id(p) for p in providers.values()}) == len(ROLES)


def test_provider_riddler_switches_only_the_riddler_role(tmp_path):
    providers = _providers(tmp_path, {"MODEL_PROVIDER": "mock", "PROVIDER_RIDDLER": "openai_compatible", **FALLBACK})
    riddler = providers["riddler"]
    assert type(riddler) is OpenAICompatibleProvider
    assert (riddler.base_url, riddler.kind, riddler.budget_s) == ("https://inference.baseten.co/v1", "riddler", 45.0)
    assert riddler._calls.host == "inference.baseten.co"
    assert {role: type(p) for role, p in providers.items() if role != "riddler"} == dict.fromkeys(set(ROLES) - {"riddler"}, MockProvider)


def test_model_provider_meta_gives_each_role_a_meta_adapter_priced_as_its_kind(tmp_path):
    providers = _providers(tmp_path, {"MODEL_PROVIDER": "meta", "META_MODEL_API_KEY": "test-key", "PROVIDER_RIDDLER": "openai_compatible", **FALLBACK})
    meta = {role: p for role, p in providers.items() if role != "riddler"}
    assert all(type(p) is MetaModelProvider for p in meta.values())
    assert {role: (p.chat_kind, p.budget_s) for role, p in meta.items()} == {role: ROLE_CALLS[role] for role in meta}
    assert ROLE_CALLS["architect"] == ("vision", 15.0) and ROLE_CALLS["dryrun"] == ("dryrun", 30.0)
    assert {p._calls.host for p in meta.values()} == {"api.meta.ai"}
    assert type(providers["riddler"]) is OpenAICompatibleProvider
    ledgers = {id(p._calls._ledger) for p in providers.values()}
    caches = {id(p._calls._cache) for p in providers.values()}
    assert len(ledgers) == 1 and len(caches) == 1, "one SpendLedger and one cache per process (AD-6)"
    assert all(p._calls.enabled for p in providers.values())


def test_cache_off_bypasses_the_cache_for_every_hosted_role(tmp_path):
    providers = _providers(tmp_path, {"MODEL_PROVIDER": "meta", "META_MODEL_API_KEY": "test-key", "CACHE": "off"})
    assert not any(p._calls.enabled for p in providers.values())


def test_an_unknown_provider_is_refused_naming_its_role(tmp_path):
    with pytest.raises(ValueError, match="PROVIDER_TRICKSTER 'fal'"):
        _providers(tmp_path, {"MODEL_PROVIDER": "mock", "PROVIDER_TRICKSTER": "fal"})


def test_the_offline_suite_resolves_five_mocks():
    settings = Settings.from_env()
    assert {getattr(settings, f"provider_{role}") for role in ROLES} == {"mock"}


# --- Job adapters, the stage slots and the restart (Story 2.12) --------------


def test_ledger_cache_and_build_clock_are_the_local_adapters():
    assert type(ledger_store()) is JsonlLedgerStore and ledger_store().path == LEDGER_PATH
    assert type(model_cache()) is DiskCache and model_cache().root == CACHE_ROOT
    assert type(build_clock()) is BuildClock


def _mock_stages(tmp_path: Path, providers: dict[Role, ModelProvider] | None = None) -> dict[Stage, StageFn]:
    """The wired stage functions over the offline mocks, the rooms and the ledger under `tmp_path`."""
    providers = providers or _providers(tmp_path, {"MODEL_PROVIDER": "mock"})
    return build_stages(providers, artifact_store(tmp_path / "rooms"), ledger_store(tmp_path / LEDGER_PATH))


def test_the_landed_stages_run_on_their_roles_and_a_stage_not_landed_raises_stage_not_built(tmp_path):
    jobs = MemoryJobStore()
    candidates = labels(6)
    architect = MockProvider("architect", MockScript(chat=[json.dumps({"candidates": candidates})], segment=[[INSIDE]] * 6))
    providers = {**_providers(tmp_path, {"MODEL_PROVIDER": "mock"}), "architect": architect}
    stages = _mock_stages(tmp_path, providers)
    assert list(stages) == list(STAGES[1:])
    build = Build(jobs=jobs, artifacts=artifact_store(tmp_path / "rooms"), clock=BuildClock(monotonic_ns=Ticker()), stages=stages, regen_max=2)

    state = build.run(build.submit(make_uploads(6)).id)

    # The unscripted Riddler mock answers with no draft, so author sends every attempt back and the job ends
    # needs_recapture there after regen_max + 1 Riddler calls.
    assert (state.status, state.stage) == ("needs_recapture", "author")
    assert [record.stage for record in state.stages][1:3] == ["architect", "segment"]
    assert [type(call) for call in architect.calls] == [ChatCall] + [SegmentCall] * len(candidates)
    assert [type(call) for call in providers["riddler"].calls] == [ChatCall] * 3
    assert len(state.mask_preview) == len(candidates)
    with pytest.raises(StageNotBuilt):
        stages["dryrun"](state)


def test_dry_run_off_builds_over_the_mocks_to_a_done_room_with_no_dry_run_call_and_a_restart_never_rewrites_it(
    tmp_path, four_lock_room
):
    providers = {**_providers(tmp_path, {"MODEL_PROVIDER": "mock"}), "riddler": riddler(reply())}
    artifacts = artifact_store(tmp_path / "rooms")
    ledger = ledger_store(tmp_path / LEDGER_PATH)
    stages = build_stages(providers, artifacts, ledger, dry_run=False)

    def segment(state: JobState) -> StageResult:
        store_interactables(artifacts, state, four_lock_room)
        return StageResult()

    stages["architect"] = lambda state: StageResult()
    stages["segment"] = segment
    jobs = MemoryJobStore()
    build = Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=Ticker()), stages=stages, regen_max=2)

    done = build.run(build.submit(make_uploads(6)).id)

    assert done.status == "done" and providers["dryrun"].calls == [] and ledger.entries() == []
    assert {verdict.verdict for verdict in done.dry_run} == {"skipped"} and len(done.dry_run) == 5
    written = artifacts.read(room_key(done.room_id))
    assert [room.id for room in artifacts.list_rooms()] == [done.room_id]

    finished = threading.Event()
    job_runner(build, on_terminal=finished.set).start(done.id)
    assert finished.wait(5)
    assert artifacts.read(room_key(done.room_id)) == written and jobs.read(done.id) == done


class RecordingRunner:
    def __init__(self) -> None:
        self.started: list[JobId] = []

    def start(self, job_id: JobId) -> None:
        self.started.append(job_id)


def test_resume_jobs_starts_exactly_the_jobs_left_queued_or_running(tmp_path):
    jobs = MemoryJobStore()
    build = Build(jobs=jobs, artifacts=artifact_store(tmp_path / "rooms"), clock=BuildClock(monotonic_ns=Ticker()),
                  stages=_mock_stages(tmp_path), regen_max=2)
    queued = build.submit(make_uploads(6))
    running = jobs.read(build.submit(make_uploads(6)).id).model_copy(update={"status": "running", "stage": "architect"})
    jobs.put(running)
    failed = build.run(build.submit(make_uploads(6)).id)
    runner = RecordingRunner()

    assert resume_jobs(jobs, runner) == sorted([queued.id, running.id]) == sorted(runner.started)
    assert failed.id not in runner.started


def test_resume_jobs_skips_a_job_file_that_does_not_parse_and_starts_the_rest(tmp_path, caplog):
    jobs = job_store(tmp_path)
    build = Build(jobs=jobs, artifacts=artifact_store(tmp_path / "rooms"), clock=BuildClock(monotonic_ns=Ticker()),
                  stages=_mock_stages(tmp_path), regen_max=2)
    queued = build.submit(make_uploads(6))
    corrupt = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    (tmp_path / JOBS_DIR / f"{corrupt}.json").write_text("{}")
    runner = RecordingRunner()

    assert resume_jobs(jobs, runner) == [queued.id] == runner.started
    assert corrupt in caplog.text and "job_unreadable" in caplog.text


def test_job_runner_runs_the_job_in_the_background_then_calls_the_terminal_hook(tmp_path):
    jobs = MemoryJobStore()
    build = Build(jobs=jobs, artifacts=artifact_store(tmp_path / "rooms"), clock=BuildClock(monotonic_ns=Ticker()),
                  stages=_mock_stages(tmp_path), regen_max=2)
    exported = threading.Event()
    runner = job_runner(build, on_terminal=exported.set)
    assert type(runner) is ThreadJobRunner
    queued = build.submit(make_uploads(6))
    runner.start(queued.id)
    assert exported.wait(5) and jobs.read(queued.id).status == "failed"


# --- MODE selects the adapters (Story 7.2, AD-9) ---------------------------------


def _wire(tmp_path: Path, settings: Settings, **options) -> wiring.Wiring:
    """`wire` with every local path under `tmp_path` and stage doubles, so no test touches the repo."""
    return wiring.wire(
        settings,
        stages={stage: _never for stage in STAGES[1:]},
        rooms_root=tmp_path / "rooms",
        ledger_path=tmp_path / LEDGER_PATH,
        exports_root=tmp_path / "exports",
        cache_root=tmp_path / CACHE_ROOT,
        **options,
    )


def test_local_mode_wires_the_disk_adapters_the_profile_routes_and_the_greeting(tmp_path):
    wired = _wire(tmp_path, Settings.from_env())
    assert (type(wired.artifacts), type(wired.jobs), type(wired.sessions)) == (DiskArtifactStore, JsonJobStore, JsonSessionStore)
    assert type(wired.runner) is ThreadJobRunner
    assert (wired.profiles, wired.greets) == (True, True)


def test_hosted_mode_wires_the_dict_and_volume_adapters_and_writes_nothing_locally(tmp_path, monkeypatch):
    monkeypatch.setattr(wiring, "OllamaPhraser", _never)
    handles = hosted_handles(tmp_path)
    seen: dict[str, object] = {}

    def providers(settings, cache, ledger):
        seen.update(cache=cache, ledger=ledger)
        return model_providers(settings, cache, ledger)

    monkeypatch.setattr(wiring, "model_providers", providers)
    wired = wiring.wire(
        hosted_settings(), handles=handles, rooms_root=tmp_path / "rooms", ledger_path=tmp_path / LEDGER_PATH,
        exports_root=tmp_path / "exports", cache_root=tmp_path / CACHE_ROOT,
    )
    assert (type(wired.artifacts), type(wired.jobs), type(wired.sessions)) == (VolumeArtifactStore, DictJobStore, DictSessionStore)
    assert type(seen["cache"]) is VolumeCache and type(seen["ledger"]._store) is DictLedgerStore
    assert seen["ledger"].cap_usd == 20  # the hosted allocation
    assert wired.jobs.jobs is handles.jobs and wired.sessions.sessions is handles.sessions
    assert (wired.profiles, wired.greets) == (False, False)
    assert type(hint_phraser(hosted_settings())) is VerbatimPhraser
    wired.startup()
    wired.on_terminal()
    assert not any((tmp_path / name).exists() for name in ("rooms", "exports", LEDGER_PATH.parts[0], CACHE_ROOT.parts[0]))
    assert (handles.jobs, handles.sessions, handles.ledger) == ({}, {}, {}) and not handles.root.exists()


def test_the_hosted_runner_leaves_the_job_queued_before_run_build(tmp_path):
    handles = hosted_handles(tmp_path)
    wired = _wire(tmp_path, hosted_settings(), handles=handles)
    assert type(wired.runner) is wiring.NoRunner
    queued = wired.build.submit(make_uploads(6))
    wired.runner.start(queued.id)
    assert wired.jobs.read(queued.id).status == "queued" and call_key(queued.id) not in handles.jobs


def test_hosted_mode_without_the_modal_handles_is_refused(tmp_path):
    with pytest.raises(ValueError, match="modal_app"):
        _wire(tmp_path, hosted_settings())


def test_wire_injects_the_access_guard_of_the_running_mode(tmp_path):
    local = _wire(tmp_path, Settings.from_env({"ACCESS_CODE": "lantern-42"}))
    local.guard(None)
    hosted = _wire(tmp_path, hosted_settings(ACCESS_CODE="lantern-42"), handles=hosted_handles(tmp_path))
    hosted.guard("lantern-42")
    with pytest.raises(AccessDenied) as excinfo:
        hosted.guard(None)
    assert (excinfo.value.status, excinfo.value.code, excinfo.value.stage) == (403, "access_denied", None)
