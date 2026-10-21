---
title: "Product Brief Addendum: Keyframe"
status: final
created: 2026-10-20
updated: 2026-10-21
---
# Product Brief Addendum: Keyframe

This addendum holds the depth that supports `brief.md` and feeds the spec, architecture, and build. Numbers match the brief; prices, rate limits, and file sizes were checked on Tue Oct 20 against the primary pages listed in Sources. Anything not verified on a primary page is marked [ASSUMPTION]. Three groups: what runs and what it costs (§What runs where to §Runtime flags); when it ships (§Hours and cut order to §Submission package); why not the alternatives (§Options considered and rejected to §Sources).

## What runs where

There are two modes, local and hosted. In both, Chrome on the M1 is the client and a FastAPI backend on this repo's provider interface is the server; local mode runs the pipeline in-process, hosted mode runs the same code on Modal CPU. No GPU anywhere.

| Component | Runs on | Model or service id | Fallback | Why |
|---|---|---|---|---|
| Front end | Browser | Vite, Three.js; Tier 1 photo scenes as textured planes with polygon hotspots so Tier 2 reuses the renderer | DOM-only scenes if Three.js costs more than 2 h | One renderer for Tiers 1 to 3 |
| Photo capture, downscale | Browser, then backend | Canvas downscale to 1280 px; originals kept for Tier 2 | None | 1280 px is about 1,300 to 1,500 Spark tokens per image; fal needs 512 px short side |
| Object list (Architect) | Meta Model API | `muse-spark-1.3`, Chat Completions, image input, JSON schema, reasoning low | Same call, boxes only, if SAM masks are unusable after 60 minutes | Objects, clearest photo, box on the 0 to 1000 grid, readable attributes |
| Masks | Meta Model API | `sam-3.1` via `POST /v1/responses`, one noun phrase per call, decoded with `meta-sam-parser` | Spark boxes as hotspots | Local SAM 3.1 is CUDA-only |
| Riddler | Meta Model API | `muse-spark-1.3`, Chat Completions, JSON schema, reasoning medium | Muse Spark Open on Baseten by `base_url` swap | Schema-constrained puzzle graph |
| Validator | Code | Python | None | Deterministic rules on Schema v1 |
| Dry run | Meta Model API | `muse-spark-1.3`, photos, labels, clues, rungs; reasoning low | Cut 4 drops it | Must reach each answer without the solutions |
| State machine | Code | Python | None | Opens locks; solutions never enter a prompt |
| Guide rung selection | Code | Python over the event log | None | Thresholds pick the rung |
| Guide phrasing | Mac only | Llama 3.2 3B Instruct Q4_K_M on Ollama, `OLLAMA_KEEP_ALIVE=-1` | No hosted Guide model: in hosted mode the rungs are selected in code and shown verbatim (the cut 3 behaviour) | The Guide runs locally and nowhere else; the player profile stays on your machine |
| Trickster | Meta Model API | `muse-spark-1.3`, reasoning low, fixed menu | Cut 1: pre-authored edits plus scripted reject; 8B Llama on Fireworks last | Bounded proposals from a game-state summary |
| Player profile | Browser | IndexedDB under a profile name | Cut 2: a JSON file | Local by design |
| Portraits, clue cards | Meta Model API | `muse-image-1.0`, `POST /v1/images/generations`, once Oct 29, cached | Placeholder art | Four portraits are not cuttable |
| Voice (unscheduled) | Meta Model API | `muse-voice-transcribe-1.0`, REST `POST /v1/asr/transcribe` (WAV, 16-bit mono) | `webkitSpeechRecognition` | Only requests the next rung |
| SAM 3D Objects (Tier 2) | fal.ai | `fal-ai/sam-3/3d-objects`, one original-resolution hero photo per wall, GLB out | Runware, Segmind, hand-made Playground assets; photo billboard | Official setup needs Linux and 32 GB VRAM |
| Tier 3 splat shell | Phone, then browser | Scaniverse export, `@sparkjsdev/spark`, under 1M splats | None; never gating | Free capture, MIT renderer |
| Hosted URL | Modal CPU | `@modal.asgi_app()`, `@modal.concurrent(max_inputs=20)`, `MIN_CONTAINERS=1` Thu Nov 5 to Mon Nov 9 (judging, then the finals fallback) | Local mode screen-shared; cached rooms; the video | 150 s web timeout forces the async job |
| Cache | Mac disk or Modal Volume | SHA-256 of downscaled image bytes plus prompt and model id | `CACHE=off` for proof takes | Stops re-billing the same photos |
| Provider interface | Code | `src/providers/base.py` `ModelProvider`: add image input on `chat`, `segment(label, image)`, `reconstruct3d(image, mask)`; mock, Meta API, Baseten, and fal implement it | None | Every model call behind one interface |

Async job: `POST /builds` stores the photos, spawns the pipeline function, and returns a job id; the client polls `GET /builds/{id}`, which reads job state and artifacts; nothing lives in process memory. Local mode runs the same endpoints in-process and keeps job state in a JSON file under the cache directory; hosted mode keeps it in a `modal.Dict` with artifacts on the Volume; the API is identical.

