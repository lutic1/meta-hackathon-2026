"""The FastAPI app: routes under `/api/` and the built client at `/` (AD-4, AD-9, AD-13).

`create_app(settings)` takes every adapter from `src/api/wiring.py` and
mounts `web/dist` at `/` when it exists (one origin, no CORS); without a
build the mount is skipped and the API still serves. Room routes return
`PlayView` and the stored downscaled JPEG bytes, never a `Room` (AD-3).
The cut-2 profile routes `GET|PUT /profile/<name>` read and write the
`Profile` as `rooms/profiles/<name>.json` on the player's machine (AD-8):
they are the only code that touches `rooms/profiles/`, every other route
sees only the posted `derived`, and the hosted app never registers them
(gated on `Settings.mode` when it lands, 7.2).

Session routes are the one server-authoritative play surface (AD-4):
`POST /sessions` starts a session and opens it with its opening line,
`POST /sessions/<id>/events` appends a client event and `GET /sessions/<id>`
replays the state, appending an `idle_tick` when `IDLE_TICK_MS` have passed
since the last event, and `GET /sessions/<id>/result` computes the
`RoomResult` from the log. In Local mode a Derived block with `sessions` >= 1
is greeted: the start reply carries `opening_line {kind: greeting, text: null}`
with `phrasing` true, and the Greeting composer (`compose_greeting`) runs off
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
(AD-10). Nothing from the Derived block is stored. Every append runs under one
lock per session id held in this process (`OpenSessions`), so events land one
after another with strictly increasing `t_ms` and each reply carries the state
that includes its own event; the lock and the clock reading at the session's
start are transient request state, never replayed state. `t_ms` is stamped
from the session clock at append, so a body carrying one is refused. Each
appended event is logged as one JSON line with `session_id`, the event type
and `duration_ms` (AR-22). Every session state served, the greeted start
reply included, carries the global Disclosure lines `src/api/meta.py`
composes (AD-15); the per-Room line joins in 6.2.

`GET /rooms` lists one `RoomSummary` per stored Room with a job record
through `ArtifactStore.list_rooms()`, newest build first, with `job_id` read
from the job record that names the Room (AD-9); `GET /meta` serves the
`Meta` model, echoing any `?profile=` name the profile routes accept (AD-14),
and `GET /schema` the JSON Schema of every AD-2 model under `$defs`, from
which `web/types` are generated. The Trickster route and the build routes
land with their stories.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError
from pydantic.json_schema import models_json_schema

from src.api.errors import (
    ApiError,
    InvalidProfile,
    InvalidProfileName,
    PhotoNotFound,
    ProfileNotFound,
    RoomNotFound,
    SessionNotFound,
    handle_api_error,
    handle_validation_error,
)
from src.api.meta import disclosure_lines, meta
from src.api.wiring import artifact_store, hint_phraser, job_store, session_clock, session_store
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
    Derived,
    Event,
    IdleTickEvent,
    JobId,
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
    SessionId,
    SessionStart,
    SessionState,
    Thresholds,
)
from src.domain.session import SessionStateMachine
from src.infra.clocks import SessionClock
from src.infra.local import ROOMS_ROOT
from src.pipeline.ports import (
    ArtifactStore,
    Clock,
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


def api_schema() -> dict[str, Any]:
    """The JSON Schema of every AD-2 model, each under `$defs` by its name, in one document."""
    _, schema = models_json_schema([(model, "validation") for model in API_MODELS], ref_template="#/$defs/{model}")
    return {"title": "Keyframe Schema v1", **schema}


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
    """One session's transient request state: its machine over the Effective room, its lock and its start."""

    machine: SessionStateMachine
    lock: threading.Lock
    started_ms: int
    """The session clock's reading when the session started; `t_ms` counts from it."""


