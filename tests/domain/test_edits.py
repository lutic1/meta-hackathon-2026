"""Story 4.1: Trickster edits land only when the Validator passes, with rule 9 for Decoys (AD-12, AD-3)."""

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from src.domain.edits import (
    accepted_edit,
    apply_edit,
    check_edit,
    effective_room,
    validate_edit,
)
from src.domain.redact import to_play_view
from src.domain.schema import (
    ClickEvent,
    CodeInput,
    Event,
    HintRequestEvent,
    LockInputEvent,
    LoosenPayload,
    PlayView,
    Room,
    SessionState,
    TricksterCardEvent,
    TricksterEdit,
    TricksterWindow,
    ValidatorResult,
)
from src.domain.session import SessionStateMachine
from src.domain.validator import (
    BOUNDS_MESSAGE,
    BUILD_RULES,
    DECOY_RULE,
    EDIT_BOUNDS,
    RULES,
    validate,
)
from tests.fixtures.rooms import (
    IX,
    PZ,
    SENTINEL_CODE,
    SENTINEL_IX,
    with_sentinel_solutions,
)

REPO = Path(__file__).resolve().parents[2]
SESSION = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"
UNKNOWN_IX = "ix_" + "8" * 26
UNKNOWN_PZ = "pz_" + "8" * 26
NOT_CHECKED = ValidatorResult(ok=False, reasons=[])
"""A proposal's `validator_result` before the Validator has run."""


# --- Builders ----------------------------------------------------------------


def te(n: int) -> str:
    return f"te_{n:026d}"


def proposal(n: int, payload: dict[str, Any], puzzle: str, *, window: int = 0) -> TricksterEdit:
    return TricksterEdit.model_validate({
        "id": te(n), "type": payload["type"], "puzzle": puzzle, "payload": payload,
        "validator_result": NOT_CHECKED.model_dump(), "accepted": False, "window": window,
    })


def decoy(n: int, puzzle: str, interactable: str, attribute: str, *, window: int = 0) -> TricksterEdit:
    ix = IX.get(interactable, interactable)
    payload = {"type": "decoy", "interactable": ix, "visible_attribute": attribute}
    return proposal(n, payload, PZ.get(puzzle, puzzle), window=window)


def merge(n: int, puzzle_a: str, puzzle_b: str, *, window: int = 0) -> TricksterEdit:
    """`puzzle_b` now waits on `puzzle_a`."""
    a, b = PZ.get(puzzle_a, puzzle_a), PZ.get(puzzle_b, puzzle_b)
    return proposal(n, {"type": "merge", "puzzle_a": a, "puzzle_b": b}, b, window=window)


def loosen(n: int, puzzle: str, rung: str, *, window: int = 0) -> TricksterEdit:
    pid = PZ.get(puzzle, puzzle)
    return proposal(n, {"type": "loosen", "puzzle": pid, "rung": rung}, pid, window=window)


def shortcut(n: int, puzzle: str, requires: str, *, window: int = 0) -> TricksterEdit:
    pid = PZ.get(puzzle, puzzle)
    return proposal(n, {"type": "shortcut", "puzzle": pid, "requires": PZ.get(requires, requires)}, pid, window=window)


def window_state(room: Room, state: str = "open", index: int | None = 0) -> SessionState:
    return SessionStateMachine(room).initial(SESSION).model_copy(
        update={"trickster_window": TricksterWindow(state=state, index=index)}
    )


def card(edit: TricksterEdit, result: ValidatorResult, revision: int, t: int) -> TricksterCardEvent:
    """The card a live window appends: the full edit with its verdict, kept server-side."""
    judged = edit.model_copy(update={"validator_result": result, "accepted": result.ok})
    return TricksterCardEvent(
        type="trickster_card", edit_id=edit.id, edit=judged, puzzle_id=edit.puzzle, accepted=result.ok,
        reason=None if result.ok else result.reasons[0].rule, room_revision=revision, t_ms=t,
    )


def code(name: str, text: str, t: int) -> LockInputEvent:
    return LockInputEvent(type="lock_input", input=CodeInput(type="code", puzzle_id=PZ[name], code=text), t_ms=t)


def click_key(t: int) -> ClickEvent:
    return ClickEvent(type="click", interactable_id=IX["key"], t_ms=t)


def hint(name: str, t: int) -> HintRequestEvent:
    return HintRequestEvent(type="hint_request", puzzle_id=PZ[name], t_ms=t)


