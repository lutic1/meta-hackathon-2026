"""Story 2.4: the model-call cache sits in front of the ledger guard (AD-6), and every call reports its row facts (AD-16)."""

import hashlib
import inspect
import json
import re
from typing import Any

import pytest

from src.domain.ledger import SEED_USD, SpendCapExceeded, fold
from src.domain.schema import ArchitectResponse, DryRunAnswers
from src.providers.base import ChatMessage, ChatResponse, ImageResponse
from src.providers.cache import CallReceipt, GuardedCalls, cache_key, schema_hash
from src.providers.mock import MockProvider
from src.providers.spend import SpendLedger, new_call_id
from tests.providers.test_spend import MemoryLedgerStore, settled
from tests.test_boundaries import REPO, _imports

CALL_ID = re.compile(r"^call_[0-9A-HJKMNP-TV-Z]{26}$")
HOST = "api.meta.ai"
JOB = "job_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SESSION = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SYSTEM = ChatMessage(role="system", content="You are the Riddler.")
USER = ChatMessage(role="user", content="Write four puzzles.")
PHOTO_A, PHOTO_B = b"\xff\xd8photo-a", b"\xff\xd8photo-b"
SQUARE = [(1.0, 1.0), (9.0, 1.0), (9.0, 9.0), (1.0, 9.0)]
REPLY = ChatResponse(text='{"ok": true}', model="muse-spark-1.3", usage={"prompt_tokens": 10, "completion_tokens": 5}, raw={"id": "x"})


class MemoryCache:
    """The `Cache` test double; `reads` and `writes` count every port call."""

    def __init__(self, **rows: dict[str, Any]) -> None:
        self.rows = dict(rows)
        self.reads = 0
        self.writes = 0

    def get(self, key: str) -> dict[str, Any] | None:
        self.reads += 1
        return self.rows.get(key)

    def put(self, key: str, value: dict[str, Any]) -> None:
        self.writes += 1
        self.rows[key] = value


class Provider:
    """A scripted paid call: returns each reply with its cost, counting how often it was reached."""

    def __init__(self, *replies: tuple[Any, float]) -> None:
        self.replies = list(replies)
        self.calls = 0

    def __call__(self) -> tuple[Any, float]:
        self.calls += 1
        return self.replies.pop(0)


def riddler_key(**overrides: Any) -> str:
    args: dict[str, Any] = dict(
        model="muse-spark-1.3", messages=[SYSTEM, USER], response_schema=ArchitectResponse,
        reasoning_effort="medium", images=[PHOTO_A, PHOTO_B], attempt=0,
    )
    args.update(overrides)
    return cache_key(args.pop("model"), **args)


def guarded(store: MemoryLedgerStore, cache: MemoryCache, *, cap: float = 60, enabled: bool = True) -> GuardedCalls:
    return GuardedCalls(cache, SpendLedger(store, cap_usd=cap), host=HOST, enabled=enabled)


# --- The key -----------------------------------------------------------------


