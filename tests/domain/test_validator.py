"""Story 1.6: rules 1 to 8 with fixed messages, the Dry run check, and token-free reasons (AD-3, AD-12)."""

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from src.domain.schema import (
    CodeSolution,
    DryRunAnswer,
    DryRunAnswers,
    OrderSolution,
    Puzzle,
    Room,
    UseOnSolution,
    ValidatorReason,
)
from src.domain.validator import RULES, DryRunResult, check_dry_run, validate
from tests.fixtures.rooms import IX, PZ

REPO = Path(__file__).resolve().parents[2]
UNKNOWN_IX = "ix_" + "9" * 26
UNKNOWN_PZ = "pz_" + "9" * 26


def puzzle(room: Room, key: str) -> Puzzle:
    return next(p for p in room.puzzles if p.id == PZ[key])


def rules_of(room: Room) -> set[int]:
    return {reason.rule for reason in validate(room).reasons}


def reasons_for(room: Room, rule: int) -> list[ValidatorReason]:
    return [reason for reason in validate(room).reasons if reason.rule == rule]


# --- Negative fixtures, one per rule ----------------------------------------


def break_rule_1(room: Room) -> Room:
    puzzle(room, "find_key").requires = [PZ["key_on_chest"]]  # key_on_chest already requires find_key
    return room


def break_rule_2(room: Room) -> Room:
    puzzle(room, "door_code").requires = [PZ["key_on_chest"]]  # the clock and shelf no longer lead to the exit
    return room


def break_rule_3(room: Room) -> Room:
    puzzle(room, "clock_code").evidence.interactable = UNKNOWN_IX
    return room


def break_rule_4(room: Room) -> Room:
    puzzle(room, "clock_code").evidence.visible_attribute = "glows in the dark"
    return room


def break_rule_5(room: Room) -> Room:
    puzzle(room, "clock_code").rungs.nudge = "Try 415 on the lock."
    return room


def break_rule_6(room: Room) -> Room:
    puzzle(room, "find_key").lore = " ".join(["word"] * 61)
    return room


def break_rule_7(room: Room) -> Room:
    puzzle(room, "clock_code").solution = CodeSolution(lock_type="code", code="41")
    return room


def break_rule_8(room: Room) -> Room:
    puzzle(room, "key_on_chest").requires = []  # the key is no longer collected first
    return room


BREAKERS = {1: break_rule_1, 2: break_rule_2, 3: break_rule_3, 4: break_rule_4,
            5: break_rule_5, 6: break_rule_6, 7: break_rule_7, 8: break_rule_8}


@pytest.mark.parametrize("rule", sorted(BREAKERS))
def test_each_negative_fixture_fails_its_rule_with_the_fixed_message(four_lock_room, rule):
    result = validate(BREAKERS[rule](four_lock_room))
    found = [reason for reason in result.reasons if reason.rule == rule]
    assert not result.ok and found
    for reason in found:
        assert reason.message == RULES[rule].message
        assert reason.field and (reason.puzzle_id is None or reason.puzzle_id.startswith("pz_"))


def test_the_table_holds_rules_1_to_9_with_their_check_names_and_fixed_messages():
    assert sorted(RULES) == list(range(1, 10))
    assert RULES[1].name == "No two locks wait on each other"
    assert RULES[1].message == "Two locks would wait on each other forever."
    assert RULES[5].name == "No hint, clue or evidence gives an answer away"
    assert RULES[5].message == "A hint gives part of an answer away."
    assert all(rule.number == number and rule.name and rule.message.endswith(".") for number, rule in RULES.items())


def test_reasons_are_sorted_by_rule_and_carry_the_puzzle_and_field(four_lock_room):
    room = break_rule_6(break_rule_1(four_lock_room))
    reasons = validate(room).reasons
    assert [r.rule for r in reasons] == sorted(r.rule for r in reasons)
    assert {(r.rule, r.puzzle_id, r.field) for r in reasons} >= {
        (1, PZ["find_key"], "requires"), (1, PZ["key_on_chest"], "requires"), (6, PZ["find_key"], "lore"),
    }


# --- Rules 1 to 4 and 8 in detail -------------------------------------------


def test_rule_2_names_the_puzzles_that_cannot_reach_the_exit(four_lock_room):
    reasons = reasons_for(break_rule_2(four_lock_room), 2)
    assert {r.puzzle_id for r in reasons} == {PZ["clock_code"], PZ["shelf_order"]}


def test_rule_2_names_a_puzzle_waiting_on_an_unknown_puzzle(four_lock_room):
    puzzle(four_lock_room, "find_key").requires = [UNKNOWN_PZ]
    assert {r.puzzle_id for r in reasons_for(four_lock_room, 2)} >= {PZ["find_key"]}


