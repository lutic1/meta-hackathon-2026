---
review: rubric
target: ../ARCHITECTURE-SPINE.md
checklist: ../../../../../.claude/skills/bmad-architecture/references/reviewer-gate.md
template: ../../../../../.claude/skills/bmad-architecture/assets/spine-template.md
author: Luis Ticas
date: 2026-10-21
verdict: revise
---

# Rubric review: ARCHITECTURE-SPINE.md against the good-spine checklist

## Verdict

**Revise before epics and stories are cut.** The mechanical half is clean: `lint_spine.py` reports zero findings, no template comment or placeholder survives, every `AD` has Binds, Prevents and Rule, and all four diagrams parse as mermaid (flowchart, flowchart, stateDiagram, erDiagram). The paradigm, the seventeen ADs, the conventions and the package layout fix most of what seven package owners would otherwise decide differently. The semantic half fails on three counts: one AD (AD-12) contains rules that cannot both hold and a function declared pure that must call a model; the seams between the packages that parallel agents will own (the HTTP route surface, event payloads, job statuses, port signatures, where sessions and the pipeline run in hosted mode) are left to whoever gets there first; and two operational dimensions (secrets; retention and deletion beyond one clause) are silent rather than decided, deferred or asked. Everything below is fixable as amended AD text, convention rows and Deferred entries; no paradigm change, no new package.

Inputs: the spine (all sections), the checklist and template, `SPEC.md` and its companions (`stack.md`, `budgets.md`, `player-profile.md`, `delivery-plan.md`, `glossary.md`), `schema-v1.md`, the scaffold (`src/providers/base.py`, `src/providers/mock.py`, `src/config.py`, `.gitignore`, `pyproject.toml`), the lint output, and a mermaid parse of each block. The two reconcile reviews in this folder were read after this pass was drafted; where a finding overlaps one of theirs the cross-reference is given so the fixes land once.

## Checklist scorecard

| Checklist item | Result | Findings |
| --- | --- | --- |
| Fixes the real divergence points for the level below and misses none | Partial: packages, ports by name, data shape, clocks and the write gate are fixed; the cross-package seams (routes, event payloads, job statuses, port sync/async, session store, hosted runner) are not | R-1, R-2, R-3, R-4, R-6, R-10, R-12 |
| Every AD Rule is enforceable and prevents its stated divergence | Fails on AD-12 (self-contradictory, non-pure function declared pure), AD-3 (test clause cannot pass), AD-6 (cache key undefined for text-only calls, no concurrency rule), AD-1 (no enforcing test named), AD-14 (ADOPTED but does not match the adopted `Settings`) | R-1, R-5, R-7, R-9, R-14 |
| Nothing under Deferred could let two units diverge | Mostly holds; "authentication beyond the access code" defers the wrong thing, since the access code's own scope is undecided; clue cards and the hosted purge are neither decided nor deferred | R-11, R-21 |
| Named tech verified-current | Holds per the memlog (PyPI, npm, GitHub checks dated Oct 21); two rows are not pinned | R-22 |
| Ratifies rather than contradicts a brownfield codebase | Mostly; AD-14 and AD-5 silently replace the scaffold's `Settings` keys and `chat` signature instead of ratifying or renaming them; the seed understates the `.gitignore` the repo already has | R-14, R-23 |
| Covers the driving spec's capabilities | All thirteen have a row; CAP-1, CAP-5, CAP-6, CAP-7, CAP-10 each have a success clause with no rule behind it | R-4, R-8, R-13, R-15, R-11 |
| No inherited parent spine | n/a | |
| Every dimension the altitude owns is decided, deferred or asked | Deployment topology and provider strategy are decided; the hosted execution model, client delivery, secrets, operations scripts, and retention beyond one clause are silent | R-2, R-3, R-6, R-16, R-17 |
| No template comment or placeholder | Holds (lint: 0 findings; manual check: no `<!--`, no `{...}`) | |
| Diagrams are valid mermaid | Holds (all four parse); two carry content errors | R-24, R-25 |

## Findings

Severity: critical / high / medium / low. Each names where it sits and the concrete change.

### R-1 (critical) — AD-12 cannot be built as written

