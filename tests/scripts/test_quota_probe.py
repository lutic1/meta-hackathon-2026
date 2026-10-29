"""`scripts/quota_probe.py`: the live check that the build quota's slot claim is atomic across processes (AD-9, Story 7.10, decisions 18 and 23).

No test reaches Modal: the ephemeral Dict is a plain dict whose `put`
honours `skip_if_exists` under one lock, the processes are threads released
together by a barrier, and a broken Dict whose `put` ignores
`skip_if_exists` stands in for a claim that is not atomic. These tests
prove the counting, never live atomicity; the ops workflow's `quota-probe`
action runs the real race.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from src.infra.modal import BUILD_QUOTA, DictJobStore, VolumeFiles, slot_key
from src.pipeline.build import new_id
from src.pipeline.ports import BuildQuotaExceeded
from tests.infra.test_modal import StubVolume

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/quota_probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("quota_probe_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prober = _load()


# --- Doubles -------------------------------------------------------------------


class AtomicDict(dict):
    """A Dict whose conditional `put` is atomic, as the quota needs Modal's to be."""

    def __init__(self) -> None:
        super().__init__()
        self.lock = threading.Lock()

    def put(self, key: str, value: Any, *, skip_if_exists: bool = False) -> bool:
        with self.lock:
            if skip_if_exists and key in self:
                return False
            self[key] = value
            return True


class BrokenDict(AtomicDict):
    """A Dict whose `put` ignores `skip_if_exists`: every claimer wins and later writes replace earlier ones."""

    def put(self, key: str, value: Any, *, skip_if_exists: bool = False) -> bool:
        return super().put(key, value)


def opener(kind: type[AtomicDict]) -> tuple[Any, list[AtomicDict]]:
    """`modal.Dict.ephemeral` over fresh fakes: each `with` yields a new empty Dict, kept for the test to read."""
    opened: list[AtomicDict] = []

    @contextmanager
    def open_slots() -> Iterator[AtomicDict]:
        opened.append(kind())
        yield opened[-1]

    return open_slots, opened


def thread_race(slots: AtomicDict, names: list[str]) -> dict[str, str | None]:
    """Every claimer runs `claim` at once on its own thread, as the script's processes do."""
    start = threading.Barrier(len(names))

    def run(name: str) -> tuple[str, str | None]:
        start.wait()
        return name, prober.claim(slots, name)

    with ThreadPoolExecutor(len(names)) as pool:
        return dict(pool.map(run, names))


# --- The claim is the hosted store's own walk ------------------------------------


def test_the_probe_races_for_the_twenty_slot_keys_the_hosted_store_uses():
    assert prober.SLOTS == [slot_key(n) for n in range(1, BUILD_QUOTA + 1)] and len(prober.SLOTS) == 20
    assert prober.CLAIMERS == 30 and prober.LAST_SLOT_CLAIMERS == 8


def test_claim_takes_the_same_slots_in_the_same_order_as_reserve_build(tmp_path: Path):
    probed, stored = AtomicDict(), AtomicDict()
    store = DictJobStore(stored, VolumeFiles(StubVolume([]), tmp_path))
    names = [new_id("job") for _ in range(BUILD_QUOTA)]
    assert [prober.claim(probed, name) for name in names] == prober.SLOTS
    for name in names:
        store.reserve_build(name)
    assert dict(probed) == dict(stored)
    assert prober.claim(probed, "one more") is None
    with pytest.raises(BuildQuotaExceeded):
        store.reserve_build(new_id("job"))


# --- The counting ------------------------------------------------------------------


def test_the_tally_counts_successes_unique_slots_stored_claims_and_overwritten_prefills():
    slots = AtomicDict()
    slots.update({"build:1": "a", "build:2": "c", "build:3": "prefilled"})
    won = {"a": "build:1", "b": "build:1", "c": "build:2", "d": None}
    tally = prober.tally("race", won, slots, expected=2, prefilled=["build:3", "build:4"])
    assert (tally.claimers, tally.wins, tally.unique, tally.stored, tally.overwritten) == (4, 3, 2, 2, 1)
    assert not tally.ok
    clean = prober.tally("race", {"a": "build:1", "c": "build:2", "d": None}, slots, expected=2, prefilled=["build:3"])
    assert clean.ok and clean.line().endswith(": ok")


def test_an_atomic_claim_passes_both_races_and_prints_the_counts(capsys):
    open_slots, opened = opener(AtomicDict)
    assert prober.probe(open_slots, thread_race) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "fresh quota: 30 claimers, 20 successes, 20 unique slots, 20 slots holding a claimer, 0 prefilled slots overwritten; expected exactly 20: ok",
        "last slot: 8 claimers, 1 successes, 1 unique slots, 1 slots holding a claimer, 0 prefilled slots overwritten; expected exactly 1: ok",
        "quota probe passed: the conditional put let exactly 20 of 30 processes claim a slot, and exactly 1 of 8 the last one",
    ]
    fresh, last = opened
    assert sorted(fresh) == sorted(prober.SLOTS)
    assert [last[key] for key in prober.SLOTS[:-1]] == [prober.PREFILL] * 19 and last[prober.SLOTS[-1]] != prober.PREFILL


def test_a_claim_that_is_not_atomic_fails_both_races_and_exits_1(capsys):
    open_slots, _ = opener(BrokenDict)
    assert prober.probe(open_slots, thread_race) == 1
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert lines[0].startswith("fresh quota: 30 claimers, 30 successes, 1 unique slots") and lines[0].endswith("FAILED")
    assert lines[1].startswith("last slot: 8 claimers, 8 successes, 1 unique slots") and "1 prefilled slots overwritten" in lines[1]
    assert "quota probe failed" in captured.err


def test_a_claimer_that_never_reports_fails_the_race():
    def lost_race(slots: AtomicDict, names: list[str]) -> dict[str, str | None]:
        won = thread_race(slots, names)
        return {name: slot for name, slot in won.items() if slot != prober.SLOTS[0]}  # its process died before reporting

    open_slots, _ = opener(AtomicDict)
    assert prober.probe(open_slots, lost_race) == 1


# --- Only an ephemeral Dict, in the named Environment ----------------------------


def test_main_prints_the_environment_and_races_on_an_ephemeral_dict_there(monkeypatch, capsys):
    import modal

    environments: list[str | None] = []
    _, opened = opener(AtomicDict)

    @contextmanager
    def ephemeral(*, environment_name: str | None = None, **_: Any) -> Iterator[AtomicDict]:
        environments.append(environment_name)
        opened.append(AtomicDict())
        yield opened[-1]

    monkeypatch.setattr(modal.Dict, "ephemeral", ephemeral)
    monkeypatch.setattr(modal.Dict, "from_name", lambda *a, **k: pytest.fail("the probe never opens a named Dict"))
    monkeypatch.setattr(prober, "process_race", thread_race)

    assert prober.main(["--env", "dev"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "Modal Environment: dev"
    assert environments == ["dev", "dev"] and len(opened) == 2


def test_the_default_environment_is_dev():
    assert prober.ENVIRONMENT == "dev"


def test_the_script_never_names_a_real_dict_and_races_in_separate_spawned_processes():
    source = SCRIPT.read_text()
    assert "\"keyframe-jobs\"" not in source and "JOBS_DICT" not in source and "from_name" not in source
    assert "modal.Dict.ephemeral(environment_name=" in source and "modal.Dict.from_id(" in source
    assert 'multiprocessing.get_context("spawn")' in source and "skip_if_exists=True" in source
