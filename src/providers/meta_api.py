"""Meta Model API adapter: Muse Spark 1.3 chat, sam-3.1 segmentation and Muse Image 1.0 (AD-5).

Standard tier only. The key comes from `Settings` (AD-14); this module reads
no environment. Every call takes the guarded path (AD-6): the cache first,
then the ledger guard on a miss, priced from the returned usage at the
`budgets.md` rates. Inside one ledger entry the adapter retries at most
once (AD-13), only on what Meta documents as retryable for that endpoint
and on a connect error, waiting `Retry-After` or 0.5 to 1 s of jitter, and
failing at once when that wait would pass what is left of the stage's
budget. Every failure surfaces as `ProviderError`, never an httpx error.
Requests go through one `httpx.Client`; tests pass an `httpx.MockTransport`
that serves recorded fixtures, so no socket opens (AD-17).
"""

from __future__ import annotations

import base64
import random
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from meta_sam_parser import CompletedOutcome, ImageSegmentationResult, decode_mask_to_svg_path, image_segmentation_format
from pydantic import BaseModel

from src.domain.ledger import CallKind, image_cost_usd, sam_cost_usd, spark_cost_usd
from src.domain.masks import area
from src.domain.schema import JobId, Polygon, Stage

from .base import (
    ChatMessage,
    ChatResponse,
    ImageResponse,
    ModelProvider,
    ProviderError,
    ReasoningEffort,
    check_reasoning_effort,
)
from .cache import GuardedCalls, cache_key

type Json = dict[str, Any]

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
CHAT_MODEL = "muse-spark-1.3"
SAM_MODEL = "sam-3.1"
IMAGE_MODEL = "muse-image-1.0"

TIMEOUT = httpx.Timeout(60.0)
SEGMENT_BUDGET_S = 10.0
"""`budgets.md`: the segment stage's 10 s, every label in parallel."""
SEGMENT_TIMEOUT = httpx.Timeout(SEGMENT_BUDGET_S, connect=3.0)
IMAGE_BUDGET_S = 120.0
"""No `budgets.md` row: long enough to wait out a 60 s overload `Retry-After` for a portrait."""


@dataclass(frozen=True)
class RateLimit:
    """A per-team limit from `budgets.md`; the adapter throttles nothing and answers a 429 with its one retry."""

    rpm: int
    tpm: int | None = None


RATE_LIMITS: dict[str, RateLimit] = {
    CHAT_MODEL: RateLimit(rpm=3_000, tpm=4_000_000),
    SAM_MODEL: RateLimit(rpm=3_000),
    IMAGE_MODEL: RateLimit(rpm=150),
}

# AD-13: what Meta documents as retryable per endpoint. Never 502, 504 or an
# undocumented 5xx; a muse-image-1.0 500 is the vendor's non-retryable class.
CHAT_RETRYABLE_STATUS = frozenset({429, 500, 503})
SAM_RETRYABLE_STATUS = frozenset({429, 500, 503})
IMAGE_RETRYABLE_STATUS = frozenset({429, 503})
RETRY_ON_CONNECT = (httpx.ConnectError, httpx.ConnectTimeout)
"""Nothing reached the server, so nothing was billed; a read timeout is never re-sent."""

_SVG_COMMAND = re.compile(r"([MLZ])([^MLZ]*)")


# --- Request pieces ----------------------------------------------------------


def _data_url(jpeg: bytes) -> str:
    """The stored downscaled bytes as sent, never re-encoded: the cache key and the masks use the same bytes."""
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


def _chat_messages(messages: list[ChatMessage], images: list[bytes]) -> list[Json]:
    """Text messages, with the images as `image_url` parts of the last user message, in order."""
    body: list[Json] = [{"role": m.role, "content": m.content} for m in messages]
    if not images:
        return body
    user = next((i for i in range(len(body) - 1, -1, -1) if body[i]["role"] == "user"), None)
    if user is None:
        raise ValueError("images need a user message to travel in")
    parts: list[Json] = [{"type": "text", "text": body[user]["content"]}]
    parts.extend({"type": "image_url", "image_url": {"url": _data_url(image)}} for image in images)
    body[user] = {"role": "user", "content": parts}
    return body


def _response_format(model: type[BaseModel]) -> Json:
    """`json_schema` with `strict: false`, the Meta default that admits AD-2's tagged unions."""
    return {"type": "json_schema", "json_schema": {"name": model.__name__, "schema": model.model_json_schema(), "strict": False}}