class OpenSessions:
    """One lock per session id in this process; a different session id never waits on another's lock."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._open: dict[SessionId, OpenSession] = {}

    def open(self, session_id: SessionId, machine: SessionStateMachine, started_ms: int) -> OpenSession:
        with self._guard:
            session = self._open[session_id] = OpenSession(machine, threading.Lock(), started_ms)
        return session

    def get(self, session_id: SessionId) -> OpenSession:
        with self._guard:
            session = self._open.get(session_id)
        if session is None:
            raise SessionNotFound(session_id)
        return session


def session_routes(
    store: ArtifactStore,
    sessions: SessionStore,
    clock: Clock,
    scale: SessionClock,
    phraser: HintPhraser,
    spawn: Spawn,
    *,
    demo: bool,
    hosted: bool,
    disclosure: list[str],
) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])
    open_sessions = OpenSessions()

    def served(state: SessionState) -> SessionState:
        """The state as the client sees it: with the global Disclosure lines (AD-15)."""
        return state.model_copy(update={"disclosure": list(disclosure)})

    def events(session_id: SessionId) -> list[Event]:
        """The session's log; a session that has appended nothing yet has none."""
        try:
            return sessions.read_all(session_id)
        except KeyError:
            return []

    def stamp(session: OpenSession, log_: list[Event]) -> Milliseconds:
        """`t_ms` from the session clock, past the last event's so the log is strictly increasing."""
        elapsed = clock.now_ms() - session.started_ms
        return max(elapsed, log_[-1].t_ms + 1) if log_ else elapsed

    def append(
        session_id: SessionId, session: OpenSession, log_: list[Event], build: Callable[[Milliseconds], Event]
    ) -> SessionState:
        """Under the session lock: append the event `build` makes for the stamped `t_ms` and reply with the state that includes it."""
        started = clock.now_ms()
        event = build(stamp(session, log_))
        sessions.append(session_id, event)
        state = served(session.machine.replay(session_id, [*log_, event]))
        log.info(json.dumps({"session_id": session_id, "event": event.type, "duration_ms": clock.now_ms() - started}))
        return state

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
        """A fresh session over the stored Room: greeted from a returning Local block, else opened with the welcome."""
        room = load_room(store, body.room_id)
        greeted = not hosted and is_returning(body.derived)
        derived = body.derived if greeted else Derived.fresh()
        machine = SessionStateMachine(
            room, opening="greeting" if greeted else "welcome", thresholds=session_thresholds(derived, scale)
        )
        session_id = new_session_id()
        session = open_sessions.open(session_id, machine, clock.now_ms())
        if greeted:
            state = served(machine.initial(session_id))
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
            return served(session.machine.replay(session_id, log_))

    @router.post("/{session_id}/events")
    def post_event(session_id: str, body: PostedEvent) -> SessionState:
        session = open_sessions.get(session_id)
        with session.lock:
            log_ = events(session_id)
            return append(session_id, session, log_, lambda t_ms: EVENT.validate_python({**body.model_dump(), "t_ms": t_ms}))

    @router.get("/{session_id}/result")
    def get_result(session_id: str) -> RoomResult:
        session = open_sessions.get(session_id)
        return session.machine.result(session_id, events(session_id), demo=demo)

    return router


def create_app(
    settings: Settings,
    *,
    rooms_root: Path = ROOMS_ROOT,
    web_dist: Path = WEB_DIST,
    clock: Clock | None = None,
    phraser: HintPhraser | None = None,
    spawn: Spawn = spawn_thread,
    hosted: bool = False,
) -> FastAPI:
    """The app over the adapters wiring builds; routes are registered before the static mount so `/api/` wins.

    Tests pass the session clock, the Guide adapter and the `Spawn` the
    greeting runs through. `hosted` stands in for `Settings.mode == "hosted"`
    until 7.2 adds `mode`: every hosted session opens with the welcome and
    `Derived.fresh()` thresholds, and `greet` is never called.
    """
    app = FastAPI(
        title="Keyframe",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    store = artifact_store(rooms_root)
    app.include_router(status_routes(settings))
    app.include_router(room_routes(store, job_store(rooms_root)))
    app.include_router(profile_routes(store))
    scale = session_clock(settings)
    app.include_router(
        session_routes(
            store,
            session_store(rooms_root),
            clock or scale,
            scale,
            phraser or hint_phraser(settings),
            spawn,
            demo=settings.demo_timescale > 1,
            hosted=hosted,
            disclosure=disclosure_lines(settings),
        )
    )
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return app


app = create_app(Settings.from_env())
"""`uv run uvicorn src.api.app:app` from the repo root."""
