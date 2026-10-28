"""Story 6.2: one function in `src/api/meta.py` composes every Disclosure list, the global lines `GET /meta` serves and each Room's list the session state carries; demo settings change only timing and the Trickster source (AD-15, NFR-12)."""

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.meta import (
    CUT1_LINE,
    EARLIER_BUILD_LINE,
    SCRIPTED_LINE,
    TIMESCALE_LINE,
    disclosure_lines,
)
from src.api.wiring import artifact_store, job_store, session_store
from src.config import Settings
from src.domain.schema import CallRow, Derived, JobState, Room
from src.infra.clocks import NS_PER_MS, SessionClock
from tests.api.test_app import make_app, store_room
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import (
    IX,
    PZ,
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)

SRC = Path(__file__).resolve().parents[2] / "src"
JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAA"
DEMO_ENV = {"DEMO_TIMESCALE": "6", "DEMO_TRICKSTER": "scripted"}
BUILT = datetime(2026, 10, 31, 9, 30, tzinfo=UTC)
EARLIER = "This room was built earlier, on Sat Oct 31."
SERVER_EVENTS = ("idle_tick", "rung_change", "opening_line", "trickster_card")


def settings(**env: str) -> Settings:
    return Settings.from_env({"GUIDE": "verbatim", **env})


def call(n: int, *, cached: bool) -> CallRow:
    return CallRow(id=f"call_01ARZ3NDEKTSV4RRFFQ69G5FA{n}", role="architect", model="muse-spark-1.3", host="meta",
                   cached=cached, spend_usd=0.0 if cached else 0.01)


def job(room: Room, *calls: CallRow) -> JobState:
    return JobState(id=JOB, status="done", room_id=room.id, regen_max=2, calls=list(calls))


def app_over(tmp_path: Path, room: Room, job_state: JobState | None, env: dict[str, str], clock: Any = None) -> FastAPI:
    """The app over one stored Room; a greeting composes inline so the log's order is fixed."""
    app = make_app(tmp_path, room, settings=settings(**env), clock=clock, spawn=lambda task: task())
    if job_state is not None:
        job_store(tmp_path / "rooms").put(job_state)
    return app


def start(client: TestClient, room: Room, **body: Any) -> dict[str, Any]:
    response = client.post("/api/sessions", json={"room_id": room.id, **body})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def built_room(four_lock_room: Room) -> Room:
    return four_lock_room.model_copy(update={"created": BUILT})


@pytest.fixture
def demo_room(built_room: Room) -> Room:
    return built_room.model_copy(update={"name": "The study"})


# --- GET /meta: the global lines --------------------------------------------


def test_meta_at_6x_with_the_scripted_trickster_holds_exactly_the_two_global_lines(tmp_path: Path, built_room: Room):
    client = TestClient(app_over(tmp_path, built_room, None, DEMO_ENV))
    body = client.get("/api/meta").json()
    assert body["disclosure"] == [
        "Hint and Trickster timings run at 6× speed; the build timer is real time.",
        "Trickster proposals replayed from a recording; the Validator ran live.",
    ]
    assert body["disclosure"] == disclosure_lines(settings(**DEMO_ENV))


def test_meta_at_1x_with_the_live_trickster_holds_no_line(tmp_path: Path, built_room: Room):
    client = TestClient(app_over(tmp_path, built_room, None, {"DEMO_TIMESCALE": "1", "DEMO_TRICKSTER": "live"}))
    body = client.get("/api/meta").json()
    assert (body["disclosure"], body["trickster"]) == ([], "live")


@pytest.mark.parametrize(("source", "trickster", "line"), [
    ("live", "live", None), ("record", "live", None), ("scripted", "scripted", SCRIPTED_LINE), ("authored", "cut1", CUT1_LINE),
])
def test_every_list_holds_at_most_the_one_trickster_line_its_source_names(
    tmp_path: Path, demo_room: Room, source: str, trickster: str, line: str | None
):
    env = {"DEMO_TIMESCALE": "6", "DEMO_TRICKSTER": source}
    client = TestClient(app_over(tmp_path, demo_room, job(demo_room, call(1, cached=True)), env))
    meta_body = client.get("/api/meta").json()
    lists = [meta_body["disclosure"], start(client, demo_room)["disclosure"], disclosure_lines(settings(**env), demo_room)]
    assert meta_body["trickster"] == trickster
    for lines in lists:
        assert [x for x in lines if x in (SCRIPTED_LINE, CUT1_LINE)] == ([line] if line else [])
        assert lines[0] == TIMESCALE_LINE.format(n=6)


