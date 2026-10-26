"""Offline guard for every test (AD-17)."""

import ipaddress
import os
import socket

import pytest

SECRET_KEYS = ("META_MODEL_API_KEY", "FAL_KEY", "OPENAI_COMPATIBLE_API_KEY", "ACCESS_CODE")
ROLES = ("ARCHITECT", "RIDDLER", "DRYRUN", "TRICKSTER", "IMAGE")
# A loopback HTTPS proxy (the cloud containers have one) would carry a request past the socket guard.
PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")

# Runs before any test module imports src.config, so .env cannot reach module-level Settings.
os.environ["MODEL_PROVIDER"] = "mock"
for _role in ROLES:
    os.environ[f"PROVIDER_{_role}"] = "mock"
for _key in SECRET_KEYS:
    os.environ[_key] = ""  # set but blank: load_dotenv() keeps it, Settings reads None

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex


def _is_loopback(address) -> bool:
    if not isinstance(address, tuple):  # AF_UNIX path
        return True
    host = address[0]
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _guard(real):
    def connect(self, address):
        if not _is_loopback(address):
            raise OSError(f"tests run offline (AD-17); blocked connect to {address!r}")
        return real(self, address)
    return connect


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    for role in ROLES:
        monkeypatch.setenv(f"PROVIDER_{role}", "mock")
    for key in SECRET_KEYS:
        monkeypatch.setenv(key, "")
    for key in PROXY_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(socket.socket, "connect", _guard(_real_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", _guard(_real_connect_ex))
