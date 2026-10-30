"""The storyteller prompt (AD-3, AD-5): the Room's wizard lines, over a story brief and nothing else.

`build_story_prompt(brief)` is pure over a `StoryBrief`: the room's name,
its area labels, the counts of photos, things, riddles and chest hints, and
the labels of the scenery Interactables (those no Puzzle's solution or
evidence names, and none holding a word the story check refuses). The
pipeline derives the brief from the Room, so no solution, target or item
label, evidence attribute, code or Puzzle text reaches this module. The fixed
prefix carries the premise of the story, every slot (the Architect's welcome
twice: to the player in their own room and to a visitor in someone else's),
each wizard's personality with the fixed lines and EXPERIENCE.md Voice and
Tone lines as style examples, and the line rules the story stage checks; the
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
LINE_MAX = 160
"""The longest a story line may be, in characters."""
FILLER_WORDS = ("drift", "linger", "sway", "gently", "softly")
"""Filler the story check refuses in any form ("lingers", "swaying"): purple prose that says nothing concrete."""


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
    hints: int
    """The hints the treasure chest holds for the whole house."""
    scenery: tuple[str, ...]
    """Labels of the Interactables no Puzzle's solution or evidence names, holding no word the story check refuses."""


SYSTEM = f"""\
You write the spoken lines of an escape room built from photos of a real home. Four wizards speak them.
The user message describes the room as JSON: "room_name" (or null), "areas" (the parts of the home the photos show,
possibly empty), "photos", "things" (objects worth a closer look), "riddles" (how many riddles), "hints" (how many
hints the chest holds for the whole house) and "scenery" (labels of objects no riddle is about).

The story: the Architect built the room from photos of a home. The Trickster locks the player in and hands the key to
the Riddler. The Riddler says that to escape the player must answer the riddles, one at a time. The Guide keeps the
hints in a treasure chest, for the whole house. At the end the player escapes.

The wizards, each with a line in their voice:
- The Architect is proud and precise and observes: plain facts with a dry aside. "I notice everything. Mostly mugs."
- The Trickster is gleeful and mischievous and has the most fun: mischief aimed at the room, never at the player.
  "Wicked of me, I know."
- The Riddler is arch and teasing; it teases, never mocks. "I taught your things to talk. Pity they only speak in
  riddles."
- The Guide is warm and dry; it encourages, never scolds, never sighs. "Not a single hint. I'm almost offended."
None of them is ever condescending.

Write one line for each slot. The examples show the voice and the length; write your own words for this room, where
{{areas}}, {{riddles}} and {{hints}} stand for the values in the user message, the counts written in words:
- "architect_welcome": to a player in a room built from their own photos: the Architect thanks them for the photos
  and welcomes them in. Like "Thank you for your photos. I built your {{areas}} from them."
- "architect_welcome_visitor": to a player visiting a room built from someone else's photos: the Architect welcomes
  them in and never thanks them for photos, which they did not send. Like "Welcome to someone's {{areas}}. I built it
  from their photos."
- "trickster_trap": the Trickster traps the player. It starts with "Oh no, you seem to be trapped!" Like "Oh no, you
  seem to be trapped! I locked the way out and gave the key to the Riddler. Wicked of me, I know."
- "riddler_entrance": the Riddler says the player must answer its riddles, one at a time, to escape, and says how many
  riddles there are. Like "Don't mind him; he thinks a locked door is a party. To escape, you must answer my riddles:
  {{riddles}} of them, one at a time."
- "guide_chest": the Guide offers the hints in the chest, says how many there are for the whole house, and says to
  choose the moment. Like "Stuck? I keep {{hints}} hints in that chest, for the whole house. Choose your moment."
- "riddles": one entry per riddle, in order; the last riddle opens the way out. "opening" is the Riddler's line as
  the riddle starts, "solved" the Riddler's line once it is solved. Both are flavour only: they never say where to
  look, what to do or what the riddle is about. Like "You must answer this." and "Well found. The house noticed you
  noticing." The last riddle's "solved" line says the way out is open, in the words "way out":
  like "The way out is yours."
- "trickster_closing", "riddler_closing": each one's line as the player escapes. Like "Fine. Out you go. I'll lock
  it again for the next guest." and "Clever mind. I'll write harder ones next time."
- "guide_closing_no_hints": the Guide's goodbye to a player who never opened the chest. Like "Not a single hint. I'm
  almost offended."
- "guide_closing_hints": the Guide's goodbye to a player who used a hint. Like "You let me help a little. I enjoyed
  every word."

Rules for every line:
- One or two short sentences, at most {LINE_MAX} characters, never empty.
- Concrete and wry, in plain words. No purple prose and none of these filler words, in any form: \
{", ".join(FILLER_WORDS)}.
- No exclamation mark, except the one in "Oh no, you seem to be trapped!"
- No numbers, in digits or in words, except how many riddles in "riddler_entrance" and how many hints in
  "guide_chest", each written in words ("two", not "2").
- Name at most one object, and only one of the scenery labels given; never hint at what a riddle is about.
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
