"""FR-11, UX-DR26, UX-DR27, UX-DR29, UX-DR39, UX-DR65, AR-7: the Inventory, the Wizard notes with Evidence cards, the
Wizard portrait component, and the poll that feeds them.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The API checks serve the
four-lock fixture room the way the Play screen reads it.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX
from tests.web.design import REPO, WEB_SRC, css_rules, design_text
from tests.web.test_contrast import PROPS, _hex, contrast


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def test_the_play_screen_polls_the_session_every_2000_ms_from_a_worker_so_a_hidden_tab_keeps_polling():
    play, ticker = _ts("play.ts"), _ts("poll-ticker.ts")
    assert "export const POLL_MS = 2000" in play
    assert "new Worker(new URL('./poll-ticker.ts', import.meta.url), { type: 'module' })" in play
    assert "ticker.postMessage(POLL_MS)" in play and "ticker.onmessage = () => void poll()" in play
    assert "setInterval(() => postMessage(null), event.data)" in ticker
    assert "const state = await getSession(session.id)" in play
    # Nothing pauses it: no visibility listener anywhere in the Play screen.
    for name in ("play.ts", "poll-ticker.ts", "scene/index.ts", "components/inventory.ts", "components/wizard-notes.ts"):
        assert "visibilitychange" not in _ts(name) and "document.hidden" not in _ts(name), name
    # One poll in flight at a time; a poll sent before a reply that arrived first is stale and dropped.
    assert "if (polling) return" in play and "if (before === replies) receive(state)" in play
    assert "ticker.terminate()" in play


def test_open_locks_the_inventory_and_wrong_attempts_render_only_from_server_state():
    play = _ts("play.ts")
    receive = play.split("function receive(", 1)[1].split("\n  }\n", 1)[0]
    assert "for (const render of parts) render(state)" in receive
    # Every state the parts draw is a poll or the server's reply to a posted event.
    assert play.count("receive(") == 3  # the definition, the reply and the poll, nothing else
    assert "parts.push(held.render, notes.render)" in play
    inventory, notes = _ts("components/inventory.ts"), _ts("components/wizard-notes.ts")
    assert "state.inventory.flatMap(" in inventory
    assert "state.locks_open.includes(puzzle.id)" in notes and "state.wrong_attempts[puzzle.id] ?? 0" in notes
    assert "state.active_puzzle_id === puzzle.id" in notes
    for text in (inventory, notes, _ts("components/evidence-card.ts"), _ts("wizards/portrait.ts")):
        assert "addEventListener" not in text and "postEvent" not in text and ".post(" not in text


def test_the_inventory_is_a_chrome_raised_tray_of_64px_slots_three_across_with_56px_crops_and_captions():
    inventory, shell = _ts("components/inventory.ts"), _rules("shell.css")
    assert "const ACROSS = 3" in inventory and "const ITEM_PX = 56" in inventory
    assert "crop(room.id, interactable, ITEM_PX)" in inventory
    assert "caption.className = 'inventory-caption caption'" in inventory and "caption.textContent = interactable.label" in inventory
    assert "(ACROSS - (held.length % ACROSS)) % ACROSS" in inventory  # dashed slots to the end of the row
    rules = _rules("components/inventory.css")
    tray = rules[".inventory"]
    assert tray["background"] == "var(--chrome-raised)" and tray["border-radius"] == "var(--rounded-md)"
    assert tray["border"] == "1px solid var(--hairline)" and "box-shadow" not in tray  # flat, a hairline edge
    assert tray["grid-template-columns"] == "repeat(3, 64px)" and tray["color"] == "var(--text)"
    well = rules[".inventory-well"]
    assert (well["width"], well["height"]) == ("64px", "64px")
    assert rules[".inventory-slot.is-empty .inventory-well"] == {"border": "1px dashed var(--hairline)"}
    # The tray sits right of the Thumbnail strip, about 288 px wide, in the Scene column's 88 px row.
    assert shell[".scene-strip-row"]["grid-template-columns"] == "minmax(0, 1fr) 288px"
    assert shell[".scene-strip-row > .inventory"] == {"grid-column": "2"}


def test_an_empty_inventory_shows_one_dashed_slot_and_nothing_in_hand_yet():
    inventory = _ts("components/inventory.ts")
    empty = inventory.split("if (held.length === 0) {", 1)[1].split("return\n", 1)[0]
    assert "empty.classList.add('is-empty')" in empty and "line.textContent = strings.nothingInHand" in empty
    assert "element.replaceChildren(empty, line)" in empty
    assert "line.className = 'inventory-nothing body-sm'" in empty
    assert _rules("components/inventory.css")[".inventory-nothing"]["color"] == "var(--text-muted)"


def test_the_wizard_notes_draw_one_entry_per_available_puzzle_in_room_order():
    notes = _ts("components/wizard-notes.ts")
    order = notes.split("export function availableInRoomOrder(", 1)[1].split("\n}\n", 1)[0]
    # Owner decision 68: available when every prerequisite is open, in Room.puzzles[] order, the order the Active-puzzle
    # fallback follows (AD-4), so the earliest unsolved entry is the one "Current" falls back to; never re-sorted.
    assert "return puzzles.filter((puzzle) => puzzle.requires.every((id) => locksOpen.includes(id)))" in order
    assert ".sort(" not in order and "availableInOrder" not in notes
    # A Puzzle a Merge hid keeps its place, as its placeholder, until it is available again (Story 4.6).
    assert "availableInRoomOrder(room.puzzles.map((puzzle) => waiting.get(puzzle.id)?.puzzle ?? puzzle), state.locks_open)" in notes
    # n is the Puzzle's fixed place in the Room, never its place in the list.
    assert "const place = (id: string): number => room.puzzles.findIndex((puzzle) => puzzle.id === id) + 1" in notes
    assert "entry(room, puzzle, place(puzzle.id), play)" in notes
    assert "heading.textContent = fill(strings.puzzleHeading, { n })" in notes


def test_each_entry_is_heading_and_count_then_portrait_and_clue_evidence_lore_rungs_and_lock():
    notes = _ts("components/wizard-notes.ts")
    assert "cards.length === 1 ? strings.evidenceCard : fill(strings.evidenceCards, { k: cards.length })" in notes
    assert "head.append(title, count, opened)" in notes
    assert "clue.append(wizardPortrait('riddler', 32), paragraph('wizard-line', speakerPrefix('riddler'), puzzle.clue))" in notes
    assert "paragraph('notes-lore lore', speakerPrefix('riddler'), puzzle.lore)" in notes
    assert "body.append(clue, evidence, lore, rungs, lock)" in notes
    assert "shown.evidence_cards.flatMap(" in notes and "drawEvidence(room, puzzle)" in notes  # in PlayView order
    rules = _rules("components/wizard-notes.css")
    sheet = rules[".wizard-notes"]
    # A flat chrome-raised tray with a hairline edge since Oct 29 (reviewer feedback 4): no paper, no shadow.
    assert sheet["background"] == "var(--chrome-raised)" and sheet["color"] == "var(--text)"
    assert sheet["border"] == "1px solid var(--hairline)" and "box-shadow" not in sheet
    assert sheet["padding"] == "var(--spacing-4)" and sheet["min-height"] == "var(--spacing-notes-min)"
    assert sheet["overflow-y"] == "auto" and sheet["border-radius"] == "var(--rounded-lg)"
    assert rules[".notes-entry + .notes-entry"] == {"border-top": "1px solid var(--hairline)"}
    assert rules[".notes-count"]["color"] == "var(--text-muted)" and rules[".notes-lore"]["color"] == "var(--text-muted)"
    assert rules[".notes-waiting"]["color"] == "var(--text-muted)"
    assert rules[".notes-clue"]["grid-template-columns"] == "32px minmax(0, 1fr)"
    assert rules[".notes-clue"]["column-gap"] == "var(--spacing-2)"
    assert css_rules((WEB_SRC / "shell.css").read_text())[".side-column"]["flex-direction"] == "column"


def test_the_active_puzzle_marker_follows_active_puzzle_id_with_a_lamp_rule_and_the_word_current():
    notes = _ts("components/wizard-notes.ts")
    update = notes.split("function update(", 1)[1].split("\n  }\n", 1)[0]
    assert "const isCurrent = state.active_puzzle_id === puzzle.id" in update
    assert "element.classList.toggle('is-current', isCurrent)" in update and "current.hidden = !isCurrent" in update
    assert "current.textContent = strings.current" in notes and "current.className = 'notes-current label'" in notes
    rules = _rules("components/wizard-notes.css")
    assert rules[".notes-entry.is-current"]["border-left"] == "3px solid var(--lamp)"
    assert rules[".notes-current"] == {"color": "var(--lamp)"}
    marker = design_text().split("  active-puzzle-marker:\n", 1)[1].split("\n  clue-card-slot:", 1)[0]
    assert "rule: '3px solid {colors.lamp}'" in marker and "labelColor: '{colors.lamp}'" in marker


def test_the_sheet_scrolls_to_the_current_entry_when_active_puzzle_id_moves_without_taking_focus():
    """Playtest Oct 29: after the pillows opened Puzzle 1 the sheet showed Puzzle 3 while Puzzle 2 was Current. Each
    draw whose `active_puzzle_id` differs from the one the sheet last followed scrolls the sheet (only the sheet) so
    the Current entry stands at its top; nothing is focused, so keyboard focus stays in the Scene."""
    notes = _ts("components/wizard-notes.ts")
    draw = notes.split("function draw(state: SessionState, afterOpening: boolean): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "if (state.active_puzzle_id !== followed) {" in draw
    assert draw.index("element.replaceChildren(...rows)") < draw.index("follow(")  # the rows are in place first
    # A frame later, so the Hint area mounted after the first draw has taken its share of the side column.
    assert draw.index("requestAnimationFrame(() => {") < draw.index("follow(current)")
    follow = notes.split("function follow(", 1)[1].split("\n  }\n", 1)[0]
    assert "element.scrollTop +=" in follow and "focus(" not in follow and "scrollIntoView" not in follow
    assert "parseFloat(getComputedStyle(element).paddingTop)" in follow  # the entry's top meets the sheet's padding
    # The Open hold draws nothing, so the sheet moves only once the solved entry has collapsed.
    render = notes.split("function render(state: SessionState): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "follow(" not in render
    experience = (REPO / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md").read_text()
    row = experience.split("\n| Wizard notes |", 1)[1].split("\n", 1)[0]
    assert "scrolls the sheet so the Current entry stands at its top" in row


def test_the_sheet_follows_the_current_entry_again_whenever_its_size_changes():
    """Playtest Oct 29 (second replay): a Trickster card stacking in the Hint area shrank the sheet from 546 px to
    299 px while it stayed scrolled to the solved Puzzle, so the Current entry and the card just added to it were out
    of view. One ResizeObserver on the sheet re-follows the entry "Current" last moved to whenever the sheet's size
    changes (a Card stacking or leaving, the Hint area growing or shrinking), as `follow` does: instantly, never
    focused."""
    notes = _code(_ts("components/wizard-notes.ts"))
    assert notes.count("new ResizeObserver(") == 1
    observer = notes.split("new ResizeObserver(", 1)[1].split(".observe(element)", 1)[0]
    assert "followed" in observer and "follow(" in observer and "isConnected" in observer
    assert "focus(" not in observer and "scrollIntoView" not in observer and "smooth" not in notes
    # Nothing threads a callback from the Hint area into the notes for it.
    assert "notes.follow" not in _code(_ts("play.ts")) and "follow:" not in notes
    experience = (REPO / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md").read_text()
    row = experience.split("\n| Wizard notes |", 1)[1].split("\n", 1)[0]
    assert "and again whenever the sheet's height changes" in row


def test_open_locks_collapse_their_entry_and_wrong_attempts_show_the_servers_count():
    notes = _ts("components/wizard-notes.ts")
    update = notes.split("function update(", 1)[1].split("\n  }\n", 1)[0]
    assert "const open = state.locks_open.includes(puzzle.id)" in update
    assert "for (const part of [clue, lore, rungs, lock]) part.hidden = open" in update  # the Evidence cards stay
    assert "opened.hidden = !open" in update and "count.hidden = open" in update
    assert _rules("components/wizard-notes.css")[".notes-entry-body > [hidden]"] == {"display": "none"}
    assert "opened.textContent = strings.solved" in notes
    assert "wrong.textContent = fill(strings.notThis, { n: attempts })" in update
    rules = _rules("components/wizard-notes.css")
    # The chips sit on the dark notes tray, so they take each state's light form.
    assert rules[".chip-open"] == {"border": "1px solid var(--success)", "color": "var(--success)"}
    assert rules[".chip-not-this"] == {"border": "1px solid var(--wrong)", "color": "var(--wrong)"}
    assert rules[".chip"]["border-radius"] == "var(--rounded-sm)"


def test_evidence_cards_are_inset_rows_a_note_until_solved_then_a_64px_crop_cut_from_the_polygons_bounds():
    card, crop, geometry = _ts("components/evidence-card.ts"), _ts("components/crop.ts"), _ts("scene/geometry.ts")
    assert "const THUMB_PX = 64" in card and "crop(roomId, interactable, THUMB_PX)" in card
    assert "label.className = 'evidence-card-label label'" in card and "label.textContent = interactable.label" in card
    assert "attribute.className = 'evidence-card-attribute body-sm'" in card
    assert "attribute.textContent = evidence.visible_attribute" in card
    # The crop is the polygons' bounds squared inside the photo; `box` is never read.
    assert "squareAround(bounds(polygons), { width: image.naturalWidth, height: image.naturalHeight })" in crop
    assert "export function bounds(polygons: readonly Polygon[]): Rect" in geometry
    rules = _rules("components/evidence-card.css")
    row = rules[".evidence-card"]
    assert row["background"] == "var(--parchment-shade)" and row["color"] == "var(--ink)"
    assert row["border-radius"] == "var(--rounded-md)" and row["grid-template-columns"] == "64px minmax(0, 1fr)"
    assert rules[".evidence-card-note"] == {"grid-template-columns": "minmax(0, 1fr)"}  # the note has no crop
    assert "note.className = 'evidence-card-note-text wizard-line'" in card
    assert rules[".evidence-card .crop"] == {"border-radius": "var(--rounded-sm)"}
    assert rules[".evidence-card-attribute"] == {"color": "var(--ink-muted)"}
    # In the Wizard notes the inset is the canvas, its text on dark (the landing's sample page keeps the paper form).
    assert rules[".wizard-notes .evidence-card"] == {"background": "var(--canvas)", "color": "var(--text)"}
    assert rules[".wizard-notes .evidence-card-attribute"] == {"color": "var(--text-muted)"}
    # The whole card's reward fade is the only motion: no hover, focus, animation, highlight or announcement.
    assert row["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".evidence-card.is-arriving"] == {"opacity": "0"}
    css = (WEB_SRC / "components/evidence-card.css").read_text()
    assert not re.search(r":hover|:focus|animation|\.is-(?!arriving)", css)
    assert "aria-live" not in card and "classList" not in card
    notes = _ts("components/wizard-notes.ts")
    opening = notes.split("function opening(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "solved = true" in opening and "for (const card of drawEvidence(...source)) fadeIn(card)" in opening


# Builds the shipped `evidenceCard` with a stand-in `document` (stylesheet imports load as empty modules) and prints
# the markup each card gives as a tree of tags, classes, text and children.
EVIDENCE_RUNNER = """
import { register } from 'node:module'
register('data:text/javascript,' + encodeURIComponent(`
  export async function load(url, context, next) {
    return url.endsWith('.css') ? { format: 'module', source: '', shortCircuit: true } : next(url, context)
  }
`))
const node = (tag) => ({
  tag, className: '', textContent: '', children: [], style: {}, attributes: {},
  setAttribute(name, value) { this.attributes[name] = value },
  append(...children) { this.children.push(...children) },
})
globalThis.window = { devicePixelRatio: 1 }
globalThis.document = { createElement: node }
const { evidenceCard } = await import(process.argv[1])
const tree = (element) => typeof element === 'string' ? element : {
  tag: element.tag, className: element.className, text: element.textContent, children: element.children.map(tree),
}
const interactable = { id: 'ix', label: 'throw pillows', photo: 2, polygons: [], instances: 1, attributes: [] }
const evidence = { interactable: 'ix', visible_attribute: 'on sofa' }
process.stdout.write(JSON.stringify([false, true].map((solved) => tree(evidenceCard('room', interactable, evidence, solved)))))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's Evidence card")