- **Location:** AD-12 Rule; AD-7 Rule; Structural Seed (`council/dryrun.py`).
- **Problem:** Three rules collide inside one AD. (a) "`dry_run(room_view)` is a pure function" contradicts `stack.md` and `schema-v1.md` §Dry run, where the dry run is a `muse-spark-1.3` call; and judging its answers needs `solution`, which `RoomView` has dropped under AD-3, so the function has neither the I/O nor the data it needs. (b) "a Room is written to `ArtifactStore` only after `validate` passes" contradicts AD-7 "persist job state plus stage artifacts after each stage", because the `author` stage's artifact is an unvalidated Room. (c) "a `TricksterEdit` produces a new Room version" has no `version` field in Schema v1 to reference, is false for `loosen` (which changes `current_rung`, a field AD-4 reserves to `SessionStateMachine.apply`), and writes a per-session change to a store keyed by room, which breaks hosted demo rooms shared by several judges. The council, pipeline and domain owners each resolve these differently. Overlaps reconcile-spec F1 and reconcile-schema H-2, H-3, M-4.
- **Fix:** Rewrite AD-12 Rule: "`validate(room)` and `check_dry_run(room, answers)` in `src/domain/validator.py` are pure; `council/dryrun.py` builds the dry-run prompt over `RoomView`; the pipeline `dryrun` stage makes the call through the injected `ModelProvider` (reasoning low) and is the only place answers meet solutions, via `check_dry_run`. The `author` stage persists a `RoomDraft` artifact; the job's `room` artifact, the only key the play routes read, is written once `validate` and (unless `DRY_RUN=off`) the dry run pass. The build's Room is immutable. `apply_edit(room, edit) -> Room` in `src/domain/edits.py` is pure; a proposal is accepted only if `validate(apply_edit(room, edit))` passes rules 1 to 8; the edit is appended to the session log as a `trickster_card` event with `accepted`, and the session's effective Room is `apply_edit` folded over accepted edits at replay; `loosen` is applied by `SessionStateMachine.apply` to `current_rung`, not to the Room. Edits never reach `ArtifactStore`." Add `RoomDraft`, `edits.py` to the seed; change the ERD edge to `SESSION ||--o{ TRICKSTER_EDIT : proposes`.

### R-2 (high) — The hosted execution model is undecided: where the pipeline and the sessions run on Modal

- **Location:** AD-7 Rule ("no request blocks on a stage"); AD-9 Rule (mode-selected list); AD-4 (session log with no store); Structural Seed (`api/modal_app.py`, `infra/modal.py`); hosted flowchart.
- **Problem:** CAP-10 success rests on a build outliving the 150 s web timeout. The spine says what the request does not do, not what runs the stages. On Modal a background task inside the `@modal.asgi_app` container dies with the container (`MIN_CONTAINERS=0` until Nov 5, `@modal.concurrent(max_inputs=20)`), and the spec's intent is a separate spawned function. The same gap exists for sessions: AD-4 defines an append-only event log but names no store for it; an in-process dict diverges the moment Modal runs two containers, and a judge mid-room loses the room. AD-9's list (`JobStore`, `ArtifactStore`, `HintPhraser`, ledger persistence) has no runner and no session store, so the api owner and the infra owner will each decide. Overlaps reconcile-spec F3 (runner only).
- **Fix:** Add two ports to `pipeline/ports.py` and to AD-9's mode-selected list: "`JobRunner.start(job_id)`: local, an in-process task; hosted, `modal.Function.spawn` of the stage runner as a separate function, so the web container never owns a build; every stage rereads job state from `JobStore` on entry, so a restarted runner resumes at the last persisted stage. `SessionStore` (append, read-all): local, a JSON file under `rooms/sessions/`; hosted, `modal.Dict`, so every container replays the same log." Add both to the seed (`infra/local.py`, `infra/modal.py`) and a `SESSION` node to the hosted flowchart.

### R-3 (high) — The HTTP route surface, event payloads and job statuses are the main seam between `api`, `web` and `domain`, and none is fixed

- **Location:** AD-4 Rule (event names only); AD-7 Rule (`POST /builds`, `GET /builds/<job id>`); AD-13 (envelope only); Conventions.
- **Problem:** The spine names four routes (`POST /builds`, `GET /builds/<id>`, `GET /schema`, `GET /meta`) and no session route, no event payloads, no job status set. With one owner per package (AD-17), the web owner and the api owner will each invent the session routes, the lock-input shapes for `code`, `order`, `use_on` and `find`, what counts as a wrong attempt, and the terminal states a poll can return (`recapture` in the state diagram has no status name). `current_rung` is also a scalar while rungs are per puzzle and several puzzles may be open. Overlaps reconcile-spec F2, F13 and reconcile-schema M-2, M-3, M-5.
- **Fix:** Add a convention row "HTTP surface": `POST /builds`, `GET /builds/<job_id>`, `GET /builds/<job_id>/room` (PlayView), `POST /sessions {room_id, derived}`, `GET /sessions/<id>`, `POST /sessions/<id>/events`, `POST /sessions/<id>/trickster`, `GET /schema`, `GET /meta`; and "Job status": `queued`, `running` (with `stage`), `done`, `failed`, `needs_more_photos`, `needs_recapture`. Amend AD-4 Rule: "client-posted events: `click {interactable_id}`, `lock_input {puzzle_id, code}` or `{item, target}`, `hint_request {puzzle_id}`; server-appended: `idle_tick` from the session `Clock`, `trickster_card`; every event is stamped by the server clock on append and client timestamps are ignored; `find` is a `click` on the target, `order` is judged on each `click` against the trailing sequence and a wrong attempt is recorded when the sequence reaches the solution's length and differs; `current_rung` is `dict[puzzle_id, 0..3]`; state carries `rung_changes[] {puzzle, rung, at, triggered_by}` so the UI shows triggers." Add the route list to AD-9 ("identical in both modes") so it is the thing that must stay identical.

