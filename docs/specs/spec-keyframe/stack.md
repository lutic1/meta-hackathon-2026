# Stack and runtime contract

Companion to `SPEC.md`. Two modes, local and hosted; in both, Chrome on the M1 is the client and a FastAPI backend on the repo's `ModelProvider` interface is the server. Local mode runs the pipeline in-process; hosted mode runs the same code on Modal CPU. No GPU anywhere.

## What runs where

| Component | Runs on | Model or service | Fallback |
|---|---|---|---|
| Front end | Browser | Vite, Three.js; Tier 1 photo scenes as textured planes with polygon hotspots | DOM-only scenes if Three.js costs more than 2 h |
| Photo capture, downscale | Browser, then backend | JPEG input only (HEIC and PNG rejected; iPhone set to Most Compatible); Canvas downscale to 1280 px; originals kept for Tier 2 | None |
| Architect (object list) | Meta Model API | `muse-spark-1.3`, Chat Completions, image input, JSON schema, reasoning low | Same call, boxes only, if SAM masks are unusable after 60 minutes |
| Masks | Meta Model API | `sam-3.1` via `POST /v1/responses`, one noun phrase per call, decoded with `meta-sam-parser` | Spark boxes as hotspots |
| Riddler | Meta Model API | `muse-spark-1.3`, Chat Completions, JSON schema, reasoning medium | Muse Spark Open on Baseten by `base_url` swap |
| Validator | Code | Python, the eight rules in `schema-v1.md` | None |
| Dry run | Meta Model API | `muse-spark-1.3`; photos, labels, clues, rungs; reasoning low | Cut 4 drops it |
| State machine | Code | Python; opens locks; solutions never enter a prompt | None |
| Guide rung selection | Code | Python over the event log | None |
| Guide phrasing | Mac only | Llama 3.2 3B Instruct Q4_K_M on Ollama, `OLLAMA_KEEP_ALIVE=-1` | None hosted: rung text verbatim |
| Trickster | Meta Model API | `muse-spark-1.3`, reasoning low, fixed menu | Cut 1: pre-authored edits plus scripted reject; 8B Llama on Fireworks last |
| Player profile | Browser | IndexedDB under a profile name | Cut 2: a JSON file |
| Portraits, clue cards | Meta Model API | `muse-image-1.0`, `POST /v1/images/generations`, once, cached | Placeholder art |
| Voice (unscheduled) | Meta Model API | `muse-voice-transcribe-1.0`, REST `POST /v1/asr/transcribe` (WAV, 16-bit mono) | `webkitSpeechRecognition` |
| SAM 3D Objects (Tier 2) | fal.ai | `fal-ai/sam-3/3d-objects`, one original-resolution hero photo per wall, GLB out | Runware, Segmind, hand-made assets, photo billboard |
| Tier 3 splat shell (never gating) | Phone, then browser | Scaniverse export, `@sparkjsdev/spark`, under 1M splats | None |
| Hosted URL | Modal CPU | `@modal.asgi_app()`, `@modal.concurrent(max_inputs=20)`, `MIN_CONTAINERS=1` Thu Nov 5 to Mon Nov 9 | Local mode screen-shared; cached rooms; the video |
| Cache | Mac disk or Modal Volume | SHA-256 of downscaled image bytes plus prompt and model id | `CACHE=off` for proof takes |
| Provider interface | Code | `src/providers/base.py` `ModelProvider`: `chat` gains image input; add `segment(label, image)` and `reconstruct3d(image, mask)`; mock, Meta API, OpenAI-compatible hosts (Baseten, Fireworks) by `base_url`, and fal implement it | None |

## Protocols

- Council calls (Architect, Riddler, dry run, Trickster) use Chat Completions with `response_format: json_schema` and an explicit `reasoning_effort`. The Meta API rejects `max_output_tokens`, `stop`, `n>1`, and `reasoning_effort: "none"`; `tool_choice` is `auto` only.
- `sam-3.1` is served only on the Responses API. One concept per request; comma lists return nothing.
- Image input: 1280 px JPEG as a base64 data URL, about 1,300 to 1,500 tokens per image; boxes come back on a 0 to 1000 grid.
- Baseten fallback for the Riddler is a `base_url` and model swap to Muse Spark Open; one schema-constrained call on Tue Oct 27 proves it, else plain-JSON prompting with validator retry.

## Async build job

`POST /builds` stores the photos, spawns the pipeline, and returns a job id; the client polls `GET /builds/{id}`, which reads job state and artifacts. Nothing lives in process memory. Local mode keeps job state in a JSON file under the cache directory; hosted mode keeps it in a `modal.Dict` with artifacts on the Volume. The API is identical in both modes because Modal web requests time out at 150 s and a build runs 110 s nominal, up to about 260 s with two regenerations.

## Privacy line

Verbatim for the README and the capture screen: "the player profile stays on your machine." It holds in every build: the profile is stored in the browser and read by the selection code on the player's machine; when Ollama phrasing ships, the phrasing runs there too; the hosted URL never runs a Guide model, and its sessions start from a fresh derived block, so no profile number leaves the browser. Photos and puzzle text go to the Meta Model API and, in Tier 2, to fal.ai; the capture screen summarizes both services' retention terms.

## Runtime flags

| Flag | Values | Default | Effect |
|---|---|---|---|
| `PROFILE` | `dev`, `playtest`, `demo` | `dev` | IndexedDB database name; video and playtest use fresh profiles |
| `CACHE` | `on`, `off` | `on` | Serve identical calls from the cache; `off` for proof takes |
| `SPEND_CAP_USD` | dollars, per mode | local 60 and hosted 20 through Wed Nov 4 (80 in all); local 5 and hosted 20 from Thu Nov 5 (25 in all) | Per-call refusal against the mode's own persisted counter; `Settings` reads the override per mode and the Modal Secret `keyframe` carries the hosted value; the daily export prints both totals and their sum against the combined ceiling; dollars move between the allocations only by a Settings change after an export shows the room (`budgets.md`) |
| `DEMO_TIMESCALE` | integer n, 1 or more | 1 | Divides the nudge threshold, rung spacing, and Trickster window by n; never the capture (build) timer, which runs in real time |
| `DEMO_TRICKSTER` | `live`, `scripted` | `live` | `scripted` replays two recorded proposals; the validator still runs live |
| `MIN_CONTAINERS` | 0, 1 | 0 | Warm hosted container, Thu Nov 5 to Mon Nov 9 only, and only if the Official Rules allow post-deadline changes to the hosted deployment (`delivery-plan.md`, Mon Oct 26 check) |
