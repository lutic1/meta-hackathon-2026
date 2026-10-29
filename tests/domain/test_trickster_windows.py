"""Story 4.2: Trickster windows, the Game-state summary and the six-call budget in `apply` (FR-18, FR-24, AD-4, AD-10)."""

import json

import pytest

from src.domain.redact import to_card_view
from src.domain.rungs import TRICKSTER_WINDOW_MS, unscaled_thresholds
from src.domain.schema import (
    Derived,
    Event,
    Profile,
    Room,
    SessionState,
    TricksterCardEvent,
    TricksterWindow,
    ValidatorResult,
)
from src.domain.session import (
    TRICKSTER_CALLS_MAX,
    GameStateSummary,
    SessionStateMachine,
    game_state_summary,
)
from src.domain.validator import BOUNDS_MESSAGE, EDIT_BOUNDS
from tests.domain.test_edits import card, decoy, loosen
from tests.domain.test_redact import json_keys
from tests.domain.test_session import (
    SESSION,
    applied,
    click,
    code,
    hint,
    idle,
    order_start,
    use_on,
)
from tests.fixtures.rooms import (
    PZ,
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    with_sentinel_solutions,
)

WINDOW = TRICKSTER_WINDOW_MS
CLOSED = TricksterWindow(state="closed")
OK = ValidatorResult(ok=True, reasons=[])
REFUSED = ValidatorResult.model_validate(
    {"ok": False, "reasons": [{"rule": EDIT_BOUNDS, "puzzle_id": None, "field": "puzzle", "message": BOUNDS_MESSAGE}]}
)


def opened(index: int) -> TricksterWindow:
    return TricksterWindow(state="open", index=index)


def skipped(t: int, revision: int = 0) -> TricksterCardEvent:
    """The card a window records on a provider error or the Spend cap."""
    return TricksterCardEvent(
        type="trickster_card", edit_id=None, edit=None, puzzle_id=None, accepted=False,
        reason="provider_unavailable", room_revision=revision, t_ms=t,
    )


def run(machine: SessionStateMachine, *events: Event) -> SessionState:
    return machine.replay(SESSION, events)


# --- When a window opens ------------------------------------------------------------


@pytest.mark.parametrize("opens", [lambda t: click("key", t), lambda t: code("clock_code", "415", t)], ids=["find", "code"])
def test_a_non_exit_lock_opening_at_the_threshold_opens_window_0(four_lock_room: Room, opens):
    machine = SessionStateMachine(four_lock_room)
    assert machine.initial(SESSION).trickster_window == CLOSED
    assert run(machine, opens(WINDOW - 1)).trickster_window == CLOSED  # A-26: the first window waits 180000 ms
    assert run(machine, opens(WINDOW)).trickster_window == opened(0)


def test_opening_the_exit_puzzles_lock_opens_no_window(code_and_find_room: Room):
    machine = SessionStateMachine(code_and_find_room)
    early = [click("key", 1_000), code("clock_code", "415", 2_000), click("lantern", 3_000)]
    before_exit = run(machine, *early)
    assert before_exit.trickster_window == CLOSED  # every non-exit lock opened before the threshold
    state = run(machine, *early, code("door_code", "7342", WINDOW + 20_000))
    assert machine.is_complete(state) and state.trickster_window == CLOSED


def test_opening_the_exit_closes_a_window_still_open_and_no_window_opens_after(four_lock_room: Room):
    # Owner decision 30: the Exit opening ends the Trickster's part, so no proposal, card or call follows.
    machine = SessionStateMachine(four_lock_room)
    to_exit = [
        click("key", WINDOW), code("clock_code", "415", WINDOW + 1_000), order_start("shelf_order", WINDOW + 2_000),
        click("candle", WINDOW + 3_000), click("lantern", WINDOW + 4_000), click("hourglass", WINDOW + 5_000),
        use_on("key", "chest", WINDOW + 6_000),
    ]
    assert run(machine, *to_exit).trickster_window == opened(0)
    log = [*to_exit, code("door_code", "7342", WINDOW + 7_000)]
    state = run(machine, *log)
    assert machine.is_complete(state) and state.trickster_window == CLOSED
    assert state.trickster_calls == 0 and state.cards == [] and state.active_puzzle_id is None
    assert applied(machine, log)[-1] == state
    assert run(machine, *log, idle(3 * WINDOW)).trickster_window == CLOSED


@pytest.mark.parametrize("event", [
    click("rug", WINDOW + 1_000),                   # an exploration click
    click("key", WINDOW + 1_000),                   # a click on a find target already open
    idle(WINDOW + 1_000),
    hint("clock_code", WINDOW + 1_000),
    code("clock_code", "999", WINDOW + 1_000),      # a Wrong attempt
], ids=["exploration click", "open find target", "idle_tick", "hint_request", "wrong attempt"])
def test_an_event_that_opens_no_lock_leaves_the_window_closed(four_lock_room: Room, event: Event):
    machine = SessionStateMachine(four_lock_room)
    state = run(machine, click("key", 1_000), event)  # the key is taken before the threshold
    assert state.locks_open == [PZ["find_key"]] and state.trickster_window == CLOSED


