"""Story 2.15: the architect stage makes one `chat` call over the 2.14 prompt and keeps the answer verbatim (AD-7, AD-16, AD-18)."""

import json
import re

import pytest

from src.council.architect import build_architect_prompt
from src.domain.schema import ArchitectResponse, StageRecord
from src.pipeline.architect import ARCHITECT_BUDGET_MS, ARCHITECT_MODEL, architect_key, read_architect, run_architect
from src.pipeline.build import STAGES
from src.pipeline.ingest import read_photos
from src.providers.base import ProviderError
from src.providers.mock import ChatCall, MockProvider, MockScript
from tests.pipeline.stages import ONE_AREA, Segmenter, architect_mock, build_over, candidate, labels, square

VERBATIM = ["No. 7 ", "ÉCOLE", "1947", "", "two words"]
CANDIDATES = [
    candidate("brass key", photo=2, box=(100, 200, 300, 400), attributes=VERBATIM, confidence=0.9),
    candidate("row of books", photo=5, box=(0, 0, 1000, 1000), plural=True, confidence=0.4),
    *labels(4),
]
MASKS = {c["label"]: [square(130, 100, 380, 285)] for c in CANDIDATES}


def test_one_chat_call_through_the_architect_role_over_the_2_14_prompt_records_one_call_row(jobs, artifacts, ticker, doubles, uploads):
    architect = architect_mock(CANDIDATES)
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect, segmenter=Segmenter(MASKS))
    done = build.run(build.submit(uploads).id)
    assert done.status == "done"
    photos = [artifacts.read(p.downscaled_path) for p in read_photos(done.room_id, artifacts)]
    assert len(architect.calls) == 1
    call = architect.calls[0]
    assert isinstance(call, ChatCall)
    assert call.images == photos == [u.downscale for u in uploads]
    assert call.messages == build_architect_prompt(photos).messages
    assert call.response_schema is ArchitectResponse and call.reasoning_effort == "low"
    rows = [row for row in done.calls if row.model == ARCHITECT_MODEL]
    assert len(rows) == 1 and rows[0].role == "architect" and rows[0].host == "mock"
    assert re.fullmatch(r"call_[0-9A-HJKMNP-TV-Z]{26}", rows[0].id)
    assert done.stages[1] == StageRecord(stage="architect", duration_ms=0, count=len(CANDIDATES), model="muse-spark-1.3")


def test_each_candidate_is_kept_by_list_position_with_its_attributes_verbatim_and_no_id(jobs, artifacts, ticker, doubles, uploads):
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect_mock(CANDIDATES), segmenter=Segmenter(MASKS))
    done = build.run(build.submit(uploads).id)
    stored = read_architect(done.room_id, artifacts)
    assert stored == ArchitectResponse.model_validate({"candidates": CANDIDATES, "photos": ONE_AREA})
    assert [(c.label, c.photo, c.box) for c in stored.candidates] == [(c["label"], c["photo"], tuple(c["box"])) for c in CANDIDATES]
    assert stored.candidates[0].attributes == VERBATIM
    raw = artifacts.read(architect_key(done.room_id)).decode()
    assert json.loads(raw)["candidates"][0]["attributes"] == VERBATIM
    assert "ix_" not in raw and '"id"' not in raw


def test_the_stage_reads_the_photos_from_the_store_and_needs_a_room(jobs, artifacts, ticker, doubles, uploads):
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect_mock(CANDIDATES), segmenter=Segmenter(MASKS))
    queued = build.submit(uploads)
    with pytest.raises(ValueError, match="names no room"):
        run_architect(queued.model_copy(update={"room_id": None}), provider=architect_mock(CANDIDATES), artifacts=artifacts)
    assert jobs.read(queued.id) == queued


def test_a_provider_error_ends_the_build_failed_at_architect(jobs, artifacts, ticker, doubles, uploads):
    class Failing(MockProvider):
        def chat(self, *args, **kwargs):
            raise ProviderError(503, "service_overloaded", "still overloaded after the retry")

    build = build_over(jobs, artifacts, ticker, doubles, architect=Failing("architect"), segmenter=Segmenter(MASKS))
    failed = build.run(build.submit(uploads).id)
    assert (failed.status, failed.stage, failed.error.code) == ("failed", "architect", "provider_error")
    assert doubles.calls == [] and [r.stage for r in failed.stages] == ["ingest"]
    with pytest.raises(KeyError):
        read_architect(failed.room_id, artifacts)


NO_CONFIDENCE = {k: v for k, v in candidate("brass key").items() if k != "confidence"}
BAD_REPLIES = {
    "missing_field": json.dumps({"candidates": [NO_CONFIDENCE, *labels(5)]}),
    "out_of_range": json.dumps({"candidates": [candidate("brass key", confidence=1.5), *labels(5)]}),
    "not_json": "Here are the objects I found: a brass key and a row of books.",
}


@pytest.mark.parametrize("reply", BAD_REPLIES.values(), ids=BAD_REPLIES.keys())
def test_a_reply_off_the_response_shape_ends_the_build_failed_at_architect_as_a_provider_error(jobs, artifacts, ticker, doubles, uploads, reply):
    architect = MockProvider("architect", MockScript(chat=[reply]))
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect, segmenter=Segmenter(MASKS))
    failed = build.run(build.submit(uploads).id)
    assert (failed.status, failed.stage, failed.error.code) == ("failed", "architect", "provider_error")
    assert failed.error.message == "200 malformed: the Architect reply did not follow the response shape"
    assert "input_value" not in failed.error.message and "brass key" not in failed.error.message
    assert doubles.calls == [] and [r.stage for r in failed.stages] == ["ingest"]
    with pytest.raises(KeyError):
        read_architect(failed.room_id, artifacts)


def test_the_15_s_budget_is_measured_from_the_build_clock_and_never_enforced(jobs, artifacts, ticker, doubles, uploads):
    class Slow(MockProvider):
        def chat(self, *args, **kwargs):
            ticker.advance_ms(16_000)
            return super().chat(*args, **kwargs)

    assert ARCHITECT_BUDGET_MS == 15_000
    architect = Slow("architect", MockScript(chat=[json.dumps({"candidates": CANDIDATES})]))
    build = build_over(jobs, artifacts, ticker, doubles, architect=architect, segmenter=Segmenter(MASKS))
    done = build.run(build.submit(uploads).id)
    assert done.status == "done" and done.error is None
    assert {r.stage: r.duration_ms for r in done.stages}["architect"] == 16_000 > ARCHITECT_BUDGET_MS
    assert [r.stage for r in done.stages] == list(STAGES)
