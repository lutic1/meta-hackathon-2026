"""The hosted app over plain dicts and a temporary Volume directory, so no test reaches Modal (AD-17)."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from src.api.app import create_app
from src.config import Settings
from src.domain.schema import JobId, Room, Stage
from src.infra.modal import ModalHandles, RunnerState
from src.pipeline.build import StageFn
from src.pipeline.ports import Clock
from tests.api.test_app import idle_stages
from tests.infra.test_modal import RecordingDict, seed_demo

HOSTED = {"MODE": "hosted", "MODEL_PROVIDER": "mock"}
"""The hosted settings the API tests run under: `MODE=hosted` with its defaults, over the mock provider."""


class NullVolume:
    """The two Volume calls the adapters make, as no-ops."""

    def commit(self) -> None:
        pass

    def reload(self) -> None:
        pass


@dataclass(frozen=True)
class SpawnedCall:
    object_id: str


class Spawn:
    """`run_build.spawn`: records each job id it was given and returns a call at once, running nothing."""

    def __init__(self) -> None:
        self.job_ids: list[JobId] = []

    def __call__(self, job_id: JobId) -> SpawnedCall:
        self.job_ids.append(job_id)
        return SpawnedCall(f"fc-{len(self.job_ids)}")


def still_running(call_id: str) -> RunnerState:
    """The watchdog's poll of a call Modal still holds: running, so no job read marks it."""
    return "running"


def hosted_settings(**env: str) -> Settings:
    return Settings.from_env({**HOSTED, **env})


def hosted_handles(tmp_path: Path) -> ModalHandles:
    """The three Dicts as plain dicts (the jobs Dict with `put`, for the build quota), the Volume mounted at `tmp_path/data`, a recording spawn and a poll that reads running."""
    return ModalHandles(
        jobs=RecordingDict(), sessions={}, ledger={}, volume=NullVolume(), root=tmp_path / "data", spawn=Spawn(), poll=still_running
    )


def make_hosted_app(
    tmp_path: Path,
    handles: ModalHandles,
    *rooms: Room,
    web_dist: Path | None = None,
    settings: Settings | None = None,
    clock: Clock | None = None,
    stages: Mapping[Stage, StageFn] | None = None,
    **options: Any,
) -> FastAPI:
    """The hosted app with `rooms` seeded as Demo rooms on the Volume; the local paths point into `tmp_path` and stay unread."""
    for room in rooms:
        seed_demo(handles, room)
    return create_app(
        settings or hosted_settings(),
        handles=handles,
        rooms_root=tmp_path / "local-rooms",
        web_dist=web_dist or tmp_path / "no-dist",
        clock=clock,
        stages=idle_stages() if stages is None else stages,
        ledger_path=tmp_path / "local-spend" / "ledger.jsonl",
        exports_root=tmp_path / "local-spend" / "exports",
        cache_root=tmp_path / "local-cache",
        **options,
    )
