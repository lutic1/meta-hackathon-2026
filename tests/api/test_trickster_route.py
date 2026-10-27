"""Story 4.4: `POST /sessions/<id>/trickster` runs the source and the live Validator in an open window, and `GET /sessions/<id>/room` serves the Effective room (FR-19, FR-25, FR-26, AD-3, AD-4, AD-12, AD-13, AD-15)."""

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import Sources
from src.api.wiring import (
    PROPOSALS_ROOT,
    artifact_store,
    session_store,
    trickster_source,
)
from src.config import Settings
from src.council.trickster import (
    AUTHORED_PROPOSALS,
    RECORDED_PROPOSALS,
    ScriptedSource,
    TricksterProposal,
)
from src.domain.edits import effective_room
from src.domain.ledger import SpendCapExceeded
from src.domain.redact import to_play_view, to_prompt_view
from src.domain.rungs import TRICKSTER_WINDOW_MS
from src.domain.schema import (
    ULID,
    Evidence,
    Meta,
    Room,
    RoomView,
    SessionState,
    TricksterCard,
    TricksterCardEvent,
)
from src.domain.session import TRICKSTER_CALLS_MAX, GameStateSummary, game_state_summary
from src.domain.validator import RULES, validate
from src.infra.local import CACHE_ROOT, LEDGER_PATH
from src.pipeline.ports import room_key
from src.providers.base import ProviderError
from tests.api.test_app import make_app
from tests.api.test_sessions import Ticker, click, code, post, start, stored
from tests.domain.test_redact import json_keys
from tests.domain.test_trickster_windows import skipped
from tests.fixtures.rooms import (
    IX,
    PZ,
    SENTINEL_FIND,
    SENTINEL_IX,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)
from tests.fixtures.rooms import SENTINEL_CODE as SENTINEL_SOLUTION

REPO = Path(__file__).resolve().parents[2]
FIXTURE_FILE = REPO / "tests/fixtures/proposals/four_lock.json"
"""The 4.3 pre-authored file for the four-lock room: window 0's Decoy passes, window 1's Merge fails rule 1."""
RECORDING: dict[str, Any] = json.loads(FIXTURE_FILE.read_text())
WINDOW = TRICKSTER_WINDOW_MS
CLOSED = {"state": "closed", "index": None}
CARD_FIELDS = set(TricksterCard.model_fields)
HIDDEN_KEYS = {"payload", "edit", "interactable", "visible_attribute", "rung"}

DECOY = TricksterProposal.model_validate(RECORDING["proposals"][0])
VALID_MERGE = {
    "type": "merge", "puzzle": PZ["clock_code"],
    "payload": {"type": "merge", "puzzle_a": PZ["find_key"], "puzzle_b": PZ["clock_code"]},
}
"""A Merge in window 1 that passes: the clock code now waits on the key, which is already found."""
SENTINEL_CODE = "ZQXJV9"
"""A clock code that appears nowhere else in the room and still has a valid lock shape, so the room validates."""


def proposals_root(tmp_path: Path, recording: dict[str, Any] = RECORDING, file: Path = RECORDED_PROPOSALS) -> Path:
    """A root holding `proposals/` with `recording` at `file`, as the repo root holds it."""
    root = tmp_path / "repo"
    (root / file).parent.mkdir(parents=True, exist_ok=True)
    (root / file).write_text(json.dumps(recording))
    return root


def app_client(tmp_path: Path, ticker: Ticker, *rooms: Room, env: dict[str, str] | None = None, **options: Any) -> TestClient:
    """The app at `DEMO_TRICKSTER=scripted` unless `env` says otherwise; `options` carry `proposals_root` or `trickster`."""
    settings = Settings.from_env({"DEMO_TRICKSTER": "scripted", **(env or {})})
    return TestClient(make_app(tmp_path, *rooms, settings=settings, clock=ticker, **options))


def trickster(client: TestClient, session_id: str) -> dict[str, Any]:
    response = client.post(f"/api/sessions/{session_id}/trickster")
    assert response.status_code == 200, response.text
    return response.json()


def state_of(client: TestClient, session_id: str) -> dict[str, Any]:
    return client.get(f"/api/sessions/{session_id}").json()


