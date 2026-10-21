---
status: draft
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics"]
inputDocuments:
  - docs/specs/spec-keyframe/SPEC.md
  - docs/specs/spec-keyframe/stack.md
  - docs/specs/spec-keyframe/budgets.md
  - docs/specs/spec-keyframe/player-profile.md
  - docs/specs/spec-keyframe/delivery-plan.md
  - docs/specs/spec-keyframe/glossary.md
  - docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md
  - docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
---

# Keyframe - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Keyframe, decomposing the requirements from the spec (`SPEC-keyframe`, which stands in for a PRD: capabilities CAP-1 to CAP-13 are the functional requirements) and the architecture spine (AD-1 to AD-18) into implementable stories. No UX design contract exists; the UI requirements are carried in the functional requirements.

## Requirements Inventory

### Functional Requirements

FR1: The player uploads 6 to 10 JPEG photos of one room from the browser; the client downscales each to a 1280 px long edge with EXIF orientation applied and uploads it with the original in one request; HEIC, PNG and every other format are rejected with a message stating the JPEG requirement. (CAP-1)
FR2: One Architect vision call lists the room's objects with the clearest photo, a box, and readable attributes for each. (CAP-1)
FR3: One `sam-3.1` call per listed object segments it; mask selection (best IoU against the vision box, plurals grouped, masks under 1% dropped, cap 12) yields 5 to 12 typed interactables with polygon hotspots, falling back to the box rectangle when SAM returns nothing. (CAP-1)
FR4: When fewer than 5 interactables survive, the build ends with status `needs_more_photos` before any authoring call and the capture screen asks for more photos. (CAP-1)
FR5: The capture screen shows a running timer from the Upload click (T0) to the first hotspot responding (T1) and the build's current stage; a build that outlasts one HTTP request still completes and reaches the player through job polling. (CAP-1, CAP-10)
FR6: The capture screen shows the retention summary: photos and puzzle text go to the Meta Model API and, in Tier 2, to fal.ai. (CAP-13)
FR7: One Riddler call authors 4 to 6 puzzles (exactly one exit; lock types `code`, `order`, `use_on`, `find`; clue, lore of at most 60 words, three rungs each) that reference only listed interactables and attributes the vision call read. (CAP-2)
FR8: Every authored room passes the eight deterministic validator rules of Schema v1 before it is stored; failures produce structured reasons that never quote a solution token or an answer. (CAP-2)
FR9: A dry run that sees photos, labels, clues and rungs, never solutions, must reach every answer; a mismatch fails the room. (CAP-2)
FR10: A failed validation or dry run regenerates the room (Riddler plus dry run) with the failure reasons, at most 2 times; then the build ends with status `needs_recapture` and the capture screen asks for a re-capture. (CAP-2)
FR11: The player plays the room as photo scenes with mask hotspots, a thumbnail strip to move between photos, a persistent inventory, and wizard notes. (CAP-3)
FR12: A lock opens only on its correct input, judged by the server: `code` typed, `order` as a hotspot-click sequence, `find` by clicking the target, `use_on` by dragging an inventory item onto the target; solving a `find` puzzle moves its interactable into the inventory; wrong attempts are counted per lock. (CAP-3)
FR13: Opening the exit lock ends the room with a completion screen showing time and hints used, and the session's room result is recorded. (CAP-3)
FR14: Player text, typed or transcribed, is reduced to a hint request and never yields anything above the current rung; a scripted "just tell me the answer" attack fails. (CAP-3)
FR15: The Guide selects the rung in code from the event log: a nudge after the threshold of no progress (90 s scaled by persistence, 60 to 135 s) or 3 wrong attempts at one lock; direction and near-answer at least 90 s apart, each after a further stall or 3 further wrong attempts. (CAP-4)
FR16: Each rung change is shown with its triggering events (idle seconds, wrong attempts). (CAP-4)
FR17: In local mode the selected rung is phrased by Llama 3.2 3B on Ollama (about 40 tokens, prompt under 400 tokens with a fixed prefix, 5 s timeout with the verbatim rung as fallback); in hosted mode the rung text is shown verbatim and no Guide model runs. (CAP-4)
FR18: Between puzzles, at most once per 3-minute window and at most 6 Spark calls per session, the Trickster proposes one change from the fixed menu (`decoy`, `merge`, `loosen`, `shortcut`) from a game-state summary that never includes the profile. (CAP-5)
FR19: Every Trickster proposal is re-validated; accepted and rejected outcomes appear as cards; an accepted edit changes the session's effective room without mutating the stored room; a provider error during a window shows a skipped card and play continues. (CAP-5)
FR20: The browser stores the player profile (IndexedDB under the `PROFILE` name; a local JSON file under cut 2) with per-room results and the derived block; a session start sends only the derived block. (CAP-6, CAP-13)
FR21: The second room's greeting cites how the player played the first, phrased from the derived block only, naming no object and no solution; hint thresholds scale to the player's persistence. (CAP-6)
FR22: Results recorded under a demo timescale are excluded when the derived block is recomputed. (CAP-6, CAP-8)
FR23: Four wizard portraits are generated once with `muse-image-1.0`, committed, and shown in play; play never generates images. (CAP-7)
FR24: `DEMO_TIMESCALE=n` divides the nudge threshold, the rung spacing, and the Trickster window by n without touching the capture timer or event timestamps. (CAP-8)
FR25: `DEMO_TRICKSTER=scripted` replays recorded proposals with the validator run live on each; cut 1 uses the same scripted source with pre-authored proposals. (CAP-5, CAP-8)
FR26: `GET /meta` exposes mode, Guide, Trickster source, timescale, cache, profile, disclosure text and retention text; the UI shows the active demo disclosures. (CAP-8, CAP-13)
FR27: Every hosted model call is cached by key (model id, schema hash, full prompt, reasoning effort, image hashes, attempt); with `CACHE=on` a hit is served without billing; `CACHE=off` bypasses the cache, never the ledger. (CAP-9)
FR28: Every hosted call that misses the cache is priced and recorded in an append-only ledger; a call that would pass `SPEND_CAP_USD` is refused and surfaced; the counter survives restarts. (CAP-9)
FR29: The ledger is exported daily (locally at API startup and after every build to `spend/exports/ledger-<date>.json`; hosted by a scheduled function at 06:00 ET); `reset` refuses to run without that day's export. (CAP-9)
FR30: Every room carries provenance (model ids, prompt hashes, stage timings, regeneration count, spend per stage); the spend log export derives from the ledger. (CAP-9)
FR31: Judges open the hosted URL and play cached demo rooms through the same API as local mode. (CAP-10)
FR32: Judges may build their own room behind an access code, at most 20 builds; builds run as a spawned job and survive the host's 150 s web timeout. (CAP-10)
FR33: Judge-uploaded rooms, their originals, sessions and cache entries are deleted together on Tue Nov 10; hosted session logs are deleted 24 h after their last event. (CAP-10, CAP-13)
FR34: (Tier 2, gated, default no-go) The room is rebuilt as a walkable 3D scene in the same scene graph with up to 20 objects reconstructed by `fal-ai/sam-3/3d-objects` from original-resolution hero photos; puzzles trigger by raycast. (CAP-11)
FR35: (Unscheduled) The player asks the wizards for help by voice (`muse-voice-transcribe-1.0` REST, browser recognition as fallback); speech is reduced to a hint request. (CAP-12)
FR36: Raw room photos never enter the repo: the input folders are git-ignored and a test asserts it; the hosted server never persists profile data. (CAP-13)

