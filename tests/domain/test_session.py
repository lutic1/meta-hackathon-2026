"""Story 1.8: the session state machine, code and find locks, the Active puzzle and the Room result (AD-4)."""

import inspect
from typing import Any

from src.domain import session as session_module
from src.domain.schema import (
    ClickEvent,
    CodeInput,
    Event,
    HintRequestEvent,
    IdleTickEvent,
    LockInputEvent,
    OpeningLineEvent,
    OrderBuffer,
    OrderStartInput,
    OrderStopInput,
    Room,
    RungChangeEvent,
    SessionState,
    UseOnInput,
)
from src.domain.session import SessionStateMachine
from tests.fixtures.rooms import IX, PZ

SESSION = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"


# --- Event builders ----------------------------------------------------------


def click(name: str, t: int = 0) -> ClickEvent:
    return ClickEvent(type="click", interactable_id=IX[name], t_ms=t)


def code(name: str, text: str, t: int = 0) -> LockInputEvent:
    return LockInputEvent(type="lock_input", input=CodeInput(type="code", puzzle_id=PZ[name], code=text), t_ms=t)


def order_start(name: str, t: int = 0) -> LockInputEvent:
    return LockInputEvent(type="lock_input", input=OrderStartInput(type="order_start", puzzle_id=PZ[name]), t_ms=t)


def order_stop(name: str, t: int = 0) -> LockInputEvent:
    return LockInputEvent(type="lock_input", input=OrderStopInput(type="order_stop", puzzle_id=PZ[name]), t_ms=t)


def use_on(item: str, target: str, t: int = 0) -> LockInputEvent:
    return LockInputEvent(type="lock_input", input=UseOnInput(type="use_on", item=IX[item], target=IX[target]), t_ms=t)


def hint(name: str | None = None, t: int = 0) -> HintRequestEvent:
    return HintRequestEvent(type="hint_request", puzzle_id=None if name is None else PZ[name], t_ms=t)


def idle(t: int) -> IdleTickEvent:
    return IdleTickEvent(type="idle_tick", t_ms=t)


def rung(name: str, level: int, t: int, *triggered_by: int) -> RungChangeEvent:
    return RungChangeEvent(type="rung_change", puzzle_id=PZ[name], rung=level, triggered_by=list(triggered_by),
                           phrased=False, phrasing_ms=None, text=f"rung {level}", t_ms=t)


def opening(t: int = 0) -> OpeningLineEvent:
    return OpeningLineEvent(type="opening_line", kind="welcome", text="Welcome. The room is listening.", t_ms=t)


# --- Room variants and runners ------------------------------------------------


def with_puzzle(room: Room, name: str, **fields: Any) -> Room:
    """The room with one puzzle's fields replaced, built directly as a Room."""
    data = room.model_dump()
    for puzzle in data["puzzles"]:
        if puzzle["id"] == PZ[name]:
            puzzle.update(fields)
    return Room.model_validate(data)


def run(machine: SessionStateMachine, *events: Event) -> SessionState:
    state = machine.initial(SESSION)
    for event in events:
        state = machine.apply(state, event)
    return state


# --- find locks ---------------------------------------------------------------


def test_a_click_on_the_target_of_an_available_find_puzzle_opens_it_into_the_inventory(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, click("key"))
    assert state.locks_open == [PZ["find_key"]] and state.inventory == [IX["key"]]
    assert all(count == 0 for count in state.wrong_attempts.values())


def test_the_same_click_while_a_required_puzzle_is_closed_opens_nothing_and_is_not_a_wrong_attempt(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, click("lantern"))
    assert state.locks_open == [] and state.inventory == []
    assert sum(state.wrong_attempts.values()) == 0
    after = machine.apply(machine.apply(state, click("key")), click("lantern"))
    assert after.locks_open == [PZ["find_key"], PZ["find_lantern"]] and after.inventory == [IX["key"], IX["lantern"]]


