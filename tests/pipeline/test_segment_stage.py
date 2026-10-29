"""Story 2.15: the segment stage fans out `sam-3.1`, selects in the domain, mints `ix_` ids and persists the Mask preview (AD-3, AD-7, AD-18)."""

import json
import re
import threading

import pytest

from src.domain import masks
from src.domain.masks import MAX_INTERACTABLES, box_polygon, box_to_frame
from src.domain.schema import Interactable, MaskPreview, StageRecord
from src.infra.clocks import BuildClock
from src.pipeline import segment as segment_module
from src.pipeline.architect import architect_key, architect_stage
from src.pipeline.build import STAGES, Build, StageStop
from src.pipeline.ingest import read_photos
from src.pipeline.segment import (
    MAX_IN_FLIGHT,
    MIN_INTERACTABLES,
    SEGMENT_BUDGET_MS,
    SEGMENT_MODEL,
    TooFewInteractables,
    frame_size,
    interactables_key,
    read_interactables,
)
from src.providers.base import ProviderError
from src.providers.mock import MockProvider, MockScript
from tests.pipeline.stages import GRID_BOX, Segmenter, architect_mock, build_over, candidate, labels, square
from tests.pipeline.test_build import Doubles, RunnerDied

IX = re.compile(r"ix_[0-9A-HJKMNP-TV-Z]{26}")
W, H = 1280, 960
"""Every synthetic upload but photo 2, which is 960 by 1280."""
BOX_PX = box_to_frame(GRID_BOX, W, H)  # (128, 96, 384, 288)
INSIDE = square(130, 100, 380, 285)
"""A mask inside the box: IoU with it well above 0.2, 69,375 px, over 1% of the frame."""
SECOND = square(140, 110, 370, 280)
TINY = square(200, 200, 210, 210)
"""100 px, under 1% of the frame and under a tenth of the 49,152 px box, so dropped."""


def _run(jobs, artifacts, ticker, doubles, uploads, candidates, segmenter):
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect_mock(candidates), segmenter=segmenter)
    return build.run(build.submit(uploads).id)


# --- The fan-out: one call per label on its clearest photo, at most 12 in flight ---


def test_one_segment_call_per_label_on_its_clearest_photo_never_more_than_12_in_flight(jobs, artifacts, ticker, doubles, uploads):
    candidates = labels(14, photo=lambda i: (i * 5) % 6)
    segmenter = Segmenter({c["label"]: [INSIDE] for c in candidates}, hold=MAX_IN_FLIGHT)
    done = _run(jobs, artifacts, ticker, doubles, uploads, candidates, segmenter)
    assert done.status == "done"
    photos = read_photos(done.room_id, artifacts)
    assert sorted(label for label, _ in segmenter.calls) == sorted(c["label"] for c in candidates)
    for label, image in segmenter.calls:
        clearest = next(c for c in candidates if c["label"] == label)["photo"]
        assert image == artifacts.read(photos[clearest].downscaled_path) == uploads[clearest].downscale
    assert segmenter.max_in_flight == MAX_IN_FLIGHT == 12 and len(segmenter.calls) == 14
    assert MAX_IN_FLIGHT == MAX_INTERACTABLES


def test_the_results_go_through_domain_masks(jobs, artifacts, ticker, doubles, uploads, monkeypatch):
    seen: list[tuple] = []
    real = masks.select_instances

    def spy(polygons, box, frame_w, frame_h, plural):
        seen.append((polygons, box, frame_w, frame_h, plural))
        return real(polygons, box, frame_w, frame_h, plural)

    monkeypatch.setattr(segment_module, "select_instances", spy)
    candidates = [
        candidate("lamp", photo=0, confidence=0.9),
        candidate("candles", photo=1, plural=True, confidence=0.8),
        candidate("mug", photo=3, confidence=0.7),
        candidate("rug", photo=4, confidence=0.6),
        candidate("poster", photo=2, box=(500, 500, 1000, 1000), confidence=0.5),
    ]
    segmenter = Segmenter({"lamp": [INSIDE, TINY], "candles": [INSIDE, SECOND], "mug": None, "rug": [TINY], "poster": [square(500, 700, 900, 1200)]})
    done = _run(jobs, artifacts, ticker, doubles, uploads, candidates, segmenter)
    assert done.status == "done"
    assert sorted((box, w, h, plural) for _, box, w, h, plural in seen) == sorted([
        (BOX_PX, W, H, False), (BOX_PX, W, H, True), (BOX_PX, W, H, False), (BOX_PX, W, H, False),
        (box_to_frame((500, 500, 1000, 1000), H, W), H, W, False),
    ])
    by_label = {ix.label: ix for ix in read_interactables(done.room_id, artifacts)}
    assert by_label["lamp"].polygons == [INSIDE] and by_label["lamp"].instances == 1
    assert by_label["candles"].polygons == [INSIDE, SECOND] and by_label["candles"].instances == 2
    assert by_label["mug"].polygons == [box_polygon(BOX_PX)] and by_label["rug"].polygons == [box_polygon(BOX_PX)]
    assert by_label["poster"].box == (480, 640, 960, 1280) and all(0 <= x <= 960 and 0 <= y <= 1280 for x, y in by_label["poster"].polygons[0])


