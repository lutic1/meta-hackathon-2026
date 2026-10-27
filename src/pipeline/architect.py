"""The architect stage (AD-7): one vision call over the stored photos, its answer kept verbatim.

`run_architect` reads the ingest records, sends the 2.14 prompt once
through the `architect` role's port with every stored downscale as bytes
in upload order, and persists the `ArchitectResponse` as it came back
under `<room_id>/architect.json`: each candidate's clearest photo index,
grid box and attributes stay in list position, the attributes character
for character, and no id is minted here (AD-18). The stage records one
call row for the call from its receipt, cached or billed, with its ledger entry
tagged by job and stage (AD-16), and names its model id, `muse-spark-1.3`.
Its 15 s budget (`budgets.md`) is measured by the runner's stage timing
and never enforced: a slow call still completes.
"""

from __future__ import annotations

from src.council.architect import build_architect_prompt
from src.domain.schema import ArchitectResponse, JobState, RoomId
from src.pipeline.build import StageFn, StageResult, call_row
from src.pipeline.ingest import read_photos
from src.pipeline.ports import ArtifactStore
from src.providers.base import ModelProvider

ARCHITECT_MODEL = "muse-spark-1.3"
ARCHITECT_BUDGET_MS = 15_000
"""`budgets.md`: the Architect's 15 s, measured through the stage timing, never enforced."""
ARCHITECT_FILE = "architect.json"
"""The stage artifact under `<room_id>/`: the `ArchitectResponse` verbatim."""


def architect_key(room_id: RoomId) -> str:
    return f"{room_id}/{ARCHITECT_FILE}"


def read_architect(room_id: RoomId, artifacts: ArtifactStore) -> ArchitectResponse:
    """The `ArchitectResponse` the stage stored for `room_id`, for the segment stage."""
    return ArchitectResponse.model_validate_json(artifacts.read(architect_key(room_id)))


def run_architect(state: JobState, *, provider: ModelProvider, artifacts: ArtifactStore) -> StageResult:
    """One `chat` call over every stored photo; the response persisted verbatim, one call row, the candidate count."""
    if state.room_id is None:
        raise ValueError(f"{state.id} names no room")
    photos = [artifacts.read(photo.downscaled_path) for photo in read_photos(state.room_id, artifacts)]
    response, reply = build_architect_prompt(photos).send(provider, job_id=state.id, stage="architect")
    artifacts.put(architect_key(state.room_id), response.model_dump_json().encode())
    row = call_row(reply.receipt, provider, "architect", ARCHITECT_MODEL)
    return StageResult(count=len(response.candidates), model=ARCHITECT_MODEL, calls=[row])


def architect_stage(provider: ModelProvider, artifacts: ArtifactStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `architect`."""
    return lambda state: run_architect(state, provider=provider, artifacts=artifacts)
