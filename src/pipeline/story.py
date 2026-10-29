"""The story stage (story mode, 29 Oct 2026): each Room's own wizard lines, written once at build time (AD-3, AD-7, AD-16).

The runner reaches story after the Dry run passed (or was skipped) and
before scene. `run_story` assembles the attempt's Room, derives its
`StoryBrief` (`story_brief`: the name, the area labels, the counts and the
scenery labels only) and makes one `chat` call through the `storyteller`
role's port at reasoning `low`, tagged with the job id and the `story`
stage for the ledger. The reply must pass `story_reasons`: every slot
present and non-empty, one riddle per Puzzle, each line at most `LINE_MAX`
characters, no solution, target or item label, evidence attribute or code
in any line (`gives_away`, rule 5's matching), no exclamation mark but the
Trickster's trap line's, and no word about AI, models or the API. A reply
that fails is sent back once at attempt 1 with its fixed reasons, which
name slots and never quote a line; a second failure, or a call that raises,
leaves the fixed templates (`template_story`, EXPERIENCE.md story mode
copy) filled from the Room, so the story never ends a Build; a call that
raises logs one JSON line naming its code. The story is
stored under `<room_id>/story.json` for scene to put on the Room; each call
that answered adds its call row, and the done row counts the story's lines
and names the model only when its lines were kept.
"""

from __future__ import annotations

import json
import logging
import re

import pydantic

from src.council.storyteller import (
    CHEST_HINTS,
    LINE_MAX,
    StoryBrief,
    build_story_prompt,
    build_story_retry_prompt,
)
from src.domain.schema import (
    CallRow,
    FindSolution,
    JobState,
    OrderSolution,
    Puzzle,
    Room,
    RoomId,
    Story,
    StoryResponse,
    StoryRiddle,
    UseOnSolution,
)
from src.domain.validator import gives_away
from src.pipeline.author import assemble_room
from src.pipeline.build import StageFn, StageResult, call_row, error_code
from src.pipeline.ports import ArtifactStore, LedgerStore
from src.providers.base import ModelProvider

logger = logging.getLogger(__name__)

STORY_FILE = "story.json"
"""The stage artifact under `<room_id>/`: the `Story` scene puts on the Room."""
TRAP_SLOT = "trickster_trap"
"""The one slot whose line keeps an exclamation mark (owner call, 29 Oct 2026)."""
SINGLE_LINES = len(Story.model_fields) - 1
"""The story's lines outside its riddles; each riddle adds two."""
OFF_STORY = re.compile(r"\b(a\.?i|llms?|models?|apis?|prompts?|chatbots?)\b", re.IGNORECASE)

SHAPE_MESSAGE = "The reply did not follow the response shape."
EMPTY_MESSAGE = "the line is empty."
LONG_MESSAGE = f"the line is longer than {LINE_MAX} characters."
LEAK_MESSAGE = "the line gives part of an answer away."
EXCLAMATION_MESSAGE = "the line has an exclamation mark."
OFF_STORY_MESSAGE = "the line talks about AI, models or the API."
"""The fixed reasons, each after its slot's name; none quotes a line."""


def story_key(room_id: RoomId) -> str:
    return f"{room_id}/{STORY_FILE}"


def read_story(room_id: RoomId, artifacts: ArtifactStore) -> Story | None:
    """The story the story stage stored for `room_id`, or None before it ran."""
    try:
        return Story.model_validate_json(artifacts.read(story_key(room_id)))
    except KeyError:
        return None


def _named(puzzle: Puzzle) -> set[str]:
    """Every `ix_` id the Puzzle's solution or evidence names."""
    solution = puzzle.solution
    if isinstance(solution, OrderSolution):
        ids = set(solution.interactables)
    elif isinstance(solution, UseOnSolution):
        ids = {solution.item, solution.target}
    elif isinstance(solution, FindSolution):
        ids = {solution.target}
    else:
        ids = set()
    return ids | {puzzle.evidence.interactable}


def story_brief(room: Room) -> StoryBrief:
    """The brief for `room`: its name, area labels (none until photos carry one), counts and scenery labels."""
    named = set().union(*(_named(puzzle) for puzzle in room.puzzles))
    areas = (getattr(photo, "area", None) for photo in room.photos)
    return StoryBrief(
        room_name=room.name,
        areas=tuple(dict.fromkeys(area for area in areas if area)),
        photos=len(room.photos),
        things=sum(ix.polygons is not None for ix in room.interactables),
        riddles=len(room.puzzles),
        scenery=tuple(ix.label for ix in room.interactables if ix.id not in named),
    )


def riddle_order(room: Room) -> list[Puzzle]:
    """The Puzzles in riddle order: the Room's order with the exit last."""
    return sorted(room.puzzles, key=lambda puzzle: puzzle.is_exit)


# --- The fixed templates (EXPERIENCE.md, story mode) --------------------------


def _joined(areas: tuple[str, ...]) -> str:
    """The area labels joined as "a, b and c"; "room" when the photos name none."""
    if not areas:
        return "room"
    return areas[0] if len(areas) == 1 else f"{', '.join(areas[:-1])} and {areas[-1]}"


def _solved_line(room: Room, puzzle: Puzzle) -> str:
    """The Riddler's reaction by lock type; a find whose target a later use_on carries keeps it."""
    if puzzle.is_exit:
        return f"{len(room.puzzles)} riddles, {len(room.puzzles)} answers. The way out is yours."
    if isinstance(puzzle.solution, FindSolution):
        carried = {p.solution.item for p in room.puzzles if isinstance(p.solution, UseOnSolution)}
        if puzzle.solution.target in carried:
            return "Well found. Keep hold of that; this house isn't finished with it."
        return "Well found. The house noticed you noticing."
    return {
        "use_on": "The right thing in the right place. The house approves.",
        "code": "The numbers agree with you. They rarely agree with anyone.",
        "order": "In order at last. Someone here will be thrilled.",
    }[puzzle.lock_type]


