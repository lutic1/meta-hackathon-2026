"""Story 7.19: `scripts/purge_judge_rooms.py` runs `delete_judge_room` on every Judge room and prints what it removed (FR-33, NFR-4, AD-9).

No test reaches Modal: the Dicts are plain dicts, the Volume is a temporary
directory behind a stub that logs `commit` and `reload`, each Judge room is
built by the real `Build` over the hosted stores, and the script's container
run is replaced by `purge` over those handles.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from src.api.app import room_routes, session_routes
from src.api.errors import ApiError, handle_api_error, handle_validation_error
from src.config import Settings
from src.domain.schema import JobState, Room
from src.infra.clocks import SessionClock
from src.infra.modal import (
    CACHE_DIR,
    DeletionRecord,
    DictSessionStore,
    ModalHandles,
    call_key,
    hosted_stores,
)
from src.providers.verbatim import VerbatimPhraser
from tests.api.test_sessions import Ticker as PlayTicker
from tests.api.test_sessions import click, code
from tests.infra.test_clocks import Ticker
from tests.infra.test_local import JOB_A
from tests.infra.test_modal import RecordingDict, StubVolume, seed_demo
from tests.infra.test_modal_partitions import ENDINGS, JudgeBuild, _snapshot
from tests.infra.test_modal_retention import (
    ENTRY,
    HOUR_MS,
    NOW,
    played,
    reminted,
    sess_at,
    store_session,
    wall_ms,
)

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/purge_judge_rooms.py"
NOV_10 = date(2026, 11, 10)


def _load():
    spec = importlib.util.spec_from_file_location("purge_judge_rooms_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


purger = _load()


# --- The hosted data: a Demo room beside Judge rooms ------------------------------


@pytest.fixture
def handles(tmp_path: Path) -> ModalHandles:
    return ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume([]), root=tmp_path / "data")


class Judge:
    """One Judge build ended `ending`; a `done` one has a recent Session on its Room."""

    def __init__(self, handles: ModalHandles, room: Room, ending: str, keys: list[str]) -> None:
        self.handles = handles
        self.build = JudgeBuild(handles, Ticker(), room)
        raises, status = ENDINGS[ending]
        self.state = self.build.run(chats={"segment": keys}, raises=raises)
        assert self.state.status == status
        self.keys = keys
        handles.jobs[call_key(self.state.id)] = "fc-judge"
        self.session: str | None = None
        if status == "done":
            self.session = sess_at(wall_ms(NOW) - HOUR_MS)
            store_session(handles, self.session, played(self.build.stored_room))

    @property
    def room_id(self) -> str:
        return self.build.room_id

    @property
    def folder(self) -> Path:
        return self.handles.root / "rooms" / "judge" / self.room_id


class Hosted:
    """A seeded Demo room with a Cache entry and a recent Session, and Judge rooms with and without a Room."""

    def __init__(self, handles: ModalHandles, demo: Room, judge_room: Room, endings: list[str]) -> None:
        self.handles = handles
        self.demo = demo
        seed_demo(handles, demo, JobState(id=JOB_A, status="done", room_id=demo.id, regen_max=2, build_time_ms=28_000))
        hosted_stores(handles).cache.put("k-demo", ENTRY)
        self.demo_session = sess_at(wall_ms(NOW) - HOUR_MS)
        store_session(handles, self.demo_session, played(demo))
        self.judges = [Judge(handles, judge_room, ending, [f"k-{n}-a", f"k-{n}-b"]) for n, ending in enumerate(endings)]
        self.demo_before = _snapshot(handles.root / "rooms" / "demo")

    @property
    def judge_dir(self) -> Path:
        return self.handles.root / "rooms" / "judge"

    def record(self, judge: Judge) -> Path:
        return self.handles.root / "rooms" / "deleted" / f"{judge.room_id}.json"

    def assert_demo_intact(self) -> None:
        assert _snapshot(self.handles.root / "rooms" / "demo") == self.demo_before
        assert (self.handles.root / CACHE_DIR / "k-demo.json").exists()
        assert self.demo_session in DictSessionStore(self.handles.sessions).list_ids()


@pytest.fixture
def hosted(handles: ModalHandles, four_lock_room: Room, code_and_find_room: Room) -> Hosted:
    return Hosted(handles, code_and_find_room, reminted(four_lock_room), ["done", "needs_recapture", "failed"])


def run_main(monkeypatch: pytest.MonkeyPatch, handles: ModalHandles, *argv: str) -> tuple[int, list[str]]:
    """`main` with the container run replaced by `purge` over `handles`; returns the status and the Environments it ran in."""
    environments: list[str] = []

    def run_remote(environment: str, *, today: date, dry_run: bool) -> int:
        environments.append(environment)
        return purger.purge(handles, today=today, dry_run=dry_run)

    monkeypatch.setattr(purger, "run_remote", run_remote)
    return purger.main(list(argv), today=NOV_10), environments


# --- Every Judge room goes, every Demo room stays and plays -----------------------


def test_every_judge_room_goes_with_or_without_a_room_and_each_ids_only_record_is_printed(monkeypatch, handles, hosted, capsys):
    assert [judge.folder.exists() for judge in hosted.judges] == [True, True, True]
    assert [(judge.folder / "room.json").exists() for judge in hosted.judges] == [True, False, False]

    status, environments = run_main(monkeypatch, handles)

    assert status == 0 and environments == ["main"]
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Modal Environment: main"
    printed = [DeletionRecord.model_validate_json(line.removeprefix("deleted ")) for line in out if line.startswith("deleted ")]
    assert sorted(printed, key=lambda r: r.room_id) == sorted(
        (DeletionRecord(room_id=judge.room_id, job_id=judge.state.id, deleted_on=NOV_10) for judge in hosted.judges), key=lambda r: r.room_id
    )
    assert list(hosted.judge_dir.iterdir()) == []
    for judge in hosted.judges:
        assert DeletionRecord.model_validate_json(hosted.record(judge).read_bytes()) in printed
        assert not any((handles.root / CACHE_DIR / f"{key}.json").exists() for key in judge.keys)
        assert judge.state.id not in handles.jobs and call_key(judge.state.id) not in handles.jobs
    assert DictSessionStore(handles.sessions).list_ids() == [hosted.demo_session]
    hosted.assert_demo_intact()


def test_after_the_purge_the_demo_room_is_listed_served_and_played_to_completion(monkeypatch, handles, hosted):
    assert run_main(monkeypatch, handles)[0] == 0
    stores = hosted_stores(handles)
    ticker = PlayTicker()
    app = FastAPI()
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.include_router(room_routes(stores.artifacts, stores.jobs))
    app.include_router(
        session_routes(
            stores.artifacts,
            stores.jobs,
            stores.sessions,
            ticker,
            SessionClock(1),
            VerbatimPhraser(),
            lambda task: None,
            Settings.from_env({"GUIDE": "verbatim"}),
            demo=False,
            greets=False,
        )
    )
    client = TestClient(app)

    assert [row["room_id"] for row in client.get("/api/rooms").json()] == [hosted.demo.id]
    assert client.get(f"/api/rooms/{hosted.demo.id}").status_code == 200
    started = client.post("/api/sessions", json={"room_id": hosted.demo.id})
    assert started.status_code == 200, started.text
    session_id = started.json()["id"]
    for body in (click("key"), code("clock_code", "415"), click("lantern"), code("door_code", "7342")):
        ticker.advance(10_000)
        assert client.post(f"/api/sessions/{session_id}/events", json=body).status_code == 200
    result = client.get(f"/api/sessions/{session_id}/result")
    assert result.status_code == 200 and all(p["solved"] for p in result.json()["puzzles"])


# --- A failed deletion is named and the rest still go ----------------------------


def test_a_failed_deletion_is_named_the_remaining_rooms_still_go_and_the_script_exits_non_zero(monkeypatch, handles, hosted, capsys):
    first = min(hosted.judges, key=lambda judge: judge.room_id)
    real = purger.delete_judge_room

    def delete(handles: ModalHandles, room_id: str, *, today: date) -> DeletionRecord:
        if room_id == first.room_id:
            raise ConnectionError("the Volume did not answer")
        return real(handles, room_id, today=today)

    monkeypatch.setattr(purger, "delete_judge_room", delete)
    status, _ = run_main(monkeypatch, handles)

    assert status == 1
    captured = capsys.readouterr()
    assert f"failed {first.room_id}: ConnectionError" in captured.err
    assert [line for line in captured.out.splitlines() if line.startswith("deleted ")] and first.room_id not in captured.out
    assert [path.name for path in hosted.judge_dir.iterdir()] == [first.room_id]
    assert not hosted.record(first).exists()
    for judge in hosted.judges:
        if judge is not first:
            assert not judge.folder.exists() and hosted.record(judge).exists()
    hosted.assert_demo_intact()


def test_a_room_delete_judge_room_refuses_is_named_and_a_rerun_after_the_fix_completes_the_purge(monkeypatch, handles, hosted, capsys):
    refused = hosted.judges[1]
    listing = refused.folder / "cache-keys.json"
    good = listing.read_bytes()
    listing.write_bytes(b'["../rooms/demo/x"]')

    status, _ = run_main(monkeypatch, handles)
    assert status == 1
    assert f"failed {refused.room_id}: ValueError" in capsys.readouterr().err
    assert [path.name for path in hosted.judge_dir.iterdir()] == [refused.room_id]

    listing.write_bytes(good)
    assert run_main(monkeypatch, handles)[0] == 0
    assert list(hosted.judge_dir.iterdir()) == [] and hosted.record(refused).exists()
    hosted.assert_demo_intact()


# --- The dry run lists and deletes nothing ----------------------------------------


def test_the_dry_run_lists_each_room_id_and_job_id_deletes_nothing_and_writes_no_record(monkeypatch, handles, hosted, capsys):
    files_before = _snapshot(handles.root)
    jobs_before, sessions_before = dict(handles.jobs), dict(handles.sessions)

    status, _ = run_main(monkeypatch, handles, "--dry-run")

    assert status == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "Modal Environment: main"
    listed = sorted(line for line in out if line.startswith("would delete "))
    assert listed == sorted(f"would delete room_id={judge.room_id} job_id={judge.state.id}" for judge in hosted.judges)
    assert _snapshot(handles.root) == files_before and not (handles.root / "rooms" / "deleted").exists()
    assert dict(handles.jobs) == jobs_before and dict(handles.sessions) == sessions_before


# --- Nothing to purge -------------------------------------------------------------


@pytest.mark.parametrize("dry_run", [False, True])
def test_with_no_judge_room_it_says_there_is_nothing_to_purge_and_exits_0(monkeypatch, handles, code_and_find_room, capsys, dry_run):
    seed_demo(handles, code_and_find_room)
    demo_before = _snapshot(handles.root)
    status, _ = run_main(monkeypatch, handles, *(["--dry-run"] if dry_run else []))
    assert status == 0
    assert capsys.readouterr().out.splitlines() == ["Modal Environment: main", "nothing to purge: rooms/judge/ holds no Judge room"]
    assert _snapshot(handles.root) == demo_before


def test_a_second_purge_finds_nothing_left(monkeypatch, handles, hosted, capsys):
    assert run_main(monkeypatch, handles)[0] == 0
    capsys.readouterr()
    assert run_main(monkeypatch, handles)[0] == 0
    assert "nothing to purge" in capsys.readouterr().out


# --- The local tree and the git index stay as they were ---------------------------


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True, text=True).stdout


def _local(path: Path) -> dict[str, float]:
    return {p.relative_to(path).as_posix(): p.stat().st_mtime for p in path.rglob("*")} if path.exists() else {}


@pytest.mark.parametrize("argv", [[], ["--dry-run"]])
def test_the_purge_leaves_the_local_rooms_cache_and_git_index_untouched(monkeypatch, handles, hosted, argv):
    before = _local(REPO / "rooms"), _local(REPO / ".cache"), _git("diff", "--cached", "--name-only"), _git("ls-files")
    run_main(monkeypatch, handles, *argv)
    run_main(monkeypatch, handles, *argv)  # the second run of a real purge finds nothing
    assert (_local(REPO / "rooms"), _local(REPO / ".cache"), _git("diff", "--cached", "--name-only"), _git("ls-files")) == before


# --- The Modal Environment is named and printed first ------------------------------


def test_the_named_environment_is_printed_before_anything_is_listed_and_the_purge_runs_in_it(monkeypatch, handles, hosted, capsys):
    def purge(handles_: ModalHandles, *, today: date, dry_run: bool = False) -> int:
        assert capsys.readouterr().out == "Modal Environment: dev\n"
        return 0

    monkeypatch.setattr(purger, "purge", purge)
    status, environments = run_main(monkeypatch, handles, "--env", "dev")
    assert status == 0 and environments == ["dev"]


def test_every_handle_is_resolved_by_name_in_the_explicit_environment(monkeypatch):
    import modal

    calls: list[tuple[str, str, dict[str, Any]]] = []
    monkeypatch.setattr(modal.Dict, "from_name", lambda name, **kw: calls.append(("Dict", name, kw)) or name)
    monkeypatch.setattr(modal.Volume, "from_name", lambda name, **kw: calls.append(("Volume", name, kw)) or name)

    handles = purger.open_handles("dev")

    assert sorted(calls) == [
        ("Dict", "keyframe-jobs", {"environment_name": "dev"}),
        ("Dict", "keyframe-ledger", {"environment_name": "dev"}),
        ("Dict", "keyframe-sessions", {"environment_name": "dev"}),
        ("Volume", "keyframe-data", {"environment_name": "dev"}),
    ]
    assert handles.root == Path("/data")


def test_the_container_app_mounts_the_volume_from_the_named_environment_without_contacting_modal(monkeypatch):
    import modal

    volumes: list[dict[str, Any]] = []
    real = modal.Volume.from_name
    monkeypatch.setattr(modal.Volume, "from_name", lambda name, **kw: volumes.append({"name": name, **kw}) or real(name, **kw))

    app, function = purger.purge_app("dev")

    assert app.name == "keyframe-purge" and isinstance(function, modal.Function)
    assert volumes == [{"name": "keyframe-data", "environment_name": "dev"}]
    source = SCRIPT.read_text()
    assert "create_if_missing=" not in source and source.count("environment_name=environment") == 6
    assert "volumes={MOUNT.as_posix(): volume}" in source and "app.run(environment_name=environment)" in source


def test_a_printed_record_carries_ids_and_the_date_only(monkeypatch, handles, hosted, capsys):
    run_main(monkeypatch, handles)
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("deleted "):
            assert set(json.loads(line.removeprefix("deleted "))) == {"room_id", "job_id", "deleted_on"}
