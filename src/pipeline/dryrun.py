"""The dryrun stage (AD-12, AD-13, A-24): a call that never saw a solution must reach every answer before scene.

With `DRY_RUN=on` the runner reaches this stage only after `validate`
passed on the same attempt. `run_dry_run` assembles that attempt's Room,
builds the 2.23 prompt over its `RoomView` (`build_dry_run_prompt`), and
makes one `chat` call through the `dryrun` role's port at reasoning `low`,
with the stored downscaled photo bytes as `images`, `attempt` set to the
Regeneration count (so the AD-6 cache never serves an earlier attempt's
answers) and the job id and `dryrun` stage tagging its ledger entry. It
records one call row. The reply is parsed into `DryRunAnswers` and handed
to `check_dry_run` with the Room: this stage is its only caller, so the only
place where answers meet solutions.

Job state gets the verdict per Puzzle and, as the stage's done-row count,
the number of answers reached, which with the verdict count reads "reached
n of m answers"; the answers themselves are never stored or logged. A
mismatched answer, a Puzzle with no answer, or a reply that does not parse
(every Puzzle then fails) raises `DryRunError` with fixed messages that quote
neither an answer nor a solution, for the regeneration loop (2.21), which
sends the job back to author or, once exhausted, ends it `needs_recapture`.
The Dry run's 30 s budget (`budgets.md`) is measured by the runner's stage
timing, never enforced. Under `DRY_RUN=off` (cut 4) wiring puts the skipped
stage (`scene.py`) in this slot instead.
"""

from __future__ import annotations

import pydantic

from src.council.dryrun import build_dry_run_prompt
from src.domain.redact import to_prompt_view
from src.domain.schema import DryRunAnswers, DryRunVerdict, JobState
from src.domain.validator import check_dry_run
from src.pipeline.author import assemble_room
from src.pipeline.build import StageFn, StageResult, call_row
from src.pipeline.ports import ArtifactStore, LedgerStore
from src.pipeline.regenerate import FailedAttempt
from src.providers.base import ModelProvider

DRY_RUN_BUDGET_MS = 30_000
"""`budgets.md`: the Dry run's 30 s, measured through the stage timing, never enforced."""

MISMATCH_MESSAGE = "The test run reached a wrong answer from a puzzle's clue and hints."
MISSING_MESSAGE = "The test run gave no answer for a puzzle."
SHAPE_MESSAGE = "The test run's reply did not follow the answer shape."
"""The fixed reasons of a failed Dry run (A-24); none quotes an answer or a solution."""


class DryRunError(FailedAttempt):
    """A Dry run that did not reach every answer (AD-13), for the regeneration loop; never a `failed` Build."""

    gate = "dryrun"


def run_dry_run(state: JobState, *, provider: ModelProvider, artifacts: ArtifactStore, ledger: LedgerStore) -> StageResult:
    """One `dryrun` `chat` call at attempt = the Regeneration count, then `check_dry_run`; any Puzzle not reached raises `DryRunError`."""
    room = assemble_room(state, artifacts, ledger)
    prompt = build_dry_run_prompt(to_prompt_view(room), DryRunAnswers)
    reply = provider.chat(
        prompt.messages,
        images=[artifacts.read(photo.downscaled_path) for photo in room.photos],
        response_schema=prompt.response_schema,
        reasoning_effort=prompt.reasoning_effort,
        attempt=state.regeneration_count,
        job_id=state.id,
        stage="dryrun",
    )
    row = call_row(reply.receipt, provider, "dryrun", reply.model)
    try:
        answers = DryRunAnswers.model_validate_json(reply.text)
    except pydantic.ValidationError:
        verdicts = [DryRunVerdict(puzzle_id=puzzle.id, verdict="fail") for puzzle in room.puzzles]
        raise DryRunError([SHAPE_MESSAGE], StageResult(count=0, model=reply.model, calls=[row], dry_run=verdicts)) from None
    result = check_dry_run(room, answers)
    stage_result = StageResult(
        count=sum(verdict.verdict == "pass" for verdict in result.verdicts), model=reply.model, calls=[row], dry_run=result.verdicts
    )
    if result.ok:
        return stage_result
    answered = {answer.puzzle_id for answer in answers.answers}
    missing = {puzzle.id for puzzle in room.puzzles} - answered
    failed = {verdict.puzzle_id for verdict in result.verdicts if verdict.verdict == "fail"}
    messages = [message for message, hit in ((MISMATCH_MESSAGE, failed - missing), (MISSING_MESSAGE, missing)) if hit]
    raise DryRunError(messages, stage_result)


def dry_run_stage(provider: ModelProvider, artifacts: ArtifactStore, ledger: LedgerStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `dryrun` under `DRY_RUN=on`, over the `dryrun` role's provider."""
    return lambda state: run_dry_run(state, provider=provider, artifacts=artifacts, ledger=ledger)