def _flat(tree: dict[str, Any]) -> list[dict[str, Any]]:
    return [tree, *(node for child in tree["children"] for node in _flat(child))]


@needs_node
def test_an_unsolved_puzzle_s_evidence_card_is_the_riddler_s_note_alone_and_the_solved_one_names_the_object():
    """Playtest Oct 29: a find lock's Evidence card named its own answer. Until the Puzzle is solved the card shows
    only the read attribute as the Riddler's quoted note: no label and no crop; solved, the whole card is the reward."""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", EVIDENCE_RUNNER, (WEB_SRC / "components/evidence-card.ts").as_uri()],
        cwd=REPO, capture_output=True, text=True, check=True,
    )
    unsolved, solved = json.loads(result.stdout)
    note = _flat(unsolved)
    assert [node["text"] for node in note if node["text"]] == ["The Riddler's note: \u201con sofa\u201d"]
    assert not any(node["tag"] in ("canvas", "img") for node in note)
    assert not any("throw pillows" in node["text"] for node in note)
    assert "evidence-card-label" not in json.dumps(unsolved)
    whole = _flat(solved)
    assert [node["tag"] for node in whole].count("canvas") == 1
    assert {node["text"] for node in whole} >= {"throw pillows", "on sofa"}


def test_the_wizard_portrait_is_a_gilt_ringed_circle_at_four_sizes_reading_web_public_portraits():
    portrait = _ts("wizards/portrait.ts")
    assert "export type PortraitSize = 24 | 32 | 48 | 96" in portrait
    assert "return `/portraits/${wizard}.webp`" in portrait  # web/public/portraits/<wizard>.webp (scripts/portraits.py)
    assert "image.alt = ''" in portrait
    assert "element.style.setProperty('--portrait-size', `${size}px`)" in portrait
    rules = _rules("wizards/portrait.css")
    circle = rules[".wizard-portrait"]
    assert circle["border"] == "2px solid var(--gilt)" and circle["border-radius"] == "var(--rounded-full)"
    assert circle["width"] == circle["height"] == "var(--portrait-size)" and circle["box-sizing"] == "border-box"
    assert rules[".wizard-portrait img"]["object-fit"] == "cover"
    # In the Play screen's side column the ring is the hairline: gilt frames the Scene alone there.
    assert rules[".side-column .wizard-portrait"] == {"border-color": "var(--hairline)"}
    # No play path generates one (FR-23).
    assert "generate" not in _code(portrait).lower()


