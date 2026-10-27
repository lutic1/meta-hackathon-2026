"""Schema v1: the one data shape (AD-2), frozen Mon Oct 26.

Every model the HTTP API accepts or returns, the job artifacts and the
session log share is declared here once; `web/types` is generated from
`GET /schema`. Later changes go through bmad-correct-course only.

Ids are prefixed ULIDs minted by server code (AD-18). Pixel coordinates
are in the space of the stored downscaled 1280 px JPEG unless a field
says otherwise; session time is `t_ms`, milliseconds on the session clock.
This module imports only the standard library and pydantic (AD-1).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# --- Ids and scalars -------------------------------------------------------

ULID = "[0-9A-HJKMNP-TV-Z]{26}"

RoomId = Annotated[str, StringConstraints(pattern=f"^room_{ULID}$")]
JobId = Annotated[str, StringConstraints(pattern=f"^job_{ULID}$")]
SessionId = Annotated[str, StringConstraints(pattern=f"^sess_{ULID}$")]
PuzzleId = Annotated[str, StringConstraints(pattern=f"^pz_{ULID}$")]
InteractableId = Annotated[str, StringConstraints(pattern=f"^ix_{ULID}$")]
EditId = Annotated[str, StringConstraints(pattern=f"^te_{ULID}$")]
CallId = Annotated[str, StringConstraints(pattern=f"^call_{ULID}$")]

Sha256 = Annotated[str, StringConstraints(pattern="^[0-9a-f]{64}$")]

Point = tuple[float, float]
Polygon = list[Point]
Box = tuple[float, float, float, float]
"""`[x0, y0, x1, y1]` in frame pixels."""
GridCoord = Annotated[int, Field(ge=0, le=1000)]
GridBox = tuple[GridCoord, GridCoord, GridCoord, GridCoord]
"""`[x0, y0, x1, y1]` on the vision call's 0 to 1000 grid."""

LockType = Literal["code", "order", "use_on", "find"]
RungName = Literal["nudge", "direction", "near_answer"]
RungLevel = Annotated[int, Field(ge=0, le=3)]
EditType = Literal["decoy", "merge", "loosen", "shortcut"]
Stage = Literal["ingest", "architect", "segment", "author", "validate", "dryrun", "scene"]
Role = Literal["architect", "riddler", "dryrun", "trickster", "image"]
JobStatus = Literal["queued", "running", "done", "failed", "needs_more_photos", "needs_recapture"]
OrdinalKey = Literal["p1", "p2", "p3", "p4", "p5", "p6"]
"""The Riddler's puzzle keys, mapped to `pz_` ids by the author stage (AD-18)."""
Milliseconds = Annotated[int, Field(ge=0)]


class Model(BaseModel):
    """Every Schema v1 model: snake_case keys, no unknown field."""

    model_config = ConfigDict(extra="forbid")


# --- Room ------------------------------------------------------------------


class Photo(Model):
    hash: Sha256
    """sha256 of the stored downscaled JPEG bytes; every call, cache key and mask uses those bytes."""
    size: Annotated[int, Field(ge=0)]
    """Byte size of the stored downscaled JPEG."""
    downscaled_path: str
    original_path: str


class Placement(Model):
    """Tier 2 object pose in original-photo pixels (fal metadata, else hand-placed)."""

    translation: tuple[float, float, float]
    rotation: tuple[float, float, float]
    scale: tuple[float, float, float]


class Tier2(Model):
    glb_path: str
    placement: Placement


class Interactable(Model):
    id: InteractableId
    label: str
    photo: Annotated[int, Field(ge=0)]
    """Index into `Room.photos[]` in upload order."""
    box: Box
    polygons: list[Polygon] | None
    """One polygon per instance; null only before the segment stage completes."""
    instances: Annotated[int, Field(ge=1)]
    attributes: list[str]
    tier2: Tier2 | None = None


class CodeSolution(Model):
    lock_type: Literal["code"]
    code: str


class OrderSolution(Model):
    lock_type: Literal["order"]
    interactables: list[InteractableId]


class UseOnSolution(Model):
    lock_type: Literal["use_on"]
    item: InteractableId
    target: InteractableId


class FindSolution(Model):
    lock_type: Literal["find"]
    target: InteractableId


Solution = Annotated[
    CodeSolution | OrderSolution | UseOnSolution | FindSolution, Field(discriminator="lock_type")
]


