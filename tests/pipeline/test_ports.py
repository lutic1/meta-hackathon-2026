"""Stories 1.10, 2.3, 2.4, 2.10, 7.10 and 7.15: `src/pipeline/ports.py` declares `ArtifactStore`, `SessionStore`, `LedgerStore`, `Cache`, `JobStore` and `JobRunner` over the domain only and re-exports `Clock` (AD-1, AD-7, AD-9, AD-10)."""

import inspect
import sys
import typing
from pathlib import Path

from src.domain import clock
from src.domain.ledger import LedgerEntry
from src.domain.schema import Event, JobId, JobState, Room, SessionId
from src.domain.session import SessionHeader
from src.pipeline import ports
from src.pipeline.ports import (
    ROOM_FILE,
    ArtifactStore,
    BuildQuotaExceeded,
    Cache,
    Clock,
    JobRunner,
    JobStore,
    LedgerStore,
    SessionStore,
    photo_key,
    room_key,
)
from tests.test_boundaries import _imports

REPO = Path(__file__).resolve().parents[2]


def test_ledger_store_declares_append_and_entries():
    assert typing.is_protocol(LedgerStore)
    assert [p.name for p in inspect.signature(LedgerStore.append, eval_str=True).parameters.values()] == ["self", "entry"]
    assert inspect.signature(LedgerStore.append, eval_str=True).parameters["entry"].annotation is LedgerEntry
    assert inspect.signature(LedgerStore.entries, eval_str=True).return_annotation == list[LedgerEntry]


def test_a_structural_double_satisfies_the_port():
    class Memory:
        def __init__(self) -> None:
            self.rows: list[LedgerEntry] = []

        def append(self, entry: LedgerEntry) -> None:
            self.rows.append(entry)

        def entries(self) -> list[LedgerEntry]:
            return list(self.rows)

    store: LedgerStore = Memory()
    assert store.entries() == []


def test_cache_declares_get_and_put_over_json_objects():
    assert typing.is_protocol(Cache)
    get = inspect.signature(Cache.get, eval_str=True)
    put = inspect.signature(Cache.put, eval_str=True)
    assert [p.name for p in get.parameters.values()] == ["self", "key"]
    assert get.parameters["key"].annotation is str and get.return_annotation == dict[str, typing.Any] | None
    assert [p.name for p in put.parameters.values()] == ["self", "key", "value"]
    assert put.parameters["value"].annotation == dict[str, typing.Any] and put.return_annotation is None


def test_a_structural_cache_double_satisfies_the_port():
    class Memory:
        def __init__(self) -> None:
            self.rows: dict[str, dict[str, typing.Any]] = {}

        def get(self, key: str) -> dict[str, typing.Any] | None:
            return self.rows.get(key)

        def put(self, key: str, value: dict[str, typing.Any]) -> None:
            self.rows[key] = value

    cache: Cache = Memory()
    assert cache.get("k") is None
    cache.put("k", {"text": "hi"})
    assert cache.get("k") == {"text": "hi"}


def _params(func) -> list[str]:
    return [p.name for p in inspect.signature(func, eval_str=True).parameters.values()]


def test_artifact_store_declares_put_read_and_list_rooms():
    assert typing.is_protocol(ArtifactStore)
    put = inspect.signature(ArtifactStore.put, eval_str=True)
    assert _params(ArtifactStore.put) == ["self", "key", "data"]
    assert put.parameters["key"].annotation is str and put.parameters["data"].annotation is bytes
    assert put.return_annotation is None
    assert _params(ArtifactStore.read) == ["self", "key"]
    assert inspect.signature(ArtifactStore.read, eval_str=True).return_annotation is bytes
    assert _params(ArtifactStore.list_rooms) == ["self"]
    assert inspect.signature(ArtifactStore.list_rooms, eval_str=True).return_annotation == list[Room]
    assert ports.ROOM_FILE == "room.json"


def test_artifact_store_declares_the_demo_room_read_over_a_room_id():
    """Story 7.15: the port tells whether a `room_id` is a Demo room, so `POST /sessions` picks the welcome from it."""
    is_demo = inspect.signature(ArtifactStore.is_demo_room, eval_str=True)
    assert _params(ArtifactStore.is_demo_room) == ["self", "room_id"]
    assert is_demo.parameters["room_id"].annotation is str and is_demo.return_annotation is bool


def test_artifact_store_declares_the_judge_room_read_over_a_room_id():
    """Story 7.21: the port tells whether a `room_id` is a Judge room, so the session state carries `judge_room`."""
    is_judge = inspect.signature(ArtifactStore.is_judge_room, eval_str=True)
    assert _params(ArtifactStore.is_judge_room) == ["self", "room_id"]
    assert is_judge.parameters["room_id"].annotation is str and is_judge.return_annotation is bool


