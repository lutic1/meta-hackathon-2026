#!/usr/bin/env python3
"""The spend ledger's daily export, merged with the latest hosted snapshot, and the Nov 5 reset (AD-6, AD-9).

    uv run scripts/ledger.py export   # writes spend/exports/ledger-<date>.json and prints the totals
    uv run scripts/ledger.py reset    # starts a new epoch in both stores; refuses unless today's export exists
    uv run scripts/ledger.py export --env dev   # the Modal Environment to read (default main)

`export` wraps `export_ledger` (`src/infra/local.py`): the current epoch's
local entries, merged with the current-epoch entries of the latest hosted
snapshot (`spend/hosted-<date>.jsonl` with the latest date, read from the
`keyframe-data` Volume with `read_file`), go to the dated export, committed
with each day's work. An entry present in both appears once and the total
counts each `call_` id once. The local total, the hosted total from the
merged snapshot and their sum are printed beside the combined ceiling, the
sum of the two allocations `Settings` knows (80 through Wed Nov 4, 25 from
Thu Nov 5 by configuration, no date logic), and a last line shows the two
allocations and where the Hosted one came from: `HOSTED_SPEND_CAP_USD`, or
the default 20 when it is unset. A sum at or above the ceiling
is a warning and changes no store. With no snapshot on the Volume, or the
Volume out of reach (no Modal token, say), the export holds the local
entries alone, says no hosted snapshot was merged and still exits 0.

`reset` writes today's date as the new epoch marker to both stores, the
`keyframe-ledger` Dict first and then the local file, so both running
totals and both cap guards count only entries appended after it; the
earlier dated exports keep the pre-reset entries and are never rewritten.
Exits 1 on a refused reset, changing neither store: no export for today,
today's export not holding the latest hosted snapshot, the hosted stores
out of reach, or a second reset on the same date, whose marker would
repeat the epoch and keep the entries appended since the first one
counting. Should the local write fail after the Dict's, the two stores
hold different epochs and every export merges no hosted entries; running
`reset` again (the local epoch is not yet today) writes both markers anew.
Every Dict and the Volume are resolved in the `--env` Modal
Environment by `from_name(..., environment_name=...)`, never in the CLI's
active one. Other scripts wrap their guarded calls in `exit_on_spend_cap`
so a `SpendCapExceeded` exits non-zero naming the cap and the running total.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Protocol

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from src.config import Settings
from src.domain.ledger import LedgerEntry, SpendCapExceeded, running_total_usd
from src.infra.local import (
    EXPORTS_ROOT,
    LEDGER_PATH,
    HostedSnapshot,
    JsonlLedgerStore,
    LedgerExport,
    export_ledger,
    export_path,
)
from src.infra.modal import (
    LEDGER_DICT,
    SPEND_DIR,
    VOLUME,
    DictLedgerStore,
    DictLike,
    snapshot_path,
)

ENVIRONMENT = "main"
"""The Modal Environment the judge app is deployed in, passed to every `from_name` explicitly."""
SNAPSHOT_NAME = re.compile(r"hosted-(\d{4}-\d{2}-\d{2})\.jsonl")


class FileEntry(Protocol):
    """An entry `modal.Volume.listdir` returns."""

    @property
    def path(self) -> str: ...


class Volume(Protocol):
    """The two remote `modal.Volume` calls the script makes from outside a container."""

    def listdir(self, path: str) -> Sequence[FileEntry]: ...

    def read_file(self, path: str) -> Iterable[bytes]: ...


@contextmanager
def exit_on_spend_cap() -> Iterator[None]:
    """Around a script's guarded calls: a refused call exits 1 printing the cap and the running total."""
    try:
        yield
    except SpendCapExceeded as error:
        sys.exit(f"{error}; see scripts/ledger.py export")


def latest_snapshot_path(volume: Volume) -> str | None:
    """The Volume path of the hosted snapshot with the latest date under `spend/`; `None` when there is none, `spend/` included."""
    from modal.exception import NotFoundError

    try:
        listing = volume.listdir(f"/{SPEND_DIR}")
    except (FileNotFoundError, NotFoundError):  # no daily snapshot has run yet
        return None
    names = (PurePosixPath(entry.path).name for entry in listing)
    days = [date.fromisoformat(match[1]) for name in names if (match := SNAPSHOT_NAME.fullmatch(name))]
    return snapshot_path(max(days)) if days else None


def read_snapshot(volume: Volume, path: str) -> HostedSnapshot:
    """Every entry of the snapshot at `path`, one JSON line each; an empty snapshot holds none."""
    text = b"".join(volume.read_file(f"/{path}")).decode()
    return HostedSnapshot(path=path, entries=[LedgerEntry.model_validate_json(line) for line in text.splitlines() if line.strip()])