class Evidence(Model):
    interactable: InteractableId
    visible_attribute: str


class Rungs(Model):
    nudge: str
    direction: str
    near_answer: str


class Puzzle(Model):
    id: PuzzleId
    lock_type: LockType
    requires: list[PuzzleId]
    solution: Solution
    evidence: Evidence
    clue: str
    lore: str
    rungs: Rungs
    is_exit: bool

    @model_validator(mode="after")
    def _solution_matches_lock_type(self) -> Puzzle:
        if self.solution.lock_type != self.lock_type:
            raise ValueError(f"solution is {self.solution.lock_type!r}, lock_type is {self.lock_type!r}")
        return self


class Decoy(Model):
    """An accepted `decoy` edit folded into a session's effective Room (option A, Oct 22)."""

    id: EditId
    puzzle: PuzzleId
    interactable: InteractableId
    visible_attribute: str


class Provenance(Model):
    model_ids: dict[Role, str]
    prompt_hashes: dict[Role, str]
    stage_timings_ms: dict[Stage, Milliseconds]
    regeneration_count: Annotated[int, Field(ge=0)]
    spend_per_stage_usd: dict[Stage, Annotated[float, Field(ge=0)]]
    applied_edits: list[EditId] = Field(default_factory=list)
    """Ids of accepted Trickster edits folded into a session's effective Room; empty on the stored build Room."""


class Room(Model):
    id: RoomId
    created: datetime
    name: str | None = Field(default=None, max_length=40)
    """Set when a Demo room is seeded; absent on ordinary Builds."""
    photos: list[Photo]
    interactables: list[Interactable]
    puzzles: list[Puzzle]
    decoys: list[Decoy] = Field(default_factory=list)
    """Empty on the stored build Room; written only by `apply_edit`."""
    provenance: Provenance


# --- Model-response schemas: no map-typed field (AD-2) ---------------------


class ArchitectCandidate(Model):
    label: str
    plural: bool
    """Whether the label names several like objects (read by mask selection)."""
    photo: Annotated[int, Field(ge=0)]
    """The clearest photo index."""
    box: GridBox
    attributes: list[str]
    confidence: Annotated[float, Field(ge=0, le=1)]


class ArchitectResponse(Model):
    """Correlated by list position; `ix_` ids are minted later by the segment stage (AD-18)."""

    candidates: list[ArchitectCandidate]


class PuzzleDraft(Model):
    key: OrdinalKey
    lock_type: LockType
    requires: list[OrdinalKey]
    solution: Solution
    evidence: Evidence
    clue: str
    lore: str
    rungs: Rungs
    is_exit: bool

    @model_validator(mode="after")
    def _solution_matches_lock_type(self) -> PuzzleDraft:
        if self.solution.lock_type != self.lock_type:
            raise ValueError(f"solution is {self.solution.lock_type!r}, lock_type is {self.lock_type!r}")
        return self


class RoomDraft(Model):
    """The Riddler's raw output, kept for provenance (AD-7)."""

    puzzles: list[PuzzleDraft]


class DryRunAnswer(Model):
    puzzle_id: PuzzleId
    answer: Solution


class DryRunAnswers(Model):
    """A list, never a map keyed by puzzle id (AD-12)."""

    answers: list[DryRunAnswer]


# --- Trickster edits and cards ---------------------------------------------


class DecoyPayload(Model):
    type: Literal["decoy"]
    interactable: InteractableId
    visible_attribute: str


class MergePayload(Model):
    """Makes `puzzle_b` require `puzzle_a`."""

    type: Literal["merge"]
    puzzle_a: PuzzleId
    puzzle_b: PuzzleId


class LoosenPayload(Model):
    type: Literal["loosen"]
    puzzle: PuzzleId
    rung: RungName


class ShortcutPayload(Model):
    """Removes the `requires` edge from `puzzle` to `requires`."""

    type: Literal["shortcut"]
    puzzle: PuzzleId
    requires: PuzzleId


Payload = Annotated[
    DecoyPayload | MergePayload | LoosenPayload | ShortcutPayload, Field(discriminator="type")
]


class ValidatorReason(Model):
    """Structured and token-free: the rule, the puzzle, the field and the rule's fixed message (AD-3)."""

    rule: Annotated[int, Field(ge=1)]
    puzzle_id: PuzzleId | None
    field: str
    message: str


class ValidatorResult(Model):
    ok: bool
    reasons: list[ValidatorReason]


