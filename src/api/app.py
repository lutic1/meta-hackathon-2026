"""The FastAPI app: routes under `/api/` and the built client at `/` (AD-9, AD-13).

`create_app(settings)` takes every adapter from `src/api/wiring.py` and
mounts `web/dist` at `/` when it exists (one origin, no CORS); without a
build the mount is skipped and the API still serves. Room routes return
`PlayView` and the stored downscaled JPEG bytes, never a `Room` (AD-3).
The session routes, the build routes, `GET /schema` and `GET /meta` land
with their stories.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Response
from fastapi.staticfiles import StaticFiles

from src.api.errors import ApiError, PhotoNotFound, RoomNotFound, handle_api_error
from src.api.wiring import artifact_store
from src.config import Settings
from src.domain.redact import to_play_view
from src.domain.schema import PlayView, Room
from src.infra.local import ROOMS_ROOT
from src.pipeline.ports import ArtifactStore, photo_key, room_key

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
"""The Vite build; `vite.config.ts` proxies `/api/*` to uvicorn in development instead."""


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
    app.include_router(room_routes(artifact_store(rooms_root)))
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return app


app = create_app(Settings.from_env())
"""`uv run uvicorn src.api.app:app` from the repo root."""