### R-4 (high) — The browser receives solutions

- **Location:** AD-2 Rule ("the same JSON travels the HTTP API, the job artifacts, and the client"); AD-3 (guards Spark and Ollama only); AD-4 (guards lock state, not lock answers).
- **Problem:** Nothing strips `solution` from what the play routes return, so a judge with devtools reads every code and the CAP-3 pitch (a game master that cannot be talked into winning) fails trivially. `RoomView` is not the answer because it also drops `evidence`, which the player must see. Overlaps reconcile-schema H-4.
- **Fix:** Amend AD-3 Rule: "`redact.py` exposes two views of one Room: `to_prompt_view(room) -> RoomView` and `to_play_view(room) -> PlayView`; play routes return only `PlayView`, which drops `solution` and `provenance`; the full Room leaves the server only through the build-artifact download. The generated `web/types` contain `PlayView`, never `Room`; an API fixture test asserts no `solution` key in any play response." Amend AD-2 to "the same JSON shapes travel ..." with `PlayView` as the client shape.

### R-5 (high) — AD-3's enforcing test cannot pass, and the validator's own reasons can leak the token it protects

- **Location:** AD-3 Rule, last clause ("the test suite runs validator rule 5 over every rendered prompt fixture"); AD-12 ("the rejected card references ...").
- **Problem:** Rule 5's solution tokens for `find` and `order` are interactable labels, and the dry-run prompt must carry every label (schema §Dry run), so rule 5 over prompts fails on every room with a `find` or `order` puzzle; the test is either never green or gets weakened. Separately, a natural rule 5 reason ("near_answer of pz_3 contains '345'") is shown on the rejected card and fed back to the Riddler on regeneration, so the same string reaches a player and a model. Overlaps reconcile-schema H-1, H-5.
- **Fix:** Replace the clause: "a fixture test renders every council prompt from a Room whose solutions are sentinel values and asserts none appears (the `code` string, the `order` id list in sequence, the `use_on` pair as a pair, the `find` target id); a second test asserts the `HintPhraser` input is exactly `(rung_text, derived)`." Add: "validator and dry-run reasons are structured `{rule, puzzle_id, field}` plus a fixed message per rule and never quote an offending token or answer; the regeneration prompt carries the reason list only, never the previous draft."

### R-6 (high) — Cache and ledger persistence have no port, so AD-1, AD-6 and AD-9 cannot all hold

- **Location:** AD-6 Rule; AD-9 Rule; AD-1 Rule; Structural Seed (`providers/cache.py`, `providers/spend.py`, `domain/ledger.py`).
- **Problem:** `stack.md` puts the cache on Mac disk or the Modal Volume. `providers/cache.py` sits in `src/providers`, which under AD-1 may import only ports and the domain, so it cannot open the Volume without importing `src/infra` (forbidden) or branching on `MODE` outside `src/infra` (forbidden by AD-9). AD-9's mode-selected list omits the cache. The ledger counter "persists through `JobStore`" per AD-6, which makes a build-job store the home of a global counter; and the counter logic is split between `domain/ledger.py` and `providers/spend.py` with no line saying what lives where, so two owners may both write it. Twelve concurrent SAM calls (`budgets.md`: in parallel, 10 s total) race on the counter and the cache directory with no atomicity rule. Overlaps reconcile-spec F9, F10.
- **Fix:** Make `Cache` and `LedgerStore` ports in `pipeline/ports.py`, add both to AD-9's list, and state the split: "`domain/ledger.py` is the pure arithmetic (estimate, settle, would-exceed); `providers/spend.py` is `SpendLedger`, which reserves the estimate atomically under a lock through `LedgerStore` and settles from returned usage; a retried call (AD-13) is one entry; `providers/cache.py` is the key logic over the `Cache` port." Amend the key: "for calls without an image (Riddler, Trickster, `generate_image`) the key omits the image hash." Update the hosted flowchart node to say the Volume backs both through the same adapter.