def open_window(client: TestClient, ticker: Ticker, session_id: str, body: dict[str, Any], index: int) -> dict[str, Any]:
    """Wait out the window threshold past the last card, then open a non-exit lock: the window at `index` opens."""
    ticker.advance(WINDOW + 1_000)
    state = post(client, session_id, body)
    assert state["trickster_window"] == {"state": "open", "index": index}
    return state


def two_windows(client: TestClient, ticker: Ticker, room: Room, key: dict[str, Any], clock_code: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """A session on the four-lock room through windows 0 and 1, one route call each; the two replies."""
    session_id = start(client, room)
    open_window(client, ticker, session_id, key, 0)
    first = trickster(client, session_id)
    open_window(client, ticker, session_id, clock_code, 1)
    return session_id, [first, trickster(client, session_id)]


def cards_in(tmp_path: Path, session_id: str) -> list[TricksterCardEvent]:
    return [event for event in stored(tmp_path, session_id) if isinstance(event, TricksterCardEvent)]


class Counting:
    """A source that counts its calls and answers `proposal`, after `pause` seconds and an optional hook."""

    def __init__(self, proposal: TricksterProposal | None = DECOY, pause: float = 0.0, during: Any = None) -> None:
        self.proposal, self.pause, self.during = proposal, pause, during
        self.calls: list[tuple[str, int]] = []
        self.inputs: list[tuple[RoomView, GameStateSummary]] = []

    def propose(self, room_id: str, window: int, room_view: RoomView, summary: GameStateSummary) -> TricksterProposal | None:
        self.calls.append((room_id, window))
        self.inputs.append((room_view, summary))
        time.sleep(self.pause)
        if self.during is not None:
            self.during()
        return self.proposal


class Raising:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def propose(self, room_id: str, window: int, room_view: RoomView, summary: GameStateSummary) -> TricksterProposal | None:
        raise self.error


def always(source: Any) -> Sources:
    return lambda: source


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


# --- Wiring resolves the source from the source table ------------------------------------


def test_wiring_resolves_the_scripted_and_authored_sources_over_proposals_under_the_repo_root(tmp_path: Path):
    assert PROPOSALS_ROOT == REPO
    recorded = proposals_root(tmp_path)
    authored = proposals_root(tmp_path, {**RECORDING, "proposals": [VALID_MERGE]}, AUTHORED_PROPOSALS)
    resolved = {
        value: trickster_source(Settings.from_env({"DEMO_TRICKSTER": value}), recorded)()
        for value in ("scripted", "authored")
    }
    assert recorded == authored and all(isinstance(source, ScriptedSource) for source in resolved.values())
    assert [p.model_dump() for p in resolved["scripted"].recording.proposals] == RECORDING["proposals"]  # type: ignore[union-attr]
    assert [p.model_dump() for p in resolved["authored"].recording.proposals] == [VALID_MERGE]  # type: ignore[union-attr]


@pytest.mark.parametrize("value", ["live", "record"])
def test_live_and_record_resolve_no_source_until_the_live_source_registers(tmp_path: Path, value: str):
    assert trickster_source(Settings.from_env({"DEMO_TRICKSTER": value}), proposals_root(tmp_path))() is None


# --- Outside an open window -------------------------------------------------------------


def test_a_closed_window_answers_200_with_the_unchanged_state_and_never_calls_the_source(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    source = Counting()
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(source))
    session_id = start(client, four_lock_room)
    ticker.advance(1_000)
    before, log = state_of(client, session_id), stored(tmp_path, session_id)
    assert before["trickster_window"] == CLOSED
    reply = trickster(client, session_id)
    assert reply == before and "cards" in reply
    assert stored(tmp_path, session_id) == log and source.calls == []


def test_a_session_at_six_calls_answers_its_unchanged_state_with_its_cards_and_never_calls_the_source(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    source = Counting()
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(source))
    session_id = start(client, four_lock_room)
    for n in range(TRICKSTER_CALLS_MAX):
        session_store(tmp_path / "rooms").append(session_id, skipped(10 + n))  # six cards written straight into the log
    ticker.advance(WINDOW)
    state = post(client, session_id, click("key"))  # a non-exit lock past the threshold: no seventh window
    assert state["trickster_window"] == CLOSED and state["trickster_calls"] == TRICKSTER_CALLS_MAX
    log = stored(tmp_path, session_id)
    reply = trickster(client, session_id)
    assert reply == state_of(client, session_id) and len(reply["cards"]) == TRICKSTER_CALLS_MAX
    assert reply["trickster_calls"] == TRICKSTER_CALLS_MAX and stored(tmp_path, session_id) == log and source.calls == []


# --- One window, one source call, one card ---------------------------------------------


def test_the_scripted_source_is_judged_live_and_one_card_lands_per_window(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    client = app_client(tmp_path, ticker, four_lock_room, proposals_root=proposals_root(tmp_path))
    session_id, (first, second) = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))

    accepted, rejected = cards_in(tmp_path, session_id)
    assert first["trickster_window"] == CLOSED and first["trickster_calls"] == 1 and first["room_revision"] == 1
    assert first["cards"] == [{
        "edit_id": accepted.edit_id, "accepted": True, "edit_type": "decoy", "puzzle_id": PZ["shelf_order"],
        "related_puzzle_id": None, "room_revision": 1, "reason": None, "message": None, "t_ms": accepted.t_ms,
    }]
    assert second["trickster_window"] == CLOSED and second["trickster_calls"] == 2 and second["room_revision"] == 1
    assert second["cards"][1] == {
        "edit_id": rejected.edit_id, "accepted": False, "edit_type": "merge", "puzzle_id": PZ["clock_code"],
        "related_puzzle_id": PZ["shelf_order"], "room_revision": 1, "reason": 1, "message": RULES[1].message,
        "t_ms": rejected.t_ms,
    }
    for reply in (first, second):
        assert all(set(card) == CARD_FIELDS for card in reply["cards"])
        assert not json_keys(reply["cards"]) & HIDDEN_KEYS


