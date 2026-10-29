# Hosted code shapes for Keyframe on Modal 1.6.2

Sketches for `src/api/modal_app.py` and `src/infra/modal.py`. The shapes, decorator stack and call order are checked: `scripts/selfcheck.py` asserts them offline, and a stand-in with the same shapes was imported with no token and no network on 2026-10-21. Keyframe names such as `Settings.min_containers`, `create_app`, `wire`, `JobState`, `build_runner` and `final_record` are placeholders for the code the stories will write. Rename them freely, but keep the order of operations.

## `src/api/modal_app.py`

```python
"""Hosted entry point. Deploy by hand from the repo root: modal deploy -m src.api.modal_app"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import modal

from src.config import Settings
from src.infra.modal import ModalHandles, export_ledger, sweep_sessions

APP_NAME = "keyframe"
DATA = "/data"
ET = ZoneInfo("America/New_York")

settings = Settings.from_env()  # read at deploy time for MIN_CONTAINERS (AD-14), again in each container

image = (
    modal.Image.debian_slim(python_version="3.13")
    .uv_sync(uv_version="0.11.32", extra_options="--no-dev")  # installs uv.lock exactly, no pytest (keyframe-devops)
    .env({"MODE": "hosted", "GUIDE": "verbatim"})       # not secret, so it goes on the image
    .add_local_python_source("src")                       # .py files only; .env never ships
    .add_local_dir("web/dist", "/root/web/dist")          # lazy: a missing build fails only at serve or deploy
)

secret = modal.Secret.from_name("keyframe", required_keys=["MODEL_API_KEY", "FAL_KEY", "ACCESS_CODE"])
volume = modal.Volume.from_name("keyframe-data", create_if_missing=True)
jobs = modal.Dict.from_name("keyframe-jobs", create_if_missing=True)
sessions = modal.Dict.from_name("keyframe-sessions", create_if_missing=True)
ledger = modal.Dict.from_name("keyframe-ledger", create_if_missing=True)

app = modal.App(APP_NAME, image=image, secrets=[secret], volumes={DATA: volume})


def handles() -> ModalHandles:
    return ModalHandles(jobs=jobs, sessions=sessions, ledger=ledger, volume=volume,
                        root=DATA, runner=run_build)


@app.function(timeout=900)                                 # AD-7: the one writer per job; no retries (AD-13)
def run_build(job_id: str) -> None:
    from src.api.wiring import build_runner
    build_runner(settings, handles()).run(job_id)


@app.function(min_containers=settings.min_containers, max_containers=1)   # AD-9; cpu and memory left at defaults
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    from src.api.app import create_app
    from src.api.wiring import wire
    return create_app(wire(settings, hosted=handles()))


@app.function(schedule=modal.Cron("0 6 * * *", timezone="America/New_York"))   # AD-9 daily export
def ledger_export() -> None:
    export_ledger(handles(), day=datetime.now(ET).date())


@app.function(schedule=modal.Cron("17 * * * *"))                               # AD-8 session retention, hourly
def session_sweep() -> None:
    sweep_sessions(handles(), now=datetime.now(UTC))
```

Notes:
- **Decorator stack.** `@app.function` is outermost, `@modal.concurrent(max_inputs=20)` sits in the middle, and `@modal.asgi_app()` sits on the function. The function takes no parameters and returns the FastAPI app. `stack.md` fixes `max_inputs=20`.
- **Imports.** FastAPI and the Keyframe app are imported inside `web()`, so the module also imports in a local environment that has only `modal`. `src.config` and `src.infra.modal` must import without FastAPI installed.
- **Runner handle.** `run_build` reaches `infra` as an injected handle (`ModalHandles.runner`). Under `modal serve` that handle points at the ephemeral app. `modal.Function.from_name("keyframe", "run_build")` would always resolve to the deployed app instead. Injection also keeps `src/infra` from importing `src/api` (AD-1).
- **`web/dist` is checked late.** `add_local_dir` records the path and reads it only when the image is built, so a missing `npm run build` passes import and the offline tests and fails at `modal serve` or `modal deploy`. Checked offline on 2026-10-21: a nonexistent directory was accepted.
- **Resources.** `web` sets no `cpu` or `memory`, so Modal's default request (0.125 core, 128 MiB) applies and billing follows the higher of the request and actual use (https://modal.com/docs/guide/resources.md). The runbook's warm-container estimate is therefore an upper bound for an idle container.
- **Image order.** `add_local_*` calls go last in the image chain. They mount files when the container starts, and any build step placed after them needs `copy=True`.
- **One Secret.** Exactly one `modal.Secret` named `keyframe` is attached at the App level (AD-14). Never build a Secret from the local `.env` (`Secret.from_dotenv`, `Secret.from_dict`) in this module.