# --- Errors and the retry wait -----------------------------------------------


def _http_error(response: httpx.Response) -> ProviderError:
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        error = None
    if not isinstance(error, dict):
        error = {"type": "unparsed" if response.content else "no_body", "message": response.text}
    return ProviderError(response.status_code, error.get("code") or error.get("type") or "unknown", error.get("message") or "")


def _transport_error(exc: httpx.RequestError) -> ProviderError:
    code = "timeout" if isinstance(exc, httpx.TimeoutException) else "transport_error"
    return ProviderError(None, code, str(exc) or type(exc).__name__)


def retry_after_s(headers: Mapping[str, str]) -> float | None:
    """`Retry-After` in seconds, from delta-seconds or an HTTP-date; `None` when absent or unreadable."""
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def retry_wait_s(retry_after: float | None, remaining_s: float) -> float | None:
    """AD-13: `Retry-After`, else 0.5 to 1 s of jitter; `None` (fail at once) past the remaining budget."""
    wait = retry_after if retry_after is not None else 0.5 + random.random() * 0.5
    return wait if wait <= remaining_s else None


# --- sam-3.1 masks to frame polygons -----------------------------------------


def svg_rings(path: str) -> list[Polygon]:
    """The rings of a `meta-sam-parser` SVG path (`M`, `L`, `Z` only), in mask raster coordinates."""
    rings: list[Polygon] = []
    for command, args in _SVG_COMMAND.findall(path):
        if command == "M":
            rings.append([])
        if command in "ML":
            x, y = map(float, args.split())
            rings[-1].append((x, y))
    return rings


def mask_polygon(svg_path: str, bounds: tuple[float, float, float, float], mask_w: int, mask_h: int) -> Polygon | None:
    """The largest ring of one mask, scaled from the raster to the frame pixels its box covers.

    The path puts pixel centers on integers, so `+ 0.5` moves a raster corner
    onto the box edge; `bounds` is the half-open box in frame pixels.
    """
    rings = svg_rings(svg_path)
    if not rings:
        return None
    left, top, right, bottom = bounds
    sx, sy = (right - left) / mask_w, (bottom - top) / mask_h
    ring = max(rings, key=lambda r: abs(area(r)))
    return [(left + (x + 0.5) * sx, top + (y + 0.5) * sy) for x, y in ring]


def polygons_from_result(result: ImageSegmentationResult) -> list[Polygon] | None:
    """One frame-pixel polygon per SAM instance; `None` when SAM found nothing (AD-5)."""
    polygons: list[Polygon] = []
    for record in result.records:
        if record.kind != "mask":
            continue
        bounds = (record.bounds.left, record.bounds.top, record.bounds.right, record.bounds.bottom)
        polygon = mask_polygon(decode_mask_to_svg_path(record.mask), bounds, record.mask.width, record.mask.height)
        if polygon is not None:
            polygons.append(polygon)
    return polygons or None


def _sam_result(raw: Json) -> ImageSegmentationResult:
    """The parsed segmentation of a completed Responses body; anything short of that is a `ProviderError`."""
    status = raw.get("status")
    if status != "completed":
        detail = (raw.get("incomplete_details") or {}).get("reason") or (raw.get("error") or {}).get("message") or ""
        raise ProviderError(200, "incomplete", f"sam-3.1 response {status}: {detail}")
    parts = [part for item in raw.get("output", []) if item.get("type") == "message" for part in item.get("content", [])]
    if any(part.get("type") == "refusal" for part in parts):
        raise ProviderError(200, "refusal", "sam-3.1 refused the prompt")
    parser = image_segmentation_format().create_parser()
    parser.push("".join(part["text"] for part in parts if part.get("type") == "output_text"), emit=False)
    result = parser.finish(CompletedOutcome()).result
    errors = [d for d in result.diagnostics if d.severity == "error"]
    if errors:
        raise ProviderError(200, "malformed", "; ".join(f"line {d.line}: {d.code}" for d in errors))
    return result


# --- The adapter -------------------------------------------------------------


