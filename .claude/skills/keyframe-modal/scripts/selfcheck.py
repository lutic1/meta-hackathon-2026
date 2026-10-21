"""Offline self-check for the keyframe-modal skill. No network, no Modal token.

Asserts the pinned modal version, the signatures the skill cites, that the
Keyframe app shape (ASGI web function, spawned runner, Cron export, Dict,
Volume and Secret handles) constructs lazily with network access blocked,
that the 1.0 renames fail loudly, and how FunctionCall.get(timeout=0)
reports each runner outcome at this version.

Section 5 loads POLL_ERRORS and runner_state from the code block in
references/hosted-code.md, so the documented classifier is the one tested.
It drives them through modal's private _Invocation.poll_function and
modal_proto messages; those imports are stable only at the pinned version,
so expect to update section 5 on any modal upgrade.

    uv run --no-project --with modal==1.6.2 \
        python .claude/skills/keyframe-modal/scripts/selfcheck.py
"""

from __future__ import annotations

import asyncio
import builtins
import inspect
import socket
import warnings
from importlib.metadata import version
from pathlib import Path
from zoneinfo import ZoneInfo

PIN = "1.6.2"


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
             .uv_pip_install("fastapi==0.156.4")
             .env({"MODE": "hosted", "GUIDE": "verbatim"}))
    secret = modal.Secret.from_name("keyframe", required_keys=["META_MODEL_API_KEY", "FAL_KEY", "ACCESS_CODE"])
    volume = modal.Volume.from_name("keyframe-data", create_if_missing=True)
    jobs = modal.Dict.from_name("keyframe-jobs", create_if_missing=True)
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

check("web is an ASGI web function, runner and export are plain functions",
      web._is_web_endpoint() and not run_build._is_web_endpoint() and not ledger_export._is_web_endpoint())
check("Dict, Volume, Secret and Functions stay unhydrated (lazy, no credentials)",
      not any(o._is_hydrated for o in (jobs, volume, secret, web, run_build, ledger_export)))
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


def load_classifier():
    """Exec POLL_ERRORS and runner_state exactly as references/hosted-code.md writes them."""
    text = (Path(__file__).resolve().parents[1] / "references" / "hosted-code.md").read_text()
    start = text.index("POLL_ERRORS = (")
    end = text.index('    return "finished"\n', start) + len('    return "finished"\n')
    ns = {"modal": modal, "mexc": mexc}
    exec(text[start:end], ns)
    return ns["POLL_ERRORS"], ns["runner_state"]


POLL_ERRORS, runner_state = load_classifier()


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

print("selfcheck passed")
