"""The stage runner (AD-7): a persisted, resumable Build job, and the one writer of its state.

`Build.submit(uploads)` refuses a bad upload before any job exists, then
mints the `job_` and `room_` ids, claims a build slot for the job through
`JobStore.reserve_build` (the hosted store raises `BuildQuotaExceeded` once
every slot is taken; the local store never refuses), and only then runs
ingest, the first photo write, and persists the job `queued` for
`JobRunner.start(job_id)`. `Build.run(job_id)` runs the stages after
the last persisted one, in order, rereading job state from `JobStore` before
each and persisting it after each stage with its duration from the build
clock, which never sees `DEMO_TIMESCALE` (AD-10); a terminal job is left as
it is, so a restart after scene never rewrites anything, and no job state
lives in a process variable between stages. Each stage after
ingest is a `StageFn` injected by wiring; what it returns (done-row count,
model id, call rows, the mask preview, the Validator's per-rule verdicts,
the per-Puzzle Dry run verdicts) goes into job state beside the timing
(AD-16), the latest verdicts replacing earlier ones, and the build time is
the sum of the finished stages. The state the runner persists `done` after
scene, the stage that writes the Room, is the job's final record. An
error raised by a stage ends the job `failed` with that stage and the
class name in snake_case (`spend_cap_exceeded`, `provider_error`;
AD-13); a `StageStop` ends it in the status the stage names instead,
keeping the stage's record and call rows (segment's `TooFewInteractables`).
A `FailedAttempt` (a draft's `ValidationError`, the Dry run's refusal) keeps
its stage's record and goes to the regeneration loop (`regenerate.py`),
which records it and either sends the job back to author for another
attempt or ends it; the runner itself sets only `queued`, `running`,
`done` and `failed`.
One JSON log line per stage carries `job_id`, `stage`, `duration_ms` and
`spend_usd` (AR-22).
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import get_args

from src.domain.schema import (
    CallRow,
    DryRunVerdict,
    ErrorDetail,
    JobId,
    JobState,
    JobStatus,
    MaskPreview,
    Role,
    RuleVerdict,
    Stage,
    StageRecord,
)
from src.pipeline.ingest import IngestRefused, Upload, store_upload, validate_upload
from src.pipeline.ports import ArtifactStore, Clock, JobStore
from src.pipeline.regenerate import FailedAttempt, rewriting, send_back
from src.providers.base import CallReceipt, ModelProvider

logger = logging.getLogger(__name__)

STAGES: tuple[Stage, ...] = ("ingest", "architect", "segment", "author", "validate", "dryrun", "scene")
TERMINAL: frozenset[JobStatus] = frozenset(get_args(JobStatus)) - {"queued", "running"}
"""Every status a job stays in; the runner reaches `done` and `failed` itself."""
CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_id(prefix: str) -> str:
    """A fresh prefixed ULID (AD-18): 48 bits of Unix milliseconds then 80 random bits, Crockford base32."""
    value = (time.time_ns() // 1_000_000) << 80 | int.from_bytes(secrets.token_bytes(10))
    return f"{prefix}_" + "".join(CROCKFORD_BASE32[(value >> shift) & 31] for shift in range(125, -1, -5))


def call_row(receipt: CallReceipt | None, provider: ModelProvider, role: Role, model: str) -> CallRow:
    """The `role` call row from the call's receipt (AD-16); the mock has none, so its row is unbilled on the mock host."""
    if receipt is None:
        return CallRow(id=new_id("call"), role=role, model=model, host=provider.name, cached=False, spend_usd=0.0)
    return CallRow(id=receipt.call_id, role=role, model=model, host=receipt.host, cached=receipt.cached, spend_usd=receipt.spend_usd)


def error_code(exc: BaseException) -> str:
    """The AD-13 code: a request refusal's own code, else the typed class name in snake_case."""
    if isinstance(exc, IngestRefused):
        return exc.code
    return re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()


def error_detail(exc: BaseException, stage: Stage | None) -> ErrorDetail:
    """The envelope's `error` for `exc`, raised at `stage` (`None` outside the pipeline)."""
    return ErrorDetail(code=error_code(exc), message=str(exc), stage=stage)


@dataclass(frozen=True)
class StageResult:
    """What a finished stage adds to job state beside its timing: its done row, call rows, mask preview and verdicts."""

    count: int | None = None
    model: str | None = None
    calls: list[CallRow] = field(default_factory=list)
    mask_preview: list[MaskPreview] = field(default_factory=list)
    validator: list[RuleVerdict] = field(default_factory=list)
    """The Validator's per-rule verdicts on this attempt's draft; empty from every other stage."""
    dry_run: list[DryRunVerdict] = field(default_factory=list)
    """The Dry run's verdict per Puzzle on this attempt's draft (`skipped` under `DRY_RUN=off`); empty from every other stage."""


type StageFn = Callable[[JobState], StageResult]
"""A stage after ingest: given the persisted job state, it reads the artifacts it needs and returns what it adds."""