def test_a_candidate_naming_no_stored_photo_is_dropped_before_any_call(jobs, artifacts, ticker, doubles, uploads):
    candidates = [*labels(5), candidate("ghost", photo=6, confidence=0.99)]
    segmenter = Segmenter({c["label"]: [INSIDE] for c in candidates})
    done = _run(jobs, artifacts, ticker, doubles, uploads, candidates, segmenter)
    assert done.status == "done" and "ghost" not in {label for label, _ in segmenter.calls}
    assert [ix.label for ix in read_interactables(done.room_id, artifacts)] == [c["label"] for c in labels(5)]


# --- A ProviderError after the adapter's retry ends the Build failed at segment ---


def test_a_provider_error_after_the_retry_ends_the_build_failed_at_segment_with_no_author_call(jobs, artifacts, ticker, doubles, uploads):
    candidates = labels(8)
    error = ProviderError(500, "server_error", "sam-3.1 failed twice")
    segmenter = Segmenter({c["label"]: [INSIDE] for c in candidates}, raises={"object 3": error})
    failed = _run(jobs, artifacts, ticker, doubles, uploads, candidates, segmenter)
    assert (failed.status, failed.stage) == ("failed", "segment")
    assert failed.error is not None and (failed.error.code, failed.error.stage, failed.error.message) == ("provider_error", "segment", str(error))
    assert doubles.calls == [] and [r.stage for r in failed.stages] == ["ingest", "architect"]
    assert failed.mask_preview == [] and [row.model for row in failed.calls] == ["muse-spark-1.3"]
    with pytest.raises(KeyError):
        read_interactables(failed.room_id, artifacts)
    assert jobs.read(failed.id) == failed


# --- Fewer than 5 survivors end the job needs_more_photos; 5 continue to author ---


def test_four_or_fewer_survivors_end_needs_more_photos_with_zero_authoring_calls(jobs, artifacts, ticker, doubles, uploads):
    candidates = labels(4)
    segmenter = Segmenter({c["label"]: [INSIDE] for c in candidates})
    ended = _run(jobs, artifacts, ticker, doubles, uploads, candidates, segmenter)
    assert (ended.status, ended.stage) == ("needs_more_photos", "segment")
    assert ended.error is not None and (ended.error.code, ended.error.stage) == ("too_few_interactables", "segment")
    assert "4 objects" in ended.error.message and "5" in ended.error.message
    assert doubles.calls == []  # no Riddler, dry-run or Trickster stage ran
    assert [r.stage for r in ended.stages] == ["ingest", "architect", "segment"]
    assert ended.stages[-1] == StageRecord(stage="segment", duration_ms=0, count=4, model="sam-3.1")
    assert [row.model for row in ended.calls] == ["muse-spark-1.3"] + ["sam-3.1"] * 4
    assert ended.mask_preview == [] and len(segmenter.calls) == 4
    with pytest.raises(KeyError):
        read_interactables(ended.room_id, artifacts)
    assert "ix_" not in artifacts.read(architect_key(ended.room_id)).decode()
    assert jobs.read(ended.id) == ended and issubclass(TooFewInteractables, StageStop) and MIN_INTERACTABLES == 5


def test_exactly_five_survivors_continue_to_author(jobs, artifacts, ticker, doubles, uploads):
    candidates = labels(5)
    done = _run(jobs, artifacts, ticker, doubles, uploads, candidates, Segmenter({c["label"]: [INSIDE] for c in candidates}))
    assert done.status == "done" and doubles.calls == ["author", "validate", "dryrun", "story", "scene"]
    assert len(doubles.seen["author"].mask_preview) == 5 and doubles.seen["author"].stages[-1].count == 5


def test_a_runner_resumed_at_segment_reads_the_stored_architect_response(jobs, artifacts, ticker, doubles, uploads):
    candidates = labels(6)
    doubles.raises["segment"] = RunnerDied()
    stages = doubles.stages()
    stages["architect"] = architect_stage(architect_mock(candidates), artifacts)
    first = Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=2)
    queued = first.submit(uploads)
    with pytest.raises(RunnerDied):
        first.run(queued.id)

    second_doubles = Doubles(ticker)
    architect = architect_mock([])  # never asked: the stored response is read instead
    segmenter = Segmenter({c["label"]: [INSIDE] for c in candidates})
    second = build_over(jobs, artifacts, ticker, second_doubles, architect=architect, segmenter=segmenter)
    done = second.run(queued.id)
    assert done.status == "done" and architect.calls == [] and len(segmenter.calls) == 6
    assert [r.stage for r in done.stages] == list(STAGES) and second_doubles.calls == ["author", "validate", "dryrun", "story", "scene"]


