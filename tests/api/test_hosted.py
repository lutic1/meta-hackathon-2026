"""Story 7.2: under `MODE=hosted` the same FastAPI app runs over the hosted adapters (AD-9, AD-13, AD-14, AD-15, FR-26).

The hosted route table is the local one without the profile routes;
`POST /builds` and `GET /builds/<job_id>/room` answer 403 `access_denied`
without the access code (the 7.11 guard wiring injects); a session takes `Derived.fresh()` whatever block it receives
and shows a Rung as written; no response carries a solution. The handles
are plain dicts and a temporary Volume directory, so nothing reaches Modal.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import ANY

import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from src.api import wiring
from src.api.app import trigger_events
from src.api.meta import HOSTED_LINE, RETENTION_HOSTED
from src.api.wiring import hint_phraser
from src.domain.schema import Derived, JobState, RungChangeEvent
from src.domain.session import SessionStateMachine
from src.infra.modal import DictSessionStore, ModalHandles, call_key, hosted_stores
from src.providers.verbatim import VerbatimPhraser
from tests.api.hosted import hosted_handles, hosted_settings, make_hosted_app
from tests.api.test_app import make_app
from tests.api.test_builds import post as post_build
from tests.api.test_sessions import FRESH_THRESHOLDS, Ticker, click, code, post
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import (
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)
from tests.pipeline.uploads import make_uploads

REPO = Path(__file__).resolve().parents[2]
JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAA"
UNKNOWN_JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ACCESS_DENIED = {"error": {"code": "access_denied", "message": ANY, "stage": None}}
PROFILE_ROUTES = {("GET", "/api/profile/{name}"), ("PUT", "/api/profile/{name}")}
WITHIN_BOUNDS = Derived(sessions=3, persistence=0.4173, time_to_first_hint_s=137.9, mean_rung_per_lock_type={"code": 2.71})
"""A returning block inside every bound, and not `Derived.fresh()`."""
SENTINEL_VALUES = ("0.4173", "137.9", "2.71")


def _never(*args: Any, **kwargs: Any) -> None:
    raise AssertionError("the Ollama adapter was constructed under MODE=hosted")


def _no_request(*args: Any, **kwargs: Any) -> None:
    raise AssertionError("an HTTP request was made under MODE=hosted")


@pytest.fixture
def handles(tmp_path: Path) -> ModalHandles:
    return hosted_handles(tmp_path)


@pytest.fixture
def no_guide_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fails the test if the Ollama adapter is built or an HTTP request goes out, loopback included (the test client has its own transport)."""
    monkeypatch.setattr(wiring, "OllamaPhraser", _never)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _no_request)


def _routes(app: FastAPI) -> set[tuple[str, str]]:
    """Every `(method, path)` the app's schema lists."""
    return {(method.upper(), path) for path, operations in app.openapi()["paths"].items() for method in operations}


# --- The route table and the static client ------------------------------------------------


def test_the_hosted_route_table_is_the_local_one_without_the_profile_routes_and_with_the_access_check(
    tmp_path: Path, handles: ModalHandles
):
    local, hosted = _routes(make_app(tmp_path)), _routes(make_hosted_app(tmp_path, handles))
    assert PROFILE_ROUTES <= local
    assert hosted == (local - PROFILE_ROUTES) | {("POST", "/api/access/check")}
    assert {("POST", "/api/builds"), ("GET", "/api/builds/{job_id}"), ("GET", "/api/builds/{job_id}/room")} <= hosted


def test_the_profile_routes_are_not_served(tmp_path: Path, handles: ModalHandles):
    client = TestClient(make_hosted_app(tmp_path, handles))
    assert client.get("/api/profile/dev").status_code == 404
    assert client.put("/api/profile/dev", json={}).status_code == 404
    assert not (tmp_path / "local-rooms").exists() and not handles.root.exists()


def test_web_dist_is_served_at_the_root_and_the_api_under_api_from_one_origin_with_no_cors(
    tmp_path: Path, handles: ModalHandles, code_and_find_room
):
    dist = tmp_path / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=\"app\"></div>")
    app = make_hosted_app(tmp_path, handles, code_and_find_room, web_dist=dist)
    client = TestClient(app)
    assert client.get("/").text == (dist / "index.html").read_text()
    assert client.get(f"/api/rooms/{code_and_find_room.id}").json()["id"] == code_and_find_room.id
    assert all(middleware.cls is not CORSMiddleware for middleware in app.user_middleware)
    response = client.get("/api/meta", headers={"Origin": "https://elsewhere.example"})
    assert response.json()["mode"] == "hosted" and "access-control-allow-origin" not in response.headers


