"""Story mode, one riddle at a time (owner decision Oct 29; build spec sections 1.3, 1.4, 1.10, 3.3 to 3.6): which
riddle the note shows and its number, the seals, the place tag, the Riddler's solved line and the where-line for the
next riddle, the chest's counts and the closing lines, all from served data alone.

riddles.ts is pure (it imports only strings.ts and walk.ts), so Node 24 runs the shipped module as it is.
"""

import json
import shutil
import subprocess

import pytest

from tests.web.design import REPO, WEB_SRC

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's riddle lines")

RUNNER = """
import { readFileSync } from 'node:fs'
const riddles = await import(process.argv[1])
const calls = JSON.parse(readFileSync(0, 'utf8'))
process.stdout.write(JSON.stringify(calls.map(([name, ...args]) => riddles[name](...args) ?? null)))
"""


def _run(*calls: list) -> list:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", RUNNER, (WEB_SRC / "riddles.ts").as_uri()],
        cwd=REPO, input=json.dumps(calls), capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _photo(area: str, pan: int | None) -> dict:
    return {"hash": "h", "size": 1, "area": area, "pan": pan}


def _puzzle(id: str, lock_type: str, start: int, requires: list[str] | None = None, exit: bool = False) -> dict:
    return {"id": id, "lock_type": lock_type, "requires": requires or [], "is_exit": exit, "clue": "c", "lore": "l",
            "evidence_cards": [], "sequence_length": None, "start_photo": start}


# The Demo room as the spec seeds it (section 7): pillows on photo 2, the vent on photo 0, the pillows on the sofa on
# photo 5, the double front door on photo 1; front hall [0, 1], lounge [3, 4, 5, 2, 6, 7].
PHOTOS = [_photo("front hall", 0), _photo("front hall", 1), _photo("lounge", 3), _photo("lounge", 0),
          _photo("lounge", 1), _photo("lounge", 2), _photo("lounge", 4), _photo("lounge", 5)]
PUZZLES = [_puzzle("pillows", "find", 2), _puzzle("vent", "find", 0), _puzzle("sofa", "use_on", 5, ["pillows"]),
           _puzzle("door", "find", 1, ["pillows", "vent", "sofa"], exit=True)]
DEMO = {"id": "room", "name": "The front hall and the lounge", "photos": PHOTOS, "interactables": [],
        "puzzles": PUZZLES, "story": None}
STORY = {
    "architect_welcome": "a", "trickster_trap": "t", "riddler_entrance": "r", "guide_chest": "g",
    "riddles": [{"puzzle_id": id, "opening": "Open.", "solved": f"{id} is done."} for id in ("pillows", "vent", "sofa", "door")],
    "trickster_closing": "Out, then.", "riddler_closing": "Until next time.",
    "guide_closing_no_hints": "No hints at all.", "guide_closing_hints": "A hint or two.",
}
TOLD = {**DEMO, "story": STORY}


@needs_node
def test_the_riddle_number_is_the_place_among_the_available_puzzles_and_n_is_every_puzzle():
    calls = [
        ["riddleNumber", PUZZLES, [], "pillows"], ["riddleNumber", PUZZLES, ["pillows"], "vent"],
        ["riddleNumber", PUZZLES, ["pillows", "vent"], "sofa"], ["riddleNumber", PUZZLES, ["pillows", "vent", "sofa"], "door"],
        ["riddleNumber", PUZZLES, [], "sofa"],  # not available yet: no number
        ["riddleHeading", PUZZLES, ["pillows"], "vent"], ["riddleHeading", PUZZLES, ["pillows", "vent", "sofa"], "door"],
    ]
    assert _run(*calls) == [1, 2, 3, 4, 0, "Riddle 2 of 4", "The way out · riddle 4 of 4"]


@needs_node
def test_the_seals_mark_each_riddle_by_its_number_solved_current_or_waiting():
    calls = [["seals", PUZZLES, [], "pillows"], ["seals", PUZZLES, ["pillows"], "vent"],
             # The vent found first, out of turn: its seal is 2 and riddle 1 is still current.
             ["seals", PUZZLES, ["vent"], "pillows"], ["seals", PUZZLES, ["pillows", "vent", "sofa", "door"], None]]
    assert _run(*calls) == [
        ["current", "waiting", "waiting", "waiting"], ["solved", "current", "waiting", "waiting"],
        ["current", "solved", "waiting", "waiting"], ["solved", "solved", "solved", "solved"],
    ]


@needs_node
def test_the_place_tag_names_the_area_of_the_riddles_start_photo():
    old = {**DEMO, "photos": [_photo("room", None) for _ in PHOTOS]}
    assert _run(["placeTag", DEMO, "pillows"], ["placeTag", DEMO, "vent"], ["placeTag", old, "door"]) == [
        "Waits in the lounge", "Waits in the front hall", "Waits in the room"]


