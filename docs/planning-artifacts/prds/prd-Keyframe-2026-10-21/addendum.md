---
title: "PRD Addendum: Keyframe"
status: final
author: Luis Ticas
created: 2026-10-21
updated: 2026-10-21
---

# PRD Addendum: Keyframe

This addendum holds the detail behind `prd.md` that belongs downstream or would bloat the PRD: the technical choices each requirement rests on, the alternatives rejected and when to revisit them, the sizing numbers, the open decisions, and pointers to where each detail lives. The PRD is written over the approved spec so UX and epics have a product-level input, and it reopens nothing in the spec. The addendum points to its sources rather than copying them, except that §3 repeats headline sizing figures inline so readers can judge scope without opening `budgets.md`. Prices and limits were checked Tue Oct 20 against primary sources. Cost, speed, and effort figures keep the [ASSUMPTION] tag their sources give them.

## 1. Technical choices behind the PRD

Every model call goes through the `ModelProvider` port (AD-5): `mock`, `meta`, `openai_compatible` (Baseten, Fireworks), `fal`, and `ollama` adapters, resolved per council role. The first table maps each council role to its model or service; the second maps each capability. "Governing AD" names the architecture spine invariants (AD-1 to AD-18) that constrain the row.

### Per council role

A council role is one of the four wizards: Architect, Riddler, Guide, and Trickster. The table has five rows because the Guide splits into rung selection and phrasing. Each row shows what that wizard consumes and produces. The dry run is not a wizard: it is a fifth Spark call that checks the Riddler's output.

| Council role | Model or service | Runs on | Governing AD | PRD FRs |
|---|---|---|---|---|
| Architect (object list) | `muse-spark-1.3`, Chat Completions, image input, JSON schema, reasoning low | Meta Model API | AD-5, AD-6, AD-18 | FR-2 |
| Riddler (puzzle graph, clues, rungs) | `muse-spark-1.3`, Chat Completions, JSON schema, reasoning medium; fallback Muse Spark Open on Baseten by `base_url` swap | Meta Model API | AD-2, AD-3, AD-5, AD-13, AD-18 | FR-7, FR-10 |
| Guide, rung selection | Python over the event log (`domain/rungs.py`) | Backend, local or Modal CPU | AD-4, AD-10 | FR-15, FR-16 |
| Guide, phrasing | Llama 3.2 3B Instruct Q4_K_M on Ollama, `OLLAMA_KEEP_ALIVE=-1`; falls back to the verbatim rung after a 5 s timeout | Mac only; hosted URL shows rung text verbatim | AD-5 (`HintPhraser`, no cloud adapter), AD-8, AD-14 | FR-17, FR-21 |
| Trickster | `muse-spark-1.3`, reasoning low, fixed menu; under cut 1, a scripted source; last fallback Fireworks Llama 8B (model id to be confirmed Mon Oct 26) | Meta Model API | AD-4, AD-12, AD-15 | FR-18, FR-19, FR-25 |

### Per capability

