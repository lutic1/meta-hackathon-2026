"""The author and validate stages (AD-7, AD-12, AD-16, AD-18): one Riddler call, its draft mapped, then the Validator.

`run_author` builds the 2.19 prompt over the stored Interactables alone (a
`RoomView` with no Puzzle, AD-3), the regeneration variant over the last
failed attempt's reasons after the first attempt (`regenerate.py`), and
makes one `chat` call through the `riddler` role's port at reasoning
`medium`, with `attempt` set to the
job's Regeneration count, so the AD-6 cache never serves an earlier
attempt's answer, and the job id and `author` stage tagging its ledger entry,
so provenance sums its spend. It records one call row from the call's
receipt: its `call_` id, host, cached or billed, and spend. The reply is parsed into the
response schema and kept as a `RoomDraft` under `<room_id>/draft.json`.
Every `ix_` reference is then matched exactly against the stored ids,
never by label, and every `p1`..`p6` key, `requires` included, becomes a
fresh `pz_` ULID (AD-18); the mapped Puzzles go to `<room_id>/puzzles.json`.
Output that fails the response schema or the exact-id match is a failed
attempt with a fixed reason (A-24), before `validate` runs.

`run_validate` runs `validate` on every mapped draft, over a Room assembled
from the stored photos, Interactables and Puzzles with its provenance, and
records one verdict per rule in job state; a draft with fewer than 4 or more
than 6 Puzzles never passes. It writes no `room` artifact either way: the
scene stage writes it, once (AD-12).

A failed attempt raises `ValidationError` with its fixed messages, which
quote no solution token or answer, and the Validator's structured reasons.
The regeneration loop records it as one `SentBack` list and either has the
Riddler write another attempt or ends the job, so a draft never ends a
Build `failed`. The Riddler's 45 s budget (`budgets.md`) is measured by the
runner's stage timing, never enforced.
"""

from __future__ import annotations

import hashlib
from collections.abc import Collection, Iterable
from datetime import UTC, datetime

import pydantic
from pydantic import TypeAdapter

from src.council import architect as architect_prompt
from src.council.riddler import PUZZLE_KEYS, build_author_prompt
from src.domain.ledger import LedgerEntry, fold
from src.domain.schema import (
    CallRow,
    FindSolution,
    Interactable,
    InteractableView,
    JobState,
    Model,
    OrderSolution,
    Provenance,
    Puzzle,
    PuzzleDraft,
    Role,
    Room,
    RoomDraft,
    RoomId,
    RoomView,
    RuleVerdict,
    Stage,
    UseOnSolution,
    ValidatorResult,
)
from src.domain.validator import BUILD_RULES, RULES, validate
from src.pipeline.build import StageFn, StageResult, new_id
from src.pipeline.ingest import read_photos
from src.pipeline.ports import ArtifactStore, LedgerStore
from src.pipeline.regenerate import FailedAttempt, riddler_prompt
from src.pipeline.segment import read_interactables
from src.providers.base import ChatResponse, ModelProvider

RIDDLER_BUDGET_MS = 45_000
"""`budgets.md`: the Riddler's 45 s, measured through the stage timing, never enforced."""
DRAFT_FILE = "draft.json"
"""The stage artifact under `<room_id>/`: the Riddler's output as a `RoomDraft`, keyed `p1`..`p6`."""
PUZZLES_FILE = "puzzles.json"
"""The stage artifact under `<room_id>/`: the mapped Puzzles, `pz_` ids minted, for the validate stage."""
PUZZLES = TypeAdapter(list[Puzzle])
PUZZLE_COUNT = range(4, 7)
"""A Room holds four to six Puzzles. The response schema already requires `p1`..`p4` and allows only `p5`
and `p6` beyond them, so the count check in `run_validate` is defence for stored Puzzles that bypassed it."""
STAGE_ROLES: dict[Stage, Role] = {"architect": "architect", "author": "riddler", "dryrun": "dryrun"}
"""The council role whose model a stage record names, for `Provenance.model_ids`."""

SHAPE_MESSAGE = "The draft did not follow the response shape."
ID_MESSAGE = "A puzzle named an object by something other than its exact id."
"""The fixed reasons of an unreadable draft (A-24); neither quotes the draft."""
COUNT_MESSAGE = "A room needs four to six puzzles."


class DraftRefused(Exception):
    """A Riddler reply that fails the response schema or the exact-id match; the message is a fixed reason (A-24)."""