def test_the_source_is_handed_the_effective_rooms_view_and_the_game_state_summary(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    source = Counting(TricksterProposal.model_validate(VALID_MERGE))
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(source))
    session_id, (first, second) = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))

    assert first["cards"][0]["accepted"] and [window for _, window in source.calls] == [0, 1]
    room_view, summary = source.inputs[1]
    assert room_view == to_prompt_view(effective_room(four_lock_room, stored(tmp_path, session_id)[:-1]))
    clock = next(puzzle for puzzle in room_view.puzzles if puzzle.id == PZ["clock_code"])
    assert clock.requires == [PZ["find_key"]]  # window 0's accepted Merge is in the view, not the stored Room's empty list
    assert summary == game_state_summary(SessionState.model_validate(second), ticker.ms)
    assert summary.locks_open == [PZ["find_key"], PZ["clock_code"]] and summary.elapsed_ms == ticker.ms > 0


def test_the_stored_card_keeps_the_judged_edit_with_a_minted_id_server_side(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    client = app_client(tmp_path, ticker, four_lock_room, proposals_root=proposals_root(tmp_path))
    session_id, _ = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))
    accepted, rejected = cards_in(tmp_path, session_id)
    for window, card in enumerate((accepted, rejected)):
        assert card.edit is not None and re.fullmatch(f"te_{ULID}", card.edit.id) and card.edit_id == card.edit.id
        assert card.edit.window == window and card.puzzle_id == card.edit.puzzle
        assert card.edit.model_dump(include={"type", "puzzle", "payload"}) == RECORDING["proposals"][window]
        assert card.accepted is card.edit.accepted is card.edit.validator_result.ok
    assert accepted.reason is None and accepted.edit.validator_result.reasons == []
    assert rejected.reason == rejected.edit.validator_result.reasons[0].rule == 1
    assert accepted.edit_id not in json.dumps(RECORDING)  # the id is minted by the route, never read from the recording
    again, _ = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))
    assert {card.edit_id for card in cards_in(tmp_path, again)}.isdisjoint({accepted.edit_id, rejected.edit_id})


