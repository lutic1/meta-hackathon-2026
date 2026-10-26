"""Offline self-check for the keyframe-modal skill. No network, no Modal token.

Asserts the pinned modal version, the signatures the skill cites, that the
Keyframe app shape (ASGI web function, spawned runner, Cron export, Dict,
Volume and Secret handles) constructs lazily with network access blocked,
that the 1.0 renames fail loudly, and how FunctionCall.get(timeout=0)
reports each runner outcome at this version.

Sections 5 and 6 execute the src/infra and src/api code blocks of
references/hosted-code.md, so the documented code is the code tested.
Section 5 drives runner_state through modal's private
_Invocation.poll_function and modal_proto messages; those imports are stable
only at the pinned version, so expect to update it on any modal upgrade.
Section 6 runs the spine's hosted rules (AD-7 to AD-9) on in-memory fakes:
the AD-9 names, the call:<job_id> key, the 20 quota slots, the ORPHAN_S and
DEADLINE_S backstops, 202 while queued or running, and the session sweep.

    uv run --no-project --with modal==1.6.2 \
        python .claude/skills/keyframe-modal/scripts/selfcheck.py
"""

from __future__ import annotations

import asyncio
import builtins
import dataclasses
import inspect
import re
import socket
import tempfile
import warnings
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

PIN = "1.6.2"
HOSTED_CODE = Path(__file__).resolve().parents[1] / "references" / "hosted-code.md"


def _no_network(*_args, **_kwargs):
    raise RuntimeError("selfcheck must not touch the network")


socket.socket.connect = _no_network
socket.create_connection = _no_network

import modal  # noqa: E402
import modal.exception as mexc  # noqa: E402


def check(label: str, ok: bool) -> None:
    if not ok:
        raise SystemExit(f"FAIL: {label}")
    print(f"ok   {label}")


def raises(fn, exc: type[BaseException], text: str = "") -> bool:
    try:
        fn()
    except exc as e:
        return text in str(e)
    return False


def params(obj) -> dict[str, inspect.Parameter]:
    return dict(inspect.signature(obj).parameters)


# 1. Version
check(f"modal {PIN} installed", version("modal") == PIN == modal.__version__)

# 2. Signatures the skill cites
fn_params = params(modal.App.function)
check("App.function takes timeout (default 300), min_containers, max_containers, scaledown_window, "
      "secrets, volumes, schedule",
      fn_params["timeout"].default == 300
      and {"min_containers", "max_containers", "scaledown_window", "secrets", "volumes", "schedule"} <= fn_params.keys())
check("App() takes image, secrets, volumes", {"image", "secrets", "volumes"} <= params(modal.App).keys())
check("modal.concurrent(*, max_inputs, target_inputs)", {"max_inputs", "target_inputs"} == params(modal.concurrent).keys())
check("modal.asgi_app(*, label, custom_domains, requires_proxy_auth)",
      {"label", "custom_domains", "requires_proxy_auth"} == params(modal.asgi_app).keys())
check("Function.spawn(*args, **kwargs) has no timeout of its own",
      [p.kind for n, p in params(modal.Function.spawn).items() if n != "self"]
      == [inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD])
check("FunctionCall.from_id(function_call_id) and get(timeout)",
      "function_call_id" in params(modal.FunctionCall.from_id) and "timeout" in params(modal.FunctionCall.get))
check("Dict.from_name(name, create_if_missing=False)", params(modal.Dict.from_name)["create_if_missing"].default is False)
check("Volume.from_name(name, create_if_missing=False)", params(modal.Volume.from_name)["create_if_missing"].default is False)
check("Volume.commit() and Volume.reload() take no arguments",
      list(params(modal.Volume.commit)) == ["self"] == list(params(modal.Volume.reload)))
check("Cron(cron_string, timezone='UTC')", params(modal.Cron)["timezone"].default == "UTC")
check("Secret.from_name(name, required_keys=[])", "required_keys" in params(modal.Secret.from_name))
check("Function.autoscaler namespace exists (update_autoscaler is deprecated in 1.6.2)",
      isinstance(inspect.getattr_static(modal.Function, "autoscaler"), property))