# --- The per-Room line --------------------------------------------------------


def test_a_demo_rooms_session_carries_the_global_lines_and_the_earlier_builds_line(tmp_path: Path, demo_room: Room):
    client = TestClient(app_over(tmp_path, demo_room, job(demo_room, call(1, cached=False)), DEMO_ENV))
    started = start(client, demo_room)
    expected = [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE, EARLIER]
    assert started["disclosure"] == client.get(f"/api/sessions/{started['id']}").json()["disclosure"] == expected
    assert disclosure_lines(settings(**DEMO_ENV), demo_room) == expected
    assert client.get("/api/meta").json()["disclosure"] == expected[:2]


def test_a_build_with_any_cached_call_carries_the_earlier_builds_line_on_its_first_session(tmp_path: Path, built_room: Room):
    client = TestClient(app_over(tmp_path, built_room, job(built_room, call(1, cached=False), call(2, cached=True)), {}))
    assert start(client, built_room)["disclosure"] == [EARLIER]
    assert EARLIER not in client.get("/api/meta").json()["disclosure"]


def test_a_cache_off_build_gets_only_the_global_lines_until_its_second_session(tmp_path: Path, built_room: Room):
    client = TestClient(app_over(tmp_path, built_room, job(built_room, call(1, cached=False), call(2, cached=False)), {"CACHE": "off"}))
    first = start(client, built_room)
    second = start(client, built_room, derived=Derived.fresh().model_dump())
    assert (first["disclosure"], second["disclosure"]) == ([], [EARLIER])
    assert client.get(f"/api/sessions/{first['id']}").json()["disclosure"] == []
    assert client.get(f"/api/sessions/{second['id']}").json()["disclosure"] == [EARLIER]
    assert client.get("/api/meta").json()["disclosure"] == []


def test_a_second_session_appends_the_line_after_the_global_ones(tmp_path: Path, built_room: Room):
    client = TestClient(app_over(tmp_path, built_room, job(built_room), DEMO_ENV))
    assert start(client, built_room)["disclosure"] == [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE]
    assert start(client, built_room)["disclosure"] == [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE, EARLIER]


def test_a_session_on_another_room_is_not_an_earlier_session(tmp_path: Path, built_room: Room, code_and_find_room: Room):
    client = TestClient(app_over(tmp_path, built_room, job(built_room), {}))
    store_room(artifact_store(tmp_path / "rooms"), code_and_find_room)
    start(client, code_and_find_room)
    assert start(client, built_room)["disclosure"] == []


def test_the_date_is_the_rooms_build_time(built_room: Room):
    for created, date in [(BUILT, "Sat Oct 31"), (datetime(2026, 11, 2, 23, 0, tzinfo=UTC), "Mon Nov 2")]:
        room = built_room.model_copy(update={"created": created, "name": "The study"})
        assert disclosure_lines(settings(), room) == [EARLIER_BUILD_LINE.format(date=date)]


def test_without_a_room_the_function_composes_only_the_global_lines(demo_room: Room):
    for env in ({}, DEMO_ENV, {"DEMO_TRICKSTER": "authored"}):
        assert disclosure_lines(settings(**env)) == disclosure_lines(settings(**env), demo_room)[:-1]
        assert not any(line.startswith("This room was built earlier") for line in disclosure_lines(settings(**env), None, job(demo_room, call(1, cached=True)), earlier_session=True))


# --- BuildView: the same function fills its Disclosure list ---------------------


def routes(app: FastAPI) -> dict[str, list[str]]:
    """Every API path the app serves, with its methods."""
    return {path: sorted(methods) for path, methods in app.openapi()["paths"].items()}


def _callers(name: str) -> set[str]:
    out: set[str] = set()
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) == name:
                out.add(path.relative_to(SRC).as_posix())
    return out