class ValidationError(FailedAttempt):
    """A draft the author stage could not read (A-24) or the Validator refused (AD-13), for the regeneration loop.

    It never ends a Build `failed`: the stage's record, call rows and
    verdicts are kept, and the loop decides what follows.
    """

    gate = "validate"


def draft_key(room_id: RoomId) -> str:
    return f"{room_id}/{DRAFT_FILE}"


def puzzles_key(room_id: RoomId) -> str:
    return f"{room_id}/{PUZZLES_FILE}"


def read_draft(room_id: RoomId, artifacts: ArtifactStore) -> RoomDraft:
    """The `RoomDraft` the author stage stored for `room_id`."""
    return RoomDraft.model_validate_json(artifacts.read(draft_key(room_id)))


def read_puzzles(room_id: RoomId, artifacts: ArtifactStore) -> list[Puzzle]:
    """The mapped Puzzles the author stage stored for `room_id`, for the validate and later stages."""
    return PUZZLES.validate_json(artifacts.read(puzzles_key(room_id)))


# --- The Riddler's draft: parse, exact ids, `pz_` ids ----------------------


def prompt_view(room_id: RoomId, interactables: Iterable[Interactable]) -> RoomView:
    """The prompt shape before any Puzzle exists: each Interactable's `id`, `label`, `attributes`, `instances` and `photo`."""
    fields = set(InteractableView.model_fields)
    return RoomView(
        id=room_id,
        interactables=[InteractableView.model_validate(ix.model_dump(include=fields)) for ix in interactables],
        puzzles=[],
    )


def parse_draft(text: str, response_schema: type[Model]) -> RoomDraft:
    """The reply as a `RoomDraft` in key order; `DraftRefused` when it fails the response schema.

    The only pattern-checked strings in the schema are `ix_` ids, so a reply
    whose every error is a pattern mismatch named an object by a label or a
    malformed id: the id-parsing reason. Anything else is the shape reason.
    """
    try:
        response = response_schema.model_validate_json(text)
    except pydantic.ValidationError as exc:
        ids_only = all(error["type"] == "string_pattern_mismatch" for error in exc.errors())
        raise DraftRefused(ID_MESSAGE if ids_only else SHAPE_MESSAGE) from None
    puzzles = [
        PuzzleDraft.model_validate({"key": key, **puzzle.model_dump()})
        for key in PUZZLE_KEYS
        if (puzzle := getattr(response, key)) is not None
    ]
    return RoomDraft(puzzles=puzzles)


def _references(puzzle: PuzzleDraft) -> list[str]:
    """Every `ix_` id the puzzle names: its evidence and its solution's objects."""
    solution = puzzle.solution
    if isinstance(solution, OrderSolution):
        named = list(solution.interactables)
    elif isinstance(solution, UseOnSolution):
        named = [solution.item, solution.target]
    elif isinstance(solution, FindSolution):
        named = [solution.target]
    else:
        named = []
    return [puzzle.evidence.interactable, *named]


def map_draft(draft: RoomDraft, interactable_ids: Collection[str]) -> list[Puzzle]:
    """The draft's Puzzles with `pz_` ids; `DraftRefused` when any `ix_` reference is not exactly a stored id.

    Every key `p1`..`p6` gets a fresh `pz_` ULID, so a `requires` naming a key
    with no Puzzle maps to an id no Puzzle has, which rule 2 refuses.
    """
    if any(ix_id not in interactable_ids for puzzle in draft.puzzles for ix_id in _references(puzzle)):
        raise DraftRefused(ID_MESSAGE)
    ids = {key: new_id("pz") for key in PUZZLE_KEYS}
    return [
        Puzzle.model_validate({
            **puzzle.model_dump(exclude={"key"}),
            "id": ids[puzzle.key],
            "requires": [ids[key] for key in puzzle.requires],
        })
        for puzzle in draft.puzzles
    ]


# --- Provenance (AD-16) and verdicts ----------------------------------------


def prompt_hashes(view: RoomView) -> dict[Role, str]:
    """sha256 of each fixed prefix the Build sent: the Architect's instructions and the Riddler's system message."""
    riddler = build_author_prompt(view).system
    return {"architect": architect_prompt.prompt_hash(), "riddler": hashlib.sha256(riddler.encode()).hexdigest()}


