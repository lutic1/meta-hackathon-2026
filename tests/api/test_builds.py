"""Story 2.12: the build routes over the persisted job, the restart of jobs a stopped API left behind, and the ledger export at startup and after every Build (AD-3, AD-7, AD-9, AD-13)."""

import json
import threading
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, get_args
from unittest.mock import ANY

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from src.api.app import create_app, read_uploads
from src.api.wiring import artifact_store, job_store, ledger_store
from src.config import Settings
from src.domain.ledger import LedgerEntry
from src.domain.schema import JobState, JobStatus, MaskPreview, Room, Stage, StageRecord
from src.infra.clocks import BuildClock
from src.infra.local import (
    CACHE_ROOT,
    EXPORTS_ROOT,
    LEDGER_PATH,
    LedgerExport,
    export_path,
)
from src.pipeline.build import STAGES, TERMINAL, Build, StageResult, new_id
from src.pipeline.ingest import Upload, photo_keys
from src.pipeline.ports import room_key
from src.providers.base import ProviderError
from src.providers.spend import new_call_id
from tests.domain.test_redact import json_keys
from tests.fixtures.rooms import SENTINEL_CODE, SENTINEL_IX, with_sentinel_solutions
from tests.infra.test_clocks import Ticker
from tests.pipeline.test_build import RunnerDied
from tests.pipeline.uploads import image_bytes, make_uploads

TODAY = date(2026, 10, 27)
UNKNOWN_JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ROOM_KEYS = {"solution", "puzzles", "interactables", "photos", "provenance", "decoys"}
"""Keys a Room carries and the job state never does."""


class Stages:
    """One double per stage after ingest, recording `(job_id, stage)` for every call; `hooks` run inside a stage."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Stage]] = []
        self.hooks: dict[Stage, Callable[[JobState], None]] = {}
        self._lock = threading.Lock()

    def _stage(self, stage: Stage) -> Callable[[JobState], StageResult]:
        def run(state: JobState) -> StageResult:
            with self._lock:
                self.calls.append((state.id, stage))
            if stage in self.hooks:
                self.hooks[stage](state)
            return StageResult()

        return run

    def functions(self) -> dict[Stage, Callable[[JobState], StageResult]]:
        return {stage: self._stage(stage) for stage in STAGES[1:]}

    def of(self, job_id: str) -> list[Stage]:
        with self._lock:
            return [stage for id_, stage in self.calls if id_ == job_id]


def builds_app(tmp_path: Path, stages: Stages) -> FastAPI:
    """The app over `tmp_path` with the stage doubles; the ledger, its exports and the cache stay out of the repo."""
    return create_app(
        Settings.from_env(),
        rooms_root=tmp_path / "rooms",
        web_dist=tmp_path / "no-dist",
        stages=stages.functions(),
        ledger_path=tmp_path / LEDGER_PATH,
        exports_root=tmp_path / EXPORTS_ROOT,
        cache_root=tmp_path / CACHE_ROOT,
        today=lambda: TODAY,
    )


def files(uploads: list[Upload]) -> list[tuple[str, tuple[str, bytes, str]]]:
    """The multipart parts of `POST /builds`: a `downscale` and an `original` per photo, in upload order."""
    parts: list[tuple[str, tuple[str, bytes, str]]] = []
    for index, upload in enumerate(uploads):
        parts.append(("downscale", (f"{index}.jpg", upload.downscale, "image/jpeg")))
        parts.append(("original", (f"IMG_{index}.jpg", upload.original, "image/jpeg")))
    return parts


def post(client: TestClient, uploads: list[Upload]) -> Response:
    return client.post("/api/builds", files=files(uploads))


def wait_terminal(client: TestClient, job_id: str, seen: list[Any] | None = None, timeout_s: float = 5.0) -> dict[str, Any]:
    """Poll `GET /builds/<job_id>` until it answers 200; every body read on the way is appended to `seen`."""
    deadline = time.monotonic() + timeout_s
    while True:
        response = client.get(f"/api/builds/{job_id}")
        if seen is not None:
            seen.append(response.json())
        if response.status_code == 200:
            return response.json()
        assert response.status_code == 202 and time.monotonic() < deadline, response.json()
        time.sleep(0.01)


def read_export(tmp_path: Path) -> LedgerExport:
    return LedgerExport.model_validate_json(export_path(tmp_path / EXPORTS_ROOT, TODAY).read_text())


def wait_export(tmp_path: Path, job_id: str, timeout_s: float = 5.0) -> LedgerExport:
    """The export once it holds an entry of `job_id`: the runner writes it after the job is terminal in the store.

    The export replaces its file whole, so every read while the runner rewrites it parses.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        export = read_export(tmp_path) if export_path(tmp_path / EXPORTS_ROOT, TODAY).exists() else None
        if export is not None and any(entry.job_id == job_id for entry in export.entries):
            return export
        assert time.monotonic() < deadline, f"no export entry for {job_id}"
        time.sleep(0.01)


