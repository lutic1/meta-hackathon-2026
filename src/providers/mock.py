"""Deterministic fake provider. Works today, no keys, no network.

Use it to build the whole app before Oct 26. Two modes:

- Default: replies with a canned, clearly-marked mock response.
- Scripted: pass `script=[...]` and each chat() call returns the next
  string in order. Built for tests and for demo rehearsals where you
  want predictable model behavior.
"""

from __future__ import annotations

from .base import ChatMessage, ChatResponse, ImageResponse, ModelProvider


class MockProvider(ModelProvider):
    name = "mock"
    default_chat_model = "mock-chat-1"
    default_image_model = "mock-image-1"

    def __init__(self, script: list[str] | None = None) -> None:
        self._script = list(script) if script else []
        self.calls: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        self.calls.append(list(messages))
        scripted = bool(self._script)
        if scripted:
            text = self._script.pop(0)
        else:
            last_user = next(
                (m.content for m in reversed(messages) if m.role == "user"),
                "",
            )
            text = f"[mock] You said: {last_user!r}. This is a canned response."
        return ChatResponse(
            text=text,
            model=model or self.default_chat_model,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            raw={"provider": self.name, "scripted": scripted},
        )

    def generate_image(
        self,
        prompt: str,
        *,
        model: str | None = None,
    ) -> ImageResponse:
        slug = "-".join(prompt.lower().split()[:5]) or "blank"
        return ImageResponse(
            data=f"mock://image/{slug}",
            model=model or self.default_image_model,
            raw={"provider": self.name, "prompt": prompt},
        )