def with_decoy_on(room: Room, puzzle: str, interactable: str, attribute: str) -> Room:
    return apply_edit(room, decoy(90, puzzle, interactable, attribute))


def bounds_rejections(room: Room) -> dict[str, tuple[Room, TricksterEdit]]:
    """Each proposal the payload bounds refuse, with the Effective room it is checked against."""
    out_of_menu = loosen(6, "clock_code", "nudge")
    out_of_menu = out_of_menu.model_copy(
        update={"payload": LoosenPayload.model_construct(type="loosen", puzzle=PZ["clock_code"], rung="reveal")}
    )
    return {
        "decoy on the exit": (room, decoy(1, "door_code", "rug", "faded red")),
        "loosen on an unknown puzzle": (room, loosen(2, UNKNOWN_PZ, "nudge")),
        "loosen outside the rung menu": (room, out_of_menu),
        "merge naming an unknown puzzle": (room, merge(3, UNKNOWN_PZ, "find_key")),
        "shortcut with no such edge": (room, shortcut(4, "clock_code", "find_key")),
        "second decoy this session": (
            with_decoy_on(room, "shelf_order", "rug", "faded red"), decoy(5, "shelf_order", "rug", "woven"),
        ),
    }


def rule_9_rejections(room: Room) -> dict[str, Room]:
    """Each Effective room whose one Decoy breaks rule 9, built through `apply_edit` (option A)."""
    return {
        "unknown interactable": apply_edit(room, decoy(11, "shelf_order", UNKNOWN_IX, "faded red")),
        "attribute never read": apply_edit(room, decoy(12, "shelf_order", "rug", "glows softly")),
        "repeats real evidence": apply_edit(room, decoy(13, "shelf_order", "clock", "stopped at a quarter past four")),
        "targets the exit": apply_edit(room, decoy(14, "door_code", "rug", "faded red")),
        "second decoy on a puzzle": apply_edit(
            with_decoy_on(room, "shelf_order", "rug", "faded red"), decoy(15, "shelf_order", "rug", "woven"),
        ),
        "gives a solution token": apply_edit(room, decoy(16, "shelf_order", "hourglass", "sand run out")),
    }


# --- The Validator table ---------------------------------------------------------


def test_rule_9_and_the_bounds_row_sit_in_the_one_validator_table():
    assert (RULES[DECOY_RULE].name, RULES[DECOY_RULE].message) == (
        "False evidence follows the decoy rules", "A false clue breaks the decoy rules.",
    )
    assert BOUNDS_MESSAGE == "The change is outside the Trickster's limits."
    assert EDIT_BOUNDS not in RULES  # no check name and no pass row
    assert list(BUILD_RULES) == list(range(1, 9))


def test_bounds_refusals_carry_the_named_edit_bounds_category_and_never_a_rule_number(four_lock_room):
    # Owner decision 29: rules 1 to 8 are the base build checks, rule 9 the Decoy check, and nothing is rule 10.
    assert list(RULES) == list(range(1, DECOY_RULE + 1))
    cases = [(room, window_state(room), edit) for room, edit in bounds_rejections(four_lock_room).values()]
    cases.append((four_lock_room, window_state(four_lock_room, "closed", None), decoy(20, "shelf_order", "rug", "faded red")))
    for room, state, edit in cases:
        reasons = validate_edit(room, state, edit).reasons
        assert reasons and {reason.rule for reason in reasons} == {"edit_bounds"}
        assert all(reason.message == BOUNDS_MESSAGE for reason in reasons)


def test_rule_9_passes_on_the_stored_build_rooms(four_lock_room, code_and_find_room):
    for room in (four_lock_room, code_and_find_room):
        assert room.decoys == [] and room.provenance.applied_edits == []
        assert validate(room).ok


# --- validate_edit: the window and payload bounds ------------------------------------


BOUNDS_CASES = (
    "decoy on the exit", "loosen on an unknown puzzle", "loosen outside the rung menu",
    "merge naming an unknown puzzle", "shortcut with no such edge", "second decoy this session",
)
RULE_9_CASES = (
    "unknown interactable", "attribute never read", "repeats real evidence",
    "targets the exit", "second decoy on a puzzle", "gives a solution token",
)


def test_the_case_lists_cover_every_builder_entry(four_lock_room):
    assert tuple(bounds_rejections(four_lock_room)) == BOUNDS_CASES
    assert tuple(rule_9_rejections(four_lock_room)) == RULE_9_CASES


