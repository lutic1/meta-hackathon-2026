---
title: "PRD Addendum: Keyframe"
status: draft
created: 2026-10-21
updated: 2026-10-21
---

# PRD Addendum: Keyframe

This addendum holds the depth behind `prd.md` that belongs downstream or would bloat the PRD: the technical choices each requirement rests on, the alternatives rejected and when to revisit them, the sizing numbers, and pointers to where each depth lives. It copies nothing it can point to. Prices and limits were checked Oct 20 on primary pages; cost, speed and effort figures are marked [ASSUMPTION] as in the sources. Author: Luis Ticas.

## 1. Technical choices behind the PRD

### Per council role

| Role | Model or service | Runs on | Governing AD | PRD FRs |
|---|---|---|---|---|
| Architect (object list) | `muse-spark-1.3`, Chat Completions, image input, JSON schema, reasoning low | Meta Model API | AD-5, AD-6, AD-18 | FR-2 |
| Riddler (puzzle graph, clues, rungs) | `muse-spark-1.3`, Chat Completions, JSON schema, reasoning medium; fallback Muse Spark Open on Baseten by `base_url` swap | Meta Model API | AD-2, AD-3, AD-5, AD-13, AD-18 | FR-7, FR-10 |
| Guide, rung selection | Python over the event log (`domain/rungs.py`) | Backend, local or Modal CPU | AD-4, AD-10 | FR-15, FR-16 |
| Guide, phrasing | Llama 3.2 3B Instruct Q4_K_M on Ollama, `OLLAMA_KEEP_ALIVE=-1`, 5 s timeout to the verbatim rung | Mac only; hosted URL shows rung text verbatim | AD-5 (`HintPhraser`, no cloud adapter), AD-8, AD-14 | FR-17, FR-21 |
| Trickster | `muse-spark-1.3`, reasoning low, fixed menu; cut 1 is a scripted source; Fireworks 8B Llama last (model id confirmed Mon Oct 26) | Meta Model API | AD-4, AD-12, AD-15 | FR-18, FR-19, FR-25 |

The four roles describe what each wizard consumes and produces; the dry run is a fifth Spark call that checks the Riddler, not a wizard.

### Per capability

| Capability | Model or service | Runs on | Governing AD | PRD FRs |
|---|---|---|---|---|
| Capture and downscale | Canvas downscale to 1280 px, EXIF applied; "6 to 10 JPEG photos", HEIC and PNG rejected | Browser, then backend ingest | AD-7 | FR-1, FR-5 |
| Masks | `sam-3.1` on the Responses API, one noun phrase per call, at most 12 in parallel, decoded with `meta-sam-parser` | Meta Model API, decode in backend | AD-5, AD-6, AD-18 | FR-3, FR-4 |
| Validator | Python, the eight rules of Schema v1 | Backend | AD-12 | FR-8 |
| Dry run | `muse-spark-1.3`, reasoning low, never sees solutions | Meta Model API | AD-3, AD-12 | FR-9 |
| Play state machine | Python, server-authoritative event log | Backend | AD-3, AD-4 | FR-11 to FR-14 |
| Scene | Vite and Three.js, textured planes with polygon hotspots | Browser | AD-11 | FR-11 |
| Player profile | IndexedDB under `PROFILE`; JSON file under cut 2 | Browser | AD-8 | FR-20, FR-22 |
| Portraits | `muse-image-1.0`, generated once by script, committed | Meta Model API, once | AD-6 | FR-23 |
| Clue cards (Tier 1.5) | `muse-image-1.0`, one image per puzzle from clue text only, never a solution, cached, shown with the clue | Meta Model API | AD-3, AD-6; stage listed under spine Deferred | FR-37 |
| Demo mode | `DEMO_TIMESCALE`, `DEMO_TRICKSTER`, `GET /meta` | Backend | AD-10, AD-15 | FR-24 to FR-26 |
| Cache and spend | SHA-256 keyed cache; append-only ledger; daily export | Mac disk or Modal Volume and Dict | AD-6, AD-9, AD-16 | FR-27 to FR-30 |
| Hosted URL | FastAPI on `@modal.asgi_app()`, build as a spawned job | Modal CPU | AD-7, AD-9 | FR-31 to FR-33 |
| Tier 2 room | `fal-ai/sam-3/3d-objects`, $0.02 a call, original-resolution hero photos, GLB out | fal.ai, cloud only | AD-11, spine Deferred | FR-34 |
| Voice (unscheduled) | `muse-voice-transcribe-1.0` REST; `webkitSpeechRecognition` fallback | Meta Model API or browser | AD-4, AD-5 | FR-35 |
| Privacy hygiene | `.gitignore` tests; standard tier only | Repo, backend | AD-3, AD-5, AD-8, AD-14 | FR-6, FR-36 |

