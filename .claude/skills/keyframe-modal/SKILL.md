---
name: keyframe-modal
description: Hosts Keyframe's judge URL on Modal 1.6.2. Covers the App and image; the FastAPI app under @app.function, @modal.concurrent(max_inputs=20) and @modal.asgi_app(); builds spawned to a timeout=900 runner and polled by a watchdog with FunctionCall.from_id(...).get(timeout=0); job state, build quota slots, sessions and ledger entries in the keyframe-jobs, keyframe-sessions and keyframe-ledger Dicts; artifacts and cache on the keyframe-data Volume (commit and reload); the daily ledger snapshot and hourly session sweep on modal.Cron; the keyframe Secret. Use when writing, testing or debugging src/api/modal_app.py, the hosted adapters in src/infra/modal.py and their tests, or the Volume and Dict access in scripts/seed_rooms.py, purge_judge_rooms.py or ledger.py export. Do not use for general Modal questions (use the modal skill), local-mode adapters in src/infra/local.py, provider wiring in src/api/wiring.py, model calls (keyframe-muse, keyframe-sam31, keyframe-sam3d-fal), or CI/CD.
when_to_use: Trigger phrases such as "judge URL", "modal_app.py", "asgi_app", "spawn the build", "build watchdog", "202 while running", "keyframe-jobs Dict", "keyframe-sessions sweep", "keyframe-data Volume", "volume busy", "build quota slot", "ledger snapshot cron", "purge judge rooms", "keyframe Secret".
paths:
  - "src/api/modal_app.py"
  - "src/infra/modal.py"
  - "tests/**/*modal*.py"
  - "scripts/seed_rooms.py"
  - "scripts/purge_judge_rooms.py"
  - "scripts/ledger.py"
---

# Modal hosting for the Keyframe judge URL

Facts here were checked against the official Modal pages and the installed `modal==1.6.2` SDK on 2026-10-21. For anything outside Keyframe's patterns, such as other decorators, GPUs, Sandboxes or the general CLI, use the official `modal` skill in `.claude/skills/modal`, which points at https://modal.com/llms.txt. Full code shapes are in [references/hosted-code.md](references/hosted-code.md). The deploy, secret and warm-container steps are in [references/runbook.md](references/runbook.md). The offline proof is [scripts/selfcheck.py](scripts/selfcheck.py).

## When to use

Use this skill for:
- `src/api/modal_app.py`: the hosted entry point. It holds the App, the image, the ASGI web function, the spawned stage runner and the two Cron functions (ledger export, session sweep). It sets `max_containers=1`.
- `src/infra/modal.py`: the hosted adapters behind `MODE=hosted` (AD-9). These are the Dict `JobStore`, the Volume `ArtifactStore` (which lists `rooms/demo/` only), the Volume `Cache`, the spawn `JobRunner`, the Dict `SessionStore` and the Dict `LedgerStore`.
- Tests of those adapters (`tests/**/*modal*.py`), and the scripts that reach the Volume or a Dict from the Mac: `seed_rooms.py`, `purge_judge_rooms.py` and `ledger.py export`.
- When a manual `modal serve`, `modal deploy` or the Nov 5 to Nov 9 warm container comes up while this skill is loaded, follow [references/runbook.md](references/runbook.md). The builder runs those steps. Never run `modal serve`, `modal deploy`, `modal secret create`, an autoscaler update, or a script that writes to a real Dict or Volume unless the user explicitly asks for it.

Do not use it for:
- General Modal knowledge: the `modal` skill covers that.
- Local mode: `src/infra/local.py` runs the same ports on disk and needs no Modal.
- Provider wiring in `src/api/wiring.py`. Its hosted branch only passes `hosted=handles()` to the adapters described here.
- Model calls, which go through `ModelProvider` and the keyframe-muse, keyframe-sam31 and keyframe-sam3d-fal skills.
- Automation. There is no CD: no push, merge or schedule runs `modal deploy`. The two hand-started paths are `.github/workflows/deploy.yml` and `.github/workflows/ops.yml`, both run from the Actions tab with the Modal token from the repository's Actions secrets: deploy takes the Environment and `MIN_CONTAINERS` as inputs and runs the same pre-deploy ladder and `modal deploy` as the runbook, then smoke-tests `/api/meta`; ops takes an action (`ledger-export`, which uploads `spend/exports/` as an artifact to download and commit, `purge-dry-run`, `purge` behind a `confirm` input, `warm`, `cool`, `autoscaler-settings`) and the Environment, and runs the runbook's SDK scripts and autoscaler commands without deploying.

