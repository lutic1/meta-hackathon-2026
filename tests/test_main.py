"""The smoke CLI picks the adapter `Settings` names."""

import pytest

from main import get_provider
from src.config import Settings
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import MockProvider


def test_factory_defaults_to_mock_under_the_test_guard():
    assert isinstance(get_provider(Settings.from_env()), MockProvider)


def test_factory_builds_meta_from_settings():
    provider = get_provider(Settings(model_provider="meta", model_api_key="test-key"))
    assert isinstance(provider, MetaModelProvider)
    assert provider.base_url == "https://api.meta.ai/v1"
    assert (provider.chat_kind, provider.budget_s) == ("vision", 15.0)


def test_factory_guards_meta_with_the_settings_cap_and_cache_flag():
    provider = get_provider(Settings(model_provider="meta", model_api_key="test-key", spend_cap_usd=3, cache="off"))
    assert isinstance(provider, MetaModelProvider)
    assert provider._calls._ledger.cap_usd == 3 and provider._calls.enabled is False


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="MODEL_PROVIDER"):
        get_provider(Settings(model_provider="nope"))