### R-7 (high) — The "fewer than 5 survivors" exit and photo-count bounds are missing from the pipeline

- **Location:** AD-7 Rule (stage list); AD-13 Rule (error set); build state diagram.
- **Problem:** CAP-1 success and `schema-v1.md` §SAM mask selection: fewer than 5 survivors asks for more photos before any authoring; the Constraints bound photos at 6 to 10. The stage list has no exit between `segment` and `author`, the error set has no class for it, and the diagram has no edge; three owners (pipeline, api, web) need the same outcome and the spine gives none. Overlaps reconcile-spec F2, reconcile-schema L-4.
- **Fix:** Add to AD-7 Rule: "`ingest` rejects fewer than 6 or more than 10 photos; `segment` ends the job with status `needs_more_photos` when fewer than 5 interactables survive mask selection, and no authoring call is made; mask selection (IoU, plural grouping, the 1% and 12 caps) is `domain/masks.py`, pure, called by the `segment` stage." Add `TooFewInteractables` to AD-13; add `segment --> needs_more_photos: survivors < 5` to the state diagram.

### R-8 (medium) — Per-session Trickster bounds and the profile fence around Spark prompts are unowned

- **Location:** AD-4 Rule; AD-3 Rule; AD-8 Rule; CAP-5 and CAP-6 rows.
- **Problem:** `player-profile.md` §Trickster bounds: one change per 3-minute window, only between puzzles, at most 6 Spark calls per session, from a game-state summary and never the profile. AD-4 names `trickster_window` as state but no count cap and no between-puzzles condition; `SpendLedger` guards dollars, not counts. AD-8 puts `derived` on the session start payload and nothing stops `council/trickster.py` or the dry-run prompt from including it, which would falsify the privacy line. The per-type payload constraints (decoy never on the exit puzzle, the rung and edge exist) are outside rules 1 to 8 and no module is named to refuse them. Overlaps reconcile-spec F4, F5 and reconcile-schema M-7.
- **Fix:** Add to AD-4 Rule: "`SessionStateMachine` opens `trickster_window` only when a lock has just opened and the previous window closed at least 3 minutes ago on the session clock; it counts proposal calls and refuses the seventh; `validate_edit(room, state, edit)` in `domain/edits.py` checks the per-type payload constraints and the window before `apply_edit`, and a failure is a rejected card with its own reason code." Add to AD-3 Rule: "`derived` is consumed only by `domain/rungs.py` and the `HintPhraser` port; `RoomView` and the Trickster game-state summary carry no profile field, and the sentinel test asserts no `derived` key in any rendered Spark prompt." Add AD-3, AD-4, AD-6 to the CAP-5 row and AD-3 to the CAP-6 and CAP-13 rows.

### R-9 (medium) — Port signatures are the seam every adapter and the mock depend on, and they are not fixed

- **Location:** AD-5 Rule; AD-17 Rule ("a story ... first declares the port change it needs"); scaffold `src/providers/base.py` (synchronous `chat(messages, model, temperature, max_tokens)`).
- **Problem:** AD-5 lists method names (`chat`, `segment`, `reconstruct3d`, `generate_image`, `transcribe`) and no signatures, no sync/async choice, and no statement of how the scaffold's `chat` is extended; `stack.md` says the Meta API rejects `max_output_tokens`, so the scaffold's `max_tokens` parameter is dead. Whether ports are sync or async decides the shape of five adapters, the mock, the stage runner's fan-out and every test; left open, the providers owner and the pipeline owner choose differently and AD-17's "declare the port change first" has nothing to declare against. The Riddler and Trickster fallbacks are per role (Baseten, Fireworks) while the Architect, SAM and dry run stay on Meta, but AD-5 injects "ports" as if one `ModelProvider` served every role, so a fallback becomes a global swap. Overlaps reconcile-spec F8, F9.
- **Fix:** Add to AD-5 Rule: "ports are synchronous; the stage runner fans out through a bounded thread pool (`segment`: one call per label, at most 12 concurrent) so the mock stays trivial. `chat(messages, *, images=[], response_schema=None, reasoning_effort='low', model=None) -> ChatResponse` extends the scaffold's signature and drops `max_tokens` and `temperature`; `segment(label, image) -> list[Polygon] | None`; `reconstruct3d(image, mask) -> GlbRef`; `generate_image(prompt) -> ImageResponse`; `transcribe(wav) -> str`. `wiring.py` resolves one `ModelProvider` per council role (`architect`, `riddler`, `dryrun`, `trickster`, `image`) from `Settings`; a fallback is a role's provider, never the global one. The `meta` adapter uses the standard tier only."

