"""Offline guard for every test (AD-17), and the synthetic fixture rooms every play story tests against."""

import ipaddress
import os
import socket
from pathlib import Path

import pytest

from src.domain.schema import Room
from tests.fixtures.rooms import write_fixtures

SECRET_KEYS = ("META_MODEL_API_KEY", "FAL_KEY", "OPENAI_COMPATIBLE_API_KEY", "ACCESS_CODE")
ROLES = ("ARCHITECT", "RIDDLER", "DRYRUN", "TRICKSTER", "IMAGE")
# A loopback HTTPS proxy (the cloud containers have one) would carry a request past the socket guard.
PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")

collect_ignore = ["sit"]  # the live-seam cases run only through scripts/sit.py (Story 2.9)

# Runs before any test module imports src.config, so .env cannot reach module-level Settings.
os.environ["MODEL_PROVIDER"] = "mock"
os.environ["GUIDE"] = "verbatim"  # the offline suite never resolves a Guide model (AD-5)
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
    monkeypatch.setenv("GUIDE", "verbatim")
    for role in ROLES:
        monkeypatch.setenv(f"PROVIDER_{role}", "mock")
    for key in SECRET_KEYS:
        monkeypatch.setenv(key, "")
    for key in PROXY_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(socket.socket, "connect", _guard(_real_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", _guard(_real_connect_ex))


# --- Synthetic fixture rooms (Story 1.6) -----------------------------------


@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory) -> Path:
    """Where the synthetic scenes land: pytest's tmp path, outside every git-ignored folder."""
    return tmp_path_factory.mktemp("fixtures")


@pytest.fixture(scope="session")
def fixture_rooms(fixture_dir: Path) -> tuple[Room, Room]:
    return write_fixtures(fixture_dir)


@pytest.fixture
def four_lock_room(fixture_rooms: tuple[Room, Room]) -> Room:
    """A fresh deep copy per test: code, order, use_on and find locks over six scenes."""
    return fixture_rooms[0].model_copy(deep=True)


@pytest.fixture
def code_and_find_room(fixture_rooms: tuple[Room, Room]) -> Room:
    """A fresh deep copy per test: code and find locks only (cut 6, video v0)."""
    return fixture_rooms[1].model_copy(deep=True)
