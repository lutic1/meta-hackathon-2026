"""FR-19, UX-DR30, UX-DR40 to UX-DR42, UX-DR70, UX-DR74, UX-DR76: Trickster cards (in play, the Trickster's bubble by
the Treasure chest, story mode; whole in the Card log), the Trickster request that asks for them once per window, and
the `TricksterCard` projection they are read from.

The client has no test runner, so the checks read the TypeScript and the stylesheets; `npm run build` and
`tsc --noEmit` prove they compile, and the criteria are checked in Chrome against the fixture rooms. The API checks
read the polled state the client reads.
"""

import json
import re
from pathlib import Path

from src.domain.ledger import SpendCapExceeded
from src.domain.schema import Room
from tests.api.test_sessions import Ticker, click, code, start
from tests.api.test_trickster_route import (
    HIDDEN_KEYS,
    Raising,
    always,
    app_client,
    open_window,
    proposals_dir,
    state_of,
    trickster,
)
from tests.web.design import WEB_SRC, css_rules, design_text, source_ts
from tests.web.test_strings import _strings
from tests.web.test_types import _interfaces, _keys

DECOY_INTERACTABLE = "ix_00000000000000000000000008"
DECOY_ATTRIBUTE = "faded red"
"""The recorded window-0 Decoy's Interactable and attribute (tests/fixtures/proposals/four_lock.json)."""


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _function(text: str, name: str) -> str:
    """The body of a function nested one level, as the chest's are."""
    return text.split(f"function {name}(", 1)[1].split("\n  }\n", 1)[0]


def _exported(text: str, name: str) -> str:
    """The body of a module-level function."""
    return text.split(f"export function {name}(", 1)[1].split("\n}\n", 1)[0]


# --- The strings ---------------------------------------------------------------------------------


def test_the_card_sentences_labels_and_summaries_are_the_experience_lines():
    strings = _strings()
    assert strings["cardDecoy"] == "A new evidence card has appeared. I do love a crowded desk."
    assert strings["cardMerge"] == "One puzzle now waits on another. Patience builds character; I build locks."
    assert strings["cardLoosen"] == "The Guide is feeling generous: a hint just opened early. Don't tell anyone I allowed it."
    assert strings["cardShortcut"] == ("One puzzle no longer waits on another, so it may turn up sooner. "
                                       "Solving it is still on you.")
    assert strings["cardRejected"] == "The Validator says that wouldn't be fair. Spoilsport."
    assert strings["cardSkipped"] == "I'm keeping quiet this time. Enjoy it while it lasts."
    assert strings["validatorPassed"].format(type="Merge", n=3) == "Validator passed · Merge · Puzzle 3"
    assert strings["validatorRefused"].format(type="Decoy", n=4) == "Validator refused · Decoy · Puzzle 4"
    assert strings["skipped"] == "Skipped"
    assert [strings[k] for k in ("decoy", "merge", "loosen", "shortcut")] == ["Decoy", "Merge", "Loosen", "Shortcut"]
    summaries = [strings[k].format(n=4, m=2) for k in ("proposedDecoy", "proposedMerge", "proposedLoosen", "proposedShortcut")]
    assert summaries == ["a false evidence card for Puzzle 4", "Puzzle 4 waits on Puzzle 2",
                         "open the next hint on Puzzle 4 early", "Puzzle 4 stops waiting on Puzzle 2"]
    assert strings["proposed"].format(summary="Puzzle 4 waits on Puzzle 2") == "Proposed: Puzzle 4 waits on Puzzle 2"
    assert strings["changeRefused"].format(message="Two locks would wait on each other forever.") == (
        "That change was refused. Two locks would wait on each other forever.")
    # No stack in play any more (story mode): the bubble shows the newest Card and the Card log keeps them all.
    assert "moreInCardLog" not in strings and "dismissCard" not in strings


def test_the_introduction_and_the_announcements_are_the_experience_lines():
    strings = _strings()
    assert strings["trickster"] == "The Trickster"
    assert strings["tricksterRole"] == ("Reads the game state; proposes changes between puzzles with muse-spark-1.3, "
                                        "and the Validator checks each one.")
    assert strings["tricksterVoice"] == "I like to move things around. The Validator keeps me honest, sadly."
    assert strings["cardAnnouncement"] == "The Trickster: {sentence} {outcome label}."
    assert strings["firstCardAnnouncement"] == "The Trickster. {role line} {voice line} {sentence} {outcome label}."


