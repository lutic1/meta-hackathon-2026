"""Story 2.7: the Meta adapter serves chat, segment and image through the cache and the ledger, offline on recorded fixtures."""

import ast
import base64
import json
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.config import Settings
from src.domain.ledger import SEED_USD, CallKind, SpendCapExceeded, fold, image_cost_usd, sam_cost_usd, spark_cost_usd
from src.domain.schema import ArchitectResponse
from src.providers import meta_api
from src.providers.base import ChatMessage, ChatResponse, ImageResponse, ProviderError
from src.providers.cache import GuardedCalls, cache_key
from src.providers.meta_api import (
    CHAT_RETRYABLE_STATUS,
    IMAGE_BUDGET_S,
    IMAGE_RETRYABLE_STATUS,
    RATE_LIMITS,
    RETRY_ON_CONNECT,
    SAM_RETRYABLE_STATUS,
    SEGMENT_BUDGET_S,
    MetaModelProvider,
    RateLimit,
    mask_polygon,
    svg_rings,
)
from src.providers.spend import SpendLedger
from tests.providers.replay import load
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

MODULE = Path(__file__).resolve().parents[2] / "src/providers/meta_api.py"
CHAT = "muse-spark-1.3/chat-three-objects"
IMAGE = "muse-image-1.0/portrait-riddler"
SEGMENT = "sam-3.1/segment-two-masks"
NO_MASK = "sam-3.1/segment-no-mask"
MESSAGES = [ChatMessage(role="system", content="You list objects."), ChatMessage(role="user", content="What do you see?")]
PHOTOS = [b"\xff\xd8\xff\xe0photo-a\xff\xd9", b"\xff\xd8\xff\xe0photo-b\xff\xd9"]
ARCHITECT_BUDGET_S = 15.0


class Replay:
    """A provider over a transport that answers each request from `items` in order, counting requests and waits.

    An item is a fixture name, an `httpx.Response`, or an httpx exception
    class to raise; the clock readings stand in for `time.monotonic`.
    """

    def __init__(
        self,
        *items: str | httpx.Response | type[httpx.RequestError],
        chat_kind: CallKind = "vision",
        budget_s: float = ARCHITECT_BUDGET_S,
        cap_usd: float = 60.0,
        cache_enabled: bool = True,
        clock: list[float] | None = None,
        api_key: str | None = "test-key",
        base_url: str | None = None,
    ) -> None:
        self.items = [fixture(item) if isinstance(item, str) else item for item in items]
        self.seen: list[httpx.Request] = []
        self.waits: list[float] = []
        self.store = MemoryLedgerStore()
        self.cache = MemoryCache()
        readings = iter(clock or [])
        self.provider = MetaModelProvider(
            api_key,
            base_url,
            calls=GuardedCalls(self.cache, SpendLedger(self.store, cap_usd=cap_usd), host="api.meta.ai", enabled=cache_enabled),
            chat_kind=chat_kind,
            budget_s=budget_s,
            transport=httpx.MockTransport(self._handle),
            sleep=self.waits.append,
            clock=(lambda: next(readings)) if clock else (lambda: 0.0),
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        item = self.items.pop(0)
        if isinstance(item, type):
            raise item("simulated", request=request)
        return item

    def body(self, index: int = 0) -> dict[str, Any]:
        return json.loads(self.seen[index].content)

    def entries(self):
        return fold(self.store.rows)


def fixture(name: str) -> httpx.Response:
    recorded = load(name)
    return httpx.Response(recorded.status, json=recorded.body)


def error(status: int, code: str = "server_error", **headers: str) -> httpx.Response:
    envelope = {"error": {"message": f"simulated {status}", "type": code, "param": None, "code": None}}
    return httpx.Response(status, headers=headers, json=envelope)


def chat(replay: Replay, **overrides: Any) -> ChatResponse:
    args: dict[str, Any] = dict(images=PHOTOS, response_schema=ArchitectResponse, reasoning_effort="low")
    args.update(overrides)
    return replay.provider.chat(MESSAGES, **args)


# --- Chat Completions for muse-spark-1.3 --------------------------------------


def test_chat_sends_images_as_data_urls_with_a_json_schema_response_format():
    replay = Replay(CHAT)
    response = chat(replay)
    request = replay.seen[0]
    assert (request.method, str(request.url)) == ("POST", "https://api.meta.ai/v1/chat/completions")
    assert request.headers["authorization"] == "Bearer test-key"
    body = replay.body()
    assert body["model"] == "muse-spark-1.3"
    assert body["messages"][0] == {"role": "system", "content": "You list objects."}
    parts = body["messages"][1]["content"]
    assert body["messages"][1]["role"] == "user" and parts[0] == {"type": "text", "text": "What do you see?"}
    assert [p["type"] for p in parts[1:]] == ["image_url", "image_url"]
    for part, photo in zip(parts[1:], PHOTOS, strict=True):
        assert part["image_url"]["url"] == "data:image/jpeg;base64," + base64.b64encode(photo).decode()
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "ArchitectResponse", "schema": ArchitectResponse.model_json_schema(), "strict": False},
    }
    assert body["reasoning_effort"] == "low"
    assert not {"temperature", "max_tokens", "n", "max_output_tokens"} & body.keys()
    assert isinstance(response, ChatResponse)
    assert (response.text, response.model) == ("A brass lamp, a blue mug and a red book.", "muse-spark-1.3")
    assert response.usage["total_tokens"] == 1470 and response.raw == load(CHAT).body