### R-10 (medium) — The greeting and the `HintPhraser` contract have no home or failure path

- **Location:** AD-5 Rule; CAP-6 row ("`web/profile`, session start payload"); CAP-4 row.
- **Problem:** CAP-6: the room-2 greeting cites the room-1 profile and names no object or solution; `player-profile.md`: phrased from the derived block only. No component produces it and no model phrases it; routed to Spark it leaks `derived` (R-8). CAP-4: about 40 tokens in 5 s or less from a fixed-prefix prompt under 400 tokens; nothing says what happens when Ollama is down during the playtest or the finals. Overlaps reconcile-spec F6, F17.
- **Fix:** Add to AD-5 Rule: "`HintPhraser.phrase(rung_text, derived) -> str` and `HintPhraser.greet(derived) -> str` use a fixed prefix, stay under 400 tokens, and time out at 5 s, after which the verbatim adapter answers (the rung text; a template filled with the numbers) and the event log records `phraser_fallback`; neither receives room content." Add `council/greeting.py` (template over `derived`, no `RoomView`) to the seed and the CAP-6 row.

### R-11 (medium) — Hosted access-code scope, build quota, demo-room seeding and the Nov 10 purge are silent; Deferred defers the wrong thing

- **Location:** AD-9 Rule; Conventions "Config and auth"; Deferred ("Authentication beyond the access code"); CAP-10 row.
- **Problem:** CAP-10 success: at most 20 own-room builds; judges play cached demo rooms; judge-uploaded rooms are deleted Tue Nov 10. The spine has the `X-Access-Code` header but not which routes it guards, no quota, no way the builder's demo rooms (photos of the builder's home, never in the repo) reach the Volume, and no way to tell a judge room from a demo room when purging. Deferred pushes "authentication beyond the access code" down, which is right, but the access code's own scope is not decided, so it is silent rather than deferred. Overlaps reconcile-spec F7.
- **Fix:** Add to AD-9 Rule: "hosted mode guards `POST /builds` only with `X-Access-Code`; the hosted `JobStore` keeps a build counter and refuses the 21st with `build_quota_exceeded`; demo rooms are seeded onto the Volume by `scripts/seed_rooms.py` under `rooms/demo/`, judge rooms land under `rooms/judge/`, and `scripts/purge_judge_rooms.py` deletes only the latter." Add `BuildQuotaExceeded` to AD-13 and `scripts/` to the seed.

### R-12 (medium) — Who serves the client to the judge, and how the client reaches the API, is undecided

- **Location:** Hosted flowchart ("Judge browser → `@modal.asgi_app` FastAPI"); local flowchart ("Chrome: web/ → FastAPI in-process"); AD-9; Structural Seed (`web/`).
- **Problem:** Nothing says whether FastAPI mounts the built `web/dist` as static files (one origin, no CORS) or the client is hosted elsewhere and calls the API cross-origin; locally the Vite dev server (port 5173) and FastAPI (port 8000) are two origins, so either a Vite proxy or CORS middleware is needed, and the web owner and the api owner will pick differently. The client's base URL and the `PROFILE` mechanism are also unstated: AD-14 lists "client-side `PROFILE`" but a browser cannot read an environment variable, and the video needs `dev|playtest|demo` switchable at runtime, so a build-time `VITE_` constant is wrong.
- **Fix:** Add to AD-9 Rule: "FastAPI mounts `web/dist` at `/` in both modes, so the client and the API share one origin and no CORS is configured; in development the Vite server proxies `/api/*` to FastAPI; API routes live under `/api/`." Amend AD-14: "the client reads `PROFILE` from the `?profile=` query parameter, defaulting to `dev`, and `GET /meta` echoes it."

### R-13 (medium) — Cut 1 and cut 2 contradict AD-15 and AD-8 as written

