"""Story 4.8: the live Trickster in wiring's source table and through the route, the six-call budget and the Fireworks fallback (FR-18, FR-25, AD-5, AD-6, AD-13, AD-15)."""

import json
from datetime import date
from functools import partial
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from src.api import wiring
from src.api.wiring import (
    ROLE_CALLS,
    ledger_store,
    model_cache,
    model_providers,
    session_store,
    spend_ledger,
    trickster_source,
    trickster_sources,
    wire,
)
from src.config import Settings
from src.council.trickster import (
    RECORDED_PROPOSALS,
    SOURCES,
    LiveSource,
    build_trickster_prompt,
    load_proposals,
)
from src.domain.redact import to_play_view, to_prompt_view
from src.domain.schema import Room, strict_schema
from src.domain.session import TRICKSTER_CALLS_MAX
from src.domain.validator import EDIT_BOUNDS, RULES
from src.infra.local import CACHE_ROOT, LEDGER_PATH
from src.infra.modal import CACHE_DIR, hosted_stores
from src.providers.cache import GuardedCalls
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import MockProvider, MockScript
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.spend import SpendLedger
from tests.api.hosted import hosted_handles, hosted_settings, make_hosted_app
from tests.api.test_app import store_room
from tests.api.test_sessions import Ticker, click, code, post, start
from tests.api.test_trickster_route import (
    CLOSED,
    WINDOW,
    always,
    app_client,
    cards_in,
    open_window,
    state_of,
    trickster,
    two_windows,
)
from tests.api.test_wiring import built
from tests.council.test_trickster_live import (
    FIRST,
    MERGE,
    REPLY,
    SUMMARY,
    assert_no_solution_or_profile_field,
)
from tests.domain.test_trickster_windows import skipped
from tests.fixtures.rooms import PZ, with_sentinel_solutions
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

REPO = Path(__file__).resolve().parents[2]
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1"
FIREWORKS = {"OPENAI_COMPATIBLE_BASE_URL": FIREWORKS_URL, "OPENAI_COMPATIBLE_API_KEY": "test-fallback-key"}
FALLBACK_FIXTURE = REPO / "tests/fixtures/fireworks/trickster-fallback.json"
"""The hand-recorded Fireworks fallback response (2.9 checklist, Sat Oct 31), with its confirmed model id and date."""
CONFIRMED_FROM = date(2026, 10, 26)
ABSENT = {**FIRST, "puzzle": f"pz_{'7' * 26}"}
"""A Decoy naming a Puzzle id the `RoomView` lacks: parsed exactly, then rejected by the bounds."""


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


def chat(content: dict[str, Any]) -> dict[str, Any]:
    """The sample Trickster response body with `content` as its reply."""
    choice = {**REPLY.body["choices"][0], "message": {"role": "assistant", "content": json.dumps(content)}}
    return {**REPLY.body, "choices": [choice]}


class Host:
    """Serves each response in turn and keeps every request body."""

    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.bodies: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.bodies.append(json.loads(request.content))
        return self.responses.pop(0)


def meta(host: Host, *, cap_usd: float = 60) -> MetaModelProvider:
    calls = GuardedCalls(MemoryCache(), SpendLedger(MemoryLedgerStore(), cap_usd=cap_usd), host="api.meta.ai")
    return MetaModelProvider(
        "test-key", calls=calls, chat_kind="trickster", budget_s=30.0, transport=httpx.MockTransport(host), sleep=lambda s: None
    )


# --- Wiring's source table and GET /meta --------------------------------------------------


def test_live_and_record_are_registered_in_wirings_source_table_beside_the_replay_values(tmp_path: Path):
    provider = MockProvider("trickster")
    table = trickster_sources(provider)
    assert set(table) == {"live", "record", "scripted", "authored"} and set(SOURCES) <= set(table)
    live = trickster_source(Settings.from_env({"DEMO_TRICKSTER": "live"}), provider, tmp_path)()
    record = trickster_source(Settings.from_env({"DEMO_TRICKSTER": "record"}), provider, tmp_path)()
    assert live == LiveSource(provider) and live.recording is None  # type: ignore[union-attr]
    assert record == LiveSource(provider, recording=tmp_path / RECORDED_PROPOSALS)


