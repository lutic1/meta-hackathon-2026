"""Story 2.22: the scene stage writes the Room once, then immutable, and the job's final record beside it (AD-7, AD-12, AD-16)."""

from collections.abc import Callable

import pytest

from src.domain.schema import CallRow, DryRunVerdict, JobState, JobStatus, Room
from src.domain.validator import BUILD_RULES
from src.infra.clocks import BuildClock
from src.infra.local import DiskArtifactStore
from src.pipeline.author import author_stage, read_puzzles, validate_stage
from src.pipeline.build import STAGES, Build, StageFn, StageResult, new_id
from src.pipeline.ingest import read_photos
from src.pipeline.ports import room_key
from src.pipeline.scene import SCENE_BUDGET_MS, run_scene, run_skipped_dry_run, scene_stage, skipped_dry_run_stage
from src.pipeline.segment import TooFewInteractables
from src.providers.mock import MockProvider
from tests.pipeline.test_author_stage import reply, riddler, store_interactables
from tests.pipeline.test_build import RunnerDied
from tests.providers.test_spend import MemoryLedgerStore


class CountingStore(DiskArtifactStore):
    """The disk store, counting every `put` by key."""

    def __init__(self, root) -> None:
        super().__init__(root)
        self.puts: list[str] = []

    def put(self, key: str, data: bytes) -> None:
        self.puts.append(key)
        super().put(key, data)


@pytest.fixture
def artifacts(tmp_path) -> CountingStore:
    return CountingStore(tmp_path / "rooms")


class DryRun:
    """The Dry run test double (2.24 lands the stage): one call row and a `pass` for every stored Puzzle."""

    def __init__(self, artifacts: CountingStore) -> None:
        self.artifacts = artifacts
        self.calls: list[JobState] = []

    def __call__(self, state: JobState) -> StageResult:
        self.calls.append(state)
        puzzles = read_puzzles(state.room_id, self.artifacts)
        row = CallRow(id=new_id("call"), role="dryrun", model="mock-chat-1", host="mock", cached=False, spend_usd=0.0)
        verdicts = [DryRunVerdict(puzzle_id=puzzle.id, verdict="pass") for puzzle in puzzles]
        return StageResult(count=len(puzzles), model="mock-chat-1", calls=[row], dry_run=verdicts)


@pytest.fixture
def dry_run(artifacts) -> DryRun:
    return DryRun(artifacts)


@pytest.fixture
def build(jobs, artifacts, ticker, doubles, four_lock_room, dry_run):
    """A Build whose segment double stores the four-lock room's Interactables, then the real author, validate and scene stages.

    The dryrun slot is the `DryRun` double with `DRY_RUN=on`, or the cut 4 stage with it off.
    """
    doubles.hooks["segment"] = lambda state: store_interactables(artifacts, state, four_lock_room)

    def make(
        provider: MockProvider,
        ledger: MemoryLedgerStore | None = None,
        *,
        regen_max: int = 0,
        dry_run_on: bool = True,
        scene: Callable[[StageFn], StageFn] = lambda fn: fn,
    ) -> Build:
        ledger = ledger or MemoryLedgerStore()
        stages = doubles.stages()
        stages["author"] = author_stage(provider, artifacts)
        stages["validate"] = validate_stage(artifacts, ledger)
        stages["dryrun"] = dry_run if dry_run_on else skipped_dry_run_stage(artifacts)
        stages["scene"] = scene(scene_stage(artifacts, ledger))
        return Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=regen_max)

    return make


def stored_room(artifacts: CountingStore, state: JobState) -> Room:
    return Room.model_validate_json(artifacts.read(room_key(state.room_id)))


# --- The Room, written once under rooms/ ----------------------------------------