def test_rule_3_covers_solution_ids_and_evidence(four_lock_room):
    puzzle(four_lock_room, "key_on_chest").solution = UseOnSolution(lock_type="use_on", item=UNKNOWN_IX, target=IX["chest"])
    reasons = reasons_for(four_lock_room, 3)
    assert {(r.puzzle_id, r.field) for r in reasons} == {(PZ["key_on_chest"], "solution")}
    assert not reasons_for(four_lock_room, 4)  # the unknown item is rule 3's, not rule 4's


def test_rule_4_matches_attributes_case_folded(four_lock_room):
    puzzle(four_lock_room, "clock_code").evidence.visible_attribute = "STOPPED AT A QUARTER PAST FOUR"
    assert 4 not in rules_of(four_lock_room)


def test_rule_8_accepts_an_item_collected_by_a_required_find(four_lock_room):
    assert 8 not in rules_of(four_lock_room)
    key_on_chest = puzzle(four_lock_room, "key_on_chest")
    key_on_chest.solution = UseOnSolution(lock_type="use_on", item=IX["lantern"], target=IX["chest"])
    assert {(r.puzzle_id, r.field) for r in reasons_for(four_lock_room, 8)} == {(PZ["key_on_chest"], "requires")}


# --- Rule 7: the exit count first, then payload shapes ----------------------


def test_zero_exits_and_two_exits_each_fail_rule_7_before_the_payload_checks(four_lock_room):
    puzzle(four_lock_room, "door_code").is_exit = False
    puzzle(four_lock_room, "clock_code").solution = CodeSolution(lock_type="code", code="4151234")
    reasons = reasons_for(four_lock_room, 7)
    assert reasons[0].puzzle_id is None and reasons[0].field == "is_exit"
    assert (PZ["clock_code"], "solution") in {(r.puzzle_id, r.field) for r in reasons[1:]}

    puzzle(four_lock_room, "door_code").is_exit = True
    puzzle(four_lock_room, "find_key").is_exit = True
    reasons = reasons_for(four_lock_room, 7)
    assert reasons[0].puzzle_id is None and reasons[0].field == "is_exit"


def test_validate_reads_only_is_exit_to_find_the_exit(four_lock_room):
    # Moving the flag to a puzzle nothing waits on fails rule 2, so the graph is not what names the exit.
    puzzle(four_lock_room, "door_code").is_exit = False
    puzzle(four_lock_room, "find_key").is_exit = True
    assert 7 not in rules_of(four_lock_room)
    assert {r.puzzle_id for r in reasons_for(four_lock_room, 2)} == {
        PZ["clock_code"], PZ["shelf_order"], PZ["key_on_chest"], PZ["door_code"],
    }


@pytest.mark.parametrize("code, ok", [("41", False), ("415", True), ("415263", True), ("4152637", False)])
def test_rule_7_code_is_3_to_6_characters(four_lock_room, code, ok):
    puzzle(four_lock_room, "door_code").solution = CodeSolution(lock_type="code", code=code)
    assert (7 not in rules_of(four_lock_room)) is ok


@pytest.mark.parametrize("length, ok", [(2, False), (3, True), (5, True), (6, False)])
def test_rule_7_order_is_3_to_5_hotspots(four_lock_room, length, ok):
    ids = [IX[name] for name in ("candle", "lantern", "hourglass", "rug", "clock", "door")][:length]
    puzzle(four_lock_room, "shelf_order").solution = OrderSolution(lock_type="order", interactables=ids)
    assert (7 not in rules_of(four_lock_room)) is ok


def test_rule_7_use_on_needs_two_distinct_ids(four_lock_room):
    puzzle(four_lock_room, "key_on_chest").solution = UseOnSolution(lock_type="use_on", item=IX["key"], target=IX["key"])
    assert (PZ["key_on_chest"], "solution") in {(r.puzzle_id, r.field) for r in reasons_for(four_lock_room, 7)}


# --- Rule 6 -----------------------------------------------------------------


def test_rule_6_lore_of_60_words_passes_and_61_fails(four_lock_room):
    puzzle(four_lock_room, "find_key").lore = " ".join(["word"] * 60)
    assert 6 not in rules_of(four_lock_room)
    assert {(r.puzzle_id, r.field) for r in reasons_for(break_rule_6(four_lock_room), 6)} == {(PZ["find_key"], "lore")}


def test_rule_6_rungs_are_non_empty_and_increase_in_length(four_lock_room):
    rungs = puzzle(four_lock_room, "find_key").rungs
    rungs.direction = rungs.near_answer + " and more"
    assert {(r.puzzle_id, r.field) for r in reasons_for(four_lock_room, 6)} == {(PZ["find_key"], "rungs")}
    rungs.direction = "Something small and metal hangs where a coat would."
    rungs.nudge = "   "
    assert {(r.puzzle_id, r.field) for r in reasons_for(four_lock_room, 6)} == {(PZ["find_key"], "rungs")}


