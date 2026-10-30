"""The validation gate (AD-12): Schema v1 rules 1 to 9 and the Dry run check.

Every function is pure; the module does no I/O and imports only the standard
library, pydantic and the domain. A reason is structured and token-free
(AD-3): the rule, the Puzzle, the field and the rule's fixed message from
`RULES`, the one table the Build view, the regeneration prompt, the "Sent
back" lines and the rejected Card read (UX-DR77), with the `validate_edit`
bounds row beside it under its own name, `edit_bounds`, never a rule number.
Rules 1 to 8 are the base build checks; rule 9 checks the Decoys of a
session's Effective room and passes on the stored build Room, whose
`decoys[]` is empty.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import NamedTuple

from .schema import (
    DryRunAnswers,
    DryRunVerdict,
    EditBounds,
    Model,
    Puzzle,
    Room,
    ValidatorReason,
    ValidatorResult,
)


class Rule(NamedTuple):
    number: int
    name: str
    """The check-phrased name a pass row shows."""
    message: str
    """The neutral fixed message a fail carries; never a token."""


RULES: dict[int, Rule] = {
    rule.number: rule
    for rule in (
        Rule(1, "No two locks wait on each other", "Two locks would wait on each other forever."),
        Rule(2, "Every lock can be reached", "A lock could never be reached."),
        Rule(3, "Every puzzle names something in this room", "A puzzle names something that isn't in this room."),
        Rule(4, "Every puzzle cites something the Architect saw", "A puzzle cites something the Architect never saw."),
        Rule(5, "No hint, clue or evidence gives an answer away", "A hint gives part of an answer away."),
        Rule(6, "Lore and hints keep to the length rules", "Lore or a hint breaks the length rules."),
        Rule(7, "Every lock has a valid shape", "A lock doesn't have a valid shape."),
        Rule(8, "Every needed item can be picked up first", "A puzzle needs an item that can't be picked up yet."),
        Rule(9, "False evidence follows the decoy rules", "A false clue breaks the decoy rules."),
    )
}
"""Check names and fixed messages by rule number: the only source of either."""
DECOY_RULE = 9
"""The rule that checks `Room.decoys[]`, which is empty on every build."""
BUILD_RULES = range(1, DECOY_RULE)
"""The rules that gate a build, its verdict rows and the Riddler's list: a draft never holds a Decoy."""
EDIT_BOUNDS: EditBounds = "edit_bounds"
"""What a `validate_edit` bounds reason carries in place of a rule number: its own named category, with no check name and no pass row."""
BOUNDS_MESSAGE = "The change is outside the Trickster's limits."
"""The fixed message of every `validate_edit` bounds reason."""

LORE_MAX_WORDS = 60
CODE_LENGTH = range(3, 7)
ORDER_LENGTH = range(3, 6)
LABEL_WORD_FLOOR = 3
"""A label word matches only when it is longer than this; code strings and digits match at any length."""

_WORD = re.compile(r"\w+")


# --- Token matching (Conventions: Validator tokens) ------------------------


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.casefold()))


def _has_whole(text: str, token: str) -> bool:
    """Whether `token` appears in `text` as a whole token, case-folded."""
    return re.search(rf"(?<!\w){re.escape(token.casefold())}(?!\w)", text.casefold()) is not None


def _names_label(text: str, label: str, shown: frozenset[str] = frozenset()) -> bool:
    """Whether any label word longer than the floor, and not in `shown`, appears in `text` as a whole word."""
    words = {word for word in _tokens(label) if len(word) > LABEL_WORD_FLOOR} - shown
    return bool(words & _tokens(text))


def _solution_labels(room: Room, puzzle: Puzzle) -> list[str]:
    """The labels a non-code solution names, in solution order; unknown ids are rule 3's."""
    solution = puzzle.solution
    if solution.lock_type == "order":
        ids = solution.interactables
    elif solution.lock_type == "use_on":
        ids = [solution.item, solution.target]
    elif solution.lock_type == "find":
        ids = [solution.target]
    else:
        return []
    labels = {ix.id: ix.label for ix in room.interactables}
    return [labels[ix_id] for ix_id in ids if ix_id in labels]


def _leaks(text: str, puzzle: Puzzle, labels: list[str], shown: frozenset[str] = frozenset()) -> int:
    """How many solution tokens `text` gives away: the code or a digit counts once, each label once (its `shown` words skipped)."""
    solution = puzzle.solution
    if solution.lock_type == "code":
        digits = {ch for ch in solution.code if ch.isdigit()}
        return int(_has_whole(text, solution.code) or bool(digits & _tokens(text)))
    return sum(_names_label(text, label, shown) for label in labels)