class TricksterEdit(Model):
    """Lives in the session log only (AD-12); never returned by a route (AD-3)."""

    id: EditId
    type: EditType
    puzzle: PuzzleId
    payload: Payload
    validator_result: ValidatorResult
    accepted: bool
    window: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def _payload_matches_type(self) -> TricksterEdit:
        if self.payload.type != self.type:
            raise ValueError(f"payload is {self.payload.type!r}, type is {self.type!r}")
        return self


CardReason = Annotated[int, Field(ge=1)] | Literal["provider_unavailable"] | None
"""Null on an accepted card, `provider_unavailable` on a skipped card, the failing rule on a rejected card."""


class TricksterCard(Model):
    """The public card projection, `to_card_view(event)`: no payload or content field (AD-3)."""

    edit_id: EditId | None
    accepted: bool
    edit_type: EditType | None
    puzzle_id: PuzzleId | None
    """The Puzzle the Card names; on a `merge`, the one that now waits (`puzzle_b`), whichever the proposal named."""
    related_puzzle_id: PuzzleId | None
    """The second Puzzle of a `merge` or `shortcut`, else null."""
    room_revision: Annotated[int, Field(ge=0)]
    reason: CardReason
    message: str | None
    """The Validator's fixed message on a rejected card, else null."""
    t_ms: Milliseconds


# --- Events (AD-4) ---------------------------------------------------------


class CodeInput(Model):
    type: Literal["code"]
    puzzle_id: PuzzleId
    code: str


class UseOnInput(Model):
    """No `puzzle_id`: the server resolves the puzzle from the pair."""

    type: Literal["use_on"]
    item: InteractableId
    target: InteractableId


class OrderStartInput(Model):
    type: Literal["order_start"]
    puzzle_id: PuzzleId


class OrderStopInput(Model):
    type: Literal["order_stop"]
    puzzle_id: PuzzleId


LockInput = Annotated[
    CodeInput | UseOnInput | OrderStartInput | OrderStopInput, Field(discriminator="type")
]


class ClickBody(Model):
    """Client-posted; `t_ms` is stamped by the API at append."""

    type: Literal["click"]
    interactable_id: InteractableId


class LockInputBody(Model):
    type: Literal["lock_input"]
    input: LockInput


class HintRequestBody(Model):
    """`puzzle_id` is always omitted by the client and resolved to the Active puzzle."""

    type: Literal["hint_request"]
    puzzle_id: PuzzleId | None = None


PostedEvent = Annotated[ClickBody | LockInputBody | HintRequestBody, Field(discriminator="type")]


class ClickEvent(ClickBody):
    t_ms: Milliseconds


class LockInputEvent(LockInputBody):
    t_ms: Milliseconds


class HintRequestEvent(HintRequestBody):
    t_ms: Milliseconds


class IdleTickEvent(Model):
    type: Literal["idle_tick"]
    t_ms: Milliseconds


class OpeningLineEvent(Model):
    type: Literal["opening_line"]
    kind: Literal["greeting", "welcome"]
    text: str
    t_ms: Milliseconds


class TricksterCardEvent(Model):
    """Stored server-side only, with the full edit for the AD-12 fold; the client sees `TricksterCard`."""

    type: Literal["trickster_card"]
    edit_id: EditId | None
    edit: TricksterEdit | None
    """Null on a skipped card."""
    puzzle_id: PuzzleId | None
    accepted: bool
    reason: CardReason
    room_revision: Annotated[int, Field(ge=0)]
    t_ms: Milliseconds


class RungChangeEvent(Model):
    type: Literal["rung_change"]
    puzzle_id: PuzzleId
    rung: Annotated[int, Field(ge=1, le=3)]
    triggered_by: list[Annotated[int, Field(ge=0)]]
    """Positions in the session log of the events that triggered it."""
    phrased: bool
    phrasing_ms: Milliseconds | None
    text: str
    """The line exactly as shown."""
    t_ms: Milliseconds


Event = Annotated[
    ClickEvent
    | LockInputEvent
    | HintRequestEvent
    | IdleTickEvent
    | OpeningLineEvent
    | TricksterCardEvent
    | RungChangeEvent,
    Field(discriminator="type"),
]


# --- Redacted views (AD-3) -------------------------------------------------


class InteractableView(Model):
    id: InteractableId
    label: str
    attributes: list[str]
    instances: Annotated[int, Field(ge=1)]
    photo: Annotated[int, Field(ge=0)]


