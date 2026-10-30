"""FR-12, NFR-14, UX-DR35, UX-DR36, UX-DR37, UX-DR26, UX-DR69: Order click progress, and `use_on` by drag or by
select-then-click.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the criteria are checked in
Chrome against the fixture rooms. The API checks post the inputs the Play screen posts against the four-lock fixture
room and read back the states the pips and chips are drawn from.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.redact import to_play_view
from src.domain.schema import OrderSolution, Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX, PZ
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_contrast import PROPS, _hex, contrast
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _body(text: str, signature: str) -> str:
    return text.split(signature, 1)[1].split("\n  }\n", 1)[0]


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def _armed_session(client: TestClient, room: Room) -> tuple[str, dict]:
    """A session with the key found and the clock open, so the order Puzzle and the `use_on` Puzzle are available."""
    session = client.post("/api/sessions", json={"room_id": room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    client.post(events, json={"type": "click", "interactable_id": IX["key"]})
    code = {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["clock_code"], "code": "415"}}
    return events, client.post(events, json=code).json()


def _order(kind: str, puzzle_id: str = PZ["shelf_order"]) -> dict:
    return {"type": "lock_input", "input": {"type": kind, "puzzle_id": puzzle_id}}


def _use_on(item: str, target: str) -> dict:
    return {"type": "lock_input", "input": {"type": "use_on", "item": item, "target": target}}


def _click(interactable: str) -> dict:
    return {"type": "click", "interactable_id": interactable}


# --- Strings, the play view and the pips' source ----------------------------------------------------------------


def test_the_order_and_use_on_strings_are_the_experience_lines():
    strings = _strings()
    assert (strings["startSequence"], strings["stopSequence"]) == ("Start the sequence", "Stop the sequence")
    assert strings["sequenceProgress"].format(filled=2, length=4) == "2 of 4"
    assert strings["usingItem"].replace("{item label}", "brass key") == "Using brass key"
    assert strings["cancel"] == "Cancel"


def test_the_play_view_gives_an_order_puzzle_its_length_and_nothing_of_its_sequence(four_lock_room: Room):
    view = to_play_view(four_lock_room)
    for got, puzzle in zip(view.puzzles, four_lock_room.puzzles, strict=True):
        if isinstance(puzzle.solution, OrderSolution):
            assert got.sequence_length == len(puzzle.solution.interactables) == 3
        else:
            assert got.sequence_length is None
    order = next(p for p in view.model_dump(mode="json")["puzzles"] if p["lock_type"] == "order")
    assert set(order) == {"id", "lock_type", "requires", "is_exit", "clue", "lore", "evidence_cards", "sequence_length", "start_photo"}
    assert "solution" not in order and "interactables" not in order
    assert "sequence_length: number | null;" in (WEB_SRC.parent / "types/index.ts").read_text()


# --- Order click progress ---------------------------------------------------------------------------------------


def test_an_order_riddle_holds_order_click_progress_on_its_note_and_redraws_on_the_buffer():
    note = _ts("components/riddle-note.ts")
    assert "puzzle.lock_type === 'code' ? codeField(puzzle, place, play) : orderProgress(puzzle, play)" in note
    # Every state updates the lock input before the note decides whether to redraw, so every acknowledged click
    # fills a pip even when only the order buffer moved (an armed click).
    draw = _body(note, "function draw(")
    assert draw.index("inputs.get(puzzle.id)?.update(state)") < draw.index("if (key === drawn) return")


def test_the_start_control_posts_order_start_or_stop_and_keeps_focus_through_its_label_change():
    order = _ts("components/order-progress.ts")
    assert "import './order-progress.css'" in order
    assert "secondaryButton({ label: strings.startSequence, onParchment: true, onActivate: () => void toggle() })" in order
    toggle = _body(order, "async function toggle(")
    assert "type: armed ? ('order_stop' as const) : ('order_start' as const), puzzle_id: puzzle.id" in toggle
    assert "await play.post({ type: 'lock_input', input })" in toggle
    assert order.count("play.post(") == 1 and "postEvent(" not in order and "t_ms" not in _code(order)
    assert "if (pending) return" in toggle  # one input per activation
    # One button whose text changes (not a pressed toggle), so focus stays on it across the change.
    update = _body(order, "function update(")
    assert "control.textContent = armed ? strings.stopSequence : strings.startSequence" in update
    assert "aria-pressed" not in order and "replaceWith" not in order and "control.remove" not in order


def test_the_pips_follow_the_servers_buffer_only_and_never_show_which_clicks_were_right():
    order = _ts("components/order-progress.ts")
    update = _body(order, "function update(")
    assert "armed = state.order_buffer.puzzle_id === puzzle.id" in update
    assert "filled = armed ? (state.order_buffer.clicks ?? []).length : 0" in update
    # Pips count clicks; they never compare a click with anything, and nothing outside `update` fills one.
    code = _code(order)
    assert "solution" not in code and "interactable" not in code and "addEventListener" not in code
    assert "const length = puzzle.sequence_length ?? 0" in order and "Array.from({ length }," in order
    assert "pips.setAttribute('aria-hidden', 'true')" in order


def test_the_hidden_description_reads_filled_of_length_and_describes_the_control():
    order = _ts("components/order-progress.ts")
    assert "description.className = 'visually-hidden'" in order
    assert "control.setAttribute('aria-describedby', description.id)" in order
    assert "description.textContent = fill(strings.sequenceProgress, { filled, length })" in _body(order, "function update(")
    assert "aria-live" not in order and "announce(" not in _code(order)  # lock outcomes go through lock-outcomes.ts


def test_a_mismatch_flashes_wrong_ink_for_300_ms_or_resets_at_once_under_reduced_motion_and_shows_not_this():
    order = _ts("components/order-progress.ts")
    assert "export const WRONG_FLASH_MS = 300" in order
    update = _body(order, "function update(")
    assert "const mismatch = armed && counted !== undefined && attempts > counted" in update
    assert "chip.textContent = fill(strings.notThis, { n: attempts })" in update
    assert "if (!mismatch || filled > 0 || reducedMotion()) {" in update
    assert "drawPips(length, true)" in update and "}, WRONG_FLASH_MS)" in update
    assert "window.matchMedia('(prefers-reduced-motion: reduce)').matches" in order
    # A disarm (stopped, or another Puzzle Active) clears Not this and draws empty pips without the flash.
    assert "} else if (!armed) chip.hidden = true" in update
    # The first state (a reload) only sets the count heard, so it never flashes.
    assert "let counted: number | undefined" in order and "counted = attempts" in update


def test_the_pips_are_10px_text_muted_rings_filled_in_lamp_and_reset_in_wrong():
    rules = _rules("components/order-progress.css")
    pip = rules[".order-pip"]
    assert (pip["width"], pip["height"], pip["box-sizing"]) == ("10px", "10px", "border-box")
    assert pip["border"] == "1.5px solid var(--text-muted)" and pip["border-radius"] == "var(--rounded-full)"
    assert rules[".order-pip.is-filled"] == {"border-color": "var(--lamp)", "background": "var(--lamp)"}
    assert rules[".order-pips.is-wrong .order-pip"] == {"border-color": "var(--wrong)", "background": "var(--wrong)"}
    token = design_text().split("  order-progress:\n", 1)[1].split("\n  use-on-selected:", 1)[0]
    assert "pip: 10px" in token and "empty: '1.5px solid {colors.text-muted}'" in token
    assert "filled: '{colors.lamp}'" in token and "reset: '{colors.wrong}'" in token
    assert "transition" not in (WEB_SRC / "components/order-progress.css").read_text()  # nothing animates


def test_starting_the_sequence_arms_it_on_the_active_puzzle_and_stopping_counts_nothing(client: TestClient, four_lock_room: Room):
    events, ready = _armed_session(client, four_lock_room)
    assert ready["order_buffer"] == {"puzzle_id": None, "clicks": []}
    assert client.post(events, json=_click(IX["candle"])).json()["order_buffer"]["clicks"] == []  # unarmed: exploration
    armed = client.post(events, json=_order("order_start")).json()
    assert armed["order_buffer"] == {"puzzle_id": PZ["shelf_order"], "clicks": []}
    assert armed["active_puzzle_id"] == PZ["shelf_order"]  # "Current"
    one = client.post(events, json=_click(IX["candle"])).json()
    assert one["order_buffer"]["clicks"] == [IX["candle"]]  # the first pip
    stopped = client.post(events, json=_order("order_stop")).json()
    assert stopped["order_buffer"] == {"puzzle_id": None, "clicks": []}
    assert stopped["wrong_attempts"][PZ["shelf_order"]] == 0


def test_a_full_length_mismatch_counts_one_and_stays_armed_and_a_reload_rebuilds_the_buffer(
    client: TestClient, four_lock_room: Room
):
    events, _ = _armed_session(client, four_lock_room)
    client.post(events, json=_order("order_start"))
    for interactable in ("candle", "hourglass"):
        state = client.post(events, json=_click(IX[interactable])).json()
    assert state["order_buffer"]["clicks"] == [IX["candle"], IX["hourglass"]]
    session = events.rsplit("/", 1)[0]
    assert client.get(session).json()["order_buffer"] == state["order_buffer"]  # a reload draws the same two pips
    wrong = client.post(events, json=_click(IX["lantern"])).json()
    assert wrong["wrong_attempts"][PZ["shelf_order"]] == 1  # "Not this · 1"
    assert wrong["order_buffer"] == {"puzzle_id": PZ["shelf_order"], "clicks": []}  # emptied, still armed
    for interactable in ("candle", "lantern", "hourglass"):
        state = client.post(events, json=_click(IX[interactable])).json()
    assert PZ["shelf_order"] in state["locks_open"] and state["order_buffer"]["puzzle_id"] is None


def test_another_active_puzzle_disarms_with_no_wrong_attempt(client: TestClient, four_lock_room: Room):
    events, _ = _armed_session(client, four_lock_room)
    client.post(events, json=_order("order_start"))
    client.post(events, json=_click(IX["candle"]))
    # A use_on resolved to the chest Puzzle makes it Active: the order sequence disarms, its count unchanged.
    state = client.post(events, json=_use_on(IX["key"], IX["rug"])).json()
    assert state["active_puzzle_id"] == PZ["key_on_chest"]
    assert state["order_buffer"] == {"puzzle_id": None, "clicks": []}
    assert state["wrong_attempts"][PZ["shelf_order"]] == 0


def test_starting_another_order_puzzle_stops_the_armed_one_first(tmp_path: Path, four_lock_room: Room):
    second = next(p for p in four_lock_room.puzzles if p.id == PZ["key_on_chest"])
    second.lock_type = "order"
    second.solution = OrderSolution(lock_type="order", interactables=[IX["chest"], IX["rug"], IX["door"]])
    client = TestClient(make_app(tmp_path, four_lock_room))
    events, _ = _armed_session(client, four_lock_room)
    client.post(events, json=_order("order_start"))
    client.post(events, json=_click(IX["candle"]))
    state = client.post(events, json=_order("order_start", second.id)).json()
    assert state["order_buffer"] == {"puzzle_id": second.id, "clicks": []}  # the first Puzzle's pips reset
    assert state["active_puzzle_id"] == second.id
    assert state["wrong_attempts"][PZ["shelf_order"]] == 0


# --- use_on: drag and select-then-click -------------------------------------------------------------------------


def test_an_inventory_item_is_a_named_button_selected_by_click_or_enter_and_a_drag_source():
    inventory, use_on = _ts("components/inventory.ts"), _ts("use-on.ts")
    assert "button.setAttribute('aria-label', capitalized(interactable.label))" in inventory
    assert "useOnItem(button, interactable, selection)" in inventory
    assert "button.setAttribute('aria-pressed', String(button.dataset.item === item))" in inventory
    assert "markSelected(item)" in inventory and "markSelected(selection.selected())" in inventory
    # A native button: Enter acts as its click, and a second activation clears the selection.
    item = use_on.split("export function useOnItem(", 1)[1].split("\n}\n", 1)[0]
    assert "selection.select(selection.selected() === interactable.id ? null : interactable.id, 'pack')" in item
    assert "button.draggable = true" in item and "button.classList.add('is-dragging')" in item
    assert "button.classList.remove('is-dragging')" in item
    assert "event.dataTransfer.setDragImage(image, " in item and "const DRAG_PX = 64" in use_on
    # Nothing the drag carries can land in a text field: no data is set on the transfer.
    assert "setData(" not in use_on


def test_the_selected_item_rings_in_lamp_and_the_dragged_one_shows_at_60_percent():
    rules = _rules("components/inventory.css")
    assert rules[".inventory-item"]["border"] == "1px solid var(--gilt)"  # story mode: a gilt-edged well
    assert rules[".inventory-item[aria-pressed='true']"] == {"border": "2px solid var(--lamp)"}
    assert rules[".inventory-item.is-dragging"] == {"opacity": "0.6"}
    drag = _rules("use-on.css")[".use-on-drag-image canvas"]
    assert drag["box-shadow"] == "var(--elevation-paper)"
    token = design_text().split("  use-on-selected:\n", 1)[1].split("\n  chip-not-this:", 1)[0]
    assert "itemRing: '2px solid {colors.lamp}'" in token
    assert "chipBackground: '{colors.parchment}'" in token and "chipForeground: '{colors.ink}'" in token


def test_the_using_chip_is_parchment_pinned_top_left_with_cancel_and_fades_out_when_cleared():
    use_on, scene = _ts("use-on.ts"), _ts("scene/index.ts")
    chip = use_on.split("export function useOnChip(", 1)[1].split("\n}\n", 1)[0]
    assert "secondaryButton({ label: strings.cancel, onActivate: () => selection.select(null), onParchment: true })" in chip
    assert "text.textContent = fill(strings.usingItem, { 'item label': label })" in chip
    assert "element.classList.toggle('is-shown', item !== null)" in chip and "element.inert = item === null" in chip
    assert "itemButton(shown)?.focus()" in chip  # focus inside the chip returns to the item
    assert "frame.prepend(useOnChip(" in scene
    rules = _rules("use-on.css")
    box = rules[".use-on-chip"]
    assert box["position"] == "absolute" and box["top"] == "var(--spacing-4)" and box["left"] == "var(--spacing-4)"
    assert box["background"] == "var(--parchment)" and box["color"] == "var(--ink)"
    assert box["opacity"] == "0" and box["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".use-on-chip.is-shown"]["opacity"] == "1"
    assert _rules("scene/scene.css")[".scene-frame"]["position"] == "relative"


def test_escape_clears_the_selection_and_the_selection_outlives_photo_switches():
    use_on, play = _ts("use-on.ts"), _ts("play.ts")
    assert "if (event.key === 'Escape' && selected !== null) select(null, 'escape')" in use_on
    assert "document.addEventListener('keydown', escape)" in use_on
    assert "dispose: () => document.removeEventListener('keydown', escape)" in use_on
    assert play.count("useOn: useOnSelection()") == 2 and play.count("play.useOn.dispose()") == 2
    # The Scene's photo switch never touches the selection; only a use_on or the user clears it.
    scene = _ts("scene/index.ts")
    for name in ("show", "walk", "arrive", "pushIn"):
        assert "select(" not in scene.split(f"async function {name}(", 1)[1].split("\n  }\n", 1)[0], name
    assert "useOn" not in _ts("components/walk-map.ts")


def test_a_hotspot_activation_while_selected_or_a_drop_posts_one_use_on_and_no_click():
    scene = _ts("scene/index.ts")
    use_on = _body(scene, "async function useOn(")
    assert "play.post({ type: 'lock_input', input: { type: 'use_on', item, target: target.id } })" in use_on
    assert "puzzle_id" not in use_on  # the server resolves the Puzzle from the pair
    assert use_on.index("play.post(") < use_on.index("play.useOn.select(null)")  # posts, then clears the selection
    activate = scene.split("async function activate(", 1)[1].split("\n  }\n", 1)[0]
    assert "if (item !== null) return useOn(item, interactable)" in activate
    assert activate.index("return useOn(") < activate.index("type: 'click'")  # no click once selected
    assert "canDrop: () => play.useOn.dragging() !== null" in scene
    assert "if (item !== null) void useOn(item, interactable).catch(() => undefined)" in scene


def test_a_drag_shows_the_hover_state_on_the_hotspot_under_the_pointer_and_a_drop_elsewhere_posts_nothing():
    layer = _ts("scene/hotspots.ts")
    over = layer.split("function dragOver(", 1)[1].split("\n}\n", 1)[0]
    assert "if (!handlers.canDrop()) return" in over and "event.preventDefault()" in over
    assert "hotspot.classList.add('is-drop-target')" in over
    assert "hotspot.addEventListener('dragleave', () => hotspot.classList.remove('is-drop-target'))" in layer
    drop = layer.split("hotspot.addEventListener('drop', (event) => {", 1)[1].split("})", 1)[0]
    assert "handlers.onDrop(interactable)" in drop
    # Only Hotspots take a drop: nothing else in the client listens for one.
    for path in WEB_SRC.rglob("*.ts"):
        if path.name not in {"hotspots.ts", "capture.ts", "capture-dropzone.ts"}:
            assert "'drop'" not in path.read_text(), path
    rules = _rules("scene/scene.css")
    assert rules[".hotspot.is-drop-target .hotspot-reveal,\n.hotspot.is-drop-target .hotspot-glow"] == {"opacity": "1"}


def test_the_target_label_chip_shows_checking_until_the_verdict():
    layer, scene = _ts("scene/hotspots.ts"), _ts("scene/index.ts")
    pending = _body(layer, "function showPending(")
    assert "checking.className = 'chip chip-pending label'" in pending
    assert "checking.textContent = `${strings.checking}…`" in pending
    assert "return showChip(interactable, [interactable.label, checking], 'pending')" in pending
    # Held: no timeout, pointer leave, blur or focus replaces it until the reply clears it.
    chip = layer.split("function showChip(", 1)[1].split("\n  }\n", 1)[0]
    assert "(release !== undefined && hold !== 'pending')) return () => undefined" in chip
    assert chip.index("release = done") < chip.index("timer = setTimeout(")
    use_on = _body(scene, "async function useOn(")
    assert "const pending = layer?.showPending(target)" in use_on and "pending?.()" in use_on.split("finally {", 1)[1]


def test_the_new_pairs_meet_aa():
    parchment, notes = _hex(PROPS["parchment"])[0], _hex(PROPS["chrome-raised"])[0]
    assert contrast(_hex(PROPS["lamp"])[0], notes) >= 3  # a filled pip (non-text), on the notes tray
    assert contrast(_hex(PROPS["wrong"])[0], notes) >= 3  # the reset pips
    assert contrast(_hex(PROPS["text-muted"])[0], notes) >= 3  # an empty pip's ring
    assert contrast(_hex(PROPS["lamp"])[0], notes) >= 4.5  # the start control
    assert contrast(_hex(PROPS["ink"])[0], parchment) >= 4.5  # the Using chip
    assert contrast(_hex(PROPS["lamp-ink"])[0], parchment) >= 4.5  # its Cancel


def test_use_on_needs_no_puzzle_id_and_a_pair_resolving_to_nothing_counts_nothing(client: TestClient, four_lock_room: Room):
    events, before = _armed_session(client, four_lock_room)
    # An item not in hand is refused and counts nothing.
    refused = client.post(events, json=_use_on(IX["candle"], IX["chest"])).json()
    assert refused["wrong_attempts"] == before["wrong_attempts"] and refused["locks_open"] == before["locks_open"]
    opened = client.post(events, json=_use_on(IX["key"], IX["chest"])).json()
    assert PZ["key_on_chest"] in opened["locks_open"]  # "Open" in the resolved entry
    assert opened["active_puzzle_id"] == PZ["shelf_order"]  # "Current" moves to the next available unsolved Puzzle
    again = client.post(events, json=_use_on(IX["key"], IX["rug"])).json()  # resolves to no available Puzzle now
    assert again["wrong_attempts"] == opened["wrong_attempts"] and again["locks_open"] == opened["locks_open"]
    with_puzzle = _use_on(IX["key"], IX["chest"])
    with_puzzle["input"]["puzzle_id"] = PZ["key_on_chest"]
    assert client.post(events, json=with_puzzle).status_code == 422  # a use_on never names its Puzzle
