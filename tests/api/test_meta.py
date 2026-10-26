"""Story 1.14: `GET /meta` serves the status model with the global Disclosure lines and the Local Retention summary, `GET /schema` every AD-2 model, and `GET /rooms` one `RoomSummary` per stored Room (AD-2, AD-9, AD-15)."""

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import api_schema, create_app, room_summary
from src.api.meta import (
    CUT1_LINE,
    DEFAULT_OLLAMA_HOST,
    RETENTION_LOCAL,
    SCRIPTED_LINE,
    TIMESCALE_LINE,
    disclosure_lines,
    meta,
)
from src.api.wiring import MODE, artifact_store, job_store
from src.config import Settings
from src.domain.schema import API_MODELS, JobState, Meta, Room, RoomSummary
from tests.api.test_app import make_app, store_room
from tests.domain.test_redact import json_keys

SRC = Path(__file__).resolve().parents[2] / "src"
JOB_A, JOB_B = "job_01ARZ3NDEKTSV4RRFFQ69G5FAA", "job_01ARZ3NDEKTSV4RRFFQ69G5FAB"


def settings(**env: str) -> Settings:
    return Settings.from_env({"GUIDE": "verbatim", **env})


def get_meta(client: TestClient, **query: str) -> dict:
    response = client.get("/api/meta", params=query)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


# --- GET /meta --------------------------------------------------------------


def test_meta_has_exactly_the_status_fields_in_local_mode(client: TestClient):
    body = get_meta(client)
    assert set(body) == {"mode", "guide", "guide_model", "trickster", "demo_timescale", "cache", "profile", "disclosure", "retention"}
    assert body == {
        "mode": "local", "guide": "verbatim", "guide_model": None, "trickster": "live", "demo_timescale": 1,
        "cache": "on", "profile": "dev", "disclosure": [], "retention": RETENTION_LOCAL,
    }
    assert MODE == "local"


def test_meta_reads_guide_timescale_and_cache_from_settings(tmp_path: Path, four_lock_room: Room):
    client = TestClient(make_app(tmp_path, four_lock_room, settings=settings(DEMO_TIMESCALE="6", CACHE="off")))
    body = get_meta(client)
    assert (body["demo_timescale"], body["cache"], body["guide"]) == (6, "off", "verbatim")


def test_guide_ollama_reports_llama_at_the_ollama_host():
    assert meta(Settings.from_env({"GUIDE": "ollama", "OLLAMA_HOST": "http://mac.local:11434"})).guide_model.model_dump() == {
        "id": "llama3.2:3b", "host": "http://mac.local:11434",
    }
    assert meta(Settings.from_env({"GUIDE": "ollama"})).guide_model.host == DEFAULT_OLLAMA_HOST
    assert meta(settings()).guide_model is None


def test_profile_is_dev_unless_the_client_asks_for_demo(client: TestClient):
    assert get_meta(client)["profile"] == "dev"
    assert get_meta(client, profile="demo")["profile"] == "demo"
    assert get_meta(client, profile="dev")["profile"] == "dev"
    assert client.get("/api/meta", params={"profile": "judge"}).status_code == 422


@pytest.mark.parametrize(("demo_trickster", "trickster"), [
    ("live", "live"), ("record", "live"), ("scripted", "scripted"), ("authored", "cut1"),
])
def test_trickster_reports_the_proposal_source(demo_trickster: str, trickster: str):
    assert meta(settings(DEMO_TRICKSTER=demo_trickster)).trickster == trickster


# --- Disclosure lines -----------------------------------------------------------


def test_disclosure_is_empty_at_the_defaults():
    assert disclosure_lines(settings()) == [] and meta(settings()).disclosure == []


def test_the_timescale_line_names_the_speed():
    assert disclosure_lines(settings(DEMO_TIMESCALE="6")) == [
        "Hint and Trickster timings run at 6× speed; the build timer is real time."
    ]
    assert disclosure_lines(settings(DEMO_TIMESCALE="3")) == [TIMESCALE_LINE.format(n=3)]


def test_the_scripted_line_is_composed_only_under_scripted():
    assert disclosure_lines(settings(DEMO_TRICKSTER="scripted")) == [
        "Trickster proposals replayed from a recording; the Validator ran live."
    ]
    for source in ("live", "record", "authored"):
        assert SCRIPTED_LINE not in disclosure_lines(settings(DEMO_TRICKSTER=source))


def test_the_cut_1_line_is_verbatim_and_composed_only_under_authored():
    assert CUT1_LINE == "Trickster proposals were written in advance; the Validator ran live on each."
    assert disclosure_lines(settings(DEMO_TRICKSTER="authored")) == [CUT1_LINE]
    for source in ("live", "record", "scripted"):
        assert CUT1_LINE not in disclosure_lines(settings(DEMO_TRICKSTER=source))


def test_both_lines_join_when_both_apply(tmp_path: Path, four_lock_room: Room):
    both = settings(DEMO_TIMESCALE="6", DEMO_TRICKSTER="scripted")
    assert disclosure_lines(both) == [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE]
    client = TestClient(make_app(tmp_path, four_lock_room, settings=both))
    assert get_meta(client)["disclosure"] == [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE]


