"""Story 7.14: hosted room partitions, Demo rooms under `rooms/demo/` listed and Judge rooms under `rooms/judge/` kept apart (AD-8, AD-9, FR-31, FR-33).

No test reaches Modal: the Dicts are plain dicts, the Volume is a temporary
directory behind a stub that logs `commit` and `reload`, and a Judge build
runs the real `Build` over the hosted stores with a stage double per stage.
A Demo room is landed on the directory as `scripts/seed_rooms.py` lands it.
"""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import room_routes
from src.api.errors import ApiError, handle_api_error
from src.api.wiring import artifact_store, job_store
from src.domain.redact import to_play_view
from src.domain.schema import JobState, Room, RoomSummary
from src.infra.clocks import BuildClock
from src.infra import modal as hosted
from src.infra.local import DiskArtifactStore
from src.infra.modal import (
    CACHE_DIR,
    CACHE_KEYS_FILE,
    JOB_FILE,
    CacheKeyLog,
    HostedStores,
    ModalHandles,
    VolumeArtifactStore,
    hosted_stores,
    run_judge_build,
)
from src.pipeline.build import Build, StageStop
from src.pipeline.ports import ROOM_FILE, photo_key, room_key
from src.providers.base import ChatResponse
from src.providers.cache import GuardedCalls
from src.providers.spend import SpendLedger
from tests.api.test_app import store_room
from tests.infra.test_clocks import Ticker
from tests.infra.test_local import JOB_A, JOB_B
from tests.infra.test_modal import RecordingDict, StubVolume, seed_demo
from tests.pipeline.test_build import Doubles, RunnerDied
from tests.pipeline.uploads import make_uploads

REPO = Path(__file__).resolve().parents[2]

# --- Doubles -------------------------------------------------------------------


class Recapture(StageStop):
    status = "needs_recapture"


class TooFew(StageStop):
    status = "needs_more_photos"


@pytest.fixture
def log() -> list[str]:
    return []


@pytest.fixture
def handles(tmp_path: Path, log: list[str]) -> ModalHandles:
    return ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume(log), root=tmp_path / "data")


@pytest.fixture
def stores(handles: ModalHandles) -> HostedStores:
    return hosted_stores(handles)


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


def _demo_job(job_id: str, room: Room) -> JobState:
    return JobState(id=job_id, status="done", room_id=room.id, regen_max=2, build_time_ms=28_000)


def _client(stores: HostedStores) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(ApiError, handle_api_error)
    app.include_router(room_routes(stores.artifacts, stores.jobs))
    return TestClient(app)


def _chat(calls: GuardedCalls, key: str) -> None:
    """One guarded chat call under `key`: served from the Cache on a hit, priced and stored on a miss."""
    calls.chat(key, "vision", model="muse-spark-1.3", call=lambda: (ChatResponse(text=key, model="muse-spark-1.3"), 0.01))


class JudgeBuild:
    """A hosted Judge build as the stage runner runs it: `Build` over the hosted stores, the providers' Cache behind a `CacheKeyLog`."""

    def __init__(self, handles: ModalHandles, ticker: Ticker, room: Room) -> None:
        self.handles = handles
        self.ticker = ticker
        self.stores = hosted_stores(handles)
        self.uploads = make_uploads(6)
        self.room = room
        self.queued = self._build(Doubles(ticker)).submit(self.uploads)
        self.room_id = self.queued.room_id or ""

    def _build(self, doubles: Doubles) -> Build:
        return Build(jobs=self.stores.jobs, artifacts=self.stores.artifacts, clock=BuildClock(monotonic_ns=self.ticker), stages=doubles.stages(), regen_max=2)

    def run(self, *, chats: dict[str, list[str]] | None = None, raises: dict[str, BaseException] | None = None) -> JobState:
        """One runner over the job: the stages named in `chats` make those guarded calls; scene stores the Room."""
        doubles = Doubles(self.ticker)
        keys = CacheKeyLog(self.stores.cache)
        calls = GuardedCalls(keys, SpendLedger(self.stores.ledger, cap_usd=10), host="api.meta.ai")
        for stage, stage_keys in (chats or {}).items():
            doubles.hooks[stage] = _calling(calls, stage_keys)
        doubles.hooks["scene"] = lambda state: self.stores.artifacts.put(room_key(self.room_id), self.stored_room.model_dump_json().encode())
        doubles.raises.update(raises or {})
        return run_judge_build(self._build(doubles).run, self.queued.id, stores=self.stores, keys=keys)

    @property
    def stored_room(self) -> Room:
        return self.room.model_copy(update={"id": self.room_id})

    def listed_keys(self) -> list[str]:
        return json.loads((self.handles.root / "rooms" / "judge" / self.room_id / CACHE_KEYS_FILE).read_bytes())


def _calling(calls: GuardedCalls, keys: list[str]) -> Callable[[JobState], None]:
    def hook(_: JobState) -> None:
        for key in keys:
            _chat(calls, key)

    return hook


def _files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


# --- GET /rooms: a summary for each Demo room, none for a Judge room --------------------


