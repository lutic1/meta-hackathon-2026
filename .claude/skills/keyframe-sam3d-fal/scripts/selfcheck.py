"""Offline check for the keyframe-sam3d-fal skill: no network, no keys.

Asserts the pinned versions and the fal-client API surface the skill cites, executes
the python block in references/adapter.md, validates what it builds against a copy of
the live fal schemas for fal-ai/sam-3/3d-objects (fetched 2026-10-21), and drives a
real fal_client.SyncClient through httpx.MockTransport.

    uv run --no-project --with fal-client==1.0.3 --with httpx==0.28.1 \
        --with pillow==13.0.0 --with jsonschema==4.26.0 \
        python .claude/skills/keyframe-sam3d-fal/scripts/selfcheck.py [openapi.json]

With a freshly downloaded OpenAPI document as the argument (OPENAPI_URL below), it
also fails if fal has changed the schema since the copy was taken.
"""

import base64
import dataclasses
import inspect
import io
import json
import re
import sys
import time
from importlib.metadata import version
from pathlib import Path

import fal_client
import httpx
import jsonschema
from PIL import Image

SKILL = Path(__file__).resolve().parent.parent
PINS = {"fal-client": "1.0.3", "httpx": "0.28.1", "pillow": "13.0.0"}
OPENAPI_URL = "https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/sam-3/3d-objects"
QUEUE = "https://queue.fal.run/fal-ai/sam-3/3d-objects"
KEY = "offline-test-key"
SUBSCRIBE = {"headers", "start_timeout", "client_timeout", "interval", "on_enqueue",
             "on_queue_update", "with_logs", "priority", "hint"}
SUBMIT = {"headers", "start_timeout", "webhook_url", "priority", "hint"}
SURFACE = {
    "subscribe": SUBSCRIBE,
    "submit": SUBMIT,
    "status": {"application", "request_id", "with_logs"},
    "result": {"application", "request_id"},
    "cancel": {"application", "request_id"},
    "encode": {"data", "content_type"},
    "encode_file": {"path"},
    "upload_file": {"path", "lifecycle"},
    "upload": {"data", "content_type", "lifecycle"},
}
# Validation-relevant keywords of the live components.schemas, trimmed by trim() below.
SCHEMAS = json.loads(r"""{
    "Sam33dObjectsInput": {"required": ["image_url"], "type": "object", "properties": {"mask_urls": {"items": {"type": "string"}, "type": "array"}, "prompt": {"default": "car", "anyOf": [{"type": "string"}, {"type": "null"}]}, "seed": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "box_prompts": {"default": [], "items": {"$ref": "#/components/schemas/BoxPromptBase"}, "type": "array"}, "image_url": {"type": "string"}, "export_textured_glb": {"default": false, "type": "boolean"}, "pointmap_url": {"anyOf": [{"type": "string"}, {"type": "null"}]}, "detection_threshold": {"anyOf": [{"type": "number", "maximum": 1, "minimum": 0.1}, {"type": "null"}]}, "point_prompts": {"default": [], "items": {"$ref": "#/components/schemas/PointPromptBase"}, "type": "array"}}},
    "Sam33dObjectsOutput": {"required": ["gaussian_splat", "metadata"], "type": "object", "properties": {"artifacts_zip": {"anyOf": [{"$ref": "#/components/schemas/File"}, {"type": "null"}]}, "individual_splats": {"anyOf": [{"items": {"$ref": "#/components/schemas/File"}, "type": "array"}, {"type": "null"}]}, "model_glb": {"default": "https://v3b.fal.media/files/b/0a8439e7/mqHMt17hzqDaqVMF7q0dB_combined_scene.glb", "$ref": "#/components/schemas/File"}, "metadata": {"items": {"$ref": "#/components/schemas/SAM3DObjectMetadata"}, "type": "array"}, "gaussian_splat": {"$ref": "#/components/schemas/File"}, "individual_glbs": {"anyOf": [{"items": {"anyOf": [{"$ref": "#/components/schemas/File"}, {"type": "null"}]}, "type": "array"}, {"type": "null"}]}}},
    "BoxPromptBase": {"type": "object", "properties": {"x_max": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "y_min": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "y_max": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "x_min": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "object_id": {"anyOf": [{"type": "integer"}, {"type": "null"}]}}},
    "PointPromptBase": {"type": "object", "properties": {"y": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "x": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "object_id": {"anyOf": [{"type": "integer"}, {"type": "null"}]}, "label": {"anyOf": [{"enum": [0, 1], "type": "integer"}, {"type": "null"}]}}},
    "File": {"required": ["url"], "type": "object", "properties": {"file_name": {"anyOf": [{"type": "string"}, {"type": "null"}]}, "url": {"type": "string"}, "content_type": {"anyOf": [{"type": "string"}, {"type": "null"}]}, "file_size": {"anyOf": [{"type": "integer"}, {"type": "null"}]}}},
    "SAM3DObjectMetadata": {"required": ["object_index"], "type": "object", "properties": {"scale": {"anyOf": [{"items": {"items": {"type": "number"}, "type": "array"}, "type": "array"}, {"type": "null"}]}, "camera_pose": {"anyOf": [{"items": {"items": {"type": "number"}, "type": "array"}, "type": "array"}, {"type": "null"}]}, "translation": {"anyOf": [{"items": {"items": {"type": "number"}, "type": "array"}, "type": "array"}, {"type": "null"}]}, "rotation": {"anyOf": [{"items": {"items": {"type": "number"}, "type": "array"}, "type": "array"}, {"type": "null"}]}, "object_index": {"type": "integer"}}}
}""")
KEEP = {"type", "required", "properties", "anyOf", "items", "enum", "minimum", "maximum", "$ref", "default"}
failures: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failures.append(name)