# --- What a Card says, from the TricksterCard projection alone -----------------------------------


def test_each_outcome_reads_its_sentence_and_label_from_the_card_fields():
    card = _code(_ts("components/trickster-card.ts"))
    text = _exported(card, "cardText")
    # Skipped: no edit type (reason provider_unavailable), the same words for a provider error and the Spend cap.
    assert "if (type === null || card.reason === 'provider_unavailable') {" in text
    assert "{ outcome: 'skipped', sentence: strings.cardSkipped, label: strings.skipped, refusal: null }" in text
    # Accepted: the edit type's sentence and "Validator passed · {type} · Puzzle {n}".
    assert "sentence: SENTENCES[type], label: fill(strings.validatorPassed, { type: TYPE_NAMES[type], n })" in text
    # Rejected: "Validator refused", the structural summary from puzzle_id and related_puzzle_id, then the message.
    assert "label: fill(strings.validatorRefused, { type: TYPE_NAMES[type], n })" in text
    assert "proposed: fill(strings.proposed, { summary: fill(SUMMARIES[type], { n, m: number(card.related_puzzle_id) }) })" in text
    assert "reason: fill(strings.changeRefused, { message: card.message ?? '' })" in text
    # n is the Puzzle's fixed order number in the Room, as Rung lines and Triggers rows count it.
    assert "room.puzzles.findIndex((puzzle) => puzzle.id === id) + 1" in text and "number(card.puzzle_id)" in text
    for table, keys in (("SENTENCES", ("cardDecoy", "cardMerge", "cardLoosen", "cardShortcut")),
                        ("SUMMARIES", ("proposedDecoy", "proposedMerge", "proposedLoosen", "proposedShortcut"))):
        body = card.split(f"const {table}: Record<EditType, string> = {{", 1)[1].split("}", 1)[0]
        assert [f"strings.{key}" for key in keys] == re.findall(r"strings\.\w+", body)


def test_the_reason_is_never_shown_and_a_decoy_card_cannot_name_its_evidence():
    card = _code(_ts("components/trickster-card.ts"))
    read = set(re.findall(r"(?<![\w-])card\.(\w+)", card))
    assert read <= {"edit_type", "reason", "accepted", "puzzle_id", "related_puzzle_id", "message"}
    # The rule number is only compared, never written into the Card.
    assert re.findall(r"card\.reason[^\n]*", card) == ["card.reason === 'provider_unavailable') {"]


def test_the_client_holds_no_edit_payload_type_or_field():
    for path, text in source_ts().items():
        code_only = _code(text)
        for name in ("TricksterCardEvent", "TricksterEdit", "payload", "visible_attribute"):
            if name == "visible_attribute" and path.endswith(("evidence-card.ts", "types.check.ts")):
                continue  # the Evidence card's read attribute, from PlayView, not from a Card
            assert name not in code_only, f"{path} names {name}"
    # The card type is the generated one, never hand-written.
    assert "import type { PlayView, TricksterCard } from '../../types'" in _ts("components/trickster-card.ts")
    assert not any(re.search(r"\b(?:interface|type) TricksterCard\b", text) for text in source_ts().values())


def test_the_polled_state_carries_only_the_tricksters_card_fields_under_cards(tmp_path: Path, four_lock_room: Room):
    ticker = Ticker()
    client = app_client(tmp_path, ticker, four_lock_room, proposals_dir=proposals_dir(tmp_path))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    assert state_of(client, session_id)["trickster_window"] == {"state": "open", "index": 0}  # what the client asks on
    trickster(client, session_id)
    open_window(client, ticker, session_id, code("clock_code", "415"), 1)
    trickster(client, session_id)
    polled = state_of(client, session_id)
    assert polled["trickster_window"]["state"] == "closed"
    assert [(card["accepted"], card["edit_type"]) for card in polled["cards"]] == [(True, "decoy"), (False, "merge")]
    fields = set(_keys(_interfaces()["TricksterCard"]))
    assert all(set(card) == fields for card in polled["cards"])
    assert not HIDDEN_KEYS & {key for card in polled["cards"] for key in card}
    served = json.dumps(polled["cards"])
    assert DECOY_INTERACTABLE not in served and DECOY_ATTRIBUTE not in served
    rejected = polled["cards"][1]
    assert isinstance(rejected["reason"], int) and rejected["message"] and rejected["related_puzzle_id"]


