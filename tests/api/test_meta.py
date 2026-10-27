"""Stories 1.14 and 7.2: `GET /meta` serves the status model with the global Disclosure lines and the Retention summary of the running mode, `GET /schema` every AD-2 model, and `GET /rooms` one `RoomSummary` per stored Room with a job record (AD-2, AD-9, AD-15)."""

import ast
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import pytest
from fastapi.testclient import TestClient

from src.api.app import API_UNIONS, api_schema, room_summary
from src.api.meta import (
    CUT1_LINE,
    HOSTED_LINE,
    RETENTION_HOSTED,
    RETENTION_LOCAL,
    RETENTION_OPENING,
    SCRIPTED_LINE,
    TIMESCALE_LINE,
    disclosure_lines,
    meta,
)
from src.api.wiring import JOBS_DIR, job_store
from src.config import Settings
from src.domain.schema import API_MODELS, JobState, Meta, Room, RoomSummary
from src.infra.modal import JOB_FILE
from src.providers.ollama import DEFAULT_HOST
from tests.api.hosted import hosted_handles, make_hosted_app
from tests.api.test_app import make_app
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import IX

SRC = Path(__file__).resolve().parents[2] / "src"
JOB_A, JOB_B = "job_01ARZ3NDEKTSV4RRFFQ69G5FAA", "job_01ARZ3NDEKTSV4RRFFQ69G5FAB"
CORRUPT_JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"


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


def test_meta_reads_guide_timescale_and_cache_from_settings(tmp_path: Path, four_lock_room: Room):
    client = TestClient(make_app(tmp_path, four_lock_room, settings=settings(DEMO_TIMESCALE="6", CACHE="off")))
    body = get_meta(client)
    assert (body["demo_timescale"], body["cache"], body["guide"]) == (6, "off", "verbatim")


def test_guide_ollama_reports_llama_at_the_ollama_host():
    assert meta(Settings.from_env({"GUIDE": "ollama", "OLLAMA_HOST": "http://mac.local:11434"})).guide_model.model_dump() == {
        "id": "llama3.2:3b", "host": "http://mac.local:11434",
    }
    assert meta(Settings.from_env({"GUIDE": "ollama"})).guide_model.host == DEFAULT_HOST
    assert meta(settings()).guide_model is None


def test_profile_is_dev_unless_the_client_names_one(client: TestClient):
    assert get_meta(client)["profile"] == "dev"
    for name in ("demo", "dev", "playtest", "my-profile_2"):
        assert get_meta(client, profile=name)["profile"] == name


@pytest.mark.parametrize("name", ["", "..", "../demo", "a/b"])
def test_meta_refuses_a_profile_name_the_profile_routes_refuse(client: TestClient, name: str):
    response = client.get("/api/meta", params={"profile": name})
    assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_profile_name")


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
    clicked = client.post(f"/api/sessions/{started['id']}/events", json={"type": "click", "interactable_id": IX["rug"]})
    assert clicked.status_code == 200, clicked.text
    lines = disclosure_lines(both)
    assert started["disclosure"] == state["disclosure"] == clicked.json()["disclosure"] == get_meta(client)["disclosure"] == lines


