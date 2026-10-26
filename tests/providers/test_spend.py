"""Story 2.3: `SpendLedger` reserves, settles and caps every paid call over the `LedgerStore` port (AD-6)."""

import inspect
import re
import threading
from pathlib import Path

import pytest

from src.config import Settings
from src.domain.ledger import SEED_USD, LedgerEntry, SpendCapExceeded, fold, spark_cost_usd
from src.providers import mock as mock_module
from src.providers import spend as spend_module
from src.providers.base import ChatMessage
from src.providers.mock import MockProvider
from src.providers.spend import SpendLedger, new_call_id

REPO = Path(__file__).resolve().parents[2]
CALL_ID = re.compile(r"^call_[0-9A-HJKMNP-TV-Z]{26}$")
JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SESSION = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"
USAGE = {"prompt_tokens": 3000, "completion_tokens": 900, "prompt_tokens_details": {"cached_tokens": 1000}}


class MemoryLedgerStore:
    """The in-memory `LedgerStore` double; `pause_s` widens the read-then-append window for the race test."""

    def __init__(self, *entries: LedgerEntry, pause_s: float = 0.0) -> None:
        self.rows = list(entries)
        self.pause_s = pause_s

    def append(self, entry: LedgerEntry) -> None:
        self.rows.append(entry)

    def entries(self) -> list[LedgerEntry]:
        rows = list(self.rows)
        if self.pause_s:
            threading.Event().wait(self.pause_s)
        return rows


def settled(usd: float, kind: str = "vision") -> LedgerEntry:
    return LedgerEntry(call_id=new_call_id(), kind=kind, status="settled", usd=usd)


# --- Reserve, then settle under the same call_ id ---------------------------


def test_a_guarded_call_is_reserved_at_its_estimate_then_settled_at_its_observed_cost():
    store = MemoryLedgerStore()
    ledger = SpendLedger(store, cap_usd=60)
    call_id = ledger.guard("riddler", job_id=JOB, stage="author")
    assert CALL_ID.match(call_id)
    assert [(e.call_id, e.kind, e.status, e.usd, e.job_id, e.stage) for e in store.rows] == [
        (call_id, "riddler", "reserved", SEED_USD["riddler"], JOB, "author")
    ]
    assert ledger.running_total_usd() == pytest.approx(SEED_USD["riddler"])

    cost = spark_cost_usd(USAGE)
    entry = ledger.settle(call_id, cost)
    assert entry.call_id == call_id and entry.status == "settled" and entry.usd == cost
    assert [e.call_id for e in store.rows] == [call_id, call_id]
    assert fold(store.rows) == [entry]
    assert ledger.running_total_usd() == pytest.approx(cost)
    assert (entry.kind, entry.job_id, entry.stage) == ("riddler", JOB, "author")


def test_a_session_call_carries_its_session_id_and_the_estimate_follows_the_last_observed_cost():
    store = MemoryLedgerStore(settled(0.004, "trickster"))
    ledger = SpendLedger(store, cap_usd=60)
    call_id = ledger.guard("trickster", session_id=SESSION)
    reserved = store.rows[-1]
    assert (reserved.call_id, reserved.session_id, reserved.job_id, reserved.stage) == (call_id, SESSION, None, None)
    assert reserved.usd == 0.004


def test_settling_an_unknown_call_id_is_refused_and_appends_nothing():
    store = MemoryLedgerStore()
    ledger = SpendLedger(store, cap_usd=60)
    with pytest.raises(KeyError):
        ledger.settle(new_call_id(), 0.01)
    assert store.rows == []


def test_call_ids_are_fresh_prefixed_ulids():
    ids = {new_call_id() for _ in range(200)}
    assert len(ids) == 200 and all(CALL_ID.match(i) for i in ids)


# --- The cap -----------------------------------------------------------------


def test_a_call_whose_estimate_would_pass_the_cap_is_refused_before_it_is_made():
    store = MemoryLedgerStore(settled(0.5), LedgerEntry(call_id=new_call_id(), kind="riddler", status="reserved", usd=0.48))
    ledger = SpendLedger(store, cap_usd=1.0)
    with pytest.raises(SpendCapExceeded) as info:
        ledger.guard("riddler", job_id=JOB, stage="author")  # 0.98 + 0.03 > 1.0
    assert (info.value.cap_usd, info.value.running_total_usd) == (1.0, pytest.approx(0.98))
    assert "1.00 USD" in str(info.value) and "0.98 USD" in str(info.value)
    assert len(store.rows) == 2


def test_a_call_landing_exactly_on_the_cap_is_accepted():
    ledger = SpendLedger(MemoryLedgerStore(settled(0.97)), cap_usd=1.0)
    ledger.guard("riddler", job_id=JOB, stage="author")  # 0.97 + 0.03 == 1.0
    assert ledger.running_total_usd() == pytest.approx(1.0)