def gives_away(text: str, room: Room, shown: Iterable[str] = ()) -> bool:
    """Whether `text` holds any Puzzle's solution token or a word of any evidence attribute, by rule 5's matching.

    For lines that speak for no single Puzzle (the story): every code and its
    digits, every label a solution names (targets and items) and every word
    longer than the label floor of every `evidence.visible_attribute`. A word
    of a `shown` text (the room's name and area labels, which the player
    already sees) is skipped when label and attribute words are matched;
    codes and digits are not.
    """
    skip = frozenset(word for phrase in shown for word in _tokens(phrase))
    return any(
        _leaks(text, puzzle, _solution_labels(room, puzzle), skip)
        or _names_label(text, puzzle.evidence.visible_attribute, skip)
        for puzzle in room.puzzles
    )


# --- Rules -----------------------------------------------------------------


def _requires_of(room: Room) -> dict[str, list[str]]:
    return {puzzle.id: list(puzzle.requires) for puzzle in room.puzzles}


def _ancestors(requires: dict[str, list[str]], start: str) -> set[str]:
    """Every puzzle reachable from `start` along `requires` edges, `start` excluded unless on a cycle."""
    seen: set[str] = set()
    stack = list(requires.get(start, []))
    while stack:
        puzzle_id = stack.pop()
        if puzzle_id in seen:
            continue
        seen.add(puzzle_id)
        stack.extend(requires.get(puzzle_id, []))
    return seen


def _rule_1(room: Room) -> list[tuple[str | None, str]]:
    """`requires` forms a DAG: no puzzle waits on itself through any chain."""
    requires = _requires_of(room)
    return [(puzzle.id, "requires") for puzzle in room.puzzles if puzzle.id in _ancestors(requires, puzzle.id)]


def _rule_2(room: Room) -> list[tuple[str | None, str]]:
    """Every puzzle is reachable from the puzzles with no prerequisites; the exit needs every other puzzle."""
    requires = _requires_of(room)
    reachable: set[str] = set()
    while True:
        grown = {pid for pid, needs in requires.items() if pid not in reachable and set(needs) <= reachable}
        if not grown:
            break
        reachable |= grown
    failing = [puzzle.id for puzzle in room.puzzles if puzzle.id not in reachable]
    exits = [puzzle for puzzle in room.puzzles if puzzle.is_exit]
    if len(exits) == 1:
        before_exit = _ancestors(requires, exits[0].id)
        failing += [p.id for p in room.puzzles if not p.is_exit and p.id not in before_exit and p.id not in failing]
    return [(puzzle_id, "requires") for puzzle_id in failing]


def _named_ids(puzzle: Puzzle) -> list[str]:
    solution = puzzle.solution
    if solution.lock_type == "code":
        return []
    if solution.lock_type == "order":
        return list(solution.interactables)
    if solution.lock_type == "use_on":
        return [solution.item, solution.target]
    return [solution.target]


def _rule_3(room: Room) -> list[tuple[str | None, str]]:
    """Every interactable named by a solution, evidence or `use_on` pair exists."""
    ids = {ix.id for ix in room.interactables}
    found: list[tuple[str | None, str]] = []
    for puzzle in room.puzzles:
        if any(ix_id not in ids for ix_id in _named_ids(puzzle)):
            found.append((puzzle.id, "solution"))
        if puzzle.evidence.interactable not in ids:
            found.append((puzzle.id, "evidence"))
    return found


def _rule_4(room: Room) -> list[tuple[str | None, str]]:
    """`evidence.visible_attribute` is one the vision call reported for that interactable, case-folded."""
    attributes = {ix.id: {a.casefold() for a in ix.attributes} for ix in room.interactables}
    return [
        (puzzle.id, "visible_attribute")
        for puzzle in room.puzzles
        if puzzle.evidence.interactable in attributes
        and puzzle.evidence.visible_attribute.casefold() not in attributes[puzzle.evidence.interactable]
    ]


def _rule_5(room: Room) -> list[tuple[str | None, str]]:
    """No rung, `clue` or `evidence.visible_attribute` holds a solution token beyond the near-answer allowance."""
    found: list[tuple[str | None, str]] = []
    for puzzle in room.puzzles:
        labels = _solution_labels(room, puzzle)
        allowance = 1 if puzzle.lock_type in ("order", "use_on") else 0
        strict = {
            "nudge": puzzle.rungs.nudge,
            "direction": puzzle.rungs.direction,
            "clue": puzzle.clue,
            "visible_attribute": puzzle.evidence.visible_attribute,
        }
        found += [(puzzle.id, field) for field, text in strict.items() if _leaks(text, puzzle, labels)]
        near_answer = puzzle.rungs.near_answer
        with_clue = f"{near_answer}\n{puzzle.clue}"
        if _leaks(near_answer, puzzle, labels) > allowance or _leaks(with_clue, puzzle, labels) > allowance:
            found.append((puzzle.id, "near_answer"))
    return found