class PuzzleView(Model):
    id: PuzzleId
    lock_type: LockType
    requires: list[PuzzleId]
    is_exit: bool
    clue: str
    lore: str
    rungs: Rungs


class RoomView(Model):
    """The only type a prompt builder accepts."""

    id: RoomId
    interactables: list[InteractableView]
    puzzles: list[PuzzleView]


class PhotoView(Model):
    hash: Sha256
    size: Annotated[int, Field(ge=0)]


class PlayInteractable(Model):
    id: InteractableId
    label: str
    photo: Annotated[int, Field(ge=0)]
    polygons: list[Polygon] | None
    instances: Annotated[int, Field(ge=1)]
    attributes: list[str]
    tier2: Tier2 | None = None


class PlayPuzzle(Model):
    """No solution and no Rung text; Rung text reaches the client only in hint replies and `rung_changes[]`."""

    id: PuzzleId
    lock_type: LockType
    requires: list[PuzzleId]
    is_exit: bool
    clue: str
    lore: str
    evidence_cards: list[Evidence]
    """Real evidence and any decoys merged in a stable order; nothing marks a card as a decoy."""
    sequence_length: Annotated[int, Field(ge=1)] | None
    """An `order` Puzzle's number of positions, one pip each (UX-DR35), never its objects; null for other lock types."""


class PlayView(Model):
    """The client shape."""

    id: RoomId
    created: datetime
    name: str | None = Field(default=None, max_length=40)
    photos: list[PhotoView]
    interactables: list[PlayInteractable]
    puzzles: list[PlayPuzzle]


# --- Job state (AD-7) and the Build view (AD-3) ----------------------------


class StageRecord(Model):
    stage: Stage
    duration_ms: Milliseconds
    count: Annotated[int, Field(ge=0)] | None = None
    """The done-row count: objects found or outlined, puzzles written or tried."""
    model: str | None = None


class SentBack(Model):
    """The fixed messages that sent back one failed attempt."""

    attempt: Annotated[int, Field(ge=0)]
    stage: Literal["validate", "dryrun"]
    messages: list[str]


class CallRow(Model):
    id: CallId
    role: Role
    model: str
    host: str
    cached: bool
    spend_usd: Annotated[float, Field(ge=0)]


class RuleVerdict(Model):
    rule: Annotated[int, Field(ge=1)]
    name: str
    """The check-phrased name from the Validator table."""
    passed: bool


class DryRunVerdict(Model):
    puzzle_id: PuzzleId
    verdict: Literal["pass", "fail", "skipped"]


class MaskPreview(Model):
    """Solution-free, served once the segment stage completes."""

    id: InteractableId
    label: str
    photo: Annotated[int, Field(ge=0)]
    polygons: list[Polygon]


class ErrorDetail(Model):
    code: str
    message: str
    stage: Stage | None
    status: JobStatus | None = Field(default=None, exclude_if=lambda status: status is None)
    """The job status, set only when `code` is `build_not_ready` (AD-13) and left out of every other answer."""

    @model_validator(mode="after")
    def _status_only_when_not_ready(self) -> ErrorDetail:
        if self.status is not None and self.code != "build_not_ready":
            raise ValueError("status is set only on build_not_ready")
        return self


class JobState(Model):
    id: JobId
    status: JobStatus
    stage: Stage | None = None
    """The stage in progress while `running`; the failing stage when `failed`."""
    room_id: RoomId | None = None
    stages: list[StageRecord] = Field(default_factory=list)
    regeneration_count: Annotated[int, Field(ge=0)] = 0
    regen_max: Annotated[int, Field(ge=0)]
    validator: list[RuleVerdict] = Field(default_factory=list)
    dry_run: list[DryRunVerdict] = Field(default_factory=list)
    sent_back: list[SentBack] = Field(default_factory=list)
    calls: list[CallRow] = Field(default_factory=list)
    build_time_ms: Milliseconds | None = None
    mask_preview: list[MaskPreview] = Field(default_factory=list)
    error: ErrorDetail | None = None

    @model_validator(mode="after")
    def _running_has_a_stage(self) -> JobState:
        if self.status == "running" and self.stage is None:
            raise ValueError("a running job names its stage")
        return self


class MaskOverlay(Model):
    interactable_id: InteractableId
    label: str
    polygons: list[Polygon]


class PhotoMasks(Model):
    photo: Annotated[int, Field(ge=0)]
    masks: list[MaskOverlay]