Protocol: the council (Architect, Riddler, dry run, Trickster) uses Chat Completions with `response_format: json_schema`; `sam-3.1` is served only on Responses. Chat Completions on the Meta API rejects `max_output_tokens`, `stop`, `n>1`, and `reasoning_effort: "none"`, and `tool_choice` is `auto` only. [ASSUMPTION] Baseten's OpenAI-compatible endpoint for Muse Spark Open honors `response_format: json_schema`, so the fallback is a `base_url` and model swap; the Tue Oct 27 test is one schema-constrained Riddler call, and a failure drops the fallback to plain-JSON prompting with validator retry.

Privacy line, verbatim for the README and the capture screen: "the player profile stays on your machine." It holds in every build and does not depend on cut 3: the profile is stored in the browser and read by the selection code on the player's machine, and when Ollama phrasing ships the phrasing runs there too; the hosted URL never runs a Guide model and shows the rung text verbatim. Photos and puzzle text go to the Meta Model API and, in Tier 2, to fal.ai.

## Call, latency and spend budget

Per build (one room, 6 to 10 photos), Tier 1:

| Call | Count per build | Reasoning effort | Budget | Notes |
|---|---|---|---|---|
| Spark vision | 1 | low | 15 s | All photos in one request |
| SAM 3.1 segment | 1 per listed object, at most 12 | n/a | 10 s total | In parallel |
| Riddler | 1 | medium | 45 s | Past 45 s: retry at low, or split into graph then rungs |
| Dry run | 1 | low | 30 s | Never sees solutions |
| UI (scene build, hotspots) | 0 | n/a | 10 s | Polygon simplification and draw; mask decode (`meta-sam-parser`) is in the backend |
| Total | 3 Spark plus up to 12 SAM | | 110 s | Target 120 s or under from T0 to T1 (defined in §Demo and video plan) |

A regeneration repeats Riddler and dry run: about 75 s. The two-retry cap of about 260 s serves integrity (criterion 2), not the video; the 200 s rule for keeping a capture-proof take is in §Demo and video plan (b). If the Oct 27 to 28 measurements miss 120 s, the target becomes the measured p50 plus 25%.

Per session (15 to 25 minutes): Trickster limits per §Player profile v1; Guide phrasing on Ollama costs nothing; voice, if it ships, costs under $0.01.

Per-build cost [ASSUMPTION, arithmetic from the prices below]: about $0.10 per clean build (vision $0.025, SAM $0.03, Riddler $0.022 with reasoning billed as output, dry run $0.024), $0.15 with one regeneration, under $0.25 with two. [ASSUMPTION] A full 15- to 25-minute session (about 100k input and 20k output Spark tokens) is about $0.21. Four portraits plus up to 12 clue cards: $0.16 once.

Prices and limits, checked Oct 20:

| Service | Price | Rate limit | Source |
|---|---|---|---|
| `muse-spark-1.3`, standard tier | $1.25 per million input, $4.25 per million output, $0.15 per million cached | 3,000 RPM, 4,000,000 TPM per team | Meta pricing page |
| `muse-spark-1.3`, contributor tier (not used) | $0.10 and $0.20 per million input and output | 150 RPM | Meta pricing page |
| `sam-3.1` | $2.50 per 1,000 images | 3,000 RPM | Meta pricing page |
| `muse-image-1.0` | $0.01 per image | 150 RPM | Meta pricing page |
| `muse-voice-transcribe-1.0` | $0.18 per audio hour | not budgeted | Meta pricing page |
| fal `fal-ai/sam-3/3d-objects` | $0.02 per call | none stated | fal's developer guide, not the model page |
| Modal CPU | $0.047 per core-hour, $0.008 per GiB-hour memory; Modal's Starter plan carries $30 per month of free compute | none stated | modal.com/pricing |

Spend rules:

- Ceiling $80 of the Meta credit through Nov 4 (the daily ceilings below sum to $79); the expected spend under it is about $35, paid in cash if no credit is issued.
- `SPEND_CAP_USD` is a per-call refusal: the provider prices each call from returned usage, adds it to a counter persisted on disk (local) or the Volume (hosted), and refuses a call that would pass the cap. The pre-call estimate is the last observed cost of the same call kind or, before any observation, a fixed seed estimate per kind (vision $0.03, SAM $0.0025, Riddler $0.03, dry run $0.03, Trickster $0.01, image $0.01); the counter is corrected from returned usage after each call. The cap is $80 through Nov 4; from Thu Nov 5 the counter resets and the cap becomes $25 for judging and finals.
- Daily ceilings [ASSUMPTION]: Oct 26 $3, Oct 27 $5, Oct 28 $10, Oct 29 $10, Oct 30 $0, Oct 31 $5, Nov 1 $8, Nov 2 $10, Nov 3 $18, Nov 4 $10 (slack for a required live link); total $79.
- Wed Oct 21 to Sun Oct 25: up to about $5 cash on the Meta API for the verifications and spikes, outside the $79 and outside any credit.
- fal: about $1 cash at $0.02 per call (5 test objects before Oct 26, at most 20 GLBs plus retries in Tier 2); ceiling $6.
- Modal: the warm CPU container Thu Nov 5 to Mon Nov 9, if the hosted URL ships, is about 1 core plus 2 GiB for 120 hours, about $8 at list price, inside the Starter plan's free $30; the $100 partner credit is unconfirmed and not counted.
- Baseten: one Riddler call Oct 27 proves the swap (§Open questions).