def _rule_6(room: Room) -> list[tuple[str | None, str]]:
    """`lore` is 60 words or fewer; the three rungs are non-empty and increase in length."""
    found: list[tuple[str | None, str]] = []
    for puzzle in room.puzzles:
        if len(puzzle.lore.split()) > LORE_MAX_WORDS:
            found.append((puzzle.id, "lore"))
        rungs = (puzzle.rungs.nudge, puzzle.rungs.direction, puzzle.rungs.near_answer)
        lengths = [len(rung) for rung in rungs]
        if any(not rung.strip() for rung in rungs) or not lengths[0] < lengths[1] < lengths[2]:
            found.append((puzzle.id, "rungs"))
    return found


def _well_formed(puzzle: Puzzle) -> bool:
    solution = puzzle.solution
    if solution.lock_type == "code":
        return len(solution.code) in CODE_LENGTH
    if solution.lock_type == "order":
        return len(solution.interactables) in ORDER_LENGTH
    if solution.lock_type == "use_on":
        return solution.item != solution.target
    return True


def _rule_7(room: Room) -> list[tuple[str | None, str]]:
    """Exactly one `is_exit` puzzle, checked first; then every payload is well-formed."""
    found: list[tuple[str | None, str]] = []
    if sum(puzzle.is_exit for puzzle in room.puzzles) != 1:
        found.append((None, "is_exit"))
    found += [(puzzle.id, "solution") for puzzle in room.puzzles if not _well_formed(puzzle)]
    return found


def _rule_8(room: Room) -> list[tuple[str | None, str]]:
    """Every `use_on.item` is the target of a `find` puzzle listed in that puzzle's `requires`."""
    by_id = {puzzle.id: puzzle for puzzle in room.puzzles}
    found: list[tuple[str | None, str]] = []
    for puzzle in room.puzzles:
        solution = puzzle.solution
        if solution.lock_type != "use_on":
            continue
        collected = {
            needed.solution.target
            for pid in puzzle.requires
            if (needed := by_id.get(pid)) is not None and needed.solution.lock_type == "find"
        }
        if solution.item not in collected:
            found.append((puzzle.id, "requires"))
    return found


def _rule_9(room: Room) -> list[tuple[str | None, str]]:
    """Each Decoy names an interactable and one of its attributes, repeats no real evidence and gives no answer away.

    Its puzzle exists, is not the exit and has no other Decoy; the attribute
    is matched against that puzzle's solution tokens as rule 5 matches evidence.
    """
    by_id = {puzzle.id: puzzle for puzzle in room.puzzles}
    attributes = {ix.id: {a.casefold() for a in ix.attributes} for ix in room.interactables}
    evidence = {(p.evidence.interactable, p.evidence.visible_attribute.casefold()) for p in room.puzzles}
    found: list[tuple[str | None, str]] = []
    decorated: set[str] = set()
    for decoy in room.decoys:
        puzzle = by_id.get(decoy.puzzle)
        attribute = decoy.visible_attribute.casefold()
        if decoy.interactable not in attributes:
            found.append((decoy.puzzle, "interactable"))
        elif attribute not in attributes[decoy.interactable]:
            found.append((decoy.puzzle, "visible_attribute"))
        if (decoy.interactable, attribute) in evidence:
            found.append((decoy.puzzle, "evidence"))
        if puzzle is None or puzzle.is_exit or decoy.puzzle in decorated:
            found.append((decoy.puzzle, "puzzle"))
        decorated.add(decoy.puzzle)
        if puzzle is not None and _leaks(decoy.visible_attribute, puzzle, _solution_labels(room, puzzle)):
            found.append((decoy.puzzle, "visible_attribute"))
    return found


_CHECKS = (_rule_1, _rule_2, _rule_3, _rule_4, _rule_5, _rule_6, _rule_7, _rule_8, _rule_9)


def validate(room: Room) -> ValidatorResult:
    """Rules 1 to 9 over a Room: one reason per failing (rule, puzzle, field), in rule order."""
    reasons = [
        ValidatorReason(rule=number, puzzle_id=puzzle_id, field=field, message=RULES[number].message)
        for number, check in enumerate(_CHECKS, start=1)
        for puzzle_id, field in dict.fromkeys(check(room))
    ]
    return ValidatorResult(ok=not reasons, reasons=reasons)


# --- Dry run (AD-12) -------------------------------------------------------


class DryRunResult(Model):
    ok: bool
    verdicts: list[DryRunVerdict]
    """One per Puzzle in Room order; never `skipped` here."""


def check_dry_run(room: Room, answers: DryRunAnswers) -> DryRunResult:
    """Pass or fail per Puzzle: the only function where Dry run answers meet solutions.

    A matching answer passes; a mismatched one, or none for the Puzzle, fails.
    The first answer for a Puzzle counts; answers naming no Puzzle are ignored.
    """
    given = {}
    for answer in answers.answers:
        given.setdefault(answer.puzzle_id, answer.answer)
    verdicts = [
        DryRunVerdict(puzzle_id=puzzle.id, verdict="pass" if given.get(puzzle.id) == puzzle.solution else "fail")
        for puzzle in room.puzzles
    ]
    return DryRunResult(ok=all(verdict.verdict == "pass" for verdict in verdicts), verdicts=verdicts)
