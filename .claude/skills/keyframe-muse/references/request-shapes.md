# Wire shapes for Muse Spark 1.3, Muse Image 1.0 and the Baseten fallback

Checked against the official pages on 2026-10-21. `scripts/selfcheck.py` builds and asserts the request bodies below offline.

## Chat Completions request (Architect)

`POST https://api.meta.ai/v1/chat/completions`, headers `Authorization: Bearer <META_MODEL_API_KEY>` and `Content-Type: application/json`.

```json
{
  "model": "muse-spark-1.3",
  "messages": [
    {"role": "system", "content": "<fixed Architect instructions>"},
    {"role": "user", "content": [
      {"type": "text", "text": "<task text from council/architect.py>"},
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<photo 0>"}},
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,<photo 1>"}}
    ]}
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {"name": "ArchitectResponse", "schema": {"...": "ArchitectResponse.model_json_schema()"}, "strict": false}
  },
  "reasoning_effort": "low",
  "max_completion_tokens": 16384
}
```

Rules behind the shape:
- System and developer content is text only. Image parts go in `user` messages. The guide says images on other roles are not processed; the vision cookbook says they are rejected with 400. Either way, never send them there.
- Images are sent in upload order so `photo` indexes in the response match `photos[]` (AD-18). Each part may also carry `image_url.detail` (`auto`, `low`, `high`; default `auto`). Keyframe leaves it unset.
- `max_completion_tokens` caps reasoning plus visible output. `max_tokens` is a deprecated alias that still works. `max_output_tokens` belongs to the Responses API and is rejected here. Input plus requested output must fit the context window, and asking for more than the model's maximum returns 400.
- Leave `temperature` and `top_p` unset (both default to 1.0, where Muse Spark is tuned). `seed` is accepted as a best-effort hint, but Keyframe does not need it because the cache key already makes repeat calls identical.

## Chat Completions response

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "muse-spark-1.3",
  "choices": [{"index": 0, "finish_reason": "stop",
               "message": {"role": "assistant", "content": "{\"objects\": [...]}"}}],
  "usage": {"prompt_tokens": 14210, "completion_tokens": 900, "total_tokens": 15110,
            "prompt_tokens_details": {"cached_tokens": 0},
            "completion_tokens_details": {"reasoning_tokens": 600}}
}
```

- Parse `choices[0].message.content` with `Model.model_validate_json`.
- `finish_reason` is one of `stop`, `length`, `tool_calls`, `content_filter`, `function_call`. Accept only `stop`. `length` means the budget ran out, usually spent on reasoning, and the JSON is cut off.
- `reasoning_tokens` are part of `completion_tokens` and are billed at the output rate. `message.reasoning_content` is empty for external keys, so never read it.
- Cost: `(prompt_tokens - cached_tokens) * 1.25 + cached_tokens * 0.15 + completion_tokens * 4.25`, divided by 1,000,000, in USD (`chat_cost_usd` in the self-check).

## Error envelope

```json
{"error": {"message": "...", "type": "invalid_request_error", "param": "top_p", "code": null}}
```

- `type` is `invalid_request_error` (4xx validation and not-found), `authentication_error` (401), `rate_limit_error` (429) or `server_error` (5xx).
- `code` is often null on validation errors, so branch on the status and `type`. Codes that do appear include `invalid_api_key`, `model_not_found`, `rate_limit_exceeded`, `server_shutting_down`, `service_overloaded`, `backend_unavailable`, `payload_too_large`, `gateway_timeout` and `content_policy_violation`.
- A 404 for an unknown path has an empty body. Only matched endpoints return the envelope.

## Structured output: schema limits and the strict subset

Limits checked before decoding. Exceeding any of them returns 400, whatever `strict` is set to:

| Constraint | Limit |
|---|---|
| Nesting depth | 10 levels |
| Properties, whole schema | 5,000 |
| Combined string length (property names, definition names, enum and const values) | 120,000 characters |
| Enum values, all enums | 1,000 (raisable per app) |
| One string enum over 250 values | 15,000 combined characters |
| Expanded size after inlining `$ref` | 200,000 nodes |
| Recursive `$ref` | rejected |

`strict` defaults to false. Output is constrained to the schema either way. `strict: true` only adds a server check that the schema fits this subset, and a violation returns 400:
- The root is a plain object, with no `anyOf`, `oneOf`, `allOf`, `enum` or `not` at the top.
- No `allOf` or `oneOf` anywhere. `anyOf` is allowed below the root.
- Every object sets `additionalProperties: false`.
- Every object lists all of its `properties` in `required`.
- The rules also apply inside `$defs` and `definitions`.

Pydantic emits discriminated unions (AD-2's tagged unions) as `oneOf` with a `discriminator` keyword, and `dict[str, X]` as an object whose `additionalProperties` is a schema. Neither fits the strict subset. `strict_schema()` in the self-check inlines `$defs`, rewrites `oneOf` to `anyOf`, drops `discriminator`, closes every object, fills `required`, and refuses map-typed fields.

`json_schema.name` allows `a-z`, `A-Z`, `0-9`, `_` and `-`, up to 64 characters. Pydantic class names fit.

## Images API request and response (portraits)

`POST https://api.meta.ai/v1/images/generations`:

