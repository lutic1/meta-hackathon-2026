"""Story 7.8: the daily hosted ledger snapshot on the `keyframe-data` Volume (AD-9, FR-29).

No test reaches Modal: the `keyframe-ledger` Dict is a plain dict and the
Volume a temporary directory behind a stub that logs `commit`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.domain.ledger import LedgerEntry, running_total_usd, settle
from src.infra.modal import DictLedgerStore, ModalHandles, export_hosted_ledger, snapshot_path
from src.providers.spend import new_call_id
from tests.infra.test_modal import RecordingDict, StubVolume

DAY = date(2026, 10, 27)


@pytest.fixture
def log() -> list[str]:
    return []


@pytest.fixture
def handles(tmp_path: Path, log: list[str]) -> ModalHandles:
    return ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume(log), root=tmp_path / "data")


def _entry(usd: float, **fields: object) -> LedgerEntry:
    return LedgerEntry.model_validate({"call_id": new_call_id(), "kind": "vision", "status": "settled", "usd": usd, **fields})


def _snapshot(handles: ModalHandles, day: date = DAY) -> list[LedgerEntry]:
    lines = (handles.root / snapshot_path(day)).read_text().splitlines()
    return [LedgerEntry.model_validate_json(line) for line in lines]


def test_the_snapshot_path_is_spend_hosted_date_jsonl():
    assert snapshot_path(DAY) == "spend/hosted-2026-10-27.jsonl"


def test_every_entry_is_one_json_line_on_the_volume_committed_and_the_total_matches_the_store(handles, log):
    store = DictLedgerStore(handles.ledger)
    reserved = _entry(0.03, kind="riddler", status="reserved", job_id="job_01ARZ3NDEKTSV4RRFFQ69G5FAV", stage="author")
    store.append(reserved)
    store.append(_entry(0.0025, kind="sam"))
    store.append(_entry(0.01, kind="trickster", session_id="sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"))
    store.append(settle(reserved, 0.022))  # replaces its reserved entry under the same key
    exported = export_hosted_ledger(handles, DAY)
    assert exported == store.entries() and len(exported) == 3
    assert _snapshot(handles) == store.entries()
    assert sum(entry.usd for entry in _snapshot(handles)) == pytest.approx(running_total_usd(store.entries()))
    assert running_total_usd(_snapshot(handles)) == pytest.approx(0.0345)
    assert log == ["commit"]
    assert [path.relative_to(handles.root).as_posix() for path in handles.root.rglob("*") if path.is_file()] == [snapshot_path(DAY)]


def test_an_empty_ledger_writes_an_empty_snapshot_and_does_not_fail(handles, log):
    assert export_hosted_ledger(handles, DAY) == []
    assert (handles.root / snapshot_path(DAY)).read_bytes() == b"" and log == ["commit"]


def test_a_snapshot_after_a_reset_holds_only_the_current_epochs_entries(handles):
    store = DictLedgerStore(handles.ledger)
    store.append(_entry(0.5))
    store.start_epoch("2026-11-05")
    later = _entry(0.03)
    store.append(later)
    export_hosted_ledger(handles, DAY)
    assert _snapshot(handles) == [later.model_copy(update={"epoch": "2026-11-05"})]


def test_a_second_run_on_the_same_day_replaces_that_days_snapshot_and_leaves_earlier_days(handles):
    store = DictLedgerStore(handles.ledger)
    first = _entry(0.03)
    store.append(first)
    export_hosted_ledger(handles, date(2026, 10, 26))
    export_hosted_ledger(handles, DAY)
    second = _entry(0.01)
    store.append(second)
    export_hosted_ledger(handles, DAY)
    assert _snapshot(handles, date(2026, 10, 26)) == [first]
    assert _snapshot(handles) == [first, second]
