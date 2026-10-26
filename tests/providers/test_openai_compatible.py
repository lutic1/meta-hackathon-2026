"""Story 2.8: the OpenAI-compatible adapter serves the Riddler fallback through the cache, the ledger and one retry (AD-5, AD-6, AD-13)."""

import ast
import json
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from src.config import Settings
from src.council.riddler import CUT6_LOCK_TYPES, LOCK_TYPES, build_author_prompt
from src.domain.ledger import SEED_USD, SpendCapExceeded, fold, spark_cost_usd
from src.domain.redact import to_prompt_view
from src.domain.schema import Derived, RoomDraft, strict_schema
from src.providers.base import ChatMessage, ChatResponse, ProviderError
from src.providers.cache import GuardedCalls, cache_key
from src.providers.meta_api import MetaModelProvider
from src.providers.openai_compatible import (
    MAX_TOKENS,
    PLAIN_JSON_ASK,
    RETRY_ON_CONNECT,
    RETRYABLE_STATUS,
    OpenAICompatibleProvider,
)
from src.providers.spend import SpendLedger
from tests.fixtures.rooms import (
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)
from tests.providers.replay import load, transport
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore, settled

MODULE = Path(__file__).resolve().parents[2] / "src/providers/openai_compatible.py"
BASE_URL = "https://inference.baseten.co/v1"
HOST = "inference.baseten.co"
DRAFT = "muse-spark-open/chat-room-draft"
PROSE = "muse-spark-open/chat-plain-prose"
MESSAGES = [ChatMessage("system", "You are the Riddler."), ChatMessage("user", "Write the puzzles.")]
SENTINEL_DERIVED = Derived(
    sessions=9731, persistence=0.4173, time_to_first_hint_s=137.9, mean_rung_per_lock_type={"code": 2.71}
)
PROFILE_FIELDS = {"derived", "profile", *Derived.model_fields}


def reply(name: str) -> httpx.Response:
    fixture = load(name)
    return httpx.Response(fixture.status, json=fixture.body)


def error(status: int, kind: str = "server_error", headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, headers=headers, json={"error": {"message": kind, "type": kind, "param": None, "code": None}})


class Host:
    """Serves each item in turn: an `httpx.Response`, or an httpx exception class to raise; records every request."""

    def __init__(self, *items: Any) -> None:
        self.queue = list(items)
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.queue.pop(0)
        if isinstance(item, type):
            raise item("simulated", request=request)
        return item

    def bodies(self) -> list[dict[str, Any]]:
        return [json.loads(request.content) for request in self.requests]


class Harness:
    def __init__(self, *items: Any, store: MemoryLedgerStore | None = None, cache: MemoryCache | None = None,
                 cap: float = 60.0, enabled: bool = True, **options: Any) -> None:
        self.host = Host(*items)
        self.store = store or MemoryLedgerStore()
        self.cache = cache or MemoryCache()
        self.waits: list[float] = []
        settings = Settings(openai_compatible_base_url=BASE_URL, openai_compatible_api_key="test-key")
        calls = GuardedCalls(self.cache, SpendLedger(self.store, cap_usd=cap), host=HOST, enabled=enabled)
        self.provider = OpenAICompatibleProvider(
            settings.openai_compatible_api_key, settings.openai_compatible_base_url, calls,
            transport=httpx.MockTransport(self.host.handler), sleep=self.waits.append, **options,
        )

    def chat(self, messages: list[ChatMessage] = MESSAGES, **kwargs: Any) -> ChatResponse:
        return self.provider.chat(messages, **kwargs)

    @property
    def bodies(self) -> list[dict[str, Any]]:
        return self.host.bodies()


def clock_at(*readings: float):
    values = iter(readings)
    return lambda: next(values)


# --- Settings, the guarded path and the request shape ------------------------