### NonFunctional Requirements

NFR1: Capture performance: T0 to T1 in 120 s or less on the M1 with `CACHE=off` and a never-built photo set (or measured p50 plus 25% if re-based after the Oct 27 to 28 measurements); stage budgets vision 15 s, SAM 10 s, Riddler 45 s, dry run 30 s, scene 10 s; a regeneration about 75 s; a capture-proof take is kept only under 200 s.
NFR2: Hint latency: about 40 tokens in 5 s or less from a prompt under 400 tokens with a fixed prefix.
NFR3: Hardware: everything local runs on one 16 GB M1 MacBook Pro without CUDA; the Guide model stays near 3 GB resident; demo-recording RAM about 10.6 GB; no local SAM 3.1, SAM 3D Objects, or 30B models.
NFR4: Privacy: the Guide model runs only on the player's Mac; the player profile stays on the player's machine and only the derived block reaches the Guide model and the greeting; raw room photos are never committed; the capture screen shows the retention summary; Meta Model API standard tier only, never contributor.
NFR5: Integrity: solutions never enter any model prompt or any play response; validator reasons never quote a token or answer; only the server's session state machine opens locks.
NFR6: Cost: `SPEND_CAP_USD` 80 through Wed Nov 4 and 25 from Thu Nov 5; fal at most $6 cash; development loops run against the mock provider with `CACHE=on`.
NFR7: Reliability: builds are persisted jobs that survive the 150 s web timeout and resume at the last persisted stage after a restart; adapters retry once with backoff on 429 and 5xx only; at most 2 regenerations.
NFR8: Testability: `pytest` passes offline against the mock provider for every story; adapter tests use recorded fixtures; an import-boundary test, a type-staleness test, and ignore-file tests run in the offline suite.
NFR9: Rate limits: within Meta Model API limits (Spark 3,000 RPM and 4,000,000 TPM; `sam-3.1` 3,000 RPM; `muse-image-1.0` 150 RPM); segment concurrency at most 12.
NFR10: Platform: Chrome on the Mac; Tier 1 scenes as Three.js textured planes; the Tier 2 gate requires 30 fps or better on the M1.
NFR11: Schedule: the backup video is recorded Sun Nov 1 by 2:00 PM from whatever runs; Tier 2 is a default no-go unless that video exists Sat Oct 31 night; Fri Oct 30 no build; Tue Nov 3 video only; submit Wed Nov 4 before 9:00 AM ET (deadline 9:00 PM ET); cuts are made nightly in the published order.
NFR12: Demo honesty: the 6x timescale, the scripted Trickster replay, and earlier builds of a room are disclosed in the video and the README; the README states which cuts shipped.
NFR13: Submission and hygiene: public MIT repo with third-party and model licenses listed; `_bmad/` and `.claude/` removed from the index before the repo goes public (Wed Nov 4 morning at the latest); `PRODUCT_BRIEF.md` stays removed; pre-existing code disclosed with the `pre-hackathon-baseline` tag and diffstat; the scaffold is not expanded before Mon Oct 26.

