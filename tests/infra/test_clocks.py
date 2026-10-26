"""Story 1.10: the session clock scales only the thresholds it hands to `apply`; the build clock scales nothing (AD-10)."""

import inspect

import pytest

from src.domain.clock import Clock
from src.infra.clocks import BuildClock, SessionClock, SessionThresholds

NUDGE_MS, SPACING_MS, WINDOW_MS = 90_000, 90_000, 180_000


class Ticker:
    """A monotonic_ns source the tests advance by hand."""

    def __init__(self) -> None:
        self.ns = 5_000_000_000

    def __call__(self) -> int:
        return self.ns

    def advance_ms(self, ms: int) -> None:
        self.ns += ms * 1_000_000


def test_the_session_clock_divides_the_three_thresholds_by_the_timescale():
    clock = SessionClock(6)
    assert clock.thresholds(nudge_threshold_ms=NUDGE_MS, rung_spacing_ms=SPACING_MS, trickster_window_ms=WINDOW_MS) == (
        SessionThresholds(nudge_threshold_ms=15_000, rung_spacing_ms=15_000, trickster_window_ms=30_000)
    )
    assert SessionClock().thresholds(nudge_threshold_ms=NUDGE_MS, rung_spacing_ms=SPACING_MS, trickster_window_ms=WINDOW_MS) == (
        SessionThresholds(nudge_threshold_ms=NUDGE_MS, rung_spacing_ms=SPACING_MS, trickster_window_ms=WINDOW_MS)
    )


def test_the_session_clock_never_scales_the_milliseconds_it_supplies_for_t_ms():
    ticker = Ticker()
    clock = SessionClock(6, monotonic_ns=ticker)
    assert clock.now_ms() == 0
    ticker.advance_ms(90_000)
    assert clock.now_ms() == 90_000
    ticker.advance_ms(2_500)
    assert clock.now_ms() - 90_000 == 2_500


def test_the_build_clock_never_scales_an_interval_and_takes_no_timescale():
    ticker = Ticker()
    clock = BuildClock(monotonic_ns=ticker)
    start = clock.now_ms()
    ticker.advance_ms(12_345)
    assert clock.now_ms() - start == 12_345
    assert "timescale" not in inspect.signature(BuildClock).parameters


def test_both_clocks_satisfy_the_port_and_read_a_real_monotonic_source():
    session: Clock = SessionClock(6)
    build: Clock = BuildClock()
    assert 0 <= session.now_ms() < 1_000 and 0 <= build.now_ms() < 1_000
    assert session.now_ms() <= session.now_ms() and build.now_ms() <= build.now_ms()


@pytest.mark.parametrize("timescale", [0, -1])
def test_a_timescale_under_one_is_refused(timescale):
    with pytest.raises(ValueError, match="DEMO_TIMESCALE"):
        SessionClock(timescale)
