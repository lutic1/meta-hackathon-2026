"""Doubles for the architect and segment stage tests: scripted candidates, a counting segmenter and a Build over the real stages."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel

from src.domain.schema import GridBox, Polygon
from src.infra.clocks import BuildClock
from src.pipeline.architect import architect_stage
from src.pipeline.build import Build
from src.pipeline.ports import ArtifactStore, JobStore
from src.pipeline.segment import segment_stage
from src.providers.base import ChatMessage, ChatResponse, ImageResponse, ModelProvider, ReasoningEffort
from src.providers.mock import MockProvider, MockScript
from tests.infra.test_clocks import Ticker
from tests.pipeline.test_build import Doubles

GRID_BOX: GridBox = (100, 100, 300, 300)
"""On a 1280 by 960 frame: pixels 128, 96 to 384, 288."""


def candidate(
    label: str,
    *,
    photo: int = 0,
    box: GridBox = GRID_BOX,
    confidence: float = 0.9,
    plural: bool = False,
    attributes: list[str] | None = None,
) -> dict[str, Any]:
    return {"label": label, "plural": plural, "photo": photo, "box": list(box), "attributes": attributes or [], "confidence": confidence}


def labels(count: int, *, photo: Callable[[int], int] = lambda i: i % 6) -> list[dict[str, Any]]:
    """`count` candidates `object 0` to `object n`, confidence falling with the index, spread over the photos."""
    return [candidate(f"object {i}", photo=photo(i), confidence=round(0.99 - i * 0.01, 2)) for i in range(count)]


def architect_mock(candidates: list[dict[str, Any]]) -> MockProvider:
    """The `architect` role's mock, scripted with one `ArchitectResponse` reply."""
    return MockProvider("architect", MockScript(chat=[json.dumps({"candidates": candidates})]))


def square(x0: float, y0: float, x1: float, y1: float) -> Polygon:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


class Segmenter(ModelProvider):
    """A `segment` port keyed by label that counts the calls in flight; with `hold`, each call waits until that many are in."""

    name = "mock"

    def __init__(
        self,
        masks: Mapping[str, list[Polygon] | None] | None = None,
        *,
        raises: Mapping[str, Exception] | None = None,
        on_call: Callable[[], None] | None = None,
        hold: int = 0,
    ) -> None:
        self.masks = dict(masks or {})
        self.raises = dict(raises or {})
        self.on_call = on_call
        self.hold = hold
        self.calls: list[tuple[str, bytes]] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self._lock = threading.Lock()
        self._gate = threading.Event()
        if hold == 0:
            self._gate.set()

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        images: list[bytes] = [],
        response_schema: type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort = "low",
        model: str | None = None,
    ) -> ChatResponse:
        raise AssertionError("the segment stage makes no chat call")

    def segment(self, label: str, image: bytes) -> list[Polygon] | None:
        with self._lock:
            self.calls.append((label, image))
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            if self.in_flight >= self.hold:
                self._gate.set()
            if self.on_call is not None:
                self.on_call()
        try:
            self._gate.wait(timeout=5)
            if label in self.raises:
                raise self.raises[label]
            return self.masks.get(label)
        finally:
            with self._lock:
                self.in_flight -= 1

    def generate_image(self, prompt: str) -> ImageResponse:
        raise AssertionError("the segment stage makes no image call")


def build_over(
    jobs: JobStore,
    artifacts: ArtifactStore,
    ticker: Ticker,
    doubles: Doubles,
    *,
    architect: ModelProvider,
    segmenter: ModelProvider,
) -> Build:
    """A Build running the real architect and segment stages over the given ports, and the doubles after them."""
    stages = doubles.stages()
    stages["architect"] = architect_stage(architect, artifacts)
    stages["segment"] = segment_stage(segmenter, artifacts)
    return Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=2)
