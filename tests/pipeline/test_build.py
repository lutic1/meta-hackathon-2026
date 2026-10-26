"""Story 2.10: the Build runs as a persisted, resumable stage job over `JobStore`, `ArtifactStore` and the build clock (AD-7, AD-10, AD-13, AD-16)."""

import inspect
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import get_args

import pytest

from src.config import Settings
from src.domain.ledger import SpendCapExceeded
from src.domain.schema import (
    CallRow,
    JobId,
    JobState,
    JobStatus,
    MaskPreview,
    Room,
    SentBack,
    Stage,
    StageRecord,
)
from src.infra.clocks import BuildClock
from src.pipeline.build import STAGES, TERMINAL, Build, StageResult, StageStop, error_code, new_id
from src.pipeline.ingest import IngestRefused, photo_keys, read_photos
from src.pipeline.ports import ArtifactStore, BuildQuotaExceeded, Clock, JobStore
from src.providers.base import ProviderError
from tests.infra.test_clocks import Ticker
from tests.pipeline.uploads import make_uploads

REPO = Path(__file__).resolve().parents[2]
AFTER_INGEST: tuple[Stage, ...] = STAGES[1:]
ARCHITECT_ROW = CallRow(id=new_id("call"), role="architect", model="muse-spark-1.3", host="api.meta.ai", cached=False, spend_usd=0.03)
SENT_BACK = SentBack(attempt=0, stage="validate", messages=["Rule 5: the clue names its answer."])


class MemoryJobStore:
    """`JobStore` over serialized state, so every read comes back through JSON like a store on disk would."""

    def __init__(self) -> None:
        self.rows: dict[str, bytes] = {}
        self.writes: list[JobState] = []
        self.reads = 0

    def put(self, state: JobState) -> None:
        self.rows[state.id] = state.model_dump_json().encode()
        self.writes.append(state)

    def read(self, job_id: JobId) -> JobState:
        if job_id not in self.rows:
            raise KeyError(job_id)
        self.reads += 1
        return JobState.model_validate_json(self.rows[job_id])

    def list_ids(self) -> list[JobId]:
        return sorted(self.rows)

    def reserve_build(self, job_id: JobId) -> None:
        """No quota here: every claim is accepted and nothing is written."""

    def builds_left(self) -> int | None:
        return None


class RunnerDied(BaseException):
    """Not an `Exception`: the process stopped mid-stage, and no stage handler saw it."""


class Doubles:
    """One test double per stage after ingest, each recording the job state it was given."""

    def __init__(self, ticker: Ticker, *, advance_ms: int = 1_000) -> None:
        self.ticker = ticker
        self.advance_ms = advance_ms
        self.calls: list[Stage] = []
        self.seen: dict[Stage, JobState] = {}
        self.results: dict[Stage, StageResult] = {}
        self.raises: dict[Stage, BaseException] = {}
        self.hooks: dict[Stage, Callable[[JobState], None]] = {}

    def _stage(self, stage: Stage) -> Callable[[JobState], StageResult]:
        def run(state: JobState) -> StageResult:
            self.calls.append(stage)
            self.seen[stage] = state
            if stage in self.hooks:
                self.hooks[stage](state)
            self.ticker.advance_ms(self.advance_ms)
            if stage in self.raises:
                raise self.raises[stage]
            return self.results.get(stage, StageResult())
        return run

    def stages(self) -> dict[Stage, Callable[[JobState], StageResult]]:
        return {stage: self._stage(stage) for stage in AFTER_INGEST}


def _build(jobs, artifacts, ticker, doubles, *, regen_max: int = 2) -> Build:
    return Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=doubles.stages(), regen_max=regen_max)


def _lines(caplog, job_id: str) -> list[dict]:
    lines = [json.loads(record.getMessage()) for record in caplog.records if record.name == "src.pipeline.build"]
    return [line for line in lines if line["job_id"] == job_id]


# --- The stage order, persistence after each stage, and what job state carries ---


