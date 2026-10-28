"""`scripts/promote_room.py` copies a Judge room on the Volume to `rooms/demo/` with its name, leaving the originals, the cache keys and the Judge copy (AD-7, AD-9).

No test reaches Modal: the Volume is a stand-in over a temporary mount
whose `listdir` and `read_file` read it as the remote calls do and whose
batch lands only when its block exits, as Modal commits a batch.
"""

import importlib.util
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from modal.volume import FileEntry, FileEntryType

from src.domain.schema import JobState, Room
from src.infra.modal import ModalHandles, hosted_stores
from tests.infra.test_modal import RecordingDict, StubVolume
from tests.scripts.test_seed_rooms import (
    JOB,
    NAME,
    DirVolume,
    files_under,
    full_job,
    snapshot,
)

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/promote_room.py"


def _load():
    spec = importlib.util.spec_from_file_location("promote_room_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


promoter = _load()


# --- Doubles -------------------------------------------------------------------


class JudgeVolume(DirVolume):
    """`DirVolume` that also lists and reads the mount as `modal.Volume.listdir` and `read_file` do from outside a container."""

    def listdir(self, path: str, *, recursive: bool = False) -> list[FileEntry]:
        folder = self.mount / path.lstrip("/")
        if not folder.is_dir():
            raise FileNotFoundError(path)
        items = sorted(folder.rglob("*") if recursive else folder.iterdir())
        kind = {True: FileEntryType.FILE, False: FileEntryType.DIRECTORY}
        return [FileEntry(path=item.relative_to(self.mount).as_posix(), type=kind[item.is_file()], mtime=0, size=0) for item in items]

    def read_file(self, path: str) -> Iterator[bytes]:
        file = self.mount / path.lstrip("/")
        if not file.is_file():
            raise FileNotFoundError(path)
        yield file.read_bytes()


@pytest.fixture
def mount(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def volume(mount: Path) -> JudgeVolume:
    return JudgeVolume(mount)


@pytest.fixture
def judge(mount: Path, code_and_find_room: Room) -> Room:
    """A Judge room as a hosted Build leaves it: the Room, photos, originals, Clue cards, `cache-keys.json` and the `done` job record."""
    folder = mount / "rooms/judge" / code_and_find_room.id
    (folder / "photos").mkdir(parents=True)
    (folder / "originals").mkdir()
    (folder / "cards").mkdir()
    (folder / "room.json").write_bytes(code_and_find_room.model_dump_json().encode())
    for index, photo in enumerate(code_and_find_room.photos):
        (folder / f"photos/{index}.jpg").write_bytes(Path(photo.downscaled_path).read_bytes())
        (folder / f"originals/{index}.jpg").write_bytes(b"original %d" % index)
    for index, puzzle in enumerate(code_and_find_room.puzzles):
        (folder / f"cards/{puzzle.id}.png").write_bytes(f"card {index}".encode())
    (folder / "cards/pz_unknown.png").write_bytes(b"not this room's puzzle")
    (folder / "cache-keys.json").write_text(json.dumps(["abc.json"]))
    (folder / "job.json").write_bytes(full_job(code_and_find_room).model_dump_json().encode())
    return code_and_find_room


def run_promote(volume: JudgeVolume, room_id: str, name: str) -> Any:
    item = promoter.plan(volume, room_id, name)
    promoter.promote(volume, item)
    return item


# --- What lands under rooms/demo/ -----------------------------------------------


def test_the_room_its_photos_its_cards_its_name_and_its_job_record_land_under_rooms_demo_in_one_committed_batch(volume, mount, judge):
    run_promote(volume, judge.id, NAME)
    demo = mount / "rooms/demo" / judge.id
    assert files_under(demo) == {
        "room.json",
        "job.json",
        *(f"photos/{i}.jpg" for i in range(len(judge.photos))),
        *(f"cards/{puzzle.id}.png" for puzzle in judge.puzzles),
    }
    assert volume.forces == [True] and volume.commits == 1
    promoted = Room.model_validate_json((demo / "room.json").read_bytes())
    assert promoted.name == NAME and promoted == judge.model_copy(update={"name": NAME})
    for index, photo in enumerate(judge.photos):
        assert (demo / f"photos/{index}.jpg").read_bytes() == Path(photo.downscaled_path).read_bytes()
    for index, puzzle in enumerate(judge.puzzles):
        assert (demo / f"cards/{puzzle.id}.png").read_bytes() == f"card {index}".encode()
    assert JobState.model_validate_json((demo / "job.json").read_bytes()) == full_job(judge)


def test_the_originals_and_the_cache_keys_stay_under_rooms_judge_and_the_judge_copy_is_untouched(volume, mount, judge):
    before = snapshot(mount / "rooms/judge")
    run_promote(volume, judge.id, NAME)
    assert snapshot(mount / "rooms/judge") == before
    assert not (mount / "rooms/demo" / judge.id / "originals").exists()
    assert not (mount / "rooms/demo" / judge.id / "cache-keys.json").exists()
    assert not (mount / "rooms/demo" / judge.id / "cards/pz_unknown.png").exists()


def test_a_second_promotion_overwrites_the_earlier_files(volume, mount, judge):
    run_promote(volume, judge.id, NAME)
    run_promote(volume, judge.id, "The study, again")
    assert Room.model_validate_json((mount / "rooms/demo" / judge.id / "room.json").read_bytes()).name == "The study, again"
    assert volume.forces == [True, True]


def test_the_promoted_room_is_a_demo_room_whose_job_reads_done_through_the_hosted_stores_with_an_empty_dict(volume, mount, judge):
    run_promote(volume, judge.id, NAME)
    handles = ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume([]), root=mount)
    stores = hosted_stores(handles)
    assert stores.artifacts.is_demo_room(judge.id) and stores.artifacts.is_judge_room(judge.id)
    assert [(room.id, room.name) for room in stores.artifacts.list_rooms()] == [(judge.id, NAME)]
    job = stores.jobs.read(JOB)
    assert job.status == "done" and job.room_id == judge.id and dict(handles.jobs) == {}


# --- Refusals: before anything is written ---------------------------------------


def test_a_name_longer_than_40_characters_is_refused_before_anything_is_written(volume, mount, judge):
    with pytest.raises(promoter.SeedRefused, match="longer than 40"):
        run_promote(volume, judge.id, "x" * 41)
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


def test_a_room_whose_job_record_is_missing_is_refused(volume, mount, judge):
    (mount / "rooms/judge" / judge.id / "job.json").unlink()
    with pytest.raises(promoter.SeedRefused, match="no done job record"):
        run_promote(volume, judge.id, NAME)
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


@pytest.mark.parametrize("status", ["queued", "failed", "needs_recapture"])
def test_a_room_whose_job_record_is_not_done_is_refused(volume, mount, judge, status):
    (mount / "rooms/judge" / judge.id / "job.json").write_bytes(full_job(judge, status=status).model_dump_json().encode())
    with pytest.raises(promoter.SeedRefused, match="no done job record"):
        run_promote(volume, judge.id, NAME)
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


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
def test_a_job_record_without_what_the_build_view_reads_is_refused(volume, mount, judge, update, missing):
    (mount / "rooms/judge" / judge.id / "job.json").write_bytes(full_job(judge, **update).model_dump_json().encode())
    with pytest.raises(promoter.SeedRefused, match=missing):
        run_promote(volume, judge.id, NAME)
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


def test_a_room_with_no_photos_or_a_photo_missing_from_the_volume_is_refused(volume, mount, judge):
    (mount / "rooms/judge" / judge.id / "photos/0.jpg").unlink()
    with pytest.raises(promoter.SeedRefused, match="photo 0"):
        run_promote(volume, judge.id, NAME)
    bare = judge.model_copy(update={"photos": [], "interactables": [], "puzzles": []})
    (mount / "rooms/judge" / judge.id / "room.json").write_bytes(bare.model_dump_json().encode())
    with pytest.raises(promoter.SeedRefused, match="no photos"):
        run_promote(volume, judge.id, NAME)
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


@pytest.mark.parametrize("room_id", ["room_01JBDEM0R00M00000000000000", "../outside"])
def test_a_room_not_on_the_volume_is_refused(volume, mount, judge, room_id):
    with pytest.raises(promoter.SeedRefused, match="no Judge room"):
        run_promote(volume, room_id, NAME)
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


# --- The command line -------------------------------------------------------------


def test_main_resolves_the_volume_in_the_named_environment_and_promotes(monkeypatch, volume, mount, judge, capsys):
    environments: list[str] = []

    def open_volume(environment: str) -> JudgeVolume:
        environments.append(environment)
        return volume

    monkeypatch.setattr(promoter, "open_volume", open_volume)
    assert promoter.main(["--room", judge.id, NAME]) == 0
    assert promoter.main(["--env", "dev", "--room", judge.id, NAME]) == 0
    assert environments == ["main", "dev"]
    assert (mount / "rooms/demo" / judge.id / "job.json").exists()
    out = capsys.readouterr().out
    assert f"promoted {judge.id} {NAME!r} with {JOB}" in out and "rooms/judge" in out


def test_main_refuses_a_long_name_writing_nothing(monkeypatch, volume, mount, judge, capsys):
    monkeypatch.setattr(promoter, "open_volume", lambda environment: volume)
    assert promoter.main(["--room", judge.id, "x" * 41]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


def test_the_script_reuses_the_seed_script_and_neither_deletes_nor_opens_a_dict():
    source = SCRIPT.read_text()
    assert "from scripts.seed_rooms import" in source
    assert "remove_file" not in source and "Dict.from_name" not in source and "create_if_missing=" not in source
    assert "from_name(" not in source  # the Volume is opened through the seed script's open_volume
