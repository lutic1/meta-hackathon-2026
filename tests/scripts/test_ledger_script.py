"""Stories 2.6 and 7.9: `scripts/ledger.py export|reset`, the dated export merged with the latest hosted snapshot, and the reset of both stores that refuses without it (AD-6, AD-9).

The hosted stores never reach Modal: `open_volume` is a local directory
standing for the `keyframe-data` Volume, filled from the snapshot fixtures
under `tests/fixtures/spend`, and `open_ledger_dict` a plain dict standing
for `keyframe-ledger`.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest
from modal.exception import NotFoundError

from src.api import wiring
from src.config import Settings
from src.domain.ledger import LedgerEntry, SpendCapExceeded
from src.infra.local import EXPORTS_ROOT, LEDGER_PATH, JsonlLedgerStore
from src.infra.modal import (
    EPOCH_KEY,
    DictLedgerStore,
    ModalHandles,
    export_hosted_ledger,
    snapshot_path,
)
from src.providers.spend import SpendLedger
from tests.api.hosted import NullVolume
from tests.providers.test_spend import MemoryLedgerStore, settled

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/ledger.py"
SNAPSHOTS = REPO / "tests/fixtures/spend"
OCT_26, NOV_4, NOV_5 = date(2026, 10, 26), date(2026, 11, 4), date(2026, 11, 5)


def _load():
    spec = importlib.util.spec_from_file_location("ledger_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = _load()


@dataclass(frozen=True)
class Entry:
    """An entry `modal.Volume.listdir` returns: its path from the Volume root."""

    path: str


class DirectoryVolume:
    """`listdir` and `read_file` over a local directory standing for the Volume root; every path asked for is recorded."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.asked: list[str] = []

    def listdir(self, path: str) -> list[Entry]:
        self.asked.append(path)
        folder = self.root / path.lstrip("/")
        return [Entry(item.relative_to(self.root).as_posix()) for item in sorted(folder.iterdir())] if folder.is_dir() else []

    def read_file(self, path: str) -> Iterator[bytes]:
        self.asked.append(path)
        yield (self.root / path.lstrip("/")).read_bytes()


@dataclass
class Hosted:
    """The two hosted stores the script reaches, and the Environments it opened them in."""

    volume: DirectoryVolume
    ledger: dict
    environments: list[str]

    def snapshot(self, *days: str) -> None:
        """Put the fixture snapshots taken on `days` on the Volume, as the daily `ledger_export` would."""
        (self.volume.root / "spend").mkdir(parents=True, exist_ok=True)
        for day in days:
            shutil.copy(SNAPSHOTS / f"hosted-{day}.jsonl", self.volume.root / "spend")


@pytest.fixture
def hosted(tmp_path: Path, monkeypatch) -> Hosted:
    stores = Hosted(DirectoryVolume(tmp_path / "volume"), {}, [])

    def open_volume(environment: str) -> DirectoryVolume:
        stores.environments.append(environment)
        return stores.volume

    def open_ledger_dict(environment: str) -> dict:
        stores.environments.append(environment)
        return stores.ledger

    monkeypatch.setattr(ledger, "open_volume", open_volume)
    monkeypatch.setattr(ledger, "open_ledger_dict", open_ledger_dict)
    return stores


@pytest.fixture
def root(tmp_path: Path, monkeypatch, hosted: Hosted) -> Path:
    """A repository root with the default allocations: local 60 and hosted 20, the 80 ceiling; the Volume holds no snapshot."""
    monkeypatch.setenv("SPEND_CAP_USD", "")
    return tmp_path / "repo"


def fixture_entries(day: str) -> list[LedgerEntry]:
    return [LedgerEntry.model_validate_json(line) for line in (SNAPSHOTS / f"hosted-{day}.jsonl").read_text().splitlines()]


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


