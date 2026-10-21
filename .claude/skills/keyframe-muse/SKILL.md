---
name: keyframe-muse
description: Calls Muse Spark 1.3 (POST /v1/chat/completions with response_format json_schema, base64 JPEG image parts and reasoning_effort) and Muse Image 1.0 (POST /v1/images/generations) on the Meta Model API through httpx for Keyframe. Use when writing, testing or debugging the meta or openai_compatible ModelProvider adapters, the Architect, Riddler, dry-run or Trickster council calls, response schemas rendered from the pydantic models in src/domain/schema.py, retries and error handling, spend pricing from returned usage, the Baseten Muse Spark Open fallback for the Riddler, or scripts/portraits.py. Do not use for sam-3.1 segmentation on the Responses API, fal.ai SAM 3D Objects, Modal deployment, Ollama Guide phrasing, Muse Voice transcription, Fireworks-specific facts for the Trickster's 8B Llama fallback (only the shared openai_compatible request path is covered), or the retired api.llama.com host and llama-api-client.
when_to_use: Trigger phrases such as "wire up Muse Spark", "Architect vision call", "Riddler schema", "dry run call", "Trickster proposal", "json_schema returns 400", "reasoning_effort", "max_completion_tokens", "muse-image portraits", "Baseten fallback", "retry on 429".
paths:
  - "src/providers/meta_api.py"
  - "src/providers/openai_compatible.py"
  - "src/council/architect.py"
  - "src/council/riddler.py"
  - "src/council/dryrun.py"
  - "src/council/trickster.py"
  - "scripts/portraits.py"
  - "tests/providers/**/test_meta_api_chat*.py"
  - "tests/providers/**/test_meta_api_image*.py"
  - "tests/providers/**/test_openai_compatible*.py"
  - "tests/council/**/test_architect*.py"
  - "tests/council/**/test_riddler*.py"
  - "tests/council/**/test_dryrun*.py"
  - "tests/council/**/test_trickster*.py"
---

# Muse Spark 1.3 and Muse Image 1.0 for Keyframe

All facts below were checked against the official pages on 2026-10-21. The full wire formats (request and response JSON, error envelope, schema limits, Baseten differences) are in [references/request-shapes.md](references/request-shapes.md). The runnable reference for every snippet is [scripts/selfcheck.py](scripts/selfcheck.py).

## When to use

Use this skill for:
- The four council calls on `muse-spark-1.3`: Architect, Riddler, dry run and Trickster.
- The `meta` adapter in `src/providers/meta_api.py`, and the `openai_compatible` adapter when it swaps the Riddler to Baseten.
- `strict_schema` and the response models in `src/domain/schema.py` that become `response_format`.
- `scripts/portraits.py`, which calls `muse-image-1.0` once to produce the four committed portraits.
- The `meta` and `openai_compatible` adapter tests (`tests/providers/test_meta_api_chat*.py`, `test_meta_api_image*.py`, `test_openai_compatible*.py`) that replay recorded fixtures from `tests/fixtures/`, and the council prompt tests for the four roles.

Never make a live Meta or Baseten call (any request with a real `META_MODEL_API_KEY` or `OPENAI_COMPATIBLE_API_KEY`), `scripts/portraits.py` and the live-only rows under Tested commands included, unless the user explicitly asks for it. Dev loops and tests use the mock provider and recorded fixtures (AD-17).

Do not use it for:
- `sam-3.1`, which runs on the Responses API with its own parser and errors.
- fal.ai SAM 3D, Modal, the Ollama `HintPhraser`, or voice.
- Fireworks specifics for the Trickster's last fallback, an 8B Llama (`stack.md`). It goes through the same `openai_compatible` adapter, so the request path and retry rules here apply, but this skill has not checked Fireworks' model id, limits or structured-output support. The spine has the model id confirmed on Oct 26 (CAP-5).
- Anything on `api.llama.com` or `llama-api-client`. This means the retired Llama API host, not Llama models served elsewhere. The old Llama API docs host now redirects to the Meta Model API overview, and Meta says the API needs no client of its own: plain HTTP or any OpenAI-compatible client works. Keyframe uses httpx 0.28.1.

## How Keyframe calls it

There is one path. Council modules build text only, and the adapter owns the HTTP, the cache and the spend ledger.

