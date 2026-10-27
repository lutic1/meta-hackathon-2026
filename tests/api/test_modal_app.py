"""Stories 7.2, 7.8 and 7.20: `src/api/modal_app.py` defines the hosted app and its functions offline (AD-7, AD-9, AD-14).

The module is reloaded with spies on the Modal decorators, so each test
sees the arguments the module passes; no Modal service is reached, no
token is read and no handle is hydrated.
"""

import importlib
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import modal
import modal.exception
import pytest
from fastapi.testclient import TestClient

from src.api import modal_app, wiring
from src.config import Settings
from src.council.trickster import RECORDED_PROPOSALS
from src.domain.ledger import LedgerEntry
from src.domain.schema import IdleTickEvent
from src.infra.modal import (
    JOBS_DICT,
    LEDGER_DICT,
    MOUNT,
    SESSIONS_DICT,
    VOLUME,
    DictLedgerStore,
    DictSessionStore,
    snapshot_path,
)
from src.providers.spend import new_call_id
from tests.api.hosted import hosted_handles
from tests.infra.test_local import JOB_A as JOB
from tests.infra.test_modal_retention import HOUR_MS, sess_at

MODAL_ENV = ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "MODAL_PROFILE", "MODAL_ENVIRONMENT", "MODAL_CONFIG_PATH")


class Spies:
    """The arguments of every `App.function`, `modal.concurrent` and `Image.env` call made while the module loads.

    `made[i]` is the Function the i-th `App.function` decorator returned.
    """

    def __init__(self) -> None:
        self.function: list[dict[str, Any]] = []
        self.made: list[Any] = []
        self.concurrent: list[dict[str, Any]] = []
        self.env: list[dict[str, Any]] = []
        self.local_dirs: list[tuple[str, str]] = []


@pytest.fixture
def spies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Spies]:
    """Spy on the decorators, drop every Modal credential and point `HOME` at an empty directory."""
    for key in MODAL_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    found = Spies()
    function, concurrent, env, add_local_dir = modal.App.function, modal.concurrent, modal.Image.env, modal.Image.add_local_dir

    def spy_function(self: modal.App, **kwargs: Any) -> Any:
        found.function.append(kwargs)
        decorator = function(self, **kwargs)

        def record(f: Any) -> Any:
            found.made.append(decorator(f))
            return found.made[-1]

        return record

    def spy_concurrent(**kwargs: Any) -> Any:
        found.concurrent.append(kwargs)
        return concurrent(**kwargs)

    def spy_env(self: modal.Image, vars: dict[str, Any]) -> Any:
        found.env.append(vars)
        return env(self, vars)

    def spy_add_local_dir(self: modal.Image, local_path: str, remote_path: str) -> Any:
        found.local_dirs.append((local_path, remote_path))
        return add_local_dir(self, local_path, remote_path)

    monkeypatch.setattr(modal.App, "function", spy_function)
    monkeypatch.setattr(modal, "concurrent", spy_concurrent)
    monkeypatch.setattr(modal.Image, "env", spy_env)
    monkeypatch.setattr(modal.Image, "add_local_dir", spy_add_local_dir)
    yield found
    monkeypatch.undo()
    importlib.reload(modal_app)


def load() -> Any:
    return importlib.reload(modal_app)


def functions(module: Any, spies: Spies) -> dict[str, dict[str, Any]]:
    """The `App.function` arguments of each of the module's functions, by name, in definition order."""
    names = {id(getattr(module, name)): name for name in ("web", "run_build", "ledger_export", "session_sweep")}
    return {names[id(made)]: kwargs for made, kwargs in zip(spies.made, spies.function, strict=True)}


def test_web_is_one_container_of_20_concurrent_inputs_with_min_containers_from_settings(spies: Spies):
    module = load()
    # no GPU, no extra Secret or Volume, and no timeout: web keeps Modal's default
    assert functions(module, spies)["web"] == {"min_containers": 0, "max_containers": 1}
    assert spies.concurrent == [{"max_inputs": 20}]
    assert module.settings.min_containers == 0
    assert module.web._is_web_endpoint()


