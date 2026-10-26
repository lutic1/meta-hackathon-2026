"""Story 5.3: the cut-2 profile routes read and write `rooms/profiles/<name>.json` in Local mode, refuse an out-of-bounds or unparseable body with 422 in the envelope, and never touch a file outside `rooms/profiles/` (AD-8, AD-13)."""

import ast
from pathlib import Path
from typing import Any
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient

from src.api.app import PROFILES, create_app, profile_key
from src.api.errors import ApiError, InvalidProfileName
from src.config import Settings
from src.domain.schema import Derived, ErrorEnvelope, Profile, RoomResult
from src.infra.local import ROOMS_ROOT

SRC = Path(__file__).resolve().parents[2] / "src"
ROOM_1 = "room_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ROOM_2 = "room_01BX5ZZKBKACTAV9WEVGEMMVRZ"
PZ = "pz_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def room_result(room_id: str, *, demo: bool = False) -> dict[str, Any]:
    return {
        "room_id": room_id, "demo": demo, "elapsed_ms": 240000, "rungs_used": 2, "wrong_attempts": 1,
        "puzzles": [{
            "puzzle_id": PZ, "lock_type": "code", "attempts": 2, "wrong_attempts": 1, "rungs_used": 2,
            "time_to_first_hint": 60000, "solved": True, "time_spent_ms": 240000, "nudge_fired": True,
            "hint_requested": True, "early_ask": False,
        }],
    }


PROFILE: dict[str, Any] = {
    "results": {ROOM_1: room_result(ROOM_1), ROOM_2: room_result(ROOM_2, demo=True)},
    "derived": {"sessions": 1, "persistence": 0.25, "time_to_first_hint_s": 60.0, "mean_rung_per_lock_type": {"code": 2.0}},
}
FRESH: dict[str, Any] = {"results": {}, "derived": Derived.fresh().model_dump(mode="json")}


def profile_file(tmp_path: Path, name: str) -> Path:
    return tmp_path / "rooms" / PROFILES / f"{name}.json"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings.from_env(), rooms_root=tmp_path / "rooms", web_dist=tmp_path / "no-dist"))


def files_under(root: Path) -> list[Path]:
    return sorted(path.relative_to(root) for path in root.rglob("*") if path.is_file())


# --- PUT writes the file, GET reads it back ---------------------------------


@pytest.mark.parametrize("body", [PROFILE, FRESH])
def test_put_writes_rooms_profiles_name_json_and_get_returns_the_same_body(client: TestClient, tmp_path: Path, body: dict[str, Any]):
    response = client.put("/api/profile/demo", json=body)
    assert response.status_code == 200
    assert response.json() == body
    path = profile_file(tmp_path, "demo")
    assert path.is_file() and Profile.model_validate_json(path.read_bytes()).model_dump(mode="json") == body
    assert client.get("/api/profile/demo").status_code == 200
    assert client.get("/api/profile/demo").json() == body
    assert files_under(tmp_path / "rooms") == [Path(PROFILES) / "demo.json"]


def test_a_second_put_replaces_the_file_and_profiles_never_mix(client: TestClient, tmp_path: Path):
    assert client.put("/api/profile/demo", json=PROFILE).status_code == 200
    assert client.put("/api/profile/demo", json=FRESH).status_code == 200
    assert client.get("/api/profile/demo").json() == FRESH
    assert client.put("/api/profile/playtest", json=PROFILE).status_code == 200
    assert client.get("/api/profile/demo").json() == FRESH
    assert client.get("/api/profile/playtest").json() == PROFILE
    assert files_under(tmp_path / "rooms") == [Path(PROFILES) / "demo.json", Path(PROFILES) / "playtest.json"]


def test_get_with_no_file_answers_404_and_creates_nothing(client: TestClient, tmp_path: Path):
    response = client.get("/api/profile/demo")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "profile_not_found", "message": ANY, "stage": None}}
    assert ErrorEnvelope.model_validate(response.json()).status is None
    assert not (tmp_path / "rooms").exists()


# --- A refused body leaves the file byte for byte unchanged -----------------


def _with_derived(**fields: Any) -> dict[str, Any]:
    return {**PROFILE, "derived": {**PROFILE["derived"], **fields}}


REFUSED: dict[str, Any] = {
    "persistence 1.5": _with_derived(persistence=1.5),
    "persistence -1.5": _with_derived(persistence=-1.5),
    "sessions -1": _with_derived(sessions=-1),
    "mean_rung 4": _with_derived(mean_rung_per_lock_type={"code": 4}),
    "unknown lock type": _with_derived(mean_rung_per_lock_type={"lever": 1}),
    "no derived": {"results": PROFILE["results"]},
    "no results": {"derived": PROFILE["derived"]},
    "unknown field": {**PROFILE, "name": "demo"},
    "result does not parse": {**PROFILE, "results": {ROOM_1: {"room_id": ROOM_1, "demo": False}}},
    "result keyed by another room": {**PROFILE, "results": {ROOM_1: room_result(ROOM_2)}},
    "results not a map": {**PROFILE, "results": [room_result(ROOM_1)]},
    "bad room id key": {**PROFILE, "results": {"room-1": room_result(ROOM_1)}},
}


