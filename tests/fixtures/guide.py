"""The Guide benchmark inputs: what SIT-05 sends the live model and what the offline suite renders again (Story 3.7).

The recorded fixture under `tests/fixtures/providers/llama3.2-3b/` holds the
response to `render_phrase_prompt(longest_rung(room), BENCHMARK_DERIVED)` on
the four-lock fixture Room, so the longest recorded prompt can be rendered
offline, and every other prompt the suite renders is checked against its length.
"""

from __future__ import annotations

from src.domain.schema import Derived, Room

RUNG_NAMES = ("nudge", "direction", "near_answer")

BENCHMARK_DERIVED = Derived(
    sessions=12,
    persistence=-0.4173,
    time_to_first_hint_s=1379.5,
    mean_rung_per_lock_type={"code": 2.71, "find": 1.37, "order": 2.05, "use_on": 0.84},
)
"""The widest Derived block the suite renders: every lock type, four-decimal persistence, a four-digit first hint."""


def rung_texts(room: Room) -> list[str]:
    """Every Rung of the Room, in Puzzle then ladder order."""
    return [getattr(puzzle.rungs, name) for puzzle in room.puzzles for name in RUNG_NAMES]


def longest_rung(room: Room) -> str:
    return max(rung_texts(room), key=len)
