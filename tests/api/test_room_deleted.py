"""Story 7.20: a deleted Judge room answers 410 `room_deleted`, an unknown id 404 (AD-9, AD-13, FR-33).

The hosted app runs over plain dicts and a temporary Volume directory. The
Judge room is built by the real `Build` over the hosted stores (Story 7.14)
and deleted by `delete_judge_room` (Story 7.18), so the record the routes
read is the one the purge writes; no test reaches Modal.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import ANY

from fastapi.testclient import TestClient
from httpx import Response

from src.api.wiring import ACCESS_HEADER
from src.domain.schema import JobState, Room
from src.infra.local import DiskArtifactStore
from src.infra.modal import (
    DeletionRecord,
    delete_judge_room,
    deletion_record_path,
    hosted_stores,
)
from src.pipeline.build import new_id
from tests.api.hosted import hosted_handles, hosted_settings, make_hosted_app
from tests.api.test_app import ROOM_NOT_FOUND, UNKNOWN, make_app
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import SENTINEL_CODE, with_sentinel_solutions
from tests.infra.test_clocks import Ticker
from tests.infra.test_modal import seed_demo
from tests.infra.test_modal_partitions import JudgeBuild

CODE = "lantern-42"
NOV_10 = date(2026, 11, 10)
UNKNOWN_JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ROOM_DELETED = {"error": {"code": "room_deleted", "message": ANY, "stage": None}}
JOB_NOT_FOUND = {"error": {"code": "job_not_found", "message": ANY, "stage": None}}
UNKNOWN_SESSION = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SESSION_NOT_FOUND = {"error": {"code": "session_not_found", "message": ANY, "stage": None}}


class Scene:
    """A hosted app over one seeded Demo room with its job record and one Judge room a real Build stored."""

    def __init__(self, tmp_path: Path, judge_room: Room, demo_room: Room) -> None:
        self.handles = hosted_handles(tmp_path)
        self.demo_room = demo_room
        self.demo_job = JobState(id=new_id("job"), status="done", room_id=demo_room.id, regen_max=2)
        seed_demo(self.handles, demo_room, self.demo_job)
        self.judge = JudgeBuild(self.handles, Ticker(), judge_room)
        self.judge_job = self.judge.run()
        assert self.judge_job.status == "done"
        app = make_hosted_app(tmp_path, self.handles, settings=hosted_settings(ACCESS_CODE=CODE))
        self.client = TestClient(app)

    @property
    def judge_room_id(self) -> str:
        return self.judge.room_id

    def delete_judge_room(self) -> DeletionRecord:
        return delete_judge_room(self.handles, self.judge_room_id, today=NOV_10)


def room_calls(client: TestClient, room_id: str) -> dict[str, Response]:
    """Each room-keyed route, called with `room_id`."""
    return {
        "GET /rooms/<room_id>": client.get(f"/api/rooms/{room_id}"),
        "GET /rooms/<room_id>/photos/0": client.get(f"/api/rooms/{room_id}/photos/0"),
        "POST /sessions": client.post("/api/sessions", json={"room_id": room_id}),
    }


def job_calls(client: TestClient, job_id: str) -> dict[str, Response]:
    """Each job-keyed route, called with `job_id`; the guarded `/room` carries the right code."""
    return {
        "GET /builds/<job_id>": client.get(f"/api/builds/{job_id}"),
        "GET /builds/<job_id>/view": client.get(f"/api/builds/{job_id}/view"),
        "GET /builds/<job_id>/room": client.get(f"/api/builds/{job_id}/room", headers={ACCESS_HEADER: CODE}),
    }


def answers(calls: dict[str, Response]) -> dict[str, tuple[int, Any]]:
    return {name: (response.status_code, response.json()) for name, response in calls.items()}


def assert_served_without_a_solution(calls: dict[str, Response]) -> None:
    """Every call answered 200 and, but for the guarded full Room (AD-3), carries no `solution` key or sentinel."""
    assert {name: r.status_code for name, r in calls.items()} == dict.fromkeys(calls, 200), [r.text for r in calls.values()]
    for name, response in calls.items():
        if name == "GET /builds/<job_id>/room":
            continue
        assert SENTINEL_CODE.encode() not in response.content and b"solution" not in response.content, name
        if response.headers["content-type"].startswith("application/json"):
            assert "solution" not in json_keys(response.json()), name


# --- A deleted Judge room: 410 room_deleted on every room-keyed and job-keyed route --------


def test_a_deleted_judge_room_id_answers_410_room_deleted_on_every_room_keyed_route(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    record = scene.delete_judge_room()
    assert record.room_id == scene.judge_room_id
    found = answers(room_calls(scene.client, scene.judge_room_id))
    assert found == dict.fromkeys(found, (410, ROOM_DELETED))
    assert all(scene.judge_room_id in body["error"]["message"] for _, body in found.values())


def test_the_deleted_rooms_job_id_answers_410_room_deleted_on_every_job_keyed_route(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    assert scene.delete_judge_room().job_id == scene.judge_job.id
    found = answers(job_calls(scene.client, scene.judge_job.id))
    assert found == dict.fromkeys(found, (410, ROOM_DELETED))


def test_the_guarded_room_route_still_refuses_a_missing_code_before_answering_410(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    scene.delete_judge_room()
    response = scene.client.get(f"/api/builds/{scene.judge_job.id}/room")
    assert response.status_code == 403 and response.json()["error"]["code"] == "access_denied"


def test_a_record_that_names_no_job_still_answers_410_for_its_room_id(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    gone = new_id("room")
    record = DeletionRecord(room_id=gone, job_id=None, deleted_on=NOV_10)
    hosted_stores(scene.handles).artifacts.files.write(deletion_record_path(gone), record.model_dump_json().encode())
    found = answers(room_calls(scene.client, gone))
    assert found == dict.fromkeys(found, (410, ROOM_DELETED))


def test_a_session_still_open_on_a_deleted_judge_room_answers_410_on_its_room_read(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    started = scene.client.post("/api/sessions", json={"room_id": scene.judge_room_id})
    assert started.status_code == 200, started.text
    session_id = started.json()["id"]
    assert scene.client.get(f"/api/sessions/{session_id}/room").status_code == 200
    scene.delete_judge_room()
    response = scene.client.get(f"/api/sessions/{session_id}/room")
    assert (response.status_code, response.json()) == (410, ROOM_DELETED)


def session_calls(client: TestClient, session_id: str) -> dict[str, Response]:
    """Each session-keyed route a bookmarked Play or Done page reaches, called with `session_id`."""
    return {
        "GET /sessions/<id>": client.get(f"/api/sessions/{session_id}"),
        "GET /sessions/<id>/room": client.get(f"/api/sessions/{session_id}/room"),
        "GET /sessions/<id>/result": client.get(f"/api/sessions/{session_id}/result"),
        "POST /sessions/<id>/events": client.post(f"/api/sessions/{session_id}/events", json={"type": "hint_request"}),
        "POST /sessions/<id>/trickster": client.post(f"/api/sessions/{session_id}/trickster"),
    }


def started_session(scene: Scene) -> str:
    started = scene.client.post("/api/sessions", json={"room_id": scene.judge_room_id})
    assert started.status_code == 200, started.text
    return started.json()["id"]


def test_every_session_route_of_a_session_still_open_on_a_deleted_judge_room_answers_410(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    """Decision 58: the Play and Done paths of a session open in this process show the deletion notice, never a blank 404."""
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    session_id = started_session(scene)
    scene.delete_judge_room()
    found = answers(session_calls(scene.client, session_id))
    assert found == dict.fromkeys(found, (410, ROOM_DELETED))


def test_a_restarted_app_answers_410_for_a_session_its_judge_rooms_deletion_took(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    """The session's log and header are gone; the ids-only deletion record still names it, so a bookmark tells deleted from unknown."""
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    session_id = started_session(scene)
    record = scene.delete_judge_room()
    assert record.session_ids == [session_id] and scene.handles.sessions == {}
    restarted = TestClient(make_hosted_app(tmp_path, scene.handles, settings=hosted_settings(ACCESS_CODE=CODE)))
    found = answers(session_calls(restarted, session_id))
    assert found == dict.fromkeys(found, (410, ROOM_DELETED))
    assert all(scene.judge_room_id in body["error"]["message"] for _, body in found.values())


