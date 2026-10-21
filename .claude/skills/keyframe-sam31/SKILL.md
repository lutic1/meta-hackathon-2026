---
name: keyframe-sam31
description: Calls Meta's SAM 3.1 segmentation model (sam-3.1 on POST https://api.meta.ai/v1/responses) with raw httpx 0.28.1 and parses the streamed masks with meta-sam-parser 0.1.0 into Keyframe hotspot polygons. Use when writing, testing or debugging the segment(label, image) port, the sam-3.1 branch of src/providers/meta_api.py and its recorded SSE fixtures, the pipeline segment stage, or src/domain/masks.py mask selection (IoU against the vision box, plural grouping, the 1% and 12 caps, SVG path to frame polygons), or when the user mentions SAM 3.1 / sam-3.1 masks, meta-sam-parser or mask decoding. Do not use for muse-spark-1.3 chat calls, muse-image-1.0 generation, SAM 3D Objects on fal.ai (sam-3/3d-objects), local SAM weights or GPU inference, or Three.js hotspot rendering.
paths:
  - "src/providers/meta_api.py"
  - "src/domain/masks.py"
  - "tests/providers/**/test_meta_api_segment*.py"
  - "tests/providers/**/*sam31*.py"
  - "tests/domain/**/*mask*.py"
  - "tests/pipeline/**/*segment*.py"
  - "tests/fixtures/sam31/**"
---

# SAM 3.1 segmentation for Keyframe

## When to use

Use this skill when the work involves:
- the `sam-3.1` request, its event stream, or its errors;
- `ModelProvider.segment(label, image)` and its mock;
- the segment stage that fans out one call per label;
- `domain/masks.py`, which turns masks into `Interactable.polygons`;
- recorded SAM fixtures for offline tests.

Do not use it for:
- `muse-spark-1.3` council calls (Chat Completions) or `muse-image-1.0`;
- fal.ai `sam-3/3d-objects` (Tier 2), which takes these masks as input but is a different API;
- local SAM weights or GPU inference;
- drawing hotspots in `web/scene`.

Never make a live `sam-3.1` call (any request with a real `META_MODEL_API_KEY`) unless the user explicitly asks for it; the First live call checklist under Tested commands is the only live step. Dev loops and tests use the mock provider and recorded fixtures (AD-17).

## How Keyframe calls it

The full, tested code is in [references/request-and-stream.md](references/request-and-stream.md) (HTTP, SSE, parser, retry) and [references/masks-to-polygons.md](references/masks-to-polygons.md) (geometry, selection).

1. **Architect.** Returns labels and boxes on the 0..1000 grid. The segment stage converts the boxes to pixels of the stored 1280 px JPEG (AD-18).
2. **Fan-out.** The segment stage makes one `segment(label, photo_bytes)` call per label, on that label's clearest photo. Calls go through a bounded thread pool, at most 12 at once. The port is synchronous (AD-5, AD-7).
3. **The meta adapter** (`src/providers/meta_api.py`, the Responses branch, AD-5):

```python
def segment(self, label: str, image: bytes) -> list[Polygon] | None:      # AD-5 port
    key = self.cache.key(model=SAM_MODEL, prompt=label, images=[image])   # AD-6 key
    raw = self.cache.get_or_call(key, lambda: self._sam_raw(label, image))
    return polygons_from_result(parse_output(raw, CompletedOutcome()))   # None = zero matches

def _sam_raw(self, label: str, image: bytes) -> str:                    # cache miss only
    call_id = self.ledger.guard("segment", SAM_PRICE_USD)                # AD-6, 0.0025 USD
    try:
        result = call_with_one_retry(self.http, self.api_key, sam_request_body(label, image),
                                     budget_s=SEGMENT_BUDGET_S)          # AD-13: one retry inside
        check_result(result)
    except SamError as error:
        raise ProviderError(str(error)) from error
    finally:
        self.ledger.settle(call_id, SAM_PRICE_USD)                       # per image, no usage; failures settled billed (unverified)
    return result.raw_output
```

   The cache and ledger names follow AD-6. Their exact signatures belong to `providers/cache.py` and `providers/spend.py`, and `self.api_key` comes from `Settings.meta_model_api_key`, read from `META_MODEL_API_KEY` (AD-14). `budget_s` is the segment budget left when the call starts; every label starts together, so it is the full 10 s.
