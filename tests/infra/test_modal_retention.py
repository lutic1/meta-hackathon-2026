"""Story 7.18: a Judge room's deletion with its ids-only record, and the Session sweep (AD-8, AD-9, FR-33, NFR-4).

No test reaches Modal: the Dicts are plain dicts, the Volume is a temporary
directory behind a stub that logs `commit` and `reload`, and each Judge room
is built by the real `Build` over the hosted stores, as in Story 7.14.
"""

from __future__ import annotations

import ast
import json
import secrets
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from src.domain.schema import (
    ClickEvent,
    CodeInput,
    Event,
    HintRequestEvent,
    IdleTickEvent,
    JobState,
    LockInputEvent,
    OpeningLineEvent,
    Room,
)
from src.infra.local import DiskArtifactStore, DiskCache, JsonJobStore, JsonlLedgerStore
from src.infra.modal import (
    CACHE_DIR,
    CACHE_KEYS_FILE,
    DEADLINE_S,
    JOB_FILE,
    SESSION_TTL_MS,
    DeletionRecord,
    DictSessionStore,
    ModalHandles,
    VolumeFiles,
    call_key,
    delete_judge_room,
    hosted_stores,
    minted_ms,
    sweep_sessions,
)
from src.pipeline.ports import ROOM_FILE
from src.providers.spend import CROCKFORD_BASE32
from tests.infra.test_clocks import Ticker
from tests.infra.test_local import JOB_A
from tests.infra.test_modal import RecordingDict, StubVolume, seed_demo
from tests.infra.test_modal_partitions import ENDINGS, JudgeBuild, _snapshot

REPO = Path(__file__).resolve().parents[2]
NOV_10 = date(2026, 11, 10)
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
HOUR_MS = 60 * 60 * 1000
ENTRY = {"text": "cached", "model": "muse-spark-1.3", "usage": {}, "raw": None}

# --- Doubles -------------------------------------------------------------------


class FlakyDict(RecordingDict):
    """A `keyframe-*` Dict whose next `pop` raises once `fail_pops` is set, or whose `pop` of `fail_key` raises once, as a Modal client error would."""

    fail_pops = 0
    fail_key: str | None = None

    def pop(self, key: Any, /) -> Any:
        if self.fail_pops or key == self.fail_key:
            self.fail_pops = max(self.fail_pops - 1, 0)
            self.fail_key = None
            raise ConnectionError("the Dict did not answer")
        return super().pop(key)


class FlakyVolume(StubVolume):
    """A stub Volume whose `fail_at`-th commit from now raises, after the files it would persist are already removed locally."""

    fail_at = 0

    def commit(self) -> None:
        if self.fail_at:
            self.fail_at -= 1
            if not self.fail_at:
                raise ConnectionError("the commit did not reach the Volume")
        super().commit()


@pytest.fixture
def log() -> list[str]:
    return []


@pytest.fixture
def handles(tmp_path: Path, log: list[str]) -> ModalHandles:
    return ModalHandles(jobs=FlakyDict(), sessions=FlakyDict(), ledger=RecordingDict(), volume=FlakyVolume(log), root=tmp_path / "data")


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


def sess_at(ms: int) -> str:
    """A `sess_` ULID minted at Unix milliseconds `ms`."""
    stamp = "".join(CROCKFORD_BASE32[(ms >> shift) & 31] for shift in range(45, -5, -5))
    return f"sess_{stamp}{''.join(secrets.choice(CROCKFORD_BASE32) for _ in range(16))}"


def wall_ms(at: datetime) -> int:
    return int(at.timestamp() * 1000)


def played(room: Room, *, last_t_ms: int = 60_000) -> list[Event]:
    """A Session on `room`: the welcome, a click on its first interactable, a code on its first puzzle and a hint, the last at `last_t_ms`."""
    return [
        OpeningLineEvent(type="opening_line", kind="welcome", text="Welcome.", t_ms=0),
        ClickEvent(type="click", interactable_id=room.interactables[0].id, t_ms=1_200),
        LockInputEvent(type="lock_input", input=CodeInput(type="code", puzzle_id=room.puzzles[0].id, code="000"), t_ms=4_800),
        HintRequestEvent(type="hint_request", puzzle_id=None, t_ms=last_t_ms),
    ]


def store_session(handles: ModalHandles, session_id: str, events: list[Event]) -> None:
    store = DictSessionStore(handles.sessions)
    for event in events:
        store.append(session_id, event)