## How Keyframe calls it

There is one hosted path. Nothing lives in process memory (AD-7), and no mode branch exists outside `src/infra` and the `src/api` wiring (AD-9).

```python
# src/api/modal_app.py (shape; full version in references/hosted-code.md)
app = modal.App("keyframe", image=image, secrets=[secret], volumes={"/data": volume})

@app.function(timeout=900)                                   # stage runner, one writer per job
def run_build(job_id: str) -> None: ...

@app.function(min_containers=settings.min_containers, max_containers=1)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():                                                   # no parameters; returns the FastAPI app
    from src.api.app import create_app
    from src.api.wiring import wire
    return create_app(wire(settings, hosted=handles()))

@app.function(schedule=modal.Cron("0 6 * * *", timezone="America/New_York"))
def ledger_export() -> None: ...                             # Dict entries -> /data/spend/hosted-<date>.jsonl

@app.function(schedule=modal.Cron("17 * * * *"))
def session_sweep() -> None: ...                             # AD-8: sessions 24 h after their last event
```

1. **Handles (AD-9, AD-14).** AD-9 names them: Dicts `keyframe-jobs`, `keyframe-sessions` and `keyframe-ledger`, Volume `keyframe-data` mounted at `/data`, Secret `keyframe`, and functions `web`, `run_build`, `ledger_export` and `session_sweep`. They are created once at module level and are all lazy. Nothing contacts Modal until first use.
   - `modal.Dict.from_name(..., create_if_missing=True)` for `keyframe-jobs`, `keyframe-sessions` and `keyframe-ledger`.
   - `modal.Volume.from_name("keyframe-data", create_if_missing=True)`, mounted at `/data`.
   - `modal.Secret.from_name("keyframe", required_keys=[...])`, attached at the App level. Secret keys become environment variables that `Settings` reads. `MODE=hosted` and `GUIDE=verbatim` are set on the image with `.env(...)`, because they are not secret.
2. **`POST /builds` (AD-7, AD-9).** After the access code check, `JobStore.reserve_build` claims one of 20 quota slot keys with `Dict.put(..., skip_if_exists=True)`; when all are taken it raises `BuildQuotaExceeded`. Ingest validates and stores both photo streams through `ArtifactStore.put`. Each write ends with `volume.commit()`. Then the route writes the `queued` job record to the Dict and calls `JobRunner.start(job_id)`:
   - That runs `run_build.spawn(job_id)`. Pass the id only, never photo bytes.
   - It stores `call.object_id` under its own key, `call:<job_id>` (AD-7). The runner owns the `job_id` key after the spawn, and the web function never writes it back.
   - If `start` raises, the route writes `failed` with stage `ingest` and answers with the error envelope.
   - The route returns at once. Spawning before the commit would let the runner `reload()` and find no photos.
3. **The runner** (`@app.function(timeout=900)`, AD-7) runs `ingest → … → scene`.
   - It rereads job state at each stage entry, stops if the status is already terminal, and writes the whole record back after each stage.
   - Artifacts go through the Volume adapter: write, then `commit()`.
   - On `scene` it writes the final job record beside the Room on the Volume.
   - It sets no `retries`, because AD-13 keeps one retry loop. 900 s covers the 260 s worst case in `budgets.md`.
