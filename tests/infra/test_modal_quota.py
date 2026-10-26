"""Story 7.10: the twenty-slot judge build quota on the `keyframe-jobs` Dict (AD-9, FR-32, A-25).

No test reaches Modal: the Dict is a plain dict whose `put` honours
`skip_if_exists` under one lock, standing in for the conditional write
Modal documents; the Volume is a temporary directory behind a stub.
Whether Modal's own `put(..., skip_if_exists=True)` is atomic under
concurrent writers is a live check outside this suite, pending in the
sprint status until it is run.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.domain.schema import JobStatus
from src.infra.modal import BUILD_QUOTA, SLOT_KEYS, DictJobStore, VolumeFiles, slot_key
from src.pipeline.build import error_code, new_id
from src.pipeline.ports import BuildQuotaExceeded
from tests.infra.test_local import _job_state
from tests.infra.test_modal import RecordingDict, StubVolume


@pytest.fixture
def jobs() -> RecordingDict:
    return RecordingDict()


@pytest.fixture
def files(tmp_path: Path) -> VolumeFiles:
    return VolumeFiles(StubVolume([]), tmp_path / "data")


def _claim_all(store: DictJobStore) -> list[str]:
    ids = [new_id("job") for _ in range(BUILD_QUOTA)]
    for job_id in ids:
        store.reserve_build(job_id)
    return ids


def _race(store: DictJobStore, claimers: list[str]) -> list[bool]:
    """Every claimer calls `reserve_build` at once, each on its own thread; whether each won a slot."""
    start = threading.Barrier(len(claimers))

    def claim(job_id: str) -> bool:
        start.wait()
        try:
            store.reserve_build(job_id)
        except BuildQuotaExceeded:
            return False
        return True

    with ThreadPoolExecutor(len(claimers)) as pool:
        return list(pool.map(claim, claimers))


def test_the_quota_is_twenty_slot_keys_in_the_jobs_dict():
    assert BUILD_QUOTA == 20
    assert SLOT_KEYS == {f"build:{n}" for n in range(1, 21)} and slot_key(1) == "build:1"


def test_twenty_claims_succeed_and_the_21st_raises_and_writes_nothing(jobs, files):
    store = DictJobStore(jobs, files)
    ids = _claim_all(store)
    assert {key: jobs[key] for key in SLOT_KEYS} == {slot_key(n): job_id for n, job_id in enumerate(ids, 1)}
    before, writes = dict(jobs), list(jobs.writes)
    with pytest.raises(BuildQuotaExceeded) as refused:
        store.reserve_build(new_id("job"))
    assert jobs == before and jobs.writes == writes
    assert refused.value.quota == 20 and str(refused.value) == "all 20 judge builds are used"
    assert error_code(refused.value) == "build_quota_exceeded"
    assert store.builds_left() == 0


def test_each_claim_is_one_conditional_put_per_slot_until_a_free_one(files):
    calls: list[tuple[str, str, bool]] = []

    class LoggingDict(RecordingDict):
        def put(self, key, value, /, *, skip_if_exists=False):
            calls.append((key, value, skip_if_exists))
            return super().put(key, value, skip_if_exists=skip_if_exists)

    jobs = LoggingDict()
    store = DictJobStore(jobs, files)
    first, second = new_id("job"), new_id("job")
    store.reserve_build(first)
    store.reserve_build(second)
    assert calls == [("build:1", first, True), ("build:1", second, True), ("build:2", second, True)]


@pytest.mark.parametrize("end", ["failed", "needs_more_photos", "needs_recapture", "done"])
def test_every_accepted_build_counts_whatever_its_end_status(jobs, files, end: JobStatus):
    store = DictJobStore(jobs, files)
    assert store.builds_left() == 20
    for left in (19, 18, 17):
        job_id = new_id("job")
        store.reserve_build(job_id)
        store.put(_job_state(job_id).model_copy(update={"status": "queued", "stage": None}))
        store.put(_job_state(job_id).model_copy(update={"status": end, "room_id": None}))
        assert store.read(job_id).status == end
        assert store.builds_left() == left


def test_the_count_lives_in_the_dict_and_reading_it_claims_nothing(jobs, files, tmp_path):
    first = DictJobStore(jobs, files)
    claimed = [new_id("job") for _ in range(7)]
    for job_id in claimed:
        first.reserve_build(job_id)
    before, writes = dict(jobs), list(jobs.writes)
    restarted = DictJobStore(jobs, VolumeFiles(StubVolume([]), tmp_path / "data"))
    assert [restarted.builds_left() for _ in range(5)] == [13] * 5
    assert jobs == before and jobs.writes == writes
    assert restarted.list_ids() == [], "slot keys are not job ids"


def test_concurrent_claimers_over_19_claimed_slots_produce_exactly_one_more_claim(jobs, files):
    for n in range(1, BUILD_QUOTA):
        jobs[slot_key(n)] = new_id("job")
    store = DictJobStore(jobs, files)
    claimers = [new_id("job") for _ in range(16)]
    won = _race(store, claimers)
    assert won.count(True) == 1
    assert jobs[slot_key(BUILD_QUOTA)] == claimers[won.index(True)]
    assert store.builds_left() == 0


def test_forty_concurrent_claimers_take_each_of_the_twenty_slots_once(jobs, files):
    store = DictJobStore(jobs, files)
    claimers = [new_id("job") for _ in range(40)]
    won = [job_id for job_id, ok in zip(claimers, _race(store, claimers), strict=True) if ok]
    assert len(won) == 20
    assert sorted(jobs[key] for key in SLOT_KEYS) == sorted(won)
    assert store.builds_left() == 0