@pytest.mark.parametrize("case", BOUNDS_CASES)
def test_payload_bounds_refuse_with_structured_reasons_and_the_fixed_message(four_lock_room, case):
    room, edit = bounds_rejections(four_lock_room)[case]
    result = validate_edit(room, window_state(room), edit)
    assert not result.ok and result.reasons
    for reason in result.reasons:
        assert (reason.rule, reason.message) == (EDIT_BOUNDS, BOUNDS_MESSAGE)
        assert reason.field and reason.field != "window" and reason.puzzle_id is not None
    assert not check_edit(room, window_state(room), edit).ok


def test_a_closed_window_refuses_on_the_window_bound_before_any_payload_check(four_lock_room):
    valid = decoy(20, "shelf_order", "rug", "faded red")
    cases = [*bounds_rejections(four_lock_room).values(), (four_lock_room, valid)]
    for room, edit in cases:
        result = validate_edit(room, window_state(room, "closed", None), edit)
        assert [(r.rule, r.puzzle_id, r.field, r.message) for r in result.reasons] == [
            (EDIT_BOUNDS, None, "window", BOUNDS_MESSAGE)
        ]
    other_window = validate_edit(four_lock_room, window_state(four_lock_room, "open", 1), valid)
    assert [r.field for r in other_window.reasons] == ["window"]


def test_an_edit_inside_the_limits_passes_validate_edit(four_lock_room):
    state = window_state(four_lock_room)
    for edit in (decoy(21, "shelf_order", "rug", "faded red"), merge(22, "clock_code", "find_key"),
                 loosen(23, "clock_code", "direction"), shortcut(24, "door_code", "shelf_order")):
        assert validate_edit(four_lock_room, state, edit) == ValidatorResult(ok=True, reasons=[])
    assert validate_edit(four_lock_room, window_state(four_lock_room, "pending", 0), merge(25, "clock_code", "find_key")).ok


def with_open(room: Room, *names: str) -> SessionState:
    """An open window in a session where the named Puzzles are already open."""
    return window_state(room).model_copy(update={"locks_open": [PZ[name] for name in names]})


def test_an_edit_naming_a_puzzle_already_open_is_refused_on_the_bounds(four_lock_room):
    # Live playtest Oct 29: an accepted edit on an open Puzzle changes nothing the player can see.
    state = with_open(four_lock_room, "find_key", "clock_code")
    cases = {
        "decoy on an open puzzle": (decoy(26, "clock_code", "rug", "faded red"), [(PZ["clock_code"], "puzzle")]),
        "loosen on an open puzzle": (loosen(27, "clock_code", "direction"), [(PZ["clock_code"], "puzzle")]),
        "merge onto an open puzzle": (merge(28, "shelf_order", "clock_code"), [(PZ["clock_code"], "puzzle"), (PZ["clock_code"], "puzzle_b")]),
        "merge waiting on an open puzzle": (merge(29, "clock_code", "shelf_order"), [(PZ["clock_code"], "puzzle_a")]),
        "shortcut off an open puzzle": (shortcut(19, "key_on_chest", "find_key"), [(PZ["find_key"], "requires")]),
    }
    for case, (edit, named) in cases.items():
        result = validate_edit(four_lock_room, state, edit)
        assert [(r.rule, r.puzzle_id, r.field, r.message) for r in result.reasons] == [
            (EDIT_BOUNDS, puzzle_id, field, BOUNDS_MESSAGE) for puzzle_id, field in named
        ], case
        assert not check_edit(four_lock_room, state, edit).ok
    assert validate_edit(four_lock_room, state, merge(18, "key_on_chest", "shelf_order")).ok  # both still locked


# --- validate(apply_edit(...)): rules 1 to 9, no Dry run ----------------------------


def test_an_edit_is_accepted_only_when_rules_1_to_9_pass(four_lock_room):
    state = window_state(four_lock_room)
    for edit in (decoy(30, "shelf_order", "rug", "faded red"), merge(31, "clock_code", "find_key"),
                 loosen(32, "clock_code", "direction")):
        assert check_edit(four_lock_room, state, edit) == ValidatorResult(ok=True, reasons=[])


