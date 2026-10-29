"""The FastAPI app: routes under `/api/` and the built client at `/` (AD-4, AD-9, AD-13).

`create_app(settings)` takes every adapter from `wire` in
`src/api/wiring.py`, which selects them by `MODE` (AD-9), and mounts
`web/dist` at `/` when it exists (one origin, no CORS); without a build the
mount is skipped and the API still serves. The hosted route table is the
local one without the profile routes, and wiring's access guard runs first
on `POST /builds` and `GET /builds/<job_id>/room`. Room routes return `PlayView` and the stored downscaled JPEG bytes, never a
`Room` (AD-3).
The cut-2 profile routes `GET|PUT /profile/<name>` read and write the
`Profile` as `rooms/profiles/<name>.json` on the player's machine (AD-8):
they are the only code that touches `rooms/profiles/`, every other route
sees only the posted `derived`, and the hosted app never registers them.

Session routes are the one server-authoritative play surface (AD-4):
`POST /sessions` starts a session and opens it with its opening line,
`POST /sessions/<id>/events` appends a client event and `GET /sessions/<id>`
replays the state, appending an `idle_tick` when `IDLE_TICK_MS` have passed
since the last event, and `GET /sessions/<id>/result` computes the
`RoomResult` from the log. In Local mode (wiring's `greets`) a Derived
block with `sessions` >= 1 is greeted: the start reply carries
`opening_line {kind: greeting, text: null}` with `phrasing` true, and the Greeting composer (`compose_greeting`) runs off
the request, its phrased line or, on a fallback, the template appended as the
one `opening_line` when it returns, with `phraser_fallback` logged against the
session when the Guide model fell back. Every other start, and every hosted
start whatever block it carries, appends a welcome at once, so its reply
already carries the line with `phrasing` false: the Demo room welcome
(`DEMO_ROOM_WELCOME`) on a Room `ArtifactStore.is_demo_room` names (hosted,
one under `rooms/demo/`; local, none), else the First-room welcome
(`FIRST_ROOM_WELCOME`). The two lines sit side by side here, the only copy
of either text; the client renders what it receives. A reload replays the
one event rather than appending another. The session's `Thresholds` are fixed at the
start from the greeted block, else `Derived.fresh()`: the 1x values from
`src/domain/rungs.py`, divided by `DEMO_TIMESCALE` on the session clock
(AD-10), and so is the Trickster window the machine opens windows against.
Nothing from the Derived block is written to the log; the block
the thresholds came from is kept with the session's transient state, as the
one input beside the Rung text that the Guide port sees. Every append runs
under one lock per session id held in this process (`OpenSessions`), so
events land one after another and each reply carries the state that
includes its own event:
posted events, `idle_tick`s and opening lines have strictly increasing `t_ms`,
and a `rung_change` the state machine selects on an appended event (3.1) is
worded through the injected `HintPhraser` and appended right after it, under
the same lock, sharing that event's `t_ms`, with `phrased`, `phrasing_ms`
(null when not phrased) and the line exactly as shown in `text`.
The event and its `rung_change` are two store writes; should the second fail,
replay still selects the same Rung on that event, so the served state keeps
the Rung (in its verbatim words) and only the log lacks it. The lock and the clock reading at the
session's start are transient request state, never replayed state. What the
start fixes that the log does not hold (the Room, the opening's kind, the 1x
nudge threshold and whether an earlier session existed) is stored once as the
session's `SessionHeader` beside the log, never a Derived field, so a process
that never opened the session (a restart, a new container) reopens it from
the header and the log, its clock resuming at the last event's `t_ms` and its
Derived block `Derived.fresh()`; only an id with no stored header answers 404
`session_not_found`, or 410 `room_deleted` when a deletion record names it. `t_ms` is
stamped from the session clock at append, so a body carrying one is refused.
A `hint_request` is answered on its reply in `hint_reply`: the current Rung
of the Puzzle it resolved to, with `next_hint_ms`, how long until an ask
opens the next one. A Rung the request itself opened (the state machine
opens one at once when none is showing, else once the Rung spacing has
passed) answers in the words its `rung_change` was appended with; a Rung
already open is routed through the `HintPhraser` again. With no Puzzle active
(once the Exit has opened) it answers the fixed `NO_HINT_LINE`, never
phrased. A `puzzle_id` that is not in the Room is a malformed body, refused
with nothing appended. Each
appended event is logged as one JSON line with `session_id`, the event type
and `duration_ms` (AR-22). Every session state served, the greeted start
reply included, carries its Room's Disclosure list, composed once at the
session's start by `disclosure_lines` in `src/api/meta.py` (AD-15): the
global lines, plus the earlier-builds line for a Demo room or a Room whose
job record holds any call served from the Cache, else the labelled replay
line for a Room with a session already started (in this process or stored by
an earlier one); a later session on the same Room never changes an earlier
session's list. Every session state served also carries
`judge_room`, read once at the session's start from
`ArtifactStore.is_judge_room` (hosted, a Room under `rooms/judge/`; local,
never): the client draws the Completion screen's deletion line from that flag
alone (FR-33).

`GET /rooms` lists one `RoomSummary` per stored Room with a job record
through `ArtifactStore.list_rooms()`, newest build first, with `job_id` read
from the job record that names the Room (AD-9); `GET /meta` serves the
`Meta` model, echoing any `?profile=` name the profile routes accept (AD-14),
and `GET /schema` the JSON Schema of every AD-2 model and of the `Event`,
`PostedEvent` and `LockInput` unions under `$defs`, from which `npm run types`
generates `web/types`.

Build routes run the persisted job (AD-7): `POST /builds` first runs the
access guard wiring injects, then reads the multipart body (the i-th
`downscale` part with the i-th `original` part), lets ingest refuse it
before any job exists (422 at stage `ingest` with `photo_count`,
`unsupported_image` or `bad_downscale`), claims a build slot (403
`build_quota_exceeded` once every judge build is used, with no photo
stored), then persists the job `queued`, hands it to the `JobRunner` and
answers 202 with the job state without waiting on a stage. In hosted mode
the guard refuses a missing or wrong `X-Access-Code` with 403
`access_denied` before the body is read, so no job, slot or photo follows
(AD-9). `GET /builds/<job_id>` reads only the persisted
job state, 202 while `queued` or `running` and 200 when terminal, and never a
Room; `GET /builds/<job_id>/room` is the one route a full Room leaves by
(AD-3), behind the same guard (open in Local mode), answering a known job
not yet `done` with 409 `build_not_ready` and the job `status`, never
`room_not_found` (decision 37). Hosted only, `POST /access/check {code}` answers the
`AccessCheck` before any photo is chosen: `{ok: true, builds_left}` read
from the `JobStore` for the right code, 200 `{ok: false, builds_left: null}`
for a wrong one, starting no Build and claiming no slot; `POST /builds`
still checks the code and claims the slot itself. Every attempt on the
guarded routes and the check counts against the per-IP limit first, and
one past it answers 429 `too_many_attempts` with `Retry-After` before the
code is compared (AD-9). `GET /builds/<job_id>/view` serves the
`BuildView` (`to_build_view`) of a `done` job to anyone with the link, never
behind the guard, with its `disclosure` composed by `disclosure_lines` for
the Room and its job record alone, so it states the same build fact a
session does and no session changes it (AD-15, decision record item 72); a known job not yet `done` answers 409
`build_not_ready` with the job `status` in the envelope, and an unknown one
404 (AD-3, AD-13). A room id or job id that a deletion record names
(`ArtifactStore.deleted_room`, hosted under `rooms/deleted/`) answers 410
`room_deleted` on `GET /rooms/<room_id>`, its photos, `POST /sessions` and
the three `/builds/<job_id>` reads, distinct from 404 `room_not_found` or
`job_not_found` for an id no record names (AD-9); the record is read only
after the Room or job is not found. Every session route answers a Session
the deletion took (its id in the record's `session_ids`, or one open in this
process whose stored header is gone) with 410 `room_deleted` too, and an
unknown or swept one with 404 `session_not_found` (decision 58). Every other route is open in both modes. At
startup the local app exports the ledger and restarts every job left
`queued` or `running`; the runner exports again after each Build ends (AD-9).

`POST /sessions/<id>/trickster` runs the configured `TricksterSource`
(wiring's `trickster_source`) inside an open window, under the session lock
(AD-4, AD-12): outside an open window (and opening the Exit closes one still
open, so none follows it) it answers 200 with the unchanged state, no source
call and no event, and a request arriving while the
source runs waits on the lock and is then served the closed window the
first one left, so a window yields at most one source call and one card.
While the source runs the window reads `pending` in the state the session
serves (`OpenSession.pending`, a mark held with the lock, never an event,
so replay is unchanged), and `GET /sessions/<id>` returns that state
without waiting on the lock. The route hands the source the stored Room's
id, the window index, the `RoomView` of the Effective room and the
Game-state summary; it mints the edit's `te_` id, judges the proposal live
with `check_edit` (the bounds, then rules 1 to 9 over `apply_edit`) and
appends one `trickster_card` carrying the full `TricksterEdit`, which
closes the window. A source that yields no proposal (another Room, a
used-up recording, or a proposals file that is missing or fails to load,
which is logged) appends nothing; a `ProviderError` (the live source's
call after the adapter's one retry, or a reply that is no proposal) or
`SpendCapExceeded` appends the skipped card
`{accepted: false, edit_id: null, reason: provider_unavailable}`, never a
rejected card or the error envelope (AD-13). The reply is the session
state, whose `cards` carry only the `TricksterCard` projection (AD-3).
`GET /sessions/<id>/room` serves the `PlayView` of the session's Effective
room, the stored Room with the accepted edits in the log folded in; the
stored Room and `GET /rooms/<room_id>` never change (AD-12).
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from email import policy
from email.parser import BytesParser
from functools import cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError
from pydantic.json_schema import models_json_schema
from starlette.concurrency import run_in_threadpool

from src.api.errors import (
    ApiError,
    BuildNotReady,
    BuildQuotaRefused,
    InvalidProfile,
    InvalidProfileName,
    JobNotFound,
    NotFound,
    PhotoNotFound,
    ProfileNotFound,
    RoomDeleted,
    RoomNotFound,
    SessionNotFound,
    UploadRefused,
    handle_api_error,
    handle_validation_error,
)
from src.api.meta import disclosure_lines, meta
from src.api.wiring import (
    ACCESS_HEADER,
    AccessGuard,
    hint_phraser,
    session_clock,
    trickster_source,
    wire,
)
from src.config import Settings
from src.council.greeting import Greeting, compose_greeting
from src.council.trickster import TricksterProposal, TricksterSource
from src.domain.edits import check_edit, effective_room
from src.domain.ledger import SpendCapExceeded
from src.domain.redact import to_build_view, to_play_view, to_prompt_view
from src.domain.rungs import (
    RUNG_SPACING_MS,
    TRICKSTER_WINDOW_MS,
    ThresholdSource,
    is_returning,
    nudge_threshold_ms,
)
from src.domain.schema import (
    API_MODELS,
    AccessCheck,
    AccessCheckRequest,
    BuildView,
    Derived,
    Event,
    HintReply,
    HintRequestBody,
    IdleTickEvent,
    JobId,
    JobState,
    LockInput,
    Meta,
    Milliseconds,
    OpeningLineEvent,
    PlayView,
    PostedEvent,
    Profile,
    Room,
    RoomId,
    RoomResult,
    RoomSummary,
    RungChangeEvent,
    SessionId,
    SessionStart,
    SessionState,
    Stage,
    Thresholds,
    TricksterCardEvent,
    TricksterEdit,
    TricksterWindow,
    TriggerEvent,
    ValidatorResult,
)
from src.domain.session import SessionHeader, SessionStateMachine, game_state_summary
from src.infra.clocks import SessionClock
from src.infra.local import CACHE_ROOT, EXPORTS_ROOT, LEDGER_PATH, ROOMS_ROOT
from src.infra.modal import ModalHandles, wall_ms
from src.pipeline.build import TERMINAL, Build, StageFn, error_code
from src.pipeline.ingest import IngestRefused, UnsupportedImage, Upload
from src.pipeline.ports import (
    ArtifactStore,
    BuildQuotaExceeded,
    Clock,
    JobRunner,
    JobStore,
    SessionStore,
    photo_key,
    room_key,
)
from src.providers.base import HintPhraser, ProviderError
from src.providers.spend import new_ulid
from src.providers.verbatim import greeting_template

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
"""The Vite build; `vite.config.ts` proxies `/api/*` to uvicorn in development instead."""
PROFILES = "profiles"
"""The profile files, `rooms/profiles/<name>.json`; only the profile routes read or write under it."""

IDLE_TICK_MS = 5000
"""A `GET /sessions/<id>` read appends an `idle_tick` once this long has passed since the last event (AD-4)."""

FIRST_ROOM_WELCOME = "Welcome to your own room. Read a riddle, then click the thing it means."
"""The fixed First-room welcome (A-13, FR-21): the `opening_line` of every session start neither greeted nor on a Demo room, worded here alone."""
DEMO_ROOM_WELCOME = "Welcome to someone else's room. Read a riddle, then click the thing it means."
"""The fixed Demo room welcome (FR-31, UX-DR45): the `opening_line` of every session start on a Demo room, worded here alone."""

NO_HINT_LINE = "A fair ask. Look around a little longer; I'll speak up if you stay stuck."
"""The fixed No-hint line (UX-DR76): the reply to a Hint request while no Rung is open, never phrased."""

EVENT = TypeAdapter(Event)

Spawn = Callable[[Callable[[], None]], None]
"""Runs a task off the request; the Greeting composer runs through it so the start reply never waits on the Guide model."""
Sources = Callable[[], TricksterSource | None]
"""The Trickster source a window asks, as wiring's `trickster_source` resolves it; None while there is none."""