def test_chat_against_the_recorded_fixture_runs_through_the_cache_and_the_ledger_priced_from_usage():
    h = Harness(reply(DRAFT))
    response = h.chat(response_schema=RoomDraft, reasoning_effort="medium")
    usage = load(DRAFT).body["usage"]
    assert isinstance(response, ChatResponse)
    assert response.text == load(DRAFT).body["choices"][0]["message"]["content"]
    assert response.model == "meta-models/muse-spark-open" and response.usage == usage and response.raw == load(DRAFT).body
    assert [(e.kind, e.status, e.usd) for e in h.store.rows] == [
        ("riddler", "reserved", SEED_USD["riddler"]), ("riddler", "settled", spark_cost_usd(usage)),
    ]
    assert len(fold(h.store.rows)) == 1 and spark_cost_usd(usage) == pytest.approx(0.0054825)
    key = cache_key("meta-models/muse-spark-open", messages=MESSAGES, response_schema=RoomDraft, reasoning_effort="medium")
    assert set(h.cache.rows) == {key} and (h.cache.reads, h.cache.writes) == (1, 1)

    again = h.chat(response_schema=RoomDraft, reasoning_effort="medium")
    assert again == response and len(h.host.requests) == 1 and len(h.store.rows) == 2


def test_the_request_goes_to_the_configured_host_with_the_key_an_explicit_effort_and_max_tokens():
    h = Harness(reply(DRAFT))
    h.chat(reasoning_effort="medium")
    request = h.host.requests[0]
    assert str(request.url) == f"{BASE_URL}/chat/completions" and request.method == "POST"
    assert request.headers["authorization"] == "Bearer test-key"
    assert h.bodies[0] == {
        "model": "meta-models/muse-spark-open",
        "messages": [{"role": "system", "content": "You are the Riddler."}, {"role": "user", "content": "Write the puzzles."}],
        "reasoning_effort": "medium",
        "max_tokens": MAX_TOKENS,
    }
    assert "temperature" not in h.bodies[0] and "max_completion_tokens" not in h.bodies[0]


def test_the_default_effort_is_sent_explicitly_and_none_is_refused_before_any_request():
    h = Harness(reply(DRAFT))
    h.chat()
    assert h.bodies[0]["reasoning_effort"] == "low"
    with pytest.raises(ValueError, match="reasoning_effort 'none'"):
        h.chat(reasoning_effort="none")  # type: ignore[arg-type]
    assert len(h.host.requests) == 1 and len(h.store.rows) == 2


def test_the_role_model_and_kind_come_from_the_constructor_and_the_call_may_override_the_model():
    h = Harness(reply(DRAFT), reply(DRAFT), model="accounts/fireworks/models/llama-v3p1-8b-instruct", kind="trickster")
    h.chat()
    h.chat(model="meta-models/muse-spark-open")
    assert [b["model"] for b in h.bodies] == ["accounts/fireworks/models/llama-v3p1-8b-instruct", "meta-models/muse-spark-open"]
    assert {e.kind for e in h.store.rows} == {"trickster"} and h.store.rows[0].usd == SEED_USD["trickster"]


def test_a_missing_base_url_or_key_is_refused():
    calls = GuardedCalls(MemoryCache(), SpendLedger(MemoryLedgerStore(), cap_usd=60), host=HOST)
    with pytest.raises(ValueError, match="OPENAI_COMPATIBLE_BASE_URL"):
        OpenAICompatibleProvider("k", None, calls)
    with pytest.raises(ValueError, match="OPENAI_COMPATIBLE_API_KEY"):
        OpenAICompatibleProvider(None, BASE_URL, calls)
    settings = Settings.from_env({"OPENAI_COMPATIBLE_BASE_URL": "", "OPENAI_COMPATIBLE_API_KEY": ""})
    with pytest.raises(ValueError, match="OPENAI_COMPATIBLE_BASE_URL"):
        OpenAICompatibleProvider(settings.openai_compatible_api_key, settings.openai_compatible_base_url, calls)


def test_a_cache_hit_is_served_before_the_guard_and_cache_off_still_refuses_at_the_cap():
    key = cache_key("meta-models/muse-spark-open", messages=MESSAGES, reasoning_effort="low")
    row = {"text": "cached", "model": "meta-models/muse-spark-open", "usage": {}, "raw": None}
    h = Harness(reply(DRAFT), store=MemoryLedgerStore(settled(60.0)), cache=MemoryCache(**{key: row}))
    assert h.chat().text == "cached" and h.host.requests == [] and len(h.store.rows) == 1

    off = Harness(reply(DRAFT), store=MemoryLedgerStore(settled(60.0)), cache=MemoryCache(**{key: row}), enabled=False)
    with pytest.raises(SpendCapExceeded):
        off.chat()
    assert off.host.requests == [] and (off.cache.reads, off.cache.writes) == (0, 0)