| Capability | Model or service | Runs on | Governing AD | PRD FRs |
|---|---|---|---|---|
| **Tier 1 build pipeline** | | | | |
| Capture and downscale | Canvas downscale to 1280 px, EXIF applied; "6 to 10 JPEG photos", HEIC and PNG rejected | Browser, then backend ingest | AD-7 | FR-1, FR-5 |
| Masks | `sam-3.1` on the Responses API, one noun phrase per call, at most 12 in parallel, decoded with `meta-sam-parser` | Meta Model API, decode in backend | AD-5, AD-6, AD-18 | FR-3, FR-4 |
| Validator | Python, the eight rules of Schema v1 | Backend | AD-12 | FR-8 |
| Dry run | `muse-spark-1.3`, reasoning low, never sees solutions | Meta Model API | AD-3, AD-12 | FR-9 |
| **Play** | | | | |
| Play state machine | Python, server-authoritative event log | Backend | AD-3, AD-4 | FR-11 to FR-14 |
| Scene | Vite and Three.js, textured planes with polygon hotspots | Browser | AD-11 | FR-11 |
| Player profile | IndexedDB database selected by `PROFILE` (`dev`, `playtest`, `demo`); a JSON file under cut 2 | Browser | AD-8 | FR-20, FR-22 |
| Portraits | `muse-image-1.0`, generated once by script, committed | Meta Model API, once | AD-6 | FR-23 |
| Demo mode | `DEMO_TIMESCALE`, `DEMO_TRICKSTER`, `GET /meta` | Backend | AD-10, AD-15 | FR-24 to FR-26 |
| **Cross-cutting** | | | | |
| Cache and spend | SHA-256-keyed cache over every paid cloud call (Meta Model API, fal.ai, Baseten, Fireworks); append-only ledger kept outside `.cache/`, so clearing the cache never touches it; `SPEND_CAP_USD` and daily export (figures in §3 Daily ceilings) | Mac disk or Modal Volume and Dict | AD-6, AD-9, AD-16 | FR-27 to FR-30 |
| Hosted URL | FastAPI on `@modal.asgi_app()`, build as a spawned job; judge photos, originals, rooms, and sessions kept on the Volume until Tue Nov 10, session logs kept 24 h; `MIN_CONTAINERS=1` Thu Nov 5 to Mon Nov 9; first deploy Tue Oct 27, which serves as the live-link fallback if the Official Rules require a live link | Modal CPU | AD-7, AD-8, AD-9 | FR-31 to FR-33 |
| Privacy hygiene | `.gitignore` tests for `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/`, and `.env`; one retention string served by `GET /meta`; Meta Model API standard tier only | Repo, backend | AD-3, AD-5, AD-8, AD-14 | FR-6, FR-36 |
| Build view | Solution-free projection of the Room plus provenance: masks, puzzle graph, per-rule validator verdict, dry-run result per puzzle, regeneration count, and model table; data route undecided (PRD §13 Q13) | Backend, browser | AD-3, AD-12 | FR-38 |
| **Later tiers** | | | | |
| Clue cards (Tier 1.5) | `muse-image-1.0`, one image per puzzle from clue text only, never a solution, cached, shown with the clue | Meta Model API | AD-3, AD-6; stage listed under spine Deferred | FR-37 |
| Tier 2 room | `fal-ai/sam-3/3d-objects`, $0.02 a call, original-resolution hero photos, GLB out; fallbacks if fal output lacks a usable pose: Runware, Segmind, hand-made assets, a photo billboard | fal.ai, cloud only | AD-11, spine Deferred | FR-34 |
| Voice (unscheduled) | `muse-voice-transcribe-1.0` REST; `webkitSpeechRecognition` fallback; audio leaves the Mac for transcription, the transcript is reduced to a hint request and never stored; transport is a spine Deferred item | Meta Model API or the browser's speech service | AD-4, AD-5 | FR-35 |

**Privacy hygiene:** the Privacy line, verbatim: "the player profile stays on your machine."

**Clue cards:** generated once per demo room by an explicit step; judge rooms and ordinary builds get them only if Luis enables them. Card references are kept outside the frozen Room, keyed by puzzle id.

## 2. Rejected alternatives

