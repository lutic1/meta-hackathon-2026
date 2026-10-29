"""FR-19, UX-DR30, UX-DR40 to UX-DR42, UX-DR70, UX-DR74, UX-DR76: Trickster cards in the Hint area, the Trickster
request that asks for them once per window, and the `TricksterCard` projection they are read from.

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
    """The body of a function nested one level, as the Hint area's are."""
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
    assert strings["moreInCardLog"].format(n=2) == "2 more in the Card log"
    assert strings["dismissCard"] == "Dismiss card"


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


# --- The Hint area stack ---------------------------------------------------------------------------


def test_at_most_two_cards_stack_newest_on_top_above_the_rung_line_the_rest_behind_the_card_log_line():
    hint = _code(_ts("components/hint-area.ts"))
    assert "export const CARDS_STACKED = 2" in hint
    assert "upper.append(stack, more, rungLine)" in hint and "stack.className = 'hint-cards'" in hint
    restack = _function(hint, "restack")
    # Newest on top: the last held Cards, reversed; only one while "How hints work" is open.
    assert "const shown = held.slice(-(triggersShown ? 1 : CARDS_STACKED)).reverse()" in restack
    assert "more.textContent = fill(strings.moreInCardLog, { n: rest })" in restack and "more.hidden = rest === 0" in restack
    assert "more.className = 'hint-more body-sm'" in hint
    toggled = _function(hint, "triggersOpen")
    assert "element.classList.toggle('is-triggers-open', open)" in toggled and "restack()" in toggled
    # The hint controls stay in the pinned lower part, outside the scrolling upper part.
    assert "lower.append(ask, triggers)" in hint and "element.append(upper, lower)" in hint
    rules = _rules("components/hint-area.css")
    assert rules[".hint-cards"]["flex-direction"] == "column" and rules[".hint-cards[hidden]"]["display"] == "none"
    assert rules[".hint-more"]["color"] == "var(--lamp)"  # a link on dark (tests/web/test_card_log.py)


def test_while_a_card_is_stacked_the_tray_grows_past_its_cap_until_the_wizard_notes_reach_notes_min():
    # The open item "Hint area cap and the first Card" (EXPERIENCE.md): the tray grows the way it does while the
    # Triggers panel is open, so the Card and the Rung line get the side column's spare height before scrolling.
    rules = _rules("components/hint-area.css")
    grown = "calc(100% - var(--spacing-notes-min) - var(--spacing-5))"
    assert rules[".hint-area.is-triggers-open,\n.hint-area:has(> .hint-upper > .hint-cards:not([hidden]))"] == {"max-height": grown}
    assert rules[".hint-area"]["max-height"] == f"min(var(--spacing-hint-area-max), {grown})"


def test_short_of_room_the_triggers_panel_gives_way_to_its_newest_row_before_the_card_and_the_rung_line_scroll():
    # The tray's bands are its flex items (the lower part and the Triggers slot are display: contents), so the panel
    # shrinks first, to one body-sm row inside its padding (the newest, scrolled to), then the upper part scrolls; the
    # hint button and "How hints work" never shrink.
    rules = _rules("components/hint-area.css")
    assert rules[".hint-lower,\n.hint-triggers"] == {"display": "contents"}
    assert rules[".hint-upper"]["flex"] == "1 1 auto" and rules[".hint-upper"]["min-height"] == "0"
    assert rules[".hint-area .triggers-panel"] == {
        "flex-shrink": "1000",
        "min-height": "calc(1.45 * 14px)",
    }
    assert rules[".hint-ask"]["flex"] == "none"
    panel = _rules("components/triggers-panel.css")
    assert panel[".triggers"] == {"display": "contents"}
    assert panel[".triggers-toggle"]["flex"] == "none" and panel[".triggers-panel"]["overflow-y"] == "auto"
    assert "flex-shrink: 1000" not in (WEB_SRC / "components/hint-area.css").read_text().split(".triggers-panel")[0]
    assert ".hint-upper:has(" not in (WEB_SRC / "components/hint-area.css").read_text()  # no floor fights the controls
    # The upper part scrolls to its end for a line that arrives and for a Card that enters, so the Card's sentence,
    # its outcome and the Rung line share the frame and the introduction is a scroll above.
    hint = _code(_ts("components/hint-area.ts"))
    assert "upper.scrollTop = upper.scrollHeight" in _function(hint, "draw")
    assert "upper.scrollTop = upper.scrollHeight" in _function(hint, "enter")
    assert "upper.scrollTop = 0" not in hint