## `src/infra/modal.py` (the hosted adapters, AD-9)

```python
import json
import os
import threading
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import modal
import modal.exception as mexc

TERMINAL = {"done", "failed", "needs_more_photos", "needs_recapture"}
BUILD_QUOTA = 20          # AD-9: 20 slot keys; the 21st build is refused
ORPHAN_S = 60             # AD-7: a queued job whose spawn was never recorded
DEADLINE_S = 900 + 300    # AD-7: runner timeout plus margin; past it an unknown poll counts as dead
SESSION_TTL = timedelta(hours=24)   # AD-8: sessions are deleted 24 h after their last event


@dataclass(frozen=True)
class ModalHandles:
    jobs: modal.Dict
    sessions: modal.Dict
    ledger: modal.Dict
    volume: modal.Volume
    root: str                 # mount path, "/data"
    runner: modal.Function    # run_build


# Modal client errors: raised while polling, or re-raised from a runner that hit one. Outcome unknown.
POLL_ERRORS = (mexc.ConnectionError, mexc.InternalError, mexc.ResourceExhaustedError,
               mexc.ServiceError, mexc.AuthError)


def runner_state(call: modal.FunctionCall) -> str:
    """Classify a spawned runner without waiting. Except-clause order matters."""
    try:
        call.get(timeout=0)
    except TimeoutError:                     # builtin TimeoutError: no output yet
        return "running"
    except mexc.FunctionTimeoutError:        # the runner passed timeout=900
        return "timed_out"
    except mexc.OutputExpiredError:          # result older than 7 days
        return "expired"
    except POLL_ERRORS:                      # the poll failed; the runner may still be going
        return "unknown"
    except Exception:                        # get() re-raises what the runner raised
        return "crashed"
    return "finished"


def age_s(state: "JobState") -> float:
    return (datetime.now(UTC) - state.created_at).total_seconds()


class ModalJobRunner:                        # JobRunner port
    def __init__(self, h: ModalHandles) -> None:
        self.h = h

    def start(self, job_id: str) -> None:
        call = self.h.runner.spawn(job_id)                 # input is the id only
        self.h.jobs[f"call:{job_id}"] = call.object_id     # AD-7: its own key; the runner owns <job_id>


class ModalJobStore:                         # JobStore port: in-flight in the Dict, final on the Volume
    def __init__(self, h: ModalHandles, files: "VolumeFiles") -> None:
        self.h, self.files = h, files

    def put(self, job_id: str, state: "JobState") -> None:
        self.h.jobs[job_id] = state.model_dump(mode="json")   # whole value, every time

    def reserve_build(self, job_id: str) -> int:
        """Claim the first free quota slot and return its number; the 21st build is refused."""
        for n in range(1, BUILD_QUOTA + 1):
            if self.h.jobs.put(f"build:{n}", job_id, skip_if_exists=True):   # one conditional write per slot
                return n
        raise BuildQuotaExceeded()

    def get(self, job_id: str) -> "JobState | None":
        raw = self.h.jobs.get(job_id)
        if raw is None:
            raw = self.final_record(job_id)                    # AD-7 record beside the Room, via self.files; None if absent
        if raw is None:
            return None
        state = JobState.model_validate(raw)
        if state.status not in TERMINAL:
            state = self._watchdog(job_id, state)
        return state

    def _watchdog(self, job_id: str, state: "JobState") -> "JobState":
        call_id = self.h.jobs.get(f"call:{job_id}")
        if call_id is None:                                   # spawn not recorded, yet or ever
            outcome = "orphaned" if age_s(state) > ORPHAN_S else "running"
        else:
            outcome = runner_state(modal.FunctionCall.from_id(call_id))
        if outcome == "running" or (outcome == "unknown" and age_s(state) < DEADLINE_S):
            return state                                      # unchanged; the client polls again
        fresh = JobState.model_validate(self.h.jobs[job_id])  # the runner may have just finished
        if fresh.status in TERMINAL:
            return fresh
        failed = fresh.model_copy(update={"status": "failed"})  # keeps its stage
        self.put(job_id, failed)
        return failed


class VolumeFiles:
    """All Volume I/O in one process goes through one lock (see SKILL.md: Volume rules)."""

    def __init__(self, h: ModalHandles) -> None:
        self.h, self.lock = h, threading.Lock()

    def write_bytes(self, rel: str, data: bytes) -> None:
        with self.lock:
            path = f"{self.h.root}/{rel}"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            self.h.volume.commit()            # nothing is visible elsewhere before this

    def read_bytes(self, rel: str) -> bytes | None:
        with self.lock:
            self.h.volume.reload()            # fails with "volume busy" if a file is open
            try:
                with open(f"{self.h.root}/{rel}", "rb") as f:
                    return f.read()           # read fully, close, then release the lock
            except FileNotFoundError:
                return None
```