4. **`GET /builds/<job_id>`** reads persisted state only: the Dict first, then the final record on the Volume.
   - While the status is `queued` or `running`, the watchdog classifies the runner with `FunctionCall.from_id(call_id).get(timeout=0)` and the route answers 202 with the job state (AD-7, HTTP conventions; `build_poll_status` in references/hosted-code.md).
   - A runner that timed out, crashed, expired or returned without a terminal status is marked `failed` and keeps its `stage`.
   - A terminal record answers 200. Local mode answers 202 and 200 the same way.
   - Classification, from `runner_state` in [references/hosted-code.md](references/hosted-code.md), which selfcheck.py loads from that file and runs against Modal's own poll code:
     - builtin `TimeoutError`: running.
     - `modal.exception.FunctionTimeoutError`: timed out.
     - `modal.exception.OutputExpiredError`: expired.
     - Modal client errors (`ConnectionError`, `InternalError`, `ResourceExhaustedError`, `ServiceError`, `AuthError`): unknown. The poll failed, so the job is left unchanged and the client polls again. Past `DEADLINE_S` (1,200 s: the 900 s runner timeout plus margin, AD-7) unknown counts as dead, because a runner that itself raised one of these classes reads the same way.
     - any other exception: crashed.
     - a returned value: finished.
   - A `queued` job with no `call:<job_id>` key after `ORPHAN_S` (60 s, AD-7) is orphaned (the spawn never happened) and is marked `failed`.
5. **Volume rules (AD-7, AD-9).** Every read starts with `volume.reload()` and every write ends with `volume.commit()`.
   - The web container serves up to 20 requests at once, but a `reload()` fails with "volume busy" while any file is open, and the Volume looks empty to that container during the reload. So all Volume I/O in one process goes through one lock, and each file is read fully and closed before the lock is released.
   - Serve photos as `Response(bytes)`, never `FileResponse` from `/data`.
   - `web/dist` ships on the image (`add_local_dir`), so `StaticFiles` never holds a Volume file open.
6. **Dict rules.** Store plain JSON dicts (`model_dump(mode="json")`).
   - Read the value, change it, and put the whole value back. A nested change that is never written back is lost.
   - Dict entries expire after 7 idle days, so durable records go to the Volume: final job records, Rooms, and the daily ledger snapshot.
   - Each session value carries `room_id` and `last_event_at`. The hourly `session_sweep` Cron deletes sessions 24 h after their last event (AD-8). A judge build's originals live under `rooms/judge/<room_id>/` beside the runner-written `cache-keys.json`, and `purge_judge_rooms.py` deletes the room, its originals, its sessions and the cache entries listed there together (AD-8). Dict expiry is not retention.
7. **Daily export (AD-9, `budgets.md`).** `ledger_export` writes every `keyframe-ledger` entry to `/data/spend/hosted-<date>.jsonl` and commits. Locally, `scripts/ledger.py export` reads that file with `volume.read_file` and merges it into `spend/exports/ledger-<date>.json`.
8. **Warm container.** The decorator reads `MIN_CONTAINERS` through `Settings` at deploy time; the default is 0. From Thu Nov 5 to Mon Nov 9, set it with `modal function autoscaler update keyframe/web --min-containers 1`, and keep `MIN_CONTAINERS=1` in the deploy shell, because every deploy resets overrides to the decorator value. See [references/runbook.md](references/runbook.md).
9. **Ports stay synchronous (AD-5).** Routes that touch a port are plain `def` routes, which FastAPI runs in its thread pool, so blocking Modal calls are fine there. Inside an `async def` route, use the `.aio` variants (`await run_build.spawn.aio(job_id)`) so the event loop never blocks.
10. **Tests (AD-17).** Tests never reach Modal. The adapters take a `ModalHandles` bundle, so tests pass plain dicts, a temporary directory and stub `commit()` and `reload()` methods.

## API constraints