def room_ids(room: Room) -> set[str]:
    return {ix.id for ix in room.interactables} | {pz.id for pz in room.puzzles}


def reminted(room: Room) -> Room:
    """The Room with fresh `ix_` and `pz_` ids, as two Builds never share one; the fixture Rooms reuse theirs."""
    raw = room.model_dump_json()
    for prefix in ("ix_", "pz_"):
        raw = raw.replace(f'"{prefix}0000000000', f'"{prefix}DDDDDDDDDD')
    return Room.model_validate_json(raw)


class Scene:
    """A seeded Demo room with its Cache entry and a recent Session, an unlisted Cache entry, and one Judge build ended `ending`."""

    def __init__(self, handles: ModalHandles, ticker: Ticker, judge_room: Room, demo_room: Room, ending: str = "done") -> None:
        demo_room = reminted(demo_room)
        assert not room_ids(judge_room) & room_ids(demo_room)
        self.handles = handles
        stores = hosted_stores(handles)
        seed_demo(handles, demo_room, JobState(id=JOB_A, status="done", room_id=demo_room.id, regen_max=2, build_time_ms=28_000))
        stores.cache.put("k-demo", ENTRY)
        stores.cache.put("k-unlisted", ENTRY)
        self.demo_session = sess_at(wall_ms(NOW) - HOUR_MS)
        store_session(handles, self.demo_session, played(demo_room))
        self.judge = JudgeBuild(handles, ticker, judge_room)
        raises, status = ENDINGS[ending]
        self.state = self.judge.run(chats={"architect": ["k-arch", "k-arch-2"]}, raises=raises)
        assert self.state.status == status
        self.handles.jobs[call_key(self.state.id)] = "fc-judge"
        self.judge_session: str | None = None
        if status == "done":
            self.judge_session = sess_at(wall_ms(NOW) - HOUR_MS)
            store_session(handles, self.judge_session, played(self.judge.stored_room))
        self.demo_before = _snapshot(handles.root / "rooms" / "demo")

    @property
    def room_id(self) -> str:
        return self.judge.room_id

    @property
    def folder(self) -> Path:
        return self.handles.root / "rooms" / "judge" / self.room_id

    @property
    def record_file(self) -> Path:
        return self.handles.root / "rooms" / "deleted" / f"{self.room_id}.json"

    def assert_deleted(self) -> None:
        """Everything of the Judge room is gone, and everything else is as it was."""
        assert not self.folder.exists()
        assert not (self.handles.root / CACHE_DIR / "k-arch.json").exists()
        assert not (self.handles.root / CACHE_DIR / "k-arch-2.json").exists()
        assert (self.handles.root / CACHE_DIR / "k-demo.json").exists() and (self.handles.root / CACHE_DIR / "k-unlisted.json").exists()
        assert _snapshot(self.handles.root / "rooms" / "demo") == self.demo_before
        assert DictSessionStore(self.handles.sessions).list_ids() == [self.demo_session]
        assert self.state.id not in self.handles.jobs and call_key(self.state.id) not in self.handles.jobs
        assert self.state.id in self.handles.jobs.values()  # the quota slot it claimed stays claimed


# --- One deletion takes the Room, its photos, originals, Sessions and listed Cache entries --


@pytest.mark.parametrize("ending", ["done", "failed", "needs_more_photos", "needs_recapture"])
def test_a_judge_room_goes_with_its_photos_originals_sessions_and_listed_cache_entries_and_the_volume_is_committed(
    handles, ticker, log, four_lock_room, code_and_find_room, ending
):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room, ending)
    assert (scene.folder / "originals" / "0.jpg").exists() and (scene.folder / "photos" / "0.jpg").exists()
    assert json.loads((scene.folder / CACHE_KEYS_FILE).read_bytes()) == ["k-arch", "k-arch-2"]
    assert (scene.folder / ROOM_FILE).exists() == (ending == "done") == (scene.folder / JOB_FILE).exists()

    record = delete_judge_room(handles, scene.room_id, today=NOV_10)

    scene.assert_deleted()
    assert record == DeletionRecord(room_id=scene.room_id, job_id=scene.state.id, deleted_on=NOV_10)
    assert log[-1] == "commit"