def test_two_requests_at_once_make_one_source_call_and_one_card(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    source = Counting(pause=0.2)
    app = make_app(tmp_path, four_lock_room, settings=Settings.from_env({"DEMO_TRICKSTER": "scripted"}), clock=ticker,
                   trickster=always(source))
    client = TestClient(app)
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)

    def one(_: int) -> Any:
        return TestClient(app).post(f"/api/sessions/{session_id}/trickster")

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(one, range(2)))
    assert [reply.status_code for reply in replies] == [200, 200]
    assert len(source.calls) == 1 and len(cards_in(tmp_path, session_id)) == 1
    first, second = (reply.json() for reply in replies)
    assert first == second  # the second request is served the state the first produced
    assert first["trickster_window"] == CLOSED and first["trickster_calls"] == 1


def test_while_the_source_runs_the_window_reads_pending_and_a_request_then_makes_no_source_call(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    seen: dict[str, Any] = {}
    late: list[Any] = []

    def during() -> None:
        seen["state"] = state_of(client, session_id)  # served at once, without waiting on the lock
        late.append(threading.Thread(target=lambda: seen.setdefault("late", trickster(client, session_id))))
        late[0].start()

    source = Counting(during=during)
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(source))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    before = stored(tmp_path, session_id)
    first = trickster(client, session_id)
    late[0].join(timeout=10)

    assert seen["state"]["trickster_window"] == {"state": "pending", "index": 0}
    assert seen["state"]["trickster_calls"] == 0 and seen["state"]["cards"] == []
    assert seen["late"] == first and len(source.calls) == 1
    assert stored(tmp_path, session_id)[: len(before)] == before and len(cards_in(tmp_path, session_id)) == 1
    assert state_of(client, session_id)["trickster_window"] == CLOSED  # the mark is cleared and never logged


# --- Nothing hidden leaves the server ----------------------------------------------------


def with_sentinel_code(room: Room) -> Room:
    """The four-lock room with the sentinel as its clock code: the token a rejected proposal will carry."""
    sentinel = room.model_copy(deep=True)
    clock = next(puzzle for puzzle in sentinel.puzzles if puzzle.id == PZ["clock_code"])
    clock.solution.code = SENTINEL_CODE  # type: ignore[union-attr]
    assert validate(sentinel).ok
    return sentinel


def test_no_session_body_carries_the_decoys_identity_or_a_rejected_proposals_token(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    room = with_sentinel_code(four_lock_room)
    leaky = {
        "type": "decoy", "puzzle": PZ["clock_code"],
        "payload": {"type": "decoy", "interactable": IX["clock"], "visible_attribute": f"its face reads {SENTINEL_CODE}"},
    }
    root = proposals_root(tmp_path, {"room_id": room.id, "proposals": [RECORDING["proposals"][0], leaky]})
    client = app_client(tmp_path, ticker, room, proposals_root=root)
    session_id = start(client, room)
    open_window(client, ticker, session_id, code("clock_code", SENTINEL_CODE), 0)
    trickster(client, session_id)
    open_window(client, ticker, session_id, click("key"), 1)
    trickster_reply = trickster(client, session_id)
    events_reply = post(client, session_id, click("door"))
    session_reply = state_of(client, session_id)

    for body in (session_reply, events_reply, trickster_reply):
        text = json.dumps(body)
        for hidden in (IX["rug"], "faded red", SENTINEL_CODE):
            assert hidden not in text
        assert not json_keys(body["cards"]) & HIDDEN_KEYS
        decoy, refused = body["cards"]
        assert (decoy["accepted"], decoy["edit_type"], decoy["puzzle_id"]) == (True, "decoy", PZ["shelf_order"])
        assert refused["accepted"] is False and refused["reason"] == 9 and refused["message"] == RULES[9].message  # rule 9: a Decoy gives no answer away


def test_no_trickster_or_effective_room_response_carries_a_solution_provenance_payload_or_edit_key_or_a_sentinel(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    room = with_sentinel_solutions(four_lock_room)
    source = Counting()
    client = app_client(tmp_path, ticker, room, trickster=always(source))
    session_id = start(client, room)
    responses = [client.post(f"/api/sessions/{session_id}/trickster")]  # outside a window
    open_window(client, ticker, session_id, code("clock_code", SENTINEL_SOLUTION), 0)
    responses += [client.post(f"/api/sessions/{session_id}/trickster"), client.get(f"/api/sessions/{session_id}/room")]

    assert [r.status_code for r in responses] == [200, 200, 200] and len(source.calls) == 1
    assert len(responses[1].json()["cards"]) == 1 and len(cards_in(tmp_path, session_id)) == 1
    sentinels = [SENTINEL_SOLUTION, json.dumps(SENTINEL_ORDER)[1:-1], *SENTINEL_PAIR, SENTINEL_FIND, *SENTINEL_IX]
    for response in responses:
        assert not json_keys(response.json()) & {"solution", "provenance", "payload", "edit"}
        assert all(sentinel.encode() not in response.content for sentinel in sentinels)


# --- The verdict is computed, never stored ------------------------------------------------


def test_the_recorded_proposals_replay_one_accepted_and_one_rejected_and_a_valid_replacement_flips_the_card(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    root = proposals_root(tmp_path)
    client = app_client(tmp_path, ticker, four_lock_room, proposals_root=root)
    _, (_, second) = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))
    assert [card["accepted"] for card in second["cards"]] == [True, False]

    proposals_root(tmp_path, {**RECORDING, "proposals": [RECORDING["proposals"][0], VALID_MERGE]})
    _, (_, flipped) = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))
    assert [card["accepted"] for card in flipped["cards"]] == [True, True]
    assert flipped["cards"][1]["reason"] is None and flipped["cards"][1]["message"] is None
    assert flipped["cards"][1]["edit_type"] == "merge" and flipped["room_revision"] == 2
    unchanged = ("accepted", "edit_type", "puzzle_id", "related_puzzle_id", "room_revision", "reason", "message")
    assert [flipped["cards"][0][key] for key in unchanged] == [second["cards"][0][key] for key in unchanged]


