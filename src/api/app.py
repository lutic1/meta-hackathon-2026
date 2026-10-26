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
start whatever block it carries, appends the First-room welcome
(`FIRST_ROOM_WELCOME`, the only copy of the text; the client renders what it
receives) at once, so its reply already carries the line with `phrasing`
false; the Demo room variant lands with 7.15. A reload replays the one event
rather than appending another. The session's `Thresholds` are fixed at the
start from the greeted block, else `Derived.fresh()`: the 1x values from
`src/domain/rungs.py`, divided by `DEMO_TIMESCALE` on the session clock
(AD-10). Nothing from the Derived block is written to the log; the block
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
session's start are transient request state, never replayed state. `t_ms` is
stamped from the session clock at append, so a body carrying one is refused.
A `hint_request` is answered on its reply in `hint_reply`: the current Rung
of the Puzzle it resolved to, routed through the `HintPhraser`, or with no
Rung open (or no Puzzle active, once the Exit has opened) the fixed
`NO_HINT_LINE`, never phrased; it never opens a Rung, and a `puzzle_id` that
is not in the Room is a malformed body, refused with nothing appended. Each
appended event is logged as one JSON line with `session_id`, the event type
and `duration_ms` (AR-22). Every session state served, the greeted start
reply included, carries its Room's Disclosure list, composed once at the
session's start by `disclosure_lines` in `src/api/meta.py` (AD-15): the
global lines, plus the earlier-builds line for a Demo room, a Room with a
session already started in this process, or a Room whose job record holds
any call served from the Cache; a later session on the same Room never
changes an earlier session's list.

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
(AD-3), behind the same guard (open in Local mode), `room_not_found` until
the job is `done`. Hosted only, `POST /access/check {code}` answers the
`AccessCheck` before any photo is chosen: `{ok: true, builds_left}` read
from the `JobStore` for the right code, 200 `{ok: false, builds_left: null}`
for a wrong one, starting no Build and claiming no slot; `POST /builds`
still checks the code and claims the slot itself. Every attempt on the
guarded routes and the check counts against the per-IP limit first, and
one past it answers 429 `too_many_attempts` with `Retry-After` before the
code is compared (AD-9). Every other route is open in both modes. At
startup the local app exports the ledger and restarts every job left
`queued` or `running`; the runner exports again after each Build ends (AD-9). The
Trickster route and `GET /builds/<job_id>/view` land with their stories.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import AsyncIterator, Callable, Mapping
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
    BuildQuotaRefused,
    InvalidProfile,
    InvalidProfileName,
    JobNotFound,
    PhotoNotFound,
    ProfileNotFound,
    RoomNotFound,
    SessionNotFound,
    UploadRefused,
    handle_api_error,
    handle_validation_error,
)
from src.api.meta import disclosure_lines, meta
from src.api.wiring import ACCESS_HEADER, AccessGuard, hint_phraser, session_clock, wire
from src.config import Settings
from src.council.greeting import Greeting, compose_greeting
from src.domain.redact import to_play_view
from src.domain.rungs import (
    RUNG_SPACING_MS,
    TRICKSTER_WINDOW_MS,
    is_returning,
    nudge_threshold_ms,
    threshold_source,
)
from src.domain.schema import (
    API_MODELS,
    AccessCheck,
    AccessCheckRequest,
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
)
from src.domain.session import SessionStateMachine
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
from src.providers.base import HintPhraser
from src.providers.spend import new_ulid
from src.providers.verbatim import greeting_template

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
"""The Vite build; `vite.config.ts` proxies `/api/*` to uvicorn in development instead."""
PROFILES = "profiles"
"""The profile files, `rooms/profiles/<name>.json`; only the profile routes read or write under it."""

IDLE_TICK_MS = 5000
"""A `GET /sessions/<id>` read appends an `idle_tick` once this long has passed since the last event (AD-4)."""

FIRST_ROOM_WELCOME = "Welcome to your own room. Find what doesn't belong."
"""The fixed First-room welcome (A-13, FR-21): the `opening_line` of every session start not greeted, worded here alone."""

NO_HINT_LINE = "A fair ask. Look around a little longer; I'll speak up if you stay stuck."
"""The fixed No-hint line (UX-DR76): the reply to a Hint request while no Rung is open, never phrased."""

EVENT = TypeAdapter(Event)

