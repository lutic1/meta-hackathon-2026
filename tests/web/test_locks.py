"""FR-12, UX-DR34, UX-DR38, UX-DR23, UX-DR65: the Code field, the find lock in the Scene, and the Checking, Not this
and Open feedback.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The API checks post the inputs
the Play screen posts against the four-lock fixture room.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX, PZ
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_contrast import PROPS, _hex, _over, contrast
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


def test_the_lock_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["codeFor"].format(n=2) == "Code for Puzzle 2"
    assert strings["checking"] == "Checking" and strings["submit"] == "Submit"
    assert strings["notThis"].format(n=3) == "Not this · 3" and strings["solved"] == "Solved"
    assert strings["inHand"].format(label="brass key") == "brass key · in hand"
    assert strings["found"].format(label="floor vent") == "floor vent · found"


def test_a_code_riddle_holds_the_code_field_on_its_note():
    note = _ts("components/riddle-note.ts")
    assert "puzzle.lock_type === 'code' ? codeField(puzzle, place, play) : orderProgress(puzzle, play)" in note
    assert "lock.replaceChildren(...(lockInput === null ? [] : [lockInput.element]))" in note
    assert "inputs.get(puzzle.id)?.update(state)" in note  # kept across redraws, so a typed code survives
    assert "riddleNote(view, play)" in _ts("play.ts")


def test_the_code_field_is_a_168_by_44_parchment_shade_inset_in_mono_code_with_no_visible_label():
    field = _ts("components/code-field.ts")
    assert "import './code-field.css'" in field
    assert "field.className = 'code-field mono-code'" in field and "field.type = 'text'" in field
    assert "export const CODE_MAX = 6" in field and "field.maxLength = CODE_MAX" in field
    assert "field.setAttribute('aria-label', fill(strings.codeFor, { n }))" in field
    assert "placeholder" not in _code(field) and "<label" not in field and "createElement('label')" not in field
    rule = _rules("components/code-field.css")[".code-field"]
    assert (rule["width"], rule["height"], rule["box-sizing"]) == ("168px", "44px", "border-box")
    assert rule["background"] == "var(--parchment-shade)" and rule["color"] == "var(--ink)"
    assert rule["border-radius"] == "var(--rounded-sm)" and rule["border"] == "1px solid transparent"
    token = design_text().split("  code-field:\n", 1)[1].split("\n  order-progress:", 1)[0]
    assert "width: 168px" in token and "height: 44px" in token and "typography: '{typography.mono-code}'" in token
    mono = _rules("tokens.css")[".mono-code"]
    assert mono["font-family"] == "var(--font-mono)" and mono["font-size"] == "20px" and mono["letter-spacing"] == "0.2em"


def test_submit_is_secondary_on_the_riddle_notes_parchment_and_disabled_below_3_characters():
    field = _ts("components/code-field.ts")
    assert "secondaryButton({ label: strings.submit, onParchment: true, onActivate: () => void submit() })" in field
    assert "export const CODE_MIN = 3" in field and "button.disabled = true" in field
    assert "button.disabled = field.value.length < CODE_MIN" in field
    assert "if (pending || code.length < CODE_MIN) return" in _body(field, "async function submit(")


def test_enter_or_submit_posts_exactly_one_code_lock_input_and_the_client_never_compares():
    field = _ts("components/code-field.ts")
    keydown = field.split("field.addEventListener('keydown', (event) => {", 1)[1].split("})", 1)[0]
    assert "if (event.key !== 'Enter') return" in keydown and "void submit()" in keydown
    submit = _body(field, "async function submit(")
    assert submit.index("pending = true") < submit.index("await play.post(")
    assert "play.post({ type: 'lock_input', input: { type: 'code', puzzle_id: puzzle.id, code } })" in submit
    assert field.count("play.post(") == 1 and "postEvent(" not in field
    # The code goes out as typed: no trim, no case change, no solution to compare it with (A-20 is the server's).
    code = _code(field)
    assert "solution" not in code and ".trim()" not in code and "toLowerCase" not in code and "toUpperCase" not in code
    assert "t_ms" not in code


def test_while_pending_the_field_is_read_only_and_the_checking_chip_shows_unannounced():
    field = _ts("components/code-field.ts")
    submit = _body(field, "async function submit(")
    assert "field.readOnly = true" in submit and "showChip('pending', `${strings.checking}\u2026`)" in submit
    assert submit.index("field.readOnly = true") < submit.index("await play.post(")
    assert "field.readOnly = false" in submit.split("finally {", 1)[1]
    assert "if (!pending) verdict(state)" in field  # a poll never clears Checking before the verdict
    for name in ("components/code-field.ts", "components/riddle-note.ts"):
        assert "aria-live" not in _ts(name) and "role', 'status'" not in _ts(name)
    rules = _rules("components/chip.css")
    assert rules[".chip-pending"] == {"border": "1px dashed var(--pending)", "color": "var(--pending)"}
    # On the Riddle note's parchment the chips take their ink forms.
    assert rules[".riddle-note .chip-pending"] == {"border-color": "var(--pending-ink)", "color": "var(--pending-ink)"}
    # The ellipsis is a character, never an animation: nothing loops.
    assert "setInterval" not in field and "requestAnimationFrame" not in field


def test_a_wrong_code_shows_the_servers_count_keeps_the_value_and_selects_it_for_retyping():
    field = _ts("components/code-field.ts")
    verdict = _body(field, "function verdict(")
    assert "const attempts = state.wrong_attempts[puzzle.id] ?? 0" in verdict
    assert "if (attempts > since) showChip('not-this', fill(strings.notThis, { n: attempts }))" in verdict
    submit = _body(field, "async function submit(")
    assert "since = play.state().wrong_attempts[puzzle.id] ?? 0" in submit
    assert "field.focus()" in submit and "field.select()" in submit
    assert "field.value = " not in field  # the value is never cleared or rewritten
    assert "field.setAttribute('aria-describedby', chip.id)" in field  # the chip is the field's description
    rules = _rules("components/code-field.css")
    selected = rules[".code-field.is-selected"]
    assert selected["border-color"] == "var(--lamp-ink)" and "var(--lamp-ink-hover-fill)" in selected["background"]
    token = design_text().split("  code-field:\n", 1)[1].split("\n  order-progress:", 1)[0]
    assert "selectedFill: '{colors.lamp-ink-hover-fill}'" in token and "selectedEdge: '1px solid {colors.lamp-ink}'" in token
    # No shake and no sound: the stylesheet moves nothing (the suite-wide motion and sound bans cover the rest).
    assert "transition" not in (WEB_SRC / "components/code-field.css").read_text()


def test_an_input_that_changes_nothing_only_clears_the_checking_chip():
    field = _ts("components/code-field.ts")
    verdict = _body(field, "function verdict(")
    assert "else showChip(null)" in verdict
    # Selection for retyping follows only a shown Not this chip.
    assert "if (!chip.hidden && field.isConnected) {" in _body(field, "async function submit(")


def test_an_open_lock_is_stamped_on_the_note_which_holds_it_until_the_player_sets_off():
    # Story mode: the Wizard notes' 1200 ms hold and collapse are gone; the note holds the solved riddle with its
    # stamp until "Take me there" (tests/web/test_story_play.py), and focus then moves to its heading.
    note = _ts("components/riddle-note.ts")
    assert "if (opened) held = true" in note and "stamp.hidden = !open" in note
    assert "heading.tabIndex = -1" in note
    assert "OPEN_HOLD_MS" not in _code(_ts("play.ts")) and not (WEB_SRC / "components/wizard-notes.ts").exists()
    fade = _ts("fade.ts")
    assert "element.classList.add('is-arriving')" in fade and "element.classList.remove('is-arriving')" in fade


def test_a_find_click_posts_only_the_click_and_the_collected_target_fades_into_the_inventory():
    scene, layer = _ts("scene/index.ts"), _ts("scene/hotspots.ts")
    assert "const click: PostedEvent = { type: 'click', interactable_id: interactable.id }" in scene
    assert "play.post(click)" in scene
    assert scene.count("play.post(") == 2  # the click, and a `use_on` (Story 1.26), never both for one activation
    assert "layer?.setCollected(state.inventory, foundTargets(play.id))" in scene
    assert "layer.setCollected(play.state().inventory, foundTargets(play.id))" in scene
    assert "onState: (render) => {\n      parts.push(render)" in _ts("play.ts")
    assert "hotspot.classList.toggle('is-collected', inventory.includes(id) || foundIds.includes(id))" in layer
    rules = _rules("scene/scene.css")
    assert rules[".hotspot-glow"]["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".hotspot.is-collected .hotspot-glow"] == {"opacity": "0"}
    css = (WEB_SRC / "scene/scene.css").read_text()
    assert css.index(".hotspot:hover .hotspot-glow") < css.index(".hotspot.is-collected .hotspot-glow")
    inventory = _ts("components/inventory.ts")
    assert "if (before !== undefined && !before.has(interactable.id)) arrived.push(button)" in inventory
    assert "for (const item of arrived) {\n      fadeIn(item)" in inventory
    slots = _rules("components/inventory.css")
    assert slots[".inventory-slot"]["transition"].startswith("opacity var(--motion-state) var(--motion-ease)")
    assert slots[".inventory-slot.is-arriving"] == {"opacity": "0"}
    assert "--motion-state: 200ms;" in (WEB_SRC / "tokens.css").read_text()


def test_a_later_click_on_a_collected_hotspot_shows_label_in_hand():
    layer = _ts("scene/hotspots.ts")
    show = _body(layer, "function showLabel(")
    assert "const held = collected.includes(interactable.id)" in show
    assert "fill(strings.inHand, { label: interactable.label })" in show


def test_a_found_target_no_use_on_needs_settles_like_a_collected_one_and_answers_found():
    # Owner decision Oct 29: a click that opened a find lock and carried nothing records its target as found in the
    # page, so its Hotspot's glow settles and a later click reads "{label} · found" on the chip and the feedback line.
    scene, layer = _ts("scene/index.ts"), _ts("scene/hotspots.ts")
    activate = _body(scene, "async function activate(")
    assert "const before = play.state()" in activate
    assert "const target = room === undefined ? null : foundBy(room, click, before, reply)" in activate
    assert "found.keep(play.id, target)" in activate
    assert "layer?.setCollected(reply.inventory, foundTargets(play.id))" in activate
    show = _body(layer, "function showLabel(")
    assert "foundIds.includes(interactable.id) ? fill(strings.found, { label: interactable.label })" in show
    # The Completion filmstrip still lights a target never carried: it reads the bloomed targets beside the Inventory.
    assert "new Set([...session.inventory, ...solvedTargets(session.id)])" in _ts("completion.ts")


def test_found_and_solved_targets_outlive_a_reload_of_the_tab():
    # A reload keeps a found target found ("{label} · found", its glow settled) and keeps every bloomed target lit on
    # the Completion filmstrip: both lists live in sessionStorage per session id, in memory when storage refuses.
    scene = _ts("scene/index.ts")
    assert "const solved = tabTargets('keyframe-solved:')" in scene
    assert "const found = tabTargets('keyframe-found:')" in scene
    targets = _body(scene, "function targets(")
    assert "sessionStorage.getItem(prefix + sessionId)" in targets and "} catch {" in targets
    keep = _body(scene, "function keep(")
    assert "sessionStorage.setItem(prefix + sessionId, JSON.stringify(next))" in keep and "} catch {" in keep
    assert "memory.set(sessionId, next)" in keep
    assert "solved.keep(play.id, target)" in _body(scene, "function bloom(")
    assert "localStorage" not in scene


def test_every_lock_color_pair_is_in_the_contrast_table_and_passes():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    # The Code field keeps its parchment-shade inset; Submit and the chips sit on the dark notes tray (Oct 29).
    pairs = {("ink", "parchment-shade"), ("lamp", "chrome-raised"), ("text-muted", "chrome-raised"),
             ("wrong", "chrome-raised"), ("success", "chrome-raised"), ("focus-ring", "chrome")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
        assert contrast(_hex(PROPS[fg])[0], _hex(PROPS[bg])[0]) >= 4.5, f"{fg} on {bg}"
    tinted = _over("lamp-ink-hover-fill", _hex(PROPS["parchment-shade"])[0])
    assert contrast(_hex(PROPS["ink"])[0], tinted) >= 4.5  # the value selected for retyping
    assert contrast(_hex(PROPS["lamp-ink"])[0], tinted) >= 3  # its 1 px edge (non-text)


def test_codes_are_judged_by_the_server_and_its_count_is_what_the_chip_shows(client: TestClient, four_lock_room: Room):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    code = {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["clock_code"], "code": "000"}}
    wrong = client.post(events, json=code).json()
    assert wrong["wrong_attempts"][PZ["clock_code"]] == 1 and PZ["clock_code"] not in wrong["locks_open"]
    assert wrong["active_puzzle_id"] == PZ["clock_code"]
    right = client.post(events, json={**code, "input": {**code["input"], "code": " 415 "}}).json()
    assert PZ["clock_code"] in right["locks_open"] and right["wrong_attempts"][PZ["clock_code"]] == 1


def test_an_input_for_a_puzzle_whose_prerequisites_are_not_open_returns_the_state_unchanged(
    client: TestClient, four_lock_room: Room
):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    door = {"type": "lock_input", "input": {"type": "code", "puzzle_id": PZ["door_code"], "code": "7342"}}
    reply = client.post(events, json=door)
    assert reply.status_code == 200
    state = reply.json()
    for key in ("locks_open", "inventory", "wrong_attempts", "active_puzzle_id"):
        assert state[key] == session[key], key


def test_a_find_click_opens_the_lock_and_a_later_click_on_its_target_changes_nothing(client: TestClient, four_lock_room: Room):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    first = client.post(events, json={"type": "click", "interactable_id": IX["key"]}).json()
    assert first["locks_open"] == [PZ["find_key"]] and first["inventory"] == [IX["key"]]  # the chest needs the key
    again = client.post(events, json={"type": "click", "interactable_id": IX["key"]}).json()
    assert again["locks_open"] == first["locks_open"] and again["inventory"] == first["inventory"]
    assert again["wrong_attempts"] == first["wrong_attempts"]  # a click is never a Wrong attempt
