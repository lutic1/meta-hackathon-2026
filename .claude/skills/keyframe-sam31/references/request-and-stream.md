# sam-3.1 request, stream and parse (httpx 0.28.1, meta-sam-parser 0.1.0)

The code blocks marked `python` in this file and in `masks-to-polygons.md` are executed and tested by `scripts/selfcheck.py`. Keep them self-contained, and run the selfcheck after editing them.

## Request

One user message holding one `input_text` part (the noun phrase) and one `input_image` part (a base64 data URL of the stored 1280 px JPEG). `stream: true` is the path Meta recommends; a non-streaming request returns the same output in one body, but it can hit a 504 if the whole response takes too long.

```json
{
  "model": "sam-3.1",
  "input": [{"type": "message", "role": "user", "content": [
    {"type": "input_text", "text": "mug"},
    {"type": "input_image", "image_url": "data:image/jpeg;base64,/9j/4AAQ..."}
  ]}],
  "stream": true,
  "store": false
}
```

- Headers: `Authorization: Bearer <key>`, `Content-Type: application/json` (httpx sets it for `json=`), `Accept: text/event-stream`.
- `store: false` keeps Meta from persisting the response. Responses default to `store: true`. No page fetched here says whether `sam-3.1` accepts `store`, so confirm it on the first live call. If a 400 names `store`, drop the field and record that in the skill.
- Optional `metadata` (every value is a string): `{"include_confidence": "true"}` adds `c` to each box and mask, and `{"mask_encoding": "one_bit"}` asks for smaller masks than the default `lossless`. Keyframe sends neither. If you add one, put it in the cache key (see the end of this file).

## The call

```python
"""sam-3.1 over raw httpx: request body, SSE reading, push/finish parsing, one retry."""

import base64
import json
import logging
import random
import time
from collections.abc import Iterable, Iterator

import httpx
from meta_sam_parser import (
    CompletedOutcome,
    ImageSegmentationResult,
    IncompleteOutcome,
    image_segmentation_format,
)

log = logging.getLogger(__name__)

SAM_URL = "https://api.meta.ai/v1/responses"
SAM_MODEL = "sam-3.1"
RETRYABLE_STATUS = frozenset({429, *range(500, 600)})  # AD-13, binding: 429 and every 5xx
# The 429 and 5xx codes in Meta's error guide, as a mid-stream error event carries them (AD-13).
RETRYABLE_STREAM_CODES = frozenset({"rate_limit_exceeded", "server_error", "server_shutting_down",
                                    "service_overloaded", "backend_unavailable", "gateway_timeout"})
MAX_RETRY_WAIT_S = 10.0  # the segment budget; a longer Retry-After (overload sends 60) is cut to it
# Anything wrong with the body of a 200 stream. DecodingError is an HTTPError but not a TransportError.
MALFORMED_STREAM = (ValueError, KeyError, AttributeError, TypeError, httpx.HTTPError)


class SamError(Exception):
    """Raised by the call; the meta adapter re-raises it as ProviderError (AD-13)."""

    def __init__(self, message: str, *, status: int | None = None, code: str | None = None,
                 retryable: bool = False, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.status, self.code = status, code
        self.retryable, self.retry_after = retryable, retry_after


def sam_request_body(label: str, jpeg: bytes) -> dict:
    data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
    return {
        "model": SAM_MODEL,
        "input": [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": label},
                {"type": "input_image", "image_url": data_url},
            ],
        }],
        "stream": True,
        "store": False,
    }


def sse_events(lines: Iterable[str]) -> Iterator[dict]:
    for line in lines:
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            return
        yield json.loads(data)


def lane_text(deltas: list[str], final: str | None) -> str:
    """Protocol lane rule: a finalized text must equal the joined deltas when any were seen."""
    joined = "".join(deltas)
    if final is None:
        return joined
    if deltas and final != joined:
        raise SamError("finalized output text conflicts with its deltas", code="response_lane")
    return final


def read_output(events: Iterable[dict]) -> tuple[str, CompletedOutcome | IncompleteOutcome]:
    """Collect the output_text lane and map the terminal event to a parser outcome."""
    deltas: list[str] = []
    final: str | None = None
    for event in events:
        kind = event.get("type", "")
        if kind == "response.output_text.delta":
            deltas.append(event["delta"])
        elif kind == "response.output_text.done":
            final = event["text"]
        elif kind == "response.content_part.done":
            part = event.get("part") or {}
            if part.get("type") == "refusal":
                raise SamError("refused", code="response_refusal")
            if part.get("type") == "output_text":
                final = part["text"]
        elif kind.startswith("response.refusal"):
            raise SamError("refused", code="response_refusal")
        elif kind == "response.completed":
            if final is None:
                log.warning("sam-3.1: response.completed without a finalized output_text lane")
            return lane_text(deltas, final), CompletedOutcome()
        elif kind == "response.incomplete":
            details = (event.get("response") or {}).get("incomplete_details") or {}
            return lane_text(deltas, final), IncompleteOutcome(reason="response", detail=details.get("reason"))
        elif kind in ("response.failed", "error"):
            error = (event.get("response") or {}).get("error") or event.get("error") or event
            code = error.get("code")
            raise SamError(error.get("message") or kind, code=code,
                           retryable=code in RETRYABLE_STREAM_CODES)
    return lane_text(deltas, final), IncompleteOutcome(reason="eof")


def parse_output(text: str, outcome: CompletedOutcome | IncompleteOutcome) -> ImageSegmentationResult:
    parser = image_segmentation_format().create_parser()
    parser.push(text, emit=False)
    return parser.finish(outcome).result


def post_sam(client: httpx.Client, api_key: str, body: dict) -> ImageSegmentationResult:
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "text/event-stream"}
    try:
        with client.stream("POST", SAM_URL, json=body, headers=headers) as response:
            if response.status_code != 200:
                response.read()
                raise _http_error(response)
            text, outcome = read_output(sse_events(response.iter_lines()))
        return parse_output(text, outcome)
    except httpx.TransportError as error:
        raise SamError(f"transport: {error!r}", code="transport") from error
    except MALFORMED_STREAM as error:
        raise SamError(f"malformed stream: {error!r}", code="malformed_stream") from error


def _http_error(response: httpx.Response) -> SamError:
    try:
        error = dict(response.json().get("error") or {})
    except (ValueError, AttributeError, TypeError):
        error = {}  # an unknown path returns 404 with an empty body; other bodies may not be envelopes
    after = response.headers.get("retry-after")
    return SamError(error.get("message") or response.reason_phrase,
                    status=response.status_code, code=error.get("code"),
                    retryable=response.status_code in RETRYABLE_STATUS,
                    retry_after=float(after) if after and after.isdigit() else None)


def call_with_one_retry(client: httpx.Client, api_key: str, body: dict,
                        sleep=time.sleep) -> ImageSegmentationResult:
    """One retry with backoff, on 429, any 5xx or their stream error codes only (AD-13)."""
    try:
        return post_sam(client, api_key, body)
    except SamError as error:
        wait = _retry_wait(error)
        if wait is None:
            raise
    sleep(wait)
    return post_sam(client, api_key, body)


def _retry_wait(error: SamError) -> float | None:
    """min(Retry-After or 0.5 to 1 s of jitter, MAX_RETRY_WAIT_S); None means do not retry."""
    if not error.retryable:
        return None
    wait = error.retry_after if error.retry_after is not None else 0.5 + random.random() * 0.5
    return min(wait, MAX_RETRY_WAIT_S)


def check_result(result: ImageSegmentationResult) -> None:
    """Port of the cookbook's validate_result: incomplete or dropped data is an error."""
    if result.outcome.status != "completed":
        raise SamError(f"incomplete: {result.outcome.reason} ({result.outcome.detail})",
                       code="incomplete")
    errors = [d for d in result.diagnostics if d.severity == "error"]
    if errors:
        raise SamError("; ".join(f"line {d.line}: {d.code}" for d in errors), code="malformed")
```

