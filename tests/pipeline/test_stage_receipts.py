"""Stories 2.15 and 2.20: the architect and segment stages record each call's receipt and tag its ledger entry (AD-6, AD-15, AD-16).

Two Builds over the same photos share one cache, as `CACHE=on` does: the
first is billed and every ledger entry names its job and stage, so
provenance sums spend for both stages; the second is served from the
cache, so its rows read cached and the Room is disclosed as built earlier.
"""

import json

import httpx

from src.api.meta import built_earlier
from src.api.wiring import ROLE_CALLS
from src.domain.schema import CallRow, JobState
from src.pipeline.author import assemble_provenance
from src.pipeline.segment import SEGMENT_MODEL
from src.providers.cache import GuardedCalls
from src.providers.meta_api import CHAT_MODEL, MetaModelProvider
from src.providers.spend import SpendLedger
from tests.pipeline.stages import build_over, labels
from tests.providers.replay import load
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

HOST = "api.meta.ai"
CANDIDATES = labels(6)


def reply(request: httpx.Request) -> httpx.Response:
    """Meta's chat endpoint answering the Architect with six candidates, and sam-3.1 with two masks."""
    if request.url.path.endswith("/responses"):
        return httpx.Response(200, json=load("sam-3.1/segment-two-masks").body)
    body = load("muse-spark-1.3/chat-three-objects").body
    choice = {**body["choices"][0], "message": {"role": "assistant", "content": json.dumps({"candidates": CANDIDATES})}}
    return httpx.Response(200, json={**body, "choices": [choice]})


def rows(job: JobState, model: str) -> list[CallRow]:
    return [row for row in job.calls if row.model == model]


def test_architect_and_segment_rows_carry_their_receipts_and_their_ledger_entries_name_job_and_stage(jobs, artifacts, ticker, doubles, uploads, four_lock_room):
    ledger = MemoryLedgerStore()
    calls = GuardedCalls(MemoryCache(), SpendLedger(ledger, cap_usd=60.0), host=HOST)
    kind, budget_s = ROLE_CALLS["architect"]
    meta = MetaModelProvider("test-key", calls=calls, chat_kind=kind, budget_s=budget_s, transport=httpx.MockTransport(reply))
    build = build_over(jobs, artifacts, ticker, doubles, architect=meta, segmenter=meta)

    first = build.run(build.submit(uploads).id)
    assert first.status == "done", first.error
    billed = rows(first, CHAT_MODEL) + rows(first, SEGMENT_MODEL)
    assert len(rows(first, CHAT_MODEL)) == 1 and len(rows(first, SEGMENT_MODEL)) == len(CANDIDATES)
    assert all(row.host == HOST and not row.cached and row.spend_usd > 0 for row in billed)
    entries = ledger.entries()
    assert {row.id for row in billed} == {entry.call_id for entry in entries}
    assert {(entry.job_id, entry.stage) for entry in entries} == {(first.id, "architect"), (first.id, "segment")}
    spend = assemble_provenance(first, entries, {}).spend_per_stage_usd
    assert spend["architect"] > 0 and spend["segment"] > 0

    second = build.run(build.submit(uploads).id)
    assert second.status == "done", second.error
    cached = rows(second, CHAT_MODEL) + rows(second, SEGMENT_MODEL)
    assert len(cached) == 1 + len(CANDIDATES)
    assert all(row.host == HOST and row.cached and row.spend_usd == 0 for row in cached)
    assert ledger.entries() == entries
    assert built_earlier(four_lock_room, second, earlier_session=False)