Notes:
- **Job state.** Store job state, sessions and ledger entries as plain JSON dicts (`model_dump(mode="json")`), not pickled pydantic objects. During a rolling redeploy an old container and a new container read the same keys, and the `modal dict items` CLI can show plain dicts.
- **Order in `POST /builds`.** Check the access code; read the body under the byte cap (413 `upload_too_large`: past `MAX_UPLOAD_BYTES` unread or mid-stream, or after parsing an original past 20 MiB or a downscale past 2 MiB); validate the upload, so a refused one claims no slot and nothing needs releasing; then `reserve_build`. Store both photo streams through `ArtifactStore` (each write commits). Then write the `queued` job record, then call `JobRunner.start`. A runner spawned before the commit would `reload()` and find no photos. If `start` raises, the route writes `failed` with stage `ingest` itself and answers with the error envelope; the watchdog's `orphaned` branch is the backstop for a web container that died in between.
- **Build counter (AD-9).** AD-9 keeps the counter as 20 slot keys, because a read-modify-write on one Dict key would let concurrent requests read the same count. Each slot is claimed with `put(..., skip_if_exists=True)`, which returns `False` when the key already exists (SDK docstring). AD-9 requires the hosted story to verify that the claim is atomic under concurrent writers before relying on it: `scripts/quota_probe.py`, run by the ops workflow's `quota-probe` action, races separate processes for the slot keys on an ephemeral Dict (runbook.md); it passed in `main` on Oct 29 (GitHub run 40821411610), processes on one runner. (amended 29 Oct 2026, correct-course record) `POST /access/check` reports `builds_left` as `BUILD_QUOTA` minus the slots present.
- **Response codes (AD-7).** `GET /builds/<job_id>` returns the job state from `JobStore.get` with `build_poll_status` (below): 202 while the status is `queued` or `running`, and 200 once it is terminal. A missing record is 404. The local `JobStore` returns the same codes, since AD-7 and the HTTP conventions fix them for both modes.
- **Who writes `<job_id>` (AD-7).** The runner owns the record and writes it after each stage; the web container never writes progress back. It writes the key only twice: the `queued` record before the spawn, and the watchdog's `failed`.
  - On `timed_out`, `crashed`, `expired` or `finished`, Modal has reported that the call ended, so the runner can no longer write and the watchdog cannot race it.
  - On `unknown` (the poll itself failed) the job is left unchanged. A runner that itself raised one of the `POLL_ERRORS` classes reads the same way, because `get()` re-raises the runner's exception class; so `unknown` past `DEADLINE_S` counts as dead.
  - `orphaned` (`ORPHAN_S`, 60 s) and the deadline (`DEADLINE_S`, 1,200 s) are AD-7's backstops, and the runner may in principle still be live. The runner therefore stops when it rereads a terminal status at a stage entry. A stage that finishes between the watchdog's write and that reread can still overwrite `failed` with its progress; this is rare and accepted.
- **Sessions (AD-8).** Each `keyframe-sessions` value carries `room_id` and `last_event_at` (ISO 8601 UTC) beside its events. The hourly `session_sweep` Cron deletes a session 24 h after its last event, and the judge-room purge deletes a purged room's sessions. The Dict's own 7-day idle expiry is not a retention control.

## `GET /builds/<job_id>` status code (`src/api`, both modes)

```python
POLLING = {"queued", "running"}


def build_poll_status(status: str) -> int:
    """AD-7 and the HTTP conventions: 202 while queued or running, 200 once terminal."""
    return 202 if status in POLLING else 200
```

The route calls it after `JobStore.get`, which has already run the watchdog, so a dead runner answers 200 with `failed`. It lives with the routes, not in `src/infra`, because both modes answer the same way.

## Daily ledger export (AD-9, `budgets.md`)

```python
def export_ledger(h: ModalHandles, day: date) -> None:
    path = f"{h.root}/spend/hosted-{day.isoformat()}.jsonl"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for key, entry in h.ledger.items():
            f.write(json.dumps({"key": key, **entry}) + "\n")
    h.volume.commit()


def sweep_sessions(h: ModalHandles, now: datetime) -> None:
    """AD-8: delete each session 24 h after its last event (hourly Cron, so at most an hour late)."""
    cutoff = (now - SESSION_TTL).isoformat()
    stale = [key for key, s in h.sessions.items() if s["last_event_at"] < cutoff]   # collect, then delete
    for key in stale:
        h.sessions.pop(key, None)
```

