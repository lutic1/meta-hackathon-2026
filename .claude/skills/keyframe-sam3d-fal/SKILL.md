---
name: keyframe-sam3d-fal
description: Calls SAM 3D Objects on fal.ai (fal-ai/sam-3/3d-objects) through fal-client 1.0.3 to turn one original-resolution hero photo plus a sam-3.1 object mask into a GLB, a Gaussian splat and pose metadata for Keyframe's Tier 2 room. Use when writing, testing or debugging the fal ModelProvider adapter in src/providers/fal.py and its reconstruct3d(image, mask) port, building mask_urls from Interactable polygons, fal queue calls (subscribe, submit, client_timeout, start_timeout), fal 400, 422 and 5xx handling, caching and spend for the $0.02 reconstructions, downloading GLBs before fal URLs expire, filling Interactable.tier2, the mock provider's reconstruct3d fixture, or the pre-Oct 26 five-object SAM 3D spike script. Do not use for sam-3.1 segmentation on the Meta Responses API, Muse Spark or Muse Image calls, Modal deployment, three.js GLB or splat rendering, Tier 3 Scaniverse splats, other fal models, or the Runware and Segmind fallbacks.
when_to_use: Trigger phrases such as "SAM 3D", "sam-3/3d-objects", "reconstruct3d", "Tier 2 GLB", "fal_client.subscribe", "FAL_KEY", "mask_urls", "fal 422", "GLB from a photo", "hero photo per wall".
paths:
  - "src/providers/fal.py"
  - "tests/providers/**/test_fal*.py"
  - "tests/fixtures/fal/**"
  - "scripts/*sam3d*.py"
---

# SAM 3D Objects on fal.ai for Keyframe (Tier 2)

All facts below were checked on 2026-10-21 against the official fal pages and the fal-client 1.0.3 source. The helpers named here are written out and tested in [references/adapter.md](references/adapter.md). Field-level schemas, headers, the retry layers and the error bodies are in [references/wire-and-errors.md](references/wire-and-errors.md). [scripts/selfcheck.py](scripts/selfcheck.py) checks both offline.

## When to use

Use this skill for:
- The `fal` adapter in `src/providers/fal.py`. It is the only implementation of `reconstruct3d(image, mask: Mask3D) -> GlbRef` besides the mock (AD-5).
- The Tier 2 objects, CAP-11: one call per interactable on its wall's original-resolution hero photo, at most 20 GLBs (SPEC Constraints).
- Writing `Interactable.tier2`, the GLB path and placement. It is the only schema field in original-photo pixels (AD-18, schema v1).
- Adapter tests under `tests/providers/` that replay recorded fixtures from `tests/fixtures/fal/` (AD-17).

Before writing any of it, check the gate. Tier 2 is a default no-go. It is attempted Sun Nov 1 only if the Tier 1 backup video exists Sat Oct 31 night, and it is judged at the Mon Nov 2 gate: 7 of 10 interactables recognizable in position, 30 fps or better on the M1, puzzles triggered by raycast. Any miss ships Tier 1 (delivery plan, SPEC CAP-11). The only earlier spend is the five-object verification before Oct 26, within the fal ceiling of $6 (`budgets.md`); name its script `scripts/<name>_sam3d.py` (or any `scripts/*sam3d*.py`) so this skill loads with it.

Never make a live fal call (`subscribe` or `submit` with a real `FAL_KEY`), the five-object spike included, unless the user explicitly asks for it. Dev loops and tests use the mock provider and recorded fixtures.

Do not use it for:
- The sam-3.1 masks themselves (`keyframe-sam31`), or the Muse calls (`keyframe-muse`).
- Running SAM 3D anywhere else. It is cloud only, through fal: never on a Modal GPU and never on the Mac (SPEC Constraints).
- Rendering the GLB or splat in `web/scene`, Tier 3 Scaniverse splats, or the fallbacks (Runware, Segmind, hand-made assets, photo billboard).

## How Keyframe calls it

There is one path. The adapter owns the fal client, Pillow, the cache, the spend ledger and the downloads. Nothing upstream sees a fal URL.