def test_a_skipped_card_in_the_polled_state_has_no_edit_type(tmp_path: Path, four_lock_room: Room):
    ticker = Ticker()
    client = app_client(tmp_path, ticker, four_lock_room, trickster=always(Raising(SpendCapExceeded(20.0, 19.99))))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    trickster(client, session_id)
    (card,) = state_of(client, session_id)["cards"]
    assert card["edit_type"] is None and card["reason"] == "provider_unavailable" and card["accepted"] is False


# --- The Trickster request ------------------------------------------------------------------------


def test_an_open_window_is_asked_once_with_no_pending_state_and_the_reply_is_not_drawn():
    request = _code(_ts("trickster-request.ts"))
    render = _function(request, "render")
    assert "const { state: phase, index = null } = state.trickster_window" in render
    # Closed, pending, or a window already asked: nothing is posted.
    assert "if (phase !== 'open' || index === null || index === asked) return" in render
    assert render.index("asked = index") < render.index("postTrickster(sessionId)")
    # The reply is dropped: the Card arrives through the polled state's cards[]. Nothing shows a pending state.
    assert "postTrickster(sessionId).catch(() => undefined)" in render and "await" not in render
    assert "document" not in request and "classList" not in request
    assert request.count("postTrickster(") == 1
    assert "render(first)" in request  # a reload inside an open window still asks once
    play = _code(_ts("play.ts"))
    assert play.count("parts.push(tricksterRequest(session.id, session))") == 1
    api = _code(_ts("api/index.ts"))
    assert "postJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}/trickster`, {})" in api


# --- In play: the Trickster's bubble by the chest (story mode) ---------------------------------------------------


def test_a_new_card_shows_in_the_tricksters_bubble_for_7_s_and_is_announced_once_and_the_card_log_keeps_it():
    chest = _code(_ts("components/treasure-chest.ts"))
    render = _function(chest, "render")
    assert "const arrived = state.cards.slice(cardsHeard)" in render and "cardsHeard = state.cards.length" in render
    assert "bubble(text.sentence, false)" in render  # announced once below, with its label, not again as a line
    assert render.count("announce(") == 1
    assert "export const BUBBLE_MS = 7000" in chest
    # The first state is only read: after a reload no Card shows again and the introduction is not repeated.
    assert "let cardsHeard = latest.cards.length" in chest and "const first = cardsHeard === 0" in render
    # The Card log lists every Card, its label and a rejected Card's lines (tests/web/test_card_log.py).
    assert "cardText(room, card)" in _ts("components/card-log.ts")
    assert not (WEB_SRC / "components/trickster-card.css").exists() and "tricksterCard(" not in _ts("components/trickster-card.ts")


def test_the_announcements_read_the_card_and_on_the_first_card_the_introduction():
    announce = _exported(_code(_ts("components/trickster-card.ts")), "cardAnnouncement")
    assert "first ? strings.firstCardAnnouncement : strings.cardAnnouncement" in announce
    assert "'role line': strings.tricksterRole" in announce and "'voice line': strings.tricksterVoice" in announce
    assert "sentence: text.sentence" in announce and "'outcome label': text.label" in announce
    # A rejected Card appends its "Proposed:" line and its reason.
    assert "`${line} ${text.refusal.proposed}. ${text.refusal.reason}`" in announce


def test_the_card_text_pairs_are_in_the_design_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    for pair in ("| `ink` #2A1D11 | `parchment` #E8DBBE |", "| `ink-muted` #5A4630 | `parchment` |",
                 "| `text-muted` / `card-skipped-text` | `chrome-raised` / `card-skipped-surface` |",
                 "| `success-ink` #275A2C | `parchment` |", "| `wrong-ink` #87321B | `parchment` |"):
        assert pair in table, pair