4. **Selection.** `domain/masks.py` (pure, AD-1) runs `select_instances(polygons, vision_box_px, 1280-frame W, H, plural)`. Its rules are below. An empty result or `None` becomes the box rectangle as the single polygon (AD-11, schema v1). What the stage does with a `ProviderError` for one label is not decided yet; see Known issues.
5. **Room cap.** The stage sorts by vision confidence, keeps 12, and mints `ix_` ids (AD-18). It ends with `needs_more_photos` when fewer than 5 survive. Otherwise it persists `id`, `label`, `photo` and `polygons` as the mask preview (AD-3, AD-7).
6. **Same code everywhere.** The code is identical in local and hosted mode; only the `Cache` adapter differs (AD-9). Polygons travel as `Interactable.polygons` in `schema.py` (AD-2).
7. **Offline tests.** The mock provider returns canned polygons and skips the cache and ledger. Adapter tests replay recorded SSE bodies from `tests/fixtures/sam31/` through `httpx.MockTransport`, so `pytest` stays offline (AD-17).

Rules that matter in code:
- **Prompt.** Send one short noun phrase per call: the label, never a list.
- **Image.** Send the stored downscaled JPEG bytes as `data:image/jpeg;base64,...`, byte for byte (AD-7).
- **Zero matches.** A completed stream with an empty lane is a normal result. The port returns `None`; it never raises for this.
- **Lane rules.** A finalized text that differs from the joined deltas raises `response_lane`; a `response.completed` with no finalizer is accepted with a warning (see `read_output`).
- **Mask size.** Read H and W from each mask (`record.mask.height`, `record.mask.width`). The raster covers the box, so map SVG coordinates with `left + (x + 0.5) * box_w / W` and the same for y. The `+ 0.5` is there because the SVG path puts pixel centers on integers; no doc states that, it was checked by running the parser (see Tested commands).
- **Selection** (schema "SAM mask selection"):
  - drop masks under 1% of the frame;
  - singular label: keep the best IoU against the vision box;
  - plural label: group every mask with IoU above 0.2;
  - cap the room at 12;
  - each polygon is the mask's largest SVG ring, mapped to frame pixels and simplified.

## API constraints