def test_min_containers_is_read_through_settings_at_deploy(spies: Spies, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MIN_CONTAINERS", "1")
    module = load()
    assert functions(module, spies)["web"] == {"min_containers": 1, "max_containers": 1}


def test_the_app_defines_web_run_build_ledger_export_and_session_sweep(spies: Spies):
    module = load()
    found = functions(module, spies)
    assert list(found) == ["web", "run_build", "ledger_export", "session_sweep"]
    assert found["run_build"] == {"timeout": 900, "max_containers": 1}  # one runner at a time, no retries (AD-13)
    assert list(found["ledger_export"]) == ["schedule"]
    cron = found["ledger_export"]["schedule"]
    assert isinstance(cron, modal.Cron)
    assert (cron.proto_message.cron.cron_string, cron.proto_message.cron.timezone) == ("0 6 * * *", "America/New_York")
    assert ZoneInfo(module.SNAPSHOT_TZ).key == "America/New_York"
    assert not module.run_build._is_web_endpoint() and not module.ledger_export._is_web_endpoint()


def test_run_build_and_the_cron_functions_carry_the_keyframe_secret_and_the_volume():
    for function in (modal_app.run_build, modal_app.ledger_export, modal_app.session_sweep):
        spec = function._spec_
        assert [repr(secret) for secret in spec.secrets] == ["modal.Secret.from_name('keyframe')"]
        assert {path: repr(volume) for path, volume in spec.volumes.items()} == {"/data": "modal.Volume.from_name('keyframe-data')"}
        assert spec.gpus is None


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


def test_the_image_carries_proposals_beside_src_when_the_folder_exists_so_a_scripted_trickster_has_a_source(
    spies: Spies, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """`wiring.PROPOSALS_ROOT` is the parent of `src/`, `/root` in the container, so `proposals/` lands at `/root/proposals` (FR-31, AD-15)."""
    monkeypatch.chdir(tmp_path)
    load()
    assert spies.local_dirs == [("web/dist", modal_app.WEB_DIST)]  # not committed yet: the deploy must not fail on it
    (tmp_path / RECORDED_PROPOSALS).parent.mkdir()
    spies.local_dirs.clear()
    load()
    assert spies.local_dirs == [("web/dist", modal_app.WEB_DIST), ("proposals", modal_app.PROPOSALS_DIR)]
    assert Path(modal_app.PROPOSALS_DIR) == Path(modal_app.WEB_DIST).parents[1] / RECORDED_PROPOSALS.parent


def test_importing_the_module_contacts_no_modal_service_and_hydrates_no_handle(spies: Spies):
    module = load()  # the offline guard blocks every non-loopback connect
    handles = module.handles()
    assert (handles.jobs, handles.sessions, handles.ledger, handles.volume) == (module.jobs, module.sessions, module.ledger, module.volume)
    assert handles.root == MOUNT
    assert callable(handles.spawn) and handles.poll is module.poll_call
    functions_ = (module.web, module.run_build, module.ledger_export, module.session_sweep)
    for handle in (module.secret, module.volume, module.jobs, module.sessions, module.ledger, *functions_):
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


# --- run_build, ledger_export and the call poll -----------------------------------------


def test_run_build_runs_the_job_over_the_hosted_handles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`run_build`'s body, called locally: the runner body in wiring, given the container's settings, the handles and the job id."""
    hosted = Settings.from_env({"MODE": "hosted", "MODEL_PROVIDER": "mock"})
    handles = hosted_handles(tmp_path)
    ran: list[tuple[object, ...]] = []
    monkeypatch.setattr(modal_app, "settings", hosted)
    monkeypatch.setattr(modal_app, "handles", lambda: handles)
    monkeypatch.setattr(wiring, "run_hosted_build", lambda *args: ran.append(args))
    with pytest.warns(UserWarning, match="executing locally"):
        assert modal_app.run_build.local(JOB) is None
    assert ran == [(hosted, handles, JOB)]


def test_ledger_export_writes_todays_snapshot_in_new_york(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    handles = hosted_handles(tmp_path)
    entry = LedgerEntry(call_id=new_call_id(), kind="vision", status="settled", usd=0.025)
    DictLedgerStore(handles.ledger).append(entry)
    monkeypatch.setattr(modal_app, "handles", lambda: handles)
    with pytest.warns(UserWarning, match="executing locally"):
        modal_app.ledger_export.local()
    day = datetime.now(ZoneInfo("America/New_York")).date()
    lines = (handles.root / snapshot_path(day)).read_text().splitlines()
    assert [LedgerEntry.model_validate_json(line) for line in lines] == [entry]


# --- session_sweep (Story 7.20) -------------------------------------------------------


def test_session_sweep_is_an_hourly_cron_with_no_web_endpoint(spies: Spies):
    module = load()
    found = functions(module, spies)["session_sweep"]
    assert list(found) == ["schedule"]  # a schedule and nothing else: no request, no retries, no GPU
    cron = found["schedule"]
    assert isinstance(cron, modal.Cron)
    minute, *rest = cron.proto_message.cron.cron_string.split()
    assert minute.isdigit() and 0 <= int(minute) < 60 and rest == ["*", "*", "*", "*"]  # once in every hour
    assert not module.session_sweep._is_web_endpoint()


def test_session_sweep_runs_sweep_sessions_over_the_hosted_handles_now(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`session_sweep`'s body, called locally: `sweep_sessions` over the handles, at the current UTC time."""
    handles = hosted_handles(tmp_path)
    swept: list[tuple[object, datetime]] = []
    monkeypatch.setattr(modal_app, "handles", lambda: handles)
    monkeypatch.setattr(modal_app, "sweep_sessions", lambda given, *, now: swept.append((given, now)) or [])
    before = datetime.now(UTC)
    with pytest.warns(UserWarning, match="executing locally"):
        assert modal_app.session_sweep.local() is None
    [(given, now)] = swept
    assert given is handles and now.tzinfo is not None and before <= now <= datetime.now(UTC)


def test_session_sweep_deletes_a_session_a_day_past_its_last_event_and_keeps_a_recent_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    handles = hosted_handles(tmp_path)
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    old, recent = sess_at(now_ms - 25 * HOUR_MS), sess_at(now_ms - HOUR_MS)
    for session_id in (old, recent):
        DictSessionStore(handles.sessions).append(session_id, IdleTickEvent(type="idle_tick", t_ms=0))
    monkeypatch.setattr(modal_app, "handles", lambda: handles)
    with pytest.warns(UserWarning, match="executing locally"):
        modal_app.session_sweep.local()
    assert list(handles.sessions) == [recent]


class Call:
    """A `FunctionCall` whose `get(timeout=0)` raises `raises`, or returns."""

    def __init__(self, raises: BaseException | None) -> None:
        self.raises = raises
        self.timeouts: list[float] = []

    def get(self, *, timeout: float) -> None:
        self.timeouts.append(timeout)
        if self.raises is not None:
            raise self.raises


OUTCOMES: dict[str, tuple[BaseException | None, str]] = {
    "no output yet": (TimeoutError(), "running"),
    "past the runner's timeout": (modal.exception.FunctionTimeoutError("timed out"), "timed_out"),
    "an expired result": (modal.exception.OutputExpiredError("expired"), "expired"),
    **{f"a failed poll ({error.__name__})": (error("poll failed"), "unknown") for error in modal_app.POLL_ERRORS},
    "a runner that raised": (ValueError("boom"), "crashed"),
    "a runner that returned": (None, "finished"),
}


@pytest.mark.parametrize(("raises", "state"), OUTCOMES.values(), ids=OUTCOMES.keys())
def test_the_call_poll_reads_each_modal_outcome_without_waiting(monkeypatch: pytest.MonkeyPatch, raises: BaseException | None, state: str):
    calls: dict[str, Call] = {}

    def from_id(call_id: str) -> Call:
        calls[call_id] = Call(raises)
        return calls[call_id]

    monkeypatch.setattr(modal.FunctionCall, "from_id", from_id)
    assert modal_app.poll_call("fc-1") == state
    assert list(calls) == ["fc-1"] and calls["fc-1"].timeouts == [0]


def test_modals_timeout_error_is_not_the_builtin_one():
    """`modal.exception.TimeoutError` is the base of the timed out and expired outcomes, never "still running"."""
    assert not issubclass(modal.exception.TimeoutError, TimeoutError)
    assert issubclass(modal.exception.FunctionTimeoutError, modal.exception.TimeoutError)