# --- Rule 5: token matching over rungs, clue and evidence -------------------


def rule_5_fields(room: Room, key: str) -> set[str]:
    return {r.field for r in reasons_for(room, 5) if r.puzzle_id == PZ[key]}


@pytest.mark.parametrize("field", ["nudge", "direction", "near_answer", "clue", "visible_attribute"])
def test_the_code_string_as_a_whole_token_fails_in_every_checked_field(four_lock_room, field):
    code = puzzle(four_lock_room, "clock_code")
    text = "Try 415 here."
    if field == "clue":
        code.clue = text
    elif field == "visible_attribute":
        code.evidence.visible_attribute = text
        code.evidence.interactable = IX["clock"]
    else:
        setattr(code.rungs, field, text)
    assert field in rule_5_fields(four_lock_room, "clock_code")


def test_a_single_digit_of_the_code_fails_as_a_whole_token_at_any_length(four_lock_room):
    code = puzzle(four_lock_room, "clock_code")
    code.rungs.nudge = "Press 4 first."
    assert rule_5_fields(four_lock_room, "clock_code") == {"nudge"}
    code.rungs.nudge = "Press 4151 first."  # the code's digits glued to another: not a whole token
    assert rule_5_fields(four_lock_room, "clock_code") == set()
    exit_code = puzzle(four_lock_room, "door_code")
    exit_code.rungs.direction = "The door wants a 7, then more."
    assert rule_5_fields(four_lock_room, "door_code") == {"direction"}


def test_the_code_string_is_matched_case_folded_and_at_any_length(four_lock_room):
    code = puzzle(four_lock_room, "clock_code")
    code.solution = CodeSolution(lock_type="code", code="ab")
    code.rungs.direction = "Think AB, then the rest of the alphabet."
    assert rule_5_fields(four_lock_room, "clock_code") == {"direction"}
    code.rungs.direction = "Think ABC, then the rest of the alphabet."
    assert rule_5_fields(four_lock_room, "clock_code") == set()


def test_a_label_word_longer_than_three_characters_fails_as_a_whole_word(four_lock_room):
    find = puzzle(four_lock_room, "find_key")  # target label "brass key"
    find.rungs.direction = "The BRASS thing by the hooks is what you want."
    assert rule_5_fields(four_lock_room, "find_key") == {"direction"}
    find.rungs.direction = "The brassy thing by the hooks is what you want."
    assert rule_5_fields(four_lock_room, "find_key") == set()


def test_a_label_word_of_three_characters_or_fewer_is_not_matched(four_lock_room):
    find = puzzle(four_lock_room, "find_key")  # "key" has three characters
    find.rungs.nudge = "A key hangs near the door, by the way."
    find.clue = "The key is on a hook."
    assert rule_5_fields(four_lock_room, "find_key") == set()


def test_evidence_naming_a_find_target_fails_on_visible_attribute(four_lock_room):
    find = puzzle(four_lock_room, "find_key")
    find.evidence.visible_attribute = "a brass thing on a hook"
    assert rule_5_fields(four_lock_room, "find_key") == {"visible_attribute"}


def test_near_answer_may_name_one_label_of_an_order_sequence_but_not_two(four_lock_room):
    order = puzzle(four_lock_room, "shelf_order")  # candle, lantern, hourglass
    assert rule_5_fields(four_lock_room, "shelf_order") == set()  # names the candle only
    order.rungs.near_answer = "Begin with the candle, then the lantern, then what runs out of grains."
    assert rule_5_fields(four_lock_room, "shelf_order") == {"near_answer"}
    order.rungs.nudge = "Start with the lantern."  # the nudge has no allowance
    assert rule_5_fields(four_lock_room, "shelf_order") == {"nudge", "near_answer"}


def test_near_answer_may_name_one_label_of_a_use_on_pair_but_not_both(four_lock_room):
    use_on = puzzle(four_lock_room, "key_on_chest")  # brass key on wooden chest
    assert rule_5_fields(four_lock_room, "key_on_chest") == set()  # names the chest only
    use_on.rungs.near_answer = "Use the brass thing from the hook on the wooden chest by the far wall."
    assert rule_5_fields(four_lock_room, "key_on_chest") == {"near_answer"}


def test_the_near_answer_allowance_is_also_checked_against_the_clue(four_lock_room):
    order = puzzle(four_lock_room, "shelf_order")
    order.clue = "Three keepers of time stand on the shelf; the lantern wakes last."
    fields = rule_5_fields(four_lock_room, "shelf_order")
    assert fields == {"clue", "near_answer"}  # the clue names a label; with the candle in the near-answer that is two