- **Location:** AD-15 ("Prevents: a faked reject"); AD-8 Rule ("the server never persists `derived` or profile data"); `delivery-plan.md` cuts 1 and 2.
- **Problem:** Cut 1 ("pre-authored edits plus a scripted reject; the reject is not evaluated live") read literally builds the faked-reject path AD-15 forbids, when the spine's own mechanism makes a live reject nearly free. Cut 2 ("profile as a JSON file") has no writer but the local-mode server, which AD-8's absolute wording forbids. Both cuts are nightly decisions, and a story cut that night needs to know which rule wins. Overlaps reconcile-spec F11, F12, F21.
- **Fix:** Add to AD-15 Rule: "cut 1 is realized through the same scripted source with pre-authored proposals and no live Spark path; the validator still runs on every card; `GET /meta` reports `trickster: live | scripted | cut1`." Amend AD-8 Rule: "the hosted server never persists `derived` or profile data; under cut 2 only, the local-mode server exposes `GET|PUT /api/profile/<name>` writing `rooms/profiles/<name>.json` on the player's machine, and the route is absent in hosted mode." Add `DRY_RUN=on|off` and `REGEN_MAX` (default 2) to AD-14 so cuts 4 and 7 are one line each.

### R-14 (medium) — AD-14 is tagged [ADOPTED] but does not ratify the adopted `Settings`

- **Location:** AD-14 Rule (flag list); scaffold `src/config.py` (`MODEL_PROVIDER`, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `CHAT_MODEL`, `IMAGE_MODEL`); AD-5.
- **Problem:** The flag list reads as closed and names none of the keys the existing `Settings` already reads, nor the ones the new adapters need (`FAL_KEY`, `OLLAMA_HOST`, an OpenAI-compatible base URL, `ACCESS_CODE`). `GUIDE` and `MODE` both select the `HintPhraser` with no precedence. The providers owner and the api owner will disagree on key names on the first day. Overlaps reconcile-spec F8.
- **Fix:** Amend AD-14 Rule: "flags are the product flags listed plus adapter settings: the scaffold's `MODEL_PROVIDER` becomes the default for `PROVIDER_<ROLE>` (`architect`, `riddler`, `dryrun`, `trickster`, `image`); `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY`, `FAL_KEY`, `OLLAMA_HOST`, `ACCESS_CODE`, `DRY_RUN`, `REGEN_MAX`; `CHAT_MODEL` and `IMAGE_MODEL` are retired in favour of per-role model ids in `Settings`. `MODE=hosted` forces `GUIDE=verbatim`."

### R-15 (medium) — Portraits are a committed asset, not a runtime call; clue cards have no slot

- **Location:** CAP-7 row ("`providers/meta_api.py` `generate_image`, cache"); AD-6 key.
- **Problem:** CAP-7: generated once (Thu Oct 29), never per build. A runtime `generate_image` behind the cache regenerates on every fresh cache (each Volume, every `CACHE=off` take). Clue cards ("when time allows", up to 12 per room) are per-room content with no stage and no Deferred entry. Overlaps reconcile-spec F15.
- **Fix:** CAP-7 row: "`scripts/portraits.py` calls `generate_image` once; outputs are committed under `web/public/portraits/`; play never calls `generate_image`." Deferred: "clue cards as an optional post-`scene` stage, Tier 1.5, same `generate_image` port."

### R-16 (medium) — Secrets are a silent dimension

- **Location:** AD-14 ("environment only"); Structural Seed; hosted flowchart; Conventions "Config and auth".
- **Problem:** Nothing says where API keys and the access code live locally (the scaffold ignores `.env` and `config.py` loads it, which the spine does not ratify), how they reach Modal (`modal.Secret`), or that `.env.example` is the committed shape. For a repo that goes public Nov 4 with a perpetual licence to the organisers, "keys never in the repo" needs the same standing as "photos never in the repo". The checklist treats a whole silent dimension as a finding.
- **Fix:** Add to AD-14 Rule: "secrets are environment variables: locally from `.env` (git-ignored; `.env.example` is committed with every key blank), hosted from one `modal.Secret` named `keyframe` attached to the app and the runner function; `Settings` is the only reader; a test asserts `.env` is ignored and `.env.example` lists every key `Settings` reads."

### R-17 (medium) — Retention and deletion are decided for the profile and silent for everything else

- **Location:** AD-8 Rule (last clause); CAP-13 row ("`GET /meta` retention text"); ERD note ("`SESSION` and `EVENT` are server-side and transient").
- **Problem:** "Transient" is not a retention decision. Nothing says when a session log is deleted (on `done`, after N hours, at purge), how long judge originals (kept at full resolution for Tier 2) sit on the Volume, whether the hosted cache keeps judge photo bytes past the room's deletion, or what the local `rooms/` and `.cache/` lifetime is. The Nov 10 purge is a CAP-10 success criterion with no mechanism (R-11). The retention summary shown on the capture screen has no source of truth, so the api owner and the web owner will each write one.
- **Fix:** Add to AD-8 Rule: "hosted session logs are deleted 24 h after their last event or when their room is deleted, whichever is first; judge rooms, their originals, their sessions and their cache entries are deleted together by `scripts/purge_judge_rooms.py` (Tue Nov 10); demo rooms persist; local `rooms/` and `.cache/` are never deleted by the app. The retention text served by `GET /meta` is one string in `src/api/meta.py` that quotes the Meta and fal retention summaries from the pre-Oct 26 verification."

