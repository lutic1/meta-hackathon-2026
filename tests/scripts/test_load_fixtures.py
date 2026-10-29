"""Story 1.14: `scripts/load_fixtures.py` stores the two validated fixture rooms and their photos under `rooms/` once, and `GET /rooms` then lists both (AD-7, AD-9).

It also installs the four-lock recording under `rooms/proposals/` for `DEMO_TRICKSTER=scripted` in local play (AD-12, AD-15).
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.wiring import JOBS_DIR, artifact_store, job_store
from src.config import Settings
from src.council.trickster import load_proposals
from src.domain.redact import to_build_view
from src.domain.schema import JobState, Room
from src.domain.validator import BUILD_RULES, RULES, validate
from src.pipeline.build import STAGES
from src.pipeline.ports import ArtifactStore, JobStore, photo_key, room_key
from tests.api.test_app import make_app
from tests.api.test_sessions import Ticker, click, code, start
from tests.api.test_trickster_route import open_window, trickster
from tests.fixtures.rooms import ROOM_IDS

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/load_fixtures.py"


def _load():
    spec = importlib.util.spec_from_file_location("load_fixtures_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


loader = _load()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "rooms"


@pytest.fixture
def stores(root: Path) -> tuple[ArtifactStore, JobStore]:
    return artifact_store(root), job_store(root)


def files_under(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def test_the_loader_stores_both_validated_rooms_and_their_photos(stores, root: Path, tmp_path: Path):
    store, jobs = stores
    loaded = loader.load_fixtures(store, jobs, tmp_path / "scenes", regen_max=2)
    assert [room.id for room in loaded] == [ROOM_IDS["four_lock"], ROOM_IDS["code_and_find"]]
    for room in loaded:
        assert validate(room).reasons == []
        stored = Room.model_validate_json(store.read(room_key(room.id)))
        assert stored == room
        for index, photo in enumerate(stored.photos):
            assert photo.downscaled_path == photo_key(room.id, index) == photo.original_path
            assert len(store.read(photo.downscaled_path)) == photo.size
        assert jobs.read(loader.JOB_IDS[room.id]).room_id == room.id
        assert jobs.read(loader.JOB_IDS[room.id]).status == "done"
    assert files_under(root) == {
        *(f"{room_id}/room.json" for room_id in ROOM_IDS.values()),
        *(f"{room_id}/photos/{index}.jpg" for room_id in ROOM_IDS.values() for index in range(6)),
        *(f"{JOBS_DIR}/{job_id}.json" for job_id in loader.JOB_IDS.values()),
    }
    assert root.resolve().is_relative_to(tmp_path.resolve())


def test_each_job_record_carries_what_the_build_view_reads(stores, tmp_path: Path):
    store, jobs = stores
    for room in loader.load_fixtures(store, jobs, tmp_path / "scenes", regen_max=2):
        job = jobs.read(loader.JOB_IDS[room.id])
        view = to_build_view(room, job)
        assert (view.regeneration_count, view.regen_max) == (0, 2)
        assert [(v.rule, v.name, v.passed) for v in view.validator] == [(n, RULES[n].name, True) for n in BUILD_RULES]
        assert [(v.puzzle_id, v.verdict) for v in view.dry_run] == [(p.id, "pass") for p in room.puzzles]
        assert [record.stage for record in job.stages] == list(STAGES)
        assert view.build_time_ms == sum(room.provenance.stage_timings_ms.values())
        assert [(row.role, row.model, row.host, row.cached, row.billed) for row in view.models] == [
            (role, room.provenance.model_ids[role], "mock", 0, 1) for role in ("architect", "riddler", "dryrun")
        ]
        assert [row.summary for row in view.models] == [
            f"found {len(room.interactables)} objects",
            f"wrote {len(room.puzzles)} puzzles",
            f"tried {len(room.puzzles)} puzzles blind",
        ]
        assert all(row.spend_usd == 0.0 for row in job.calls)


def test_a_second_run_stores_no_duplicate(stores, root: Path, tmp_path: Path):
    store, jobs = stores
    first = loader.load_fixtures(store, jobs, tmp_path / "scenes-1", regen_max=2)
    before = {path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}
    assert loader.load_fixtures(store, jobs, tmp_path / "scenes-2", regen_max=2) == []
    after = {path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file()}
    assert after == before and len(first) == 2
    assert sorted(room.id for room in store.list_rooms()) == sorted(ROOM_IDS.values())


def test_a_rerun_completes_a_thin_or_missing_job_record_beside_a_stored_room(stores, root: Path, tmp_path: Path):
    store, jobs = stores
    rooms = loader.load_fixtures(store, jobs, tmp_path / "scenes-1", regen_max=2)
    thin, missing = (loader.JOB_IDS[room.id] for room in rooms)
    # the record loaders before Fix F12 wrote; the other room has lost its record
    jobs.put(JobState(id=thin, status="done", room_id=rooms[0].id, regen_max=0, build_time_ms=0))
    (root / JOBS_DIR / f"{missing}.json").unlink()
    rooms_before = {path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file() and JOBS_DIR not in path.parts}
    assert loader.load_fixtures(store, jobs, tmp_path / "scenes-2", regen_max=2) == []
    for room in rooms:
        view = to_build_view(room, jobs.read(loader.JOB_IDS[room.id]))
        assert view.regen_max == 2
        assert len(view.validator) == len(BUILD_RULES) == 8
        assert [row.role for row in view.models] == ["architect", "riddler", "dryrun"]
    assert {path: path.stat().st_mtime_ns for path in root.rglob("*") if path.is_file() and JOBS_DIR not in path.parts} == rooms_before


def test_a_room_that_fails_validation_is_not_stored(stores, tmp_path: Path, monkeypatch):
    store, jobs = stores
    broken = [room.model_copy(update={"puzzles": [p.model_copy(update={"is_exit": False}) for p in room.puzzles]})
              for room in loader.write_fixtures(tmp_path / "scenes")]
    monkeypatch.setattr(loader, "write_fixtures", lambda out_dir: tuple(broken))
    with pytest.raises(ValueError, match="fails validation"):
        loader.load_fixtures(store, jobs, tmp_path / "scenes", regen_max=2)
    assert store.list_rooms() == [] and jobs.list_ids() == []


def test_get_rooms_lists_both_after_the_loader_runs(stores, root: Path, tmp_path: Path):
    store, jobs = stores
    loader.load_fixtures(store, jobs, tmp_path / "scenes", regen_max=2)
    client = TestClient(create_app(Settings.from_env(), rooms_root=root, web_dist=tmp_path / "no-dist"))
    response = client.get("/api/rooms")
    assert response.status_code == 200
    # both fixture rooms share one build time, so their relative order is not asserted
    assert sorted((row["room_id"], row["job_id"], row["puzzle_count"]) for row in response.json()) == [
        (ROOM_IDS["four_lock"], loader.JOB_IDS[ROOM_IDS["four_lock"]], 5),
        (ROOM_IDS["code_and_find"], loader.JOB_IDS[ROOM_IDS["code_and_find"]], 4),
    ]
    for row in response.json():
        assert client.get(f"/api/rooms/{row['room_id']}").status_code == 200
        assert client.get(f"/api/rooms/{row['room_id']}/photos/{row['cover_photo']}").headers["content-type"] == "image/jpeg"


def test_the_script_runs_from_any_directory_and_reports_the_second_run(root: Path, tmp_path: Path):
    first = subprocess.run([sys.executable, str(SCRIPT), str(root)], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert first.returncode == 0, first.stderr
    assert first.stdout.count("stored room_") == 2
    second = subprocess.run([sys.executable, str(SCRIPT), str(root)], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert second.returncode == 0 and "already stored" in second.stdout
    assert len(list(root.rglob("room.json"))) == 2
    env_line = f"DEMO_TRICKSTER=scripted DEMO_PROPOSALS_DIR={root / loader.PROPOSALS_DIR}"
    assert env_line in first.stdout and env_line in second.stdout


# --- The four-lock proposals for scripted local play (AD-12, AD-15) ------------------------------


def test_the_loader_installs_the_four_lock_recording_beside_the_rooms_for_the_stored_fixture_room(stores, root: Path, tmp_path: Path):
    loader.load_fixtures(*stores, tmp_path / "scenes", regen_max=2)
    installed = loader.install_proposals(root, stores[0])
    assert installed == root / "proposals" / "recorded.json"
    recording = load_proposals(installed)
    assert recording == load_proposals(loader.FIXTURE_PROPOSALS) and recording.room_id == ROOM_IDS["four_lock"]
    assert not list(root.glob("proposals/**/room.json"))  # never a room the store would list


def test_the_recording_is_not_installed_before_its_room_is_stored(stores, root: Path):
    with pytest.raises(ValueError, match=ROOM_IDS["four_lock"]):
        loader.install_proposals(root, stores[0])
    assert not (root / "proposals").exists()


def test_a_scripted_session_over_the_installed_recording_gets_a_card_in_each_window(stores, root: Path, tmp_path: Path):
    """Local play with `DEMO_TRICKSTER=scripted` and the printed env line: a card in each window.

    Under the default chest hint policy (story mode) window 0's Decoy is refused, since evidence is hidden until a lock
    opens, and window 1's Merge fails rule 1.
    """
    loader.load_fixtures(*stores, tmp_path / "scenes", regen_max=2)
    loader.install_proposals(root, stores[0])
    settings = Settings.from_env({"DEMO_TRICKSTER": "scripted", "DEMO_PROPOSALS_DIR": str(root / loader.PROPOSALS_DIR)})
    ticker = Ticker()
    client = TestClient(make_app(tmp_path, settings=settings, clock=ticker))
    room = Room.model_validate_json(stores[0].read(room_key(ROOM_IDS["four_lock"])))
    session_id = start(client, room)
    open_window(client, ticker, session_id, click("key"), 0)
    first = trickster(client, session_id)
    open_window(client, ticker, session_id, code("clock_code", "415"), 1)
    second = trickster(client, session_id)
    assert [(card["accepted"], card["edit_type"], card["message"]) for card in first["cards"]] == [
        (False, "decoy", "Evidence is hidden until a lock opens.")
    ]
    assert [(card["accepted"], card["edit_type"], card["reason"]) for card in second["cards"]] == [
        (False, "decoy", "edit_bounds"), (False, "merge", 1)
    ]