UNCHECKED = ValidatorResult(ok=False, reasons=[])
"""The verdict a minted edit carries until `check_edit` has judged it."""

log = logging.getLogger("keyframe.sessions")


def missing_room(store: ArtifactStore, id_: str) -> RoomDeleted | None:
    """`RoomDeleted` when a deletion record names `id_`, a room id or a job id, else `None` (AD-9)."""
    room_id = store.deleted_room(id_)
    return None if room_id is None else RoomDeleted(room_id)


def load_room(store: ArtifactStore, room_id: str) -> Room:
    """The stored Room, else `RoomDeleted` for a deleted Judge room or `RoomNotFound`; a key the store refuses is as unknown as a missing one."""
    try:
        data = store.read(room_key(room_id))
    except (KeyError, ValueError):
        raise missing_room(store, room_id) or RoomNotFound(room_id) from None
    return Room.model_validate_json(data)


def room_summary(room: Room, job_id: JobId) -> RoomSummary:
    """The listing row (AD-9): the first photo is the cover, and `built_at` is the Room's build time."""
    return RoomSummary(
        room_id=room.id,
        name=room.name,
        cover_photo=0,
        puzzle_count=len(room.puzzles),
        job_id=job_id,
        built_at=room.created,
    )


def jobs_by_room(jobs: JobStore) -> dict[RoomId, JobId]:
    """The job record that names each Room; a job that has no Room yet names none.

    A job record that does not parse is logged and skipped, as `resume_jobs`
    skips it at startup, so one corrupt record never hides every Room.
    """
    by_room: dict[RoomId, JobId] = {}
    for job_id in jobs.list_ids():
        try:
            job = jobs.read(job_id)
        except ValidationError as exc:
            log.warning(json.dumps({"job_id": job_id, "event": "job_unreadable", "error": f"{exc.error_count()} errors"}))
            continue
        if job.room_id is not None:
            by_room[job.room_id] = job.id
    return by_room


