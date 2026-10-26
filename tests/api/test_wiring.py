"""Story 3.2: `GUIDE` alone selects the `HintPhraser`, and `GUIDE=ollama` refuses to start without its adapter (AD-5, AD-14)."""

import pytest

from src.api.wiring import NO_OLLAMA_ADAPTER, hint_phraser
from src.config import Settings
from src.providers.base import HintPhraser
from src.providers.verbatim import VerbatimPhraser


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


def test_wiring_is_the_only_module_that_constructs_the_adapter():
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "src"
    constructors = [p for p in src.rglob("*.py") if "VerbatimPhraser()" in p.read_text()]
    assert constructors == [src / "api/wiring.py"]