def test_session_state_carries_the_same_global_lines(tmp_path: Path, four_lock_room: Room):
    both = settings(DEMO_TIMESCALE="6", DEMO_TRICKSTER="authored")
    client = TestClient(make_app(tmp_path, four_lock_room, settings=both))
    started = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    state = client.get(f"/api/sessions/{started['id']}").json()
    assert started["disclosure"] == state["disclosure"] == get_meta(client)["disclosure"] == disclosure_lines(both)


def _string_constants(path: Path) -> set[str]:
    return {node.value for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def test_meta_py_is_the_only_module_that_writes_a_disclosure_line():
    """No other module under `src/` holds a Disclosure line or a piece of one."""
    pieces = ("the Validator ran live", "the build timer is real time", "This room was built earlier")
    holders = {
        path.relative_to(SRC).as_posix()
        for path in SRC.rglob("*.py")
        if any(piece in text for text in _string_constants(path) for piece in pieces)
    }
    assert holders == {"api/meta.py"}


# --- Retention ---------------------------------------------------------------


def test_the_local_retention_summary(client: TestClient):
    retention = get_meta(client)["retention"]
    assert retention == RETENTION_LOCAL
    assert retention.startswith("Your photos and the puzzle text go to the Meta Model API (standard tier)")
    assert "Baseten or Fireworks" in retention
    assert "Leave out faces, documents and other people's belongings." in retention
    assert retention.endswith("A copy of your photos is also kept on this computer.")
    assert "Modal" not in retention


# --- GET /schema -------------------------------------------------------------


def test_schema_returns_every_ad_2_model(client: TestClient):
    response = client.get("/api/schema")
    assert response.status_code == 200
    schema = response.json()
    assert schema == api_schema()
    defs = schema["$defs"]
    assert {model.__name__ for model in API_MODELS} <= set(defs)
    for name in (
        "Room", "RoomDraft", "PlayView", "BuildView", "RoomView", "RoomSummary", "AccessCheck", "Derived", "RoomResult",
        "Meta", "TricksterCard", "JobState", "SessionState", "ErrorEnvelope", "ClickEvent", "LockInputEvent",
        "HintRequestEvent", "IdleTickEvent", "OpeningLineEvent", "TricksterCardEvent", "RungChangeEvent",
    ):
        assert defs[name]["type"] == "object" and "properties" in defs[name]
    assert set(defs["Meta"]["properties"]) == set(Meta.model_fields)
    assert set(defs["RoomSummary"]["properties"]) == {"room_id", "name", "cover_photo", "puzzle_count", "job_id", "built_at"}


def test_schema_refs_point_into_its_own_defs(client: TestClient):
    schema = client.get("/api/schema").json()
    refs = {node["$ref"] for node in _walk(schema) if isinstance(node, dict) and "$ref" in node}
    assert refs and all(ref.startswith("#/$defs/") for ref in refs)
    assert {ref.removeprefix("#/$defs/") for ref in refs} <= set(schema["$defs"])
    assert "Puzzle" in schema["$defs"] and "oneOf" in schema["$defs"]["Puzzle"]["properties"]["solution"]


def _walk(node):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


# --- GET /rooms --------------------------------------------------------------


def test_no_stored_room_lists_nothing(tmp_path: Path):
    client = TestClient(make_app(tmp_path))
    response = client.get("/api/rooms")
    assert response.status_code == 200 and response.json() == []


def test_room_summary_fields(four_lock_room: Room):
    summary = room_summary(four_lock_room, JOB_A)
    assert summary == RoomSummary(
        room_id=four_lock_room.id, name=None, cover_photo=0, puzzle_count=5, job_id=JOB_A, built_at=four_lock_room.created
    )


def test_rooms_lists_one_summary_per_stored_room_newest_first(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    older = four_lock_room.model_copy(update={"created": datetime(2026, 10, 25, 9, 0, tzinfo=UTC), "name": "Room 1"})
    newer = code_and_find_room
    root = tmp_path / "rooms"
    store, jobs = artifact_store(root), job_store(root)
    store_room(store, older)
    store_room(store, newer)
    jobs.put(JobState(id=JOB_A, status="done", room_id=older.id, regen_max=2))
    jobs.put(JobState(id=JOB_B, status="done", room_id=newer.id, regen_max=2))
    jobs.put(JobState(id="job_01ARZ3NDEKTSV4RRFFQ69G5FAC", status="queued", regen_max=2))
    client = TestClient(create_app(settings(), rooms_root=root, web_dist=tmp_path / "no-dist"))
    response = client.get("/api/rooms")
    assert response.status_code == 200
    assert response.json() == [
        {"room_id": newer.id, "name": None, "cover_photo": 0, "puzzle_count": 4, "job_id": JOB_B, "built_at": "2026-10-26T12:00:00Z"},
        {"room_id": older.id, "name": "Room 1", "cover_photo": 0, "puzzle_count": 5, "job_id": JOB_A, "built_at": "2026-10-25T09:00:00Z"},
    ]
    assert not {"solution", "puzzles", "interactables", "photos", "provenance"} & json_keys(response.json())
