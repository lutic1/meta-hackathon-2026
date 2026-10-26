"""The ports and doubles every stage-runner test builds over: a job store in memory, artifacts on disk, a hand-advanced clock."""

import pytest

from src.infra.local import DiskArtifactStore
from src.pipeline.ingest import Upload
from tests.infra.test_clocks import Ticker
from tests.pipeline.test_build import Doubles, MemoryJobStore
from tests.pipeline.uploads import make_uploads


@pytest.fixture(scope="module")
def uploads() -> list[Upload]:
    return make_uploads(6)


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def jobs() -> MemoryJobStore:
    return MemoryJobStore()


@pytest.fixture
def artifacts(tmp_path) -> DiskArtifactStore:
    return DiskArtifactStore(tmp_path / "rooms")


@pytest.fixture
def doubles(ticker) -> Doubles:
    return Doubles(ticker)
