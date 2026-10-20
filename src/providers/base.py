"""Model provider interface.

Everything in this project talks to models through this interface only.
Build and test against MockProvider today; swap in MetaModelProvider on
Oct 26 when Meta Model API access lands. No app code changes needed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResponse:
    text: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


@dataclass
class ImageResponse:
    """Result of a text-to-image call (e.g. Muse Image).

    `data` is a URL or a base64 payload, depending on the provider.
    The app layer decides how to store or display it.
    """

    data: str
    model: str
    raw: Any = None


class ModelProvider(ABC):
    """The only surface the app is allowed to depend on."""

    name: str = "base"
    default_chat_model: str = ""
    default_image_model: str = ""

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """Send a conversation, return the assistant's reply."""
        raise NotImplementedError

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        *,
        model: str | None = None,
    ) -> ImageResponse:
        """Generate an image from a text prompt."""
        raise NotImplementedError
