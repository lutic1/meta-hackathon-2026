#!/usr/bin/env python3
"""Write the wizard story onto a Demo room built before story mode, with the story stage's own code, on Modal (AD-6, AD-7, AD-9).

    uv run scripts/story_demo_room.py --room <room_id> --dry-run
    uv run scripts/story_demo_room.py --env main --room <room_id>

The first line printed is the Modal Environment. The run happens in one
short-lived container of its own app, as the purge's does: the image installs
`uv.lock`, sets `MODE=hosted` and `GUIDE=verbatim` as the hosted app's does,
mounts `keyframe-data` at `/data` and carries the `keyframe` Secret, so the
`storyteller` role's provider is built the way the hosted Build builds it
(`model_providers` over the hosted Cache and a `SpendLedger` on
`keyframe-ledger`): its call is cached, priced and recorded like any Build's,
each ledger row tagged with the job id of the room's `job.json` and the
`story` stage. The container's output is streamed back. The Demo room's calls
skip the Judge build's `cache-keys.json`, which lives under `rooms/judge/` and
only the Nov 10 purge reads.

The Room is read from `rooms/demo/<room_id>/room.json`; an id that is not a
Demo room, a Judge room included, or a Demo room without its `job.json`
exits 1 with no call made. The story comes from `tell_story`, the story
stage's path: the brief (`story_brief`), `build_story_prompt`, the line
rules with one retry over `build_story_retry_prompt`, and the fixed
templates as the last resort.

Both runs print, for each refused attempt, its fixed reasons by slot and
the refused line itself (the retry prompt still never quotes a line).
`--dry-run` prints the brief, every line by slot, the path that produced it
(model attempt 0 or 1, or the templates) and the spend, and writes nothing to
the room; its call is cached, so a real run after it costs nothing and keeps
the same lines. A real run sets `Room.story` in `room.json` (the Demo layout
keeps the story nowhere else: `story.json` is a Judge build's stage
artifact), reads it back, checks it parses as a Room with that story and
prints one line. `job.json`, the photos, the Sessions and the quota are never
touched. The Volume, Dicts and Secret are resolved in the Environment `--env`
names (default `main`), never the CLI's active one, and need a Modal token.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` and `scripts` import from any working directory

from scripts.purge_judge_rooms import TIMEOUT_S, UV_VERSION, open_handles
from scripts.seed_rooms import DEMO_PREFIX, ENVIRONMENT
from src.api.wiring import model_providers, spend_ledger
from src.config import Settings
from src.domain.schema import JobState, Room, RoomId, Story
from src.infra.modal import (
    JOB_FILE,
    MOUNT,
    VOLUME,
    ModalHandles,
    VolumeFiles,
    hosted_stores,
)
from src.pipeline.ports import room_key
from src.pipeline.story import Told, story_brief, tell_story
from src.providers.base import ModelProvider

if TYPE_CHECKING:
    import modal

APP_NAME = "keyframe-story"
"""The script's own short-lived app; it never deploys and shares nothing with `keyframe` but the named Dicts, Volume and Secret."""
SECRET = "keyframe"
"""The hosted app's one Secret (AD-14), which carries `MODEL_API_KEY` and `SPEND_CAP_USD`."""
HOSTED_ENV = {"MODE": "hosted", "GUIDE": "verbatim"}
"""What the hosted app's image sets, so `Settings` selects the hosted values here too."""
DEMO_DIR = DEMO_PREFIX.lstrip("/")
"""The Demo partition as a path under the Volume's mount."""


class StoryRefused(Exception):
    """A room the story cannot be written for; raised before any call or write."""


def storyteller(settings: Settings, handles: ModalHandles) -> ModelProvider:
    """The `storyteller` role's provider as the hosted Build builds it: over the hosted Cache and a `SpendLedger` on the hosted ledger."""
    stores = hosted_stores(handles)
    return model_providers(settings, stores.cache, spend_ledger(settings, stores.ledger))["storyteller"]


def demo_room(files: VolumeFiles, room_id: str) -> tuple[Room, JobState]:
    """The Demo room stored under `room_id` and its job record; anything else raises `StoryRefused`."""
    try:
        TypeAdapter(RoomId).validate_python(room_id)
    except ValidationError:
        raise StoryRefused(f"{room_id!r} is not a room id") from None
    try:
        room = Room.model_validate_json(files.read(f"{DEMO_DIR}/{room_key(room_id)}"))
    except (KeyError, ValueError):
        raise StoryRefused(f"{room_id}: no Demo room is stored under {DEMO_DIR}/") from None
    try:
        job = JobState.model_validate_json(files.read(f"{DEMO_DIR}/{room_id}/{JOB_FILE}"))
    except (KeyError, ValueError):
        raise StoryRefused(f"{room_id}: no job record is stored at {DEMO_DIR}/{room_id}/{JOB_FILE}") from None
    return room, job


