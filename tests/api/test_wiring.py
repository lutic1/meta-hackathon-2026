"""Stories 1.11, 1.12 and 3.2: wiring is the one module that builds an adapter; `GUIDE` alone selects the `HintPhraser`, and `GUIDE=ollama` refuses to start without its adapter (AD-5, AD-9, AD-14)."""

import ast
from pathlib import Path

import pytest

from src.api.wiring import NO_OLLAMA_ADAPTER, SESSIONS_DIR, artifact_store, hint_phraser, session_clock, session_store
from src.config import Settings
from src.infra.clocks import BuildClock, SessionClock
from src.infra.local import ROOMS_ROOT, DiskArtifactStore, DiskCache, JsonlLedgerStore, JsonSessionStore
from src.providers.base import HintPhraser
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import MockProvider
from src.providers.verbatim import VerbatimPhraser

SRC = Path(__file__).resolve().parents[2] / "src"
ADAPTERS = (
    DiskArtifactStore, JsonSessionStore, JsonlLedgerStore, DiskCache, SessionClock, BuildClock,
    VerbatimPhraser, MockProvider, MetaModelProvider,
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


@pytest.mark.parametrize("env", [{}, {"GUIDE": "ollama"}, {"GUIDE": "ollama", "OLLAMA_HOST": "http://127.0.0.1:11434"}])
def test_guide_ollama_fails_at_startup_naming_guide_verbatim(env):
    settings = Settings.from_env(env)
    assert settings.guide == "ollama"
    with pytest.raises(ValueError, match="GUIDE=verbatim") as excinfo:
        hint_phraser(settings)
    assert str(excinfo.value) == NO_OLLAMA_ADAPTER


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
    assert constructors == {"api/wiring.py": {"DiskArtifactStore", "JsonSessionStore", "SessionClock", "VerbatimPhraser"}}


def test_artifact_store_is_the_disk_store_under_rooms(tmp_path):
    store = artifact_store()
    assert type(store) is DiskArtifactStore and store.root == ROOMS_ROOT.resolve()
    assert artifact_store(tmp_path / "rooms").root == tmp_path / "rooms"


def test_session_store_is_the_json_log_under_rooms_sessions(tmp_path):
    store = session_store()
    assert type(store) is JsonSessionStore and store.directory == ROOMS_ROOT / "sessions"
    assert SESSIONS_DIR == "sessions" and session_store(tmp_path).directory == tmp_path / "sessions"


@pytest.mark.parametrize("env, timescale", [({}, 1), ({"DEMO_TIMESCALE": "6"}, 6)])
def test_session_clock_takes_the_timescale_from_settings(env, timescale):
    clock = session_clock(Settings.from_env(env))
    assert type(clock) is SessionClock and clock.timescale == timescale