| Constraint | Value | Source |
|---|---|---|
| Web request limit | 150 s for every web function type. After that Modal answers 303 to a result URL, which breaks CORS. Keyframe never holds a request that long: it spawns | https://modal.com/docs/guide/webhook-timeouts.md |
| Decorator stack | `@app.function` outermost, then `@modal.concurrent(max_inputs=...)`, then `@modal.asgi_app()` | https://modal.com/docs/guide/webhooks.md |
| Decorator errors | `asgi_app` above `app.function` raises `InvalidError` ("swap the order"); an `asgi_app` function with parameters raises `InvalidError` ("can't have parameters") | SDK 1.6.2 behaviour, asserted by scripts/selfcheck.py |
| `@modal.concurrent` | `max_inputs` is required (`TypeError` without it); `target_inputs` is optional. Sync handlers run on threads and must be thread-safe; async handlers share one event loop and must not block it | https://modal.com/docs/guide/concurrent-inputs.md |
| Function timeout | default 300 s, range 1 s to 24 h, counted per attempt. `FunctionTimeoutError` comes after retries run out. `startup_timeout` covers slow container starts | https://modal.com/docs/guide/timeouts.md |
| `Function.spawn` | returns a `FunctionCall` at once and takes no timeout of its own; the timeout is the runner's decorator value. Outside a running or deployed app it raises `ExecutionError` | https://modal.com/docs/guide/function-invocation-methods.md |
| Polling | `FunctionCall.from_id(id).get(timeout=0)` raises the builtin `TimeoutError` while running. Results are kept 7 days, then `OutputExpiredError`. Poll with 202, as in Modal's example | https://modal.com/docs/guide/job-queue.md |
| `modal.Dict` | `from_name(..., create_if_missing=True)`; values are cloudpickled, up to 100 MiB each (keep them under 5 MiB), 10,000 entries per update. Entries expire after 7 days with no reads or writes. Mutations need a put-back. Data survives redeploys | https://modal.com/docs/guide/dicts.md |
| `Dict.put(skip_if_exists=True)` | returns `False` and writes nothing when the key exists. Whether this is atomic under concurrent writers is not documented (live-only) | SDK 1.6.2 docstring, asserted by scripts/selfcheck.py |
| `Volume.batch_upload` | `force=False` by default, so uploading over an existing file fails; directories can never be overwritten | SDK 1.6.2 docstring, asserted by scripts/selfcheck.py |
| `modal.Volume` | `commit()` persists writes and makes them visible to other containers; background commits run every few seconds and at shutdown. `reload()` shows other containers' commits, fails with "volume busy" while files are open, and empties the view in that container while it runs. The last write wins on the same file. Run at most about 5 concurrent small commits. v1 has a hard cap of 500,000 inodes | https://modal.com/docs/guide/volumes.md |
| `modal.Cron` | `Cron("0 6 * * *", timezone="America/New_York")`. Deploying the App activates the schedule. That it never fires under `serve` or `run` is inferred, not stated (live-only). Schedules cannot be paused; remove the schedule and redeploy. The dashboard has "run now". `Period` resets on redeploy and `Cron` does not | https://modal.com/docs/guide/cron.md |
| Warm containers | `min_containers` keeps a floor of warm containers, billed while idle. `scaledown_window` defaults to 60 s (range 2 s to 20 min) | https://modal.com/docs/guide/cold-start.md |
| Default resources | with no `cpu` or `memory`, a container requests 0.125 core and 128 MiB; billing is the higher of the request and actual use | https://modal.com/docs/guide/resources.md |
| Autoscaler overrides | `Function.from_name(app, fn).autoscaler.update(min_containers=...)` or `modal function autoscaler update app/fn`. Overrides revert on the next deploy. `update_autoscaler()` is deprecated in 1.6.2 | https://modal.com/docs/guide/scale.md |
| Container cap | 4,000 concurrent containers per Function | https://modal.com/docs/guide/scale.md |
| Web limits | a new workspace is rate-limited to 200 requests per second (excess gets 429). Web request bodies can be up to 4 GiB | https://modal.com/docs/guide/webhooks.md |
| Secrets | attached with `secrets=[...]` and read as environment variables; later Secrets override earlier ones. Key names use letters, digits and `_` and cannot start with a digit; values are at most 32,768 characters | https://modal.com/docs/guide/secrets.md |
| `required_keys` | `Secret.from_name(..., required_keys=[...])`: the server asserts the keys exist on the Secret | SDK 1.6.2 docstring (`modal/secret.py`) |
| URLs | deployed: `https://<source>--<app>-<function>.modal.run`. `modal serve` adds `-dev` to the label. Labels longer than 63 characters are truncated with a hash | https://modal.com/docs/guide/webhook-urls.md |
| Environments | each Environment has its own Secrets, and Dict and Volume names resolve inside it; every workspace starts with one called "main". `modal serve -e dev` cannot touch judging data. Outside an app, `from_name` without `environment_name` resolves in the CLI's active Environment (`MODAL_ENVIRONMENT`, then the profile, then the workspace default) | https://modal.com/docs/guide/environments.md; `modal deploy --help` |
| 1.0 renames | `keep_warm` became `min_containers`, `concurrency_limit` became `max_containers`, `container_idle_timeout` became `scaledown_window`, `allow_concurrent_inputs` became `@modal.concurrent`, and `web_endpoint` became `fastapi_endpoint`: in 1.6.2 these five raise `DeprecationError`. `.lookup` (now `.from_name`) and `Mount` (now `Image.add_local_*`) are removed and raise `AttributeError` | https://modal.com/docs/guide/modal-1-0-migration.md; 1.6.2 behaviour asserted by scripts/selfcheck.py |
| Removed APIs | `modal.Stub` raises `AttributeError` (use `modal.App`). 1.5.0 removed the static `.delete()` and `.create_deployed()`. 1.6.0 forbids a custom `__init__` on `@app.cls`. 1.6.2 adds `Function.autoscaler` | https://modal.com/docs/sdk/py/releases.md |