def test_a_session_on_a_judge_room_is_found_through_list_ids_and_read_all_and_removed_with_delete(handles, ticker, four_lock_room, code_and_find_room, monkeypatch):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    calls: list[tuple[str, str]] = []
    for name in ("list_ids", "read_all", "delete"):
        real = getattr(DictSessionStore, name)
        monkeypatch.setattr(DictSessionStore, name, lambda self, *args, _real=real, _name=name: calls.append((_name, *args)) or _real(self, *args))
    delete_judge_room(handles, scene.room_id, today=NOV_10)
    assert ("list_ids",) in calls and ("read_all", scene.judge_session) in calls and ("read_all", scene.demo_session) in calls
    assert [call for call in calls if call[0] == "delete"] == [("delete", scene.judge_session)]


# --- The ids-only record under rooms/deleted/ --------------------------------------------


def test_the_deletion_record_holds_the_room_id_job_id_and_date_and_no_content(handles, ticker, four_lock_room, code_and_find_room):
    named = four_lock_room.model_copy(update={"name": "Grandma's kitchen"})
    scene = Scene(handles, ticker, named, code_and_find_room)
    delete_judge_room(handles, scene.room_id, today=NOV_10)

    deleted = handles.root / "rooms" / "deleted"
    assert [path.name for path in deleted.iterdir()] == [f"{scene.room_id}.json"]
    raw = scene.record_file.read_text()
    assert json.loads(raw) == {"room_id": scene.room_id, "job_id": scene.state.id, "deleted_on": "2026-11-10"}
    content = {"Grandma's kitchen", *(ix.label for ix in named.interactables), *(pz.clue for pz in named.puzzles), "jpg", "originals"}
    assert not [text for text in content if text and text in raw]


def test_a_judge_room_whose_job_record_is_gone_is_still_deleted_with_a_null_job_id(handles, ticker, four_lock_room, code_and_find_room):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room, "failed")
    handles.jobs.pop(scene.state.id)
    assert delete_judge_room(handles, scene.room_id, today=NOV_10) == DeletionRecord(room_id=scene.room_id, job_id=None, deleted_on=NOV_10)
    assert not scene.folder.exists()


# --- A Demo room id is refused --------------------------------------------------------------


def test_a_demo_room_id_is_refused_and_nothing_is_deleted(handles, ticker, four_lock_room, code_and_find_room):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    files_before = _snapshot(handles.root)
    sessions_before, jobs_before = dict(handles.sessions), dict(handles.jobs)

    with pytest.raises(ValueError, match="Demo room"):
        delete_judge_room(handles, code_and_find_room.id, today=NOV_10)

    assert _snapshot(handles.root) == files_before and not (handles.root / "rooms" / "deleted").exists()
    assert dict(handles.sessions) == sessions_before and dict(handles.jobs) == jobs_before
    assert scene.folder.exists()


@pytest.mark.parametrize("room_id", ["../demo/x", "room_x", "", "room_01ARZ3NDEKTSV4RRFFQ69G5FAV/.."])
def test_an_id_that_is_not_a_room_id_is_refused_before_the_volume_is_touched(handles, log, room_id):
    with pytest.raises(ValueError):
        delete_judge_room(handles, room_id, today=NOV_10)
    assert log == [] and not handles.root.exists()


def test_an_unknown_room_id_raises_key_error_and_writes_no_record(handles):
    with pytest.raises(KeyError):
        delete_judge_room(handles, "room_01CX5ZZKBKACTAV9WEVGEMMVRZ", today=NOV_10)
    assert not (handles.root / "rooms" / "deleted").exists()


def test_a_room_already_deleted_returns_its_first_record_again(handles, ticker, four_lock_room, code_and_find_room):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    first = delete_judge_room(handles, scene.room_id, today=NOV_10)
    assert delete_judge_room(handles, scene.room_id, today=date(2026, 11, 11)) == first
    scene.assert_deleted()


@pytest.mark.parametrize("listing", [b'["../rooms/demo/x"]', b'[".."]', b'["k/../../rooms"]'])
def test_a_listed_key_that_is_not_a_file_name_stops_the_deletion_before_any_cache_entry_goes(handles, ticker, four_lock_room, code_and_find_room, listing):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    (scene.folder / CACHE_KEYS_FILE).write_bytes(listing)
    with pytest.raises(ValueError, match="not a file name"):
        delete_judge_room(handles, scene.room_id, today=NOV_10)
    assert scene.folder.exists() and not scene.record_file.exists()
    assert _snapshot(handles.root / "rooms" / "demo") == scene.demo_before


# --- A deletion that fails part-way raises, writes no record, and a rerun completes it ------