### Additional Requirements

- Starter: no starter template for the backend; the existing scaffold (`src/providers` `ModelProvider` ABC with mock and Meta stub, `src/config.py` `Settings`, `pytest` under `tests/`) is ratified. The first providers story bumps `requires-python` to `>=3.13`, moves the Stack table into `[project.dependencies]` with `==` pins, drops `requirements.txt`, and sets the Meta `DEFAULT_BASE_URL` to `https://api.meta.ai/v1`. The client `web/` is created from the Vite 8 vanilla-ts template (TypeScript ~6.0.3) with three 0.186.1 and Node 24 LTS (`.nvmrc` = 24). This shapes Epic 1 Story 1.
- Paradigm and boundaries (AD-1): pure `src/domain`; `src/council` and `src/pipeline` depend only on the domain and ports; adapters in `src/providers` and `src/infra`; `src/api` wires; `tests/test_boundaries.py` enforces imports.
- One data shape (AD-2): Schema v1 realized once as pydantic models in `src/domain/schema.py`; tagged unions for `solution` and `payload`; `GET /schema` returns every API model; `web/types` generated and committed with a staleness test; snake_case JSON end to end.
- Solution boundary (AD-3): `to_prompt_view` (RoomView) and `to_play_view` (PlayView) in `src/domain/redact.py`; play routes return only PlayView; full Room only via the access-coded `GET /builds/<job_id>/room`; sentinel-solution fixture tests over every council prompt and every play response.
- Event-sourced sessions (AD-4): typed client events (`click`, `lock_input`, `hint_request`) and server events (`idle_tick`, `trickster_card`, `rung_change`); server-stamped `t_ms`; `idle_tick` appended on `GET /sessions/<id>` after 5000 ms (client polls every 2000 ms); `SessionStateMachine.apply` the sole writer of session state; replay equals live.
- Model ports (AD-5): synchronous `ModelProvider` with fixed signatures (`chat` with images, `response_schema`, `reasoning_effort`; `segment`; `reconstruct3d`; `generate_image`; `transcribe`); `strict_schema` helper; one provider per council role; `HintPhraser` (`phrase`, `greet`) implemented only by Ollama and verbatim adapters; adapters `mock`, `meta`, `openai_compatible`, `fal`, `ollama`.
- Guarded calls (AD-6): cache then ledger guard on every hosted call; the mock bypasses both; `SpendLedger` serializes `guard` per process; `scripts/ledger.py reset|export`.
- Persisted build job (AD-7): multipart `POST /builds` with client-produced downscale plus original; ingest validation (6 to 10, JPEG only, 1280 px long edge, orientation 1); stages `ingest → architect → segment → author → validate → dryrun → scene` through `JobRunner`, `JobStore`, `ArtifactStore`; hosted runner `@app.function(timeout=900)` via `.spawn()`, Volume commit and reload, watchdog for dead runners; job statuses `queued`, `running`, `done`, `failed`, `needs_more_photos`, `needs_recapture`.
- Profile ownership (AD-8): `Derived` and `RoomResult` pydantic models with bounds; `POST /sessions {room_id, derived}`; `GET /sessions/<id>/result` with a `demo` flag; local-only cut-2 `GET|PUT /profile/<name>`; retention rules and the retention string in `src/api/meta.py`.
- Two modes (AD-9): `MODE` selects `JobStore`, `ArtifactStore`, `JobRunner`, `SessionStore`, `LedgerStore`, `Cache` in `src/infra`; `GUIDE` alone selects `HintPhraser`; one origin (FastAPI mounts `web/dist`; routes under `/api/`; Vite proxy in development); `X-Access-Code` on `POST /builds` and the full-Room download; 20-build quota; `scripts/seed_rooms.py` and `scripts/purge_judge_rooms.py`; `max_containers=1`; daily ledger snapshot by `modal.Cron("0 6 * * *", timezone="America/New_York")`; local live ledger `spend/ledger.jsonl`, daily exports committed.
- Clocks (AD-10): a `Clock` port; the session clock applies `DEMO_TIMESCALE` to thresholds only; the build clock never applies it.
- Scene contract (AD-11): Three.js textured planes with polygon hotspots in downscaled-JPEG pixel space served from `GET /rooms/<room_id>/photos/<i>`; hotspot id equals interactable id; the DOM-only fallback keeps the contract.
- Validation gate and edits (AD-12): pure `validate` and `check_dry_run`; the pipeline makes the dry-run call; the build Room is immutable; `domain/edits.py` `validate_edit` and `apply_edit`; edits folded at replay with `room_revision`; `GET /sessions/<id>/room`.
- Errors (AD-13): typed errors (`ProviderError`, `ValidationError`, `DryRunError`, `TooFewInteractables`, `UnsupportedImage`, `BuildQuotaExceeded`, `SpendCapExceeded`); `regenerate.py` the sole regeneration loop (`REGEN_MAX`); envelope `{error: {code, message, stage}}`.
- Configuration (AD-14): environment read once by `Settings`; product flags and per-role adapter settings; `.env` git-ignored, `.env.example` complete (tested); hosted secrets in the `modal.Secret` `keyframe`; `GUIDE=ollama` refused under `MODE=hosted`.
- Demo mode (AD-15) and provenance (AD-16): scripted Trickster source with the live validator; the `Meta` model; provenance written by the pipeline.
- Ownership (AD-17): one owner per package (`domain`, `council`, `pipeline`, `providers`, `api`, `infra`, `web`); a story touches one package plus tests or first declares its port change.
- Identity (AD-18): `ix_` ids minted by the segment stage; `ArchitectResponse` correlated by position; Riddler ordinal keys `p1`..`p6` mapped to `pz_`; exact-id parsing; boxes converted to pixels at segment.
- Schema timeline: the Thu Oct 22 review makes one pick (decoy storage, options A, B, C in `schema-v1.md`, A recommended); the schema freezes Mon Oct 26; later changes through `bmad-correct-course`.
- Carried to Mon Oct 26 (not on the critical path before then): the Fireworks Trickster fallback model id, the `GET /meta` retention wording, the hosted full-Room download route.