def test_the_next_window_waits_the_threshold_after_the_previous_card(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    first = [click("key", WINDOW), skipped(WINDOW + 10_000)]
    closed_at = WINDOW + 10_000
    assert run(machine, *first).trickster_window == CLOSED
    assert run(machine, *first, code("clock_code", "415", closed_at + WINDOW - 1)).trickster_window == CLOSED
    assert run(machine, *first, code("clock_code", "415", closed_at + WINDOW)).trickster_window == opened(1)


def test_a_lock_opening_while_a_window_is_open_keeps_that_window(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    state = run(machine, click("key", WINDOW), code("clock_code", "415", WINDOW + 5_000))
    assert state.trickster_window == opened(0) and state.trickster_calls == 0


def test_at_demo_timescale_6_the_window_is_30_s_and_t_ms_stays_unscaled(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room, trickster_window_ms=WINDOW // 6)  # the session clock's scaled value
    assert run(machine, click("key", 29_999)).trickster_window == CLOSED
    log: list[Event] = [click("key", 30_000), skipped(31_000)]
    assert run(machine, *log).trickster_window == CLOSED
    assert run(machine, *log, code("clock_code", "415", 60_999)).trickster_window == CLOSED
    state = run(machine, *log, code("clock_code", "415", 61_000))
    assert state.trickster_window == opened(1)  # 30 s after the previous window closed (180000 / 6)
    assert [c.t_ms for c in state.cards] == [31_000]  # the card keeps the t_ms stamped at append
    assert SessionStateMachine(four_lock_room).trickster_window_ms == WINDOW  # 1x unless wiring passes the scaled one


# --- The Game-state summary ------------------------------------------------------------


NON_DEFAULT = Derived(sessions=3, persistence=0.5, time_to_first_hint_s=42.0, mean_rung_per_lock_type={"code": 1.5})


def sentinel_log() -> list[Event]:
    """Three Wrong codes open the nudge, then the sentinel code and the sentinel find target open two locks."""
    wrong = [code("clock_code", "000", t) for t in (1_000, 2_000, 3_000)]
    return [*wrong, code("clock_code", SENTINEL_CODE, 4_000), click_ix(SENTINEL_FIND, WINDOW)]


def click_ix(interactable_id: str, t: int) -> Event:
    return click("key", t).model_copy(update={"interactable_id": interactable_id})


def test_the_game_state_summary_holds_exactly_the_open_locks_the_elapsed_time_and_the_rungs_used(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    machine = SessionStateMachine(room, thresholds=unscaled_thresholds(NON_DEFAULT))
    log = sentinel_log()
    state = run(machine, *log)
    assert state.locks_open == [PZ["clock_code"], PZ["find_key"]] and state.rungs_used == 1
    assert SENTINEL_FIND in state.inventory  # the state holds it; the summary never does
    summary = game_state_summary(state, 200_000)
    assert summary == GameStateSummary(locks_open=[PZ["clock_code"], PZ["find_key"]], elapsed_ms=200_000, rungs_used=1)
    assert set(GameStateSummary.model_fields) == {"locks_open", "elapsed_ms", "rungs_used"}

    forbidden_keys = set(Derived.model_fields) | set(Profile.model_fields) | {"solution", "thresholds", "inventory"}
    tokens = {SENTINEL_CODE, SENTINEL_CODE.casefold(), json.dumps(SENTINEL_ORDER), " ".join(SENTINEL_ORDER), *SENTINEL_IX}
    for n in range(len(log) + 1):  # every state of the session, the empty one included
        data = game_state_summary(run(machine, *log[:n]), log[n - 1].t_ms if n else 0).model_dump(mode="json")
        text = json.dumps(data)
        assert json_keys(data) == {"locks_open", "elapsed_ms", "rungs_used"} and not json_keys(data) & forbidden_keys
        assert not any(token in text for token in tokens), text
        assert "42" not in text and "0.5" not in text and "1.5" not in text  # no Derived value either


def test_the_summary_is_a_new_value(four_lock_room: Room):
    state = run(SessionStateMachine(four_lock_room), click("key", 1_000))
    summary = game_state_summary(state, 1_000)
    summary.locks_open.append(PZ["clock_code"])
    assert state.locks_open == [PZ["find_key"]]


# --- How a window closes ---------------------------------------------------------------


def test_an_accepted_card_closes_the_window_counts_one_call_and_raises_room_revision(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    edit = decoy(1, "shelf_order", "rug", "faded red")
    accepted = card(edit, OK, 1, WINDOW + 7_000)
    before = run(machine, click("key", WINDOW))
    state = run(machine, click("key", WINDOW), accepted)
    assert before.trickster_window == opened(0) and before.cards == []
    assert state.trickster_window == CLOSED and state.trickster_calls == before.trickster_calls + 1
    assert state.cards == [to_card_view(accepted)] and state.cards[-1].t_ms == WINDOW + 7_000
    assert state.room_revision == before.room_revision + 1
    keys = json_keys(state.model_dump(mode="json")["cards"])
    assert not keys & {"edit", "payload", "interactable", "visible_attribute", "rung", "validator_result"}
    assert "faded red" not in json.dumps(state.model_dump(mode="json"))  # the edit is never copied into the card


def test_a_rejected_card_closes_the_window_counts_one_call_and_leaves_room_revision(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    rejected = card(loosen(2, "clock_code", "direction"), REFUSED, 0, WINDOW + 7_000)
    state = run(machine, click("key", WINDOW), rejected)
    assert state.trickster_window == CLOSED and state.trickster_calls == 1 and state.room_revision == 0
    assert state.cards == [to_card_view(rejected)] and state.cards[0].message == BOUNDS_MESSAGE
    assert state.current_rung[PZ["clock_code"]] == 0


def test_a_skipped_card_closes_the_window_counts_one_call_and_changes_no_judgment(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    opening = [click("key", WINDOW)]
    state = run(machine, *opening, skipped(WINDOW + 7_000))
    assert state.trickster_window == CLOSED and state.trickster_calls == 1 and state.room_revision == 0
    assert state.cards == [to_card_view(skipped(WINDOW + 7_000))]
    assert (state.cards[0].edit_id, state.cards[0].accepted, state.cards[0].reason) == (None, False, "provider_unavailable")
    for lock_input in (code("clock_code", "000", WINDOW + 8_000), code("clock_code", "415", WINDOW + 8_000),
                       use_on("key", "chest", WINDOW + 8_000)):
        with_card = run(machine, *opening, skipped(WINDOW + 7_000), lock_input)
        without = run(machine, *opening, lock_input)
        judged = ("locks_open", "inventory", "wrong_attempts", "active_puzzle_id", "order_buffer", "room_revision")
        assert {f: getattr(with_card, f) for f in judged} == {f: getattr(without, f) for f in judged}


# --- The six-call budget, window indices and replay -------------------------------------


def six_cards() -> list[Event]:
    return [skipped(1_000 + n) for n in range(TRICKSTER_CALLS_MAX)]


def test_after_six_cards_no_window_opens_and_trickster_calls_stays_at_6(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    full = run(machine, *six_cards())
    assert full.trickster_calls == TRICKSTER_CALLS_MAX == 6 and full.trickster_window == CLOSED
    later = [click("key", 10 * WINDOW), code("clock_code", "415", 12 * WINDOW), idle(13 * WINDOW)]
    for n in range(1, len(later) + 1):
        state = run(machine, *six_cards(), *later[:n])
        assert state.trickster_window == CLOSED and state.trickster_calls == 6  # the seventh is refused before any request
    assert len(run(machine, *six_cards(), *later).cards) == 6


def four_windows() -> list[Event]:
    """Every non-exit lock of the four-lock room opening a threshold apart, each window closed by a card."""
    t = WINDOW
    log: list[Event] = [click("key", t), card(decoy(1, "shelf_order", "rug", "faded red"), OK, 1, t + 1_000)]
    t += 1_000 + WINDOW
    log += [code("clock_code", "415", t), skipped(t + 1_000, 1)]
    t += 1_000 + WINDOW
    log += [order_start("shelf_order", t - 3_000), click("candle", t - 2_000), click("lantern", t - 1_000), click("hourglass", t)]
    log += [card(loosen(2, "key_on_chest", "direction"), REFUSED, 1, t + 1_000)]
    t += 1_000 + WINDOW
    log += [use_on("key", "chest", t)]
    return log


def test_each_window_carries_its_index_counted_from_0_and_replay_equals_live(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    log = four_windows()
    live = applied(machine, log)
    windows = [(state.trickster_window.state, state.trickster_window.index) for state in live]
    assert [w for w in windows if w[0] == "open"] == [("open", 0), ("open", 1), ("open", 2), ("open", 3)]
    cards = [w for w, event in zip(windows, log, strict=True) if isinstance(event, TricksterCardEvent)]
    assert cards == [("closed", None)] * 3
    assert (live[-1].trickster_window, live[-1].trickster_calls, live[-1].room_revision) == (opened(3), 3, 1)
    for n, state in enumerate(live):  # replaying any prefix yields the window, the calls and the revision of live play
        replayed = machine.replay(SESSION, log[: n + 1])
        assert replayed == state
        fields = ("trickster_window", "trickster_calls", "room_revision", "cards")
        assert {f: getattr(replayed, f) for f in fields} == {f: getattr(state, f) for f in fields}


def test_six_cards_built_directly_replay_like_live(four_lock_room: Room):
    machine = SessionStateMachine(four_lock_room)
    log = [*six_cards(), click("key", 10 * WINDOW)]
    assert applied(machine, log)[-1] == machine.replay(SESSION, log)
