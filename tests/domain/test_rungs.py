"""Story 5.6: the nudge threshold over the Derived block and its source, computed in `domain/rungs.py` alone (AD-8, AR-31)."""

import ast
from pathlib import Path

import pytest

from src.domain.rungs import (
    NUDGE_THRESHOLD_CEILING_MS,
    NUDGE_THRESHOLD_FLOOR_MS,
    NUDGE_THRESHOLD_MS,
    RUNG_SPACING_MS,
    TRICKSTER_WINDOW_MS,
    is_returning,
    nudge_threshold_ms,
    threshold_source,
)
from src.domain.schema import Derived

REPO = Path(__file__).resolve().parents[2]


def derived(sessions: int = 1, persistence: float = 0) -> Derived:
    return Derived(sessions=sessions, persistence=persistence, time_to_first_hint_s=40.0, mean_rung_per_lock_type={})


def test_the_fixed_values_are_the_spec_numbers():
    assert (NUDGE_THRESHOLD_MS, NUDGE_THRESHOLD_FLOOR_MS, NUDGE_THRESHOLD_CEILING_MS) == (90_000, 60_000, 135_000)
    assert (RUNG_SPACING_MS, TRICKSTER_WINDOW_MS) == (90_000, 180_000)


@pytest.mark.parametrize(("persistence", "threshold_ms"), [
    (0, 90_000),
    (1, 135_000),
    (-1, 60_000),  # 45 s before the 60 s floor
    (0.5, 112_500),
    (-0.5, 67_500),
    (-0.6, 63_000),
    (-0.7, 60_000),
])
def test_the_nudge_threshold_scales_with_persistence_inside_the_floor_and_ceiling(persistence: float, threshold_ms: int):
    assert nudge_threshold_ms(derived(persistence=persistence)) == threshold_ms


def test_a_fresh_profile_waits_the_plain_90_seconds():
    assert nudge_threshold_ms(Derived.fresh()) == 90_000


@pytest.mark.parametrize(("sessions", "returning", "source"), [(0, False, "fresh"), (1, True, "derived"), (7, True, "derived")])
def test_a_played_room_makes_a_returning_player_and_the_derived_block_the_source(sessions: int, returning: bool, source: str):
    block = derived(sessions=sessions)
    assert (is_returning(block), threshold_source(block)) == (returning, source)
    assert threshold_source(Derived.fresh()) == "fresh"


def test_no_other_module_under_src_computes_the_nudge_threshold():
    """The clamp's numbers appear as literals only in `domain/rungs.py`."""
    numbers = {NUDGE_THRESHOLD_MS, NUDGE_THRESHOLD_FLOOR_MS, NUDGE_THRESHOLD_CEILING_MS}
    holders = sorted(
        path.relative_to(REPO).as_posix()
        for path in (REPO / "src").rglob("*.py")
        if any(isinstance(node, ast.Constant) and node.value in numbers for node in ast.walk(ast.parse(path.read_text())))
    )
    assert holders == ["src/domain/rungs.py"]
