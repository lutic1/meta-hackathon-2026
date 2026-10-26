"""SIT-14: one Dry run `chat` call on Meta at low over the 2.23 prompt, on a draft that passed `validate`, judged by the dryrun stage."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.schema import JobState
from src.infra.local import DiskArtifactStore
from src.pipeline.author import PUZZLES, puzzles_key, run_validate
from src.pipeline.build import new_id
from src.pipeline.dryrun import DRY_RUN_BUDGET_MS, DryRunError, run_dry_run
from src.pipeline.ingest import Upload, store_upload
from src.pipeline.segment import INTERACTABLES, interactables_key
from src.providers.meta_api import CHAT_MODEL
from tests.fixtures.rooms import write_fixtures

if TYPE_CHECKING:
    from scripts.sit import Sit

FIXTURE = "chat-dry-run"
"""Replayed offline by the dryrun stage tests."""
DRY_RUN_BUDGET_S = DRY_RUN_BUDGET_MS / 1000


def run(sit: Sit) -> str:
    """`CACHE=off`: the synthetic four-lock room's scenes, labels, clues and hints only; every answer must be reached."""
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        room, _ = write_fixtures(root / "scenes")  # synthetic scenes outside the repo; no room photo is sent
        artifacts = DiskArtifactStore(root / "rooms")
        scenes = [Path(photo.downscaled_path).read_bytes() for photo in room.photos]
        store_upload([Upload(scene, scene) for scene in scenes], room.id, artifacts)
        artifacts.put(interactables_key(room.id), INTERACTABLES.dump_json(room.interactables))
        artifacts.put(puzzles_key(room.id), PUZZLES.dump_json(room.puzzles))
        state = JobState(id=new_id("job"), status="running", stage="dryrun", room_id=room.id, regen_max=sit.settings.regen_max)
        assert all(v.passed for v in run_validate(state, artifacts=artifacts, ledger=sit.store).validator), "the draft must pass validate"
        provider = sit.meta("dryrun", DRY_RUN_BUDGET_S, cache=False)

        started = time.monotonic()
        try:
            result = run_dry_run(state, provider=provider, artifacts=artifacts, ledger=sit.store)
        except DryRunError as failure:
            raise AssertionError(
                f"reached {failure.result.count} of {len(failure.result.dry_run)} answers: {' '.join(failure.messages)}"
            ) from None
        latency = time.monotonic() - started
    sit.record(FIXTURE, model=CHAT_MODEL)
    usage = sit.transport.responses[-1][1].get("usage", {})
    overrun = f"; over the {DRY_RUN_BUDGET_S:.0f} s budget" if latency > DRY_RUN_BUDGET_S else ""
    return (
        f"reached {result.count} of {len(result.dry_run)} answers in {latency:.1f} s{overrun}; "
        f"{usage.get('prompt_tokens', '?')} in, {usage.get('completion_tokens', '?')} out"
    )
