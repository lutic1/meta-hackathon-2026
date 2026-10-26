"""The smoke CLI picks the adapter `Settings` names."""

import pytest

from main import get_provider
from src.config import Settings
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import MockProvider


def test_factory_defaults_to_mock_under_the_test_guard():
    assert isinstance(get_provider(Settings.from_env()), MockProvider)


def test_factory_builds_meta_from_settings():
    provider = get_provider(Settings(model_provider="meta", meta_model_api_key="test-key"))
    assert isinstance(provider, MetaModelProvider)
    assert provider.base_url == "https://api.meta.ai/v1"


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="MODEL_PROVIDER"):
        get_provider(Settings(model_provider="nope"))
