#!/usr/bin/env python3
"""Purge every Judge room from the hosted `keyframe-data` Volume and print what went (FR-33, NFR-4, AD-8, AD-9). Run Tue Nov 10.

    uv run scripts/purge_judge_rooms.py               # Environment main
    uv run scripts/purge_judge_rooms.py --env dev --dry-run

The first line printed is the Modal Environment, before anything is listed
or deleted; every Dict and the Volume are resolved in that Environment by
`from_name(..., environment_name=...)`, never in the CLI's active one, and
need a Modal token. `delete_judge_room` reads and writes the Volume through
its mount, so the purge runs in one short-lived container of its own app
that mounts `keyframe-data` at `/data`, its output streamed back.

`purge` runs `delete_judge_room` on every directory under `rooms/judge/`,
those of Builds that ended without a Room included (each keeps its final job
record there, so its job id is known after the Dict entry expires), and on
every room whose deletion record under `rooms/deleted/` names a job whose
keys are still in `keyframe-jobs`, which that call pops from the record
before reading any stale job entry; it prints each ids-only record returned. A room whose deletion fails is named on stderr and the
remaining rooms are still attempted; any failure exits 1, and a rerun
completes what an earlier attempt left. `--dry-run` prints the `room_id`
and `job_id` of every Judge room that would go and deletes nothing, so no
record is written. With no Judge room it prints that there is nothing to
purge. Demo rooms under `rooms/demo/` are never touched: a listed id that
is also a Demo room (a Judge copy an older promotion left) is kept, in the
dry run and the real run alike, with `kept <room_id>: a Demo room` printed,
so no deletion record names a Demo room and the purge never fails on one
(`scripts/promote_room.py` removes that Judge copy). Nothing on the local
machine is written: not `rooms/`, not `.cache/`, not the git index.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from src.infra.modal import (
    JOBS_DICT,
    JUDGE_PARTITION,
    LEDGER_DICT,
    MOUNT,
    ROOMS_DIR,
    SESSIONS_DICT,
    VOLUME,
    DictJobStore,
    ModalHandles,
    VolumeArtifactStore,
    VolumeFiles,
    call_key,
    delete_judge_room,
    deletion_records,
)

if TYPE_CHECKING:
    import modal

ENVIRONMENT = "main"
"""The Modal Environment the judge app is deployed in, passed to every `from_name` explicitly."""
APP_NAME = "keyframe-purge"
"""The purge's own short-lived app; it never deploys and shares nothing with `keyframe` but the named Dicts and Volume."""
UV_VERSION = "0.11.32"
"""CI's uv, as `src/api/modal_app.py` installs `uv.lock` with."""
TIMEOUT_S = 900
"""The purge container's time limit in seconds."""
JUDGE_DIR = f"{ROOMS_DIR}/{JUDGE_PARTITION}"


def judge_room_ids(handles: ModalHandles) -> list[str]:
    """The name of every directory under `rooms/judge/`, sorted; a Build that ended without a Room still has one."""
    files = VolumeFiles(handles.volume, handles.root)
    return [name for name in files.names(JUDGE_DIR) if (handles.root / JUDGE_DIR / name).is_dir()]


def lingering_room_ids(handles: ModalHandles) -> list[str]:
    """The room id of every deletion record whose job still has a key in `keyframe-jobs`: an earlier deletion left it unfinished."""
    records = deletion_records(VolumeFiles(handles.volume, handles.root))
    return sorted(r.room_id for r in records if r.job_id is not None and (r.job_id in handles.jobs or call_key(r.job_id) in handles.jobs))


def purge(handles: ModalHandles, *, today: date, dry_run: bool = False) -> int:
    """Delete every Judge room and finish every lingering deletion, printing each ids-only record; 1 when any failed, after every room was attempted.

    A listed id that is also a Demo room (`ArtifactStore.is_demo_room`) is kept and named, never deleted.
    """
    files = VolumeFiles(handles.volume, handles.root)
    demo = VolumeArtifactStore(files)
    room_ids: list[str] = []
    for room_id in sorted({*judge_room_ids(handles), *lingering_room_ids(handles)}):
        if demo.is_demo_room(room_id):
            print(f"kept {room_id}: a Demo room")
        else:
            room_ids.append(room_id)
    if not room_ids:
        print(f"nothing to purge: {JUDGE_DIR}/ holds no Judge room")
        return 0
    if dry_run:
        jobs = DictJobStore(handles.jobs, files)
        for room_id in room_ids:
            print(f"would delete room_id={room_id} job_id={jobs.job_of(room_id)}")
        print(f"dry run: {len(room_ids)} Judge rooms would go; nothing deleted")
        return 0
    failed: list[str] = []
    for room_id in room_ids:
        try:
            record = delete_judge_room(handles, room_id, today=today)
        except Exception as error:  # noqa: BLE001 - name the room and go on; a rerun completes it
            failed.append(room_id)
            print(f"failed {room_id}: {type(error).__name__}: {error}", file=sys.stderr)
            continue
        print(f"deleted {record.model_dump_json()}")
    if failed:
        print(f"purge incomplete: {len(failed)} of {len(room_ids)} Judge rooms failed: {' '.join(failed)}", file=sys.stderr)
        return 1
    print(f"purged {len(room_ids)} Judge rooms; {JUDGE_DIR}/ holds no Judge room")
    return 0


def open_handles(environment: str) -> ModalHandles:
    """The AD-9 handles in `environment`, without `create_if_missing`, so a wrong Environment fails instead of purging an empty Volume."""
    import modal

    return ModalHandles(
        jobs=modal.Dict.from_name(JOBS_DICT, environment_name=environment),
        sessions=modal.Dict.from_name(SESSIONS_DICT, environment_name=environment),
        ledger=modal.Dict.from_name(LEDGER_DICT, environment_name=environment),
        volume=modal.Volume.from_name(VOLUME, environment_name=environment),
        root=MOUNT,
    )


def purge_app(environment: str) -> tuple[modal.App, modal.Function]:
    """The purge's app and its one function, which runs `purge` where `keyframe-data` from `environment` is mounted at `/data`; nothing is contacted until it runs."""
    import modal

    image = (
        modal.Image.debian_slim(python_version="3.13")
        .uv_sync(str(REPO), uv_version=UV_VERSION, extra_options="--no-dev")
        .add_local_python_source("src")
    )
    app = modal.App(APP_NAME, image=image)
    volume = modal.Volume.from_name(VOLUME, environment_name=environment)

    @app.function(serialized=True, volumes={MOUNT.as_posix(): volume}, timeout=TIMEOUT_S)
    def purge_mounted(today: date, dry_run: bool) -> int:
        return purge(open_handles(environment), today=today, dry_run=dry_run)

    return app, purge_mounted


def run_remote(environment: str, *, today: date, dry_run: bool) -> int:
    """Run the purge in its container, streaming its output here, and return its exit status."""
    import modal

    app, purge_mounted = purge_app(environment)
    with modal.enable_output(), app.run(environment_name=environment):
        return purge_mounted.remote(today, dry_run)


def main(argv: Sequence[str], *, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purge every Judge room from the keyframe-data Volume.")
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment (default {ENVIRONMENT})")
    parser.add_argument("--dry-run", action="store_true", help="list the Judge rooms that would go and delete nothing")
    args = parser.parse_args(argv)
    print(f"Modal Environment: {args.env}", flush=True)
    return run_remote(args.env, today=today or date.today(), dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