@pytest.fixture
def stages() -> Stages:
    return Stages()


@pytest.fixture
def client(tmp_path: Path, stages: Stages) -> TestClient:
    return TestClient(builds_app(tmp_path, stages))


# --- POST /builds returns a job id without blocking on a stage --------------


def test_post_builds_returns_a_job_id_while_a_stage_is_held_open(client: TestClient, stages: Stages, tmp_path: Path):
    entered, release = threading.Event(), threading.Event()

    def hold(state: JobState) -> None:
        entered.set()
        assert release.wait(5)

    stages.hooks["architect"] = hold
    uploads = make_uploads(6)
    response = post(client, uploads)

    assert response.status_code == 202
    queued = JobState.model_validate(response.json())
    assert queued.status in ("queued", "running") and queued.id.startswith("job_")
    assert entered.wait(5)
    held = client.get(f"/api/builds/{queued.id}")
    assert held.status_code == 202 and (held.json()["status"], held.json()["stage"]) == ("running", "architect")
    release.set()
    assert wait_terminal(client, queued.id)["status"] == "done"
    assert stages.of(queued.id) == list(STAGES[1:])


def test_post_builds_stores_each_downscale_and_original_byte_for_byte(client: TestClient, tmp_path: Path):
    uploads = make_uploads(7)
    job_id = post(client, uploads).json()["id"]
    state = wait_terminal(client, job_id)
    store = artifact_store(tmp_path / "rooms")
    for index, upload in enumerate(uploads):
        downscale, original = photo_keys(state["room_id"], index)
        assert store.read(downscale) == upload.downscale and store.read(original) == upload.original


def test_multipart_parts_round_trip_bytes_that_look_like_boundaries_and_line_ends():
    tricky = [Upload(b"\r\n--x\r\n\n\r" + bytes(range(256)) * 4 + b"\r\n", b"\xff\xd8\r\n\r\n--\r\n" * 50) for _ in range(3)]
    request = TestClient(FastAPI()).build_request("POST", "/", files=files(tricky))
    assert read_uploads(request.headers["content-type"], request.read()) == tricky


# --- Ingest refusals: 422 at stage ingest, and no job ------------------------


def _with(uploads: list[Upload], index: int, *, downscale: bytes | None = None, original: bytes | None = None) -> list[Upload]:
    changed = list(uploads)
    changed[index] = Upload(downscale or uploads[index].downscale, original or uploads[index].original)
    return changed


SIX = make_uploads(6)
REFUSED = {
    "five photos": (make_uploads(5), "photo_count"),
    "eleven photos": (make_uploads(11), "photo_count"),
    "a PNG downscale": (_with(SIX, 3, downscale=image_bytes(1280, 960, format="PNG")), "unsupported_image"),
    "a PNG original": (_with(SIX, 0, original=image_bytes(2560, 1920, format="PNG")), "unsupported_image"),
    "a 1024 px downscale": (_with(SIX, 1, downscale=image_bytes(1024, 768)), "bad_downscale"),
    "a rotated downscale": (_with(SIX, 4, downscale=image_bytes(1280, 960, orientation=6)), "bad_downscale"),
}


@pytest.mark.parametrize("uploads, code", REFUSED.values(), ids=REFUSED.keys())
def test_an_upload_ingest_refuses_answers_422_at_ingest_and_queues_no_job(
    client: TestClient, stages: Stages, tmp_path: Path, uploads: list[Upload], code: str
):
    response = post(client, uploads)
    assert response.status_code == 422
    assert response.json() == {"error": {"code": code, "message": ANY, "stage": "ingest"}}
    assert job_store(tmp_path / "rooms").list_ids() == [] and stages.calls == []
    assert not (tmp_path / "rooms").exists() or not any((tmp_path / "rooms").rglob("*.jpg"))