def test_the_stages_run_in_order_and_the_job_ends_done(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    queued = build.submit(uploads)
    assert re.fullmatch(r"job_[0-9A-HJKMNP-TV-Z]{26}", queued.id) and re.fullmatch(r"room_[0-9A-HJKMNP-TV-Z]{26}", queued.room_id)
    assert queued.status == "queued" and queued.stage is None and doubles.calls == []
    done = build.run(queued.id)
    assert doubles.calls == list(AFTER_INGEST)
    assert [record.stage for record in done.stages] == list(STAGES) == [
        "ingest", "architect", "segment", "author", "validate", "dryrun", "scene",
    ]
    assert done.status == "done" and done.stage is None and done.error is None
    assert jobs.read(queued.id) == done


def test_the_stage_literal_lists_the_same_seven_stages():
    assert set(STAGES) == set(get_args(Stage)) and len(STAGES) == 7


def test_job_state_is_persisted_through_the_store_after_every_stage(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    queued = build.submit(uploads)
    assert jobs.read(queued.id) == queued and [record.stage for record in queued.stages] == ["ingest"]
    for stage in AFTER_INGEST:
        def check(state: JobState, stage: Stage = stage) -> None:
            stored = jobs.read(state.id)
            assert stored == state and stored.status == "running" and stored.stage == stage
            assert [record.stage for record in stored.stages] == list(STAGES[: STAGES.index(stage)])
        doubles.hooks[stage] = check
    build.run(queued.id)
    persisted = [[record.stage for record in state.stages] for state in jobs.writes]
    assert persisted[-1] == list(STAGES)
    assert [stages[-1] for stages in persisted if stages] == sorted(
        [stages[-1] for stages in persisted if stages], key=STAGES.index
    )


def test_ingest_persists_the_photos_as_stage_artifacts_under_the_room(jobs, artifacts, ticker, doubles, uploads, tmp_path):
    build = _build(jobs, artifacts, ticker, doubles)
    queued = build.submit(uploads)
    photos = read_photos(queued.room_id, artifacts)
    assert len(photos) == 6 and queued.stages[0] == StageRecord(stage="ingest", duration_ms=0, count=6, model=None)
    for index, upload in enumerate(uploads):
        downscaled_path, original_path = photo_keys(queued.room_id, index)
        assert (tmp_path / "rooms" / downscaled_path).read_bytes() == upload.downscale
        assert (tmp_path / "rooms" / original_path).read_bytes() == upload.original
        assert photos[index].downscaled_path == downscaled_path
    doubles.hooks["architect"] = lambda state: artifacts.read(read_photos(state.room_id, artifacts)[0].downscaled_path)
    build.run(queued.id)


def test_each_stage_timing_comes_from_the_build_clock(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    doubles.advance_ms = 0
    expected = {"architect": 12_345, "segment": 9_000, "author": 30_000, "validate": 2, "dryrun": 25_000, "scene": 7}
    for stage, ms in expected.items():
        doubles.hooks[stage] = lambda _state, ms=ms: ticker.advance_ms(ms)
    done = build.run(build.submit(uploads).id)
    assert {record.stage: record.duration_ms for record in done.stages[1:]} == expected
    assert done.build_time_ms == sum(expected.values()) + done.stages[0].duration_ms


def test_job_state_carries_counts_model_ids_call_rows_and_the_build_time(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    sam_row = CallRow(id=new_id("call"), role="architect", model="sam-3.1", host="api.meta.ai", cached=True, spend_usd=0.0)
    riddler_row = CallRow(id=new_id("call"), role="riddler", model="muse-spark-1.3", host="api.meta.ai", cached=False, spend_usd=0.03)
    doubles.results = {
        "architect": StageResult(count=9, model="muse-spark-1.3", calls=[ARCHITECT_ROW]),
        "segment": StageResult(count=9, model="sam-3.1", calls=[sam_row]),
        "author": StageResult(count=5, model="muse-spark-1.3", calls=[riddler_row]),
        "validate": StageResult(count=8),
        "dryrun": StageResult(count=5, model="muse-spark-1.3"),
        "scene": StageResult(count=1),
    }
    done = build.run(build.submit(uploads).id)
    assert [(r.stage, r.count, r.model) for r in done.stages] == [
        ("ingest", 6, None), ("architect", 9, "muse-spark-1.3"), ("segment", 9, "sam-3.1"), ("author", 5, "muse-spark-1.3"),
        ("validate", 8, None), ("dryrun", 5, "muse-spark-1.3"), ("scene", 1, None),
    ]
    assert done.calls == [ARCHITECT_ROW, sam_row, riddler_row]
    assert done.sent_back == []  # the regeneration loop is its only writer
    assert done.build_time_ms == sum(record.duration_ms for record in done.stages) == 6_000
    assert done.regen_max == 2 and done.regeneration_count == 0


def test_demo_timescale_6_leaves_every_timing_unchanged(jobs, artifacts, ticker, doubles, uploads, monkeypatch):
    monkeypatch.setenv("DEMO_TIMESCALE", "6")
    assert Settings.from_env().demo_timescale == 6
    build = _build(jobs, artifacts, ticker, doubles)
    doubles.advance_ms = 90_000
    done = build.run(build.submit(uploads).id)
    assert all(record.duration_ms == 90_000 for record in done.stages[1:])
    assert done.build_time_ms == 6 * 90_000 + done.stages[0].duration_ms
    code = (REPO / "src" / "pipeline" / "build.py").read_text().split('"""', 2)[2]  # past the module docstring
    assert "timescale" not in code.lower() and "Settings" not in code
    assert "timescale" not in inspect.signature(Build).parameters


# --- A restarted runner resumes at the last persisted stage ---


def test_a_new_runner_resumes_at_segment_and_never_repeats_the_architect_call(jobs, artifacts, ticker, doubles, uploads):
    first = _build(jobs, artifacts, ticker, doubles)
    doubles.results["architect"] = StageResult(count=9, model="muse-spark-1.3", calls=[ARCHITECT_ROW])
    doubles.raises["segment"] = RunnerDied()
    queued = first.submit(uploads)
    with pytest.raises(RunnerDied):
        first.run(queued.id)
    left = jobs.read(queued.id)
    assert left.status == "running" and left.stage == "segment"
    assert [record.stage for record in left.stages] == ["ingest", "architect"] and left.calls == [ARCHITECT_ROW]
    assert doubles.calls == ["architect", "segment"]

    second_doubles = Doubles(ticker)
    second = _build(jobs, artifacts, ticker, second_doubles)
    done = second.run(queued.id)
    assert second_doubles.calls == ["segment", "author", "validate", "dryrun", "scene"]
    assert second_doubles.seen["segment"] == left.model_copy(update={"status": "running", "stage": "segment"})
    assert done.status == "done" and done.calls == [ARCHITECT_ROW]
    assert [record.stage for record in done.stages] == list(STAGES)


def test_the_runner_rereads_job_state_from_the_store_on_entry(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    queued = build.submit(uploads)
    architect = StageRecord(stage="architect", duration_ms=4_000, count=9, model="muse-spark-1.3")
    author = StageRecord(stage="author", duration_ms=20_000, count=5, model="muse-spark-1.3")
    segment = StageRecord(stage="segment", duration_ms=3_000, count=9, model="sam-3.1")
    edited = queued.model_copy(update={"status": "running", "stage": "validate", "stages": [*queued.stages, architect, segment, author]})
    jobs.put(edited)
    done = build.run(queued.id)
    assert doubles.calls == ["validate", "dryrun", "scene"]
    assert [record.stage for record in done.stages] == list(STAGES) and done.stages[1:4] == [architect, segment, author]


def test_every_stage_rereads_job_state_from_the_store_before_it_runs(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    queued = build.submit(uploads)
    jobs.reads = 0
    for stage in AFTER_INGEST:
        def check(state: JobState, stage: Stage = stage) -> None:
            assert jobs.reads == STAGES.index(stage) and state == JobState.model_validate_json(jobs.rows[state.id])
        doubles.hooks[stage] = check
    build.run(queued.id)
    assert jobs.reads == len(STAGES)  # one read before each stage after ingest, and one that finds scene finished


@pytest.mark.parametrize("status", sorted(TERMINAL))
def test_a_terminal_job_is_left_as_it_is(jobs, artifacts, ticker, doubles, uploads, status):
    build = _build(jobs, artifacts, ticker, doubles)
    queued = build.submit(uploads)
    terminal = queued.model_copy(update={"status": status})
    jobs.put(terminal)
    assert build.run(queued.id) == terminal and doubles.calls == [] and jobs.read(queued.id) == terminal


def test_an_unknown_job_raises_key_error(jobs, artifacts, ticker, doubles):
    with pytest.raises(KeyError):
        _build(jobs, artifacts, ticker, doubles).run("job_01ARZ3NDEKTSV4RRFFQ69G5FAV")


# --- Status through the runner, and typed errors ending the job failed ---


def test_status_is_queued_then_running_with_the_stage_then_done(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    queued = build.submit(uploads)
    assert (queued.status, queued.stage) == ("queued", None) and jobs.read(queued.id).status == "queued"
    for stage in AFTER_INGEST:
        def check(state: JobState, stage: Stage = stage) -> None:
            stored = jobs.read(state.id)
            assert (stored.status, stored.stage) == ("running", stage)
        doubles.hooks[stage] = check
    done = build.run(queued.id)
    assert (done.status, done.stage) == ("done", None)
    assert [(state.status, state.stage) for state in jobs.writes[-3:]] == [("running", "scene"), ("running", "scene"), ("done", None)]


def test_the_runner_sets_neither_needs_more_photos_nor_needs_recapture():
    source = (REPO / "src" / "pipeline" / "build.py").read_text()
    assert "needs_more_photos" not in source and "needs_recapture" not in source
    assert TERMINAL == {"done", "failed", "needs_more_photos", "needs_recapture"}
    assert set(get_args(JobStatus)) == TERMINAL | {"queued", "running"}


@pytest.mark.parametrize(("stage", "exc", "code"), [
    ("architect", SpendCapExceeded(60.0, 59.99), "spend_cap_exceeded"),
    ("segment", ProviderError(500, "server_error", "sam-3.1 failed twice"), "provider_error"),
    ("scene", ValueError("room already written"), "value_error"),
])
def test_an_error_raised_by_a_stage_ends_the_job_failed_with_its_stage_and_code(jobs, artifacts, ticker, doubles, uploads, stage, exc, code):
    build = _build(jobs, artifacts, ticker, doubles)
    doubles.raises[stage] = exc
    failed = build.run(build.submit(uploads).id)
    assert (failed.status, failed.stage) == ("failed", stage)
    assert failed.error is not None and (failed.error.code, failed.error.stage) == (code, stage) and failed.error.message == str(exc)
    assert doubles.calls == list(STAGES[1 : STAGES.index(stage) + 1])
    assert [record.stage for record in failed.stages] == list(STAGES[: STAGES.index(stage)])
    assert jobs.read(failed.id) == failed


def test_error_codes_are_the_class_names_in_snake_case_or_the_refusal_codes():
    assert error_code(SpendCapExceeded(1.0, 2.0)) == "spend_cap_exceeded"
    assert error_code(ProviderError(None, "timeout", "no reply")) == "provider_error"
    assert error_code(IngestRefused("photo_count", "")) == "photo_count"
    assert error_code(IngestRefused("bad_downscale", "")) == "bad_downscale"


def test_a_refused_upload_creates_and_queues_no_job_and_stores_nothing(jobs, artifacts, ticker, doubles, tmp_path):
    build = _build(jobs, artifacts, ticker, doubles)
    with pytest.raises(IngestRefused) as info:
        build.submit(make_uploads(5))
    assert info.value.code == "photo_count"
    assert jobs.list_ids() == [] and jobs.writes == [] and doubles.calls == []
    assert not (tmp_path / "rooms").exists()


# --- The build slot: claimed after the ingest checks, before the first photo write (7.11) ---


class OrderedArtifacts:
    """An `ArtifactStore` over disk that logs each `put` into a shared log."""

    def __init__(self, inner: ArtifactStore, log: list[str]) -> None:
        self.inner, self.log = inner, log

    def put(self, key: str, data: bytes) -> None:
        self.log.append(f"put {key}")
        self.inner.put(key, data)

    def read(self, key: str) -> bytes:
        return self.inner.read(key)

    def list_rooms(self) -> list[Room]:
        return self.inner.list_rooms()


class QuotaJobStore(MemoryJobStore):
    """`MemoryJobStore` with `left` build slots, logging each claim into a shared log."""

    def __init__(self, log: list[str], left: int) -> None:
        super().__init__()
        self.log, self.left = log, left

    def reserve_build(self, job_id: JobId) -> None:
        if self.left == 0:
            raise BuildQuotaExceeded(20)
        self.left -= 1
        self.log.append(f"claim {job_id}")


def test_the_slot_is_claimed_for_the_job_before_the_first_photo_write(artifacts, ticker, doubles, uploads):
    log: list[str] = []
    jobs = QuotaJobStore(log, left=1)
    queued = _build(jobs, OrderedArtifacts(artifacts, log), ticker, doubles).submit(uploads)
    assert log[0] == f"claim {queued.id}" and log[1].startswith(f"put {queued.room_id}/") and jobs.left == 0


def test_a_refused_upload_claims_no_slot(artifacts, ticker, doubles, tmp_path):
    log: list[str] = []
    jobs = QuotaJobStore(log, left=1)
    with pytest.raises(IngestRefused):
        _build(jobs, OrderedArtifacts(artifacts, log), ticker, doubles).submit(make_uploads(11))
    assert log == [] and jobs.left == 1 and jobs.writes == []


def test_a_refused_claim_stores_no_photo_and_creates_no_job(artifacts, ticker, doubles, uploads, tmp_path):
    log: list[str] = []
    jobs = QuotaJobStore(log, left=0)
    with pytest.raises(BuildQuotaExceeded):
        _build(jobs, OrderedArtifacts(artifacts, log), ticker, doubles).submit(uploads)
    assert log == [] and jobs.writes == [] and doubles.calls == [] and not (tmp_path / "rooms").exists()


# --- One JSON log line per stage ---


def test_each_stage_writes_exactly_one_json_log_line(jobs, artifacts, ticker, doubles, uploads, caplog):
    caplog.set_level(logging.INFO, logger="src.pipeline.build")
    build = _build(jobs, artifacts, ticker, doubles)
    doubles.results["architect"] = StageResult(count=9, model="muse-spark-1.3", calls=[ARCHITECT_ROW])
    doubles.advance_ms = 2_500
    done = build.run(build.submit(uploads).id)
    lines = _lines(caplog, done.id)
    assert [line["stage"] for line in lines] == list(STAGES)
    assert all(set(line) == {"job_id", "stage", "duration_ms", "spend_usd"} for line in lines)
    assert [line["duration_ms"] for line in lines] == [0] + [2_500] * 6
    assert [line["spend_usd"] for line in lines] == [0.0, 0.03, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_a_failed_stage_logs_its_one_line_with_the_code(jobs, artifacts, ticker, doubles, uploads, caplog):
    caplog.set_level(logging.INFO, logger="src.pipeline.build")
    build = _build(jobs, artifacts, ticker, doubles)
    doubles.raises["author"] = SpendCapExceeded(60.0, 59.99)
    failed = build.run(build.submit(uploads).id)
    lines = _lines(caplog, failed.id)
    assert [line["stage"] for line in lines] == ["ingest", "architect", "segment", "author"]
    assert lines[-1] == {"job_id": failed.id, "stage": "author", "duration_ms": 1_000, "spend_usd": 0.0, "code": "spend_cap_exceeded"}


# --- The runner is built only over the ports ---


def test_the_build_takes_the_job_store_the_clock_and_every_stage_after_ingest(jobs, artifacts, ticker):
    parameters = inspect.signature(Build, eval_str=True).parameters
    assert parameters["jobs"].annotation is JobStore and parameters["clock"].annotation is Clock
    assert parameters["artifacts"].annotation is ArtifactStore
    with pytest.raises(ValueError, match="scene"):
        Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages={}, regen_max=2)
    assert jobs.list_ids() == []


# --- A stage's own stop, and the mask preview a stage returns ---


class Recapture(StageStop):
    status = "needs_recapture"


def test_a_stage_stop_ends_the_job_in_the_stages_status_keeping_its_record_and_calls(jobs, artifacts, ticker, doubles, uploads, caplog):
    caplog.set_level(logging.INFO, logger="src.pipeline.build")
    build = _build(jobs, artifacts, ticker, doubles)
    doubles.raises["validate"] = Recapture("rule 5 failed twice", StageResult(count=3, calls=[ARCHITECT_ROW]))
    ended = build.run(build.submit(uploads).id)
    assert (ended.status, ended.stage) == ("needs_recapture", "validate")
    assert ended.error is not None and (ended.error.code, ended.error.message, ended.error.stage) == ("recapture", "rule 5 failed twice", "validate")
    assert doubles.calls == ["architect", "segment", "author", "validate"]
    assert ended.stages[-1] == StageRecord(stage="validate", duration_ms=1_000, count=3, model=None)
    assert ended.calls == [ARCHITECT_ROW] and ended.build_time_ms == 4_000
    assert jobs.read(ended.id) == ended and build.run(ended.id) == ended and doubles.calls[-1] == "validate"
    assert _lines(caplog, ended.id)[-1] == {"job_id": ended.id, "stage": "validate", "duration_ms": 1_000, "spend_usd": 0.03, "code": "recapture"}


def test_the_mask_preview_a_stage_returns_is_persisted_into_job_state(jobs, artifacts, ticker, doubles, uploads):
    build = _build(jobs, artifacts, ticker, doubles)
    preview = [MaskPreview(id="ix_01ARZ3NDEKTSV4RRFFQ69G5FAV", label="lamp", photo=0, polygons=[[(0, 0), (1, 0), (1, 1)]])]
    doubles.results["segment"] = StageResult(count=1, model="sam-3.1", mask_preview=preview)
    done = build.run(build.submit(uploads).id)
    assert done.mask_preview == preview and doubles.seen["author"].mask_preview == preview
    assert doubles.seen["segment"].mask_preview == [] and jobs.read(done.id).mask_preview == preview
