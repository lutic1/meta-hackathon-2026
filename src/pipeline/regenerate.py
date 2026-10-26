"""The regeneration loop (AD-13, AD-6): a refused draft goes back to the Riddler with its reasons only, at most `REGEN_MAX` times.

A gate that refuses an attempt raises `FailedAttempt`: the author stage on
output it cannot read (A-24), the validate stage on the Validator's reasons,
and any later gate (the Dry run, 2.24) alike. The runner records the gate's
stage and hands the failure to `send_back`, which records the attempt's
fixed messages in job state as one `SentBack` list, keeps its reasons under
`<room_id>/reasons.json` for the next prompt, and then either advances the
Regeneration count, so the runner writes the next attempt (`rewriting`), or,
with the count at the job's `regen_max`, ends the job `needs_recapture`.
With `REGEN_MAX=2` that is at most 3 Riddler calls, with `REGEN_MAX=1`
(cut 7) at most 2. An exhausted loop has no error class of its own: the job
status says it.

This module is the only writer of the count. The stages only read it: as the
`attempt` of every Riddler and Dry run call, so under `CACHE=on` attempt n is
never served attempt n-1's answer, and into provenance. `riddler_prompt`
picks the Riddler's prompt: the authoring prompt on attempt 0, then the 2.19
regeneration variant over the last failed attempt's reasons only, never its
draft.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar, Literal

from pydantic import TypeAdapter

from src.council.riddler import (
    RiddlerPrompt,
    build_author_prompt,
    build_regeneration_prompt,
)
from src.domain.schema import (
    ErrorDetail,
    JobState,
    RoomId,
    RoomView,
    SentBack,
    ValidatorReason,
)
from src.pipeline.ports import ArtifactStore

if TYPE_CHECKING:
    from src.pipeline.build import StageResult

REASONS_FILE = "reasons.json"
"""The stage artifact under `<room_id>/`: the last failed attempt's reasons, for the regeneration prompt."""
REASONS = TypeAdapter(list[ValidatorReason])


class FailedAttempt(Exception):
    """A draft a gate sent back (AD-13): its fixed messages, which quote no token or answer, and its structured reasons.

    `result` is what the gate's stage did first (its call rows and
    verdicts), which the runner records before the loop decides.
    """

    gate: ClassVar[Literal["validate", "dryrun"]]
    """The gate the "Sent back" lines name: `validate` for the author stage's refusals and the Validator's."""

    def __init__(self, messages: Sequence[str], result: StageResult, reasons: Sequence[ValidatorReason] = ()) -> None:
        super().__init__("The draft was sent back: " + " ".join(messages))
        self.messages = list(messages)
        self.result = result
        self.reasons = list(reasons)


def reasons_key(room_id: RoomId) -> str:
    return f"{room_id}/{REASONS_FILE}"


def read_reasons(room_id: RoomId, artifacts: ArtifactStore) -> list[ValidatorReason]:
    """The reasons of the last failed attempt for `room_id`."""
    return REASONS.validate_json(artifacts.read(reasons_key(room_id)))


def rewriting(state: JobState) -> bool:
    """Whether the attempt at the current Regeneration count is still to be written, so the runner runs author next."""
    authored = sum(record.stage == "author" for record in state.stages)
    return 0 < authored <= state.regeneration_count


def send_back(state: JobState, failure: FailedAttempt, error: ErrorDetail, artifacts: ArtifactStore) -> JobState:
    """The failed attempt's `SentBack` list recorded, then the count advanced, or the job ended `needs_recapture` with `error`."""
    if state.room_id is None:
        raise ValueError(f"{state.id} names no room")
    artifacts.put(reasons_key(state.room_id), REASONS.dump_json(failure.reasons))
    record = SentBack(attempt=state.regeneration_count, stage=failure.gate, messages=failure.messages)
    state = state.model_copy(update={"sent_back": [*state.sent_back, record]})
    if state.regeneration_count < state.regen_max:
        return state.model_copy(update={"regeneration_count": state.regeneration_count + 1})
    return state.model_copy(update={"status": "needs_recapture", "stage": error.stage, "error": error})


def riddler_prompt(state: JobState, view: RoomView, artifacts: ArtifactStore) -> RiddlerPrompt:
    """The authoring prompt on attempt 0; after that, the regeneration variant over the last failed attempt's reasons only."""
    if state.regeneration_count == 0:
        return build_author_prompt(view)
    return build_regeneration_prompt(view, read_reasons(view.id, artifacts))
