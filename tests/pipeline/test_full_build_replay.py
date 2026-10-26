"""Story 2.24: the SIT-03 full Build's recorded Architect, Riddler and Dry run replies replay offline through the wired stages to its recorded job record."""

import json
import re
from pathlib import Path

import httpx

from src.api.wiring import ROLE_CALLS, build_stages
from src.domain.schema import JobState, Role
from src.infra.clocks import BuildClock
from src.infra.local import DiskArtifactStore
from src.pipeline.build import Build
from src.pipeline.ingest import MIN_PHOTOS
from src.pipeline.ports import room_key
from src.providers.cache import GuardedCalls
from src.providers.meta_api import MetaModelProvider
from src.providers.spend import SpendLedger
from tests.infra.test_clocks import Ticker
from tests.pipeline.test_build import MemoryJobStore
from tests.pipeline.test_dryrun_stage import keys
from tests.pipeline.uploads import make_uploads
from tests.providers.replay import load
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

JOB = Path(__file__).resolve().parents[1] / "fixtures/jobs/full-build.json"
"""SIT-03's job record (`tests/sit/test_09_full_build.py`); it holds verdicts, never a solution or an answer."""
RECORDED = {
    "ArchitectResponse": "muse-spark-1.3/chat-full-build-architect",
    "RiddlerResponse": "muse-spark-1.3/chat-full-build-riddler",
    "DryRunAnswers": "muse-spark-1.3/chat-full-build-dry-run",
}
"""SIT-03's last chat reply per role, by the response schema its request names."""
SEGMENT = "sam-3.1/segment-no-mask"
"""Every object keeps its Architect box; the Build's own segment responses are not recorded."""
LISTED_IN_RIDDLER = re.compile(r'"id": "(ix_\w+)",\s*"label": "([^"]+)"')
LISTED_IN_DRY_RUN = re.compile(r"^- (ix_\w+): (.+)$", re.MULTILINE)
PUZZLES_IN_DRY_RUN = re.compile(r"^Puzzle (pz_\w+)$", re.MULTILINE)
SOLUTION_KEYS = {"solution", "answer", "answers"}


def job_record() -> JobState:
    return JobState.model_validate_json(JOB.read_bytes())


def user_text(body: dict) -> str:
    content = next(m["content"] for m in body["messages"] if m["role"] == "user")
    return content if isinstance(content, str) else "".join(part.get("text", "") for part in content)


class Replay:
    """Meta's chat and segment endpoints serving the SIT-03 recordings, the live Build's ids rewritten to this Build's.

    The job record's Mask preview gives each live `ix_` id's label and its Dry run verdicts the live `pz_`
    ids in Puzzle order; each prompt lists this Build's ids, so a recorded id becomes the one with its label or place.
    """

    def __init__(self, job: JobState) -> None:
        self.labels = {preview.id: preview.label for preview in job.mask_preview}
        self.puzzles = [verdict.puzzle_id for verdict in job.dry_run]
        self.schemas: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/responses"):
            return httpx.Response(200, json=load(SEGMENT).body)
        body = json.loads(request.content)
        schema = body["response_format"]["json_schema"]["name"]
        self.schemas.append(schema)
        fixture = load(RECORDED[schema])
        prompt = user_text(body)
        listed = {label: ix for ix, label in [*LISTED_IN_RIDDLER.findall(prompt), *LISTED_IN_DRY_RUN.findall(prompt)]}
        renamed = {old: listed[label] for old, label in self.labels.items() if label in listed}
        if schema == "DryRunAnswers":
            renamed |= dict(zip(self.puzzles, PUZZLES_IN_DRY_RUN.findall(prompt), strict=True))
        choice = fixture.body["choices"][0]
        text = choice["message"]["content"]
        for old, new in renamed.items():
            text = text.replace(old, new)
        return httpx.Response(fixture.status, json={**fixture.body, "choices": [{**choice, "message": {**choice["message"], "content": text}}]})


def test_the_recorded_full_build_replays_through_the_wired_stages_to_its_recorded_outcome(tmp_path):
    job = job_record()
    dry_run = any(verdict.verdict != "skipped" for verdict in job.dry_run)  # cut 4 records no Dry run reply
    replay, ledger = Replay(job), MemoryLedgerStore()
    providers: dict[Role, MetaModelProvider] = {
        role: MetaModelProvider(
            "test-key",
            calls=GuardedCalls(MemoryCache(), SpendLedger(ledger, cap_usd=60.0), host="api.meta.ai"),
            chat_kind=ROLE_CALLS[role][0],
            budget_s=ROLE_CALLS[role][1],
            transport=httpx.MockTransport(replay),
        )
        for role in ("architect", "riddler", "dryrun")
    }
    artifacts = DiskArtifactStore(tmp_path / "rooms")
    stages = build_stages(providers, artifacts, ledger, dry_run=dry_run)
    build = Build(jobs=MemoryJobStore(), artifacts=artifacts, clock=BuildClock(monotonic_ns=Ticker()), stages=stages, regen_max=job.regen_max)

    replayed = build.run(build.submit(make_uploads(MIN_PHOTOS)).id)

    assert replayed.status == "done", replayed.error
    assert replay.schemas == ["ArchitectResponse", "RiddlerResponse", *(["DryRunAnswers"] if dry_run else [])]
    assert replayed.regeneration_count == 0  # the recorded draft is the one that shipped
    assert replayed.validator == job.validator and all(verdict.passed for verdict in replayed.validator)
    assert [verdict.verdict for verdict in replayed.dry_run] == [verdict.verdict for verdict in job.dry_run]
    assert [preview.label for preview in replayed.mask_preview] == [preview.label for preview in job.mask_preview]
    counts = {record.stage: record.count for record in replayed.stages}
    assert counts == {record.stage: record.count for record in job.stages}
    assert artifacts.read(room_key(replayed.room_id))


def test_the_recorded_job_record_is_a_done_build_that_holds_no_solution_or_answer():
    raw = json.loads(JOB.read_bytes())
    job = job_record()
    assert job.status == "done" and job.error is None
    assert keys(raw).isdisjoint(SOLUTION_KEYS)
    answers = json.loads(load(RECORDED["DryRunAnswers"]).body["choices"][0]["message"]["content"])["answers"]
    codes = [answer["answer"]["code"] for answer in answers if answer["answer"]["lock_type"] == "code"]
    assert all(f'"{code}"' not in JOB.read_text() for code in codes)
