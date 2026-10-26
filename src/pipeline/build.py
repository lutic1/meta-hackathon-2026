"""The stage runner (AD-7): a persisted, resumable Build job, and the one writer of its state.

`Build.submit(uploads)` refuses a bad upload before any job exists, then
mints the `job_` and `room_` ids, runs ingest and persists the job `queued`
for `JobRunner.start(job_id)`. `Build.run(job_id)` rereads job state from
`JobStore` on entry and runs the stages after the last persisted one, in
order, persisting state after each stage with its duration from the build
clock, which never sees `DEMO_TIMESCALE` (AD-10); a terminal job is left as
it is, so a restart after scene never rewrites anything. Each stage after
ingest is a `StageFn` injected by wiring; what it returns (done-row count,
model id, call rows, sent-back messages) goes into job state beside the
timing (AD-16), and the build time is the sum of the finished stages. An
error raised by a stage ends the job `failed` with that stage and the
class name in snake_case (`spend_cap_exceeded`, `provider_error`; AD-13);
the runner itself sets only `queued`, `running`, `done` and `failed`.
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
    ErrorDetail,
    JobId,
    JobState,
    JobStatus,
    SentBack,
    Stage,
    StageRecord,
)
from src.pipeline.ingest import IngestRefused, Upload, store_upload, validate_upload
from src.pipeline.ports import ArtifactStore, Clock, JobStore

logger = logging.getLogger(__name__)

STAGES: tuple[Stage, ...] = ("ingest", "architect", "segment", "author", "validate", "dryrun", "scene")
TERMINAL: frozenset[JobStatus] = frozenset(get_args(JobStatus)) - {"queued", "running"}
"""Every status a job stays in; the runner reaches `done` and `failed` itself."""
CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_id(prefix: str) -> str:
    """A fresh prefixed ULID (AD-18): 48 bits of Unix milliseconds then 80 random bits, Crockford base32."""
    value = (time.time_ns() // 1_000_000) << 80 | int.from_bytes(secrets.token_bytes(10))
    return f"{prefix}_" + "".join(CROCKFORD_BASE32[(value >> shift) & 31] for shift in range(125, -1, -5))


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
    """What a finished stage adds to job state beside its timing: its done row, call rows and sent-back messages."""

    count: int | None = None
    model: str | None = None
    calls: list[CallRow] = field(default_factory=list)
    sent_back: list[SentBack] = field(default_factory=list)


type StageFn = Callable[[JobState], StageResult]
"""A stage after ingest: given the persisted job state, it reads the artifacts it needs and returns what it adds."""


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
        """Refuse the upload before any job exists, else mint the ids, run ingest and persist the job `queued`."""
        validate_upload(uploads)
        room_id = new_id("room")
        state = JobState(id=new_id("job"), status="running", stage="ingest", room_id=room_id, regen_max=self._regen_max)
        state = self._finish(state, "ingest", lambda _: StageResult(count=len(store_upload(uploads, room_id, self._artifacts))))
        if state.status == "failed":
            return self._put(state)
        return self._put(state.model_copy(update={"status": "queued", "stage": None}))

    def run(self, job_id: JobId) -> JobState:
        """Reread the job and run every stage after its last persisted one, in order; a terminal job is left as it is."""
        state = self._jobs.read(job_id)
        if state.status in TERMINAL:
            return state
        if not state.stages:
            raise ValueError(f"{job_id} holds no ingest record to resume from")
        for stage in STAGES[STAGES.index(state.stages[-1].stage) + 1:]:
            state = self._put(state.model_copy(update={"status": "running", "stage": stage}))
            state = self._put(self._finish(state, stage, self._stages[stage]))
            if state.status == "failed":
                return state
        return self._put(state.model_copy(update={"status": "done", "stage": None}))

    def _put(self, state: JobState) -> JobState:
        self._jobs.put(state)
        return state

    def _finish(self, state: JobState, stage: Stage, fn: StageFn) -> JobState:
        """Run `stage` against the build clock: the state with its record appended, or `failed` at that stage."""
        start = self._clock.now_ms()
        try:
            result = fn(state)
        except Exception as exc:  # noqa: BLE001 - any error a stage raises ends the job failed (AD-13)
            duration_ms = self._clock.now_ms() - start
            self._log(state.id, stage, duration_ms, 0.0, code=error_code(exc))
            return state.model_copy(update={"status": "failed", "stage": stage, "error": error_detail(exc, stage)})
        duration_ms = self._clock.now_ms() - start
        spend_usd = sum(row.spend_usd for row in result.calls)
        self._log(state.id, stage, duration_ms, spend_usd)
        record = StageRecord(stage=stage, duration_ms=duration_ms, count=result.count, model=result.model)
        return state.model_copy(update={
            "stages": [*state.stages, record],
            "calls": [*state.calls, *result.calls],
            "sent_back": [*state.sent_back, *result.sent_back],
            "build_time_ms": (state.build_time_ms or 0) + duration_ms,
        })

    @staticmethod
    def _log(job_id: JobId, stage: Stage, duration_ms: int, spend_usd: float, *, code: str | None = None) -> None:
        line: dict[str, object] = {"job_id": job_id, "stage": stage, "duration_ms": duration_ms, "spend_usd": spend_usd}
        if code is not None:
            line["code"] = code
        logger.info(json.dumps(line))