def test_a_draft_that_passed_both_gates_is_written_once_as_the_room_under_rooms_and_the_job_ends_done(
    build, uploads, artifacts, tmp_path, four_lock_room, dry_run
):
    runner = build(riddler(reply()))
    done = runner.run(runner.submit(uploads).id)
    assert done.status == "done" and done.stage is None and done.error is None
    assert len(dry_run.calls) == 1
    assert artifacts.puts.count(room_key(done.room_id)) == 1
    assert (tmp_path / "rooms" / done.room_id / "room.json").read_bytes() == artifacts.read(room_key(done.room_id))
    room = stored_room(artifacts, done)
    assert room.id == done.room_id and room.name is None and room.decoys == []
    assert room.photos == read_photos(done.room_id, artifacts)
    assert room.interactables == four_lock_room.interactables
    assert room.puzzles == read_puzzles(done.room_id, artifacts) and len(room.puzzles) == 5
    assert artifacts.list_rooms() == [room]


def test_the_room_carries_its_provenance_with_the_regeneration_count(build, uploads, artifacts):
    runner = build(riddler("not json", reply()), regen_max=2)
    done = runner.run(runner.submit(uploads).id)
    assert done.status == "done" and done.regeneration_count == 1
    provenance = stored_room(artifacts, done).provenance
    assert provenance.regeneration_count == 1 and provenance.applied_edits == []
    assert provenance.model_ids == {"riddler": "mock-chat-1", "dryrun": "mock-chat-1"}
    assert list(provenance.stage_timings_ms) == list(STAGES[:-1])
    assert set(provenance.prompt_hashes) == {"architect", "riddler", "storyteller"}


def test_run_scene_never_writes_over_a_room_already_stored(build, uploads, artifacts):
    runner = build(riddler(reply()))
    done = runner.run(runner.submit(uploads).id)
    written = artifacts.read(room_key(done.room_id))
    result = run_scene(done, artifacts=artifacts, ledger=MemoryLedgerStore())
    assert artifacts.read(room_key(done.room_id)) == written
    assert artifacts.puts.count(room_key(done.room_id)) == 1
    assert result.count == len(uploads)


def test_the_stage_needs_a_room(jobs, artifacts):
    state = JobState(id=new_id("job"), status="running", stage="scene", regen_max=2)
    with pytest.raises(ValueError, match="names no room"):
        run_scene(state, artifacts=artifacts, ledger=MemoryLedgerStore())


# --- The final job record ----------------------------------------------------------


def test_the_final_job_record_holds_timings_calls_verdicts_count_scenes_and_build_time(build, uploads, jobs, artifacts):
    runner = build(riddler(reply()))
    done = runner.run(runner.submit(uploads).id)
    record = jobs.read(done.id)
    assert record == done and record.status == "done"
    assert [stage.stage for stage in record.stages] == list(STAGES)
    assert record.build_time_ms == sum(stage.duration_ms for stage in record.stages)
    assert [row.role for row in record.calls] == ["riddler", "dryrun"]
    assert [(v.rule, v.passed) for v in record.validator] == [(n, True) for n in BUILD_RULES]
    puzzle_ids = [puzzle.id for puzzle in stored_room(artifacts, done).puzzles]
    assert record.dry_run == [DryRunVerdict(puzzle_id=pid, verdict="pass") for pid in puzzle_ids]
    assert record.regeneration_count == 0
    scene = record.stages[-1]
    assert scene.stage == "scene" and scene.count == len(uploads) == 6 and scene.model is None


def test_the_scene_stage_is_timed_against_its_10_s_budget_and_never_enforced(build, uploads, ticker):
    def slow(fn: StageFn) -> StageFn:
        def run(state: JobState) -> StageResult:
            ticker.advance_ms(11_000)
            return fn(state)
        return run

    runner = build(riddler(reply()), scene=slow)
    done = runner.run(runner.submit(uploads).id)
    assert SCENE_BUDGET_MS == 10_000
    assert done.status == "done"
    assert done.stages[-1].stage == "scene" and done.stages[-1].duration_ms == 11_000 > SCENE_BUDGET_MS