Every model call goes through the `ModelProvider` port (AD-5): mock, `meta`, `openai_compatible` (Baseten, Fireworks), `fal` and `ollama` adapters, resolved per council role. The privacy line, verbatim: "the player profile stays on your machine."

## 2. Rejected alternatives

| Option | Rejected because | Revisit when |
|---|---|---|
| Muse Glimmer as the on-device Guide | Smallest official quant needs about 19 GiB resident; the M1 has 16 GB | Not revisited for this build |
| Llama 3.1 8B for the demo | About 6 GB resident; development near 17 GB and a stuttering recording | Quality comparisons only, IDE closed |
| Modal GPU for SAM 3D Objects | Linux, 32 GB VRAM, cu121 torch, PyTorch3D, Kaolin, a gated checkpoint; L40S $1.95 an hour against fal's $0.02 a call | fal output proves unusable and Tier 2 is a go |
| Local SAM 3.1 (MPS) | Official repo is CUDA-only; the MPS and CPU PR is unmerged and reportedly slower than CPU | The PR merges and beats 10 s per room |
| Apple RoomPlan or Object Capture | Needs a LiDAR iPhone and a Swift app; RoomPlan gives boxes, Object Capture needs 20 to 200 photos per object | A hero object needs hand-making |
| Responses API for the council | Chat Completions keeps the Baseten fallback a `base_url` swap; no council call needs carried reasoning; `tool_choice` is `auto` only on both | A call needs reasoning carried across turns |
| Contributor tier | Meta may train on the data; the demo rooms are in Luis's home; 150 RPM | Never for photos |
| A single uncut video | A 15-minute session is unwatchable and Demo is 25% of the score | Never; the unedited capture proof covers trust |
| A Saturday Oct 31 video gate | 16 h exist through Saturday against 22 h for Tier 1 with all eight cuts | Never; Saturday night stays the early gate for Tier 2 only |
| Live phone capture | A mobile client and upload path with nothing to show in the loop; photos come from the camera roll | After the hackathon |
| Quest or MR | No headset; ROOM//ZERO holds that framing; the browser reaches every judge | Vision, two to three years out |
| Hugging Face ZeroGPU as a live dependency | 5 free GPU minutes a day, queue priority, custom CUDA builds | Pre-rendering assets the night before |
| `bmad-prd` ahead of `bmad-spec` | One person decides and Tier 2 is not a second epic before the Mon Nov 2 gate, so the spec came first and holds the build contract | A second contributor or epic; this PRD is written over the approved spec so UX and epics have a product-level input, and reopens nothing in it |

## 3. Sizing

All arithmetic from the Oct 20 list prices; replace with ledger figures once Mon Oct 26 measurements exist.

### Calls and latency per build (Tier 1, one room)

3 Spark calls (Architect, Riddler, dry run) plus at most 12 `sam-3.1` calls. Nominal 110 s from Upload click to first hotspot, target 120 s or less (NFR1); a regeneration adds about 75 s, two cap at about 260 s. If the Oct 27 to 28 measurements miss 120 s, the target becomes measured p50 plus 25%. Stage budgets: `budgets.md` §Calls and latency.

### Cost [ASSUMPTION]

