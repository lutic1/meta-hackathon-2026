"""Story 7.7: the hosted build runner, the `queued` state, the final record on the Volume and the watchdog (AD-7, FR-32, NFR-7).

No test reaches Modal: `run_build.spawn` is a stub that records its
arguments, the call poll is a stub returning a `RunnerState`, the Dicts are
plain dicts that log their writes, and the Volume is a temporary directory
behind a stub that logs `commit` and `reload`. A job's age is read on a
hand-set wall clock against the time its `job_` ULID was minted.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import pytest

from src.domain.schema import CallRow, JobState, StageRecord
from src.infra.clocks import BuildClock
from src.infra.modal import (
    DEADLINE_S,
    ENDED,
    JOB_FILE,
    ORPHAN_S,
    DictJobStore,
    ModalHandles,
    ModalJobRunner,
    RunnerState,
    VolumeFiles,
    call_key,
    hosted_stores,
    minted_ms,
    slot_key,
)
from src.pipeline.architect import architect_stage
from src.pipeline.build import STAGES, Build, StageResult, new_id
from src.pipeline.segment import segment_stage
from src.providers.base import ChatMessage
from src.providers.mock import MockProvider
from tests.infra.test_clocks import Ticker
from tests.infra.test_local import JOB_A, _job_state
from tests.infra.test_modal import RecordingDict, StubVolume
from tests.pipeline.stages import Segmenter, architect_mock, labels, square
from tests.pipeline.test_build import Doubles, RunnerDied
from tests.pipeline.uploads import make_uploads

ARCHITECT_ROW = CallRow(id=new_id("call"), role="architect", model="muse-spark-1.3", host="api.meta.ai", cached=False, spend_usd=0.03)
INSIDE = square(130, 100, 380, 285)
"""A mask well inside each candidate's box, so every label survives segment."""

# --- Doubles -------------------------------------------------------------------


@dataclass
class Wall:
    """A wall clock set by hand: `at(job_id, s)` reads `s` seconds after the job was minted."""

    ms: int = 0

    def at(self, job_id: str, seconds: float) -> None:
        self.ms = minted_ms(job_id) + int(seconds * 1000)

    def __call__(self) -> int:
        return self.ms


@dataclass
class Poll:
    """The call poll: answers `state` and records each call id it was asked about; `before` runs first."""

    state: RunnerState = "running"
    asked: list[str] = field(default_factory=list)
    before: Callable[[], None] | None = None

    def __call__(self, call_id: str) -> RunnerState:
        self.asked.append(call_id)
        if self.before is not None:
            self.before()
        return self.state


@dataclass(frozen=True)
class Call:
    object_id: str


class Spawn:
    """`run_build.spawn`: records its arguments and returns a call at once, running nothing."""

    def __init__(self, raises: Exception | None = None) -> None:
        self.raises = raises
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def __call__(self, *args: object, **kwargs: object) -> Call:
        self.calls.append((args, kwargs))
        if self.raises is not None:
            raise self.raises
        return Call(f"fc-{len(self.calls)}")


class ExecutionError(Exception):
    """Stands in for Modal's `ExecutionError` from a spawn outside a running app."""


@pytest.fixture
def log() -> list[str]:
    return []


@pytest.fixture
def handles(tmp_path: Path, log: list[str]) -> ModalHandles:
    return ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume(log), root=tmp_path / "data")


@pytest.fixture
def wall() -> Wall:
    return Wall()


@pytest.fixture
def poll() -> Poll:
    return Poll()


@pytest.fixture
def web(handles: ModalHandles, poll: Poll, wall: Wall) -> DictJobStore:
    """The web side's job store: its reads run the watchdog."""
    return DictJobStore(handles.jobs, VolumeFiles(handles.volume, handles.root), poll=poll, now_ms=wall)


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def doubles(ticker: Ticker) -> Doubles:
    return Doubles(ticker)


def _runner_build(handles: ModalHandles, ticker: Ticker, doubles: Doubles) -> Build:
    """The stage runner's Build over its own hosted stores, which carry no poll."""
    stores = hosted_stores(handles)
    return Build(jobs=stores.jobs, artifacts=stores.artifacts, clock=BuildClock(monotonic_ns=ticker), stages=doubles.stages(), regen_max=2)


def _submit(handles: ModalHandles, web: DictJobStore, ticker: Ticker) -> JobState:
    """`POST /builds` as far as this story goes: ingest on the web side, the job persisted `queued`."""
    stores = hosted_stores(handles)
    build = Build(jobs=web, artifacts=stores.artifacts, clock=BuildClock(monotonic_ns=ticker), stages=Doubles(ticker).stages(), regen_max=2)
    return build.submit(make_uploads(6))