The Cron functions run in their own containers, so they do not need the web container's lock. The export writes one new file per day, so it never contends on a path. Whether iterating `ledger.items()` resets the 7-day idle clock of each entry is not documented (the Dicts page counts "reads or writes"); do not rely on the export to keep entries alive.

## Local scripts that touch the Volume (need a Modal token; live-only)

These run on the Mac, outside any container. `commit()` and `reload()` work only inside a container that mounts the Volume, so the scripts use the remote file API.

Handles: `modal.Volume.from_name("keyframe-data", environment_name=ENV)` and `modal.Dict.from_name("keyframe-sessions", environment_name=ENV)`, where `ENV = "main"` (every workspace's default Environment, https://modal.com/docs/guide/environments.md) or whichever Environment the judge app is deployed in. Without `environment_name`, the name resolves in the CLI's active Environment (`MODAL_ENVIRONMENT`, then the profile, then the workspace default, per `modal deploy --help`), so a profile set to `dev` would seed or purge the wrong Volume. No `create_if_missing`, so a typo fails with `NotFoundError` instead of creating an empty object.

| Script | Call | Note |
|---|---|---|
| `scripts/seed_rooms.py` | `with volume.batch_upload(force=True) as batch: batch.put_file(local, "/rooms/demo/<room_id>/...")` | `force` defaults to `False`, so a reseed over existing files fails without it (SDK docstring). Running containers see the files after their next `reload()` |
| `scripts/purge_judge_rooms.py` | the sketch below | Run Tue Nov 10. A listed id that is also a Demo room is kept (`kept <room_id>: a Demo room`), with no record |
| `scripts/promote_room.py` | `batch_upload(force=True)` of the Demo copy, its read-back through `read_file` and `listdir`, then one `remove_file("/rooms/judge/<room_id>", recursive=True)` | Moves a Judge room to `rooms/demo/`; no deletion record, no Dict opened; `already promoted` when no Judge copy is left | (amended 29 Oct 2026, correct-course record)
| `scripts/ledger.py export` | `b"".join(volume.read_file("/spend/hosted-<date>.jsonl"))` | Merges the latest hosted snapshot into `spend/exports/ledger-<date>.json` |

AD-8 deletes a judge room's originals, sessions and the cache entries listed in its `cache-keys.json` together with the room. The build leaves a way to find each:
- `ArtifactStore` writes every artifact of a hosted judge build, downscaled photos and originals included, under the build's `rooms/judge/<room_id>/` prefix.
- Cache files are keyed by content hash with no room index, so the runner (the one writer per job) writes `cache-keys.json` beside the final record, listing every cache key the build read or wrote. A key shared with another build is deleted too; that only costs a cache miss later.
- In code (`src/infra/modal.py`), `run_build` (Story 7.8) runs `Build.run` through `run_judge_build(run, job_id, keys=CacheKeyLog(stores.cache, stores.artifacts, room_id))` and hands that `CacheKeyLog` to the providers as their Cache. The log adds each key to `cache-keys.json`, committed, before the entry is first read or written, so a runner killed mid-stage leaves no unlisted entry; calling `Build.run` directly would leave no `cache-keys.json` at all.
- Session values carry `room_id` (see Sessions above).

```python
# scripts/purge_judge_rooms.py, per judge room (shape)
keys = json.loads(b"".join(volume.read_file(f"/rooms/judge/{room_id}/cache-keys.json")))
for key in keys:
    volume.remove_file(f"/cache/{key}")
for sid in [k for k, s in sessions.items() if s["room_id"] == room_id]:
    sessions.pop(sid, None)
volume.remove_file(f"/rooms/judge/{room_id}", recursive=True)   # Room, final record, photos, originals
with volume.batch_upload() as batch:                            # ids-only record (AD-9)
    batch.put_file(io.BytesIO(json.dumps(record).encode()), f"/rooms/deleted/{room_id}.json")
jobs.pop(job_id, None)
jobs.pop(f"call:{job_id}", None)
```

## Offline tests

Tests under `tests/` never reach Modal (AD-17). The adapters take `ModalHandles`, so tests can pass a plain `dict` for each Dict, a temporary directory for `root`, and a stub with no-op `commit()` and `reload()` for the Volume. The runner can be a stub whose `spawn()` returns an object with an `object_id`; the watchdog tests pass a stub whose `get()` raises each outcome. Calling `.spawn()` on a real Function outside a running app raises `ExecutionError` ("has not been hydrated"), and any Dict access raises `AuthError` with no token. `scripts/selfcheck.py` executes this file's `src/infra` and `src/api` blocks as written: it runs `runner_state` against Modal's real poll code, and the job store, runner, watchdog, `build_poll_status`, `sweep_sessions` and `export_ledger` against the same kind of in-memory fakes, so the code here and the checks cannot drift apart.