def test_a_merge_closing_a_cycle_is_rejected_on_rule_1(four_lock_room):
    edit = merge(33, "key_on_chest", "find_key")  # key_on_chest already waits on find_key
    assert validate_edit(four_lock_room, window_state(four_lock_room), edit).ok
    result = check_edit(four_lock_room, window_state(four_lock_room), edit)
    assert not result.ok
    assert (1, "Two locks would wait on each other forever.") in {(r.rule, r.message) for r in result.reasons}


def test_a_shortcut_removing_the_find_an_item_depends_on_is_rejected_on_rule_8(four_lock_room):
    edit = shortcut(34, "key_on_chest", "find_key")
    assert validate_edit(four_lock_room, window_state(four_lock_room), edit).ok
    result = check_edit(four_lock_room, window_state(four_lock_room), edit)
    assert (8, PZ["key_on_chest"], "A puzzle needs an item that can't be picked up yet.") in {
        (r.rule, r.puzzle_id, r.message) for r in result.reasons
    }


def test_no_dry_run_is_reachable_from_the_edit_check():
    tree = ast.parse((REPO / "src/domain/edits.py").read_text())
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    assert "check_dry_run" not in names and "DryRunAnswers" not in names
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert modules <= {"__future__", "collections.abc", "functools", "rungs", "schema", "validator"}


# --- Rule 9: Decoys (option A) ---------------------------------------------------


@pytest.mark.parametrize("case", RULE_9_CASES)
def test_each_broken_decoy_is_rejected_on_rule_9_alone(four_lock_room, case):
    result = validate(rule_9_rejections(four_lock_room)[case])
    assert not result.ok
    assert {(r.rule, r.puzzle_id is not None, r.message) for r in result.reasons} == {
        (DECOY_RULE, True, "A false clue breaks the decoy rules.")
    }


def test_rule_9_matches_attributes_case_folded(four_lock_room):
    assert validate(apply_edit(four_lock_room, decoy(17, "shelf_order", "rug", "Faded Red"))).ok
    repeated = apply_edit(four_lock_room, decoy(18, "shelf_order", "candle", "HALF BURNT"))
    assert [r.rule for r in validate(repeated).reasons] == [DECOY_RULE]


def _rejections(room: Room) -> list[ValidatorResult]:
    state = window_state(room)
    results = [validate_edit(r, state, edit) for r, edit in bounds_rejections(room).values()]
    results += [validate_edit(r, window_state(r, "closed", None), edit) for r, edit in bounds_rejections(room).values()]
    results += [validate(edited) for edited in rule_9_rejections(room).values()]
    results += [check_edit(room, state, merge(40, "key_on_chest", "find_key"))]
    results += [check_edit(room, state, shortcut(41, "key_on_chest", "find_key"))]
    return results


def test_no_rejection_reason_quotes_a_token_a_code_a_digit_or_a_solution_label(four_lock_room):
    for room in (four_lock_room, with_sentinel_solutions(four_lock_room)):
        labels = {ix.label for ix in room.interactables}
        codes = {p.solution.code for p in room.puzzles if p.solution.lock_type == "code"} | {SENTINEL_CODE}
        offending = {"sand", "sand run out", "glows softly", "woven", "faded red", "stopped at a quarter past four"}
        ids = {UNKNOWN_IX, *SENTINEL_IX, *IX.values()}
        results = _rejections(room)
        assert all(not result.ok for result in results)
        for reason in (reason for result in results for reason in result.reasons):
            assert reason.message in (BOUNDS_MESSAGE, *(rule.message for rule in RULES.values()))
            text = f"{reason.message}\n{reason.field}".casefold()
            assert not any(ch.isdigit() for ch in text)  # no code string and none of its digits
            whole = json.dumps(reason.model_dump()).casefold()
            assert not any(token.casefold() in whole for token in codes | ids)
            assert not any(token.casefold() in text for token in labels | offending)
            assert not any(word in text for label in labels for word in label.split() if len(word) > 3)


# --- apply_edit: a new Room, the stored Room untouched ---------------------------------


