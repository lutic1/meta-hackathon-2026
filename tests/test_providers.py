"""Smoke tests for the scaffold. All run offline against the mock.

The point: prove today that the app plumbing works end to end, and
prove on Oct 26 (with two clearly-marked tests flipped) that the Meta
provider honors the same interface.
"""

import pytest

from src.config import Settings
from src.providers import MetaModelProvider, MockProvider, get_provider
from src.providers.base import ChatMessage


def test_mock_chat_default_response():
    provider = MockProvider()
    response = provider.chat([ChatMessage(role="user", content="hello")])
    assert "hello" in response.text
    assert response.model == provider.default_chat_model


def test_mock_chat_scripted_responses_in_order():
    provider = MockProvider(script=["first", "second"])
    assert provider.chat([ChatMessage(role="user", content="a")]).text == "first"
    assert provider.chat([ChatMessage(role="user", content="b")]).text == "second"
    # Script exhausted: falls back to the canned response.
    assert provider.chat([ChatMessage(role="user", content="c")]).text.startswith("[mock]")


def test_mock_generate_image_returns_placeholder():
    provider = MockProvider()
    image = provider.generate_image("a red car on a road")
    assert image.data.startswith("mock://image/")


def test_factory_defaults_to_mock():
    provider = get_provider(Settings(provider="mock"))
    assert isinstance(provider, MockProvider)


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_provider(Settings(provider="nope"))


def test_meta_provider_requires_api_key():
    with pytest.raises(ValueError, match="META_MODEL_API_KEY"):
        MetaModelProvider(api_key=None)


def test_meta_provider_is_a_stub_until_oct_26():
    provider = MetaModelProvider(api_key="test-key")
    with pytest.raises(NotImplementedError):
        provider.chat([ChatMessage(role="user", content="hi")])
    with pytest.raises(NotImplementedError):
        provider.generate_image("anything")