### UX Design Requirements

No UX design contract exists. The UI surfaces (capture screen with timer, stages and retention summary; photo scenes with hotspots, thumbnail strip, inventory and wizard notes; lock inputs; rung display with triggers; Trickster cards; completion screen; room-2 greeting; demo disclosures) are specified by FR1 to FR26 and AD-11.

### FR Coverage Map

FR1: Epic 2 - JPEG-only upload with client downscale
FR2: Epic 2 - Architect vision call
FR3: Epic 2 - SAM segmentation and mask selection into interactables
FR4: Epic 2 - needs_more_photos exit
FR5: Epic 2 - capture timer, stages, job polling (hosted spawn in Epic 7)
FR6: Epic 2 - retention summary on the capture screen
FR7: Epic 2 - Riddler authoring
FR8: Epic 1 - eight-rule validator with structured reasons
FR9: Epic 2 - dry run
FR10: Epic 2 - regeneration loop and needs_recapture
FR11: Epic 1 - photo scenes, hotspots, thumbnail strip, inventory, wizard notes
FR12: Epic 1 - server-judged locks and inventory
FR13: Epic 1 - completion screen and room result
FR14: Epic 3 - hint requests never exceed the current rung
FR15: Epic 3 - rung selection thresholds
FR16: Epic 3 - rung changes shown with triggers
FR17: Epic 3 - Ollama phrasing locally, verbatim hosted
FR18: Epic 4 - bounded Trickster proposals
FR19: Epic 4 - re-validated edits as cards, session-scoped
FR20: Epic 5 - browser-owned profile, derived-only session start
FR21: Epic 5 - room-2 greeting and scaled thresholds
FR22: Epic 5 - demo results excluded from derived
FR23: Epic 3 - four wizard portraits, generated once
FR24: Epic 3 - demo timescale on thresholds only
FR25: Epic 4 - scripted Trickster source with live validator
FR26: Epic 1 - GET /meta endpoint (disclosure UI in Epic 6)
FR27: Epic 2 - model-call cache
FR28: Epic 2 - spend ledger and cap
FR29: Epic 2 - daily local ledger export (hosted snapshot in Epic 7)
FR30: Epic 2 - provenance on every room
FR31: Epic 7 - hosted URL with demo rooms
FR32: Epic 7 - access-coded judge builds, spawned runner
FR33: Epic 7 - deletion and retention
FR34: Epic 8 - walkable 3D room (gated)
FR35: Epic 9 - voice help (unscheduled)
FR36: Epic 1 - ignore-file guarantees for raw photos (hosted no-profile in Epic 7)

