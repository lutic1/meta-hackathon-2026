"""Story 7.11: the hosted access guard on `POST /builds` and `GET /builds/<job_id>/room`, and the quota refusal (AD-3, AD-9, AD-13).

The hosted app is `MODE=hosted` over plain dicts and a temporary Volume
directory, so the 7.10 slot claims run offline.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from src.api.errors import AccessDenied
from src.api.wiring import ACCESS_HEADER, access_guard, job_store
from src.config import Settings
from src.domain.schema import JobState, Room
from src.infra.modal import BUILD_QUOTA, ROOMS_DIR, SLOT_KEYS, hosted_stores, slot_key
from src.pipeline.build import new_id
from tests.api.hosted import hosted_handles, hosted_settings, make_hosted_app
from tests.api.test_app import make_app
from tests.api.test_builds import Stages, files, wait_terminal
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import SENTINEL_CODE, with_sentinel_solutions
from tests.pipeline.uploads import make_uploads

SRC = Path(__file__).resolve().parents[2] / "src"
CODE = "lantern-42"
ACCESS_DENIED = {"error": {"code": "access_denied", "message": ANY, "stage": None}}
QUOTA_EXCEEDED = {"error": {"code": "build_quota_exceeded", "message": ANY, "stage": None}}
WRONG = {"no header": {}, "a wrong code": {ACCESS_HEADER: "lantern-41"}, "an empty code": {ACCESS_HEADER: ""}}


class Hosted:
    """The `MODE=hosted` app over `tmp_path`: the Dict job store, the stage doubles, and every Room it was given seeded as a Demo room."""

    def __init__(self, tmp_path: Path, *rooms: Room, access_code: str | None = CODE) -> None:
        handles = hosted_handles(tmp_path)
        self.dict = handles.jobs
        self.jobs = hosted_stores(handles).jobs
        self.stages = Stages()
        self.rooms = handles.root / ROOMS_DIR
        settings = hosted_settings(**({"ACCESS_CODE": access_code} if access_code else {}))
        self.client = TestClient(make_hosted_app(tmp_path, handles, *rooms, settings=settings, stages=self.stages.functions()))

    def stored(self) -> set[Path]:
        """Every file the Volume holds under `rooms/`."""
        return {path for path in self.rooms.rglob("*") if path.is_file()} if self.rooms.exists() else set()

    def claim_all(self) -> None:
        for _ in range(BUILD_QUOTA):
            self.jobs.reserve_build(new_id("job"))

    def done(self, room: Room) -> JobState:
        """A `done` job record naming `room`, as a finished Build leaves it."""
        state = JobState(id=new_id("job"), status="done", room_id=room.id, regen_max=2)
        self.jobs.put(state)
        return state


def post(client: TestClient, headers: dict[str, str], count: int = 6) -> Response:
    return client.post("/api/builds", files=files(make_uploads(count)), headers=headers)


# --- POST /builds without the right code: 403 before anything is stored ---------


@pytest.mark.parametrize("headers", WRONG.values(), ids=WRONG.keys())
def test_a_build_without_the_right_code_is_refused_before_any_photo_job_or_slot(tmp_path: Path, headers: dict[str, str]):
    hosted = Hosted(tmp_path)
    response = post(hosted.client, headers)
    assert response.status_code == 403 and response.json() == ACCESS_DENIED
    assert hosted.jobs.list_ids() == [] and hosted.jobs.builds_left() == BUILD_QUOTA and hosted.dict.writes == []
    assert hosted.stored() == set() and hosted.stages.calls == []


def test_without_an_access_code_configured_every_code_is_refused(tmp_path: Path):
    hosted = Hosted(tmp_path, access_code=None)
    for headers in ({}, {ACCESS_HEADER: ""}, {ACCESS_HEADER: CODE}):
        assert post(hosted.client, headers).json() == ACCESS_DENIED
    assert hosted.dict.writes == [] and hosted.stored() == set()


def test_a_build_with_the_right_code_claims_one_slot_and_is_queued(tmp_path: Path):
    hosted = Hosted(tmp_path)
    response = post(hosted.client, {ACCESS_HEADER: CODE})
    assert response.status_code == 202 and response.json()["status"] == "queued"
    job_id = response.json()["id"]
    assert hosted.jobs.builds_left() == BUILD_QUOTA - 1 and hosted.dict[slot_key(1)] == job_id
    assert hosted.jobs.read(job_id).status == "queued" and hosted.stages.calls == []  # `run_build` (7.8) runs the stages


# --- GET /builds/<job_id>/room: the full Room only with the right code -------------


@pytest.mark.parametrize("headers", WRONG.values(), ids=WRONG.keys())
def test_the_full_room_without_the_right_code_is_refused_and_returns_no_part_of_it(
    tmp_path: Path, four_lock_room: Room, headers: dict[str, str]
):
    room = with_sentinel_solutions(four_lock_room)
    hosted = Hosted(tmp_path, room)
    state = hosted.done(room)
    response = hosted.client.get(f"/api/builds/{state.id}/room", headers=headers)
    assert response.status_code == 403 and response.json() == ACCESS_DENIED
    assert SENTINEL_CODE not in response.text and room.id not in response.text


def test_the_full_room_with_the_right_code_is_the_whole_room(tmp_path: Path, four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    hosted = Hosted(tmp_path, room)
    state = hosted.done(room)
    response = hosted.client.get(f"/api/builds/{state.id}/room", headers={ACCESS_HEADER: CODE})
    assert response.status_code == 200 and Room.model_validate(response.json()) == room
    assert SENTINEL_CODE in response.text


def test_the_guard_runs_before_the_job_lookup_so_an_unknown_job_is_refused_alike(tmp_path: Path):
    hosted = Hosted(tmp_path)
    response = hosted.client.get(f"/api/builds/{new_id('job')}/room")
    assert response.status_code == 403 and response.json() == ACCESS_DENIED


# --- Every other route answers without a code, with no solution in it -------------


def _open_responses(client: TestClient, room: Room, job_id: str) -> list[Response]:
    """One call of each open route this codebase serves, none carrying `X-Access-Code`."""
    started = client.post("/api/sessions", json={"room_id": room.id})
    session_id = started.json()["id"]
    click = {"type": "click", "interactable_id": room.interactables[0].id}
    return [
        client.get("/api/rooms"),
        client.get(f"/api/rooms/{room.id}"),
        client.get(f"/api/rooms/{room.id}/photos/0"),
        started,
        client.get(f"/api/sessions/{session_id}"),
        client.post(f"/api/sessions/{session_id}/events", json=click),
        client.get(f"/api/sessions/{session_id}/result"),
        client.get(f"/api/builds/{job_id}"),
        client.get("/api/schema"),
        client.get("/api/meta"),
    ]


def test_every_open_route_answers_without_a_code_and_carries_no_solution(tmp_path: Path, four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    hosted = Hosted(tmp_path, room)
    state = hosted.done(room)
    responses = _open_responses(hosted.client, room, state.id)
    assert [r.status_code for r in responses] == [200] * len(responses), [r.text for r in responses]
    assert hosted.client.get("/api/rooms").json()[0]["job_id"] == state.id
    for response in responses:
        assert SENTINEL_CODE.encode() not in response.content
        if response.headers["content-type"].startswith("application/json") and response.request.url.path != "/api/schema":
            assert "solution" not in json_keys(response.json())


# --- The 21st build: build_quota_exceeded, and the Demo rooms stay open ------------


def test_the_21st_build_with_the_right_code_is_refused_with_the_quota_and_stores_nothing(tmp_path: Path, four_lock_room: Room):
    hosted = Hosted(tmp_path, four_lock_room)
    hosted.done(four_lock_room)
    hosted.claim_all()
    before, writes = hosted.stored(), list(hosted.dict.writes)

    response = post(hosted.client, {ACCESS_HEADER: CODE})

    assert response.status_code == 403 and response.json() == QUOTA_EXCEEDED
    assert hosted.stored() == before and hosted.dict.writes == writes and hosted.stages.calls == []
    assert len(hosted.jobs.list_ids()) == 1 and hosted.jobs.builds_left() == 0
    assert [summary["room_id"] for summary in hosted.client.get("/api/rooms").json()] == [four_lock_room.id]
    started = hosted.client.post("/api/sessions", json={"room_id": four_lock_room.id})
    assert started.status_code == 200 and hosted.client.get(f"/api/sessions/{started.json()['id']}").status_code == 200


def test_the_quota_refusal_still_needs_the_right_code_first(tmp_path: Path):
    hosted = Hosted(tmp_path)
    hosted.claim_all()
    assert post(hosted.client, {ACCESS_HEADER: "lantern-41"}).json() == ACCESS_DENIED


# --- Ingest refuses before the slot claim ---------------------------------------


@pytest.mark.parametrize("count", [5, 11])
def test_an_upload_ingest_refuses_claims_no_slot_and_stores_nothing(tmp_path: Path, count: int):
    hosted = Hosted(tmp_path)
    response = post(hosted.client, {ACCESS_HEADER: CODE}, count)
    assert response.status_code == 422 and response.json()["error"]["code"] == "photo_count"
    assert hosted.dict.writes == [] and not SLOT_KEYS & set(hosted.dict) and hosted.stored() == set()


def test_an_ingest_refusal_with_every_slot_taken_is_still_the_ingest_refusal(tmp_path: Path):
    hosted = Hosted(tmp_path)
    hosted.claim_all()
    assert post(hosted.client, {ACCESS_HEADER: CODE}, 5).json()["error"]["code"] == "photo_count"


# --- Local mode: no code check and no quota ----------------------------------------


def test_local_mode_serves_both_guarded_routes_with_no_code_even_with_one_configured(tmp_path: Path, four_lock_room: Room):
    stages = Stages()
    settings = Settings.from_env({"GUIDE": "verbatim", "ACCESS_CODE": CODE})
    client = TestClient(make_app(tmp_path, four_lock_room, settings=settings, stages=stages.functions()))
    response = post(client, {})
    assert response.status_code == 202 and wait_terminal(client, response.json()["id"])["status"] == "done"
    state = JobState(id=new_id("job"), status="done", room_id=four_lock_room.id, regen_max=2)
    job_store(tmp_path / "rooms").put(state)
    full = client.get(f"/api/builds/{state.id}/room")
    assert full.status_code == 200 and Room.model_validate(full.json()) == four_lock_room


def test_the_local_job_store_never_refuses_a_build(tmp_path: Path):
    app = make_app(tmp_path, stages=Stages().functions())
    client = TestClient(app)
    for _ in range(BUILD_QUOTA + 1):
        assert post(client, {}).status_code == 202
    assert job_store(tmp_path / "rooms").builds_left() is None


# --- Wiring injects the guard from Settings; no route handler reads the mode -------


def test_the_local_guard_lets_every_code_through():
    guard = access_guard(Settings.from_env({"ACCESS_CODE": CODE}), hosted=False)
    for code in (None, "", "wrong", CODE):
        guard(code)


def test_the_hosted_guard_accepts_only_the_configured_code():
    guard = access_guard(Settings.from_env({"ACCESS_CODE": CODE}), hosted=True)
    guard(CODE)
    for code in (None, "", "wrong", CODE.upper(), f"{CODE} ", CODE[:-1]):
        with pytest.raises(AccessDenied):
            guard(code)


def test_the_hosted_guard_without_a_configured_code_refuses_every_code():
    guard = access_guard(Settings.from_env({}), hosted=True)
    for code in (None, "", "anything"):
        with pytest.raises(AccessDenied):
            guard(code)


def _reads(attr: str) -> set[str]:
    """Every module under src/ that reads `<x>.<attr>`."""
    out: set[str] = set()
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        if any(isinstance(node, ast.Attribute) and node.attr == attr for node in ast.walk(tree)):
            out.add(str(path.relative_to(SRC)))
    return out


def test_only_wiring_reads_the_access_code_and_the_build_routes_take_the_guard_not_the_mode():
    assert _reads("access_code") == {"api/wiring.py"}
    tree = ast.parse((SRC / "api" / "app.py").read_text())
    routes = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_routes")
    names = {getattr(node, "id", None) or getattr(node, "arg", None) or getattr(node, "attr", None) for node in ast.walk(routes)}
    assert "guard" in names and not names & {"hosted", "mode", "access_code", "settings"}

