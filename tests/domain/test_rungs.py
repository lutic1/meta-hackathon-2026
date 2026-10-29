"""Stories 5.6 and 3.1: the nudge threshold over the Derived block, computed in `domain/rungs.py` alone, and the Rung for each Puzzle selected in pure code from the session log (AD-4, AD-8, AD-10, AR-31)."""

import ast
from collections.abc import Sequence
from pathlib import Path

import pytest

from src.domain.rungs import (
    NUDGE_THRESHOLD_CEILING_MS,
    NUDGE_THRESHOLD_FLOOR_MS,
    NUDGE_THRESHOLD_MS,
    RUNG_SPACING_MS,
    TRICKSTER_WINDOW_MS,
    Judged,
    RungStep,
    is_returning,
    nudge_threshold_ms,
    select_rung,
    threshold_source,
    unscaled_thresholds,
)
from src.domain.schema import (
    Derived,
    Event,
    Room,
    RungChangeEvent,
    SessionState,
    Thresholds,
)
from src.domain.session import SessionStateMachine
from tests.domain.test_session import (
    SESSION,
    click,
    code,
    hint,
    idle,
    opening,
    order_start,
    order_stop,
    use_on,
)
from tests.fixtures.rooms import PZ

REPO = Path(__file__).resolve().parents[2]

DEMO = Thresholds(
    nudge_threshold_ms=15_000, nudge_threshold_base_ms=90_000, rung_spacing_ms=15_000, rung_spacing_base_ms=90_000,
    source="fresh",
)
"""What wiring hands `apply` at `DEMO_TIMESCALE=6` on `Derived.fresh()`."""


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


# --- Rung selection (Story 3.1) ------------------------------------------------------


def play(machine: SessionStateMachine, *events: Event, after: Sequence[Event] = ()) -> list[Event]:
    """The log as the API builds it live: each event appended to `after`, then any `rung_change` the machine selected on it."""
    log = list(after)
    for event in events:
        state = machine.replay(SESSION, [*log, event])
        log += [event, *state.rung_changes[sum(isinstance(e, RungChangeEvent) for e in log):]]
    return log


def rungs(log: list[Event]) -> list[RungChangeEvent]:
    return [event for event in log if isinstance(event, RungChangeEvent)]


def ticks(start: int, stop: int, every: int = 5_000) -> list[Event]:
    return [idle(t) for t in range(start, stop + 1, every)]


def summary(log: list[Event]) -> list[tuple[str, int, list[int], int]]:
    """Each `rung_change` as (puzzle, rung, triggered_by, t_ms), with the puzzle by its fixture name."""
    names = {pid: name for name, pid in PZ.items()}
    return [(names[r.puzzle_id], r.rung, r.triggered_by, r.t_ms) for r in rungs(log)]


# --- The thresholds a machine runs on -----------------------------------------------


def test_the_unscaled_thresholds_take_the_nudge_from_the_derived_block_and_never_scale_the_spacing():
    assert unscaled_thresholds(Derived.fresh()) == Thresholds(
        nudge_threshold_ms=90_000, nudge_threshold_base_ms=90_000, rung_spacing_ms=90_000, rung_spacing_base_ms=90_000,
        source="fresh",
    )
    low, high = unscaled_thresholds(derived(persistence=-1)), unscaled_thresholds(derived(persistence=1))
    assert (low.nudge_threshold_ms, high.nudge_threshold_ms) == (60_000, 135_000)
    assert low.rung_spacing_ms == high.rung_spacing_ms == 90_000 and low.source == high.source == "derived"


# --- Idle (FR-15) -----------------------------------------------------------------------


