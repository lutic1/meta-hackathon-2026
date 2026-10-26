"""AD-14: configuration enters once, through Settings."""

import ast
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import ENV_KEYS, ROLES, Settings

REPO = Path(__file__).resolve().parents[1]
ENV_READS = {"environ", "getenv", "putenv", "unsetenv"}


class CountingEnv(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads: Counter[str] = Counter()

    def get(self, key, default=None):
        self.reads[key] += 1
        return super().get(key, default)


def test_defaults_when_nothing_is_set():
    s = Settings.from_env({})
    assert (s.cache, s.spend_cap_usd, s.demo_timescale, s.demo_trickster) == ("on", 60, 1, "live")
    assert (s.dry_run, s.regen_max, s.guide) == ("on", 2, "ollama")
    assert s.model_provider == "meta"
    assert all(getattr(s, f"provider_{role}") == "meta" for role in ROLES)
    assert all(getattr(s, f"model_{role}") == "muse-spark-1.3" for role in ROLES if role != "image")
    assert s.model_image == "muse-image-1.0"
    assert s.meta_model_api_key is None and s.fal_key is None and s.access_code is None
    assert s.meta_model_api_base_url is None and s.ollama_host is None
    assert s.openai_compatible_base_url is None and s.openai_compatible_api_key is None


def test_reads_each_key_exactly_once_and_nothing_else():
    env = CountingEnv()
    Settings.from_env(env)
    assert env.reads == Counter(ENV_KEYS)
    assert "MODE" not in env.reads and "MIN_CONTAINERS" not in env.reads
    assert "CHAT_MODEL" not in env.reads and "IMAGE_MODEL" not in env.reads
    assert not any(key.startswith("MAX_COMPLETION_TOKENS_") for key in env.reads)


def test_no_mode_or_min_containers_field():
    assert "mode" not in Settings.model_fields
    assert "min_containers" not in Settings.model_fields


def test_values_are_read_and_blank_means_unset():
    s = Settings.from_env({
        "CACHE": "off", "SPEND_CAP_USD": "20", "DEMO_TIMESCALE": "6", "DEMO_TRICKSTER": "scripted",
        "DRY_RUN": "off", "REGEN_MAX": "1", "GUIDE": "verbatim", "META_MODEL_API_KEY": "k",
        "FAL_KEY": "", "ACCESS_CODE": "secret", "OLLAMA_HOST": "http://127.0.0.1:11434",
    })
    assert (s.cache, s.spend_cap_usd, s.demo_timescale, s.demo_trickster) == ("off", 20.0, 6, "scripted")
    assert (s.dry_run, s.regen_max, s.guide) == ("off", 1, "verbatim")
    assert s.meta_model_api_key == "k" and s.fal_key is None and s.access_code == "secret"
    assert s.ollama_host == "http://127.0.0.1:11434"


@pytest.mark.parametrize("value", ["live", "record", "scripted", "authored"])
def test_demo_trickster_accepts_the_four_values(value):
    assert Settings.from_env({"DEMO_TRICKSTER": value}).demo_trickster == value


@pytest.mark.parametrize("env", [{"DEMO_TRICKSTER": "replay"}, {"GUIDE": "cloud"}, {"CACHE": "yes"},
                                 {"DEMO_TIMESCALE": "0"}, {"REGEN_MAX": "two"}])
def test_invalid_flag_fails_at_startup(env):
    with pytest.raises(ValidationError):
        Settings.from_env(env)


def test_model_provider_is_the_default_for_each_role():
    s = Settings.from_env({"MODEL_PROVIDER": "mock", "PROVIDER_RIDDLER": "openai_compatible"})
    assert s.provider_riddler == "openai_compatible"
    assert all(getattr(s, f"provider_{role}") == "mock" for role in ROLES if role != "riddler")


def test_conftest_forces_mock_and_blank_secrets():
    s = Settings.from_env()
    assert s.model_provider == "mock"
    assert all(getattr(s, f"provider_{role}") == "mock" for role in ROLES)
    assert s.meta_model_api_key is None and s.fal_key is None
    assert s.openai_compatible_api_key is None and s.access_code is None


def _reads_environ(path: Path) -> bool:
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if (isinstance(node, ast.Attribute) and node.attr in ENV_READS
                and isinstance(node.value, ast.Name) and node.value.id == "os"):
            return True
        if (isinstance(node, ast.ImportFrom) and node.module == "os"
                and any(alias.name in ENV_READS for alias in node.names)):
            return True
    return False


def test_only_config_reads_the_environment():
    offenders = [p for p in (REPO / "src").rglob("*.py") if p != REPO / "src/config.py" and _reads_environ(p)]
    assert offenders == [], f"modules reading os.environ outside src/config.py: {offenders}"
    assert _reads_environ(REPO / "src/config.py")