def assemble_provenance(state: JobState, entries: Iterable[LedgerEntry], hashes: dict[Role, str]) -> Provenance:
    """Model ids from the stage records, the prompt hashes, summed stage timings, the Regeneration count and spend per stage.

    Spend per stage sums this job's ledger entries by the stage they name,
    each `call_` id once; `applied_edits` is empty on a build Room.
    """
    timings: dict[Stage, int] = {}
    for record in state.stages:
        timings[record.stage] = timings.get(record.stage, 0) + record.duration_ms
    model_ids = {STAGE_ROLES[r.stage]: r.model for r in state.stages if r.stage in STAGE_ROLES and r.model is not None}
    spend = dict.fromkeys(timings, 0.0)
    for entry in fold(entries):
        if entry.job_id == state.id and entry.stage is not None:
            spend[entry.stage] = spend.get(entry.stage, 0.0) + entry.usd
    return Provenance(
        model_ids=model_ids,
        prompt_hashes=hashes,
        stage_timings_ms=timings,
        regeneration_count=state.regeneration_count,
        spend_per_stage_usd=spend,
        applied_edits=[],
    )


def rule_verdicts(result: ValidatorResult) -> list[RuleVerdict]:
    """One verdict per build rule in the Validator table, by its check-phrased name."""
    failing = {reason.rule for reason in result.reasons}
    return [RuleVerdict(rule=number, name=RULES[number].name, passed=number not in failing) for number in BUILD_RULES]


# --- The stages ------------------------------------------------------------


def _room_id(state: JobState) -> RoomId:
    if state.room_id is None:
        raise ValueError(f"{state.id} names no room")
    return state.room_id


def _call_row(reply: ChatResponse, provider: ModelProvider) -> CallRow:
    """The `riddler` call row from the call's receipt; the mock has none, so its row is unbilled on the mock host."""
    receipt = reply.receipt
    if receipt is None:
        return CallRow(id=new_id("call"), role="riddler", model=reply.model, host=provider.name, cached=False, spend_usd=0.0)
    return CallRow(
        id=receipt.call_id,
        role="riddler",
        model=reply.model,
        host=receipt.host,
        cached=receipt.cached,
        spend_usd=receipt.spend_usd,
    )


def run_author(state: JobState, *, provider: ModelProvider, artifacts: ArtifactStore) -> StageResult:
    """One Riddler `chat` call at attempt = the Regeneration count; the `RoomDraft` and the mapped Puzzles persisted, one call row."""
    room_id = _room_id(state)
    interactables = read_interactables(room_id, artifacts)
    prompt = riddler_prompt(state, prompt_view(room_id, interactables), artifacts)
    reply = provider.chat(
        prompt.messages(),
        response_schema=prompt.response_schema,
        reasoning_effort=prompt.reasoning_effort,
        attempt=state.regeneration_count,
        job_id=state.id,
        stage="author",
    )
    row = _call_row(reply, provider)
    try:
        draft = parse_draft(reply.text, prompt.response_schema)
        artifacts.put(draft_key(room_id), draft.model_dump_json().encode())
        puzzles = map_draft(draft, {ix.id for ix in interactables})
    except DraftRefused as exc:
        raise ValidationError([str(exc)], StageResult(model=reply.model, calls=[row])) from None
    artifacts.put(puzzles_key(room_id), PUZZLES.dump_json(puzzles))
    return StageResult(count=len(puzzles), model=reply.model, calls=[row])


def run_validate(state: JobState, *, artifacts: ArtifactStore, ledger: LedgerStore) -> StageResult:
    """`validate` on the mapped draft, its per-rule verdicts recorded; a fail raises `ValidationError`, and no `room` artifact is written."""
    room_id = _room_id(state)
    interactables = read_interactables(room_id, artifacts)
    puzzles = read_puzzles(room_id, artifacts)
    room = Room(
        id=room_id,
        created=datetime.now(UTC),
        photos=read_photos(room_id, artifacts),
        interactables=interactables,
        puzzles=puzzles,
        provenance=assemble_provenance(state, ledger.entries(), prompt_hashes(prompt_view(room_id, interactables))),
    )
    result = validate(room)
    stage_result = StageResult(validator=rule_verdicts(result))
    messages = list(dict.fromkeys(reason.message for reason in result.reasons))
    if len(puzzles) not in PUZZLE_COUNT:
        messages.insert(0, COUNT_MESSAGE)
    if messages:
        raise ValidationError(messages, stage_result, result.reasons)
    return stage_result


def author_stage(provider: ModelProvider, artifacts: ArtifactStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `author`, over the `riddler` role's provider."""
    return lambda state: run_author(state, provider=provider, artifacts=artifacts)


def validate_stage(artifacts: ArtifactStore, ledger: LedgerStore) -> StageFn:
    """The `StageFn` wiring hands the runner for `validate`."""
    return lambda state: run_validate(state, artifacts=artifacts, ledger=ledger)