def test_a_downscale_without_its_original_is_refused_as_photo_count(client: TestClient, tmp_path: Path):
    parts = files(SIX)[:-1]
    response = client.post("/api/builds", files=parts)
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "photo_count", "message": ANY, "stage": "ingest"}}
    assert job_store(tmp_path / "rooms").list_ids() == []


def test_a_body_that_is_not_multipart_holds_no_photos(client: TestClient, tmp_path: Path):
    response = client.post("/api/builds", content=b"not a form", headers={"content-type": "application/octet-stream"})
    assert response.status_code == 422 and response.json()["error"]["code"] == "photo_count"
    assert job_store(tmp_path / "rooms").list_ids() == []


# --- GET /builds/<job_id> reads persisted state only -------------------------


def _persisted(status: JobStatus) -> JobState:
    """A stored job in `status`, past segment, with its Mask preview."""
    stages = [StageRecord(stage=stage, duration_ms=10) for stage in STAGES[:3]]
    preview = [MaskPreview(id=new_id("ix"), label="mug", photo=0, polygons=[[(0, 0), (8, 0), (8, 8)]])]
    return JobState(
        id=new_id("job"),
        status=status,
        stage="author" if status == "running" else None,
        room_id=new_id("room"),
        stages=stages,
        regen_max=2,
        mask_preview=preview,
    )


@pytest.mark.parametrize("status", get_args(JobStatus))
def test_job_state_answers_202_while_queued_or_running_and_200_when_terminal(tmp_path: Path, stages: Stages, status: JobStatus):
    state = _persisted(status)
    job_store(tmp_path / "rooms").put(state)

    response = TestClient(builds_app(tmp_path, stages)).get(f"/api/builds/{state.id}")

    assert response.status_code == (200 if status in TERMINAL else 202)
    assert response.json() == state.model_dump(mode="json")
    assert response.json()["mask_preview"][0]["label"] == "mug" and stages.calls == []