1. **Inputs.** `image` is the stored original JPEG of the hero photo, read byte for byte from ingest (AD-7). `mask` is a `Mask3D {label, polygons, frame_size}` from `src/domain/schema.py` (AD-5), built from the interactable's persisted `polygons` (frame pixels of the 1280 px JPEG), the frame size and its `label`.
2. **Prepare** (in the adapter, because AD-1 keeps Pillow out of `domain` and `pipeline`):
   - `upright_jpeg` applies a non-1 EXIF orientation;
   - `mask_png` scales the `Mask3D` polygons to the upright original and fills them into a binary PNG of exactly that size;
   - `build_arguments` sets `image_url` and `mask_urls` as data URIs, `prompt` to `Mask3D.label` (AD-5; the API default is `"car"`), and a fixed `seed`.
3. **Guard** (AD-6): `Cache.get_or_call(cache_key(image, mask, label, seed, attempt))`. On a miss only, `SpendLedger.guard("reconstruct3d", 0.02)`. The spine seeds that estimate at $0.02.
4. **Call.** `run_queued` calls `SyncClient.subscribe` with `X-Fal-Store-IO: 0`, a one-hour output lifecycle, `start_timeout=120`, `client_timeout=300` and a 1 s poll. `on_enqueue` writes the fal `request_id` into the job's call row (AD-16). `retry_once` wraps it: one retry with backoff, only on fal's retryable set (AD-13): a 429, a 5xx whose `X-Fal-Needs-Retry` allows it, or a connect error.
5. **Keep.** `parse_result` requires a real `model_glb`, `gaussian_splat` and `metadata`, or raises `NoMeshError`. `fetch` downloads the GLB and the splat right away and checks their signatures, then `ArtifactStore.put` writes `tier2/<ix_id>.glb` and `.ply` beside the Room. Hosted, that is the Volume, ending with `commit()` (AD-7). The cache value is the artifact keys plus the raw metadata, never the expiring fal URLs.
6. **Record.** Write `Interactable.tier2` with the GLB artifact path, plus a placement from fal's `metadata` if it composes into a room layout, or hand-placed otherwise (spine Deferred).

```python
# src/providers/fal.py, FalProvider.reconstruct3d(self, original_jpeg: bytes, mask: Mask3D) -> GlbRef
# (shape only; helpers from references/adapter.md)
client = fal_client.SyncClient(key=self.settings.fal_key)     # never the module-level fal_client.* calls
image, size = upright_jpeg(original_jpeg)
mask_bytes = mask_png(mask, size)
args = build_arguments(image, mask_bytes, mask.label)        # AD-5: the fal prompt is the label

def call() -> dict:
    call_id = self.ledger.guard("reconstruct3d", PRICE_USD)   # SpendCapExceeded before any HTTP
    cost = PRICE_USD                                           # anything unclassified settles billed
    try:
        rec = parse_result(retry_once(lambda: run_queued(client, args, self.calls.record_request_id)))
        glb = fetch(self.http, rec.glb_url, GLB_MAGIC)
        ply = fetch(self.http, rec.splat_url, PLY_MAGIC)
    except (fal_client.FalClientError, httpx.HTTPError, NoMeshError) as exc:
        failure = classify(exc)
        cost = PRICE_USD if failure.billed else 0.0
        raise ProviderError(failure.status, failure.code, "reconstruct3d failed") from exc
    finally:
        self.ledger.settle(call_id, cost)                      # every reserved entry is settled
    return {"glb": self.artifacts.put(f"{prefix}/{ix_id}.glb", glb),
            "splat": self.artifacts.put(f"{prefix}/{ix_id}.ply", ply),
            "metadata": rec.metadata}

return GlbRef(**self.cache.get_or_call(cache_key(image, mask_bytes, mask.label), call))
```