# 3. The Keyframe app shape constructs offline, with deprecation warnings as errors
with warnings.catch_warnings():
    warnings.simplefilter("error")
    image = (modal.Image.debian_slim(python_version="3.13")
             .uv_sync(uv_version="0.11.32", extra_options="--no-dev")
             .env({"MODE": "hosted", "GUIDE": "verbatim"}))
    secret = modal.Secret.from_name("keyframe", required_keys=["MODEL_API_KEY", "FAL_KEY", "ACCESS_CODE"])
    volume = modal.Volume.from_name("keyframe-data", create_if_missing=True)
    jobs = modal.Dict.from_name("keyframe-jobs", create_if_missing=True)
    sessions = modal.Dict.from_name("keyframe-sessions", create_if_missing=True)
    ledger = modal.Dict.from_name("keyframe-ledger", create_if_missing=True)
    app = modal.App("keyframe", image=image, secrets=[secret], volumes={"/data": volume})

    @app.function(timeout=900, serialized=True)
    def run_build(job_id: str) -> None: ...

    @app.function(min_containers=0, max_containers=1, serialized=True)
    @modal.concurrent(max_inputs=20)
    @modal.asgi_app()
    def web():
        from fastapi import FastAPI  # only in the image; not needed locally

        return FastAPI()

    @app.function(schedule=modal.Cron("0 6 * * *", timezone="America/New_York"), serialized=True)
    def ledger_export() -> None: ...

    @app.function(schedule=modal.Cron("17 * * * *"), serialized=True)
    def session_sweep() -> None: ...

check("web is an ASGI web function; runner, export and sweep are plain functions",
      web._is_web_endpoint()
      and not any(f._is_web_endpoint() for f in (run_build, ledger_export, session_sweep)))
check("Dicts, Volume, Secret and Functions stay unhydrated (lazy, no credentials)",
      not any(o._is_hydrated for o in (jobs, sessions, ledger, volume, secret,
                                       web, run_build, ledger_export, session_sweep)))
check("Cron accepts any timezone string offline, so check the IANA name here",
      modal.Cron("0 6 * * *", timezone="Not/AZone") is not None and ZoneInfo("America/New_York").key == "America/New_York")
check(".spawn() outside a running or deployed app raises ExecutionError (live-only)",
      raises(run_build.spawn, mexc.ExecutionError, "not been hydrated"))

# 4. Decorator rules and 1.0 renames fail loudly
scratch = modal.App("selfcheck")


def asgi_above_function():
    @modal.asgi_app()
    @scratch.function(serialized=True)
    def w(): ...


def concurrent_without_max():
    @scratch.function(serialized=True)
    @modal.concurrent()
    @modal.asgi_app()
    def w(): ...


def asgi_with_parameter():
    @scratch.function(serialized=True)
    @modal.asgi_app()
    def w(request): ...


check("@modal.asgi_app above @app.function raises InvalidError",
      raises(asgi_above_function, mexc.InvalidError, "swap the order"))
check("an @modal.asgi_app function with parameters raises InvalidError",
      raises(asgi_with_parameter, mexc.InvalidError, "can't have parameters"))
check("@modal.concurrent() without max_inputs raises TypeError", raises(concurrent_without_max, TypeError, "max_inputs"))
for old, new in [("keep_warm", "min_containers"), ("concurrency_limit", "max_containers"),
                 ("container_idle_timeout", "scaledown_window"), ("allow_concurrent_inputs", "@modal.concurrent")]:
    def old_kwarg(old=old):
        @scratch.function(serialized=True, **{old: 1})
        def g(): ...
    check(f"app.function({old}=...) raises DeprecationError naming {new}",
          raises(old_kwarg, mexc.DeprecationError, new.lstrip("@")))
check("modal.Stub and modal.Mount are gone (AttributeError)",
      raises(lambda: modal.Stub, AttributeError) and raises(lambda: modal.Mount, AttributeError))
