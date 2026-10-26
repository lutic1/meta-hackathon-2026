"""Story 7.12: `POST /access/check` before photo selection, and the per-IP access attempt limit (AD-9, AD-13).

The hosted app is 7.11's `Hosted`: the Dict job store and the Dict attempt
store over one recording jobs dict, with an access clock the tests advance, so the
limit runs offline and a restarted app sees the same count.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from unittest.mock import ANY

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from src.api import wiring
from src.api.errors import AccessDenied, TooManyAttempts
from src.api.wiring import ACCESS_ATTEMPTS, ACCESS_HEADER, access_guard
from src.config import Settings
from src.domain.schema import AccessCheck, Room
from src.infra.modal import BUILD_QUOTA, DictAttemptStore, ModalHandles, hosted_stores
from src.pipeline.build import new_id
from tests.api.test_access import (
    ACCESS_DENIED,
    CLIENT,
    CODE,
    QUOTA_EXCEEDED,
    Hosted,
    WallClock,
    post,
)
from tests.api.test_app import make_app
from tests.api.test_builds import Stages
from tests.infra.test_modal import RecordingDict, StubVolume

WRONG_CODE = "lantern-41"
TOO_MANY = {"error": {"code": "too_many_attempts", "message": ANY, "stage": None}}
ATTEMPT_KEY = ACCESS_ATTEMPTS.key.format(ip="testclient")
"""The store key of the `TestClient`'s address."""


def check(client: TestClient, code: str) -> Response:
    return client.post("/api/access/check", json={"code": code})


# --- The right code: builds left from the hosted JobStore, and nothing started ------


def test_the_right_code_answers_ok_with_the_builds_left_and_starts_nothing(tmp_path: Path):
    hosted = Hosted(tmp_path)
    for _ in range(3):
        hosted.jobs.reserve_build(new_id("job"))
    writes = list(hosted.job_writes())

    response = check(hosted.client, CODE)

    assert response.status_code == 200 and response.json() == {"ok": True, "builds_left": BUILD_QUOTA - 3}
    assert AccessCheck.model_validate(response.json()) == AccessCheck(ok=True, builds_left=BUILD_QUOTA - 3)
    assert hosted.job_writes() == writes and hosted.jobs.builds_left() == BUILD_QUOTA - 3
    assert hosted.jobs.list_ids() == [] and hosted.stored() == set() and hosted.stages.calls == []


def test_with_every_slot_taken_the_right_code_answers_ok_with_none_left(tmp_path: Path):
    hosted = Hosted(tmp_path)
    hosted.claim_all()
    assert check(hosted.client, CODE).json() == {"ok": True, "builds_left": 0}


# --- A wrong code: 200 ok false, never the envelope ---------------------------------


@pytest.mark.parametrize("code", [WRONG_CODE, "", CODE.upper(), f"{CODE} "])
def test_a_wrong_code_answers_200_ok_false_with_no_count_and_starts_nothing(tmp_path: Path, code: str):
    hosted = Hosted(tmp_path)
    response = check(hosted.client, code)
    assert response.status_code == 200 and response.json() == {"ok": False, "builds_left": None}
    assert "error" not in response.json()
    assert hosted.job_writes() == [] and hosted.stored() == set() and hosted.stages.calls == []


def test_without_an_access_code_configured_every_check_answers_ok_false(tmp_path: Path):
    hosted = Hosted(tmp_path, access_code=None)
    for code in ("", CODE, "anything"):
        assert check(hosted.client, code).json() == {"ok": False, "builds_left": None}


# --- More than 10 attempts per IP in 10 minutes: 429 before the code is compared ----


def test_the_limit_window_and_key_are_one_named_constant():
    assert (ACCESS_ATTEMPTS.attempts, ACCESS_ATTEMPTS.window_ms, ACCESS_ATTEMPTS.key) == (10, 600_000, "attempts:{ip}")