| Item | Estimate |
|---|---|
| Clean build | about $0.10 (vision $0.025, SAM $0.03, Riddler $0.022, dry run $0.024) |
| Build with one or two regenerations | $0.15; under $0.25 |
| Session, 15 to 25 minutes | about $0.21 (Trickster at most 6 Spark calls; Guide on Ollama costs nothing) |
| Four portraits plus up to 12 clue cards | $0.16 once |
| fal.ai, Tier 2 | about $1 cash, ceiling $6 |
| Modal warm container, Thu Nov 5 to Mon Nov 9 | about $8, inside the Starter plan's $30 |
| Meta API verifications Oct 21 to 25 | up to about $5 cash, outside the ceilings |

### Daily ceilings [ASSUMPTION]

Oct 26 $3, Oct 27 $5, Oct 28 $10, Oct 29 $10, Oct 30 $0, Oct 31 $5, Nov 1 $8, Nov 2 $10, Nov 3 $18, Nov 4 $10: total $79 under `SPEND_CAP_USD` 80 through Wed Nov 4; expected spend about $35. From Thu Nov 5 the counter resets to a $25 cap. The daily ledger export is the durable spend record. Agent dev loops run on the mock provider with `CACHE=on` and never draw on the cap.

### RAM on the 16 GB M1

Development about 13.8 GB (swap likely); demo recording about 10.6 GB with the IDE and chat apps closed. Llama 3.2 3B Q4_K_M is a 2.02 GB file, about 3 GB resident. Decode speed [ASSUMPTION, extrapolated from a measured 7B on an M1]: 25 to 35 tok/s for 3B, so a 40-token hint is about 1.6 s; the Ollama benchmark before Mon Oct 26 replaces this.

### Effort ladder [ASSUMPTION, Oct 20 estimates]

Tier 1 is 35 h as estimated, 28 h after cuts 1 to 5, 22 h with all eight cuts. Luis has about 32 h in-window (16 h through Sat Oct 31) plus about 8 h Oct 21 to 25, spent on review, direction, playtesting and recording; multiple coding agents implement around the clock against the mock provider and Schema v1. The ladder is the fallback if reviewed output lags; cuts are made nightly and the Sun Nov 1 2:00 PM backup-video gate never moves. Cut list and order: `delivery-plan.md` §Effort and cut order.

## 4. Pointers

| Depth | Lives in |
|---|---|
| What runs where, protocols, async build job, runtime flags | `docs/specs/spec-keyframe/stack.md` |
| Call counts, prices, rate limits, spend rules, RAM table | `docs/specs/spec-keyframe/budgets.md` |
| Profile fields, derived block, nudge threshold | `docs/specs/spec-keyframe/player-profile.md`; spine AD-8 |
| Tiers, gates, cut ladder, day plan, videos, submission package | `docs/specs/spec-keyframe/delivery-plan.md` |
| Terms (rung, interactable, Tier 1.5, cut) | `docs/specs/spec-keyframe/glossary.md` |
| Room fields, eight validator rules, dry run, mask selection, decoy pick | `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md` |
| Invariants AD-1 to AD-18, conventions, pinned versions, structural seed | `docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md` |
| Capability to package and AD map | Spine §Capability → Architecture Map |
| Deferred items (clue card stage, Tier 2 placement, voice transport) | Spine §Deferred |
| Prior art, hackathon terms, sources | Brief addendum §Prior art, §Hackathon terms, §Sources |
| Epic and story breakdown of FR-1 to FR-36 and NFR1 to NFR13 | `docs/planning-artifacts/epics.md` |

### Decisions held outside this PRD

- Thu Oct 22 schema review: one pick, decoy storage (options A, B, C; A recommended). See `schema-v1.md` §Open pick.
- Carried to Mon Oct 26: the Fireworks Trickster fallback model id, the `GET /meta` retention wording, the hosted full-Room download route.
- Open with Luis: the two rooms, payment methods on dev.meta.ai, fal.ai and Modal, the playtester for Nov 1 or 2, and availability Mon Nov 9.
