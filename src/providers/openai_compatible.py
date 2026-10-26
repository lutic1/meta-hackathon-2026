"""OpenAI-compatible adapter: the Riddler fallback on Baseten or Fireworks (AD-5, AD-6, AD-13).

`OPENAI_COMPATIBLE_BASE_URL` picks the host and `OPENAI_COMPATIBLE_API_KEY`
signs the requests, both from `Settings` (AD-14); this module reads no
environment. `chat` is the only call it serves: no fallback host runs
`segment` or `generate_image`. Every call goes through `GuardedCalls`
(the cache, then the ledger guard on a miss) and `post_with_retry` (one
retry with backoff on 429, 500, 503 or a connect error, inside that one
ledger entry; never on 502, 504, another 5xx or a read timeout), and is
priced from the returned usage at the Spark rates in `domain/ledger.py`,
the only documented ones.

`json_mode` is how a `response_schema` travels. `json_schema` sends
`strict_schema(model)` as `response_format` with `strict: true`, which
Baseten fixes. `plain` is for a host that does not honor it: the prompt
asks for the JSON and no `response_format` is sent, so a reply that does
not parse is the caller's parse failure, which the regeneration loop
counts; the adapter adds no loop of its own. The body carries the
messages it is given and nothing else: a solution, a `derived` block or
a profile field never enters here (AD-3). Wiring switches the `riddler`
role to it in 2.12; the Trickster fallback reuses it in 4.8.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from src.domain.ledger import CallKind, spark_cost_usd
from src.domain.schema import Polygon, strict_schema

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

BASETEN_MODEL = "meta-models/muse-spark-open"
"""Muse Spark Open on Baseten, the documented Riddler fallback; wiring passes the role's model id."""
MAX_TOKENS = 16384
"""Reasoning plus visible output; Baseten defaults `max_tokens` to 4096, so it is always sent."""
RIDDLER_BUDGET_S = 45.0
"""The Riddler row of budgets.md: what a retry wait must fit in."""
TIMEOUT_S = 60.0
RETRYABLE_STATUS = frozenset({429, 500, 503})
"""AD-13: the documented retryable set; never 502, 504 or another 5xx."""
RETRY_ON_CONNECT = (httpx.ConnectError, httpx.ConnectTimeout)
"""Nothing reached the host, so nothing was billed; a read timeout is never re-sent."""

JsonMode = Literal["json_schema", "plain"]

PLAIN_JSON_ASK = (
    "Answer with one JSON object that matches this JSON Schema, and nothing else: no prose, no code fence.\n"
)


# --- One retry with backoff (AD-13) -----------------------------------------


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


def _retry_wait_s(retry_after: float | None, remaining_s: float) -> float | None:
    """`Retry-After`, else 0.5 to 1 s of jitter; `None` (fail at once) when it passes the remaining budget."""
    wait = retry_after if retry_after is not None else 0.5 + random.random() * 0.5
    return wait if wait <= remaining_s else None


def provider_error(response: httpx.Response) -> ProviderError:
    """The typed error for a failed response: the vendor envelope's `type`, else `unparsed` or `no_body`."""
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        error = None
    if not isinstance(error, dict):
        error = {"type": "unparsed" if response.content else "no_body", "message": response.text}
    return ProviderError(response.status_code, error.get("type") or "unknown", error.get("message") or "")


def transport_error(exc: httpx.RequestError) -> ProviderError:
    kind = "timeout" if isinstance(exc, httpx.TimeoutException) else "transport_error"
    return ProviderError(None, kind, str(exc) or type(exc).__name__)