# --- DRY_RUN=off (cut 4) --------------------------------------------------------------


def test_dry_run_off_makes_no_call_records_every_puzzle_skipped_and_writes_the_room_on_the_validator_pass(
    build, uploads, artifacts, dry_run
):
    ledger = MemoryLedgerStore()
    runner = build(riddler(reply()), ledger, dry_run_on=False)
    done = runner.run(runner.submit(uploads).id)
    assert done.status == "done" and dry_run.calls == []
    assert ledger.entries() == []
    assert [row.role for row in done.calls] == ["riddler"]
    puzzle_ids = [puzzle.id for puzzle in stored_room(artifacts, done).puzzles]
    assert done.dry_run == [DryRunVerdict(puzzle_id=pid, verdict="skipped") for pid in puzzle_ids] and len(puzzle_ids) == 5
    dryrun = next(record for record in done.stages if record.stage == "dryrun")
    assert dryrun.model is None and dryrun.count is None


def test_the_skipped_dry_run_reads_the_stored_puzzles_only(build, uploads, artifacts):
    runner = build(riddler(reply()), dry_run_on=False)
    done = runner.run(runner.submit(uploads).id)
    result = run_skipped_dry_run(done, artifacts=artifacts)
    assert result.calls == [] and {v.verdict for v in result.dry_run} == {"skipped"}


# --- A restart after scene never rewrites the Room -------------------------------


def test_a_restart_after_scene_leaves_the_room_bytes_unchanged_and_the_job_done(build, uploads, artifacts, doubles):
    runner = build(riddler(reply()))
    done = runner.run(runner.submit(uploads).id)
    written = artifacts.read(room_key(done.room_id))
    calls = list(doubles.calls)
    again = runner.run(done.id)
    assert again == done and again.status == "done"
    assert artifacts.read(room_key(done.room_id)) == written
    assert doubles.calls == calls and artifacts.puts.count(room_key(done.room_id)) == 1


def test_a_runner_that_died_after_writing_the_room_resumes_to_done_without_rewriting_it(build, uploads, jobs, artifacts):
    deaths = [RunnerDied()]

    def dies_once(fn: StageFn) -> StageFn:
        def run(state: JobState) -> StageResult:
            result = fn(state)
            if deaths:
                raise deaths.pop()
            return result
        return run

    runner = build(riddler(reply()), scene=dies_once)
    queued = runner.submit(uploads)
    with pytest.raises(RunnerDied):
        runner.run(queued.id)
    stopped = jobs.read(queued.id)
    assert (stopped.status, stopped.stage) == ("running", "scene")
    written = artifacts.read(room_key(stopped.room_id))

    done = runner.run(queued.id)
    assert done.status == "done" and done.stages[-1].stage == "scene"
    assert artifacts.read(room_key(done.room_id)) == written
    assert artifacts.puts.count(room_key(done.room_id)) == 1


# --- No Room for a job that does not reach done --------------------------------------


@pytest.mark.parametrize("status", ["failed", "needs_more_photos", "needs_recapture"])
def test_a_job_that_ends_short_of_done_has_no_room_artifact(build, uploads, artifacts, doubles, status: JobStatus):
    text = "not json" if status == "needs_recapture" else reply()
    if status == "failed":
        doubles.raises["architect"] = RuntimeError("the host is down")
    if status == "needs_more_photos":
        doubles.raises["segment"] = TooFewInteractables("only 3 objects survived")
    runner = build(riddler(text))
    stopped = runner.run(runner.submit(uploads).id)
    assert stopped.status == status
    assert "scene" not in [record.stage for record in stopped.stages]
    with pytest.raises(KeyError):
        artifacts.read(room_key(stopped.room_id))
    assert artifacts.list_rooms() == []
    assert room_key(stopped.room_id) not in artifacts.puts