def _job_writes(handles: ModalHandles, job_id: str) -> list[dict]:
    return [value for key, value in handles.jobs.writes if key == job_id]


def _queued(job_id: str = JOB_A) -> JobState:
    return JobState(id=job_id, status="queued", room_id="room_01ARZ3NDEKTSV4RRFFQ69G5FAV", stages=[StageRecord(stage="ingest", duration_ms=0, count=6)], regen_max=2)


# --- JobRunner.start: the id only, the call id under its own key, at once ---------------


def test_start_spawns_with_the_job_id_only_stores_the_call_id_under_its_own_key_and_returns_at_once(handles, web, ticker, doubles):
    queued = _submit(handles, web, ticker)
    before = list(handles.jobs.writes)
    spawn = Spawn()
    ModalJobRunner(web, spawn).start(queued.id)
    assert spawn.calls == [((queued.id,), {})]
    assert handles.jobs.writes[len(before):] == [(call_key(queued.id), "fc-1")] and call_key(queued.id) == f"call:{queued.id}"
    assert doubles.calls == [] and web.read(queued.id) == queued and queued.status == "queued"


def test_the_job_reads_queued_while_it_waits_until_the_runners_first_stage_write(handles, web, poll, wall, ticker, doubles):
    queued = _submit(handles, web, ticker)
    ModalJobRunner(web, Spawn()).start(queued.id)
    for seconds in (0, ORPHAN_S + 1, DEADLINE_S + 1):  # a call Modal still holds in line polls as running, however long it waits
        wall.at(queued.id, seconds)
        assert web.read(queued.id) == queued
    seen: list[tuple[str, str | None]] = []
    doubles.hooks["architect"] = lambda _: seen.append((web.read(queued.id).status, web.read(queued.id).stage))
    _runner_build(handles, ticker, doubles).run(queued.id)
    assert seen == [("running", "architect")] and poll.asked and set(poll.asked) == {"fc-1"}


def test_a_spawn_that_raises_marks_the_job_failed_at_ingest_and_reraises(handles, web, ticker):
    queued = _submit(handles, web, ticker)
    with pytest.raises(ExecutionError, match="has not been hydrated"):
        ModalJobRunner(web, Spawn(raises=ExecutionError("Function has not been hydrated"))).start(queued.id)
    failed = web.read(queued.id)
    assert failed.status == "failed" and failed.stage == "ingest" and failed.stages == queued.stages
    assert failed.error is not None and (failed.error.code, failed.error.stage) == ("execution_error", "ingest")
    assert call_key(queued.id) not in handles.jobs


# --- One writer per job ------------------------------------------------------------------


def test_the_runner_is_the_only_writer_of_the_record_and_a_web_read_never_writes_it_back(handles, web, ticker, doubles):
    queued = _submit(handles, web, ticker)
    ModalJobRunner(web, Spawn()).start(queued.id)
    assert [value["status"] for value in _job_writes(handles, queued.id)] == ["queued"]
    web_writes: list[int] = []

    def poll_from_the_web(_: JobState) -> None:
        count = len(handles.jobs.writes)
        web.read(queued.id)
        web.list_ids()
        web_writes.append(len(handles.jobs.writes) - count)

    for stage in STAGES[1:]:
        doubles.hooks[stage] = poll_from_the_web
    done = _runner_build(handles, ticker, doubles).run(queued.id)
    assert done.status == "done" and web_writes == [0] * 6
    assert web.read(queued.id) == done and len(_job_writes(handles, queued.id)) == 1 + 2 * 6 + 1  # queued, then the runner's
    # the build slot is claimed before the queued record (7.11); it is its own key, never the record
    assert [key for key, _ in handles.jobs.writes] == [slot_key(1), queued.id, call_key(queued.id), *[queued.id] * 13]
    artifacts = handles.root / "rooms" / "judge" / queued.room_id
    assert sorted(p.relative_to(artifacts).as_posix() for p in artifacts.rglob("*") if p.is_file()) == sorted(
        [*(f"photos/{i}.jpg" for i in range(6)), *(f"originals/{i}.jpg" for i in range(6)), "photos.json", JOB_FILE]
    )