def test_the_hosted_app_starts_without_the_local_export_or_a_job_restart(tmp_path: Path, handles: ModalHandles):
    with TestClient(make_hosted_app(tmp_path, handles)) as client:
        assert client.get("/api/meta").status_code == 200
    assert not (tmp_path / "local-spend").exists() and not (tmp_path / "local-rooms").exists()
    assert (handles.jobs, handles.sessions, handles.ledger) == ({}, {}, {})


def test_the_api_module_imports_under_mode_hosted_and_builds_no_app_without_the_handles():
    """The hosted entry imports `create_app` in a `MODE=hosted` container; the local `app` is built only when read."""
    code = "import src.api.app as m\ntry:\n    m.app\nexcept ValueError as error:\n    print('refused:', error)\n"
    env = {**os.environ, "MODE": "hosted", "GUIDE": "verbatim", "DEMO_TRICKSTER": ""}
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True, check=True)
    assert result.stdout.startswith("refused: MODE=hosted runs on Modal"), result.stdout + result.stderr


# --- The build routes are refused without the access code -----------------------------------


def test_post_builds_without_the_code_is_refused_with_403_and_no_photo_is_stored_and_no_job_created(
    tmp_path: Path, handles: ModalHandles, code_and_find_room
):
    client = TestClient(make_hosted_app(tmp_path, handles, code_and_find_room))
    before = sorted(handles.root.rglob("*"))
    response = post_build(client, make_uploads())
    assert response.status_code == 403 and response.json() == ACCESS_DENIED
    assert sorted(handles.root.rglob("*")) == before
    assert all(key.startswith("attempts:") for key in handles.jobs) and not (tmp_path / "local-rooms").exists()


@pytest.mark.parametrize("job_id", [JOB, UNKNOWN_JOB])
def test_the_full_room_download_without_the_code_is_refused_with_403_and_no_room_leaves(
    tmp_path: Path, handles: ModalHandles, four_lock_room, job_id: str
):
    room = with_sentinel_solutions(four_lock_room)
    client = TestClient(make_hosted_app(tmp_path, handles, room))
    hosted_stores(handles).jobs.put(JobState(id=JOB, status="done", room_id=room.id, regen_max=2))
    response = client.get(f"/api/builds/{job_id}/room")
    assert response.status_code == 403 and response.json() == ACCESS_DENIED
    assert b"solution" not in response.content and SENTINEL_CODE.encode() not in response.content


def test_the_job_state_route_is_served_from_the_dict(tmp_path: Path, handles: ModalHandles):
    client = TestClient(make_hosted_app(tmp_path, handles))
    hosted_stores(handles).jobs.put(JobState(id=JOB, status="running", stage="architect", regen_max=2))
    handles.jobs[call_key(JOB)] = "fc-1"  # its runner's call, which the watchdog polls as still running
    response = client.get(f"/api/builds/{JOB}")
    assert (response.status_code, response.json()["status"], response.json()["stage"]) == (202, "running", "architect")
    assert client.get(f"/api/builds/{UNKNOWN_JOB}").status_code == 404


# --- GET /meta ---------------------------------------------------------------------------------


def test_meta_reports_hosted_verbatim_no_guide_model_and_the_hosted_texts(tmp_path: Path, handles: ModalHandles):
    body = TestClient(make_hosted_app(tmp_path, handles)).get("/api/meta").json()
    assert body == {
        "mode": "hosted", "guide": "verbatim", "guide_model": None, "trickster": "live", "demo_timescale": 1,
        "cache": "on", "profile": "dev", "disclosure": [HOSTED_LINE], "retention": RETENTION_HOSTED,
    }


# --- A hosted session: fresh thresholds, nothing received stored, the Rung as written -----------