@pytest.mark.parametrize("value", ["live", "record"])
def test_wire_hands_the_trickster_roles_provider_to_the_live_source_and_meta_reports_live(
    tmp_path: Path, ticker: Ticker, value: str
):
    settings = Settings.from_env({"DEMO_TRICKSTER": value, "MODEL_PROVIDER": "mock"})
    wired = wire(settings, rooms_root=tmp_path / "rooms", ledger_path=tmp_path / LEDGER_PATH, cache_root=tmp_path / CACHE_ROOT,
                 exports_root=tmp_path / "exports")
    assert type(wired.trickster) is MockProvider and wired.trickster.role == "trickster"
    assert app_client(tmp_path, ticker, env={"DEMO_TRICKSTER": value}).get("/api/meta").json()["trickster"] == "live"


def test_record_is_refused_at_startup_in_hosted_mode():
    with pytest.raises(ValueError, match="DEMO_TRICKSTER=record"):
        Settings.from_env({"MODE": "hosted", "DEMO_TRICKSTER": "record"})


# --- Through the route ------------------------------------------------------------------


def test_a_live_proposal_is_carded_by_the_live_validator_and_an_absent_id_is_a_rejected_card_never_applied(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    host = Host(httpx.Response(200, json=chat(ABSENT)), httpx.Response(200, json=chat(FIRST)))
    client = app_client(tmp_path, ticker, four_lock_room, env={"DEMO_TRICKSTER": "live"}, trickster=always(LiveSource(meta(host))))
    session_id, (first, second) = two_windows(client, ticker, four_lock_room, click("key"), code("clock_code", "415"))

    rejected, accepted = cards_in(tmp_path, session_id)
    assert not rejected.accepted and rejected.reason == EDIT_BOUNDS and rejected.edit is not None
    assert rejected.edit.puzzle == ABSENT["puzzle"]  # kept exactly as the reply wrote it
    assert first["room_revision"] == 0 and first["trickster_window"] == CLOSED
    assert accepted.accepted and second["room_revision"] == 1
    assert [body["model"] for body in host.bodies] == ["muse-spark-1.3", "muse-spark-1.3"]
    assert all(body["reasoning_effort"] == "low" for body in host.bodies)


def test_the_rejected_card_leaves_the_effective_room_as_it_was(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    host = Host(httpx.Response(200, json=chat(ABSENT)))
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(LiveSource(meta(host))))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    reply = trickster(client, session_id)
    assert reply["cards"][0]["accepted"] is False and reply["room_revision"] == 0
    opened = [PZ["find_key"]]
    assert client.get(f"/api/sessions/{session_id}/room").json() == to_play_view(four_lock_room, opened=opened).model_dump(mode="json")


def test_a_provider_error_after_the_one_retry_records_the_skipped_card_and_play_continues(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    overloaded = {"error": {"message": "busy", "type": "server_error", "param": None, "code": None}}
    host = Host(httpx.Response(500, json=overloaded), httpx.Response(500, json=overloaded))
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(LiveSource(meta(host))))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    reply = trickster(client, session_id)
    assert len(host.bodies) == 2  # the adapter's one retry, then the error
    assert reply["cards"] == [{
        "edit_id": None, "accepted": False, "edit_type": None, "puzzle_id": None, "related_puzzle_id": None,
        "room_revision": 0, "reason": "provider_unavailable", "message": None, "t_ms": reply["cards"][0]["t_ms"],
    }]
    assert reply["trickster_window"] == CLOSED
    assert post(client, session_id, code("clock_code", "415"))["locks_open"] == [PZ["find_key"], PZ["clock_code"]]


def test_the_spend_cap_records_the_skipped_card_with_no_request(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    host = Host()
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(LiveSource(meta(host, cap_usd=0))))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    reply = trickster(client, session_id)
    assert host.bodies == [] and reply["cards"][0]["reason"] == "provider_unavailable" and reply["cards"][0]["edit_id"] is None


def test_six_cards_open_no_window_and_the_live_source_makes_no_provider_call(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    provider = MockProvider("trickster", script=MockScript(chat=[json.dumps(FIRST)]))
    client = app_client(tmp_path, ticker, four_lock_room, env={"DEMO_TRICKSTER": "live"}, trickster=lambda: LiveSource(provider))
    session_id = start(client, four_lock_room)
    for n in range(TRICKSTER_CALLS_MAX):
        session_store(tmp_path / "rooms").append(session_id, skipped(10 + n))
    ticker.advance(WINDOW)
    state = post(client, session_id, click("key"))
    assert state["trickster_window"] == CLOSED and state["trickster_calls"] == TRICKSTER_CALLS_MAX
    assert trickster(client, session_id) == state_of(client, session_id)
    assert provider.calls == []


def test_a_hosted_live_window_on_a_judge_room_is_priced_but_leaves_no_cache_entry_the_purge_cannot_list(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room, monkeypatch: pytest.MonkeyPatch
):
    host = Host(httpx.Response(200, json=chat(FIRST)))
    monkeypatch.setattr(
        wiring, "MetaModelProvider", partial(MetaModelProvider, transport=httpx.MockTransport(host), sleep=lambda s: None)
    )
    handles = hosted_handles(tmp_path)
    store_room(hosted_stores(handles).artifacts, four_lock_room)  # a Judge room, under rooms/judge/
    settings = hosted_settings(PROVIDER_TRICKSTER="meta", MODEL_API_KEY="test-key", HINT_POLICY="ladder")
    assert (settings.demo_trickster, settings.cache) == ("live", "on")
    client = TestClient(make_hosted_app(tmp_path, handles, settings=settings, clock=ticker))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    assert trickster(client, session_id)["cards"][0]["accepted"] and len(host.bodies) == 1
    assert not (handles.root / CACHE_DIR).exists()  # only `cache-keys.json` names what the Nov 10 purge deletes (AD-8)
    assert [entry for entry in handles.ledger if not entry.startswith("epoch")], "the call is still guarded and priced (AD-6)"


# --- DEMO_TRICKSTER=record, then scripted (FR-25, AD-15) ----------------------------------


def test_record_cards_each_live_proposal_and_writes_it_and_scripted_then_replays_it_through_the_live_validator(
    tmp_path: Path, ticker: Ticker, four_lock_room: Room
):
    root = tmp_path / "repo"
    provider = MockProvider("trickster", script=MockScript(chat=[json.dumps(FIRST), json.dumps(MERGE)]))
    recording = app_client(tmp_path, ticker, four_lock_room, env={"DEMO_TRICKSTER": "record"},
                           trickster=trickster_source(Settings.from_env({"DEMO_TRICKSTER": "record"}), provider, root))
    _, (_, second) = two_windows(recording, ticker, four_lock_room, click("key"), code("clock_code", "415"))
    live_cards = [(card["accepted"], card["edit_type"], card["reason"]) for card in second["cards"]]
    assert live_cards == [(True, "decoy", None), (False, "merge", 1)] and len(provider.calls) == 2

    artifact = load_proposals(root / RECORDED_PROPOSALS)
    assert artifact.room_id == four_lock_room.id and [p.model_dump() for p in artifact.proposals] == [FIRST, MERGE]
    assert "accepted" not in (root / RECORDED_PROPOSALS).read_text()

    replay = app_client(tmp_path / "replay", ticker, four_lock_room, proposals_dir=root)
    _, (_, replayed) = two_windows(replay, ticker, four_lock_room, click("key"), code("clock_code", "415"))
    assert [(card["accepted"], card["edit_type"], card["reason"]) for card in replayed["cards"]] == live_cards
    assert replayed["cards"][1]["message"] == RULES[1].message
    assert {card["edit_id"] for card in replayed["cards"]}.isdisjoint({card["edit_id"] for card in second["cards"]})


def test_live_writes_no_artifact(tmp_path: Path, ticker: Ticker, four_lock_room: Room):
    root = tmp_path / "repo"
    provider = MockProvider("trickster", script=MockScript(chat=[json.dumps(FIRST)]))
    client = app_client(tmp_path, ticker, four_lock_room, env={"DEMO_TRICKSTER": "live"},
                        trickster=trickster_source(Settings.from_env({"DEMO_TRICKSTER": "live"}), provider, root))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    assert trickster(client, session_id)["cards"][0]["accepted"] and not root.exists()


# --- The Fireworks fallback (AD-5) -----------------------------------------------------


def providers_for(tmp_path: Path, env: dict[str, str]) -> dict[str, Any]:
    """The per-role providers, each paid one built now as its first call would build it."""
    settings = Settings.from_env(env)
    providers = model_providers(settings, model_cache(tmp_path / CACHE_ROOT), spend_ledger(settings, ledger_store(tmp_path / LEDGER_PATH)))
    return {role: built(provider) for role, provider in providers.items()}


def test_provider_trickster_replaces_only_the_trickster_roles_provider(tmp_path: Path):
    env = {"MODEL_PROVIDER": "meta", "MODEL_API_KEY": "test-key", "PROVIDER_TRICKSTER": "openai_compatible", **FIREWORKS,
           "MODEL_TRICKSTER": "accounts/fireworks/models/trickster-test"}
    providers = providers_for(tmp_path, env)
    fallback = providers["trickster"]
    assert type(fallback) is OpenAICompatibleProvider
    assert (fallback.base_url, fallback.kind, fallback.budget_s) == (FIREWORKS_URL, "trickster", ROLE_CALLS["trickster"][1])
    assert fallback.default_chat_model == env["MODEL_TRICKSTER"] and fallback._calls.host == "api.fireworks.ai"
    assert all(type(p) is MetaModelProvider for role, p in providers.items() if role != "trickster")
    assert {role: p.chat_kind for role, p in providers.items() if role != "trickster"} == {
        role: kind for role, (kind, _) in ROLE_CALLS.items() if role != "trickster"
    }


def test_each_fallback_calls_its_own_roles_model_id_and_an_unset_one_keeps_the_adapters_default(tmp_path: Path):
    providers = providers_for(tmp_path, {"MODEL_PROVIDER": "mock", "PROVIDER_RIDDLER": "openai_compatible",
                                         "PROVIDER_TRICKSTER": "openai_compatible", **FIREWORKS,
                                         "MODEL_TRICKSTER": "accounts/fireworks/models/trickster-test"})
    assert providers["riddler"].default_chat_model == "meta-models/muse-spark-open"
    assert providers["trickster"].default_chat_model == "accounts/fireworks/models/trickster-test"


def test_the_prompt_sent_to_the_fallback_holds_no_solution_or_profile_field(tmp_path: Path, four_lock_room: Room):
    host = Host(httpx.Response(200, json=chat(FIRST)))
    calls = GuardedCalls(MemoryCache(), SpendLedger(MemoryLedgerStore(), cap_usd=60), host="api.fireworks.ai")
    fallback = OpenAICompatibleProvider("test-fallback-key", FIREWORKS_URL, calls, model="accounts/fireworks/models/trickster-test",
                                        kind="trickster", budget_s=30.0, transport=httpx.MockTransport(host))
    room = with_sentinel_solutions(four_lock_room)
    proposal = LiveSource(fallback).propose(room.id, 0, to_prompt_view(room), SUMMARY)
    assert proposal is not None and proposal.model_dump() == FIRST
    (body,) = host.bodies
    assert body["response_format"]["json_schema"] == {
        "name": "TricksterProposal", "schema": strict_schema(build_trickster_prompt(to_prompt_view(room), SUMMARY).response_schema),
        "strict": True,
    }
    assert body["reasoning_effort"] == "low"
    assert_no_solution_or_profile_field(json.dumps(body["messages"]))


class FallbackFixture(BaseModel):
    """The hand-recorded Fireworks response: the confirmed model id, its confirmation date, the status and the body."""

    model_config = ConfigDict(extra="forbid")

    model: str
    confirmed: date
    status: int
    body: dict[str, Any]


def test_the_recorded_fallback_fixture_holds_the_confirmed_model_id_the_trickster_role_is_configured_with(tmp_path: Path):
    if not FALLBACK_FIXTURE.exists():
        # Open gate (sprint status, 4.8): the Fireworks model id is confirmed on Mon Oct 26 and the fixture is
        # recorded by hand on Sat Oct 31 (2.9 checklist); commit it here and this test runs.
        pytest.skip(f"{FALLBACK_FIXTURE.relative_to(REPO)} is recorded by hand once the Fireworks model id is confirmed")
    fixture = FallbackFixture.model_validate_json(FALLBACK_FIXTURE.read_bytes())
    assert fixture.confirmed >= CONFIRMED_FROM and fixture.status == 200
    env = {"MODEL_PROVIDER": "mock", "PROVIDER_TRICKSTER": "openai_compatible", **FIREWORKS, "MODEL_TRICKSTER": fixture.model}
    assert providers_for(tmp_path, env)["trickster"].default_chat_model == fixture.model == fixture.body["model"]
    assert_no_solution_or_profile_field(json.dumps(fixture.body))