def room_job(jobs: JobStore, room_id: RoomId) -> JobState | None:
    """The job record that names the Room; a Room stored without one has none."""
    job_id = jobs_by_room(jobs).get(room_id)
    return None if job_id is None else jobs.read(job_id)


def room_routes(store: ArtifactStore, jobs: JobStore) -> APIRouter:
    router = APIRouter(prefix="/api/rooms", tags=["rooms"])

    @router.get("")
    def list_rooms() -> list[RoomSummary]:
        """Every stored Room with a job record, newest build first; a Room without one has no `job_id` to list."""
        job_ids = jobs_by_room(jobs)
        return [room_summary(room, job_ids[room.id]) for room in store.list_rooms() if room.id in job_ids]

    @router.get("/{room_id}")
    def get_room(room_id: str) -> PlayView:
        return to_play_view(load_room(store, room_id))

    @router.get("/{room_id}/photos/{index}")
    def get_photo(room_id: str, index: int) -> Response:
        room = load_room(store, room_id)
        if not 0 <= index < len(room.photos):
            raise PhotoNotFound(room_id, index)
        return Response(store.read(photo_key(room_id, index)), media_type="image/jpeg")

    return router


def profile_key(name: str) -> str:
    """The profile file `profiles/<name>.json`; a name that is not a plain file name is refused."""
    if not name or name == ".." or Path(name).name != name:
        raise InvalidProfileName(name)
    return f"{PROFILES}/{name}.json"


