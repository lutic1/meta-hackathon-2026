"""SIT-02: one `sam-3.1` segment on a present label and one on an absent label, both recorded."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.domain.schema import ArchitectResponse
from src.providers.meta_api import CHAT_MODEL, SAM_MODEL, SEGMENT_BUDGET_S

if TYPE_CHECKING:
    from scripts.sit import Sit

ARCHITECT_FIXTURE = "chat-architect-two-photos"
"""The Architect case's recording: its surest candidate is the known-present label, on its photo."""
ABSENT_LABEL = "a live penguin"


def run(sit: Sit) -> str:
    """`CACHE=off`: the present label must give at least one polygon inside the frame, the absent one `None`."""
    recorded = sit.recorded(ARCHITECT_FIXTURE, model=CHAT_MODEL)
    architect = ArchitectResponse.model_validate_json(recorded["choices"][0]["message"]["content"])
    candidate = max(architect.candidates, key=lambda c: c.confidence)
    photo = sit.photos(candidate.photo + 1)[candidate.photo]
    provider = sit.meta("vision", SEGMENT_BUDGET_S, cache=False)

    started = time.monotonic()
    polygons = provider.segment(candidate.label, photo)
    latency = time.monotonic() - started
    sit.record("segment-present-label", model=SAM_MODEL)
    assert polygons, f"no mask for the present label {candidate.label!r}"
    assert all(len(polygon) >= 3 and all(x >= 0 and y >= 0 for x, y in polygon) for polygon in polygons), "a polygon left the frame"

    absent = provider.segment(ABSENT_LABEL, photo)
    sit.record("segment-absent-label", model=SAM_MODEL)
    assert absent is None, f"{ABSENT_LABEL!r} gave {len(absent)} mask(s)"
    overrun = f"; over the {SEGMENT_BUDGET_S:.0f} s budget" if latency > SEGMENT_BUDGET_S else ""
    return f"{candidate.label!r}: {len(polygons)} polygon(s) in {latency:.1f} s{overrun}; {ABSENT_LABEL!r}: none"