def test_a_missing_portrait_falls_back_to_the_initial_in_display_sm_gilt_on_chrome_raised():
    portrait = _ts("wizards/portrait.ts")
    assert "initial.className = 'wizard-portrait-initial display-sm'" in portrait
    assert "initial.textContent = wizard.charAt(0).toUpperCase()" in portrait
    assert "initial.setAttribute('aria-hidden', 'true')" in portrait
    # The painting replaces the placeholder only once it has loaded; a missing file keeps the placeholder.
    assert "image.onerror = () => reject(" in portrait and "element.replaceChildren(image)" in portrait
    rules = _rules("wizards/portrait.css")
    assert rules[".wizard-portrait"]["background"] == "var(--chrome-raised)"
    assert rules[".wizard-portrait > .wizard-portrait-initial"]["color"] == "var(--gilt)"
    # The initial is text: gilt on chrome-raised clears 4.5:1 for 22 px type.
    assert contrast(_hex(PROPS["gilt"])[0], _hex(PROPS["chrome-raised"])[0]) >= 4.5


def test_every_in_character_line_carries_a_visually_hidden_speaker_prefix():
    portrait, style = _ts("wizards/portrait.ts"), _rules("style.css")
    assert "prefix.className = 'visually-hidden'" in portrait and "prefix.textContent = `${SPEAKERS[wizard]} `" in portrait
    assert "riddler: strings.speakerRiddler" in portrait
    hidden = style[".visually-hidden"]
    assert hidden["position"] == "absolute" and hidden["width"] == hidden["height"] == "1px"
    assert hidden["clip-path"] == "inset(50%)" and hidden["overflow"] == "hidden"