@pytest.mark.parametrize("env", [{}, DEMO_ENV, {"DEMO_TRICKSTER": "authored"}])
def test_the_build_views_disclosure_is_the_list_the_function_composes_for_the_room(
    tmp_path: Path, built_room: Room, demo_room: Room, env: dict[str, str]
):
    for room, cached in ((built_room, False), (built_room, True), (demo_room, False)):
        job_state = job(room, call(1, cached=cached))
        client = TestClient(app_over(tmp_path / f"{room.name}-{cached}", room, job_state, env))
        view = client.get(f"/api/builds/{JOB}/view")
        assert view.status_code == 200, view.text
        assert view.json()["disclosure"] == disclosure_lines(settings(**env), room, job_state)
    assert _callers("disclosure_lines") == {"api/meta.py", "api/app.py"}
    assert _callers("to_build_view") == {"api/app.py"}


def test_the_build_view_carries_the_earlier_builds_line_once_a_session_has_started_on_the_room(tmp_path: Path, built_room: Room):
    """The Build view opened from the Completion screen keeps the Disclosure the session showed (EXPERIENCE.md, Disclosure banner)."""
    job_state = job(built_room, call(1, cached=False))
    client = TestClient(app_over(tmp_path, built_room, job_state, {"CACHE": "off"}))
    assert client.get(f"/api/builds/{JOB}/view").json()["disclosure"] == []
    start(client, built_room)
    view = client.get(f"/api/builds/{JOB}/view")
    assert view.status_code == 200, view.text
    assert view.json()["disclosure"] == [EARLIER]
    assert view.json()["disclosure"] == disclosure_lines(settings(), built_room, job_state, earlier_session=True)
    assert client.get("/api/meta").json()["disclosure"] == []


# --- No Room content in any line, no sentinel in any response -----------------------


def test_no_line_carries_a_room_label_a_clue_a_solution_or_a_derived_field(tmp_path: Path, four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room).model_copy(update={"created": BUILT, "name": "ZQXJV study"})
    client = TestClient(app_over(tmp_path, room, job(room, call(1, cached=True)), DEMO_ENV))
    derived = {"sessions": 7, "persistence": 0.4321, "time_to_first_hint_s": 98.765, "mean_rung_per_lock_type": {"code": 2.345}}
    started = start(client, room, derived=derived)
    state = client.get(f"/api/sessions/{started['id']}")
    meta_response = client.get("/api/meta")
    forbidden = [
        room.name, *(ix.label for ix in room.interactables), *(p.clue for p in room.puzzles), *(p.lore for p in room.puzzles),
        *(rung for p in room.puzzles for rung in (p.rungs.nudge, p.rungs.direction, p.rungs.near_answer)),
        SENTINEL_CODE, SENTINEL_FIND, *SENTINEL_IX, *SENTINEL_PAIR, *SENTINEL_ORDER,
        *Derived.model_fields, "0.4321", "98.765", "2.345",
    ]
    lines = [*started["disclosure"], *state.json()["disclosure"], *meta_response.json()["disclosure"]]
    assert started["disclosure"] == [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE, EARLIER]
    for line in lines:
        assert not [token for token in forbidden if token and token.lower() in line.lower()], line
    sentinels = [SENTINEL_CODE, json.dumps(SENTINEL_ORDER)[1:-1], *SENTINEL_PAIR, SENTINEL_FIND, *SENTINEL_IX]
    for response in (state, meta_response):
        assert response.status_code == 200
        assert b"solution" not in response.content and "solution" not in json_keys(response.json())
        assert all(sentinel.encode() not in response.content for sentinel in sentinels)


# --- Demo settings change only timing and the Trickster source -----------------------


class FakeMonotonic:
    def __init__(self) -> None:
        self.ns = 0

    def __call__(self) -> int:
        return self.ns

    def advance(self, ms: int) -> None:
        self.ns += ms * NS_PER_MS


