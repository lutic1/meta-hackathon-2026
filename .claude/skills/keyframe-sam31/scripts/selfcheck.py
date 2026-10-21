"""Offline check for the keyframe-sam31 skill: no network, no keys.

Asserts the pinned versions and API surface, then executes the python blocks in
references/*.md and drives them through httpx.MockTransport with a synthetic
sam-3.1 event stream built from Meta's documented lossless example line.

    uv run --no-project --with meta-sam-parser==0.1.0 --with httpx==0.28.1 \
        python .claude/skills/keyframe-sam31/scripts/selfcheck.py
"""

import asyncio
import inspect
import json
import logging
import re
import sys
from importlib.metadata import version
from pathlib import Path

import httpx
import meta_sam_parser as msp

SKILL = Path(__file__).resolve().parent.parent
PINS = {"meta-sam-parser": "0.1.0", "httpx": "0.28.1"}
SIGNATURES = {
    "parse_responses_stream": "(source: 'AsyncIterable[ResponsesEventLike]', format: 'ResponseFormat[EventT, ResultT]') -> 'ParsedResponsesStream[EventT, ResultT]'",
    "image_segmentation_format": "() -> 'ResponseFormat[ImageSegmentationSnapshot, ImageSegmentationResult]'",
    "decode_mask_to_raster": "(mask: 'SegmentationMask') -> 'bytes'",
    "decode_mask_to_rle": "(mask: 'SegmentationMask') -> 'RLEObject'",
    "decode_mask_to_svg_path": "(mask: 'SegmentationMask') -> 'str'",
}
# From dev.meta.ai/docs/sam/reading-segmentation (video example, frame 0; two lossless masks).
LINE = (
    "<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,60,~!!!!M!0c[0o91w?q1!pIH4pPRVp2B3'7`e.ioeAf6-k/#Xd8%dX9x(|>"
    ",1<|box;x1=155;y1=228;x2=202;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,48,~!!!!J!0c[q=Pj_zs=*4C4(/./x#:/`S_GnD`=o3?X{emCgO$y@|>\n"
)
LANE = {"item_id": "msg_1", "output_index": 0, "content_index": 0}
failures: list[str] = []
warnings: list[str] = []


class Collect(logging.Handler):
    """Records the reference code's log messages (the logger is named after the exec namespace)."""

    def emit(self, record: logging.LogRecord) -> None:
        warnings.append(record.getMessage())


def check(name: str, ok: bool) -> None:
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failures.append(name)


def load_reference_code() -> dict:
    namespace: dict = {"__name__": "skill_reference"}
    for name in ("masks-to-polygons.md", "request-and-stream.md"):
        text = (SKILL / "references" / name).read_text(encoding="utf-8")
        for block in re.findall(r"```python\n(.*?)```", text, re.S):
            exec(compile(block, name, "exec"), namespace)
    return namespace


def events_for(text: str, finalized: bool = True) -> list[dict]:
    events = [{"type": "response.created", "response": {"status": "in_progress"}}]
    if text:
        events.append({"type": "response.output_text.delta", **LANE, "delta": text})
    if finalized:
        events.append({"type": "response.content_part.done", **LANE,
                       "part": {"type": "output_text", "text": text}})
    events.append({"type": "response.completed", "response": {"status": "completed"}})
    return events


def sse(events: list[dict]) -> httpx.Response:
    body = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body.encode())


def raw(body: str, **headers: str) -> httpx.Response:
    return httpx.Response(200, headers=headers, stream=httpx.ByteStream(body.encode()))  # decoded on read


def failure(status: int, retry_after: str | None = None, body: bool = True) -> httpx.Response:
    envelope = {"error": {"message": "x", "type": "t", "param": None, "code": None}}
    return httpx.Response(status, headers={"retry-after": retry_after} if retry_after else {},
                          content=json.dumps(envelope).encode() if body else b"")


def call(ns: dict, *responses: httpx.Response):
    queue, seen, sleeps = list(responses), [], []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    body = ns["sam_request_body"]("mug", b"\xff\xd8\xff\xe0not-a-real-jpeg")
    try:
        return ns["call_with_one_retry"](client, "test-key", body, sleep=sleeps.append), seen, sleeps
    except ns["SamError"] as error:
        return error, seen, sleeps


async def aiter_list(items):
    for item in items:
        yield item


