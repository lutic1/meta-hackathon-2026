"""Story 3.7: the Ollama adapter words a Rung or the Greeting on the Mac and falls back to verbatim (AD-3, AD-5).

The fixtures under `tests/fixtures/providers/llama3.2-3b/` are in the shape
`scripts/sit.py` records (SIT-05 overwrites them with the live responses);
no Ollama process runs here and no socket opens.
"""

import json
import logging
from collections.abc import Callable

import httpx
import pytest

from src.domain.schema import Derived, GuideModel, Room
from src.providers.base import HintPhraser, PhraserResponse
from src.providers.ollama import (
    DEFAULT_HOST,
    GUIDE_MODEL,
    KEEP_ALIVE,
    NUM_PREDICT,
    PREFIX,
    PROMPT_TOKEN_LIMIT,
    TIMEOUT_S,
    OllamaPhraser,
    derived_block,
    fallback_cause,
    render_greet_prompt,
    render_phrase_prompt,
)
from src.providers.verbatim import GREETING_TEMPLATES, VerbatimPhraser, greeting_template
from tests.fixtures.guide import BENCHMARK_DERIVED, longest_rung, rung_texts
from tests.fixtures.rooms import SENTINEL_CODE, SENTINEL_FIND, SENTINEL_ORDER, SENTINEL_PAIR, with_sentinel_solutions
from tests.providers.replay import FIXTURES, load

HOST = "http://127.0.0.1:11434"
FIXTURE_DIR = "llama3.2-3b"
PHRASE_FIXTURE = f"{FIXTURE_DIR}/generate-phrase-longest"
GREET_FIXTURE = f"{FIXTURE_DIR}/generate-greet"
RUNG = "Look by the hooks."
MAX_PROMPT_CHARS = 3 * PROMPT_TOKEN_LIMIT
"""Three characters per token is a pessimistic Llama 3 rate for English prose and JSON."""


def _derived(persistence: float, time_to_first_hint_s: float | None = 42.5, sessions: int = 3) -> Derived:
    return Derived(sessions=sessions, persistence=persistence, time_to_first_hint_s=time_to_first_hint_s,
                   mean_rung_per_lock_type={"code": 1.5, "find": 0.5})


DERIVED_BLOCKS = (Derived.fresh(), _derived(0.9), _derived(-0.335, None), _derived(0.0, 137.9, 8641), BENCHMARK_DERIVED)


def recording(respond: Callable[[httpx.Request], httpx.Response]) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """A transport that keeps every request it answers, so a test can read what the adapter sent."""
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return respond(request)

    return httpx.MockTransport(handle), requests


def replying(name: str) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    fixture = load(name)
    return recording(lambda request: httpx.Response(fixture.status, json=fixture.body))


def phraser(transport: httpx.BaseTransport, host: str | None = HOST, fallback: HintPhraser | None = None) -> OllamaPhraser:
    return OllamaPhraser(host, fallback or VerbatimPhraser(), transport=transport)


def sent(request: httpx.Request) -> dict:
    return json.loads(request.content)


class RecordingPhraser(HintPhraser):
    """A fallback that records what reached it and answers a marked line."""

    name = "recording"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def phrase(self, *args, **kwargs) -> PhraserResponse:
        self.calls.append(("phrase", args, kwargs))
        return PhraserResponse(text="fallback phrase", phrased=False, latency_ms=0)

    def greet(self, *args, **kwargs) -> PhraserResponse:
        self.calls.append(("greet", args, kwargs))
        return PhraserResponse(text="fallback greet", phrased=False, latency_ms=0)


# --- one request to llama3.2:3b, the phrased line ----------------------------


