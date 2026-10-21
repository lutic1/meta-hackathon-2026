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
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

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
SEGMENT_BUDGET_S = 10.0  # budgets.md: all labels in parallel
# AD-13: Meta documents 429, 500 and 503 as retryable; never 502, 504 or an undocumented 5xx.
SAM_RETRYABLE_STATUS = frozenset({429, 500, 503})
# The same classes as a mid-stream error event carries them (no gateway_timeout: that is the 504).
SAM_RETRYABLE_STREAM_CODES = frozenset({"rate_limit_exceeded", "server_error", "server_shutting_down",
                                        "service_overloaded", "backend_unavailable"})
RETRY_ON_CONNECT = (httpx.ConnectError, httpx.ConnectTimeout)  # nothing was sent, so nothing was billed
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
                           retryable=code in SAM_RETRYABLE_STREAM_CODES)
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
    except RETRY_ON_CONNECT as error:
        raise SamError(f"connect: {error!r}", code="connect", retryable=True) from error
    except httpx.TimeoutException as error:  # read, write or pool: the server may still bill
        raise SamError(f"timeout: {error!r}", code="timeout") from error
    except httpx.TransportError as error:
        raise SamError(f"transport: {error!r}", code="transport") from error
    except MALFORMED_STREAM as error:
        raise SamError(f"malformed stream: {error!r}", code="malformed_stream") from error


def _http_error(response: httpx.Response) -> SamError:
    try:
        error = dict(response.json().get("error") or {})
    except (ValueError, AttributeError, TypeError):
        error = {}  # an unknown path returns 404 with an empty body; other bodies may not be envelopes
    return SamError(error.get("message") or response.reason_phrase,
                    status=response.status_code, code=error.get("code"),
                    retryable=response.status_code in SAM_RETRYABLE_STATUS,
                    retry_after=retry_after_s(response.headers))


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


def call_with_one_retry(client: httpx.Client, api_key: str, body: dict, *,
                        budget_s: float = SEGMENT_BUDGET_S,
                        sleep: Callable[[float], None] = time.sleep,
                        clock: Callable[[], float] = time.monotonic) -> ImageSegmentationResult:
    """AD-13: one retry with backoff, only on a retryable status, stream code or connect error."""
    started = clock()
    try:
        return post_sam(client, api_key, body)
    except SamError as error:
        remaining = budget_s - (clock() - started)
        wait = retry_wait_s(error.retry_after, remaining) if error.retryable else None
        if wait is None:
            raise
    sleep(wait)
    return post_sam(client, api_key, body)


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

The timeout comes from the segment budget: 10 s total for all labels in parallel (`docs/specs/spec-keyframe/budgets.md`). httpx's read timeout bounds the wait for each chunk, not the whole response (https://www.python-httpx.org/advanced/timeouts/). A sam-3.1 stream sends almost nothing until inference ends, so the read timeout is in effect the time to first event, and 10 s makes a stalled attempt give up at about the budget instead of three times it. A read timeout is never retried, and the retry starts only while the budget lasts, so a label's worst case is the 10 s budget plus one more attempt (connect 3 s, first event 10 s): about 23 s. That overruns the stage target, but it is bounded and only happens on the error path. Raising the timeout is fine if the first live calls show slower first events; record the measured value in SKILL.md.

The retry implements AD-13: one retry with backoff, inside the one ledger entry `_sam_raw` holds (AD-6), only on what Meta documents as retryable. That is `SAM_RETRYABLE_STATUS` (429, 500, 503), the same classes when they arrive as a mid-stream error event (`SAM_RETRYABLE_STREAM_CODES`), and a connect error (`RETRY_ON_CONNECT`), where nothing reached the server. A 502, a 504 or any other 5xx is not retried, nor is a read timeout, because the server may still be working and billing. The wait is `Retry-After` when the server sends one (delta-seconds or an HTTP-date), otherwise 0.5 to 1 s of jitter. When that wait is longer than what is left of `budget_s`, the call fails at once instead of waiting: a 503 overload or backend-unavailable answer asks for 60 s, more than the whole 10 s segment budget, so that label fails at once with `ProviderError`.

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
| `response.failed` | failure, with `response.error.code` | `SamError`, retried once if the code is a 429, 500 or 503 code (`SAM_RETRYABLE_STREAM_CODES`); `gateway_timeout` is not |
| `error` | the stream itself failed, for example `server_shutting_down` | `SamError`, retried once if the code is a 429, 500 or 503 code (`SAM_RETRYABLE_STREAM_CODES`); `gateway_timeout` is not |
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