def main() -> int:
    for package, pinned in PINS.items():
        check(f"{package}=={pinned} installed", version(package) == pinned)
    for name, expected in SIGNATURES.items():
        check(f"signature {name}", str(inspect.signature(getattr(msp, name))) == expected)
    parser = msp.image_segmentation_format().create_parser()
    check("push/finish signatures",
          str(inspect.signature(parser.push)).startswith("(chunk: 'str', *, emit: 'bool' = True)")
          and str(inspect.signature(parser.finish)).startswith("(outcome: 'ResponseStreamOutcome')"))
    for name in ("CompletedOutcome", "IncompleteOutcome", "ResponsesStreamLaneError", "InvalidSegmentationMaskError"):
        check(f"export {name}", hasattr(msp, name))

    ns = load_reference_code()
    logging.getLogger("skill_reference").addHandler(Collect())

    result, seen, _ = call(ns, sse(events_for(LINE)))
    sent = json.loads(seen[0].content)
    parts = sent["input"][0]["content"]
    check("request: POST /v1/responses, bearer, SSE accept",
          str(seen[0].url) == "https://api.meta.ai/v1/responses"
          and seen[0].headers["authorization"] == "Bearer test-key"
          and seen[0].headers["accept"] == "text/event-stream")
    check("request: sam-3.1, stream, one input_text + one JPEG data URL",
          sent["model"] == "sam-3.1" and sent["stream"] is True and len(parts) == 2
          and parts[0] == {"type": "input_text", "text": "mug"}
          and parts[1]["image_url"].startswith("data:image/jpeg;base64,"))
    ns["check_result"](result)
    boxes = [r for r in result.records if r.kind == "box"]
    masks = [r for r in result.records if r.kind == "mask"]
    check("two box + two mask records, ids '0' and '1'",
          [b.object_id for b in boxes] == ["0", "1"] and len(masks) == 2)
    check("each mask raster is box-sized (H, W read from the mask)",
          all((m.mask.height, m.mask.width) == (m.bounds.bottom - m.bounds.top, m.bounds.right - m.bounds.left)
              for m in masks))
    raster = msp.decode_mask_to_raster(masks[0].mask)
    rle = msp.decode_mask_to_rle(masks[0].mask)
    check("raster/RLE/SVG decode",
          len(raster) == 27 * 60 and set(raster) <= {0, 1} and tuple(rle.size) == (27, 60)
          and msp.decode_mask_to_svg_path(masks[0].mask).startswith("M"))
    polygons = ns["polygons_from_result"](result)
    check("polygons in frame pixels, inside their boxes",
          len(polygons) == 2 and all(
              b.left <= x <= b.right and b.top <= y <= b.bottom
              for b, poly in zip(boxes, polygons) for x, y in poly))

    for label, finalized in (("finalized empty lane", True), ("no lane events", False)):
        warnings.clear()
        empty, _, _ = call(ns, sse(events_for("", finalized)))
        check(f"zero matches ({label}) -> completed, polygons None, "
              + ("no warning" if finalized else "warning logged"),
              empty.outcome.status == "completed" and ns["polygons_from_result"](empty) is None
              and bool(warnings) is not finalized)

    conflict = [{"type": "response.output_text.delta", **LANE, "delta": LINE},
                {"type": "response.content_part.done", **LANE, "part": {"type": "output_text", "text": ""}},
                {"type": "response.completed", "response": {"status": "completed"}}]
    error, seen, _ = call(ns, sse(conflict))
    check("finalized text conflicting with deltas -> response_lane, no retry",
          isinstance(error, ns["SamError"]) and error.code == "response_lane" and len(seen) == 1)

    no_delta_key = json.dumps({"type": "response.output_text.delta", **LANE})
    for label, response in (("non-JSON data line", raw("data: {not json\n\n")),
                            ("non-object data line", raw("data: 123\n\n")),
                            ("delta without 'delta'", raw(f"data: {no_delta_key}\n\n")),
                            ("undecodable gzip body", raw("not gzip", **{"content-encoding": "gzip"}))):
        error, seen, _ = call(ns, response)
        check(f"{label} -> malformed_stream, no retry",
              isinstance(error, ns["SamError"]) and error.code == "malformed_stream" and len(seen) == 1)

    check("AD-13 retry set: 429 and every 5xx, no other status",
          ns["RETRYABLE_STATUS"] == frozenset({429, *range(500, 600)}))
    for status in (400, 401, 403, 404, 413):
        error, seen, _ = call(ns, failure(status))
        check(f"{status} raised without retry", error.status == status and len(seen) == 1)
    error, seen, _ = call(ns, failure(404, body=False))
    check("404 with empty body handled", error.status == 404 and error.code is None and len(seen) == 1)
    error, seen, _ = call(ns, failure(429), failure(429))
    check("second 429 raised (one retry only)", error.status == 429 and len(seen) == 2)
    for status in (429, 500, 502, 503, 504):
        ok, seen, sleeps = call(ns, failure(status, retry_after="2"), sse(events_for(LINE)))
        check(f"{status} retried once after Retry-After", len(seen) == 2 and sleeps == [2.0] and len(ok.records) == 4)
    ok, seen, sleeps = call(ns, failure(500), sse(events_for(LINE)))
    check("5xx without Retry-After retried once after 0.5 to 1 s of jitter",
          len(seen) == 2 and len(sleeps) == 1 and 0.5 <= sleeps[0] <= 1.0 and len(ok.records) == 4)
    error, seen, sleeps = call(ns, failure(503, retry_after="60"), failure(503, retry_after="60"))
    check("Retry-After 60 waited at the 10 s cap, one retry, then raised",
          error.status == 503 and len(seen) == 2 and sleeps == [10.0])
    for code in sorted(ns["RETRYABLE_STREAM_CODES"]):
        stream_error = sse([{"type": "error", "code": code, "message": "x"}])
        ok, seen, _ = call(ns, stream_error, sse(events_for(LINE)))
        check(f"mid-stream {code} retried once", len(seen) == 2 and len(ok.records) == 4)
    failed = sse([{"type": "response.failed",
                   "response": {"status": "failed", "error": {"code": "invalid_prompt", "message": "no"}}}])
    error, seen, _ = call(ns, failed)
    check("response.failed with a non-retryable code raised, no retry",
          error.code == "invalid_prompt" and len(seen) == 1)
    refusal = sse([{"type": "response.content_part.done", **LANE, "part": {"type": "refusal", "refusal": "no"}}])
    error, seen, _ = call(ns, refusal)
    check("refusal content part -> response_refusal, no retry",
          error.code == "response_refusal" and len(seen) == 1)
    delta_only = {"type": "response.output_text.delta", **LANE, "delta": LINE}
    cut, _, _ = call(ns, httpx.Response(200, content=f"data: {json.dumps(delta_only)}\n\n".encode()))
    check("no terminal event -> incomplete eof",
          cut.outcome.status == "incomplete" and cut.outcome.reason == "eof")
    try:
        ns["check_result"](cut)
        check("check_result rejects incomplete", False)
    except ns["SamError"]:
        check("check_result rejects incomplete", True)

    async_result = asyncio.run(ns["parse_image_events"](aiter_list(events_for(LINE))))
    check("parse_responses_stream path gives the same records",
          [(r.kind, r.object_id) for r in async_result.records] == [(r.kind, r.object_id) for r in result.records])
    try:
        asyncio.run(ns["parse_image_events"](aiter_list(events_for("", finalized=False))))
        check("parse_responses_stream rejects completed-without-lane", False)
    except msp.ResponsesStreamLaneError as error:
        check("parse_responses_stream rejects completed-without-lane (response_lane)", error.code == "response_lane")

    square = lambda l, t, r, b: [(l, t), (r, t), (r, b), (l, b)]
    select = ns["select_instances"]
    check("selection: best IoU kept",
          select([square(110, 110, 290, 290), square(600, 600, 800, 800)], (100, 100, 300, 300), 1280, 960, False)
          == [square(110, 110, 290, 290)])
    check("selection: under 1% of the frame dropped",
          select([square(100, 100, 110, 110)], (100, 100, 300, 300), 1280, 960, False) == [])
    books = [square(100 + 40 * i, 100, 140 + 40 * i, 300) for i in range(5)]
    check("selection: plural, 2 books grouped", len(select(books[:2], (100, 100, 180, 300), 640, 480, True)) == 2)
    check("selection: plural, 5 books score IoU 0.2 each (known issue) -> single fallback",
          len(select(books, (100, 100, 300, 300), 640, 480, True)) == 1)

    print(f"{'OK' if not failures else 'FAILED'}: {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
