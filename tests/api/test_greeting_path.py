"""Story 5.6: a returning Local start opens with the Greeting, every other start with the First-room welcome (FR-20, FR-21, AR-31, AD-4, AD-8)."""

import json
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import ANY

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.app import FIRST_ROOM_WELCOME, IDLE_TICK_MS
from src.config import Settings
from src.domain.rungs import ThresholdSource
from src.domain.schema import Derived, GuideModel, OpeningLineEvent, Room, Thresholds
from src.domain.session import SessionStateMachine
from src.providers.base import HintPhraser, PhraserResponse
from src.providers.ollama import OllamaPhraser
from src.providers.verbatim import VerbatimPhraser, greeting_template
from tests.api.test_app import make_app
from tests.api.test_sessions import Ticker, click, post, stored
from tests.providers.replay import load, transport

PHRASED = load("llama3.2-3b/generate-greet").body["response"]
RETURNING = Derived(sessions=1, persistence=0.4173, time_to_first_hint_s=137.9, mean_rung_per_lock_type={"code": 2.71})
SENTINEL_VALUES = ("0.4173", "137.9", "2.71")
WELCOME_LINE = {"kind": "welcome", "text": FIRST_ROOM_WELCOME}
GREETING_PENDING = {"kind": "greeting", "text": None}
INVALID_REQUEST = {"error": {"code": "invalid_request", "message": ANY, "stage": None}}
SESSIONS_LOG = "keyframe.sessions"


class SpyPhraser(HintPhraser):
    """A Guide model that records every Derived block `greet` receives and answers the recorded Greeting."""

    name = "spy"
    guide_model = GuideModel(id="llama3.2:3b", host="http://127.0.0.1:11434")

    def __init__(self) -> None:
        self.greeted: list[Derived] = []

    def phrase(self, rung_text: str, derived: Derived) -> PhraserResponse:
        raise AssertionError("no Rung is phrased at a session start")

    def greet(self, derived: Derived) -> PhraserResponse:
        self.greeted.append(derived)
        return PhraserResponse(text=PHRASED, phrased=True, latency_ms=1498)


class Later:
    """A `Spawn` that holds each task until the test runs it, so the Greeting lands when the test says."""

    def __init__(self) -> None:
        self.tasks: list[Callable[[], None]] = []

    def __call__(self, task: Callable[[], None]) -> None:
        self.tasks.append(task)

    def run(self) -> None:
        tasks, self.tasks = self.tasks, []
        for task in tasks:
            task()


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def spy() -> SpyPhraser:
    return SpyPhraser()


@pytest.fixture
def later() -> Later:
    return Later()


@pytest.fixture
def client(tmp_path: Path, code_and_find_room: Room, ticker: Ticker, spy: SpyPhraser, later: Later) -> TestClient:
    return TestClient(make_app(tmp_path, code_and_find_room, clock=ticker, phraser=spy, spawn=later))


def begin(client: TestClient, room: Room, derived: Derived | dict[str, Any] = RETURNING) -> dict[str, Any]:
    block = derived.model_dump() if isinstance(derived, Derived) else derived
    response = client.post("/api/sessions", json={"room_id": room.id, "derived": block})
    assert response.status_code == 200, response.text
    return response.json()