1. The Riddler, dry-run and Trickster builders in `src/council/<role>.py` render `(system, user_text)` from a `RoomView` only (AD-3), so solutions never reach a prompt. The Architect runs before any Room exists. It renders fixed instructions, and the photo bytes reach the adapter as `images`.
2. The pipeline stage calls the role's port (AD-5): `chat(messages, *, images=[...], response_schema=Model, reasoning_effort=...)`. `wiring.py` builds one `ModelProvider` per role from `Settings` (AD-14), each with its own output budget. The Riddler fallback swaps only that role's provider.
3. The adapter runs AD-6 guarded calls:
   - `Cache.get_or_call(key)`, where `key = sha256(model id || schema hash || full prompt including system || reasoning_effort || sha256 of each image in order || attempt)`. A hit is never priced or refused.
   - On a miss only, `SpendLedger.guard(kind, estimate)`. A call that would pass `SPEND_CAP_USD` raises `SpendCapExceeded` before any HTTP. The ledger keeps one entry per call, and a retried call is still one entry.
   - The adapter builds the body, POSTs with `post_with_retry` (AD-13: one retry, only on the endpoint's retryable set, within the role's budget), parses the result, and settles the ledger from `usage`.
4. The result is validated with pydantic into the AD-2 model and returned as `ChatResponse`.

```python
# src/wiring.py: one provider per role; output and time budgets are fixed at construction
riddler = MetaModelProvider(client, model=settings.model_riddler,
                            max_completion_tokens=settings.max_completion_tokens_riddler,
                            budget_s=45.0)                         # budgets.md, Riddler row

# src/providers/meta_api.py, inside MetaModelProvider.chat (shape only; helpers as in scripts/selfcheck.py)
body = chat_body(system, user_text, images, response_schema, reasoning_effort,
                 self.max_completion_tokens)                       # strict=False on Meta
resp = post_with_retry(self.client, "/chat/completions", body,
                       retryable=CHAT_RETRYABLE_STATUS, budget_s=self.budget_s)
choice = resp.json()["choices"][0]
if choice["finish_reason"] != "stop":                              # "length" means truncated JSON
    raise ProviderError(200, choice["finish_reason"], "incomplete structured output")
parsed = response_schema.model_validate_json(choice["message"]["content"])
ledger.settle(call_id, chat_cost_usd(resp.json()["usage"]))
```

