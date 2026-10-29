"""FR-19, FR-11, UX-DR27, UX-DR39, UX-DR65: an accepted Trickster edit reshapes the room in play.

A changed `room_revision` refetches the session's Effective room and redraws the Wizard notes and the Hotspots in
place; a Decoy adds an Evidence card drawn like the real ones, a Merge leaves its placeholder, a Shortcut reveals an
entry only once nothing else gates it, and a Loosen's Rung shows on the Rung line and in its entry. The client has no
test runner, so the checks read the TypeScript and the stylesheets (`npm run build` and `tsc --noEmit` prove they
compile; the criteria are checked in Chrome against the fixture rooms), and the API checks read what the client reads.
"""

import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_sessions import Ticker, click, code, start
from tests.api.test_trickster_route import (
    app_client,
    open_window,
    proposals_dir,
    state_of,
    trickster,
)
from tests.fixtures.rooms import IX, PZ
from tests.web.design import WEB_SRC, css_rules, source_ts
from tests.web.test_strings import _strings
from tests.web.test_types import _interfaces, _keys


def _ts(name: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _nested(text: str, start: str) -> str:
    """The body of a function nested one level, from `start` to its closing brace."""
    return text.split(start, 1)[1].split("\n  }\n", 1)[0]


def _proposal(kind: str, target: str, **payload: str) -> dict[str, Any]:
    """A proposal on the Puzzle named `target`, its payload as given (ids already resolved)."""
    return {"type": kind, "puzzle": PZ[target], "payload": {"type": kind, **payload}}


def _decoy(puzzle: str) -> dict[str, Any]:
    return _proposal("decoy", puzzle, interactable=IX["rug"], visible_attribute="faded red")


def _merge(waiting: str, on: str) -> dict[str, Any]:
    return _proposal("merge", waiting, puzzle_a=PZ[on], puzzle_b=PZ[waiting])


def _client(tmp_path: Path, room: Room, *proposals: dict[str, Any]) -> tuple[TestClient, Ticker]:
    ticker = Ticker()
    recording = {"room_id": room.id, "proposals": list(proposals)}
    return app_client(tmp_path, ticker, room, proposals_dir=proposals_dir(tmp_path, recording)), ticker


def _room(client: TestClient, session_id: str) -> dict[str, dict[str, Any]]:
    view = client.get(f"/api/sessions/{session_id}/room").json()
    return {puzzle["id"]: puzzle for puzzle in view["puzzles"]}


# --- The refetch ---------------------------------------------------------------------------------------------------


def test_the_play_screen_draws_from_the_effective_room_and_records_the_revision_it_mounted_with():
    play, api = _ts("play.ts"), _ts("api/index.ts")
    assert "return getJson<PlayView>(`/sessions/${encodeURIComponent(sessionId)}/room`)" in api
    # The Play screen and the screen under the Completion sheet both read the Effective room, never GET /rooms/<id>.
    assert play.count("const room: Promise<PlayView> = getEffectiveRoom(session.id)") == 2 and "getRoom" not in play
    assert "let fetchedRevision = session.room_revision" in play


def test_a_changed_room_revision_refetches_the_room_once_and_redraws_the_notes_and_the_hotspots():
    play = _ts("play.ts")
    refetch = play.split("const refetchRoom = async (state: SessionState): Promise<void> => {", 1)[1].split("\n      }\n", 1)[0]
    # A rejected or skipped Card leaves room_revision as it was, so nothing is fetched; one request at a time.
    assert "if (refetching || state.room_revision === fetchedRevision) return" in refetch
    assert "const next = await getEffectiveRoom(session.id)" in refetch
    assert "fetchedRevision = state.room_revision" in refetch
    assert refetch.index("scene.reshape(next)") < refetch.index("notes.reshape(next)")
    assert "void refetchRoom(latest)" in refetch  # a revision that arrived meanwhile is fetched next
    assert "parts.push((state) => void refetchRoom(state))" in play
    # No page reload, and the Inventory, the Hint area and the Scene are never rebuilt for it.
    assert "location.reload" not in play and play.count("inventory(view, play.useOn)") == 2
    assert play.count("mountScene(") == 2 and "announce(" not in refetch


def test_the_scene_keeps_its_photo_and_lays_changed_hotspots_again_with_focus_on_the_same_one():
    scene = _ts("scene/index.ts")
    reshape = _nested(scene, "function reshape(view: PlayView): void {")
    assert "room = view" in reshape
    assert "if (before === undefined || size === undefined || photo.hidden || layer === undefined) return" in reshape
    # The shown photo's Hotspots are laid again only when its Interactables changed, so focus stays put otherwise.
    assert "if (on(before) === on(view)) return" in reshape
    assert "const focused = svg.contains(document.activeElement) ? document.activeElement?.id : undefined" in reshape
    assert "layHotspots(view, size, current)" in reshape
    assert "layer.elements[0].querySelector<SVGElement>(`[id=\"${focused}\"]`)?.focus()" in reshape
    assert "show(" not in reshape and "strip" not in reshape and "useOn" not in reshape
    assert "return { unmount, reshape, lastTarget: () => lastTarget, bloom, say: feedback.say }" in scene


def test_rehung_hotspots_stay_focusable_buttons_that_show_all_objects_still_outlines():
    layer, play = _ts("scene/hotspots.ts"), _ts("play.ts")
    assert "hotspot.setAttribute('tabindex', '0')" in layer and "hotspot.setAttribute('role', 'button')" in layer
    assert "if (event.key === 'Enter') handlers.onActivate(interactable)" in layer
    # "Show all objects" marks the Scene column, which outlives every Hotspot laid inside it.
    assert "onToggle: (on) => sceneColumn.classList.toggle('is-showing-all', on)" in play


# --- The Wizard notes ----------------------------------------------------------------------------------------------


def test_the_notes_keep_their_entries_and_redraw_the_evidence_cards_and_count_in_place():
    notes = _ts("components/wizard-notes.ts")
    reshape = _nested(notes, "function reshape(view: PlayView): void {")
    assert "for (const puzzle of view.puzzles) entries.get(puzzle.id)?.evidence(view, puzzle)" in reshape
    assert "entry(" not in reshape  # no entry is rebuilt, so the Code field and focus stay
    evidence = _nested(notes, "function drawEvidence(view: PlayView, shown: PlayPuzzle): void {")
    assert "if (key === drawnEvidence) return" in evidence
    assert "shown.evidence_cards.flatMap((card) => {" in evidence  # in the order PlayView gives
    assert "[evidenceCard(view.id, interactable, card)]" in evidence
    assert "count.textContent = cards.length === 1 ? strings.evidenceCard : fill(strings.evidenceCards, { k: cards.length })" in evidence
    assert "evidence.replaceChildren(...cards)" in evidence
    # No highlight, badge, animation or announcement marks the new card or the count.
    for banned in ("fadeIn", "classList", "announce", "animate", "setAttribute"):
        assert banned not in evidence, banned


def test_a_decoy_card_is_drawn_like_any_other_and_nothing_in_the_client_tells_it_apart():
    card = _ts("components/evidence-card.ts")
    assert "element.className = 'evidence-card'" in card and card.count("className =") == 3
    assert set(_keys(_interfaces()["Evidence"])) == {"interactable", "visible_attribute"}
    for path in ("components/evidence-card.ts", "components/wizard-notes.ts", "scene/index.ts", "play.ts"):
        assert "decoy" not in _ts(path).lower(), path
    assert not any(re.search(r"\b(?:interface|type) (?:PlayView|PlayPuzzle|Evidence)\b", text) for text in source_ts().values())
    assert "import type { PlayPuzzle, PlayView, RungChangeEvent, SessionState } from '../../types'" in _ts("components/wizard-notes.ts")


def test_an_entry_a_merge_gates_fades_out_and_its_placeholder_holds_its_place_with_focus():
    assert _strings()["puzzleWaits"] == "Puzzle {n} now waits on another puzzle."
    notes = _ts("components/wizard-notes.ts")
    reshape = _nested(notes, "function reshape(view: PlayView): void {")
    # Gated: a drawn, unopened entry whose Puzzle now waits on an unopened one.
    assert "return shown && now !== undefined && !now.requires.every((id) => open.includes(id))" in reshape
    assert "waiting.set(puzzle.id, { puzzle, line: waitingLine(place(puzzle.id)) })" in reshape
    assert "made.element.classList.add('is-leaving')" in reshape and "setTimeout(redraw, stateFadeMs())" in reshape
    # Focus inside the gated entry moves to its line when the line takes its place, whichever draw does that.
    focus = _nested(notes, "function keepFocus(focused: Element | null): HTMLElement | undefined {")
    assert "const line = [...waiting].find(([id]) => entries.get(id)?.element.contains(focused))?.[1].line" in focus
    assert "line.focus()" in focus
    line = notes.split("function waitingLine(n: number): HTMLParagraphElement {", 1)[1].split("\n}\n", 1)[0]
    assert "paragraph('notes-entry notes-waiting label', fill(strings.puzzleWaits, { n }))" in line
    assert "element.tabIndex = -1" in line
    # The placeholder keeps the place the entry was drawn in until the Puzzle is available again.
    draw = _nested(notes, "function draw(state: SessionState, afterOpening: boolean): void {")
    assert "puzzle.requires.every((id) => state.locks_open.includes(id))) waiting.delete(puzzle.id)" in draw
    assert "const rows = listed.map((puzzle) => waiting.get(puzzle.id)?.line ?? built(puzzle).element)" in draw
    rules = css_rules((WEB_SRC / "components/wizard-notes.css").read_text())
    assert rules[".notes-entry.is-leaving"] == {"opacity": "0"}
    assert rules[".notes-waiting"] == {"margin": "0", "color": "var(--ink-muted)"}


def test_a_merge_that_lands_in_the_open_hold_keeps_its_entry_faded_until_the_holds_draw_puts_the_line_in():
    notes = _ts("components/wizard-notes.ts")
    reshape = _nested(notes, "function reshape(view: PlayView): void {")
    # Gated against the latest state: a lock the hold shows open gates nothing.
    assert "const open = latest?.locks_open ?? []" in reshape and "drawnOpen" not in reshape
    # The fade-out is never undone while the hold runs; the hold's draw swaps the line in.
    assert "classList.remove('is-leaving')" not in reshape
    redraw = reshape.split("const redraw = (): void => {", 1)[1].split("\n    }\n", 1)[0]
    assert "if (!holding && latest !== undefined && element.isConnected) draw(latest, false)" in redraw
    draw = _nested(notes, "function draw(state: SessionState, afterOpening: boolean): void {")
    # Only an entry drawn again loses the class, and a line that took focus keeps it over the arriving heading.
    shown = draw.split("const shown = listed.flatMap((puzzle) => {", 1)[1].split("\n    })\n", 1)[0]
    assert "if (waiting.has(puzzle.id)) return []" in shown
    assert shown.index("return []") < shown.index("made.element.classList.remove('is-leaving')")
    assert "line = keepFocus(focused)" in draw and "if (!afterOpening || line !== undefined) return" in draw


def test_a_row_swap_keeps_focus_on_an_entry_that_stays():
    notes = _ts("components/wizard-notes.ts")
    draw = _nested(notes, "function draw(state: SessionState, afterOpening: boolean): void {")
    # replaceChildren detaches every kept entry for a moment, so focus is read before and put back after.
    assert draw.index("const focused = document.activeElement") < draw.index("element.replaceChildren(...rows)")
    assert draw.index("element.replaceChildren(...rows)") < draw.index("line = keepFocus(focused)")
    # Focusing forces a style pass, so the arriving entries take their transparent start first or skip their fade.
    assert draw.index("for (const made of arrived) fadeIn(made.element)") < draw.index("line = keepFocus(focused)")
    focus = _nested(notes, "function keepFocus(focused: Element | null): HTMLElement | undefined {")
    assert "if (!(focused instanceof HTMLElement) || document.activeElement === focused) return undefined" in focus
    assert "if (focused.isConnected) {\n      focused.focus({ preventScroll: true })" in focus


def test_a_shortcut_entry_fades_in_only_once_no_prerequisite_is_unmet():
    notes = _ts("components/wizard-notes.ts")
    order_ = notes.split("export function availableInOrder(", 1)[1].split("\n}\n", 1)[0]
    assert ".filter(({ puzzle }) => puzzle.requires.every((id) => locksOpen.includes(id)))" in order_
    draw = _nested(notes, "function draw(state: SessionState, afterOpening: boolean): void {")
    assert "if (before.size > 0) for (const made of arrived) fadeIn(made.element)" in draw
    reshape = _nested(notes, "function reshape(view: PlayView): void {")
    assert "if (!holding && latest !== undefined && element.isConnected) draw(latest, false)" in reshape


def test_a_loosen_rung_shows_on_the_rung_line_and_in_its_puzzles_entry():
    hint = _ts("components/hint-area.ts")
    loosen = hint.split("function byLoosen(", 1)[1].split("\n}\n", 1)[0]
    assert "return only !== undefined && rest.length === 0 && events?.[only]?.type === 'trickster_card'" in loosen
    opened = hint.split("export function openedRungs(", 1)[1].split("\n}\n", 1)[0]
    assert "change.rung !== shown.rung || byLoosen(change, events)" in opened
    assert "onOpened(openedRungs(latest.rung_changes, line.shown, latest.trigger_events))" in hint


def test_nothing_the_reshape_draws_reaches_the_live_region_and_every_fade_is_instant_under_reduced_motion():
    assert "announce" not in _ts("components/wizard-notes.ts")
    fade = _ts("fade.ts")
    assert "export function stateFadeMs(): number {" in fade and "getPropertyValue('--motion-state')" in fade
    tokens = (WEB_SRC / "tokens.css").read_text()
    assert "--motion-state: 0ms;" in tokens and "prefers-reduced-motion: reduce" in tokens
    rules = css_rules((WEB_SRC / "components/wizard-notes.css").read_text())
    assert rules[".notes-entry"]["transition"] == "opacity var(--motion-state) var(--motion-ease)"


# --- What the client reads from the API ----------------------------------------------------------------------------


def test_an_accepted_decoy_raises_the_revision_and_adds_one_card_a_rejected_or_skipped_card_does_not(
    tmp_path: Path, four_lock_room: Room
):
    client, ticker = _client(tmp_path, four_lock_room, _decoy("clock_code"), _merge("clock_code", "shelf_order"))
    session_id = start(client, four_lock_room)
    before = _room(client, session_id)
    open_window(client, ticker, session_id, click("key"), 0)
    assert state_of(client, session_id)["room_revision"] == 0
    trickster(client, session_id)
    assert state_of(client, session_id)["room_revision"] == 1
    after = _room(client, session_id)
    cards = after[PZ["clock_code"]]["evidence_cards"]
    assert len(cards) == len(before[PZ["clock_code"]]["evidence_cards"]) + 1
    assert all(set(card) == {"interactable", "visible_attribute"} for card in cards)
    # A Merge that would deadlock is rejected: the revision, and so the client's room, stay as they were.
    open_window(client, ticker, session_id, code("clock_code", "415"), 1)
    trickster(client, session_id)
    state = state_of(client, session_id)
    assert [card["accepted"] for card in state["cards"]] == [True, False] and state["room_revision"] == 1
    assert _room(client, session_id) == after


def test_an_accepted_merge_gates_the_visible_entry_the_card_names(tmp_path: Path, four_lock_room: Room):
    client, ticker = _client(tmp_path, four_lock_room, _merge("key_on_chest", "clock_code"))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)  # Puzzle 4 (the chest) is available
    trickster(client, session_id)
    state = state_of(client, session_id)
    (card,) = state["cards"]
    assert card["accepted"] and card["edit_type"] == "merge" and state["room_revision"] == 1
    room = _room(client, session_id)
    gated = room[card["puzzle_id"]]
    # The Card's Puzzle is the one that now waits on an unopened Puzzle, so its label and the placeholder agree.
    assert card["puzzle_id"] == PZ["key_on_chest"] and card["related_puzzle_id"] in gated["requires"]
    assert not all(required in state["locks_open"] for required in gated["requires"])
    assert state["active_puzzle_id"] != PZ["key_on_chest"]