| Constraint | Value | Source |
|---|---|---|
| Endpoint, model, auth | `POST https://api.meta.ai/v1/responses`, `model: "sam-3.1"`, `Authorization: Bearer <key>`; served on the Responses API | https://dev.meta.ai/docs/sam/overview.md |
| Input | One user message: one `input_text` (prompt) plus one `input_image` whose `image_url` is a public URL or a base64 data URL | https://dev.meta.ai/docs/sam/segmenting.md |
| Prompt | One short concrete noun phrase per request. Comma, semicolon and plus lists return zero matches. An "and" or a second `input_text` segments only one concept. Commands, questions, negation, OR and spatial words are unreliable, so filter by box position in code | https://dev.meta.ai/docs/sam/segmenting.md |
| Prompt kinds | A noun phrase or box/point prompts, never both (400) | https://dev.meta.ai/docs/sam/segmenting.md |
| Streaming | `stream: true` is recommended. Non-streaming returns identical output but is exposed to the non-streaming 504 time limit | https://dev.meta.ai/docs/sam/segmenting.md, https://dev.meta.ai/docs/error-handling.md |
| Lane finalizer | The live API ends the text lane with `response.content_part.done`, never `response.output_text.done`. meta-sam-parser 0.1.0 accepts either | https://pypi.org/project/meta-sam-parser/0.1.0/ |
| Lane rules | One output_text lane. When deltas were seen, the finalized text must equal their concatenation. Completed and explicit incomplete terminal events require a finalized lane; end of input does not | https://github.com/meta-models/meta-sam/blob/main/protocol/sam3.md |
| Zero matches | `response.completed` with an empty `output_text` and no delta events. A valid result, not an error. Because completion requires a finalized lane, expect a `response.content_part.done` with empty text before it | https://dev.meta.ai/docs/sam/reading-segmentation.md, https://github.com/meta-models/meta-sam/blob/main/protocol/sam3.md |
| Output line | An image gives one line, `<0f>`, then comma-separated records: object id, one box, one mask. Ids are stable but not dense or 0-based; the parser keeps them as strings | https://dev.meta.ai/docs/sam/reading-segmentation.md |
| Box | `x1,y1,x2,y2` in source pixels, with inclusive `x2`/`y2`; the parser makes them half-open `right`/`bottom`. `w`/`h` give the source size | https://github.com/meta-models/meta-sam/blob/main/protocol/sam3.md |
| Mask | `data=H,W,<marker>payload`, height first, smaller than the frame. Base85, not base64 | https://dev.meta.ai/docs/sam/reading-segmentation.md |
| Mask size | Observed equal to the box size in the cookbook's live `duck` run and in Meta's captured live case (11x11 mask for an 11x11 box on a 1440x900 frame). No doc states it as a rule | https://dev.meta.ai/docs/cookbook/sam-api-basics.md, https://github.com/meta-models/meta-sam/blob/main/conformance/cases/captured-api-image-lossless.json |
| `mask_encoding` | `lossless` (`~`) is the default; `one_bit` (`!`) is opt-in through `metadata`. Box and point prompts always return `one_bit` | https://dev.meta.ai/docs/sam/segmenting.md |
| `include_confidence` | `metadata.include_confidence` must be the string `"true"` or `"false"`; anything else is a 400. A missing `c` does not mean 0. Needs parser 0.0.6 or later | https://dev.meta.ai/docs/sam/segmenting.md |
| Object caps | Image concept prompts return every match. The 16-object limit applies to box/point prompts, and to video tracking per frame | https://dev.meta.ai/docs/sam/segmenting.md |
| Inline media size | 50 MB per inline file. No SAM-specific pixel limit is documented | https://dev.meta.ai/docs/error-handling.md |
| `store` | Responses default to `store: true`. Keyframe sends `false`; sam-3.1 acceptance is unconfirmed | https://dev.meta.ai/docs/protocols/responses.md |
| Price | 2.50 USD per 1,000 images, the same for streaming and non-streaming | https://dev.meta.ai/docs/pricing-rate-limits.md |
| Rate limit | 3,000 requests per minute per team (not per key); no token limit | https://dev.meta.ai/docs/pricing-rate-limits.md |
| Retry rules (vendor) | Retry 429, 500 and 503 with exponential backoff (start at 0.5 to 1 s, add jitter, honor `Retry-After`); 503 overload and backend-unavailable send `Retry-After: 60`, a deploy drain a few seconds. Never retry 400, 401, 402, 403, 404 or 413. Don't retry a 504 unchanged. AD-13 adopts this set (Failure scenarios) | https://dev.meta.ai/docs/error-handling.md |
| Client timeout | `httpx.Timeout(10.0, connect=3.0)`: the read timeout is per chunk, so in effect the time to first event, set to the 10 s segment budget. A read timeout is never retried (AD-13). Worst case for one label with its retry: about 23 s, the 10 s budget plus one more attempt, because a retry starts only while the budget lasts | https://www.python-httpx.org/advanced/timeouts/, `docs/specs/spec-keyframe/budgets.md` |
| Parser package | `meta-sam-parser==0.1.0`: Python 3.10 or later, no dependencies. Import from the package root only. `parse_responses_stream` + `image_segmentation_format`, or `create_parser().push()/finish()`; `decode_mask_to_raster`, `decode_mask_to_rle`, `decode_mask_to_svg_path` | https://pypi.org/project/meta-sam-parser/0.1.0/ |
| Outcomes | `CompletedOutcome()`, or `IncompleteOutcome(reason="response" or "eof", detail)`. Check `diagnostics` even on a completed result | https://pypi.org/project/meta-sam-parser/0.1.0/ |

## Failure scenarios

The adapter column is settled. "Stage: box" marks the assumed per-label box fallback, which no spine or schema decision covers yet (Known issues).

The adapter retries at most once, and the single regeneration loop lives in `pipeline/regenerate.py`, never in the adapter (AD-13). AD-13 retries only what the vendor documents as retryable, and this adapter declares its set in references/request-and-stream.md:
- `SAM_RETRYABLE_STATUS`: 429, 500 and 503. Never 502, 504 or any other 5xx.
- `SAM_RETRYABLE_STREAM_CODES`: the same classes as a mid-stream error event carries them (`gateway_timeout`, the 504, is left out).
- `RETRY_ON_CONNECT`: `httpx.ConnectError` and `httpx.ConnectTimeout`, where nothing reached the server. A read timeout is never retried, because the server may still bill.

The retry runs inside the one ledger entry `_sam_raw` holds (AD-6). Before it, the adapter waits `Retry-After` (delta-seconds or an HTTP-date), or 0.5 to 1 s of jitter when there is none. If that wait is longer than what is left of the 10 s segment budget, the call fails at once with `ProviderError` instead (`retry_wait_s`). Every other failure surfaces as a typed `ProviderError`, never a raw httpx exception.