def test_no_rung_before_90000_ms_of_idle_and_the_nudge_on_the_first_tick_at_or_past_it(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    log = play(machine, opening(0), *ticks(5_000, 85_000))
    assert rungs(log) == [] and machine.replay(SESSION, log).current_rung[PZ["find_key"]] == 0
    log = play(machine, opening(0), *ticks(5_000, 90_000))
    # Idle counts from session start, so only the tick is named.
    assert summary(log) == [("find_key", 1, [18], 90_000)] and log[19] == rungs(log)[0]
    assert rungs(log)[0].text == code_and_find_room.puzzles[0].rungs.nudge
    assert (rungs(log)[0].phrased, rungs(log)[0].phrasing_ms) == (False, None)
    state = machine.replay(SESSION, log)
    assert state.current_rung[PZ["find_key"]] == 1 and state.rungs_used == 1


@pytest.mark.parametrize("activity", [click("rug", 10_000), code("door_code", "7342", 10_000)])
def test_idle_counts_from_the_last_click_or_lock_input(code_and_find_room: Room, activity: Event):
    machine = SessionStateMachine(code_and_find_room)
    log = play(machine, opening(0), activity, *ticks(15_000, 95_000))
    assert rungs(log) == []
    log = play(machine, opening(0), activity, *ticks(15_000, 100_000))
    assert summary(log) == [("find_key", 1, [1, 19], 100_000)]


def test_idle_counts_from_the_last_hint_request_too(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    wrong = [code("clock_code", "0", t) for t in (1_000, 2_000, 3_000)]
    # The ask inside the spacing repeats the nudge and opens nothing, but the direction's stall counts from it.
    log = play(machine, opening(0), *wrong, hint(None, 10_000), *ticks(15_000, 95_000))
    assert summary(log) == [("clock_code", 1, [1, 2, 3], 3_000)]
    log = play(machine, *ticks(100_000, 100_000), after=log)
    assert summary(log)[1:] == [("clock_code", 2, [5, len(log) - 2], 100_000)]


def test_an_idle_tick_never_resets_idle(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    every_second = play(machine, opening(0), *ticks(1_000, 90_000, every=1_000))
    assert summary(every_second) == [("find_key", 1, [90], 90_000)]


def test_a_puzzle_that_is_not_the_active_puzzle_never_receives_an_idle_rung(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    log = play(machine, opening(0), hint("clock_code", 1_000), *ticks(6_000, 600_000))
    assert {r.puzzle_id for r in rungs(log)} == {PZ["clock_code"]}
    assert [r.t_ms for r in rungs(log)] == [1_000, 91_000, 181_000]  # the ask opens the nudge; stalls open the rest


# --- The Active puzzle moves on after a solve (1.8) -----------------------------------


@pytest.mark.parametrize("before", [[], [hint("clock_code", 1_500)]])
def test_after_a_code_lock_opens_the_idle_nudge_goes_to_the_next_find_puzzle(code_and_find_room: Room, before: list[Event]):
    machine = SessionStateMachine(code_and_find_room)
    head = [opening(0), click("key", 1_000), *before, code("clock_code", "415", 2_000)]
    assert machine.replay(SESSION, head).active_puzzle_id == PZ["find_lantern"]
    log = play(machine, *head, *ticks(7_000, 92_000))
    opened, tick = log.index(head[-1]), log.index(idle(92_000))
    assert [entry for entry in summary(log) if entry[0] != "clock_code"] == [("find_lantern", 1, [opened, tick], 92_000)]


# --- Wrong attempts ---------------------------------------------------------------------


def test_three_wrong_codes_open_the_nudge_on_the_third(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    log = play(machine, opening(0), code("clock_code", "1", 1_000), code("clock_code", "2", 2_000))
    assert rungs(log) == []
    log = play(machine, opening(0), *(code("clock_code", str(n), n * 1_000) for n in (1, 2, 3)))
    assert summary(log) == [("clock_code", 1, [1, 2, 3], 3_000)]


def test_three_resolved_use_on_pairs_that_do_not_match_open_the_nudge(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    log = play(machine, opening(0), click("key", 1_000), *(use_on("key", "rug", t) for t in (2_000, 3_000, 4_000)))
    assert summary(log) == [("key_on_chest", 1, [2, 3, 4], 4_000)]


def test_three_mismatched_full_length_order_buffers_open_the_nudge(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    wrong = [click(name, 0) for _ in range(3) for name in ("lantern", "candle", "hourglass")]
    log = play(machine, opening(0), code("clock_code", "415"), order_start("shelf_order"), *wrong)
    assert summary(log) == [("shelf_order", 1, [5, 8, 11], 0)]


def test_clicks_refused_inputs_and_wrong_attempts_at_another_lock_never_count(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    log = play(
        machine,
        opening(0),
        code("clock_code", "000", 1_000),
        code("clock_code", "001", 2_000),
        *(click(name, 3_000) for name in ("rug", "door", "clock", "candle")),
        code("door_code", "7342", 4_000),  # unmet requires: refused
        use_on("lantern", "chest", 5_000),  # not in the inventory: refused
        order_start("shelf_order", 6_000),  # unmet requires: refused
        click("key", 7_000),
        use_on("key", "rug", 8_000),  # a Wrong attempt, at the chest
        use_on("key", "rug", 9_000),
    )
    assert rungs(log) == []
    state = machine.replay(SESSION, log)
    assert state.wrong_attempts[PZ["clock_code"]] == 2 and state.wrong_attempts[PZ["key_on_chest"]] == 2
    log = play(machine, code("clock_code", "002", 10_000), after=log)
    assert summary(log) == [("clock_code", 1, [1, 2, 13], 10_000)]


def test_an_order_stop_and_the_disarm_on_a_change_of_active_puzzle_never_count(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    events: list[Event] = [opening(0), code("clock_code", "415", 1_000)]
    for stop in (order_stop("shelf_order", 2_000), hint("find_key", 2_000)) * 2:
        # Two clicks of a three-click sequence, then a disarm: by `order_stop`, or by the hint moving the Active puzzle.
        events += [order_start("shelf_order", 2_000), click("lantern", 2_000), click("candle", 2_000), stop]
    log = play(machine, *events, order_start("shelf_order", 3_000), click("candle", 3_000))
    state = machine.replay(SESSION, log)
    assert all(r.puzzle_id != PZ["shelf_order"] for r in rungs(log)) and state.wrong_attempts[PZ["shelf_order"]] == 0
    assert state.order_buffer.clicks == [click("candle").interactable_id]


# --- Direction and near-answer: further stalls, further Wrong attempts, the spacing -----


@pytest.mark.parametrize("persistence", [-1, 0, 1])
def test_further_wrong_attempts_wait_out_the_90_second_spacing_at_any_persistence(code_and_find_room: Room, persistence: float):
    machine = SessionStateMachine(code_and_find_room, thresholds=unscaled_thresholds(derived(persistence=persistence)))
    wrong = [code("clock_code", str(n), n * 1_000) for n in range(1, 7)]
    log = play(machine, opening(0), *wrong, idle(50_000), idle(92_999))
    assert summary(log) == [("clock_code", 1, [1, 2, 3], 3_000)]
    log = play(machine, idle(93_000), after=log)
    assert summary(log)[1:] == [("clock_code", 2, [5, 6, 7, 10], 93_000)]
    log = play(machine, *(code("clock_code", str(n), 93_000 + n * 1_000) for n in range(1, 4)), idle(182_999), after=log)
    assert len(rungs(log)) == 2
    log = play(machine, idle(183_000), after=log)
    assert summary(log)[2:] == [("clock_code", 3, [12, 13, 14, 16], 183_000)]


@pytest.mark.parametrize("persistence, expected", [(0, [90_000, 180_000, 270_000]), (-1, [60_000, 150_000, 240_000]),
                                                   (1, [135_000, 270_000, 405_000])])
def test_each_further_stall_counts_from_the_previous_rung_and_the_spacing_never_scales(
    code_and_find_room: Room, persistence: float, expected: list[int]
):
    machine = SessionStateMachine(code_and_find_room, thresholds=unscaled_thresholds(derived(persistence=persistence)))
    log = play(machine, opening(0), *ticks(5_000, 450_000))
    assert [r.t_ms for r in rungs(log)] == expected and [r.rung for r in rungs(log)] == [1, 2, 3]
    first, second = rungs(log)[:2]
    # The direction names the nudge's `rung_change` (Idle counts from it) and its own tick.
    nudge_at = log.index(first)
    assert second.triggered_by == [nudge_at, log.index(second) - 1]


def test_after_the_near_answer_no_rung_change_follows(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    log = play(machine, opening(0), hint("clock_code", 0), *ticks(5_000, 300_000))
    assert [(r.puzzle_id, r.rung) for r in rungs(log)] == [(PZ["clock_code"], n) for n in (1, 2, 3)]
    log = play(machine, *(code("clock_code", str(n), 300_000 + n) for n in range(1, 10)), *ticks(305_000, 900_000), after=log)
    state = machine.replay(SESSION, log)
    assert len(rungs(log)) == 3 and state.wrong_attempts[PZ["clock_code"]] == 9
    assert state.current_rung[PZ["clock_code"]] == 3 and state.active_puzzle_id == PZ["clock_code"]


# --- apply reads the judged history -----------------------------------------------------


def test_apply_takes_the_judged_history_as_a_required_argument(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    with pytest.raises(TypeError):
        machine.apply(machine.initial(SESSION), idle(5_000))  # type: ignore[call-arg]


def test_apply_on_a_state_with_a_rung_open_never_lowers_it(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    log = play(machine, opening(0), *ticks(5_000, 200_000))
    state = machine.replay(SESSION, log)
    assert state.current_rung[PZ["find_key"]] == 2 and [r.t_ms for r in state.rung_changes] == [90_000, 180_000]
    after = machine.apply(state, idle(205_000), history=machine.history(SESSION, log))
    assert (after.current_rung, after.rungs_used, after.rung_changes) == (state.current_rung, 2, state.rung_changes)
    # A history that leaves out the open Rungs still never lowers one nor adds a lower `rung_change`.
    blind = machine.apply(state, idle(205_000), history=())
    assert (blind.current_rung, blind.rungs_used, blind.rung_changes) == (state.current_rung, 2, state.rung_changes)


def test_replay_and_result_fold_through_the_judged_history(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    log = play(machine, opening(0), *ticks(5_000, 300_000))
    assert [r.rung for r in rungs(log)] == [1, 2, 3]
    assert machine.replay(SESSION, log).rung_changes == rungs(log)
    result = machine.result(SESSION, log)
    assert result.rungs_used == 3 and next(p for p in result.puzzles if p.puzzle_id == PZ["find_key"]).rungs_used == 3


# --- The Loosen hook ----------------------------------------------------------------


def test_the_loosen_hook_opens_a_named_rung_at_once_outside_the_spacing():
    pid = PZ["clock_code"]
    events = [Judged(t_ms=0, activity=False, wrong_attempt=None, rung=None, active_puzzle_id=pid),
              Judged(t_ms=1_000, activity=False, wrong_attempt=None, rung=(pid, 1), active_puzzle_id=pid),
              Judged(t_ms=2_000, activity=False, wrong_attempt=None, rung=None, active_puzzle_id=pid)]
    assert select_rung(events, DEMO) is None
    assert select_rung(events, DEMO, loosen=(pid, "near_answer")) == RungStep(pid, 3, (2,))
    assert select_rung(events, DEMO, loosen=(pid, "nudge")) is None


def test_select_rung_returns_the_same_result_for_the_same_inputs():
    pid = PZ["find_key"]
    events = [Judged(t_ms=t, activity=False, wrong_attempt=None, rung=None, active_puzzle_id=pid) for t in (0, 15_000)]
    assert select_rung(events, DEMO) == select_rung(events, DEMO) == RungStep(pid, 1, (1,))
    assert select_rung([], DEMO) is None


# --- Replay equals live -------------------------------------------------------------------


def test_replay_reaches_exactly_the_rungs_appended_live_and_appends_none(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    events: list[Event] = [
        opening(0), click("rug", 1_000), *(code("clock_code", "9", t) for t in (2_000, 3_000, 4_000)),
        hint(None, 5_000), *ticks(10_000, 100_000), click("key", 101_000), *(use_on("key", "rug", 102_000 + t) for t in range(3)),
        code("clock_code", "415", 110_000), *ticks(115_000, 400_000),
    ]
    log: list[Event] = []
    live: SessionState = machine.initial(SESSION)
    for event in events:
        live = machine.replay(SESSION, [*log, event])
        log += [event, *live.rung_changes[len(rungs(log)):]]
    replayed = machine.replay(SESSION, log)
    assert len(rungs(log)) >= 5
    assert (replayed.current_rung, replayed.wrong_attempts, replayed.rungs_used, replayed.rung_changes) == (
        live.current_rung, live.wrong_attempts, live.rungs_used, live.rung_changes)
    assert replayed.rung_changes == rungs(log)  # each Rung once: replay appends none
    assert SessionStateMachine(four_lock_room).replay(SESSION, log) == replayed
    assert machine.result(SESSION, log).rungs_used == replayed.rungs_used


# --- DEMO_TIMESCALE=6 (FR-24) -------------------------------------------------------------


def test_at_timescale_6_three_rungs_arrive_by_38000_ms_on_wrong_codes(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    log = play(machine, opening(0), *(code("clock_code", "0", t) for t in range(2_000, 40_001, 2_000)))
    assert [(r.rung, r.t_ms) for r in rungs(log)] == [(1, 6_000), (2, 22_000), (3, 38_000)]


def test_at_timescale_6_an_idle_only_log_reaches_the_three_rungs_at_15_30_and_45_seconds(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    log = play(machine, opening(0), *ticks(1_000, 60_000, every=1_000))
    assert [(r.rung, r.t_ms) for r in rungs(log)] == [(1, 15_000), (2, 30_000), (3, 45_000)]


# --- Asking opens the next Rung, the spacing allowing (owner decision Oct 29, FR-15/16) -----------------


def test_an_ask_with_no_rung_showing_opens_the_nudge_on_the_active_puzzle_at_once(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    log = play(machine, opening(0), hint(None, 5_000))
    assert summary(log) == [("find_key", 1, [1], 5_000)]
    state = machine.replay(SESSION, log)
    assert state.current_rung[PZ["find_key"]] == 1 and machine.current_rung_text(state) == code_and_find_room.puzzles[0].rungs.nudge
    # The ask still counts as a hint used, and as an Early ask: no Rung was showing when it was made.
    result = next(p for p in machine.result(SESSION, log).puzzles if p.puzzle_id == PZ["find_key"])
    assert result.hint_requested and result.early_ask and result.rungs_used == 1


def test_an_ask_inside_the_spacing_repeats_the_rung_and_reports_the_wait_and_past_it_opens_the_next(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    log = play(machine, opening(0), hint(None, 1_000))
    assert machine.next_hint_ms(machine.replay(SESSION, log), 1_000) == 15_000  # the full spacing after the Rung it opened
    log = play(machine, hint(None, 10_000), after=log)
    state = machine.replay(SESSION, log)
    assert summary(log) == [("find_key", 1, [1], 1_000)] and state.current_rung[PZ["find_key"]] == 1
    assert machine.next_hint_ms(state, 10_000) == 6_000  # 15000 ms spacing, 9000 ms gone
    log = play(machine, hint(None, 16_000), hint(None, 31_000), after=log)
    assert summary(log)[1:] == [("find_key", 2, [4], 16_000), ("find_key", 3, [6], 31_000)]
    # Nothing follows the near-answer: an ask repeats it, with no wait to count down.
    log = play(machine, hint(None, 60_000), after=log)
    state = machine.replay(SESSION, log)
    assert len(rungs(log)) == 3 and machine.next_hint_ms(state, 60_000) is None


def test_the_wait_counts_from_the_puzzles_last_rung_change_whatever_opened_it(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    wrong = [code("clock_code", "0", t) for t in (1_000, 2_000, 3_000)]
    log = play(machine, opening(0), *wrong)
    assert summary(log) == [("clock_code", 1, [1, 2, 3], 3_000)]
    state = machine.replay(SESSION, log)
    assert machine.next_hint_ms(state, 5_000) == 13_000
    log = play(machine, hint(None, 5_000), hint(None, 18_000), after=log)
    assert summary(log)[1:] == [("clock_code", 2, [6], 18_000)]
    # The next Puzzle has no Rung showing: an ask there opens its nudge at once, whatever the clock's wait.
    log = play(machine, click("key", 19_000), code("clock_code", "415", 20_000), hint(None, 21_000), after=log)
    assert summary(log)[2:] == [("find_lantern", 1, [10], 21_000)]
    assert machine.next_hint_ms(machine.replay(SESSION, log), 21_000) == 15_000


def test_asks_replay_to_exactly_the_rungs_appended_live(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room, thresholds=DEMO)
    log = play(machine, opening(0), hint(None, 1_000), hint(None, 2_000), *ticks(5_000, 20_000), hint(None, 21_000),
               hint("clock_code", 22_000), hint(None, 40_000))
    replayed = machine.replay(SESSION, log)
    assert replayed.rung_changes == rungs(log) and len(rungs(log)) == 4
    assert SessionStateMachine(four_lock_room, thresholds=DEMO).replay(SESSION, log) == replayed


def test_an_ask_once_the_exit_is_open_opens_nothing_and_has_no_wait(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    log = play(machine, opening(0), click("key", 1_000), code("clock_code", "415", 2_000), click("lantern", 3_000),
               code("door_code", "7342", 4_000), hint(None, 5_000))
    state = machine.replay(SESSION, log)
    assert rungs(log) == [] and state.active_puzzle_id is None and machine.next_hint_ms(state, 5_000) is None


def test_current_rung_text_is_the_verbatim_text_of_the_active_puzzles_current_rung(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    clock = next(p for p in code_and_find_room.puzzles if p.id == PZ["clock_code"])
    log = play(machine, opening(0), code("clock_code", "0", 1_000))
    assert machine.current_rung_text(machine.replay(SESSION, log)) is None  # no Rung open
    log = play(machine, *(code("clock_code", "0", t) for t in range(2_000, 22_001, 2_000)), after=log)
    state = machine.replay(SESSION, log)
    assert state.current_rung[PZ["clock_code"]] == 2 and machine.current_rung_text(state) == clock.rungs.direction
    exited = play(machine, click("key", 30_000), code("clock_code", "415", 31_000), click("lantern", 32_000),
                  code("door_code", "7342", 33_000), after=log)
    assert machine.current_rung_text(machine.replay(SESSION, exited)) is None  # no Puzzle is active
