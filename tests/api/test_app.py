"""Story 1.11: the room routes serve `PlayView` and the stored photo bytes under `/api/`, the envelope answers an unknown room, and `web/dist` is mounted at `/` only when it exists (AD-3, AD-9, AD-13)."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import ANY

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Mount

from src.api.app import WEB_DIST, create_app, load_room
from src.api.errors import ApiError, PhotoNotFound, RoomNotFound, envelope
from src.api.wiring import artifact_store
from src.config import Settings
from src.domain.redact import to_play_view
from src.domain.schema import ErrorEnvelope, Room
from src.pipeline.ports import ArtifactStore, photo_key, room_key
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import (
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)

UNKNOWN = "room_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ROOM_NOT_FOUND = {"error": {"code": "room_not_found", "message": ANY, "stage": None}}


def store_room(store: ArtifactStore, room: Room) -> None:
    """Put the Room and its photos under the keys the routes read."""
    store.put(room_key(room.id), room.model_dump_json().encode())
    for index, photo in enumerate(room.photos):
        store.put(photo_key(room.id, index), Path(photo.downscaled_path).read_bytes())


def make_app(tmp_path: Path, *rooms: Room, web_dist: Path | None = None) -> FastAPI:
    root = tmp_path / "rooms"
    store = artifact_store(root)
    for room in rooms:
        store_room(store, room)
    return create_app(Settings.from_env(), rooms_root=root, web_dist=web_dist or tmp_path / "no-dist")


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


# --- The PlayView and photo routes ----------------------------------------


def test_get_room_returns_the_play_view(client: TestClient, four_lock_room: Room):
    response = client.get(f"/api/rooms/{four_lock_room.id}")
    assert response.status_code == 200
    assert response.json() == to_play_view(four_lock_room).model_dump(mode="json")
    assert "solution" not in json_keys(response.json())


def test_get_photo_returns_the_stored_jpeg_bytes_byte_for_byte(client: TestClient, four_lock_room: Room):
    for index, photo in enumerate(four_lock_room.photos):
        response = client.get(f"/api/rooms/{four_lock_room.id}/photos/{index}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == Path(photo.downscaled_path).read_bytes()
        assert len(response.content) == photo.size


@pytest.mark.parametrize("index", [6, 7, -1, 1000])
def test_a_photo_index_outside_the_room_answers_404(client: TestClient, four_lock_room: Room, index: int):
    response = client.get(f"/api/rooms/{four_lock_room.id}/photos/{index}")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "photo_not_found", "message": ANY, "stage": None}}


def test_a_photo_index_that_is_not_an_integer_answers_422(client: TestClient, four_lock_room: Room):
    assert client.get(f"/api/rooms/{four_lock_room.id}/photos/first").status_code == 422


# --- An unknown room ---------------------------------------------------------


@pytest.mark.parametrize("path", ["/api/rooms/{room_id}", "/api/rooms/{room_id}/photos/0"])
def test_an_unknown_room_answers_404_with_the_envelope(client: TestClient, path: str):
    response = client.get(path.format(room_id=UNKNOWN))
    assert response.status_code == 404
    assert response.json() == ROOM_NOT_FOUND
    assert ErrorEnvelope.model_validate(response.json()).status is None


@pytest.mark.parametrize("room_id", [UNKNOWN, "..", "nope", "sessions"])
def test_load_room_raises_room_not_found(tmp_path: Path, four_lock_room: Room, room_id: str):
    store = artifact_store(tmp_path / "rooms")
    store_room(store, four_lock_room)
    assert load_room(store, four_lock_room.id) == four_lock_room
    with pytest.raises(RoomNotFound) as excinfo:
        load_room(store, room_id)
    assert isinstance(excinfo.value, ApiError) and (excinfo.value.status, excinfo.value.code) == (404, "room_not_found")


def test_the_envelope_carries_a_null_stage_and_no_status():
    for error in (RoomNotFound(UNKNOWN), PhotoNotFound(UNKNOWN, 9)):
        model = envelope(error)
        assert model.error.stage is None and model.status is None
        assert model.model_dump(mode="json", exclude_unset=True) == {
            "error": {"code": error.code, "message": error.message, "stage": None},
        }


# --- Every route under /api/, the client at / ------------------------------


def _paths(app: FastAPI) -> list[str]:
    """Every path the app serves: the schema's operations plus each plain route and mount (stored as `""` for `/`)."""
    return sorted({*app.openapi()["paths"], *(route.path or "/" for route in app.routes if hasattr(route, "path"))})


