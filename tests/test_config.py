"""AD-14: configuration enters once, through Settings."""

import ast
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import ENV_KEYS, ROLES, SECRET_KEYS, Settings

REPO = Path(__file__).resolve().parents[1]
ENV_READS = {"environ", "getenv", "putenv", "unsetenv"}
RETIRED_META_KEY = "META_" + "MODEL_API_KEY"  # the retired name, spelled so a repo search finds only history


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
    assert s.hosted_spend_cap_usd == 20 and s.spend_cap_usd + s.hosted_spend_cap_usd == 80
    assert s.model_provider == "meta"
    assert all(getattr(s, f"provider_{role}") == "meta" for role in ROLES)
    assert all(getattr(s, f"model_{role}") == "muse-spark-1.3" for role in ROLES if role != "image")
    assert s.model_image == "muse-image-1.0"
    assert s.model_api_key is None and s.fal_key is None and s.access_code is None
    assert s.meta_model_api_base_url is None and s.ollama_host is None
    assert s.openai_compatible_base_url is None and s.openai_compatible_api_key is None


def test_reads_each_key_exactly_once_and_nothing_else():
    env = CountingEnv()
    Settings.from_env(env)
    assert env.reads == Counter(ENV_KEYS)
    assert env.reads["MODE"] == 1 and env.reads["MIN_CONTAINERS"] == 1
    assert "CHAT_MODEL" not in env.reads and "IMAGE_MODEL" not in env.reads
    assert not any(key.startswith("MAX_COMPLETION_TOKENS_") for key in env.reads)


def test_mode_and_min_containers_default_to_local_and_zero():
    s = Settings.from_env({})
    assert (s.mode, s.min_containers) == ("local", 0)
    s = Settings.from_env({"MODE": "hosted", "MIN_CONTAINERS": "1"})
    assert (s.mode, s.min_containers) == ("hosted", 1)


@pytest.mark.parametrize("env", [{"MODE": "cloud"}, {"MODE": "HOSTED"}, {"MIN_CONTAINERS": "-1"}, {"MIN_CONTAINERS": "one"}])
def test_an_invalid_mode_or_min_containers_fails_at_startup(env):
    with pytest.raises(ValidationError):
        Settings.from_env(env)


@pytest.mark.parametrize(("env", "cap"), [
    ({}, 60), ({"MODE": "local"}, 60), ({"MODE": "hosted"}, 20),
    ({"MODE": "local", "SPEND_CAP_USD": "5"}, 5), ({"MODE": "hosted", "SPEND_CAP_USD": "12.5"}, 12.5),
    ({"MODE": "hosted", "SPEND_CAP_USD": ""}, 20),
])
def test_spend_cap_defaults_per_mode_and_an_explicit_value_overrides_it(env, cap):
    assert Settings.from_env(env).spend_cap_usd == cap


def test_the_mode_defaults_also_apply_to_settings_built_directly():
    assert (Settings(mode="hosted").spend_cap_usd, Settings(mode="hosted").guide) == (20, "verbatim")
    assert (Settings().spend_cap_usd, Settings().guide) == (60, "ollama")
    assert Settings(mode="hosted", spend_cap_usd=3).spend_cap_usd == 3


def test_guide_defaults_per_mode():
    assert Settings.from_env({"MODE": "local"}).guide == "ollama"
    assert Settings.from_env({"MODE": "hosted"}).guide == "verbatim"
    assert Settings.from_env({"MODE": "hosted", "GUIDE": "verbatim"}).guide == "verbatim"


def test_hosted_mode_with_guide_ollama_fails_at_startup():
    with pytest.raises(ValidationError, match="MODE=hosted refuses GUIDE=ollama"):
        Settings.from_env({"MODE": "hosted", "GUIDE": "ollama"})
    with pytest.raises(ValidationError):
        Settings(mode="hosted", guide="ollama")


def test_hosted_mode_with_the_recorder_fails_at_startup():
    with pytest.raises(ValidationError, match="MODE=hosted refuses DEMO_TRICKSTER=record"):
        Settings.from_env({"MODE": "hosted", "DEMO_TRICKSTER": "record"})
    assert Settings.from_env({"MODE": "local", "DEMO_TRICKSTER": "record"}).demo_trickster == "record"


