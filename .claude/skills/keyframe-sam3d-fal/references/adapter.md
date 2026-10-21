# fal adapter core for SAM 3D Objects

The `python` block below is the reference for the helpers in `src/providers/fal.py`. `scripts/selfcheck.py` executes it unchanged and drives it through a real `fal_client.SyncClient` on `httpx.MockTransport`. Keyframe's own pieces (`Cache`, `SpendLedger`, `ArtifactStore`, `ProviderError`) wrap it, as SKILL.md shows; they are left out here so the block runs on its own.

## Why the inputs look like this

- **Upright original.** Ingest keeps the original JPEG byte for byte (AD-7), so an iPhone original can still carry an EXIF orientation tag other than 1. The downscaled frame had that orientation applied in the browser, and the fal docs do not say whether the model applies it. So the adapter sends an upright copy, re-encoded only when the tag is not 1, and the cache key hashes the bytes actually sent.
- **Mask from persisted polygons.** Schema v1 persists `polygons` in frame pixels (the stored 1280 px JPEG), not the raw sam-3.1 raster. AD-5's port takes them as `Mask3D {label, polygons, frame_size}`, defined in `src/domain/schema.py`; the block below carries a dataclass stand-in with the same fields so it runs on its own. The adapter scales the polygons to the upright original and fills them into a binary PNG of exactly that size, 255 for the object and 0 elsewhere. A plural interactable has one polygon per instance, so they all land in one mask, which makes one object. Pillow runs here, in an adapter, because AD-1 keeps it out of `src/domain` and `src/pipeline`.
- **Data URIs, no CDN upload, by default.** fal accepts a base64 data URI wherever a file URL is expected, but its CDN page says outright that data URIs are "not recommended for files larger than a few KB", because the whole file travels in the request body. A 4032x3024 original is several megabytes, so this default goes against fal's advice. It is kept for privacy: the photo never becomes a CDN object. That with `X-Fal-Store-IO: 0` no copy of a data-URI input persists at fal is an inference, not a documented guarantee; confirm it, and that the size is accepted without a 413, on the first live call (SKILL.md, Tested commands).
- **Upload fallback.** If the data URI is too slow, or the request is refused (413, `file_too_large`), switch only `image_url` to an upload. A plain `client.upload` is publicly readable by URL until it expires. The private form sets an ACL in the same lifecycle setting: `client.upload(image, "image/jpeg", lifecycle=fal_client.StorageSettings(expires_in="1h", initial_acl=fal_client.StorageACL(default="forbid")))` (`"hide"` answers 404 instead of 403). The owning account keeps access, but whether the model runner can still read a `forbid` input is not documented; check it live before relying on it (https://fal.ai/docs/documentation/model-apis/file-access-controls.md).
- **`prompt` is always the label.** AD-5 makes the fal prompt `Mask3D.label`. The input schema defaults `prompt` to `"car"`. Masks take precedence, but a dropped or empty mask must not quietly reconstruct a car.
- **One object per call.** A single mask returns `model_glb` and `gaussian_splat` for that object. `individual_glbs` and `individual_splats` appear only in multi-object scenes, so this code never reads them.

```python
"""Core of the fal adapter for SAM 3D Objects (src/providers/fal.py)."""

import hashlib
import io
import json
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import fal_client
import httpx
from PIL import Image, ImageDraw, ImageOps

ENDPOINT = "fal-ai/sam-3/3d-objects"
PRICE_USD = 0.02  # "per unit" on the model card, assumed one call; also the AD-6 seed estimate
SEED = 7  # fixed, so an identical request is a cache hit and reproducible
START_TIMEOUT_S = 120  # server side: 504 if no runner has started by then
CLIENT_TIMEOUT_S = 300  # client side: total wait; subscribe then cancels the request
POLL_INTERVAL_S = 1.0  # the client default of 0.1 s polls ten times a second
# AD-13: fal's retryable set is a 429, or a 5xx whose X-Fal-Needs-Retry allows it, or a connect error.
FAL_RETRYABLE_STATUS = frozenset({429})
NEEDS_RETRY_HEADER = "x-fal-needs-retry"
RETRY_ON_CONNECT = (httpx.ConnectError, httpx.ConnectTimeout)  # nothing was sent, so nothing was billed
HEADERS = {
    "X-Fal-Store-IO": "0",  # keep inputs and outputs out of fal request history
    "X-Fal-Object-Lifecycle-Preference": json.dumps({"expiration_duration_seconds": 3600}),
}
GLB_MAGIC = b"glTF"
PLY_MAGIC = b"ply"
# The output schema's default for model_glb is a sample scene, never this request's mesh.
SCHEMA_SAMPLE_GLB = (
    "https://v3b.fal.media/files/b/0a8439e7/mqHMt17hzqDaqVMF7q0dB_combined_scene.glb"
)
_EXIF_ORIENTATION = 0x0112

Point = tuple[float, float]


@dataclass(frozen=True)
class Mask3D:
    """Stand-in for the AD-5 port type in src/domain/schema.py (a pydantic model there)."""

    label: str  # the fal prompt
    polygons: list[list[Point]]  # one per instance, in frame pixels
    frame_size: tuple[int, int]  # width, height of the stored downscaled JPEG


class NoMeshError(Exception):
    """fal answered 200 but gave no usable mesh or file. Messages never carry URLs."""


def upright_jpeg(original: bytes) -> tuple[bytes, tuple[int, int]]:
    """The original photo as sent to fal (EXIF orientation applied) and its size."""
    with Image.open(io.BytesIO(original)) as img:
        if img.getexif().get(_EXIF_ORIENTATION, 1) == 1:
            return original, img.size
        upright = ImageOps.exif_transpose(img)
    buf = io.BytesIO()
    upright.save(buf, "JPEG", quality=95)
    return buf.getvalue(), upright.size


def mask_png(mask: Mask3D, size: tuple[int, int]) -> bytes:
    """Binary PNG at the upright original's size from the mask's frame-pixel polygons."""
    sx, sy = size[0] / mask.frame_size[0], size[1] / mask.frame_size[1]
    png = Image.new("L", size, 0)
    draw = ImageDraw.Draw(png)
    for polygon in mask.polygons:
        draw.polygon([(x * sx, y * sy) for x, y in polygon], fill=255)
    buf = io.BytesIO()
    png.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def build_arguments(image: bytes, mask_bytes: bytes, label: str, seed: int = SEED) -> dict:
    return {
        "image_url": fal_client.encode(image, "image/jpeg"),
        "mask_urls": [fal_client.encode(mask_bytes, "image/png")],
        "prompt": label,
        "seed": seed,
    }


def cache_key(image: bytes, mask_bytes: bytes, label: str, seed: int = SEED, attempt: int = 0) -> str:
    """AD-6 key: endpoint, prompt, seed, sha256 of each file in order, attempt."""
    parts = [
        ENDPOINT,
        label,
        str(seed),
        hashlib.sha256(image).hexdigest(),
        hashlib.sha256(mask_bytes).hexdigest(),
        str(attempt),
    ]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def run_queued(
    client: fal_client.SyncClient,
    arguments: dict,
    on_enqueue: Callable[[str], None] | None = None,
    *,
    start_timeout: float = START_TIMEOUT_S,
    client_timeout: float = CLIENT_TIMEOUT_S,
) -> dict:
    """Queue the request and block until its result, within client_timeout seconds."""
    return client.subscribe(
        ENDPOINT,
        arguments,
        headers=HEADERS,
        start_timeout=start_timeout,
        client_timeout=client_timeout,
        interval=POLL_INTERVAL_S,
        on_enqueue=on_enqueue,
    )


def is_retryable(exc: Exception) -> bool:
    """AD-13: a 429, a 5xx whose X-Fal-Needs-Retry allows it, or a connect error."""
    if isinstance(exc, RETRY_ON_CONNECT):
        return True
    if not isinstance(exc, fal_client.FalClientHTTPError):
        return False  # FalClientTimeoutError among them: the request may still run and bill
    if exc.status_code in FAL_RETRYABLE_STATUS:
        return True
    needs_retry = exc.response.headers.get(NEEDS_RETRY_HEADER, "").strip().lower()
    return exc.status_code >= 500 and needs_retry in ("true", "1")


def retry_after_s(headers: Mapping[str, str]) -> float | None:
    """Retry-After in seconds, from delta-seconds or an HTTP-date; None when absent or unreadable."""
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def retry_wait_s(retry_after: float | None, remaining_s: float) -> float | None:
    """AD-13: Retry-After, else 0.5 to 1 s of jitter; None (fail at once) past the remaining budget."""
    wait = retry_after if retry_after is not None else 0.5 + random.random() * 0.5
    return wait if wait <= remaining_s else None


def retry_once(call: Callable[[], dict], *, budget_s: float = CLIENT_TIMEOUT_S,
               sleep: Callable[[float], None] = time.sleep,
               clock: Callable[[], float] = time.monotonic) -> dict:
    """AD-13: one retry with backoff, only when is_retryable says so and the wait fits the budget."""
    started = clock()
    try:
        return call()
    except (fal_client.FalClientHTTPError, *RETRY_ON_CONNECT) as exc:
        headers = exc.response.headers if isinstance(exc, fal_client.FalClientHTTPError) else {}
        remaining = budget_s - (clock() - started)
        wait = retry_wait_s(retry_after_s(headers), remaining) if is_retryable(exc) else None
        if wait is None:
            raise
    sleep(wait)
    return call()


@dataclass(frozen=True)
class Reconstruction:
    glb_url: str
    splat_url: str
    metadata: list[dict]  # SAM3DObjectMetadata, kept raw for Interactable.tier2


def parse_result(result: dict) -> Reconstruction:
    glb = (result.get("model_glb") or {}).get("url")
    splat = (result.get("gaussian_splat") or {}).get("url")
    if not glb or glb == SCHEMA_SAMPLE_GLB:
        raise NoMeshError("no model_glb for this object")
    if not splat or "metadata" not in result:
        raise NoMeshError("result lacks gaussian_splat or metadata")
    return Reconstruction(glb, splat, result["metadata"])


def fetch(http: httpx.Client, url: str, magic: bytes) -> bytes:
    """Download one output before its URL expires and check its file signature."""
    response = http.get(url, follow_redirects=True)
    response.raise_for_status()
    if not response.content.startswith(magic):
        raise NoMeshError(f"downloaded file does not start with {magic!r}")
    return response.content


@dataclass(frozen=True)
class Failure:
    code: str  # snake_case code for ProviderError and the job's call row
    status: int | None
    billed: bool  # settle the ledger at PRICE_USD (True) or at 0 (False)


def classify(exc: fal_client.FalClientError | httpx.HTTPError | NoMeshError) -> Failure:
    """Map an exception the adapter catches to a Failure. Never re-raises."""
    if isinstance(exc, NoMeshError):
        return Failure("fal_bad_output", 200, True)
    if isinstance(exc, fal_client.FalClientTimeoutError):
        return Failure("fal_client_timeout", None, True)
    if isinstance(exc, fal_client.FalClientHTTPError):
        status = exc.status_code
        code = _detail_type(exc) or exc.error_type or f"fal_http_{status}"
        return Failure(code, status, status < 500)  # fal bills no 5xx
    if isinstance(exc, httpx.HTTPError):
        return Failure("fal_transport_error", None, True)
    return Failure("fal_client_error", None, True)


def _detail_type(exc: fal_client.FalClientHTTPError) -> str | None:
    """First `type` from a model error body: {"detail": [{"loc", "msg", "type", ...}]}."""
    try:
        body = exc.response.json()
    except ValueError:
        return None
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
        return detail[0].get("type")
    return None
```

## Notes on the block

- `classify` treats every outcome except a 5xx as billed. fal only documents that 5xx failures are free. Settling a 4xx (including a 413 or a surfaced 429) or a client timeout at $0.02 is conservative. Correct it from the fal usage dashboard after the first live failures.
- `classify` covers exactly what the adapter catches and never re-raises, so every caught failure is settled. Anything else (fal-client's own `ValueError("Unknown status: ...")`, a JSON decode error, a bug) is settled at $0.02 by the `finally` in SKILL.md and propagates unchanged.
- `retry_once` is AD-13's single adapter retry. It runs inside one guarded call, so a retried call is one ledger entry (AD-6). `is_retryable` declares fal's set: a 429 always; a 5xx only when `X-Fal-Needs-Retry` allows it (fal's model errors carry the header; infrastructure errors such as a runner 503 or a start-timeout 504 do not, so they are not retried here, and the queue has already retried the 503s and 504s it can); a connect error (`httpx.ConnectError`, `httpx.ConnectTimeout`). fal documents the header only as retryable "true or false", so `"true"` and `"1"` count as allowing a retry. A 5xx is unbilled, so its retry costs time only. A `FalClientTimeoutError` (client timeout) or a read timeout is never retried, because that request may still be running and billing.
- The wait is `Retry-After` (delta-seconds or an HTTP-date) or 0.5 to 1 s of jitter, and a wait longer than what is left of `budget_s` fails at once (`retry_wait_s`). `budgets.md` gives Tier 2 no stage budget, so `budget_s` defaults to `CLIENT_TIMEOUT_S` (300 s), a Keyframe choice.
- fal-client retries transport errors itself (10 attempts and a backup domain), so a connect error rarely reaches `retry_once`. When one does after the submit succeeded (on a status poll), the retry submits again and the first request may still run; `classify` settles it billed, which stays conservative.
- `NoMeshError` and the `ProviderError` built from a `Failure` carry no URL: the output URLs are public until they expire, and error messages end up in job state and logs.
- `run_queued` passes `start_timeout` explicitly. When only `client_timeout` is given, fal-client 1.0.3 copies it into `start_timeout`. The explicit 120 s means that a request no runner picks up fails fast with a 504 and is not billed.
- On `client_timeout`, fal-client 1.0.3 cancels the request (best effort) and raises `FalClientTimeoutError` with `request_id`. The polling thread keeps running in the background until fal reports the request finished.
- `fetch` uses the adapter's own `httpx.Client` with an explicit timeout, never the fal client. The output URLs are public CDN links, and `HEADERS` makes them expire after an hour.
