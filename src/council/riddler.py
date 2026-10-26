"""The Riddler prompt (AD-3, AD-5): the author call and its regeneration variant.

Both builders are pure over a `RoomView` and render its Interactables only
(`id`, `label`, `attributes`, `instances`, `photo`): never a Puzzle, a
solution, a photo or a profile field. The fixed prefix carries the response
shape, the Validator's checks and the generated-line voice rules (UX-DR76),
so a Rung shown word for word still reads in character. The regeneration
variant adds the refused attempt's fixed messages (UX-DR77) and never its
draft. The response schema keys Puzzles by `p1`..`p6` (AD-18), admits only
the Lock types the builder is given and has no map-typed field (AD-2).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache, reduce
from operator import or_
from typing import Annotated, Literal

from pydantic import Field, create_model, model_validator

from src.domain.schema import (
    CodeSolution,
    Evidence,
    FindSolution,
    LockType,
    Model,
    OrderSolution,
    OrdinalKey,
    RoomView,
    Rungs,
    Solution,
    UseOnSolution,
    ValidatorReason,
)
from src.domain.validator import CODE_LENGTH, LORE_MAX_WORDS, ORDER_LENGTH, RULES
from src.providers.base import ChatMessage, ReasoningEffort

LOCK_TYPES: tuple[LockType, ...] = ("code", "order", "use_on", "find")
CUT6_LOCK_TYPES: tuple[LockType, ...] = ("code", "find")
REASONING_EFFORT: ReasoningEffort = "medium"
PUZZLE_KEYS: tuple[OrdinalKey, ...] = ("p1", "p2", "p3", "p4", "p5", "p6")
REQUIRED_KEYS: tuple[OrdinalKey, ...] = PUZZLE_KEYS[:4]

_SOLUTIONS: dict[LockType, type[Model]] = {
    "code": CodeSolution,
    "order": OrderSolution,
    "use_on": UseOnSolution,
    "find": FindSolution,
}
_LOCK_SHAPES: dict[LockType, str] = {
    "code": f'"code": a string of {CODE_LENGTH.start} to {CODE_LENGTH[-1]} characters the player types, '
    "read off the room (digits on a dial, a date, letters on a spine).",
    "order": f'"order": "interactables", {ORDER_LENGTH.start} to {ORDER_LENGTH[-1]} object ids '
    "the player clicks in that sequence.",
    "use_on": '"use_on": an "item" the player carries, used on a "target"; the two differ, and the item is the '
    'target of a "find" puzzle listed in this puzzle\'s "requires".',
    "find": '"find": the "target" the player must click to pick up or discover.',
}


# --- Response schema (AD-2, AD-18) -------------------------------------------


class _Puzzle(Model):
    """One drafted Puzzle; `lock_type` and `solution` are narrowed to the Lock types the builder is given."""

    lock_type: LockType
    is_exit: bool
    requires: list[OrdinalKey]
    clue: str
    lore: str
    rungs: Rungs
    evidence: Evidence
    solution: Solution

    @model_validator(mode="after")
    def _solution_matches_lock_type(self) -> _Puzzle:
        if self.solution.lock_type != self.lock_type:
            raise ValueError(f"solution is {self.solution.lock_type!r}, lock_type is {self.lock_type!r}")
        return self


def response_schema(lock_types: tuple[LockType, ...] = LOCK_TYPES) -> type[Model]:
    """The Riddler's response model: `p1`..`p4` required, `p5` and `p6` optional, one Puzzle each.

    `lock_type` and the `solution` union admit only `lock_types`; `requires` and
    the puzzle keys are the fixed `p1`..`p6`, so no field is map-typed. One
    class per set of Lock types, so a schema hash is stable across calls.
    """
    return _response_schema(tuple(lock_types))


@cache
def _response_schema(lock_types: tuple[LockType, ...]) -> type[Model]:
    unknown = [lock_type for lock_type in lock_types if lock_type not in _SOLUTIONS]
    if not lock_types or unknown:
        raise ValueError(f"lock types must be a non-empty subset of {', '.join(_SOLUTIONS)}; got {lock_types!r}")
    solution = reduce(or_, (_SOLUTIONS[lock_type] for lock_type in lock_types))
    puzzle = create_model(
        "RiddlerPuzzle",
        __base__=_Puzzle,
        lock_type=(Literal[*lock_types], ...),
        solution=(Annotated[solution, Field(discriminator="lock_type")], ...),
    )
    fields = {key: (puzzle, ...) for key in REQUIRED_KEYS} | {key: (puzzle | None, None) for key in PUZZLE_KEYS[4:]}
    return create_model("RiddlerResponse", __base__=Model, **fields)


# --- Prompt text ------------------------------------------------------------


def _system(lock_types: tuple[LockType, ...]) -> str:
    """The fixed prefix: the task, the response shape, the Validator's checks and the voice rules."""
    allowance = (
        ' The "near_answer" of an "order" or "use_on" puzzle may name at most one of the objects its solution lists.'
        if {"order", "use_on"} & set(lock_types)
        else ""
    )
    return "\n".join((
        "You are the Riddler, the wizard who writes the puzzles of an escape room built from a player's own photos.",
        "",
        'The user message lists the room\'s objects as JSON: each has an "id" (ix_...), a "label", the "attributes"',
        'a vision pass read off it, "instances" (how many alike were found) and "photo" (the index of the photo that',
        "shows it best). Write puzzles about these objects and nothing else, and name an object only by its exact",
        '"id", never by its label.',
        "",
        "Response shape",
        f"- Answer with the keys {', '.join(PUZZLE_KEYS)}: {', '.join(REQUIRED_KEYS)} are required; "
        f"{' and '.join(PUZZLE_KEYS[4:])} are null when you write fewer puzzles. Each key holds one puzzle.",
        '- Exactly one puzzle has "is_exit": true. Every other puzzle leads to it: directly or through a chain of',
        '  "requires", the exit waits on all of them.',
        '- "requires" lists the keys (p1 to p6) of the puzzles that must be open before this one; a puzzle never',
        "  waits on itself through any chain, and at least one puzzle requires nothing.",
        f'- "lock_type" is one of: {", ".join(lock_types)}. "solution" takes the shape of that lock type:',
        *(f"  - {_LOCK_SHAPES[lock_type]}" for lock_type in lock_types),
        '- "evidence" names, by "id", the object that gives the puzzle away and copies one of that object\'s',
        '  "attributes" word for word into "visible_attribute". The attribute says where to look and never holds',
        "  a solution token.",
        "",
        "The Validator refuses a draft that fails any of these checks, and the build sends it back to you:",
        *(f"{rule.number}. {rule.name}." for rule in RULES.values()),
        "",
        "Voice",
        '- The "clue" and the "lore" speak in the Riddler\'s voice: wry and teasing, never mocking, never',
        "  condescending. The clue is one or two sentences that point at the evidence without quoting it. The lore",
        f"  is in-world flavor of at most {LORE_MAX_WORDS} words and gives no help.",
        '- The three "rungs" speak in the Guide\'s voice, encouraging and warm, never scolding, because the Guide',
        "  signs them and may show them word for word. They climb a ladder, and each rung on its own moves the",
        "  player one step forward:",
        '  - "nudge" says where to look. It is the shortest: one short sentence.',
        '  - "direction" says what to notice there. It is longer than the nudge.',
        '  - "near_answer" says how to use what was noticed. It is the longest, and still at most two sentences.',
        "  Lengths increase from nudge to direction to near-answer.",
        '- Never write "the answer is", "the code is" or anything like it. A rung scaffolds; it never answers.',
        "- No clue, lore line or rung holds a solution token: not the code or any digit of it, and not the label of"
        f" an object the solution names.{allowance}",
    ))