class PuzzleNode(Model):
    id: PuzzleId
    lock_type: LockType
    requires: list[PuzzleId]
    is_exit: bool


class ModelRow(Model):
    role: Role
    model: str
    host: str
    cached: Annotated[int, Field(ge=0)]
    billed: Annotated[int, Field(ge=0)]
    summary: str
    """The provenance count, such as "found 9 objects"."""


class BuildView(Model):
    """`to_build_view(room, job)`: never a solution, a dry-run answer or a clue-to-answer pairing."""

    room_id: RoomId
    job_id: JobId
    name: str | None = Field(default=None, max_length=40)
    built_at: datetime
    build_time_ms: Milliseconds
    photos: list[PhotoMasks]
    puzzles: list[PuzzleNode]
    validator: list[RuleVerdict]
    dry_run: list[DryRunVerdict]
    regeneration_count: Annotated[int, Field(ge=0)]
    regen_max: Annotated[int, Field(ge=0)]
    sent_back: list[SentBack]
    models: list[ModelRow]
    calls: list[CallRow]
    disclosure: list[str]


# --- Session state (AD-4) --------------------------------------------------


class OpeningLine(Model):
    kind: Literal["greeting", "welcome"]
    text: str | None
    """Null while `phrasing` is true."""


class OrderBuffer(Model):
    """Armed only while `puzzle_id` is the Active puzzle; clicks are the buffer."""

    puzzle_id: PuzzleId | None = None
    clicks: list[InteractableId] = Field(default_factory=list)


class TricksterWindow(Model):
    state: Literal["closed", "open", "pending"]
    index: Annotated[int, Field(ge=0)] | None = None
    """The open window's index, counted from 0 per session; null while closed."""


class Thresholds(Model):
    """The effective nudge threshold and Rung spacing, their 1x values and the threshold's source."""

    nudge_threshold_ms: Milliseconds
    nudge_threshold_base_ms: Milliseconds
    rung_spacing_ms: Milliseconds
    rung_spacing_base_ms: Milliseconds
    source: Literal["derived", "fresh"]


class TriggerEvent(Model):
    """One log event a `rung_change` names in `triggered_by`: its type and `t_ms`, never its payload (AD-3)."""

    type: Literal["click", "lock_input", "hint_request", "idle_tick", "opening_line", "trickster_card", "rung_change"]
    t_ms: Milliseconds


class HintReply(Model):
    """The answer to a `hint_request`: the current Rung through the Guide port, or the No-hint line at `rung` 0."""

    puzzle_id: PuzzleId | None
    """The Puzzle the request was answered for; null once the Exit has opened."""
    rung: RungLevel
    text: str
    """The line exactly as shown."""


class SessionState(Model):
    """Replayed from the log; carries `cards`, never an edit or the event log."""

    id: SessionId
    room_id: RoomId
    locks_open: list[PuzzleId]
    inventory: list[InteractableId]
    current_rung: dict[PuzzleId, RungLevel]
    wrong_attempts: dict[PuzzleId, Annotated[int, Field(ge=0)]]
    rungs_used: Annotated[int, Field(ge=0)]
    order_buffer: OrderBuffer
    active_puzzle_id: PuzzleId | None
    """Null only when no Puzzle is available."""
    opening_line: OpeningLine | None
    phrasing: bool
    rung_changes: list[RungChangeEvent]
    trickster_window: TricksterWindow
    trickster_calls: Annotated[int, Field(ge=0, le=6)]
    cards: list[TricksterCard]
    room_revision: Annotated[int, Field(ge=0)]
    disclosure: list[str]
    judge_room: bool = False
    thresholds: Thresholds | None = None
    trigger_events: dict[int, TriggerEvent] = Field(default_factory=dict)
    """Each log event a `rung_changes[]` entry names in `triggered_by`, by its log position, for the Triggers panel;
    served on top of the replayed state (`trigger_events` in the API), never written by `apply`."""
    hint_reply: HintReply | None = None
    """Set only on the reply to the `hint_request` it answers; never replayed."""


# --- Profile (AD-8) --------------------------------------------------------


class Derived(Model):
    sessions: Annotated[int, Field(ge=0)]
    persistence: Annotated[float, Field(ge=-1, le=1)]
    time_to_first_hint_s: Annotated[float, Field(ge=0)] | None
    mean_rung_per_lock_type: dict[LockType, Annotated[float, Field(ge=0, le=3)]]

    @classmethod
    def fresh(cls) -> Derived:
        return cls(sessions=0, persistence=0, time_to_first_hint_s=None, mean_rung_per_lock_type={})