@needs_node
def test_the_solve_line_is_the_reaction_then_the_where_line_and_the_exit_reacts_alone():
    # The Demo run (spec 3.4): solved in the lounge, then the front hall, then the lounge, then the front hall.
    calls = [
        ["solveLine", DEMO, "pillows", "vent", 2, ["pillows"], True, True],
        ["solveLine", DEMO, "vent", "sofa", 0, ["pillows", "vent"], False, True],
        ["solveLine", DEMO, "sofa", "door", 5, ["pillows", "vent", "sofa"], False, False],
        ["solveLine", DEMO, "door", None, 1, ["pillows", "vent", "sofa", "door"], False, False],
    ]
    assert _run(*calls) == [
        "Well found. Keep hold of that; this house isn't finished with it. The next riddle waits in the front hall.",
        "Well found. The house noticed you noticing. Back to the lounge for the next one. Bring what you're carrying.",
        "The right thing in the right place. The house approves. One riddle left, the way out. It waits in the front hall.",
        "Every riddle, every answer. The way out is yours.",
    ]


@needs_node
def test_the_where_line_says_right_here_back_or_next_and_a_use_on_with_nothing_carried_brings_nothing():
    calls = [
        ["whereLine", DEMO, "sofa", 4, ["pillows", "vent"], False],  # standing in the lounge already
        ["whereLine", DEMO, "vent", 3, ["pillows"], True],  # never in the front hall yet
        ["whereLine", DEMO, "sofa", 0, ["pillows", "vent"], False],  # back where riddle 1 was, carrying nothing
        ["whereLine", DEMO, "door", 4, ["pillows", "vent", "sofa"], False],
        ["firstWhereLine", DEMO, "pillows"],
    ]
    assert _run(*calls) == [
        "The next riddle waits right here in the lounge.", "The next riddle waits in the front hall.",
        "Back to the lounge for the next one.", "One riddle left, the way out. It waits in the front hall.",
        "Start in the lounge.",
    ]


@needs_node
def test_every_lock_type_has_its_reaction_and_the_story_line_wins_when_the_room_has_one():
    code, order = _puzzle("dial", "code", 0), _puzzle("steps", "order", 0)
    room = {**DEMO, "puzzles": [*PUZZLES[:3], code, order, PUZZLES[3]]}
    calls = [["reaction", room, "dial", False], ["reaction", room, "steps", False], ["reaction", room, "door", False],
             ["reaction", TOLD, "pillows", True], ["solveLine", TOLD, "vent", "sofa", 0, ["pillows", "vent"], False, False]]
    assert _run(*calls) == [
        "The numbers agree with you. They rarely agree with anyone.", "In order at last. Someone here will be thrilled.",
        "Every riddle, every answer. The way out is yours.", "pillows is done.",
        "vent is done. Back to the lounge for the next one.",
    ]


@needs_node
def test_the_chest_counts_its_gems_from_hints_left_and_names_the_riddle_it_spends_on():
    calls = [["chestCount", 2], ["chestCount", 1], ["chestCount", 0],
             ["chestName", 2], ["chestName", 1], ["chestName", 0],
             ["spendLine", 2, 1], ["spendLine", 1, 3]]
    assert _run(*calls) == [
        "2 hints for the whole house", "1 hint for the whole house", "Empty",
        "Treasure chest: 2 hints left", "Treasure chest: 1 hint left", "Treasure chest: empty",
        "Spend 1 of your 2 hints on riddle 1. There are only 2 for the whole house.",
        "Spend 1 of your 1 hint on riddle 3. There are only 2 for the whole house.",
    ]


@needs_node
def test_a_bought_hint_is_labelled_and_announced_by_its_rung():
    calls = [["hintLabel", 1], ["hintLabel", 2], ["hintAnnouncement", 1, "Search down low."],
             ["hintAnnouncement", 2, "Notice the slats."]]
    assert _run(*calls) == ["The Guide's hint · Nudge", "The Guide's hint · Direction",
                            "The Guide's hint, nudge: Search down low.", "The Guide's hint, direction: Notice the slats."]


@needs_node
def test_the_closing_lines_come_from_the_story_or_the_templates_and_the_guide_follows_the_hints_spent():
    calls = [["closingLines", DEMO, 0], ["closingLines", DEMO, 2], ["closingLines", TOLD, 0], ["closingLines", TOLD, 1],
             ["escapedSubline", DEMO], ["escapedSubline", {**DEMO, "name": None}]]
    assert _run(*calls) == [
        {"trickster": "Fine. Out you go. I'll lock it again for the next guest.",
         "riddler": "Clever mind. I'll write harder ones next time.", "guide": "Not a single hint. I'm almost offended."},
        {"trickster": "Fine. Out you go. I'll lock it again for the next guest.",
         "riddler": "Clever mind. I'll write harder ones next time.", "guide": "You let me help a little. I enjoyed every word."},
        {"trickster": "Out, then.", "riddler": "Until next time.", "guide": "No hints at all."},
        {"trickster": "Out, then.", "riddler": "Until next time.", "guide": "A hint or two."},
        "The front hall and the lounge · every riddle answered, the door open",
        "Your room · every riddle answered, the door open",
    ]


def test_the_module_stays_pure_so_node_runs_it_as_it_ships():
    source = (WEB_SRC / "riddles.ts").read_text()
    imports = [line for line in source.splitlines() if line.startswith("import ")]
    assert all("import type" in line or "./strings.ts'" in line or "./walk.ts'" in line for line in imports), imports
    assert "document" not in source and "window" not in source