def profile_routes(store: ArtifactStore) -> APIRouter:
    """Local mode, cut 2 only: the file is written whole after the body validates, so a refused body changes nothing."""
    router = APIRouter(prefix="/api/profile", tags=["profile"])

    @router.get("/{name}")
    def get_profile(name: str) -> Profile:
        try:
            data = store.read(profile_key(name))
        except ValueError:
            raise InvalidProfileName(name) from None
        except KeyError:
            raise ProfileNotFound(name) from None
        return Profile.model_validate_json(data)

    @router.put("/{name}")
    async def put_profile(name: str, request: Request) -> Profile:
        key = profile_key(name)
        try:
            profile = Profile.model_validate_json(await request.body())
        except ValidationError as error:
            raise InvalidProfile(name, error) from None
        try:
            store.put(key, profile.model_dump_json().encode())
        except ValueError:
            raise InvalidProfileName(name) from None
        return profile

    return router


# --- Status and schema (AD-2, AD-15) ----------------------------------------


API_UNIONS: dict[str, Any] = {"Event": Event, "PostedEvent": PostedEvent, "LockInput": LockInput}
"""The tagged unions on `type` the API speaks, served by name so `web/types` declares them (AD-2)."""


def api_schema() -> dict[str, Any]:
    """The JSON Schema of every AD-2 model and tagged union, each under `$defs` by its name, in one document."""
    _, schema = models_json_schema([(model, "validation") for model in API_MODELS], ref_template="#/$defs/{model}")
    defs = schema["$defs"]
    for name, union in API_UNIONS.items():
        union_schema = TypeAdapter(union).json_schema(ref_template="#/$defs/{model}")
        union_schema.pop("$defs", None)  # every member is already under `$defs` through API_MODELS
        defs[name] = {"title": name, **union_schema}
    return {"title": "Keyframe Schema v1", "$defs": dict(sorted(defs.items()))}


def status_routes(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["status"])

    @router.get("/meta")
    def get_meta(profile: str = "dev") -> Meta:
        """Echoes the client's `?profile=` (AD-14), `dev` when absent; a name `/profile/<name>` refuses is refused here too."""
        profile_key(profile)
        return meta(settings, profile)

    @router.get("/schema")
    def get_schema() -> dict[str, Any]:
        return api_schema()

    return router


# --- Access (AD-9) ----------------------------------------------------------


def client_ip(request: Request) -> str:
    """The address the request came from: the key the access attempts are counted under."""
    return request.client.host if request.client else ""


def access_routes(guard: AccessGuard, jobs: JobStore) -> APIRouter:
    """Hosted only: the code check before photo selection, which starts no Build and claims no slot."""
    router = APIRouter(prefix="/api/access", tags=["access"])

    @router.post("/check")
    def check_access(body: AccessCheckRequest, request: Request) -> AccessCheck:
        """The right code answers the builds left; a wrong one 200 `ok: false`, never the error envelope."""
        if not guard.check(body.code, client_ip(request)):
            return AccessCheck(ok=False, builds_left=None)
        return AccessCheck(ok=True, builds_left=jobs.builds_left())

    return router


# --- Builds (AD-7) ----------------------------------------------------------

DOWNSCALE, ORIGINAL = "downscale", "original"
"""The multipart field names of `POST /builds`: one of each per photo, paired in upload order."""


def read_uploads(content_type: str, body: bytes) -> list[Upload]:
    """The photos of a multipart body, the i-th `downscale` with the i-th `original`, byte for byte.

    A body that is not multipart holds no photos; a body whose downscale and
    original counts differ is refused as `photo_count`.
    """
    message = BytesParser(policy=policy.HTTP).parsebytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body)
    parts: dict[str, list[bytes]] = {DOWNSCALE: [], ORIGINAL: []}
    if message.is_multipart():
        for part in message.get_payload():
            name = part.get_param("name", header="content-disposition")
            if name in parts:
                parts[name].append(part.get_payload(decode=True) or b"")
    downscales, originals = parts[DOWNSCALE], parts[ORIGINAL]
    if len(downscales) != len(originals):
        raise IngestRefused("photo_count", f"each photo needs a downscale and an original, got {len(downscales)} and {len(originals)}")
    return [Upload(downscale, original) for downscale, original in zip(downscales, originals, strict=True)]


def read_job(jobs: JobStore, store: ArtifactStore, job_id: str) -> JobState:
    """The persisted job state, else `RoomDeleted` when a deletion record names the job, or `JobNotFound`; an id the store refuses is as unknown as a missing one.

    A job file that does not parse is not an unknown job: its `ValidationError` surfaces as a 500.
    """
    try:
        return jobs.read(job_id)
    except ValidationError:
        raise
    except (KeyError, ValueError):
        raise missing_room(store, job_id) or JobNotFound(job_id) from None


def job_status_code(state: JobState) -> int:
    """202 while the job is `queued` or `running`, 200 once it is terminal (AD-7)."""
    return 200 if state.status in TERMINAL else 202


def build_routes(
    build: Build,
    jobs: JobStore,
    store: ArtifactStore,
    runner: JobRunner,
    on_terminal: Callable[[], object],
    guard: AccessGuard,
) -> APIRouter:
    router = APIRouter(prefix="/api/builds", tags=["builds"])

    @router.post("", status_code=202)
    async def post_build(request: Request, response: Response) -> JobState:
        """The guard runs before the body is read; ingest refuses a bad upload before any slot is claimed or job exists.

        An accepted upload claims a slot, is queued and started, never awaited.
        The guard's attempt store I/O, the multipart parse, ingest and the runner's start (a spawn and a Dict write in Hosted mode)
        run in the thread pool, so none of them holds the event loop.
        """
        await run_in_threadpool(guard, request.headers.get(ACCESS_HEADER), client_ip(request))
        content_type, body = request.headers.get("content-type", ""), await request.body()
        try:
            state = await run_in_threadpool(lambda: build.submit(read_uploads(content_type, body)))
        except (IngestRefused, UnsupportedImage) as exc:
            raise UploadRefused(error_code(exc), str(exc)) from None
        except BuildQuotaExceeded as exc:
            raise BuildQuotaRefused(str(exc)) from None
        if state.status in TERMINAL:
            on_terminal()
        else:
            await run_in_threadpool(runner.start, state.id)
        response.status_code = job_status_code(state)
        return state

    @router.get("/{job_id}")
    def get_build(job_id: str, response: Response) -> JobState:
        """The persisted job state alone: status, stage, timings, the Mask preview once segment completed, never a Room."""
        state = read_job(jobs, store, job_id)
        response.status_code = job_status_code(state)
        return state

    @router.get("/{job_id}/room")
    def get_build_room(job_id: str, request: Request) -> Room:
        """The full Room, solutions included: the one route a Room leaves the server by (AD-3), behind the access guard.

        A known job not yet `done` answers 409 `build_not_ready` with its status, as the Build view does, never `room_not_found`.
        """
        guard(request.headers.get(ACCESS_HEADER), client_ip(request))
        state = read_job(jobs, store, job_id)
        if state.status != "done":
            raise BuildNotReady(job_id, state.status)
        if state.room_id is None:
            raise RoomNotFound(job_id)
        return load_room(store, state.room_id)

    return router


