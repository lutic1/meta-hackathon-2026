"""Story 7.8: a hosted Build spawned per job and polled to the end over persisted state (AD-7, FR-32, NFR-7).

No test reaches Modal. The hosted app runs over plain dicts and a
temporary Volume directory; `run_build.spawn` is a stub that records the
job id and runs nothing, and the test then plays the spawned container by
calling the runner body, `run_hosted_build`, over the same handles. The
Dict, the Volume stub and the spawn write to one log, so the order of the
`POST /builds` steps can be read from it. Stage durations come from a fake
build clock.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api import wiring
from src.api.wiring import ACCESS_HEADER
from src.domain.schema import JobId, JobState, Room, Stage
from src.infra.clocks import BuildClock
from src.infra.modal import ModalHandles, call_key, hosted_stores, slot_key
from src.pipeline.build import StageResult
from src.pipeline.ports import room_key
from tests.api.hosted import SpawnedCall, hosted_settings, make_hosted_app, still_running
from tests.api.test_builds import files
from tests.infra.test_clocks import Ticker
from tests.infra.test_modal import RecordingDict, StubVolume
from tests.pipeline.test_build import Doubles
from tests.pipeline.test_regenerate import DRY_MESSAGE, DryRunRefused
from tests.pipeline.uploads import make_uploads

CODE = "lantern-42"
SETTINGS = hosted_settings(ACCESS_CODE=CODE)
WEB_TIMEOUT_MS = 150_000
"""Modal's web request limit, which no Build may depend on."""
BUDGET_MS: dict[Stage, int] = {"architect": 15_000, "segment": 10_000, "author": 45_000, "validate": 0, "dryrun": 30_000, "scene": 10_000}
"""The `budgets.md` stage budgets: 110 s clean, and each Regeneration repeats author, validate and dryrun (75 s)."""


class LoggedDict(RecordingDict):
    """The `keyframe-jobs` Dict, logging each item write as `set <key>`."""

    def __init__(self, log: list[str]) -> None:
        super().__init__()
        self.log = log

    def __setitem__(self, key: Any, value: Any) -> None:
        self.log.append(f"set {key}")
        super().__setitem__(key, value)


class LoggedSpawn:
    """`run_build.spawn`: logs `spawn <job_id>` and returns a call at once, running nothing."""

    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.job_ids: list[JobId] = []

    def __call__(self, job_id: JobId) -> SpawnedCall:
        self.log.append(f"spawn {job_id}")
        self.job_ids.append(job_id)
        return SpawnedCall(f"fc-{len(self.job_ids)}")


class Hosted:
    """The hosted web app and the spawned runner over one set of handles, with stage doubles timed on a fake build clock."""

    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.log: list[str] = []
        self.spawn = LoggedSpawn(self.log)
        self.handles = ModalHandles(
            jobs=LoggedDict(self.log), sessions={}, ledger={}, volume=StubVolume(self.log), root=tmp_path / "data",
            spawn=self.spawn, poll=still_running,
        )
        self.ticker = Ticker()
        monkeypatch.setattr(wiring, "build_clock", lambda: BuildClock(monotonic_ns=self.ticker))  # ingest too, in the web app
        self.web_stages = Doubles(self.ticker)
        self.client = TestClient(make_hosted_app(tmp_path, self.handles, settings=SETTINGS, stages=self.web_stages.stages()))

    def post(self) -> JobId:
        response = self.client.post("/api/builds", files=files(make_uploads(6)), headers={ACCESS_HEADER: CODE})
        assert response.status_code == 202 and response.json()["status"] == "queued"
        return response.json()["id"]

    def poll(self, job_id: JobId) -> tuple[int, str, str | None]:
        """One `GET /builds/<job_id>`, which must write nothing to the Dict."""
        writes = len(self.handles.jobs.writes)
        response = self.client.get(f"/api/builds/{job_id}")
        assert len(self.handles.jobs.writes) == writes
        body = response.json()
        return response.status_code, body["status"], body["stage"]

    def run(self, job_id: JobId, doubles: Doubles) -> JobState:
        """The spawned `run_build(job_id)`, in its own container over the same Dict and Volume."""
        return wiring.run_hosted_build(SETTINGS, self.handles, job_id, stages=doubles.stages())


