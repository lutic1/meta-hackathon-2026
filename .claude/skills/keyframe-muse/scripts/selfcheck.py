"""Offline self-check for the keyframe-muse skill. No network, no keys.

Asserts the pinned versions, builds the Muse Spark and Muse Image request
bodies the skill documents, checks the strict-schema transform, and drives
the AD-13 retry policy against httpx.MockTransport.

    uv run --no-project --with httpx==0.28.1 --with pydantic==2.14.1 \
        python .claude/skills/keyframe-muse/scripts/selfcheck.py
"""

from __future__ import annotations

import base64
import json
import random
import re
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from importlib.metadata import version
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field

PINS = {"httpx": "0.28.1", "pydantic": "2.14.1"}
BASE_URL = "https://api.meta.ai/v1"
CHAT_MODEL = "muse-spark-1.3"
IMAGE_MODEL = "muse-image-1.0"
EFFORTS = {"low", "medium"}
REJECTED_CHAT_PARAMS = {"max_output_tokens", "stop", "logprobs", "logit_bias",
                        "verbosity", "prediction", "modalities", "audio", "text"}
# AD-13: each endpoint declares what Meta documents as retryable. Never 502, 504 or an
# undocumented 5xx; a muse-image-1.0 500 is the vendor's non-retryable class.
CHAT_RETRYABLE_STATUS = frozenset({429, 500, 503})
IMAGE_RETRYABLE_STATUS = frozenset({429, 503})
RETRY_ON_CONNECT = (httpx.ConnectError, httpx.ConnectTimeout)  # nothing was sent, so nothing was billed
# Seconds left in the stage budget when a call starts (budgets.md); the Trickster and
# portraits have no budget there, so these two are Keyframe choices.
BUDGET_S = {"architect": 15.0, "riddler": 45.0, "dryrun": 30.0, "trickster": 30.0, "image": 120.0}
SCHEMA_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ProviderError(Exception):
    def __init__(self, status: int | None, kind: str, message: str) -> None:
        super().__init__(f"{status} {kind}: {message}")
        self.status, self.kind = status, kind


# Shapes in the style of src/domain/schema.py (AD-2, AD-12, AD-18).
class ArchitectObject(BaseModel):
    label: str
    photo: int
    box: list[int]  # [x0, y0, x1, y1] on the 0..1000 grid; clamp in code
    attributes: list[str]
    instances: int
    confidence: float


class ArchitectResponse(BaseModel):
    objects: list[ArchitectObject]


class CodeSolution(BaseModel):
    lock_type: Literal["code"]
    code: str


class FindSolution(BaseModel):
    lock_type: Literal["find"]
    target: str


Solution = Annotated[CodeSolution | FindSolution, Field(discriminator="lock_type")]


class DryRunAnswer(BaseModel):
    puzzle_id: str
    answer: Solution


class DryRunAnswers(BaseModel):
    """AD-12: a list of {puzzle_id, answer}, never a map, so strict mode can express it."""

    answers: list[DryRunAnswer]


class MapShaped(BaseModel):
    """What AD-2 forbids in a model-response schema: a map-typed field."""

    answers: dict[str, Solution]