check("modal.web_endpoint raises DeprecationError", raises(modal.web_endpoint, mexc.DeprecationError))
check("Dict.lookup and Volume.lookup are gone (use from_name)",
      not hasattr(modal.Dict, "lookup") and not hasattr(modal.Volume, "lookup"))
check("Image.add_local_dir defers the path check to build time (missing web/dist passes offline)",
      modal.Image.debian_slim().add_local_dir("does/not/exist", "/root/web/dist") is not None)
check("Volume.batch_upload(force=False) by default: a reseed needs force=True",
      params(modal.Volume.batch_upload)["force"].default is False)
check("Dict.put(..., skip_if_exists=False) is the slot-reservation primitive",
      params(modal.Dict.put)["skip_if_exists"].default is False)
check("Volume, Dict and Secret from_name take environment_name",
      all("environment_name" in params(f) for f in (modal.Volume.from_name, modal.Dict.from_name, modal.Secret.from_name)))

# 5. How get(timeout=0) reports runner outcomes (drives modal's own poll path with canned responses)
from modal._functions import _Invocation  # noqa: E402
from modal._serialization import serialize  # noqa: E402
from modal_proto import api_pb2  # noqa: E402


BLOCKS = re.findall(r"```python\n(.*?)```", HOSTED_CODE.read_text(), re.S)
APP_BLOCK = BLOCKS[0]  # src/api/modal_app.py: imports src.config, so it is read, not executed


def load_hosted_code() -> dict:
    """Exec the src/infra and src/api blocks of references/hosted-code.md as written."""
    ns: dict = {"__name__": "hosted_code"}
    for block in BLOCKS[1:]:
        if not block.startswith("# scripts/"):  # the purge sketch is a fragment, not a module
            exec(compile(block, "hosted-code.md", "exec", dont_inherit=True), ns)  # no __future__ flags
    return ns


HOSTED = load_hosted_code()
POLL_ERRORS, runner_state = HOSTED["POLL_ERRORS"], HOSTED["runner_state"]


class CannedCall:
    """Stands in for modal.FunctionCall; get() runs modal's real _Invocation.poll_function."""

    def __init__(self, response: api_pb2.FunctionGetOutputsResponse | None = None,
                 poll_error: BaseException | None = None) -> None:
        self.response, self.poll_error = response, poll_error

    def get(self, timeout: float | None = None):
        inv = _Invocation(stub=None, function_call_id="fc-selfcheck", client=None)

        async def pop(**_kwargs):
            if self.poll_error is not None:
                raise self.poll_error
            return self.response

        inv.pop_function_call_outputs = pop
        return asyncio.run(inv.poll_function(timeout=timeout))


G = api_pb2.GenericResult


def output(status: int, data: bytes = b"", exception: str = "") -> api_pb2.FunctionGetOutputsResponse:
    return api_pb2.FunctionGetOutputsResponse(outputs=[api_pb2.FunctionGetOutputsItem(
        result=G(status=status, data=data, exception=exception), data_format=api_pb2.DATA_FORMAT_PICKLE)])


check("no output yet raises builtin TimeoutError, not modal.exception.TimeoutError",
      raises(CannedCall(api_pb2.FunctionGetOutputsResponse(num_unfinished_inputs=1)).get, builtins.TimeoutError)
      and not issubclass(builtins.TimeoutError, mexc.TimeoutError))
check("FunctionTimeoutError and OutputExpiredError are modal TimeoutErrors, not builtin ones",
      issubclass(mexc.FunctionTimeoutError, mexc.TimeoutError) and issubclass(mexc.OutputExpiredError, mexc.TimeoutError)
      and not issubclass(mexc.FunctionTimeoutError, builtins.TimeoutError)
      and not issubclass(mexc.OutputExpiredError, builtins.TimeoutError))