def test_the_11th_attempt_mixing_checks_and_guarded_routes_is_the_only_one_refused(
    tmp_path: Path, four_lock_room: Room, monkeypatch: pytest.MonkeyPatch
):
    hosted = Hosted(tmp_path, four_lock_room)
    done = hosted.done(four_lock_room)
    compared: list[bytes] = []
    compare_digest = secrets.compare_digest

    def counting(a: bytes, b: bytes) -> bool:
        compared.append(a)
        return compare_digest(a, b)

    monkeypatch.setattr(wiring.secrets, "compare_digest", counting)
    client = hosted.client
    room = f"/api/builds/{done.id}/room"
    attempts = [
        (lambda: check(client, CODE), 200),
        (lambda: check(client, WRONG_CODE), 200),
        (lambda: post(client, {ACCESS_HEADER: WRONG_CODE}), 403),
        (lambda: post(client, {ACCESS_HEADER: CODE}), 202),
        (lambda: client.get(room, headers={ACCESS_HEADER: WRONG_CODE}), 403),
        (lambda: client.get(room, headers={ACCESS_HEADER: CODE}), 200),
        (lambda: post(client, {}), 403),
        (lambda: client.get(room), 403),
        (lambda: check(client, ""), 200),
        (lambda: check(client, CODE), 200),
    ]
    for attempt, status in attempts:
        hosted.clock.advance_s(1)
        assert attempt().status_code == status

    hosted.clock.advance_s(1)
    before = len(compared)
    refused = check(client, CODE)

    assert refused.status_code == 429 and refused.json() == TOO_MANY
    assert len(compared) == before
    assert int(refused.headers["Retry-After"]) == 600 - 10
    assert len(hosted.attempts.read(ATTEMPT_KEY)) == ACCESS_ATTEMPTS.attempts


@pytest.mark.parametrize("route", ["build", "room"])
def test_a_guarded_route_past_the_limit_is_refused_with_429_before_the_code(
    tmp_path: Path, four_lock_room: Room, route: str
):
    hosted = Hosted(tmp_path, four_lock_room)
    done = hosted.done(four_lock_room)
    for _ in range(ACCESS_ATTEMPTS.attempts):
        check(hosted.client, WRONG_CODE)
    writes = list(hosted.job_writes())
    if route == "build":
        response = post(hosted.client, {ACCESS_HEADER: CODE})
    else:
        response = hosted.client.get(f"/api/builds/{done.id}/room", headers={ACCESS_HEADER: CODE})
    assert response.status_code == 429 and response.json() == TOO_MANY and "Retry-After" in response.headers
    assert hosted.job_writes() == writes and hosted.stages.calls == []
    assert four_lock_room.id not in response.text


def test_an_attempt_after_the_retry_after_wait_answers_normally(tmp_path: Path):
    hosted = Hosted(tmp_path)
    for _ in range(ACCESS_ATTEMPTS.attempts):
        check(hosted.client, WRONG_CODE)
    hosted.clock.advance_s(30)
    refused = check(hosted.client, CODE)
    assert refused.status_code == 429
    wait_s = int(refused.headers["Retry-After"])
    assert wait_s == 600 - 30

    hosted.clock.advance_s(wait_s - 1)
    assert check(hosted.client, CODE).status_code == 429
    hosted.clock.advance_s(1)
    assert check(hosted.client, CODE).json() == {"ok": True, "builds_left": BUILD_QUOTA}
    assert post(hosted.client, {ACCESS_HEADER: CODE}).status_code == 202


def test_the_count_lives_in_the_hosted_store_so_a_restarted_app_keeps_it(tmp_path: Path):
    hosted = Hosted(tmp_path)
    for _ in range(ACCESS_ATTEMPTS.attempts):
        check(hosted.client, CODE)
    assert hosted.dict[ATTEMPT_KEY] == [hosted.clock.ms] * ACCESS_ATTEMPTS.attempts

    restarted = hosted.start()
    assert check(restarted, CODE).status_code == 429
    assert post(restarted, {ACCESS_HEADER: CODE}).status_code == 429


def test_each_client_ip_has_its_own_count():
    store = DictAttemptStore(RecordingDict())
    clock = WallClock()
    guard = access_guard(Settings.from_env({"ACCESS_CODE": CODE}), hosted=True, attempts=store, now_ms=clock.now_ms)
    for _ in range(ACCESS_ATTEMPTS.attempts):
        guard(CODE, CLIENT)
    with pytest.raises(TooManyAttempts):
        guard(CODE, CLIENT)
    assert guard.check(CODE, "198.51.100.9") is True
    with pytest.raises(AccessDenied):
        guard(WRONG_CODE, "198.51.100.9")