- **Key.** `FAL_KEY` comes only from `Settings` (AD-14; the first providers story adds `fal_key` to `Settings` and a blank `FAL_KEY` to `.env.example`). Locally it lives in `.env`, which is git-ignored and never committed. Hosted, it lives in the `keyframe` `modal.Secret`. Pass it as `SyncClient(key=...)`. The module-level `fal_client.subscribe` reads `FAL_KEY` from `os.environ` itself, which AD-14 forbids outside `Settings`.
- **Where it runs.** Run it in the spawned stage runner (`@app.function(timeout=900)`) or in a local script, never inside an ASGI request, because Modal web requests time out at 150 s. `subscribe` blocks a thread: fan objects out through the same bounded thread pool the segment stage uses. A new fal account runs only 2 requests at once and queues the rest.
- **Retries.** `retry_once` implements AD-13: one retry, inside the same ledger entry (AD-6), only on what fal documents as retryable. `is_retryable` declares the set: a 429 always, a 5xx only when `X-Fal-Needs-Retry` allows it, and a connect error (`httpx.ConnectError`, `httpx.ConnectTimeout`). The wait is `Retry-After` or 0.5 to 1 s of jitter; a wait longer than what is left of `budget_s` (default `CLIENT_TIMEOUT_S`, 300 s, since `budgets.md` gives Tier 2 no stage budget) fails at once. Below it, the fal queue retries runner 503s, 504s and connection errors up to 10 times, and fal-client retries each HTTP call on any 408, 409 or 429 and on ingress errors. A 5xx is unbilled, so the adapter's retry costs time only. A client timeout is never retried.
- **Privacy.** Room photos go to fal only in Tier 2, as the capture screen discloses (`stack.md` privacy line). `X-Fal-Store-IO: 0` keeps the photo and the outputs out of fal's 90-day request history. The photo goes as a data URI so it never becomes a public CDN object, although fal calls data URIs "not recommended for files larger than a few KB"; that no copy of a data-URI input persists is unverified and is on the live-only list. If an upload is needed, the private form sets `initial_acl` to `forbid` or `hide` (references/adapter.md). The fal MCP relay's `store_payload: false` is the same idea for dev-time tool calls (https://fal.ai/docs/documentation/model-apis/mcp.md); it is not a fal-client parameter.
- **Mock.** The mock provider returns a fixture GLB from `tests/fixtures/fal/` and never imports `fal_client`. Offline tests replay recorded queue responses through `httpx.MockTransport`, as the selfcheck does.

## API constraints

| Constraint | Value | Source |
|---|---|---|
| Endpoint | `fal-ai/sam-3/3d-objects`; sync host `https://fal.run` | https://fal.ai/models/fal-ai/sam-3/3d-objects/llms.txt |
| Queue host | `https://queue.fal.run` (OpenAPI `servers`) | https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/sam-3/3d-objects, https://fal.ai/docs/documentation/model-apis/inference/queue.md |
| Price | $0.02 "per unit", unit not defined; assumed one request with one mask; confirm on the usage dashboard | https://fal.ai/models/fal-ai/sam-3/3d-objects/llms.txt |
| Client | `fal-client==1.0.3` (released 2026-09-21; 0.9.0 is yanked) | https://pypi.org/project/fal-client/ |
| Auth | `Authorization: Key <FAL_KEY>`; `SyncClient(key=None, default_timeout=120.0)` | https://fal.ai/docs/api-reference/client-libraries/python/fal_client.md |
| Key fallback | with `key=None`, fal-client reads `FAL_KEY` (or `FAL_KEY_ID` and `FAL_KEY_SECRET`) from the environment | fal-client 1.0.3 source, `fal_client/auth.py` (not in the docs) |
| Required input | `image_url` only; a public URL or a base64 data URI. fal: data URIs are "not recommended for files larger than a few KB" | https://fal.ai/models/fal-ai/sam-3/3d-objects/api, https://fal.ai/docs/documentation/model-apis/fal-cdn.md |
| Masks | `mask_urls`: list, one mask per object; used instead of auto-segmentation | https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/sam-3/3d-objects |
| `prompt` | string, default `"car"`; used for auto-segmentation when no mask is given | same OpenAPI document |
| Point and box prompts | objects `{x, y, label 0/1, object_id}` and `{x_min, y_min, x_max, y_max, object_id}`, integers (pixel units inferred, not stated), default `[]` | same OpenAPI document |
| Other inputs | `seed` integer; `detection_threshold` 0.1 to 1.0; `export_textured_glb` default false; `pointmap_url` NPY or NPZ | same OpenAPI document |
| Unknown keys | the schema does not forbid them (no `additionalProperties: false`); that the server silently ignores a typo is inferred, not documented | same OpenAPI document |
| Outputs | required: `gaussian_splat` (.ply) and `metadata`; optional: `model_glb`, `artifacts_zip`; `individual_glbs` and `individual_splats` only for multi-object scenes | same OpenAPI document |
| `model_glb` default | the schema's default is a sample scene URL; treat it as no mesh | same OpenAPI document |
| Metadata | per object `object_index`, plus `scale`, `rotation` (quaternion x, y, z, w), `translation` and `camera_pose`, each typed as a list of lists of numbers | same OpenAPI document |
| `subscribe` | submit, poll status, fetch result; `on_enqueue(request_id)` | https://fal.ai/docs/documentation/model-apis/inference/queue.md |
| Poll interval | `interval` default 0.1 s | https://fal.ai/docs/api-reference/client-libraries/python/fal_client.md |
| `client_timeout` | `subscribe` only; total wait; unset means wait forever; when set alone it also becomes `start_timeout` | https://fal.ai/docs/documentation/model-apis/inference/queue.md |
| `start_timeout` | server deadline until a runner starts (queue, retries, routing); past it, 504 with `X-Fal-Request-Timeout-Type: user` and no more retries | https://fal.ai/docs/documentation/model-apis/common-parameters.md |
| Per-HTTP timeout | 120 s for submit and each poll (`default_timeout`) | https://fal.ai/docs/api-reference/client-libraries/python/fal_client.md |
| Queue retries | 503, 504 and connection errors only, up to 10 attempts; sync calls get no retry | https://fal.ai/docs/documentation/model-apis/inference/reliability.md |
| Billing on failure | failed requests returning 5xx are not billed | https://fal.ai/docs/documentation/model-apis/inference/reliability.md |
| Concurrency | new accounts get 2 requests in progress, up to 40 self-serve as credits are bought; the queue never returns the concurrency 429, it holds the request in `IN_QUEUE` | https://fal.ai/docs/documentation/model-apis/concurrency-limits.md, https://fal.ai/docs/documentation/model-apis/request-errors.md |
| Request history | inputs and outputs kept 90 days unless `X-Fal-Store-IO: 0` | https://fal.ai/docs/documentation/model-apis/media-expiration.md |
| Output files | public CDN URLs; `X-Fal-Object-Lifecycle-Preference` sets expiry; expired files are deleted for good | https://fal.ai/docs/documentation/model-apis/media-expiration.md |
| Error bodies | request errors: `{detail, error_type}`; model errors: `detail: [{loc, msg, type, url, ctx}]`; 422 types are non-retryable; 500/504 types (`internal_server_error`, `generation_timeout`, `downstream_service_*`) may be retryable per the `X-Fal-Needs-Retry` header | https://fal.ai/docs/documentation/model-apis/request-errors.md, https://fal.ai/docs/documentation/model-apis/errors.md |
| Stored result window | with `X-Fal-Store-IO: 0`, `result()` works until the stored result expires: about 1 h after completion, about 6 min for results of 10 KB or more | https://fal.ai/docs/documentation/model-apis/inference/webhooks.md |
| Webhooks | optional, `submit(webhook_url=...)` only; signed, retried, no redirects | https://fal.ai/docs/documentation/model-apis/inference/webhooks.md |
| Input quality | at least 512 px on the short side (shared best practices); glass, mirrors, chrome and harsh shadows reconstruct poorly. The 40 to 50% occlusion limit is stated for SAM 3D Body (humans) only | https://fal.ai/learn/devs/sam-3d-developer-guide (Dec 2025, partly outdated) |
| Latency | 4 to 8 s nominal for SAM 3D Objects; 15 to 30 s or more for inputs of 2048 px and above, for which the guide asks for a 60 s+ timeout; `client_timeout=300` covers both | https://fal.ai/learn/devs/sam-3d-developer-guide |

## Failure scenarios

| Symptom or status | Cause | What the code does | Retry |
|---|---|---|---|
| `SpendCapExceeded` before any HTTP | the $0.02 estimate would pass `SPEND_CAP_USD` | the guard refuses; the object keeps `tier2: null` | no |
| Cache hit | same image, mask, label, seed and attempt | returns the stored artifact keys and metadata, unpriced (AD-6) | n/a |
| Empty `fal_key` in `Settings` | `FAL_KEY` not set | `wiring.py` refuses to build the `fal` provider. With `key=None`, fal-client would fall back to the environment or saved `fal auth login` tokens, and its `MissingCredentialsError` is a plain `Exception`, not a `FalClientError` | no |
| 401 or 403 | wrong or revoked key | `ProviderError`; check `.env` or the `keyframe` secret | no |
| 400 `bad_request` on submit | malformed request, for example an invalid timeout header | `ProviderError`; fix the builder | no |
| 422 `image_load_error`, `file_download_error`, `unsupported_image_format`, `image_too_small`, `image_too_large`, `file_too_large` | the data URI or the image itself was rejected | `ProviderError` with the `type`; if size is the problem, switch the photo to an upload (references/adapter.md) | no |
| 422 `no_media_generated`, or any other 422 | no object reconstructed from that mask (the guide's "segmentation failure") | `ProviderError`; the object falls back (photo billboard or hand-made asset). A deliberate re-run with `box_prompts` uses `attempt=1` in the key | no |
| More requests than the account concurrency cap | more than the allowed requests in progress | nothing: the cap never errors on the queue; the request waits in `IN_QUEUE` | n/a |
| 429 on any queue HTTP call | not the concurrency cap (the queue never returns that 429); some other rate limit | fal-client retries any 429 up to 10 times; a 429 that still surfaces gets `retry_once` after `Retry-After` (at once `ProviderError` if that is past the budget), then `ProviderError`, settled at $0.02 (conservative) | automatic, then once |
| 503 `runner_*`, 504 `request_timeout` or `startup_timeout` | runner failure | the queue retries up to 10 times; one that still surfaces carries no `X-Fal-Needs-Retry`, so `ProviderError` at once, settled at $0 | automatic only |
| 500 `runner_server_error` or `internal_error`, 502 `runner_incomplete_response` | runner or platform error | not retried by the queue, and no `X-Fal-Needs-Retry`: `ProviderError` at once, settled at $0 | no (AD-13) |
| 500 `internal_server_error`, `downstream_service_error`, `downstream_service_unavailable`; 504 `generation_timeout` (model errors with a `detail` list) | model-side failure; fal marks it retryable or not in `X-Fal-Needs-Retry` | `classify` takes the `type` as the code and settles at $0; `retry_once` retries once only when the header is `true` (or `1`), otherwise `ProviderError` at once | once, if the header allows |
| 504 with `X-Fal-Request-Timeout-Type: user` | no runner started within `start_timeout` (120 s), a deliberate deadline | neither fal-client nor `retry_once` retries it (no `X-Fal-Needs-Retry`); `ProviderError`, settled at $0 | no |
| `FalClientTimeoutError` (with `request_id`) | `client_timeout` (300 s) passed | fal-client cancels the request (best effort); settled at $0.02; the request id is in the call row | no; call `result(app, request_id)` within minutes (the stored result lasts about 6 min above 10 KB, about 1 h below) before paying for a re-run |
| 413 on submit | the data-URI body is too large for fal's ingress | `ProviderError("fal_http_413")`, settled at $0.02 (conservative); switch `image_url` to an upload (references/adapter.md) | no |
| `httpx.ConnectError`, `httpx.ConnectTimeout` | network, after fal-client's 10 attempts and one backup-domain try | `retry_once` retries once after 0.5 to 1 s (AD-13), then `ProviderError`, settled at $0.02 (a poll-time failure may follow a billed submit) | automatic, then once |
| any other `httpx` transport error, a read timeout | network, after fal-client's own attempts | `ProviderError`, never re-sent by the adapter (the request may still bill) | automatic only |
| 200 without `model_glb`, `gaussian_splat` or `metadata`, or with the schema's sample URL | no mesh produced | `NoMeshError`, then `ProviderError(200, "fal_bad_output", ...)`, settled at $0.02 | no |
| Download error | URL expired (one-hour lifecycle) or a CDN error | `ProviderError(None, "fal_transport_error", ...)`, settled at $0.02; an expired URL means a new paid call | no |
| File signature other than `glTF` or `ply` | a CDN error page served with 200 | `NoMeshError`, then `ProviderError(200, "fal_bad_output", ...)`; no URL in the message | no |
| Any other exception (fal-client's `ValueError("Unknown status: ...")`, a JSON decode error, a bug) | outside what the adapter catches | the `finally` settles at $0.02 and the exception propagates unchanged; investigate | no |
| Mesh misplaced or not to scale in the room | `metadata` pose does not compose into a layout | hand-placed transform in `tier2` (spine Deferred) | n/a |
| Mesh mangled | glass, mirror, chrome, heavy occlusion, harsh shadows | not an error; pick another object or use the photo billboard | n/a |

## Tested commands

| Command | What it proves | Result on 2026-10-21 | Where |
|---|---|---|---|
| `uv run --no-project --with fal-client==1.0.3 python -I -c "import inspect, sys, fal_client; from importlib.metadata import version; print(sys.version.split()[0], version('fal-client')); [print(n, inspect.signature(getattr(fal_client, n))) for n in ('subscribe', 'submit', 'status', 'result', 'cancel', 'encode', 'encode_file', 'upload_file', 'upload', 'run', 'SyncClient')]"` | Every function and parameter this skill cites exists in fal-client 1.0.3. `client_timeout` is on `subscribe` only, `webhook_url` on `submit` only, `interval` defaults to 0.1 and `default_timeout` to 120.0 | pass: `3.13.16 1.0.3`, all eleven names present with the signatures quoted in references/wire-and-errors.md | offline here |
| `curl -sSL -o openapi.json "https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/sam-3/3d-objects"` | Fetches the live input and output schema (not a model call) | pass: HTTP 200, 9,842 bytes | here (public docs fetch; no key, no spend) |
| `uv run --no-project --with fal-client==1.0.3 --with httpx==0.28.1 --with pillow==13.0.0 --with jsonschema==4.26.0 python .claude/skills/keyframe-sam3d-fal/scripts/selfcheck.py` (uv 0.11.32, Python 3.13.16) | Pins and API surface. EXIF orientation 6 is made upright (3024x4032). `Mask3D` has exactly `label`, `polygons` and `frame_size` (AD-5); the mask PNG built from it has the original's size with the polygons scaled and filled. The arguments validate against `SAM3DObjectInput`, every key is declared, `prompt` is `Mask3D.label`, and the data URIs round-trip. Array-shaped box prompts and a threshold of 0.05 are rejected. The cache key moves with seed, mask, label and attempt. Output schema and `parse_result`: `NoMeshError` for a missing `model_glb`, `gaussian_splat` or `metadata` and for the sample URL. `StorageSettings` with a `forbid` ACL builds. Through a real `SyncClient` on `httpx.MockTransport`: full submit, poll and result flow with key, privacy and timeout headers; 429 on submit retried by fal-client; 400 not retried; 422 maps to `image_load_error`; 503 and a 500 `internal_server_error` model error settled unbilled. The amended AD-13: `FAL_RETRYABLE_STATUS` is 429 alone and `RETRY_ON_CONNECT` is `ConnectError` and `ConnectTimeout`; `is_retryable` accepts 429, a 5xx with `X-Fal-Needs-Retry` `true` or `1` and connect errors, and refuses a bare 500, a 503 with `false`, a 422, a read timeout and a client timeout; a 500 model error with `X-Fal-Needs-Retry: true` is retried once after 0.5 to 1 s, and a second one raised; a 500 with `false`, a runner 503 with no header, a start-timeout 504 and a 422 are raised with no retry; a surfaced 429 with `Retry-After: 2` waits 2 s and retries; `Retry-After: 600` past the 300 s budget, and `Retry-After: 30` with 20 s left (fake clock), fail at once; a connect error is retried once; a `FalClientTimeoutError` is never retried. `classify` settles `NoMeshError` and a plain `FalClientError` without re-raising; `client_timeout` raises with the request id and cancels; GLB and PLY signature checks with no URL in the error | pass: 67 `PASS` lines, ending `selfcheck passed`, exit 0 (re-run on 2026-10-21 after the amended AD-13 and AD-5) | offline here (packages from uv's cache; no fal host contacted) |
| the same `uv run ... selfcheck.py openapi.json`, with the document from the row above | Adds the drift check: the embedded schema copy equals the live document | pass earlier on 2026-10-21 with the then 56 checks; not re-run after the amendment, because it needs a fresh download from fal.ai. The embedded copy did not change | offline here, after the download |
| `claude plugin validate .claude/skills` | This skill's frontmatter parses and validates | pass: `Validation passed` | offline here |
| One real call, only when the user explicitly asks: a 4032x3024 original as a data URI, one mask PNG at that size, `prompt` set, `seed` 7, with the two privacy headers | A 4032x3024 data URI is accepted, with no 413. A mask at original size is the expected format. `model_glb` comes back for a single mask. The metadata nesting. The headers are honored on a shared model. Latency against `client_timeout=300` | not run | live-only: confirm in the five-object spike before Oct 26 |
| Request history and storage views on the fal dashboard after that call | No copy of the data-URI input persists at fal with `X-Fal-Store-IO: 0` | not run | live-only |
| Only if the upload fallback is needed: one call whose `image_url` is an upload with `initial_acl` default `forbid` | The model runner can still read a `forbid` input | not run | live-only |
| fal usage dashboard after a 422 and a client timeout | Whether 4xx and cancelled requests are billed (the code assumes yes) | not run | live-only |
| GLB loaded with three.js `GLTFLoader` beside the photo plane | Units, up axis and origin match `metadata` | not run | live-only (Tier 2 epic) |

## Known issues

- **`X-Fal-Needs-Retry` values.** AD-13 retries a fal 5xx only when this header allows it, but fal documents the value only as retryable "true or false". `is_retryable` accepts `true` and `1` (any case); record the real value from the first live 5xx.
- **The docs and the client disagree.** The docs say `start_timeout` is sent as `X-Fal-Request-Start-Timeout`, while fal-client 1.0.3 sends `X-Fal-Request-Timeout`. The reliability page says the server keeps running after `client_timeout`, while 1.0.3 also sends a cancel. Both were read in the installed source. Confirm the server's behavior on the first live timeout.
- **GLB is optional.** `stack.md` says "GLB out", but `model_glb` is optional in the schema, and its default is a sample scene URL that could pass for a real mesh. `parse_result` refuses both cases. The spike must show a GLB for a single mask, or Tier 2 renders the splat instead.
- **The developer guide is outdated.** It uses `mask_url`, array-shaped box prompts and `individual_glbs[0]` for a single object. None of these match the live schema. Trust the OpenAPI document and re-fetch it before Nov 4 (run the selfcheck with it), because fal renames endpoints.
- **Retention text.** The Retention summary served by `GET /meta` (AD-8, AD-15) quotes the fal retention summary from the pre-Oct 26 verification. It should state: request history is off for these calls through `X-Fal-Store-IO: 0`, and generated files expire after an hour. Disabling payload storage is not full Zero Data Retention, which needs fal sales.

## References

- https://fal.ai/models/fal-ai/sam-3/3d-objects/llms.txt: model card with the input and output schema, the price and a `subscribe` example.
- https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/sam-3/3d-objects: machine-readable schema (prompt objects, metadata typing, queue paths); the selfcheck's drift source.
- https://fal.ai/models/fal-ai/sam-3/3d-objects/api: API page; file inputs as data URIs, hosted URLs or uploads; queue and webhooks.
- https://fal.ai/docs/api-reference/client-libraries/python/fal_client.md: every fal-client function, class and parameter.
- https://fal.ai/docs/documentation/model-apis/inference/queue.md: queue lifecycle, `start_timeout`, `client_timeout`, cancel, `X-Fal-No-Retry`.
- https://fal.ai/docs/documentation/model-apis/inference/reliability.md: automatic retries, backup domains, no charge for 5xx.
- https://fal.ai/docs/documentation/model-apis/common-parameters.md: platform headers (`X-Fal-Store-IO`, lifecycle, start timeout, priority).
- https://fal.ai/docs/documentation/model-apis/media-expiration.md: request-history retention, CDN expiry, ZDR scope.
- https://fal.ai/docs/documentation/model-apis/fal-cdn.md: uploads, public-by-default URLs, the "a few KB" data URI caveat.
- https://fal.ai/docs/documentation/model-apis/file-access-controls.md: `initial_acl` (`allow`, `forbid`, `hide`) on uploads and outputs; the owner keeps access.
- https://fal.ai/docs/documentation/model-apis/concurrency-limits.md: account concurrency (2 for new accounts), queue behavior at the cap.
- https://fal.ai/docs/documentation/model-apis/request-errors.md: infrastructure `error_type` values and status codes; the concurrency 429 is sync-only.
- https://fal.ai/docs/documentation/model-apis/errors.md: typed model errors (422, 500, 504), retryability and the `X-Fal-Needs-Retry` header.
- https://fal.ai/docs/documentation/model-apis/inference/webhooks.md: webhook payload, retries, signature verification, and how long a stored result stays retrievable.
- https://fal.ai/docs/documentation/model-apis/mcp.md: the fal MCP relay, including `store_payload: false`.
- https://fal.ai/learn/devs/sam-3d-developer-guide: input quality, failure cases, caching advice (Dec 2025; its parameter shapes are outdated).
- https://pypi.org/project/fal-client/: release history and the 1.0.3 wheel whose source the selfcheck exercises.
