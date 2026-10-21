# SAM 3D Objects on fal: wire format, headers, retries, errors

Checked on 2026-10-21 against the live OpenAPI document (https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/sam-3/3d-objects), the model's llms.txt, and the fal-client 1.0.3 source. `scripts/selfcheck.py` holds a copy of the input and output schemas and validates against them.

## Input (`SAM3DObjectInput`)

| Field | Type | Default | Keyframe |
|---|---|---|---|
| `image_url` | string, required | none | data URI of the upright original hero photo |
| `mask_urls` | list of string | none | one data-URI PNG per object; Keyframe sends exactly one |
| `prompt` | string or null | `"car"` | always the interactable's `label` |
| `point_prompts` | list of `{x, y, label, object_id}` | `[]` | not sent; integers (pixels, inferred), `label` 1 = foreground, 0 = background |
| `box_prompts` | list of `{x_min, y_min, x_max, y_max, object_id}` | `[]` | not sent; integers (pixels, inferred); boxes sharing an `object_id` refine one object |
| `seed` | integer or null | none | fixed (`SEED`), part of the cache key |
| `pointmap_url` | string or null | none | not sent (NPY or NPZ depth) |
| `detection_threshold` | number 0.1 to 1.0, or null | model default | not sent |
| `export_textured_glb` | boolean | `false` | not sent; `true` bakes a texture with UVs instead of vertex colors |

- Prompt objects are JSON objects, never arrays. The 2025 developer guide's `box_prompts: [[x1, y1, x2, y2]]` and `mask_url` are wrong for this endpoint.
- The schema does not set `additionalProperties: false`, so it does not reject a misspelled key such as `mask_url`. That the server then ignores such a key silently is inferred from the schema, not documented. The selfcheck asserts that every key Keyframe sends is a declared property.
- The schema types prompt coordinates as integers only; that they are image pixels is inferred from the field names and the developer guide, not stated in the schema.
- Points that carry an `object_id` while a text prompt is also set choose which detected object the points refine.

## Output (`SAM3DObjectOutput`)

| Field | Required | Notes |
|---|---|---|
| `gaussian_splat` | yes | `File` (.ply): the combined scene for several objects, otherwise the single object |
| `metadata` | yes | list of `SAM3DObjectMetadata`, one per object |
| `model_glb` | no | `File` (GLB): combined scene or single mesh. Its schema default is a sample scene URL, so treat that URL as missing |
| `individual_splats`, `individual_glbs` | no | only for multi-object scenes |
| `artifacts_zip` | no | zip of all artifacts and metadata |

- `File` is `{url (required), content_type, file_name, file_size}`. The example response in llms.txt shows `image/png` for every file; that is placeholder text, so check the file signature (`glTF` for GLB, `ply` for PLY) instead.
- `SAM3DObjectMetadata` is `{object_index (required), scale, rotation, translation, camera_pose}`. Each of the last four is typed as a **list of lists of numbers** (or null), even though the descriptions read `[sx, sy, sz]`, `[x, y, z, w]` quaternion, `[tx, ty, tz]` and "camera pose matrix". Store the raw values in `Interactable.tier2` and confirm the nesting on the first live call before composing a room layout (spine Deferred: placement).

## Queue protocol (what `subscribe` does)

1. `POST https://queue.fal.run/fal-ai/sam-3/3d-objects` with the JSON arguments. The response holds `request_id`, `status_url`, `response_url` and `cancel_url`.
2. Poll `GET .../requests/{id}/status` until `status` is `COMPLETED` (`IN_QUEUE` carries `queue_position`, `IN_PROGRESS` carries logs). A failed request also ends `COMPLETED`, with `error` and `error_type`.
3. `GET .../requests/{id}` returns the model's own status code and body. A model failure therefore surfaces here, as `FalClientHTTPError`.
4. `PUT .../requests/{id}/cancel` removes a queued request, or signals the runner if it is in progress.