### R-18 (medium) — AD-1 names no enforcing check, and `Clock` has two homes

- **Location:** AD-1 Rule; AD-17 Rule; Structural Seed (`domain/clock.py`; `pipeline/ports.py (JobStore, ArtifactStore, Clock)`); dependency diagram.
- **Problem:** AD-1 is the paradigm's load-bearing rule and the only one with no test named; a rule enforced by review alone drifts under seven parallel owners. The seed puts a `Clock` in `src/domain` (AD-1: no clock reads) and a `Clock` port in `pipeline/ports.py`, so the domain owner and the pipeline owner will each define one. The dependency diagram also draws `src/domain` twice (`SESSION` and `DOMAIN` nodes), which hides that `api` and `pipeline` depend on the same package.
- **Fix:** Add to AD-1 Rule: "`tests/test_boundaries.py` walks every module's imports and fails on a violation; it runs in the offline suite (AD-17)." Decide one home: "`Clock` is a `Protocol` in `src/domain/clock.py` (an interface, not a reader); the two implementations (session clock with `DEMO_TIMESCALE`, build clock) live in `src/infra/clocks.py`; `pipeline/ports.py` re-exports it." Merge the two `src/domain` nodes in the diagram and add `PROV --> DOMAIN` and `INFRA --> DOMAIN`.

### R-19 (medium) — Hotspot geometry, null masks and plural instances are undefined across the client seam

- **Location:** AD-11 Rule; Conventions "Time and formats" ("masks as polygons in image pixel space"); schema `box` (0 to 1000 grid), `mask` (one polygon, null on fallback), `instances`.
- **Problem:** `box` is normalised and `mask` is in pixels of an unnamed image; on the box fallback (`stack.md`) the client must build a hotspot from a differently scaled shape; a grouped plural has several SAM masks and one `mask` field. The segment owner and the web owner will each pick a coordinate space. Overlaps reconcile-spec F16, reconcile-schema M-6.
- **Fix:** Convention row "Hotspot geometry": "pixel coordinates of the downscaled 1280 px image; `mask` is a list of polygons (one per instance) and the hotspot is their union; when SAM yields nothing the `segment` stage writes the `box` rectangle scaled to the same space as the single polygon, so the client never reads `box`." Carry `mask: polygon[] | null` to the Oct 22 schema review.

### R-20 (medium) — Id generation crosses the model boundary

- **Location:** Conventions "Ids" ("prefixed ULIDs: `room_`, `job_`, `sess_`, `pz_`, `ix_`, `te_`"); AD-2; AD-5.
- **Problem:** `ix_` ids are assigned by the `segment` stage and `te_` by the pipeline, which is fine, but `pz_` ids appear first in the Riddler's JSON output, and a model does not emit ULIDs. The council owner will either put an id field in the response schema (and get free-text ids) or leave it out (and the pipeline assigns), and the schema's `requires[]` and `use_on` references depend on which.
- **Fix:** Add to the Ids row: "ids are assigned only by server code; the Riddler's response schema uses ordinal keys (`p1`..`p6`) for puzzles and their `requires` references, and the pipeline `author` stage maps them to `pz_` ULIDs before `validate`; interactable references in model output use the `ix_` ids given in the prompt view."

### R-21 (low) — Deferred and Capability-map gaps

- **Location:** Deferred; Capability map rows; frontmatter.
- **Problem:** The scope label calls CAP-10 Tier 1 while `delivery-plan.md` puts it in Tier 1.5; `glossary.md` is a spec companion but not a spine companion; CAP-2 lacks `pipeline/regenerate.py`; CAP-9 lacks AD-9 and AD-13; CAP-13 lacks AD-5 (the Guide-only-on-the-Mac guarantee is a privacy rule) and the standard-tier-only constraint; the cut table's "reject not evaluated live" is superseded by AD-15 but nothing says so.
- **Fix:** Scope: "Tier 1 (CAP-1 to CAP-9) and Tier 1.5 (CAP-10)". Add `glossary.md` to companions. Fill the rows. Deferred: "cut 1's 'not evaluated live' wording in `delivery-plan.md` is superseded by AD-15."

