"""Decision 37: an error answer never echoes what the client sent, a dict key or a room id included, and an unknown `/api/` path answers 404 in the envelope (AD-13)."""

from collections.abc import Iterator
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.domain.schema import Derived, Profile, SessionStart
from tests.api.test_app import make_app
from tests.api.test_profile import ROOM_1, ROOM_2, room_result

SENTINEL = "sk-live-0123456789abcdef"
FRESH = Derived.fresh().model_dump(mode="json")
REQUESTS: dict[str, tuple[str, str, type[BaseModel], dict[str, Any]]] = {
    "start session": ("POST", "/api/sessions", SessionStart, {"room_id": ROOM_1, "derived": FRESH}),
    "put profile": ("PUT", "/api/profile/demo", Profile, {"results": {}, "derived": FRESH}),
}
"""Every request model the API accepts that holds a dict-typed field, with a body it accepts; the posted events and the access check hold none."""


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(make_app(tmp_path))


def dict_fields(model: type[BaseModel], prefix: tuple[str, ...] = ()) -> Iterator[tuple[str, ...]]:
    """The path of every dict-typed field reachable from `model` through nested models."""
    for name, field in model.model_fields.items():
        yield from _dict_fields(field.annotation, (*prefix, name))


def _dict_fields(annotation: Any, path: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    if get_origin(annotation) is dict:
        yield path
    elif get_origin(annotation) in (Union, UnionType):
        for arg in get_args(annotation):
            yield from _dict_fields(arg, path)
    elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
        yield from dict_fields(annotation, path)


def with_sentinel_key(body: dict[str, Any], path: tuple[str, ...], value: Any) -> dict[str, Any]:
    *parents, last = path
    copy: dict[str, Any] = {**body}
    node = copy
    for name in parents:
        node[name] = {**node[name]}
        node = node[name]
    node[last] = {**node[last], SENTINEL: value}
    return copy


CASES = [
    pytest.param(method, url, with_sentinel_key(body, path, value), id=f"{name}:{'.'.join(path)}:{label}")
    for name, (method, url, model, body) in REQUESTS.items()
    for path in dict_fields(model)
    for label, value in {"number": 1, "text": "x", "room result": room_result(ROOM_1)}.items()
]


def test_every_request_model_with_a_dict_field_is_probed():
    assert {name: list(dict_fields(model)) for name, (_, _, model, _) in REQUESTS.items()} == {
        "start session": [("derived", "mean_rung_per_lock_type")],
        "put profile": [("results",), ("derived", "mean_rung_per_lock_type")],
    }


@pytest.mark.parametrize(("method", "url", "body"), CASES)
def test_a_key_sent_in_any_dict_field_never_appears_in_the_422(client: TestClient, method: str, url: str, body: dict[str, Any]):
    response = client.request(method, url, json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] in ("invalid_request", "invalid_profile")
    assert SENTINEL not in response.text, response.text


def test_the_start_session_422_names_the_declared_field_path(client: TestClient):
    body = with_sentinel_key(REQUESTS["start session"][3], ("derived", "mean_rung_per_lock_type"), 1)
    message = client.post("/api/sessions", json=body).json()["error"]["message"]
    assert message.startswith("body.derived.mean_rung_per_lock_type: "), message


def test_a_profile_result_keyed_by_another_room_names_neither_room(client: TestClient):
    response = client.put("/api/profile/demo", json={"results": {ROOM_2: room_result(ROOM_1)}, "derived": FRESH})
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_profile"
    assert ROOM_1 not in response.text and ROOM_2 not in response.text, response.text


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_an_unknown_api_path_answers_404_in_the_envelope(client: TestClient, method: str):
    response = client.request(method, f"/api/nope/{SENTINEL}", json={SENTINEL: 1} if method != "GET" else None)
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": ANY, "stage": None}}
    assert SENTINEL not in response.text


def test_the_web_app_is_still_served_beside_the_unknown_api_answer(tmp_path: Path):
    dist = tmp_path / "web" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=\"app\"></div>")
    (dist / "assets" / "app.js").write_text("console.log('keyframe')")
    client = TestClient(make_app(tmp_path, web_dist=dist))
    assert client.get("/").text == (dist / "index.html").read_text()
    assert client.get("/assets/app.js").text == "console.log('keyframe')"
    assert client.get("/api/nope").json()["error"]["code"] == "not_found"