def test_the_window_slides_so_each_old_attempt_frees_one_more():
    store = DictAttemptStore(RecordingDict())
    clock = WallClock()
    guard = access_guard(Settings.from_env({"ACCESS_CODE": CODE}), hosted=True, attempts=store, now_ms=clock.now_ms)
    for _ in range(ACCESS_ATTEMPTS.attempts):
        guard.check(WRONG_CODE, CLIENT)
        clock.advance_s(60)
    # ten attempts at 0, 60, ..., 540 s; now 600 s: the first has left the window
    assert guard.check(CODE, CLIENT) is True
    with pytest.raises(TooManyAttempts) as refused:
        guard.check(CODE, CLIENT)
    assert refused.value.headers == {"Retry-After": "60"}


def test_the_dict_attempt_store_shares_the_jobs_dict_and_never_names_a_job(tmp_path: Path):
    handles_jobs = RecordingDict()
    stores = hosted_stores(ModalHandles(handles_jobs, RecordingDict(), RecordingDict(), StubVolume([]), tmp_path))
    stores.attempts.write(ATTEMPT_KEY, [1, 2])
    assert stores.attempts.read(ATTEMPT_KEY) == [1, 2] and stores.attempts.read("attempts:other") == []
    assert handles_jobs[ATTEMPT_KEY] == [1, 2] and stores.jobs.list_ids() == []


def test_the_local_guard_counts_nothing():
    store = DictAttemptStore(RecordingDict())
    guard = access_guard(Settings.from_env({"ACCESS_CODE": CODE}), hosted=False, attempts=store)
    for _ in range(ACCESS_ATTEMPTS.attempts + 5):
        guard(None, CLIENT)
    assert store.read(ACCESS_ATTEMPTS.key.format(ip=CLIENT)) == []


# --- Local mode: the route is not served; the profile routes are 7.2's difference ---


def _routes(client: TestClient) -> set[tuple[str, str]]:
    """Every `(path, method)` the app serves, read from its OpenAPI document."""
    paths = client.get("/api/openapi.json").json()["paths"]
    return {(path, method.upper()) for path, operations in paths.items() for method in operations}


def test_local_mode_does_not_serve_the_check_the_only_route_difference_it_adds(tmp_path: Path):
    local = TestClient(make_app(tmp_path / "local", settings=Settings.from_env({"ACCESS_CODE": CODE}), stages=Stages().functions()))
    response = check(local, CODE)
    assert response.status_code == 404
    hosted = Hosted(tmp_path / "hosted")
    assert _routes(hosted.client) - _routes(local) == {("/api/access/check", "POST")}
    assert {path for path, _ in _routes(local) - _routes(hosted.client)} == {"/api/profile/{name}"}


# --- A check that answered ok does not stand in for the re-check on POST /builds ----


def test_the_last_slot_claimed_after_the_check_is_refused_with_the_quota(tmp_path: Path):
    hosted = Hosted(tmp_path)
    for _ in range(BUILD_QUOTA - 1):
        hosted.jobs.reserve_build(new_id("job"))
    assert check(hosted.client, CODE).json() == {"ok": True, "builds_left": 1}
    hosted.jobs.reserve_build(new_id("job"))  # another judge's Build takes the last slot

    response = post(hosted.client, {ACCESS_HEADER: CODE})

    assert response.status_code == 403 and response.json() == QUOTA_EXCEEDED
    assert hosted.jobs.list_ids() == [] and hosted.stored() == set() and hosted.stages.calls == []


def test_a_code_changed_after_the_check_is_refused_with_access_denied(tmp_path: Path):
    hosted = Hosted(tmp_path)
    assert check(hosted.client, CODE).json()["ok"] is True
    changed = hosted.start(access_code="lantern-43")

    response = post(changed, {ACCESS_HEADER: CODE})

    assert response.status_code == 403 and response.json() == ACCESS_DENIED
    assert hosted.job_writes() == [] and hosted.stored() == set() and hosted.stages.calls == []
