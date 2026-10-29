"""Story 7.13: `scripts/seed_rooms.py` writes each Demo room, its photos, its name and its final job record under `rooms/demo/` on the Volume (AD-7, AD-9).

No test reaches Modal: the Volume is a stand-in whose batch lands under a
temporary mount only when the block exits, as Modal commits a batch, and
the hosted side reads that mount through the real hosted stores over plain
dicts.
"""

import importlib.util
import json
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, get_args

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from src.api.app import room_routes, session_routes
from src.api.errors import ApiError, handle_api_error, handle_validation_error
from src.api.wiring import artifact_store, job_store
from src.config import Settings
from src.domain.schema import (
    CallRow,
    DryRunVerdict,
    JobState,
    Placement,
    Room,
    RuleVerdict,
    Stage,
    StageRecord,
    Tier2,
)
from src.infra.clocks import SessionClock
from src.infra.modal import HostedStores, ModalHandles, hosted_stores
from src.pipeline.ports import photo_key
from src.providers.verbatim import VerbatimPhraser
from tests.api.test_app import store_room
from tests.api.test_sessions import Ticker, click, code
from tests.infra.test_modal import RecordingDict, StubVolume

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/seed_rooms.py"
JOB = "job_01JBDEM0R00M000000000000J1"
OTHER_JOB = "job_01JBDEM0R00M000000000000J2"
CALL = "call_01JBDEM0R00M000000000000C1"
NAME = "The study"


def _load():
    spec = importlib.util.spec_from_file_location("seed_rooms_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # the script's dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


seeder = _load()


# --- Doubles -------------------------------------------------------------------


class DirVolume:
    """`modal.Volume` as the script sees it from outside a container: a batch lands under `mount` only when its block exits."""

    def __init__(self, mount: Path) -> None:
        self.mount = mount
        self.forces: list[bool] = []
        self.commits = 0

    @contextmanager
    def batch_upload(self, force: bool = False) -> Iterator[Any]:
        self.forces.append(force)
        pending: dict[str, bytes] = {}

        class Batch:
            def put_file(self, local_file: BinaryIO, remote_path: str) -> None:
                assert remote_path.startswith("/") and remote_path not in pending
                pending[remote_path] = local_file.read()

        yield Batch()
        for remote, data in pending.items():
            path = self.mount / remote.lstrip("/")
            if path.exists() and not force:
                raise FileExistsError(remote)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.commits += 1


def full_job(room: Room, job_id: str = JOB, **update: Any) -> JobState:
    """A `done` record holding everything the Build view reads."""
    job = JobState(
        id=job_id,
        status="done",
        room_id=room.id,
        stages=[StageRecord(stage=stage, duration_ms=1_000 * (i + 1)) for i, stage in enumerate(get_args(Stage))],
        regen_max=2,
        validator=[RuleVerdict(rule=1, name="every puzzle is reachable", passed=True)],
        dry_run=[DryRunVerdict(puzzle_id=puzzle.id, verdict="pass") for puzzle in room.puzzles],
        calls=[CallRow(id=CALL, role="riddler", model="muse-spark-1.3", host="meta", cached=False, spend_usd=0.01)],
        build_time_ms=28_000,
    )
    return job.model_copy(update=update)


def demo_copy(room: Room, name: str = NAME) -> Room:
    """The Room as its Demo copy stores it: named, each photo's paths naming the downscaled file the copy holds (decision 9)."""
    photos = [photo.model_copy(update={"downscaled_path": photo_key(room.id, i), "original_path": photo_key(room.id, i)}) for i, photo in enumerate(room.photos)]
    return room.model_copy(update={"name": name, "photos": photos})


def with_glb(room: Room) -> Room:
    """The Room with a Tier 2 model on its first interactable, a file no seed carries."""
    tier2 = Tier2(glb_path=f"{room.id}/tier2/0.glb", placement=Placement(translation=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)))
    first = room.interactables[0].model_copy(update={"tier2": tier2})
    return room.model_copy(update={"interactables": [first, *room.interactables[1:]]})


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "rooms"