def test_session_store_declares_append_read_all_list_ids_and_delete():
    assert typing.is_protocol(SessionStore)
    append = inspect.signature(SessionStore.append, eval_str=True)
    assert _params(SessionStore.append) == ["self", "session_id", "event"]
    assert append.parameters["session_id"].annotation == SessionId and append.parameters["event"].annotation == Event
    assert append.return_annotation is None
    assert _params(SessionStore.read_all) == ["self", "session_id"]
    assert inspect.signature(SessionStore.read_all, eval_str=True).return_annotation == list[Event]
    assert _params(SessionStore.list_ids) == ["self"]
    assert inspect.signature(SessionStore.list_ids, eval_str=True).return_annotation == list[SessionId]
    assert _params(SessionStore.delete) == ["self", "session_id"]
    assert inspect.signature(SessionStore.delete, eval_str=True).return_annotation is None


def test_session_store_declares_the_header_beside_the_log():
    put = inspect.signature(SessionStore.put_header, eval_str=True)
    assert _params(SessionStore.put_header) == ["self", "session_id", "header"]
    assert put.parameters["header"].annotation is SessionHeader and put.return_annotation is None
    assert _params(SessionStore.read_header) == ["self", "session_id"]
    assert inspect.signature(SessionStore.read_header, eval_str=True).return_annotation is SessionHeader


def test_job_store_declares_put_read_and_list_ids_over_job_state():
    assert typing.is_protocol(JobStore)
    put = inspect.signature(JobStore.put, eval_str=True)
    assert _params(JobStore.put) == ["self", "state"]
    assert put.parameters["state"].annotation is JobState and put.return_annotation is None
    read = inspect.signature(JobStore.read, eval_str=True)
    assert _params(JobStore.read) == ["self", "job_id"]
    assert read.parameters["job_id"].annotation == JobId and read.return_annotation is JobState
    assert _params(JobStore.list_ids) == ["self"]
    assert inspect.signature(JobStore.list_ids, eval_str=True).return_annotation == list[JobId]


def test_job_store_declares_a_slot_claim_and_a_builds_left_read():
    reserve = inspect.signature(JobStore.reserve_build, eval_str=True)
    assert _params(JobStore.reserve_build) == ["self", "job_id"]
    assert reserve.parameters["job_id"].annotation == JobId and reserve.return_annotation is None
    assert _params(JobStore.builds_left) == ["self"]
    assert inspect.signature(JobStore.builds_left, eval_str=True).return_annotation == int | None
    assert "BuildQuotaExceeded" in ports.__all__ and issubclass(BuildQuotaExceeded, Exception)
    assert "BuildQuotaExceeded" in (JobStore.__doc__ or "")
    refused = BuildQuotaExceeded(20)
    assert refused.quota == 20 and str(refused) == "all 20 judge builds are used"


def test_job_runner_declares_start_over_a_job_id():
    assert typing.is_protocol(JobRunner)
    start = inspect.signature(JobRunner.start, eval_str=True)
    assert _params(JobRunner.start) == ["self", "job_id"]
    assert start.parameters["job_id"].annotation == JobId and start.return_annotation is None


def test_structural_job_doubles_satisfy_both_ports():
    class Memory:
        def __init__(self) -> None:
            self.rows: dict[str, JobState] = {}
            self.claimed: list[JobId] = []

        def put(self, state: JobState) -> None:
            self.rows[state.id] = state

        def read(self, job_id: JobId) -> JobState:
            return self.rows[job_id]

        def list_ids(self) -> list[JobId]:
            return sorted(self.rows)

        def reserve_build(self, job_id: JobId) -> None:
            if self.builds_left() == 0:
                raise BuildQuotaExceeded(1)
            self.claimed.append(job_id)

        def builds_left(self) -> int | None:
            return 1 - len(self.claimed)

    class Runner:
        def __init__(self) -> None:
            self.started: list[JobId] = []

        def start(self, job_id: JobId) -> None:
            self.started.append(job_id)

    store: JobStore = Memory()
    runner: JobRunner = Runner()
    state = JobState(id="job_01ARZ3NDEKTSV4RRFFQ69G5FAV", status="queued", regen_max=2)
    store.put(state)
    assert store.read(state.id) == state and store.list_ids() == [state.id]
    runner.start(state.id)
    assert runner.started == [state.id]
    store.reserve_build(state.id)
    assert store.builds_left() == 0


def test_clock_is_re_exported_from_the_domain():
    assert Clock is clock.Clock and "Clock" in ports.__all__
    assert {"JobStore", "JobRunner"} <= set(ports.__all__)


def test_ports_import_only_the_domain():
    src = REPO / "src"
    names = _imports(src / "pipeline" / "ports.py", "src.pipeline.ports", src)
    internal = {n for n in names if n.startswith("src.")}
    assert internal and all(n.startswith("src.domain") for n in internal), names
    assert {n.split(".")[0] for n in names - internal} <= set(sys.stdlib_module_names)


def test_room_and_photo_keys_sit_under_the_room_folder():
    room_id = "room_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert room_key(room_id) == f"{room_id}/{ROOM_FILE}" == f"{room_id}/room.json"
    assert [photo_key(room_id, i) for i in range(2)] == [f"{room_id}/photos/0.jpg", f"{room_id}/photos/1.jpg"]