def test_the_record_keeps_only_ids_and_the_date_for_the_sessions_it_routes(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    first, second = started_session(scene), started_session(scene)
    scene.delete_judge_room()
    raw = json.loads((scene.handles.root / deletion_record_path(scene.judge_room_id)).read_bytes())
    assert raw == {"room_id": scene.judge_room_id, "job_id": scene.judge_job.id, "deleted_on": "2026-11-10", "session_ids": sorted([first, second])}
    artifacts = hosted_stores(scene.handles).artifacts
    assert artifacts.deleted_room(first) == artifacts.deleted_room(second) == scene.judge_room_id


def test_an_unknown_session_stays_404_session_not_found_beside_a_deletion_record(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    started_session(scene)
    scene.delete_judge_room()
    found = answers(session_calls(scene.client, UNKNOWN_SESSION))
    assert found == dict.fromkeys(found, (404, SESSION_NOT_FOUND))


def test_a_session_on_the_demo_room_plays_on_once_a_judge_room_is_deleted(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    started = scene.client.post("/api/sessions", json={"room_id": scene.demo_room.id})
    scene.delete_judge_room()
    calls = session_calls(scene.client, started.json()["id"])
    assert {name: r.status_code for name, r in calls.items()} == dict.fromkeys(calls, 200), [r.text for r in calls.values()]


# --- An id with no Room and no record: 404 -------------------------------------------------


def test_an_unknown_room_id_answers_404_room_not_found_beside_a_deletion_record(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    scene.delete_judge_room()
    found = answers(room_calls(scene.client, UNKNOWN))
    assert found == dict.fromkeys(found, (404, ROOM_NOT_FOUND))


def test_an_unknown_job_id_keeps_its_404_job_not_found(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    scene.delete_judge_room()
    found = answers(job_calls(scene.client, UNKNOWN_JOB))
    assert found == dict.fromkeys(found, (404, JOB_NOT_FOUND))


# --- A Demo room and a Judge room not yet deleted answer as before ---------------------------


def test_a_demo_room_and_a_live_judge_room_answer_as_before_with_no_solution(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, with_sentinel_solutions(four_lock_room), with_sentinel_solutions(code_and_find_room))
    assert_served_without_a_solution(room_calls(scene.client, scene.judge_room_id) | job_calls(scene.client, scene.judge_job.id))
    assert_served_without_a_solution(room_calls(scene.client, scene.demo_room.id) | job_calls(scene.client, scene.demo_job.id))
    full = scene.client.get(f"/api/builds/{scene.judge_job.id}/room", headers={ACCESS_HEADER: CODE})
    assert Room.model_validate(full.json()).id == scene.judge_room_id  # the guarded full Room, as before (AD-3)


def test_the_demo_room_answers_as_before_once_a_judge_room_is_deleted(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, with_sentinel_solutions(code_and_find_room))
    scene.delete_judge_room()
    assert_served_without_a_solution(room_calls(scene.client, scene.demo_room.id) | job_calls(scene.client, scene.demo_job.id))


# --- The store's lookup -------------------------------------------------------------------


def test_the_volume_store_names_the_deleted_room_by_its_room_id_or_its_job_id(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    scene = Scene(tmp_path, four_lock_room, code_and_find_room)
    artifacts = hosted_stores(scene.handles).artifacts
    assert artifacts.deleted_room(scene.judge_room_id) is None and artifacts.deleted_room(scene.judge_job.id) is None
    scene.delete_judge_room()
    assert artifacts.deleted_room(scene.judge_room_id) == scene.judge_room_id
    assert artifacts.deleted_room(scene.judge_job.id) == scene.judge_room_id
    assert artifacts.deleted_room(UNKNOWN) is None and artifacts.deleted_room(scene.demo_room.id) is None


def test_local_mode_keeps_no_deletion_record_so_an_unknown_room_stays_404(tmp_path: Path):
    gone = new_id("room")
    record = DeletionRecord(room_id=gone, job_id=None, deleted_on=NOV_10)
    path = tmp_path / "rooms" / "deleted" / f"{gone}.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(record.model_dump_json().encode())
    assert DiskArtifactStore(tmp_path / "rooms").deleted_room(gone) is None
    found = answers(room_calls(TestClient(make_app(tmp_path)), gone))
    assert found == dict.fromkeys(found, (404, ROOM_NOT_FOUND))