@pytest.fixture
def mount(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def volume(mount: Path) -> DirVolume:
    return DirVolume(mount)


@pytest.fixture
def built(root: Path, code_and_find_room: Room) -> Room:
    """A Demo room built locally: the Room, its photos, an original and its `done` job record under `rooms/`."""
    store_room(artifact_store(root), code_and_find_room)
    (root / code_and_find_room.id / "originals").mkdir(parents=True)
    (root / code_and_find_room.id / "originals/0.jpg").write_bytes(b"original")
    job_store(root).put(full_job(code_and_find_room))
    return code_and_find_room


@pytest.fixture
def hosted(mount: Path) -> tuple[ModalHandles, HostedStores]:
    handles = ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume([]), root=mount)
    return handles, hosted_stores(handles, poll=_never_polled)


def _never_polled(call_id: str) -> Any:
    raise AssertionError("a seeded job is done, so the watchdog never polls")


def files_under(path: Path) -> set[str]:
    return {p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()} if path.exists() else set()


def snapshot(path: Path) -> dict[str, tuple[bytes, int]]:
    return {p.relative_to(path).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns) for p in path.rglob("*") if p.is_file()}


def run_seed(root: Path, volume: DirVolume, *demo: tuple[str, str]) -> list[Any]:
    seeds = seeder.plan(root, [seeder.DemoRoom(room_id, name) for room_id, name in demo])
    seeder.seed(volume, seeds)
    return seeds


# --- What lands on the Volume ---------------------------------------------------


def test_the_room_its_photos_its_name_and_its_job_record_land_under_rooms_demo_in_one_committed_batch(root, volume, mount, built):
    run_seed(root, volume, (built.id, NAME))
    demo = f"rooms/demo/{built.id}"
    assert files_under(mount) == {f"{demo}/room.json", f"{demo}/job.json", *(f"{demo}/photos/{i}.jpg" for i in range(len(built.photos)))}
    assert volume.forces == [True] and volume.commits == 1
    seeded = Room.model_validate_json((mount / demo / "room.json").read_bytes())
    assert seeded.name == NAME and seeded == demo_copy(built)
    for index in range(len(built.photos)):
        assert (mount / demo / f"photos/{index}.jpg").read_bytes() == artifact_store(root).read(photo_key(built.id, index))
    assert JobState.model_validate_json((mount / demo / "job.json").read_bytes()) == full_job(built)


def test_every_asset_the_seeded_room_references_is_a_file_in_its_demo_folder_and_no_original_is_copied(root, volume, mount, built):
    run_seed(root, volume, (built.id, NAME))
    seeded = Room.model_validate_json((mount / f"rooms/demo/{built.id}/room.json").read_bytes())
    for index, photo in enumerate(seeded.photos):
        assert photo.original_path == photo.downscaled_path == photo_key(built.id, index)
        assert (mount / "rooms/demo" / photo.original_path).read_bytes() == artifact_store(root).read(photo_key(built.id, index))
    assert not (mount / f"rooms/demo/{built.id}/originals").exists()


def test_a_room_referencing_an_asset_the_seed_does_not_carry_is_refused_before_anything_is_written(root, volume, mount, built):
    artifact_store(root).put(f"{built.id}/room.json", with_glb(built).model_dump_json().encode())
    with pytest.raises(seeder.SeedRefused, match="tier2/0.glb"):
        run_seed(root, volume, (built.id, NAME))
    assert volume.forces == [] and not mount.exists()


def test_a_photo_missing_from_the_local_store_is_refused_before_anything_is_written(root, volume, mount, built):
    (root / photo_key(built.id, 1)).unlink()
    with pytest.raises(seeder.SeedRefused, match="photo 1"):
        run_seed(root, volume, (built.id, NAME))
    assert volume.forces == [] and not mount.exists()


def test_a_reseed_overwrites_the_earlier_files(root, volume, mount, built):
    run_seed(root, volume, (built.id, NAME))
    run_seed(root, volume, (built.id, "The study, again"))
    assert Room.model_validate_json((mount / f"rooms/demo/{built.id}/room.json").read_bytes()).name == "The study, again"
    assert volume.forces == [True, True]