def _files(root: Path) -> dict[str, bytes]:
    """Every stored file outside the session logs, by path."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file() and "sessions" not in p.parts}


def _play(tmp_path: Path, room: Room, env: dict[str, str], timescale: int) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    monotonic = FakeMonotonic()
    root = tmp_path / "rooms"
    app = app_over(tmp_path, room, job(room), env, clock=SessionClock(timescale, monotonic_ns=monotonic))
    before = _files(root)
    client = TestClient(app)
    derived = {"sessions": 1, "persistence": 0.5, "time_to_first_hint_s": 40.0, "mean_rung_per_lock_type": {"code": 1.0}}
    session_id = start(client, room, derived=derived)["id"]
    bodies = [
        {"type": "click", "interactable_id": IX["rug"]},
        {"type": "click", "interactable_id": IX["key"]},
        {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["clock_code"], "code": "000"}},
        {"type": "hint_request"},
    ]
    for body in bodies:
        monotonic.advance(1500)
        response = client.post(f"/api/sessions/{session_id}/events", json=body)
        assert response.status_code == 200, response.text
    monotonic.advance(6000)
    state = client.get(f"/api/sessions/{session_id}").json()
    log = [event.model_dump(mode="json") for event in session_store(root).read_all(session_id)]
    return log, state, _files(root) == before


def test_the_same_posted_events_at_6x_scripted_append_only_what_normal_session_logic_produces(tmp_path: Path, built_room: Room):
    demo_log, demo_state, demo_unchanged = _play(tmp_path / "demo", built_room, DEMO_ENV, 6)
    live_log, live_state, live_unchanged = _play(tmp_path / "live", built_room, {}, 1)
    assert demo_log == live_log
    assert [event["t_ms"] for event in demo_log] == [0, 1500, 3000, 4500, 6000, 12000]
    posted = {"click", "lock_input", "hint_request"}
    assert {event["type"] for event in demo_log} - posted <= set(SERVER_EVENTS)
    for position, event in enumerate(demo_log):
        if event["type"] == "rung_change":
            assert event["triggered_by"] and all(0 <= i < position for i in event["triggered_by"])
    assert [e for e in demo_log if e["type"] == "opening_line"] == [e for e in live_log if e["type"] == "opening_line"]
    # The Rung thresholds run on the session clock, so only they and the Disclosure list differ (AD-10, AD-15).
    assert {**demo_state, "id": None, "disclosure": None, "thresholds": None} == {**live_state, "id": None, "disclosure": None, "thresholds": None}
    assert demo_state["thresholds"]["nudge_threshold_ms"] * 6 == live_state["thresholds"]["nudge_threshold_ms"]
    assert demo_state["disclosure"] == [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE] and live_state["disclosure"] == []
    assert demo_unchanged and live_unchanged


@pytest.mark.parametrize("env", [{}, DEMO_ENV, {"DEMO_TRICKSTER": "authored"}, {"DEMO_TRICKSTER": "record"}])
def test_no_route_lets_a_client_post_a_server_event(tmp_path: Path, built_room: Room, env: dict[str, str]):
    client = TestClient(app_over(tmp_path, built_room, None, env))
    session_id = start(client, built_room)["id"]
    bodies = [
        {"type": "idle_tick"},
        {"type": "opening_line", "kind": "greeting", "text": "Welcome back."},
        {"type": "rung_change", "puzzle_id": PZ["find_key"], "rung": 3, "triggered_by": [], "phrased": False, "phrasing_ms": None, "text": "Look down."},
        {"type": "trickster_card", "edit_id": "te_01ARZ3NDEKTSV4RRFFQ69G5FAA", "edit": None, "puzzle_id": None, "accepted": True, "reason": None, "room_revision": 1},
    ]
    for body in bodies:
        assert client.post(f"/api/sessions/{session_id}/events", json=body).status_code == 422
    assert [event.type for event in session_store(tmp_path / "rooms").read_all(session_id)] == ["opening_line"]


def test_no_route_or_settings_flag_injects_play_or_build_output(tmp_path: Path, built_room: Room):
    app = app_over(tmp_path, built_room, None, DEMO_ENV)
    assert routes(app) == {
        "/api/meta": ["get"], "/api/schema": ["get"], "/api/rooms": ["get"], "/api/rooms/{room_id}": ["get"],
        "/api/rooms/{room_id}/photos/{index}": ["get"], "/api/profile/{name}": ["get", "put"], "/api/sessions": ["post"],
        "/api/sessions/{session_id}": ["get"], "/api/sessions/{session_id}/events": ["post"], "/api/sessions/{session_id}/result": ["get"],
        "/api/sessions/{session_id}/trickster": ["post"], "/api/sessions/{session_id}/room": ["get"],
        "/api/builds": ["post"], "/api/builds/{job_id}": ["get"], "/api/builds/{job_id}/room": ["get"],
        "/api/builds/{job_id}/view": ["get"],
    }
    assert [name for name in Settings.model_fields if "demo" in name] == ["demo_timescale", "demo_trickster", "demo_proposals_dir"]
