"""The Dry run prompt: what a player sees, and nothing else (AD-3, AD-12).

`build_dry_run_prompt(room_view, response_schema)` is pure over `RoomView`.
It renders each Interactable's `id` and `label` and each Puzzle's `id`, Clue
and three Rungs; never a solution, Lore, an attribute or a profile field.
The pipeline dryrun stage makes the call at reasoning `low`, hands the stored
photo bytes to the adapter as `images`, and is the only place the answers
meet the solutions (`check_dry_run`).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from src.domain.schema import InteractableView, PuzzleView, RoomView
from src.providers.base import ChatMessage, ReasoningEffort

REASONING_EFFORT: ReasoningEffort = "low"

SYSTEM = (
    "You are a player inside a photo escape room. The attached photos show the room, "
    "and the objects listed in the task are what a player can click, each named by its id. "
    "Solve every puzzle from the photos, its clue and its three hints alone, as a player would. "
    "Reply with JSON only: `answers`, one `{puzzle_id, answer}` per puzzle, in the order given. "
    "`answer` takes one of four shapes, chosen by its `lock_type`: "
    "`code` with `code`, the string a player would type; "
    "`order` with `interactables`, the object ids in the order a player would click them; "
    "`use_on` with `item` and `target`, the object id used and the object id it is used on; "
    "`find` with `target`, the object id a player would pick up. "
    "Name objects only by the ids listed, never by label."
)


@dataclass(frozen=True)
class DryRunPrompt:
    """The `chat` arguments of the Dry run call; the photos join them as `images` at the call."""

    messages: list[ChatMessage]
    response_schema: type[BaseModel]
    reasoning_effort: ReasoningEffort


def _object_line(interactable: InteractableView) -> str:
    return f"- {interactable.id}: {interactable.label}"


def _puzzle_block(puzzle: PuzzleView) -> str:
    return "\n".join((
        f"Puzzle {puzzle.id}",
        f"Clue: {puzzle.clue}",
        "Hints, from the vaguest to the most direct:",
        f"1. {puzzle.rungs.nudge}",
        f"2. {puzzle.rungs.direction}",
        f"3. {puzzle.rungs.near_answer}",
    ))


def render_task(room_view: RoomView) -> str:
    """The user text: the clickable objects by id and label, then each puzzle's id, clue and hints."""
    objects = "\n".join(_object_line(ix) for ix in room_view.interactables)
    puzzles = "\n\n".join(_puzzle_block(puzzle) for puzzle in room_view.puzzles)
    return f"Objects in the room (id: label):\n{objects}\n\nPuzzles:\n\n{puzzles}\n"


def build_dry_run_prompt(room_view: RoomView, response_schema: type[BaseModel]) -> DryRunPrompt:
    """The Dry run call over what a player sees: fixed instructions, the rendered task, reasoning `low`."""
    return DryRunPrompt(
        messages=[ChatMessage("system", SYSTEM), ChatMessage("user", render_task(room_view))],
        response_schema=response_schema,
        reasoning_effort=REASONING_EFFORT,
    )
