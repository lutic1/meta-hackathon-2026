"""Story 2.1: the scripted mock answers per role and call kind, with no network (AD-5, AD-17)."""

import socket

import pytest
from pydantic import BaseModel

from src.providers.base import ChatMessage
from src.providers.mock import (
    CANNED_POLYGON,
    ChatCall,
    ImageCall,
    MockProvider,
    MockScript,
    SegmentCall,
)

ROLES = ("architect", "riddler", "dryrun", "trickster", "image")
SQUARE = [(1.0, 1.0), (9.0, 1.0), (9.0, 9.0), (1.0, 9.0)]
HELLO = [ChatMessage(role="user", content="hello")]


def _refuse_sockets(monkeypatch):
    def refuse(self, address):
        raise AssertionError(f"the mock opened a socket to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


@pytest.mark.parametrize("role", ROLES)
def test_each_role_answers_from_its_own_script(role, monkeypatch):
    _refuse_sockets(monkeypatch)
    script = MockScript(chat=[f"{role} speaks"], segment=[[SQUARE]], image=[f"mock://{role}.webp"])
    mock = MockProvider(role, script)
    reply = mock.chat(HELLO)
    assert (reply.text, reply.model, reply.raw) == (f"{role} speaks", "mock-chat-1", {"provider": "mock", "role": role, "scripted": True})
    assert mock.segment("lamp", b"jpeg") == [SQUARE]
    image = mock.generate_image("a wizard")
    assert (image.data, image.model) == (f"mock://{role}.webp", "mock-image-1")


def test_scripted_replies_come_in_order_and_a_kind_runs_out_loudly():
    mock = MockProvider("riddler", MockScript(chat=["first", "second"]))
    assert [mock.chat(HELLO).text for _ in range(2)] == ["first", "second"]
    with pytest.raises(LookupError, match="the mock riddler script has no chat reply left"):
        mock.chat(HELLO)
    with pytest.raises(LookupError, match="no segment reply left"):
        mock.segment("lamp", b"jpeg")
    with pytest.raises(LookupError, match="no image reply left"):
        mock.generate_image("a wizard")


def test_a_segment_script_entry_of_none_stands_for_no_mask():
    mock = MockProvider("architect", MockScript(segment=[None, [SQUARE, SQUARE]]))
    assert mock.segment("ghost", b"jpeg") is None
    assert mock.segment("books", b"jpeg") == [SQUARE, SQUARE]


def test_unscripted_mock_gives_canned_replies():
    mock = MockProvider("dryrun")
    reply = mock.chat([ChatMessage(role="system", content="rules"), *HELLO])
    assert reply.text == "[mock dryrun] You said: 'hello'. This is a canned response."
    assert reply.raw == {"provider": "mock", "role": "dryrun", "scripted": False}
    assert mock.segment("lamp", b"jpeg") == [CANNED_POLYGON]
    assert mock.generate_image("a red car on a road").data == "mock://image/a-red-car-on-a"


def test_chat_refuses_reasoning_effort_none_and_serves_no_reply():
    mock = MockProvider("riddler", MockScript(chat=["kept for the next call"]))
    with pytest.raises(ValueError, match="reasoning_effort 'none'"):
        mock.chat(HELLO, reasoning_effort="none")
    assert mock.calls == []
    assert mock.chat(HELLO).text == "kept for the next call"


@pytest.mark.parametrize("effort", ["minimal", "low", "medium", "high", "xhigh"])
def test_chat_accepts_every_allowed_effort(effort):
    mock = MockProvider("trickster")
    assert mock.chat(HELLO, reasoning_effort=effort).text.startswith("[mock trickster]")
    assert mock.calls[0].reasoning_effort == effort


def test_calls_are_recorded_with_their_arguments():
    class Reply(BaseModel):
        ok: bool

    mock = MockProvider("architect")
    mock.chat(HELLO, images=[b"a", b"b"], response_schema=Reply, reasoning_effort="medium", model="m")
    mock.segment("lamp", b"a")
    mock.generate_image("a wizard")
    assert mock.calls == [
        ChatCall(HELLO, [b"a", b"b"], Reply, "medium", "m"),
        SegmentCall("lamp", b"a"),
        ImageCall("a wizard"),
    ]
    assert mock.calls[0].messages is not HELLO  # a copy, so a later edit cannot rewrite the record
