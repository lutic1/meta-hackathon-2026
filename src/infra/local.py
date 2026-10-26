"""Local-mode adapters (AD-9): the jsonl `LedgerStore` and the disk `Cache`.

`JsonlLedgerStore` appends one JSON line per entry to `spend/ledger.jsonl`
under an exclusive file lock, outside `.cache/`, so the running total
survives a restart and clearing the cache never touches the record of
spend. The file holds two kinds of line: an entry, and the epoch marker
`{"epoch": "<date>"}` that the reset writes (`scripts/ledger.py`, 2.6);
`append` stamps each entry with the current epoch (`None` before the first
marker) and `entries` returns the current epoch's entries in append order,
so `SpendLedger` counts exactly what the store returns. `DiskCache` keeps
one JSON file per key under `.cache/`, written whole and renamed into
place. The other local adapters (JSON `JobStore`, disk `ArtifactStore`,
in-process `JobRunner`, JSON `SessionStore`) land with their stories.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

from src.domain.ledger import LedgerEntry

LEDGER_PATH = Path("spend/ledger.jsonl")
"""The live ledger, git-ignored; `spend/exports/` beside it holds the committed daily exports."""
CACHE_ROOT = Path(".cache")
"""The model-call cache, git-ignored; deleting it never touches `spend/`."""


def _read_ledger(file: TextIO) -> tuple[list[LedgerEntry], str | None]:
    """Every entry in the file, and the epoch its last marker line names."""
    rows: list[LedgerEntry] = []
    epoch: str | None = None
    for line in file:
        if not line.strip():
            continue
        record = json.loads(line)
        if "call_id" in record:
            rows.append(LedgerEntry.model_validate(record))
        else:
            epoch = record["epoch"]
    return rows, epoch


class JsonlLedgerStore:
    """`LedgerStore` over one jsonl file; every read and append holds the file's exclusive lock."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _locked(self) -> Iterator[TextIO]:
        """The file opened for append and read, locked for the block; the lock is released after a flush."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as file:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX)
            try:
                file.seek(0)
                yield file
                file.flush()
            finally:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)

    def append(self, entry: LedgerEntry) -> None:
        """Write the entry as one line under the current epoch."""
        with self._locked() as file:
            _, epoch = _read_ledger(file)
            stamped = LedgerEntry.model_validate({**entry.model_dump(), "epoch": epoch})
            file.seek(0, os.SEEK_END)
            file.write(stamped.model_dump_json() + "\n")

    def entries(self) -> list[LedgerEntry]:
        """The current epoch's entries in append order."""
        with self._locked() as file:
            rows, epoch = _read_ledger(file)
        return [row for row in rows if row.epoch == epoch]


class DiskCache:
    """`Cache` over one JSON file per key under `root`."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        try:
            return json.loads(self._path(key).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        """Write the object to a temporary file in `root`, then rename it over the key's file."""
        self.root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=self.root, prefix=f"{key}.", suffix=".tmp", delete=False, encoding="utf-8") as file:
            json.dump(value, file)
        os.replace(file.name, self._path(key))