@pytest.mark.parametrize("value", ["live", "scripted", "authored"])
def test_hosted_mode_starts_with_every_other_trickster_source(value):
    assert Settings.from_env({"MODE": "hosted", "DEMO_TRICKSTER": value}).demo_trickster == value


def test_a_refusal_names_only_the_refused_value_never_a_secret():
    with pytest.raises(ValidationError) as excinfo:
        Settings.from_env({"MODE": "hosted", "GUIDE": "ollama", "MODEL_API_KEY": "sk-sentinel", "ACCESS_CODE": "code-sentinel"})
    assert "sentinel" not in str(excinfo.value)


def test_values_are_read_and_blank_means_unset():
    s = Settings.from_env({
        "CACHE": "off", "SPEND_CAP_USD": "20", "DEMO_TIMESCALE": "6", "DEMO_TRICKSTER": "scripted",
        "DRY_RUN": "off", "REGEN_MAX": "1", "GUIDE": "verbatim", "MODEL_API_KEY": "k",
        "FAL_KEY": "", "ACCESS_CODE": "secret", "OLLAMA_HOST": "http://127.0.0.1:11434",
    })
    assert (s.cache, s.spend_cap_usd, s.demo_timescale, s.demo_trickster) == ("off", 20.0, 6, "scripted")
    assert Settings.from_env({"SPEND_CAP_USD": "5"}).spend_cap_usd + s.hosted_spend_cap_usd == 25  # the Thu Nov 5 configuration
    assert (s.dry_run, s.regen_max, s.guide) == ("off", 1, "verbatim")
    assert s.model_api_key == "k" and s.fal_key is None and s.access_code == "secret"
    assert s.ollama_host == "http://127.0.0.1:11434"


def test_the_meta_key_is_read_from_model_api_key_and_never_the_old_name():
    assert Settings.from_env({"MODEL_API_KEY": "k"}).model_api_key == "k"
    assert Settings.from_env({RETIRED_META_KEY: "old"}).model_api_key is None
    assert RETIRED_META_KEY not in ENV_KEYS and "MODEL_API_KEY" in SECRET_KEYS
    assert RETIRED_META_KEY.lower() not in Settings.model_fields


@pytest.mark.parametrize("value", ["live", "record", "scripted", "authored"])
def test_demo_trickster_accepts_the_four_values(value):
    assert Settings.from_env({"DEMO_TRICKSTER": value}).demo_trickster == value


def test_demo_proposals_dir_is_read_as_a_path_and_unset_leaves_the_default_folder_to_wiring():
    assert "DEMO_PROPOSALS_DIR" in ENV_KEYS and "DEMO_PROPOSALS_DIR" not in SECRET_KEYS
    assert Settings.from_env({}).demo_proposals_dir is None
    assert Settings.from_env({"DEMO_PROPOSALS_DIR": "rooms/proposals"}).demo_proposals_dir == Path("rooms/proposals")


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
    assert s.guide == "verbatim"
    assert all(getattr(s, f"provider_{role}") == "mock" for role in ROLES)
    assert s.model_api_key is None and s.fal_key is None
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


def test_the_hosted_allocation_is_read_from_its_key_and_says_where_it_came_from():
    default, blank = Settings.from_env({}), Settings.from_env({"HOSTED_SPEND_CAP_USD": ""})
    assert (default.hosted_spend_cap_usd, default.hosted_spend_cap_source) == (20, "default")
    assert (blank.hosted_spend_cap_usd, blank.hosted_spend_cap_source) == (20, "default")
    s = Settings.from_env({"HOSTED_SPEND_CAP_USD": "15"})
    assert (s.hosted_spend_cap_usd, s.hosted_spend_cap_source) == (15.0, "env")
    assert "HOSTED_SPEND_CAP_USD" in ENV_KEYS and "HOSTED_SPEND_CAP_USD" not in SECRET_KEYS