def test_a_hosted_session_computes_every_threshold_from_fresh_and_shows_the_rung_as_written(
    tmp_path: Path, handles: ModalHandles, code_and_find_room, no_guide_model: None
):
    ticker = Ticker()
    client = TestClient(make_hosted_app(tmp_path, handles, code_and_find_room, clock=ticker))
    assert WITHIN_BOUNDS != Derived.fresh()
    started = client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": WITHIN_BOUNDS.model_dump(mode="json")})
    assert started.status_code == 200, started.text
    session_id = started.json()["id"]
    assert started.json()["thresholds"] == FRESH_THRESHOLDS.model_dump()
    assert started.json()["opening_line"]["kind"] == "welcome" and started.json()["disclosure"] == [HOSTED_LINE]

    ticker.advance(4_000)
    hinted = post(client, session_id, {"type": "hint_request"})
    puzzle = next(p for p in code_and_find_room.puzzles if p.id == hinted["active_puzzle_id"])

    # No route opens a Rung yet (the ladder lands in Epic 3), so the Rung opens here as the ladder will
    # open it: worded by the HintPhraser wiring resolves for the hosted settings, appended to the hosted log.
    phraser = hint_phraser(hosted_settings())
    assert type(phraser) is VerbatimPhraser
    worded = phraser.phrase(puzzle.rungs.nudge, Derived.fresh())
    sessions = DictSessionStore(handles.sessions)
    log = sessions.read_all(session_id)
    sessions.append(session_id, RungChangeEvent(
        type="rung_change", puzzle_id=puzzle.id, rung=1, triggered_by=[len(log) - 1],
        phrased=worded.phrased, phrasing_ms=None, text=worded.text, t_ms=log[-1].t_ms + 1,
    ))

    live = client.get(f"/api/sessions/{session_id}").json()
    assert [(change["text"], change["phrased"]) for change in live["rung_changes"]] == [(puzzle.rungs.nudge, False)]
    assert live["thresholds"] == FRESH_THRESHOLDS.model_dump()
    replayed = SessionStateMachine(code_and_find_room, opening="welcome", thresholds=FRESH_THRESHOLDS).replay(
        session_id, sessions.read_all(session_id)
    )
    served = {"disclosure": [HOSTED_LINE], "trigger_events": trigger_events(replayed, sessions.read_all(session_id))}
    assert live == replayed.model_copy(update=served).model_dump(mode="json")

    stored = json.dumps(handles.sessions[session_id])
    assert not any(key in stored for key in ("derived", *Derived.model_fields))
    assert not any(value in stored for value in SENTINEL_VALUES)


# --- No solution in any play, job-state or GET /meta response ------------------------------------


def test_no_play_job_state_or_meta_response_carries_a_solution(tmp_path: Path, handles: ModalHandles, four_lock_room):
    room = with_sentinel_solutions(four_lock_room)
    client = TestClient(make_hosted_app(tmp_path, handles, room))
    jobs = hosted_stores(handles).jobs
    jobs.put(JobState(id=JOB, status="done", room_id=room.id, regen_max=2))
    jobs.put(JobState(id=UNKNOWN_JOB, status="queued", regen_max=2))

    session = client.post("/api/sessions", json={"room_id": room.id})
    session_id = session.json()["id"]
    responses = [
        client.get("/api/meta"),
        client.get("/api/rooms"),
        client.get(f"/api/rooms/{room.id}"),
        *(client.get(f"/api/rooms/{room.id}/photos/{i}") for i in range(len(room.photos))),
        session,
        client.post(f"/api/sessions/{session_id}/events", json=click("rug")),
        client.post(f"/api/sessions/{session_id}/events", json=code("clock_code", "000")),
        client.get(f"/api/sessions/{session_id}"),
        client.get(f"/api/sessions/{session_id}/result"),
        client.get(f"/api/builds/{JOB}"),
        client.get(f"/api/builds/{UNKNOWN_JOB}"),
    ]
    assert all(response.status_code in (200, 202) for response in responses), [r.text for r in responses]
    sentinels = [SENTINEL_CODE, json.dumps(SENTINEL_ORDER)[1:-1], *SENTINEL_PAIR, SENTINEL_FIND, *SENTINEL_IX]
    for response in responses:
        assert b"solution" not in response.content
        assert all(sentinel.encode() not in response.content for sentinel in sentinels)
        if response.headers["content-type"].startswith("application/json"):
            assert "solution" not in json_keys(response.json())