def test_phrase_sends_one_generate_request_with_keep_alive_and_returns_the_phrased_line():
    transport, requests = replying(PHRASE_FIXTURE)
    derived = _derived(0.4)
    reply = phraser(transport).phrase(RUNG, derived)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST" and str(request.url) == f"{HOST}/api/generate"
    body = sent(request)
    assert body["model"] == GUIDE_MODEL == "llama3.2:3b"
    assert body["keep_alive"] == KEEP_ALIVE == -1
    assert body["options"] == {"num_predict": NUM_PREDICT} and body["stream"] is False
    assert body["prompt"] == render_phrase_prompt(RUNG, derived)
    assert not {"system", "images", "template", "context", "raw", "format"} & set(body)

    assert isinstance(reply, PhraserResponse)
    assert reply.text == load(PHRASE_FIXTURE).body["response"].strip() and reply.text
    assert reply.phrased is True
    assert isinstance(reply.latency_ms, int) and reply.latency_ms >= 0


def test_greet_sends_one_generate_request_from_the_derived_block_alone():
    transport, requests = replying(GREET_FIXTURE)
    reply = phraser(transport).greet(BENCHMARK_DERIVED)

    assert len(requests) == 1
    body = sent(requests[0])
    assert body["model"] == GUIDE_MODEL and body["keep_alive"] == -1 and body["options"] == {"num_predict": NUM_PREDICT}
    assert body["prompt"] == render_greet_prompt(BENCHMARK_DERIVED) == f"{PREFIX}\nPlay record:\n{derived_block(BENCHMARK_DERIVED)}\n"
    assert reply.text == load(GREET_FIXTURE).body["response"].strip() and reply.phrased is True


def test_the_output_is_capped_at_about_forty_tokens():
    assert 32 <= NUM_PREDICT <= 64


def test_the_reply_is_stripped_of_surrounding_whitespace():
    transport, _ = recording(lambda r: httpx.Response(200, json={"model": GUIDE_MODEL, "response": "  A line.\n\n", "done": True}))
    assert phraser(transport).phrase(RUNG, _derived(0.1)).text == "A line."


def test_the_request_carries_the_five_second_timeout():
    transport, requests = replying(PHRASE_FIXTURE)
    phraser(transport).phrase(RUNG, _derived(0.2))
    assert TIMEOUT_S == 5.0
    assert requests[0].extensions["timeout"] == {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}


# --- the host and what GET /meta reports --------------------------------------


@pytest.mark.parametrize(("given", "host"), [(None, DEFAULT_HOST), ("", DEFAULT_HOST), ("http://127.0.0.1:11435", "http://127.0.0.1:11435")])
def test_the_adapter_talks_to_ollama_host_and_reports_the_guide_model(given, host):
    transport, requests = replying(PHRASE_FIXTURE)
    adapter = phraser(transport, host=given)
    adapter.phrase(RUNG, _derived(0.2))

    assert isinstance(adapter, HintPhraser) and adapter.name == "ollama"
    assert adapter.host == host and str(requests[0].url) == f"{host}/api/generate"
    assert adapter.guide_model == GuideModel(id="llama3.2:3b", host=host)
    assert DEFAULT_HOST == "http://127.0.0.1:11434"


# --- the fixed prefix and the prompt it precedes -----------------------------


def _prompts(room: Room) -> tuple[list[tuple[str, str, Derived]], list[tuple[str, Derived]]]:
    phrase = [(render_phrase_prompt(rung, d), rung, d) for rung in rung_texts(room) for d in DERIVED_BLOCKS]
    greet = [(render_greet_prompt(d), d) for d in DERIVED_BLOCKS]
    return phrase, greet