def test_racing_guards_are_serialized_and_never_pass_the_cap():
    # 0.90 settled, cap 1.00, trickster seed 0.01: exactly ten more calls fit.
    store = MemoryLedgerStore(settled(0.9), pause_s=0.002)
    ledger = SpendLedger(store, cap_usd=1.0)
    threads_n = 32
    start = threading.Barrier(threads_n)
    outcomes: list[str | SpendCapExceeded] = []
    lock = threading.Lock()

    def worker() -> None:
        start.wait()
        try:
            result: str | SpendCapExceeded = ledger.guard("trickster", session_id=SESSION)
        except SpendCapExceeded as exc:
            result = exc
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker) for _ in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    accepted = [o for o in outcomes if isinstance(o, str)]
    refused = [o for o in outcomes if isinstance(o, SpendCapExceeded)]
    assert (len(accepted), len(refused)) == (10, 22)
    assert ledger.running_total_usd() == pytest.approx(1.0)
    assert all(exc.cap_usd == 1.0 and exc.running_total_usd == pytest.approx(1.0) for exc in refused)


def test_each_store_is_capped_on_its_own_allocation_and_never_reads_the_other():
    local_store = MemoryLedgerStore(settled(60.0))
    hosted_store = MemoryLedgerStore(settled(19.0))
    local = SpendLedger(local_store, cap_usd=Settings.from_env({}).spend_cap_usd)
    hosted = SpendLedger(hosted_store, cap_usd=Settings.from_env({"SPEND_CAP_USD": "20"}).spend_cap_usd)

    with pytest.raises(SpendCapExceeded) as info:
        local.guard("sam", job_id=JOB, stage="segment")
    assert (info.value.cap_usd, info.value.running_total_usd) == (60, 60.0)
    assert hosted.guard("sam", job_id=JOB, stage="segment")
    assert [e.usd for e in local_store.rows] == [60.0]
    assert hosted.running_total_usd() == pytest.approx(19.0025) and local.running_total_usd() == 60.0
    assert local.cap_usd + hosted.cap_usd == 80


def test_settings_default_the_local_allocation_and_an_explicit_cap_overrides_it():
    assert Settings.from_env({}).spend_cap_usd == 60
    assert Settings.from_env({"SPEND_CAP_USD": "20"}).spend_cap_usd == 20
    assert Settings.from_env({"SPEND_CAP_USD": "5"}).spend_cap_usd == 5


def test_no_module_holds_date_logic_for_the_allocations():
    for rel in ("config.py", "domain/ledger.py", "providers/spend.py", "pipeline/ports.py"):
        source = (REPO / "src" / rel).read_text()
        assert "datetime" not in source and "zoneinfo" not in source and "calendar" not in source, rel
        assert "Nov" not in source and "2026-11" not in source, rel


# --- One entry per call, and the mock bypass ----------------------------------


def test_a_call_retried_once_inside_one_guard_holds_one_entry_under_one_call_id():
    store = MemoryLedgerStore()
    ledger = SpendLedger(store, cap_usd=60)
    attempts = [ConnectionError("retryable"), USAGE]

    def post() -> dict:
        outcome = attempts.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    call_id = ledger.guard("riddler", job_id=JOB, stage="author")
    for _ in range(2):
        try:
            usage = post()
            break
        except ConnectionError:
            continue
    ledger.settle(call_id, spark_cost_usd(usage))

    assert attempts == []
    assert {e.call_id for e in store.rows} == {call_id}
    assert len(fold(store.rows)) == 1 and fold(store.rows)[0].usd == spark_cost_usd(USAGE)


@pytest.mark.parametrize("role", ["architect", "riddler", "dryrun", "trickster", "image"])
def test_the_mock_appends_no_entry_and_is_never_refused_even_past_the_cap(role):
    store = MemoryLedgerStore(settled(60.0))
    ledger = SpendLedger(store, cap_usd=60)
    with pytest.raises(SpendCapExceeded):
        ledger.guard("riddler", job_id=JOB, stage="author")
    mock = MockProvider(role)
    assert mock.chat([ChatMessage(role="user", content="hi")]).text
    assert mock.segment("lamp", b"jpeg")
    assert mock.generate_image("a wizard").data
    assert len(store.rows) == 1 and len(mock.calls) == 3
    assert "ledger" not in inspect.signature(MockProvider.__init__).parameters
    assert "spend" not in inspect.getsource(mock_module)


def test_guard_and_settle_run_under_one_lock():
    source = inspect.getsource(spend_module)
    assert "threading.Lock()" in source
    assert all("with self._lock:" in inspect.getsource(getattr(SpendLedger, m)) for m in ("guard", "settle", "running_total_usd"))