def _reference_key(parts: list[str]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(f"{len(part.encode())}:".encode() + part.encode())
    return digest.hexdigest()


def test_the_key_is_sha256_over_model_schema_prompt_effort_image_hashes_and_attempt():
    schema = hashlib.sha256(json.dumps(ArchitectResponse.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    prompt = json.dumps([["system", SYSTEM.content], ["user", USER.content]], separators=(",", ":"))
    images = [hashlib.sha256(PHOTO_A).hexdigest(), hashlib.sha256(PHOTO_B).hexdigest()]
    assert schema_hash(ArchitectResponse) == schema
    assert riddler_key() == _reference_key(["muse-spark-1.3", schema, prompt, "medium", *images, "0"])
    assert re.fullmatch(r"[0-9a-f]{64}", riddler_key())


def test_a_text_only_call_leaves_the_image_segment_out_and_attempt_defaults_to_zero():
    prompt = json.dumps([["user", "a wizard"]], separators=(",", ":"))
    key = cache_key("muse-image-1.0", messages=[ChatMessage(role="user", content="a wizard")])
    assert key == _reference_key(["muse-image-1.0", "", prompt, "", "0"])
    assert key == cache_key("muse-image-1.0", messages=[ChatMessage(role="user", content="a wizard")], images=[], attempt=0)
    assert schema_hash(None) == ""


@pytest.mark.parametrize("change", [
    {"model": "muse-spark-1.2"},
    {"response_schema": DryRunAnswers},
    {"response_schema": None},
    {"messages": [ChatMessage(role="system", content="You are the Trickster."), USER]},
    {"messages": [USER]},
    {"reasoning_effort": "low"},
    {"images": [PHOTO_B, PHOTO_A]},
    {"images": [PHOTO_A]},
    {"images": [PHOTO_A, PHOTO_B, PHOTO_A]},
    {"attempt": 1},
])
def test_changing_any_single_component_changes_the_key(change):
    assert riddler_key(**change) != riddler_key()
    assert riddler_key(**change) == riddler_key(**change)


def test_the_prompt_segment_cannot_run_into_its_neighbours():
    left = cache_key("m", messages=[ChatMessage(role="user", content="ab")], reasoning_effort=None)
    right = cache_key("ma", messages=[ChatMessage(role="user", content="b")], reasoning_effort=None)
    assert left != right


# --- A hit never reaches the guard; a miss is guarded and priced once -------


def test_a_hit_is_served_before_the_guard_and_is_never_priced_or_refused():
    store = MemoryLedgerStore(settled(60.0))
    ledger = SpendLedger(store, cap_usd=60)
    with pytest.raises(SpendCapExceeded):
        ledger.guard("riddler")
    cache = MemoryCache(**{riddler_key(): {"text": "cached", "model": "muse-spark-1.3", "usage": {}, "raw": None}})
    calls = GuardedCalls(cache, ledger, host=HOST)
    provider = Provider()

    response, receipt = calls.chat(riddler_key(), "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")

    assert response == ChatResponse(text="cached", model="muse-spark-1.3", usage={}, raw=None)
    assert provider.calls == 0 and (cache.reads, cache.writes) == (1, 0)
    assert [e.usd for e in store.rows] == [60.0]
    assert receipt == CallReceipt(receipt.call_id, "muse-spark-1.3", HOST, cached=True, spend_usd=0.0)
    assert CALL_ID.match(receipt.call_id) and receipt.call_id not in {e.call_id for e in store.rows}


def test_a_miss_is_guarded_and_priced_exactly_once_and_stored_under_its_key():
    store = MemoryLedgerStore()
    cache = MemoryCache()
    calls = guarded(store, cache)
    provider = Provider((REPLY, 0.0125))

    response, receipt = calls.chat(riddler_key(), "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")

    assert response is REPLY and provider.calls == 1
    assert [(e.call_id, e.kind, e.status, e.usd, e.job_id, e.stage) for e in store.rows] == [
        (receipt.call_id, "riddler", "reserved", SEED_USD["riddler"], JOB, "author"),
        (receipt.call_id, "riddler", "settled", 0.0125, JOB, "author"),
    ]
    assert len(fold(store.rows)) == 1
    assert receipt == CallReceipt(receipt.call_id, "muse-spark-1.3", HOST, cached=False, spend_usd=0.0125)
    assert cache.rows == {riddler_key(): {"text": REPLY.text, "model": REPLY.model, "usage": REPLY.usage, "raw": REPLY.raw}}
    assert (cache.reads, cache.writes) == (1, 1)

    again, receipt_again = calls.chat(riddler_key(), "riddler", model="muse-spark-1.3", call=provider, job_id=JOB, stage="author")
    assert again == REPLY and again is not REPLY and provider.calls == 1
    assert receipt_again.cached and receipt_again.spend_usd == 0.0 and len(store.rows) == 2


def test_a_miss_the_guard_refuses_is_never_made_and_stores_nothing():
    store = MemoryLedgerStore(settled(60.0))
    cache = MemoryCache()
    provider = Provider((REPLY, 0.01))
    with pytest.raises(SpendCapExceeded):
        guarded(store, cache, cap=60).chat(riddler_key(), "riddler", model="muse-spark-1.3", call=provider)
    assert provider.calls == 0 and cache.rows == {} and len(store.rows) == 1


def test_a_call_that_raises_keeps_its_reservation_and_stores_nothing():
    store = MemoryLedgerStore()
    cache = MemoryCache()

    def failing() -> tuple[ChatResponse, float]:
        raise ConnectionError("read timeout")

    with pytest.raises(ConnectionError):
        guarded(store, cache).chat(riddler_key(), "riddler", model="muse-spark-1.3", call=failing)
    assert [e.status for e in store.rows] == ["reserved"] and cache.rows == {}


# --- Attempts and CACHE=off ---------------------------------------------------


def test_attempt_n_is_never_served_attempt_n_minus_one_answer():
    store = MemoryLedgerStore()
    cache = MemoryCache()
    calls = guarded(store, cache)
    first = ChatResponse(text="first draft", model="muse-spark-1.3")
    second = ChatResponse(text="second draft", model="muse-spark-1.3")
    provider = Provider((first, 0.02), (second, 0.03))

    assert calls.chat(riddler_key(attempt=0), "riddler", model="muse-spark-1.3", call=provider)[0] is first
    response, receipt = calls.chat(riddler_key(attempt=1), "riddler", model="muse-spark-1.3", call=provider)

    assert response is second and provider.calls == 2
    assert (receipt.cached, receipt.spend_usd) == (False, 0.03)
    assert [e.usd for e in fold(store.rows)] == [0.02, 0.03]
    assert set(cache.rows) == {riddler_key(attempt=0), riddler_key(attempt=1)}


def test_cache_off_neither_reads_nor_writes_the_cache_and_every_call_passes_the_guard():
    store = MemoryLedgerStore()
    cache = MemoryCache(**{riddler_key(): {"text": "stale", "model": "muse-spark-1.3", "usage": {}, "raw": None}})
    calls = guarded(store, cache, enabled=False)
    provider = Provider((REPLY, 0.01), (REPLY, 0.02))

    receipts = [calls.chat(riddler_key(), "riddler", model="muse-spark-1.3", call=provider)[1] for _ in range(2)]

    assert provider.calls == 2 and (cache.reads, cache.writes) == (0, 0)
    assert [r.cached for r in receipts] == [False, False] and [r.spend_usd for r in receipts] == [0.01, 0.02]
    assert [e.usd for e in fold(store.rows)] == [0.01, 0.02]
    assert len({r.call_id for r in receipts}) == 2


def test_cache_off_still_refuses_at_the_cap():
    store = MemoryLedgerStore(settled(60.0))
    cache = MemoryCache()
    with pytest.raises(SpendCapExceeded):
        guarded(store, cache, cap=60, enabled=False).chat(riddler_key(), "riddler", model="muse-spark-1.3", call=Provider((REPLY, 0.01)))
    assert (cache.reads, cache.writes) == (0, 0)


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("role", ["architect", "riddler", "dryrun", "trickster", "image"])
def test_the_mock_bypasses_the_cache_and_the_ledger_alike(role, enabled):
    store = MemoryLedgerStore(settled(60.0))
    cache = MemoryCache()
    guarded(store, cache, cap=60, enabled=enabled)
    mock = MockProvider(role)
    assert mock.chat([SYSTEM, USER], images=[PHOTO_A], reasoning_effort="medium").text
    assert mock.segment("lamp", PHOTO_A) and mock.generate_image("a wizard").data
    assert (cache.reads, cache.writes) == (0, 0) and len(store.rows) == 1 and len(mock.calls) == 3
    assert "cache" not in inspect.signature(MockProvider.__init__).parameters
    imports = _imports(REPO / "src" / "providers" / "mock.py", "src.providers.mock", REPO / "src")
    assert not imports & {"src.providers.cache", "src.providers.spend", "src.pipeline.ports"}, imports


# --- Every kind reports its row facts (AD-16) ---------------------------------


def test_segment_reports_its_row_facts_and_a_hit_restores_the_polygons():
    store = MemoryLedgerStore()
    cache = MemoryCache()
    calls = guarded(store, cache)
    key = cache_key("sam-3.1", messages=[ChatMessage(role="user", content="lamp")], images=[PHOTO_A])
    provider = Provider(([SQUARE, SQUARE], 0.0025))

    polygons, receipt = calls.segment(key, model="sam-3.1", call=provider, job_id=JOB, stage="segment")
    assert polygons == [SQUARE, SQUARE]
    assert receipt == CallReceipt(receipt.call_id, "sam-3.1", HOST, cached=False, spend_usd=0.0025)
    assert [(e.kind, e.status, e.usd) for e in store.rows] == [("sam", "reserved", SEED_USD["sam"]), ("sam", "settled", 0.0025)]
    assert cache.rows[key] == {"polygons": [[[1.0, 1.0], [9.0, 1.0], [9.0, 9.0], [1.0, 9.0]]] * 2}

    hit, hit_receipt = calls.segment(key, model="sam-3.1", call=provider, job_id=JOB, stage="segment")
    assert hit == [SQUARE, SQUARE] and all(isinstance(point, tuple) for polygon in hit for point in polygon)
    assert (hit_receipt.cached, hit_receipt.spend_usd, hit_receipt.model, hit_receipt.host) == (True, 0.0, "sam-3.1", HOST)
    assert provider.calls == 1 and len(store.rows) == 2


def test_a_segment_call_with_no_mask_is_cached_as_none():
    store = MemoryLedgerStore()
    cache = MemoryCache()
    calls = guarded(store, cache)
    key = cache_key("sam-3.1", messages=[ChatMessage(role="user", content="ghost")], images=[PHOTO_B])
    provider = Provider((None, 0.0025))
    assert calls.segment(key, model="sam-3.1", call=provider)[0] is None
    assert cache.rows[key] == {"polygons": None}
    polygons, receipt = calls.segment(key, model="sam-3.1", call=provider)
    assert polygons is None and receipt.cached and provider.calls == 1


def test_generate_image_reports_its_row_facts_and_a_hit_restores_the_image():
    store = MemoryLedgerStore()
    cache = MemoryCache()
    calls = guarded(store, cache)
    key = cache_key("muse-image-1.0", messages=[ChatMessage(role="user", content="a wizard")])
    image = ImageResponse(data="YmFzZTY0", model="muse-image-1.0", raw={"data": [{"b64_json": "YmFzZTY0"}]})
    provider = Provider((image, 0.01))

    response, receipt = calls.generate_image(key, model="muse-image-1.0", call=provider, session_id=SESSION)
    assert response is image
    assert receipt == CallReceipt(receipt.call_id, "muse-image-1.0", HOST, cached=False, spend_usd=0.01)
    assert [(e.kind, e.status, e.session_id) for e in store.rows] == [("image", "reserved", SESSION), ("image", "settled", SESSION)]
    assert cache.rows[key] == {"data": "YmFzZTY0", "model": "muse-image-1.0", "raw": image.raw}

    hit, hit_receipt = calls.generate_image(key, model="muse-image-1.0", call=provider)
    assert hit == image and hit.data == "YmFzZTY0" and hit_receipt.cached and hit_receipt.spend_usd == 0.0
    assert provider.calls == 1


def test_a_chat_hit_carries_a_fresh_call_id_and_a_billed_call_the_ledger_one():
    store = MemoryLedgerStore()
    cache = MemoryCache()
    calls = guarded(store, cache)
    _, billed = calls.chat(riddler_key(), "vision", model="muse-spark-1.3", call=Provider((REPLY, 0.006)), job_id=JOB, stage="architect")
    _, cached = calls.chat(riddler_key(), "vision", model="muse-spark-1.3", call=Provider(), job_id=JOB, stage="architect")
    assert billed.call_id == store.rows[0].call_id and store.rows[0].kind == "vision"
    assert cached.call_id != billed.call_id and CALL_ID.match(cached.call_id)
    assert new_call_id() != cached.call_id


def test_the_cache_module_is_key_logic_over_the_port_and_the_ledger_and_reads_no_environment():
    src = REPO / "src"
    imports = {n for n in _imports(src / "providers" / "cache.py", "src.providers.cache", src) if n.startswith("src.")}
    assert imports == {"src.domain.ledger", "src.domain.schema", "src.pipeline.ports", "src.providers.base", "src.providers.spend"}
    source = (src / "providers" / "cache.py").read_text()
    assert "os.environ" not in source and "Settings" not in source and "datetime" not in source