def test_apply_edit_returns_a_new_room_per_type_and_leaves_the_input_untouched(four_lock_room):
    before = four_lock_room.model_copy(deep=True)
    puzzles = {p.id: p for p in four_lock_room.puzzles}

    merged = apply_edit(four_lock_room, merge(50, "clock_code", "find_key"))
    assert next(p for p in merged.puzzles if p.id == PZ["find_key"]).requires == [PZ["clock_code"]]
    shortened = apply_edit(four_lock_room, shortcut(51, "door_code", "shelf_order"))
    assert next(p for p in shortened.puzzles if p.id == PZ["door_code"]).requires == [PZ["key_on_chest"]]
    decorated = apply_edit(four_lock_room, decoy(52, "shelf_order", "rug", "faded red"))
    assert [d.model_dump() for d in decorated.decoys] == [
        {"id": te(52), "puzzle": PZ["shelf_order"], "interactable": IX["rug"], "visible_attribute": "faded red"}
    ]
    loosened = apply_edit(four_lock_room, loosen(53, "clock_code", "direction"))
    assert loosened.puzzles == four_lock_room.puzzles and loosened.decoys == []

    for n, edited in zip((50, 51, 52, 53), (merged, shortened, decorated, loosened), strict=True):
        assert edited is not four_lock_room and edited.provenance.applied_edits == [te(n)]
        unchanged = [p for p in edited.puzzles if p.id not in (PZ["find_key"], PZ["door_code"])]
        assert all(p == puzzles[p.id] for p in unchanged)
    assert four_lock_room == before
    assert four_lock_room.provenance.applied_edits == [] and four_lock_room.decoys == []


def test_edits_reach_no_artifact_store():
    tree = ast.parse((REPO / "src/domain/edits.py").read_text())
    imported = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imported |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(name.startswith(("src.", "infra", "pipeline", "api", "providers")) for name in imported)


# --- The Effective room folded from the session log ----------------------------------


def _play(room: Room) -> tuple[list[Event], list[Room]]:
    """A session that runs each proposal through the live check, keeping the Effective room as it goes."""
    machine = SessionStateMachine(room)
    log: list[Event] = []
    live_rooms = [room]
    proposals = [
        merge(60, "clock_code", "key_on_chest"),          # accepted: key_on_chest now waits on clock_code too
        decoy(61, "shelf_order", "rug", "faded red"),      # accepted
        decoy(62, "shelf_order", "rug", "woven"),          # rejected: a second Decoy on the Puzzle (bounds)
        shortcut(63, "shelf_order", "clock_code"),         # accepted: clock_code still leads to the exit
        shortcut(64, "key_on_chest", "find_key"),          # rejected on rule 8
        loosen(65, "key_on_chest", "direction"),           # accepted
    ]
    t = 1_000
    log.append(ClickEvent(type="click", interactable_id=IX["rug"], t_ms=t))  # exploration: every Puzzle stays locked
    revision = 0
    for window, edit in enumerate(proposals):
        edit = edit.model_copy(update={"window": window})
        t += 1_000
        state = machine.replay(SESSION, log).model_copy(
            update={"trickster_window": TricksterWindow(state="open", index=window)}
        )
        result = check_edit(live_rooms[-1], state, edit)
        revision += result.ok
        log.append(card(edit, result, revision, t))
        live_rooms.append(apply_edit(live_rooms[-1], edit) if result.ok else live_rooms[-1])
    return log, live_rooms


def test_the_effective_room_is_the_accepted_edits_folded_in_log_order(four_lock_room):
    before = four_lock_room.model_copy(deep=True)
    log, live_rooms = _play(four_lock_room)
    cards = [event for event in log if isinstance(event, TricksterCardEvent)]
    assert [c.accepted for c in cards] == [True, True, False, True, False, True]
    assert [c.reason for c in cards] == [None, None, EDIT_BOUNDS, None, 2, None]  # the first failing rule
    assert {r.rule for r in cards[4].edit.validator_result.reasons} == {2, 8}  # find_key no longer feeds the chest

    effective = effective_room(four_lock_room, log)
    assert effective == live_rooms[-1]  # replay equals live
    assert effective.provenance.applied_edits == [te(60), te(61), te(63), te(65)]
    assert [(d.id, d.puzzle) for d in effective.decoys] == [(te(61), PZ["shelf_order"])]
    requires = {p.id: p.requires for p in effective.puzzles}
    assert requires[PZ["key_on_chest"]] == [PZ["find_key"], PZ["clock_code"]] and requires[PZ["shelf_order"]] == []
    assert validate(effective).ok

    for n, event in enumerate(log):  # a rejected card leaves the Effective room unchanged
        if isinstance(event, TricksterCardEvent) and not event.accepted:
            assert effective_room(four_lock_room, log[: n + 1]) == effective_room(four_lock_room, log[:n])
    assert four_lock_room == before and four_lock_room.decoys == [] and four_lock_room.provenance.applied_edits == []
    assert effective_room(four_lock_room, [log[0]]) == four_lock_room  # no card: the stored Room itself


