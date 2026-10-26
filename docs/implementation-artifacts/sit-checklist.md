---
title: 'Keyframe lean SIT checklist'
status: final
author: Luis Ticas
created: '2026-10-21'
updated: '2026-10-26'
sources:
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md
  - docs/planning-artifacts/epics.md
  - docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
  - docs/specs/spec-keyframe/budgets.md
  - docs/specs/spec-keyframe/delivery-plan.md
  - docs/specs/spec-keyframe/stack.md
  - docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md
---

# Keyframe lean SIT checklist

## Purpose and rules

SIT here is one checklist of live-seam cases (AR-25, Story 2.9). It makes real Paid cloud calls and real Ollama calls across the adapter, pipeline and hosted seams, and it records each live response as a fixture under `tests/fixtures` for the offline suite. Luis runs it from the M1 with `scripts/sit.py`, after `scripts/doctor.py` passes, at the end of each build day from Tue Oct 27, with a full pass on Sat Oct 31. Every live call goes through the real Cache and `SpendLedger`, so a run stays within the Spend cap ($80 through Wed Nov 4, which `SPEND_CAP_USD` allocates per mode: local $60 and hosted $20; $25 from Thu Nov 5: local $5 and hosted $20) and the day's ceiling in `budgets.md`. The daily export prints the local total, the hosted total and their sum against the combined ceiling, and is committed from Mon Oct 26. SIT never runs in CI: CI is one job, `scripts/check.sh`, offline only. Each day's result and each dated builder item go into `docs/implementation-artifacts/sprint-status.yaml`. There is no separate SIT sign-off; a green Sat Oct 31 full pass is a precondition on the UAT sheet. Privacy: input photos come only from the git-ignored `photos/` folder (no faces, documents or others' belongings), never from `tests/`. A fixture holds the response only, with no request body, no image bytes and no `data:` URL, and the offline `pytest` scan fails on `data:image` or JPEG magic bytes under `tests/fixtures`. Raw room photos are never committed, and `git ls-files rooms/ photos/` prints nothing.

## Cases

Cases are modules under `tests/sit/`. `scripts/sit.py` discovers them, and the offline `pytest` run never collects them (`collect_ignore` in `tests/conftest.py`). Each case sets its own cache flag in its module, so `CACHE` in `.env` does not apply to a SIT run. Live-call cases run with `CACHE=off`, which skips the Cache but never the ledger (AD-6), so every run calls the vendor and is priced. The exceptions: SIT-06 runs with `CACHE=on`, and SIT-04 runs with `CACHE=on` so `muse-image-1.0` is billed only once. Daily cost with `CACHE=off` is about $0.45 at most, inside the $5 lowest ceiling. Costs come from `budgets.md` rates and seeds.

| Id | Seam | Story adding the module | What the case does | Pass criteria | Approx. cost | Fixture recorded | First run |
|---|---|---|---|---|---|---|---|
| SIT-01 | Meta chat, Architect (`muse-spark-1.3`) | 2.9 | Makes one Chat Completions call through `build_architect_prompt` with the first 2 photos of `photos/` (downscaled to 1280 px by `sit.py`) as data URLs, `response_format` `json_schema` with `ArchitectResponse` and `strict: false`, and `reasoning_effort` low. Module `tests/sit/test_02_architect.py`. | 200; the response parses into `ArchitectResponse`; one ledger entry, settled from returned usage; latency recorded against the 15 s Architect budget (an overrun is logged, never a fail, NFR-1) | vision $0.025 (seed $0.03) | `muse-spark-1.3/chat-architect-two-photos` | Tue Oct 27 |
| SIT-02 | `sam-3.1` segment, `meta-sam-parser` | 2.9 | Sends one known-present label and one absent label on a real 1280 px JPEG via Responses, `store: false`. The present label is the surest candidate of the SIT-01 recording, on its photo; the absent label is fixed. Module `tests/sit/test_03_segment.py`. | The present label's SVG path (M/L/Z) decodes with `meta-sam-parser` 0.1.0 into `[[x, y], ...]` in the frame pixels of the stored 1280 px JPEG, inside its box; the absent label returns `None` | $0.0025 per call (2 calls, $0.005; the 12-call parallel latency check is a builder item run by hand on the first run) | `sam-3.1/segment-present-label` and `sam-3.1/segment-absent-label` (Responses bodies; the adapter does not stream) | Tue Oct 27 |
| SIT-03 | Full live Build, local | 2.24 | Uploads a 6 to 10 JPEG Photo set through `POST /builds` with `CACHE=off`, then polls `GET /builds/<job_id>` to a terminal status (UJ-1 to T1). Module `tests/sit/test_09_full_build.py`. | Ends `done`; the Room passed the Validator within the configured `REGEN_MAX` (2, or 1 under cut 7), and the Dry run unless cut 4 is taken; stage timings recorded against Architect 15 s, segmentation 10 s, Riddler 45 s, Dry run 30 s and Scene 10 s, with the total against the 110 s budget; a total over the Capture target (120 s, or p50 plus 25% if 2.26 re-bases it) is logged as an NFR-1 miss | about $0.10 clean, $0.15 with one Regeneration, under $0.25 with two | Stage responses and the job record: `muse-spark-1.3/chat-full-build-architect`, `chat-full-build-riddler` and `chat-full-build-dry-run` (each role's last reply; no Dry run reply under cut 4) and `tests/fixtures/jobs/full-build.json`, replayed offline through the wired stages by `tests/pipeline/test_full_build_replay.py`; the run note carries the job record's build time, Dry run count, Regenerations and budget overruns | Wed Oct 28 |
| SIT-04 | `muse-image-1.0` | 2.9 | Makes one `POST /v1/images/generations` call with `n: 1` on a fixed clue-card prompt. Module `tests/sit/test_04_image.py`. | First run: an `ImageResponse` (`b64_json` webp), one ledger entry settled at $0.01. Later runs: served from the Cache, no entry, $0 | $0.01 | `muse-image-1.0/image-sit-clue-card` | Tue Oct 27 |
| SIT-05 | Ollama Guide, `HintPhraser` | 3.7 | Calls `phrase(rung_text, derived)` on `llama3.2:3b` (Q4_K_M, keep-alive -1) at `OLLAMA_HOST`, then repeats it with Ollama unreachable. | Phrased line in 5 s or less, about 40 tokens out, `prompt_eval_count` under 400 (NFR-2, SM-9); unreachable: the verbatim Rung at once, reported as not phrased, `phraser_fallback` logged with cause `unreachable` | $0 | Ollama response | Sat Oct 31 |
| SIT-06 | Cache hit | 2.9 | Makes one cheap text-only chat call twice with `CACHE=on`; the prompt carries the date, so each day's first call is billed and the second call must be served from the Cache. Module `tests/sit/test_01_cache_hit.py`, so it sorts first. | The second call is served from the Cache before the ledger guard; the caller is told it was cached; no ledger entry; running total unchanged ($0) | one text-only chat call (first call only); the repeat $0 | `muse-spark-1.3/chat-sit-ok` (the billed first call); totals before and after go in the run log | Tue Oct 27 |
| SIT-07 | Spend cap refusal | 2.9 | Builds a second `SpendLedger` over the real `LedgerStore` whose cap is the current running local total, for this case only (the run's own ledger keeps the `SPEND_CAP_USD` allocation: $60 through Wed Nov 4, $5 from Thu Nov 5), then guards one `CACHE=off` chat call behind it. Module `tests/sit/test_00_cap_refusal.py`, so it sorts first. | `SpendCapExceeded` carrying that cap and the running local total; the provider is never called (no request leaves the transport); no entry appended | $0 | none | Tue Oct 27 |
| SIT-08 | Hosted spawned Build, Volume | 7.7, 7.8, 7.11 (no story names the module yet) | Posts two different never-built Photo sets back to back with `X-Access-Code` on the `modal serve -e dev` URL, so the second waits `queued` behind `max_containers=1` and runs uncached, finishing more than 150 s after its POST (UJ-5 step 6). | `POST /builds` returns the `job_` id at once; `call:<job_id>` is stored; polls answer 202 `queued`, or `running` with `stage`, never an error or timeout; the runner reads the photos committed before the spawn (`Volume.commit()`, then `Volume.reload()`); the final poll answers 200 `done` and `GET /rooms/<room_id>` serves the PlayView; `volume.reload()` latency recorded | two clean Builds, about $0.10 each | Job records from the poll | After 7.8 and 7.11 merge (Tier 1.5), before Thu Nov 5 |
| SIT-09 | Hosted Cron ledger snapshot | 7.8, 7.9 (manual) | Runs `modal deploy -m src.api.modal_app`, then the dashboard's "run now" on `ledger_export`, then `scripts/ledger.py export`. | `spend/hosted-<date>.jsonl` is written to the Volume and committed, with a total equal to the hosted `LedgerStore` sum; the committed `spend/exports/ledger-<date>.json` merges it with each `call_` entry once; under `modal serve -e dev` neither Cron fires | $0 | Hosted snapshot (7.9 reads it offline) | After 7.9 merges (Tier 1.5), before the Thu Nov 5 reset |
| SIT-10 | Local and hosted parity | 7.23 (Hosted parity check in the browser; depends on 7.3, 1.19, 3.4) | Plays the same fixture Room with the same event sequence in the browser, in Local mode (`GUIDE=verbatim`) and on the deployed URL, with `DEMO_TRICKSTER=scripted` (before 4.3 lands the flag only affects `GET /meta` and the Disclosure; the Oct 29 run opens Rungs by Wrong attempts and no Trickster window). | Same `GET /rooms/<room_id>` PlayView and same session state, with every Rung shown as written in both; hosted `GET /api/meta` answers `mode: hosted`, `guide: verbatim`, `guide_model: null` with the hosted Retention text; the hosted opening line is the welcome, never a Greeting; `POST /api/builds` without the code is refused. A live link submitted Wed Nov 4 needs a pass against the deployed commit | $0 | PlayView and `GET /meta` responses from both modes | Thu Oct 29 (the Tue Oct 27 item is the 7.3 infrastructure smoke only) |
| SIT-11 | Baseten fallback (`openai_compatible`) | 2.9 | Makes one Riddler call to the host `OPENAI_COMPATIBLE_BASE_URL` names (Baseten, or Fireworks with its model id) through `build_author_prompt` over the synthetic fixture Room (`tests/fixtures/rooms.py`; no photo is sent), in `json_schema` mode: the strict schema of the Riddler's `p1`..`p6` response model as `response_format` with `strict: true`, `reasoning_effort` medium and `max_tokens` sent. Plain-JSON mode is the adapter's `json_mode="plain"`, switched in the module if the Tue Oct 27 test chooses it. Module `tests/sit/test_05_fallback_chat.py`. | The chosen mode yields one reply that parses into the Riddler's response model (`validate` runs on a Room, so it waits for the author stage that maps `p1`..`p6` to `pz_` ids); the plain-JSON parse-failure propagation is an offline test in story 2.8, never a SIT pass; the chosen mode and the Baseten price from its dashboard are dated in the sprint status and in the Tue Oct 27 builder item | priced from returned usage at the Spark rates (`budgets.md` has no Baseten rate; the dashboard price is dated in the Tue Oct 27 builder item) | `muse-spark-open/chat-riddler-author` (the folder is the model id's last segment) | Tue Oct 27 |
| SIT-12 | fal SAM 3D (Tier 2 only) | 8.1 (builder task, run by hand; no module; fixtures come with the post-gate fal adapter story) | Sends 10 demo-room objects through `fal-ai/sam-3/3d-objects` on original-resolution photos (short side at least 512 px), with `X-Fal-Store-IO: 0`; runs only if backup video v1 existed Sat Oct 31 night, and only if the Tier 1 Scenes are textured planes in the Three.js scene graph (the NFR-10 DOM-only fallback was not taken). | Each GLB opens in Three.js; no Clue, Rung, solution or Derived field is sent; each call is guarded as `reconstruct3d` (seed $0.02); total fal cash, including the pre-Oct 26 five objects, stays within $6; results recorded for the Mon Nov 2 gate (7 of 10, 30 fps, raycast) | $0.02 per call | none (measurements and Ledger export only, 8.1) | Sun Nov 1, only if attempted |

### Later-story cases

These cases arrive with their stories. `scripts/sit.py` picks each one up with no change.

| Id | Seam | Story | What the case does | Pass criteria | Approx. cost | Fixture recorded | First run |
|---|---|---|---|---|---|---|---|
| SIT-13 | Riddler, live | 2.20 | Makes one `chat` call through the `riddler` role at medium over the 2.19 prompt, with `attempt` set to the Regeneration count, over the synthetic fixture Room's Interactables (`tests/fixtures/rooms.py`; no photo is sent). Module `tests/sit/test_07_riddler.py`. | Parses to a `RoomDraft`; `p1`..`p6` map to `pz_` ULIDs; `ix_` references match exactly; `validate` verdicts recorded; latency against the 45 s budget; the output is not cut short at the `max_completion_tokens` setting | Riddler $0.022 (seed $0.03) | `muse-spark-1.3/chat-riddler-author`, replayed offline by `tests/pipeline/test_author_stage.py` | Wed Oct 28 |
| SIT-14 | Dry run, live | 2.24 | Makes one `chat` call through the `dryrun` role, `reasoning_effort='low'`, on a draft that passed `validate`: the synthetic fixture Room's scenes, labels, Clues and Rungs (`tests/fixtures/rooms.py`; no room photo is sent), judged by the dryrun stage. Module `tests/sit/test_08_dry_run.py`. | `check_dry_run` reaches every answer; job state holds pass or fail per Puzzle and "reached n of m answers", never the answers; latency against the 30 s budget | dry run $0.024 (seed $0.03) | `muse-spark-1.3/chat-dry-run`, replayed offline by `tests/pipeline/test_dryrun_stage.py` | Wed Oct 28 |
| SIT-15 | Trickster, live | 4.8 (cut 1 drops it) | Makes one `muse-spark-1.3` call at low with `strict_schema` allowing only `decoy`, `merge`, `loosen` and `shortcut`, in an open window. | Ids are parsed by exact match; the live Validator cards the proposal | Trickster seed $0.01 | Trickster response | Sat Oct 31 |
| SIT-16 | Voice (unscheduled) | 9.1 | Makes one live `muse-voice-transcribe-1.0` call on a short 16-bit mono WAV. Runs only if voice is attempted. | Transcript returned; result dated | $0.18 per audio hour | Transcribe response | Only if attempted |

Gaps for `bmad-correct-course`: no story's acceptance criteria add the `tests/sit/` module for SIT-08, so until one does, SIT-08 and SIT-09 run by hand. Story 7.23 adds the SIT-10 module (first run Thu Oct 29). SIT-12 is a builder task under 8.1 and is always run by hand.

## Live-only items confirmed on the first live call

| Skill | Item to confirm | Case |
|---|---|---|
| keyframe-muse | The live API accepts the pydantic schema with `strict: false`, including `discriminator` on unions; real image token counts; `reasoning_tokens` at low (the starting value for tuning `max_completion_tokens`) | SIT-01 |
| keyframe-muse | Riddler at medium: latency against 45 s, 504 risk, whether 16384 `max_completion_tokens` is enough | SIT-13 |
| keyframe-muse | Image call returns `b64_json` webp; $0.01 billed | SIT-04 |
| keyframe-muse | Baseten accepts `strict_schema(RoomDraft)` with `strict: true` and `reasoning_effort: medium`; whether it enforces Meta's strict subset; the Baseten price read from its dashboard | SIT-11 |
| keyframe-sam31 | Auth, request shape, event names, `store: false`, latency against the 10 s read timeout | SIT-02 |
| keyframe-sam31 | The zero-match stream closes an empty lane with `response.content_part.done` before `response.completed` | SIT-02 |
| keyframe-sam31 | Each mask's H and W equal its box size; `w`/`h` equal 1280 by the photo height (the spine's "scaled to the frame" wording awaits this) | SIT-02 |
| keyframe-sam31 | 12 calls in parallel against the 10 s budget and the 10 s read timeout | SIT-02 (first run) |
| keyframe-sam3d-fal | A 4032x3024 data URI is accepted (no 413); an original-size mask works; `model_glb` for a single mask; metadata nesting; the privacy headers honored; latency against `client_timeout=300` | Pre-Oct 26 five-object spike; SIT-12 |
| keyframe-sam3d-fal | No copy of the data-URI input persists on the fal dashboard with `X-Fal-Store-IO: 0`; whether 4xx and cancelled requests are billed; the price unit | Pre-Oct 26 spike; SIT-12 |
| keyframe-sam3d-fal | GLB units, up axis and origin in `GLTFLoader` against `metadata`; the real `X-Fal-Needs-Retry` value and timeout behavior when they first occur | SIT-12 |
| keyframe-modal | `modal serve -e dev` builds the image and serves the `-dev` URL | SIT-08 (and the Tue Oct 27 pre-deploy) |
| keyframe-modal | First `POST /builds` and `GET /builds/<id>` on the dev URL: spawn returns at once, 202 while running, `call:<job_id>` key, the runner sees the committed photos; `volume.reload()` latency | SIT-08 |
| keyframe-modal | `Secret.from_name(..., required_keys=[...])` with a key missing fails at deploy | Tue Oct 27 pre-deploy (7.3) |
| keyframe-modal | Neither Cron fires under `serve`; `modal deploy` registers the Cron and "run now" on `ledger_export` writes the snapshot | SIT-09 |
| keyframe-modal | 20 concurrent `reserve_build` calls on the dev Dict: exactly one caller claims each slot | Dated builder item (7.10) |
| keyframe-modal | `purge_judge_rooms.py` on a dev judge room removes the room prefix, the cache keys in `cache-keys.json` and the sessions, and writes an ids-only record | Dated builder item (7.19), in a non-judging Environment, before Tue Nov 10 |
| keyframe-modal | `modal function autoscaler update keyframe/web --min-containers 1` applies without a redeploy | Dated builder item, Thu Nov 5 (7.22) |
| keyframe-sam3d-fal | The model runner can read an upload with `initial_acl` forbid | SIT-12, only if the upload fallback is used |
| keyframe-devops | `python3 scripts/doctor.py` on the M1: real Ollama, real RAM, arm64, model resident near 3 GB | Precondition of every run; SIT-05 |

## Dated builder items

| Date | Item | Record | Done (date, result) |
|---|---|---|---|
| Wed Oct 21 to Sun Oct 25 (SIT-0) | Pre-kickoff verifications: Meta key and a `sam-3.1` mask on an own photo, a mask decoded with `meta-sam-parser` to a Hotspot polygon in Chrome, three Riddler calls against the draft schema, five objects through `fal-ai/sam-3/3d-objects`, a hello-world `modal deploy`, the Ollama benchmark | Each dated in the sprint status; a failure moves API wiring from Mon Oct 26 to Tue Oct 27 | |
| Mon Oct 26 | Fireworks Trickster fallback model id confirmed (PRD §13 Q2; the 4.8 gate) | Id and date in the sprint status, later in the hand-recorded Fireworks fallback fixture | |
| Mon Oct 26 | First daily Ledger export (stories 2.3, 2.5 and 2.6 land Mon Oct 26, so SM-6 holds from day one) | `spend/exports/ledger-2026-10-26.json` committed; dated in the sprint status | |
| Tue Oct 27 | One-call Baseten test: `json_schema` support, the chosen mode (SIT-11) and the Baseten price read from its dashboard | Mode and price dated here and in the sprint status (the SIT-11 cost cell reads this row) | |
| Tue Oct 27 | First manual `modal deploy` (7.3) after `bash scripts/check.sh --predeploy`; infrastructure smoke only: the deploy, `GET /api/meta`, the refusals (`POST /api/builds` without the code), and a curl-started session answering the welcome | Deploy date, URL and smoke result | |
| Thu Oct 29 | First SIT-10 run (7.23) in the browser against the deployed URL | Run log row; result in the sprint status | |
| Tue Oct 27 to Wed Oct 28 | Capture measured (2.26): at least 5 live Builds, p50 per stage and end to end | p50s and the re-base decision, dated Wed Oct 28; SIT-03 uses the decided target | |
| When 3.7 lands (Sat Oct 31) | M1 Ollama benchmark: 400-token prompt, prefill and decode rates, end-to-end latency for about 40 tokens, resident memory near 3 GB | Dated here and in the sprint status; above 5 s is flagged as an NFR-2 miss | prefill tok/s, decode tok/s, ms for about 40 tokens, resident GB; over 5 s flagged as an NFR-2 miss |
| Sat Oct 31 | Live Trickster case run within the Spend cap (4.8). The Fireworks fallback fixture is recorded once by hand with `OPENAI_COMPATIBLE_BASE_URL` and `OPENAI_COMPATIBLE_API_KEY` set to Fireworks for that one call, storing the confirmed model id and its confirmation date (on or after 2026-10-26) | Dated | |
| Sat Oct 31 | Full pass, plus `check.sh --predeploy` and a `modal serve -e dev` smoke | Run log | |
| Before Thu Nov 5 | Quota claim atomicity (7.10) in a non-judging Modal Environment | Result in the sprint status; a failure goes through `bmad-correct-course` before 7.11 | |
| Thu Nov 5 | Autoscaler `--min-containers 1` override applied without a redeploy (7.22); only if the Official Rules allow changes to the hosted deployment after the deadline, otherwise not applicable | Result in the sprint status | |
| Before Tue Nov 10 | `purge_judge_rooms.py` on a dev judge room (7.19) in a non-judging Environment | Ids-only record; result in the sprint status | |
| Each build day from Mon Oct 26 | `spend/exports/ledger-<date>.json` in the day's commit, printing the local total, the hosted total and their sum against the combined ceiling | Run log column; dated in the sprint status | |

## How to run

```sh
python3 scripts/doctor.py                  # a FAIL stops the run (see below)
uv run scripts/sit.py                      # every case under tests/sit/; exits non-zero naming the failed cases
uv run scripts/ledger.py export            # then commit spend/exports/ledger-<date>.json with the day's work
```

`sit.py` prints one `PASS <case>: <seconds>, spend <delta> USD (<note>)` or `FAIL <case>: <error>` line per case, the failed case's traceback on stderr, and a summary with the running total; the run log takes the totals from the first and last lines.

Writing a case (a later story adds its file and nothing in `sit.py` changes): a module `tests/sit/test_<nn>_<name>.py` whose docstring starts with its `SIT-nn` id and whose `run(sit)` raises to fail (an `AssertionError` names the broken check) and returns a short note on a pass. `sit` carries `settings` (from `.env`), the real ledger (`sit.ledger`, `sit.store`, `sit.running_total_usd()`), the disk cache, `sit.photos(n)` (the first `n` JPEGs of the git-ignored `photos/`, downscaled to 1280 px), `sit.meta(kind, budget_s, cache=...)` and `sit.openai_compatible(...)` (adapters over the run's guarded path, each case choosing `cache=True` or `False`), `sit.record(name, model=...)` (the last live response as `tests/fixtures/providers/<model>/<name>.json`, refused when the call was served from the cache or holds a `data:` URL) and `sit.recorded(name, model=...)` (the body of a fixture an earlier case recorded). Fixtures are read back offline by `tests/providers/replay.py`.

- Story 2.9 defines no flags: `sit.py` runs every discovered case, in file-name order, and does not fail fast. Keys come from `.env` (`MODEL_API_KEY`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY`; `FAL_KEY` only for SIT-12). `.env` holds the Baseten values used by SIT-11. Hosted cases need the `modal serve -e dev` URL running. `photos/` holds at least two own JPEGs (`.jpg` or `.jpeg`; HEIC is not read).
- The daily export is committed from Mon Oct 26 (stories 2.3, 2.5 and 2.6 land that day); SIT cases run from Tue Oct 27. The export prints the local total, the hosted total and their sum against the combined ceiling ($80 through Wed Nov 4, $25 from Thu Nov 5); `SPEND_CAP_USD` allocates it per mode (local $60 and hosted $20, then local $5 and hosted $20).
- Any live link submitted Wed Nov 4 requires a SIT-10 pass against the deployed commit, recorded in the run log and the sprint status with the commit hash and URL.
- Items dated Thu Nov 5 to Mon Nov 9 (the 7.22 redeploy and its checks, the autoscaler override) run only if the Official Rules allow changes to the hosted deployment after the deadline, checked at kickoff Mon Oct 26; otherwise the Wed Nov 4 deployment is the final hosted state and they are recorded as not applicable, not failed.
- A doctor FAIL stops the run, except Ollama or guide-model lines once cut 3 is taken.
- A case whose feature is cut reports "cut <n>" instead of pass or fail, read from the Settings flag the cut sets: SIT-15 under cut 1 (`DEMO_TRICKSTER`), SIT-05 under cut 3 (`GUIDE=verbatim`), SIT-14 under cut 4 (`DRY_RUN=off`). That is a recorded cut, not a skipped case.
- Daily ceilings: Oct 26 $3 (no SIT case), Oct 27 $5, Oct 28 $10, Oct 29 $10, Oct 31 $5, Nov 1 $8, Nov 2 $10, Nov 3 $18, Nov 4 $10. Fri Oct 30 has no build and no run.
- On a failure: fix forward, re-run the failing case, and record the date, case, cause and action in the run log and the sprint status. Never weaken a check to turn a case green: no relaxed threshold, skipped case or hand-edited fixture, no weaker Validator or Dry run (SM-C1), no vaguer Rung (SM-C4). Re-record a fixture only from a live call. A stage over budget is logged and never fails the Build; only 2.26 re-bases the target, on Wed Oct 28.
- SIT-07 and SIT-06 run first. If either is red, stop, fix it, and re-run before trusting the day's spend. `sit.py` itself does not fail fast (story 2.9); if a fail-fast is wanted, it goes into story 2.9 through `bmad-correct-course` first.

If a seam stays red, this applies (`delivery-plan.md`, `stack.md`):

| Seam red | What applies |
|---|---|
| Meta API at the Mon Oct 26 check | API wiring moves to Tue Oct 27 and everything after slips a day |
| SAM masks (SIT-02) | The Architect's boxes become the Hotspots ("same call, boxes only, if SAM masks are unusable after 60 minutes") |
| Riddler on Meta (SIT-13) | Muse Spark Open on Baseten (`PROVIDER_RIDDLER=openai_compatible`); without `json_schema`, plain-JSON prompting with validator retry |
| Dry run (SIT-14) | Cut 4, `DRY_RUN=off` |
| Full Build over the Capture target (SIT-03) | Re-base to measured p50 plus 25% (2.26 window only); never by weakening a check |
| Ollama (SIT-05) | Cut 3, `GUIDE=verbatim`; the README drops the phrasing claim; the Privacy line stays verbatim: "the player profile stays on your machine." |
| Live Trickster (SIT-15) | Cut 1, `DEMO_TRICKSTER=authored`; 8B Llama on Fireworks is the last fallback |
| `muse-image-1.0` (SIT-04) | Placeholder art (FR-23) |
| Hosted (SIT-08 to SIT-10) | Tier 1 is untouched; if the Official Rules require a live link Wed Nov 4, the hosted URL as redeployed Thu Oct 29 serves Demo rooms only with Rungs verbatim, after a SIT-10 pass against the deployed commit; the finals fallback order holds (7.22) |
| fal (SIT-12) | The Tier 2 gate misses and Tier 1 ships |

## Run log

| Date | Cases run | Pass | Fail | Failing cases | Action | Ledger export committed |
|---|---|---|---|---|---|---|
| Mon Oct 26 (no SIT cases; the first daily export only) | none | | | | | |
| Tue Oct 27 (plus the 7.3 infrastructure smoke) | | | | | | |
| Wed Oct 28 | | | | | | |
| Thu Oct 29 (first SIT-10 run, 7.23) | | | | | | |
| Sat Oct 31 (full pass) | | | | | | |
| Sun Nov 1 | | | | | | |
| Mon Nov 2 | | | | | | |
| Tue Nov 3 | | | | | | |
| Wed Nov 4 (no daily SIT; hosted SIT-08 and SIT-09 if 7.8 has merged) | | | | | | |
