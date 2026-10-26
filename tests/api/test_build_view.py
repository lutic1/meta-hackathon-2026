"""Story 2.28: `GET /builds/<job_id>/view` serves the `BuildView` of a `done` job to anyone with the link (AD-3, AD-13, AD-15)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, get_args
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient

from src.api.errors import ApiError, BuildNotReady, JobNotFound, RoomNotFound, envelope
from src.api.meta import disclosure_lines
from src.api.wiring import ACCESS_HEADER, job_store
from src.config import Settings
from src.domain.redact import to_build_view
from src.domain.schema import (
    BuildView,
    DryRunAnswer,
    DryRunAnswers,
    JobState,
    JobStatus,
    Room,
)
from src.infra.modal import hosted_stores
from src.pipeline.build import new_id
from tests.api.hosted import hosted_handles, hosted_settings, make_hosted_app
from tests.api.test_app import make_app
from tests.domain.test_redact import done_job, json_keys
from tests.fixtures.rooms import (
    SENTINEL_CODE,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)

SRC = Path(__file__).resolve().parents[2] / "src"
WEB_SCHEMA = Path(__file__).resolve().parents[2] / "web" / "types" / "schema.json"
CODE = "lantern-42"
DEMO_ENV = {"DEMO_TIMESCALE": "6", "DEMO_TRICKSTER": "scripted"}
NOT_DONE = sorted(set(get_args(JobStatus)) - {"done"})


def settings(**env: str) -> Settings:
    return Settings.from_env({"GUIDE": "verbatim", **env})


def view_client(tmp_path: Path, room: Room | None, *jobs: JobState, hosted: bool = False, **env: str) -> TestClient:
    """The Local app, or the `MODE=hosted` one over plain dicts, with one stored Room (or none) and the given job records."""
    rooms = [room] if room else []
    if not hosted:
        app = make_app(tmp_path, *rooms, settings=settings(**env))
        for job in jobs:
            job_store(tmp_path / "rooms").put(job)
        return TestClient(app)
    handles = hosted_handles(tmp_path)
    app = make_hosted_app(tmp_path, handles, *rooms, settings=hosted_settings(**env))
    for job in jobs:
        hosted_stores(handles).jobs.put(job)
    return TestClient(app)


def not_done(status: JobStatus) -> JobState:
    """A known job in `status`; only `running` names a stage."""
    return JobState(
        id=new_id("job"), status=status, stage="author" if status == "running" else None, room_id=new_id("room"), regen_max=2
    )


# --- A done job: 200 with the BuildView, its Disclosure list from meta.py ------------


@pytest.mark.parametrize("env", [{}, DEMO_ENV], ids=["defaults", "demo"])
def test_a_done_job_answers_200_with_its_build_view_and_the_rooms_disclosure_list(
    tmp_path: Path, four_lock_room: Room, env: dict[str, str]
):
    job = done_job(four_lock_room)
    response = view_client(tmp_path, four_lock_room, job, **env).get(f"/api/builds/{job.id}/view")
    assert response.status_code == 200, response.text
    disclosure = disclosure_lines(settings(**env), four_lock_room, job)
    assert response.json() == to_build_view(four_lock_room, job, disclosure=disclosure).model_dump(mode="json")
    assert BuildView.model_validate(response.json()).disclosure == disclosure
    assert "This room was built earlier" in disclosure[-1]  # the job's calls include one served from the Cache


# --- Open in both modes: never behind X-Access-Code -----------------------------------


@pytest.mark.parametrize("hosted", [False, True], ids=["local", "hosted"])
@pytest.mark.parametrize("headers", [{}, {ACCESS_HEADER: "lantern-41"}, {ACCESS_HEADER: CODE}], ids=["none", "wrong", "right"])
def test_the_view_answers_in_either_mode_whatever_access_code_is_sent(
    tmp_path: Path, four_lock_room: Room, hosted: bool, headers: dict[str, str]
):
    job = done_job(four_lock_room)
    client = view_client(tmp_path, four_lock_room, job, hosted=hosted, ACCESS_CODE=CODE)
    response = client.get(f"/api/builds/{job.id}/view", headers=headers)
    assert response.status_code == 200, response.text
    if hosted:  # the guarded route beside it does refuse here, so the guard is live
        assert client.get(f"/api/builds/{job.id}/room").json()["error"]["code"] == "access_denied"


def test_the_view_route_takes_no_access_guard():
    tree = ast.parse((SRC / "api" / "app.py").read_text())
    routes = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_view_routes")
    names = {getattr(node, "id", None) or getattr(node, "arg", None) or getattr(node, "attr", None) for node in ast.walk(routes)}
    assert not names & {"guard", "access_guard", "ACCESS_HEADER", "hosted", "mode", "access_code"}


# --- Unknown job: 404 ----------------------------------------------------------------


def test_an_unknown_job_answers_404(tmp_path: Path):
    client = view_client(tmp_path, None)
    for job_id in (new_id("job"), "not-a-job"):
        response = client.get(f"/api/builds/{job_id}/view")
        assert response.status_code == 404
        assert response.json() == {"error": {"code": "job_not_found", "message": ANY, "stage": None}}


def test_a_done_job_whose_room_is_not_stored_answers_room_not_found(tmp_path: Path, four_lock_room: Room):
    job = done_job(four_lock_room)
    response = view_client(tmp_path, None, job).get(f"/api/builds/{job.id}/view")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "room_not_found", "message": ANY, "stage": None}}


# --- Not done: 409 build_not_ready with the job status --------------------------------


@pytest.mark.parametrize("status", NOT_DONE)
def test_a_job_not_yet_done_answers_409_build_not_ready_with_its_status(tmp_path: Path, four_lock_room: Room, status: JobStatus):
    job = not_done(status)
    response = view_client(tmp_path, four_lock_room, job).get(f"/api/builds/{job.id}/view")
    assert response.status_code == 409
    assert response.json() == {"error": {"code": "build_not_ready", "message": ANY, "stage": None}, "status": status}


def test_status_appears_on_build_not_ready_only(tmp_path: Path, four_lock_room: Room):
    client = view_client(tmp_path, four_lock_room, hosted=True, ACCESS_CODE=CODE)
    others = [
        client.get(f"/api/builds/{new_id('job')}/view"),  # job_not_found
        client.get(f"/api/rooms/{new_id('room')}"),  # room_not_found
        client.get(f"/api/builds/{new_id('job')}/room"),  # access_denied
        client.post("/api/sessions", json={}),  # invalid_request
    ]
    assert [r.json()["error"]["code"] for r in others] == ["job_not_found", "room_not_found", "access_denied", "invalid_request"]
    assert all(set(r.json()) == {"error"} for r in others)
    errors: list[ApiError] = [JobNotFound("job_x"), RoomNotFound("room_x"), BuildNotReady("job_x", "running")]
    assert [envelope(e).model_dump(mode="json", exclude_unset=True).get("status") for e in errors] == [None, None, "running"]


# --- API sentinel test: no solution, pairing or Dry run answer --------------------------


def test_the_view_holds_no_solution_sentinel_pairing_or_dry_run_answer(tmp_path: Path, four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    assert SENTINEL_CODE in room.model_dump_json()  # the sentinels are in the stored Room
    assert {ix.id for ix in room.interactables}.isdisjoint(SENTINEL_IX)  # and nowhere else in it
    answers = DryRunAnswers(answers=[DryRunAnswer(puzzle_id=p.id, answer=p.solution) for p in room.puzzles])
    job = done_job(room)
    response = view_client(tmp_path, room, job, **DEMO_ENV).get(f"/api/builds/{job.id}/view")
    assert response.status_code == 200, response.text
    data: Any = response.json()
    text = response.text
    assert "solution" not in json_keys(data) and b"solution" not in response.content
    assert json_keys(data).isdisjoint(("answer", "answers", "clue", "evidence", "code", "item", "target"))
    assert SENTINEL_CODE not in text and all(ix not in text for ix in SENTINEL_IX)
    assert json.dumps(SENTINEL_ORDER)[1:-1] not in text and json.dumps(list(SENTINEL_PAIR))[1:-1] not in text
    for answer in answers.answers:
        assert json.dumps(answer.answer.model_dump(mode="json")) not in text
    for puzzle in room.puzzles:
        assert puzzle.clue not in text and puzzle.evidence.visible_attribute not in text


# --- GET /schema carries BuildView and web/types matches it ---------------------------


def test_the_schema_serves_build_view_as_committed_in_web_types(tmp_path: Path):
    served = view_client(tmp_path, None).get("/api/schema").json()["$defs"]
    committed = json.loads(WEB_SCHEMA.read_text())["$defs"]
    assert served["BuildView"] == committed["BuildView"]
    assert "export interface BuildView {" in (WEB_SCHEMA.parent / "index.ts").read_text()