## Failure scenarios

| Symptom or status | Cause | What the code does | Retry |
|---|---|---|---|
| `InvalidError: Cannot stack @modal.asgi_app on top of @app.function` | decorator order | swap the decorators so `@app.function` is outermost | no |
| `DeprecationError` naming `min_containers`, `max_containers`, `scaledown_window` or `@modal.concurrent` | a pre-1.0 parameter (`keep_warm` and the others) | rename it; never silence the warning | no |
| `AttributeError` on `modal.Mount`, `modal.Stub` or `.lookup` | an API removed before 1.6.2 | `Image.add_local_*`, `modal.App`, `.from_name` | no |
| `modal serve` or `modal deploy` fails on `web/dist` | `npm run build` was not run; `add_local_dir` checks the path only at image build, so import and offline tests pass | run `cd web && npm run build` first (runbook) | once, after the build |
| `ExecutionError: Function has not been hydrated` | `.spawn()` called outside `modal serve` or `modal deploy` (a test or local script) | tests inject a stub runner; local mode uses the in-process `JobRunner` | no |
| `AuthError: Token missing` | Dict, Volume or FunctionCall access without a Modal token | offline tests must use fakes; on the Mac, run `modal setup` first | no |
| `NotFoundError` on a Secret or Volume | not created in this Environment, or a typo with `create_if_missing` off | create the `keyframe` Secret per Environment (runbook) | no |
| `GET /builds/<id>` while building | `get(timeout=0)` raised builtin `TimeoutError` | 202 with the persisted job state | client polls |
| Runner passed 900 s | `FunctionTimeoutError` from `get` | the watchdog writes `failed` with the last `stage` | no (one retry loop, AD-13) |
| Runner raised | `get` re-raises the runner's exception (crashed) | `failed` with `stage`; typed errors are normally persisted by the runner itself | no |
| Poll raises `ConnectionError`, `InternalError`, `ResourceExhaustedError`, `ServiceError` or `AuthError` | Modal's client failed while polling; the runner may still be going (or the runner itself raised that class) | `unknown`: 202 with the job unchanged; past `DEADLINE_S` the watchdog writes `failed` | client polls |
| Job stuck `queued` | `spawn()` failed after the `queued` record was written | the route writes `failed` (stage `ingest`) when `start` raises; the watchdog fails a `queued` job with no `call:<job_id>` key after 60 s | no |
| Call id older than 7 days | `OutputExpiredError` | `failed` if the record is not terminal; final records come from the Volume anyway | no |
| Request takes over 150 s | a route did build-scale work inline | never: builds are spawned. Any such route is a bug | n/a |
| Runner sees no photos, or a reader sees an old artifact | the writer did not `commit()` or the reader did not `reload()` | `put` ends with `commit()` and `get` begins with `reload()`; spawn only after the photo commit | once, after the fix |
| `volume busy` on `reload()` | a file on `/data` is open in the same container (`FileResponse`, an unclosed handle) | one process lock; read fully, then close | once |
| Artifact silently lost | two containers wrote the same path; the last write wins | one writer per job; cache files keyed by content hash; no shared index file (`list_rooms` lists directories) | no |
| Job progress reverted | the web container wrote the job record while the runner was live | the web container writes `<job_id>` only before the spawn and in the watchdog, after Modal reports the call ended or a backstop (orphan, deadline) fires; the runner stops on a terminal status at stage entry | no |
| Two requests take the same build quota slot, or the 21st build starts | a read-modify-write counter on one Dict key | one key per slot claimed with `put(..., skip_if_exists=True)` (AD-9); all 20 taken raises `BuildQuotaExceeded`. Slot keys expire after 7 idle days, which only frees a build. Atomicity under concurrent writers is verified in the hosted story first | no |
| Dict change lost | a nested value was changed without a put-back | write the whole value back | no |
| Dict entry gone | 7 days with no reads or writes | durable data lives on the Volume; the daily snapshot is the spend record | no |
| No `hosted-<date>.jsonl` | the app was only served, or deployed after 06:00 ET | deploy, then "run now" once on the dashboard | next run |
| Cold start on a judge's first visit | `min_containers` is 0 | autoscaler update to 1 (runbook) | n/a |
| Warm container gone mid-window | a redeploy reset the override | redeploy with `MIN_CONTAINERS=1`, or update again | n/a |
| Requests queue under load | `max_containers=1` plus more than 20 concurrent requests | by design (AD-9); raising the cap is Deferred | n/a |
| 429 from the Modal edge | workspace rate limit (200 requests per second for new accounts) | not expected at judging scale; ask Modal to raise it | client backoff |
| Dev traffic shows up in judge data | `modal serve` ran without `-e dev` | always serve in the dev Environment | n/a |
| A local script seeded or purged the wrong Volume | `from_name` resolved in the CLI's active Environment (for example a profile set to `dev`) | scripts pass `environment_name=` explicitly | once, with the right Environment |
| Reseed fails on existing files | `batch_upload()` defaults to `force=False` | `seed_rooms.py` uses `batch_upload(force=True)` | once, after the fix |
| Judge sessions or cache entries survive the purge | the purge removed only `rooms/judge/<room_id>` | the purge also deletes the room's sessions and the cache keys in its `cache-keys.json` | rerun the purge |