def test_chat_without_images_or_schema_still_sends_reasoning_effort_explicitly():
    replay = Replay(CHAT)
    replay.provider.chat([ChatMessage(role="user", content="hello")], reasoning_effort="medium")
    body = replay.body()
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    assert body["reasoning_effort"] == "medium" and "response_format" not in body


def test_chat_default_effort_is_sent_and_none_is_refused_before_sending():
    replay = Replay(CHAT)
    chat(replay, reasoning_effort="low")
    assert replay.body()["reasoning_effort"] == "low"
    with pytest.raises(ValueError, match="reasoning_effort 'none'"):
        chat(replay, reasoning_effort="none")
    assert len(replay.seen) == 1


def test_images_without_a_user_message_are_refused_before_sending():
    replay = Replay(CHAT)
    with pytest.raises(ValueError, match="user message"):
        replay.provider.chat([ChatMessage(role="system", content="x")], images=PHOTOS)
    assert replay.seen == []


def test_chat_uses_the_requested_model_id():
    replay = Replay(CHAT)
    replay.provider.chat([ChatMessage(role="user", content="x")], model="muse-spark-1.3")
    assert replay.body()["model"] == "muse-spark-1.3"


def test_a_reply_cut_short_is_a_provider_error():
    body = json.loads(json.dumps(load(CHAT).body))
    body["choices"][0]["finish_reason"] = "length"
    replay = Replay(httpx.Response(200, json=body))
    with pytest.raises(ProviderError, match="200 length"):
        chat(replay)


def test_standard_tier_only_and_the_key_comes_from_settings():
    settings = Settings.from_env({"MODEL_API_KEY": "from-settings", "META_MODEL_API_BASE_URL": "https://example.test/v1/"})
    replay = Replay(CHAT, api_key=settings.model_api_key, base_url=settings.meta_model_api_base_url)
    chat(replay)
    assert str(replay.seen[0].url) == "https://example.test/v1/chat/completions"
    assert replay.seen[0].headers["authorization"] == "Bearer from-settings"
    source = MODULE.read_text()
    assert "contributor" not in source and "muse-spark-1.3-" not in source
    assert replay.body()["model"] == "muse-spark-1.3"


def test_the_key_is_sent_as_a_bearer_header_when_set():
    replay = Replay(CHAT, api_key="test-key")
    chat(replay)
    assert replay.seen[0].headers["authorization"] == "Bearer test-key"


@pytest.mark.parametrize("api_key", [None, ""])
def test_without_a_key_no_authorization_header_is_sent(api_key):
    replay = Replay(CHAT, api_key=api_key)
    chat(replay)
    assert "authorization" not in replay.seen[0].headers
    assert "authorization" not in replay.provider.client.headers


@pytest.mark.parametrize("kind", ["chat", "segment", "image"])
@pytest.mark.parametrize("status", [401, 403])
def test_a_keyless_auth_refusal_names_model_api_key_without_a_retry(kind, status):
    replay = Replay(error(status, "authentication_error"), CHAT, api_key=None)
    with pytest.raises(ProviderError, match="MODEL_API_KEY") as info:
        _call(replay, kind)
    assert (info.value.status, info.value.code) == (status, "missing_key")
    assert str(info.value) == f"{status} missing_key: {meta_api.KEYLESS_REFUSED_MESSAGE}"
    assert len(replay.seen) == 1 and replay.waits == [] and replay.cache.writes == 0