def strict_schema(model: type[BaseModel]) -> dict:
    """Inline $defs, oneOf -> anyOf, close every object, require every key."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        node = dict(node)
        if "$ref" in node:
            target = defs[node.pop("$ref").rsplit("/", 1)[1]]
            node = {**target, **node}
        node.pop("discriminator", None)
        if "oneOf" in node:
            node["anyOf"] = node.pop("oneOf")
        if isinstance(node.get("additionalProperties"), dict):
            raise ValueError("map-typed field cannot be strict; use a list or fixed keys (AD-2)")
        out = {k: walk(v) for k, v in node.items() if k != "properties"}
        if "properties" in node:
            out["properties"] = {k: walk(v) for k, v in node["properties"].items()}
        if out.get("type") == "object":
            out["additionalProperties"] = False
            out["required"] = list(out.get("properties", {}))
        return out

    return walk(schema)


def response_format(model: type[BaseModel], *, strict: bool) -> dict:
    schema = strict_schema(model) if strict else model.model_json_schema()
    return {"type": "json_schema",
            "json_schema": {"name": model.__name__, "schema": schema, "strict": strict}}


def data_url(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")


def chat_body(system: str, user: str, images: list[bytes], schema: type[BaseModel],
              effort: str, max_completion_tokens: int, *, strict: bool = False) -> dict:
    content = [{"type": "text", "text": user}]
    content += [{"type": "image_url", "image_url": {"url": data_url(b)}} for b in images]
    return {
        "model": CHAT_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": content}],
        "response_format": response_format(schema, strict=strict),
        "reasoning_effort": effort,
        "max_completion_tokens": max_completion_tokens,
    }


def image_body(prompt: str) -> dict:
    return {"model": IMAGE_MODEL, "prompt": prompt, "n": 1,
            "response_format": "b64_json", "output_format": "webp"}


def retry_after_s(headers: Mapping[str, str]) -> float | None:
    """Retry-After in seconds, from delta-seconds or an HTTP-date; None when absent or unreadable."""
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
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def retry_wait_s(retry_after: float | None, remaining_s: float) -> float | None:
    """AD-13: Retry-After, else 0.5 to 1 s of jitter; None (fail at once) past the remaining budget."""
    wait = retry_after if retry_after is not None else 0.5 + random.random() * 0.5
    return wait if wait <= remaining_s else None


def provider_error(response: httpx.Response) -> ProviderError:
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        error = None
    if not isinstance(error, dict):
        error = {"type": "unparsed" if response.content else "no_body", "message": response.text}
    return ProviderError(response.status_code, error.get("type") or "unknown",
                         error.get("message") or "")


def transport_error(exc: httpx.RequestError) -> ProviderError:
    kind = "timeout" if isinstance(exc, httpx.TimeoutException) else "transport_error"
    return ProviderError(None, kind, str(exc) or type(exc).__name__)


def post_with_retry(client: httpx.Client, path: str, body: dict, *, retryable: frozenset[int],
                    budget_s: float, sleep: Callable[[float], None] = time.sleep,
                    clock: Callable[[], float] = time.monotonic) -> httpx.Response:
    """AD-13: at most one retry with backoff. Raises ProviderError, never an httpx error.

    Retries a status in `retryable` or a connect error, after Retry-After or 0.5 to 1 s of
    jitter, unless that wait is longer than what is left of `budget_s`. A read timeout is
    never re-sent: the server may still be generating, and billing.
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
        wait = retry_wait_s(after, budget_s - (clock() - started)) if retry and attempt == 0 else None
        if wait is None:
            raise error from cause
        sleep(wait)
    raise AssertionError("unreachable")


def chat_cost_usd(usage: dict) -> float:
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    fresh = usage["prompt_tokens"] - cached
    return (fresh * 1.25 + cached * 0.15 + usage["completion_tokens"] * 4.25) / 1_000_000


# Checks ---------------------------------------------------------------------

def check_strict_subset(schema: dict) -> None:
    assert not {"anyOf", "oneOf", "allOf", "enum", "not"} & schema.keys(), "root"
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
            continue
        if not isinstance(node, dict):
            continue
        assert "oneOf" not in node and "allOf" not in node and "$ref" not in node
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert sorted(node["required"]) == sorted(node.get("properties", {}))
        stack.extend(node.values())


def mock_client(responses: list, seen: list[httpx.Request]) -> httpx.Client:
    """Each item is an httpx.Response to return or an httpx exception class to raise."""
    queue = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        item = next(queue)
        if isinstance(item, type):
            raise item("simulated", request=request)
        return item

    return httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler),
                        headers={"Authorization": "Bearer test-not-a-key"})


def error(status: int, kind: str, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status, headers=headers,
                          json={"error": {"message": kind, "type": kind, "param": None, "code": None}})


def clock_at(*readings: float) -> Callable[[], float]:
    """A fake monotonic clock that returns the given readings in order."""
    values = iter(readings)
    return lambda: next(values)


def run(responses, body, path="/chat/completions", retryable=CHAT_RETRYABLE_STATUS,
        budget_s=BUDGET_S["architect"], **options):
    seen, waits = [], []
    with mock_client(responses, seen) as client:
        try:
            result = post_with_retry(client, path, body, retryable=retryable, budget_s=budget_s,
                                     sleep=waits.append, **options)
        except ProviderError as exc:
            result = exc
    return result, seen, waits


