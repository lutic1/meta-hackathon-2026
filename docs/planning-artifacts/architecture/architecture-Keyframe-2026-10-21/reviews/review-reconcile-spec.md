---
review: reconcile-spec
target: ../ARCHITECTURE-SPINE.md
inputs:
  - ../../../../specs/spec-keyframe/SPEC.md
  - ../../../../specs/spec-keyframe/stack.md
  - ../../../../specs/spec-keyframe/budgets.md
  - ../../../../specs/spec-keyframe/player-profile.md
  - ../../../../specs/spec-keyframe/delivery-plan.md
  - ../../../../specs/spec-keyframe/glossary.md
  - ../../../briefs/brief-Keyframe-2026-10-20/schema-v1.md
author: Luis Ticas
date: 2026-10-21
verdict: revise
---

# Reconciliation review: spec package against the architecture spine

## Verdict

**Revise before stories are cut.** The paradigm, the seventeen ADs, and the package layout carry the spec's load-bearing rules (solution boundary, server-authoritative session, async build, one schema, Guide on the Mac only, spend guard, two clocks). What did not land is a layer of quiet requirements: the "too few interactables" exit, the per-session Trickster caps, the hosted 20-build cap, the derived-block fence around Spark prompts, the greeting, the cache's storage mode, and where the pipeline actually executes on Modal. Three findings are contradictions between a spine rule and the spec (dry run declared pure, cut 2 versus AD-8, cut 1 versus AD-15). All are fixable as amended AD text, convention rows, or Deferred entries; none require a new AD or a paradigm change.

Method: every capability's intent and success line, every constraint bullet, every flag in `stack.md`, every cap in `budgets.md`, every threshold in `player-profile.md`, and every gate and cut in `delivery-plan.md` was checked for (a) a spine rule that realizes it, (b) a row in the Capability map, and (c) a spine rule that contradicts it.

## What landed (no action)

- CAP-1 pipeline shape, 1280 px plus original, stage timings on the build clock (AD-7, AD-10, conventions).
- CAP-2 validator as write gate, immutable room versions, regeneration loop at most 2 then re-capture, typed errors (AD-12, AD-13, state diagram).
- CAP-3 event-sourced session, state machine as the only lock writer, client posts events (AD-4, AD-11).
- CAP-4 rung selection in domain, `HintPhraser` port that no cloud adapter may implement (AD-5), `GUIDE=ollama|verbatim` as the cut-3 switch.
- CAP-5 `TricksterEdit` as a new validated version, `trickster_window` on the session (AD-4, AD-12).
- CAP-6, CAP-13 profile in the browser, `derived` only at session start, nothing profile-shaped persisted on the server (AD-8).
- CAP-8 `DEMO_TIMESCALE` on the session clock only; `DEMO_TRICKSTER=scripted` swaps the source, not the check; `GET /meta` carries disclosure (AD-10, AD-15).
- CAP-9 guard-then-cache order, `CACHE=off` never bypasses the ledger, persisted counter, spend log derived from the ledger (AD-6, AD-16).
- CAP-10 async job that outlives 150 s, one codebase two modes (AD-7, AD-9).
- CAP-11, CAP-12 seams reserved in the port (`reconstruct3d`, `transcribe`) and the scene graph (AD-5, AD-11, Deferred).
- Build model: one owner per package, offline tests against the mock (AD-17); schema-first (AD-2).

## Findings

### F1 (high) — AD-12 declares the dry run a pure function; the spec makes it a Spark call

- **Location:** AD-12 Rule: "`validate(room)` and `dry_run(room_view)` are pure functions".
- **Problem:** `stack.md` ("Dry run | Meta Model API | `muse-spark-1.3`") and `schema-v1.md` §Dry run define the dry run as a second model call that receives photos, labels, clues, and rungs and must return an answer per puzzle. It cannot be pure. Worse, the comparison of the returned answers with the solutions needs the full `Room`, which AD-3 forbids `src/council` from seeing (council is typed on `RoomView`). As written, an agent either makes `dryrun.py` call the model (breaking AD-12) or compares answers inside council (breaking AD-3). The sentence also leaves nowhere for the "reasoning low, 30 s" budget to attach.
- **Fix:** Rewrite the AD-12 Rule opening: "`validate(room)` is a pure function in `src/domain/validator.py`. The dry run is three parts: `council/dryrun.py` builds the prompt over `RoomView`; the pipeline `dryrun` stage makes the model call through the injected `ModelProvider` (reasoning low); `domain/validator.py::check_dry_run(room, answers)` is a pure comparison of answers to solutions in the solution shape and is the only place solutions and answers meet." Keep the rest of the rule as is.

