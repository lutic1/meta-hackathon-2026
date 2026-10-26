"""SIT-04: one `muse-image-1.0` image with `n: 1`, billed once and served from the cache on later runs."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from src.domain.ledger import IMAGE_USD_PER_IMAGE
from src.providers.meta_api import IMAGE_MODEL

if TYPE_CHECKING:
    from scripts.sit import Sit

PROMPT = "A small brass key on a wooden desk, soft lamplight, illustration for a clue card."
FIXTURE = "image-sit-clue-card"


def run(sit: Sit) -> str:
    """`CACHE=on`: the first run records an `ImageResponse` and one $0.01 entry; later runs make no call."""
    provider = sit.meta("vision", 0.0, cache=True)
    total, responses = sit.running_total_usd(), len(sit.transport.responses)
    image = provider.generate_image(PROMPT)
    assert image.model == IMAGE_MODEL
    webp = base64.b64decode(image.data)
    assert webp[:4] == b"RIFF" and webp[8:12] == b"WEBP", "the payload is not a webp"
    if len(sit.transport.responses) == responses:
        assert sit.running_total_usd() == total, "a cached image was billed"
        return f"served from the cache, {len(webp)} bytes of webp, no entry"
    sit.record(FIXTURE, model=IMAGE_MODEL)
    spent = sit.running_total_usd() - total
    assert abs(spent - IMAGE_USD_PER_IMAGE) < 1e-9, f"billed {spent:.4f} USD, not {IMAGE_USD_PER_IMAGE:.2f}"
    return f"{len(webp)} bytes of webp, billed {spent:.2f} USD, recorded"