| Area | Option | Rejected because | Revisit when |
|---|---|---|---|
| On-device model | Muse Glimmer as the on-device Guide | Smallest official quant needs about 19 GiB resident; the M1 has 16 GB | Not revisited for this build |
| On-device model | Llama 3.1 8B for the demo | About 6 GB resident, which puts development near 17 GB and makes the recording stutter | Quality comparisons only, with the IDE closed |
| Cloud and 3D | Modal GPU for SAM 3D Objects | Linux, 32 GB VRAM, cu121 torch, PyTorch3D, Kaolin, a gated checkpoint; L40S $1.95 an hour against fal's $0.02 a call | fal output proves unusable and Tier 2 is a go |
| Cloud and 3D | Local SAM 3.1 (MPS) | Official repo is CUDA-only; the MPS and CPU PR is unmerged and reportedly slower than CPU | The PR merges and beats 10 s per room |
| Cloud and 3D | Apple RoomPlan or Object Capture | Needs a LiDAR iPhone and a Swift app; RoomPlan gives boxes, Object Capture needs 20 to 200 photos per object | A hero object needs hand-making |
| Cloud and 3D | Hugging Face ZeroGPU as a live dependency | 5 free GPU minutes a day; paid users get queue priority; needs custom CUDA builds | Pre-rendering assets the night before |
| API and data tier | Responses API for the council | Chat Completions keeps the Baseten fallback a `base_url` swap; no council call needs carried reasoning; both APIs allow only `auto` for `tool_choice` | A call needs reasoning carried across turns |
| API and data tier | Contributor tier | Meta may train on the data; the demo rooms are in Luis's home; a 150 RPM rate limit | Never for photos |
| Video and gates | A single uncut video | A 15-minute session is unwatchable and Demo is 25% of the score | Never; the unedited capture proof covers trust |
| Video and gates | A Saturday Oct 31 video gate | Only 16 h are available through Saturday; Tier 1 needs 22 h with all eight cuts | Never; Saturday night stays the early gate for Tier 2 only |
| Product scope | Live phone capture | Needs a mobile client and an upload path that add nothing visible to the demo loop; photos come from the camera roll | After the hackathon |
| Product scope | Quest or MR | No headset; ROOM//ZERO holds that framing; the browser reaches every judge | Vision, two to three years out |
| Product scope | A reveal or skip control after the near-answer | Adds an event, a schema field, and a scoring rule for a case the dry run is meant to prevent; the MVP keeps the near-answer as the last help (PRD A-21) | The playtest (SM-2) shows a player stuck after the near-answer |
| Product scope | Re-checking phrased hints for solution tokens | The phraser never receives room content or a solution (AD-3), so a match would be chance; the check needs a spine change | A phrased hint is seen to leak |
| Process | `bmad-prd` ahead of `bmad-spec` | One person decides and Tier 2 is not a second epic before the Mon Nov 2 gate, so the spec came first and holds the build contract | A second contributor or epic |

## 3. Sizing

All figures use the Tue Oct 20 list prices. Replace them with ledger figures once the Mon Oct 26 measurements exist.

### Calls and latency per build (Tier 1, one room)

Three Spark calls (Architect, Riddler, dry run) plus at most 12 `sam-3.1` calls. Nominal time from Upload click to first hotspot is 110 s, against a target of 120 s or less (NFR1). Each regeneration adds about 75 s; two regenerations, the cap, bring the total to about 260 s. If the Tue Oct 27 to Wed Oct 28 measurements miss 120 s, the target becomes measured p50 plus 25%. Stage budgets: `budgets.md` §Calls and latency.

### Cost [ASSUMPTION]

| Item | Estimate |
|---|---|
| Clean build | about $0.10 (vision $0.025, SAM $0.03, Riddler $0.022, dry run $0.024) |
| Build with one or two regenerations | $0.15 with one regeneration; under $0.25 with two |
| Session, 15 to 25 minutes | about $0.21 (Trickster at most 6 Spark calls; Guide on Ollama costs nothing) |
| Four portraits plus clue cards for the demo rooms (up to 12) | $0.16 once |
| Clue cards per build, only if Luis enables them | about $0.04 to $0.06 (4 to 6 images at the $0.01 image seed) |
| fal.ai, Tier 2 | about $1 cash, ceiling $6 |
| Modal warm container, Thu Nov 5 to Mon Nov 9 | about $8, inside the Starter plan's $30 |
| Meta API verifications Wed Oct 21 to Sun Oct 25 | up to about $5 cash, outside the ceilings |

### Daily ceilings [ASSUMPTION]

| Date | Mon Oct 26 | Tue Oct 27 | Wed Oct 28 | Thu Oct 29 | Fri Oct 30 | Sat Oct 31 | Sun Nov 1 | Mon Nov 2 | Tue Nov 3 | Wed Nov 4 |
|---|---|---|---|---|---|---|---|---|---|---|
| Cap | $3 | $5 | $10 | $10 | $0 | $5 | $8 | $10 | $18 | $10 |