def test_an_accepted_shortcut_frees_a_puzzle_with_no_other_unmet_prerequisite(tmp_path: Path, four_lock_room: Room):
    shortcut = _proposal("shortcut", "key_on_chest", puzzle=PZ["key_on_chest"], requires=PZ["shelf_order"])
    client, ticker = _client(tmp_path, four_lock_room, _merge("key_on_chest", "shelf_order"), shortcut)
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, code("clock_code", "415"), 0)
    trickster(client, session_id)  # the chest now waits on the shelf as well as the key
    open_window(client, ticker, session_id, click("key"), 1)
    assert _room(client, session_id)[PZ["key_on_chest"]]["requires"] == [PZ["find_key"], PZ["shelf_order"]]
    trickster(client, session_id)
    state = state_of(client, session_id)
    assert [card["accepted"] for card in state["cards"]] == [True, True] and state["room_revision"] == 2
    freed = _room(client, session_id)[PZ["key_on_chest"]]
    assert all(required in state["locks_open"] for required in freed["requires"])


def test_an_accepted_loosen_opens_its_rung_with_a_rung_change_the_card_triggered(tmp_path: Path, four_lock_room: Room):
    loosen = _proposal("loosen", "clock_code", puzzle=PZ["clock_code"], rung="nudge")
    client, ticker = _client(tmp_path, four_lock_room, loosen)
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    trickster(client, session_id)
    state = state_of(client, session_id)
    (change,) = state["rung_changes"]
    assert change["puzzle_id"] == PZ["clock_code"] and change["rung"] == 1
    (position,) = change["triggered_by"]
    assert state["trigger_events"][str(position)]["type"] == "trickster_card" and state["room_revision"] == 1


def test_a_reload_reads_the_same_effective_room_and_revision_and_the_stored_room_is_unchanged(
    tmp_path: Path, four_lock_room: Room
):
    client, ticker = _client(tmp_path, four_lock_room, _decoy("clock_code"))
    session_id = start(client, four_lock_room)
    open_window(client, ticker, session_id, click("key"), 0)
    trickster(client, session_id)
    shown = _room(client, session_id)
    assert state_of(client, session_id)["room_revision"] == 1 and _room(client, session_id) == shown
    stored = {puzzle["id"]: puzzle for puzzle in client.get(f"/api/rooms/{four_lock_room.id}").json()["puzzles"]}
    assert len(stored[PZ["clock_code"]]["evidence_cards"]) == len(shown[PZ["clock_code"]]["evidence_cards"]) - 1
