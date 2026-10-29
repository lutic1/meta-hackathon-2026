"""`scripts/promote_room.py` moves a Judge room on the Volume to `rooms/demo/` with its name: the Demo copy goes up, reads back, then the Judge copy goes (AD-7, AD-9).

No test reaches Modal: the Volume is a stand-in over a temporary mount
whose `listdir`, `read_file` and `remove_file` act on it as the remote calls
do and whose batch lands only when its block exits, as Modal commits a batch.
"""

import importlib.util
import json
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from modal.volume import FileEntry, FileEntryType

from src.domain.schema import JobState, Room
from src.infra.modal import ModalHandles, hosted_stores, slot_key
from tests.infra.test_modal import RecordingDict, StubVolume
from tests.scripts.test_seed_rooms import (
    JOB,
    NAME,
    DirVolume,
    demo_copy,
    files_under,
    full_job,
    snapshot,
    with_glb,
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

    def remove_file(self, path: str, recursive: bool = False) -> None:
        target = self.mount / path.lstrip("/")
        self.removed.append(path)
        if target.is_dir():
            assert recursive, path
            shutil.rmtree(target)
        else:
            target.unlink()


class DroppingVolume(JudgeVolume):
    """A Volume whose batch loses photo 0, so the Demo copy never reads back whole."""

    @contextmanager
    def batch_upload(self, force: bool = False) -> Iterator[Any]:
        with super().batch_upload(force) as batch:
            put = batch.put_file
            batch.put_file = lambda local, remote: None if remote.endswith("/photos/0.jpg") else put(local, remote)
            yield batch


@pytest.fixture
def mount(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def volume(mount: Path) -> JudgeVolume:
    volume = JudgeVolume(mount)
    volume.removed = []
    return volume


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
    assert promoted.name == NAME and promoted == demo_copy(judge)
    for index, photo in enumerate(judge.photos):
        assert (demo / f"photos/{index}.jpg").read_bytes() == Path(photo.downscaled_path).read_bytes()
    for index, puzzle in enumerate(judge.puzzles):
        assert (demo / f"cards/{puzzle.id}.png").read_bytes() == f"card {index}".encode()
    assert JobState.model_validate_json((demo / "job.json").read_bytes()) == full_job(judge)


def test_every_asset_the_promoted_room_references_is_a_file_in_its_demo_folder(volume, mount, judge):
    run_promote(volume, judge.id, NAME)
    promoted = Room.model_validate_json((mount / "rooms/demo" / judge.id / "room.json").read_bytes())
    for index, photo in enumerate(promoted.photos):
        assert photo.original_path == photo.downscaled_path == f"{judge.id}/photos/{index}.jpg"
        assert (mount / "rooms/demo" / photo.original_path).read_bytes() == Path(judge.photos[index].downscaled_path).read_bytes()
    assert not (mount / "rooms/demo" / judge.id / "originals").exists()


def test_a_room_referencing_an_asset_the_promotion_does_not_carry_is_refused_before_anything_is_written(volume, mount, judge):
    (mount / "rooms/judge" / judge.id / "room.json").write_bytes(with_glb(judge).model_dump_json().encode())
    with pytest.raises(promoter.SeedRefused, match="tier2/0.glb"):
        run_promote(volume, judge.id, NAME)
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


def test_the_judge_copy_with_its_originals_and_cache_keys_is_removed_once_the_demo_copy_reads_back(volume, mount, judge):
    run_promote(volume, judge.id, NAME)
    assert volume.removed == [f"/rooms/judge/{judge.id}"] and not (mount / "rooms/judge" / judge.id).exists()
    assert not (mount / "rooms/demo" / judge.id / "originals").exists()
    assert not (mount / "rooms/demo" / judge.id / "cache-keys.json").exists()
    assert not (mount / "rooms/demo" / judge.id / "cards/pz_unknown.png").exists()
    assert not (mount / "rooms/deleted").exists()  # a promotion is no deletion: no record is written


def test_a_demo_copy_that_does_not_read_back_keeps_the_judge_copy(mount, judge):
    volume = DroppingVolume(mount)
    volume.removed = []
    before = snapshot(mount / "rooms/judge")
    with pytest.raises(promoter.SeedRefused, match="does not read back"):
        run_promote(volume, judge.id, NAME)
    assert volume.removed == [] and snapshot(mount / "rooms/judge") == before


def test_an_earlier_promotion_that_left_its_judge_copy_is_finished_without_copying_again(volume, mount, judge):
    promoter.seed(volume, [promoter.plan(volume, judge.id, NAME)])  # an older promotion: the copy only
    demo_before = snapshot(mount / "rooms/demo")
    run_promote(volume, judge.id, NAME)
    assert volume.forces == [True] and snapshot(mount / "rooms/demo") == demo_before
    assert not (mount / "rooms/judge" / judge.id).exists() and not (mount / "rooms/deleted").exists()


def test_an_earlier_demo_copy_that_differs_is_overwritten_before_the_judge_copy_goes(volume, mount, judge):
    promoter.seed(volume, [promoter.plan(volume, judge.id, "An older name")])
    run_promote(volume, judge.id, NAME)
    assert volume.forces == [True, True] and not (mount / "rooms/judge" / judge.id).exists()
    assert Room.model_validate_json((mount / "rooms/demo" / judge.id / "room.json").read_bytes()).name == NAME


def test_a_second_run_reports_already_promoted_writes_nothing_and_exits_0(monkeypatch, volume, mount, judge, capsys):
    monkeypatch.setattr(promoter, "open_volume", lambda environment: volume)
    assert promoter.main(["--room", judge.id, NAME]) == 0
    capsys.readouterr()
    demo_before = snapshot(mount / "rooms/demo")
    assert promoter.main(["--room", judge.id, NAME]) == 0
    assert "already promoted" in capsys.readouterr().out
    assert volume.forces == [True] and volume.removed == [f"/rooms/judge/{judge.id}"]
    assert snapshot(mount / "rooms/demo") == demo_before


def test_the_promotion_leaves_the_claimed_quota_slot_and_writes_no_deletion_record(volume, mount, judge):
    handles = ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume([]), root=mount)
    handles.jobs[slot_key(1)] = JOB
    run_promote(volume, judge.id, NAME)
    stores = hosted_stores(handles)
    assert handles.jobs[slot_key(1)] == JOB and stores.artifacts.deleted_room(judge.id) is None
    assert stores.artifacts.deleted_room(JOB) is None


def test_the_promoted_room_is_a_demo_room_whose_job_reads_done_through_the_hosted_stores_with_an_empty_dict(volume, mount, judge):
    run_promote(volume, judge.id, NAME)
    handles = ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume([]), root=mount)
    stores = hosted_stores(handles)
    assert stores.artifacts.is_demo_room(judge.id) and not stores.artifacts.is_judge_room(judge.id)
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
    out = capsys.readouterr().out
    assert f"promoted {judge.id} {NAME!r} with {JOB}" in out and f"removed the Judge copy under /rooms/judge/{judge.id}/" in out
    assert promoter.main(["--env", "dev", "--room", judge.id, NAME]) == 0
    assert environments == ["main", "dev"]
    assert (mount / "rooms/demo" / judge.id / "job.json").exists()
    assert "already promoted" in capsys.readouterr().out


def test_main_refuses_a_long_name_writing_nothing(monkeypatch, volume, mount, judge, capsys):
    monkeypatch.setattr(promoter, "open_volume", lambda environment: volume)
    assert promoter.main(["--room", judge.id, "x" * 41]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert volume.forces == [] and not (mount / "rooms/demo").exists()


def test_the_script_reuses_the_seed_script_removes_the_judge_copy_only_and_never_opens_a_dict():
    source = SCRIPT.read_text()
    assert "from scripts.seed_rooms import" in source
    assert source.count("volume.remove_file(") == 1 and 'volume.remove_file(f"{JUDGE_PREFIX}/{item.room.id}", recursive=True)' in source
    assert "Dict.from_name" not in source and "create_if_missing=" not in source
    assert "from_name(" not in source  # the Volume is opened through the seed script's open_volume