@pytest.mark.parametrize("ended", sorted(ENDED))
def test_the_watchdogs_failed_mark_on_an_ended_runner_is_the_only_other_write(handles, web, poll, wall, ended):
    running = _job_state(JOB_A)
    web.put(running)
    handles.jobs[call_key(JOB_A)] = "fc-1"
    wall.at(JOB_A, 30)
    poll.state = ended
    count = len(handles.jobs.writes)
    failed = web.read(JOB_A)
    assert failed == running.model_copy(update={"status": "failed"}) and failed.stage == "segment"
    assert handles.jobs.writes[count:] == [(JOB_A, failed.model_dump(mode="json"))]
    assert web.read(JOB_A) == failed and len(handles.jobs.writes) == count + 1 and poll.asked == ["fc-1"]


# --- The final record on the Volume, and the Dict-then-Volume read ------------------------


def test_the_done_record_is_written_beside_the_room_committed_and_read_once_the_dict_entry_is_gone(handles, web, ticker, doubles, log):
    queued = _submit(handles, web, ticker)
    ModalJobRunner(web, Spawn()).start(queued.id)
    final = handles.root / "rooms" / "judge" / queued.room_id / JOB_FILE
    doubles.hooks["scene"] = lambda _: log.append(f"before scene: {final.exists()}")
    doubles.results["architect"] = StageResult(count=9, model="muse-spark-1.3", calls=[ARCHITECT_ROW])
    done = _runner_build(handles, ticker, doubles).run(queued.id)
    assert done.status == "done" and "before scene: False" in log and log[-1] == "commit"
    assert JobState.model_validate_json(final.read_bytes()) == done

    handles.jobs.pop(queued.id)
    handles.jobs.pop(call_key(queued.id))
    again = hosted_stores(handles).jobs
    for store in (again, web):
        read = store.read(queued.id)
        assert read == done and read.status == "done" and read.calls == [ARCHITECT_ROW]
        assert [record.stage for record in read.stages] == list(STAGES) and all(r.duration_ms == 1_000 for r in read.stages[1:])
        assert store.list_ids() == [queued.id]
    with pytest.raises(KeyError):
        again.read("job_01CX5ZZKBKACTAV9WEVGEMMVRZ")


@pytest.mark.parametrize("status", ["queued", "running", "failed", "needs_more_photos", "needs_recapture"])
def test_only_a_done_record_reaches_the_volume(handles, log, status):
    store = hosted_stores(handles).jobs
    state = _job_state(JOB_A).model_copy(update={"status": status, "stage": "segment" if status != "queued" else None})
    store.put(state)
    assert log == [] and not handles.root.exists() and store.read(JOB_A) == state


# --- The watchdog --------------------------------------------------------------------------


def test_a_queued_job_with_no_call_key_is_left_until_orphan_s_then_marked_failed(handles, web, wall):
    queued = _queued()
    web.put(queued)
    wall.at(JOB_A, ORPHAN_S - 1)
    assert web.read(JOB_A) == queued
    wall.at(JOB_A, ORPHAN_S + 1)
    failed = web.read(JOB_A)
    assert failed == queued.model_copy(update={"status": "failed", "stage": "ingest"})
    assert _job_writes(handles, JOB_A) == [queued.model_dump(mode="json"), failed.model_dump(mode="json")]


def test_a_running_job_with_no_call_key_counts_as_unknown_until_the_deadline(handles, web, wall):
    running = _job_state(JOB_A)
    web.put(running)
    wall.at(JOB_A, DEADLINE_S - 1)
    assert web.read(JOB_A) == running
    wall.at(JOB_A, DEADLINE_S + 1)
    assert web.read(JOB_A) == running.model_copy(update={"status": "failed"})


def test_an_unknown_call_state_leaves_the_job_unchanged_until_deadline_s_then_marks_it_failed(handles, web, poll, wall):
    running = _job_state(JOB_A)
    web.put(running)
    handles.jobs[call_key(JOB_A)] = "fc-1"
    poll.state = "unknown"
    for seconds in (0, ORPHAN_S + 1, DEADLINE_S - 1):
        wall.at(JOB_A, seconds)
        assert web.read(JOB_A) == running
    assert len(_job_writes(handles, JOB_A)) == 1
    wall.at(JOB_A, DEADLINE_S + 1)
    failed = web.read(JOB_A)
    assert failed.status == "failed" and failed.stage == "segment" and len(_job_writes(handles, JOB_A)) == 2


def test_a_running_call_is_never_failed_and_a_terminal_job_is_never_polled(handles, web, poll, wall):
    running = _job_state(JOB_A)
    web.put(running)
    handles.jobs[call_key(JOB_A)] = "fc-1"
    wall.at(JOB_A, DEADLINE_S * 10)
    assert web.read(JOB_A) == running and poll.asked == ["fc-1"]
    for status in ("done", "failed", "needs_more_photos", "needs_recapture"):
        terminal = running.model_copy(update={"status": status})
        web.put(terminal)
        assert web.read(JOB_A) == terminal
    assert poll.asked == ["fc-1"]