## Epic List

### Epic 1: Play a room in the browser
A player opens a room in Chrome and plays it end to end: photo scenes with hotspots, a thumbnail strip, an inventory, wizard notes, all four lock types judged by the server, and a completion screen. Built on a hand-authored fixture room and the mock provider, so it ships on Mon Oct 26 with no model access and becomes the play surface every later epic feeds.
**FRs covered:** FR8, FR11, FR12, FR13, FR26 (endpoint), FR36
**Implementation notes:** first stories ratify the scaffold (pins, `requires-python>=3.13`, `Settings`, boundary and ignore-file tests), realize Schema v1 after the Mon Oct 26 freeze, and create `web/` from the Vite 8 vanilla-ts template; session state is event-sourced (AD-4) with `t_ms` stamped by the server; `order` and `use_on` locks are separate stories so cut 6 drops them cleanly.

### Epic 2: Turn your photos into a verified room
A player uploads 6 to 10 JPEG photos and, within the capture target, gets a room built from their own objects that has passed the validator and the dry run, ready to play in Epic 1's surface. Every hosted call is cached, priced, capped, and recorded in a ledger that is exported daily.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR9, FR10, FR27, FR28, FR29 (local export), FR30
**Implementation notes:** the spend/cache guard lands before the first real API call (Mon Oct 26 to Tue Oct 27); the Meta adapter is wired only after the pre-kickoff verifications passed; the dry run (cut 4) and the second regeneration (cut 7) are separate stories; stage timings feed the 120 s measurement on Oct 27 to 28.