def _objects(view: RoomView) -> str:
    """The Interactables as JSON: exactly the prompt view's fields, and nothing from a Puzzle."""
    return json.dumps([ix.model_dump() for ix in view.interactables], indent=2)


def _reason_line(reason: ValidatorReason) -> str:
    where = f"puzzle {reason.puzzle_id}, " if reason.puzzle_id is not None else ""
    return f"- rule {reason.rule}, {where}field {reason.field}: {reason.message}"


@dataclass(frozen=True)
class RiddlerPrompt:
    """What the author stage hands to the `riddler` port: text, the response model and the effort."""

    system: str
    user: str
    response_schema: type[Model]
    reasoning_effort: ReasoningEffort = REASONING_EFFORT

    def messages(self) -> list[ChatMessage]:
        return [ChatMessage("system", self.system), ChatMessage("user", self.user)]


def build_author_prompt(view: RoomView, lock_types: tuple[LockType, ...] = LOCK_TYPES) -> RiddlerPrompt:
    """The authoring prompt over the view's Interactables only, at reasoning `medium`."""
    return RiddlerPrompt(
        system=_system(lock_types),
        user=f"Objects in this room:\n{_objects(view)}\n",
        response_schema=response_schema(lock_types),
    )


def build_regeneration_prompt(
    view: RoomView, reasons: Sequence[ValidatorReason], lock_types: tuple[LockType, ...] = LOCK_TYPES
) -> RiddlerPrompt:
    """The authoring prompt plus the refused attempt's reasons (rule, Puzzle, field, fixed message), never its draft."""
    prompt = build_author_prompt(view, lock_types)
    sent_back = "\n".join((
        "Your previous draft was refused and is not shown. The Validator sent it back for these reasons; write a",
        "fresh draft that passes every check:",
        *(_reason_line(reason) for reason in reasons),
    ))
    return RiddlerPrompt(
        system=prompt.system,
        user=f"{prompt.user}\n{sent_back}\n",
        response_schema=prompt.response_schema,
    )
