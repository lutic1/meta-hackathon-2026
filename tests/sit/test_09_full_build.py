"""SIT-03: a full live Build through `POST /builds` with `CACHE=off`, polled on `GET /builds/<job_id>` to a terminal status: it ends `done`."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from src.api.app import DOWNSCALE, ORIGINAL, create_app
from src.api.wiring import ROLE_CALLS, artifact_store, build_stages
from src.domain.schema import JobState, Role, Stage
from src.infra.local import LEDGER_PATH
from src.pipeline.architect import ARCHITECT_BUDGET_MS
from src.pipeline.author import RIDDLER_BUDGET_MS
from src.pipeline.dryrun import DRY_RUN_BUDGET_MS
from src.pipeline.ingest import MIN_PHOTOS
from src.pipeline.scene import SCENE_BUDGET_MS
from src.pipeline.segment import SEGMENT_BUDGET_MS
from src.providers.base import ModelProvider
from src.providers.verbatim import VerbatimPhraser

if TYPE_CHECKING:
    from scripts.sit import Sit

BUILD_ROLES: tuple[Role, ...] = ("architect", "riddler", "dryrun")
"""The council roles a Build calls; the Trickster and the image role never run in one."""
BUDGETS_MS: dict[Stage, int] = {
    "architect": ARCHITECT_BUDGET_MS,
    "segment": SEGMENT_BUDGET_MS,
    "author": RIDDLER_BUDGET_MS,
    "dryrun": DRY_RUN_BUDGET_MS,
    "scene": SCENE_BUDGET_MS,
}
"""`budgets.md`, per stage run; an overrun is noted, never a fail (NFR-1)."""
TOTAL_BUDGET_MS = 110_000
CAPTURE_TARGET_MS = 120_000
"""The Capture target; a Build over it is logged as an NFR-1 miss (2.26 may re-base it)."""
POLL_S = 0.5
TIMEOUT_S = 600.0


def poll(client: TestClient, job_id: str) -> JobState:
    """`GET /builds/<job_id>` until it answers 200, the terminal status; 202 while `queued` or `running`."""
    deadline = time.monotonic() + TIMEOUT_S
    while (response := client.get(f"/api/builds/{job_id}")).status_code == 202:
        if time.monotonic() > deadline:
            raise TimeoutError(f"{job_id} still {response.json()['status']} after {TIMEOUT_S:.0f} s")
        time.sleep(POLL_S)
    assert response.status_code == 200, response.text
    return JobState.model_validate(response.json())


def run(sit: Sit) -> str:
    """Six own room photos from `photos/`, the wired stages on Meta with no cache, the real ledger; `DRY_RUN` as configured."""
    uploads = list(zip(sit.photos(MIN_PHOTOS), sit.originals(MIN_PHOTOS), strict=True))
    providers: dict[Role, ModelProvider] = {role: sit.meta(*ROLE_CALLS[role], cache=False) for role in BUILD_ROLES}
    dry_run = sit.settings.dry_run == "on"
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        stages = build_stages(providers, artifact_store(root / "rooms"), sit.store, dry_run=dry_run)
        app = create_app(
            sit.settings,
            rooms_root=root / "rooms",
            web_dist=root / "web",
            phraser=VerbatimPhraser(),
            stages=stages,
            ledger_path=sit.root / LEDGER_PATH,
            exports_root=root / "exports",
            cache_root=root / "cache",
        )
        files = [
            (name, (f"{i}.jpg", data, "image/jpeg"))
            for i, pair in enumerate(uploads)
            for name, data in zip((DOWNSCALE, ORIGINAL), pair, strict=True)
        ]
        with TestClient(app) as client:
            accepted = client.post("/api/builds", files=files)
            assert accepted.status_code == 202, accepted.text
            state = poll(client, accepted.json()["id"])

    error = f" ({state.error.code}: {state.error.message})" if state.error else ""
    assert state.status == "done", f"ended {state.status} at {state.stage}{error}; sent back {[s.messages for s in state.sent_back]}"
    assert all(verdict.passed for verdict in state.validator), "the Room passed without every Validator rule"
    if dry_run:
        assert {verdict.verdict for verdict in state.dry_run} == {"pass"}, "the Room passed without reaching every answer"
    overruns = [
        f"{record.stage} {record.duration_ms / 1000:.1f} s"
        for record in state.stages
        if record.stage in BUDGETS_MS and record.duration_ms > BUDGETS_MS[record.stage]
    ]
    total = state.build_time_ms or 0
    passes = sum(verdict.verdict == "pass" for verdict in state.dry_run)
    notes = [
        f"done in {total / 1000:.1f} s against {TOTAL_BUDGET_MS / 1000:.0f} s",
        f"reached {passes} of {len(state.dry_run)} answers" if dry_run else "Dry run skipped (cut 4)",
        f"{state.regeneration_count} of {state.regen_max} regenerations",
        f"over budget: {', '.join(overruns)}" if overruns else "every stage within budget",
    ]
    if total > CAPTURE_TARGET_MS:
        notes.append(f"NFR-1 miss: over the {CAPTURE_TARGET_MS / 1000:.0f} s Capture target")
    return "; ".join(notes)