### Epic 3: A game master that helps without telling
While playing, the player gets stuck and the Guide escalates nudge, direction, near-answer from how they play, with the triggering events visible; asking for the answer yields nothing above the current rung; the four wizard portraits appear in play. Hints are phrased locally by Llama 3.2 3B and never contain the solution.
**FRs covered:** FR14, FR15, FR16, FR17, FR23, FR24
**Implementation notes:** rung selection is pure code inside `SessionStateMachine.apply` (AD-4); Ollama phrasing is its own story (cut 3 ships the verbatim adapter only); the triggers panel is its own story (cut 5 moves it to a second window); portraits are generated once by a script and committed.

### Epic 4: The room fights back, fairly
Between puzzles the Trickster proposes one bounded change; the validator decides; the player sees accepted and rejected cards and the room they play changes only when an edit is accepted. A scripted source replays recorded proposals for the video, with the validator still live.
**FRs covered:** FR18, FR19, FR25
**Implementation notes:** decoy storage follows the Thu Oct 22 schema pick (option A recommended); edits are session-scoped and folded at replay (AD-12); the scripted source story doubles as cut 1.

### Epic 5: The second room remembers you
A returning player starts a second room and is greeted from how they played the first; hint thresholds adapt to their persistence; the profile stays in their browser.
**FRs covered:** FR20, FR21, FR22
**Implementation notes:** the profile lives in IndexedDB (cut 2: a local JSON file through the local-only profile route); the greeting is phrased from the derived block only; room 2 moves to Sun Nov 1 afternoon under cut 8.

### Epic 6: Record the demo and submit
The builder records the backup video by Sun Nov 1 2:00 PM, the capture proof and main demo on Tue Nov 3, and submits on Wed Nov 4 before 9:00 AM ET, with every demo shortcut disclosed, the README complete, and the repo cleaned for the public.
**FRs covered:** FR26 (disclosure UI)
**Implementation notes:** carries NFR11 to NFR13; builder stories (videos, submission) sit beside agent stories (disclosure overlay, README model table, architecture diagram, pre-existing-code section, CHANGELOG, hygiene pass); the hygiene pass (`_bmad/` and `.claude/` out, `PRODUCT_BRIEF.md` stays deleted) is the Wed Nov 4 morning story.

### Epic 7: Judges play it themselves
A judge opens the hosted URL, plays the cached demo rooms, and can build their own room behind an access code, with builds surviving the host's web timeout and judge data deleted on Tue Nov 10.
**FRs covered:** FR29 (hosted snapshot), FR31, FR32, FR33
**Implementation notes:** Tier 1.5: deployed from Tue Oct 27 for smoke tests, made judge-ready Thu Nov 5 to Sun Nov 8; same code as local mode, adapters selected by `MODE` (AD-9); no Guide model hosted (verbatim rungs).

### Epic 8: Walk the room in 3D
The player walks a 3D version of the room with reconstructed objects and triggers puzzles by raycast.
**FRs covered:** FR34
**Implementation notes:** Tier 2, default no-go: attempted Sun Nov 1 only if the backup video already exists Sat Oct 31 night; gate Mon Nov 2 (7 of 10 interactables in position, 30 fps, raycast puzzles); no second epic is planned until the gate passes.

### Epic 9: Ask the wizards by voice
The player asks for help by voice and gets the same rung a click would give.
**FRs covered:** FR35
**Implementation notes:** unscheduled; ships only if everything else is done Mon Nov 2.