def test_clue_cards_keyed_by_puzzle_id_are_seeded_under_the_same_keys(root, volume, mount, built):
    cards = {f"{built.id}/cards/{puzzle.id}.png": f"card {i}".encode() for i, puzzle in enumerate(built.puzzles)}
    for key, data in cards.items():
        (root / key).parent.mkdir(parents=True, exist_ok=True)
        (root / key).write_bytes(data)
    (root / built.id / "cards/pz_unknown.png").write_bytes(b"not this room's puzzle")
    run_seed(root, volume, (built.id, NAME))
    for key, data in cards.items():
        assert (mount / "rooms/demo" / key).read_bytes() == data
    assert not (mount / f"rooms/demo/{built.id}/cards/pz_unknown.png").exists()
    assert not (mount / f"rooms/demo/{built.id}/originals").exists()


def test_two_demo_rooms_are_seeded_in_the_one_batch(root, volume, mount, built, four_lock_room):
    store_room(artifact_store(root), four_lock_room)
    job_store(root).put(full_job(four_lock_room, OTHER_JOB))
    run_seed(root, volume, (built.id, NAME), (four_lock_room.id, "The workshop"))
    assert volume.commits == 1
    assert JobState.model_validate_json((mount / f"rooms/demo/{four_lock_room.id}/job.json").read_bytes()).id == OTHER_JOB


# --- Refusals: before anything is written ---------------------------------------


def test_a_name_of_40_characters_is_seeded(root, volume, mount, built):
    run_seed(root, volume, (built.id, "x" * 40))
    assert Room.model_validate_json((mount / f"rooms/demo/{built.id}/room.json").read_bytes()).name == "x" * 40


def test_a_name_longer_than_40_characters_is_refused_before_anything_is_written(root, volume, mount, built, four_lock_room):
    store_room(artifact_store(root), four_lock_room)
    job_store(root).put(full_job(four_lock_room, OTHER_JOB))
    with pytest.raises(seeder.SeedRefused, match="longer than 40"):
        run_seed(root, volume, (four_lock_room.id, "The workshop"), (built.id, "x" * 41))
    assert volume.forces == [] and not mount.exists()


@pytest.mark.parametrize(
    ("update", "missing"),
    [
        ({"stages": []}, "stage timings"),
        ({"calls": []}, "call rows"),
        ({"validator": []}, "validator verdicts"),
        ({"dry_run": []}, "Dry run verdicts"),
        ({"build_time_ms": None}, "build time"),
    ],
)
def test_a_job_record_without_what_the_build_view_reads_is_refused(root, volume, mount, built, update, missing):
    job_store(root).put(full_job(built, **update))
    with pytest.raises(seeder.SeedRefused, match=missing):
        run_seed(root, volume, (built.id, NAME))
    assert volume.forces == [] and not mount.exists()


@pytest.mark.parametrize("status", ["queued", "failed", "needs_recapture"])
def test_a_room_with_no_done_job_record_is_refused(root, volume, mount, built, status):
    job_store(root).put(full_job(built, status=status))
    with pytest.raises(seeder.SeedRefused, match="no done job record"):
        run_seed(root, volume, (built.id, NAME))
    assert not mount.exists()


@pytest.mark.parametrize("room_id", ["room_01JBDEM0R00M00000000000000", "../outside"])
def test_a_room_not_stored_locally_is_refused(root, volume, mount, built, room_id):
    with pytest.raises(seeder.SeedRefused, match="no Room is stored"):
        run_seed(root, volume, (room_id, NAME))
    assert not mount.exists()


def test_no_room_or_a_room_named_twice_is_refused(root, volume, built):
    with pytest.raises(seeder.SeedRefused, match="at least one"):
        run_seed(root, volume)
    with pytest.raises(seeder.SeedRefused, match="twice"):
        run_seed(root, volume, (built.id, NAME), (built.id, "Again"))
    assert volume.forces == []


# --- The hosted side reads the seeded Volume ------------------------------------


