"""`LazyProvider`: a paid adapter built on its role's first call (decisions 61 and 63, AD-5, AD-14).

Wiring hands one to the Build and the live Trickster for each role whose
`PROVIDER_<ROLE>` names a paid host, so a keyless checkout starts and plays
with no paid adapter constructed. The adapter is built once, on the first
`chat`, `segment` or `generate_image`, and reused after; a setting it
refuses at construction (`ValueError`, such as the fallback's base URL or
key unset) fails that call as `ProviderError` `not_configured` naming the
setting, before the guard reserves anything, and is never answered by the
mock.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from pydantic import BaseModel

from src.domain.schema import JobId, SessionId, Stage

from .base import ChatMessage, ChatResponse, ImageResponse, ModelProvider, ProviderError, ReasoningEffort, SegmentResponse


class LazyProvider(ModelProvider):
    """`build` constructs the adapter `kind` names on the first call; a refused build fails that call, and the next one tries again.

    The lock keeps concurrent first calls (segment's labels) to one adapter.
    """

    def __init__(self, kind: str, build: Callable[[], ModelProvider]) -> None:
        self.name = kind
        self._build = build
        self._built: ModelProvider | None = None
        self._lock = threading.Lock()

    @property
    def provider(self) -> ModelProvider:
        """The adapter, built now if this is the role's first call."""
        with self._lock:
            if self._built is None:
                try:
                    self._built = self._build()
                except ValueError as exc:
                    raise ProviderError(None, "not_configured", str(exc)) from None
            return self._built

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
        return self.provider.chat(
            messages, images=images, response_schema=response_schema, reasoning_effort=reasoning_effort, model=model,
            attempt=attempt, job_id=job_id, stage=stage, session_id=session_id,
        )

    def segment(self, label: str, image: bytes, *, job_id: JobId | None = None, stage: Stage | None = None) -> SegmentResponse:
        return self.provider.segment(label, image, job_id=job_id, stage=stage)

    def generate_image(self, prompt: str) -> ImageResponse:
        return self.provider.generate_image(prompt)