## Tested commands

| Command or snippet | What it proves | Result on 2026-10-21 | Where |
|---|---|---|---|
| `uv run --no-project --with modal==1.6.2 python .claude/skills/keyframe-modal/scripts/selfcheck.py` (uv 0.11.32, Python 3.13.16) | Pinned version, in a clean environment with only the pin. Signatures of `App.function` (timeout default 300, min/max containers, secrets, volumes, schedule), `App`, `concurrent`, `asgi_app`, `Function.spawn`, `FunctionCall.from_id`/`get`, `Dict.from_name`/`put(skip_if_exists)`, `Volume.from_name`/`commit`/`reload`/`batch_upload(force=False)`, `Cron`, `Secret.from_name`, and `environment_name` on the three `from_name`s. The Keyframe app shape (three Dicts, Volume, Secret, web, runner and both Cron functions) builds lazily with sockets blocked and deprecations as errors. Wrong order and an ASGI function with parameters raise `InvalidError`. Missing `max_inputs` raises `TypeError`. The four old kwargs and `web_endpoint` raise `DeprecationError`; `Stub`, `Mount` and `.lookup` raise `AttributeError`. `add_local_dir` accepts a missing directory. `.spawn()` offline raises `ExecutionError`. The src/infra and src/api blocks of references/hosted-code.md, executed as written: `runner_state` returns running, expired, timed_out, crashed and finished on Modal's real `_Invocation.poll_function`, unknown for each of the five client errors raised by the poll, and unknown for a runner that itself raised `ConnectionError`. The amended spine on in-memory fakes: the AD-9 names in modal_app.py (Dicts, Volume at `/data`, Secret, the four functions), `timeout=900` and `max_containers=1`; `ORPHAN_S` 60 and `DEADLINE_S` 1,200; `start` writes only `call:<job_id>`; 20 quota slots then `BuildQuotaExceeded`; the watchdog leaves a young orphan queued, fails an old one, leaves running and young unknown runners alone, fails an unknown runner past `DEADLINE_S` and a crashed one (stage kept), and returns a terminal record the runner wrote meanwhile; `build_poll_status` is 202 for queued and running, 200 for every terminal status; `sweep_sessions` deletes only sessions idle 24 h; `export_ledger` writes one JSON line per entry and commits | pass: 62 `ok` lines, then `selfcheck passed`, exit 0 (re-run on 2026-10-21 after the spine amendment) | offline here (packages from uv's cache; no Modal host contacted) |
| Stand-in `modal_app` module (App, image with `add_local_dir("web/dist")` and no such directory, Secret, three Dicts, Volume, ASGI web function, spawned runner, both Cron functions), imported with `MODAL_TOKEN_*` unset, an empty `HOME`, sockets blocked, deprecations as errors | the module-level code in references/hosted-code.md needs no credentials, network or `web/dist` to import | pass: four Functions defined, `web` is a web endpoint, no handle hydrated | offline here |
| `modal --version` | CLI version | `modal client version: 1.6.2` | offline here |
| `modal deploy --help`, `modal serve --help` | `-m`, `-e/--env`, `--strategy rolling\|recreate`, `--name`, `--tag`; serve documents the `-dev` suffix | pass: flags as cited | offline here |
| `modal secret create --help` | `--from-dotenv PATH`, `--from-json`, `--force`, `-e` | pass | offline here |
| `modal function autoscaler update --help`, `... settings --help` | `--min-containers`, `--max-containers`, `--scaledown-window`, `--buffer-containers`; FUNCTION is `APP/FUNCTION` or an id; settings shows overrides | pass | offline here |
| `modal environment create --help`, `modal setup --help` | `environment create NAME`; `setup` bootstraps config | pass | offline here |
| `modal volume ls --help`, `modal dict items --help`, `modal app logs --help` | `volume ls VOLUME [PATH]`; `dict items NAME [N]`; `app logs APP --since --function-call` | pass | offline here |
| `modal skills install --help` | `--claude`, `-g`, `--no-docs`, `-y` (how `.claude/skills/modal` was installed) | pass | offline here |
| `modal deploy --help` (`-e` text) | names outside an app resolve via `MODAL_ENVIRONMENT`, then the profile, then the workspace default | pass: wording as cited | offline here |
| `claude plugin validate .claude/skills` | frontmatter parses after the `paths` and description change (Claude Code 2.1.306) | pass: `Validation passed` | offline here |
| `modal serve -e dev -m src.api.modal_app` | image builds, the `-dev` URL serves, the decorator stack is accepted server-side | not run | live-only: confirm on the first hosted story |
| First `POST /builds` then `GET /builds/<id>` on the dev URL | spawn returns at once; 202 while running; `call:<job_id>` key; the runner sees the committed photos | not run | live-only |
| `Secret.from_name(..., required_keys=[...])` with a key missing | the failure surfaces at deploy, not at the first request | not run | live-only |
| 20 concurrent `reserve_build` calls on the dev Dict | `put(..., skip_if_exists=True)` lets exactly one caller claim each slot | not run | live-only: confirm before Thu Nov 5 |
| `modal serve -e dev`, then wait past 06:00 ET and `:17` | neither Cron fires under `serve` (inferred from cron.md) | not run | live-only |
| `purge_judge_rooms.py` against a dev judge room | room prefix, cache keys from `cache-keys.json` and sessions all gone; ids-only record written | not run | live-only (dev Environment first) |
| `volume.reload()` latency in the web container | cost of AD-7's reload-before-every-read | not run | live-only: measure on the first hosted build |
| `modal deploy -m src.api.modal_app`, then the dashboard's "run now" on `ledger_export` | permanent URL; Cron registered; snapshot written | not run | live-only (manual) |
| `modal function autoscaler update keyframe/web --min-containers 1`, then `... settings` | override applies without redeploy | not run | live-only (Thu Nov 5) |

