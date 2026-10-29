"""Story mode (owner decision Oct 29): the treasure chest's 2 hints per Session and no automatic hints (AD-4, AD-12).

Under the `chest` hint policy an ask opens the Active puzzle's next Rung at
once and spends one of the Session's hints; idle time and wrong attempts open
nothing; the Trickster's `loosen` and `decoy` are refused. The `ladder`
policy keeps the earlier behaviour, so a log played under it replays the same.
"""

from collections.abc import Sequence

import pytest

from src.domain.edits import check_edit, validate_edit
from src.domain.rungs import HINTS_PER_SESSION, Judged, RungStep, select_rung
from src.domain.schema import (
    DecoyPayload,
    LoosenPayload,
    MergePayload,
    Room,
    TricksterEdit,
    TricksterWindow,
    ValidatorResult,
)
from src.domain.session import SessionHeader, SessionStateMachine
from tests.domain.test_rungs import DEMO, play, rungs, summary, ticks
from tests.domain.test_session import SESSION, code, hint, opening
from tests.fixtures.rooms import IX, PZ


def chest(room: Room, cap: int = HINTS_PER_SESSION) -> SessionStateMachine:
    return SessionStateMachine(room, thresholds=DEMO, hint_policy="chest", hint_cap=cap)


def test_the_chest_holds_2_hints_per_session():
    assert HINTS_PER_SESSION == 2


def test_a_fresh_session_has_every_hint_left(code_and_find_room: Room):
    assert chest(code_and_find_room).initial(SESSION).hints_left == 2
    assert chest(code_and_find_room, cap=3).initial(SESSION).hints_left == 3


def test_idle_time_and_wrong_attempts_open_nothing_under_the_chest(code_and_find_room: Room):
    machine = chest(code_and_find_room)
    wrong = [code("clock_code", "0", t) for t in range(1_000, 30_001, 1_000)]
    log = play(machine, opening(0), *wrong, *ticks(35_000, 200_000))
    state = machine.replay(SESSION, log)
    assert rungs(log) == [] and state.rungs_used == 0 and state.hints_left == 2


def test_an_ask_opens_the_next_rung_at_once_inside_the_spacing_and_spends_one_hint(code_and_find_room: Room):
    machine = chest(code_and_find_room)
    log = play(machine, opening(0), hint(None, 1_000))
    assert machine.replay(SESSION, log).hints_left == 1
    log = play(machine, hint(None, 2_000), after=log)  # 1000 ms after the nudge: the 15000 ms spacing no longer applies
    state = machine.replay(SESSION, log)
    assert summary(log) == [("find_key", 1, [1], 1_000), ("find_key", 2, [3], 2_000)]
    assert state.hints_left == 0 and state.current_rung[PZ["find_key"]] == 2


def test_an_ask_with_no_hint_left_opens_nothing(code_and_find_room: Room):
    machine = chest(code_and_find_room)
    log = play(machine, opening(0), hint(None, 1_000), hint(None, 2_000), hint(None, 3_000))
    state = machine.replay(SESSION, log)
    assert len(rungs(log)) == 2 and state.hints_left == 0 and state.current_rung[PZ["find_key"]] == 2


def test_an_ask_once_the_near_answer_is_open_spends_nothing(code_and_find_room: Room):
    machine = chest(code_and_find_room, cap=5)
    log = play(machine, opening(0), *(hint(None, t) for t in (1_000, 2_000, 3_000, 4_000)))
    state = machine.replay(SESSION, log)
    assert len(rungs(log)) == 3 and state.current_rung[PZ["find_key"]] == 3 and state.hints_left == 2


def test_the_wait_for_the_next_ask_is_0_while_a_hint_is_left_and_none_after(code_and_find_room: Room):
    machine = chest(code_and_find_room)
    log = play(machine, opening(0), hint(None, 1_000))
    assert machine.next_hint_ms(machine.replay(SESSION, log), 1_000) == 0
    log = play(machine, hint(None, 2_000), after=log)
    assert machine.next_hint_ms(machine.replay(SESSION, log), 2_000) is None


