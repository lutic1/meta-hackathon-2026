"""Meta Model API provider. STUB: wire up on Monday, Oct 26.

Access to the Muse Spark series, Muse Image, and SAM 3.1 through the
Meta Model API is granted at hackathon kickoff. Until the official API
docs are in hand, the endpoint paths and payload shapes below are
placeholders. The wiring job on Monday is deliberately small:

1. Set META_MODEL_API_KEY (and META_MODEL_API_BASE_URL if the docs give
   a non-default one) in .env.
2. Fill in the endpoint paths and payload/response mapping in chat()
   and generate_image() from the official docs.
3. Flip MODEL_PROVIDER=meta and run the smoke test in docs/MONDAY.md.

Nothing else in the repo changes. That is the point of the interface.
"""

from __future__ import annotations

import json
import os
import urllib.request

from .base import ChatMessage, ChatResponse, ImageResponse, ModelProvider

# TODO (Oct 26): confirm against the official Meta Model API docs.
DEFAULT_BASE_URL = "https://api.meta.com/v1"  # placeholder, verify Monday
CHAT_MODEL_PLACEHOLDER = "muse-spark"  # placeholder, use the real model id
IMAGE_MODEL_PLACEHOLDER = "muse-image"  # placeholder, use the real model id


class MetaModelProvider(ModelProvider):
    name = "meta"
    default_chat_model = CHAT_MODEL_PLACEHOLDER
    default_image_model = IMAGE_MODEL_PLACEHOLDER

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("META_MODEL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "META_MODEL_API_KEY is not set. Add it to .env "
                "(see .env.example) once hackathon API access lands."
            )
        self.base_url = (
            base_url
            or os.environ.get("META_MODEL_API_BASE_URL")
            or DEFAULT_BASE_URL
        ).rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        """POST JSON to the Meta Model API and return parsed JSON.

        TODO (Oct 26): confirm the auth header name and base path from
        the official docs; adjust here only, nowhere else.
        """
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        # TODO (Oct 26): set the real chat endpoint path and map the
        # response fields. Expected shape to fill in:
        #
        #   payload = {
        #       "model": model or self.default_chat_model,
        #       "messages": [{"role": m.role, "content": m.content} for m in messages],
        #       "temperature": temperature,
        #       **({"max_tokens": max_tokens} if max_tokens else {}),
        #   }
        #   raw = self._post("/chat/completions", payload)
        #   return ChatResponse(text=raw[...], model=..., usage=raw.get("usage", {}), raw=raw)
        raise NotImplementedError(
            "Meta Model API chat wiring lands Oct 26. See docs/MONDAY.md."
        )

    def generate_image(
        self,
        prompt: str,
        *,
        model: str | None = None,
    ) -> ImageResponse:
        # TODO (Oct 26): set the real image endpoint path (Muse Image)
        # and map the response. See chat() above for the pattern.
        raise NotImplementedError(
            "Meta Model API image wiring lands Oct 26. See docs/MONDAY.md."
        )