class MetaModelProvider(ModelProvider):
    name = "meta"
    default_chat_model = CHAT_MODEL
    default_image_model = IMAGE_MODEL

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None = None,
        *,
        calls: GuardedCalls,
        chat_kind: CallKind,
        budget_s: float,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """One provider per council role: `chat_kind` prices its chat calls and `budget_s` is its stage budget."""
        if not api_key:
            raise ValueError("META_MODEL_API_KEY is not set. Add it to .env (see .env.example).")
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.chat_kind = chat_kind
        self.budget_s = budget_s
        self._calls = calls
        self._sleep = sleep
        self._clock = clock
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT,
            transport=transport,
        )

    def _post(
        self,
        path: str,
        body: Json,
        *,
        retryable: frozenset[int],
        budget_s: float,
        timeout: httpx.Timeout = TIMEOUT,
    ) -> Json:
        """POST once, and once more after backoff on a retryable status or a connect error (AD-13)."""
        started = self._clock()
        may_retry = True
        while True:
            try:
                response = self.client.post(path, json=body, timeout=timeout)
            except httpx.RequestError as exc:
                error: ProviderError = _transport_error(exc)
                cause: BaseException | None = exc
                retry, after = isinstance(exc, RETRY_ON_CONNECT), None
            else:
                if response.is_success:
                    return response.json()
                error, cause = _http_error(response), None
                retry, after = response.status_code in retryable, retry_after_s(response.headers)
            wait = retry_wait_s(after, budget_s - (self._clock() - started)) if retry and may_retry else None
            if wait is None:
                raise error from cause
            self._sleep(wait)
            may_retry = False

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
    ) -> ChatResponse:
        check_reasoning_effort(reasoning_effort)
        chat_model = model or self.default_chat_model
        key = cache_key(
            chat_model,
            messages=messages,
            response_schema=response_schema,
            reasoning_effort=reasoning_effort,
            images=images,
            attempt=attempt,
        )
        # Sampling stays at the API default, so neither `temperature` nor `max_tokens` is sent.
        body: Json = {
            "model": chat_model,
            "messages": _chat_messages(messages, images),
            "reasoning_effort": reasoning_effort,
        }
        if response_schema is not None:
            body["response_format"] = _response_format(response_schema)

        def call() -> tuple[ChatResponse, float]:
            raw = self._post("/chat/completions", body, retryable=CHAT_RETRYABLE_STATUS, budget_s=self.budget_s)
            choice = raw["choices"][0]
            if choice.get("finish_reason", "stop") != "stop":
                raise ProviderError(200, choice["finish_reason"], "the reply did not finish")
            usage = raw.get("usage", {})
            response = ChatResponse(text=choice["message"]["content"], model=raw.get("model", chat_model), usage=usage, raw=raw)
            return response, spark_cost_usd(usage)

        response, receipt = self._calls.chat(key, self.chat_kind, model=chat_model, call=call, job_id=job_id, stage=stage)
        return replace(response, receipt=receipt)

    def segment(self, label: str, image: bytes) -> list[Polygon] | None:
        """One Responses request with one noun phrase and the stored bytes; polygons in frame pixels, `None` for no mask."""
        key = cache_key(SAM_MODEL, messages=[ChatMessage(role="user", content=label)], images=[image])
        body: Json = {
            "model": SAM_MODEL,
            "input": [{
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": label},
                    {"type": "input_image", "image_url": _data_url(image)},
                ],
            }],
            "store": False,
        }

        def call() -> tuple[list[Polygon] | None, float]:
            raw = self._post(
                "/responses", body, retryable=SAM_RETRYABLE_STATUS, budget_s=SEGMENT_BUDGET_S, timeout=SEGMENT_TIMEOUT
            )
            return polygons_from_result(_sam_result(raw)), sam_cost_usd(1)

        polygons, _ = self._calls.segment(key, model=SAM_MODEL, call=call)
        return polygons

    def generate_image(self, prompt: str) -> ImageResponse:
        key = cache_key(self.default_image_model, messages=[ChatMessage(role="user", content=prompt)])
        body: Json = {
            "model": self.default_image_model,
            "prompt": prompt,
            "n": 1,
            "response_format": "b64_json",
        }

        def call() -> tuple[ImageResponse, float]:
            raw = self._post("/images/generations", body, retryable=IMAGE_RETRYABLE_STATUS, budget_s=IMAGE_BUDGET_S)
            images = raw["data"]
            return ImageResponse(data=images[0]["b64_json"], model=body["model"], raw=raw), image_cost_usd(len(images))

        image, _ = self._calls.generate_image(key, model=body["model"], call=call)
        return image