def raises(exc_type: type[BaseException], fn, *args, **kwargs) -> BaseException | None:
    try:
        fn(*args, **kwargs)
    except exc_type as exc:
        return exc
    return None


def trim(node, in_properties: bool = False):
    if isinstance(node, dict):
        if in_properties:
            return {k: trim(v) for k, v in node.items()}
        return {k: trim(v, k == "properties") for k, v in node.items() if k in KEEP}
    if isinstance(node, list):
        return [trim(v) for v in node]
    return node


def validator(name: str) -> jsonschema.Draft202012Validator:
    root = {"$ref": f"#/components/schemas/{name}", "components": {"schemas": SCHEMAS}}
    return jsonschema.Draft202012Validator(root)


def load_reference() -> dict:
    text = (SKILL / "references" / "adapter.md").read_text(encoding="utf-8")
    namespace: dict = {"__name__": "skill_reference"}
    for block in re.findall(r"```python\n(.*?)```", text, re.S):
        exec(compile(block, "adapter.md", "exec"), namespace)
    return namespace


def jpeg(size: tuple[int, int], orientation: int = 1) -> bytes:
    exif = Image.Exif()
    exif[0x0112] = orientation
    buf = io.BytesIO()
    Image.new("RGB", size, (90, 120, 150)).save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def decode_data_uri(uri: str) -> bytes:
    return base64.b64decode(uri.split(",", 1)[1])


class FakeQueue:
    """Just enough of queue.fal.run for one request id."""

    def __init__(self, *, submit=(200,), result=(200, {}), steps=2, hang=False):
        self.submit = list(submit)
        self.results = result if isinstance(result, list) else [result]
        self.steps, self.hang, self.cancelled = steps, hang, False
        self.requests: list[httpx.Request] = []

    def count(self, method: str, suffix: str = "") -> int:
        return sum(r.method == method and r.url.path.endswith(suffix) for r in self.requests)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        base = f"{QUEUE}/requests/req_1"
        if request.method == "POST":
            status = self.submit.pop(0) if len(self.submit) > 1 else self.submit[0]
            if status != 200:
                return httpx.Response(status, json={"detail": "bad timeout header", "error_type": "bad_request"})
            return httpx.Response(200, json={"request_id": "req_1", "response_url": base,
                                             "status_url": base + "/status", "cancel_url": base + "/cancel"})
        if request.method == "PUT":
            self.cancelled = True
            return httpx.Response(200, json={"success": True})
        if request.url.path.endswith("/status"):
            polls = self.count("GET", "/status")
            if (self.hang and not self.cancelled) or (not self.hang and polls <= self.steps):
                state = "IN_QUEUE" if polls == 1 else "IN_PROGRESS"
                body = {"status": state, "request_id": "req_1", "queue_position": 0, "logs": None}
                return httpx.Response(200, json=body)
            return httpx.Response(200, json={"status": "COMPLETED", "request_id": "req_1", "logs": None})
        status, body = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        return httpx.Response(status, json=body, headers={"x-fal-request-id": "req_1"})


def mock_client(queue: FakeQueue) -> fal_client.SyncClient:
    """A real SyncClient whose httpx client has the same config but a mock transport."""
    client = fal_client.SyncClient(key=KEY)
    http = httpx.Client(transport=httpx.MockTransport(queue), timeout=client.default_timeout,
                        headers={"Authorization": client._auth.header_value}, follow_redirects=True)
    object.__setattr__(client, "_client", http)
    return client


