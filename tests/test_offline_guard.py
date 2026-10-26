"""AD-17: the conftest guard refuses every non-loopback socket and forces the mock provider."""

import os
import socket

import httpx
import pytest


def test_non_loopback_connect_is_refused():
    with socket.socket() as s, pytest.raises(OSError, match=r"tests run offline \(AD-17\)"):
        s.connect(("203.0.113.1", 443))


def test_connect_ex_is_guarded_too():
    with socket.socket() as s, pytest.raises(OSError, match="tests run offline"):
        s.connect_ex(("example.com", 80))


def test_loopback_is_allowed():
    with socket.socket() as s:
        s.settimeout(0.2)
        assert s.connect_ex(("127.0.0.1", 1)) != 0  # refused by the OS, not by the guard


def test_mock_transport_opens_no_socket():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True})))
    assert client.get("https://api.meta.ai/v1/x").json() == {"ok": True}


def test_httpx_live_call_is_refused():
    with pytest.raises(httpx.ConnectError, match="tests run offline"):
        httpx.get("https://api.meta.ai/v1/x", timeout=1)


def test_mock_provider_and_blank_secrets_are_forced():
    assert os.environ["MODEL_PROVIDER"] == "mock"
    assert all(os.environ[f"PROVIDER_{r}"] == "mock" for r in ("ARCHITECT", "RIDDLER", "DRYRUN", "TRICKSTER", "IMAGE"))
    assert all(os.environ[k] == "" for k in ("MODEL_API_KEY", "FAL_KEY", "OPENAI_COMPATIBLE_API_KEY", "ACCESS_CODE"))