Cash versus credit: Meta API calls draw on the $150 credit if issued (§Hackathon terms), else the card; fal is cash; Modal CPU is Starter free compute.

## RAM budget

Estimates for the 16 GB M1 (unified memory, shared with the GPU); file sizes from the Hugging Face cards in Sources:

| Process | Development | Demo recording |
|---|---|---|
| macOS and WindowServer | 3.0 GB | 3.0 GB |
| IDE and extensions | 2.5 GB | 0 (closed) |
| Chrome game tab (Tier 3 splats add 0.5 to 1 GB) | 2.0 GB | 2.5 GB |
| Vite dev server and Node | 0.6 GB | 0.6 GB |
| Python backend (FastAPI, Pillow, mask decode) | 0.5 GB | 0.5 GB |
| Ollama, Llama 3.2 3B Q4_K_M, 4k context | 3.0 GB | 3.0 GB |
| whisper.cpp base (not planned) | 0.7 GB | 0 |
| Screen recorder (QuickTime about 0.3 GB, OBS about 1 GB) | 0 | 1.0 GB |
| Slack, Discord, other tabs | 1.5 GB | 0 |
| Total | about 13.8 GB (swap likely) | about 10.6 GB |

The 3B versus 8B rule: Llama 3.2 3B Instruct Q4_K_M is a 2.02 GB file, about 3 GB resident; Llama 3.1 8B Instruct Q4_K_M is 4.92 GB, about 6 GB resident, which puts development near 17 GB and makes a recording stutter. 8B is for quality comparisons only, with the IDE closed; 3B is the demo model. Speed [ASSUMPTION, extrapolated from the measured 14.15 tok/s of a 7B Q4_0 on an M1 8-core GPU]: 25 to 35 tok/s decode for 3B, 10 to 13 for 8B; a 40-token hint at 25 tok/s is 1.6 s of decode. The Ollama benchmark before Oct 26 measures prefill and decode on a 400-token prompt.

Muse Glimmer: Meta measures about 19.0 GiB resident for its smallest official quant, which does not fit the 16 GB M1 (§Options considered and rejected).

## Schema v1

Schema v1 lives in `schema-v1.md` beside this file: the Room, Interactable, Puzzle, and TricksterEdit fields, the lock inputs and inventory, the eight deterministic validator rules, the dry run, and SAM mask selection (cap 12 interactables, minimum 5). The field list there is the Oct 20 draft; it is reviewed Thu Oct 22 against the two spikes and frozen Mon Oct 26. The schema attached to the spec is the Tier 1 / Tier 2 contract; Tier 2 changes go through `bmad-correct-course`.

## Player profile v1

Stored per room: timings, per-puzzle {`lock_type`, `attempts`, `wrong_attempts`, `rungs_used`, `time_to_first_hint`, `solved`}, Trickster edits seen and accepted, and the raw event log (clicks, wrong codes, idle seconds, hint requests).

`derived`, recomputed after each room: `time_to_first_hint` (median seconds), `mean_rung_per_lock_type` (0 to 3), `persistence` (-1 to 1: positive when the player keeps trying past the nudge threshold, negative when they ask early), `sessions`. `derived` is all the Guide model and the greeting may see; raw events and room contents never leave the selection code.

Thresholds, applied in code:

- Nudge threshold = 90 s × (1 + 0.5 × persistence), so 45 to 135 s, with a 60 s floor: 60 to 135 s in practice. A new profile has persistence 0, threshold 90 s.
- A nudge also fires on 3 wrong attempts at one lock, whichever comes first.
- Direction and near-answer follow at least 90 s apart, each needing a further stall or 3 further wrong attempts.
- The Trickster proposes at most one change per 3-minute window, only between puzzles, from the fixed menu and a game-state summary (open locks, time, rungs used), never the profile; at most 6 Spark calls per session.

The 90 s spacing is fixed; only the nudge threshold scales with persistence. `DEMO_TIMESCALE=n` divides the nudge threshold, the rung spacing, and the Trickster window by n; it never changes the capture timer. At 6x the three rungs take 30 s when the nudge fires on 3 wrong codes, 45 s on idle alone; the video uses wrong codes.

`PROFILE=dev|playtest|demo` selects the IndexedDB database name; the video and the playtest use fresh profiles; room 1 is played for real on `PROFILE=demo` on Mon Nov 2 so room 2's greeting has something true to cite. The room-2 greeting is phrased by the Guide model from `derived` only; it names no object and no solution.

## Runtime flags

