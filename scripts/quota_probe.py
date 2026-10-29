#!/usr/bin/env python3
"""Check live that the build quota's slot claim is atomic across processes, on an ephemeral Dict (AD-9, Story 7.10, decisions 18 and 23).

    uv run scripts/quota_probe.py               # Environment dev
    uv run scripts/quota_probe.py --env main

The first line printed is the Modal Environment. Two races then run, each
against its own `modal.Dict.ephemeral()` created in that Environment, never
against `keyframe-jobs`, so no real quota slot is claimed. In each race
every claimer is a separate process that opens the Dict by id and, once all
are ready, walks the 20 slot keys the hosted `JobStore` uses (`build:1` to
`build:20`) with `put(slot, claimer, skip_if_exists=True)`, as
`DictJobStore.reserve_build` does, and reports the slot it took or none.

1. A fresh quota: 30 processes race; exactly 20 must succeed, each on its
   own slot, and the Dict must hold 20 slots naming a claimer.
2. The last slot: 19 slots are prefilled and 8 processes race; exactly one
   must win, and no prefilled slot may be overwritten.

Each race's counts are printed; any other outcome, a claimer that never
reports included, exits 1. The ephemeral Dicts are gone when the script
ends. Needs a Modal token; it makes no model call and writes no file.
"""

from __future__ import annotations

import argparse
import multiprocessing
import queue
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier
from pathlib import Path
from typing import TYPE_CHECKING

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from src.infra.modal import BUILD_QUOTA, DictLike, slot_key

if TYPE_CHECKING:
    import modal

ENVIRONMENT = "dev"
"""The Modal Environment the ephemeral Dicts are created in; never the real quota's Dict, whatever the Environment."""
SLOTS = [slot_key(n) for n in range(1, BUILD_QUOTA + 1)]
"""The 20 slot keys, in the order `reserve_build` tries them."""
CLAIMERS = 30
"""Processes racing for a fresh quota; exactly `BUILD_QUOTA` must win."""
LAST_SLOT_CLAIMERS = 8
"""Processes racing for the one slot left after 19 are prefilled; exactly one must win."""
PREFILL = "prefilled"
"""The value the 19 prefilled slots hold; a claimer never writes it."""
START_TIMEOUT_S = 120
"""How long a ready claimer waits for the others before the race is called off."""
RESULT_TIMEOUT_S = 300
"""How long the script waits for each claimer's report."""


def claim(slots: DictLike, claimer: str) -> str | None:
    """`DictJobStore.reserve_build`'s walk: the first slot this claimer's conditional write took; `None` with all 20 taken."""
    return next((key for key in SLOTS if slots.put(key, claimer, skip_if_exists=True)), None)


@dataclass(frozen=True)
class Tally:
    """One race's counts against the number of winners it must have."""

    race: str
    claimers: int
    expected: int
    wins: int
    """Claimers that reported a slot."""
    unique: int
    """Distinct slots among those reports."""
    stored: int
    """Slot keys whose stored value names one of the claimers."""
    overwritten: int
    """Prefilled slots that no longer hold `PREFILL`."""

    @property
    def ok(self) -> bool:
        return self.wins == self.unique == self.stored == self.expected and self.overwritten == 0

    def line(self) -> str:
        return (
            f"{self.race}: {self.claimers} claimers, {self.wins} successes, {self.unique} unique slots, "
            f"{self.stored} slots holding a claimer, {self.overwritten} prefilled slots overwritten; "
            f"expected exactly {self.expected}: {'ok' if self.ok else 'FAILED'}"
        )


def tally(race: str, won: Mapping[str, str | None], slots: DictLike, *, expected: int, prefilled: Sequence[str] = ()) -> Tally:
    """Count one race from each claimer's report and the Dict as it ended."""
    taken = [slot for slot in won.values() if slot is not None]
    return Tally(
        race=race,
        claimers=len(won),
        expected=expected,
        wins=len(taken),
        unique=len(set(taken)),
        stored=sum(1 for key in SLOTS if slots.get(key) in won),
        overwritten=sum(1 for key in prefilled if slots.get(key) != PREFILL),
    )


def names(count: int) -> list[str]:
    return [f"claimer-{n:02d}" for n in range(1, count + 1)]


def probe[S: DictLike](open_slots: Callable[[], AbstractContextManager[S]], race: Callable[[S, list[str]], dict[str, str | None]]) -> int:
    """Run both races, each on a Dict `open_slots` opens, print their counts, and return 0 only when both came out exactly right."""
    with open_slots() as slots:
        fresh = tally("fresh quota", race(slots, names(CLAIMERS)), slots, expected=BUILD_QUOTA)
    with open_slots() as slots:
        for key in SLOTS[:-1]:
            slots.put(key, PREFILL)
        last = tally("last slot", race(slots, names(LAST_SLOT_CLAIMERS)), slots, expected=1, prefilled=SLOTS[:-1])
    for result in (fresh, last):
        print(result.line(), flush=True)
    if fresh.ok and last.ok:
        print(
            f"quota probe passed: the conditional put let exactly {BUILD_QUOTA} of {CLAIMERS} processes claim a slot, "
            f"and exactly 1 of {LAST_SLOT_CLAIMERS} the last one"
        )
        return 0
    print("quota probe failed: the slot claim is not atomic across processes; the quota goes through correct-course before uploads", file=sys.stderr)
    return 1


def _claim_in_process(dict_id: str, claimer: str, start: Barrier, results: Queue[tuple[str, str | None]]) -> None:
    """One claimer: open the Dict by id, wait for every other claimer, then claim and report."""
    import modal

    slots = modal.Dict.from_id(dict_id)
    slots.hydrate()
    start.wait(START_TIMEOUT_S)
    results.put((claimer, claim(slots, claimer)))


def process_race(slots: modal.Dict, claimers: list[str]) -> dict[str, str | None]:
    """Each claimer in its own spawned process, released together; the slot each reported, leaving out any that never did."""
    context = multiprocessing.get_context("spawn")
    start = context.Barrier(len(claimers))
    results: Queue[tuple[str, str | None]] = context.Queue()
    processes = [context.Process(target=_claim_in_process, args=(slots.object_id, name, start, results)) for name in claimers]
    for process in processes:
        process.start()
    won: dict[str, str | None] = {}
    try:
        for _ in processes:
            name, slot = results.get(timeout=RESULT_TIMEOUT_S)
            won[name] = slot
    except queue.Empty:
        print(f"{len(claimers) - len(won)} claimers never reported", file=sys.stderr)
    for process in processes:
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
    return won


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Race separate processes for the build quota's slot keys on an ephemeral Dict.")
    parser.add_argument("--env", default=ENVIRONMENT, help=f"the Modal Environment the ephemeral Dicts are created in (default {ENVIRONMENT})")
    args = parser.parse_args(argv)
    print(f"Modal Environment: {args.env}", flush=True)
    import modal

    return probe(lambda: modal.Dict.ephemeral(environment_name=args.env), process_race)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
