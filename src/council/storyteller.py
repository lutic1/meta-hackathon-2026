"""The storyteller prompt (AD-3, AD-5): the Room's wizard lines, over a story brief and nothing else.

`build_story_prompt(brief)` is pure over a `StoryBrief`: the room's name,
its area labels, the counts of photos, things and riddles, and the labels of
the scenery Interactables (those no Puzzle's solution or evidence names).
The pipeline derives the brief from the Room, so no solution, target or item
label, evidence attribute, code or Puzzle text reaches this module. The fixed
prefix carries the premise of the story, every slot, each wizard's voice
(EXPERIENCE.md Voice and Tone) and the line rules the story stage checks; the
retry variant adds the refused reply's fixed reasons as a further user
message and never the reply itself. The response schema has no map field
(AD-2): the riddles are a list in riddle order, the exit last.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from src.domain.schema import StoryResponse
from src.providers.base import ChatMessage, ReasoningEffort

REASONING_EFFORT: ReasoningEffort = "low"
LINE_MAX = 220
"""The longest a story line may be, in characters."""
CHEST_HINTS = 2
"""The hints the treasure chest holds for the whole game (story mode, 29 Oct 2026)."""


@dataclass(frozen=True)
class StoryBrief:
    """What the storyteller is told about a Room: counts and labels only, never a Puzzle's content."""

    room_name: str | None
    areas: tuple[str, ...]
    """The Architect's area labels in first-appearance order; empty when the photos carry none."""
    photos: int
    things: int
    """Interactables with an outline."""
    riddles: int
    scenery: tuple[str, ...]
    """Labels of the Interactables no Puzzle's solution or evidence names."""


SYSTEM = f"""\
You write the spoken lines of an escape room built from photos of a player's own room. Four wizards speak them.
The user message describes the room as JSON: "room_name" (or null), "areas" (the parts of the home the photos show,
possibly empty), "photos", "things" (objects worth a closer look), "riddles" and "scenery" (labels of objects no
riddle is about).

The story: the Architect built the room from the player's photos and thanks them for it. The Trickster locks the
player in and hands the key to the Riddler. The Riddler says that to escape the player must answer the riddles, one
at a time. The Guide keeps {CHEST_HINTS} hints in a treasure chest, for the whole game. At the end the player escapes.

Write one line for each slot:
- "architect_welcome": the Architect thanks the player for the photos and welcomes them in.
- "trickster_trap": the Trickster traps the player. It starts with "Oh no, you seem to be trapped!"
- "riddler_entrance": the Riddler says the player must answer the riddles, one at a time, to escape.
- "guide_chest": the Guide offers the hints in the chest, for the whole game, and says to choose the moment.
- "riddles": one entry per riddle, in order; the last riddle opens the way out. "opening" is the Riddler's line as
  the riddle starts, "solved" the Riddler's line once it is solved. Both are flavour only: they never say where to
  look, what to do or what the riddle is about.
- "trickster_closing", "riddler_closing": each one's line as the player escapes.
- "guide_closing_no_hints": the Guide's goodbye to a player who never opened the chest.
- "guide_closing_hints": the Guide's goodbye to a player who used a hint.

Voices: the Architect observes (plain facts with a dry aside), the Riddler teases (never mocks), the Guide
encourages (never scolds, never sighs), the Trickster has the most fun (mischief aimed at the room, never at the
player). Never condescending.

Rules for every line:
- One or two sentences, at most {LINE_MAX} characters, never empty.
- No exclamation mark, except the one in "Oh no, you seem to be trapped!"
- Write no numbers, in digits or in words.
- Name no object except the scenery labels given; never hint at what a riddle is about.
- Stay inside the story: never mention AI, models, prompts or an API.
Answer only with the JSON the schema asks for."""


def prompt_hash() -> str:
    """sha256 of the fixed prefix, for `Provenance.prompt_hashes['storyteller']` (AD-16)."""
    return hashlib.sha256(SYSTEM.encode()).hexdigest()


@dataclass(frozen=True)
class StoryPrompt:
    """What the story stage hands to the `storyteller` port: the messages, the response model and the effort."""

    system: str
    user: tuple[str, ...]
    response_schema: type[StoryResponse] = StoryResponse
    reasoning_effort: ReasoningEffort = REASONING_EFFORT

    def messages(self) -> list[ChatMessage]:
        return [ChatMessage("system", self.system), *(ChatMessage("user", text) for text in self.user)]


def build_story_prompt(brief: StoryBrief) -> StoryPrompt:
    """The story prompt: the fixed prefix, then the brief as JSON."""
    return StoryPrompt(system=SYSTEM, user=(json.dumps(asdict(brief)),))


def build_story_retry_prompt(brief: StoryBrief, reasons: Sequence[str]) -> StoryPrompt:
    """The story prompt plus the refused reply's fixed reasons, never the reply."""
    sent_back = "\n".join((
        "Your previous story was refused and is not shown, for these reasons; write a fresh one that keeps every rule:",
        *(f"- {reason}" for reason in reasons),
    ))
    return StoryPrompt(system=SYSTEM, user=(*build_story_prompt(brief).user, sent_back))
