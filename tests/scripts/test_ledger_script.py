"""Story 2.6: `scripts/ledger.py export|reset`, the dated export and the reset that refuses without it (AD-6, AD-9)."""

import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from src.domain.ledger import SpendCapExceeded
from src.infra.local import EXPORTS_ROOT, LEDGER_PATH, JsonlLedgerStore
from src.providers.spend import SpendLedger
from tests.providers.test_spend import MemoryLedgerStore, settled

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/ledger.py"
OCT_26, NOV_4, NOV_5 = date(2026, 10, 26), date(2026, 11, 4), date(2026, 11, 5)


def _load():
    spec = importlib.util.spec_from_file_location("ledger_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = _load()


@pytest.fixture
def root(tmp_path: Path, monkeypatch) -> Path:
    """A repository root with the default allocations: local 60 and hosted 20, the 80 ceiling."""
    monkeypatch.setenv("SPEND_CAP_USD", "")
    return tmp_path


def store(root: Path) -> JsonlLedgerStore:
    return JsonlLedgerStore(root / LEDGER_PATH)


def export_file(root: Path, today: date) -> Path:
    return root / EXPORTS_ROOT / f"ledger-{today.isoformat()}.json"


# --- export ---------------------------------------------------------------------


def test_export_writes_todays_file_and_prints_the_three_totals_beside_the_ceiling(root, capsys):
    store(root).append(settled(0.5))
    store(root).append(settled(0.25, "sam"))

    assert ledger.main(["export"], root=root, today=OCT_26) == 0

    written = json.loads(export_file(root, OCT_26).read_text())
    assert [e["usd"] for e in written["entries"]] == [0.5, 0.25]
    assert (written["local_total_usd"], written["hosted_total_usd"], written["total_usd"]) == (0.75, 0.0, 0.75)
    assert (written["ceiling_usd"], written["epoch"], written["date"]) == (80.0, None, "2026-10-26")
    out = capsys.readouterr()
    lines = out.out.splitlines()
    assert lines[0] == "wrote spend/exports/ledger-2026-10-26.json: 2 entries, epoch none"
    assert lines[1].startswith("local total") and "0.75 USD" in lines[1] and "80.00 USD combined ceiling" in lines[1]
    assert lines[2].startswith("hosted total") and "0.00 USD" in lines[2] and lines[2].endswith("(no hosted snapshot merged)")
    assert lines[3].startswith("sum") and "0.75 USD" in lines[3] and "80.00 USD combined ceiling" in lines[3]
    assert "WARNING" not in out.err


def test_an_empty_ledger_exports_a_valid_file_with_a_total_of_0(root, capsys):
    assert ledger.main(["export"], root=root, today=OCT_26) == 0
    written = json.loads(export_file(root, OCT_26).read_text())
    assert (written["entries"], written["total_usd"], written["local_total_usd"]) == ([], 0.0, 0.0)
    assert "0 entries" in capsys.readouterr().out


def test_the_ceiling_is_the_sum_of_the_two_allocations_settings_knows_with_no_date_logic(root, capsys, monkeypatch):
    monkeypatch.setenv("SPEND_CAP_USD", "5")  # the Thu Nov 5 configuration: local 5 and hosted 20
    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    assert json.loads(export_file(root, NOV_5).read_text())["ceiling_usd"] == 25.0
    assert "25.00 USD combined ceiling" in capsys.readouterr().out


def test_a_sum_at_or_above_the_ceiling_is_printed_as_a_warning_and_changes_no_store(root, capsys, monkeypatch):
    monkeypatch.setenv("SPEND_CAP_USD", "1")  # ceiling 21 with the hosted 20
    store(root).append(settled(21.0))
    before = (root / LEDGER_PATH).read_bytes()

    assert ledger.main(["export"], root=root, today=OCT_26) == 0

    out = capsys.readouterr()
    assert "WARNING" in out.err and "21.00 USD" in out.err and "combined ceiling" in out.err
    assert (root / LEDGER_PATH).read_bytes() == before
    assert json.loads(export_file(root, OCT_26).read_text())["total_usd"] == 21.0


# --- reset ----------------------------------------------------------------------


def test_reset_refuses_without_todays_export_and_leaves_the_ledger_and_the_total_unchanged(root, capsys):
    store(root).append(settled(0.5))
    before = (root / LEDGER_PATH).read_bytes()

    assert ledger.main(["reset"], root=root, today=OCT_26) == 1

    assert "refusing to reset" in capsys.readouterr().err
    assert (root / LEDGER_PATH).read_bytes() == before
    assert SpendLedger(store(root), cap_usd=60).running_total_usd() == pytest.approx(0.5)
    assert not (root / EXPORTS_ROOT).exists()


def test_reset_proceeds_once_todays_export_exists_and_leaves_the_export_untouched(root, capsys):
    store(root).append(settled(0.5))
    assert ledger.main(["export"], root=root, today=OCT_26) == 0
    export_bytes = export_file(root, OCT_26).read_bytes()

    assert ledger.main(["reset"], root=root, today=OCT_26) == 0

    assert "new epoch 2026-10-26; running total 0.00 USD" in capsys.readouterr().out
    assert SpendLedger(store(root), cap_usd=60).running_total_usd() == 0
    assert store(root).epoch() == "2026-10-26"
    assert export_file(root, OCT_26).read_bytes() == export_bytes


def test_a_second_reset_on_the_same_date_is_refused_and_the_entries_since_the_first_keep_counting(root, capsys):
    assert ledger.main(["export"], root=root, today=OCT_26) == 0
    assert ledger.main(["reset"], root=root, today=OCT_26) == 0
    store(root).append(settled(0.25))
    before = (root / LEDGER_PATH).read_bytes()

    assert ledger.main(["reset"], root=root, today=OCT_26) == 1

    assert "already reset today" in capsys.readouterr().err
    assert (root / LEDGER_PATH).read_bytes() == before
    assert SpendLedger(store(root), cap_usd=60).running_total_usd() == pytest.approx(0.25)


def test_the_export_after_the_nov_5_reset_reports_only_the_new_epoch_and_the_earlier_export_is_unchanged(root, monkeypatch):
    before_reset = [settled(30.0), settled(25.0, "riddler")]
    for entry in before_reset:
        store(root).append(entry)
    assert ledger.main(["export"], root=root, today=NOV_4) == 0
    nov_4 = export_file(root, NOV_4).read_bytes()
    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    assert ledger.main(["reset"], root=root, today=NOV_5) == 0

    monkeypatch.setenv("SPEND_CAP_USD", "5")
    guard = SpendLedger(store(root), cap_usd=5)
    assert guard.running_total_usd() == 0
    guard.settle(guard.guard("vision"), 0.5)
    assert ledger.main(["export"], root=root, today=NOV_5) == 0

    nov_5 = json.loads(export_file(root, NOV_5).read_text())
    assert nov_5["epoch"] == "2026-11-05" and nov_5["ceiling_usd"] == 25.0
    assert [(e["epoch"], e["status"]) for e in nov_5["entries"]] == [("2026-11-05", "reserved"), ("2026-11-05", "settled")]
    assert nov_5["total_usd"] == 0.5
    assert export_file(root, NOV_4).read_bytes() == nov_4
    earlier = json.loads(nov_4)
    assert [e["epoch"] for e in earlier["entries"]] == [None, None] and earlier["total_usd"] == 55.0
    assert [row.get("epoch") for row in map(json.loads, (root / LEDGER_PATH).read_text().splitlines())] == [None, None, "2026-11-05", "2026-11-05", "2026-11-05"]


# --- a script hitting the cap ---------------------------------------------------


def test_a_guarded_call_past_the_cap_exits_non_zero_printing_the_cap_and_the_running_total(capsys):
    guard = SpendLedger(MemoryLedgerStore(settled(59.99)), cap_usd=60)
    with pytest.raises(SystemExit) as info:
        with ledger.exit_on_spend_cap():
            guard.guard("vision")
    assert info.value.code != 0
    assert "60.00 USD" in str(info.value.code) and "59.99 USD" in str(info.value.code)
    assert str(info.value.code).startswith(str(SpendCapExceeded(60, 59.99)))


def test_the_script_runs_from_any_working_directory(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=tmp_path, capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert "{export,reset}" in result.stdout