### F2 (high) — The "fewer than 5 survivors" exit and ingest validation are missing; job terminal states are unnamed

- **Location:** AD-7 Rule, AD-13 Rule, the build `stateDiagram`.
- **Problem:** CAP-1 success: "Fewer than 5 survivors asks for more photos before any authoring"; `schema-v1.md` §SAM mask selection repeats it; the Constraints cap photos at 6 to 10 and interactables at 5 to 12. The spine's stage list and state diagram have no exit between `segment` and `author`; AD-13's error set (`ProviderError`, `ValidationError`, `DryRunError`, `SpendCapExceeded`) has no class for it; the diagram's `recapture` terminal has no job status name. Three owners (pipeline, api, web) each need the same job status enum and the same two "come back with photos" outcomes, and the spine gives them neither.
- **Fix:** (a) Add to AD-7 Rule: "`ingest` rejects fewer than 6 or more than 10 photos; `segment` ends the job with status `needs_more_photos` when fewer than 5 interactables survive mask selection; no authoring call is made." (b) Add `TooFewInteractables` to AD-13's error list and `needs_more_photos` and `needs_recapture` as terminal job statuses; add a convention row "Job status: `queued`, `running` (with `stage`), `done`, `failed`, `needs_more_photos`, `needs_recapture`". (c) Add a `segment --> needs_more_photos: survivors < 5` edge to the state diagram.

### F3 (high) — Where the pipeline executes in hosted mode is unspecified

- **Location:** AD-7 Rule, AD-9 Rule, Structural Seed (`api/modal_app.py`), hosted flowchart.
- **Problem:** CAP-10 success hinges on "a build outlasting the host's 150 s web timeout still completes". `stack.md` §Async build job says `POST /builds` "spawns the pipeline". The spine says only "no request blocks on a stage". On Modal, a background task inside the `@modal.asgi_app` container is tied to that container's lifetime and to `@modal.concurrent(max_inputs=20)`; with `MIN_CONTAINERS=0` (the default until Nov 5) an idle scale-down can kill a build that is still in `author`. The spec's intent is a separate Modal function (`.spawn()`), which is a different adapter from the local in-process task. AD-9's mode-selected list (`JobStore`, `ArtifactStore`, `HintPhraser`, ledger persistence) has no runner.
- **Fix:** Add `JobRunner` to the ports in `pipeline/ports.py` and to AD-9's mode-selected list: "local: an in-process task; hosted: `modal.Function.spawn` of the stage runner in a separate function, so the web container never owns a build. Every stage rereads job state from `JobStore` on entry so a restarted runner resumes at the last persisted stage." Add the runner to the Structural Seed (`infra/local.py`, `infra/modal.py`).

### F4 (medium) — Per-session Trickster caps are not enforced anywhere

- **Location:** AD-4 Rule, AD-15 Rule, CAP-5 row.
- **Problem:** CAP-5 success and `player-profile.md` §Trickster bounds: at most one change per 3-minute window, only between puzzles, at most 6 Spark calls per session. AD-4 names `trickster_window` as state but says nothing about the 6-call cap or the "between puzzles" condition, and `SpendLedger` guards dollars, not counts. The CAP-5 row cites AD-3, AD-12, AD-15 but not AD-4 or AD-6, so the session owner has no rule telling them the cap is theirs.
- **Fix:** Add to AD-4 Rule: "`SessionStateMachine` opens `trickster_window` only when a lock has just opened and the previous window closed at least 3 minutes ago (session clock); it counts Trickster proposal calls and refuses the seventh; the API never calls the Trickster outside an open window." Add AD-4 and AD-6 to the CAP-5 row.

### F5 (medium) — The derived block can reach Spark prompts; the Trickster must never see the profile