### R-22 (low) — Two Stack rows are not pinned

- **Location:** Stack ("python-dotenv 1.x", "Node 24 LTS").
- **Problem:** The template asks for name and version; "1.x" and "LTS" are ranges. The lint accepts them, two agents' lockfiles will not agree.
- **Fix:** Pin both to the versions the lockfile and `.nvmrc` will carry (the memlog records Node 24.22.0; take python-dotenv from `uv lock`).

### R-23 (low) — Brownfield facts the seed should ratify instead of restating

- **Location:** Structural Seed last line ("`rooms/`, `.cache/` git-ignored"); AD-8.
- **Problem:** The repo's `.gitignore` already ignores `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `*.HEIC`, `.cache/`, `cache/`, which is the full CAP-13 list; the seed names two of them, and no test guards the list. The local `ArtifactStore` path is unnamed, so an upload could land outside it.
- **Fix:** Seed line: "`rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/` git-ignored (existing)". Add to AD-8: "the local `ArtifactStore` writes under `rooms/` only; a test asserts the ignore list."

### R-24 (low) — State diagram and ERD carry content errors

- **Location:** Build `stateDiagram`; `erDiagram`.
- **Problem:** The state diagram has no exit after `segment` (R-7) and `recapture` is a state with no job status. The ERD hangs `TRICKSTER_EDIT` off `ROOM` (R-1), omits `JOB ||--o| ROOM` and `ROOM ||--|{ PHOTO`, and shows `PROFILE ||--|| DERIVED` which is a computed block, not an entity.
- **Fix:** Add `segment --> needs_more_photos: survivors < 5`; rename `recapture` to `needs_recapture`; apply the ERD edges from R-1 and add `JOB ||--o| ROOM : produces`, `ROOM ||--|{ PHOTO : from`; keep `DERIVED` only if annotated as the client-computed block.

### R-25 (low) — Ingest format rules and HEIC

- **Location:** AD-7 `ingest`; Conventions "Time and formats".
- **Problem:** `stack.md` places the 1280 px downscale in the browser with originals kept; `*.heic` in the ignore list implies phone originals; Chrome's Canvas cannot decode HEIC and Pillow 13 has no HEIF plugin, so a HEIC upload fails inside the capture timer. Overlaps reconcile-spec F19.
- **Fix:** Add to AD-7: "the client uploads the original plus its 1280 px JPEG; `ingest` accepts JPEG and PNG only and rejects HEIC with `UnsupportedImage`; the README says to export JPEG." Add the error to AD-13.

### R-26 (low) — Test location wording is ambiguous

- **Location:** Conventions "Code style" ("tests next to the package they cover under `tests/`").
- **Problem:** "Next to the package" and "under `tests/`" describe two layouts; the seed shows the second.
- **Fix:** "tests under `tests/<package>/`, mirroring `src/`; `web/` tests under `web/tests/`."

## What holds

- Paradigm named and mapped to directories; the dependency direction is a rule and a diagram.
- Schema v1 realised once, types generated and staleness-tested (AD-2); snake_case end to end.
- Server-authoritative, replayable session; the state machine as the only lock writer (AD-4).
- `HintPhraser` as a port no cloud adapter may implement (AD-5) is the right shape for the Mac-only Guide and survives cut 3 through `GUIDE=verbatim`.
- Guard-then-cache order, `CACHE=off` never bypassing the ledger, spend log derived from the ledger (AD-6, AD-16).
- Two clocks with `DEMO_TIMESCALE` fenced off the capture timer (AD-10).
- One scene graph for Tiers 1 to 3, hotspot id equals interactable id (AD-11).
- Typed errors, one regeneration loop, adapter retry only on 429 and 5xx (AD-13).
- Demo mode swaps the source, never the check; `GET /meta` carries the disclosure (AD-15).
- One owner per package and offline tests per story (AD-17) is the right contract for parallel agents; it only lacks the seam definitions above to be sufficient.
- Deployment topology for both modes is drawn; `MIN_CONTAINERS` and the Modal Dict and Volume are decided; the Deferred list is honest about what Tier 2, Tier 3 and voice leave open.

## Suggested order

R-1, R-4, R-5 are spine text edits with no schema change and unblock the council, domain and api stories. R-2, R-3, R-6, R-9 define the seams and should land before any story is assigned. R-7, R-8, R-10 to R-20 are amended AD text and convention rows. R-1 (`Room.version`, decoy field), R-19 (`mask: polygon[]`) and R-20 (ordinal keys in the Riddler schema) carry to the Thu Oct 22 schema review before the Mon Oct 26 freeze.