cases = {
    "running": CannedCall(api_pb2.FunctionGetOutputsResponse(num_unfinished_inputs=1)),
    "expired": CannedCall(api_pb2.FunctionGetOutputsResponse(num_unfinished_inputs=0)),
    "timed_out": CannedCall(output(G.GENERIC_STATUS_TIMEOUT, exception="runner exceeded timeout")),
    "crashed": CannedCall(output(G.GENERIC_STATUS_FAILURE, serialize(ValueError("runner raised")))),
    "finished": CannedCall(output(G.GENERIC_STATUS_SUCCESS, serialize(None))),
}
for expected, call in cases.items():
    check(f"runner_state -> {expected}", runner_state(call) == expected)
for exc in POLL_ERRORS:
    check(f"{exc.__name__} raised by the poll -> unknown (job left unchanged)",
          runner_state(CannedCall(poll_error=exc("transient"))) == "unknown")
check("a runner that itself raised modal ConnectionError also reads unknown (hence DEADLINE_S)",
      runner_state(CannedCall(output(G.GENERIC_STATUS_FAILURE, serialize(mexc.ConnectionError("runner side")))))
      == "unknown")


# 6. The spine's hosted rules on in-memory fakes (AD-7 to AD-9)
def decorated(block: str) -> list[str]:
    return re.findall(r"@app\.function\([^\n]*\n(?:@[^\n]*\n)*def (\w+)\(", block)


check("AD-9 names: Dicts keyframe-jobs, keyframe-sessions, keyframe-ledger",
      re.findall(r'Dict\.from_name\("([^"]+)"', APP_BLOCK) == ["keyframe-jobs", "keyframe-sessions", "keyframe-ledger"])
check("AD-9 names: Volume keyframe-data mounted at /data, Secret keyframe",
      re.findall(r'Volume\.from_name\("([^"]+)"', APP_BLOCK) == ["keyframe-data"] and 'DATA = "/data"' in APP_BLOCK
      and re.findall(r'Secret\.from_name\("([^"]+)"', APP_BLOCK) == ["keyframe"])
check("AD-9 names: functions web, run_build, ledger_export, session_sweep",
      sorted(decorated(APP_BLOCK)) == ["ledger_export", "run_build", "session_sweep", "web"])
check("AD-7 runner timeout=900 and AD-9 max_containers=1 in modal_app.py",
      "@app.function(timeout=900)" in APP_BLOCK and "max_containers=1" in APP_BLOCK)


class FakeDict(dict):
    """modal.Dict's surface used by the adapters, in memory."""

    def put(self, key, value, *, skip_if_exists=False) -> bool:
        if skip_if_exists and key in self:
            return False
        self[key] = value
        return True


@dataclasses.dataclass(frozen=True)
class JobState:
    """Stand-in for the pydantic job state the stories will write."""

    status: str
    stage: str | None
    created_at: datetime

    @classmethod
    def model_validate(cls, raw: dict) -> "JobState":
        return cls(raw["status"], raw.get("stage"), datetime.fromisoformat(raw["created_at"]))

    def model_dump(self, mode: str = "json") -> dict:
        return {"status": self.status, "stage": self.stage, "created_at": self.created_at.isoformat()}

    def model_copy(self, update: dict) -> "JobState":
        return dataclasses.replace(self, **update)


class QuotaExceeded(Exception):
    pass


class FakeVolume:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def reload(self) -> None:
        pass


canned: dict[str, CannedCall] = {}
HOSTED.update(JobState=JobState, BuildQuotaExceeded=QuotaExceeded,
              modal=SimpleNamespace(FunctionCall=SimpleNamespace(from_id=canned.__getitem__)))
tmp = tempfile.TemporaryDirectory()
h = HOSTED["ModalHandles"](jobs=FakeDict(), sessions=FakeDict(), ledger=FakeDict(), volume=FakeVolume(),
                           root=tmp.name, runner=SimpleNamespace(spawn=lambda job_id: SimpleNamespace(object_id="fc-1")))
store = HOSTED["ModalJobStore"](h, files=None)


def job(status: str, stage: str | None, age_s: float) -> JobState:
    return JobState(status, stage, datetime.now(UTC) - timedelta(seconds=age_s))


check("AD-7 backstops: ORPHAN_S 60 s, DEADLINE_S 1,200 s",
      HOSTED["ORPHAN_S"] == 60 and HOSTED["DEADLINE_S"] == 1200)