def test_the_notes_tray_takes_the_shared_two_tone_focus_ring():
    rules = _rules("components/wizard-notes.css")
    # No shadow of its own to keep, so the global ring (outline over the inner ring) applies unchanged.
    assert ".wizard-notes:focus-visible" not in rules and "box-shadow" not in rules[".wizard-notes"]
    assert _ts("components/wizard-notes.ts").count("element.tabIndex = 0") == 1


def test_every_new_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "chrome-raised"), ("text-muted", "chrome-raised"), ("lamp", "chrome-raised"),
             ("success", "chrome-raised"), ("wrong", "chrome-raised"), ("text", "canvas"), ("text-muted", "canvas"),
             ("ink", "parchment-shade"), ("ink-muted", "parchment-shade"), ("focus-ring", "chrome")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"


def test_the_four_lock_room_serves_what_the_notes_and_the_inventory_draw(client: TestClient, four_lock_room: Room):
    view = client.get(f"/api/rooms/{four_lock_room.id}").json()
    ids = {interactable["id"] for interactable in view["interactables"]}
    for puzzle in view["puzzles"]:
        assert puzzle["clue"] and puzzle["lore"] and puzzle["evidence_cards"]
        assert all(card["interactable"] in ids and card["visible_attribute"] for card in puzzle["evidence_cards"])
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    assert session["inventory"] == [] and session["active_puzzle_id"] == view["puzzles"][0]["id"]
    events = f"/api/sessions/{session['id']}/events"
    client.post(events, json={"type": "click", "interactable_id": IX["key"]})
    clock = view["puzzles"][1]["id"]
    client.post(events, json={"type": "lock_input", "input": {"type": "code", "puzzle_id": clock, "code": "000"}})
    client.post(events, json={"type": "lock_input", "input": {"type": "code", "puzzle_id": clock, "code": "415"}})
    state = client.get(f"/api/sessions/{session['id']}").json()
    assert state["inventory"] == [IX["key"]]
    # locks_open keeps the order locks opened in, which is the order the notes read availability from.
    assert state["locks_open"] == [view["puzzles"][0]["id"], clock]
    assert state["wrong_attempts"][clock] == 1


