"""Story 3.6: play never paints; only `scripts/portraits.py` calls `generate_image` (FR-23, CAP-7, AD-6)."""

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from src.api import wiring
from src.api.app import create_app
from src.api.wiring import artifact_store
from src.config import Settings
from src.domain.schema import Room
from src.infra.local import CACHE_ROOT, EXPORTS_ROOT, LEDGER_PATH
from src.providers.mock import ImageCall, MockProvider
from tests.api.test_app import make_app, store_room
from tests.api.test_sessions import Ticker, click, play_to_the_exit, post, start

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
WEB = (REPO / "web/src", REPO / "web/types", REPO / "web/index.html")
IMAGE_REQUESTS = ("generate_image", "images/generations", "generateImage")


def test_a_full_play_session_makes_no_image_call(tmp_path: Path, code_and_find_room: Room, monkeypatch):
    providers: dict[str, MockProvider] = {}
    model_providers = wiring.model_providers

    def recording(settings, cache, ledger):
        providers.update(model_providers(settings, cache, ledger))
        return providers

    monkeypatch.setattr(wiring, "model_providers", recording)
    root = tmp_path / "rooms"
    store_room(artifact_store(root), code_and_find_room)
    ticker = Ticker()
    app = create_app(
        Settings.from_env(), rooms_root=root, web_dist=tmp_path / "no-dist", clock=ticker,
        ledger_path=tmp_path / LEDGER_PATH, exports_root=tmp_path / EXPORTS_ROOT, cache_root=tmp_path / CACHE_ROOT,
    )

    with TestClient(app) as client:
        session_id = start(client, code_and_find_room)
        post(client, session_id, click("key"))
        post(client, session_id, {"type": "hint_request"})
        play_to_the_exit(client, session_id, ticker)
        assert client.get(f"/api/sessions/{session_id}").status_code == 200
        assert client.get(f"/api/sessions/{session_id}/result").status_code == 200

    assert set(providers) == {"architect", "riddler", "dryrun", "trickster", "image"}
    assert all(type(p) is MockProvider for p in providers.values())
    assert [call for p in providers.values() for call in p.calls if isinstance(call, ImageCall)] == []


def _mentions_generate_image(path: Path) -> bool:
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Attribute) and node.attr == "generate_image":
            return True
        if isinstance(node, ast.Name) and node.id == "generate_image":
            return True
    return False


def test_no_module_outside_the_providers_reaches_generate_image():
    callers = [str(p.relative_to(REPO)) for p in sorted(SRC.rglob("*.py")) if _mentions_generate_image(p)]
    assert all(path.startswith("src/providers/") for path in callers), callers


def test_no_route_starts_image_generation(tmp_path: Path):
    paths = list(make_app(tmp_path).openapi()["paths"])
    assert "/api/sessions/{session_id}/events" in paths
    assert not [path for path in paths if "portrait" in path or "image" in path or "generat" in path], paths
    assert not [p.name for p in sorted((SRC / "api").glob("*.py")) if _mentions_generate_image(p)]


def test_no_web_module_requests_an_image():
    paths = [p for root in WEB for p in ([root] if root.is_file() else sorted(root.rglob("*"))) if p.is_file()]
    assert paths
    found = [(str(p.relative_to(REPO)), word) for p in paths for word in IMAGE_REQUESTS if word in p.read_text()]
    assert found == []