def opening(state: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    return state["opening_line"], state["phrasing"]


def thresholds(nudge_ms: int, nudge_base_ms: int, spacing_ms: int, source: ThresholdSource) -> dict[str, Any]:
    return Thresholds(
        nudge_threshold_ms=nudge_ms,
        nudge_threshold_base_ms=nudge_base_ms,
        rung_spacing_ms=spacing_ms,
        rung_spacing_base_ms=90_000,
        source=source,
    ).model_dump()


def fallback_lines(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    lines = [json.loads(record.getMessage()) for record in caplog.records if record.name == SESSIONS_LOG]
    return [line for line in lines if line["event"] == "phraser_fallback"]


# --- A returning player in Local mode is greeted -------------------------------------


def test_a_returning_start_replies_with_a_pending_greeting_then_appends_the_composed_line_once(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker, spy: SpyPhraser, later: Later
):
    state = begin(client, code_and_find_room)
    assert opening(state) == (GREETING_PENDING, True)
    assert stored(tmp_path, state["id"]) == [] and spy.greeted == []

    ticker.advance(1_600)
    later.run()
    assert spy.greeted == [RETURNING]  # exactly the Derived block of the start
    log = stored(tmp_path, state["id"])
    assert log == [OpeningLineEvent(type="opening_line", kind="greeting", text=PHRASED, t_ms=1_600)]
    assert opening(client.get(f"/api/sessions/{state['id']}").json()) == ({"kind": "greeting", "text": PHRASED}, False)


def test_polled_every_2000_ms_before_and_after_the_line_the_session_holds_one_opening_line_and_replays_the_same(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker, later: Later
):
    session_id = begin(client, code_and_find_room)["id"]
    for _ in range(2):
        ticker.advance(2_000)
        assert opening(client.get(f"/api/sessions/{session_id}").json()) == (GREETING_PENDING, True)
    ticker.advance(600)
    later.run()
    replies = []
    for _ in range(6):
        ticker.advance(2_000)
        replies.append(client.get(f"/api/sessions/{session_id}").json())
    assert all(opening(reply) == ({"kind": "greeting", "text": PHRASED}, False) for reply in replies)

    log = stored(tmp_path, session_id)
    assert [event.type for event in log].count("opening_line") == 1 and log[0].t_ms == 4_600
    machine = SessionStateMachine(
        code_and_find_room, opening="greeting", thresholds=Thresholds.model_validate(replies[-1]["thresholds"])
    )
    assert replies[-1] == machine.replay(session_id, log).model_dump(mode="json")


def test_a_reload_never_appends_a_second_opening_line(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker, spy: SpyPhraser, later: Later
):
    session_id = begin(client, code_and_find_room)["id"]
    later.run()
    for _ in range(3):  # each reload of #/play/<session_id> reads the state again
        assert client.get(f"/api/sessions/{session_id}").status_code == 200
    ticker.advance(1_000)
    post(client, session_id, click("rug"))
    for _ in range(3):
        ticker.advance(IDLE_TICK_MS)
        assert client.get(f"/api/sessions/{session_id}").status_code == 200
    types = [event.type for event in stored(tmp_path, session_id)]
    assert types.count("opening_line") == 1 and types[0] == "opening_line"
    assert len(spy.greeted) == 1 and later.tasks == []


def test_events_posted_while_the_greeting_is_phrased_keep_it_pending_and_land_before_it(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, ticker: Ticker, later: Later
):
    session_id = begin(client, code_and_find_room)["id"]
    ticker.advance(800)
    assert opening(post(client, session_id, click("key"))) == (GREETING_PENDING, True)
    ticker.advance(800)
    later.run()
    assert [(event.type, event.t_ms) for event in stored(tmp_path, session_id)] == [("click", 800), ("opening_line", 1_600)]


def test_the_start_reply_never_waits_on_the_guide_model(tmp_path: Path, code_and_find_room: Room):
    """With the default `Spawn`, the reply comes back while `greet` is still running, and the line follows."""
    gate = threading.Event()

    class Slow(SpyPhraser):
        def greet(self, derived: Derived) -> PhraserResponse:
            assert gate.wait(5)
            return super().greet(derived)

    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=Slow()))
    state = begin(client, code_and_find_room)
    assert opening(state) == (GREETING_PENDING, True)
    assert opening(client.get(f"/api/sessions/{state['id']}").json()) == (GREETING_PENDING, True)
    gate.set()
    deadline = time.monotonic() + 5
    while (reply := client.get(f"/api/sessions/{state['id']}").json())["phrasing"] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert opening(reply) == ({"kind": "greeting", "text": PHRASED}, False)