def test_a_reload_rebuilds_the_play_screen_from_the_session_and_its_room_announcing_nothing():
    shell, play = _ts("shell.ts"), _ts("play.ts")
    assert "getSession(sessionId).catch(refused)" in shell and "const room: Promise<PlayView> = getEffectiveRoom(session.id)" in play
    # The first draw shows open locks collapsed and held items in place: no Open hold, no fade, no focus move.
    notes, held = _ts("components/wizard-notes.ts"), _ts("components/inventory.ts")
    assert "previous === undefined\n        ? []" in notes and "if (before.size > 0) for (const made of arrived) fadeIn(made.element)" in notes
    assert "if (before !== undefined && !before.has(interactable.id)) arrived.push(item)" in held
    assert "if (opening.text !== null && playHasBegun(session)) play.openingLine = opening.text" in play
    # Only a reply to a posted input speaks its feedback line; a reload posts nothing.
    assert re.findall(r"announce\(([^)]*)\)", _code(play)) == ["strings.reconnectingPlay", "`${strings.speakerGuide} ${line}`"]


def test_two_consecutive_missed_polls_show_the_reconnecting_strip_once_and_hold_every_input():
    play = _ts("play.ts")
    assert "export const MISSES_TO_RECONNECT = 2" in play
    assert "const strip = statusStrip(strings.reconnectingPlay)" in play
    missed = play.split("function missed(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "misses += 1" in missed and "if (misses < MISSES_TO_RECONNECT || reconnecting || ended) return" in missed
    assert "stage.prepend(strip)" in missed and "announce(strings.reconnectingPlay)" in missed
    # A failed poll is missed, and so is one still unanswered at the next tick.
    poll = play.split("async function poll(): Promise<void> {", 1)[1].split("\n  }\n", 1)[0]
    assert "if (polling) return missed()" in poll and "else missed()" in poll
    hold = play.split("function holdInputs(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "const held = reconnecting || ended" in hold and "element.inert = held" in hold
    assert "[sceneFrame, stripRow, ...sideColumn.children]" in hold and "stage.classList.toggle('is-dimmed', held)" in hold
    # The strip is plain and takes no focus.
    strip = _ts("components/status-strip.ts")
    assert "tabIndex" not in strip and "focus" not in _code(strip)
    assert _rules("components/status-strip.css")[".status-strip"]["height"] == "var(--spacing-status-strip)"


def test_the_strip_sits_above_the_scene_frame_which_shrinks_by_its_height_and_the_photo_dims_to_60_percent():
    rules = _rules("shell.css")
    stage = rules[".scene-stage"]
    assert stage["display"] == "flex" and stage["flex-direction"] == "column" and stage["position"] == "relative"
    assert rules[".scene-stage > .status-strip"] == {"flex": "none"}
    assert rules[".scene-stage > .scene-frame"] == {"flex": "1 1 0"}
    assert rules[".scene-stage.is-dimmed .scene-photo"] == {"opacity": "0.6"}
    assert "sceneColumn.append(stage, stripRow)" in _ts("play.ts")
    assert "status-strip: 32px" in design_text()


def test_an_input_that_never_reached_the_server_is_dropped_and_the_next_state_removes_the_strip():
    play, field = _ts("play.ts"), _ts("components/code-field.ts")
    receive = play.split("function receive(", 1)[1].split("\n  }\n", 1)[0]
    assert "misses = 0" in receive and "strip.remove()" in receive and "for (const render of parts) render(state)" in receive
    # A post that failed counts nothing on the client: no state is drawn from it and the field keeps its value.
    post = play.split("post: async (body) => {", 1)[1].split("\n    },", 1)[0]
    assert post.index("await postEvent(") < post.index("receive(reply)")
    assert "showChip(null) // nothing reached the server" in field and "field.value = " not in field


def test_a_session_answered_404_dims_the_photo_under_the_session_gone_line_with_start_again():
    play, ended = _ts("play.ts"), _ts("components/play-ended.ts")
    assert "if (error instanceof RequestFailed && error.status === 404) endPlay()" in play
    end = play.split("function endPlay(): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "ticker.terminate()" in end and "stage.append(playEnded(() => void startAgain()))" in end and "holdInputs()" in end
    again = play.split("async function startAgain(): Promise<void> {", 1)[1].split("\n  }\n", 1)[0]
    assert "startSession(await sessionStart(session.room_id, currentPlace().profile, frame.mode))" in again
    assert "route: { name: 'play', sessionId: next.id }" in again
    assert "line.textContent = strings.sessionGone" in ended and "line.className = 'play-ended-line body-md'" in ended
    assert "secondaryButton({ label: strings.startAgain, onActivate: onStartAgain })" in ended
    box = _rules("components/play-ended.css")[".play-ended-box"]
    assert box["background"] == "var(--chrome-raised)" and box["color"] == "var(--text)"


def test_a_room_answered_404_room_not_found_shows_the_centered_480px_card_focused_on_its_heading():
    play, card, gone = _ts("play.ts"), _ts("components/notice-card.ts"), _ts("room-gone.ts")
    assert "const gone = roomGone(error)\n      if (mounted && gone !== null) roomMissing(gone)" in play
    assert "if (error.status === 404 && error.code === 'room_not_found') return 'room_not_found'" in gone
    missing = play.split("function roomMissing(gone: RoomGone): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "showRoomGone(frame.body, gone, frame.mode, currentPlace().profile)" in missing
    assert "heading: deleted ? strings.roomDeleted : strings.roomNotFound" in gone
    assert "sentence: deleted ? strings.roomDeletedBody : strings.roomNotFoundBody" in gone
    assert "label: deleted || mode === 'hosted' ? strings.goToDemoRooms : strings.buildARoom" in gone
    assert "route: { name: 'home' }" in gone
    assert "body.replaceChildren(card.element)\n  card.heading.focus()" in gone
    assert "heading.tabIndex = -1" in card and "heading.className = 'notice-card-heading display-sm'" in card
    assert "body.className = 'notice-card-sentence body-md'" in card and "primaryButton({" in card
    rules = _rules("components/notice-card.css")
    sheet = rules[".notice-card"]
    assert sheet["width"] == "480px" and sheet["background"] == "var(--chrome-raised)" and sheet["color"] == "var(--text)"
    assert sheet["border-radius"] == "var(--rounded-lg)" and sheet["box-shadow"] == "var(--elevation-overlay)"
    token = design_text().split("  leave-room-confirmation:\n", 1)[1].split("\n  build-view-header:", 1)[0]
    assert "width: 480px" in token and "background: '{colors.chrome-raised}'" in token
    assert _rules("shell.css")[".notice-layout"]["place-items"] == "center"


def test_every_color_pair_of_the_reconnecting_ended_and_missing_states_passes_the_audit():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in {("text", "warning-surface"), ("text", "chrome-raised"), ("lamp", "chrome-raised"), ("on-lamp", "lamp")}:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    # The two-tone ring around "Start again" and "Build a room" sits on chrome-raised: 3:1 for non-text.
    assert contrast(_hex(PROPS["focus-ring"])[0], _hex(PROPS["chrome-raised"])[0]) >= 3


def test_an_unknown_session_and_an_unknown_room_answer_404_with_their_codes(client: TestClient):
    session = client.get("/api/sessions/sess_01JZZZZZZZZZZZZZZZZZZZZZZZ")
    assert session.status_code == 404 and session.json()["error"]["code"] == "session_not_found"
    room = client.get("/api/rooms/room_missing")
    assert room.status_code == 404 and room.json()["error"]["code"] == "room_not_found"


def test_the_play_screen_keeps_one_ornate_frame_around_the_scene_and_the_current_riddle_reads_largest():
    """Reviewer feedback 4 (Oct 29): the gilt rule and the vignette frame the Scene alone; the Thumbnail strip, the
    Inventory, the Wizard notes and the Hint area are flat, quiet grounds with a hairline edge, and the Current
    puzzle's Clue is a type step larger (wizard-line-lg) than every other line in the side column."""
    frame = _rules("scene/scene.css")[".scene-frame"]
    assert frame["border"] == "1px solid var(--gilt)" and frame["box-shadow"] == "var(--elevation-vignette)"
    trays = {"components/inventory.css": ".inventory", "components/wizard-notes.css": ".wizard-notes",
             "components/hint-area.css": ".hint-area"}
    for name, selector in trays.items():
        tray = _rules(name)[selector]
        assert tray["background"] == "var(--chrome-raised)" and tray["border"] == "1px solid var(--hairline)", name
        assert "box-shadow" not in tray, name
    for name in ("components/thumbnail-strip.css", "components/order-progress.css", *trays):
        css = _code((WEB_SRC / name).read_text())
        assert "--gilt" not in css and "--elevation-vignette" not in css and "--parchment" not in css, name
    badge = _rules("components/thumbnail-strip.css")[".thumbnail-count"]
    assert badge["background"] == "var(--chrome-raised)" and badge["color"] == "var(--text)"
    # The Current puzzle's Clue in wizard-line-lg, every other entry's in wizard-line.
    current = _rules("components/wizard-notes.css")[".notes-entry.is-current .notes-clue p"]
    lg = css_rules(_ts("tokens.css"))[".wizard-line-lg"]
    assert current == {"font-size": lg["font-size"], "line-height": lg["line-height"]} == {
        "font-size": "24px", "line-height": "1.4"}
    marker = design_text().split("  wizard-notes:\n", 1)[1].split("\n  wizard-portrait:", 1)[0]
    assert "currentClue: '{typography.wizard-line-lg}'" in marker and "edge: '1px solid {colors.hairline}'" in marker