def test_the_prefix_is_byte_identical_across_every_phrase_and_greet_call(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    phrase, greet = _prompts(room)
    assert len(phrase) == 15 * len(DERIVED_BLOCKS) and len(greet) == len(DERIVED_BLOCKS)
    prefixes = {prompt[: len(PREFIX)].encode() for prompt, *_ in phrase} | {prompt[: len(PREFIX)].encode() for prompt, _ in greet}
    assert prefixes == {PREFIX.encode()}

    transport, requests = replying(PHRASE_FIXTURE)
    adapter = phraser(transport)
    for rung in rung_texts(room):
        adapter.phrase(rung, BENCHMARK_DERIVED)
    adapter.greet(BENCHMARK_DERIVED)
    assert {sent(r)["prompt"][: len(PREFIX)].encode() for r in requests} == {PREFIX.encode()}


def test_the_prefix_tells_the_model_to_reword_only_and_never_add_content():
    assert "reword it only and never add content" in PREFIX
    assert "no new object, number, step or answer" in PREFIX
    assert "never a solution" in PREFIX
    for brief in ("wry, warm and specific about how they play", "never about an object or an answer", "nothing that sounds like surveillance"):
        assert brief in PREFIX  # the Greeting brief (UX contract)
    assert PREFIX.endswith("\n")


def test_every_recorded_fixture_prompt_eval_count_is_under_400():
    paths = sorted((FIXTURES / FIXTURE_DIR).glob("*.json"))
    assert {path.stem for path in paths} >= {"generate-phrase-longest", "generate-greet"}
    for path in paths:
        fixture = load(f"{FIXTURE_DIR}/{path.stem}")
        body = fixture.body
        assert fixture.status == 200 and body["model"] == GUIDE_MODEL and body["done"] is True, path.name
        assert 0 < body["prompt_eval_count"] < PROMPT_TOKEN_LIMIT, path.name
        assert body["response"].strip() and body["eval_count"] <= NUM_PREDICT, path.name


def test_every_prompt_rendered_offline_is_no_longer_than_the_longest_recorded_prompt(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    recorded = render_phrase_prompt(longest_rung(room), BENCHMARK_DERIVED)  # what SIT-05 sent, recorded as generate-phrase-longest
    assert len(recorded) <= MAX_PROMPT_CHARS
    phrase, greet = _prompts(room)
    for prompt, rung, derived in phrase:
        assert len(prompt) <= len(recorded), (rung, derived)
    for prompt, derived in greet:
        assert len(prompt) < len(recorded), derived


def test_no_prompt_holds_a_sentinel_solution_label_clue_lore_other_rung_or_id(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    rungs = set(rung_texts(room))
    ids = {ix.id for ix in room.interactables} | {pz.id for pz in room.puzzles} | {room.id}
    labels = {ix.label for ix in room.interactables}
    clues_and_lore = {pz.clue for pz in room.puzzles} | {pz.lore for pz in room.puzzles}
    solutions = {SENTINEL_CODE, json.dumps(SENTINEL_ORDER), " ".join(SENTINEL_ORDER), " ".join(SENTINEL_PAIR), SENTINEL_FIND}
    forbidden = ids | labels | clues_and_lore | solutions | {"ix_", "pz_", "room_", "solution", "label", "clue", "lore", "evidence"}

    phrase, greet = _prompts(room)
    for prompt, rung, derived in phrase:
        assert prompt == f"{PREFIX}\nLine:\n{rung}\n\nPlay record:\n{derived_block(derived)}\n"
        around = prompt[len(PREFIX):].replace(rung, "", 1)  # the Rung itself may name where to look
        assert not any(token in around for token in forbidden), (rung, derived)
        assert not any(other in around for other in rungs), rung
        assert set(json.loads(derived_block(derived))) == set(Derived.model_fields)
    for prompt, derived in greet:
        assert prompt == f"{PREFIX}\nPlay record:\n{derived_block(derived)}\n"
        tail = prompt[len(PREFIX):]
        assert not any(token in tail for token in forbidden | rungs), derived
    assert not any(token in PREFIX for token in ids | labels | clues_and_lore | solutions | rungs)


# --- the fallback: timeout, unreachable, error ---------------------------------


def _raise(error: Exception) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        raise error
    return respond


FAILURES: dict[str, tuple[str, Callable[[httpx.Request], httpx.Response]]] = {
    "read timeout": ("timeout", _raise(httpx.ReadTimeout("the reply took too long"))),
    "connect timeout": ("timeout", _raise(httpx.ConnectTimeout("no answer on connect"))),
    "connection refused": ("unreachable", _raise(httpx.ConnectError("connection refused"))),
    "server error": ("error", lambda r: httpx.Response(500, json={"error": "llama runner process has terminated"})),
    "model missing": ("error", lambda r: httpx.Response(404, json={"error": "model 'llama3.2:3b' not found"})),
    "not json": ("error", lambda r: httpx.Response(200, content=b"<html>not ollama</html>")),
    "empty line": ("error", lambda r: httpx.Response(200, json={"model": GUIDE_MODEL, "response": " \n", "done": True})),
    "protocol error": ("error", _raise(httpx.RemoteProtocolError("the server closed the connection"))),
}


@pytest.mark.parametrize("failure", FAILURES)
def test_phrase_falls_back_to_the_verbatim_rung_and_logs_phraser_fallback_with_its_cause(failure, caplog):
    cause, respond = FAILURES[failure]
    transport, requests = recording(respond)
    derived = _derived(0.4173, 137.9)
    with caplog.at_level(logging.WARNING, logger="src.providers.ollama"):
        reply = phraser(transport).phrase(RUNG, derived)

    assert len(requests) == 1
    assert reply.text == RUNG and reply.text.encode() == RUNG.encode()
    assert reply.phrased is False and isinstance(reply.latency_ms, int)
    assert len(caplog.records) == 1
    line = json.loads(caplog.records[0].getMessage())
    assert line["event"] == "phraser_fallback" and line["cause"] == cause and line["call"] == "phrase"
    assert isinstance(line["duration_ms"], int) and line["error"]


@pytest.mark.parametrize("failure", FAILURES)
@pytest.mark.parametrize(("derived", "template"), [
    (_derived(0.9, None), GREETING_TEMPLATES[0]),
    (_derived(0.34), GREETING_TEMPLATES[1]),
    (_derived(0.0), GREETING_TEMPLATES[2]),
    (_derived(-0.34), GREETING_TEMPLATES[3]),
])
def test_greet_falls_back_to_the_greeting_template_the_derived_block_chooses(failure, derived, template, caplog):
    cause, respond = FAILURES[failure]
    transport, _ = recording(respond)
    with caplog.at_level(logging.WARNING, logger="src.providers.ollama"):
        reply = phraser(transport).greet(derived)
    assert reply.text == template == greeting_template(derived) and reply.phrased is False
    line = json.loads(caplog.records[-1].getMessage())
    assert (line["event"], line["call"], line["cause"]) == ("phraser_fallback", "greet", cause)


def test_the_fallback_is_the_injected_adapter_called_with_the_same_input():
    transport, _ = recording(_raise(httpx.ConnectError("refused")))
    fallback = RecordingPhraser()
    derived = _derived(0.2)
    adapter = phraser(transport, fallback=fallback)
    assert adapter.phrase(RUNG, derived).text == "fallback phrase"
    assert adapter.greet(derived).text == "fallback greet"
    assert fallback.calls == [("phrase", (RUNG, derived), {}), ("greet", (derived,), {})]


def test_a_working_model_logs_nothing_and_never_reaches_the_fallback(caplog):
    transport, _ = replying(PHRASE_FIXTURE)
    fallback = RecordingPhraser()
    with caplog.at_level(logging.DEBUG, logger="src.providers.ollama"):
        reply = phraser(transport, fallback=fallback).phrase(RUNG, _derived(0.2))
    assert reply.phrased is True and fallback.calls == [] and caplog.records == []


def test_fallback_causes():
    assert fallback_cause(httpx.ReadTimeout("slow")) == "timeout"
    assert fallback_cause(httpx.ConnectTimeout("slow")) == "timeout"
    assert fallback_cause(ConnectionError("refused")) == "unreachable"
    assert fallback_cause(httpx.ConnectError("refused")) == "unreachable"
    assert fallback_cause(ValueError("bad body")) == "error"
    assert fallback_cause(httpx.RemoteProtocolError("closed")) == "error"