Spawn = Callable[[Callable[[], None]], None]
"""Runs a task off the request; the Greeting composer runs through it so the start reply never waits on the Guide model."""

log = logging.getLogger("keyframe.sessions")


def load_room(store: ArtifactStore, room_id: str) -> Room:
    """The stored Room, or `RoomNotFound`; a key the store refuses is as unknown as a missing one."""
    try:
        data = store.read(room_key(room_id))
    except (KeyError, ValueError):
        raise RoomNotFound(room_id) from None
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
    """The job record that names each Room; a job that has no Room yet names none."""
    return {job.room_id: job.id for job in map(jobs.read, jobs.list_ids()) if job.room_id is not None}


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
            first = error.errors(include_url=False)[0]
            raise InvalidProfile(name, f"{'.'.join(map(str, first['loc'])) or 'body'}: {first['msg']}") from None
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


def read_job(jobs: JobStore, job_id: str) -> JobState:
    """The persisted job state, or `JobNotFound`; an id the store refuses is as unknown as a missing one.

    A job file that does not parse is not an unknown job: its `ValidationError` surfaces as a 500.
    """
    try:
        return jobs.read(job_id)
    except ValidationError:
        raise
    except (KeyError, ValueError):
        raise JobNotFound(job_id) from None


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
        The multipart parse and ingest run in the thread pool, so a large body never holds the event loop.
        """
        guard(request.headers.get(ACCESS_HEADER), client_ip(request))
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
            runner.start(state.id)
        response.status_code = job_status_code(state)
        return state

    @router.get("/{job_id}")
    def get_build(job_id: str, response: Response) -> JobState:
        """The persisted job state alone: status, stage, timings, the Mask preview once segment completed, never a Room."""
        state = read_job(jobs, job_id)
        response.status_code = job_status_code(state)
        return state

    @router.get("/{job_id}/room")
    def get_build_room(job_id: str, request: Request) -> Room:
        """The full Room, solutions included: the one route a Room leaves the server by (AD-3), behind the access guard."""
        guard(request.headers.get(ACCESS_HEADER), client_ip(request))
        state = read_job(jobs, job_id)
        if state.status != "done" or state.room_id is None:
            raise RoomNotFound(state.room_id or job_id)
        return load_room(store, state.room_id)

    return router


# --- Sessions (AD-4) --------------------------------------------------------


def spawn_thread(task: Callable[[], None]) -> None:
    """The default `Spawn`: a daemon thread in this process."""
    threading.Thread(target=task, name="greeting", daemon=True).start()


def session_thresholds(derived: Derived, scale: SessionClock) -> Thresholds:
    """The session's thresholds: the 1x values `rungs` computes from `derived`, divided by the session clock (AD-10)."""
    nudge_ms = nudge_threshold_ms(derived)
    scaled = scale.thresholds(
        nudge_threshold_ms=nudge_ms, rung_spacing_ms=RUNG_SPACING_MS, trickster_window_ms=TRICKSTER_WINDOW_MS
    )
    return Thresholds(
        nudge_threshold_ms=scaled.nudge_threshold_ms,
        nudge_threshold_base_ms=nudge_ms,
        rung_spacing_ms=scaled.rung_spacing_ms,
        rung_spacing_base_ms=RUNG_SPACING_MS,
        source=threshold_source(derived),
    )


def new_session_id() -> SessionId:
    """A fresh `sess_` ULID (AD-18)."""
    return f"sess_{new_ulid()}"


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