Total $79, under `SPEND_CAP_USD` 80 through Wed Nov 4; expected spend about $35. The counter resets on Thu Nov 5, and the cap is then $25. The daily ledger export is the durable spend record. Agent dev loops run on the mock provider with `CACHE=on` and never draw on the cap.

### RAM on the 16 GB M1

Development about 13.8 GB (swap likely); demo recording about 10.6 GB with the IDE and chat apps closed. Llama 3.2 3B Q4_K_M is a 2.02 GB file, about 3 GB resident. Decode speed [ASSUMPTION, extrapolated from a measured 7B on an M1]: 25 to 35 tok/s for 3B, so a 40-token hint is about 1.6 s; the Ollama benchmark before Mon Oct 26 replaces this estimate.

### Effort ladder [ASSUMPTION, Oct 20 estimates]

The Build view (FR-38) and the accessibility floor (NFR-14) are not in the Oct 20 estimates; they are sized during epic breakdown. Tier 1 is 35 h as estimated, 28 h after cuts 1 to 5, 22 h with all eight cuts. Luis has about 32 h in-window (16 h through Sat Oct 31) plus about 8 h Wed Oct 21 to Sun Oct 25, spent on review, direction, playtesting, and recording; multiple coding agents implement around the clock against the mock provider and Schema v1. The ladder is the fallback if reviewed output lags; cuts are made nightly and the Sun Nov 1 2:00 PM backup-video gate never moves. Cut list and order: `delivery-plan.md` §Effort and cut order.

## 4. Pointers

| Detail | Lives in |
|---|---|
| What runs where, protocols, async build job, and runtime flags | `docs/specs/spec-keyframe/stack.md` |
| Call counts, prices, rate limits, spend rules, and RAM table | `docs/specs/spec-keyframe/budgets.md` |
| Profile fields, derived block, and nudge threshold | `docs/specs/spec-keyframe/player-profile.md`; `docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md` AD-8 |
| Tiers, gates, cut ladder, day plan, videos, and submission package | `docs/specs/spec-keyframe/delivery-plan.md` |
| Terms (rung, interactable, Tier 1.5, cut) | `docs/specs/spec-keyframe/glossary.md` |
| Room fields, eight validator rules, dry run, mask selection, and decoy pick | `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md` |
| Invariants AD-1 to AD-18, conventions, pinned versions, and structural seed | `docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md` |
| Capability-to-package and AD map | `docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md` §Capability → Architecture Map |
| Deferred items (clue card stage, Tier 2 placement, and voice transport) | `docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md` §Deferred |
| Prior art, hackathon terms, and sources | `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/addendum.md` §Prior art, §Hackathon terms, §Sources |
| Risks and their mitigations | `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/brief.md` §Risks & Open Questions; `docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md` §13a |
| Main demo shot list, capture proof, and submission package | `docs/specs/spec-keyframe/delivery-plan.md` §Videos, §Submission package; `docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md` §11.3 |
| Epic and story breakdown of FR-1 to FR-36 and NFR1 to NFR13 (FR-37, FR-38, and NFR-14 are new in the PRD and not yet broken down) | `docs/planning-artifacts/epics.md` |

## 5. Open decisions

These decisions are held outside this PRD.

- Thu Oct 22 schema review: one open pick (decoy storage: option A, B, or C; A recommended). See `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md` §Open pick.
- Carried to Mon Oct 26: the Fireworks Trickster fallback model id, the `GET /meta` retention wording, and the hosted full-Room download route.
- Open with Luis: the two rooms; payment methods on dev.meta.ai, fal.ai, and Modal; the playtester for Sun Nov 1 or Mon Nov 2; and availability Mon Nov 9.
- Raised by the PRD review (PRD §13 Q9 to Q13): whether an early hint request releases the nudge; whether the hosted-mode Derived block uses `Derived.fresh()` or transient numbers; the hosted Trickster source; whether to add a Clue check to rule 5 before the Mon Oct 26 freeze; the Build view data route.
