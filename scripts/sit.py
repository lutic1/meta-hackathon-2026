#!/usr/bin/env python3
"""The lean SIT: every live-seam case under `tests/sit/`, on the real cache and ledger (AR-25, AD-6, AD-17).

    uv run scripts/sit.py                  # runs every case, prints PASS or FAIL per case, exits 1 on any FAIL

A case is a module `tests/sit/test_<nn>_<name>.py` with a `run(sit)` function
and a one-line docstring; `sit.py` discovers the modules in file-name order
and runs each one in turn, so a later story adds its case as a file and
nothing here changes. `run` raises to fail (an `AssertionError` or any
`Exception`) and may return a short note that is printed beside its PASS.
The checklist, `docs/implementation-artifacts/sit-checklist.md`, carries
the cases, the dated builder items and the run log.

`Sit` is what each case receives: `Settings` (the keys come from `.env`),
the real `JsonlLedgerStore` under `spend/ledger.jsonl` guarded by one
`SpendLedger` at the local `SPEND_CAP_USD`, the `DiskCache` under `.cache/`,
a provider factory per adapter (every call takes `GuardedCalls`, so a run
stays within the cap and a cache hit is never billed), the input photos
from the git-ignored `photos/` folder (never `tests/`), downscaled to the
1280 px long edge the pipeline sends, and `record`, which writes the last
live response (or one the case names) as a fixture under
`tests/fixtures/providers/<model>/` in the shape `tests/providers/replay.py`
replays: the response status and body only, never the request, an image or
a `data:` URL. `record_job` writes a Build's job record, which holds no
solution or answer, under `tests/fixtures/jobs/`. The offline suite never
collects `tests/sit/` (`collect_ignore` in `tests/conftest.py`).
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import sys
import time
import traceback
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from src.config import Settings
from src.domain.ledger import CallKind
from src.domain.schema import JobState
from src.infra.local import CACHE_ROOT, LEDGER_PATH, DiskCache, JsonlLedgerStore
from src.providers.cache import GuardedCalls
from src.providers.meta_api import MetaModelProvider
from src.providers.ollama import OllamaPhraser
from src.providers.openai_compatible import JsonMode, OpenAICompatibleProvider
from src.providers.spend import SpendLedger
from src.providers.verbatim import VerbatimPhraser

CASES_ROOT = Path("tests/sit")
FIXTURES_ROOT = Path("tests/fixtures/providers")
JOBS_ROOT = Path("tests/fixtures/jobs")
PHOTOS_ROOT = Path("photos")
"""Git-ignored; the only place the SIT reads an input photo from."""
LONG_EDGE = 1280
"""The stored downscaled JPEG's long edge (AD-7), what every live call sends."""
PHOTO_SUFFIXES = (".jpg", ".jpeg")
META_HOST = "api.meta.ai"
FORBIDDEN_IN_FIXTURES = (b"data:image", b"\xff\xd8\xff")
"""What a recorded fixture may never hold: a data URL or JPEG magic bytes; the offline scan checks the same."""