class OpenSessions:
    """One lock per session id in this process; a different session id never waits on another's lock."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._open: dict[SessionId, OpenSession] = {}

    def open(
        self, session_id: SessionId, machine: SessionStateMachine, started_ms: int, disclosure: list[str], derived: Derived
    ) -> OpenSession:
        with self._guard:
            session = self._open[session_id] = OpenSession(machine, threading.Lock(), started_ms, disclosure, derived)
        return session

    def any_on(self, room_id: RoomId) -> bool:
        """Whether a session on this Room has started in this process."""
        with self._guard:
            return any(session.machine.room.id == room_id for session in self._open.values())

    def get(self, session_id: SessionId) -> OpenSession:
        with self._guard:
            session = self._open.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        return session


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
) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])
    open_sessions = OpenSessions()

    def served(session: OpenSession, state: SessionState) -> SessionState:
        """The state as the client sees it: with the Room's Disclosure list (AD-15)."""
        return state.model_copy(update={"disclosure": list(session.disclosure)})

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
        if selected:
            state = session.machine.replay(session_id, [*log_, event, *selected])
        return served(session, state)

    def worded(session: OpenSession, change: RungChangeEvent) -> RungChangeEvent:
        """The selected Rung as shown: its verbatim text through the Guide port, with whether it was phrased and how long that took."""
        line = phraser.phrase(change.text, session.derived)
        return change.model_copy(
            update={"text": line.text, "phrased": line.phrased, "phrasing_ms": line.latency_ms if line.phrased else None}
        )

    def hint_reply(session: OpenSession, state: SessionState) -> HintReply:
        """The current Rung of the Puzzle the request resolved to, through the Guide port, else the No-hint line, never phrased."""
        puzzle_id = state.active_puzzle_id
        rung_text = session.machine.current_rung_text(state)
        if puzzle_id is None or rung_text is None:
            return HintReply(puzzle_id=puzzle_id, rung=0, text=NO_HINT_LINE)
        line = phraser.phrase(rung_text, session.derived)
        return HintReply(puzzle_id=puzzle_id, rung=state.current_rung[puzzle_id], text=line.text)

    def welcome(t_ms: Milliseconds) -> Event:
        return OpeningLineEvent(type="opening_line", kind="welcome", text=FIRST_ROOM_WELCOME, t_ms=t_ms)

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
        """A fresh session over the stored Room: greeted from a returning block where wiring greets, else opened with the welcome."""
        room = load_room(store, body.room_id)
        greeted = greets and is_returning(body.derived)
        derived = body.derived if greeted else Derived.fresh()
        machine = SessionStateMachine(
            room, opening="greeting" if greeted else "welcome", thresholds=session_thresholds(derived, scale)
        )
        disclosure = disclosure_lines(settings, room, room_job(jobs, room.id), earlier_session=open_sessions.any_on(room.id))
        session_id = new_session_id()
        session = open_sessions.open(session_id, machine, clock.now_ms(), disclosure, derived)
        if greeted:
            state = served(session, machine.initial(session_id))
            spawn(lambda: greet(session_id, session, derived))
            return state
        with session.lock:
            return append(session_id, session, [], welcome)

    @router.get("/{session_id}")
    def get_session(session_id: str) -> SessionState:
        session = open_sessions.get(session_id)
        with session.lock:
            log_ = events(session_id)
            last_ms = log_[-1].t_ms if log_ else 0
            if clock.now_ms() - session.started_ms - last_ms >= IDLE_TICK_MS:
                return append(session_id, session, log_, lambda t_ms: IdleTickEvent(type="idle_tick", t_ms=t_ms))
            return served(session, session.machine.replay(session_id, log_))

    @router.post("/{session_id}/events")
    def post_event(session_id: str, body: PostedEvent) -> SessionState:
        session = open_sessions.get(session_id)
        hint = isinstance(body, HintRequestBody)
        if hint and body.puzzle_id is not None and all(puzzle.id != body.puzzle_id for puzzle in session.machine.room.puzzles):
            raise RequestValidationError(
                [{"loc": ("body", "puzzle_id"), "msg": f"no puzzle {body.puzzle_id} in this room", "type": "value_error"}]
            )
        with session.lock:
            log_ = events(session_id)
            state = append(session_id, session, log_, lambda t_ms: EVENT.validate_python({**body.model_dump(), "t_ms": t_ms}))
            return state.model_copy(update={"hint_reply": hint_reply(session, state)}) if hint else state

    @router.get("/{session_id}/result")
    def get_result(session_id: str) -> RoomResult:
        session = open_sessions.get(session_id)
        return session.machine.result(session_id, events(session_id), demo=demo)

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
) -> FastAPI:
    """The app over the adapters `wire` selects; routes are registered before the static mount so `/api/` wins.

    `handles` are the Modal handles `src/api/modal_app.py` passes under
    `MODE=hosted`. Tests pass the session clock, the Guide adapter and the
    `Spawn` the greeting runs through; `stages` replaces the stage
    functions wiring builds over the per-role providers (tests pass
    doubles); `access_clock`, Unix milliseconds, times the hosted access
    attempts; the paths and `today` let tests keep the ledger, its exports
    and the cache out of the repo.
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
        )
    )
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
