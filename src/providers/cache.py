"""The model-call cache in front of the ledger guard (AD-6): key logic over the `Cache` port.

`cache_key` is `sha256(model id || schema hash || full prompt including the
system message || reasoning_effort || sha256 of each image in order ||
attempt)`; text-only calls omit the image segment and `attempt` defaults to
0, so a Regeneration (attempt n) is never served attempt n-1's answer.
`GuardedCalls` is the path every hosted adapter call takes, for `chat`,
`segment` and `generate_image` alike: a hit returns before the guard runs
and is never priced or refused; a miss is guarded and priced exactly once,
then stored under its key. With `CACHE=off` the cache is neither read nor
written and every call passes the guard. Each call returns its
`CallReceipt` (cached or billed, model id, host, spend) so the stage can
write its call row (AD-16). The mock provider bypasses this module and the
ledger alike.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from pydantic import BaseModel

from src.domain.ledger import CallKind
from src.domain.schema import JobId, Polygon, SessionId, Stage
from src.pipeline.ports import Cache

from .base import CallReceipt, ChatMessage, ChatResponse, ImageResponse, ReasoningEffort
from .spend import SpendLedger, new_call_id

type Json = dict[str, Any]


def schema_hash(model: type[BaseModel] | None) -> str:
    """sha256 of the model's JSON Schema in canonical form; empty when the call carries no schema."""
    if model is None:
        return ""
    canonical = json.dumps(model.model_json_schema(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _digest(parts: Iterable[str]) -> str:
    """sha256 over length-prefixed parts, so no part can run into its neighbour."""
    digest = hashlib.sha256()
    for part in parts:
        data = part.encode()
        digest.update(f"{len(data)}:".encode())
        digest.update(data)
    return digest.hexdigest()


def cache_key(
    model: str,
    *,
    messages: Sequence[ChatMessage],
    response_schema: type[BaseModel] | None = None,
    reasoning_effort: ReasoningEffort | None = None,
    images: Sequence[bytes] = (),
    attempt: int = 0,
) -> str:
    """The AD-6 key; `segment` keys on its label and image, `generate_image` on its prompt alone."""
    prompt = json.dumps([[m.role, m.content] for m in messages], ensure_ascii=False, separators=(",", ":"))
    parts = [model, schema_hash(response_schema), prompt, reasoning_effort or ""]
    parts.extend(hashlib.sha256(image).hexdigest() for image in images)
    parts.append(str(attempt))
    return _digest(parts)


def _encode_chat(response: ChatResponse) -> Json:
    return {"text": response.text, "model": response.model, "usage": response.usage, "raw": response.raw}


def _decode_chat(value: Json) -> ChatResponse:
    return ChatResponse(text=value["text"], model=value["model"], usage=value["usage"], raw=value["raw"])


def _encode_image(response: ImageResponse) -> Json:
    return {"data": response.data, "model": response.model, "raw": response.raw}


def _decode_image(value: Json) -> ImageResponse:
    return ImageResponse(data=value["data"], model=value["model"], raw=value["raw"])


def _encode_polygons(polygons: list[Polygon] | None) -> Json:
    return {"polygons": None if polygons is None else [[list(point) for point in polygon] for polygon in polygons]}


def _decode_polygons(value: Json) -> list[Polygon] | None:
    polygons = value["polygons"]
    return None if polygons is None else [[(float(x), float(y)) for x, y in polygon] for polygon in polygons]


class GuardedCalls:
    """Cache first, then the ledger guard on a miss only; `host` names where the billed calls run."""

    def __init__(self, cache: Cache, ledger: SpendLedger, *, host: str, enabled: bool = True) -> None:
        """`enabled` is `CACHE=on`; off bypasses the cache, never the ledger."""
        self._cache = cache
        self._ledger = ledger
        self.host = host
        self.enabled = enabled

    def chat(
        self,
        key: str,
        kind: CallKind,
        *,
        model: str,
        call: Callable[[], tuple[ChatResponse, float]],
        job_id: JobId | None = None,
        stage: Stage | None = None,
        session_id: SessionId | None = None,
    ) -> tuple[ChatResponse, CallReceipt]:
        return self._call(key, kind, model, call, _encode_chat, _decode_chat, job_id, stage, session_id)

    def segment(
        self,
        key: str,
        *,
        model: str,
        call: Callable[[], tuple[list[Polygon] | None, float]],
        job_id: JobId | None = None,
        stage: Stage | None = None,
        session_id: SessionId | None = None,
    ) -> tuple[list[Polygon] | None, CallReceipt]:
        return self._call(key, "sam", model, call, _encode_polygons, _decode_polygons, job_id, stage, session_id)

    def generate_image(
        self,
        key: str,
        *,
        model: str,
        call: Callable[[], tuple[ImageResponse, float]],
        job_id: JobId | None = None,
        stage: Stage | None = None,
        session_id: SessionId | None = None,
    ) -> tuple[ImageResponse, CallReceipt]:
        return self._call(key, "image", model, call, _encode_image, _decode_image, job_id, stage, session_id)

    def _call[T](
        self,
        key: str,
        kind: CallKind,
        model: str,
        call: Callable[[], tuple[T, float]],
        encode: Callable[[T], Json],
        decode: Callable[[Json], T],
        job_id: JobId | None,
        stage: Stage | None,
        session_id: SessionId | None,
    ) -> tuple[T, CallReceipt]:
        """`call` makes the priced call and returns the response with its observed cost in USD.

        A call that raises keeps its reserved entry, as the host may still
        have billed it, and stores nothing.
        """
        if self.enabled and (cached := self._cache.get(key)) is not None:
            return decode(cached), CallReceipt(new_call_id(), model, self.host, cached=True, spend_usd=0.0)
        call_id = self._ledger.guard(kind, job_id=job_id, stage=stage, session_id=session_id)
        response, usd = call()
        settled = self._ledger.settle(call_id, usd)
        if self.enabled:
            self._cache.put(key, encode(response))
        return response, CallReceipt(call_id, model, self.host, cached=False, spend_usd=settled.usd)
