"""Story 2.24: the dryrun stage proves every Puzzle solvable from its Clue and Rungs before scene writes the Room (AD-12, AD-13, A-24)."""

import json
from collections.abc import Callable

import pytest
from pydantic import BaseModel

from src.council.dryrun import build_dry_run_prompt
from src.domain.redact import to_prompt_view
from src.domain.schema import (
    CodeSolution,
    DryRunAnswer,
    DryRunAnswers,
    DryRunVerdict,
    JobId,
    JobState,
    Puzzle,
    SentBack,
    Stage,
    StageRecord,
)
from src.infra.clocks import BuildClock
from src.pipeline.author import (
    PUZZLES,
    assemble_provenance,
    assemble_room,
    author_stage,
    puzzles_key,
    read_puzzles,
    validate_stage,
)
from src.pipeline.build import Build
from src.pipeline.dryrun import (
    DRY_RUN_BUDGET_MS,
    MISMATCH_MESSAGE,
    MISSING_MESSAGE,
    SHAPE_MESSAGE,
    DryRunError,
    dry_run_stage,
    run_dry_run,
)
from src.pipeline.ingest import read_photos
from src.pipeline.ports import room_key
from src.pipeline.regenerate import FailedAttempt
from src.pipeline.scene import scene_stage
from src.providers.base import (
    ChatMessage,
    ChatResponse,
    ImageResponse,
    ModelProvider,
    ProviderError,
    ReasoningEffort,
    SegmentResponse,
)
from src.providers.cache import GuardedCalls
from src.providers.meta_api import CHAT_MODEL, MetaModelProvider
from src.providers.mock import ChatCall, MockProvider, MockScript
from src.providers.spend import SpendLedger
from tests.pipeline.test_author_stage import LEAKY, reply, riddler, store_interactables
from tests.pipeline.test_build import MemoryJobStore
from tests.providers.replay import transport
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

RECORDED = "muse-spark-1.3/chat-dry-run"
"""The SIT-14 reply over the synthetic four-lock room: one answer per Puzzle, every one reached."""
SENTINEL = "SENTINEL-8642"
"""A wrong code no Puzzle has; it must never reach job state, a message or a log."""

type Answering = Callable[[list[Puzzle]], str]


def solved(puzzles: list[Puzzle]) -> str:
    """Every Puzzle answered with its own solution, as the Dry run's JSON text."""
    return DryRunAnswers(answers=[DryRunAnswer(puzzle_id=p.id, answer=p.solution) for p in puzzles]).model_dump_json()


def wrong_code(puzzles: list[Puzzle]) -> str:
    """The first code Puzzle answered with the sentinel; the rest solved."""
    target = next(p.id for p in puzzles if p.solution.lock_type == "code")
    answers = [DryRunAnswer(puzzle_id=p.id, answer=CodeSolution(lock_type="code", code=SENTINEL) if p.id == target else p.solution)
               for p in puzzles]
    return DryRunAnswers(answers=answers).model_dump_json()


def one_missing(puzzles: list[Puzzle]) -> str:
    """Every Puzzle but the last answered."""
    return solved(puzzles[:-1])


def unparseable(puzzles: list[Puzzle]) -> str:
    return f"I think the code is {SENTINEL}."


class Solver(ModelProvider):
    """The `dryrun` port as a player: it reads the job's stored Puzzles and answers through the next `answering`, else solves them all."""

    name = "mock"

    def __init__(self, jobs: MemoryJobStore, artifacts, *answering: Answering) -> None:
        self.jobs = jobs
        self.artifacts = artifacts
        self.answering = list(answering)
        self.calls: list[ChatCall] = []

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        images: list[bytes] = [],  # noqa: B006 - the port's signature
        response_schema: type[BaseModel] | None = None,
        reasoning_effort: ReasoningEffort = "low",
        model: str | None = None,
        attempt: int = 0,
        job_id: JobId | None = None,
        stage: Stage | None = None,
    ) -> ChatResponse:
        self.calls.append(ChatCall(list(messages), list(images), response_schema, reasoning_effort, model, attempt, job_id, stage))
        assert job_id is not None
        puzzles = read_puzzles(self.jobs.read(job_id).room_id, self.artifacts)
        answer = self.answering.pop(0) if self.answering else solved
        return ChatResponse(text=answer(puzzles), model="mock-chat-1")

    def segment(self, label: str, image: bytes, *, job_id: JobId | None = None, stage: Stage | None = None) -> SegmentResponse:
        raise AssertionError("the dryrun stage makes no segment call")

    def generate_image(self, prompt: str) -> ImageResponse:
        raise AssertionError("the dryrun stage makes no image call")