| Symptom or status | Cause | What the code does | Retry |
|---|---|---|---|
| Completed, empty lane | The concept is not in the photo | `segment` returns `None`; the stage writes the box rectangle (AD-11) | No |
| 400, `invalid prompt: ...` or `metadata[...]` | Bad prompt or metadata value | `SamError` becomes `ProviderError`. Stage: box | No, permanent |
| 401 / 402 / 403 | Bad key, billing, or permission | `ProviderError`; fix `Settings` or the account | No |
| 404, `code: model_not_found` | Wrong model id, or the team has no access | `ProviderError` | No |
| 404, empty body | Wrong URL path; there is no JSON envelope | `ProviderError` with `code=None` | No |
| 413 | Body over a size limit | `ProviderError`. A 1280 px JPEG is far below 50 MB, so suspect the wrong bytes | No |
| 429 | Team rate limit | Waits `Retry-After` (or 0.5 to 1 s with jitter), then one retry; a `Retry-After` past the remaining budget is `ProviderError` at once | Once |
| 500 | Transient server error, or a model-output parsing failure | One retry after backoff | Once |
| 502, or any other 5xx Meta does not document | Gateway or proxy error | `ProviderError` at once. Stage: box | No (AD-13) |
| 503, `service_overloaded` / `backend_unavailable` / `server_shutting_down` | Overload, backend unavailable, or a deploy drain. A 503 on model lookup means try again, not "missing" | A deploy drain's short `Retry-After` is waited, then one retry. Overload and backend-unavailable send `Retry-After: 60`, past the 10 s budget, so `ProviderError` at once. Stage: box | Once, if the wait fits the budget |
| 504, `gateway_timeout` | Non-streaming time limit, or a streaming first event that came too late | `ProviderError` at once; re-sent unchanged it would time out again. Stage: box | No (AD-13) |
| SSE `error` or `response.failed` with a 429, 500 or 503 code: `rate_limit_exceeded`, `server_error`, `server_shutting_down`, `service_overloaded` or `backend_unavailable` | The stream failed partway | One retry of the full request after 0.5 to 1 s of jitter | Once |
| SSE `error` or `response.failed` with `gateway_timeout` | A 504 reported mid-stream | `ProviderError` | No (AD-13) |
| SSE `response.failed` with any other code | Response-level failure | `ProviderError` | No |
| Finalized text differs from the joined deltas | Conflicting or truncated lane | `SamError(code="response_lane")`, then `ProviderError` | No |
| `response.completed` with no lane finalizer | Protocol deviation (the protocol requires one) | Warning logged; the joined deltas are parsed, usually as zero matches | n/a |
| A data line that is not JSON, not an object, or lacks a field; an undecodable body (`httpx.DecodingError`) | Malformed stream | `SamError(code="malformed_stream")`, then `ProviderError` | No |
| `response.incomplete`, or the body ends with no terminal event | Truncated output | `check_result` raises `ProviderError` | No |
| Diagnostic with severity `error` (`malformed_record`) | The parser dropped a malformed record | `check_result` raises; `raw_output` is logged | No |
| Diagnostic with severity `warning` (`ignored_field`, `ignored_token`, `ignored_confidence`) | An unknown wire field | Record kept; warning logged | n/a |
| Refusal event or `refusal` content part | The model refused | `ProviderError` | No |
| `httpx.ConnectError`, `httpx.ConnectTimeout` | The connection was never made, so nothing was sent or billed | `SamError(code="connect")`; one retry after 0.5 to 1 s of jitter, then `ProviderError` | Once |
| `httpx.ReadTimeout`, `WriteTimeout`, `PoolTimeout` | Client timeout; the server may still be working and billing | `SamError(code="timeout")`, then `ProviderError` | No (AD-13) |
| Any other `httpx.TransportError` (`RemoteProtocolError`, `ReadError`, ...) | Connection dropped mid-request | `SamError(code="transport")`, then `ProviderError` | No |
| `SpendCapExceeded` from the guard | The cap would be passed | Raised before any request; a cache hit is never refused (AD-6) | No |

## Tested commands

Every entry below was run on 2026-10-21 in this repo's container, with no network access to Meta and no API key.