- **Location:** AD-3 Rule, AD-8 Rule.
- **Problem:** The Constraints say "the Guide model and the greeting see only the profile's derived block", and `player-profile.md` says the Trickster works "from a game-state summary (open locks, time, rungs used), never the profile". AD-8 puts `derived` on the session start payload, and from there nothing stops `council/trickster.py` or the dry-run prompt from including it. The privacy line ("the player profile stays on your machine") is only true if `derived` never leaves for the Meta API.
- **Fix:** Add to AD-3 Rule: "`derived` is consumed only by `domain/rungs.py` (thresholds) and the `HintPhraser` port; `RoomView` and the Trickster game-state summary carry no profile fields, and the test suite asserts no `derived` key in any rendered Spark prompt fixture." Add AD-3 to the CAP-6 and CAP-13 rows.

### F6 (medium) — The room-2 greeting has no home

- **Location:** CAP-6 row ("`web/profile`, session start payload"), AD-5, AD-8.
- **Problem:** CAP-6 success: "the greeting names no object and no solution"; `player-profile.md`: "phrased from the derived block only". The spine names no component that produces it, no model that phrases it, and no hosted behavior. If an agent routes it to `muse-spark-1.3`, it both leaks `derived` to a cloud model (F5) and contradicts "only the Guide model and the greeting see the derived block" in spirit, since the spec places the greeting beside the Guide.
- **Fix:** Add to AD-5 Rule: "The greeting is produced through the same `HintPhraser` port from `derived` and a fixed template (Ollama locally; the verbatim adapter fills the template with the numbers hosted); it receives no room content." Add `council/greeting.py` (template over `derived`, no `RoomView`) to the seed and to the CAP-6 row.

### F7 (medium) — Hosted own-room quota, access-code scope, demo-room seeding, and the Nov 10 purge are missing

- **Location:** CAP-10 row, conventions "Config and auth", AD-8 last clause.
- **Problem:** CAP-10 success: "at most 20 own-room builds"; judges "play cached demo rooms"; "judge-uploaded rooms are deleted Tue Nov 10". The spine has the `X-Access-Code` header but not which routes it guards, no quota, no statement of how the builder's demo rooms (photos of the builder's home, never in the repo) reach the Volume, and no way to tell a judge room from a demo room when purging.
- **Fix:** Add to AD-9 Rule: "Hosted mode guards `POST /builds` only with `X-Access-Code`; the hosted `JobStore` keeps a build counter and refuses the 21st with `build_quota_exceeded`; demo rooms are seeded onto the Volume by `scripts/seed_rooms.py` under `rooms/demo/`, judge rooms land under `rooms/judge/`, and `scripts/purge_judge_rooms.py` deletes only the latter." Add `BuildQuotaExceeded` to AD-13's error list and the two scripts to the seed.

### F8 (medium) — The Settings surface is incomplete and the Riddler fallback needs per-role providers

- **Location:** AD-14 Rule, AD-5 Rule, `src/config.py` (existing `Settings` reads `MODEL_PROVIDER`, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `CHAT_MODEL`, `IMAGE_MODEL`).
- **Problem:** AD-14's flag list reads as closed and omits provider selection, API keys, `base_url`, `OLLAMA_HOST`, `FAL_KEY`, and `ACCESS_CODE`. The spec's fallbacks are per role: the Riddler falls back to Muse Spark Open on Baseten by `base_url` swap while Architect, SAM, and dry run stay on the Meta API; the Trickster falls back to 8B Llama on Fireworks "last". AD-5 injects "ports", singular in effect, so an agent will wire one `ModelProvider` and the fallback becomes a global swap that also moves the vision call off Meta. `GUIDE` and `MODE` also both select the `HintPhraser` with no precedence stated.
- **Fix:** Amend AD-14 Rule: "flags are the product flags above plus adapter settings (`PROVIDER_<ROLE>` for `architect`, `riddler`, `dryrun`, `trickster`, `image` defaulting to `meta`; `META_MODEL_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, `FAL_KEY`, `OLLAMA_HOST`, `ACCESS_CODE`); `MODE=hosted` forces `GUIDE=verbatim`; the client reads `PROFILE` from the `?profile=` query, defaulting to `dev`, and `GET /meta` echoes it." Amend AD-5: "`wiring.py` resolves one `ModelProvider` per council role from `Settings`; the Riddler and Trickster fallbacks are a role's provider, never the global one."

### F9 (medium) — SAM fan-out, port concurrency, and ledger atomicity are unstated