def test_list_rooms_returns_a_summary_for_each_demo_room_and_none_for_any_judge_room(handles, stores, ticker, four_lock_room, code_and_find_room):
    named = code_and_find_room.model_copy(update={"name": "The study"})
    older = four_lock_room.model_copy(update={"created": four_lock_room.created.replace(year=2025)})
    seed_demo(handles, named, _demo_job(JOB_A, named))
    seed_demo(handles, older, _demo_job(JOB_B, older))
    judge = JudgeBuild(handles, ticker, four_lock_room)
    assert judge.run().status == "done"
    assert (handles.root / "rooms" / "judge" / judge.room_id / ROOM_FILE).exists()

    assert [room.id for room in stores.artifacts.list_rooms()] == [named.id, older.id]
    listed = _client(stores).get("/api/rooms")
    assert listed.status_code == 200
    assert [RoomSummary.model_validate(row) for row in listed.json()] == [
        RoomSummary(room_id=named.id, name="The study", cover_photo=0, puzzle_count=len(named.puzzles), job_id=JOB_A, built_at=named.created),
        RoomSummary(room_id=older.id, name=None, cover_photo=0, puzzle_count=len(older.puzzles), job_id=JOB_B, built_at=older.created),
    ]
    assert judge.room_id not in listed.text and judge.queued.id not in listed.text


# --- Every path a Judge build writes is under rooms/judge/<room_id>/ ---------------------


ENDINGS: dict[str, tuple[dict[str, BaseException], str | None]] = {
    "done": ({}, "done"),
    "failed": ({"segment": RuntimeError("the segment host went away")}, "failed"),
    "needs_more_photos": ({"segment": TooFew("only 3 interactables survived")}, "needs_more_photos"),
    "needs_recapture": ({"dryrun": Recapture("the room cannot be played as built")}, "needs_recapture"),
    "runner died": ({"author": RunnerDied()}, None),
}


@pytest.mark.parametrize("ending", list(ENDINGS))
def test_every_path_a_judge_build_writes_is_under_its_judge_folder_whatever_its_end_status(handles, stores, ticker, four_lock_room, code_and_find_room, ending):
    seed_demo(handles, code_and_find_room, _demo_job(JOB_A, code_and_find_room))
    demo_before = _snapshot(handles.root / "rooms" / "demo")
    judge = JudgeBuild(handles, ticker, four_lock_room)
    raises, status = ENDINGS[ending]
    if status is None:
        with pytest.raises(RunnerDied):
            judge.run(chats={"architect": ["k-arch"]}, raises=raises)
    else:
        assert judge.run(chats={"architect": ["k-arch"]}, raises=raises).status == status

    folder = f"rooms/judge/{judge.room_id}"
    written = _files(handles.root) - {f"rooms/demo/{key}" for key in demo_before}
    expected = {
        *(f"{folder}/photos/{i}.jpg" for i in range(6)),
        *(f"{folder}/originals/{i}.jpg" for i in range(6)),
        f"{folder}/photos.json",
        f"{folder}/{CACHE_KEYS_FILE}",
        f"{CACHE_DIR}/k-arch.json",
    }
    if status == "done":
        expected |= {f"{folder}/{ROOM_FILE}", f"{folder}/{JOB_FILE}"}
    assert written == expected
    assert _snapshot(handles.root / "rooms" / "demo") == demo_before
    assert (handles.root / folder / "originals" / "0.jpg").read_bytes() == judge.uploads[0].original
    assert judge.listed_keys() == ["k-arch"]


def test_the_done_record_lands_in_the_judge_partition_and_reads_back_after_the_dict_entry_is_gone(handles, ticker, four_lock_room, code_and_find_room):
    seed_demo(handles, code_and_find_room, _demo_job(JOB_A, code_and_find_room))
    judge = JudgeBuild(handles, ticker, four_lock_room)
    done = judge.run()
    assert JobState.model_validate_json((handles.root / "rooms" / "judge" / judge.room_id / JOB_FILE).read_bytes()) == done
    handles.jobs.pop(done.id)
    again = hosted_stores(handles).jobs
    assert again.read(done.id) == done and again.read(JOB_A) == _demo_job(JOB_A, code_and_find_room)
    assert again.list_ids() == sorted([JOB_A, done.id])


@pytest.mark.parametrize("key", ["../demo/room_x/room.json", "../demo/room_x/photos/0.jpg", "x/../../demo/room_x/job.json"])
def test_no_artifact_key_reaches_the_demo_partition(handles, stores, log, key):
    with pytest.raises(ValueError, match="outside its partition"):
        stores.artifacts.put(key, b"x")
    assert log == [] and not handles.root.exists()


def test_only_the_seed_script_names_the_demo_partition_and_no_hosted_write_path_uses_it():
    sources = [*sorted((REPO / "src").rglob("*.py")), *sorted((REPO / "scripts").rglob("*.py"))]
    naming = set()
    for path in sources:
        tree = ast.parse(path.read_text())
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
            alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names
        }
        strings = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
        if "DEMO_PARTITION" in names or any("rooms/demo" in s and "\n" not in s for s in strings):
            naming.add(path.relative_to(REPO).as_posix())
    assert naming == {"src/infra/modal.py", "scripts/seed_rooms.py"}
    for writer in (VolumeArtifactStore.put, hosted.DictJobStore.put, hosted._final_record, run_judge_build):
        assert "demo" not in _code(writer).lower(), writer.__qualname__