# --- Survivors: ix_ ids minted here, boxes in frame pixels, polygons, and the Mask preview ---


def test_survivors_after_selection_and_the_12_cap_get_ix_ids_boxes_in_frame_pixels_and_polygons(jobs, artifacts, ticker, doubles, uploads):
    candidates = [
        *labels(12, photo=lambda i: i % 6),
        candidate("dropped low", photo=0, confidence=0.1, attributes=["never kept"]),
        candidate("dropped lower", photo=1, confidence=0.05),
    ]
    candidates[3]["attributes"] = ["No. 7 ", "ÉCOLE"]
    segmenter = Segmenter({c["label"]: [INSIDE] for c in candidates})
    done = _run(jobs, artifacts, ticker, doubles, uploads, candidates, segmenter)
    assert len(segmenter.calls) == 14
    kept = read_interactables(done.room_id, artifacts)
    assert len(kept) == 12 == done.stages[2].count and [ix.label for ix in kept] == [c["label"] for c in candidates[:12]]
    assert all(IX.fullmatch(ix.id) for ix in kept) and len({ix.id for ix in kept}) == 12
    for ix, c in zip(kept, candidates[:12], strict=True):
        width, height = frame_size(uploads[c["photo"]].downscale)
        assert ix.photo == c["photo"] and ix.box == box_to_frame(tuple(c["box"]), width, height)
        assert ix.polygons == [INSIDE] and ix.instances == 1 and ix.tier2 is None
    assert kept[3].attributes == ["No. 7 ", "ÉCOLE"]
    raw = artifacts.read(interactables_key(done.room_id)).decode()
    assert "dropped low" not in raw and "never kept" not in raw and len(IX.findall(raw)) == 12
    assert "ix_" not in artifacts.read(architect_key(done.room_id)).decode()
    assert kept == [Interactable.model_validate(row) for row in json.loads(raw)]


def test_job_state_gains_the_solution_free_mask_preview_the_count_and_the_model_ids(jobs, artifacts, ticker, doubles, uploads):
    candidates = labels(7)
    done = _run(jobs, artifacts, ticker, doubles, uploads, candidates, Segmenter({c["label"]: [INSIDE] for c in candidates}))
    kept = read_interactables(done.room_id, artifacts)
    assert done.mask_preview == [MaskPreview(id=ix.id, label=ix.label, photo=ix.photo, polygons=ix.polygons) for ix in kept]
    assert set(MaskPreview.model_fields) == {"id", "label", "photo", "polygons"}
    assert all(preview.polygons for preview in done.mask_preview)
    serialized = done.model_dump_json()
    assert not any(key in serialized for key in ("solution", "puzzle", "clue", "attributes", "box"))
    assert [(r.stage, r.count, r.model) for r in done.stages[1:3]] == [("architect", 7, "muse-spark-1.3"), ("segment", 7, "sam-3.1")]
    assert [row.model for row in done.calls] == ["muse-spark-1.3"] + ["sam-3.1"] * 7
    assert all(row.role == "architect" and row.host == "mock" for row in done.calls)
    assert SEGMENT_MODEL == "sam-3.1" and jobs.read(done.id) == done
    assert doubles.seen["author"].mask_preview == done.mask_preview  # the preview is in job state before any authoring


# --- Timings from the build clock; budgets measured, never enforced ---


def test_both_durations_come_from_the_build_clock_and_a_slow_segment_still_completes(jobs, artifacts, ticker, doubles, uploads):
    assert SEGMENT_BUDGET_MS == 10_000
    candidates = labels(6)
    once = threading.Lock()
    advanced = False

    def slow() -> None:
        nonlocal advanced
        with once:
            if not advanced:
                advanced = True
                ticker.advance_ms(11_000)

    class SlowArchitect(MockProvider):
        def chat(self, *args, **kwargs):
            ticker.advance_ms(16_000)
            return super().chat(*args, **kwargs)

    architect = SlowArchitect("architect", MockScript(chat=[json.dumps({"candidates": candidates})]))
    segmenter = Segmenter({c["label"]: [INSIDE] for c in candidates}, on_call=slow)
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect, segmenter=segmenter)
    done = build.run(build.submit(uploads).id)
    assert done.status == "done" and done.error is None
    timings = {r.stage: r.duration_ms for r in done.stages}
    assert timings["architect"] == 16_000 and timings["segment"] == 11_000 > SEGMENT_BUDGET_MS
    assert done.build_time_ms == sum(timings.values())