- **Location:** AD-6 Rule, AD-7 Rule, `providers/base.py` (existing port is synchronous).
- **Problem:** `budgets.md`: "SAM 3.1 segment, 1 per listed object, at most 12, in parallel, 10 s total". Twelve serial calls at 1 to 3 s each miss the 120 s target on their own. The spine never says the segment stage fans out, whether ports are sync or async (which decides the shape of every adapter and the mock), or that `SpendLedger.guard` plus `Cache.get_or_call` are safe when twelve calls race on the counter and the cache directory.
- **Fix:** Add to AD-7 Rule: "`segment` issues one `segment` call per label concurrently (bounded to 12); ports are synchronous and stages fan out through a thread pool so the mock stays trivial." Add to AD-6 Rule: "`guard` reserves the estimate atomically under a lock and settles from returned usage; a retried call (AD-13) is one ledger entry."

### F10 (medium) — Cache storage is mode-dependent but has no port; AD-9 omits it

- **Location:** AD-9 Rule (mode-selected list), Structural Seed (`providers/cache.py`), AD-1.
- **Problem:** `stack.md`: "Cache | Mac disk or Modal Volume". AD-9's list has `JobStore`, `ArtifactStore`, `HintPhraser`, and ledger persistence but not the cache. `providers/cache.py` sits in `src/providers`, which under AD-1 may import only ports and the domain, so it cannot open the Volume itself without importing `src/infra` (forbidden) or branching on `MODE` outside `src/infra` (forbidden by AD-9).
- **Fix:** Make `Cache` a port in `pipeline/ports.py` (or reuse `ArtifactStore` with a `cache/` prefix), add it to AD-9's mode-selected list, and move the key logic to `providers/cache.py` over that port. Update the hosted flowchart node "Volume artifacts, cache" to say the Volume backs both via the same adapter.

### F11 (medium) — Cut 1 and AD-15 describe the Trickster reject differently

- **Location:** AD-15 "Prevents: a faked reject"; `delivery-plan.md` cut 1: "pre-authored edits plus a scripted reject ... the reject is not evaluated live".
- **Problem:** The spine's own mechanism (a recorded proposals artifact with the validator unchanged) makes a live reject nearly free, since the validator is code. If the cut-1 story reads the cut table literally it will build a second, faked-reject path that AD-15 forbids. The README disclosure also differs: cut 1 means no live Spark proposal at all; `DEMO_TRICKSTER=scripted` means recorded proposals for the video only.
- **Fix:** Add to AD-15 Rule: "Cut 1 is realized through the same scripted source with pre-authored proposals and no live Spark path; the validator still runs on every card. `GET /meta` distinguishes `trickster: live | scripted | cut1` so the README and the video disclosure read the right line." Add a Deferred line noting the cut table's "not evaluated live" is superseded.

### F12 (medium) — Cut 2 (profile as a JSON file) contradicts AD-8 as written

- **Location:** AD-8 Rule: "the server never persists `derived` or profile data".
- **Problem:** CAP-13 success allows "a local JSON file under cut 2" and `stack.md` names it the profile fallback. A browser cannot write a file on disk; under cut 2 the only writer is the local-mode server. AD-8's absolute wording forbids that, so the cut-2 story either violates the AD or re-reads "JSON file" as `localStorage`, which is a spec change.
- **Fix:** Amend AD-8 Rule: "... the hosted server never persists `derived` or profile data. Under cut 2 only, the local-mode server exposes `GET|PUT /profile/<name>` writing `rooms/profiles/<name>.json` (git-ignored) on the player's machine; the route is absent in hosted mode, so the privacy line holds in both." Add the route to the CAP-6 row.

### F13 (medium) — The persuasion attack, free text, and visible rung triggers have no rule

- **Location:** AD-4 Rule (event list), CAP-3 and CAP-4 rows.
- **Problem:** CAP-3 success: a typed "just tell me the answer" yields nothing above the current rung; CAP-12: "speech only requests the next rung"; CAP-4: "each rung change shows its triggering events". AD-4's event list (`click`, `lock_input`, `idle_tick`, `hint_request`, `trickster_card`) says nothing about what happens to player text, so an agent may forward it to the `HintPhraser` prompt as a "question" (no solution leak, but a prompt-injection surface and a departure from the fixed-prefix, under-400-token contract) or to Spark. Nothing says what `hint_request` returns before the first rung unlocks, and nothing exposes which events caused a rung change, which cut 5 and the video both need.
- **Fix:** Add to AD-4 Rule: "Player text, typed or transcribed, is reduced client-side to a `hint_request` event and never travels as text; a `hint_request` returns the current rung, or a fixed no-hint line when no rung is open; session state carries `rung_changes[] {puzzle, rung, at, triggered_by: [event ids]}` so the UI shows triggers." Add a convention row for the session routes (`POST /sessions`, `GET /sessions/<id>`, `POST /sessions/<id>/events`, `POST /sessions/<id>/trickster`) so api and web owners share one surface.

