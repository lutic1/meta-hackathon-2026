"""The hosted app over plain dicts and a temporary Volume directory, so no test reaches Modal (AD-17)."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from src.api.app import create_app
from src.config import Settings
from src.domain.schema import Room, Stage
from src.infra.modal import ModalHandles
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


def hosted_settings(**env: str) -> Settings:
    return Settings.from_env({**HOSTED, **env})


def hosted_handles(tmp_path: Path) -> ModalHandles:
    """The three Dicts as plain dicts (the jobs Dict with `put`, for the build quota) and the Volume mounted at `tmp_path/data`."""
    return ModalHandles(jobs=RecordingDict(), sessions={}, ledger={}, volume=NullVolume(), root=tmp_path / "data")


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
