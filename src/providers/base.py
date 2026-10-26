"""The `ModelProvider` and `HintPhraser` ports: the only ways to reach a model (AD-5).

Ports are synchronous; the stage runner fans out through a bounded thread
pool, so adapters and the mock stay trivial. Council and pipeline code
receives a provider by injection and never imports an adapter. `HintPhraser`
is a separate port, selected by `GUIDE` alone and implemented only by the
verbatim and the Ollama adapters; its input is exactly the Rung text and the
Derived block (AD-3). `transcribe` joins with its own story; `reconstruct3d`
only if the Tier 2 gate passes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

from src.domain.schema import Derived, GuideModel, Polygon

ReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]
REASONING_EFFORTS: tuple[ReasoningEffort, ...] = ("minimal", "low", "medium", "high", "xhigh")


def check_reasoning_effort(effort: str) -> None:
    """Refuse what Muse Spark refuses with HTTP 400: `none`, or anything outside AD-5's set."""
    if effort not in REASONING_EFFORTS:
        raise ValueError(f"reasoning_effort {effort!r} is not one of {', '.join(REASONING_EFFORTS)}")


class ProviderError(Exception):
    """A hosted call that failed: after the adapter's one retry, or on what is never retried (AD-13).

    `status` is the HTTP status, or `None` when no response came back (a
    transport error or a timeout); `code` is the API's error code or type, or
    the adapter's own name for what went wrong (`timeout`, `transport_error`,
    `retry_wait_s`, `incomplete`, ...).
    """

    def __init__(self, status: int | None, code: str, message: str) -> None:
        super().__init__(f"{status if status is not None else 'transport'} {code}: {message}")
        self.status = status
        self.code = code


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResponse:
    text: str
    """The reply; with a `response_schema`, its JSON for `Model.model_validate_json`."""
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None


@dataclass
class ImageResponse:
    """Result of a text-to-image call (Muse Image).

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
        images: list[bytes] = [],
        response_schema: type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort = "low",
        model: str | None = None,
    ) -> ChatResponse:
        """Send a conversation, with the stored JPEG bytes as its images, and return the reply."""
        raise NotImplementedError

    @abstractmethod
    def segment(self, label: str, image: bytes) -> list[Polygon] | None:
        """One polygon per instance of `label` in frame pixels; `None` when there is no mask."""
        raise NotImplementedError

    @abstractmethod
    def generate_image(self, prompt: str) -> ImageResponse:
        """Generate an image from a text prompt."""
        raise NotImplementedError


@dataclass
class PhraserResponse:
    """A Rung or Greeting line, with what the caller records about how it was worded."""

    text: str
    phrased: bool
    """False when the line is shown as written (the verbatim adapter, or a fallback to it)."""
    latency_ms: int


class HintPhraser(ABC):
    """The Guide port: rewords a Rung or greets from the Derived block, and sees nothing else (AD-3, AD-5)."""

    name: str = "base"
    guide_model: GuideModel | None = None
    """What `GET /meta` reports as `guide_model`; null when no Guide model runs."""

    @abstractmethod
    def phrase(self, rung_text: str, derived: Derived) -> PhraserResponse:
        """Reword `rung_text` in the Guide's voice without adding content; the input is exactly these two."""
        raise NotImplementedError

    @abstractmethod
    def greet(self, derived: Derived) -> PhraserResponse:
        """The returning player's Greeting from the Derived block alone, naming no object or solution."""
        raise NotImplementedError