def fail_record_write(handles: ModalHandles, monkeypatch: pytest.MonkeyPatch) -> None:
    """The next write of a deletion record raises before anything reaches the disk."""
    real = VolumeFiles.write
    pending = [True]

    def write(self: VolumeFiles, rel: str, data: bytes) -> None:
        if rel.startswith("rooms/deleted/") and pending:
            pending.clear()
            raise ConnectionError("the write did not reach the Volume")
        real(self, rel, data)

    monkeypatch.setattr(VolumeFiles, "write", write)


FAILURES: dict[str, tuple[Callable[[Scene, pytest.MonkeyPatch], None], bool]] = {
    "session delete": (lambda scene, _: setattr(scene.handles.sessions, "fail_pops", 1), False),
    "cache entry commit": (lambda scene, _: setattr(scene.handles.volume, "fail_at", 1), False),
    "folder commit": (lambda scene, _: setattr(scene.handles.volume, "fail_at", 2), False),
    "record write": (lambda scene, mp: fail_record_write(scene.handles, mp), False),
    "record write with the job entry expired": (lambda scene, mp: (scene.handles.jobs.pop(scene.state.id), fail_record_write(scene.handles, mp)), False),
    "record commit": (lambda scene, _: setattr(scene.handles.volume, "fail_at", 3), True),
    "final record commit": (lambda scene, _: setattr(scene.handles.volume, "fail_at", 4), True),
    "job key delete": (lambda scene, _: setattr(scene.handles.jobs, "fail_pops", 1), True),
    "call key delete": (lambda scene, _: setattr(scene.handles.jobs, "fail_key", call_key(scene.state.id)), True),
}
"""Each failure point, and whether the record is on disk when it raises: it is written once the Room's content is gone, before the job is forgotten."""


@pytest.mark.parametrize("failure", list(FAILURES))
def test_a_deletion_that_fails_part_way_raises_and_a_rerun_completes_it_with_the_right_job_id(handles, ticker, four_lock_room, code_and_find_room, monkeypatch, failure):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    fail, record_written = FAILURES[failure]
    fail(scene, monkeypatch)

    with pytest.raises(ConnectionError):
        delete_judge_room(handles, scene.room_id, today=NOV_10)
    assert scene.record_file.exists() == record_written
    if record_written:  # the Room, photos, originals, Sessions and listed Cache entries went before the record
        assert not scene.folder.exists() or [path.name for path in scene.folder.iterdir()] == [JOB_FILE]
        assert DictSessionStore(handles.sessions).list_ids() == [scene.demo_session]

    record = delete_judge_room(handles, scene.room_id, today=date(2026, 11, 11))
    scene.assert_deleted()
    assert record == DeletionRecord(room_id=scene.room_id, job_id=scene.state.id, deleted_on=NOV_10 if record_written else date(2026, 11, 11))
    assert DeletionRecord.model_validate_json(scene.record_file.read_bytes()) == record


# --- A Room whose job may still be running is refused -----------------------------------


def test_a_room_whose_job_is_still_running_is_refused_and_nothing_is_deleted(handles, ticker, four_lock_room, code_and_find_room):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    handles.jobs[scene.state.id] = scene.state.model_copy(update={"status": "running", "stage": "scene"}).model_dump(mode="json")
    files_before, sessions_before = _snapshot(handles.root), dict(handles.sessions)

    with pytest.raises(ValueError, match="running job"):
        delete_judge_room(handles, scene.room_id, today=NOV_10)
    assert _snapshot(handles.root) == files_before and dict(handles.sessions) == sessions_before


def test_a_room_whose_job_is_stuck_running_past_its_deadline_is_deleted(handles, ticker, four_lock_room, code_and_find_room, monkeypatch):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    handles.jobs[scene.state.id] = scene.state.model_copy(update={"status": "running", "stage": "scene"}).model_dump(mode="json")
    late = minted_ms(scene.state.id) + DEADLINE_S * 1000 + 1
    monkeypatch.setattr("src.infra.modal.wall_ms", lambda: late)
    delete_judge_room(handles, scene.room_id, today=NOV_10)
    scene.assert_deleted()


# --- The Session sweep ------------------------------------------------------------------