Use one `httpx.Client` per adapter, built with `timeout=httpx.Timeout(10.0, connect=3.0)` and `limits=httpx.Limits(max_connections=12)` to match the segment fan-out (AD-5).

The timeout comes from the segment budget: 10 s total for all labels in parallel (`docs/specs/spec-keyframe/budgets.md`). httpx's read timeout bounds the wait for each chunk, not the whole response (https://www.python-httpx.org/advanced/timeouts/). A sam-3.1 stream sends almost nothing until inference ends, so the read timeout is in effect the time to first event, and 10 s makes a stalled attempt give up at about the budget instead of three times it. A label's worst case is two attempts plus the retry wait: about 27 s with the default backoff, about 36 s when a `Retry-After` of 10 s or more is honoured. That overruns the stage target, but it is bounded and only happens on the error path. Raising the timeout is fine if the first live calls show slower first events; record the measured value in SKILL.md.

The retry follows AD-13 as written: one retry with backoff on 429 and every 5xx, and on the same classes when they arrive as a mid-stream error event, inside the one ledger entry `_sam_raw` holds (AD-6). The wait is `Retry-After` when the server sends one, otherwise 0.5 to 1 s of jitter, and never more than `MAX_RETRY_WAIT_S`. That 10 s cap is the segment budget, a Keyframe choice, not a vendor number. A 503 overload or backend-unavailable answer asks for 60 s, so its retry goes out 50 s early, usually gets another 503, and the label fails with `ProviderError`. Meta's guide is narrower (no 504 retry unchanged, no 502); following it is a proposed deviation in SKILL.md, Known issues.

## Why push/finish and not `parse_responses_stream`