def test_a_card_that_enters_or_leaves_restacks_the_bands_and_the_triggers_panel_reveals_its_newest_row():
    # The panel shrinks to its newest row when a Card enters and grows back when one is dismissed, each with a stale
    # scrollTop, so the Hint area tells the panel to scroll that row back into view after each restack; on a toggle
    # the panel reveals the row itself (components/triggers-panel.ts), so the Hint area says nothing then.
    hint = _code(_ts("components/hint-area.ts"))
    assert "onStacked: () => void," in hint
    enter = _function(hint, "enter")
    assert enter.index("restack()") < enter.index("upper.scrollTop = upper.scrollHeight") < enter.index("onStacked()")
    dismiss = _function(hint, "dismiss")
    assert dismiss.index("restack()") < dismiss.index("onStacked()") < dismiss.index("next.focus()")
    assert "onStacked()" not in _function(hint, "triggersOpen")
    play = _code(_ts("play.ts"))
    assert "hints = hintArea(view, play, frame.guide, notes.openedRungs, cardLog.open, () => triggers.reveal())" in play
    assert "const triggers = triggersPanel(view, latest, currentPlace().profile, (open) => area.triggersOpen(open))" in play


def test_a_new_card_enters_after_the_lock_open_state_and_is_announced_once():
    hint = _code(_ts("components/hint-area.ts"))
    received = _function(hint, "receiveCards")
    assert "if (state.locks_open.length > locksSeen) hold()" in received
    assert "state.cards.slice(cardsHeard).forEach((card, index) => waiting.push({ card, first: cardsHeard + index === 0 }))" in received
    # The Open chip's 1200 ms, then the entry collapse and the next Puzzle's 200 ms fade-in.
    hold = _function(hint, "hold")
    assert "OPEN_HOLD_MS + stateFadeMs()" in hold and "import { OPEN_HOLD_MS } from './wizard-notes.ts'" in hint
    enter = _function(hint, "enter")
    assert "if (holding !== undefined || waiting.length === 0) return" in enter
    assert "fadeIn(made)" in enter and "announce(arrived.map(({ line }) => line).join(' '))" in enter
    assert enter.count("announce(") == 1
    assert "receiveCards(state)" in _function(hint, "render")


def test_after_a_reload_no_card_is_restacked_and_the_introduction_is_not_shown_again():
    hint = _code(_ts("components/hint-area.ts"))
    # Only cards[] entries after those in the first state arrive; the introduction goes on cards[0] alone.
    assert "let cardsHeard = latest.cards.length" in hint
    assert "first: cardsHeard + index === 0" in hint


def test_a_card_stays_until_dismissed_and_focus_moves_to_the_next_card_else_the_hint_button():
    hint = _code(_ts("components/hint-area.ts"))
    dismiss = _function(hint, "dismiss")
    assert "held.splice(held.indexOf(card), 1)" in dismiss and "card.remove()" in dismiss
    assert "const next = stack.children[at] ?? stack.lastElementChild" in dismiss
    assert "if (next instanceof HTMLElement) next.focus()\n    else button.focus()" in dismiss
    card = _code(_ts("components/trickster-card.ts"))
    assert "element.tabIndex = -1" in card  # focusable from script, so focus can land on the next Card
    assert "dismiss.setAttribute('aria-label', strings.dismissCard)" in card and "dismiss.type = 'button'" in card
    assert "dismiss.addEventListener('click', onDismiss)" in card
    # Nothing but the dismiss control removes a Card from the Hint area.
    assert hint.count("held.splice(") == 1


# --- The Card itself ---------------------------------------------------------------------------------