def slot_lines(story: Story) -> list[str]:
    """Every line of the story under its slot's name, the riddles as `riddle n (<puzzle_id>) opening|solved`."""
    scalars = [f"{slot}: {text}" for slot, text in story.model_dump().items() if slot != "riddles"]
    riddles = [
        f"riddle {n} ({riddle.puzzle_id}) {part}: {text}"
        for n, riddle in enumerate(story.riddles, start=1)
        for part, text in (("opening", riddle.opening), ("solved", riddle.solved))
    ]
    return scalars + riddles


def refused_lines(told: Told) -> list[str]:
    """Each refused attempt's fixed reasons by slot, each beside the line it refused."""
    return [
        f"attempt {refused.attempt} refused: {reason}" + ("" if line is None else f' Line: "{line}"')
        for refused in told.refused
        for reason, line in refused.reasons
    ]


def path(told: Told) -> str:
    return "the fixed templates" if told.attempt is None else f"model attempt {told.attempt} ({told.model})"


def spend(told: Told) -> str:
    cached = sum(row.cached for row in told.calls)
    return f"${sum(row.spend_usd for row in told.calls):.4f} over {len(told.calls)} calls ({cached} cached)"


def story_demo_room(handles: ModalHandles, room_id: str, *, provider: ModelProvider, dry_run: bool) -> int:
    """Tell the Demo room's story and, unless `dry_run`, write it onto `room.json` and read it back; 1 on any refusal."""
    files = VolumeFiles(handles.volume, handles.root)
    try:
        room, job = demo_room(files, room_id)
    except StoryRefused as refusal:
        print(f"refused, nothing written: {refusal}", file=sys.stderr)
        return 1
    print(f"brief: {story_brief(room)}")
    told = tell_story(room, provider, job.id)
    for line in refused_lines(told):
        print(line)
    print("\n".join(slot_lines(told.story)))
    print(f"story from {path(told)}; spend {spend(told)}, ledger rows tagged {job.id} story")
    key = f"{DEMO_DIR}/{room_key(room.id)}"
    if dry_run:
        print(f"dry run: nothing written to {key}")
        return 0
    data = Room.model_validate({**room.model_dump(), "story": told.story.model_dump()}).model_dump_json().encode()
    files.write(key, data)
    try:
        back = files.read(key)
        stored = Room.model_validate_json(back)
    except (KeyError, ValueError):
        stored = None
    if stored is None or back != data or stored.story != told.story:
        print(f"refused: {room.id}: {key} does not read back as written", file=sys.stderr)
        return 1
    print(
        f"storied {room.id}: {len(slot_lines(told.story))} lines from {path(told)} on {key}, read back equal; "
        "job.json and the photos untouched"
    )
    return 0


def story_app(environment: str) -> tuple[modal.App, modal.Function]:
    """The script's app and its one function, which runs `story_demo_room` where `keyframe-data` from `environment` is mounted at `/data`; nothing is contacted until it runs."""
    import modal

    image = (
        modal.Image.debian_slim(python_version="3.13")
        .uv_sync(str(REPO), uv_version=UV_VERSION, extra_options="--no-dev")
        .env(HOSTED_ENV)
        .add_local_python_source("src", "scripts")
    )
    app = modal.App(APP_NAME, image=image)
    volume = modal.Volume.from_name(VOLUME, environment_name=environment)
    secret = modal.Secret.from_name(SECRET, environment_name=environment)

    @app.function(serialized=True, volumes={MOUNT.as_posix(): volume}, secrets=[secret], timeout=TIMEOUT_S)
    def story_mounted(room_id: str, dry_run: bool) -> int:
        handles = open_handles(environment)
        return story_demo_room(handles, room_id, provider=storyteller(Settings.from_env(), handles), dry_run=dry_run)

    return app, story_mounted


def run_remote(environment: str, *, room_id: str, dry_run: bool) -> int:
    """Run the story in its container, streaming its output here, and return its exit status."""
    import modal

    app, story_mounted = story_app(environment)
    with modal.enable_output(), app.run(environment_name=environment):
        return story_mounted.remote(room_id, dry_run)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Write the wizard story onto a Demo room on the keyframe-data Volume.")
    parser.add_argument("--room", required=True, metavar="ROOM_ID", help="the Demo room to write the story for")
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment (default {ENVIRONMENT})")
    parser.add_argument("--dry-run", action="store_true", help="print the brief, every line, its path and the spend; write nothing")
    args = parser.parse_args(argv)
    print(f"Modal Environment: {args.env}", flush=True)
    return run_remote(args.env, room_id=args.room, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