def template_story(room: Room, brief: StoryBrief | None = None) -> Story:
    """The fixed story lines filled from the Room: what plays when the storyteller's lines are not kept."""
    brief = brief or story_brief(room)
    return Story(
        architect_welcome=f"Thank you for your photos. I built your {_joined(brief.areas)} from them: "
        f"{brief.photos} angles, {brief.things} things worth a closer look.",
        trickster_trap="Oh no, you seem to be trapped! I locked the way out and gave the key to the Riddler. "
        "Wicked of me, I know.",
        riddler_entrance="Don't mind him; he thinks a locked door is a party. To escape, you must answer my riddles: "
        f"{brief.riddles} of them, one at a time.",
        guide_chest=f"Stuck? I keep {CHEST_HINTS} hints in that chest, for the whole house. Choose your moment.",
        riddles=[
            StoryRiddle(puzzle_id=puzzle.id, opening="You must answer this.", solved=_solved_line(room, puzzle))
            for puzzle in riddle_order(room)
        ],
        trickster_closing="Fine. Out you go. I'll lock it again for the next guest.",
        riddler_closing="Clever mind. I'll write harder ones next time.",
        guide_closing_no_hints="Not a single hint. I'm almost offended.",
        guide_closing_hints="You let me help a little. I enjoyed every word.",
    )


# --- The storyteller's reply ------------------------------------------------


def _slots(response: StoryResponse) -> list[tuple[str, str]]:
    """Every line of the reply under its slot's name, the riddles as `riddle n, opening|solved`."""
    scalars = [(slot, text) for slot, text in response.model_dump().items() if slot != "riddles"]
    riddles = [
        (f"riddle {n}, {part}", text)
        for n, riddle in enumerate(response.riddles, start=1)
        for part, text in (("opening", riddle.opening), ("solved", riddle.solved))
    ]
    return scalars + riddles


def _line_reason(slot: str, text: str, room: Room) -> str | None:
    if not text.strip():
        return EMPTY_MESSAGE
    if len(text) > LINE_MAX:
        return LONG_MESSAGE
    if gives_away(text, room):
        return LEAK_MESSAGE
    if "!" in text and slot != TRAP_SLOT:
        return EXCLAMATION_MESSAGE
    if OFF_STORY.search(text):
        return OFF_STORY_MESSAGE
    return None


def story_reasons(response: StoryResponse, room: Room) -> list[str]:
    """The fixed reasons the reply breaks a line rule, each naming its slot; empty when every line passes."""
    reasons = [f"{slot}: {reason}" for slot, text in _slots(response) if (reason := _line_reason(slot, text, room))]
    if len(response.riddles) != len(room.puzzles):
        reasons.append(f"riddles: write exactly {len(room.puzzles)} riddles.")
    return reasons


def _story(response: StoryResponse, room: Room) -> Story:
    """The reply as the Room's `Story`, each riddle keyed by its Puzzle in riddle order."""
    riddles = [
        StoryRiddle(puzzle_id=puzzle.id, opening=lines.opening, solved=lines.solved)
        for puzzle, lines in zip(riddle_order(room), response.riddles, strict=True)
    ]
    return Story.model_validate({**response.model_dump(exclude={"riddles"}), "riddles": riddles})


def _reasons(text: str, room: Room) -> tuple[StoryResponse | None, list[str]]:
    """The reply parsed and checked: its reasons, or the shape reason when it does not parse."""
    try:
        response = StoryResponse.model_validate_json(text)
    except pydantic.ValidationError:
        return None, [SHAPE_MESSAGE]
    return response, story_reasons(response, room)


def run_story(state: JobState, *, provider: ModelProvider, artifacts: ArtifactStore, ledger: LedgerStore) -> StageResult:
    """The storyteller's lines when they pass, after at most one retry, else the templates; stored under `story.json`."""
    room = assemble_room(state, artifacts, ledger)
    brief = story_brief(room)
    prompt = build_story_prompt(brief)
    rows: list[CallRow] = []
    story: Story | None = None
    model: str | None = None
    try:
        for attempt in range(2):
            reply = provider.chat(
                prompt.messages(),
                response_schema=prompt.response_schema,
                reasoning_effort=prompt.reasoning_effort,
                attempt=attempt,
                job_id=state.id,
                stage="story",
            )
            rows.append(call_row(reply.receipt, provider, "storyteller", reply.model))
            response, reasons = _reasons(reply.text, room)
            if response is not None and not reasons:
                story, model = _story(response, room), reply.model
                break
            prompt = build_story_retry_prompt(brief, reasons)
    except Exception as exc:  # noqa: BLE001 - the story never ends a Build: a call that raises leaves the templates
        logger.info(json.dumps({"job_id": state.id, "stage": "story", "fallback": error_code(exc)}))
    story = story or template_story(room, brief)
    artifacts.put(story_key(room.id), story.model_dump_json().encode())
    return StageResult(count=SINGLE_LINES + 2 * len(story.riddles), model=model, calls=rows)


def story_stage(provider: ModelProvider, artifacts: ArtifactStore, ledger: LedgerStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `story`, over the `storyteller` role's provider."""
    return lambda state: run_story(state, provider=provider, artifacts=artifacts, ledger=ledger)