class RecordingTransport(httpx.BaseTransport):
    """Keeps the status and JSON body of every response that came back through `inner`, so a case can record it."""

    def __init__(self, inner: httpx.BaseTransport) -> None:
        self.inner = inner
        self.responses: list[tuple[int, Any]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self.inner.handle_request(request)
        response.read()
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        self.responses.append((response.status_code, body))
        return response


class EnvironmentTransport(httpx.BaseTransport):
    """Routes each request the way `httpx.Client(trust_env=True)` does: through the environment's proxy unless `NO_PROXY` covers the host.

    An adapter given an explicit transport bypasses its client's own environment proxy mounts, so a bare
    `httpx.HTTPTransport` would send every SIT call straight to the host; in the cloud container the egress
    proxy at `HTTPS_PROXY` is what adds the Meta key (AD-14), and without it every Meta call answers 401.
    With no proxy variable set (the Mac) every request goes direct, as before. `NO_PROXY` matching is loose:
    `*`, an exact host, or a suffix after a leading dot; CIDR entries are not matched.
    """

    def __init__(self, direct: httpx.BaseTransport, proxied: Mapping[str, httpx.BaseTransport], no_proxy: tuple[str, ...]) -> None:
        self.direct = direct
        self.proxied = proxied  # by request scheme
        self.no_proxy = no_proxy

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> EnvironmentTransport:
        """`HTTPS_PROXY` for https requests and `HTTP_PROXY` for http ones (either case), `NO_PROXY` as a comma-separated host list."""

        def read(name: str) -> str:
            return env.get(name.upper()) or env.get(name.lower()) or ""

        proxied = {scheme: httpx.HTTPTransport(proxy=url) for scheme in ("https", "http") if (url := read(f"{scheme}_proxy"))}
        no_proxy = tuple(entry.strip() for entry in read("no_proxy").split(",") if entry.strip())
        return cls(httpx.HTTPTransport(), proxied, no_proxy)

    def covered(self, host: str) -> bool:
        return any(entry == "*" or entry == host or (entry.startswith(".") and host.endswith(entry)) for entry in self.no_proxy)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        proxied = None if self.covered(request.url.host) else self.proxied.get(request.url.scheme)
        return (proxied or self.direct).handle_request(request)

    def close(self) -> None:
        self.direct.close()
        for transport in self.proxied.values():
            transport.close()


def downscale(jpeg: bytes, long_edge: int = LONG_EDGE) -> bytes:
    """The photo as the pipeline stores it: a JPEG whose long edge is at most `long_edge`; smaller bytes pass unchanged."""
    with Image.open(io.BytesIO(jpeg)) as image:
        if max(image.size) <= long_edge and image.format == "JPEG":
            return jpeg
        image.thumbnail((long_edge, long_edge))
        out = io.BytesIO()
        image.convert("RGB").save(out, format="JPEG", quality=85)
    return out.getvalue()


@dataclass
class Sit:
    """What `run(sit)` receives: one ledger, one cache and one recording transport for the whole run."""

    root: Path
    settings: Settings
    transport: RecordingTransport
    store: JsonlLedgerStore = field(init=False)
    ledger: SpendLedger = field(init=False)
    cache: DiskCache = field(init=False)

    def __post_init__(self) -> None:
        self.store = JsonlLedgerStore(self.root / LEDGER_PATH)
        self.ledger = SpendLedger(self.store, cap_usd=self.settings.spend_cap_usd)
        self.cache = DiskCache(self.root / CACHE_ROOT)

    def running_total_usd(self) -> float:
        return self.ledger.running_total_usd()

    def recording(self) -> RecordingTransport:
        """A transport over this run's that also keeps its own responses, so a case can tell one adapter's replies apart."""
        return RecordingTransport(self.transport)

    def calls(self, *, cache: bool, host: str = META_HOST, ledger: SpendLedger | None = None) -> GuardedCalls:
        """The guarded path every live call takes; `cache=False` is `CACHE=off`, which skips the cache and never the ledger."""
        return GuardedCalls(self.cache, ledger or self.ledger, host=host, enabled=cache)

    def meta(
        self,
        chat_kind: CallKind,
        budget_s: float,
        *,
        cache: bool = False,
        ledger: SpendLedger | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> MetaModelProvider:
        """The Meta adapter for one council role, over this run's cache, ledger and recording transport (or one wrapping it)."""
        return MetaModelProvider(
            self.settings.model_api_key,
            self.settings.meta_model_api_base_url,
            calls=self.calls(cache=cache, ledger=ledger),
            chat_kind=chat_kind,
            budget_s=budget_s,
            transport=transport or self.transport,
        )

    def openai_compatible(
        self, *, kind: CallKind = "riddler", json_mode: JsonMode = "json_schema", model: str | None = None, cache: bool = False
    ) -> OpenAICompatibleProvider:
        """The fallback adapter on the host `OPENAI_COMPATIBLE_BASE_URL` names (Baseten or Fireworks)."""
        base_url = self.settings.openai_compatible_base_url
        return OpenAICompatibleProvider(
            self.settings.openai_compatible_api_key,
            base_url,
            self.calls(cache=cache, host=httpx.URL(base_url).host if base_url else ""),
            model=model,
            kind=kind,
            json_mode=json_mode,
            transport=self.transport,
        )

    def ollama(self, host: str | None = None) -> OllamaPhraser:
        """The Guide adapter over the verbatim one, at `OLLAMA_HOST` unless `host` says otherwise; no cache or ledger, the model is free."""
        return OllamaPhraser(host or self.settings.ollama_host, fallback=VerbatimPhraser(), transport=self.transport)

    def originals(self, count: int) -> list[bytes]:
        """The bytes of the first `count` JPEGs under `photos/` in name order, as the camera wrote them."""
        folder = self.root / PHOTOS_ROOT
        paths = sorted(p for p in folder.glob("*") if p.suffix.lower() in PHOTO_SUFFIXES) if folder.is_dir() else []
        if len(paths) < count:
            raise FileNotFoundError(f"{PHOTOS_ROOT}/ holds {len(paths)} JPEG(s); the SIT needs {count} (own room photos, no faces or documents)")
        return [path.read_bytes() for path in paths[:count]]

    def photos(self, count: int) -> list[bytes]:
        """The first `count` JPEGs under `photos/` in name order, downscaled to the 1280 px long edge."""
        return [downscale(original) for original in self.originals(count)]

    def fixture_path(self, name: str, *, model: str) -> Path:
        return self.root / FIXTURES_ROOT / model / f"{name}.json"

    def record(self, name: str, *, model: str, response: tuple[int, Any] | None = None) -> Path:
        """Write `response`, by default the case's last live one, as `tests/fixtures/providers/<model>/<name>.json`; refused when it made no call."""
        if response is None:
            if not self.transport.responses:
                raise LookupError(f"no live response to record as {model}/{name}: the call was served from the cache or never made")
            response = self.transport.responses[-1]
        status, body = response
        data = json.dumps({"model": model, "status": status, "body": body}, indent=2, ensure_ascii=False).encode() + b"\n"
        return self._write(self.fixture_path(name, model=model), data, f"{model}/{name}")

    def record_job(self, name: str, state: JobState) -> Path:
        """Write a Build's job record, which holds verdicts and never a solution or an answer, as `tests/fixtures/jobs/<name>.json`."""
        return self._write(self.root / JOBS_ROOT / f"{name}.json", state.model_dump_json(indent=2).encode() + b"\n", f"jobs/{name}")

    @staticmethod
    def _write(path: Path, data: bytes, label: str) -> Path:
        for marker in FORBIDDEN_IN_FIXTURES:
            if marker in data:
                raise ValueError(f"refusing to record {label}: it holds {marker!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def recorded(self, name: str, *, model: str) -> Any:
        """The body of a fixture an earlier case recorded; a missing one is named, never fetched."""
        path = self.fixture_path(name, model=model)
        if not path.is_file():
            raise LookupError(f"no recorded fixture {model}/{name} at {path.relative_to(self.root)}; run its case first")
        return json.loads(path.read_bytes())["body"]


# --- Discovery and the run ----------------------------------------------------


def discover(cases_root: Path) -> list[Path]:
    """Every `test_*.py` under `cases_root`, in file-name order; the order is the run order."""
    return sorted(cases_root.glob("test_*.py")) if cases_root.is_dir() else []


def load_case(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"sit_case_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not callable(getattr(module, "run", None)):
        raise TypeError(f"{path.name} defines no run(sit) function")
    return module


def run_case(path: Path, sit: Sit) -> tuple[bool, str]:
    """Run one case; `(passed, note)` where a failure's note is its error, with the traceback printed."""
    before, started = sit.running_total_usd(), time.monotonic()
    sit.transport.responses.clear()  # so `record` sees only this case's live responses
    try:
        note = load_case(path).run(sit)
    except Exception as error:  # noqa: BLE001 - any error is the case's failure, named in the report
        traceback.print_exc()
        return False, f"{type(error).__name__}: {error}"
    spent = sit.running_total_usd() - before
    tail = f" ({note})" if note else ""
    return True, f"{time.monotonic() - started:.1f} s, spend {spent:+.4f} USD{tail}"


def main(argv: list[str] | None = None, *, root: Path = REPO, cases_root: Path | None = None, transport: RecordingTransport | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    cases = discover(cases_root or root / CASES_ROOT)
    if not cases:
        print(f"no case under {CASES_ROOT}/", file=sys.stderr)
        return 1
    sit = Sit(root, Settings.from_env(), transport or RecordingTransport(EnvironmentTransport.from_env()))
    print(f"sit {date.today().isoformat()}: {len(cases)} cases; running total {sit.running_total_usd():.4f} USD against the {sit.ledger.cap_usd:.2f} USD local cap")
    failed: list[str] = []
    for path in cases:
        passed, note = run_case(path, sit)
        if not passed:
            failed.append(path.stem)
        print(f"{'PASS' if passed else 'FAIL'} {path.stem}: {note}")
    print(f"\nsit: {len(cases) - len(failed)} pass, {len(failed)} fail; running total {sit.running_total_usd():.4f} USD")
    if failed:
        print("failed: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
