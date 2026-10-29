"""The segment stage (AD-7, AD-18): one `sam-3.1` call per label, selection in the domain, the Mask preview.

`run_segment` reads the stored `ArchitectResponse` and issues one
`segment` call per candidate on that candidate's clearest photo through a
thread pool of at most 12 workers, so never more than 12 calls are in
flight; a candidate naming a photo index past the stored photos cannot be
segmented and is dropped. Each call's row comes from its receipt and its
ledger entry names the job and this stage (AD-16). A `ProviderError` from any call, after the
adapter's one retry, ends the Build failed at this stage (AD-13). The
results go through `domain/masks.py`: the grid box becomes frame pixels
of the stored downscale, the masks are selected against it (the box
rectangle when there is none, AD-11) and the candidates are capped at 12
by Architect confidence. Fewer than 5 survivors raise
`TooFewInteractables`, which ends the job `needs_more_photos` before any
authoring call. Otherwise each survivor gets an `ix_` id minted here, the
`Interactable` records are persisted under `<room_id>/interactables.json`
for the author stage, and the stage returns the solution-free Mask preview
(`id`, `label`, `photo`, `polygons`) for job state (AD-3). The 10 s budget
(`budgets.md`) is measured by the runner's stage timing, never enforced.

Photo areas (amended 29 Oct 2026, story mode): the stage copies the
Architect's `photos` answer onto the stored photo records the Room is built
from, each label trimmed and lowercased, once it names every photo exactly
once, at most `MAX_AREAS` areas of 1 to 24 characters and a pan of 0 or more;
on any failure every photo gets area "room" and no pan, one ring in upload
order. No heuristic stands in for the Architect's answer.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from PIL import Image
from pydantic import TypeAdapter

from src.domain.masks import MAX_INTERACTABLES, Selection, box_to_frame, cap_by_confidence, select_instances
from src.domain.schema import (
    DEFAULT_AREA,
    ArchitectCandidate,
    ArchitectPhoto,
    Interactable,
    JobState,
    JobStatus,
    MaskPreview,
    Photo,
    Polygon,
    RoomId,
)
from src.pipeline.architect import read_architect
from src.pipeline.build import StageFn, StageResult, StageStop, call_row, new_id
from src.pipeline.ingest import PHOTOS, PHOTOS_FILE, read_photos
from src.pipeline.ports import ArtifactStore
from src.providers.base import ModelProvider

SEGMENT_MODEL = "sam-3.1"
SEGMENT_BUDGET_MS = 10_000
"""`budgets.md`: the segment stage's 10 s, measured through the stage timing, never enforced."""
MAX_IN_FLIGHT = MAX_INTERACTABLES
"""The thread pool's size: at most 12 `segment` calls in flight (AD-7)."""
MIN_INTERACTABLES = 5
"""Fewer survivors end the job `needs_more_photos`: four to six puzzles need that many distinct objects."""
INTERACTABLES_FILE = "interactables.json"
"""The stage artifact under `<room_id>/`: the surviving `Interactable` records, ids minted."""
INTERACTABLES = TypeAdapter(list[Interactable])
MAX_AREAS = 4
"""At most this many areas in one Room; an Architect answer naming more falls back to the one area."""
AREA_LENGTH = range(1, 25)


class TooFewInteractables(StageStop):
    """Fewer than 5 Interactables survived selection (AD-7, AD-13): the job ends `needs_more_photos`, not `failed`."""

    status: JobStatus = "needs_more_photos"


def interactables_key(room_id: RoomId) -> str:
    return f"{room_id}/{INTERACTABLES_FILE}"


def read_interactables(room_id: RoomId, artifacts: ArtifactStore) -> list[Interactable]:
    """The `Interactable` records the stage stored for `room_id`, for the author stage."""
    return INTERACTABLES.validate_json(artifacts.read(interactables_key(room_id)))


def photo_areas(photos: list[Photo], answer: list[ArchitectPhoto]) -> list[Photo]:
    """Each photo with the area and pan the Architect gave it; on any gap, every photo in area "room" with no pan."""
    named = {entry.photo: (entry.area.strip().lower(), entry.pan) for entry in answer}
    fits = (
        len(answer) == len(photos)
        and set(named) == set(range(len(photos)))
        and len({area for area, _ in named.values()}) <= MAX_AREAS
        and all(len(area) in AREA_LENGTH and pan >= 0 for area, pan in named.values())
    )
    if not fits:
        return [photo.model_copy(update={"area": DEFAULT_AREA, "pan": None}) for photo in photos]
    return [photo.model_copy(update={"area": named[i][0], "pan": named[i][1]}) for i, photo in enumerate(photos)]


def frame_size(jpeg: bytes) -> tuple[int, int]:
    """Width and height of a stored downscale, from its header."""
    return Image.open(BytesIO(jpeg)).size


def run_segment(state: JobState, *, provider: ModelProvider, artifacts: ArtifactStore) -> StageResult:
    """One `segment` call per candidate, at most 12 in flight; selection, the 12 cap, the `ix_` ids and the Mask preview."""
    if state.room_id is None:
        raise ValueError(f"{state.id} names no room")
    photos = read_photos(state.room_id, artifacts)
    architect = read_architect(state.room_id, artifacts)
    artifacts.put(f"{state.room_id}/{PHOTOS_FILE}", PHOTOS.dump_json(photo_areas(photos, architect.photos)))
    candidates = [c for c in architect.candidates if c.photo < len(photos)]
    frames = {index: artifacts.read(photos[index].downscaled_path) for index in {c.photo for c in candidates}}
    sizes = {index: frame_size(jpeg) for index, jpeg in frames.items()}

    with ThreadPoolExecutor(max_workers=MAX_IN_FLIGHT) as pool:
        replies = list(pool.map(lambda c: provider.segment(c.label, frames[c.photo], job_id=state.id, stage="segment"), candidates))
    calls = [call_row(reply.receipt, provider, "architect", SEGMENT_MODEL) for reply in replies]

    selected = [_select(candidate, reply.polygons, sizes[candidate.photo]) for candidate, reply in zip(candidates, replies, strict=True)]
    kept = cap_by_confidence(selected, lambda pair: pair[0].confidence)
    if len(kept) < MIN_INTERACTABLES:
        result = StageResult(count=len(kept), model=SEGMENT_MODEL, calls=calls)
        raise TooFewInteractables(f"{len(kept)} objects survived selection; Keyframe needs {MIN_INTERACTABLES}", result)

    interactables = [
        Interactable(
            id=new_id("ix"),
            label=candidate.label,
            photo=candidate.photo,
            box=box_to_frame(candidate.box, *sizes[candidate.photo]),
            polygons=selection.polygons,
            instances=selection.instances,
            attributes=candidate.attributes,
        )
        for candidate, selection in kept
    ]
    artifacts.put(interactables_key(state.room_id), INTERACTABLES.dump_json(interactables))
    preview = [MaskPreview(id=ix.id, label=ix.label, photo=ix.photo, polygons=ix.polygons or []) for ix in interactables]
    return StageResult(count=len(interactables), model=SEGMENT_MODEL, calls=calls, mask_preview=preview)


def _select(candidate: ArchitectCandidate, polygons: list[Polygon] | None, size: tuple[int, int]) -> tuple[ArchitectCandidate, Selection]:
    width, height = size
    return candidate, select_instances(polygons, box_to_frame(candidate.box, width, height), width, height, candidate.plural)


def segment_stage(provider: ModelProvider, artifacts: ArtifactStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `segment`."""
    return lambda state: run_segment(state, provider=provider, artifacts=artifacts)