def test_the_ollama_guide_phrases_the_greeting_from_the_recorded_reply(
    tmp_path: Path, code_and_find_room: Room, later: Later, caplog: pytest.LogCaptureFixture
):
    guide = OllamaPhraser(None, VerbatimPhraser(), transport=transport("llama3.2-3b/generate-greet"))
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=guide, spawn=later))
    with caplog.at_level(logging.INFO):
        session_id = begin(client, code_and_find_room)["id"]
        later.run()
    assert opening(client.get(f"/api/sessions/{session_id}").json()) == ({"kind": "greeting", "text": PHRASED}, False)
    assert fallback_lines(caplog) == []


# --- The template when the Guide model falls back, or none runs ---------------------------


def _raise(error: Exception) -> Callable[[httpx.Request], httpx.Response]:
    def respond(request: httpx.Request) -> httpx.Response:
        raise error
    return respond


@pytest.mark.parametrize("failure", [
    httpx.ReadTimeout("past 5 s"),
    httpx.ConnectTimeout("no answer on connect"),
    httpx.ConnectError("connection refused"),
])
def test_past_5_s_or_unreachable_the_template_is_the_opening_line_and_phraser_fallback_is_logged_once(
    tmp_path: Path,
    code_and_find_room: Room,
    ticker: Ticker,
    later: Later,
    caplog: pytest.LogCaptureFixture,
    failure: Exception,
):
    guide = OllamaPhraser(None, VerbatimPhraser(), transport=httpx.MockTransport(_raise(failure)))
    client = TestClient(make_app(tmp_path, code_and_find_room, clock=ticker, phraser=guide, spawn=later))
    with caplog.at_level(logging.INFO):
        state = begin(client, code_and_find_room)
        assert opening(state) == (GREETING_PENDING, True)
        later.run()
        for _ in range(3):
            client.get(f"/api/sessions/{state['id']}")
    template = greeting_template(RETURNING)
    assert stored(tmp_path, state["id"]) == [OpeningLineEvent(type="opening_line", kind="greeting", text=template, t_ms=0)]
    assert opening(client.get(f"/api/sessions/{state['id']}").json()) == ({"kind": "greeting", "text": template}, False)
    assert fallback_lines(caplog) == [{"session_id": state["id"], "event": "phraser_fallback", "duration_ms": ANY}]


def test_under_guide_verbatim_the_template_lands_and_no_fallback_is_logged(
    tmp_path: Path, code_and_find_room: Room, later: Later, caplog: pytest.LogCaptureFixture
):
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=VerbatimPhraser(), spawn=later))
    with caplog.at_level(logging.INFO):
        session_id = begin(client, code_and_find_room)["id"]
        later.run()
    line = {"kind": "greeting", "text": greeting_template(RETURNING)}
    assert opening(client.get(f"/api/sessions/{session_id}").json()) == (line, False)
    assert fallback_lines(caplog) == []


# --- The First-room welcome: a first room, and every hosted room ------------------------------


def test_a_first_room_start_gets_the_welcome_at_once_and_greet_is_not_called(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, spy: SpyPhraser, later: Later
):
    state = begin(client, code_and_find_room, Derived.fresh())
    assert opening(state) == (WELCOME_LINE, False)
    assert stored(tmp_path, state["id"]) == [OpeningLineEvent(type="opening_line", t_ms=0, **WELCOME_LINE)]
    assert spy.greeted == [] and later.tasks == []


@pytest.mark.parametrize("sessions", [3, 1, 0])
def test_a_hosted_start_gets_the_welcome_and_fresh_thresholds_whatever_block_it_receives(
    tmp_path: Path, code_and_find_room: Room, spy: SpyPhraser, later: Later, sessions: int
):
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=spy, spawn=later, hosted=True))
    received = RETURNING.model_copy(update={"sessions": sessions, "persistence": 1})
    state = begin(client, code_and_find_room, received)
    assert opening(state) == (WELCOME_LINE, False)
    assert spy.greeted == [] and later.tasks == []
    assert client.get(f"/api/sessions/{state['id']}").json()["thresholds"] == thresholds(90_000, 90_000, 90_000, "fresh")


