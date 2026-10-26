"""Story 2.1: recorded fixtures replay into the port types and never reach the network (AD-17)."""

import re
import socket

import pytest

from src.providers.base import ChatMessage, ChatResponse, ImageResponse
from src.providers.cache import GuardedCalls
from src.providers.meta_api import MetaModelProvider
from src.providers.spend import SpendLedger
from tests.providers.replay import FIXTURES, Fixture, MissingFixture, load, transport
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

FILES = sorted(path for path in FIXTURES.rglob("*") if path.is_file())


def _refuse_sockets(monkeypatch):
    def refuse(self, address):
        raise AssertionError(f"the replay opened a socket to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


def _provider(name: str) -> MetaModelProvider:
    calls = GuardedCalls(MemoryCache(), SpendLedger(MemoryLedgerStore(), cap_usd=60.0), host="api.meta.ai")
    return MetaModelProvider("test-key", calls=calls, chat_kind="vision", budget_s=15.0, transport=transport(name))


def test_chat_fixture_replays_into_a_chat_response(monkeypatch):
    _refuse_sockets(monkeypatch)
    name = "muse-spark-1.3/chat-three-objects"
    response = _provider(name).chat([ChatMessage(role="user", content="What do you see?")])
    assert isinstance(response, ChatResponse)
    assert response.text == "A brass lamp, a blue mug and a red book."
    assert response.model == "muse-spark-1.3"
    assert response.usage["total_tokens"] == 1470
    assert response.raw == load(name).body


def test_image_fixture_replays_into_an_image_response(monkeypatch):
    _refuse_sockets(monkeypatch)
    name = "muse-image-1.0/portrait-riddler"
    image = _provider(name).generate_image("a riddler wizard")
    assert isinstance(image, ImageResponse)
    assert image.data.startswith("UklGR")  # a webp, as the API returns
    assert image.model == "muse-image-1.0"
    assert image.raw == load(name).body


def test_missing_fixture_is_named_and_never_reaches_the_network(monkeypatch):
    _refuse_sockets(monkeypatch)
    expected = FIXTURES / "muse-spark-1.3" / "not-recorded.json"
    with pytest.raises(MissingFixture, match=re.escape(f"no recorded fixture 'muse-spark-1.3/not-recorded' at {expected}")):
        transport("muse-spark-1.3/not-recorded")


def test_a_sample_fixture_exists_per_tier_1_response_type():
    assert {path.parent.name for path in FILES} >= {"muse-spark-1.3", "sam-3.1", "muse-image-1.0"}


@pytest.mark.parametrize("path", FILES, ids=[str(path.relative_to(FIXTURES)) for path in FILES])
def test_every_fixture_stores_one_response_only(path):
    assert path.suffix == ".json" and path.parent.parent == FIXTURES, "fixtures live at <model>/<name>.json"
    raw = path.read_bytes()
    assert not raw.startswith(b"\xff\xd8\xff") and b"data:image" not in raw, "no photo or input image in a fixture"
    fixture = Fixture.model_validate_json(raw)  # extra keys (a request, a prompt) are refused
    assert fixture.model == path.parent.name