def stored_session_on(sessions: SessionStore, room_id: RoomId) -> bool:
    """Whether a stored session header names this Room: a session this process or an earlier one started."""
    for session_id in sessions.list_ids():
        try:
            if sessions.read_header(session_id).room_id == room_id:
                return True
        except KeyError:
            continue
    return False


def build_view_routes(jobs: JobStore, store: ArtifactStore, settings: Settings) -> APIRouter:
    """The Build view: open in both modes, so it takes no access guard (AD-3)."""
    router = APIRouter(prefix="/api/builds", tags=["builds"])

    @router.get("/{job_id}/view")
    def get_build_view(job_id: str) -> BuildView:
        """The `done` job's `BuildView` with the Room's Disclosure list from its provenance alone (item 72); never a solution, a pairing or a Dry run answer."""
        state = read_job(jobs, store, job_id)
        if state.status != "done":
            raise BuildNotReady(job_id, state.status)
        if state.room_id is None:
            raise RoomNotFound(job_id)
        room = load_room(store, state.room_id)
        disclosure = disclosure_lines(settings, room, state, demo_room=store.is_demo_room(room.id))
        return to_build_view(room, state, disclosure=disclosure)

    return router


# --- Sessions (AD-4) --------------------------------------------------------


def spawn_thread(task: Callable[[], None]) -> None:
    """The default `Spawn`: a daemon thread in this process."""
    threading.Thread(target=task, name="greeting", daemon=True).start()


def scaled_thresholds(
    nudge_ms: Milliseconds, source: ThresholdSource, scale: SessionClock
) -> tuple[Thresholds, Milliseconds]:
    """The thresholds and Trickster window over a 1x nudge threshold, divided by the session clock (AD-10)."""
    scaled = scale.thresholds(
        nudge_threshold_ms=nudge_ms, rung_spacing_ms=RUNG_SPACING_MS, trickster_window_ms=TRICKSTER_WINDOW_MS
    )
    thresholds = Thresholds(
        nudge_threshold_ms=scaled.nudge_threshold_ms,
        nudge_threshold_base_ms=nudge_ms,
        rung_spacing_ms=scaled.rung_spacing_ms,
        rung_spacing_base_ms=RUNG_SPACING_MS,
        source=source,
    )
    return thresholds, scaled.trickster_window_ms


def new_session_id() -> SessionId:
    """A fresh `sess_` ULID (AD-18)."""
    return f"sess_{new_ulid()}"


def new_edit_id() -> str:
    """A fresh `te_` ULID, minted in server code whatever the source supplied (AD-18)."""
    return f"te_{new_ulid()}"


def judged_card(room: Room, state: SessionState, proposal: TricksterProposal) -> Callable[[Milliseconds], Event]:
    """The `trickster_card` for a proposal in `state`'s window, judged live over the Effective `room` (AD-12).

    The edit gets a fresh `te_` id and the verdict `check_edit` computes; an
    accepted card raises `room_revision` by one, a rejected one carries its
    first failing rule in `reason`.
    """
    window = state.trickster_window.index or 0
    draft = TricksterEdit(
        id=new_edit_id(), type=proposal.type, puzzle=proposal.puzzle, payload=proposal.payload,
        validator_result=UNCHECKED, accepted=False, window=window,
    )
    result = check_edit(room, state, draft)
    edit = draft.model_copy(update={"validator_result": result, "accepted": result.ok})
    return lambda t_ms: TricksterCardEvent(
        type="trickster_card",
        edit_id=edit.id,
        edit=edit,
        puzzle_id=edit.puzzle,
        accepted=result.ok,
        reason=None if result.ok else result.reasons[0].rule,
        room_revision=state.room_revision + int(result.ok),
        t_ms=t_ms,
    )


def skipped_card(state: SessionState) -> Callable[[Milliseconds], Event]:
    """The card a provider error or the Spend cap leaves: no edit, `provider_unavailable`, `room_revision` unchanged (AD-4)."""
    return lambda t_ms: TricksterCardEvent(
        type="trickster_card", edit_id=None, edit=None, puzzle_id=None, accepted=False,
        reason="provider_unavailable", room_revision=state.room_revision, t_ms=t_ms,
    )


def trigger_events(state: SessionState, log_: Sequence[Event]) -> dict[int, TriggerEvent]:
    """The type and `t_ms` of each logged event a Rung change in `state` names in `triggered_by`, by log position.

    Served with the state for the Triggers panel, like the Disclosure list, so `apply` and replay never write it.
    """
    named = sorted({i for change in state.rung_changes for i in change.triggered_by})
    return {i: TriggerEvent(type=log_[i].type, t_ms=log_[i].t_ms) for i in named}


@dataclass(slots=True)
class OpenSession:
    """One session's transient request state: its machine over the Effective room, its lock, its start, its Disclosure list and its Derived block."""

    machine: SessionStateMachine
    lock: threading.Lock
    started_ms: int
    """The session clock's reading when the session started; `t_ms` counts from it."""
    disclosure: list[str]
    """The Room's Disclosure list, composed when the session started (AD-15)."""
    derived: Derived
    """The block the thresholds came from (`Derived.fresh()` unless greeted), the Guide port's one input beside a Rung."""
    judge_room: bool
    """Whether the Room is a Judge room (`ArtifactStore.is_judge_room`), read when the session started."""
    pending: SessionState | None = None
    """The state served while the Trickster source runs, its window `pending`; set and cleared under the lock, never logged."""


