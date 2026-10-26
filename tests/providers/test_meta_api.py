"""The Meta adapter builds its requests through httpx, offline against a stubbed transport."""

import ast
import json
from pathlib import Path

import httpx
import pytest

from src.config import Settings
from src.providers.base import ChatMessage
from src.providers.meta_api import MetaModelProvider

MODULE = Path(__file__).resolve().parents[2] / "src/providers/meta_api.py"

CHAT_REPLY = {
    "id": "chatcmpl-1", "object": "chat.completion", "model": "muse-spark-1.3",
    "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi there"}}],
    "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
}
IMAGE_REPLY = {"created": 1, "data": [{"b64_json": "UklGR"}], "output_format": "webp"}


def _provider(reply: dict, seen: list[httpx.Request], key: str = "test-key") -> MetaModelProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=reply)

    return MetaModelProvider(api_key=key, transport=httpx.MockTransport(handler))


def test_chat_request_shape():
    seen: list[httpx.Request] = []
    response = _provider(CHAT_REPLY, seen).chat([ChatMessage(role="user", content="hello")])
    assert str(seen[0].url) == "https://api.meta.ai/v1/chat/completions"
    assert seen[0].method == "POST"
    assert seen[0].headers["authorization"] == "Bearer test-key"
    body = json.loads(seen[0].content)
    assert body == {"model": "muse-spark-1.3", "messages": [{"role": "user", "content": "hello"}]}
    assert "temperature" not in body and "max_tokens" not in body
    assert (response.text, response.model, response.usage["total_tokens"]) == ("hi there", "muse-spark-1.3", 5)


def test_image_request_shape():
    seen: list[httpx.Request] = []
    image = _provider(IMAGE_REPLY, seen).generate_image("a wizard")
    assert str(seen[0].url) == "https://api.meta.ai/v1/images/generations"
    body = json.loads(seen[0].content)
    assert body["model"] == "muse-image-1.0" and body["prompt"] == "a wizard"
    assert (image.data, image.model) == ("UklGR", "muse-image-1.0")


def test_key_and_base_url_come_from_settings():
    settings = Settings(meta_model_api_key="from-settings", meta_model_api_base_url="https://example.test/v1/")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CHAT_REPLY)

    provider = MetaModelProvider(settings.meta_model_api_key, settings.meta_model_api_base_url,
                                 transport=httpx.MockTransport(handler))
    provider.chat([ChatMessage(role="user", content="x")])
    assert str(seen[0].url) == "https://example.test/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer from-settings"


def test_missing_key_is_refused():
    with pytest.raises(ValueError, match="META_MODEL_API_KEY"):
        MetaModelProvider(api_key=None)


def test_http_error_raises():
    provider = MetaModelProvider("k", transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"error": {}})))
    with pytest.raises(httpx.HTTPStatusError):
        provider.chat([ChatMessage(role="user", content="x")])


def test_module_uses_httpx_only_and_no_environment_or_contributor_tier():
    tree = ast.parse(MODULE.read_text())
    imported = {alias.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert "httpx" in imported
    assert not {"urllib", "os", "requests"} & imported
    assert "contributor" not in MODULE.read_text()  # standard tier only (FR-36, NFR-4)


def test_live_host_is_blocked_by_the_offline_guard():
    provider = MetaModelProvider("k")
    with pytest.raises(httpx.ConnectError, match="tests run offline"):
        provider.chat([ChatMessage(role="user", content="x")])
