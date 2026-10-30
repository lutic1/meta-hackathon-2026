"""Story mode on the Play screen (owner decision Oct 29; build spec 1.3, 1.4, 1.7 to 1.10, 3.2 to 3.6 and 6): one
riddle at a time on the Riddle note, the two-hint Treasure chest, the coach pill, "Your pack", the solve beat with
"Take me there", the way out and the closing sheet. The lines themselves are pure and run in Node
(tests/web/test_riddles.py); the server's chest rules are tests/api/test_chest_hints.py. These checks read the
TypeScript and the stylesheets (the client has no test runner) and post the client's own bodies to the app; the browser
run proves the rest.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import _section, _strings

STORY_CSS = ("components/riddle-note.css", "components/treasure-chest.css", "components/story-stage.css")


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n  }\n", 1)[0]


# --- The Riddle note -------------------------------------------------------------------------------------------------


def test_the_note_draws_one_riddle_the_active_one_unless_it_holds_a_solved_one():
    note = _ts("components/riddle-note.ts")
    draw = _function(note, "draw")
    assert "const id = held ? shown : (state.active_puzzle_id ?? shown)" in draw
    assert "heading.textContent = riddleHeading(room.puzzles, state.locks_open, puzzle.id)" in draw
    assert "seals(room.puzzles, state.locks_open, held ? puzzle.id : state.active_puzzle_id)" in draw
    assert "place.append(placeTag(room, puzzle.id))" in draw
    # Only that riddle's bought hints; a code or order riddle's lock input; the stamp once its lock is open.
    assert "state.rung_changes.filter((change) => change.puzzle_id === puzzle.id)" in draw
    assert "if (puzzle.lock_type !== 'code' && puzzle.lock_type !== 'order') return null" in note
    assert "stamp.replaceChildren(seal, strings.solved)" in draw
    # No evidence, no list of other riddles: nothing else is drawn.
    code = _code(note)
    assert "evidence" not in code and "availableInRoomOrder(" not in code
    assert not (WEB_SRC / "components/wizard-notes.ts").exists()


def test_the_note_holds_a_riddle_as_it_opens_and_shows_the_next_when_the_player_sets_off():
    note = _ts("components/riddle-note.ts")
    render = _function(note, "render")
    assert "const opened = shown !== null && state.locks_open.includes(shown) && !latest.locks_open.includes(shown)" in render
    assert "if (opened) held = true" in render and "classList.add('is-stamping')" in render
    release = note.split("release: () => {", 1)[1].split("\n    },", 1)[0]
    assert "held = false" in release and "draw(latest)" in release
    solve = _function(_ts("play.ts"), "solveBeat")
    assert solve.index("note.release()") < solve.index("await scene.walkTo(target.start_photo)") < solve.index("note.focus()")


def test_the_note_is_a_section_named_by_its_heading_with_the_lore_folded_away():
    note = _ts("components/riddle-note.ts")
    assert "element.setAttribute('aria-labelledby', 'riddle-note-heading')" in note
    assert "heading.id = 'riddle-note-heading'" in note and "heading.tabIndex = -1" in note
    assert "toggle.textContent = strings.riddlersAside" in note and "toggle.setAttribute('aria-expanded', 'false')" in note
    assert "lore.hidden = true" in note and "lore.hidden = !open" in note
    assert "wizardPortrait('riddler', 40)" in note and "wizardPortrait('guide', 26)" in note
    assert "paragraph('riddle-hint-label label', hintLabel(line.rung))" in note
    assert "focus: () => heading.focus({ preventScroll: true })" in note


def test_the_note_is_pinned_top_left_on_the_wall_and_scrolls_inside_itself():
    note = _rules("components/riddle-note.css")[".riddle-note"]
    assert (note["position"], note["top"], note["left"]) == ("absolute", "18px", "20px")
    assert note["width"] == "clamp(300px, calc((100% - var(--wall-width, 0px)) / 2 - 40px), 400px)"
    assert note["max-height"] == "calc(58vh - 44px)" and note["overflow-y"] == "auto"
    assert note["background"] == "var(--parchment)" and note["color"] == "var(--ink)"
    scene = _ts("scene/index.ts")
    assert "frame.style.setProperty('--wall-width', `${fitted.width}px`)" in scene


# --- The Treasure chest ----------------------------------------------------------------------------------------------


def test_the_chest_counts_its_gems_from_hints_left_never_from_a_client_count():
    chest = _ts("components/treasure-chest.ts")
    draw = _function(chest, "draw")
    assert "const left = state.hints_left" in draw
    assert "gemList.forEach((gem, k) => gem.classList.toggle('is-spent', k >= left))" in draw
    assert "chest.setAttribute('aria-label', chestName(left))" in draw and "count.textContent = chestCount(left)" in draw
    assert "hints_left" in _ts("../types/index.ts")


def test_the_chest_dialog_takes_and_traps_focus_and_escape_gives_it_back_to_the_chest():
    chest = _ts("components/treasure-chest.ts")
    assert "dialog.setAttribute('role', 'dialog')" in chest and "dialog.setAttribute('aria-modal', 'true')" in chest
    assert "dialog.setAttribute('aria-labelledby', 'chest-dialog-heading')" in chest
    assert "buttons[0]?.focus({ preventScroll: true })" in _function(chest, "open")
    keys = chest.split("dialog.addEventListener('keydown', (event) => {", 1)[1].split("\n  })", 1)[0]
    assert "event.stopPropagation() // a held item stays in hand" in keys and "close()" in keys
    assert "buttons[(at + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length]?.focus()" in keys
    assert "chest.focus({ preventScroll: true })" in _function(chest, "close")
    # The arrow keys walk nowhere from inside a dialog.
    assert "target.closest('[role=\"dialog\"]') !== null) return false" in _ts("scene/index.ts")


def test_open_it_posts_one_hint_request_and_the_reply_lands_on_the_note():
    chest = _ts("components/treasure-chest.ts")
    spend = _function(chest, "spendOne")
    assert _code(chest).count(".post(") == 1 and "play.post({ type: 'hint_request' })" in spend  # AD-4: no puzzle_id
    assert spend.index("await fly(gem)") < spend.index("note.hintArrived()") < spend.index("announce(hintAnnouncement(reply.rung, reply.text))")
    assert "if (reply !== null) onNoHint(reply.text)" in spend  # the No-hint line spends nothing
    assert "if (error instanceof RequestFailed && error.code === 'hint_cap_reached') openEmpty()" in spend
    assert "if (reduced()) return" in _function(chest, "fly")
    assert "export const GEM_FLIGHT_MS = 650" in chest
    empty = _function(chest, "openEmpty")
    assert "strings.chestEmptyLine" in empty and "open(strings.chestIsEmpty, [line], [dialogButton(strings.backToTheRoom" in empty


def test_the_tricksters_bubble_says_the_chest_line_once_and_each_new_card():
    chest = _ts("components/treasure-chest.ts")
    assert "export const BUBBLE_MS = 7000" in chest
    render = _function(chest, "render")
    assert "const arrived = state.cards.slice(cardsHeard)" in render and "bubble(text.sentence, false)" in render
    assert "cardAnnouncement(cardText(room, card), first && k === 0)" in render
    assert "let cardsHeard = latest.cards.length" in chest  # a reload shows no Card again
    play = _ts("play.ts")
    start = play.split("async function begin(): Promise<void> {", 1)[1].split("\n      }\n", 1)[0]
    assert "note.focus()" in start and "if (latest.locks_open.length > 0) return" in start
    assert "scene.coach(true)" in start and "chest.bubble(strings.chestBubble)" in start


def test_a_chest_hint_is_asked_with_the_clients_body_and_the_cap_is_the_servers(tmp_path: Path, four_lock_room: Room):
    client = TestClient(make_app(tmp_path, four_lock_room))
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    assert session["hints_left"] == 2
    events = f"/api/sessions/{session['id']}/events"
    first = client.post(events, json={"type": "hint_request"}).json()
    assert (first["hints_left"], first["hint_reply"]["rung"], first["hint_reply"]["hints_left"]) == (1, 1, 1)
    assert first["rung_changes"][-1]["puzzle_id"] == first["active_puzzle_id"]  # the hint the note pins
    assert client.post(events, json={"type": "hint_request"}).json()["hints_left"] == 0
    refused = client.post(events, json={"type": "hint_request"})
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "hint_cap_reached"
    # The note shows no evidence before a lock opens: the session's room serves none.
    room = client.get(f"/api/sessions/{session['id']}/room").json()
    assert all(puzzle["evidence_cards"] == [] for puzzle in room["puzzles"])


# --- The coach pill, the feedback line and "Your pack" ---------------------------------------------------------------


def test_the_coach_pill_shares_the_feedback_lines_slot_and_steps_aside():
    line = _ts("components/feedback-line.ts")
    assert "export const COACH_MS = 15000" in line and "coachPill.textContent" not in line
    coach = _function(line, "coach")
    assert "coachPill.hidden = !on" in coach and "if (on) coaching = setTimeout(() => coach(false), COACH_MS)" in coach
    rules = _rules("components/feedback-line.css")
    assert rules[".feedback-line.is-shown ~ .coach-pill"] == {"opacity": "0"}
    assert rules[".feedback-line"]["bottom"] == "22px" and "wizardPortrait('guide', 30)" in line
    play = _ts("play.ts")
    assert "if (body.type === 'click') scene.coach(false)" in play  # the first Hotspot click
    assert "treasureChest(view, play, note, () => scene.coach(false), speak)" in play  # opening the chest


def test_your_pack_stands_on_the_floor_left_of_the_photo_and_says_what_to_do():
    pack = _ts("components/inventory.ts")
    assert "name.textContent = strings.yourPack" in pack
    assert "crop(room.id, interactable, ITEM_WIDTH, ITEM_HEIGHT)" in pack and "const ITEM_WIDTH = 76" in pack
    describe = _function(pack, "describe")
    assert "strings.packEmptyAgain : strings.packEmpty" in describe and "strings.packHold : strings.packInHand" in describe
    change = pack.split("selection.onChange((item, cause) => {", 1)[1].split("\n  })", 1)[0]
    assert "say(fill(strings.inHandWhere, { Label: capitalized(label(item)) }))" in change
    assert "say(fill(strings.putAway, { label: label(was) }))" in change and "say(strings.handsEmpty)" in change
    # A crop is cut around the largest polygon, so the two-polygon pillows read as one object.
    assert "const polygon = largest(interactable.polygons ?? []) ?? []" in _ts("components/crop.ts")


def test_the_pack_and_the_chest_stand_by_the_photo_but_never_leave_the_frame():
    # 22 px beside the photo and 26 px up, but a landscape photo nearly as wide as the frame leaves a side margin
    # narrower than either part: the pack then starts 16 px inside the frame's left edge (`safe` alignment) and the
    # chest ends 16 px inside its right edge, each over the photo's lower corner, so the page never scrolls sideways.
    pack = _rules("components/inventory.css")
    floor = pack[".inventory"]
    assert floor["right"] == "calc(50% + var(--wall-width, 0px) / 2 + 22px)" and floor["bottom"] == "26px"
    assert floor["left"] == "16px" and floor["grid-template-columns"] == "max-content"
    assert floor["justify-content"] == "safe end" and floor["justify-items"] == "end"
    assert "width" not in floor  # the box spans the margin; its column takes what it needs
    assert floor["pointer-events"] == "none" and pack[".inventory > *"]["pointer-events"] == "auto"
    rules = _rules("components/treasure-chest.css")
    chest = rules[".treasure-chest"]
    edge = "calc(50% + var(--wall-width, 0px) / 2 + 22px)"
    assert chest["left"] == f"min({edge}, calc(100% - var(--chest-width) - 16px))" and chest["bottom"] == "26px"
    assert chest["right"] == "16px" and chest["container-type"] == "inline-size"
    assert chest["--chest-width"] == "168px"  # the chest over "2 hints for the whole house", the widest label
    assert chest["pointer-events"] == "none" and rules[".treasure-chest > :not(.chest-bubble)"]["pointer-events"] == "auto"
    # The bubble (250 px) and the dialog (340 px) overhang the box; they slide left by what would overflow it, and
    # the bubble's tail stays over the chest.
    assert rules[".chest-bubble"]["width"] == "250px" and rules[".chest-dialog"]["width"] == "340px"
    assert rules[".chest-bubble"]["left"] == "min(-10px, calc(100cqw - 250px))"
    assert rules[".chest-dialog"]["left"] == "min(0px, calc(100cqw - 340px))"
    assert rules[".chest-bubble::after"]["left"] == "max(40px, calc(280px - 100cqw))"


def test_the_parts_hang_in_the_frame_in_the_tab_order_and_the_side_column_is_gone():
    scene = _ts("scene/index.ts")
    assert "frame.append(slots.note, ground, feedback.element, feedback.coachPill, turns.left, turns.right, slots.floor)" in scene
    play = _ts("play.ts")
    assert "scene.slots.note.append(note.element)" in play and "scene.slots.floor.append(held.element, chest.element)" in play
    assert _rules("shell.css")[".side-column"] == {"display": "none"}
    assert _rules("shell.css")[".play-layout"]["grid-template-columns"] == "minmax(0, 1fr)"


# --- The solve beat, the way out and the closing sheet ---------------------------------------------------------------


def test_the_solve_beat_is_the_riddler_on_the_light_stage_with_take_me_there():
    solve = _function(_ts("play.ts"), "solveBeat")
    assert "speaker: 'riddler'" in solve and "role: strings.roleRiddler" in solve
    assert "solveLine(shown, puzzle.id, next, scene.current(), after.locks_open, item !== undefined, latest.inventory.length > 0)" in solve
    assert "button: puzzle.is_exit ? strings.stepOutside : strings.takeMeThere" in solve
    assert "solved: riddleNumber(shown.puzzles, after.locks_open, puzzle.id)" in solve
    assert solve.index("beating = true") < solve.index("await beats.play(")  # the Scene is inert under the beat
    stage = _ts("components/story-stage.ts")
    play = _function(stage, "play")
    assert "element.classList.toggle('is-light', beat.solved !== undefined)" in play
    assert "announce(`${NAMES[beat.speaker]}: ${beat.line}" in play and "next.focus({ preventScroll: true })" in play
    keys = _function(stage, "onKey")
    assert "if (event.key !== 'Enter' || !waiting || event.target === next || event.target === skip) return" in keys
    assert "typing" not in _code(stage)  # lines appear whole


def test_the_way_out_lights_the_door_and_the_closing_sheet_follows():
    play = _ts("play.ts")
    assert "export const EXIT_SHEET_DELAY_MS = 900" in play
    out = _function(play, "wayOut")
    assert "void scene.daylight(solvedTargets(session.id).at(-1) ?? null)" in out
    assert "leaveForDone(stateFadeMs() === 0 ? 0 : EXIT_SHEET_DELAY_MS)" in out and "exited.add(session.id)" in out
    behind = play.split("export function mountPlayBehind(", 1)[1]
    assert "void scene.daylight(solvedTargets(session.id).at(-1) ?? null, true)" in behind
    scene = _ts("scene/index.ts")
    assert "export const DAYLIGHT_MS = 1200" in scene and "export const EXIT_PUSH_MS = 1400" in scene
    assert "if (still || reduced()) return" in _function(scene, "daylight")
    rules = _rules("scene/walk.css")
    assert rules[".hotspot.is-daylight .hotspot-bloom"]["fill"] == "#FFF4DC"


def test_the_closing_sheet_docks_low_with_the_story_lines_the_four_stats_and_play_again():
    completion = _ts("completion.ts")
    assert "heading.textContent = strings.youEscaped" in completion
    assert "subline.textContent = escapedSubline(room)" in completion
    assert "const { trickster, riddler, guide } = closingLines(room, hintsSpent(session))" in completion
    assert "announce(`${strings.speakerGuide} ${guide}`)" in completion
    for stat in ("statRiddles", "statTime", "statChestHints", "statWrongTries"):
        assert f"stat(strings.{stat})" in completion, stat
    assert "label: strings.playAgain" in completion and "startSession(await sessionStart(session.room_id, profile, mode))" in completion
    assert "return Math.max(0, CHEST_HINTS - session.hints_left)" in completion
    assert "details.append(summary, filmstrip, times, wizards, actions, copied)" in completion
    sheet = _rules("completion.css")[".completion-sheet"]
    assert sheet["width"] == "min(860px, 100%)" and sheet["margin"] == "auto auto 0"
    assert _rules("completion.css")[".completion-scrim"]["padding"] == "var(--spacing-frame-margin) 20px 22px"


# --- Motion, strings and the contract --------------------------------------------------------------------------------


def test_every_story_motion_is_off_under_reduced_motion():
    for name in STORY_CSS:
        text = (WEB_SRC / name).read_text()
        reduced = text.split("@media (prefers-reduced-motion: reduce) {", 1)[1]
        for selector, rule in css_rules(text.split("@media (prefers-reduced-motion: reduce) {", 1)[0]).items():
            if "animation" in rule:
                assert selector in reduced and "animation: none" in reduced, (name, selector)
            if "transition" in rule and "transform" in rule["transition"]:
                assert selector in reduced, (name, selector)


def test_the_retired_strings_are_gone_and_the_new_lines_are_the_experience_lines():
    strings = _strings()
    for gone in ("getHint", "nextHintIn", "noHintsYet", "hintArea", "askTheGuide", "wizardNotes", "current",
                 "evidenceCards", "puzzleWaits", "puzzleAvailable", "lockSolved", "roomOpen", "statHints", "statWrong",
                 "rungNudge", "thresholdDerived", "moreInCardLog", "dismissCard", "guideThinking"):
        assert gone not in strings, gone
    assert strings["hintsExplained"] == ("The chest holds 2 hints for the whole game. Each one opens the next hint for "
                                         "the riddle you're on. Nothing opens on its own.")
    assert strings["coachPill"] == "Click things in the photo · Turn with ← → or the edges"
    assert strings["chestBubble"] == "2 hints, for the whole house. Spend them like they're mine."
    # No exclamation marks (EXPERIENCE.md), bar the Trickster's trap line in the intro (owner call).
    assert "!" not in "".join(value for key, value in strings.items() if key != "introTrap")


def test_the_contract_records_the_note_the_chest_the_beat_and_the_sheet():
    patterns = _section("Component Patterns")
    for row in ("| Riddle note (story mode", "| Treasure chest (story mode", "| Story stage: the solve beat",
                "| Coach pill (story mode", "| Your pack (story mode"):
        assert row in patterns, row
    for gone in ("| Wizard notes |", "| Hint area |", "| Rung line |", "| Hint button |"):
        assert gone not in patterns, gone
    design = design_text()
    for component in ("  riddle-note:\n", "  treasure-chest:\n", "  story-stage:\n", "  coach-pill:\n"):
        assert component in design, component
    for gone in ("  wizard-notes:\n", "  hint-area:\n", "  rung-line:\n"):
        assert gone not in design, gone
