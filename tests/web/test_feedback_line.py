"""The feedback line (owner decision, Oct 29): every reply to a posted input answers in one place, a parchment strip
over the bottom edge of the Scene frame with the Guide's 32 px portrait, held about 2.5 s and then faded, and written
once to the live region. The line is chosen by a pure module that Node runs as it ships; the rest is read from the
TypeScript and the stylesheets (the client has no test runner) and proved in the browser run.
"""

import json
import re
import shutil
import subprocess
from typing import Any

import pytest

from tests.web.design import REPO, WEB_SRC, css_rules, design_text
from tests.web.test_strings import _section, _strings

RUNNER = """
import { readFileSync } from 'node:fs'
const { feedbackFor, foundBy } = await import(process.argv[1])
const { room, cases } = JSON.parse(readFileSync(0, 'utf8'))
process.stdout.write(JSON.stringify(cases.map(({ input, before, after, found }) => [
  feedbackFor(room, input, before, after, found), foundBy(room, input, before, after),
])))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's pure modules")

# The owner's real room in miniature: lock 1 find (throw pillows), lock 2 find (floor vent), lock 3 use_on (the
# pillows on the sofa), lock 4 the Exit, a find on the front door; plus a code and an order lock for the other inputs.
# Only the pillows are carried (owner decision Oct 29): the vent and the door are found, and nothing enters the hand.
PUZZLES = [
    {"id": "p1", "lock_type": "find", "is_exit": False},
    {"id": "p2", "lock_type": "find", "is_exit": False},
    {"id": "p3", "lock_type": "use_on", "is_exit": False},
    {"id": "p4", "lock_type": "code", "is_exit": False},
    {"id": "p5", "lock_type": "order", "is_exit": False},
    {"id": "p6", "lock_type": "find", "is_exit": True},
]
LABELS = {"rug": "entryway rug", "pillows": "throw pillows", "vent": "floor vent", "sofa": "sectional sofa",
          "door": "double front door", "tree": "potted artificial tree"}
ROOM = {"puzzles": PUZZLES, "interactables": [{"id": id, "label": label} for id, label in LABELS.items()]}


def _state(locks: tuple[str, ...] = (), inventory: tuple[str, ...] = (), wrong: dict[str, int] | None = None,
           order: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"locks_open": list(locks), "inventory": list(inventory), "wrong_attempts": wrong or {},
            "order_buffer": order or {"puzzle_id": None, "clicks": []}}


def _click(id: str) -> dict[str, Any]:
    return {"type": "click", "interactable_id": id}


def _use_on(item: str, target: str) -> dict[str, Any]:
    return {"type": "lock_input", "input": {"type": "use_on", "item": item, "target": target}}


HELD = _state(("p1", "p2"), ("pillows",))
CASES: list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], str | None]] = [
    ("a click that opens nothing", _click("rug"), _state(), _state(), "entryway rug. Not this one."),
    ("a pickup that solves a find lock", _click("pillows"), _state(), _state(("p1",), ("pillows",)),
     "You pick up the throw pillows. Puzzle 1 solved."),
    ("a find no use_on needs: found, with no pickup clause", _click("vent"), _state(("p1",), ("pillows",)), HELD,
     "Puzzle 2 solved."),
    ("a use_on that opens its lock", _use_on("pillows", "sofa"), HELD, _state(("p1", "p2", "p3"), ("pillows",)),
     "Puzzle 3 solved."),
    ("the Exit, found and never carried", _click("door"), _state(("p1", "p2", "p3"), ("pillows",)),
     _state(("p1", "p2", "p3", "p6"), ("pillows",)), "The way out is open."),
    ("a wrong use_on", _use_on("pillows", "tree"), HELD, _state(("p1", "p2"), ("pillows",), {"p3": 1}),
     "Puzzle 3: not this, 1."),
    ("a wrong code", {"type": "lock_input", "input": {"type": "code", "puzzle_id": "p4", "code": "111"}},
     _state(wrong={"p4": 1}), _state(wrong={"p4": 2}), "Puzzle 4: not this, 2."),
    ("a right code", {"type": "lock_input", "input": {"type": "code", "puzzle_id": "p4", "code": "415"}},
     _state(), _state(("p4",)), "Puzzle 4 solved."),
    ("a wrong order", _click("tree"), _state(order={"puzzle_id": "p5", "clicks": ["rug"]}),
     _state(wrong={"p5": 1}, order={"puzzle_id": "p5", "clicks": []}), "Puzzle 5: not this, 1."),
    ("an order click mid-sequence: the Order click progress answers", _click("tree"),
     _state(order={"puzzle_id": "p5", "clicks": []}), _state(order={"puzzle_id": "p5", "clicks": ["tree"]}), None),
    ("a use_on that resolves to no Puzzle", _use_on("pillows", "rug"), HELD, HELD, "entryway rug. Not this one."),
    ("a click on an item in hand", _click("pillows"), HELD, HELD, "throw pillows · in hand"),
    ("a click on a found target", _click("vent"), HELD, HELD, "floor vent · found"),
    ("arming an order sequence", {"type": "lock_input", "input": {"type": "order_start", "puzzle_id": "p5"}},
     _state(), _state(order={"puzzle_id": "p5", "clicks": []}), None),
    ("a hint request", {"type": "hint_request"}, _state(), _state(), None),
]


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]


FOUND = ["vent"]
"""What the page found before each case: the vent, solved by a find no use_on needs."""

FOUND_BY: dict[str, str] = {"a find no use_on needs: found, with no pickup clause": "vent",
                            "the Exit, found and never carried": "door"}
"""The cases whose reply found a target: a click that opened a find lock and put nothing in the Inventory."""


def _replies() -> list[tuple[str | None, str | None]]:
    cases = [{"input": input, "before": before, "after": after, "found": FOUND} for _, input, before, after, _ in CASES]
    result = subprocess.run(
        ["node", "--input-type=module", "-e", RUNNER, (WEB_SRC / "feedback.ts").as_uri()],
        input=json.dumps({"room": ROOM, "cases": cases}), cwd=REPO, capture_output=True, text=True, check=True,
    )
    return [tuple(reply) for reply in json.loads(result.stdout)]


@needs_node
def test_each_reply_reads_one_line_per_outcome():
    for (name, *_, expected), (line, _) in zip(CASES, _replies(), strict=True):
        assert line == expected, name


@needs_node
def test_a_find_that_carries_nothing_is_found_and_every_other_reply_finds_nothing():
    # The pillows go into the Inventory (a use_on needs them); the order click and the code open no find lock.
    for (name, *_), (_, found) in zip(CASES, _replies(), strict=True):
        assert found == FOUND_BY.get(name), name


def test_the_lines_are_the_experience_lines_and_the_chip_reads_solved():
    strings = _strings()
    assert strings["notThisOne"].format(label="entryway rug") == "entryway rug. Not this one."
    assert strings["pickUp"].format(label="throw pillows") == "You pick up the throw pillows."
    assert strings["lockSolved"].format(n=1) == "Puzzle 1 solved."
    assert strings["wayOut"] == "The way out is open."
    assert strings["lockNotThis"].format(n=2, count=1) == "Puzzle 2: not this, 1."
    assert strings["found"].format(label="floor vent") == "floor vent · found"
    assert strings["solved"] == "Solved" and "open" not in strings and "lockOpen" not in strings
    play = _section("Voice and Tone").split("**Play screen**", 1)[1]
    row = next(line for line in play.splitlines() if line.startswith("| Feedback line"))
    for key in ("notThisOne", "pickUp", "lockSolved", "wayOut", "lockNotThis", "inHand", "found"):
        assert f'"{strings[key]}"' in row, key
    assert '| Solved chip | plain | "Solved" |' in play and "| Open chip |" not in play
    # The side panel's chip says what the player did: "Solved", never "Open", wherever a Puzzle shows solved.
    assert "opened.textContent = strings.solved" in _ts("components/wizard-notes.ts")
    for path, text in ((p, p.read_text()) for p in WEB_SRC.rglob("*.ts")):
        assert "strings.open\n" not in text and "strings.open)" not in text and "strings.lockOpen" not in text, path


def test_the_line_is_chosen_once_per_reply_and_written_once_to_the_live_region():
    play = _ts("play.ts")
    post = play.split("post: async (body) => {", 1)[1].split("\n    },", 1)[0]
    # The state the input was sent against, not a poll that landed meanwhile.
    assert post.index("const before = latest") < post.index("await postEvent(") < post.index("receive(reply)")
    assert post.index("receive(reply)") < post.index("feedback?.(body, before, reply)")
    said = play.split("feedback = (body, before, reply) => {", 1)[1].split("\n      }\n", 1)[0]
    assert "const line = feedbackFor(shown, body, before, reply, foundTargets(session.id))" in said
    assert "scene.say(line)" in said and "announce(`${strings.speakerGuide} ${line}`)" in said
    assert "if (!mounted || ended || line === null) return" in said
    # The line replaces the state-read lock outcomes, so nothing is heard twice; the Completion screen says nothing.
    assert not (WEB_SRC / "lock-outcomes.ts").exists() and "lockOutcomes" not in play
    assert "feedback" not in play.split("export function mountPlayBehind(", 1)[1]
    selection = _code(_ts("feedback.ts"))
    for banned in ("document", "announce(", ".post(", "addEventListener"):
        assert banned not in selection, banned


def test_the_line_sits_over_the_bottom_of_the_scene_frame_with_the_guide_and_fades_after_its_hold():
    line = _ts("components/feedback-line.ts")
    assert "import './feedback-line.css'" in line
    assert "export const FEEDBACK_HOLD_MS = 2500" in line
    assert "wizardPortrait('guide', 32)" in line
    assert "words.className = 'wizard-line'" in line
    assert "element.setAttribute('aria-hidden', 'true')" in line  # heard once, from the live region
    say = _function(line, "feedbackLine").split("function say(", 1)[1]
    assert "fadeIn(element)" in say and "setTimeout(() => element.classList.remove('is-shown'), FEEDBACK_HOLD_MS)" in say
    scene = _ts("scene/index.ts")
    assert "const feedback = feedbackLine()" in scene and "frame.append(ground, feedback.element, turns.left, turns.right)" in scene
    assert "say: feedback.say" in scene
    rules = css_rules(_ts("components/feedback-line.css"))
    strip = rules[".feedback-line"]
    assert strip["position"] == "absolute" and strip["bottom"] == "var(--spacing-3)"
    assert strip["background"] == "var(--parchment)" and strip["color"] == "var(--ink)"
    assert strip["pointer-events"] == "none" and strip["opacity"] == "0"
    assert strip["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".feedback-line.is-shown"] == {"opacity": "1"}
    assert "transform" not in _code(_ts("components/feedback-line.css"))


def test_a_new_inventory_item_glows_once():
    inventory = _ts("components/inventory.ts")
    assert "glowOnce(item, 'is-glowing', hold)" in inventory
    assert "matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS" in inventory
    rules = css_rules(_ts("components/inventory.css"))
    assert rules[".inventory-slot.is-glowing .inventory-well"] == {"box-shadow": "var(--elevation-lamp-glow)"}
    assert rules[".inventory-well"]["transition"] == "box-shadow var(--motion-hover) var(--motion-ease)"


def test_the_asides_left_are_the_ones_the_line_does_not_repeat():
    opened = _ts("lock-opened.ts")
    # The Exit's aside and the Wrong attempt aside said what the feedback line now says, so neither is spoken.
    assert "if (puzzle.is_exit) return null" in _function(opened, "asideFor")
    assert "notThat" not in opened and "notThat" not in _ts("components/hint-area.ts")
    assert "notThatOne" not in _strings() and "asideExit" not in _strings()


def test_the_contract_records_the_feedback_line():
    patterns = _section("Component Patterns")
    assert "| Feedback line |" in patterns and "2.5 s" in patterns
    floor = _section("Accessibility Floor")
    assert "feedback line" in floor.lower()
    design = design_text()
    component = design.split("  feedback-line:\n", 1)[1].split("\n  ", 1)[0]
    assert "background: '{colors.parchment}'" in component
    assert "feedback line" in design.split("**Motion.**", 1)[1].split("\n\n", 1)[0]