def main() -> int:
    for dist, pin in PINS.items():
        check(f"{dist}=={pin} installed", version(dist) == pin)

    for name, params in SURFACE.items():
        sig = inspect.signature(getattr(fal_client, name))
        check(f"fal_client.{name} has {sorted(params)}", params <= set(sig.parameters))
    for name in ("subscribe", "submit", "status", "result", "cancel", "upload"):
        sig = inspect.signature(getattr(fal_client.SyncClient, name))
        check(f"SyncClient.{name} matches fal_client.{name}", SURFACE[name] <= set(sig.parameters))
    check("client_timeout exists on subscribe only",
          "client_timeout" not in inspect.signature(fal_client.submit).parameters)
    client_sig = inspect.signature(fal_client.SyncClient)
    check("SyncClient(key=None, default_timeout=120.0)",
          client_sig.parameters["key"].default is None and client_sig.parameters["default_timeout"].default == 120.0)
    check("FalClientHTTPError carries status_code, response, error_type",
          {"status_code", "response", "error_type"} <= {f.name for f in dataclasses.fields(fal_client.FalClientHTTPError)})
    check("FalClientTimeoutError carries timeout, request_id and is a TimeoutError",
          {"timeout", "request_id"} <= {f.name for f in dataclasses.fields(fal_client.FalClientTimeoutError)}
          and issubclass(fal_client.FalClientTimeoutError, TimeoutError))
    private = fal_client.StorageSettings(expires_in="1h", initial_acl=fal_client.StorageACL(default="forbid"))
    check("StorageSettings(expires_in='1h', initial_acl=StorageACL(default='forbid')) builds",
          private.expires_in == "1h" and private.initial_acl.default == "forbid")

    ref = load_reference()

    if len(sys.argv) > 1:
        live = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["components"]["schemas"]
        check("embedded schema copy matches the downloaded OpenAPI document",
              {name: trim(live[name]) for name in SCHEMAS} == SCHEMAS)

    # Images: upright original and mask at its size.
    plain = jpeg((4032, 3024))
    rotated = jpeg((4032, 3024), orientation=6)
    same, size = ref["upright_jpeg"](plain)
    check("orientation 1: original bytes sent unchanged", same is plain and size == (4032, 3024))
    upright, usize = ref["upright_jpeg"](rotated)
    with Image.open(io.BytesIO(upright)) as img:
        tag = img.getexif().get(0x0112, 1)
    check("orientation 6: re-encoded upright 3024x4032 with no rotation tag", usize == (3024, 4032) and tag == 1)

    square = [(100.0, 100.0), (300.0, 100.0), (300.0, 300.0), (100.0, 300.0)]
    second = [(800.0, 500.0), (900.0, 500.0), (900.0, 600.0)]
    mask = ref["mask_png"]([square, second], (1280, 960), (4032, 3024))
    with Image.open(io.BytesIO(mask)) as m:
        pixels = (m.size, m.mode, m.getpixel((630, 630)), m.getpixel((200, 200)), m.getpixel((2700, 1620)))
    check("mask PNG is 4032x3024 L, polygons scaled and filled, background 0",
          pixels == ((4032, 3024), "L", 255, 0, 255))

    # Arguments against the live input schema.
    args = ref["build_arguments"](plain, mask, "brass desk lamp")
    errors = list(validator("Sam33dObjectsInput").iter_errors(args))
    check("arguments validate against SAM3DObjectInput", not errors)
    check("every argument key is a declared property", set(args) <= set(SCHEMAS["Sam33dObjectsInput"]["properties"]))
    check("prompt is the label, never the 'car' default", args["prompt"] == "brass desk lamp")
    check("image_url and mask_urls are data URIs that round-trip",
          args["image_url"].startswith("data:image/jpeg;base64,") and decode_data_uri(args["image_url"]) == plain
          and len(args["mask_urls"]) == 1 and decode_data_uri(args["mask_urls"][0]) == mask)
    check("schema itself would accept the misspelled key mask_url (why the key check exists)",
          validator("Sam33dObjectsInput").is_valid({**args, "mask_url": "x"}))
    check("array-shaped box prompt is rejected",
          not validator("Sam33dObjectsInput").is_valid({**args, "box_prompts": [[1, 2, 3, 4]]}))
    check("object-shaped box and point prompts are accepted",
          validator("Sam33dObjectsInput").is_valid({**args,
              "box_prompts": [{"x_min": 1, "y_min": 2, "x_max": 30, "y_max": 40, "object_id": 1}],
              "point_prompts": [{"x": 10, "y": 20, "label": 1, "object_id": 1}]}))
    check("detection_threshold below 0.1 is rejected",
          not validator("Sam33dObjectsInput").is_valid({**args, "detection_threshold": 0.05}))
    key = ref["cache_key"]
    base_key = key(plain, mask, "brass desk lamp")
    check("cache key is stable and moves with seed, mask, label and attempt",
          base_key == key(plain, mask, "brass desk lamp")
          and len({base_key, key(plain, mask, "brass desk lamp", seed=8), key(plain, mask + b"x", "brass desk lamp"),
                   key(plain, mask, "desk lamp"), key(plain, mask, "brass desk lamp", attempt=1)}) == 5)

    # Output schema and parsing.
    meta = [{"object_index": 0, "rotation": [[0.0, 0.0, 0.0, 1.0]], "translation": [[0.1, 0.2, 1.5]],
             "scale": [[0.4, 0.4, 0.4]], "camera_pose": None}]
    result = {"gaussian_splat": {"url": "https://v3b.fal.media/files/b/x/object.ply"},
              "model_glb": {"url": "https://v3b.fal.media/files/b/x/object.glb"}, "metadata": meta}
    check("sample result validates against SAM3DObjectOutput", validator("Sam33dObjectsOutput").is_valid(result))
    check("flat rotation list is outside the schema (fields are lists of lists)",
          not validator("Sam33dObjectsOutput").is_valid({**result, "metadata": [{"object_index": 0, "rotation": [0, 0, 0, 1]}]}))
    rec = ref["parse_result"](result)
    check("parse_result keeps GLB, splat and raw metadata",
          (rec.glb_url, rec.splat_url, rec.metadata) == (result["model_glb"]["url"], result["gaussian_splat"]["url"], meta))
    no_mesh = ref["NoMeshError"]
    refused = [{k: v for k, v in result.items() if k != "model_glb"},
               {**result, "model_glb": {"url": ref["SCHEMA_SAMPLE_GLB"]}},
               {k: v for k, v in result.items() if k != "gaussian_splat"},
               {k: v for k, v in result.items() if k != "metadata"}]
    check("missing model_glb, gaussian_splat or metadata, and the sample URL, raise NoMeshError",
          all(raises(no_mesh, ref["parse_result"], r) is not None for r in refused))

    # Queue flow through the real client.
    queue = FakeQueue(result=(200, result))
    seen: list[str] = []
    started = time.monotonic()
    out = ref["run_queued"](mock_client(queue), args, on_enqueue=seen.append)
    post = next(r for r in queue.requests if r.method == "POST")
    check("subscribe returns the result after IN_QUEUE, IN_PROGRESS, COMPLETED", out == result)
    check("submit POSTs the arguments to queue.fal.run with the key",
          str(post.url) == QUEUE and json.loads(post.content) == args and post.headers["authorization"] == f"Key {KEY}")
    check("privacy and timeout headers are on the submit request",
          post.headers.get("x-fal-store-io") == "0"
          and json.loads(post.headers["x-fal-object-lifecycle-preference"]) == {"expiration_duration_seconds": 3600}
          and post.headers.get("x-fal-request-timeout") == "120.0")
    check("on_enqueue receives the request id", seen == ["req_1"])
    check("polls at the 1 s interval (3 status calls, about 2 s)",
          queue.count("GET", "/status") == 3 and 1.8 < time.monotonic() - started < 6)

    queue = FakeQueue(submit=(429, 200), result=(200, result), steps=0)
    check("429 on submit is retried by fal-client and then succeeds",
          ref["run_queued"](mock_client(queue), args) == result and queue.count("POST") == 2)

    queue = FakeQueue(submit=(400,), steps=0)
    exc = raises(fal_client.FalClientHTTPError, ref["run_queued"], mock_client(queue), args)
    failure = ref["classify"](exc) if exc else None
    check("400 on submit raises at once, no retry, code bad_request",
          exc is not None and exc.status_code == 400 and queue.count("POST") == 1
          and failure == ref["Failure"]("bad_request", 400, True))

    model_error = {"detail": [{"loc": ["body", "image_url"], "msg": "Failed to load the image",
                               "type": "image_load_error", "url": "https://docs.fal.ai/errors#image_load_error"}]}
    queue = FakeQueue(result=(422, model_error), steps=0)
    exc = raises(fal_client.FalClientHTTPError, ref["run_queued"], mock_client(queue), args)
    check("422 from the result raises with the model error type, one result fetch",
          exc is not None and exc.status_code == 422 and queue.count("GET", "/req_1") == 1
          and ref["classify"](exc) == ref["Failure"]("image_load_error", 422, True))

    runner_503 = (503, {"detail": "Runner disconnected", "error_type": "runner_disconnected"})
    queue = FakeQueue(result=runner_503, steps=0)
    exc = raises(fal_client.FalClientHTTPError, ref["run_queued"], mock_client(queue), args)
    check("503 that reaches the result is not retried client-side and is settled unbilled",
          exc is not None and queue.count("GET", "/req_1") == 1
          and ref["classify"](exc) == ref["Failure"]("runner_disconnected", 503, False))

    model_500 = {"detail": [{"loc": ["body"], "msg": "Internal server error", "type": "internal_server_error",
                             "url": "https://docs.fal.ai/errors#internal_server_error"}]}
    queue = FakeQueue(result=(500, model_500), steps=0)
    exc = raises(fal_client.FalClientHTTPError, ref["run_queued"], mock_client(queue), args)
    check("500 model error maps to its detail type and is settled unbilled",
          exc is not None and ref["classify"](exc) == ref["Failure"]("internal_server_error", 500, False))

    sleeps: list[float] = []
    client = mock_client(queue := FakeQueue(result=[runner_503, (200, result)], steps=0))
    out = ref["retry_once"](lambda: ref["run_queued"](client, args), sleep=sleeps.append)
    check("retry_once retries a surfaced 5xx once, after 2 to 4 s, and returns the result",
          out == result and queue.count("POST") == 2 and len(sleeps) == 1 and 2.0 <= sleeps[0] <= 4.0)

    sleeps.clear()
    client = mock_client(queue := FakeQueue(result=runner_503, steps=0))
    exc = raises(fal_client.FalClientHTTPError, ref["retry_once"], lambda: ref["run_queued"](client, args),
                 sleep=sleeps.append)
    check("retry_once gives up after the second 5xx", exc is not None and queue.count("POST") == 2 and len(sleeps) == 1)

    sleeps.clear()
    client = mock_client(queue := FakeQueue(result=(422, model_error), steps=0))
    exc = raises(fal_client.FalClientHTTPError, ref["retry_once"], lambda: ref["run_queued"](client, args),
                 sleep=sleeps.append)
    check("retry_once never retries a 422", exc is not None and queue.count("POST") == 1 and not sleeps)

    check("classify settles every caught type: NoMeshError and a plain FalClientError are billed",
          ref["classify"](no_mesh("x")) == ref["Failure"]("fal_bad_output", 200, True)
          and ref["classify"](fal_client.FalClientError("x")) == ref["Failure"]("fal_client_error", None, True))

    queue = FakeQueue(hang=True)
    started = time.monotonic()
    exc = raises(fal_client.FalClientTimeoutError, ref["run_queued"], mock_client(queue), args,
                 start_timeout=1.5, client_timeout=2)
    elapsed = time.monotonic() - started
    time.sleep(1.5)  # let the background poller see COMPLETED and exit
    check("client_timeout raises FalClientTimeoutError with the request id and cancels the request",
          exc is not None and exc.request_id == "req_1" and queue.cancelled and 1.9 < elapsed < 4
          and ref["classify"](exc) == ref["Failure"]("fal_client_timeout", None, True))

    def cdn(request: httpx.Request) -> httpx.Response:
        payload = {"/object.glb": b"glTF\x02\x00\x00\x00", "/object.ply": b"ply\nformat binary_little_endian 1.0\n"}
        return httpx.Response(200, content=payload.get(request.url.path, b"<html>expired</html>"))

    with httpx.Client(transport=httpx.MockTransport(cdn), base_url="https://v3b.fal.media") as http:
        glb = ref["fetch"](http, "https://v3b.fal.media/object.glb", ref["GLB_MAGIC"])
        ply = ref["fetch"](http, "https://v3b.fal.media/object.ply", ref["PLY_MAGIC"])
        bad = raises(no_mesh, ref["fetch"], http, "https://v3b.fal.media/gone.glb", ref["GLB_MAGIC"])
    check("fetch checks glTF and ply signatures and refuses anything else, with no URL in the error",
          glb.startswith(b"glTF") and ply.startswith(b"ply") and bad is not None and "http" not in str(bad))

    if failures:
        print(f"selfcheck FAILED: {len(failures)} check(s)")
        return 1
    print("selfcheck passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