def _code(fn: Callable[..., object]) -> str:
    """The function's code without its docstring."""
    node = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    assert isinstance(node, ast.FunctionDef)
    if ast.get_docstring(node) is not None:
        node.body = node.body[1:]
    return ast.unparse(node)


# --- cache-keys.json beside the originals, committed -----------------------------------


def test_cache_keys_json_lists_every_key_the_build_read_or_wrote_and_the_volume_is_committed(handles, stores, ticker, log, four_lock_room):
    stores.cache.put("k-hit", {"text": "cached", "model": "muse-spark-1.3", "usage": {}, "raw": None})
    stores.cache.put("k-other-build", {"text": "not ours", "model": "muse-spark-1.3", "usage": {}, "raw": None})
    judge = JudgeBuild(handles, ticker, four_lock_room)
    done = judge.run(chats={"architect": ["k-hit", "k-miss"], "segment": ["k-seg", "k-hit"], "author": ["k-miss", "k-author"]})
    assert done.status == "done"
    folder = handles.root / "rooms" / "judge" / judge.room_id
    assert judge.listed_keys() == ["k-hit", "k-miss", "k-seg", "k-author"]
    assert (folder / CACHE_KEYS_FILE).parent == (folder / "originals").parent
    assert all((handles.root / CACHE_DIR / f"{key}.json").exists() for key in judge.listed_keys())
    assert log[-1] == "commit"


def test_a_build_with_no_cache_call_still_leaves_an_empty_cache_keys_json(handles, ticker, four_lock_room):
    judge = JudgeBuild(handles, ticker, four_lock_room)
    assert judge.run().status == "done" and judge.listed_keys() == []


def test_a_restarted_runner_adds_its_keys_to_those_the_first_one_listed(handles, ticker, four_lock_room):
    judge = JudgeBuild(handles, ticker, four_lock_room)
    with pytest.raises(RunnerDied):
        judge.run(chats={"architect": ["k-arch"]}, raises={"author": RunnerDied()})
    assert judge.listed_keys() == ["k-arch"]
    done = judge.run(chats={"author": ["k-author", "k-arch"]})
    assert done.status == "done" and judge.listed_keys() == ["k-arch", "k-author"]


def test_the_key_log_records_reads_and_writes_once_each_in_first_use_order(handles, stores):
    keys = CacheKeyLog(stores.cache)
    assert keys.get("a") is None
    keys.put("b", {"v": 1})
    keys.put("a", {"v": 2})
    assert keys.get("b") == {"v": 1} and stores.cache.get("a") == {"v": 2}
    assert keys.keys() == ["a", "b"]


# --- A Judge room plays by its id, although it is never listed ---------------------------


def test_a_judge_room_serves_its_play_view_and_photos_by_id_although_it_is_never_listed(handles, stores, ticker, four_lock_room):
    judge = JudgeBuild(handles, ticker, four_lock_room)
    assert judge.run().status == "done"
    client = _client(stores)
    played = client.get(f"/api/rooms/{judge.room_id}")
    assert played.status_code == 200
    assert played.json() == to_play_view(judge.stored_room).model_dump(mode="json")
    photo = client.get(f"/api/rooms/{judge.room_id}/photos/0")
    assert photo.status_code == 200 and photo.content == judge.uploads[0].downscale
    assert stores.artifacts.read(photo_key(judge.room_id, 0)) == judge.uploads[0].downscale
    assert client.get("/api/rooms").json() == []
    assert client.get("/api/rooms/room_01CX5ZZKBKACTAV9WEVGEMMVRZ").status_code == 404


# --- Local mode lists every stored Room -----------------------------------------------


def test_local_list_rooms_still_lists_every_stored_room(tmp_path, four_lock_room, code_and_find_room):
    root = tmp_path / "rooms"
    store = DiskArtifactStore(root)
    third = four_lock_room.model_copy(update={"id": "room_01CX5ZZKBKACTAV9WEVGEMMVRZ", "created": four_lock_room.created.replace(year=2024)})
    store_room(store, four_lock_room)
    for partition, room in (("demo", code_and_find_room), ("judge", third)):
        store.put(f"{partition}/{room_key(room.id)}", room.model_dump_json().encode())
    assert {room.id for room in store.list_rooms()} == {four_lock_room.id, code_and_find_room.id, third.id}

    local = tmp_path / "local"
    local_store, jobs = artifact_store(local), job_store(local)
    for job_id, room in ((JOB_A, four_lock_room), (JOB_B, code_and_find_room)):
        store_room(local_store, room)
        jobs.put(_demo_job(job_id, room))
    app = FastAPI()
    app.include_router(room_routes(local_store, jobs))
    listed = TestClient(app).get("/api/rooms").json()
    assert sorted(row["room_id"] for row in listed) == sorted([four_lock_room.id, code_and_find_room.id])