def test_under_authored_the_route_replays_the_pre_authored_file_through_the_live_validator(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    root = proposals_root(tmp_path, file=AUTHORED_PROPOSALS)
    assert not (root / RECORDED_PROPOSALS).exists()
    client = app_client(tmp_path, ticker, four_lock_room, env={"DEMO_TRICKSTER": "authored"}, proposals_root=root)
    session_id, (_, second) = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))
    assert [(card["accepted"], card["reason"]) for card in second["cards"]] == [(True, None), (False, 1)]
    assert [card.edit.validator_result.ok for card in cards_in(tmp_path, session_id) if card.edit] == [True, False]


# --- A window with no proposal ------------------------------------------------------------


def files_outside_sessions(tmp_path: Path) -> list[Path]:
    return sorted(path for path in tmp_path.rglob("*") if "sessions" not in path.parts)


@pytest.mark.parametrize("case", ["another room", "used up"])
def test_a_window_with_no_proposal_appends_nothing_and_stays_as_it_was(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room, code_and_find_room: Room, case: str
):
    one_proposal = {**RECORDING, "proposals": RECORDING["proposals"][:1]}
    root = proposals_root(tmp_path, one_proposal)
    client = app_client(tmp_path, ticker, four_lock_room, code_and_find_room, proposals_root=root)
    if case == "another room":
        session_id = start(client, code_and_find_room)
        open_window(client, ticker, session_id, click("key"), 0)
    else:
        session_id = start(client, four_lock_room)
        open_window(client, ticker, session_id, click("key"), 0)
        trickster(client, session_id)
        open_window(client, ticker, session_id, code("clock_code", "415"), 1)
    before, log, files = state_of(client, session_id), stored(tmp_path, session_id), files_outside_sessions(tmp_path)
    for _ in range(2):  # a repeat POST in the same window is again a no-op
        reply = trickster(client, session_id)
        assert reply == before
        assert stored(tmp_path, session_id) == log
    fields = ("trickster_window", "trickster_calls", "room_revision", "cards")
    assert [reply[field] for field in fields] == [before[field] for field in fields]
    assert files_outside_sessions(tmp_path) == files  # no ledger entry, no cache entry
    assert not (tmp_path / LEDGER_PATH).exists() and not (tmp_path / CACHE_ROOT).exists()