def test_the_watchdog_returns_the_terminal_record_the_runner_wrote_meanwhile(handles, web, poll, wall):
    running = _job_state(JOB_A)
    web.put(running)
    handles.jobs[call_key(JOB_A)] = "fc-1"
    done = running.model_copy(update={"status": "done", "stage": None})
    poll.state = "finished"
    poll.before = lambda: handles.jobs.__setitem__(JOB_A, done.model_dump(mode="json"))  # the runner's last write lands mid-read
    wall.at(JOB_A, 30)
    assert web.read(JOB_A) == done
    assert [value["status"] for value in _job_writes(handles, JOB_A)] == ["running", "done"]


def test_the_runners_own_store_has_no_poll_so_it_never_runs_the_watchdog(handles):
    def poll(_: str) -> RunnerState:
        return "crashed"

    assert hosted_stores(handles).jobs.poll is None and hosted_stores(handles, poll=poll).jobs.poll is poll
    running = _job_state(JOB_A)
    runner_store = hosted_stores(handles).jobs
    runner_store.put(running)
    handles.jobs[call_key(JOB_A)] = "fc-1"
    assert runner_store.read(JOB_A) == running and hosted_stores(handles, poll=poll).jobs.read(JOB_A).status == "failed"


def test_a_job_age_is_read_from_its_ulid_and_the_runner_states_are_the_six_modal_outcomes():
    before = time.time_ns() // 1_000_000
    job_id = new_id("job")
    assert before <= minted_ms(job_id) <= time.time_ns() // 1_000_000
    assert datetime.fromtimestamp(minted_ms(JOB_A) / 1000, UTC) == datetime(2016, 7, 30, 23, 54, 10, 259_000, UTC)  # the ULID spec's example
    assert set(get_args(RunnerState.__value__)) == {"running", "finished", "timed_out", "crashed", "expired", "unknown"}
    assert ENDED == {"finished", "timed_out", "crashed", "expired"}
    assert (ORPHAN_S, DEADLINE_S) == (60, 1_200)


# --- A restarted runner resumes at validate --------------------------------------------------


def _resumable_build(handles: ModalHandles, ticker: Ticker, doubles: Doubles, architect: MockProvider, segmenter: Segmenter, riddler: MockProvider) -> Build:
    """A fresh runner over its own hosted stores: the real architect and segment stages, an author stage making one Riddler call on the mock."""
    stores = hosted_stores(handles)

    def author(state: JobState) -> StageResult:
        reply = riddler.chat([ChatMessage(role="user", content=f"author {state.room_id}")])
        return StageResult(count=1, model=reply.model)

    stages = {
        **doubles.stages(),
        "architect": architect_stage(architect, stores.artifacts),
        "segment": segment_stage(segmenter, stores.artifacts),
        "author": author,
    }
    return Build(jobs=stores.jobs, artifacts=stores.artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=2)


def test_a_runner_restarted_after_author_resumes_at_validate_with_no_repeated_model_call(handles, web, ticker):
    candidates = labels(14, photo=lambda i: (i * 5) % 6)
    architect, segmenter, riddler = architect_mock(candidates), Segmenter({c["label"]: [INSIDE] for c in candidates}), MockProvider("riddler")
    queued = _submit(handles, web, ticker)
    ModalJobRunner(web, Spawn()).start(queued.id)

    first_doubles = Doubles(ticker)
    first_doubles.raises["validate"] = RunnerDied()
    with pytest.raises(RunnerDied):
        _resumable_build(handles, ticker, first_doubles, architect, segmenter, riddler).run(queued.id)
    left = hosted_stores(handles).jobs.read(queued.id)
    assert left.status == "running" and left.stage == "validate"
    assert [record.stage for record in left.stages] == ["ingest", "architect", "segment", "author"]
    calls = (len(architect.calls), len(segmenter.calls), len(riddler.calls))
    assert calls == (1, 14, 1)

    second_doubles = Doubles(ticker)
    done = _resumable_build(handles, ticker, second_doubles, architect, segmenter, riddler).run(queued.id)
    assert second_doubles.calls == ["validate", "dryrun", "scene"]
    assert second_doubles.seen["validate"] == left
    assert (len(architect.calls), len(segmenter.calls), len(riddler.calls)) == calls
    assert done.status == "done" and done.stages[:4] == left.stages
    assert JobState.model_validate_json((handles.root / "rooms" / "judge" / queued.room_id / JOB_FILE).read_bytes()) == done