| Command or snippet | What it proves | Result observed | Where |
|---|---|---|---|
| `uv run --no-project --with meta-sam-parser==0.1.0 --with httpx==0.28.1 python .claude/skills/keyframe-sam31/scripts/selfcheck.py` | See the list below the table | 68 PASS, 0 FAIL, exit 0, ending `OK: 0 failure(s)` (uv 0.11.32, CPython 3.13.16; re-run on 2026-10-21 after the amended AD-13) | Offline |
| Replay of Meta's conformance corpus (`conformance/cases/*.json` from meta-models/meta-sam, fetched as data) through `parse_responses_stream`, converted to wire-shaped events | The documented async form matches Meta's expected rasters, COCO RLE, SVG paths, outcomes and error codes. The captured live lossless case shows an 11x11 mask for an 11x11 box on a 1440x900 frame | 38 cases matched; 4 source-failure cases skipped (they need a failing iterator); 0 failed. The same harness's httpx and retry checks (39/39 PASS) ran against an earlier draft of the call code, not the blocks shipped here; those cases now live in the selfcheck | Offline, harness not shipped |
| Replay of the 33 image cases of that corpus through the shipped `read_output` + `parse_output` | How the canonical sync path compares with the strict lane rules | 25 agree, 8 differ, 9 skipped (source-failure or video). All 8 are lane-strictness cases the reader accepts by design: 5 come back incomplete (so `check_result` raises), 3 come back completed (`lane-completed-before-done` with a warning, and two repeated identical finalizers). Both conflicting-finalizer cases now raise `response_lane` | Offline, harness not shipped |
| `decode_mask_to_svg_path` on the docs' 27x60 lossless mask, compared with `decode_mask_to_raster` | SVG pixel centers sit on integers | SVG x from -0.5 to 59.5 for raster columns 0 to 59; y from -0.5 to 26.5 | Offline |
| `inspect.signature` on `parse_responses_stream`, `image_segmentation_format`, `decode_mask_to_raster`, `decode_mask_to_rle`, `decode_mask_to_svg_path`, `push`, `finish` | The names and signatures cited in this skill exist as shown | Matches (asserted in the selfcheck) | Offline |
| `python3 -c "import yaml; print(yaml.safe_load(open('.claude/skills/keyframe-sam31/SKILL.md').read().split('---')[1]))"` | The frontmatter parses, with keys `name`, `description` (778 characters, under 1,024) and `paths` | Parsed | Offline |
| A real `sam-3.1` call | Auth, the request shape, the event names, the empty zero-match finalizer, `store: false`, latency against the 10 s read timeout | Not run (no key, no paid calls) | Live-only: confirm on the first live call |

What the selfcheck covers:
- the pinned versions and signatures;
- the python blocks in `references/*.md`, executed as written;
- the request shape;
- a synthetic SSE stream through `httpx.MockTransport`, parsed and decoded to raster, RLE and SVG;
- box-sized masks, and polygons that land inside their boxes;
- zero matches with a finalized lane (no warning) and without one (warning logged);
- a finalized text that conflicts with its deltas (`response_lane`, no retry);
- malformed streams: a non-JSON line, a non-object line, a delta without `delta`, an undecodable gzip body (`malformed_stream`, no retry);
- the amended AD-13 retry set: `SAM_RETRYABLE_STATUS` is exactly 429, 500 and 503, the stream codes leave out `gateway_timeout`, and `RETRY_ON_CONNECT` is `ConnectError` and `ConnectTimeout`;
- no retry on 400, 401, 403, 404 (with and without a body), 413, 501, 502, 504 or 599; one retry after `Retry-After` on 429, 500 and 503, and a second 429 raised; an HTTP-date `Retry-After` honoured; jittered backoff (0.5 to 1 s) without `Retry-After`;
- the budget rule: a 60 s `Retry-After` against the 10 s segment budget fails at once with no wait; a 2 s `Retry-After` with 1 s left (fake clock) fails at once; a 60 s `Retry-After` inside a 90 s budget is waited and retried;
- one retry on each mid-stream 429, 500 or 503 code, none on `gateway_timeout`; a non-retryable `response.failed`; a refusal content part;
- `ConnectError` and `ConnectTimeout` retried once, a second `ConnectError` raised; `ReadTimeout` and `RemoteProtocolError` raised with no retry;
- EOF reported as incomplete, and `check_result` rejecting it;
- the `parse_responses_stream` variant;
- the selection rules.

First live call checklist. Only when the user explicitly asks for it: it needs the API key in `Settings` and makes about 14 paid calls, roughly 0.035 USD. Run it once, record the result here, then save the SSE bodies as fixtures under `tests/fixtures/sam31/`:
1. Send one known-present label and one absent label on a real 1280 px JPEG, with `store: false`.
2. Record the event types, and check that the zero-match stream closes an empty lane with `response.content_part.done` before `response.completed`.
3. Check that each mask's H and W equal its box size, and that `w`/`h` equal 1280 by the photo height.
4. Measure latency with 12 calls in parallel against the 10 s budget and the 10 s read timeout.