`ModelProvider` ports are synchronous (AD-5), and `parse_responses_stream` needs an async iterable. So the adapter reads the stream with the sync httpx client, and `read_output` collects the lane text and feeds it to the push/finish parser, which has no event loop and no lane rules of its own.

`read_output` therefore applies the two lane rules that change the result (https://github.com/meta-models/meta-sam/blob/main/protocol/sam3.md):

- When deltas were seen, the finalized text must equal their concatenation. A mismatch raises `SamError(code="response_lane")`, which is not retried. Without this check, a truncated or conflicting stream could come back as a valid zero-match result, and the stage would quietly write the box.
- A completed (or explicitly incomplete) response needs a finalized output_text lane. The protocol requires it, so the expected live zero-match stream is an empty delta-less lane closed by `response.content_part.done` with `text: ""`, then `response.completed`. If `response.completed` arrives with no finalizer, the reader logs a warning and keeps the joined deltas (usually empty, so zero matches). `parse_responses_stream` raises `response_lane` there instead. The warning makes the difference visible without failing a build on a stream the live API is not expected to send. Confirm the empty finalizer on the first live call.

The reader stays lenient on the remaining lane rules (interleaved lanes, repeated finalizers, deltas after finalization). Only the single lane SAM uses for an image is read.

For async code, here is the documented form (iterate inside `async with`, then `final_result()`). It is tested offline against Meta's conformance cases:

```python
from collections.abc import AsyncIterable

from meta_sam_parser import ImageSegmentationResult, image_segmentation_format, parse_responses_stream


async def parse_image_events(events: AsyncIterable[dict]) -> ImageSegmentationResult:
    parsed = parse_responses_stream(events, image_segmentation_format())
    async with parsed:
        async for _snapshot in parsed:
            pass  # cumulative snapshots; render the latest if you need progress
    return await parsed.final_result()
```

Calling `final_result()` before any iteration selects final-only mode, which drains the source without emitting snapshots. Leaving `async with` early makes `final_result()` raise `ResponsesStreamAbortedError`. In 0.1.0 the adapter finalizes the lane from `response.content_part.done` on its own. The cookbook's step that synthesizes `response.output_text.done` (`stream_events` in `sam_api.py`) is harmless, but this version no longer needs it.

Cross-reference only (Keyframe has no `openai` dependency): Meta's cookbook makes the same call with `AsyncOpenAI(base_url="https://api.meta.ai/v1")`, `await client.responses.create(model="sam-3.1", stream=True, input=[...])`, and passes the SDK events, dumped to dicts, to `parse_responses_stream`. See `07_sam/01_api_basics/python/sam_api.py` in https://github.com/meta-models/meta-model-cookbook.

## Events the reader handles

| Event | Meaning | Reader |
|---|---|---|
| `response.output_text.delta` | one line of output (one per frame; an image has one) | appended |
| `response.content_part.done` with `part.type == "output_text"` | the live API's lane finalizer, holding the full text | final text |
| `response.output_text.done` | the alternative finalizer, which the live API does not emit | final text |
| `response.completed` | normal end, including zero matches | `CompletedOutcome()` |
| `response.incomplete` | ended early, with `response.incomplete_details.reason` | `IncompleteOutcome(reason="response")`, then `check_result` raises |
| `response.failed` | failure, with `response.error.code` | `SamError`, retried once if the code is a 429 or 5xx code (`RETRYABLE_STREAM_CODES`) |
| `error` | the stream itself failed, for example `server_shutting_down` | `SamError`, retried once if the code is a 429 or 5xx code (`RETRYABLE_STREAM_CODES`) |
| refusal events, or a `refusal` content part | the model refused | `SamError(code="response_refusal")`, not retried |
| end of body without a terminal event | transport cut | `IncompleteOutcome(reason="eof")`, then `check_result` raises |
| finalized text that differs from the joined deltas | conflicting or truncated lane | `SamError(code="response_lane")`, not retried |
| `response.completed` with no finalizer | protocol deviation | warning logged, joined deltas used |
| a data line that is not JSON, not an object, or missing a field | malformed stream | `SamError(code="malformed_stream")`, not retried |

## Cache and spend for a SAM call (AD-6)

- Key components: model id `sam-3.1`; an empty schema hash; the prompt (the label, plus any `metadata` you add); no reasoning effort; the sha256 of the stored downscaled JPEG; and `attempt` 0.
- Cache the completed `result.raw_output` string. It is small and can be parsed again with `parse_output(raw, CompletedOutcome())`. Cache a zero-match result too, as the empty string. Never cache an error or an incomplete result.
- `SpendLedger.guard("segment", 0.0025)` runs on a cache miss only. A retried call counts as one ledger entry. Settle at 0.0025 USD, because SAM is billed per image, not per token, so there is no usage to read. No page fetched here says whether a failed request is billed.
- The mock provider skips both the cache and the ledger, and returns canned polygons.