@pytest.fixture
def ledger() -> MemoryLedgerStore:
    return MemoryLedgerStore()


@pytest.fixture
def build(jobs, artifacts, ticker, doubles, four_lock_room, ledger):
    """A Build whose segment double stores the four-lock room's Interactables, then the real author, validate, dryrun and scene stages."""
    doubles.hooks["segment"] = lambda state: store_interactables(artifacts, state, four_lock_room)

    def make(dry_run: ModelProvider, *, regen_max: int = 0, drafts: int = 1, texts: list[str] | None = None) -> Build:
        stages = doubles.stages()
        stages["author"] = author_stage(riddler(*(texts or [reply()] * drafts)), artifacts)
        stages["validate"] = validate_stage(artifacts, ledger)
        stages["dryrun"] = dry_run_stage(dry_run, artifacts, ledger)
        stages["scene"] = scene_stage(artifacts, ledger)
        return Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=regen_max)

    return make


def stored(artifacts, key: str) -> bool:
    try:
        artifacts.read(key)
    except KeyError:
        return False
    return True


def keys(value: object) -> set[str]:
    """Every object key anywhere in a JSON value."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


def reached(state: JobState) -> tuple[int, int]:
    """The Build view's "reached n of m answers": the dryrun record's count over the per-Puzzle verdicts."""
    record = [r for r in state.stages if r.stage == "dryrun"][-1]
    return record.count or 0, len(state.dry_run)


# --- One call, every answer reached, on to scene ------------------------------------


def test_one_dryrun_chat_call_over_the_2_23_prompt_with_the_photos_reaches_every_answer_and_the_job_goes_on_to_scene(
    build, uploads, jobs, artifacts, ledger
):
    solver = Solver(jobs, artifacts)
    runner = build(solver)
    done = runner.run(runner.submit(uploads).id)

    assert done.status == "done" and done.error is None and stored(artifacts, room_key(done.room_id))
    assert [r.stage for r in done.stages][-2:] == ["dryrun", "scene"]
    assert len(solver.calls) == 1
    call = solver.calls[0]
    prompt = build_dry_run_prompt(to_prompt_view(assemble_room(done, artifacts, ledger)), DryRunAnswers)
    assert call.messages == prompt.messages and call.response_schema is DryRunAnswers
    assert call.reasoning_effort == "low" and call.attempt == 0 and (call.job_id, call.stage) == (done.id, "dryrun")
    assert call.images == [artifacts.read(photo.downscaled_path) for photo in read_photos(done.room_id, artifacts)]
    rows = [row for row in done.calls if row.role == "dryrun"]
    assert len(rows) == 1 and (rows[0].model, rows[0].host, rows[0].cached, rows[0].spend_usd) == ("mock-chat-1", "mock", False, 0.0)
    puzzle_ids = [p.id for p in read_puzzles(done.room_id, artifacts)]
    assert done.dry_run == [DryRunVerdict(puzzle_id=pid, verdict="pass") for pid in puzzle_ids]
    assert reached(done) == (5, 5)
    record = next(r for r in done.stages if r.stage == "dryrun")
    assert record == StageRecord(stage="dryrun", duration_ms=record.duration_ms, count=5, model="mock-chat-1")


def test_the_prompt_never_carries_a_solution_and_the_dry_run_model_joins_provenance(build, uploads, jobs, artifacts, ledger):
    solver = Solver(jobs, artifacts)
    runner = build(solver)
    done = runner.run(runner.submit(uploads).id)
    text = "\n".join(message.content for message in solver.calls[0].messages)
    for puzzle in read_puzzles(done.room_id, artifacts):
        if puzzle.solution.lock_type == "code":
            assert f": {puzzle.solution.code}" not in text and f" {puzzle.solution.code}\n" not in text
        assert puzzle.lore not in text
    provenance = assemble_provenance(done, ledger.entries(), {})
    assert provenance.model_ids == {"riddler": "mock-chat-1", "dryrun": "mock-chat-1"}
    assert "dryrun" in provenance.stage_timings_ms


# --- A Puzzle not reached is a failed attempt for the loop ----------------------------


@pytest.mark.parametrize(
    ("answering", "messages", "passes"),
    [
        (wrong_code, [MISMATCH_MESSAGE], 4),
        (one_missing, [MISSING_MESSAGE], 4),
        (unparseable, [SHAPE_MESSAGE], 0),
    ],
    ids=["mismatch", "missing", "unparseable"],
)
def test_a_puzzle_not_reached_fails_the_attempt_with_a_fixed_reason_and_an_exhausted_loop_ends_needs_recapture(
    build, uploads, jobs, artifacts, answering, messages, passes
):
    runner = build(Solver(jobs, artifacts, answering))
    ended = runner.run(runner.submit(uploads).id)

    assert (ended.status, ended.stage) == ("needs_recapture", "dryrun")
    assert ended.error.code == "dry_run_error" and ended.error.stage == "dryrun"
    assert ended.sent_back == [SentBack(attempt=0, stage="dryrun", messages=messages)]
    assert not stored(artifacts, room_key(ended.room_id)), "a room that never passed the Dry run is never written"
    assert reached(ended) == (passes, 5)
    assert sum(v.verdict == "fail" for v in ended.dry_run) == 5 - passes
    assert [r.stage for r in ended.stages][-1] == "dryrun"
    assert len([row for row in ended.calls if row.role == "dryrun"]) == 1


def test_mismatched_and_missing_answers_together_give_both_fixed_reasons(build, uploads, jobs, artifacts):
    runner = build(Solver(jobs, artifacts, lambda puzzles: wrong_code(puzzles[:-1])))
    ended = runner.run(runner.submit(uploads).id)
    assert ended.sent_back[-1].messages == [MISMATCH_MESSAGE, MISSING_MESSAGE]
    assert reached(ended) == (3, 5)


def test_a_failed_dry_run_sends_the_job_back_to_author_and_the_retry_carries_the_next_attempt(build, uploads, jobs, artifacts):
    solver = Solver(jobs, artifacts, wrong_code)
    runner = build(solver, regen_max=2, drafts=2)
    done = runner.run(runner.submit(uploads).id)

    assert done.status == "done" and done.regeneration_count == 1
    assert [call.attempt for call in solver.calls] == [0, 1]
    assert done.sent_back == [SentBack(attempt=0, stage="dryrun", messages=[MISMATCH_MESSAGE])]
    assert [r.stage for r in done.stages][3:] == ["author", "validate", "dryrun", "author", "validate", "dryrun", "scene"]
    assert {v.verdict for v in done.dry_run} == {"pass"} and reached(done) == (5, 5)
    assert {v.puzzle_id for v in done.dry_run} == {p.id for p in read_puzzles(done.room_id, artifacts)}


def test_every_attempt_failing_the_dry_run_ends_needs_recapture_after_regen_max_plus_one_calls(build, uploads, jobs, artifacts):
    solver = Solver(jobs, artifacts, wrong_code, one_missing, unparseable)
    runner = build(solver, regen_max=2, drafts=3)
    ended = runner.run(runner.submit(uploads).id)
    assert (ended.status, ended.stage, ended.regeneration_count) == ("needs_recapture", "dryrun", 2)
    assert [call.attempt for call in solver.calls] == [0, 1, 2]
    assert [record.messages for record in ended.sent_back] == [[MISMATCH_MESSAGE], [MISSING_MESSAGE], [SHAPE_MESSAGE]]
    assert not stored(artifacts, room_key(ended.room_id))


def test_a_later_attempt_ending_at_validate_keeps_no_dry_run_verdict_from_an_earlier_draft(build, uploads, jobs, artifacts):
    runner = build(Solver(jobs, artifacts, wrong_code), regen_max=1, texts=[reply(), reply(p2=LEAKY)])
    ended = runner.run(runner.submit(uploads).id)
    assert (ended.status, ended.stage, ended.regeneration_count) == ("needs_recapture", "validate", 1)
    assert [record.stage for record in ended.sent_back] == ["dryrun", "validate"]
    assert ended.dry_run == [], "the first draft's verdicts name Puzzles puzzles.json no longer holds"


def test_dry_run_error_is_a_failed_attempt_at_the_dryrun_gate():
    assert issubclass(DryRunError, FailedAttempt) and DryRunError.gate == "dryrun"
    assert DRY_RUN_BUDGET_MS == 30_000


# --- Job state never holds an answer ----------------------------------------------------


@pytest.mark.parametrize("answering", [wrong_code, unparseable], ids=["mismatch", "unparseable"])
def test_job_state_records_verdicts_and_the_count_and_never_an_answer_or_a_solution(build, uploads, jobs, artifacts, answering, caplog):
    caplog.set_level("INFO")
    runner = build(Solver(jobs, artifacts, answering))
    ended = runner.run(runner.submit(uploads).id)
    persisted = jobs.rows[ended.id].decode()
    assert SENTINEL not in persisted and SENTINEL not in caplog.text
    assert not keys(json.loads(persisted)) & {"answer", "answers", "solution", "interactables", "item", "target"}
    for message in ended.sent_back[-1].messages:
        assert message in (MISMATCH_MESSAGE, MISSING_MESSAGE, SHAPE_MESSAGE)
    for puzzle in read_puzzles(ended.room_id, artifacts):
        if puzzle.solution.lock_type == "code":
            assert all(puzzle.solution.code not in message for message in ended.sent_back[-1].messages)
    assert set(json.loads(persisted)["dry_run"][0]) == {"puzzle_id", "verdict"}


# --- The stage on its own ------------------------------------------------------------------


@pytest.fixture
def seeded(jobs, artifacts, ticker, doubles, uploads, four_lock_room) -> JobState:
    """A job whose photos are ingested and whose stored Interactables and Puzzles are the four-lock room's, ready for `run_dry_run`."""
    runner = Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=doubles.stages(), regen_max=2)
    state = runner.submit(uploads)
    store_interactables(artifacts, state, four_lock_room)
    artifacts.put(puzzles_key(state.room_id), PUZZLES.dump_json(four_lock_room.puzzles))
    return state


