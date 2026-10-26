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
index, holds no state between calls, makes no `ModelProvider` call and
writes no Ledger entry.

`SOURCES` maps the `DEMO_TRICKSTER` values to a source over a root folder:
`scripted` replays the recorded-proposals artifact at `RECORDED_PROPOSALS`
and `authored` (cut 1) the committed pre-authored file at
`AUTHORED_PROPOSALS`, neither with a live path; `live` and `record` join
with the live source.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import model_validator

from src.domain.schema import EditType, Model, Payload, PuzzleId, RoomId, RoomView
from src.domain.session import GameStateSummary

RECORDED_PROPOSALS = Path("proposals/recorded.json")
"""The recorded-proposals artifact `DEMO_TRICKSTER=scripted` replays, under the source's root."""
AUTHORED_PROPOSALS = Path("proposals/authored.json")
"""The committed pre-authored proposals file `DEMO_TRICKSTER=authored` (cut 1) replays, under the source's root."""


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
        return proposals[window]


def _scripted_over(file: Path) -> Callable[[Path], TricksterSource]:
    def source(root: Path) -> TricksterSource:
        return ScriptedSource(load_proposals(root / file))

    return source


SOURCES: dict[str, Callable[[Path], TricksterSource]] = {
    "scripted": _scripted_over(RECORDED_PROPOSALS),
    "authored": _scripted_over(AUTHORED_PROPOSALS),
}
"""`DEMO_TRICKSTER` value to its source over a root folder; neither scripted value has a live path (AD-15)."""
