"""Story 7.2: `src/api/modal_app.py` defines the hosted app offline (AD-9, AD-14).

The module is reloaded with spies on the Modal decorators, so each test
sees the arguments the module passes; no Modal service is reached, no
token is read and no handle is hydrated.
"""

import importlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import modal
import pytest
from fastapi.testclient import TestClient

from src.api import modal_app
from src.config import Settings
from src.infra.modal import JOBS_DICT, LEDGER_DICT, MOUNT, SESSIONS_DICT, VOLUME
from tests.api.hosted import hosted_handles

MODAL_ENV = ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "MODAL_PROFILE", "MODAL_ENVIRONMENT", "MODAL_CONFIG_PATH")


class Spies:
    """The arguments of every `App.function`, `modal.concurrent` and `Image.env` call made while the module loads."""

    def __init__(self) -> None:
        self.function: list[dict[str, Any]] = []
        self.concurrent: list[dict[str, Any]] = []
        self.env: list[dict[str, Any]] = []


@pytest.fixture
def spies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Spies]:
    """Spy on the decorators, drop every Modal credential and point `HOME` at an empty directory."""
    for key in MODAL_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    found = Spies()
    function, concurrent, env = modal.App.function, modal.concurrent, modal.Image.env

    def spy_function(self: modal.App, **kwargs: Any) -> Any:
        found.function.append(kwargs)
        return function(self, **kwargs)

    def spy_concurrent(**kwargs: Any) -> Any:
        found.concurrent.append(kwargs)
        return concurrent(**kwargs)

    def spy_env(self: modal.Image, vars: dict[str, Any]) -> Any:
        found.env.append(vars)
        return env(self, vars)

    monkeypatch.setattr(modal.App, "function", spy_function)
    monkeypatch.setattr(modal, "concurrent", spy_concurrent)
    monkeypatch.setattr(modal.Image, "env", spy_env)
    yield found
    monkeypatch.undo()
    importlib.reload(modal_app)


def load() -> Any:
    return importlib.reload(modal_app)


def test_web_is_one_container_of_20_concurrent_inputs_with_min_containers_from_settings(spies: Spies):
    module = load()
    assert spies.function == [{"min_containers": 0, "max_containers": 1}]  # no GPU, no extra Secret or Volume
    assert spies.concurrent == [{"max_inputs": 20}]
    assert module.settings.min_containers == 0
    assert module.web._is_web_endpoint()


def test_min_containers_is_read_through_settings_at_deploy(spies: Spies, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MIN_CONTAINERS", "1")
    load()
    assert spies.function == [{"min_containers": 1, "max_containers": 1}]


def test_the_decorators_stack_function_over_concurrent_over_asgi_app():
    source = Path(modal_app.__file__).read_text()
    stack = source[source.index("@app.function(") : source.index("def web(")].split()
    assert stack == [
        "@app.function(min_containers=settings.min_containers,", "max_containers=1)",
        "@modal.concurrent(max_inputs=20)",
        "@modal.asgi_app()",
    ]


def test_the_secret_and_the_volume_are_attached_and_no_gpu_is_requested():
    spec = modal_app.web._spec_
    assert [repr(secret) for secret in spec.secrets] == ["modal.Secret.from_name('keyframe')"]
    assert {path: repr(volume) for path, volume in spec.volumes.items()} == {"/data": "modal.Volume.from_name('keyframe-data')"}
    assert spec.gpus is None
    assert modal_app.app.name == "keyframe" and MOUNT.as_posix() == "/data"


def test_the_image_runs_hosted_with_the_verbatim_guide(spies: Spies):
    load()
    assert spies.env == [{"MODE": "hosted", "GUIDE": "verbatim"}]
    settings = Settings.from_env({**spies.env[0], "MODEL_PROVIDER": "mock"})
    assert (settings.mode, settings.guide, settings.spend_cap_usd) == ("hosted", "verbatim", 20)


def test_importing_the_module_contacts_no_modal_service_and_hydrates_no_handle(spies: Spies):
    module = load()  # the offline guard blocks every non-loopback connect
    handles = module.handles()
    assert (handles.jobs, handles.sessions, handles.ledger, handles.volume) == (module.jobs, module.sessions, module.ledger, module.volume)
    assert handles.root == MOUNT
    for handle in (module.secret, module.volume, module.jobs, module.sessions, module.ledger, module.web):
        assert not handle._is_hydrated
    assert [repr(d) for d in (module.jobs, module.sessions, module.ledger)] == [
        f"modal.Dict.from_name('{name}')" for name in (JOBS_DICT, SESSIONS_DICT, LEDGER_DICT)
    ]
    assert repr(module.volume) == f"modal.Volume.from_name('{VOLUME}')"


def test_web_returns_the_app_over_the_hosted_adapters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`web`'s body, called locally with stand-in handles under the container's settings."""
    hosted = Settings.from_env({"MODE": "hosted", "MODEL_PROVIDER": "mock"})
    monkeypatch.setattr(modal_app, "settings", hosted)
    monkeypatch.setattr(modal_app, "handles", lambda: hosted_handles(tmp_path))
    with pytest.warns(UserWarning, match="executing locally"):
        app = modal_app.web.local()
    client = TestClient(app)
    assert client.get("/api/meta").json()["mode"] == "hosted"
    assert client.get("/api/profile/dev").status_code == 404
