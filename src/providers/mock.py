"""Scripted mock adapter: one per council role, no keys, no network (AD-5, AD-17).

`MockProvider(role)` answers every call with a canned, clearly marked reply.
`MockProvider(role, script=MockScript(...))` answers each call kind from that
role's script in order and raises once a kind runs out, so a test is never
served a reply it did not write. The mock bypasses the cache and the ledger
(AD-6) and refuses `reasoning_effort='none'` like the real API.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from src.domain.schema import JobId, Polygon, Role, SessionId, Stage

from .base import (
    ChatMessage,
    ChatResponse,
    ImageResponse,
    ModelProvider,
    ReasoningEffort,
    SegmentResponse,
    check_reasoning_effort,
)

CANNED_POLYGON: Polygon = [(0.0, 0.0), (64.0, 0.0), (64.0, 64.0), (0.0, 64.0)]


@dataclass
class MockScript:
    """Replies per call kind, served in order; a `segment` entry of `None` stands for no mask."""

    chat: list[str] = field(default_factory=list)
    segment: list[list[Polygon] | None] = field(default_factory=list)
    image: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChatCall:
    messages: list[ChatMessage]
    images: list[bytes]
    response_schema: type[BaseModel] | None
    reasoning_effort: str
    model: str | None
    attempt: int = 0
    job_id: JobId | None = None
    stage: Stage | None = None


@dataclass(frozen=True)
class SegmentCall:
    label: str
    image: bytes


@dataclass(frozen=True)
class ImageCall:
    prompt: str


class MockProvider(ModelProvider):
    name = "mock"
    default_chat_model = "mock-chat-1"
    default_image_model = "mock-image-1"

    def __init__(self, role: Role, script: MockScript | None = None) -> None:
        self.role = role
        self._script = script
        self.calls: list[ChatCall | SegmentCall | ImageCall] = []

    def _next[T](self, kind: str, replies: list[T]) -> T:
        if not replies:
            raise LookupError(f"the mock {self.role} script has no {kind} reply left")
        return replies.pop(0)

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        images: list[bytes] = [],
        response_schema: type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort = "low",
        model: str | None = None,
        attempt: int = 0,
        job_id: JobId | None = None,
        stage: Stage | None = None,
        session_id: SessionId | None = None,
    ) -> ChatResponse:
        check_reasoning_effort(reasoning_effort)
        self.calls.append(ChatCall(list(messages), list(images), response_schema, reasoning_effort, model, attempt, job_id, stage))
        if self._script is not None:
            text = self._next("chat", self._script.chat)
        else:
            last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
            text = f"[mock {self.role}] You said: {last_user!r}. This is a canned response."
        return ChatResponse(
            text=text,
            model=model or self.default_chat_model,
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            raw={"provider": self.name, "role": self.role, "scripted": self._script is not None},
        )

    def segment(self, label: str, image: bytes, *, job_id: JobId | None = None, stage: Stage | None = None) -> SegmentResponse:
        self.calls.append(SegmentCall(label, image))
        if self._script is not None:
            return SegmentResponse(self._next("segment", self._script.segment))
        return SegmentResponse([list(CANNED_POLYGON)])

    def generate_image(self, prompt: str) -> ImageResponse:
        self.calls.append(ImageCall(prompt))
        if self._script is not None:
            data = self._next("image", self._script.image)
        else:
            slug = "-".join(prompt.lower().split()[:5]) or "blank"
            data = f"mock://image/{slug}"
        return ImageResponse(
            data=data,
            model=self.default_image_model,
            raw={"provider": self.name, "role": self.role, "prompt": prompt},
        )
