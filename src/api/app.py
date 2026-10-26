"""The FastAPI app: routes under `/api/` and the built client at `/` (AD-9, AD-13).

`create_app(settings)` takes every adapter from `src/api/wiring.py` and
mounts `web/dist` at `/` when it exists (one origin, no CORS); without a
build the mount is skipped and the API still serves. Room routes return
`PlayView` and the stored downscaled JPEG bytes, never a `Room` (AD-3).
The cut-2 profile routes `GET|PUT /profile/<name>` read and write the
`Profile` as `rooms/profiles/<name>.json` on the player's machine (AD-8):
they are the only code that touches `rooms/profiles/`, every other route
sees only the posted `derived`, and the hosted app never registers them
(gated on `Settings.mode` when it lands, 7.2). The session routes, the
build routes, `GET /schema` and `GET /meta` land with their stories.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from src.api.errors import (
    ApiError,
    InvalidProfile,
    InvalidProfileName,
    PhotoNotFound,
    ProfileNotFound,
    RoomNotFound,
    handle_api_error,
)
from src.api.wiring import artifact_store
from src.config import Settings
from src.domain.redact import to_play_view
from src.domain.schema import PlayView, Profile, Room
from src.infra.local import ROOMS_ROOT
from src.pipeline.ports import ArtifactStore, photo_key, room_key

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
"""The Vite build; `vite.config.ts` proxies `/api/*` to uvicorn in development instead."""
PROFILES = "profiles"
"""The profile files, `rooms/profiles/<name>.json`; only the profile routes read or write under it."""


def load_room(store: ArtifactStore, room_id: str) -> Room:
    """The stored Room, or `RoomNotFound`; a key the store refuses is as unknown as a missing one."""
    try:
        data = store.read(room_key(room_id))
    except (KeyError, ValueError):
        raise RoomNotFound(room_id) from None
    return Room.model_validate_json(data)


def room_routes(store: ArtifactStore) -> APIRouter:
    router = APIRouter(prefix="/api/rooms", tags=["rooms"])

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


def create_app(settings: Settings, *, rooms_root: Path = ROOMS_ROOT, web_dist: Path = WEB_DIST) -> FastAPI:
    """The app over the adapters wiring builds; routes are registered before the static mount so `/api/` wins."""
    app = FastAPI(
        title="Keyframe",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,
    )
    app.add_exception_handler(ApiError, handle_api_error)
    store = artifact_store(rooms_root)
    app.include_router(room_routes(store))
    app.include_router(profile_routes(store))
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return app


app = create_app(Settings.from_env())
"""`uv run uvicorn src.api.app:app` from the repo root."""
