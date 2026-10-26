"""Stories 2.3 and 2.4: `src/pipeline/ports.py` declares `LedgerStore` (`append`, `entries`) and `Cache` (`get`, `put`) over the domain only (AD-1, AD-9)."""

import inspect
import sys
import typing
from pathlib import Path

from src.domain.ledger import LedgerEntry
from src.pipeline.ports import Cache, LedgerStore
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


def test_cache_declares_get_and_put_over_json_objects():
    assert typing.is_protocol(Cache)
    get = inspect.signature(Cache.get, eval_str=True)
    put = inspect.signature(Cache.put, eval_str=True)
    assert [p.name for p in get.parameters.values()] == ["self", "key"]
    assert get.parameters["key"].annotation is str and get.return_annotation == dict[str, typing.Any] | None
    assert [p.name for p in put.parameters.values()] == ["self", "key", "value"]
    assert put.parameters["value"].annotation == dict[str, typing.Any] and put.return_annotation is None


def test_a_structural_cache_double_satisfies_the_port():
    class Memory:
        def __init__(self) -> None:
            self.rows: dict[str, dict[str, typing.Any]] = {}

        def get(self, key: str) -> dict[str, typing.Any] | None:
            return self.rows.get(key)

        def put(self, key: str, value: dict[str, typing.Any]) -> None:
            self.rows[key] = value

    cache: Cache = Memory()
    assert cache.get("k") is None
    cache.put("k", {"text": "hi"})
    assert cache.get("k") == {"text": "hi"}


def test_ports_import_only_the_domain():
    src = REPO / "src"
    names = _imports(src / "pipeline" / "ports.py", "src.pipeline.ports", src)
    internal = {n for n in names if n.startswith("src.")}
    assert internal and all(n.startswith("src.domain") for n in internal), names
    assert {n.split(".")[0] for n in names - internal} <= set(sys.stdlib_module_names)