def test_the_recorded_dry_run_replays_through_the_meta_adapter_reaching_every_answer_with_one_billed_row(seeded, artifacts, ledger):
    meta = MetaModelProvider(
        "test-key",
        calls=GuardedCalls(MemoryCache(), SpendLedger(ledger, cap_usd=60.0), host="api.meta.ai"),
        chat_kind="dryrun",
        budget_s=DRY_RUN_BUDGET_MS / 1000,
        transport=transport(RECORDED),
    )
    result = run_dry_run(seeded, provider=meta, artifacts=artifacts, ledger=ledger)
    assert (result.count, result.model) == (5, CHAT_MODEL) and {v.verdict for v in result.dry_run} == {"pass"}
    assert [(e.kind, e.status, e.job_id, e.stage) for e in ledger.entries()] == [
        ("dryrun", "reserved", seeded.id, "dryrun"), ("dryrun", "settled", seeded.id, "dryrun"),
    ]
    settled = ledger.entries()[-1]
    row = result.calls[0]
    assert (row.id, row.role, row.host, row.cached) == (settled.call_id, "dryrun", "api.meta.ai", False)
    assert row.spend_usd == settled.usd > 0
    assert assemble_provenance(seeded, ledger.entries(), {}).spend_per_stage_usd["dryrun"] == pytest.approx(settled.usd)