- **Client.** Use one `httpx.Client(base_url="https://api.meta.ai/v1", headers={"Authorization": f"Bearer {key}"}, timeout=...)` per provider. The key comes from `Settings.meta_model_api_key`, read from `META_MODEL_API_KEY` (AD-14 keeps that name, not Meta's documented `MODEL_API_KEY`). Read it in no other module. Locally it lives in `.env`; hosted, in the `keyframe` `modal.Secret`.
- **Images.** Send the stored downscaled 1280 px JPEG bytes from ingest (AD-7) as `data:image/jpeg;base64,...` parts in the user message, in upload order. Never re-encode them, because the cache key and the masks use the same bytes.
- **Boxes.** Boxes come back on a 0 to 1000 grid of the image as sent. The segment stage converts them to frame pixels and clamps them (AD-18, Conventions). The model may return 1001 at an edge.
- **Schemas.** On Meta, send `Model.model_json_schema()` with `strict: false`, which is the API default and AD-5's first option; AD-2 requires it for any schema holding a tagged union. Output is still constrained to the schema. Use `strict_schema(Model)` with `strict: true` only where the host requires strict mode: Baseten's reference fixes `strict` to `true`. Meta's strict subset forbids `oneOf` and open maps, so `strict_schema` rewrites the `oneOf` that AD-2's tagged unions produce and refuses map-typed fields. AD-2 keeps map-typed fields out of every model-response schema (`RoomDraft`, `DryRunAnswers`, `ArchitectResponse`: lists or fixed `p1` to `p6` keys), so the refusal only catches a regression. Baseten documents no subset of its own. That it enforces Meta's is an assumption to confirm in the Tue Oct 27 live call.

| Role | Effort | Images | Response model | Budget (`budgets.md`), passed as `budget_s` |
|---|---|---|---|---|
| Architect | `low` | all 6 to 10 photos | `ArchitectResponse` (AD-18) | 15 s |
| Riddler | `medium` | none (prompt view: interactables only) | `RoomDraft` (AD-7), ordinal keys `p1` to `p6` | 45 s; past that, retry at `low` |
| Dry run | `low` | photos, plus labels, clues and rungs | `DryRunAnswers` (AD-12): a list of `{puzzle_id, answer}`, never a map | 30 s |
| Trickster | `low` | none named in the spec | edit proposal from the fixed menu (`decoy`, `merge`, `loosen`, `shortcut`) | at most 6 calls per session; no time budget, so `budget_s=30` (Keyframe choice) |

- **Portraits.** `scripts/portraits.py` calls `generate_image(prompt)` (AD-5) once per wizard through the same guarded path, with kind `image` and a seed estimate of $0.01, `retryable=IMAGE_RETRYABLE_STATUS` and `budget_s=120` (Keyframe choice, so a 60 s overload `Retry-After` fits). It decodes `data[0].b64_json` and writes `web/public/portraits/*.webp`. Play never calls it (CAP-7).
- **Output budget.** `max_completion_tokens` is a constructor argument of the adapter, not a port argument (AD-5's `chat` has no role). Its per-role value needs a new setting, for example `MAX_COMPLETION_TOKENS_<ROLE>` next to `PROVIDER_<ROLE>`. AD-14 lists every adapter setting and has none for this, so the setting needs an AD-14 amendment approved by the architect, plus a `.env.example` entry, before the providers story reads it. A starting value of 16384 per role is an assumption to tune from `usage.completion_tokens_details.reasoning_tokens` on the first live calls. Reasoning tokens count against this budget.

## API constraints

| Constraint | Value | Source |
|---|---|---|
| Base URL, auth | `https://api.meta.ai/v1`, `Authorization: Bearer <key>`; keys look like `LLM_...` | https://dev.meta.ai/docs/error-handling.md |
| Chat model and endpoint | `muse-spark-1.3`, `POST /v1/chat/completions` | https://dev.meta.ai/docs/protocols/chat-completions.md |
| Structured output | `response_format: {type: "json_schema", json_schema: {name, schema, strict}}`; the result is a JSON string in `choices[0].message.content` | https://dev.meta.ai/docs/structured-output.md |
| `json_schema.name` | `[A-Za-z0-9_-]`, up to 64 characters | https://dev.meta.ai/docs/api-reference/chat-completions/schemas.md |
| `strict` | defaults to false; output is constrained either way. `true` adds subset checks: plain-object root, no `oneOf` or `allOf`, `additionalProperties: false`, every key in `required` | https://dev.meta.ai/docs/structured-output.md |
| Schema limits (400 if exceeded) | depth 10; 5,000 properties; 120,000 combined characters; 1,000 enum values; 200,000 nodes after `$ref` inlining; no recursive `$ref` | https://dev.meta.ai/docs/structured-output.md |
| Image parts | `{type: "image_url", image_url: {url: "data:image/jpeg;base64,..."}}`, user messages only | https://dev.meta.ai/docs/image-understanding.md |
| Image limits | 50 images per request (more returns 400); 50 MB per inline image; JPEG, PNG, GIF, WebP, ICO; undecodable bytes return 400 | https://dev.meta.ai/docs/image-understanding.md |
| Image tokens | a ~1280 px image is roughly 1,300 to 1,500 input tokens, so 10 photos are about 14k | https://dev.meta.ai/docs/image-understanding.md |
| Grounding grid | 0 to 1000 on both axes, origin top left, relative to the image sent; clamp values just outside the range | https://dev.meta.ai/docs/image-understanding.md |
| `reasoning_effort` | top level; Keyframe sends `low` or `medium`, inside AD-5's allowed set (`minimal` to `xhigh`). The reasoning page also lists `max`, which Keyframe never sends. `none` returns 400 on Muse Spark | https://dev.meta.ai/docs/reasoning.md |
| Output cap | `max_completion_tokens` covers reasoning plus visible output; `max_tokens` is a deprecated alias; input plus output must fit the context | https://dev.meta.ai/docs/protocols/chat-completions.md |
| Rejected on Chat Completions (400) | `max_output_tokens`, `stop`, `n` > 1, `logprobs: true`, `logit_bias`, `verbosity`, `prediction`, `modalities`, `audio`, `web_search_options`, `text.format`, `top_p: 0` | https://dev.meta.ai/docs/protocols/chat-completions.md |
| `tool_choice` | `auto` only (enum of one value) | https://dev.meta.ai/docs/api-reference/chat-completions/schemas.md |
| Sampling | leave `temperature` and `top_p` at the 1.0 default; `seed` is accepted (best effort) on chat, but returns 400 on the images endpoint | https://dev.meta.ai/docs/protocols/chat-completions.md |
| Multi-turn reasoning | not carried on Chat Completions; `reasoning_content` is empty for external keys | https://dev.meta.ai/docs/reasoning.md |
| Spark price (standard tier) | $1.25 per 1M input, $0.15 per 1M cached input, $4.25 per 1M output (reasoning billed as output) | https://dev.meta.ai/docs/pricing-rate-limits.md |
| Spark rate limit | 3,000 RPM and 4,000,000 TPM per team, shared by all keys; `x-ratelimit-remaining-*` headers | https://dev.meta.ai/docs/pricing-rate-limits.md |
| Contributor tier | `muse-spark-1.3-contributor` trains on your data; never used (AD-5) | https://dev.meta.ai/docs/pricing-rate-limits.md |
| Image model and endpoint | `muse-image-1.0`, `POST /v1/images/generations`; `n` 1 to 10; `b64_json` by default; `webp` by default | https://dev.meta.ai/docs/image-generation.md |
| Image rejects | any unknown top-level field (`seed`), `moderation`, aspect ratio over 16:1, bad `n` or formats: 400; non-JSON content type: 415 | https://dev.meta.ai/docs/image-generation.md |
| Image price and limit | $0.01 per returned image, failed or filtered images free; 150 RPM, no TPM limit | https://dev.meta.ai/docs/pricing-rate-limits.md |
| Retry rules (vendor) | retry 429, 500 and 503 with backoff (start at 0.5 to 1 s, add jitter, honor `Retry-After`); 503 overload and backend-unavailable send `Retry-After: 60`, a deploy drain a few seconds; never retry 400, 401, 402, 403, 404 or 413; do not retry 504 unchanged. AD-13 adopts this set | https://dev.meta.ai/docs/error-handling.md |
| Baseten fallback | `https://inference.baseten.co/v1`, model `meta-models/muse-spark-open`, OpenAI-compatible | https://dev.meta.ai/docs/muse-spark-open/deploy.md |
| Baseten request fields | `json_schema.strict` is `const: true`, with no schema subset documented; `max_tokens` defaults to 4096 | https://docs.baseten.co/reference/inference-api/chat-completions.md |
| Spark Open effort default | `xhigh` (strength 512); `medium` is 32 | https://dev.meta.ai/docs/muse-spark-open/settings.md |

## Failure scenarios

The adapter retries at most once, and the single regeneration loop lives in `pipeline/regenerate.py`, never in the adapter (AD-13). AD-13 retries only what the vendor documents as retryable, and the adapter declares its sets (in the self-check):
- `CHAT_RETRYABLE_STATUS`: 429, 500 and 503 on `/chat/completions`.
- `IMAGE_RETRYABLE_STATUS`: 429 and 503 on `/images/generations`. A `muse-image-1.0` 500 is the vendor's non-retryable class.
- Never 502, 504 or any other 5xx. A 504 re-sent unchanged times out again.
- `RETRY_ON_CONNECT`: `httpx.ConnectError` and `httpx.ConnectTimeout`, where nothing reached the server. A read timeout is never re-sent.

The retry runs inside one ledger entry (AD-6). Before it, `post_with_retry` waits `Retry-After` (delta-seconds or an HTTP-date), or 0.5 to 1 s of jitter when there is none. If that wait is longer than what is left of the role's `budget_s`, the call fails at once with `ProviderError` (`retry_wait_s`): a 503 overload or backend-unavailable answer asks for 60 s, so in a 15, 30 or 45 s stage it fails at once, while `portraits.py`, with 120 s, waits and retries. Every other failure surfaces as a typed `ProviderError`, never a raw httpx exception.

| Symptom or status | Cause | What the code does | Retry |
|---|---|---|---|
| `SpendCapExceeded` before any HTTP | the estimate would pass `SPEND_CAP_USD` | the guard refuses; the build fails with that typed error; inside play the Trickster shows a skipped card (AD-4, AD-13) | no |
| Cache hit | identical key | returns the stored response, unpriced (AD-6) | n/a |
| 400 `invalid_request_error`, `param` set | rejected parameter, image on a non-user role, schema over the limits or outside the strict subset, undecodable JPEG, context exceeded | `ProviderError`; fix the request builder | no |
| 400 `content_policy_violation` | image prompt blocked by safety | `ProviderError`; edit the portrait prompt | no |
| 401 `invalid_api_key` | missing or wrong key | `ProviderError`; check `.env` or the `keyframe` secret | no |
| 402, 403, 413, 415 | billing, permission, body size, content type | `ProviderError` | no |
| 404 with `model_not_found` | wrong model id (see Known issues) | `ProviderError` | no |
| 404 with an empty body | wrong path or base URL | `ProviderError` with `type: no_body` | no |
| error body without the `{error: {...}}` envelope | proxy or gateway page | `ProviderError` with `type: unparsed` | per status |
| 429 `rate_limit_error` | team RPM or TPM exceeded | waits `Retry-After` (or 0.5 to 1 s), then one retry; a wait past the remaining `budget_s` is `ProviderError` at once | once |
| 500 on chat | transient, or the model produced malformed output | jittered backoff, one retry | once |
| 500 on images | generation failure Meta did not classify as retryable | `ProviderError` at once | no (AD-13) |
| 502, or any other 5xx Meta does not document | gateway or proxy error | `ProviderError` at once | no (AD-13) |
| 503 | deploy drain (`Retry-After` of a few seconds), overload or backend down (`Retry-After: 60`), retryable image failure | waits `Retry-After`, then one retry, if the wait fits the remaining `budget_s`; otherwise `ProviderError` at once (a 60 s overload in any build stage) | once, if it fits |
| 504 `gateway_timeout` | non-streaming call ran past the server limit | `ProviderError` at once; the stage then lowers effort or input (Riddler: re-issue at `low` per `budgets.md`) | no (AD-13) |
| `httpx.ConnectError`, `httpx.ConnectTimeout` | the connection was never made, so nothing was sent or billed | jittered backoff, one retry; a second failure is `ProviderError(None, "transport_error" or "timeout")` | once |
| `httpx.ReadTimeout`, `WriteTimeout`, `PoolTimeout` | client timeout | `ProviderError(None, "timeout")`, not re-sent because the server may still be generating and billing | no |
| any other `httpx.RequestError` (`RemoteProtocolError`, `ReadError`, ...) | connection dropped mid-request | `ProviderError(None, "transport_error")` | no |
| 200 with `finish_reason: length` | reasoning used up `max_completion_tokens` | `ProviderError`; raise the role's budget | no |
| 200 with `finish_reason: content_filter` | output filtered | `ProviderError` | no |
| 200 with a box value of 1001 | edge object on the 0 to 1000 grid | clamp at segment time; not an error | n/a |
| Baseten 200 cut off around 4k tokens | `max_tokens` left at its 4096 default | always send `max_tokens` on Baseten | no |

## Tested commands

| Command | What it proves | Result on 2026-10-21 | Where |
|---|---|---|---|
| `uv run --no-project --with httpx==0.28.1 --with pydantic==2.14.1 python .claude/skills/keyframe-muse/scripts/selfcheck.py` (uv 0.11.32, Python 3.13.16) | Pinned versions, in a clean throwaway environment with only the two pins (`--no-project` keeps uv from creating a `.venv` for the repo's `pyproject.toml`). The Architect chat body built with `httpx.Request`: model, `reasoning_effort` low, image parts only in the user message as JPEG data URLs, `strict` false, a valid schema name, no rejected parameters. `strict_schema` output fits the strict subset (oneOf rewritten to anyOf, objects closed, all keys required) for `ArchitectResponse` and for `DryRunAnswers` as a list of `{puzzle_id, answer}` (AD-12), and refuses a map-typed field (AD-2). The image body has `muse-image-1.0`, `b64_json` and no `seed`. The AD-13 sets: chat 429, 500, 503; image 429, 503; connect errors `ConnectError`, `ConnectTimeout`. On `httpx.MockTransport`: 200 parsed into `ArchitectResponse` with cost $0.006475; 400 made 1 request and no retry; 429 with `retry-after: 2` waited 2.0 s then succeeded; 429 twice gave up after 2 requests; `retry-after: 0` waited 0.0 s and an HTTP-date `Retry-After` was honored; 503 with `retry-after: 60` in a 30 s budget, and `retry-after: 2` with 1 s of budget left (fake clock), each failed at once after 1 request with no wait; chat 500 retried once after 0.5 to 1 s; chat 502, 504 and 501 failed after 1 request; image 500 failed after 1 request; image 503 with `retry-after: 60` in a 120 s budget waited 60.0 s and retried once; `ReadTimeout` and `RemoteProtocolError` raised `ProviderError` after 1 request; `ConnectTimeout` and `ConnectError` retried once; a non-envelope error body and an empty 404 raised `ProviderError` | pass: 17 lines printed, ending `selfcheck passed`, exit 0 (re-run on 2026-10-21 after the amended AD-13) | offline here (packages from uv's cache; no Meta host contacted) |
| `claude plugin validate .claude/skills` | The frontmatter of this skill (and its siblings) parses and validates | pass: `Validation passed` | offline here |
| One Architect call with 2 real downscaled photos and `ArchitectResponse` | the live API accepts the pydantic schema with `strict: false`, including the `discriminator` keyword on unions; real image token counts; `reasoning_tokens` at `low` | not run | live-only: confirm on the first live call |
| One Riddler call at `medium` | latency against the 45 s budget, 504 risk, and whether 16384 `max_completion_tokens` is enough | not run | live-only |
| One `POST /v1/images/generations` with `n: 1` | `b64_json` webp comes back; $0.01 billed | not run | live-only |
| One Baseten Riddler call with `strict_schema(RoomDraft)` and `strict: true` | Baseten accepts the strict schema and `reasoning_effort: medium`, and whether it enforces Meta's strict subset (assumed, not documented by Baseten) | not run | live-only (Tue Oct 27, per `stack.md`) |

## Known issues

- `src/providers/meta_api.py` sets `IMAGE_MODEL_PLACEHOLDER = "muse-image"`, but the model id is `muse-image-1.0`. As written, image calls would return 404 `model_not_found`. The same scaffold also has `DEFAULT_BASE_URL = "https://api.meta.com/v1"` (it should be `https://api.meta.ai/v1`, as the Conventions row says) and `CHAT_MODEL_PLACEHOLDER = "muse-spark"` (it should be `muse-spark-1.3`). It uses urllib and defaults `temperature` to 0.7, which AD-5's port drops. Fix all of these in the first providers story.
- Baseten documents no strict subset. The code assumes Meta's (no `oneOf`, no open maps) until the Tue Oct 27 live call shows otherwise. The schema side is settled in AD-2 and AD-12: tagged unions go with `strict: false` on Meta, and no model-response schema has a map-typed field, so `strict_schema(RoomDraft)` can express the fallback.
- The vendor docs disagree in three places. The reasoning page names `max_tokens` for Chat Completions while the protocol page names `max_completion_tokens`; use `max_completion_tokens`. The error-retry cookbook retries every 5xx while the error-handling guide excludes 504; AD-13 follows the guide. The reasoning page and the API reference list a `max` effort that the protocol page's parameter table omits; AD-5 does not allow it either, so Keyframe never sends it.

## References

- https://dev.meta.ai/llms.txt: index of every Meta Model API page.
- https://dev.meta.ai/docs/protocols/chat-completions.md: parameters, defaults, rejected OpenAI parameters, message structure.
- https://dev.meta.ai/docs/api-reference/chat-completions/schemas.md: field-level request and response schema (`tool_choice`, `json_schema.name`, `usage`, `finish_reason`).
- https://dev.meta.ai/docs/structured-output.md: `json_schema`, strict subset, schema limits.
- https://dev.meta.ai/docs/image-understanding.md: image parts, user-only rule, limits, token cost, 0 to 1000 grounding grid.
- https://dev.meta.ai/docs/reasoning.md: `reasoning_effort` values, `none` returns 400, reasoning tokens in the budget and the bill.
- https://dev.meta.ai/docs/error-handling.md: error envelope, every status code, retry strategy, 504 guidance.
- https://dev.meta.ai/docs/pricing-rate-limits.md: prices, per-team rate limits, rate-limit headers.
- https://dev.meta.ai/docs/image-generation.md: images endpoints, parameters, response shape, errors, pricing.
- https://dev.meta.ai/docs/cookbook/structured-output.md, https://dev.meta.ai/docs/cookbook/vision-input.md, https://dev.meta.ai/docs/cookbook/reasoning-thinking-tokens.md, https://dev.meta.ai/docs/cookbook/error-handling-retry.md: worked Python recipes for the same calls.
- https://dev.meta.ai/docs/cookbook/anchored-image-series.md: keeping a series of images consistent by chaining Responses turns.
- https://dev.meta.ai/docs/sdks.md: no Meta-specific client is needed; any OpenAI-compatible client with the base URL works.
- https://llama.developer.meta.com/docs/: the old Llama API docs host, which redirected to https://dev.meta.ai/docs/overview when checked on 2026-10-21.
- https://dev.meta.ai/docs/muse-spark-open/deploy.md and https://dev.meta.ai/docs/muse-spark-open/settings.md: Baseten endpoint and model string, open-weight reasoning defaults.
- https://docs.baseten.co/reference/inference-api/chat-completions.md: Baseten Chat Completions schema (`strict`, `max_tokens`, `reasoning_effort`).