def post_with_retry(
    client: httpx.Client,
    path: str,
    body: dict[str, Any],
    *,
    retryable: frozenset[int],
    budget_s: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> httpx.Response:
    """POST once, and once more after backoff on a status in `retryable` or a connect error.

    The wait is `Retry-After` or 0.5 to 1 s of jitter; past what is left
    of `budget_s` the call fails at once. Raises `ProviderError`, never an
    httpx error.
    """
    started = clock()
    for attempt in (0, 1):
        try:
            response = client.post(path, json=body)
        except httpx.RequestError as exc:
            error, cause = transport_error(exc), exc
            retry, after = isinstance(exc, RETRY_ON_CONNECT), None
        else:
            if response.status_code < 400:
                return response
            error, cause = provider_error(response), None
            retry, after = response.status_code in retryable, retry_after_s(response.headers)
        wait = _retry_wait_s(after, budget_s - (clock() - started)) if retry and attempt == 0 else None
        if wait is None:
            raise error from cause
        sleep(wait)
    raise AssertionError("unreachable")


# --- The adapter -------------------------------------------------------------


class OpenAICompatibleProvider(ModelProvider):
    name = "openai_compatible"
    default_chat_model = BASETEN_MODEL

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None,
        calls: GuardedCalls,
        *,
        model: str | None = None,
        kind: CallKind = "riddler",
        json_mode: JsonMode = "json_schema",
        max_tokens: int = MAX_TOKENS,
        budget_s: float = RIDDLER_BUDGET_S,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """`calls` is the role's guarded path (AD-6); `kind` names its ledger entries; `budget_s` bounds a retry wait."""
        if not base_url:
            raise ValueError("OPENAI_COMPATIBLE_BASE_URL is not set. Add it to .env (see .env.example).")
        if not api_key:
            raise ValueError("OPENAI_COMPATIBLE_API_KEY is not set. Add it to .env (see .env.example).")
        self.base_url = base_url.rstrip("/")
        self.default_chat_model = model or BASETEN_MODEL
        self.kind: CallKind = kind
        self.json_mode: JsonMode = json_mode
        self.max_tokens = max_tokens
        self.budget_s = budget_s
        self._calls = calls
        self._sleep = sleep
        self._clock = clock
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT_S,
            transport=transport,
        )

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        images: list[bytes] = [],
        response_schema: type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort = "low",
        model: str | None = None,
    ) -> ChatResponse:
        check_reasoning_effort(reasoning_effort)
        if images:
            raise ValueError("no fallback role sends images; the openai_compatible adapter is text only")
        chat_model = model or self.default_chat_model
        sent = self._messages(messages, response_schema)
        body: dict[str, Any] = {
            "model": chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in sent],
            "reasoning_effort": reasoning_effort,
            "max_tokens": self.max_tokens,
        }
        if response_schema is not None and self.json_mode == "json_schema":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "schema": strict_schema(response_schema),
                    "strict": True,
                },
            }
        key = cache_key(chat_model, messages=sent, response_schema=response_schema, reasoning_effort=reasoning_effort)
        response, _ = self._calls.chat(key, self.kind, model=chat_model, call=lambda: self._post(body))
        return response

    def _messages(self, messages: list[ChatMessage], response_schema: type[BaseModel] | None) -> list[ChatMessage]:
        """The messages as given; in plain-JSON mode the system message also asks for the schema's JSON."""
        if response_schema is None or self.json_mode == "json_schema":
            return list(messages)
        ask = PLAIN_JSON_ASK + json.dumps(strict_schema(response_schema), separators=(",", ":"))
        if messages and messages[0].role == "system":
            return [ChatMessage("system", f"{messages[0].content}\n\n{ask}"), *messages[1:]]
        return [ChatMessage("system", ask), *messages]

    def _post(self, body: dict[str, Any]) -> tuple[ChatResponse, float]:
        """The priced call: one POST with its one retry, the reply and its cost from the returned usage."""
        response = post_with_retry(
            self.client, "/chat/completions", body,
            retryable=RETRYABLE_STATUS, budget_s=self.budget_s, sleep=self._sleep, clock=self._clock,
        )
        raw = response.json()
        choice = raw["choices"][0]
        finish_reason = choice.get("finish_reason", "stop")
        if finish_reason != "stop":
            raise ProviderError(response.status_code, finish_reason, "the reply ended before its end")
        if "usage" not in raw:
            raise ProviderError(response.status_code, "no_usage", "the reply carries no usage, so it cannot be priced")
        reply = ChatResponse(
            text=choice["message"]["content"],
            model=raw.get("model", body["model"]),
            usage=raw["usage"],
            raw=raw,
        )
        return reply, spark_cost_usd(raw["usage"])

    def segment(self, label: str, image: bytes) -> list[Polygon] | None:
        raise NotImplementedError("no fallback host serves segment; sam-3.1 runs on the meta adapter only")

    def generate_image(self, prompt: str) -> ImageResponse:
        raise NotImplementedError("no fallback host serves generate_image; muse-image-1.0 runs on the meta adapter only")
