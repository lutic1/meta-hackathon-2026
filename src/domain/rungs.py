"""The Rung thresholds over the Derived block (AD-4, AD-8, AD-10, AR-31).

The nudge threshold is `clamp(90000 * (1 + 0.5 * persistence), 60000, 135000)`
ms, computed here alone (the spec's player-profile numbers): a returning
player who kept going waits longer for the nudge, one who asked early waits
less, and a fresh profile waits the plain 90 s. The Rung spacing and the
Trickster window are fixed 1x values. These are the thresholds wiring passes
into `apply` after the session clock has divided them by `DEMO_TIMESCALE`
(AD-10); this module never sees the timescale. The threshold's source is the
Derived block for a returning player (`sessions` >= 1) and `Derived.fresh()`
otherwise; in Local mode the same test decides whether a session start is
greeted.
`select_rung(events, derived, thresholds)` joins with the Rung stories.
"""

from __future__ import annotations

from typing import Literal

from .schema import Derived, Milliseconds

ThresholdSource = Literal["derived", "fresh"]
"""`Thresholds.source`: the Derived block of a returning player, or `Derived.fresh()`."""

NUDGE_THRESHOLD_MS: Milliseconds = 90_000
"""The 1x nudge threshold at `persistence` 0."""
NUDGE_THRESHOLD_FLOOR_MS: Milliseconds = 60_000
NUDGE_THRESHOLD_CEILING_MS: Milliseconds = 135_000
RUNG_SPACING_MS: Milliseconds = 90_000
"""The direction and near-answer Rungs follow at least this long apart; only the nudge threshold scales."""
TRICKSTER_WINDOW_MS: Milliseconds = 180_000
"""`apply` opens a Trickster window only when the previous one closed at least this long ago (AD-4)."""


def is_returning(derived: Derived) -> bool:
    """Whether the block comes from a played room: `sessions` >= 1 is greeted and sets the threshold."""
    return derived.sessions >= 1


def nudge_threshold_ms(derived: Derived) -> Milliseconds:
    """The 1x nudge threshold from `persistence`: 90 s at 0, clamped to 60 s and 135 s, rounded to the millisecond."""
    scaled = round(NUDGE_THRESHOLD_MS * (1 + 0.5 * derived.persistence))
    return min(max(scaled, NUDGE_THRESHOLD_FLOOR_MS), NUDGE_THRESHOLD_CEILING_MS)


def threshold_source(derived: Derived) -> ThresholdSource:
    """Where the threshold came from: the Derived block of a returning player, else `Derived.fresh()`."""
    return "derived" if is_returning(derived) else "fresh"
