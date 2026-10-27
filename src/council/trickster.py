"""Trickster proposal sources (AD-12, AD-15): the `TricksterSource` port, the recorded proposals and their replay.

A source answers one window: given the Room's `room_id`, the window index
(the `window` of the `TricksterEdit` the route builds, counted from 0 per
Session), the `RoomView` and the Game-state summary, it returns one
`TricksterProposal` (a `type`, `puzzle` and `payload`) or None. A source
never decides a Card: the route mints the `te_` id and the live Validator
accepts or rejects every proposal (AD-12), whatever the source.

A recorded-proposals artifact is bound to one Room: its `room_id` and its
proposals in window order, and no verdict, so a file carrying
`validator_result` or `accepted` fails to load. `ScriptedSource` replays
one: the proposal at the window index on that Room, None on any other Room
or once the recording is used up. It reads only `room_id` and the window
index, holds no state between calls (each answer is a fresh copy, so a
caller changing it never changes a later window), makes no `ModelProvider`
call and writes no Ledger entry.

`SOURCES` maps the replay values of `DEMO_TRICKSTER` to a source over a
root folder: `scripted` replays the recorded-proposals artifact at
`RECORDED_PROPOSALS` and `authored` (cut 1) the committed pre-authored file
at `AUTHORED_PROPOSALS`, neither with a live path. `live` and `record` take
`LiveSource` over the `trickster` role's provider, which wiring registers
beside them in its own source table.

`LiveSource` asks the model for one window's proposal (FR-18, AD-3, AD-6):
`build_trickster_prompt` renders the fixed menu, the `RoomView` and the
Game-state summary, and never a `Room`, so no solution, `derived` key or
Player profile field can reach the prompt. It makes one `chat` call at
reasoning `low` with `TricksterProposal` as the response schema (the four
edit types and their payloads; it passes `strict_schema`, which the
`openai_compatible` fallback sends) and `attempt` set to the window index,
so two windows never share a cache key. The reply's ids are kept exactly as
written, never matched by label or case: an id the `RoomView` lacks reaches
the Validator, which rejects the Card. A reply that does not parse into a
proposal is a `ProviderError`, so the window records the skipped card like
any other provider failure (AD-13). With a `recording` path (`record`) each
proposal is also written by `record_proposal` into the recorded-proposals
artifact for its Room, in window order and with no verdict, for `scripted`
to replay through the live Validator (FR-25, AD-15).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError, model_validator

from src.domain.schema import EditType, Model, Payload, PuzzleId, RoomId, RoomView
from src.domain.session import GameStateSummary
from src.providers.base import ChatMessage, ModelProvider, ProviderError, ReasoningEffort

RECORDED_PROPOSALS = Path("proposals/recorded.json")
"""The recorded-proposals artifact `DEMO_TRICKSTER=scripted` replays, under the source's root."""
AUTHORED_PROPOSALS = Path("proposals/authored.json")
"""The committed pre-authored proposals file `DEMO_TRICKSTER=authored` (cut 1) replays, under the source's root."""
REASONING_EFFORT: ReasoningEffort = "low"


class TricksterProposal(Model):
    """One window's proposal: the `TricksterEdit` fields a source supplies, with no id, window or verdict."""

    type: EditType
    puzzle: PuzzleId
    payload: Payload

    @model_validator(mode="after")
    def _payload_matches_type(self) -> TricksterProposal:
        if self.payload.type != self.type:
            raise ValueError(f"payload is {self.payload.type!r}, type is {self.type!r}")
        return self


class RecordedProposals(Model):
    """A recorded-proposals artifact: one Room and its proposals in window order (index 0 first)."""

    room_id: RoomId
    proposals: list[TricksterProposal]


def load_proposals(path: Path) -> RecordedProposals:
    """Read an artifact; one carrying `validator_result`, `accepted` or any other unknown key fails to load."""
    return RecordedProposals.model_validate_json(path.read_text())


class TricksterSource(Protocol):
    """Where a window's proposal comes from; the Validator, never the source, decides the Card."""

    def propose(
        self, room_id: str, window: int, room_view: RoomView, summary: GameStateSummary
    ) -> TricksterProposal | None: ...


@dataclass(frozen=True)
class ScriptedSource:
    """Replays one artifact by `room_id` and window index alone; the `RoomView` and summary never change its answer."""

    recording: RecordedProposals

    def propose(
        self, room_id: str, window: int, room_view: RoomView, summary: GameStateSummary
    ) -> TricksterProposal | None:
        proposals = self.recording.proposals
        if room_id != self.recording.room_id or not 0 <= window < len(proposals):
            return None
        return proposals[window].model_copy(deep=True)


def _scripted_over(file: Path) -> Callable[[Path], TricksterSource]:
    def source(root: Path) -> TricksterSource:
        return ScriptedSource(load_proposals(root / file))

    return source