def _mounts(app: FastAPI) -> list[str]:
    return [route.path or "/" for route in app.routes if isinstance(route, Mount)]


def test_every_api_route_lives_under_api(tmp_path: Path):
    paths = _paths(make_app(tmp_path))
    assert "/api/rooms/{room_id}" in paths and "/api/rooms/{room_id}/photos/{index}" in paths
    assert all(path.startswith("/api/") for path in paths), paths


def test_the_mount_is_skipped_when_web_dist_does_not_exist(tmp_path: Path, four_lock_room: Room):
    app = make_app(tmp_path, four_lock_room, web_dist=tmp_path / "web" / "dist")
    assert not (tmp_path / "web" / "dist").exists()
    assert "/" not in _paths(app) and _mounts(app) == []
    client = TestClient(app)
    assert client.get("/").status_code == 404
    assert client.get(f"/api/rooms/{four_lock_room.id}").status_code == 200


def test_web_dist_is_mounted_at_the_root_behind_the_api_routes(tmp_path: Path, four_lock_room: Room):
    dist = tmp_path / "web" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=\"app\"></div>")
    (dist / "assets" / "app.js").write_text("console.log('keyframe')")
    app = make_app(tmp_path, four_lock_room, web_dist=dist)
    assert _mounts(app) == ["/"]
    assert [path for path in _paths(app) if not path.startswith("/api/")] == ["/"]
    client = TestClient(app)
    assert client.get("/").text == (dist / "index.html").read_text()
    assert client.get("/assets/app.js").text == "console.log('keyframe')"
    assert client.get("/missing.js").status_code == 404
    assert client.get(f"/api/rooms/{four_lock_room.id}").json()["id"] == four_lock_room.id
    assert client.get(f"/api/rooms/{UNKNOWN}").json() == ROOM_NOT_FOUND


def test_the_default_app_points_at_web_dist_and_rooms():
    from src.api.app import app
    from src.infra.local import ROOMS_ROOT

    assert WEB_DIST == Path(__file__).resolve().parents[2] / "web" / "dist"
    assert ROOMS_ROOT == Path("rooms")
    assert all(path.startswith("/api/") or path == "/" for path in _paths(app))


# --- No solution and no sentinel in any response ---------------------------


def _responses(client: TestClient, room: Room) -> list[Any]:
    """Every response of both routes: the view, each photo, one index past the end and an unknown room."""
    paths = [f"/api/rooms/{room.id}", *(f"/api/rooms/{room.id}/photos/{i}" for i in range(len(room.photos) + 1))]
    paths += [f"/api/rooms/{UNKNOWN}", f"/api/rooms/{UNKNOWN}/photos/0"]
    return [client.get(path) for path in paths]


def test_no_response_of_either_route_carries_a_solution_key_or_a_sentinel(tmp_path: Path, four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    assert SENTINEL_CODE in room.model_dump_json()
    responses = _responses(TestClient(make_app(tmp_path, room)), room)
    assert [r.status_code for r in responses] == [200, *[200] * len(room.photos), 404, 404, 404]
    sentinels = [SENTINEL_CODE, json.dumps(SENTINEL_ORDER)[1:-1], *SENTINEL_PAIR, SENTINEL_FIND, *SENTINEL_IX]
    for response in responses:
        assert b"solution" not in response.content
        assert all(sentinel.encode() not in response.content for sentinel in sentinels)
        if response.headers["content-type"].startswith("application/json"):
            assert "solution" not in json_keys(response.json())