class PuzzleResult(Model):
    puzzle_id: PuzzleId
    lock_type: LockType
    attempts: Annotated[int, Field(ge=0)]
    wrong_attempts: Annotated[int, Field(ge=0)]
    rungs_used: RungLevel
    time_to_first_hint: Milliseconds | None
    solved: bool
    time_spent_ms: Milliseconds
    nudge_fired: bool
    hint_requested: bool
    early_ask: bool
    """A hint request made with no Rung open (the A-19 inputs are these three flags)."""


class RoomResult(Model):
    room_id: RoomId
    demo: bool
    elapsed_ms: Milliseconds
    rungs_used: Annotated[int, Field(ge=0)]
    wrong_attempts: Annotated[int, Field(ge=0)]
    puzzles: list[PuzzleResult]


class Profile(Model):
    """The player profile as a whole: every `RoomResult` keyed by its `room_id`, plus the `Derived` block.

    The browser owns it (AD-8); under cut 2 only, `GET|PUT /profile/<name>`
    reads and writes it as `rooms/profiles/<name>.json` in Local mode.
    """

    results: dict[RoomId, RoomResult]
    derived: Derived

    @model_validator(mode="after")
    def _results_keyed_by_room_id(self) -> Profile:
        for room_id, result in self.results.items():
            if result.room_id != room_id:
                raise ValueError(f"results[{room_id!r}] is the result of {result.room_id!r}")
        return self


class SessionStart(Model):
    """`POST /sessions`; hosted clients always send `Derived.fresh()`."""

    room_id: RoomId
    derived: Derived = Field(default_factory=Derived.fresh)


# --- Status, listing, access and errors ------------------------------------


class GuideModel(Model):
    id: str
    host: str


class Meta(Model):
    mode: Literal["local", "hosted"]
    guide: Literal["ollama", "verbatim"]
    guide_model: GuideModel | None
    trickster: Literal["live", "scripted", "cut1"]
    demo_timescale: Annotated[int, Field(ge=1)]
    cache: Literal["on", "off"]
    profile: str
    disclosure: list[str]
    retention: str


class RoomSummary(Model):
    room_id: RoomId
    name: str | None = Field(default=None, max_length=40)
    cover_photo: Annotated[int, Field(ge=0)]
    puzzle_count: Annotated[int, Field(ge=0)]
    job_id: JobId
    built_at: datetime


class AccessCheckRequest(Model):
    code: str


class AccessCheck(Model):
    ok: bool
    builds_left: Annotated[int, Field(ge=0)] | None

    @model_validator(mode="after")
    def _no_count_on_refusal(self) -> AccessCheck:
        if not self.ok and self.builds_left is not None:
            raise ValueError("builds_left is null when ok is false")
        return self


class ErrorEnvelope(Model):
    error: ErrorDetail


API_MODELS: tuple[type[Model], ...] = (
    Room,
    RoomDraft,
    ArchitectResponse,
    DryRunAnswers,
    RoomView,
    PlayView,
    BuildView,
    TricksterEdit,
    TricksterCard,
    JobState,
    SessionState,
    SessionStart,
    RoomResult,
    Derived,
    Profile,
    RoomSummary,
    AccessCheckRequest,
    AccessCheck,
    Meta,
    ErrorEnvelope,
    ClickBody,
    LockInputBody,
    HintRequestBody,
    ClickEvent,
    LockInputEvent,
    HintRequestEvent,
    IdleTickEvent,
    OpeningLineEvent,
    TricksterCardEvent,
    RungChangeEvent,
)
"""Every model `GET /schema` returns (AD-2)."""


# --- Strict response schemas (AD-5) ----------------------------------------


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema with `$defs` inlined, `additionalProperties: false` and every property required."""
    schema = model.model_json_schema()
    defs: dict[str, Any] = schema.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            name = node["$ref"].rsplit("/", 1)[-1]
            return walk({**defs[name], **{k: v for k, v in node.items() if k != "$ref"}})
        out = {k: walk(v) for k, v in node.items() if k not in ("discriminator", "default")}
        if out.get("type") == "object":
            out["additionalProperties"] = False
            out["required"] = list(out.get("properties", {}))
        return out

    return walk(schema)
