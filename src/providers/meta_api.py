"""Meta Model API adapter: Muse Spark 1.3 chat and Muse Image 1.0 (standard tier only).

The key comes from `Settings` (AD-14); this module reads no environment.
Requests go through one `httpx.Client`; tests pass an `httpx.MockTransport`
so no socket opens (AD-17). The guarded-call path (cache, spend ledger,
retry), the image parts, `response_format` and `sam-3.1` segmentation land
with the adapter story; until then `chat` refuses what it cannot yet send.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from src.domain.schema import Polygon

from .base import (
    ChatMessage,
    ChatResponse,
    ImageResponse,
    ModelProvider,
    ReasoningEffort,
    check_reasoning_effort,
)

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
CHAT_MODEL = "muse-spark-1.3"
IMAGE_MODEL = "muse-image-1.0"
TIMEOUT_S = 60.0


class MetaModelProvider(ModelProvider):
    name = "meta"
    default_chat_model = CHAT_MODEL
    default_image_model = IMAGE_MODEL

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("META_MODEL_API_KEY is not set. Add it to .env (see .env.example).")
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT_S,
            transport=transport,
        )

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(path, json=body)
        response.raise_for_status()
        return response.json()

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        images: list[bytes] = [],
        response_schema: type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort = "low",
        model: str | None = None,
    ) -> ChatResponse:
        check_reasoning_effort(reasoning_effort)
        if images or response_schema is not None:
            raise NotImplementedError("image parts and response_format land with the Meta adapter story")
        # Sampling stays at the API default and the output cap is an adapter
        # setting, so neither `temperature` nor `max_tokens` is sent.
        body = {
            "model": model or self.default_chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        raw = self._post("/chat/completions", body)
        return ChatResponse(
            text=raw["choices"][0]["message"]["content"],
            model=raw.get("model", body["model"]),
            usage=raw.get("usage", {}),
            raw=raw,
        )

    def segment(self, label: str, image: bytes) -> list[Polygon] | None:
        raise NotImplementedError("sam-3.1 segmentation lands with the Meta adapter story")

    def generate_image(self, prompt: str) -> ImageResponse:
        body = {
            "model": self.default_image_model,
            "prompt": prompt,
            "n": 1,
            "response_format": "b64_json",
        }
        raw = self._post("/images/generations", body)
        return ImageResponse(data=raw["data"][0]["b64_json"], model=body["model"], raw=raw)