class OpenSessions:
    """One lock per session id in this process; a different session id never waits on another's lock.

    A session id this process has not opened is reopened through `reopen`
    (the session's stored header and log, so a restart loses no session);
    without one, or when it finds none, the id answers `SessionNotFound`.
    """

    def __init__(self, reopen: Callable[[SessionId], OpenSession | None] = lambda session_id: None) -> None:
        self._guard = threading.Lock()
        self._open: dict[SessionId, OpenSession] = {}
        self._reopen = reopen

    def open(
        self,
        session_id: SessionId,
        machine: SessionStateMachine,
        started_ms: int,
        disclosure: list[str],
        derived: Derived,
        judge_room: bool = False,
    ) -> OpenSession:
        with self._guard:
            session = self._open[session_id] = OpenSession(
                machine, threading.Lock(), started_ms, disclosure, derived, judge_room
            )
        return session

    def any_on(self, room_id: RoomId) -> bool:
        """Whether a session on this Room has started in this process."""
        with self._guard:
            return any(session.machine.room.id == room_id for session in self._open.values())

    def get(self, session_id: SessionId) -> OpenSession:
        with self._guard:
            session = self._open.get(session_id)
        if session is not None:
            return session
        reopened = self._reopen(session_id)
        if reopened is None:
            raise SessionNotFound(session_id)
        with self._guard:
            return self._open.setdefault(session_id, reopened)


