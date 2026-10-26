"""The scaffold's mock adapter: deterministic, scriptable, no network."""

from src.providers.base import ChatMessage
from src.providers.mock import MockProvider


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