def test_the_fold_reads_each_edit_from_its_card_and_room_revision_counts_the_accepted(four_lock_room):
    log, _ = _play(four_lock_room)
    machine = SessionStateMachine(four_lock_room)
    assert [accepted_edit(event).id for event in log if accepted_edit(event)] == [te(60), te(61), te(63), te(65)]
    for event in log[1:]:
        assert isinstance(event, TricksterCardEvent) and event.edit is not None  # the full edit rides in the card: id, type, puzzle, payload, verdict, outcome, window
        assert set(event.edit.model_dump()) == {"id", "type", "puzzle", "payload", "validator_result", "accepted", "window"}
        assert event.edit.accepted == event.accepted
    live = machine.initial(SESSION)
    for n, event in enumerate(log):
        live = machine.apply(live, event, history=machine.history(SESSION, log[:n]))
        assert live.room_revision == len(effective_room(four_lock_room, log[: n + 1]).provenance.applied_edits)
    replayed = machine.replay(SESSION, log)
    assert live == replayed and replayed.room_revision == 4


def test_session_state_carries_no_edit_payload_or_event(four_lock_room):
    log, _ = _play(four_lock_room)
    state = SessionStateMachine(four_lock_room).replay(SESSION, log)
    text = json.dumps(state.model_dump(mode="json"))
    assert "faded red" not in text and "woven" not in text and IX["rug"] not in text
    assert '"payload"' not in text and '"edit"' not in text and '"validator_result"' not in text
    assert "edit" not in SessionState.model_fields and "events" not in SessionState.model_fields


def test_an_accepted_merge_hiding_the_active_puzzle_moves_it_in_the_cards_step(four_lock_room):
    machine = SessionStateMachine(four_lock_room)
    edit = merge(70, "clock_code", "find_key")
    accepted = card(edit, check_edit(four_lock_room, window_state(four_lock_room), edit), 1, 1_000)
    log: list[Event] = [accepted, click_key(2_000), code("clock_code", "415", 3_000), click_key(4_000)]
    assert machine.initial(SESSION).active_puzzle_id == PZ["find_key"]
    states = [machine.replay(SESSION, log[: n + 1]) for n in range(len(log))]
    assert states[0].active_puzzle_id == PZ["clock_code"]  # find_key now waits on clock_code
    assert PZ["find_key"] not in states[1].locks_open  # the key cannot be taken yet
    assert PZ["find_key"] in states[3].locks_open
    live = machine.initial(SESSION)
    for n, event in enumerate(log):
        live = machine.apply(live, event, history=machine.history(SESSION, log[:n]))
    assert live == states[-1]



# --- The Inventory across edits (owner decision, Oct 29) ----------------------------


def test_after_every_accepted_edit_each_open_find_target_a_use_on_names_is_carried_and_nothing_held_leaves(four_lock_room):
    machine = SessionStateMachine(four_lock_room)
    found: list[Event] = [click_key(1_000)]
    log, room = list(found), four_lock_room
    edits = [merge(71, "clock_code", "key_on_chest"), shortcut(72, "shelf_order", "clock_code"),
             decoy(73, "shelf_order", "rug", "faded red"), loosen(74, "clock_code", "nudge")]
    for revision, edit in enumerate(edits, start=1):
        accepted = card(edit, check_edit(room, window_state(room), edit), revision, 1_000 + revision)
        assert accepted.accepted, edit.type
        log, room = [*log, accepted], apply_edit(room, edit)
        assert machine.replay(SESSION, log).inventory == [IX["key"]], edit.type
    # The key found while no use_on named it (no edit type changes a solution today): the edit's step carries it.
    edit = loosen(75, "clock_code", "nudge")
    accepted = card(edit, check_edit(four_lock_room, window_state(four_lock_room), edit), 1, 2_000)
    uncarried = machine.replay(SESSION, found).model_copy(update={"inventory": []})
    after = machine.apply(uncarried, accepted, history=machine.history(SESSION, found))
    assert after.locks_open == [PZ["find_key"]] and after.inventory == [IX["key"]]

# --- Loosen: the Rung opens at once --------------------------------------------------