def test_segment_and_generate_image_have_no_fallback_host():
    h = Harness()
    with pytest.raises(NotImplementedError, match="segment"):
        h.provider.segment("lamp", b"jpeg")
    with pytest.raises(NotImplementedError, match="generate_image"):
        h.provider.generate_image("a wizard")
    with pytest.raises(ValueError, match="images"):
        h.chat(images=[b"jpeg"])
    assert h.host.requests == [] and h.store.rows == []


# --- One retry with backoff, inside one ledger entry (AD-13) -----------------


def test_the_declared_sets_are_the_documented_ones():
    assert RETRYABLE_STATUS == {429, 500, 503}
    assert RETRY_ON_CONNECT == (httpx.ConnectError, httpx.ConnectTimeout)


@pytest.mark.parametrize("first", [error(429, "rate_limit_error"), error(500), error(503), httpx.ConnectError, httpx.ConnectTimeout],
                         ids=["429", "500", "503", "ConnectError", "ConnectTimeout"])
def test_a_retryable_failure_then_a_success_retries_exactly_once_inside_one_ledger_entry(first):
    h = Harness(first, reply(DRAFT))
    response = h.chat(response_schema=RoomDraft)
    assert response.text == load(DRAFT).body["choices"][0]["message"]["content"]
    assert len(h.host.requests) == 2 and h.bodies[0] == h.bodies[1]
    assert len(h.waits) == 1 and 0.5 <= h.waits[0] <= 1.0
    assert len(fold(h.store.rows)) == 1 and [e.status for e in h.store.rows] == ["reserved", "settled"]
    assert h.store.rows[1].usd == spark_cost_usd(load(DRAFT).body["usage"]) and len(h.cache.rows) == 1


@pytest.mark.parametrize("failure", [error(429, "rate_limit_error"), error(503), httpx.ConnectError], ids=["429", "503", "ConnectError"])
def test_a_second_failure_is_a_provider_error_after_two_requests(failure):
    h = Harness(failure, failure, reply(DRAFT))
    with pytest.raises(ProviderError) as info:
        h.chat()
    assert len(h.host.requests) == 2 and len(h.waits) == 1
    assert info.value.status == (None if isinstance(failure, type) else failure.status_code)
    assert [e.status for e in h.store.rows] == ["reserved"] and h.cache.rows == {}


@pytest.mark.parametrize("failure", [error(502), error(504, "gateway_timeout"), error(501), error(400, "invalid_request_error"), httpx.ReadTimeout, httpx.RemoteProtocolError],
                         ids=["502", "504", "501", "400", "ReadTimeout", "RemoteProtocolError"])
def test_other_failures_raise_a_provider_error_with_no_retry(failure):
    h = Harness(failure, reply(DRAFT))
    with pytest.raises(ProviderError) as info:
        h.chat()
    assert len(h.host.requests) == 1 and h.waits == []
    if isinstance(failure, type):
        assert info.value.status is None
        assert info.value.kind == ("timeout" if failure is httpx.ReadTimeout else "transport_error")
    else:
        assert (info.value.status, info.value.kind) == (failure.status_code, failure.json()["error"]["type"])
    assert [e.status for e in h.store.rows] == ["reserved"] and h.cache.rows == {}


def test_retry_after_is_honored_in_seconds_and_as_an_http_date():
    h = Harness(error(429, "rate_limit_error", {"retry-after": "2"}), reply(DRAFT))
    h.chat()
    assert h.waits == [2.0] and len(h.host.requests) == 2
    soon = format_datetime(datetime.now(UTC) + timedelta(seconds=5), usegmt=True)
    dated = Harness(error(503, headers={"retry-after": soon}), reply(DRAFT))
    dated.chat()
    assert len(dated.waits) == 1 and 3.0 <= dated.waits[0] <= 5.0


def test_a_wait_past_the_remaining_budget_fails_at_once_with_no_retry():
    overloaded = Harness(error(503, headers={"retry-after": "60"}), reply(DRAFT))
    with pytest.raises(ProviderError) as info:
        overloaded.chat()
    assert info.value.status == 503 and len(overloaded.host.requests) == 1 and overloaded.waits == []
    late = Harness(error(429, "rate_limit_error", {"retry-after": "2"}), reply(DRAFT), clock=clock_at(0.0, 44.0))
    with pytest.raises(ProviderError):
        late.chat()
    assert len(late.host.requests) == 1 and late.waits == []
    assert overloaded.provider.budget_s == 45.0