def test_a_click_on_any_other_hotspot_changes_no_lock_and_counts_nothing(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    fresh = machine.initial(SESSION)
    for name in ("rug", "clock", "door", "chest"):
        state = machine.apply(fresh, click(name))
        assert state.locks_open == [] and state.inventory == [] and sum(state.wrong_attempts.values()) == 0


# --- code locks ---------------------------------------------------------------


def test_codes_are_compared_trimmed_and_case_folded(code_and_find_room):
    room = with_puzzle(code_and_find_room, "clock_code", solution={"lock_type": "code", "code": "AB12"})
    machine = SessionStateMachine(room)
    state = run(machine, code("clock_code", " ab12 "))
    assert state.locks_open == [PZ["clock_code"]] and state.wrong_attempts[PZ["clock_code"]] == 0


def test_any_other_input_leaves_the_lock_closed_and_adds_exactly_one_wrong_attempt(code_and_find_room):
    room = with_puzzle(code_and_find_room, "clock_code", solution={"lock_type": "code", "code": "AB12"})
    machine = SessionStateMachine(room)
    state = run(machine, code("clock_code", "AB13"), code("clock_code", ""), code("clock_code", "ab 12"))
    assert state.locks_open == []
    assert state.wrong_attempts[PZ["clock_code"]] == 3
    assert all(count == 0 for pid, count in state.wrong_attempts.items() if pid != PZ["clock_code"])


def test_a_correct_input_to_a_puzzle_with_unmet_requires_never_opens_it_and_is_not_a_wrong_attempt(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, code("door_code", "7342"), code("door_code", "0000"))
    assert state.locks_open == [] and state.wrong_attempts[PZ["door_code"]] == 0


def test_an_input_to_an_open_or_unknown_puzzle_counts_nothing(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, code("clock_code", "415"), code("clock_code", "000"), code("find_key", "415"))
    assert state.locks_open == [PZ["clock_code"]] and sum(state.wrong_attempts.values()) == 0


# --- The Active puzzle ----------------------------------------------------------


def test_a_fresh_session_targets_the_earliest_available_puzzle(code_and_find_room):
    assert SessionStateMachine(code_and_find_room).initial(SESSION).active_puzzle_id == PZ["find_key"]


def test_after_a_code_puzzle_opens_the_active_puzzle_moves_to_the_next_available_unsolved_one(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, click("key"))
    assert state.active_puzzle_id == PZ["clock_code"]
    state = machine.apply(state, code("clock_code", "415"))
    assert state.locks_open == [PZ["find_key"], PZ["clock_code"]]
    assert state.active_puzzle_id == PZ["find_lantern"]  # a find Puzzle, with no further input


def test_the_click_that_opens_the_active_find_puzzle_moves_it_to_the_next_available_unsolved_one(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, click("key"), code("clock_code", "415"))
    assert state.active_puzzle_id == PZ["find_lantern"]
    state = machine.apply(state, click("lantern"))
    assert state.active_puzzle_id == PZ["door_code"]


def test_a_lock_input_targets_its_puzzle_and_the_target_survives_other_locks_opening(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, code("clock_code", "000"))
    assert state.active_puzzle_id == PZ["clock_code"]
    state = machine.apply(state, click("key"))
    assert state.active_puzzle_id == PZ["clock_code"]


def test_a_hint_request_naming_an_available_unsolved_puzzle_moves_the_active_puzzle_there(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, hint("clock_code"))
    assert state.active_puzzle_id == PZ["clock_code"]
    assert state.locks_open == [] and sum(state.wrong_attempts.values()) == 0


def test_an_effective_room_hiding_the_targeted_puzzle_moves_it_to_the_earliest_available_unsolved_one(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, code("clock_code", "000"))
    assert state.active_puzzle_id == PZ["clock_code"]
    # The accepted Merge of 4.1, built directly as a Room: the clock now requires the lantern.
    merged = with_puzzle(code_and_find_room, "clock_code", requires=[PZ["find_lantern"]])
    state = SessionStateMachine(merged).apply(state, idle(5000))
    assert state.active_puzzle_id == PZ["find_key"]


def test_an_exploration_click_on_any_hotspot_leaves_the_active_puzzle_unchanged(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, hint("clock_code"))
    for name in ("rug", "clock", "lantern", "door"):
        state = machine.apply(state, click(name))
        assert state.active_puzzle_id == PZ["clock_code"] and state.locks_open == []


def test_a_hint_request_naming_an_open_or_unavailable_puzzle_leaves_the_active_puzzle_unchanged(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, click("key"), hint("find_key"), hint("door_code"), hint("find_key"))
    assert state.active_puzzle_id == PZ["clock_code"]


def test_the_active_puzzle_is_null_only_once_no_puzzle_is_available(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, click("key"), code("clock_code", "415"), click("lantern"))
    assert state.active_puzzle_id == PZ["door_code"] and not machine.is_complete(state)
    state = machine.apply(state, code("door_code", "7342"))
    assert state.active_puzzle_id is None and machine.is_complete(state)
    assert machine.apply(state, hint()).active_puzzle_id is None


# --- Hint requests in the session's records ------------------------------------


def test_a_hint_request_with_no_puzzle_id_is_resolved_to_the_active_puzzle_and_counts_for_it(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    events = [code("clock_code", "000", 1000), hint(None, 2000)]
    assert run(machine, *events).active_puzzle_id == PZ["clock_code"]
    result = machine.result(SESSION, events)
    by_id = {puzzle.puzzle_id: puzzle for puzzle in result.puzzles}
    assert by_id[PZ["clock_code"]].hint_requested and by_id[PZ["clock_code"]].early_ask
    assert by_id[PZ["clock_code"]].time_to_first_hint == 2000
    assert not any(p.hint_requested for pid, p in by_id.items() if pid != PZ["clock_code"])


def test_a_hint_naming_an_unavailable_or_open_puzzle_counts_for_the_active_puzzle_which_does_not_move(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    events = [click("key", 1000), hint("door_code", 2000), hint("find_key", 3000)]
    assert run(machine, *events).active_puzzle_id == PZ["clock_code"]
    by_id = {puzzle.puzzle_id: puzzle for puzzle in machine.result(SESSION, events).puzzles}
    assert by_id[PZ["clock_code"]].hint_requested and by_id[PZ["clock_code"]].early_ask
    assert by_id[PZ["clock_code"]].time_to_first_hint == 2000
    assert not by_id[PZ["door_code"]].hint_requested and not by_id[PZ["find_key"]].hint_requested


def test_once_the_exit_has_opened_a_hint_request_is_logged_against_no_puzzle(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    events = [click("key", 1000), code("clock_code", "415", 2000), click("lantern", 3000),
              code("door_code", "7342", 4000), hint(None, 5000)]
    result = machine.result(SESSION, events)
    assert not any(puzzle.hint_requested or puzzle.early_ask for puzzle in result.puzzles)
    assert result.elapsed_ms == 4000


def test_a_hint_request_never_opens_a_lock_counts_a_wrong_attempt_or_changes_a_rung(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    before = run(machine, click("key"), rung("clock_code", 2, 500))
    after = machine.apply(before, hint())
    assert after.locks_open == before.locks_open and after.wrong_attempts == before.wrong_attempts
    assert after.current_rung == before.current_rung and after.rungs_used == before.rungs_used


# --- The order buffer is armed only while its Puzzle is the Active puzzle -------


def test_order_start_arms_the_buffer_and_makes_its_puzzle_the_active_puzzle(four_lock_room):
    machine = SessionStateMachine(four_lock_room)
    state = run(machine, code("clock_code", "415"), order_start("shelf_order"))
    assert state.active_puzzle_id == PZ["shelf_order"]
    assert state.order_buffer == OrderBuffer(puzzle_id=PZ["shelf_order"], clicks=[])
    assert machine.apply(state, order_stop("shelf_order")).order_buffer == OrderBuffer()


def test_order_start_on_an_unavailable_puzzle_arms_nothing_and_sets_no_target(four_lock_room):
    state = run(SessionStateMachine(four_lock_room), order_start("shelf_order"))
    assert state.order_buffer == OrderBuffer() and state.active_puzzle_id == PZ["find_key"]


def test_a_wrong_code_on_another_puzzle_disarms_the_buffer_with_no_wrong_attempt(four_lock_room):
    # A (the shelf) is made available from the start so B (the clock) stays a closed code Puzzle.
    room = with_puzzle(four_lock_room, "shelf_order", requires=[])
    machine = SessionStateMachine(room)
    armed = run(machine, order_start("shelf_order"))
    assert armed.active_puzzle_id == PZ["shelf_order"] and armed.order_buffer.puzzle_id == PZ["shelf_order"]
    state = machine.apply(armed, code("clock_code", "000"))
    assert state.active_puzzle_id == PZ["clock_code"] and state.wrong_attempts[PZ["clock_code"]] == 1
    assert state.order_buffer == OrderBuffer() and state.wrong_attempts[PZ["shelf_order"]] == 0
    for name in ("candle", "lantern", "hourglass"):
        state = machine.apply(state, click(name))
    assert state.order_buffer == OrderBuffer() and state.locks_open == []
    assert state.wrong_attempts[PZ["shelf_order"]] == 0 and state.active_puzzle_id == PZ["clock_code"]
    assert machine.apply(state, order_start("shelf_order")).order_buffer.puzzle_id == PZ["shelf_order"]


def test_a_hint_naming_another_available_puzzle_disarms_the_buffer_and_a_hint_naming_the_armed_one_does_not(four_lock_room):
    room = with_puzzle(four_lock_room, "shelf_order", requires=[])
    machine = SessionStateMachine(room)
    armed = run(machine, order_start("shelf_order"))
    assert machine.apply(armed, hint("shelf_order")).order_buffer.puzzle_id == PZ["shelf_order"]
    assert machine.apply(armed, hint(None)).order_buffer.puzzle_id == PZ["shelf_order"]
    assert machine.apply(armed, hint("find_key")).order_buffer == OrderBuffer()


def test_a_merge_hiding_the_armed_puzzle_disarms_the_buffer(four_lock_room):
    room = with_puzzle(four_lock_room, "shelf_order", requires=[])
    armed = run(SessionStateMachine(room), order_start("shelf_order"))
    state = SessionStateMachine(four_lock_room).apply(armed, idle(5000))
    assert state.active_puzzle_id == PZ["find_key"] and state.order_buffer == OrderBuffer()


def test_a_use_on_input_opens_nothing_and_counts_nothing_in_this_story(four_lock_room):
    machine = SessionStateMachine(four_lock_room)
    state = run(machine, click("key"), use_on("key", "chest"))
    assert state.locks_open == [PZ["find_key"]] and sum(state.wrong_attempts.values()) == 0


# --- The opening line ----------------------------------------------------------


def test_phrasing_is_true_until_the_opening_line_event_is_applied(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    fresh = machine.initial(SESSION)
    assert fresh.phrasing is True and fresh.opening_line is None
    state = machine.apply(fresh, opening(1200))
    assert state.phrasing is False
    assert state.opening_line is not None and state.opening_line.model_dump() == {
        "kind": "welcome", "text": "Welcome. The room is listening."}


# --- Replay, purity and the clock ------------------------------------------------


def full_log() -> list[Event]:
    """Every Puzzle of the code-and-find room solved, with wrong codes, idle ticks, hints and rungs."""
    return [
        opening(100),
        click("rug", 1000),
        code("clock_code", "514", 2000),
        idle(7000),
        idle(12000),
        hint(None, 13000),
        code("door_code", "7342", 14000),  # unmet requires: nothing
        click("key", 15000),
        rung("clock_code", 1, 16000, 2),
        code("clock_code", "451", 17000),
        code("clock_code", " 415 ", 18000),
        idle(23000),
        click("lantern", 24000),
        code("door_code", "7324", 25000),
        rung("door_code", 1, 26000, 13),
        hint(None, 27000),
        code("door_code", "7342", 28000),
        idle(33000),
    ]


def test_the_replayed_state_equals_the_state_built_live(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    live = machine.initial(SESSION)
    for event in full_log():
        live = machine.apply(live, event)
    assert machine.replay(SESSION, full_log()) == live
    assert machine.is_complete(live) and live.active_puzzle_id is None
    assert live.locks_open == [PZ["find_key"], PZ["clock_code"], PZ["find_lantern"], PZ["door_code"]]
    assert live.inventory == [IX["key"], IX["lantern"]]
    assert live.wrong_attempts == {PZ["find_key"]: 0, PZ["clock_code"]: 2, PZ["find_lantern"]: 0, PZ["door_code"]: 1}
    assert live.current_rung == {PZ["find_key"]: 0, PZ["clock_code"]: 1, PZ["find_lantern"]: 0, PZ["door_code"]: 1}
    assert live.rungs_used == 2 and [r.t_ms for r in live.rung_changes] == [16000, 26000]


def test_apply_returns_a_new_state_each_time_and_leaves_its_input_unchanged(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = machine.initial(SESSION)
    for event in full_log():
        before = state.model_dump()
        after = machine.apply(state, event)
        assert after is not state and state.model_dump() == before
        assert after.locks_open is not state.locks_open and after.wrong_attempts is not state.wrong_attempts
        state = after


def test_an_idle_tick_changes_no_lock_inventory_or_wrong_attempt_count(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = run(machine, click("key"), code("clock_code", "000"))
    ticked = machine.apply(state, idle(90000))
    assert ticked.locks_open == state.locks_open and ticked.inventory == state.inventory
    assert ticked.wrong_attempts == state.wrong_attempts and ticked.active_puzzle_id == state.active_puzzle_id


def test_the_session_is_complete_once_the_exit_lock_opens_and_not_before(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    state = machine.initial(SESSION)
    for event in (click("key"), code("clock_code", "415"), click("lantern")):
        state = machine.apply(state, event)
        assert not machine.is_complete(state)
    assert machine.is_complete(machine.apply(state, code("door_code", "7342")))


def test_no_domain_function_reads_the_wall_clock():
    source = inspect.getsource(session_module)
    assert "datetime" not in source and "import time" not in source and "import src.domain.clock" not in source
    assert "t_ms" in source


# --- The Room result ---------------------------------------------------------------


def test_room_result_is_computed_from_the_log_alone(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    result = machine.result(SESSION, full_log())
    assert result.room_id == code_and_find_room.id and result.demo is False
    assert result.elapsed_ms == 28000  # the t_ms of the event that opened the exit
    assert result.rungs_used == 2 and result.wrong_attempts == 3
    by_id = {puzzle.puzzle_id: puzzle for puzzle in result.puzzles}
    assert [puzzle.puzzle_id for puzzle in result.puzzles] == [p.id for p in code_and_find_room.puzzles]
    assert {pid: p.lock_type for pid, p in by_id.items()} == {p.id: p.lock_type for p in code_and_find_room.puzzles}

    find_key = by_id[PZ["find_key"]]
    assert find_key.model_dump() == {
        "puzzle_id": PZ["find_key"], "lock_type": "find", "attempts": 1, "wrong_attempts": 0, "rungs_used": 0,
        "time_to_first_hint": None, "solved": True, "time_spent_ms": 15000, "nudge_fired": False,
        "hint_requested": False, "early_ask": False}

    clock = by_id[PZ["clock_code"]]
    assert (clock.attempts, clock.wrong_attempts, clock.rungs_used, clock.solved) == (3, 2, 1, True)
    assert clock.time_spent_ms == 18000 and clock.time_to_first_hint == 13000
    assert clock.nudge_fired and clock.hint_requested and clock.early_ask

    lantern = by_id[PZ["find_lantern"]]
    assert lantern.solved and lantern.time_spent_ms == 24000 - 15000 and lantern.time_to_first_hint is None
    assert not (lantern.nudge_fired or lantern.hint_requested or lantern.early_ask)

    door = by_id[PZ["door_code"]]
    assert (door.attempts, door.wrong_attempts, door.rungs_used, door.solved) == (2, 1, 1, True)
    assert door.time_spent_ms == 28000 - 24000 and door.time_to_first_hint == 27000 - 24000
    assert door.nudge_fired and door.hint_requested and not door.early_ask  # asked with rung 1 open


def test_room_result_of_an_unfinished_log_counts_to_its_last_event(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    result = machine.result(SESSION, [click("key", 1000), code("clock_code", "000", 2000), idle(7000)], demo=True)
    assert result.demo is True and result.elapsed_ms == 7000 and result.wrong_attempts == 1
    by_id = {puzzle.puzzle_id: puzzle for puzzle in result.puzzles}
    assert by_id[PZ["clock_code"]].time_spent_ms == 7000 and not by_id[PZ["clock_code"]].solved
    assert by_id[PZ["find_lantern"]].time_spent_ms == 6000 and by_id[PZ["door_code"]].time_spent_ms == 0
    assert machine.result(SESSION, []).elapsed_ms == 0


def test_room_result_leaves_the_log_and_the_room_unchanged(code_and_find_room):
    machine = SessionStateMachine(code_and_find_room)
    events = full_log()
    dumped = [event.model_dump() for event in events]
    before = code_and_find_room.model_copy(deep=True)
    machine.result(SESSION, events)
    assert [event.model_dump() for event in events] == dumped and code_and_find_room == before