## Known issues

- **Spine wording vs observed masks.** The spine's Hotspot geometry convention and schema v1 say mask rasters are "scaled to the frame". Every documented example, the cookbook's live run, and Meta's captured live case show a mask raster the size of its box, not the frame. Polygons are offset to the box origin, and scaled only by box/mask, which has been 1 in every observed case. Fix that wording at the next spine or schema edit.
- **Per-label `ProviderError`.** What the segment stage does when one label's call fails is undecided. This skill assumes it writes the box rectangle for that label, as AD-11 does for zero matches, but AD-11 covers only zero matches, AD-13 only says stages raise `ProviderError`, and `stack.md`'s "Spark boxes as hotspots" is a fallback for the whole Masks component. PRD assumption A-24 says the opposite: the Build ends `failed` at the segment stage. Settle it in AD-7 or AD-13 before coding the stage. How a label is marked plural is also undefined in schema v1.
- **Plural grouping above IoU 0.2** fails for groups of five or more similar objects. Each instance's IoU against a group box is about its area share; 5 books score 0.2 each. Measured in the selfcheck; details in [references/masks-to-polygons.md](references/masks-to-polygons.md).
- **Zero-match finalizer.** The protocol requires a finalized output_text lane on completion, so the expected live zero-match stream is `response.content_part.done` with empty text, then `response.completed` (protocol/sam3.md). `read_output` still accepts a completed stream with no finalizer, with a warning, where `parse_responses_stream` raises `response_lane`. Confirm the empty finalizer on the first live call.
- **Lenient lane reader.** `read_output` enforces the conflict rule but not interleaved lanes, repeated finalizers or deltas after finalization. In the conformance replay, those cases end incomplete (and are rejected) or completed with identical text. Port the remaining rules only if a live stream ever shows them.
- **httpx thread safety.** Sharing one sync `httpx.Client` across the 12 worker threads is assumed safe. No official httpx page fetched here states it; if in doubt, use one client per worker.
- **Path scope.** `src/providers/base.py`, `mock.py` and `src/pipeline/build.py` are left out of `paths` on purpose: they hold every port and stage, so this skill would load for unrelated work. The `src/providers/meta_api.py` overlap with keyframe-muse cannot be avoided, since one file holds both branches.
- **License.** meta-sam-parser is under the SAM License (not OSI). Depending on it is fine. Code copied from meta-sam must ship that license's text. The cookbook is MIT.

## References

- https://dev.meta.ai/docs/sam/overview.md: what sam-3.1 is, the request and response anatomy, and zero matches as a valid outcome.
- https://dev.meta.ai/docs/sam/segmenting.md: prompt rules, the request shape, streaming, `include_confidence`, `mask_encoding`, limits, and the 400 and 404 messages.
- https://dev.meta.ai/docs/sam/reading-segmentation.md: the line and record grammar, object ids, box and mask fields, and the base85 payload.
- https://dev.meta.ai/docs/sam/client-libraries.md: parser entry points, snapshots, outcomes, diagnostics, the error codes, and the mask conversions.
- https://dev.meta.ai/docs/cookbook/sam-api-basics.md: the cookbook walk-through and a real `duck` run showing box-sized masks.
- https://github.com/meta-models/meta-model-cookbook/tree/main/07_sam: `sam_api.py` with `validate_result` and `summarize_result` (MIT); the AsyncOpenAI form.
- https://github.com/meta-models/meta-sam/blob/main/protocol/sam3.md: the normative wire format, finalizer rules, and outcomes.
- https://github.com/meta-models/meta-sam/tree/main/conformance: the cross-language conformance cases used for the offline replay.
- https://pypi.org/project/meta-sam-parser/0.1.0/: the Python package README (push/finish, `parse_responses_stream` modes, decoders).
- https://dev.meta.ai/docs/error-handling.md: the error envelope, each status code, retry rules, and streaming error events.
- https://dev.meta.ai/docs/pricing-rate-limits.md: SAM price per image and the per-team rate limits.
- https://dev.meta.ai/docs/protocols/responses.md: SSE event types, the `[DONE]` terminator, and the `store` default.
- https://www.python-httpx.org/advanced/timeouts/: what httpx's connect, read, write and pool timeouts bound (the read timeout is per chunk).
