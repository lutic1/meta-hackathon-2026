"""SIT-15: one Trickster `chat` call on Meta at low in an open window, its ids parsed by exact match and carded by the live Validator."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from src.api.app import judged_card
from src.api.wiring import ROLE_CALLS
from src.council.trickster import LiveSource
from src.domain.redact import to_prompt_view
from src.domain.rungs import TRICKSTER_WINDOW_MS
from src.domain.schema import ClickEvent, TricksterCardEvent
from src.domain.session import SessionStateMachine, game_state_summary
from src.providers.meta_api import CHAT_MODEL
from tests.fixtures.rooms import IX, write_fixtures

if TYPE_CHECKING:
    from scripts.sit import Sit

FIXTURE = "chat-trickster"
"""Replayed offline by the live Trickster tests."""
SESSION_ID = "sess_01ARZ3NDEKTSV4RRFFQ69G5FAV"
TRICKSTER_KIND, TRICKSTER_BUDGET_S = ROLE_CALLS["trickster"]


def run(sit: Sit) -> str:
    """`CACHE=off`: window 0 of a Session on the synthetic four-lock room; the verdict is reported, not asserted."""
    if sit.settings.demo_trickster == "authored":
        return "cut 1"  # pre-authored proposals, no live Trickster call
    with tempfile.TemporaryDirectory() as scratch:
        room, _ = write_fixtures(Path(scratch))  # synthetic scenes outside the repo; no photo is sent
    found_key = ClickEvent(type="click", interactable_id=IX["key"], t_ms=TRICKSTER_WINDOW_MS)
    state = SessionStateMachine(room).replay(SESSION_ID, [found_key])
    window = state.trickster_window
    assert window.state == "open" and window.index == 0, window
    provider = sit.meta(TRICKSTER_KIND, TRICKSTER_BUDGET_S, cache=False)

    proposal = LiveSource(provider).propose(
        room.id, window.index, to_prompt_view(room), game_state_summary(state, TRICKSTER_WINDOW_MS)
    )
    sit.record(FIXTURE, model=CHAT_MODEL)
    assert proposal is not None
    card = judged_card(room, state, proposal)(TRICKSTER_WINDOW_MS)
    assert isinstance(card, TricksterCardEvent)
    verdict = "accepted" if card.accepted else f"rejected, rule {card.reason}"
    return f"{proposal.type} on {proposal.puzzle}: {verdict}"
