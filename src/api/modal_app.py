"""The hosted entry (AD-9, AD-14): one Modal app that serves the same FastAPI app as Local mode.

Deploy by hand from the repo root, after the web build:
`modal deploy -m src.api.modal_app`. The image
installs `uv.lock` and sets `MODE=hosted` and `GUIDE=verbatim`, so in the
container `Settings` selects the hosted adapters and the verbatim Guide;
it carries `proposals/` when the folder exists, so `DEMO_TRICKSTER=scripted`
or `authored` has its source in the container (FR-31, AD-15);
the `keyframe` Secret carries the keys `Settings` reads, `SPEND_CAP_USD`
(the hosted allocation) among them, and must carry `SECRET_KEYS`, which the
deploy asserts. `web` serves `web/dist` at `/` and the
API under `/api/` from one origin with no CORS, in one container
(`max_containers=1`, AD-9) taking up to 20 requests at once, with no GPU.
`MIN_CONTAINERS` is read through `Settings` when the module is imported,
so a deploy takes it from the deploying shell (default 0).

`POST /builds` ingests and commits the photos, writes the `queued` record
and spawns `run_build` with the job id only, then answers at once; `web`
keeps its default timeout and never runs a stage (AD-7). `run_build` is
the stage runner, `timeout=900` and `max_containers=1`, so a second
spawned Build waits `queued` until the first ends; it sets no `retries`
(AD-13). Each read of an in-flight job polls the runner's call with
`FunctionCall.from_id(id).get(timeout=0)` for the watchdog. `ledger_export`
runs daily at 06:00 New York time and writes the hosted ledger snapshot
`spend/hosted-<date>.jsonl` to the Volume (AD-9). `session_sweep` runs
hourly at minute 17 and deletes every Session more than 24 h past its last
event through `sweep_sessions` (AD-8); no request triggers it.

Importing this module contacts no Modal service: the Secret, the Volume,
the three Dicts and the functions are lazy handles, and FastAPI, the app
and the wiring are imported inside the functions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import modal
import modal.exception

from src.config import Settings
from src.infra.modal import (
    JOBS_DICT,
    LEDGER_DICT,
    MOUNT,
    SESSIONS_DICT,
    VOLUME,
    ModalHandles,
    RunnerState,
    export_hosted_ledger,
    sweep_sessions,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

APP_NAME = "keyframe"
SECRET = "keyframe"
"""The one Secret (AD-14), attached at the App level."""
SECRET_KEYS = ["MODEL_API_KEY", "FAL_KEY", "ACCESS_CODE"]
"""The keys the Secret must carry: Modal asserts them when the Secret hydrates at deploy, so a Secret
missing one fails `modal deploy` by name instead of serving and failing the first Build (the Meta
adapter itself runs keyless, AD-14)."""
WEB_DIST = "/root/web/dist"
"""Where the image puts `web/dist`: beside `/root/src`, where `src/api/app.py` looks for it."""
PROPOSALS_DIR = "/root/proposals"
"""Where the image puts `proposals/`: beside `/root/src`, where `wiring.PROPOSALS_ROOT` looks for it (AD-15)."""
SNAPSHOT_TZ = "America/New_York"
"""The daily ledger snapshot runs at 06:00 in this zone and is named by its date there (AD-9)."""
SWEEP_CRON = "17 * * * *"
"""The hourly Session sweep (AD-8), off the top of the hour, in UTC."""
POLL_ERRORS = (
    modal.exception.ConnectionError,
    modal.exception.InternalError,
    modal.exception.ResourceExhaustedError,
    modal.exception.ServiceError,
    modal.exception.AuthError,
)
"""Modal client errors: the poll failed, or the runner itself raised one, so the call's state is not known."""

settings = Settings.from_env()
"""Read where the deploy runs for `MIN_CONTAINERS`, and again in each container, which is `MODE=hosted`."""

image = (
    modal.Image.debian_slim(python_version="3.13")
    .uv_sync(uv_version="0.11.32", extra_options="--no-dev")
    .env({"MODE": "hosted", "GUIDE": "verbatim"})
    .add_local_python_source("src")
    .add_local_dir("web/dist", WEB_DIST)
)
if Path("proposals").is_dir():  # not committed yet; a missing folder would fail the deploy
    image = image.add_local_dir("proposals", PROPOSALS_DIR)
secret = modal.Secret.from_name(SECRET, required_keys=SECRET_KEYS)
volume = modal.Volume.from_name(VOLUME, create_if_missing=True)
jobs = modal.Dict.from_name(JOBS_DICT, create_if_missing=True)
sessions = modal.Dict.from_name(SESSIONS_DICT, create_if_missing=True)
ledger = modal.Dict.from_name(LEDGER_DICT, create_if_missing=True)

app = modal.App(APP_NAME, image=image, secrets=[secret], volumes={MOUNT.as_posix(): volume})


def handles() -> ModalHandles:
    """The AD-9 handles the hosted adapters run over, with `run_build.spawn` and the call poll."""
    return ModalHandles(jobs=jobs, sessions=sessions, ledger=ledger, volume=volume, root=MOUNT, spawn=run_build.spawn, poll=poll_call)


def poll_call(call_id: str) -> RunnerState:
    """The state of a spawned call, without waiting; the except order matters.

    The builtin `TimeoutError` means no output yet; Modal's own
    `TimeoutError` subclasses are the call's timeout and its expired result.
    """
    try:
        modal.FunctionCall.from_id(call_id).get(timeout=0)
    except TimeoutError:
        return "running"
    except modal.exception.FunctionTimeoutError:
        return "timed_out"
    except modal.exception.OutputExpiredError:
        return "expired"
    except POLL_ERRORS:
        return "unknown"
    except Exception:  # noqa: BLE001 - `get` re-raises whatever the runner raised
        return "crashed"
    return "finished"


@app.function(min_containers=settings.min_containers, max_containers=1)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web() -> FastAPI:
    """The FastAPI app over the hosted adapters."""
    from src.api.app import create_app

    return create_app(settings, handles=handles())


@app.function(timeout=900, max_containers=1)
def run_build(job_id: str) -> None:
    """The stage runner (AD-7): the one writer of the job's record, spawned per Build with its id only."""
    from src.api.wiring import run_hosted_build

    run_hosted_build(settings, handles(), job_id)


@app.function(schedule=modal.Cron("0 6 * * *", timezone=SNAPSHOT_TZ))
def ledger_export() -> None:
    """The daily hosted ledger snapshot: every current-epoch entry to `spend/hosted-<date>.jsonl` on the Volume, committed (AD-9)."""
    export_hosted_ledger(handles(), datetime.now(ZoneInfo(SNAPSHOT_TZ)).date())


@app.function(schedule=modal.Cron(SWEEP_CRON))
def session_sweep() -> None:
    """The hourly Session sweep (AD-8): every Session whose last event is more than 24 h old is deleted."""
    sweep_sessions(handles(), now=datetime.now(UTC))