HOSTED["ModalJobRunner"](h).start("job_1")
check("AD-7 JobRunner.start stores the FunctionCall id under call:<job_id>, never in the record",
      h.jobs == {"call:job_1": "fc-1"})
slots = [store.reserve_build(f"job_{n}") for n in range(1, 21)]
check("AD-9 quota: 20 slot keys claimed with skip_if_exists, numbered 1 to 20",
      slots == list(range(1, 21)) and all(f"build:{n}" in h.jobs for n in slots))
check("AD-9 quota: the 21st build raises BuildQuotaExceeded",
      raises(lambda: store.reserve_build("job_21"), QuotaExceeded))

store.put("job_young", job("queued", "ingest", 30))
check("queued job with no call key under ORPHAN_S is left queued",
      store.get("job_young").status == "queued" and h.jobs["job_young"]["status"] == "queued")
store.put("job_orphan", job("queued", "ingest", 61))
check("queued job with no call key past ORPHAN_S is marked failed, keeping its stage",
      (store.get("job_orphan").status, h.jobs["job_orphan"]["stage"]) == ("failed", "ingest"))

canned.update({
    "fc-running": CannedCall(api_pb2.FunctionGetOutputsResponse(num_unfinished_inputs=1)),
    "fc-unknown": CannedCall(poll_error=mexc.ConnectionError("transient")),
    "fc-crashed": CannedCall(output(G.GENERIC_STATUS_FAILURE, serialize(ValueError("runner raised")))),
    "fc-finished": CannedCall(output(G.GENERIC_STATUS_SUCCESS, serialize(None))),
})
for job_id, call_id, age, expected in (("job_run", "fc-running", 2000, "running"),
                                       ("job_unk", "fc-unknown", 100, "running"),
                                       ("job_dead", "fc-unknown", 1201, "failed"),
                                       ("job_crash", "fc-crashed", 100, "failed")):
    store.put(job_id, job("running", "segment", age))
    h.jobs[f"call:{job_id}"] = call_id
    got = store.get(job_id)
    check(f"watchdog: {call_id.removeprefix('fc-')} runner, job {age} s old -> {expected}"
          + (", stage kept" if expected == "failed" else ""),
          got.status == expected and got.stage == "segment" and h.jobs[job_id]["status"] == expected)
store.put("job_raced", job("done", "scene", 100))
h.jobs["call:job_raced"] = "fc-finished"
check("watchdog: a runner that finished meanwhile wins (its terminal record is returned, not overwritten)",
      store._watchdog("job_raced", job("running", "scene", 100)).status == "done"
      and h.jobs["job_raced"]["status"] == "done")

poll = HOSTED["build_poll_status"]
check("AD-7 GET /builds/<job_id>: 202 while queued or running, 200 when terminal",
      [poll(s) for s in ("queued", "running")] == [202, 202]
      and all(poll(s) == 200 for s in HOSTED["TERMINAL"]))

now = datetime.now(UTC)
h.sessions.update({"sess_old": {"room_id": "room_a", "last_event_at": (now - timedelta(hours=25)).isoformat()},
                   "sess_new": {"room_id": "room_a", "last_event_at": (now - timedelta(hours=1)).isoformat()}})
HOSTED["sweep_sessions"](h, now=now)
check("AD-8 session_sweep: deletes sessions 24 h after their last event, keeps the rest",
      HOSTED["SESSION_TTL"] == timedelta(hours=24) and list(h.sessions) == ["sess_new"])
h.ledger.update({"call_1": {"kind": "segment", "usd": 0.0025}})
HOSTED["export_ledger"](h, day=now.date())
snapshot = Path(tmp.name, "spend", f"hosted-{now.date().isoformat()}.jsonl").read_text()
check("AD-9 ledger_export: one JSON line per ledger entry under spend/, then commit",
      snapshot.strip() == '{"key": "call_1", "kind": "segment", "usd": 0.0025}' and h.volume.commits == 1)
tmp.cleanup()

print("selfcheck passed")