def session_routes(
    store: ArtifactStore,
    jobs: JobStore,
    sessions: SessionStore,
    clock: Clock,
    scale: SessionClock,
    phraser: HintPhraser,
    spawn: Spawn,
    settings: Settings,
    *,
    demo: bool,
    greets: bool,
    trickster: Sources = lambda: None,
) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    def machine_for(room: Room, header: SessionHeader) -> SessionStateMachine:
        """The session's machine over the stored Room, with the opening and thresholds its start fixed."""
        source: ThresholdSource = "derived" if header.opening == "greeting" else "fresh"
        thresholds, window_ms = scaled_thresholds(header.nudge_threshold_base_ms, source, scale)
        return SessionStateMachine(room, opening=header.opening, thresholds=thresholds, trickster_window_ms=window_ms)

    def room_disclosure(room: Room, earlier: bool) -> list[str]:
        """The Room's Disclosure list at a session's start (AD-15): a Demo room is the one the store names, as for the welcome."""
        return disclosure_lines(settings, room, room_job(jobs, room.id), earlier_session=earlier, demo_room=store.is_demo_room(room.id))

    def reopen(session_id: SessionId) -> OpenSession | None:
        """A session another process started, from its stored header and log; None when no header is stored.

        Its clock resumes at the last event's `t_ms`, so the downtime is not
        counted; its Derived block, never stored, is `Derived.fresh()`.
        """
        try:
            header = sessions.read_header(session_id)
        except KeyError:
            return None
        room = load_room(store, header.room_id)
        log_ = events(session_id)
        disclosure = room_disclosure(room, header.earlier_session)
        return OpenSession(
            machine_for(room, header),
            threading.Lock(),
            clock.now_ms() - (log_[-1].t_ms if log_ else 0),
            disclosure,
            Derived.fresh(),
            store.is_judge_room(room.id),
        )

    def opened(session_id: SessionId) -> OpenSession:
        """The open session, else 410 `room_deleted` when a deletion record names it, else 404 `session_not_found` (decision 58).

        A session open in this process whose stored header is gone was
        deleted meanwhile, by its Judge room's deletion or the 24 h sweep, so
        it is answered like one this process never opened.
        """
        try:
            session = open_sessions.get(session_id)
            sessions.read_header(session_id)
        except (SessionNotFound, KeyError):
            raise missing_room(store, session_id) or SessionNotFound(session_id) from None
        return session

    def earlier_session(room_id: RoomId) -> bool:
        """Whether a session on this Room has started: in this process, or stored by an earlier one."""
        return open_sessions.any_on(room_id) or stored_session_on(sessions, room_id)

    open_sessions = OpenSessions(reopen)

    def served(session: OpenSession, state: SessionState, log_: Sequence[Event]) -> SessionState:
        """The state as the client sees it: with the Room's Disclosure list (AD-15), its Judge room flag and the events its Rungs name."""
        return state.model_copy(
            update={
                "disclosure": list(session.disclosure),
                "judge_room": session.judge_room,
                "trigger_events": trigger_events(state, log_),
            }
        )

    def events(session_id: SessionId) -> list[Event]:
        """The session's log; a session that has appended nothing yet has none."""
        try:
            return sessions.read_all(session_id)
        except KeyError:
            return []

    def stamp(session: OpenSession, log_: list[Event]) -> Milliseconds:
        """`t_ms` from the session clock, past the last event's; only a `rung_change` shares its trigger's `t_ms`."""
        elapsed = clock.now_ms() - session.started_ms
        return max(elapsed, log_[-1].t_ms + 1) if log_ else elapsed

    def append(
        session_id: SessionId, session: OpenSession, log_: list[Event], build: Callable[[Milliseconds], Event]
    ) -> SessionState:
        """Under the session lock: append the event `build` makes for the stamped `t_ms`, then any `rung_change` it selected.

        The selection is the state's Rung change triggered at the event's own
        log position, worded through the Guide port before it is appended; the
        reply is the state that includes both.
        """
        started = clock.now_ms()
        event = build(stamp(session, log_))
        state = session.machine.replay(session_id, [*log_, event])
        selected = [
            worded(session, change) for change in state.rung_changes if change.triggered_by[-1:] == [len(log_)]
        ]
        for appended in (event, *selected):
            sessions.append(session_id, appended)
            log.info(json.dumps({"session_id": session_id, "event": appended.type, "duration_ms": clock.now_ms() - started}))
        logged = [*log_, event, *selected]
        if selected:
            state = session.machine.replay(session_id, logged)
        return served(session, state, logged)

    def worded(session: OpenSession, change: RungChangeEvent) -> RungChangeEvent:
        """The selected Rung as shown: its verbatim text through the Guide port, with whether it was phrased and how long that took."""
        line = phraser.phrase(change.text, session.derived)
        return change.model_copy(
            update={"text": line.text, "phrased": line.phrased, "phrasing_ms": line.latency_ms if line.phrased else None}
        )

    def hint_reply(session: OpenSession, state: SessionState, t_ms: Milliseconds) -> HintReply:
        """The current Rung of the Puzzle the request at `t_ms` resolved to and the wait for the next, else the No-hint line, never phrased.

        A Rung the request opened shares its `t_ms` and answers in the words it was appended with, so it is worded once.
        """
        puzzle_id = state.active_puzzle_id
        rung_text = session.machine.current_rung_text(state)
        if puzzle_id is None or rung_text is None:
            return HintReply(puzzle_id=puzzle_id, rung=0, text=NO_HINT_LINE, next_hint_ms=None)
        rung = state.current_rung[puzzle_id]
        opened = next((c for c in state.rung_changes if (c.puzzle_id, c.rung, c.t_ms) == (puzzle_id, rung, t_ms)), None)
        text = opened.text if opened is not None else phraser.phrase(rung_text, session.derived).text
        return HintReply(puzzle_id=puzzle_id, rung=rung, text=text, next_hint_ms=session.machine.next_hint_ms(state, t_ms))

    def welcome(room_id: RoomId) -> Callable[[Milliseconds], Event]:
        """The Room's welcome: the Demo room line on a Demo room, else the First-room line."""
        text = DEMO_ROOM_WELCOME if store.is_demo_room(room_id) else FIRST_ROOM_WELCOME
        return lambda t_ms: OpeningLineEvent(type="opening_line", kind="welcome", text=text, t_ms=t_ms)

    def greet(session_id: SessionId, session: OpenSession, derived: Derived) -> None:
        """Off the request: one composer call, then its line appended under the session lock as the one opening line.

        A composer that raises falls back to the template like any other fallback, so the session never stays pending.
        """
        started = clock.now_ms()
        line: dict[str, object] = {"session_id": session_id, "event": "phraser_fallback"}
        try:
            greeting = compose_greeting(phraser, derived)
        except Exception as exc:
            elapsed_ms = clock.now_ms() - started
            greeting = Greeting(text=greeting_template(derived), reason="phraser_fallback", latency_ms=elapsed_ms)
            line["error"] = f"{type(exc).__name__}: {exc}"
        if greeting.reason == "phraser_fallback":
            log.warning(json.dumps({**line, "duration_ms": greeting.latency_ms}))
        with session.lock:
            append(
                session_id,
                session,
                events(session_id),
                lambda t_ms: OpeningLineEvent(type="opening_line", kind="greeting", text=greeting.text, t_ms=t_ms),
            )

    @router.post("")
    def start_session(body: SessionStart) -> SessionState:
        """A fresh session over the stored Room: greeted from a returning block where wiring greets, else opened with the Room's welcome."""
        room = load_room(store, body.room_id)
        greeted = greets and is_returning(body.derived)
        derived = body.derived if greeted else Derived.fresh()
        header = SessionHeader(
            room_id=room.id,
            opening="greeting" if greeted else "welcome",
            nudge_threshold_base_ms=nudge_threshold_ms(derived),
            earlier_session=earlier_session(room.id),
        )
        machine = machine_for(room, header)
        disclosure = room_disclosure(room, header.earlier_session)
        session_id = new_session_id()
        sessions.put_header(session_id, header)
        session = open_sessions.open(
            session_id, machine, clock.now_ms(), disclosure, derived, judge_room=store.is_judge_room(room.id)
        )
        if greeted:
            state = served(session, machine.initial(session_id), [])
            spawn(lambda: greet(session_id, session, derived))
            return state
        with session.lock:
            return append(session_id, session, [], welcome(room.id))

    @router.get("/{session_id}")
    def get_session(session_id: str) -> SessionState:
        """The replayed state, with an `idle_tick` once due; while the Trickster source runs, its `pending` state without waiting."""
        session = opened(session_id)
        if (pending := session.pending) is not None:
            return pending
        with session.lock:
            log_ = events(session_id)
            last_ms = log_[-1].t_ms if log_ else 0
            if clock.now_ms() - session.started_ms - last_ms >= IDLE_TICK_MS:
                return append(session_id, session, log_, lambda t_ms: IdleTickEvent(type="idle_tick", t_ms=t_ms))
            return served(session, session.machine.replay(session_id, log_), log_)

    @router.post("/{session_id}/events")
    def post_event(session_id: str, body: PostedEvent) -> SessionState:
        session = opened(session_id)
        hint = isinstance(body, HintRequestBody)
        if hint and body.puzzle_id is not None and all(puzzle.id != body.puzzle_id for puzzle in session.machine.room.puzzles):
            raise RequestValidationError(
                [{"loc": ("body", "puzzle_id"), "msg": "names no puzzle in this room", "type": "value_error"}]
            )
        posted: list[Event] = []

        def build(t_ms: Milliseconds) -> Event:
            posted.append(EVENT.validate_python({**body.model_dump(), "t_ms": t_ms}))
            return posted[-1]

        with session.lock:
            state = append(session_id, session, events(session_id), build)
            return state.model_copy(update={"hint_reply": hint_reply(session, state, posted[-1].t_ms)}) if hint else state

    @router.post("/{session_id}/trickster")
    def post_trickster(session_id: str) -> SessionState:
        """One source call and one card per open window, under the session lock; outside one, the unchanged state."""
        session = opened(session_id)
        with session.lock:
            log_ = events(session_id)
            state = session.machine.replay(session_id, log_)
            window = state.trickster_window
            if window.state != "open" or window.index is None:
                return served(session, state, log_)
            pending = state.model_copy(update={"trickster_window": TricksterWindow(state="pending", index=window.index)})
            session.pending = served(session, pending, log_)
            try:
                room = effective_room(session.machine.room, log_)
                summary = game_state_summary(state, max(0, clock.now_ms() - session.started_ms))
                try:
                    source = trickster()
                except (OSError, ValidationError) as exc:  # a missing or malformed proposals file: no proposal
                    log.warning(json.dumps({"session_id": session_id, "event": "trickster_source_unavailable", "error": type(exc).__name__}))
                    source = None
                try:
                    proposal = None if source is None else source.propose(
                        session.machine.room.id, window.index, to_prompt_view(room), summary, session_id=session_id
                    )
                except (ProviderError, SpendCapExceeded) as exc:
                    log.warning(json.dumps({"session_id": session_id, "event": "trickster_skipped", "error": type(exc).__name__}))
                    return append(session_id, session, log_, skipped_card(state))
                if proposal is None:
                    return served(session, state, log_)
                return append(session_id, session, log_, judged_card(room, pending, proposal))
            finally:
                session.pending = None

    @router.get("/{session_id}/room")
    def get_session_room(session_id: str) -> PlayView:
        """The Effective room as `PlayView`: accepted edits folded in, any Decoy an unflagged evidence card (AD-3, AD-12).

        A Judge room deleted while its session is still open here answers
        `RoomDeleted`, so the client shows its room-gone card (AD-9).
        """
        session = opened(session_id)
        if session.judge_room and (gone := missing_room(store, session.machine.room.id)) is not None:
            raise gone
        return to_play_view(effective_room(session.machine.room, events(session_id)))

    @router.get("/{session_id}/result")
    def get_result(session_id: str) -> RoomResult:
        session = opened(session_id)
        return session.machine.result(session_id, events(session_id), demo=demo)

    return router