```json
{"model": "muse-image-1.0", "prompt": "<portrait prompt>", "n": 1,
 "response_format": "b64_json", "output_format": "webp"}
```

```json
{"created": 1784584435, "data": [{"b64_json": "UklGR..."}], "output_format": "webp",
 "background": "opaque", "usage": {"input_tokens": 9831, "output_tokens": 749, "total_tokens": 10580}}
```

- `n` is 1 to 10. `response_format` is `b64_json` (the default) or `url` (a temporary signed URL). `output_format` is `webp` (the default), `png` or `jpeg`.
- `size` takes a `"WxH"` string that sets only the aspect ratio. Aspect ratios beyond 16:1 return 400.
- Meta extensions sit at the top level: `reasoning_strength` (`high` by default, or `low`) and `tool_enablement` {`enable_image_search`, `enable_web_search`, `enable_shell`}. The price is the same either way.
- Any unknown top-level field, `seed` included, returns 400 with the field named in `param`. `moderation` returns 400 on `muse-image-1.0`.
- A content-safety block is 400 `content_policy_violation` with `param: prompt`. A retryable generation failure is 503 `server_error`. A non-retryable failure is 500.
- A request is billed $0.01 per returned image (`n` images cost `n` cents). Images that fail or are filtered are not billed. The limit is 150 requests per minute per team.
- For a matched set of four portraits, the documented consistency technique chains turns with `previous_response_id` on the Responses API (anchored image series cookbook). That would be a change to the spine's `generate_image(prompt)` port, so raise it first rather than doing it silently.

## Baseten fallback (Riddler only)

`openai_compatible` adapter, same Chat Completions body with these differences:

| Field | Meta Model API | Baseten Model APIs |
|---|---|---|
| Base URL | `https://api.meta.ai/v1` | `https://inference.baseten.co/v1` |
| Auth | `Bearer META_MODEL_API_KEY` | `Bearer OPENAI_COMPATIBLE_API_KEY` (a Baseten key) |
| `model` | `muse-spark-1.3` | `meta-models/muse-spark-open` |
| Output cap | `max_completion_tokens` | `max_tokens` (default 4096, so always set it) |
| `json_schema.strict` | false (the default) | schema says `const: true`: send `strict_schema(Model)` with `strict: true`. Baseten documents no schema subset; Meta's subset (no `oneOf`, no open maps) is assumed until the Oct 27 live call |
| `reasoning_effort` | omitted means model-set | open-weight default is `xhigh` (strength 512), so always send `medium` |

Baseten also documents `stop` and the `x-ratelimit-*` headers, and serves the full 1,048,576-token context with image input. Whether one strict schema-constrained Riddler call succeeds is the Tue Oct 27 live check in `stack.md`. If it fails, fall back to plain-JSON prompting with validator retry.