def _string_constants(path: Path) -> set[str]:
    return {node.value for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def test_meta_py_is_the_only_module_that_writes_a_disclosure_line():
    """No other module under `src/` holds a Disclosure line or a piece of one."""
    pieces = ("the Validator ran live", "the build timer is real time", "This room was built earlier", "no hint model runs here")
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
    assert "Leave out faces" not in retention
    assert retention.endswith("A copy of your photos is also kept on this computer.")
    assert "Modal" not in retention


LOCAL_SENTENCE = "A copy of your photos is also kept on this computer."


def test_meta_reads_the_mode_from_settings():
    assert meta(settings()).mode == "local"
    assert meta(Settings.from_env({"MODE": "hosted"})).mode == "hosted"
    tree = ast.parse((SRC / "api" / "meta.py").read_text())
    assert not any(isinstance(node, ast.ImportFrom) and node.module == "src.api.wiring" for node in ast.walk(tree))


def test_hosted_meta_reports_verbatim_with_no_guide_model_and_the_hosted_line():
    hosted = meta(Settings.from_env({"MODE": "hosted"}))
    assert (hosted.mode, hosted.guide, hosted.guide_model) == ("hosted", "verbatim", None)
    assert HOSTED_LINE == "Hosted mode: hints are shown as written; no hint model runs here."
    assert hosted.disclosure == [HOSTED_LINE]
    assert HOSTED_LINE not in meta(settings()).disclosure


def test_the_hosted_line_follows_the_trickster_source_line():
    hosted = Settings.from_env({"MODE": "hosted", "DEMO_TIMESCALE": "6", "DEMO_TRICKSTER": "scripted"})
    assert disclosure_lines(hosted) == [TIMESCALE_LINE.format(n=6), SCRIPTED_LINE, HOSTED_LINE]


def test_the_hosted_retention_summary_replaces_the_local_storage_sentence():
    retention = meta(Settings.from_env({"MODE": "hosted"})).retention
    assert retention == RETENTION_HOSTED
    assert retention.startswith(RETENTION_OPENING) and RETENTION_LOCAL.startswith(RETENTION_OPENING)
    assert retention.removeprefix(RETENTION_OPENING) == (
        "In Hosted mode, your photos, the originals, your room and its play-throughs are stored on Modal "
        "and deleted Tue Nov 10. Play-through logs are deleted 24 hours after their last event. "
        "No player profile data leaves your browser."
    )
    assert LOCAL_SENTENCE not in retention and "kept on this computer" not in retention
    assert "Leave out faces" not in retention
    assert RETENTION_LOCAL.removeprefix(RETENTION_OPENING) == LOCAL_SENTENCE


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


def test_schema_serves_the_tagged_unions_by_name(client: TestClient):
    defs = client.get("/api/schema").json()["$defs"]
    for name, union in API_UNIONS.items():
        members = [ref["$ref"].removeprefix("#/$defs/") for ref in defs[name]["oneOf"]]
        assert defs[name]["title"] == name and defs[name]["discriminator"]["propertyName"] == "type"
        assert members == [model.__name__ for model in get_args(get_args(union)[0])]


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
    app = make_app(tmp_path, older, newer, settings=settings())
    jobs = job_store(tmp_path / "rooms")
    jobs.put(JobState(id=JOB_A, status="done", room_id=older.id, regen_max=2))
    jobs.put(JobState(id=JOB_B, status="done", room_id=newer.id, regen_max=2))
    jobs.put(JobState(id="job_01ARZ3NDEKTSV4RRFFQ69G5FAC", status="queued", regen_max=2))
    client = TestClient(app)
    response = client.get("/api/rooms")
    assert response.status_code == 200
    assert response.json() == [
        {"room_id": newer.id, "name": None, "cover_photo": 0, "puzzle_count": 4, "job_id": JOB_B, "built_at": "2026-10-26T12:00:00Z"},
        {"room_id": older.id, "name": "Room 1", "cover_photo": 0, "puzzle_count": 5, "job_id": JOB_A, "built_at": "2026-10-25T09:00:00Z"},
    ]
    assert not {"solution", "puzzles", "interactables", "photos", "provenance"} & json_keys(response.json())


def test_a_stored_room_without_a_job_record_is_not_listed(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    """`RoomSummary.job_id` is required, so a Room no job record names has no row to list."""
    app = make_app(tmp_path, four_lock_room, code_and_find_room, settings=settings())
    job_store(tmp_path / "rooms").put(JobState(id=JOB_A, status="done", room_id=four_lock_room.id, regen_max=2))
    client = TestClient(app)
    assert [row["room_id"] for row in client.get("/api/rooms").json()] == [four_lock_room.id]


def test_one_job_record_that_does_not_parse_is_skipped_and_every_other_room_is_still_listed(
    tmp_path: Path, four_lock_room: Room, code_and_find_room: Room, caplog: pytest.LogCaptureFixture
):
    """A corrupt job file names only itself: the list, like `resume_jobs`, logs it and skips it rather than hiding every Room."""
    app = make_app(tmp_path, four_lock_room, code_and_find_room, settings=settings())
    jobs = job_store(tmp_path / "rooms")
    jobs.put(JobState(id=JOB_A, status="done", room_id=four_lock_room.id, regen_max=2))
    jobs.put(JobState(id=JOB_B, status="done", room_id=code_and_find_room.id, regen_max=2))
    (tmp_path / "rooms" / JOBS_DIR / f"{CORRUPT_JOB}.json").write_text("{}")
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/rooms")

    assert response.status_code == 200, response.text
    assert sorted(row["room_id"] for row in response.json()) == sorted([four_lock_room.id, code_and_find_room.id])
    assert CORRUPT_JOB in caplog.text and "job_unreadable" in caplog.text
    assert client.post("/api/sessions", json={"room_id": four_lock_room.id}).status_code == 200
    assert client.get(f"/api/builds/{CORRUPT_JOB}").status_code == 500  # the corrupt job's own route still fails


def test_a_hosted_final_record_that_does_not_parse_is_skipped_and_the_demo_room_is_still_listed(
    tmp_path: Path, four_lock_room: Room, caplog: pytest.LogCaptureFixture
):
    handles = hosted_handles(tmp_path)
    app = make_hosted_app(tmp_path, handles, four_lock_room)
    (handles.root / "rooms" / "demo" / four_lock_room.id / JOB_FILE).write_text(
        JobState(id=JOB_A, status="done", room_id=four_lock_room.id, regen_max=2).model_dump_json()
    )
    corrupt = handles.root / "rooms" / "judge" / "room_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    corrupt.mkdir(parents=True)
    (corrupt / JOB_FILE).write_text("{}")
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/rooms")

    assert response.status_code == 200, response.text
    assert [row["job_id"] for row in response.json()] == [JOB_A]
    assert "job_unreadable" in caplog.text
    assert client.post("/api/sessions", json={"room_id": four_lock_room.id}).status_code == 200