@pytest.mark.parametrize("contents", [None, "{not json", json.dumps({"room_id": "nope"})], ids=["missing", "malformed", "invalid"])
def test_a_proposals_file_that_fails_to_load_is_no_proposal_and_never_a_500(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room, contents: str | None, caplog: pytest.LogCaptureFixture
):
    root = tmp_path / "repo"
    if contents is not None:
        (root / RECORDED_PROPOSALS).parent.mkdir(parents=True)
        (root / RECORDED_PROPOSALS).write_text(contents)
    client = app_client(tmp_path, ticker, four_lock_room, proposals_root=root)
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    before, log = state_of(client, session_id), stored(tmp_path, session_id)
    caplog.set_level("WARNING", logger="keyframe.sessions")
    assert trickster(client, session_id) == before and stored(tmp_path, session_id) == log
    assert before["trickster_window"] == {"state": "open", "index": 0}
    assert any("trickster_source_unavailable" in record.getMessage() for record in caplog.records)


# --- A provider failure is a skipped card ------------------------------------------------


@pytest.mark.parametrize("error", [ProviderError(503, "unavailable", "down"), SpendCapExceeded(20.0, 19.99)], ids=["provider", "cap"])
def test_a_provider_error_or_the_spend_cap_appends_the_skipped_card_and_play_goes_on(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room, error: Exception
):
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(Raising(error)))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    reply = trickster(client, session_id)
    card = cards_in(tmp_path, session_id)
    assert len(card) == 1 and card[0].edit is None
    assert reply["cards"] == [{
        "edit_id": None, "accepted": False, "edit_type": None, "puzzle_id": None, "related_puzzle_id": None,
        "room_revision": 0, "reason": "provider_unavailable", "message": None, "t_ms": card[0].t_ms,
    }]
    assert reply["trickster_window"] == CLOSED and reply["trickster_calls"] == 1 and reply["room_revision"] == 0
    after = post(client, session_id, code("clock_code", "415"))
    assert PZ["clock_code"] in after["locks_open"] and stored(tmp_path, session_id)[-1].type == "lock_input"


# --- The Effective room ------------------------------------------------------------------


def test_the_room_route_serves_the_effective_room_with_the_accepted_edit_only(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    original = four_lock_room.model_dump_json()
    client = app_client(tmp_path, ticker, four_lock_room, proposals_root=proposals_root(tmp_path))
    session_id, _ = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))

    response = client.get(f"/api/sessions/{session_id}/room")
    assert response.status_code == 200
    view = response.json()
    assert view == to_play_view(effective_room(four_lock_room, stored(tmp_path, session_id))).model_dump(mode="json")
    puzzles = {puzzle["id"]: puzzle for puzzle in view["puzzles"]}
    decoy_card = Evidence(interactable=IX["rug"], visible_attribute="faded red").model_dump()
    assert decoy_card in puzzles[PZ["shelf_order"]]["evidence_cards"] and len(puzzles[PZ["shelf_order"]]["evidence_cards"]) == 2
    assert all(set(card) == {"interactable", "visible_attribute"} for card in puzzles[PZ["shelf_order"]]["evidence_cards"])
    assert puzzles[PZ["clock_code"]]["requires"] == []  # the rejected Merge is not in the room
    assert "te_" not in response.text and "decoy" not in response.text

    assert client.get(f"/api/rooms/{four_lock_room.id}").json() == to_play_view(four_lock_room).model_dump(mode="json")
    assert artifact_store(tmp_path / "rooms").read(room_key(four_lock_room.id)).decode() == original


def test_the_room_route_answers_an_unknown_session_with_the_envelope(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    client = app_client(tmp_path, ticker, four_lock_room)
    for response in (client.get("/api/sessions/sess_01ARZ3NDEKTSV4RRFFQ69G5FAV/room"),
                     client.post("/api/sessions/sess_01ARZ3NDEKTSV4RRFFQ69G5FAV/trickster")):
        assert response.status_code == 404 and response.json()["error"]["code"] == "session_not_found"


@pytest.mark.parametrize(("demo_trickster", "reported"), [
    ("live", "live"), ("record", "live"), ("scripted", "scripted"), ("authored", "cut1"),
])
def test_meta_keeps_exactly_its_fields_and_reports_the_source(tmp_path: Path, ticker: Ticker, demo_trickster: str, reported: str):
    client = app_client(tmp_path, ticker, env={"DEMO_TRICKSTER": demo_trickster})
    body = client.get("/api/meta").json()
    assert set(body) == set(Meta.model_fields) and body["trickster"] == reported