def test_the_seeded_job_record_reads_done_through_the_hosted_job_store_with_an_empty_dict(root, volume, built, hosted):
    run_seed(root, volume, (built.id, NAME))
    handles, stores = hosted
    job = stores.jobs.read(JOB)
    assert job.status == "done" and job.room_id == built.id
    assert job.stages == full_job(built).stages and job.calls == full_job(built).calls
    assert job.validator and job.dry_run and job.build_time_ms == 28_000
    assert stores.jobs.list_ids() == [JOB]
    assert dict(handles.jobs) == {}


def test_a_seeded_demo_room_is_listed_served_and_played_to_completion_with_no_ledger_entry(root, volume, built, hosted):
    run_seed(root, volume, (built.id, NAME))
    handles, stores = hosted
    app = FastAPI()
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    ticker = Ticker()
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

    listed = client.get("/api/rooms").json()
    assert [(row["room_id"], row["name"], row["job_id"]) for row in listed] == [(built.id, NAME, JOB)]
    view = client.get(f"/api/rooms/{built.id}")
    assert view.status_code == 200 and view.json()["name"] == NAME and "solution" not in view.text
    for index in range(len(built.photos)):
        photo = client.get(f"/api/rooms/{built.id}/photos/{index}")
        assert photo.status_code == 200 and photo.content == artifact_store(root).read(photo_key(built.id, index))

    started = client.post("/api/sessions", json={"room_id": built.id})
    assert started.status_code == 200, started.text
    session_id = started.json()["id"]
    for body in (click("key"), code("clock_code", "415"), click("lantern"), code("door_code", "7342")):
        ticker.advance(10_000)
        assert client.post(f"/api/sessions/{session_id}/events", json=body).status_code == 200
    result = client.get(f"/api/sessions/{session_id}/result")
    assert result.status_code == 200 and all(p["solved"] for p in result.json()["puzzles"])
    assert dict(handles.ledger) == {} and handles.ledger.writes == []


# --- The local tree and the git index stay as they were ------------------------


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True, text=True).stdout


def test_seeding_changes_nothing_under_rooms_or_cache_and_adds_nothing_to_the_git_index(root, volume, built, tmp_path):
    cache = tmp_path / ".cache"
    cache.mkdir()
    (cache / "abc.json").write_text(json.dumps({"cached": True}))
    (root / built.id / "cards").mkdir()
    (root / built.id / f"cards/{built.puzzles[0].id}.png").write_bytes(b"card")
    before = snapshot(root), snapshot(cache), _git("diff", "--cached", "--name-only"), _git("ls-files")
    run_seed(root, volume, (built.id, NAME))
    assert (snapshot(root), snapshot(cache), _git("diff", "--cached", "--name-only"), _git("ls-files")) == before


# --- The command line -------------------------------------------------------------


def test_main_resolves_the_volume_in_the_named_environment_and_seeds(monkeypatch, root, volume, mount, built, capsys):
    environments: list[str] = []

    def open_volume(environment: str) -> DirVolume:
        environments.append(environment)
        return volume

    monkeypatch.setattr(seeder, "open_volume", open_volume)
    assert seeder.main(["--rooms", str(root), "--room", built.id, NAME]) == 0
    assert seeder.main(["--rooms", str(root), "--env", "dev", "--room", built.id, NAME]) == 0
    assert environments == ["main", "dev"]
    assert (mount / f"rooms/demo/{built.id}/job.json").exists()
    assert f"seeded {built.id}" in capsys.readouterr().out


def test_main_refuses_a_long_name_without_opening_the_volume(monkeypatch, root, built, capsys):
    def open_volume(environment: str) -> DirVolume:
        raise AssertionError("a refused run never opens the Volume")

    monkeypatch.setattr(seeder, "open_volume", open_volume)
    assert seeder.main(["--rooms", str(root), "--room", built.id, "x" * 41]) == 1
    assert "nothing written" in capsys.readouterr().err


def test_the_script_opens_only_the_volume_by_name_in_an_explicit_environment():
    source = SCRIPT.read_text()
    assert "modal.Volume.from_name(VOLUME, environment_name=environment)" in source
    assert "Dict.from_name" not in source and "create_if_missing=" not in source