def test_an_error_body_without_the_envelope_and_an_empty_404_are_typed():
    h = Harness(httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(ProviderError) as info:
        h.chat()
    assert info.value.kind == "unparsed"
    empty = Harness(httpx.Response(404))
    with pytest.raises(ProviderError) as info:
        empty.chat()
    assert (info.value.status, info.value.kind) == (404, "no_body")


def test_a_reply_cut_off_by_length_or_without_usage_is_a_provider_error():
    body = load(DRAFT).body
    cut = {**body, "choices": [{**body["choices"][0], "finish_reason": "length"}]}
    h = Harness(httpx.Response(200, json=cut))
    with pytest.raises(ProviderError) as info:
        h.chat()
    assert (info.value.status, info.value.kind) == (200, "length") and len(h.host.requests) == 1
    unpriced = Harness(httpx.Response(200, json={k: v for k, v in body.items() if k != "usage"}))
    with pytest.raises(ProviderError, match="no_usage"):
        unpriced.chat()


# --- json_schema mode: the constrained response parses as on the meta path --


def test_json_schema_mode_sends_strict_schema_and_the_reply_parses_as_on_the_meta_path():
    h = Harness(reply(DRAFT))
    response = h.chat(response_schema=RoomDraft, reasoning_effort="medium")
    assert h.bodies[0]["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "RoomDraft", "schema": strict_schema(RoomDraft), "strict": True},
    }
    assert "$defs" not in json.dumps(h.bodies[0]["response_format"])
    meta = MetaModelProvider("meta-key", transport=transport(DRAFT)).chat(MESSAGES)
    assert response.text == meta.text and response.raw == meta.raw
    draft = RoomDraft.model_validate_json(response.text)
    assert draft == RoomDraft.model_validate_json(meta.text)
    assert draft.puzzles[0].key == "p1" and draft.puzzles[0].solution.lock_type == "code" and draft.puzzles[0].is_exit


def test_json_schema_mode_leaves_the_messages_as_given_and_a_call_without_a_schema_sends_no_response_format():
    h = Harness(reply(DRAFT), reply(DRAFT))
    h.chat(response_schema=RoomDraft)
    h.chat()
    assert h.bodies[0]["messages"] == h.bodies[1]["messages"] == [{"role": m.role, "content": m.content} for m in MESSAGES]
    assert "response_format" not in h.bodies[1]


# --- plain-JSON mode: parse failures fall to the caller, no adapter loop ------


def test_plain_json_mode_asks_for_the_json_in_the_prompt_and_sends_no_response_format():
    h = Harness(reply(DRAFT), json_mode="plain")
    response = h.chat(response_schema=RoomDraft)
    body = h.bodies[0]
    assert "response_format" not in body
    ask = PLAIN_JSON_ASK + json.dumps(strict_schema(RoomDraft), separators=(",", ":"))
    assert body["messages"] == [
        {"role": "system", "content": f"You are the Riddler.\n\n{ask}"},
        {"role": "user", "content": "Write the puzzles."},
    ]
    assert "JSON" in PLAIN_JSON_ASK and "no code fence" in PLAIN_JSON_ASK
    assert RoomDraft.model_validate_json(response.text).puzzles[0].key == "p1"
    key = cache_key("meta-models/muse-spark-open", messages=[ChatMessage("system", body["messages"][0]["content"]), MESSAGES[1]],
                    response_schema=RoomDraft, reasoning_effort="low")
    assert set(h.cache.rows) == {key}


def test_plain_json_mode_without_a_system_message_prepends_one_and_without_a_schema_adds_nothing():
    h = Harness(reply(DRAFT), reply(DRAFT), json_mode="plain")
    h.chat([MESSAGES[1]], response_schema=RoomDraft)
    h.chat([MESSAGES[1]])
    assert [m["role"] for m in h.bodies[0]["messages"]] == ["system", "user"]
    assert h.bodies[0]["messages"][0]["content"].startswith(PLAIN_JSON_ASK)
    assert h.bodies[1]["messages"] == [{"role": "user", "content": "Write the puzzles."}]


def test_plain_json_parse_failure_goes_back_to_the_caller_after_one_request_as_a_failed_attempt():
    h = Harness(reply(PROSE), json_mode="plain")
    response = h.chat(response_schema=RoomDraft)
    assert response.text.startswith("Here is the room.")
    with pytest.raises(ValidationError):
        RoomDraft.model_validate_json(response.text)
    assert len(h.host.requests) == 1 and h.waits == []
    assert [e.status for e in h.store.rows] == ["reserved", "settled"]  # the call was made, priced and is over

    failed_attempts = 0  # what the regeneration loop (its own story) does with that failure
    for attempt in range(2):
        h.host.queue.append(reply(PROSE))
        try:
            RoomDraft.model_validate_json(h.chat([MESSAGES[0], ChatMessage("user", f"Write the puzzles. Attempt {attempt}.")],
                                                 response_schema=RoomDraft).text)
        except ValidationError:
            failed_attempts += 1
    assert failed_attempts == 2 and len(h.host.requests) == 3


def test_plain_json_mode_makes_no_request_beyond_the_one_documented_retry():
    h = Harness(error(500), reply(PROSE), json_mode="plain")
    response = h.chat(response_schema=RoomDraft)
    with pytest.raises(ValidationError):
        RoomDraft.model_validate_json(response.text)
    assert len(h.host.requests) == 2 and len(h.waits) == 1 and len(fold(h.store.rows)) == 1
    twice = Harness(error(500), error(500), reply(DRAFT), json_mode="plain")
    with pytest.raises(ProviderError):
        twice.chat(response_schema=RoomDraft)
    assert len(twice.host.requests) == 2


# --- Sentinel solutions, Derived keys and profile fields (AD-3) -------------


@pytest.mark.parametrize("json_mode", ["json_schema", "plain"])
@pytest.mark.parametrize("fixture", ["four_lock_room", "code_and_find_room"])
def test_the_body_carries_only_the_messages_it_was_given_and_no_sentinel_solution_derived_key_or_profile_field(
    json_mode: str, fixture: str, request
):
    room = with_sentinel_solutions(request.getfixturevalue(fixture))
    assert SENTINEL_CODE in json.dumps(room.model_dump(mode="json"))
    assert all(ix not in json.dumps([i.model_dump() for i in room.interactables]) for ix in SENTINEL_IX)
    prompt = build_author_prompt(to_prompt_view(room), CUT6_LOCK_TYPES if fixture == "code_and_find_room" else LOCK_TYPES)
    given = prompt.messages()
    h = Harness(reply(DRAFT), json_mode=json_mode)
    h.chat(given, response_schema=prompt.response_schema, reasoning_effort=prompt.reasoning_effort)

    body = h.bodies[0]
    sent = body["messages"]
    assert [m["role"] for m in sent] == [m.role for m in given]
    if json_mode == "json_schema":
        assert sent == [{"role": m.role, "content": m.content} for m in given]
    else:
        assert sent[0]["content"].startswith(given[0].content + "\n\n" + PLAIN_JSON_ASK)
        assert sent[1:] == [{"role": m.role, "content": m.content} for m in given[1:]]
    assert set(body) <= {"model", "messages", "reasoning_effort", "max_tokens", "response_format"}

    text = json.dumps(body)
    assert SENTINEL_CODE not in text
    assert json.dumps(SENTINEL_ORDER)[1:-1] not in text and ", ".join(SENTINEL_ORDER) not in text
    assert SENTINEL_PAIR[0] not in text and SENTINEL_PAIR[1] not in text
    assert SENTINEL_FIND not in text and all(ix not in text for ix in SENTINEL_IX)
    assert "derived" not in text and all(field not in text for field in PROFILE_FIELDS)
    derived = SENTINEL_DERIVED.model_dump(mode="json")
    assert all(str(value) not in text for value in (derived["sessions"], derived["persistence"], derived["time_to_first_hint_s"], 2.71))


# --- Module hygiene -----------------------------------------------------------


def test_module_uses_httpx_only_and_reads_no_environment():
    tree = ast.parse(MODULE.read_text())
    imported = {alias.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert "httpx" in imported and not {"urllib", "os", "requests"} & imported
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert "src.config" not in modules and "contributor" not in MODULE.read_text()


def test_live_host_is_blocked_by_the_offline_guard():
    calls = GuardedCalls(MemoryCache(), SpendLedger(MemoryLedgerStore(), cap_usd=60), host=HOST)
    provider = OpenAICompatibleProvider("k", BASE_URL, calls)
    with pytest.raises(ProviderError, match="tests run offline") as info:
        provider.chat(MESSAGES)
    assert info.value.kind == "transport_error"