`subscribe` runs steps 1 to 3. `submit` returns a `SyncRequestHandle` after step 1. `status(app, id)`, `result(app, id)` and `cancel(app, id)` exist both on the module and on `SyncClient`, so a restarted runner can pick up a recorded `request_id` instead of paying again. With `X-Fal-Store-IO: 0` a result stays retrievable only until the stored result expires: about 1 hour after the request completes, or about 6 minutes for results of 10 KB or more (https://fal.ai/docs/documentation/model-apis/inference/webhooks.md). A SAM 3D result body with its metadata may well pass 10 KB, so after a client timeout call `result(app, request_id)` within a few minutes, before paying for a re-run.

Webhooks are optional and not used by Keyframe: `submit(..., webhook_url=...)` makes fal POST `{request_id, status: "OK" | "ERROR", payload}` to a public HTTPS URL. Deliveries are signed with ED25519 and retried, and redirects or private addresses are dropped. Polling inside the spawned runner is simpler.

## Platform headers Keyframe sets

| Header | Value | Effect |
|---|---|---|
| `X-Fal-Store-IO` | `"0"` | inputs and outputs are not kept in request history (90 days by default). Only settable through `headers` |
| `X-Fal-Object-Lifecycle-Preference` | `{"expiration_duration_seconds": 3600}` | generated CDN files expire after an hour; download them first |
| start timeout (`start_timeout=`) | 120 | the server returns 504 with `X-Fal-Request-Timeout-Type: user` if no runner has started by then, and retries stop. fal-client 1.0.3 sends it as `X-Fal-Request-Timeout`; the docs name `X-Fal-Request-Start-Timeout` |

Not used: `X-Fal-No-Retry` (turns off the queue's retries), `X-Fal-Queue-Priority` (`priority=`), `X-Fal-Runner-Hint` (`hint=`), and `x-app-fal-disable-fallback`.

## Who retries what

| Layer | Retries | Limit |
|---|---|---|
| fal queue (server) | 503, 504 and connection errors from the runner, re-queued with backoff | 10 attempts; stops at the start-timeout deadline |
| fal queue, concurrency | none needed: the queue never returns the concurrency 429 (only the sync API does); the request waits in `IN_QUEUE`, which does not count as a retry | none (new accounts get 2 concurrent requests, rising with credit purchases up to 40) |
| fal-client 1.0.3 (each HTTP call: submit, status, result, cancel) | 408, 409, 429, 502/503/504 that look like ingress errors (no `x-fal-request-id`), transport errors, read timeouts without a user timeout header | 10 attempts, exponential backoff from 0.1 s capped at 30 s, with jitter; one backup-domain attempt (`queue.falrun.com`) |
| Keyframe adapter (`retry_once`) | AD-13: one retry with 2 to 4 s backoff on a surfaced 429 or 5xx; never on a client timeout | 2 attempts, one ledger entry. A 5xx is unbilled, so the retry costs time only |
| synchronous `run` | none on the server | not used |

## Error bodies

- **Request errors** (infrastructure): `{"detail": "<text>", "error_type": "<type>"}`, with the same value in `X-Fal-Error-Type`. Types: `request_timeout` and `startup_timeout` (504); `runner_scheduling_failure`, `runner_connection_timeout`, `runner_disconnected`, `runner_connection_refused` and `runner_connection_error` (503); `runner_incomplete_response` (502); `runner_server_error` and `internal_error` (500); `client_cancelled` and `client_disconnected` (499); `bad_request` (400, for example an invalid timeout header). fal-client puts these in `FalClientHTTPError.error_type`. The queue's own retries cover 503, 504 and connection errors only, so a 500 or 502 reaches the client without a server-side retry (https://fal.ai/docs/documentation/model-apis/request-errors.md, https://fal.ai/docs/documentation/model-apis/inference/reliability.md).
- **Model errors**: `{"detail": [{"loc", "msg", "type", "url", "ctx"?, "input"?}]}`, plus an `X-Fal-Needs-Retry` header that fal says to read for retry decisions (https://fal.ai/docs/documentation/model-apis/errors.md). Branch on `type`, never on `msg`.
  - 422, never retryable: types that fit this model include `image_load_error`, `file_download_error`, `image_too_small`, `image_too_large`, `unsupported_image_format`, `file_too_large` (ctx `max_size`), `no_media_generated`, `content_policy_violation` and `value_error`. Any unlisted `type` (pydantic passthrough such as `missing`) is a non-retryable 422 too.
  - 500 (`internal_server_error`, `downstream_service_error`, `downstream_service_unavailable`) and 504 (`generation_timeout`): retryable "true or false" per fal, decided by `X-Fal-Needs-Retry`. `classify` settles them at $0 like any 5xx, and `retry_once` retries them once regardless of the header (AD-13).
  - fal-client sets `str(exc)` to the `detail` list for these bodies, so `classify` reads `exc.response.json()` instead.
- **Ingress 413**: an oversized request body may be refused before it reaches fal's queue. The body is not documented, so `classify` records it as `fal_http_413`, billed at $0.02 until the dashboard says otherwise. The fix is the upload fallback in references/adapter.md, not a retry.
- The developer guide describes a 400 as invalid image format or quality and a 422 as segmentation finding no object. Treat both as permanent for the same input.