def test_reset_refuses_without_todays_export_and_leaves_the_ledger_and_the_total_unchanged(root, capsys, hosted):
    store(root).append(settled(0.5))
    before = (root / LEDGER_PATH).read_bytes()

    assert ledger.main(["reset"], root=root, today=OCT_26) == 1

    assert "refusing to reset" in capsys.readouterr().err
    assert (root / LEDGER_PATH).read_bytes() == before
    assert SpendLedger(store(root), cap_usd=60).running_total_usd() == pytest.approx(0.5)
    assert not (root / EXPORTS_ROOT).exists()
    assert hosted.ledger == {}


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
    with pytest.raises(SystemExit) as info, ledger.exit_on_spend_cap():
        guard.guard("vision")
    assert info.value.code != 0
    assert "60.00 USD" in str(info.value.code) and "59.99 USD" in str(info.value.code)
    assert str(info.value.code).startswith(str(SpendCapExceeded(60, 59.99)))


def test_the_script_runs_from_any_working_directory(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=tmp_path, capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert "{export,reset}" in result.stdout


# --- 7.9: the latest hosted snapshot merged into the export ----------------------


def test_export_merges_the_local_entries_with_the_snapshot_of_the_latest_date(root, hosted, capsys):
    store(root).append(settled(0.5))
    store(root).append(settled(0.25, "sam"))
    hosted.snapshot("2026-11-03", "2026-11-04")

    assert ledger.main(["export"], root=root, today=NOV_4) == 0

    written = json.loads(export_file(root, NOV_4).read_text())
    local = [entry.model_dump(mode="json") for entry in store(root).entries()]
    assert written["entries"] == local + [entry.model_dump(mode="json") for entry in fixture_entries("2026-11-04")]
    assert written["hosted_snapshot"] == "spend/hosted-2026-11-04.jsonl"
    assert (written["local_total_usd"], written["hosted_total_usd"]) == (0.75, pytest.approx(1.78))
    assert written["total_usd"] == pytest.approx(2.53)
    assert hosted.volume.asked == ["/spend", "/spend/hosted-2026-11-04.jsonl"]
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "wrote spend/exports/ledger-2026-11-04.json: 5 entries, epoch none"
    assert "0.75 USD" in lines[1] and "1.78 USD" in lines[2] and "2.53 USD" in lines[3]
    assert lines[2].endswith("80.00 USD combined ceiling (from spend/hosted-2026-11-04.jsonl)")
    assert len(lines) == 4


def test_a_call_entry_in_both_sources_appears_once_and_the_total_sums_the_distinct_entries(root, hosted):
    shared = fixture_entries("2026-11-04")[2]
    store(root).append(shared)
    store(root).append(settled(0.5))
    hosted.snapshot("2026-11-03", "2026-11-04")

    assert ledger.main(["export"], root=root, today=NOV_4) == 0

    written = json.loads(export_file(root, NOV_4).read_text())
    ids = [entry["call_id"] for entry in written["entries"]]
    assert len(ids) == len(set(ids)) == 4 and ids.count(shared.call_id) == 1
    assert fixture_entries("2026-11-03")[0].call_id not in ids
    assert written["total_usd"] == pytest.approx(0.5 + 0.5 + 1.25 + 0.03)
    assert written["total_usd"] == pytest.approx(sum(entry["usd"] for entry in written["entries"]))


def test_with_no_hosted_snapshot_the_export_holds_the_local_entries_alone_and_exits_0(root, hosted, capsys):
    store(root).append(settled(0.5))

    assert ledger.main(["export"], root=root, today=OCT_26) == 0

    written = json.loads(export_file(root, OCT_26).read_text())
    assert (len(written["entries"]), written["hosted_snapshot"], written["hosted_total_usd"], written["total_usd"]) == (1, None, 0.0, 0.5)
    out = capsys.readouterr().out
    assert "(no hosted snapshot merged)" in out
    assert out.splitlines()[-1] == "no hosted snapshot merged: spend/ on keyframe-data in main holds no hosted-<date>.jsonl"


def test_a_volume_out_of_reach_merges_no_snapshot_and_still_exits_0(root, monkeypatch, capsys):
    def unreachable(environment: str):
        raise ConnectionError("no Modal token")

    monkeypatch.setattr(ledger, "open_volume", unreachable)
    store(root).append(settled(0.5))

    assert ledger.main(["export"], root=root, today=OCT_26) == 0

    assert json.loads(export_file(root, OCT_26).read_text())["entries"][0]["usd"] == 0.5
    assert "no hosted snapshot merged: could not read keyframe-data in main: ConnectionError: no Modal token" in capsys.readouterr().out


def test_the_hosted_stores_are_opened_in_the_named_environment(root, hosted):
    assert ledger.main(["export", "--env", "dev"], root=root, today=OCT_26) == 0
    assert ledger.main(["reset", "--env", "dev"], root=root, today=OCT_26) == 0
    assert set(hosted.environments) == {"dev"}


def test_a_merged_sum_at_or_above_the_ceiling_is_a_warning_and_changes_no_store(root, hosted, capsys, monkeypatch):
    monkeypatch.setenv("SPEND_CAP_USD", "1")  # ceiling 21 with the hosted 20
    store(root).append(settled(20.0))
    hosted.snapshot("2026-11-04")
    before = (root / LEDGER_PATH).read_bytes(), (hosted.volume.root / snapshot_path(NOV_4)).read_bytes()

    assert ledger.main(["export"], root=root, today=NOV_4) == 0

    assert "WARNING: the sum 21.78 USD is at or above the 21.00 USD combined ceiling" in capsys.readouterr().err
    assert ((root / LEDGER_PATH).read_bytes(), (hosted.volume.root / snapshot_path(NOV_4)).read_bytes()) == before
    assert hosted.ledger == {}


@pytest.mark.parametrize("missing", [FileNotFoundError("/spend"), NotFoundError("No such file or directory: spend")])
def test_a_volume_with_no_spend_folder_holds_no_snapshot(root, hosted, monkeypatch, capsys, missing):
    def listdir(path: str):
        raise missing

    monkeypatch.setattr(hosted.volume, "listdir", listdir)

    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "no hosted snapshot merged: spend/ on keyframe-data in main holds no hosted-<date>.jsonl"
    assert ledger.main(["reset"], root=root, today=NOV_5) == 0


def test_the_api_export_after_a_build_keeps_the_snapshot_todays_export_merged(root, hosted):
    store(root).append(settled(0.5))
    hosted.snapshot("2026-11-04")
    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    merged = json.loads(export_file(root, NOV_5).read_text())
    api_export = wiring.ledger_export(Settings.from_env(), store(root), root / EXPORTS_ROOT, lambda: NOV_5)

    store(root).append(settled(0.25, "sam"))  # a build finishing while the API runs
    api_export()

    written = json.loads(export_file(root, NOV_5).read_text())
    assert (written["hosted_snapshot"], written["hosted_total_usd"]) == ("spend/hosted-2026-11-04.jsonl", pytest.approx(1.78))
    assert written["entries"] == merged["entries"][:1] + [store(root).entries()[1].model_dump(mode="json")] + merged["entries"][1:]
    assert (written["local_total_usd"], written["total_usd"]) == (0.75, pytest.approx(2.53))
    assert ledger.main(["reset"], root=root, today=NOV_5) == 0


def test_the_api_export_after_the_reset_keeps_no_snapshot_of_the_earlier_epoch(root, hosted):
    hosted.snapshot("2026-11-04")
    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    assert ledger.main(["reset"], root=root, today=NOV_5) == 0

    wiring.ledger_export(Settings.from_env(), store(root), root / EXPORTS_ROOT, lambda: NOV_5)()

    written = json.loads(export_file(root, NOV_5).read_text())
    assert (written["epoch"], written["entries"], written["hosted_snapshot"], written["hosted_total_usd"]) == ("2026-11-05", [], None, 0.0)


# --- 7.9: the reset of both stores ----------------------------------------------


def test_reset_refuses_while_todays_export_does_not_hold_the_latest_snapshot(root, hosted, capsys):
    store(root).append(settled(0.5))
    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    hosted.snapshot("2026-11-04")
    before = (root / LEDGER_PATH).read_bytes()

    assert ledger.main(["reset"], root=root, today=NOV_5) == 1

    assert "holds no hosted snapshot, not the latest spend/hosted-2026-11-04.jsonl" in capsys.readouterr().err
    assert ((root / LEDGER_PATH).read_bytes(), hosted.ledger) == (before, {})
    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    assert ledger.main(["reset"], root=root, today=NOV_5) == 0


def test_reset_refuses_and_changes_neither_store_when_the_hosted_ledger_is_out_of_reach(root, monkeypatch, capsys):
    def unreachable(environment: str):
        raise ConnectionError("no Modal token")

    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    monkeypatch.setattr(ledger, "open_ledger_dict", unreachable)

    assert ledger.main(["reset"], root=root, today=NOV_5) == 1

    assert "could not reach the hosted stores in main: ConnectionError" in capsys.readouterr().err
    assert store(root).epoch() is None


def test_reset_writes_the_new_epoch_to_both_stores_and_the_next_snapshot_holds_only_that_epoch(root, hosted, tmp_path, capsys):
    hosted_store = DictLedgerStore(hosted.ledger)
    before = settled(1.25, "riddler")
    hosted_store.append(before)
    store(root).append(settled(0.5))
    hosted.snapshot("2026-11-04")
    assert ledger.main(["export"], root=root, today=NOV_5) == 0

    assert ledger.main(["reset"], root=root, today=NOV_5) == 0

    assert "new epoch 2026-11-05; running total 0.00 USD local, 0.00 USD hosted" in capsys.readouterr().out
    assert (store(root).epoch(), hosted.ledger[EPOCH_KEY]) == ("2026-11-05", "2026-11-05")
    assert SpendLedger(hosted_store, cap_usd=20).running_total_usd() == 0
    after = settled(0.75)
    hosted_store.append(after)
    assert [entry.epoch for entry in hosted_store.entries()] == ["2026-11-05"]
    volume_root = tmp_path / "data"
    snapshot = export_hosted_ledger(ModalHandles(jobs={}, sessions={}, ledger=hosted.ledger, volume=NullVolume(), root=volume_root), NOV_5)
    lines = (volume_root / snapshot_path(NOV_5)).read_text().splitlines()
    assert [LedgerEntry.model_validate_json(line).call_id for line in lines] == [entry.call_id for entry in snapshot] == [after.call_id]


def test_after_the_reset_the_25_report_merges_only_current_epoch_entries_and_the_earlier_export_is_unchanged(root, hosted, monkeypatch):
    store(root).append(settled(30.0))
    hosted.snapshot("2026-11-03", "2026-11-04")
    assert ledger.main(["export"], root=root, today=NOV_4) == 0
    nov_4 = export_file(root, NOV_4).read_bytes()
    assert ledger.main(["export"], root=root, today=NOV_5) == 0
    assert ledger.main(["reset"], root=root, today=NOV_5) == 0

    monkeypatch.setenv("SPEND_CAP_USD", "5")
    store(root).append(settled(0.5))
    hosted.snapshot("2026-11-05")  # entries of two epochs: none and 2026-11-05
    assert ledger.main(["export"], root=root, today=NOV_5) == 0

    report = json.loads(export_file(root, NOV_5).read_text())
    assert (report["epoch"], report["ceiling_usd"], report["hosted_snapshot"]) == ("2026-11-05", 25.0, "spend/hosted-2026-11-05.jsonl")
    assert {entry["epoch"] for entry in report["entries"]} == {"2026-11-05"}
    current = [entry.call_id for entry in fixture_entries("2026-11-05") if entry.epoch == "2026-11-05"]
    assert [entry["call_id"] for entry in report["entries"]][1:] == current
    assert (report["local_total_usd"], report["hosted_total_usd"]) == (0.5, pytest.approx(0.76))
    assert report["total_usd"] == pytest.approx(1.26)
    assert export_file(root, NOV_4).read_bytes() == nov_4
    earlier = json.loads(nov_4)
    assert earlier["total_usd"] == pytest.approx(31.78) and {entry["epoch"] for entry in earlier["entries"]} == {None}