## Known issues

- **Two kinds of `TimeoutError`.** Modal's poll raises the builtin `TimeoutError` for "still running". `modal.exception.TimeoutError` is a different class: it is the base of `FunctionTimeoutError` and `OutputExpiredError`, and it does not catch the running case. Never write `from modal.exception import TimeoutError`. Keep the except order of `runner_state`.
- **Quota slot atomicity (AD-9).** The build quota relies on `Dict.put(..., skip_if_exists=True)` returning `False` to every caller but one. The SDK docstring states the return value, not that the check is atomic under concurrent writers; AD-9 requires the hosted story to verify it (20 concurrent `reserve_build` calls on the dev Dict, Tested commands) before relying on it.
- **Reload on every read (AD-7).** Combined with `max_inputs=20`, this requires the process-wide Volume lock above, and the latency of `reload()` is unmeasured. Rooms are immutable (AD-12) and cache files are content-addressed, so "read first, reload only on a miss" would be safe for them, but that needs an AD-7 amendment first.
- **Ledger guard is per process (settled in AD-6).** The web container and every concurrent runner container hold their own `SpendLedger` lock over the shared `keyframe-ledger` Dict, so the cap can be overshot by the estimates of calls in flight. AD-6 accepts this for the hackathon; an atomic ledger store, and raising `max_containers`, stay Deferred.
- **Settings fields.** `Settings.mode` (`MODE`) and `Settings.min_containers` (`MIN_CONTAINERS`, default 0) landed with story 7.2. The Secret carries the names `Settings` reads, `MODEL_API_KEY` among them (Meta's documented name, AD-14).
- **Docs disagree on decorator order.** The job-queue guide stacks `@modal.asgi_app()` above `@modal.concurrent`, while the webhooks guide uses the order this skill uses. Both build offline. Keep the webhooks order.
- **`scaledown_window` range.** The cold-start guide says 2 s to 20 min, while the `autoscaler.update` docstring says 2 to 3600 s. Keyframe leaves it at the default.
- **Timezones are not checked offline.** `modal.Cron` accepts any timezone string offline, so a typo would surface only at deploy. selfcheck.py checks `America/New_York` with `zoneinfo`.

## References

- https://modal.com/llms.txt: index of every Modal docs page (append `.md` for plain text).
- https://modal.com/docs/guide/webhooks.md: `@modal.asgi_app`, the decorator order with `@modal.concurrent`, rate limits, body size.
- https://modal.com/docs/guide/webhook-timeouts.md: the 150 s limit, the 303 result URL, the spawn-and-poll pattern.
- https://modal.com/docs/guide/job-queue.md: `spawn`, `FunctionCall.from_id`, `get(timeout=0)`, 202 and expired handling, 7-day results.
- https://modal.com/docs/guide/function-invocation-methods.md: sync versus async invocation limits, result retention.
- https://modal.com/docs/guide/concurrent-inputs.md: `@modal.concurrent`, `max_inputs` and `target_inputs`, the thread and async rules.
- https://modal.com/docs/guide/timeouts.md: the default, range and per-attempt timeouts, `FunctionTimeoutError`, `startup_timeout`.
- https://modal.com/docs/guide/dicts.md: `Dict.from_name`, serialization, size limits, 7-day idle expiry, the put-back rule.
- https://modal.com/docs/guide/volumes.md: commit and reload, background commits, "volume busy", last write wins, limits, `batch_upload`.
- https://modal.com/docs/guide/cron.md: `Cron` and `Period`, deploy-only activation, no pause, "run now".
- https://modal.com/docs/guide/cold-start.md: `min_containers`, `buffer_containers`, `scaledown_window`, idle billing.
- https://modal.com/docs/guide/resources.md: default CPU and memory requests, billing on the higher of request and use.
- https://modal.com/docs/guide/scale.md: autoscaler settings, `Function.autoscaler.update` and `settings`, the per-function container cap.
- https://modal.com/docs/guide/secrets.md: creating and attaching Secrets, key and value limits, precedence.
- https://modal.com/docs/guide/webhook-urls.md: deployed URL structure, the `-dev` suffix under `serve`, label truncation.
- https://modal.com/docs/guide/environments.md: per-Environment Secrets and object lookups, the default "main" Environment.
- https://modal.com/docs/guide/managing-deployments.md: the `rolling` and `recreate` deploy strategies, stopping apps.
- https://modal.com/docs/guide/modal-1-0-migration.md: the 1.0 renames and removals.
- https://modal.com/docs/sdk/py/releases.md: 1.6.2 (`Function.autoscaler`, `modal function autoscaler`), 1.6.0 and 1.5.0 breaking changes.
- https://modal.com/docs/cli/latest/skills.md: `modal skills install --claude`, which installed the general `modal` skill.
