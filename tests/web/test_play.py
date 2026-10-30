"""FR-11, UX-DR26, UX-DR27, UX-DR29, UX-DR39, UX-DR65, AR-7: the pack, the Riddle note (story mode; the Wizard notes
before it, tests/web/test_story_play.py), the Evidence card the landing's sample page draws, the Wizard portrait
component, and the poll that feeds them.

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
    for name in ("play.ts", "poll-ticker.ts", "scene/index.ts", "components/inventory.ts", "components/riddle-note.ts"):
        assert "visibilitychange" not in _ts(name) and "document.hidden" not in _ts(name), name
    # One poll in flight at a time; a poll sent before a reply that arrived first is stale and dropped.
    assert "if (polling) return" in play and "if (before === replies) receive(state)" in play
    assert "ticker.terminate()" in play


def test_open_locks_the_pack_and_wrong_attempts_render_only_from_server_state():
    play = _ts("play.ts")
    receive = play.split("function receive(", 1)[1].split("\n  }\n", 1)[0]
    assert "for (const render of parts) render(state)" in receive
    # Every state the parts draw is a poll or the server's reply to a posted event.
    assert play.count("receive(") == 3  # the definition, the reply and the poll, nothing else
    assert "parts.push(held.render, note.render, chest.render)" in play
    inventory, note = _ts("components/inventory.ts"), _ts("components/riddle-note.ts")
    assert "state.inventory.flatMap(" in inventory
    assert "state.locks_open.includes(puzzle.id)" in note and "state.active_puzzle_id" in note
    for text in (inventory, note, _ts("components/evidence-card.ts"), _ts("wizards/portrait.ts")):
        assert "postEvent" not in text and ".post(" not in text


def test_the_pack_is_a_row_of_76_by_60_crops_in_gilt_edged_wells_with_a_dashed_free_well():
    inventory = _ts("components/inventory.ts")
    assert "const ITEM_WIDTH = 76" in inventory and "const ITEM_HEIGHT = 60" in inventory
    assert "button.setAttribute('aria-label', capitalized(interactable.label))" in inventory
    assert "slots.setAttribute('role', 'group')" in inventory and "slots.setAttribute('aria-labelledby', name.id)" in inventory
    rules = _rules("components/inventory.css")
    slot = rules[".inventory-slot"]
    assert (slot["width"], slot["height"], slot["border-radius"]) == ("76px", "60px", "var(--rounded-md)")
    assert rules[".inventory-slot.is-empty"]["border"] == "1px dashed var(--hairline)"
    assert rules[".inventory-item"]["border"] == "1px solid var(--gilt)"
    assert rules[".inventory-item[aria-pressed='true']"] == {"border": "2px solid var(--lamp)"}


def test_an_empty_pack_shows_one_dashed_slot_and_its_caption():
    inventory = _ts("components/inventory.ts")
    empty = inventory.split("if (held.length === 0) {", 1)[1].split("return describe()", 1)[0]
    assert "empty.className = 'inventory-slot is-empty'" in empty and "slots.replaceChildren(empty)" in empty
    assert _rules("components/inventory.css")[".inventory-caption"]["color"] == "var(--text-muted)"


def test_evidence_cards_are_inset_rows_a_note_until_solved_then_a_64px_crop_cut_from_the_first_polygons_bounds():
    card, crop, geometry = _ts("components/evidence-card.ts"), _ts("components/crop.ts"), _ts("scene/geometry.ts")
    assert "const THUMB_PX = 64" in card and "crop(roomId, interactable, THUMB_PX)" in card
    assert "label.className = 'evidence-card-label label'" in card and "label.textContent = interactable.label" in card
    assert "attribute.className = 'evidence-card-attribute body-sm'" in card
    assert "attribute.textContent = evidence.visible_attribute" in card
    # The crop is the largest polygon's bounds (one instance, so far-apart instances never shrink it to a slice of the
    # room; story mode: the largest, so the two-polygon pillows read whole) at the crop's aspect inside the photo;
    # `box` is never read.
    assert "const polygon = largest(interactable.polygons ?? []) ?? []" in crop and "if (polygon.length === 0) return canvas" in crop
    assert "cropAround(bounds([polygon]), { width: image.naturalWidth, height: image.naturalHeight }, width / height)" in crop
    assert ".box" not in crop
    assert "export function bounds(polygons: readonly Polygon[]): Rect" in geometry
    rules = _rules("components/evidence-card.css")
    row = rules[".evidence-card"]
    assert row["background"] == "var(--parchment-shade)" and row["color"] == "var(--ink)"
    assert row["border-radius"] == "var(--rounded-md)" and row["grid-template-columns"] == "64px minmax(0, 1fr)"
    assert rules[".evidence-card-note"] == {"grid-template-columns": "minmax(0, 1fr)"}  # the note has no crop
    assert "note.className = 'evidence-card-note-text wizard-line'" in card
    assert rules[".evidence-card .crop"] == {"border-radius": "var(--rounded-sm)"}
    assert rules[".evidence-card-attribute"] == {"color": "var(--ink-muted)"}
    # Story mode: only the landing's sample page draws it, on paper; the Play screen draws none.
    assert ".wizard-notes .evidence-card" not in rules and "evidenceCard" not in _ts("play.ts")
    # The whole card's reward fade is the only motion: no hover, focus, animation, highlight or announcement.
    assert row["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".evidence-card.is-arriving"] == {"opacity": "0"}
    css = (WEB_SRC / "components/evidence-card.css").read_text()
    assert not re.search(r":hover|:focus|animation|\.is-(?!arriving)", css)
    assert "aria-live" not in card and "classList" not in card


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


def test_the_wizard_portrait_is_a_gilt_ringed_circle_at_its_sizes_reading_web_public_portraits():
    portrait = _ts("wizards/portrait.ts")
    assert "export type PortraitSize = 24 | 26 | 30 | 32 | 36 | 40 | 48 | 96" in portrait
    assert "return `/portraits/${wizard}.webp`" in portrait  # web/public/portraits/<wizard>.webp (scripts/portraits.py)
    assert "image.alt = ''" in portrait
    assert "element.style.setProperty('--portrait-size', `${size}px`)" in portrait
    rules = _rules("wizards/portrait.css")
    circle = rules[".wizard-portrait"]
    assert circle["border"] == "2px solid var(--gilt)" and circle["border-radius"] == "var(--rounded-full)"
    assert circle["width"] == circle["height"] == "var(--portrait-size)" and circle["box-sizing"] == "border-box"
    assert rules[".wizard-portrait img"]["object-fit"] == "cover"
    # The side column is gone (story mode), and with it the hairline ring it gave the portraits.
    assert ".side-column .wizard-portrait" not in rules
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


def test_every_new_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "chrome-raised"), ("text-muted", "chrome-raised"), ("lamp", "chrome-raised"),
             ("success", "chrome-raised"), ("wrong", "chrome-raised"), ("text", "canvas"), ("text-muted", "canvas"),
             ("ink", "parchment-shade"), ("ink-muted", "parchment-shade"), ("focus-ring", "chrome")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"


def test_the_four_lock_room_serves_what_the_note_and_the_pack_draw(client: TestClient, four_lock_room: Room):
    view = client.get(f"/api/rooms/{four_lock_room.id}").json()
    ids = {interactable["id"] for interactable in view["interactables"]}
    for puzzle in view["puzzles"]:
        assert puzzle["clue"] and puzzle["lore"] and puzzle["evidence_cards"] == []  # held back until the lock opens (story mode)
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    assert session["inventory"] == [] and session["active_puzzle_id"] == view["puzzles"][0]["id"]
    events = f"/api/sessions/{session['id']}/events"
    client.post(events, json={"type": "click", "interactable_id": IX["key"]})
    clock = view["puzzles"][1]["id"]
    client.post(events, json={"type": "lock_input", "input": {"type": "code", "puzzle_id": clock, "code": "000"}})
    client.post(events, json={"type": "lock_input", "input": {"type": "code", "puzzle_id": clock, "code": "415"}})
    state = client.get(f"/api/sessions/{session['id']}").json()
    assert state["inventory"] == [IX["key"]]
    # locks_open keeps the order locks opened in; the note reads availability from it.
    assert state["locks_open"] == [view["puzzles"][0]["id"], clock]
    assert state["wrong_attempts"][clock] == 1
    shown = client.get(f"/api/sessions/{session['id']}/room").json()["puzzles"]
    assert all(card["interactable"] in ids for puzzle in shown for card in puzzle["evidence_cards"])
    assert [bool(puzzle["evidence_cards"]) for puzzle in shown] == [True, True, False, False, False]


def test_a_reload_rebuilds_the_play_screen_from_the_session_and_its_room_announcing_nothing():
    shell, play = _ts("shell.ts"), _ts("play.ts")
    assert "getSession(sessionId).catch(refused)" in shell and "const room: Promise<PlayView> = getEffectiveRoom(session.id)" in play
    # The first draw shows the active riddle and held items in place: no beat, no stamp, no fade.
    note, held = _ts("components/riddle-note.ts"), _ts("components/inventory.ts")
    assert "let latest = play.state()" in note and "render(latest)" in note
    assert "if (before !== undefined && !before.has(interactable.id)) arrived.push(button)" in held
    assert "lockOpened(() => shown, latest, scene," in play  # the mounting state is only read
    # Only a reply to a posted input speaks; a reload posts nothing.
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
    assert "const held = reconnecting || ended" in hold and "sceneFrame.inert = held || beating" in hold
    assert "stage.classList.toggle('is-dimmed', held)" in hold  # everything that takes input hangs in the frame
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
    assert rules[".scene-stage.is-dimmed .scene-world"] == {"opacity": "0.6"}  # the photo and its walls
    assert "sceneColumn.append(stage)" in _ts("play.ts")
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


def test_the_play_screen_keeps_one_ornate_frame_around_the_scene_and_the_note_is_paper_on_the_wall():
    """Reviewer feedback 4 (Oct 29): the gilt rule and the vignette frame the Scene alone. Story mode (owner decision
    Oct 29): the Riddle note is a parchment note pinned on the wall inside it, the pack and the chest stand on its floor
    and the walk map is a quiet dark card, so nothing else is framed."""
    frame = _rules("scene/scene.css")[".scene-frame"]
    assert frame["border"] == "1px solid var(--gilt)" and frame["box-shadow"] == "var(--elevation-vignette)"
    for name in ("components/walk-map.css", "components/order-progress.css", "components/inventory.css"):
        css = _code((WEB_SRC / name).read_text())
        assert "--elevation-vignette" not in css and "--parchment" not in css, name
    note = _rules("components/riddle-note.css")[".riddle-note"]
    assert note["background"] == "var(--parchment)" and "--elevation-vignette" not in note["box-shadow"]
    marker = design_text().split("  riddle-note:\n", 1)[1].split("\n  wizard-portrait:", 1)[0]
    assert "background: '{colors.parchment}'" in marker and "clue: '{typography.wizard-line}'" in marker


