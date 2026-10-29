"""Decisions 61 and 63: paid providers are built on their role's first call, so a keyless checkout starts and plays.

A fresh clone with no key serves the stored and fixture Rooms and sample play
with no paid adapter constructed; a missing credential blocks only a Build
that asks for it, failing that Build by name and reserving nothing, and never
falls back to the mock. A live Trickster window's ledger entry names its
session (AD-6, AD-16).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.wiring import artifact_store, ledger_store
from src.config import Settings
from src.council.trickster import LiveSource
from src.domain.schema import Room
from src.infra.local import CACHE_ROOT, EXPORTS_ROOT, LEDGER_PATH
from src.providers.meta_api import MetaModelProvider
from src.providers.openai_compatible import OpenAICompatibleProvider
from tests.api.test_app import fixture_proposals, store_room
from tests.api.test_builds import post, wait_terminal
from tests.api.test_live_trickster_route import Host, chat, meta
from tests.api.test_sessions import Ticker, click, start
from tests.api.test_sessions import post as post_event
from tests.api.test_trickster_route import always, app_client, open_window, trickster
from tests.council.test_trickster_live import FIRST
from tests.pipeline.uploads import make_uploads


def keyless_app(tmp_path: Path, env: dict[str, str], *rooms: Room, **options: Any) -> TestClient:
    """The app as a fresh clone runs it: no key in `env`, the ledger, its exports and the cache under `tmp_path`."""
    root = tmp_path / "rooms"
    for room in rooms:
        store_room(artifact_store(root), room)
    app = create_app(
        Settings.from_env({"GUIDE": "verbatim", **env}),
        rooms_root=root,
        web_dist=tmp_path / "no-dist",
        ledger_path=tmp_path / LEDGER_PATH,
        exports_root=tmp_path / EXPORTS_ROOT,
        cache_root=tmp_path / CACHE_ROOT,
        proposals_dir=fixture_proposals(tmp_path),
        **options,
    )
    return TestClient(app)


@pytest.mark.parametrize("env", [
    {"MODEL_PROVIDER": "meta"},
    {"MODEL_PROVIDER": "meta", "DEMO_TRICKSTER": "scripted"},
    {"MODEL_PROVIDER": "openai_compatible"},
    {"MODEL_PROVIDER": "mock", "PROVIDER_ARCHITECT": "openai_compatible", "PROVIDER_TRICKSTER": "meta"},
], ids=["meta", "meta-scripted", "openai_compatible-unset", "one-role-unset"])
def test_a_keyless_checkout_starts_and_plays_a_stored_room_with_no_paid_adapter_built(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code_and_find_room: Room, env: dict[str, str]
):
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a paid adapter was constructed for play")

    monkeypatch.setattr(MetaModelProvider, "__init__", refuse)
    monkeypatch.setattr(OpenAICompatibleProvider, "__init__", refuse)
    with keyless_app(tmp_path, env, code_and_find_room) as client:
        assert [row["room_id"] for row in client.get("/api/rooms").json()] in ([], [code_and_find_room.id])
        assert client.get(f"/api/rooms/{code_and_find_room.id}").status_code == 200
        session_id = start(client, code_and_find_room)
        post_event(client, session_id, click("key"))
        assert client.get(f"/api/sessions/{session_id}/room").status_code == 200
        assert client.get(f"/api/sessions/{session_id}/result").status_code == 200


def test_a_missing_fallback_credential_fails_only_the_build_that_asks_for_it_by_name_and_reserves_nothing(tmp_path: Path):
    env = {"MODEL_PROVIDER": "mock", "PROVIDER_ARCHITECT": "openai_compatible"}
    with keyless_app(tmp_path, env) as client:
        assert client.get("/api/meta").status_code == 200
        posted = post(client, make_uploads(6))
        assert posted.status_code == 202, posted.text
        final = wait_terminal(client, posted.json()["id"])
    assert (final["status"], final["stage"]) == ("failed", "architect")
    assert "OPENAI_COMPATIBLE_BASE_URL is not set" in final["error"]["message"]
    assert final["calls"] == [] and ledger_store(tmp_path / LEDGER_PATH).entries() == []


def test_a_live_trickster_windows_ledger_entry_names_its_session(tmp_path: Path, four_lock_room: Room):
    ticker = Ticker()
    provider = meta(Host(httpx.Response(200, json=chat(FIRST))))
    client = app_client(tmp_path, ticker, four_lock_room, env={"DEMO_TRICKSTER": "live"}, trickster=always(LiveSource(provider)))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    assert trickster(client, session_id)["cards"][0]["accepted"]
    rows = provider._calls._ledger._store.rows
    assert [(entry.kind, entry.status, entry.session_id) for entry in rows] == [
        ("trickster", "reserved", session_id), ("trickster", "settled", session_id),
    ]