def test_run_dry_run_sends_the_attempt_and_the_stored_photo_bytes(seeded, artifacts, ledger, four_lock_room):
    provider = MockProvider("dryrun", MockScript(chat=[solved(four_lock_room.puzzles)]))
    state = seeded.model_copy(update={"regeneration_count": 2})
    result = run_dry_run(state, provider=provider, artifacts=artifacts, ledger=ledger)
    call = provider.calls[0]
    assert isinstance(call, ChatCall) and call.attempt == 2 and call.stage == "dryrun" and call.job_id == state.id
    assert len(call.images) == 6 and all(image[:3] == b"\xff\xd8\xff" for image in call.images)
    assert result.dry_run == [DryRunVerdict(puzzle_id=p.id, verdict="pass") for p in four_lock_room.puzzles]


def test_an_unreached_answer_raises_dry_run_error_keeping_the_call_row_and_verdicts(seeded, artifacts, ledger, four_lock_room):
    provider = MockProvider("dryrun", MockScript(chat=[wrong_code(four_lock_room.puzzles)]))
    with pytest.raises(DryRunError) as raised:
        run_dry_run(seeded, provider=provider, artifacts=artifacts, ledger=ledger)
    failure = raised.value
    assert failure.messages == [MISMATCH_MESSAGE] and failure.reasons == []
    assert SENTINEL not in str(failure) and "415" not in str(failure) and "7342" not in str(failure)
    assert len(failure.result.calls) == 1 and failure.result.count == 4
    assert [v.verdict for v in failure.result.dry_run] == ["pass", "fail", "pass", "pass", "pass"]


def test_a_provider_error_ends_the_build_failed_at_dryrun_not_in_the_loop(build, uploads, artifacts):
    class Failing(MockProvider):
        def chat(self, *args, **kwargs):
            raise ProviderError(503, "overloaded", "busy")

    runner = build(Failing("dryrun"), regen_max=2)
    ended = runner.run(runner.submit(uploads).id)
    assert (ended.status, ended.stage, ended.error.code) == ("failed", "dryrun", "provider_error")
    assert ended.sent_back == [] and not stored(artifacts, room_key(ended.room_id))