class StageStop(Exception):
    """A stage's own end to the job (AD-7, AD-13): the status it ends in instead of `failed`, with what the stage did first.

    The job keeps the stage's record and call rows under `status`, with the
    stop's code and message as its `error`; no later stage runs.
    """

    status: JobStatus

    def __init__(self, message: str, result: StageResult | None = None) -> None:
        super().__init__(message)
        self.result = result or StageResult()


class Build:
    """The stage runner over `JobStore`, `ArtifactStore` and the build clock."""

    def __init__(
        self,
        *,
        jobs: JobStore,
        artifacts: ArtifactStore,
        clock: Clock,
        stages: Mapping[Stage, StageFn],
        regen_max: int,
    ) -> None:
        missing = [stage for stage in STAGES[1:] if stage not in stages]
        if missing:
            raise ValueError(f"no stage function for {', '.join(missing)}")
        self._jobs = jobs
        self._artifacts = artifacts
        self._clock = clock
        self._stages = stages
        self._regen_max = regen_max

    def submit(self, uploads: Sequence[Upload]) -> JobState:
        """Refuse the upload before any job exists, else mint the ids, claim a build slot, run ingest and persist the job `queued`.

        A refused upload claims no slot, and a refused claim (`BuildQuotaExceeded`) stores nothing.
        """
        validate_upload(uploads)
        room_id = new_id("room")
        state = JobState(id=new_id("job"), status="running", stage="ingest", room_id=room_id, regen_max=self._regen_max)
        self._jobs.reserve_build(state.id)
        state = self._finish(state, "ingest", lambda _: StageResult(count=len(store_upload(uploads, room_id, self._artifacts))))
        if state.status == "failed":
            return self._put(state)
        return self._put(state.model_copy(update={"status": "queued", "stage": None}))

    def run(self, job_id: JobId) -> JobState:
        """Run every stage after the last persisted one, in order, rereading the job from the store before each; a terminal job is left as it is.

        After a failed attempt the regeneration loop has advanced the count,
        and the next stage is author again.
        """
        while (state := self._jobs.read(job_id)).status not in TERMINAL:
            if not state.stages:
                raise ValueError(f"{job_id} holds no ingest record to resume from")
            finished = STAGES.index(state.stages[-1].stage) + 1
            if finished == len(STAGES):
                return self._put(state.model_copy(update={"status": "done", "stage": None}))
            stage = "author" if rewriting(state) else STAGES[finished]
            state = self._put(state.model_copy(update={"status": "running", "stage": stage}))
            self._put(self._finish(state, stage, self._stages[stage]))
        return state

    def _put(self, state: JobState) -> JobState:
        self._jobs.put(state)
        return state

    def _finish(self, state: JobState, stage: Stage, fn: StageFn) -> JobState:
        """Run `stage` against the build clock: the state with its record appended, sent back, stopped by the stage, or `failed` at it."""
        start = self._clock.now_ms()
        try:
            result = fn(state)
        except FailedAttempt as exc:
            recorded = self._record(state, stage, exc.result, self._clock.now_ms() - start, code=error_code(exc))
            try:
                return send_back(recorded, exc, error_detail(exc, stage), self._artifacts)
            except Exception as err:  # noqa: BLE001 - a failed attempt the loop cannot record ends the job failed (AD-13)
                return recorded.model_copy(update={"status": "failed", "stage": stage, "error": error_detail(err, stage)})
        except StageStop as exc:
            recorded = self._record(state, stage, exc.result, self._clock.now_ms() - start, code=error_code(exc))
            return recorded.model_copy(update={"status": exc.status, "stage": stage, "error": error_detail(exc, stage)})
        except Exception as exc:  # noqa: BLE001 - any error a stage raises ends the job failed (AD-13)
            duration_ms = self._clock.now_ms() - start
            self._log(state.id, stage, duration_ms, 0.0, code=error_code(exc))
            return state.model_copy(update={"status": "failed", "stage": stage, "error": error_detail(exc, stage)})
        return self._record(state, stage, result, self._clock.now_ms() - start)

    def _record(self, state: JobState, stage: Stage, result: StageResult, duration_ms: int, *, code: str | None = None) -> JobState:
        """The state with the stage's record, call rows and mask preview appended, verdicts replaced, and its log line written.

        A new draft (author) clears the last attempt's Dry run verdicts, which name Puzzles it no longer holds.
        """
        self._log(state.id, stage, duration_ms, sum(row.spend_usd for row in result.calls), code=code)
        record = StageRecord(stage=stage, duration_ms=duration_ms, count=result.count, model=result.model)
        return state.model_copy(update={
            "stages": [*state.stages, record],
            "calls": [*state.calls, *result.calls],
            "mask_preview": [*state.mask_preview, *result.mask_preview],
            "validator": result.validator or state.validator,
            "dry_run": result.dry_run or ([] if stage == "author" else state.dry_run),
            "build_time_ms": (state.build_time_ms or 0) + duration_ms,
        })

    @staticmethod
    def _log(job_id: JobId, stage: Stage, duration_ms: int, spend_usd: float, *, code: str | None = None) -> None:
        line: dict[str, object] = {"job_id": job_id, "stage": stage, "duration_ms": duration_ms, "spend_usd": spend_usd}
        if code is not None:
            line["code"] = code
        logger.info(json.dumps(line))