def test_the_rule_5_matching_is_case_folded(four_lock_room):
    order = puzzle(four_lock_room, "shelf_order")
    order.rungs.direction = "Look at the HOURGLASS."
    assert rule_5_fields(four_lock_room, "shelf_order") == {"direction"}


# --- Reasons never leak ------------------------------------------------------


def solution_tokens(room: Room) -> set[str]:
    labels = {ix.id: ix.label for ix in room.interactables}
    tokens: set[str] = set()
    for p in room.puzzles:
        solution = p.solution
        if solution.lock_type == "code":
            tokens.add(solution.code)
        elif solution.lock_type == "order":
            tokens.update(labels[i] for i in solution.interactables)
        elif solution.lock_type == "use_on":
            tokens.update((labels[solution.item], labels[solution.target]))
        else:
            tokens.add(labels[solution.target])
    return tokens


@pytest.mark.parametrize("rule", sorted(BREAKERS))
def test_serialized_reasons_hold_only_rule_puzzle_field_and_fixed_message(four_lock_room, rule):
    room = BREAKERS[rule](four_lock_room)
    result = validate(room)
    text = json.dumps(result.model_dump())
    for token in solution_tokens(room) | {ix.id for ix in room.interactables} | {"415", "7342"}:
        assert token not in text
    for word in ("hook", "clock", "shelf", "chest", "door", "glows"):
        assert word not in text.casefold()
    for reason in result.reasons:
        assert set(reason.model_dump()) == {"rule", "puzzle_id", "field", "message"}
        assert reason.message == RULES[reason.rule].message


# --- Dry run ------------------------------------------------------------------


def answers_for(room: Room, **overrides: Any) -> DryRunAnswers:
    answers = []
    for p in room.puzzles:
        answer = overrides.get(p.id, p.solution)
        if answer is not None:
            answers.append(DryRunAnswer(puzzle_id=p.id, answer=answer))
    return DryRunAnswers(answers=answers)


def test_matching_answers_pass_every_puzzle(four_lock_room):
    result = check_dry_run(four_lock_room, answers_for(four_lock_room))
    assert isinstance(result, DryRunResult) and result.ok
    assert [v.puzzle_id for v in result.verdicts] == [p.id for p in four_lock_room.puzzles]
    assert {v.verdict for v in result.verdicts} == {"pass"}


def test_a_mismatched_answer_fails_its_puzzle_only(four_lock_room):
    wrong = CodeSolution(lock_type="code", code="416")
    result = check_dry_run(four_lock_room, answers_for(four_lock_room, **{PZ["clock_code"]: wrong}))
    verdicts = {v.puzzle_id: v.verdict for v in result.verdicts}
    assert not result.ok and verdicts[PZ["clock_code"]] == "fail"
    assert all(verdict == "pass" for pid, verdict in verdicts.items() if pid != PZ["clock_code"])


def test_a_puzzle_with_no_answer_fails(four_lock_room):
    result = check_dry_run(four_lock_room, answers_for(four_lock_room, **{PZ["shelf_order"]: None}))
    verdicts = {v.puzzle_id: v.verdict for v in result.verdicts}
    assert not result.ok and verdicts[PZ["shelf_order"]] == "fail" and verdicts[PZ["find_key"]] == "pass"


def test_an_order_answer_must_match_in_sequence_and_a_use_on_pair_in_role(four_lock_room):
    order = puzzle(four_lock_room, "shelf_order").solution
    assert order.lock_type == "order"
    reversed_order = OrderSolution(lock_type="order", interactables=list(reversed(order.interactables)))
    swapped_pair = UseOnSolution(lock_type="use_on", item=IX["chest"], target=IX["key"])
    answers = answers_for(four_lock_room, **{PZ["shelf_order"]: reversed_order, PZ["key_on_chest"]: swapped_pair})
    verdicts = {v.puzzle_id: v.verdict for v in check_dry_run(four_lock_room, answers).verdicts}
    assert verdicts[PZ["shelf_order"]] == "fail" and verdicts[PZ["key_on_chest"]] == "fail"


def test_check_dry_run_and_validate_leave_the_room_unchanged(four_lock_room, fixture_rooms):
    validate(four_lock_room)
    check_dry_run(four_lock_room, answers_for(four_lock_room))
    assert four_lock_room == fixture_rooms[0]


# --- Purity of the module ---------------------------------------------------


def test_validator_imports_only_stdlib_pydantic_and_the_domain():
    source = (REPO / "src" / "domain" / "validator.py").read_text()
    tops: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 1 and node.module == "schema" or node.level == 0, ast.dump(node)
            if node.level == 0:
                tops.add((node.module or "").split(".")[0])
    assert tops <= set(sys.stdlib_module_names) | {"pydantic"}, tops
    assert tops.isdisjoint({"os", "io", "pathlib", "socket", "subprocess", "shutil", "tempfile", "asyncio"})
    assert "open(" not in source
