"""Story 2.5: the jsonl `LedgerStore` under a file lock outside `.cache/`, and the disk `Cache` under `.cache/` (AD-9)."""

import fcntl
import inspect
import json
import shutil
import threading
from pathlib import Path

import pytest

from src.domain.ledger import SEED_USD, LedgerEntry, SpendCapExceeded, running_total_usd
from src.infra import local as local_module
from src.infra.local import CACHE_ROOT, LEDGER_PATH, DiskCache, JsonlLedgerStore
from src.providers.base import ChatMessage, ChatResponse
from src.providers.cache import GuardedCalls, cache_key
from src.providers.spend import SpendLedger
from tests.providers.test_cache import Provider
from tests.providers.test_spend import JOB, settled

REPLY = ChatResponse(text='{"ok": true}', model="muse-spark-1.3", usage={"prompt_tokens": 10, "completion_tokens": 5}, raw={"id": "x"})
KEY = cache_key("muse-spark-1.3", messages=[ChatMessage(role="user", content="Write four puzzles.")])


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A repository root: the ledger at `spend/ledger.jsonl`, the cache under `.cache/`."""
    return tmp_path


def ledger_store(root: Path) -> JsonlLedgerStore:
    return JsonlLedgerStore(root / LEDGER_PATH)


def lines(root: Path) -> list[dict]:
    return [json.loads(line) for line in (root / LEDGER_PATH).read_text().splitlines()]


# --- The ledger file: one line per entry, under a file lock, outside .cache/ ----


def test_entries_are_appended_one_per_line_to_spend_ledger_jsonl_outside_the_cache(root):
    store = ledger_store(root)
    first, second = settled(0.5), settled(0.25, "sam")
    store.append(first)
    store.append(second)

    assert (root / "spend" / "ledger.jsonl").is_file()
    assert LEDGER_PATH == Path("spend/ledger.jsonl") and CACHE_ROOT == Path(".cache")
    assert not LEDGER_PATH.is_relative_to(CACHE_ROOT) and not (root / ".cache").exists()
    assert lines(root) == [first.model_dump(), second.model_dump()]
    assert store.entries() == [first, second]
    assert (root / LEDGER_PATH).read_text().endswith("\n")


def test_a_missing_file_reads_as_no_entries(root):
    assert ledger_store(root).entries() == []


def test_two_concurrent_writers_leave_every_entry_intact_one_per_line(root):
    writers = [ledger_store(root) for _ in range(2)]
    batches = [[settled(0.001 * i, "trickster") for i in range(200)] for _ in writers]
    start = threading.Barrier(len(writers))

    def write(store: JsonlLedgerStore, batch: list[LedgerEntry]) -> None:
        start.wait()
        for entry in batch:
            store.append(entry)

    threads = [threading.Thread(target=write, args=(w, b)) for w, b in zip(writers, batches)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    rows = lines(root)
    assert len(rows) == 400
    assert {row["call_id"] for row in rows} == {e.call_id for batch in batches for e in batch}
    assert sorted(ledger_store(root).entries(), key=lambda e: e.call_id) == sorted((e for b in batches for e in b), key=lambda e: e.call_id)


def test_an_append_waits_for_the_file_lock_held_by_another_writer(root):
    store = ledger_store(root)
    store.append(settled(0.1))
    appended = threading.Event()

    with (root / LEDGER_PATH).open("a") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX)
        thread = threading.Thread(target=lambda: (store.append(settled(0.2)), appended.set()))
        thread.start()
        assert not appended.wait(0.2)
        assert len(lines(root)) == 1
        fcntl.flock(held.fileno(), fcntl.LOCK_UN)
    thread.join(timeout=5)
    assert appended.is_set() and len(lines(root)) == 2
    assert "fcntl.flock" in inspect.getsource(local_module)


def test_append_stores_under_the_current_epoch_and_entries_returns_only_that_epoch(root):
    store = ledger_store(root)
    before = settled(1.0)
    store.append(before)
    with (root / LEDGER_PATH).open("a") as file:
        file.write(json.dumps({"epoch": "2026-11-05"}) + "\n")
    after = settled(0.5)
    store.append(after)

    stamped = LedgerEntry.model_validate({**after.model_dump(), "epoch": "2026-11-05"})
    assert lines(root)[-1] == stamped.model_dump() and lines(root)[0]["epoch"] is None
    assert store.entries() == [stamped]
    assert SpendLedger(store, cap_usd=60).running_total_usd() == pytest.approx(0.5)


# --- The total survives a restart ---------------------------------------------


def test_a_new_spend_ledger_over_the_same_file_sees_the_total_and_enforces_the_cap_against_it(root):
    ledger = SpendLedger(ledger_store(root), cap_usd=1.0)
    ledger.settle(ledger.guard("vision", job_id=JOB, stage="ingest"), 0.5)
    ledger.settle(ledger.guard("riddler", job_id=JOB, stage="author"), 0.45)
    pending = ledger.guard("trickster")
    total = ledger.running_total_usd()
    assert total == pytest.approx(0.95 + SEED_USD["trickster"])

    restarted = SpendLedger(ledger_store(root), cap_usd=1.0)
    assert restarted.running_total_usd() == pytest.approx(total)
    assert running_total_usd(restarted._store.entries()) == pytest.approx(total)
    with pytest.raises(SpendCapExceeded) as info:
        restarted.guard("riddler", job_id=JOB, stage="author")  # 0.96 + 0.45 > 1.0
    assert info.value.running_total_usd == pytest.approx(total)
    assert restarted.settle(pending, 0.004).usd == 0.004
    assert restarted.running_total_usd() == pytest.approx(0.954)
    assert len(lines(root)) == 6


# --- The disk cache -------------------------------------------------------------


def test_a_put_response_is_returned_by_a_new_cache_over_the_same_root(root):
    cache = DiskCache(root / CACHE_ROOT)
    assert cache.get(KEY) is None
    value = {"text": REPLY.text, "model": REPLY.model, "usage": REPLY.usage, "raw": REPLY.raw}
    cache.put(KEY, value)

    assert DiskCache(root / CACHE_ROOT).get(KEY) == value
    assert sorted(p.name for p in (root / ".cache").iterdir()) == [f"{KEY}.json"]
    assert not (root / "spend").exists()


def test_a_put_replaces_the_previous_value_under_the_key(root):
    cache = DiskCache(root / CACHE_ROOT)
    cache.put(KEY, {"text": "first"})
    cache.put(KEY, {"text": "second"})
    assert cache.get(KEY) == {"text": "second"}
    assert [p.name for p in (root / ".cache").iterdir()] == [f"{KEY}.json"]


def test_deleting_the_cache_leaves_the_ledger_and_exports_unchanged_and_the_next_call_is_priced_again(root):
    export = root / "spend" / "exports" / "ledger-2026-10-26.json"
    export.parent.mkdir(parents=True)
    export.write_text('{"total_usd": 0.0}')
    ledger = SpendLedger(ledger_store(root), cap_usd=60)
    calls = GuardedCalls(DiskCache(root / CACHE_ROOT), ledger, host="api.meta.ai")
    provider = Provider((REPLY, 0.0125), (REPLY, 0.0125))

    billed = calls.chat(KEY, "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")[1]
    hit = calls.chat(KEY, "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")[1]
    assert (billed.cached, hit.cached, provider.calls) == (False, True, 1)
    ledger_bytes = (root / LEDGER_PATH).read_bytes()
    total = ledger.running_total_usd()

    shutil.rmtree(root / CACHE_ROOT)

    assert (root / LEDGER_PATH).read_bytes() == ledger_bytes
    assert export.read_text() == '{"total_usd": 0.0}'
    assert ledger.running_total_usd() == pytest.approx(total) == pytest.approx(0.0125)
    response, again = calls.chat(KEY, "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")
    assert response == REPLY and (again.cached, again.spend_usd, provider.calls) == (False, 0.0125, 2)
    assert ledger.running_total_usd() == pytest.approx(0.025)
    assert [e["status"] for e in lines(root)] == ["reserved", "settled", "reserved", "settled"]
    assert DiskCache(root / CACHE_ROOT).get(KEY) is not None