def test_module_uses_httpx_and_the_parser_only_and_reads_no_environment():
    tree = ast.parse(MODULE.read_text())
    imported = {alias.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert {"httpx", "meta_sam_parser"} <= imported
    assert not {"urllib", "os", "requests", "dotenv"} & imported


# --- Responses for sam-3.1 ---------------------------------------------------


def test_segment_sends_one_noun_phrase_with_the_stored_bytes():
    replay = Replay(SEGMENT)
    replay.provider.segment("mug", PHOTOS[0])
    assert str(replay.seen[0].url) == "https://api.meta.ai/v1/responses"
    body = replay.body()
    assert body["model"] == "sam-3.1" and body["store"] is False
    assert body["input"] == [{
        "type": "message",
        "role": "user",
        "content": [
            {"type": "input_text", "text": "mug"},
            {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(PHOTOS[0]).decode()},
        ],
    }]
    assert sum(part["type"] == "input_text" for part in body["input"][0]["content"]) == 1


def test_segment_decodes_each_mask_svg_path_into_a_frame_pixel_polygon():
    polygons = Replay(SEGMENT).provider.segment("mug", PHOTOS[0]).polygons
    assert polygons is not None and len(polygons) == 2
    # The recorded boxes are 211..270 x 228..254 (a 60x27 mask) and 155..202 x 228..254 (48x27).
    for polygon, (left, top, right, bottom) in zip(polygons, [(211, 228, 271, 255), (155, 228, 203, 255)], strict=True):
        assert len(polygon) >= 3
        assert all(left <= x <= right and top <= y <= bottom for x, y in polygon)
        xs, ys = [x for x, _ in polygon], [y for _, y in polygon]
        assert min(xs) < left + 2 and max(xs) > right - 2 and min(ys) < top + 2 and max(ys) > bottom - 2
        assert all(isinstance(x, float) and isinstance(y, float) for x, y in polygon)
    assert polygons[0][0] == (211 + 5.0, 228 + 0.5)  # the path's first `M4.5 0`, raster corner moved onto the box edge


def test_svg_path_rings_and_scaling_from_the_mask_raster_to_the_box():
    assert svg_rings("M0 0L3 0L3 3L0 3ZM1 1L2 1L2 2Z") == [[(0, 0), (3, 0), (3, 3), (0, 3)], [(1, 1), (2, 1), (2, 2)]]
    assert svg_rings("") == [] and mask_polygon("", (0, 0, 10, 10), 5, 5) is None
    # A 5x5 raster over a 10x20 box scales by 2 and 4 and keeps the largest ring.
    polygon = mask_polygon("M-0.5 -0.5L4.5 -0.5L4.5 4.5L-0.5 4.5ZM1 1L2 1L2 2Z", (100, 200, 110, 220), 5, 5)
    assert polygon == [(100.0, 200.0), (110.0, 200.0), (110.0, 220.0), (100.0, 220.0)]


def test_segment_with_no_mask_returns_none():
    replay = Replay(NO_MASK)
    assert replay.provider.segment("unicorn", PHOTOS[0]).polygons is None
    assert len(replay.seen) == 1


def test_segment_rejects_an_incomplete_or_refused_response():
    incomplete = {**load(NO_MASK).body, "status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    with pytest.raises(ProviderError, match="incomplete"):
        Replay(httpx.Response(200, json=incomplete)).provider.segment("mug", PHOTOS[0])
    refused = json.loads(json.dumps(load(NO_MASK).body))
    refused["output"][0]["content"] = [{"type": "refusal", "refusal": "no"}]
    with pytest.raises(ProviderError, match="refusal"):
        Replay(httpx.Response(200, json=refused)).provider.segment("mug", PHOTOS[0])


# --- Images for muse-image-1.0 -----------------------------------------------


def test_generate_image_returns_an_image_response_priced_at_one_cent():
    replay = Replay(IMAGE)
    image = replay.provider.generate_image("a riddler wizard")
    assert str(replay.seen[0].url) == "https://api.meta.ai/v1/images/generations"
    body = replay.body()
    assert body == {"model": "muse-image-1.0", "prompt": "a riddler wizard", "n": 1, "response_format": "b64_json"}
    assert isinstance(image, ImageResponse)
    assert image.data.startswith("UklGR") and image.model == "muse-image-1.0" and image.raw == load(IMAGE).body
    [entry] = replay.entries()
    assert (entry.kind, entry.status, entry.usd) == ("image", "settled", 0.01)
    assert entry.usd == image_cost_usd(1)


# --- One retry inside one ledger entry (AD-13, AD-6) --------------------------


def _call(replay: Replay, kind: str) -> Any:
    if kind == "chat":
        return chat(replay)
    if kind == "segment":
        return replay.provider.segment("mug", PHOTOS[0])
    return replay.provider.generate_image("a portrait")


RETRIED = [
    ("chat", CHAT, 429), ("chat", CHAT, 500), ("chat", CHAT, 503),
    ("chat", CHAT, httpx.ConnectError), ("chat", CHAT, httpx.ConnectTimeout),
    ("segment", SEGMENT, 429), ("segment", SEGMENT, 500), ("segment", SEGMENT, 503), ("segment", SEGMENT, httpx.ConnectError),
    ("image", IMAGE, 429), ("image", IMAGE, 503), ("image", IMAGE, httpx.ConnectTimeout),
]


@pytest.mark.parametrize(("kind", "name", "first"), RETRIED, ids=[f"{k}-{getattr(f, '__name__', f)}" for k, _, f in RETRIED])
def test_a_retryable_failure_is_retried_exactly_once_with_backoff_in_one_ledger_entry(kind, name, first):
    replay = Replay(error(first) if isinstance(first, int) else first, name)
    result = _call(replay, kind)
    assert result is not None and len(replay.seen) == 2
    assert len(replay.waits) == 1 and 0.5 <= replay.waits[0] <= 1.0
    [entry] = replay.entries()
    assert entry.status == "settled"


@pytest.mark.parametrize("first", [429, 500, 503, httpx.ConnectError, httpx.ConnectTimeout])
def test_a_second_failure_raises_provider_error_after_two_requests(first):
    second = error(first) if isinstance(first, int) else first
    replay = Replay(error(first) if isinstance(first, int) else first, second)
    with pytest.raises(ProviderError) as info:
        chat(replay)
    assert len(replay.seen) == 2 and len(replay.waits) == 1
    assert info.value.status == (first if isinstance(first, int) else None)
    assert replay.cache.writes == 0


NOT_RETRIED = [
    ("chat", CHAT, 502), ("chat", CHAT, 504), ("chat", CHAT, 501), ("chat", CHAT, 599), ("chat", CHAT, 400),
    ("chat", CHAT, 401), ("chat", CHAT, httpx.ReadTimeout), ("chat", CHAT, httpx.RemoteProtocolError),
    ("segment", SEGMENT, 502), ("segment", SEGMENT, 504), ("segment", SEGMENT, 400), ("segment", SEGMENT, httpx.ReadTimeout),
    ("image", IMAGE, 500), ("image", IMAGE, 502), ("image", IMAGE, 504), ("image", IMAGE, 400), ("image", IMAGE, httpx.ReadTimeout),
]


@pytest.mark.parametrize(("kind", "name", "first"), NOT_RETRIED, ids=[f"{k}-{getattr(f, '__name__', f)}" for k, _, f in NOT_RETRIED])
def test_what_is_never_retried_raises_provider_error_after_one_request(kind, name, first):
    replay = Replay(error(first) if isinstance(first, int) else first, name)
    with pytest.raises(ProviderError) as info:
        _call(replay, kind)
    assert len(replay.seen) == 1 and replay.waits == []
    if isinstance(first, int):
        assert info.value.status == first
    else:
        assert info.value.status is None and info.value.code == ("timeout" if first is httpx.ReadTimeout else "transport_error")
    assert replay.cache.writes == 0 and replay.items  # the success reply was never requested


# --- Settling a failed call (decision 24): zero only when provably never sent ---------


@pytest.mark.parametrize("kind", ["chat", "segment", "image"])
@pytest.mark.parametrize("second", [httpx.ConnectError, httpx.ConnectTimeout])
def test_a_call_that_never_reached_the_host_settles_at_zero_and_keeps_its_entry(kind, second):
    name = {"chat": CHAT, "segment": SEGMENT, "image": IMAGE}[kind]
    replay = Replay(httpx.ConnectError, second, name)
    with pytest.raises(ProviderError) as info:
        _call(replay, kind)
    assert info.value.dispatched is False and len(replay.seen) == 2
    assert [(e.status, e.usd) for e in replay.store.rows][1:] == [("settled", 0.0)]
    assert replay.store.rows[0].status == "reserved" and replay.store.rows[0].call_id == replay.store.rows[1].call_id


@pytest.mark.parametrize("items", [
    (httpx.ReadTimeout,), (httpx.RemoteProtocolError,), (error(401),), (error(502),),
    (httpx.ConnectError, error(500)), (error(503), httpx.ConnectError), (httpx.ConnectError, httpx.ReadTimeout),
], ids=["ReadTimeout", "RemoteProtocolError", "401", "502", "ConnectError-500", "503-ConnectError", "ConnectError-ReadTimeout"])
def test_a_call_that_may_have_reached_the_host_keeps_its_reserved_estimate(items):
    replay = Replay(*items, CHAT)
    with pytest.raises(ProviderError) as info:
        chat(replay)
    assert info.value.dispatched is True
    assert [(e.status, e.usd) for e in replay.store.rows] == [("reserved", SEED_USD["vision"])]


def test_error_bodies_without_the_envelope_still_become_provider_errors():
    with pytest.raises(ProviderError, match="400 unparsed"):
        chat(Replay(httpx.Response(400, json={"error": "bad"})))
    with pytest.raises(ProviderError, match="404 no_body"):
        chat(Replay(httpx.Response(404)))


def test_live_host_is_blocked_by_the_offline_guard():
    provider = MetaModelProvider(
        "k", calls=Replay(CHAT).provider._calls, chat_kind="vision", budget_s=ARCHITECT_BUDGET_S, sleep=lambda s: None
    )
    with pytest.raises(ProviderError, match="tests run offline"):
        provider.chat([ChatMessage(role="user", content="x")])


# --- Retry-After against the stage's remaining budget ------------------------


def test_retry_after_that_fits_the_budget_is_waited_in_full():
    replay = Replay(error(429, "rate_limit_error", **{"retry-after": "2"}), CHAT)
    chat(replay)
    assert replay.waits == [2.0] and len(replay.seen) == 2
    replay = Replay(error(429, "rate_limit_error", **{"retry-after": "0"}), CHAT)
    chat(replay)
    assert replay.waits == [0.0]
    soon = format_datetime(datetime.now(UTC) + timedelta(seconds=5), usegmt=True)
    replay = Replay(error(429, "rate_limit_error", **{"retry-after": soon}), CHAT)
    chat(replay)
    assert 3.0 <= replay.waits[0] <= 5.0


def test_retry_after_past_the_budget_fails_at_once():
    replay = Replay(error(429, "rate_limit_error", **{"retry-after": "60"}), CHAT, budget_s=30.0)
    with pytest.raises(ProviderError, match="429 rate_limit_error"):
        chat(replay)
    assert len(replay.seen) == 1 and replay.waits == []
    # 2 s asked with 1 s of the 15 s budget left, measured on the adapter's clock.
    replay = Replay(error(429, "rate_limit_error", **{"retry-after": "2"}), CHAT, clock=[0.0, 14.0])
    with pytest.raises(ProviderError):
        chat(replay)
    assert len(replay.seen) == 1 and replay.waits == []


def test_segment_and_image_budgets_decide_their_own_retry_after():
    replay = Replay(error(503, **{"retry-after": "60"}), SEGMENT)
    with pytest.raises(ProviderError, match="503"):
        replay.provider.segment("mug", PHOTOS[0])
    assert len(replay.seen) == 1 and replay.waits == [] and SEGMENT_BUDGET_S == 10.0
    replay = Replay(error(503, **{"retry-after": "60"}), IMAGE)
    replay.provider.generate_image("a portrait")
    assert replay.waits == [60.0] and len(replay.seen) == 2 and IMAGE_BUDGET_S == 120.0


# --- The guarded path: cache, ledger, observed cost ---------------------------


def test_every_call_goes_through_the_cache_and_then_the_ledger_guard_on_a_miss():
    replay = Replay(CHAT, SEGMENT, IMAGE)
    chat(replay)
    chat(replay)  # a hit: no request, no entry
    replay.provider.segment("mug", PHOTOS[0])
    replay.provider.segment("mug", PHOTOS[0])
    replay.provider.generate_image("a portrait")
    replay.provider.generate_image("a portrait")
    assert len(replay.seen) == 3 and replay.cache.writes == 3 and replay.cache.reads == 6
    assert [e.kind for e in replay.entries()] == ["vision", "sam", "image"]
    assert all(e.status == "settled" for e in replay.entries())


def test_attempt_joins_the_cache_key_so_a_regeneration_is_never_served_the_earlier_answer():
    """Story 2.20: the author stage passes the Regeneration count as `attempt` (AD-6)."""
    replay = Replay(CHAT, CHAT)
    chat(replay, attempt=0)
    chat(replay, attempt=1)  # a miss: attempt 1 is a new key
    chat(replay, attempt=1)  # a hit
    assert len(replay.seen) == 2 and len(replay.entries()) == 2
    key = cache_key(meta_api.CHAT_MODEL, messages=MESSAGES, response_schema=ArchitectResponse, reasoning_effort="low", images=PHOTOS, attempt=1)
    assert key in replay.cache.rows


def test_chat_tags_its_ledger_entry_with_the_job_and_stage_and_returns_the_receipt():
    """Story 2.20: provenance sums spend per stage from these tags, and the call row reads the receipt (AD-16)."""
    replay = Replay(CHAT)
    job_id = "job_01JBZ0000000000000000000AA"
    billed = chat(replay, job_id=job_id, stage="architect")
    assert [(e.job_id, e.stage) for e in replay.store.rows] == [(job_id, "architect"), (job_id, "architect")]
    settled = replay.entries()[0]
    assert billed.receipt is not None
    assert (billed.receipt.call_id, billed.receipt.host, billed.receipt.cached) == (settled.call_id, "api.meta.ai", False)
    assert billed.receipt.spend_usd == settled.usd
    cached = chat(replay, job_id=job_id, stage="architect")
    assert cached.receipt is not None and (cached.receipt.cached, cached.receipt.spend_usd) == (True, 0.0)


def test_cache_off_still_guards_every_call():
    replay = Replay(CHAT, CHAT, cache_enabled=False)
    chat(replay)
    chat(replay)
    assert len(replay.seen) == 2 and replay.cache.reads == 0 and len(replay.entries()) == 2


def test_the_guard_refuses_before_any_request_and_a_hit_is_never_refused():
    replay = Replay(CHAT, cap_usd=0.0)
    with pytest.raises(SpendCapExceeded):
        chat(replay)
    assert replay.seen == []
    replay = Replay(CHAT, cap_usd=60.0)
    chat(replay)
    replay.provider._calls._ledger.cap_usd = 0.0
    assert chat(replay).text == "A brass lamp, a blue mug and a red book."


def test_observed_cost_comes_from_the_returned_usage_at_budgets_rates():
    replay = Replay(CHAT, SEGMENT, IMAGE, chat_kind="riddler")
    chat(replay)
    replay.provider.segment("mug", PHOTOS[0])
    replay.provider.generate_image("a portrait")
    usage = load(CHAT).body["usage"]
    expected = {
        "riddler": spark_cost_usd(usage),
        "sam": sam_cost_usd(1),
        "image": image_cost_usd(1),
    }
    assert {e.kind: e.usd for e in replay.entries()} == expected
    assert expected["riddler"] == pytest.approx((1412 * 1.25 + 58 * 4.25) / 1_000_000)
    assert (expected["sam"], expected["image"]) == (0.0025, 0.01)


def test_model_ids_limits_and_retry_sets_match_budgets_and_ad_13():
    assert (meta_api.CHAT_MODEL, meta_api.SAM_MODEL, meta_api.IMAGE_MODEL) == ("muse-spark-1.3", "sam-3.1", "muse-image-1.0")
    assert RATE_LIMITS == {
        "muse-spark-1.3": RateLimit(rpm=3_000, tpm=4_000_000),
        "sam-3.1": RateLimit(rpm=3_000, tpm=None),
        "muse-image-1.0": RateLimit(rpm=150, tpm=None),
    }
    assert CHAT_RETRYABLE_STATUS == SAM_RETRYABLE_STATUS == {429, 500, 503}
    assert IMAGE_RETRYABLE_STATUS == {429, 503}
    assert RETRY_ON_CONNECT == (httpx.ConnectError, httpx.ConnectTimeout)
    assert meta_api.DEFAULT_BASE_URL == "https://api.meta.ai/v1"