def test_an_unknown_job_answers_404(client: TestClient):
    for path in (f"/api/builds/{UNKNOWN_JOB}", f"/api/builds/{UNKNOWN_JOB}/room", "/api/builds/not-a-job"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json() == {"error": {"code": "job_not_found", "message": ANY, "stage": None}}


def test_a_job_file_that_does_not_parse_is_a_server_error_not_an_unknown_job(tmp_path: Path, stages: Stages):
    (tmp_path / "rooms" / "jobs").mkdir(parents=True)
    (tmp_path / "rooms" / "jobs" / f"{UNKNOWN_JOB}.json").write_text("{}")
    client = TestClient(builds_app(tmp_path, stages), raise_server_exceptions=False)
    assert client.get(f"/api/builds/{UNKNOWN_JOB}").status_code == 500


def test_job_state_reads_the_same_from_a_second_app_over_the_same_store(client: TestClient, tmp_path: Path):
    job_id = post(client, make_uploads(6)).json()["id"]
    finished = wait_terminal(client, job_id)
    restarted = TestClient(builds_app(tmp_path, Stages()))
    response = restarted.get(f"/api/builds/{job_id}")
    assert response.status_code == 200 and response.json() == finished


# --- No Room in job state; the full Room only from /builds/<job_id>/room ------


def test_job_state_never_carries_a_room_and_only_the_room_route_returns_one(
    client: TestClient, stages: Stages, tmp_path: Path, four_lock_room: Room
):
    store = artifact_store(tmp_path / "rooms")
    room: dict[str, Room] = {}
    entered, release = threading.Event(), threading.Event()

    def hold(state: JobState) -> None:
        entered.set()
        assert release.wait(5)

    def scene(state: JobState) -> None:
        assert state.room_id is not None
        room["room"] = with_sentinel_solutions(four_lock_room).model_copy(update={"id": state.room_id})
        store.put(room_key(state.room_id), room["room"].model_dump_json().encode())

    stages.hooks.update({"dryrun": hold, "scene": scene})
    posted = post(client, make_uploads(6)).json()
    assert entered.wait(5)
    seen = [client.get(f"/api/builds/{posted['id']}").json()]
    assert client.get(f"/api/builds/{posted['id']}/room").json()["error"] == {
        "code": "build_not_ready", "message": ANY, "stage": None, "status": "running",
    }
    release.set()
    final = wait_terminal(client, posted["id"], seen)

    assert final["status"] == "done"
    for body in (posted, *seen):
        assert json_keys(body).isdisjoint(ROOM_KEYS)
        text = json.dumps(body)
        assert SENTINEL_CODE not in text and not any(ix in text for ix in SENTINEL_IX)
    full = client.get(f"/api/builds/{posted['id']}/room")
    assert full.status_code == 200 and Room.model_validate(full.json()) == room["room"]
    assert SENTINEL_CODE in full.text
    play = client.get(f"/api/rooms/{final['room_id']}")
    assert play.status_code == 200 and "solution" not in json_keys(play.json())


@pytest.mark.parametrize("status", sorted(set(get_args(JobStatus)) - {"done"}))
def test_the_room_route_answers_409_build_not_ready_with_the_status_until_the_job_is_done(tmp_path: Path, stages: Stages, status: JobStatus):
    """Decision 37: a known job not yet `done` is not an unknown Room; its envelope carries the job status, as the Build view's does."""
    state = _persisted(status)
    job_store(tmp_path / "rooms").put(state)
    response = TestClient(builds_app(tmp_path, stages)).get(f"/api/builds/{state.id}/room")
    assert response.status_code == 409
    assert response.json() == {"error": {"code": "build_not_ready", "message": ANY, "stage": None, "status": status}}


# --- A restarted API resumes every job left queued or running ----------------


def test_a_restarted_api_resumes_each_unfinished_job_after_its_last_persisted_stage(tmp_path: Path):
    root = tmp_path / "rooms"
    first = Stages()
    build = Build(jobs=job_store(root), artifacts=artifact_store(root), clock=BuildClock(monotonic_ns=Ticker()),
                  stages=first.functions(), regen_max=2)
    queued = build.submit(make_uploads(6))
    running = build.submit(make_uploads(8))
    done = build.submit(make_uploads(6))
    build.run(done.id)

    def die(state: JobState) -> None:
        raise RunnerDied()

    first.hooks["segment"] = die
    with pytest.raises(RunnerDied):
        build.run(running.id)
    before = job_store(root).read(running.id)
    assert (before.status, before.stage, [r.stage for r in before.stages]) == ("running", "segment", ["ingest", "architect"])

    second = Stages()
    app = builds_app(tmp_path, second)
    assert TestClient(app).get(f"/api/builds/{running.id}").json() == before.model_dump(mode="json")
    with TestClient(app) as client:
        assert wait_terminal(client, queued.id)["status"] == "done"
        assert wait_terminal(client, running.id)["status"] == "done"

    assert second.of(queued.id) == list(STAGES[1:])
    assert second.of(running.id) == ["segment", "author", "validate", "dryrun", "scene"]
    assert second.of(done.id) == [] and first.of(running.id).count("architect") == 1


# --- The ledger export at startup and after every terminal Build -------------


def _entry(job_id: str | None, stage: Stage | None = None) -> LedgerEntry:
    return LedgerEntry(call_id=new_call_id(), kind="vision", status="settled", usd=0.03, job_id=job_id, stage=stage)


def test_api_startup_writes_the_dated_export(tmp_path: Path, stages: Stages):
    earlier = _entry(None)
    ledger_store(tmp_path / LEDGER_PATH).append(earlier)
    app = builds_app(tmp_path, stages)
    assert not export_path(tmp_path / EXPORTS_ROOT, TODAY).exists()

    with TestClient(app):
        export = read_export(tmp_path)

    assert export.date == TODAY.isoformat() and [e.call_id for e in export.entries] == [earlier.call_id]
    assert export.total_usd == pytest.approx(0.03) and export.ceiling_usd == 80


@pytest.mark.parametrize("fails", [False, True], ids=["done", "failed"])
def test_a_build_reaching_a_terminal_status_is_exported_with_its_entries(tmp_path: Path, stages: Stages, fails: bool):
    ledger = ledger_store(tmp_path / LEDGER_PATH)

    def architect(state: JobState) -> None:
        ledger.append(_entry(state.id, "architect"))
        if fails:
            raise ProviderError(503, "overloaded", "try later")

    stages.hooks["architect"] = architect
    with TestClient(builds_app(tmp_path, stages)) as client:
        job_id = post(client, make_uploads(6)).json()["id"]
        final = wait_terminal(client, job_id)
        export = wait_export(tmp_path, job_id)

    assert final["status"] == ("failed" if fails else "done")
    assert [(e.job_id, e.stage) for e in export.entries] == [(job_id, "architect")]