def open_volume(environment: str) -> Volume:
    """`keyframe-data` in `environment`; no `create_if_missing`, so a wrong Environment fails instead of reading an empty Volume."""
    import modal

    return modal.Volume.from_name(VOLUME, environment_name=environment)


def open_ledger_dict(environment: str) -> DictLike:
    """`keyframe-ledger` in `environment`; no `create_if_missing`, so a wrong Environment fails instead of resetting an empty Dict."""
    import modal

    return modal.Dict.from_name(LEDGER_DICT, environment_name=environment)


def export(root: Path, today: date, settings: Settings, environment: str) -> int:
    local_cap, hosted_cap, cap_source = settings.spend_cap_usd, settings.hosted_spend_cap_usd, settings.hosted_spend_cap_source
    ceiling = local_cap + hosted_cap
    hosted: HostedSnapshot | None = None
    try:
        volume = open_volume(environment)
        path = latest_snapshot_path(volume)
        hosted = read_snapshot(volume, path) if path else None
        missing = None if path else f"{SPEND_DIR}/ on {VOLUME} in {environment} holds no hosted-<date>.jsonl"
    except Exception as error:  # noqa: BLE001 - the export still holds the local entries and exits 0
        missing = f"could not read {VOLUME} in {environment}: {type(error).__name__}: {error}"
    result = export_ledger(JsonlLedgerStore(root / LEDGER_PATH), root / EXPORTS_ROOT, today, local_cap, hosted_cap, cap_source, hosted)
    source = f"(from {result.hosted_snapshot})" if result.hosted_snapshot else "(no hosted snapshot merged)"
    print(f"wrote {export_path(EXPORTS_ROOT, today)}: {len(result.entries)} entries, epoch {result.epoch or 'none'}")
    print(f"local total  {result.local_total_usd:8.2f} USD against the {ceiling:.2f} USD combined ceiling")
    print(f"hosted total {result.hosted_total_usd:8.2f} USD against the {ceiling:.2f} USD combined ceiling {source}")
    print(f"sum          {result.total_usd:8.2f} USD against the {ceiling:.2f} USD combined ceiling")
    origin = "from HOSTED_SPEND_CAP_USD" if cap_source == "env" else "from the default; HOSTED_SPEND_CAP_USD is unset"
    print(f"ceiling      {ceiling:8.2f} USD: local {local_cap:.2f} + hosted {hosted_cap:.2f} USD (hosted {origin})")
    if missing:
        print(f"no hosted snapshot merged: {missing}")
    if result.total_usd >= ceiling:
        print(f"WARNING: the sum {result.total_usd:.2f} USD is at or above the {ceiling:.2f} USD combined ceiling", file=sys.stderr)
    return 0


def reset(root: Path, today: date, environment: str) -> int:
    path = export_path(EXPORTS_ROOT, today)
    if not (root / path).is_file():
        print(f"refusing to reset: today's export {path} does not exist; run scripts/ledger.py export first", file=sys.stderr)
        return 1
    store = JsonlLedgerStore(root / LEDGER_PATH)
    epoch = today.isoformat()
    if store.epoch() == epoch:
        print(f"refusing to reset: the ledger was already reset today ({epoch})", file=sys.stderr)
        return 1
    merged = LedgerExport.model_validate_json((root / path).read_bytes()).hosted_snapshot
    try:
        latest = latest_snapshot_path(open_volume(environment))
        hosted = DictLedgerStore(open_ledger_dict(environment))
    except Exception as error:  # noqa: BLE001 - refuse and change neither store
        print(f"refusing to reset: could not reach the hosted stores in {environment}: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    if merged != latest:
        print(
            f"refusing to reset: today's export {path} holds {merged or 'no hosted snapshot'}, not the latest {latest}; "
            "run scripts/ledger.py export first",
            file=sys.stderr,
        )
        return 1
    try:
        hosted.start_epoch(epoch)
    except Exception as error:  # noqa: BLE001 - nothing was written, so neither store changed
        print(f"refusing to reset: could not write the epoch to {LEDGER_DICT} in {environment}: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    store.start_epoch(epoch)
    local, remote = running_total_usd(store.entries()), running_total_usd(hosted.entries())
    print(
        f"reset: new epoch {epoch}; running total {local:.2f} USD local, {remote:.2f} USD hosted; "
        f"marker written to {LEDGER_PATH} and {LEDGER_DICT} in {environment}; {path} untouched"
    )
    return 0


def main(argv: list[str] | None = None, *, root: Path = REPO, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(description="export the spend ledger merged with the latest hosted snapshot, or reset both stores into a new epoch")
    parser.add_argument("command", choices=("export", "reset"))
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment of the hosted stores (default {ENVIRONMENT})")
    args = parser.parse_args(argv)
    today = today or date.today()
    if args.command == "export":
        return export(root, today, Settings.from_env(), args.env)
    return reset(root, today, args.env)


if __name__ == "__main__":
    sys.exit(main())