SOURCES: dict[str, Callable[[Path], TricksterSource]] = {
    "scripted": _scripted_over(RECORDED_PROPOSALS),
    "authored": _scripted_over(AUTHORED_PROPOSALS),
}
"""`DEMO_TRICKSTER` value to its source over a root folder; neither scripted value has a live path (AD-15)."""


# --- The live source (FR-18, AD-3, AD-6) ---------------------------------------------

SYSTEM = """\
You are the Trickster, the wizard who bends an escape room while a player is inside it.

Propose exactly one change from this fixed menu, and nothing else:
- "decoy": false evidence for a puzzle that is not the exit. The payload names an object by its "interactable" id
  and copies one of that object's "attributes" word for word into "visible_attribute". A puzzle takes one decoy at most.
- "merge": "puzzle_b" now waits on "puzzle_a"; "puzzle" is one of the two.
- "loosen": the next hint of "puzzle" opens early; the payload repeats "puzzle" and names the "rung":
  "nudge", "direction" or "near_answer".
- "shortcut": "puzzle" stops waiting on one puzzle it waits on now; the payload repeats "puzzle" and names that
  puzzle as "requires".

Read the game state: a player racing ahead earns a harder room, a player who is stuck an easier one.
Name puzzles and objects only by the exact ids listed. Every change is checked against the room's rules
before it applies, and one that breaks a rule is refused in front of the player.

Reply with JSON only: "type", "puzzle" and "payload", where the payload's "type" repeats "type"."""


@dataclass(frozen=True)
class TricksterPrompt:
    """The `chat` arguments of one window's call: the messages, the response model and the effort."""

    messages: list[ChatMessage]
    response_schema: type[TricksterProposal]
    reasoning_effort: ReasoningEffort


def _minutes(elapsed_ms: int) -> str:
    seconds = elapsed_ms // 1000
    return f"{seconds // 60} min {seconds % 60} s"


def render_state(room_view: RoomView, summary: GameStateSummary) -> str:
    """The user text: the objects and puzzles as a player sees them, then how the game is going."""
    objects = [{"id": ix.id, "label": ix.label, "attributes": ix.attributes} for ix in room_view.interactables]
    puzzles = [
        {"id": pz.id, "lock_type": pz.lock_type, "requires": pz.requires, "is_exit": pz.is_exit, "clue": pz.clue}
        for pz in room_view.puzzles
    ]
    return "\n".join((
        f"Objects in the room:\n{json.dumps(objects, indent=2)}",
        "",
        f"Puzzles:\n{json.dumps(puzzles, indent=2)}",
        "",
        "Game state:",
        f"- Locks open: {', '.join(summary.locks_open) or 'none'}",
        f"- Time in the room: {_minutes(summary.elapsed_ms)}",
        f"- Hints used: {summary.rungs_used}",
        "",
    ))


def build_trickster_prompt(room_view: RoomView, summary: GameStateSummary) -> TricksterPrompt:
    """One window's call over the `RoomView` and the Game-state summary alone, at reasoning `low`."""
    return TricksterPrompt(
        messages=[ChatMessage("system", SYSTEM), ChatMessage("user", render_state(room_view, summary))],
        response_schema=TricksterProposal,
        reasoning_effort=REASONING_EFFORT,
    )


def parse_proposal(text: str) -> TricksterProposal:
    """The reply as a proposal, its ids exactly as written; a reply that is not one is a `ProviderError`."""
    try:
        return TricksterProposal.model_validate_json(text)
    except ValidationError as exc:
        raise ProviderError(200, "invalid_proposal", f"the reply is not a proposal ({exc.error_count()} errors)") from exc


def record_proposal(path: Path, room_id: str, window: int, proposal: TricksterProposal) -> RecordedProposals:
    """Write `proposal` as window `window` of the artifact for `room_id` at `path`, with no verdict.

    The artifact keeps the proposals of the windows before `window` when it
    already belongs to `room_id`, so a fresh Session (window 0) starts a new
    recording and an artifact for another Room is replaced.
    """
    earlier: list[TricksterProposal] = []
    if path.is_file():
        stored = load_proposals(path)
        if stored.room_id == room_id:
            earlier = stored.proposals[:window]
    recording = RecordedProposals(room_id=room_id, proposals=[*earlier, proposal])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(recording.model_dump_json(indent=2) + "\n")
    return recording


@dataclass(frozen=True)
class LiveSource:
    """One `chat` call per window on the `trickster` role's provider; with `recording` (`record`), each proposal is also written there."""

    provider: ModelProvider
    recording: Path | None = None

    def propose(
        self, room_id: str, window: int, room_view: RoomView, summary: GameStateSummary
    ) -> TricksterProposal | None:
        prompt = build_trickster_prompt(room_view, summary)
        reply = self.provider.chat(
            prompt.messages,
            response_schema=prompt.response_schema,
            reasoning_effort=prompt.reasoning_effort,
            attempt=window,
        )
        proposal = parse_proposal(reply.text)
        if self.recording is not None:
            record_proposal(self.recording, room_id, window, proposal)
        return proposal
