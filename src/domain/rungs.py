"""The Rung thresholds over the Derived block and Rung selection (AD-4, AD-8, AD-10, AR-31).

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

`select_rung(events, thresholds)` runs inside `SessionStateMachine.apply`
after every event but a `rung_change` or a `hint_request`, over the log as
`apply` judged it (`Judged`), and names at most one Rung to open on the
Active puzzle. Time reaches it only as `t_ms` and the session's
`Thresholds`, whose nudge threshold `nudge_threshold_ms` computed from the
Derived block, so the same log always selects the same Rungs, live or
replayed. This module imports only the standard library, pydantic and the
domain (AD-1).

Idle counts from the `t_ms` of the last click, lock input or `hint_request`;
an `idle_tick` never resets it. The nudge (rung 1) opens once Idle reaches
the nudge threshold or after 3 Wrong attempts at the lock. The direction and
the near-answer each need a further stall (Idle at the nudge threshold,
counted from the later of the last click, lock input or `hint_request` and
the Puzzle's previous `rung_change`) or 3 further Wrong attempts, and open
no sooner than the Rung spacing after the previous Rung, whatever the
persistence. Nothing follows the near-answer: no reveal and no skip.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from .schema import Derived, Milliseconds, PuzzleId, RungName, Thresholds, TricksterEdit

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
WRONG_ATTEMPTS_PER_RUNG = 3
RUNG_NAMES: tuple[RungName, ...] = ("nudge", "direction", "near_answer")
"""Rung `n` is `RUNG_NAMES[n - 1]`; rung 0 is no Rung open."""
NEAR_ANSWER = len(RUNG_NAMES)


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


def unscaled_thresholds(derived: Derived) -> Thresholds:
    """The 1x `Thresholds` for `derived`, for a machine that wiring has not handed the session's."""
    nudge_ms = nudge_threshold_ms(derived)
    return Thresholds(
        nudge_threshold_ms=nudge_ms,
        nudge_threshold_base_ms=nudge_ms,
        rung_spacing_ms=RUNG_SPACING_MS,
        rung_spacing_base_ms=RUNG_SPACING_MS,
        source=threshold_source(derived),
    )


@dataclass(frozen=True, slots=True)
class Judged:
    """One session-log event as `apply` judged it; its index in the sequence is its position in the log."""

    t_ms: int
    activity: bool
    """A click, lock input or `hint_request`: Idle counts from the last one."""
    wrong_attempt: PuzzleId | None
    """The Puzzle whose lock this event was a Wrong attempt at, if any."""
    rung: tuple[PuzzleId, int] | None
    """The Rung this event opened: a `rung_change`, or the Rung `select_rung` chose on it."""
    active_puzzle_id: PuzzleId | None
    """The Active puzzle after this event."""
    accepted_edit: TricksterEdit | None = None
    """The edit this event's accepted `trickster_card` carries: the Effective room holds it from this event on."""


@dataclass(frozen=True, slots=True)
class RungStep:
    """The Rung to open now and the log positions of the events that triggered it."""

    puzzle_id: PuzzleId
    rung: int
    triggered_by: tuple[int, ...]


def select_rung(
    events: Sequence[Judged],
    thresholds: Thresholds,
    *,
    loosen: tuple[PuzzleId, RungName] | None = None,
) -> RungStep | None:
    """The Rung the last event opens on the Active puzzle, or None.

    `events` is the log up to and including the event just applied, and
    `thresholds` the session's, already divided by the timescale; the
    Derived block reaches the timing only through its nudge threshold.
    `loosen` is the Loosen hook: an accepted `loosen` card opens the named
    Rung on its Puzzle at once, outside the spacing, triggered by the card.
    """
    if not events:
        return None
    now = len(events) - 1
    if loosen is not None:
        puzzle_id, name = loosen
        rung = RUNG_NAMES.index(name) + 1
        return RungStep(puzzle_id, rung, (now,)) if rung > _last_rung(events, puzzle_id)[0] else None
    puzzle_id = events[now].active_puzzle_id
    if puzzle_id is None:
        return None
    rung, since = _last_rung(events, puzzle_id)
    if rung >= NEAR_ANSWER:
        return None
    t_ms = events[now].t_ms
    if since is not None and t_ms - events[since].t_ms < thresholds.rung_spacing_ms:
        return None
    start = 0 if since is None else since + 1
    wrong = [i for i in range(start, now + 1) if events[i].wrong_attempt == puzzle_id]
    if len(wrong) >= WRONG_ATTEMPTS_PER_RUNG:
        triggered = wrong[-WRONG_ATTEMPTS_PER_RUNG:]
        return RungStep(puzzle_id, rung + 1, tuple(triggered if triggered[-1] == now else [*triggered, now]))
    anchor = _idle_anchor(events, since)
    idle_ms = t_ms - (0 if anchor is None else events[anchor].t_ms)
    if idle_ms >= thresholds.nudge_threshold_ms:
        return RungStep(puzzle_id, rung + 1, (now,) if anchor is None else (anchor, now))
    return None


def _last_rung(events: Sequence[Judged], puzzle_id: PuzzleId) -> tuple[int, int | None]:
    """The Puzzle's current Rung and the position of the event that opened it (0 and None while none is open)."""
    for i in range(len(events) - 1, -1, -1):
        rung = events[i].rung
        if rung is not None and rung[0] == puzzle_id:
            return rung[1], i
    return 0, None


def _idle_anchor(events: Sequence[Judged], since: int | None) -> int | None:
    """The position Idle counts from: the last click, lock input or `hint_request`, or `since` when later; None at session start."""
    for i in range(len(events) - 1, -1 if since is None else since, -1):
        if events[i].activity:
            return i
    return since