# --- POST /builds: photos committed, the queued record, then the spawn ----------------------


def test_post_builds_commits_the_photos_writes_the_queued_record_then_spawns_and_answers_at_once(tmp_path, monkeypatch):
    hosted = Hosted(tmp_path, monkeypatch)
    job_id = hosted.post()
    queued = hosted_stores(hosted.handles).jobs.read(job_id)
    photos = [path for path in (hosted.handles.root / "rooms" / "judge" / str(queued.room_id)).rglob("*") if path.is_file()]
    assert len(photos) == 13  # six downscales, six originals, and the photo list
    steps = [line for line in hosted.log if not line.startswith("set attempts:")]
    assert steps == [f"set {slot_key(1)}", *["commit"] * len(photos), f"set {job_id}", f"spawn {job_id}", f"set {call_key(job_id)}"]
    assert hosted.spawn.job_ids == [job_id] and hosted.handles.jobs[call_key(job_id)] == "fc-1"
    assert queued.status == "queued" and queued.stage is None and [record.stage for record in queued.stages] == ["ingest"]
    assert hosted.web_stages.calls == []  # the web function ran no stage after ingest
    assert hosted.poll(job_id) == (202, "queued", None)


def test_a_second_build_waits_queued_until_the_first_runner_ends(tmp_path, monkeypatch):
    hosted = Hosted(tmp_path, monkeypatch)
    first, second = hosted.post(), hosted.post()
    assert hosted.spawn.job_ids == [first, second]
    doubles = Doubles(hosted.ticker)
    seen: list[tuple[int, str, str | None]] = []
    doubles.hooks["architect"] = lambda state: seen.append(hosted.poll(second))
    assert hosted.run(first, doubles).status == "done"
    assert seen == [(202, "queued", None)] and hosted.poll(second) == (202, "queued", None)
    assert hosted.run(second, Doubles(hosted.ticker)).status == "done" and hosted.poll(second)[:2] == (200, "done")


# --- A Build longer than the web timeout, polled to the end -------------------------------------


def test_a_260_s_build_with_two_regenerations_is_polled_over_persisted_state_to_done_and_its_room_plays(
    tmp_path, monkeypatch, four_lock_room: Room
):
    hosted = Hosted(tmp_path, monkeypatch)
    job_id = hosted.post()
    room_id = str(hosted_stores(hosted.handles).jobs.read(job_id).room_id)
    polls = [hosted.poll(job_id)]
    doubles = Doubles(hosted.ticker, advance_ms=0)

    def timed(stage: Stage) -> None:
        def hook(state: JobState) -> None:
            polls.append(hosted.poll(job_id))
            hosted.ticker.advance_ms(BUDGET_MS[stage])
            if stage == "dryrun" and state.regeneration_count < 2:
                raise DryRunRefused([DRY_MESSAGE], StageResult(count=3))
            if stage == "scene":
                room = four_lock_room.model_copy(update={"id": room_id})
                hosted_stores(hosted.handles).artifacts.put(room_key(room_id), room.model_dump_json().encode())

        doubles.hooks[stage] = hook

    for stage in BUDGET_MS:
        timed(stage)
    done = hosted.run(job_id, doubles)

    attempt = [(202, "running", "author"), (202, "running", "validate"), (202, "running", "dryrun")]
    assert polls == [
        (202, "queued", None),
        (202, "running", "architect"),
        (202, "running", "segment"),
        *attempt * 3,
        (202, "running", "scene"),
    ]
    assert done.status == "done" and done.regeneration_count == 2
    assert done.build_time_ms == 260_000 and done.build_time_ms > WEB_TIMEOUT_MS
    final = hosted.client.get(f"/api/builds/{job_id}")
    assert final.status_code == 200 and final.json()["status"] == "done" and final.json()["build_time_ms"] == 260_000
    play = hosted.client.get(f"/api/rooms/{room_id}")
    assert play.status_code == 200 and play.json()["id"] == room_id
    assert [puzzle["id"] for puzzle in play.json()["puzzles"]] == [puzzle.id for puzzle in four_lock_room.puzzles]
    assert hosted.web_stages.calls == []