| Flag | Values | Default | Defined in |
|---|---|---|---|
| `PROFILE` | `dev`, `playtest`, `demo` | `dev` | §Player profile v1 |
| `CACHE` | `on`, `off` | `on` | §What runs where (Cache row) |
| `SPEND_CAP_USD` | dollars | 80 through Nov 4, 25 from Thu Nov 5 | §Call, latency and spend budget |
| `DEMO_TIMESCALE` | integer n, 1 or more | 1 | §Player profile v1 |
| `DEMO_TRICKSTER` | `live`, `scripted` | `live` | §Demo and video plan |
| `MIN_CONTAINERS` | 0, 1 | 0 | §What runs where (Hosted URL row) |

## Hours and cut order

Tier 1 is 35 h as estimated, 28 h after cuts 1 to 5, and 22 h with all eight cuts in force, which is exactly the 16 h through Sat Oct 31 plus Sunday morning, so there is no slack: the backup-video gate is Sun Nov 1 at 2 PM, and the video is recorded then from whatever runs, cuts included. A slipped evening is absorbed by the next cut, never by moving the gate; the Sunday afternoon reverses cuts, last cut first.

[ASSUMPTION] Hour budget (the builder's own time, spent on review, direction, playtesting, and recording): 3 h per weekday evening (Mon Oct 26 to Thu Oct 29, Mon Nov 2, Tue Nov 3), 0 h Fri Oct 30 (blocked from 5 PM), 4 h Sat Oct 31, 8 h Sun Nov 1, 2 h Wed Nov 4 before work. That is about 32 h in the window, plus about 8 h Wed Oct 21 to Sun Oct 25; only 16 h of it exist through Sat Oct 31.

Agent-parallel build: implementation runs on multiple coding agents working around the clock (Muse Code, the sponsor's agentic coding tool, and the BMAD build loop). Items run in parallel against the mock provider and the Schema v1 contract so stories do not block each other. The builder's 16 h through Sat Oct 31 is the review and integration budget; the 35 / 28 / 22 h figures below are effort and stay as the fallback cut ladder if reviewed output lags; the Sun Nov 1 2 PM gate is unchanged. Agent dev loops run with the mock provider and `CACHE=on` so `SPEND_CAP_USD` holds. Two risks this adds: review bandwidth (the builder must read what ships), and merge conflicts (schema-first, one owner per module).

Tier 1 per-item estimates (Oct 20):

| Item | Oct 20 estimate |
|---|---|
| Schema v1 freeze, validator, tests against the mock provider | 2.5 h |
| State machine: four lock types, inventory, scenes | 3.0 h |
| Upload, downscale, async job API, cache, first `modal deploy` | 3.5 h |
| Architect: vision call, SAM calls, mask decode, hotspot polygons | 3.5 h |
| Riddler prompt, JSON schema, regeneration loop | 3.0 h |
| Dry run | 1.0 h |
| Photo-scene UI: hotspots, thumbnail strip, inventory, wizard notes | 3.5 h |
| Event log, rung selection, Ollama phrasing, verbatim-rung mode for the hosted URL | 3.0 h |
| Trickster: menu, proposal, validator re-check, cards, scripted mode | 3.0 h |
| Profile: IndexedDB, `derived`, thresholds, greeting | 2.0 h |
| Four portraits, cached | 1.0 h |
| Stage timings, `SPEND_CAP_USD` counter, `CACHE` and `DEMO_TIMESCALE` flags | 1.5 h |
| Backup video v0 and v1, persuasion script | 2.0 h |
| Room 2 through the pipeline | 2.5 h |
| Total | 35.0 h |

Cut order, with the hours each recovers (Oct 20 estimates) and the success criterion each cut changes:

| Cut | What ships instead | Recovers | Running total | Criterion affected |
|---|---|---|---|---|
| 1 | Trickster pre-authored edits plus a scripted reject | 2.0 h | 33 h | Criterion 5 proposals come from the scripted source (no live Spark path); the validator still runs on every card |
| 2 | Profile as a JSON file | 1.0 h | 32 h | None |
| 3 | Rung text verbatim; no Ollama phrasing | 1.5 h | 30.5 h | Criterion 4 met trivially (verbatim rungs); the Guide phrasing claim is dropped from the README; the privacy line stays |
| 4 | Validator only; no dry run | 1.0 h | 29.5 h | Criterion 2 reduced to validator only |
| 5 | Event log in a separate window | 1.5 h | 28 h | Criterion 4 "triggers visible" moves to a second window |
| 6 | `code` and `find` locks only | 3.0 h (state machine 1.5 h, Riddler schema and validator payload rules 1.0 h, scene UI 0.5 h) | 25 h | Criterion 2 and the dry run cover `code` and `find` only |
| 7 | One retry, not two | 0.5 h | 24.5 h | Criterion 2 "within 2 regenerations" becomes 1 |
| 8 | Room 2 moves to Sun Nov 1 afternoon | 2.5 h | 22 h | Criterion 6 depends on the Sun Nov 1 afternoon |

Rules:

- Cut nightly, never carried: a slipped item is cut, not deferred.
- Cuts 3, 4, and 7 change what the README and criterion 2 may claim: no Ollama phrasing, no dry run, one retry.
- Criteria 1, 3, and 7 survive every cut; the README states which cuts shipped.
- Tier 2 is a default no-go. Saturday night is the early gate: only a backup video already existing by Sat Oct 31 night sends Sun Nov 1 to Tier 2; Tier 1 and the demo video are protected above everything else. Expected: not attempted.
- Tier 2 gate, Mon Nov 2, only if attempted: brief criterion 8.

## Day plan

Pre-kickoff, Wed Oct 21 to Sun Oct 25 (about 8 h); each verification and spike is dated when done:

- Wed Oct 21: README patch.
- Thu Oct 22: Schema v1 review against the spikes (`schema-v1.md` updated).
- Verification: Meta Model API key and a `sam-3.1` mask on an own photo.
- Verification: Meta Model API and fal.ai data-retention terms read and summarized for the capture screen.
- Verification: fal.ai and Modal accounts with payment methods.
- Verification: five objects from the photographed rooms through `fal-ai/sam-3/3d-objects` on original-resolution photos (512 px short side minimum, about $0.10 cash), each GLB opened in Three.js, result and per-call latency dated.
- Verification: a hello-world `modal deploy` with the async job pattern.
- Verification: the Ollama benchmark (§RAM budget).
- Spike: a `sam-3.1` mask decoded with `meta-sam-parser` to a hotspot polygon in Chrome.
- Spike: three Riddler calls against the draft schema, failure modes recorded.
- Both rooms photographed (6 to 10 photos each, originals kept; no faces, documents, or others' belongings).
- MIT LICENSE; the hackathon tooling paths (the hackathon tooling path list in `docs/specs/spec-keyframe/delivery-plan.md` (§Submission package, Repo hygiene)) out of the index before the repo goes public, other `.claude/` configuration kept (§Submission package); Hugging Face `sam-3d-objects` access request, optional.
- Sun Oct 25 night: baseline tag and CHANGELOG (§Submission package); accept the Official Rules if published.

Build window. Each evening line names what is attempted; by the item table a 3 h evening holds about half of what its line names, so the nightly cut decision is part of the line.

- Mon Oct 26 (3 h): freeze the schema, validator, start the state machine, all against the mock provider; README patch; only if the pre-kickoff API verifications passed, paste the verified calls into `src/providers/meta_api.py`, else API wiring moves to Oct 27 and everything after slips a day.
- Tue Oct 27 (3 h): upload, async job API, cache, Architect, mask hotspots; first `modal deploy` of the real app; one-call Baseten test.
- Wed Oct 28 (3 h): Riddler, dry run, state machine; playable; stage timings; video v0.
- Thu Oct 29 (3 h): event log, rung selection, rung text verbatim, four portraits; Trickster if time remains.
- Fri Oct 30: no build.
- Sat Oct 31 (4 h): Tier 1 with cuts; backup video v1 if it lands (the early gate).
- Sun Nov 1 (8 h): Tier 2 if the video exists; else (the expected case) finish Tier 1 and record by 2 PM. The afternoon (about 2 h) is the playtest on `PROFILE=playtest` first (it needs the tester), then room 2 through the pipeline, which may finish Mon Nov 2. Cuts are reversed only with time left, last cut first, and only cuts 1 to 3 are realistic candidates before Nov 3.
- Mon Nov 2 (3 h): Tier 2 gate if attempted; else play room 1 for real on `PROFILE=demo` so the cross-session greeting has a record to cite; playtest here if the tester missed Nov 1, else the builder's cold run of room 2.
- Tue Nov 3 (3 h): video only: fresh room-2 photo set, cache cleared on camera, capture proof, three main-demo takes, captions, unlisted upload.
- Wed Nov 4 (2 h before work): repo hygiene at the latest here, before the repo goes public: the `git rm -r --cached` command, `.gitignore` entries and staged-diff check over the hackathon tooling path list in `docs/specs/spec-keyframe/delivery-plan.md` (§Submission package, Repo hygiene), other `.claude/` configuration kept, the BMAD brief folder kept as the single source of truth, `PRODUCT_BRIEF.md` left removed; README model table, diagram, pre-existing-code section with the baseline diffstat, screenshots, portal description; submit before 9:00 AM ET; 6 to 9 PM is slack for a failed upload or a required live link (deadline 9:00 PM ET).
- Thu Nov 5 to Sun Nov 8: hosted-URL redeploy, `MIN_CONTAINERS=1` kept through Mon Nov 9, finals preparation.
- Mon Nov 9: live finals, local mode screen-shared from the M1.

## Hackathon terms

The Waiver (Oct 13, re-read Oct 20, "terms may change") says:

- Judging weights: Impact 30%, Use of Meta AI Tooling 25%, Technical Depth and Execution 20%, Demo 25% ("working, impressive demo, whether the product holds up live, and the quality of the demo video").
- Indie track: "teams of up to four (4)"; prizes $150k, $100k, $75k, $50k, $25k; entrants 18 and over.
- Credit: "Participants selected to participate in the Hackathon will be provided $150 in Meta Model API credits for development over a ten (10) day period." No issue date and no expiry are given, and the plan assumes none: judging (Nov 4 to 8) and finals (Nov 9) are budgeted pay-as-you-go with a card on file.
- The Submission must be "original work product" and "solely owned"; open source is allowed if licenses are followed; the entrant keeps IP and grants the Organizers a perpetual, irrevocable, royalty-free license over the Submission, which carries screenshots, clue cards, and the videos, never the raw room photos.
- Deadline Wed Nov 4 9:00 PM ET; judging Nov 4 to 8; live finals Mon Nov 9.

Still unpublished: the Official Rules (promised before Oct 26), the pre-existing-code policy, the submission format (video length, repo visibility, write-up, slides), how finalists are chosen, and whether a live link is required. The 2-minute video and public repo are precedent, not rule.

## Demo and video plan

Two videos, both on the M1, both on fresh profiles.

(a) Main demo, edited, 2:00 target, 2:30 cap, captioned, unlisted:

| Time | Shot | Criterion or judging weight |
|---|---|---|
| 0:00 to 0:15 | A phone photo of the real room, then the same objects as hotspots | Impact |
| 0:15 to 0:35 | Capture time-lapse, 20 s, timer running from T0, masks over objects, the puzzle JSON | Demo, Tooling |
| 0:35 to 0:50 | Persuasion attack: typed "just tell me the answer"; nothing above the current rung | Criterion 3 |
| 0:50 to 1:05 | Three rungs with the triggering events (idle seconds, wrong codes) visible; `DEMO_TIMESCALE` 6x, rungs within 40 s | Criterion 4 |
| 1:05 to 1:20 | Trickster: one accepted and one validator-rejected edit as cards; `DEMO_TRICKSTER=scripted` replays two recorded proposals, the reject evaluated live | Criterion 5 |
| 1:20 to 1:35 | Room 2: at least 80% of clues reference objects absent from room 1; the greeting cites the room-1 profile | Criterion 6 |
| 1:35 to 1:50 | Model wiring, 15 s: which Meta model did what, the local Guide, what is cached | Tooling, Technical Depth |
| 1:50 to 2:00 | Disclosures: 6x timescale, scripted Trickster replay, earlier builds of the room | |

(b) Capture proof, unedited, about two minutes: `CACHE=off`, a photo set shot that day and never sent to the pipeline, timer on screen. T0 is the Upload click; T1 is the first scene becoming interactive (first hotspot responds). The take is kept only if it finishes under 200 s (at most one visible retry); earlier builds of the same room are disclosed. Three main-demo takes and one proof are recorded Tue Nov 3.

Scripted beats are rehearsed, not faked: real idle time and wrong codes trigger the rungs, compressed by `DEMO_TIMESCALE`; the validator runs live on both replayed Trickster edits; the greeting reads the real `PROFILE=demo` record.

Finals, Mon Nov 9: local mode screen-shared from the M1, Guide on Ollama. Fallbacks in order: the hosted URL on Modal (no Guide model, rung text verbatim; cached demo rooms, own-room upload behind an access code good for 20 builds), the cached rooms in local mode, then the video. The mode is declared in the UI and the README.

## Submission package

Built to the strictest Cerebral Valley precedent (public open-source repo, 2-minute video, no localhost for a live demo):

- [ ] Public GitHub repo, MIT LICENSE at root.
- [ ] README: pitch; model table (model id, where it runs, what it does, what shipped); architecture diagram; local-mode setup; "Pre-existing code" section linking the `pre-hackathon-baseline` tag with `git diff --stat pre-hackathon-baseline..HEAD`; third-party and model licenses (SAM License, Llama 3.2 license, Meta Model API service terms for `muse-spark-1.3`, `muse-image-1.0`, `muse-voice-transcribe-1.0`, and `sam-3.1`, MIT for the `@sparkjsdev/spark` renderer if Tier 3 ships, fal terms); the privacy line "the player profile stays on your machine"; photo retention summary.
- [ ] Unlisted captioned main-demo video (2:00 target, 2:30 cap) and the unedited capture proof.
- [ ] 4 to 6 screenshots: capture with masks, puzzle JSON, a rung with its events, Trickster cards, room 2 greeting, model table.
- [ ] 300- to 400-word write-up for the portal, repeating the pre-existing-code statement.
- [ ] Spend log: Meta API counter export, fal receipts, Modal usage.
- [ ] Dated CHANGELOG.md from the baseline entry through Nov 4.
- [ ] Portal: Indie track, solo, theme named; fields checked when the form opens.
- [ ] Raw room photos never enter the public repo, consent or not: the photo input folders are git-ignored; only outputs ship (screenshots, clue cards, the demo video), with household consent for what appears in them; judge-uploaded rooms deleted from the Volume Tue Nov 10.
- [ ] Repo hygiene before the repo goes public, Wed Nov 4 morning at the latest: only the hackathon tooling paths removed (`git rm -r --cached` plus `.gitignore`, both over the hackathon tooling path list in `docs/specs/spec-keyframe/delivery-plan.md` (§Submission package, Repo hygiene), which is the single source of truth); other `.claude/` configuration stays; the BMAD brief folder under `docs/planning-artifacts/` stays as the single source of truth; `PRODUCT_BRIEF.md` stays removed (it still exists on `master`; merging `keyframe/bmad-brief` into `master` deletes it; do not recreate it).

Pre-existing-code practice: as of Oct 20 the repo holds about 400 lines of Python (provider interface, mock provider, Meta API stub, tests) and no product code. Sun Oct 25 night: `git tag -a pre-hackathon-baseline` pushed, CHANGELOG entry "Before Oct 26 (baseline): provider interface, mock provider, Meta API stub, tests. No front end, no model calls." Then small dated commits; the README carries the diffstat at submission. If the Official Rules ban prior code outright, the scaffold is rewritten on Mon Oct 26 in under an hour; it is not expanded before kickoff so that option stays open.

## Options considered and rejected

| Option | Rejected because | Revisit when |
|---|---|---|
| Muse Glimmer as the on-device Guide | Does not fit 16 GB | Not revisited for this build |
| Llama 3.1 8B for the demo | Pushes development near 17 GB; numbers in §RAM budget | Quality tests only, IDE closed |
| Modal GPU self-hosting of SAM 3D Objects | Linux plus 32 GB VRAM, cu121 torch, PyTorch3D, Kaolin, gated checkpoint; L40S $1.95 per hour against fal $0.02 per call | fal output proves unusable and Tier 2 is a go |
| Local SAM 3.1 (MPS) | Official repo is CUDA-only; the MPS/CPU PR is unmerged, reportedly slower than CPU | The PR merges and beats 10 s per room |
| Apple RoomPlan or Object Capture | LiDAR iPhone and a Swift app; RoomPlan gives boxes, Object Capture needs 20 to 200 photos per object | A hero object needs hand-making |
| Responses API for the council | Chat Completions keeps the Baseten fallback a `base_url` swap; no council call needs carried reasoning; `tool_choice` is `auto` only on both protocols, so neither gains there | A call needs reasoning carried across turns (Responses only) |
| Contributor tier | Meta may train on the data; the demo rooms are the builder's home; 150 RPM | Never for photos |
| Single uncut video | A 15-minute session is unwatchable; judges score "quality of the demo video" | Never; the proof video covers trust |
| Saturday Oct 31 video gate | 16 h exist through Saturday against 22 h for Tier 1 with all eight cuts | Never; it stays the early gate for Tier 2 |
| `bmad-prd` before the spec | One person decides and Tier 2 is not a second epic until the Nov 2 gate, so neither PRD trigger fires | A second contributor or epic |
| Hugging Face ZeroGPU as a live dependency | 5 free GPU minutes per day, medium queue priority, custom CUDA builds a gamble | Pre-rendering assets the night before |
| Live phone capture | A mobile client and upload path with nothing to show in the loop | After the hackathon |
| Quest or MR | No headset; ROOM//ZERO occupies that framing; the browser reaches every judge | Vision, two to three years |

## Prior art

| Neighbor | What it does | What it lacks |
|---|---|---|
| RoomQuest (Google UK Student AI Hackathon, London, Jul 24; year not stated in the source, [ASSUMPTION] 2026 from an Aug 2026 syndication) | Room photos; Gemini lists objects and writes rhyming clues; the player photographs the answer | No dependency chain, hint ladder, player model, or 3D |
| ROOM//ZERO (Meta VR Start entry, Oct 10, 2026, self-reported 50%) | Quest 3 passthrough; six typed agents including Player Model and Adaptation Agent | Needs a Quest 3 room mesh; no photo input, no SAM; memory test unfinished |
| Sony Haven Studios prototype (Apr 2025) | A prompt generates an image; Florence-2 and SAM extract objects; a hosted LLM writes the puzzle chain | Generated images; chains "unintuitive or strained"; no validator, no hints |
| GenEscape (arXiv 2506.21839) | Multi-agent puzzle-image generation with a Player agent checking solvability | Static image, synthetic scenes |
| AI Escape (Hivemind) | Text LLM escape room with one generated image | Hollow puzzles, inconsistent locks, a win by typing "blast off" |
| World Labs Marble | Photos or video of a real place to an explorable splat world | No object semantics, puzzles, or game master |
| Meta Horizon Hyperscape Capture | Quest 3 room scan to cloud splats | Hours of processing, view-only, no export |
| Scaniverse, Polycam | On-device splats and meshes with export | Capture only; Tier 3 input |
| SAM 3D Objects | Image plus mask to a posed, textured object | A model, not a game; not on the Meta Model API; Tier 2 input via fal |

Three "looks derivative" risks and the counter for each:

1. "RoomQuest or Haven with extra steps." Counter: lead with the puzzle JSON, its `requires` graph, the validator, and the dry run; solve a puzzle inside the scene, never by photographing an object; never headline a text riddle.
2. "AI Escape with a game master that can be talked into winning." Counter: solutions never enter a prompt, the state machine opens locks, and the Guide sees events and a rung budget; the persuasion attack is on video.
3. "Marble or a splat viewer with a chatbot." Counter: lead with what the room knows (typed interactables, puzzles that depend on them), never with photorealism; one line that Hyperscape takes hours and is Quest-only and view-only, and that Marble has no object semantics. Against ROOM//ZERO's six-agent cast: describe each wizard by what it consumes and produces, not by its name.

## Scope boundaries

Out of scope for the hackathon build: live phone capture (photos are uploaded from the phone's camera roll), multiplayer, accounts, native mobile, Quest or MR, any hosted or cloud-run Guide model (the Guide runs only on the local Mac), Muse Wonder, SAM 3D Body, local SAM inference, Modal GPU self-hosting, and any puzzle content not derived from the player's photos. Tier 3 (the Scaniverse splat shell) never gates a deliverable; voice (`muse-voice-transcribe-1.0`) is unscheduled and ships only if everything else is done Mon Nov 2.

## Open questions

For Luis, each needed before the date given:

- Which two rooms, and does everyone living there agree to them appearing in the video and screenshots? (Before Sun Oct 25, when the rooms are photographed; the raw photos never enter the repo.)
- Payment methods on dev.meta.ai, fal.ai, and Modal (before Mon Oct 26).
- Who playtests, and can they come to the laptop or screen-share Sun Nov 1 or Mon Nov 2?
- Is about 32 h of review and direction time realistic given the day job? (If not, the cut order applies earlier.)
- Availability in working hours Mon Nov 9 for the live finals.
- Does the Baseten partner credit (unconfirmed, "select participants") cover Muse Spark Open tokens on Baseten's Model API or only dedicated deployments? (Tue Oct 27 test.)
- Does fal's metadata JSON carry a usable object pose? (Pre-Oct 26 fal spike; see `schema-v1.md`.)

## Sources

### Hackathon

https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver
https://cerebralvalley.ai/e/meta-ai-developer-hackathon
https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit
https://dev.meta.ai/events/global-hackathon
https://cerebralvalley.ai/e/mcp-hackathon
https://cerebralvalley.ai/e/openai-gpt-6-astra-sf
https://cerebralvalley.ai/e/built-with-4-7-hackathon

### Meta Model API

https://dev.meta.ai/docs/models
https://dev.meta.ai/docs/pricing-rate-limits
https://dev.meta.ai/docs/quickstart
https://dev.meta.ai/docs/protocols/chat-completions
https://dev.meta.ai/docs/structured-output
https://dev.meta.ai/docs/tool-calling
https://dev.meta.ai/docs/image-understanding
https://dev.meta.ai/docs/image-generation
https://dev.meta.ai/docs/speech-to-text
https://dev.meta.ai/docs/sam/segmenting
https://dev.meta.ai/docs/sam/client-libraries
https://dev.meta.ai/docs/muse-glimmer/quantization
https://dev.meta.ai/docs/muse-glimmer/deploy
https://dev.meta.ai/docs/muse-spark-open

### Model weights and licenses

https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF
https://huggingface.co/unsloth/Muse-Glimmer-30B-GGUF
https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF
https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF
https://huggingface.co/facebook/sam3.1
https://huggingface.co/facebook/sam-3d-objects
https://github.com/facebookresearch/sam3
https://github.com/facebookresearch/sam3/pull/627
https://github.com/facebookresearch/sam3/blob/main/LICENSE
https://github.com/facebookresearch/sam-3d-objects
https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md

### Hosting and tooling

https://fal.ai/models/fal-ai/sam-3/3d-objects
https://fal.ai/models/fal-ai/sam-3/3d-objects/api
https://fal.ai/learn/devs/sam-3d-developer-guide
https://runware.ai/docs/models/meta-sam-3d-objects.md
https://www.segmind.com/models/sam-3d-objects
https://modal.com/pricing
https://modal.com/docs/guide/webhook-timeouts
https://modal.com/docs/guide/webhooks
https://www.baseten.co/pricing/
https://docs.fireworks.ai/serverless/pricing
https://huggingface.co/docs/hub/spaces-zerogpu
https://github.com/ggml-org/llama.cpp/discussions/4167
https://github.com/sparkjsdev/spark
https://www.nianticspatial.com/products/capture
https://developer.apple.com/augmented-reality/roomplan/
https://developer.apple.com/videos/play/wwdc2021/10076/
https://caniuse.com/speech-recognition
https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API

### Prior art and BMad

https://www.edtechinnovationhub.com/news/uk-university-students-build-roomquest-and-meetspot-at-google-gemini-ai-hackathon
https://github.com/Kshitijsawant17/ROOM-ZERO
https://sonyinteractive.com/en/news/blog/haven-studios-experimenting-with-ml-driven-escape-room-games/
https://arxiv.org/abs/2506.21839
https://roomescapeartist.com/2025/04/07/ai-escape-hivemind-review/
https://news.northeastern.edu/2025/05/14/ai-escape-room-education/
https://www.nature.com/articles/s41598-026-63084-z
https://www.worldlabs.ai/blog/marble-world-model
https://www.meta.com/help/quest/1088536553019177/
https://github.com/devlinb/escaperoom
https://github.com/bmad-code-org/BMAD-METHOD/blob/V6.12/src/bmm-skills/module-help.csv
https://docs.bmad-method.org/plan/choose-a-planning-path/