@pytest.mark.parametrize("body", REFUSED.values(), ids=REFUSED)
def test_an_out_of_bounds_or_unparseable_body_answers_422_and_leaves_the_file_unchanged(
    client: TestClient, tmp_path: Path, body: dict[str, Any],
):
    assert client.put("/api/profile/demo", json=FRESH).status_code == 200
    before = profile_file(tmp_path, "demo").read_bytes()
    response = client.put("/api/profile/demo", json=body)
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "invalid_profile", "message": ANY, "stage": None}}
    assert ErrorEnvelope.model_validate(response.json()).status is None
    assert profile_file(tmp_path, "demo").read_bytes() == before
    assert client.get("/api/profile/demo").json() == FRESH


@pytest.mark.parametrize("content", [b"", b"not json", b"[]", b"null", b'"demo"'])
def test_a_body_that_is_not_a_json_object_answers_422_in_the_envelope(client: TestClient, tmp_path: Path, content: bytes):
    response = client.put("/api/profile/demo", content=content, headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "invalid_profile", "message": ANY, "stage": None}}
    assert not (tmp_path / "rooms").exists()


def test_the_422_message_names_the_failing_field_and_not_the_body(client: TestClient):
    response = client.put("/api/profile/demo", json=_with_derived(persistence=1.5))
    assert response.json()["error"]["message"].startswith("profile demo does not parse: derived.persistence: ")
    assert ROOM_1 not in response.text


# --- A name outside rooms/profiles/ ------------------------------------------


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "../demo", "/etc/passwd", "demo/", "profiles/../demo"])
def test_profile_key_refuses_a_name_that_is_not_a_file_name(name: str):
    with pytest.raises(InvalidProfileName) as excinfo:
        profile_key(name)
    assert isinstance(excinfo.value, ApiError) and (excinfo.value.status, excinfo.value.code) == (422, "invalid_profile_name")


@pytest.mark.parametrize("name", ["demo", "dev", "playtest", "my-profile_2", "demo.json"])
def test_profile_key_is_profiles_name_json(name: str):
    assert profile_key(name) == f"{PROFILES}/{name}.json"
    assert Path(profile_key(name)).parent == Path(PROFILES)


# `%2E%2E` reaches the handler as `..`; an encoded slash never matches `{name}`; a NUL byte breaks the resolved path.
@pytest.mark.parametrize("name", ["%2E%2E", "%2E", "a%00b"])
def test_a_route_name_that_would_leave_rooms_profiles_is_refused_with_422(client: TestClient, tmp_path: Path, name: str):
    for method in ("GET", "PUT"):
        response = client.request(method, f"/api/profile/{name}", json=PROFILE)
        assert response.status_code == 422, (method, name)
        assert response.json() == {"error": {"code": "invalid_profile_name", "message": ANY, "stage": None}}
    assert not (tmp_path / "rooms").exists()


@pytest.mark.parametrize("name", ["..%2Fdemo", "demo%2F..%2F..%2Fx", "%2Fetc%2Fpasswd", ""])
def test_a_route_name_with_a_path_separator_matches_no_route_and_writes_nothing(client: TestClient, tmp_path: Path, name: str):
    assert client.get(f"/api/profile/{name}").status_code == 404
    assert client.put(f"/api/profile/{name}", json=PROFILE).status_code in (404, 405)
    assert not (tmp_path / "rooms").exists()


def test_nothing_is_written_outside_rooms_profiles(client: TestClient, tmp_path: Path):
    (tmp_path / "rooms").mkdir()
    assert client.put("/api/profile/demo", json=PROFILE).status_code == 200
    for name in ("%2E%2E", "a%00b", "..%2Fdemo", "demo%2F..%2F..%2Fx"):
        client.put(f"/api/profile/{name}", json=PROFILE)
        client.get(f"/api/profile/{name}")
    assert files_under(tmp_path) == [Path("rooms") / PROFILES / "demo.json"]


# --- Only the profile routes touch rooms/profiles/ ---------------------------


def _names(path: Path) -> set[str]:
    """Every bare name a module's code uses, docstrings aside."""
    return {node.id for node in ast.walk(ast.parse(path.read_text(), filename=str(path))) if isinstance(node, ast.Name)}


def test_only_the_profile_routes_name_rooms_profiles_or_use_the_profile_model():
    """No session log, prompt, ledger entry or cache key can hold a stored profile: no other code reaches one."""
    names = {path.relative_to(SRC).as_posix(): _names(path) for path in SRC.rglob("*.py")}
    assert {module for module, used in names.items() if used & {"PROFILES", "profile_key"}} == {"api/app.py"}
    assert {module for module, used in names.items() if "Profile" in used} == {"api/app.py", "domain/schema.py"}


def test_the_profile_routes_live_under_api_and_the_default_app_reads_rooms_profiles():
    from src.api.app import app

    paths = app.openapi()["paths"]
    assert set(paths["/api/profile/{name}"]) == {"get", "put"}
    assert ROOMS_ROOT / PROFILES == Path("rooms/profiles")


# --- The model ----------------------------------------------------------------


def test_profile_is_the_results_keyed_by_room_id_plus_the_derived_block():
    assert set(Profile.model_fields) == {"results", "derived"}
    profile = Profile.model_validate(PROFILE)
    assert set(profile.results) == {ROOM_1, ROOM_2}
    assert all(isinstance(result, RoomResult) and result.room_id == key for key, result in profile.results.items())
    assert isinstance(profile.derived, Derived)
    assert Profile.model_validate(FRESH).derived == Derived.fresh()