def test_the_card_anatomy_with_the_introduction_on_the_first_card_only():
    card = _code(_ts("components/trickster-card.ts"))
    built = _exported(card, "tricksterCard")
    assert "element.className = `trickster-card is-${text.outcome}`" in built
    intro = built.split("if (first) {", 1)[1].split("} else {", 1)[0]
    assert intro.index("strings.trickster)") < intro.index("strings.tricksterRole") < intro.index("strings.tricksterVoice")
    assert intro.index("strings.tricksterVoice") < intro.index("text.sentence")
    assert "paragraph('trickster-card-role body-sm', strings.tricksterRole)" in intro
    assert "paragraph('trickster-card-sentence wizard-line', text.sentence)" in built
    assert "paragraph('trickster-card-outcome label', text.label)" in built
    assert "paragraph('trickster-card-refusal body-sm', text.refusal.proposed)" in built
    assert "paragraph('trickster-card-refusal body-sm', text.refusal.reason)" in built
    assert "element.append(wizardPortrait('trickster', 48), words, dismiss)" in built
    # Every in-character line carries the visually hidden "The Trickster:" prefix once.
    assert built.count("speakerPrefix('trickster')") == 2


def test_the_announcements_read_the_card_and_on_the_first_card_the_introduction():
    announce = _exported(_code(_ts("components/trickster-card.ts")), "cardAnnouncement")
    assert "first ? strings.firstCardAnnouncement : strings.cardAnnouncement" in announce
    assert "'role line': strings.tricksterRole" in announce and "'voice line': strings.tricksterVoice" in announce
    assert "sentence: text.sentence" in announce and "'outcome label': text.label" in announce
    # A rejected Card appends its "Proposed:" line and its reason.
    assert "`${line} ${text.refusal.proposed}. ${text.refusal.reason}`" in announce


def test_the_card_styles_follow_the_design_components():
    rules = _rules("components/trickster-card.css")
    card = rules[".trickster-card"]
    assert card["background"] == "var(--card-accepted-surface)" and card["color"] == "var(--ink)"
    assert card["border-left"] == "4px solid var(--card-accepted-edge)" and card["border-radius"] == "var(--rounded-md)"
    assert card["grid-template-columns"] == "48px minmax(0, 1fr)" and card["box-shadow"] == "var(--elevation-paper)"
    # A 200 ms fade, instant under reduced motion (tokens.css sets --motion-state to 0ms).
    assert card["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".trickster-card.is-arriving"]["opacity"] == "0"
    rejected = rules[".trickster-card.is-rejected"]
    assert rejected == {"border-left-color": "var(--card-rejected-edge)", "background": "var(--card-rejected-surface)"}
    skipped = rules[".trickster-card.is-skipped"]
    assert skipped["border"] == "1px dashed var(--card-skipped-edge)" and skipped["background"] == "var(--card-skipped-surface)"
    assert skipped["color"] == "var(--card-skipped-text)" and skipped["box-shadow"] == "none"
    assert rules[".trickster-card.is-skipped .wizard-portrait"]["opacity"] == "0.6"
    assert rules[".trickster-card-words > .trickster-card-role"]["color"] == "var(--ink-muted)"
    assert rules[".trickster-card.is-skipped .trickster-card-role"]["color"] == "var(--card-skipped-text)"
    dismiss = rules[".trickster-card-dismiss"]
    assert dismiss["width"] == "32px" and dismiss["height"] == "32px"
    assert "outline" not in dismiss  # the shared :focus-visible ring
    assert "--motion-state: 0ms;" in _ts("tokens.css")


def test_the_card_text_pairs_are_in_the_design_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    for pair in ("| `ink` #2A1D11 | `parchment` #E8DBBE |", "| `ink-muted` #5A4630 | `parchment` |",
                 "| `text-muted` / `card-skipped-text` | `chrome-raised` / `card-skipped-surface` |",
                 "| `success-ink` #275A2C | `parchment` |", "| `wrong-ink` #87321B | `parchment` |"):
        assert pair in table, pair