@pytest.mark.parametrize("hosted", [True, False])
def test_no_part_of_the_derived_block_is_stored_in_the_session_log(
    tmp_path: Path, code_and_find_room: Room, spy: SpyPhraser, later: Later, hosted: bool
):
    client = TestClient(make_app(tmp_path, code_and_find_room, phraser=spy, spawn=later, hosted=hosted))
    session_id = begin(client, code_and_find_room, RETURNING.model_copy(update={"sessions": 3}))["id"]
    later.run()
    post(client, session_id, click("key"))
    files = [path for path in (tmp_path / "rooms").rglob("*") if path.is_file() and "sessions" in path.parts]
    assert files
    for path in files:
        text = path.read_text()
        assert not any(key in text for key in ("derived", *Derived.model_fields))
        assert not any(value in text for value in SENTINEL_VALUES)


# --- A Derived block outside its bounds ---------------------------------------------------------


@pytest.mark.parametrize("change", [
    {"persistence": 2},
    {"persistence": -1.5},
    {"sessions": -1},
    {"mean_rung_per_lock_type": {"code": 4}},
    {"mean_rung_per_lock_type": {"riddle": 1}},
    {"time_to_first_hint_s": -1},
])
def test_an_out_of_bounds_block_answers_422_creates_no_session_and_never_greets(
    client: TestClient, tmp_path: Path, code_and_find_room: Room, spy: SpyPhraser, later: Later, change: dict[str, Any]
):
    response = client.post("/api/sessions", json={"room_id": code_and_find_room.id, "derived": {**RETURNING.model_dump(), **change}})
    assert response.status_code == 422 and response.json() == INVALID_REQUEST
    assert not (tmp_path / "rooms" / "sessions").exists()
    assert spy.greeted == [] and later.tasks == []


# --- The thresholds session state reports (AR-31) -----------------------------------------------


@pytest.mark.parametrize(("persistence", "nudge_ms"), [(0, 90_000), (1, 135_000), (-1, 60_000)])
def test_a_returning_start_reports_its_nudge_threshold_from_the_derived_block(
    client: TestClient, code_and_find_room: Room, later: Later, persistence: float, nudge_ms: int
):
    session_id = begin(client, code_and_find_room, RETURNING.model_copy(update={"persistence": persistence}))["id"]
    expected = thresholds(nudge_ms, nudge_ms, 90_000, "derived")
    assert client.get(f"/api/sessions/{session_id}").json()["thresholds"] == expected
    later.run()
    assert client.get(f"/api/sessions/{session_id}").json()["thresholds"] == expected


def test_a_fresh_start_reports_the_default_threshold_from_derived_fresh(client: TestClient, code_and_find_room: Room):
    session_id = begin(client, code_and_find_room, Derived.fresh())["id"]
    assert client.get(f"/api/sessions/{session_id}").json()["thresholds"] == thresholds(90_000, 90_000, 90_000, "fresh")


def test_a_first_room_block_with_a_persistence_still_takes_the_fresh_threshold(client: TestClient, code_and_find_room: Room):
    session_id = begin(client, code_and_find_room, RETURNING.model_copy(update={"sessions": 0, "persistence": 1}))["id"]
    assert client.get(f"/api/sessions/{session_id}").json()["thresholds"] == thresholds(90_000, 90_000, 90_000, "fresh")


@pytest.mark.parametrize(("derived", "expected"), [
    (RETURNING.model_copy(update={"persistence": 0}), thresholds(15_000, 90_000, 15_000, "derived")),
    (RETURNING.model_copy(update={"persistence": 1}), thresholds(22_500, 135_000, 15_000, "derived")),
    (Derived.fresh(), thresholds(15_000, 90_000, 15_000, "fresh")),
])
def test_at_demo_timescale_6_each_threshold_is_divided_and_carries_its_1x_value(
    tmp_path: Path, code_and_find_room: Room, ticker: Ticker, spy: SpyPhraser, later: Later, derived: Derived, expected: dict[str, Any]
):
    settings = Settings(demo_timescale=6, guide="verbatim")
    client = TestClient(make_app(tmp_path, code_and_find_room, settings=settings, clock=ticker, phraser=spy, spawn=later))
    session_id = begin(client, code_and_find_room, derived)["id"]
    assert client.get(f"/api/sessions/{session_id}").json()["thresholds"] == expected