def test_a_session_whose_last_event_is_over_24_h_old_is_swept_and_a_recent_one_kept(handles, code_and_find_room):
    old = sess_at(wall_ms(NOW) - 26 * HOUR_MS)
    store_session(handles, old, played(code_and_find_room, last_t_ms=HOUR_MS + 1))  # last event 25 h before NOW
    started_long_ago = sess_at(wall_ms(NOW) - 30 * HOUR_MS)
    store_session(handles, started_long_ago, played(code_and_find_room, last_t_ms=29 * HOUR_MS))  # last event 1 h before NOW
    assert minted_ms(old) == wall_ms(NOW) - 26 * HOUR_MS

    assert sweep_sessions(handles, now=NOW) == [old]
    assert DictSessionStore(handles.sessions).list_ids() == [started_long_ago]


def test_a_session_exactly_24_h_past_its_last_event_is_kept_until_it_is_older(handles, code_and_find_room):
    session = sess_at(wall_ms(NOW) - SESSION_TTL_MS - 60_000)
    store_session(handles, session, played(code_and_find_room, last_t_ms=60_000))
    assert sweep_sessions(handles, now=NOW) == []
    assert sweep_sessions(handles, now=NOW + timedelta(milliseconds=1)) == [session]


def test_a_session_with_only_its_opening_line_and_idle_ticks_ages_from_its_last_tick(handles):
    session = sess_at(wall_ms(NOW) - 25 * HOUR_MS)
    store_session(handles, session, [OpeningLineEvent(type="opening_line", kind="welcome", text="Welcome.", t_ms=0), IdleTickEvent(type="idle_tick", t_ms=2 * HOUR_MS)])
    assert sweep_sessions(handles, now=NOW) == []
    assert sweep_sessions(handles, now=NOW + timedelta(hours=1, milliseconds=1)) == [session]


def test_sessions_of_a_deleted_room_go_whatever_their_age_while_the_sweep_keeps_recent_ones(handles, ticker, four_lock_room, code_and_find_room):
    scene = Scene(handles, ticker, four_lock_room, code_and_find_room)
    assert sweep_sessions(handles, now=NOW) == []
    assert DictSessionStore(handles.sessions).list_ids() == sorted([scene.demo_session, scene.judge_session or ""])

    delete_judge_room(handles, scene.room_id, today=NOV_10)
    assert DictSessionStore(handles.sessions).list_ids() == [scene.demo_session]


# --- Local mode deletes nothing but the one session file the port names ------------------


def _calls(path: Path) -> list[tuple[str, str]]:
    """Every call in the file as (called name, the dotted class and function it sits in, "" at module level)."""
    found: list[tuple[str, str]] = []

    def walk(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            inner = scope
            if isinstance(child, ast.FunctionDef | ast.ClassDef):
                inner = f"{scope}.{child.name}" if scope else child.name
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute):
                    found.append((func.attr, inner))
                elif isinstance(func, ast.Name):
                    found.append((func.id, inner))
            walk(child, inner)

    walk(ast.parse(path.read_text()), "")
    return found


REMOVERS = {"unlink", "rmtree", "rmdir", "remove", "removedirs"}
HOSTED_ONLY = {"src/infra/modal.py", "src/api/modal_app.py", "scripts/purge_judge_rooms.py"}
"""The hosted entry point and the purge script are the only other places allowed to run the retention functions."""
IN_MEMORY = {"src/domain/edits.py": {"remove"}}
"""Calls named like a remover that only edit a list in memory: a Shortcut takes one Puzzle off a `requires` list."""


def test_no_local_adapter_deletes_and_nothing_outside_the_hosted_modules_runs_a_deletion():
    sources = sorted([*(REPO / "src").rglob("*.py"), *(REPO / "scripts").rglob("*.py")])
    local = [(name, scope) for name, scope in _calls(REPO / "src" / "infra" / "local.py") if name in REMOVERS | {"delete"}]
    assert set(local) == {("unlink", "JsonSessionStore.delete")}  # the log and its header
    for path in sources:
        rel = path.relative_to(REPO).as_posix()
        if rel in HOSTED_ONLY or rel == "src/infra/local.py":
            continue
        calls = {name for name, _ in _calls(path)} - IN_MEMORY.get(rel, set())
        assert not calls & (REMOVERS | {"delete", "delete_judge_room", "sweep_sessions"}), rel
        assert "delete_judge_room" not in path.read_text() and "sweep_sessions" not in path.read_text(), rel


def test_the_local_artifact_store_and_cache_have_no_way_to_delete():
    for adapter in (DiskArtifactStore, DiskCache, JsonJobStore, JsonlLedgerStore):
        assert not {name for name in vars(adapter) if not name.startswith("_")} & {"delete", "remove", "purge", "clear"}, adapter.__name__
