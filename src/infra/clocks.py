"""The session and build clocks behind the `Clock` port (AD-10).

Both read `time.monotonic_ns` and count milliseconds since they were made,
so an interval is the difference of two readings. The session clock is the
only place `DEMO_TIMESCALE` touches time: `thresholds` divides the nudge
threshold, the Rung spacing and the Trickster window that wiring passes
into `SessionStateMachine.apply`, while `now_ms`, which stamps `t_ms`, is
never scaled. The build clock has no timescale at all: stage timings and
the capture timer read real milliseconds.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

NS_PER_MS = 1_000_000


@dataclass(frozen=True, slots=True)
class SessionThresholds:
    """The thresholds `apply` compares against `t_ms`, already divided by the timescale."""

    nudge_threshold_ms: int
    rung_spacing_ms: int
    trickster_window_ms: int


class SessionClock:
    """Session time: unscaled milliseconds for `t_ms`, scaled thresholds for `apply`."""

    def __init__(self, timescale: int = 1, *, monotonic_ns: Callable[[], int] = time.monotonic_ns) -> None:
        if timescale < 1:
            raise ValueError(f"DEMO_TIMESCALE must be at least 1, got {timescale}")
        self.timescale = timescale
        self._monotonic_ns = monotonic_ns
        self._start_ns = monotonic_ns()

    def now_ms(self) -> int:
        return (self._monotonic_ns() - self._start_ns) // NS_PER_MS

    def thresholds(self, *, nudge_threshold_ms: int, rung_spacing_ms: int, trickster_window_ms: int) -> SessionThresholds:
        """Each 1x threshold divided by the timescale: 90000 ms is 15000 ms at `DEMO_TIMESCALE=6`."""
        return SessionThresholds(
            nudge_threshold_ms=nudge_threshold_ms // self.timescale,
            rung_spacing_ms=rung_spacing_ms // self.timescale,
            trickster_window_ms=trickster_window_ms // self.timescale,
        )


class BuildClock:
    """Build time for stage timings and the capture timer; it never sees the timescale."""

    def __init__(self, *, monotonic_ns: Callable[[], int] = time.monotonic_ns) -> None:
        self._monotonic_ns = monotonic_ns
        self._start_ns = monotonic_ns()

    def now_ms(self) -> int:
        return (self._monotonic_ns() - self._start_ns) // NS_PER_MS