API_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def unknown_api_routes() -> APIRouter:
    """The last API route: any other `/api/` path answers 404 `not_found` in the envelope, never the static mount's 405 to a POST."""
    router = APIRouter()

    @router.api_route("/api/{path:path}", methods=API_METHODS, include_in_schema=False)
    def unknown_api_path(path: str) -> None:
        raise NotFound()

    return router


def create_app(
    settings: Settings,
    *,
    handles: ModalHandles | None = None,
    rooms_root: Path = ROOMS_ROOT,
    web_dist: Path = WEB_DIST,
    clock: Clock | None = None,
    phraser: HintPhraser | None = None,
    spawn: Spawn = spawn_thread,
    stages: Mapping[Stage, StageFn] | None = None,
    access_clock: Callable[[], int] = wall_ms,
    ledger_path: Path = LEDGER_PATH,
    exports_root: Path = EXPORTS_ROOT,
    cache_root: Path = CACHE_ROOT,
    today: Callable[[], date] = date.today,
    proposals_dir: Path | None = None,
    trickster: Sources | None = None,
) -> FastAPI:
    """The app over the adapters `wire` selects; routes are registered before the static mount so `/api/` wins.

    An `/api/` path no route serves answers 404 in both modes, before the
    static mount, so a route one mode leaves out (`POST /access/check` in
    Local mode) is not found whether or not `web/dist` is built.

    `handles` are the Modal handles `src/api/modal_app.py` passes under
    `MODE=hosted`. Tests pass the session clock, the Guide adapter and the
    `Spawn` the greeting runs through; `stages` replaces the stage
    functions wiring builds over the per-role providers (tests pass
    doubles); `access_clock`, Unix milliseconds, times the hosted access
    attempts; the paths and `today` let tests keep the ledger, its exports
    and the cache out of the repo. `proposals_dir` replaces the proposals
    folder `DEMO_PROPOSALS_DIR` names, and `trickster` the source wiring
    resolves from `DEMO_TRICKSTER` (tests pass doubles).
    """
    wired = wire(
        settings,
        handles=handles,
        stages=stages,
        rooms_root=rooms_root,
        ledger_path=ledger_path,
        exports_root=exports_root,
        cache_root=cache_root,
        today=today,
        access_clock=access_clock,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """At startup: wiring's startup hook (locally, the ledger export and the restart of every job left in flight)."""
        wired.startup()
        yield

    app = FastAPI(
        title="Keyframe",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
        lifespan=lifespan,
    )
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.include_router(status_routes(settings))
    if wired.access_check:
        app.include_router(access_routes(wired.guard, wired.jobs))
    app.include_router(
        build_routes(wired.build, wired.jobs, wired.artifacts, wired.runner, on_terminal=wired.on_terminal, guard=wired.guard)
    )
    app.include_router(build_view_routes(wired.jobs, wired.artifacts, settings))
    app.include_router(room_routes(wired.artifacts, wired.jobs))
    if wired.profiles:
        app.include_router(profile_routes(wired.artifacts))
    scale = session_clock(settings)
    app.include_router(
        session_routes(
            wired.artifacts,
            wired.jobs,
            wired.sessions,
            clock or scale,
            scale,
            phraser or hint_phraser(settings),
            spawn,
            settings,
            demo=settings.demo_timescale > 1,
            greets=wired.greets,
            trickster=trickster or trickster_source(settings, wired.trickster, proposals_dir),
        )
    )
    app.include_router(unknown_api_routes())
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return app


@cache
def local_app() -> FastAPI:
    """The app over the environment's `Settings`, built once on first use."""
    return create_app(Settings.from_env())


def __getattr__(name: str) -> FastAPI:
    """`uv run uvicorn src.api.app:app` from the repo root: `app` is built when first read, not at import.

    So the hosted entry can import `create_app` in a container whose
    environment says `MODE=hosted` without building an app with no handles.
    """
    if name == "app":
        return local_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