### F14 (medium) — The git-ignore list is incomplete and the local upload location is unnamed

- **Location:** Structural Seed last line: "`rooms/`, `.cache/` git-ignored"; CAP-13 row.
- **Problem:** CAP-13 success lists `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, and the cache. The spine names two of six. The disk `ArtifactStore` path is also unnamed, so a local upload could land somewhere that is not ignored; the submission rule "raw room photos never enter the public repo, consent or not" has no test.
- **Fix:** Change the seed line to the full list and add to AD-8 Rule: "the local `ArtifactStore` writes under `rooms/` only; a test asserts that `.gitignore` contains `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/`."

### F15 (low) — Portraits should be committed assets, not runtime calls; clue cards have no slot

- **Location:** CAP-7 row ("`providers/meta_api.py` `generate_image`, cache").
- **Problem:** CAP-7: "generated once (Thu Oct 29), never per build". A runtime `generate_image` behind the cache regenerates on every fresh cache (each Volume, each `CACHE=off` take) and the cache key in AD-6 is defined over image bytes, which a text-to-image call lacks. Clue cards ("when time allows", up to 12 per room) are per-room content with no pipeline stage and no Deferred entry.
- **Fix:** CAP-7 row: "`scripts/portraits.py` calls `generate_image` once; outputs are committed under `web/public/portraits/`; play never calls `generate_image`." AD-6: "for text-only calls the key omits the image hash." Deferred: "clue cards as an optional post-`scene` stage, Tier 1.5."

### F16 (low) — Box fallback hotspots and the boxes-only Architect fallback

- **Location:** AD-11 Rule ("polygon hotspots").
- **Problem:** `stack.md` fallbacks: "Spark boxes as hotspots" when SAM masks are unusable; `schema-v1.md`: `mask` is null on the box fallback. The hotspot contract does not say how a null mask renders.
- **Fix:** Add to AD-11 Rule: "a hotspot is the mask polygon, or the box as a four-point polygon when `mask` is null; the client never branches on which."

### F17 (low) — `HintPhraser` contract and Ollama failure path

- **Location:** AD-5 Rule.
- **Problem:** CAP-4 success: about 40 tokens in 5 s or less from a prompt under 400 tokens with a fixed prefix (the fixed prefix is what makes `OLLAMA_KEEP_ALIVE=-1` pay). Nothing says what happens when Ollama is down or slow during the playtest or the finals.
- **Fix:** Add to AD-5 Rule: "`HintPhraser.phrase(rung_text, derived)` uses a fixed prefix, stays under 400 tokens, and times out at 5 s, after which the verbatim adapter answers and the event log records `phraser_fallback`."

### F18 (low) — Idle is computed by the server, not posted by the client

- **Location:** AD-4 Rule (`idle_tick` as a client event).
- **Problem:** "Server-authoritative" sits awkwardly beside a client-posted `idle_tick`; the nudge threshold and `DEMO_TIMESCALE` live on the server clock (AD-10), so idle seconds should derive from the last event timestamp there.
- **Fix:** Reword: "`idle_tick` is a heartbeat; idle seconds are computed in `apply` from the session clock and the last non-tick event."

### F19 (low) — Ingest format rules, HEIC, and where the downscale happens

- **Location:** Conventions "Time and formats"; AD-7 `ingest`.
- **Problem:** `stack.md` places the 1280 px downscale in the browser (Canvas) with originals kept; `*.heic` in the ignore list implies phone originals. Chrome's Canvas cannot decode HEIC and the spine's Pillow 13 has no HEIF plugin, so a HEIC upload fails inside the capture timer.
- **Fix:** Add to AD-7 Rule: "the client uploads the original plus its 1280 px JPEG; `ingest` accepts JPEG and PNG only and rejects HEIC with `UnsupportedImage`; the README says to export JPEG." Add the error to AD-13.

### F20 (low) — Spend operations: Nov 5 reset, fal seed, refused mid-session call

- **Location:** AD-6 Rule, AD-13 Rule.
- **Problem:** `budgets.md`: the counter resets Thu Nov 5 and the cap becomes 25; fal calls are guarded at $0.02; a refused Trickster call mid-session must be "surfaced" but AD-13's envelope is for requests, and a session should not break on it.
- **Fix:** Add to AD-6: "`scripts/ledger.py reset|export` is the only way to reset; seed estimates per kind come from `budgets.md` plus `reconstruct3d` $0.02." Add to AD-15 or AD-4: "a `SpendCapExceeded` during a Trickster window closes the window and renders a `skipped` card."

### F21 (low) — Cuts 4 and 7 should be single constants

- **Location:** AD-12 ("unless cut 4"), AD-13 ("at most 2").
- **Problem:** Cuts are nightly decisions; each should be one line, not a code deletion, and AD-14's closed flag list has no `DRY_RUN`.
- **Fix:** Add `DRY_RUN=on|off` and `REGEN_MAX` (default 2) to AD-14's list; AD-12 and AD-13 reference them.

### F22 (low) — Scope label, companions, and Capability map gaps

- **Location:** Frontmatter `scope`, `companions`; Capability map rows.
- **Problem:** The spine calls CAP-10 Tier 1; `delivery-plan.md` puts it in Tier 1.5. `glossary.md` is a spec companion but not a spine companion. Row gaps: CAP-2 lacks `pipeline/regenerate.py`; CAP-5 lacks AD-4, AD-6; CAP-9 lacks AD-9 (ledger persistence per mode), AD-13; CAP-13 lacks AD-3, AD-5 (the Guide-only-on-the-Mac guarantee is a privacy rule) and the Meta standard-tier-only constraint (`budgets.md`: contributor tier never, because Meta may train on the data).
- **Fix:** Scope: "Tier 1 (CAP-1 to CAP-9) and Tier 1.5 (CAP-10)". Add `glossary.md` to companions. Fill the rows as listed. Add to AD-5: "the `meta` adapter uses the standard tier only."

### F23 (low) — AD-16 extends the frozen schema

- **Location:** AD-16 Rule ("spend per stage" in `provenance`).
- **Problem:** `schema-v1.md` lists `provenance` as model ids, prompt hashes, stage timings, regeneration count. The spine adds spend per stage. Schema v1 freezes Mon Oct 26 and later changes go through `bmad-correct-course`.
- **Fix:** Note in AD-16 that the field is added in the Thu Oct 22 schema review, before the freeze.

## Checklist coverage

| Spec item | Spine | Status |
| --- | --- | --- |
| CAP-1 counts, formats, 120 s, box fallback, <5 survivors | AD-7, AD-10, AD-11 | F2, F16, F19 |
| CAP-2 validator, dry run, regen 2, re-capture | AD-12, AD-13 | F1, F21 |
| CAP-3 play, lock opens only on correct input, persuasion attack | AD-4, AD-11 | F13 |
| CAP-4 rungs in code, Mac-only phraser, triggers visible, 5 s | AD-5, AD-8, AD-10 | F13, F17, F18 |
| CAP-5 menu, re-validate, cards, 1 per 3 min, 6 calls, no profile | AD-4, AD-12, AD-15 | F4, F5, F11, F20 |
| CAP-6 profile in browser, greeting, thresholds | AD-8 | F6, F12 |
| CAP-7 portraits once, cached | AD-6 | F15 |
| CAP-8 timescale, scripted Trickster, disclosure | AD-10, AD-15 | landed |
| CAP-9 cap, cache, persisted counter | AD-6, AD-16 | F9, F10, F20 |
| CAP-10 150 s, 20 builds, verbatim, Nov 10 purge, demo rooms | AD-7, AD-9 | F3, F7 |
| CAP-11, CAP-12 seams | AD-5, AD-11, Deferred | landed |
| CAP-13 IndexedDB, derived only, ignore list, retention text | AD-8, AD-14 | F5, F14 |
| Flags `PROFILE`, `CACHE`, `SPEND_CAP_USD`, `DEMO_TIMESCALE`, `DEMO_TRICKSTER`, `MIN_CONTAINERS` | AD-14 | F8 |
| Per-role fallbacks (Baseten Riddler, Fireworks Trickster) | AD-5 | F8 |
| Cuts 1 to 8 | AD-8, AD-12, AD-13, AD-15 | F11, F12, F21 |
| Gates, videos, submission hygiene | not architecture | n/a |