def test_an_accepted_loosen_raises_the_rung_at_once_and_a_hint_returns_it(four_lock_room):
    machine = SessionStateMachine(four_lock_room)
    edit = loosen(80, "clock_code", "direction")
    accepted = card(edit, check_edit(four_lock_room, window_state(four_lock_room), edit), 1, 2_000)
    log: list[Event] = [code("clock_code", "000", 1_000), accepted]
    state = machine.replay(SESSION, log)
    assert state.current_rung[PZ["clock_code"]] == 2  # no Idle and only one Wrong attempt
    change = state.rung_changes[-1]
    assert (change.puzzle_id, change.rung, change.triggered_by, change.t_ms) == (PZ["clock_code"], 2, [1], 2_000)
    clock = next(p for p in four_lock_room.puzzles if p.id == PZ["clock_code"])
    assert change.text == clock.rungs.direction

    replied = machine.replay(SESSION, [*log, change, hint("clock_code", 2_500)])
    assert replied.active_puzzle_id == PZ["clock_code"] and replied.current_rung[PZ["clock_code"]] == 2
    assert replied.rung_changes == state.rung_changes  # the stored rung_change replaces the selection
    assert effective_room(four_lock_room, log).puzzles == four_lock_room.puzzles


def test_a_loosen_opens_outside_the_rung_spacing(four_lock_room):
    machine = SessionStateMachine(four_lock_room)
    wrong = [code("clock_code", "000", t) for t in (1_000, 2_000, 3_000)]  # three Wrong attempts open the nudge
    nudged = machine.replay(SESSION, wrong)
    assert nudged.current_rung[PZ["clock_code"]] == 1
    edit = loosen(81, "clock_code", "near_answer")
    accepted = card(edit, check_edit(four_lock_room, window_state(four_lock_room), edit), 1, 4_000)  # 1 s later
    state = machine.replay(SESSION, [*wrong, accepted])
    assert state.current_rung[PZ["clock_code"]] == 3 and state.rung_changes[-1].triggered_by == [3]
    lower = loosen(82, "clock_code", "nudge")  # a Rung already open: nothing to raise
    unchanged = machine.replay(SESSION, [*wrong, card(lower, ValidatorResult(ok=True, reasons=[]), 1, 4_000)])
    assert unchanged.current_rung[PZ["clock_code"]] == 1 and len(unchanged.rung_changes) == 1


def test_a_rejected_loosen_opens_nothing(four_lock_room):
    machine = SessionStateMachine(four_lock_room)
    edit = loosen(83, "clock_code", "direction")
    refused = ValidatorResult.model_validate({"ok": False, "reasons": [
        {"rule": EDIT_BOUNDS, "puzzle_id": None, "field": "window", "message": BOUNDS_MESSAGE}]})
    state = machine.replay(SESSION, [card(edit, refused, 0, 1_000)])
    assert state.current_rung[PZ["clock_code"]] == 0 and state.rung_changes == [] and state.room_revision == 0


# --- The Play view of an Effective room with a Decoy ----------------------------------


def test_a_decoy_and_the_real_evidence_cannot_be_told_apart_in_the_play_view(four_lock_room):
    log, _ = _play(four_lock_room)
    effective = effective_room(four_lock_room, log)
    view = to_play_view(effective)
    shelf = next(p for p in view.puzzles if p.id == PZ["shelf_order"])
    real = next(p for p in four_lock_room.puzzles if p.id == PZ["shelf_order"]).evidence
    assert len(shelf.evidence_cards) == 2 and real in shelf.evidence_cards
    assert {(c.interactable, c.visible_attribute) for c in shelf.evidence_cards} == {
        (real.interactable, real.visible_attribute), (IX["rug"], "faded red"),
    }
    assert {type(c) for c in shelf.evidence_cards} == {type(real)}
    assert all(set(c.model_dump()) == {"interactable", "visible_attribute"} for c in shelf.evidence_cards)
    assert all(len(p.evidence_cards) == 1 for p in view.puzzles if p.id != PZ["shelf_order"])

    assert to_play_view(effective) == view  # stable on every call
    assert to_play_view(effective_room(four_lock_room, log)) == view  # and on every replay
    data = view.model_dump(mode="json")
    keys: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            keys.update(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    assert keys.isdisjoint({"decoys", "solution", "provenance", "applied_edits"})
    assert "te_" not in json.dumps(data)
    assert set(PlayView.model_fields).isdisjoint({"decoys", "solution", "provenance"})
