"""The hosted entry (AD-9, AD-14): one Modal app that serves the same FastAPI app as Local mode.

Deploy by hand from the repo root, after the web build:
`modal deploy -m src.api.modal_app` (the keyframe-modal runbook). The image
installs `uv.lock` and sets `MODE=hosted` and `GUIDE=verbatim`, so in the
container `Settings` selects the hosted adapters and the verbatim Guide;
the `keyframe` Secret carries the keys `Settings` reads, `SPEND_CAP_USD`
(the hosted allocation) among them. `web` serves `web/dist` at `/` and the
API under `/api/` from one origin with no CORS, in one container
(`max_containers=1`, AD-9) taking up to 20 requests at once, with no GPU.
`MIN_CONTAINERS` is read through `Settings` when the module is imported,
so a deploy takes it from the deploying shell (default 0).

Importing this module contacts no Modal service: the Secret, the Volume and
the three Dicts are lazy handles, and FastAPI and the app are imported
inside `web`. `run_build` and the two Cron functions join with their
stories (7.8 and the session sweep).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import modal

from src.config import Settings
from src.infra.modal import JOBS_DICT, LEDGER_DICT, MOUNT, SESSIONS_DICT, VOLUME, ModalHandles

if TYPE_CHECKING:
    from fastapi import FastAPI

APP_NAME = "keyframe"
SECRET = "keyframe"
"""The one Secret (AD-14), attached at the App level."""
WEB_DIST = "/root/web/dist"
"""Where the image puts `web/dist`: beside `/root/src`, where `src/api/app.py` looks for it."""

settings = Settings.from_env()
"""Read where the deploy runs for `MIN_CONTAINERS`, and again in each container, which is `MODE=hosted`."""

image = (
    modal.Image.debian_slim(python_version="3.13")
    .uv_sync(uv_version="0.11.32", extra_options="--no-dev")
    .env({"MODE": "hosted", "GUIDE": "verbatim"})
    .add_local_python_source("src")
    .add_local_dir("web/dist", WEB_DIST)
)
secret = modal.Secret.from_name(SECRET)
volume = modal.Volume.from_name(VOLUME, create_if_missing=True)
jobs = modal.Dict.from_name(JOBS_DICT, create_if_missing=True)
sessions = modal.Dict.from_name(SESSIONS_DICT, create_if_missing=True)
ledger = modal.Dict.from_name(LEDGER_DICT, create_if_missing=True)

app = modal.App(APP_NAME, image=image, secrets=[secret], volumes={MOUNT.as_posix(): volume})


def handles() -> ModalHandles:
    """The AD-9 handles the hosted adapters run over."""
    return ModalHandles(jobs=jobs, sessions=sessions, ledger=ledger, volume=volume, root=MOUNT)


@app.function(min_containers=settings.min_containers, max_containers=1)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web() -> FastAPI:
    """The FastAPI app over the hosted adapters."""
    from src.api.app import create_app

    return create_app(settings, handles=handles())