def failed(result, status: int | None, requests: int, seen: list) -> bool:
    return isinstance(result, ProviderError) and result.status == status and len(seen) == requests


def main() -> None:
    for package, pinned in PINS.items():
        assert version(package) == pinned, f"{package} {version(package)} != {pinned}"
    print(f"pins ok: httpx {version('httpx')}, pydantic {version('pydantic')}")

    jpeg = b"\xff\xd8\xff\xe0fake-jpeg\xff\xd9"
    body = chat_body("You list objects.", "List the objects.", [jpeg, jpeg],
                     ArchitectResponse, "low", 16384)
    request = httpx.Request("POST", f"{BASE_URL}/chat/completions", json=body)
    sent = json.loads(request.content)
    assert request.url.path == "/v1/chat/completions"
    assert not REJECTED_CHAT_PARAMS & sent.keys() and sent.get("n", 1) == 1
    assert sent["reasoning_effort"] in EFFORTS and sent["model"] == CHAT_MODEL
    assert isinstance(sent["messages"][0]["content"], str), "system message is text only"
    parts = sent["messages"][1]["content"]
    assert [p["type"] for p in parts] == ["text", "image_url", "image_url"]
    assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    fmt = sent["response_format"]["json_schema"]
    assert SCHEMA_NAME.match(fmt["name"]) and fmt["strict"] is False
    print("chat body ok: images only in the user message, strict false, no rejected params")

    for model in (ArchitectResponse, DryRunAnswers):
        check_strict_subset(response_format(model, strict=True)["json_schema"]["schema"])
    assert "oneOf" in json.dumps(DryRunAnswers.model_json_schema()), "pydantic emits oneOf"
    answer = DryRunAnswers.model_validate_json(
        '{"answers": [{"puzzle_id": "p1", "answer": {"lock_type": "code", "code": "0412"}}]}')
    assert isinstance(answer.answers[0].answer, CodeSolution)
    try:
        strict_schema(MapShaped)
        raise AssertionError("map field accepted as strict")
    except ValueError:
        pass
    print("strict_schema ok: DryRunAnswers as a list of {puzzle_id, answer} fits the strict "
          "subset (oneOf rewritten to anyOf); a map-typed field is refused")

    img = json.loads(httpx.Request("POST", f"{BASE_URL}/images/generations",
                                   json=image_body("a portrait")).content)
    assert img["model"] == IMAGE_MODEL and "seed" not in img and 1 <= img["n"] <= 10
    print("image body ok: muse-image-1.0, b64_json, no seed")

    assert CHAT_RETRYABLE_STATUS == {429, 500, 503} and IMAGE_RETRYABLE_STATUS == {429, 503}
    assert RETRY_ON_CONNECT == (httpx.ConnectError, httpx.ConnectTimeout)
    print("AD-13 sets ok: chat 429, 500, 503; image 429, 503; connect errors ConnectError, ConnectTimeout")

    content = json.dumps({"objects": [{"label": "lamp", "photo": 0, "box": [10, 20, 300, 1001],
                                       "attributes": ["brass"], "instances": 1,
                                       "confidence": 0.9}]})
    usage = {"prompt_tokens": 3000, "completion_tokens": 900, "total_tokens": 3900,
             "prompt_tokens_details": {"cached_tokens": 1000},
             "completion_tokens_details": {"reasoning_tokens": 600}}
    ok = httpx.Response(200, json={"choices": [{"index": 0, "finish_reason": "stop",
                                                "message": {"role": "assistant", "content": content}}],
                                   "usage": usage})
    result, seen, waits = run([ok], body)
    parsed = ArchitectResponse.model_validate_json(result.json()["choices"][0]["message"]["content"])
    assert len(seen) == 1 and not waits and parsed.objects[0].label == "lamp"
    assert seen[0].headers["authorization"].startswith("Bearer ")
    assert abs(chat_cost_usd(usage) - 0.006475) < 1e-9
    print(f"200: 1 request, parsed ArchitectResponse, cost ${chat_cost_usd(usage):.6f}")

    result, seen, waits = run([error(400, "invalid_request_error")], body)
    assert failed(result, 400, 1, seen) and not waits
    print("400: 1 request, no retry, ProviderError invalid_request_error")

    result, seen, waits = run([error(429, "rate_limit_error", {"retry-after": "2"}), ok], body)
    assert result.status_code == 200 and len(seen) == 2 and waits == [2.0]
    print("429 retry-after 2: waited 2.0 s, 2 requests, then 200")

    result, seen, waits = run([error(429, "rate_limit_error", {"retry-after": "1"})] * 2, body)
    assert failed(result, 429, 2, seen)
    print("429 twice: 2 requests, then ProviderError (one retry only)")

    result, seen, waits = run([error(429, "rate_limit_error", {"retry-after": "0"}), ok], body)
    assert result.status_code == 200 and waits == [0.0]
    soon = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=5), usegmt=True)
    result, seen, waits = run([error(429, "rate_limit_error", {"retry-after": soon}), ok], body)
    assert result.status_code == 200 and 3.0 <= waits[0] <= 5.0
    print(f"retry-after 0: waited 0.0 s; retry-after HTTP-date: waited {waits[0]:.1f} s")

    result, seen, waits = run([error(503, "server_error", {"retry-after": "60"}), ok], body,
                              budget_s=BUDGET_S["dryrun"])
    assert failed(result, 503, 1, seen) and not waits
    result, seen, waits = run([error(429, "rate_limit_error", {"retry-after": "2"}), ok], body,
                              budget_s=BUDGET_S["architect"], clock=clock_at(0.0, 14.0))
    assert failed(result, 429, 1, seen) and not waits
    print("503 retry-after 60 in a 30 s budget, and retry-after 2 with 1 s left: "
          "1 request each, no wait, ProviderError at once")

    result, seen, waits = run([error(500, "server_error"), ok], body)
    assert result.status_code == 200 and len(seen) == 2 and 0.5 <= waits[0] <= 1.0
    print(f"chat 500: retried once after {waits[0]:.2f} s jittered backoff")

    for status in (502, 504, 501):
        result, seen, waits = run([error(status, "server_error"), ok], body)
        assert failed(result, status, 1, seen) and not waits
    print("chat 502, 504 and an undocumented 501: 1 request each, ProviderError, no retry")

    gen = image_body("a portrait")
    image_ok = httpx.Response(200, json={"created": 1, "data": [{"b64_json": "UklGRg=="}],
                                         "output_format": "webp"})
    image = {"path": "/images/generations", "retryable": IMAGE_RETRYABLE_STATUS,
             "budget_s": BUDGET_S["image"]}
    result, seen, _ = run([error(500, "server_error"), image_ok], gen, **image)
    assert failed(result, 500, 1, seen)
    result, seen, waits = run([error(503, "server_error", {"retry-after": "60"}), image_ok], gen, **image)
    assert result.json()["data"][0]["b64_json"] and len(seen) == 2 and waits == [60.0]
    print("image 500: 1 request, ProviderError; image 503 retry-after 60 in a 120 s budget: "
          "waited 60.0 s, retried once")

    result, seen, waits = run([httpx.ReadTimeout, ok], body)
    assert failed(result, None, 1, seen) and result.kind == "timeout" and not waits
    result, seen, _ = run([httpx.RemoteProtocolError, ok], body)
    assert failed(result, None, 1, seen) and result.kind == "transport_error"
    result, seen, waits = run([httpx.ConnectTimeout, ok], body)
    assert result.status_code == 200 and len(seen) == 2 and 0.5 <= waits[0] <= 1.0
    result, seen, _ = run([httpx.ConnectError] * 2, body)
    assert failed(result, None, 2, seen) and result.kind == "transport_error"
    print("ReadTimeout and RemoteProtocolError: 1 request, ProviderError; "
          "ConnectTimeout and ConnectError: retried once")

    result, seen, _ = run([httpx.Response(400, json={"error": "bad"})], body)
    assert isinstance(result, ProviderError) and result.kind == "unparsed"
    result, seen, _ = run([httpx.Response(404)], body)
    assert isinstance(result, ProviderError) and result.kind == "no_body"
    print("non-envelope error body: ProviderError unparsed; empty 404: ProviderError no_body")
    print("selfcheck passed")


if __name__ == "__main__":
    main()
