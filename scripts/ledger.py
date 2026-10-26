#!/usr/bin/env python3
"""The spend ledger's daily export and the Nov 5 reset (AD-6, AD-9).

    uv run scripts/ledger.py export   # writes spend/exports/ledger-<date>.json and prints the totals
    uv run scripts/ledger.py reset    # starts a new epoch; refuses unless today's export exists

`export` wraps `export_ledger` (`src/infra/local.py`): the current epoch's
entries and running total go to the dated export, committed with each day's
work, and the local total, the hosted total (0 until the hosted snapshot
merge, 7.9) and their sum are printed beside the combined ceiling, the sum of
the two allocations `Settings` knows (80 through Wed Nov 4, 25 from Thu Nov
5 by configuration, no date logic). A sum at or above the ceiling is a
warning and changes no store. `reset` writes today's date as the new epoch
marker, so the running total and the cap guard count only entries appended
after it; the earlier dated exports keep the pre-reset entries and are never
rewritten. Exits 1 on a refused reset: no export for today, or a second
reset on the same date, whose marker would repeat the epoch and keep the
entries appended since the first one counting. Other scripts wrap their guarded calls
in `exit_on_spend_cap` so a `SpendCapExceeded` exits non-zero naming the cap
and the running total.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from src.config import Settings
from src.domain.ledger import SpendCapExceeded, running_total_usd
from src.infra.local import (
    EXPORTS_ROOT,
    LEDGER_PATH,
    JsonlLedgerStore,
    export_ledger,
    export_path,
)


@contextmanager
def exit_on_spend_cap() -> Iterator[None]:
    """Around a script's guarded calls: a refused call exits 1 printing the cap and the running total."""
    try:
        yield
    except SpendCapExceeded as error:
        sys.exit(f"{error}; see scripts/ledger.py export")


def export(root: Path, today: date, settings: Settings) -> int:
    ceiling = settings.spend_cap_usd + settings.hosted_spend_cap_usd
    result = export_ledger(JsonlLedgerStore(root / LEDGER_PATH), root / EXPORTS_ROOT, today, ceiling)
    print(f"wrote {export_path(EXPORTS_ROOT, today)}: {len(result.entries)} entries, epoch {result.epoch or 'none'}")
    print(f"local total  {result.local_total_usd:8.2f} USD against the {ceiling:.2f} USD combined ceiling")
    print(f"hosted total {result.hosted_total_usd:8.2f} USD against the {ceiling:.2f} USD combined ceiling (no hosted snapshot merged)")
    print(f"sum          {result.total_usd:8.2f} USD against the {ceiling:.2f} USD combined ceiling")
    if result.total_usd >= ceiling:
        print(f"WARNING: the sum {result.total_usd:.2f} USD is at or above the {ceiling:.2f} USD combined ceiling", file=sys.stderr)
    return 0


def reset(root: Path, today: date) -> int:
    path = export_path(EXPORTS_ROOT, today)
    if not (root / path).is_file():
        print(f"refusing to reset: today's export {path} does not exist; run scripts/ledger.py export first", file=sys.stderr)
        return 1
    store = JsonlLedgerStore(root / LEDGER_PATH)
    if store.epoch() == today.isoformat():
        print(f"refusing to reset: the ledger was already reset today ({today.isoformat()})", file=sys.stderr)
        return 1
    store.start_epoch(today.isoformat())
    total = running_total_usd(store.entries())
    print(f"reset: new epoch {today.isoformat()}; running total {total:.2f} USD; {path} untouched")
    return 0


def main(argv: list[str] | None = None, *, root: Path = REPO, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(description="export the spend ledger, or reset it into a new epoch")
    parser.add_argument("command", choices=("export", "reset"))
    args = parser.parse_args(argv)
    today = today or date.today()
    if args.command == "export":
        return export(root, today, Settings.from_env())
    return reset(root, today)


if __name__ == "__main__":
    sys.exit(main())
