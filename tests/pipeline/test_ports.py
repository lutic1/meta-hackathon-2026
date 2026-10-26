"""Story 2.3: `src/pipeline/ports.py` declares `LedgerStore` (`append`, `entries`) over the domain only (AD-1, AD-9)."""

import inspect
import sys
import typing
from pathlib import Path

from src.domain.ledger import LedgerEntry
from src.pipeline.ports import LedgerStore
from tests.test_boundaries import _imports

REPO = Path(__file__).resolve().parents[2]


def test_ledger_store_declares_append_and_entries():
    assert typing.is_protocol(LedgerStore)
    assert [p.name for p in inspect.signature(LedgerStore.append, eval_str=True).parameters.values()] == ["self", "entry"]
    assert inspect.signature(LedgerStore.append, eval_str=True).parameters["entry"].annotation is LedgerEntry
    assert inspect.signature(LedgerStore.entries, eval_str=True).return_annotation == list[LedgerEntry]


def test_a_structural_double_satisfies_the_port():
    class Memory:
        def __init__(self) -> None:
            self.rows: list[LedgerEntry] = []

        def append(self, entry: LedgerEntry) -> None:
            self.rows.append(entry)

        def entries(self) -> list[LedgerEntry]:
            return list(self.rows)

    store: LedgerStore = Memory()
    assert store.entries() == []


def test_ports_import_only_the_domain():
    src = REPO / "src"
    names = _imports(src / "pipeline" / "ports.py", "src.pipeline.ports", src)
    internal = {n for n in names if n.startswith("src.")}
    assert internal and all(n.startswith("src.domain") for n in internal), names
    assert {n.split(".")[0] for n in names - internal} <= set(sys.stdlib_module_names)
