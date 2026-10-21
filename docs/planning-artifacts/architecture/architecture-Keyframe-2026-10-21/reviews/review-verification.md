# Review: verification of versions and named technologies

Spine: `ARCHITECTURE-SPINE.md` (Keyframe, draft, 2026-10-21). Author: Luis Ticas.
Lens: every committed version and every named technology or API behaviour checked on 2026-10-21 against the live registry or vendor page, and against the repo (`pyproject.toml`, `requirements.txt`, `src/`, `docs/specs/spec-keyframe/`).

**Verdict: pass with fixes.** Every version in the Stack table is the current release on its registry today, and every named service, model id, package and decorator exists and fits. What was not checked is runtime behaviour of the hosted substrate the spine leans on (Modal Volume visibility across containers, the 300 s function timeout, Dict expiry), the live default of the Vite starter (TypeScript ~6.0.3, not 7.0.2), and three API conventions that the spine's rules silently assume (Spark's 0–1000 box grid, SAM's sub-frame mask rasters, the strict structured-output subset). None is wrong today; each would cost an agent a story if left unstated.

## Stack table, line by line

| Spine row | Verified value (source) | Status |
| --- | --- | --- |
| Python 3.13 | 3.13.16 is the current 3.13 patch (endoflife.date); 3.15.0 is the newest line; modal 1.6.2 requires `<3.16,>=3.10`; Pillow 13 requires `>=3.11` | OK. Note: repo `pyproject.toml` says `requires-python = ">=3.11"` |
| FastAPI 0.156.4 | PyPI latest 0.156.4 | OK |
| uvicorn 0.54.0 | PyPI latest 0.54.0 | OK |
| pydantic 2.14.1 | PyPI latest 2.14.1 | OK |
| httpx 0.28.1 | PyPI latest 0.28.1; fal-client pins `httpx<1` | OK |
| Pillow 13.0.0 | PyPI latest 13.0.0 | OK |
| meta-sam-parser 0.1.0 | PyPI latest 0.1.0, author Meta Platforms, Inc., repo `meta-models/meta-sam`, `>=3.10`, zero runtime deps; named on `dev.meta.ai/docs/sam/client-libraries` as the official Python parser | OK, exists and is the right package |
| fal-client 1.0.3 | PyPI latest 1.0.3 | OK |
| ollama 0.6.3 | PyPI latest 0.6.3 | OK |
| Ollama runtime v0.40.6, `llama3.2:3b` | GitHub releases: v0.40.6 (Oct 16) is "Latest"; v0.40.7-rc0 (Oct 18) is a pre-release; `registry.ollama.ai/v2/library/llama3.2/manifests/3b` returns 200 | OK |
| modal 1.6.2 | PyPI latest 1.6.2 (uploaded Oct 16) | OK |
| pytest 9.1.1 | PyPI latest 9.1.1 | OK |
| python-dotenv 1.x | PyPI latest 1.2.4 | OK |
| Node 24 LTS | nodejs.org index: v24.22.0 is the active LTS ("Krypton"); v26.12.0 is Current and becomes LTS on 2026-10-28, inside the build week | OK; pin it (F7) |
| Vite 8.3.4 | npm latest 8.3.4; `engines.node: ^20.19.0 \|\| >=22.12.0` (the spine's "Vite 8 node requirement" holds; Node 24 satisfies it) | OK |
| three 0.186.1 | npm latest 0.186.1 (Sep 24) | OK |
| TypeScript 7.0.2 | npm latest 7.0.2 (Jul 8), the native compiler; the Vite `template-vanilla-ts` on `vitejs/vite@main` pins `"typescript": "~6.0.3"` and `"build": "tsc && vite build"`; 6.0.3 is the last 6.x | Exists, but is not the starter's live default (F4) |
| json-schema-to-typescript 16.0.0 | npm latest 16.0.0 (Aug 28); no dependency on `typescript`, so it works under either TS major; quicktype (the Deferred alternative) is 26.0.0 | OK |
| @sparkjsdev/spark 2.4.0 | npm latest 2.4.0 (Oct 20); peer `three >=0.180.0`, satisfied by 0.186.1 | OK |

## Named technologies and API behaviour

| Claim in the spine | Verified against | Result |
| --- | --- | --- |
| AD-5: `meta` adapter uses Chat Completions for the council (`chat` with images, `response_schema`, `reasoning_effort`) | `dev.meta.ai/docs/protocols/chat-completions`, `/docs/image-understanding`, `/docs/structured-output`, `/docs/models` | Confirmed. `POST https://api.meta.ai/v1/chat/completions`, bearer auth; `muse-spark-1.3` on Responses, Chat Completions and Messages; images as `{"type":"image_url","image_url":{"url":"<base64 data URL>"}}` in `user` messages, up to 50 per request, ~1,300–1,500 tokens at 1280 px; `response_format: {type: "json_schema", json_schema: {name, schema, strict}}`; `reasoning_effort` is top-level with values `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `none` returns HTTP 400 on Muse Spark |
| AD-5: Responses for `sam-3.1` | `/docs/models`, `/docs/sam/client-libraries`, `/docs/sam/reading-segmentation` | Confirmed. `sam-3.1` is served on the Responses API only (`model: "sam-3.1"`, `client.responses.create`, streamed); boxes come back in source pixels with `w,h`; each mask is a base85 raster of its own `H,W`, smaller than the frame; the parser decodes to raster, COCO RLE or an `M`/`L`/`Z` SVG path, and there is no polygon output |
| Diagram: `muse-image-1.0`, `muse-spark-1.3`, `sam-3.1` | `/docs/models` | All three ids exist as written; `muse-image-1.0` serves `POST /v1/images/generations`; `muse-voice-transcribe-1.0` serves `POST /v1/asr/transcribe` (the `transcribe` port's target, not named in the spine) |
| AD-5: `openai_compatible` with `base_url` for Baseten, Fireworks | Baseten changelog | Baseten serves `meta-models/muse-spark-open` at `https://inference.baseten.co/v1`, OpenAI-compatible. Fireworks' model library shows no Llama 3.1 8B Instruct (only 70B/405B 3.1, 3.2 1B/3B/11B/90B, 3.3 70B); that fallback is named only in `stack.md`, not in the spine |
| Diagram: `fal.ai sam-3/3d-objects` | `fal.ai/models/fal-ai/sam-3/3d-objects/api` | Endpoint id `fal-ai/sam-3/3d-objects` exists; input `image_url` (required), `mask_urls`, `prompt`, `point_prompts`, `box_prompts`, `export_textured_glb`; output `gaussian_splat` (required), `model_glb`, `individual_glbs`, and a required `metadata` list with `scale`, `rotation` (quaternion), `translation`, `camera_pose` per object |
| Diagram: `@modal.asgi_app` FastAPI, `modal.Dict` jobs, Volume artifacts; AD-7: 150 s web timeout; AD-14: `MIN_CONTAINERS` | `modal.com/docs/guide/webhooks`, `/guide/webhook-timeouts`, `/reference/modal.Dict`, `/guide/volumes`, `/guide/cold-start`, `/guide/timeouts` | `@modal.asgi_app()` and `@modal.concurrent(max_inputs=…)` are current; the 150 s HTTP limit is real and the docs' own pattern is spawn + poll (what AD-7 does); `min_containers=` is the parameter (no `keep_warm`); Function timeout default is **300 s**, max 24 h, set with `timeout=`; `Dict.from_name(..., create_if_missing=True)` is durable for Dicts created after 2025-05-20 but **entries expire after 7 days without a read or write**; `Volume.from_name(..., create_if_missing=True)` is v1 by default (v2 is opt-in beta), writes are visible to other containers only after `commit()` on the writer and `reload()` on the reader, concurrent writes to one file are last-write-wins, and `reload()` fails with "volume busy" while files are open |
| Ollama Guide: `llama3.2:3b` on v0.40.6 | GitHub releases, Ollama registry | Confirmed (see table) |
| AD-14: `Settings` in `src/config.py` "(existing)" | repo | `src/config.py` is a dataclass `Settings.from_env()` reading `MODEL_PROVIDER`, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `CHAT_MODEL`, `IMAGE_MODEL` via `os.environ`; none of the spine's flags exist yet. `src/providers/base.py` is a sync ABC with `chat(messages, model, temperature, max_tokens)` and `generate_image`; `meta_api.py` is a stub with placeholder base URL `https://api.meta.com/v1` (the live one is `https://api.meta.ai/v1`). `pyproject.toml` declares no dependencies; `requirements.txt` has only `python-dotenv` and `pytest` |

## Findings

### F1 (high) — AD-7 / Structural Seed: Volume writes are invisible across Modal containers without `commit()` and `reload()`
The pipeline is spawned as a separate Function (that is how AD-7 escapes the 150 s limit), so it runs in a different container from the ASGI app. On Modal's Volume (v1, the default), the worker's files reach other containers only after `vol.commit()`, and the web container sees them only after `vol.reload()`; `reload()` fails while the container has files on the Volume open. As written, "persist job state plus stage artifacts through `JobStore` and `ArtifactStore` after each stage" and "`GET /builds/<job id>` reads persisted state only" can return a job marked `scene` done whose Room file the web container cannot yet read.
**Fix:** amend AD-7's Rule: "in hosted mode `ArtifactStore.put` ends with `Volume.commit()` and every read begins with `Volume.reload()` from a container that holds no open Volume files; one writer per job (the stage runner), so no file is written by two containers." Add to the Structural Seed note for `infra/modal.py`: `Volume.from_name(..., create_if_missing=True)`, v1; artifacts under `/artifacts/<job_id>/<stage>/`.

### F2 (high) — AD-7: the spawned pipeline Function inherits Modal's 300 s default timeout
The spine names only the 150 s web timeout. The spawned stage runner has its own Function timeout, default 300 s. `budgets.md` puts a build at 110 s nominal and about 260 s with two regenerations, before photo decode, SAM fan-out waits and a 429 retry with backoff (AD-13). A third slow Riddler call kills the job silently at 300 s, exactly the failure AD-7 exists to prevent.
**Fix:** AD-7 Rule, add: "the stage runner is a separate `@app.function(timeout=900)` invoked with `.spawn()`; the ASGI Function keeps the default; a job whose runner dies is marked `failed` with `stage` by a watchdog read of the `FunctionCall` id stored in the job record."

### F3 (medium) — AD-7 / AD-6 / AD-9: `modal.Dict` entries expire after 7 days without a read or write
Demo rooms built around Oct 29 and first opened by a judge on Nov 5–8 sit untouched for about a week. The job record (and, per AD-6, the ledger counter, which "persists through `JobStore`") lives in the Dict and can be gone when `GET /builds/<job id>` is called. `budgets.md` says the hosted counter persists on the Volume, which disagrees with AD-6.
**Fix:** AD-7 Rule: "the Dict holds in-flight job state only; on `scene` the final job record is written to the Volume beside the Room and `GET /builds` falls through Dict → Volume." AD-6 Rule: replace "persists through `JobStore`" with "persists on disk (local) or the Volume (hosted) through `ArtifactStore`", matching `budgets.md`.

### F4 (medium) — Stack: TypeScript 7.0.2 is not what the Vite starter the spine leans on installs
`create-vite`'s `template-vanilla-ts` (checked on `vitejs/vite@main`, create-vite 9.3.1 published Oct 20) pins `typescript ~6.0.3` and `build: "tsc && vite build"`. 7.0.2 is the Go-native compiler: 6.0 deprecations become hard errors, `module` defaults to `esnext`, `strict` and `stableTypeOrdering` are on, `rootDir`/`types` defaults changed. It works for new code that is clean under 6.0, but a `web/` story that scaffolds with `npm create vite@latest -- --template vanilla-ts` and then "upgrades" to 7 on the spine's say-so can lose an hour on config errors, and the two agents touching `web/` may not land on the same major.
**Fix:** either pin the row to `TypeScript ~6.0.3 (the Vite 8 vanilla-ts template default)`, or keep 7.0.2 and add to the row: "replace the template's `~6.0.3`; `tsconfig` from the TS 7 defaults, no `ignoreDeprecations`." Add to the Deferred note on type generation that `json-schema-to-typescript` 16 has no `typescript` dependency, so the choice is independent of this.

### F5 (medium) — Consistency Conventions "Time and formats": three coordinate spaces, one convention
The spine says "masks as polygons in image pixel space" and AD-11 says "polygon hotspots". On the live API: Spark vision boxes come back on a normalized 0–1000 grid (can slightly exceed 1000, must be clamped); SAM 3.1 boxes come back in source pixels with the frame `w,h`; each SAM mask is a raster of its own smaller `H,W` that must be scaled to the frame; `meta-sam-parser` emits raster, COCO RLE or an `M`/`L`/`Z` SVG path, never a polygon list. Without this in the conventions, the `pipeline` owner and the `web/` owner will each pick a space.
**Fix:** convention row: "Spark boxes arrive on a 0–1000 grid and are converted to 1280 px frame pixels and clamped at `ingest`; SAM boxes arrive in source pixels; SAM mask rasters (`H,W` < frame) are scaled to the 1280 px frame; the hotspot polygon is the parser's SVG path (`M`/`L`/`Z`) parsed to `[[x,y],…]` in frame pixels, simplified to at most N points in `domain`." Add `meta-sam-parser` to the CAP-1 "Lives in" cell.

### F6 (medium) — AD-2 / AD-5: one pydantic schema cannot be both the API schema and a `strict: true` response schema
Meta's structured output: `strict` defaults to `false` and output is constrained to the schema either way; `strict: true` additionally requires every object to carry `additionalProperties: false` and to list every property in `required`, forbids `allOf`/`oneOf`, and any self-referencing schema returns HTTP 400 regardless of `strict`. pydantic's `model_json_schema()` for `Room` (optional fields, `$defs`) fails the strict subset as emitted. AD-2's "realized once" is right; the council's `response_schema` must be derived, not reused verbatim.
**Fix:** AD-5 Rule, add: "`response_schema` is passed with `strict: false` (Meta's default; output is schema-constrained either way) or through one `strict_schema(model)` helper in `src/domain/schema.py` that inlines `$defs`, sets `additionalProperties: false` and fills `required`; Schema v1 contains no self-referencing model." Also: "`reasoning_effort` is one of `minimal|low|medium|high|xhigh`; `none` is rejected by Muse Spark (HTTP 400) and the mock refuses it too."

### F7 (low) — Stack: Node 26 becomes LTS on Oct 28, mid-build
Node 24.22.0 is the active LTS today and satisfies Vite 8 (`^20.19.0 || >=22.12.0`); on Oct 28 Node 26.12 becomes LTS, and an agent reading "Node LTS" on Oct 29 installs 26.
**Fix:** row reads `Node 24.22 (LTS; .nvmrc = 24, engines.node = "24.x")`.

### F8 (low) — Code style vs repo: `requires-python >=3.11`, no declared dependencies
The spine commits to Python 3.13 type hints and a pinned stack, but `pyproject.toml` says `>=3.11` and lists no dependencies; `requirements.txt` has two. Agents starting from the repo will target 3.11 syntax and install nothing.
**Fix:** Deferred or Conventions: "the first `providers` story bumps `requires-python` to `>=3.13` and moves the Stack table into `[project.dependencies]` with `==` pins; `requirements.txt` is dropped." The `meta_api.py` stub's placeholder `https://api.meta.com/v1` becomes `https://api.meta.ai/v1`.

### F9 (low) — Deferred: fal does return a pose
`fal-ai/sam-3/3d-objects` returns a required `metadata` list with `scale`, `rotation` (quaternion), `translation` and `camera_pose` per object, plus `model_glb` / `individual_glbs`. The deferred question is not "when fal returns no pose" but "when the returned pose is unusable for a wall layout".
**Fix:** reword the first Deferred bullet: "Tier 2 object placement when fal's per-object `translation`/`rotation`/`scale` metadata does not compose into a room layout (hand-placed transforms in `tier2` versus a layout stage)."

### F10 (low) — AD-5: the Fireworks fallback has no 8B Llama to point at
Baseten's `meta-models/muse-spark-open` is live and OpenAI-compatible. Fireworks' library today lists Llama 3.2 1B/3B/11B/90B, 3.1 70B/405B and 3.3 70B, not Llama 3.1 8B Instruct; the "8B Llama on Fireworks" Trickster fallback exists only in `stack.md`. Nothing in the spine breaks, but the `openai_compatible` adapter's fixtures should not assume that id.
**Fix:** no spine change required; note in the CAP-5 row: "Fireworks fallback model id confirmed on Oct 26 before a fixture is recorded."

## What was checked and found correct (no action)
All PyPI and npm pins (table above); Ollama v0.40.6 and the `llama3.2:3b` tag; `@modal.asgi_app()`, `@modal.concurrent`, `min_containers`, the 150 s web timeout; `muse-spark-1.3`, `sam-3.1`, `muse-image-1.0`, `muse-voice-transcribe-1.0` model ids and their protocols; images and `response_format` on Chat Completions; `reasoning_effort` parameter name; `meta-sam-parser` identity, version, zero-dependency claim and its acceptance of plain-mapping Responses events (no `openai` SDK needed, consistent with the spine's httpx-only stack); `fal-ai/sam-3/3d-objects` id and schema; `@sparkjsdev/spark` peer on three; Baseten Muse Spark Open; Vite 8 engines; Python 3.13 support window of modal and Pillow.