def test_hints_left_replays_from_the_log_and_never_counts_an_idle_or_wrong_rung(code_and_find_room: Room):
    ladder = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    wrong = [code("clock_code", "0", t) for t in (1_000, 2_000, 3_000)]
    log = play(ladder, opening(0), *wrong, hint(None, 20_000))
    assert summary(log) == [("clock_code", 1, [1, 2, 3], 3_000), ("clock_code", 2, [5], 20_000)]
    assert ladder.replay(SESSION, log).hints_left == 1  # only the asked Rung spent a hint
    assert SessionStateMachine(code_and_find_room, thresholds=DEMO).replay(SESSION, log).hints_left == 1


def test_a_ladder_log_replays_with_its_idle_rungs_and_spacing_as_before(code_and_find_room: Room):
    ladder = SessionStateMachine(code_and_find_room, thresholds=DEMO)
    log = play(ladder, opening(0), *ticks(5_000, 20_000), hint(None, 21_000), hint(None, 22_000))
    assert summary(log) == [("find_key", 1, [3], 15_000)]  # the nudge on idle; the asks wait out the spacing
    state = ladder.replay(SESSION, log)
    assert state.hints_left == 2 and ladder.next_hint_ms(state, 22_000) == 8_000


def test_select_rung_under_the_chest_opens_only_an_asked_rung():
    events: Sequence[Judged] = [
        Judged(t_ms=0, activity=False, wrong_attempt=None, rung=None, active_puzzle_id=PZ["find_key"]),
        Judged(t_ms=500_000, activity=False, wrong_attempt=None, rung=None, active_puzzle_id=PZ["find_key"]),
    ]
    assert select_rung(events, DEMO, policy="ladder") == RungStep(PZ["find_key"], 1, (1,))
    assert select_rung(events, DEMO, policy="chest") is None
    assert select_rung(events, DEMO, policy="chest", asked=True) == RungStep(PZ["find_key"], 1, (1,))


def test_a_header_stored_before_story_mode_replays_under_the_ladder():
    header = SessionHeader.model_validate(
        {"room_id": "room_" + "0" * 25 + "1", "opening": "welcome", "nudge_threshold_base_ms": 90_000, "earlier_session": False}
    )
    assert (header.hint_policy, header.hint_cap) == ("ladder", 2)


# --- The Trickster under the chest (4.2) --------------------------------------------


def edit(payload: LoosenPayload | DecoyPayload | MergePayload, puzzle: str) -> TricksterEdit:
    return TricksterEdit(
        id="te_" + "0" * 25 + "1", type=payload.type, puzzle=PZ[puzzle], payload=payload,
        validator_result=ValidatorResult(ok=False, reasons=[]), accepted=False, window=0,
    )


LOOSEN = edit(LoosenPayload(type="loosen", puzzle=PZ["clock_code"], rung="nudge"), "clock_code")
DECOY = edit(DecoyPayload(type="decoy", interactable=IX["rug"], visible_attribute="woven"), "clock_code")


@pytest.mark.parametrize(("proposal", "message"), [
    (LOOSEN, "Hints come only from the chest."),
    (DECOY, "Evidence is hidden until a lock opens."),
])
def test_loosen_and_decoy_are_refused_under_the_chest_with_their_fixed_reason(four_lock_room: Room, proposal: TricksterEdit, message: str):
    state = chest(four_lock_room).initial(SESSION).model_copy(update={"trickster_window": TricksterWindow(state="open", index=0)})
    refused = validate_edit(four_lock_room, state, proposal, hint_policy="chest")
    assert not refused.ok and [(r.rule, r.message) for r in refused.reasons] == [("edit_bounds", message)]
    assert check_edit(four_lock_room, state, proposal, hint_policy="chest") == refused
    assert validate_edit(four_lock_room, state, proposal, hint_policy="ladder").ok


def test_merge_and_shortcut_stay_open_to_the_trickster_under_the_chest(four_lock_room: Room):
    state = chest(four_lock_room).initial(SESSION).model_copy(update={"trickster_window": TricksterWindow(state="open", index=0)})
    merge = edit(MergePayload(type="merge", puzzle_a=PZ["clock_code"], puzzle_b=PZ["key_on_chest"]), "key_on_chest")
    assert validate_edit(four_lock_room, state, merge, hint_policy="chest").ok
