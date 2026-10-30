"""The unlock moment (owner decision, Oct 28; story mode, Oct 29): one `lockOpened` routine, fed the states the server
sends, fires when a Puzzle moves to open: the solved Hotspot blooms and the Scene frame glows once, then it hands over
to the solve beat (build spec 1.9). The Guide's unlock asides are retired with the Hint area: the Riddler's solve line
says it (tests/web/test_story_play.py). Source-reading checks, as the client has no test runner; the browser run
proves the rest.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import _section, _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n  }\n", 1)[0]


def test_the_asides_are_gone_with_the_hint_area():
    strings = _strings()
    for key in ("asideFind", "asideCode", "asideOrder", "asideUseOn"):
        assert key not in strings, key
    opened = _ts("lock-opened.ts")
    assert "asideFor" not in opened and "aside" not in _code(opened)
    assert "That was the latch." not in _section("Voice and Tone")


def test_the_routine_blooms_the_target_then_hands_over_to_the_solve_beat():
    opened = _ts("lock-opened.ts")
    # The last clicked target for find, use_on and order; for code the frame alone blooms.
    assert "return puzzle.lock_type === 'code' ? null : lastTarget" in _function(opened, "bloomTarget")
    routine = opened.split("export function lockOpened(", 1)[1]
    assert routine.index("stage.bloom(bloomTarget(last, stage.lastTarget()))") < routine.index("onOpened(last, before, state)")
    assert "export const SOLVE_BEAT_DELAY_MS = 1100" in opened
    # The target is the Interactable the latest click or use_on named, recorded where each is posted.
    scene = _ts("scene/index.ts")
    assert "lastTarget = interactable.id" in _function(scene, "activate")
    assert "lastTarget = target.id" in _function(scene, "useOn")
    play = _ts("play.ts")
    assert "lockOpened(() => shown, latest, scene, (puzzle, before, after) => {" in play
    assert "queue = queue.then(() => solveBeat(puzzle, before, after))" in play
    assert "await pause(SOLVE_BEAT_DELAY_MS)" in _function(play, "solveBeat")


def test_nothing_blooms_or_plays_on_reload_and_nothing_is_announced_logged_or_counted():
    opened = _ts("lock-opened.ts")
    routine = opened.split("export function lockOpened(", 1)[1]
    assert "let seen = first" in routine and "seen = state" in routine
    code = _code(opened)
    for banned in ("announce(", ".post(", "hint_request", "localStorage", "rung"):
        assert banned not in code, banned
    behind = _ts("play.ts").split("export function mountPlayBehind(", 1)[1]
    assert "lockOpened(" not in behind and "solveBeat" not in behind  # the closing sheet's Scene plays nothing


def test_the_bloom_and_the_frame_glow_stay_inside_the_motion_rule():
    fade = _ts("fade.ts")
    glow = fade.split("export function glowOnce(", 1)[1]
    assert "element.classList.add(className)" in glow and "element.classList.remove(className), hold)" in glow
    scene = _ts("scene/index.ts")
    bloom = _function(scene, "bloom")
    assert "matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS" in bloom
    assert "glowOnce(frame, 'is-glowing', hold)" in bloom and "layer?.bloom(target, hold)" in bloom
    layer = _ts("scene/hotspots.ts")
    assert "hotspot.append(hotspotReveal(d), path('hotspot-bloom', d), path('hotspot-hit', d))" in layer
    assert "glowOnce(hotspot, 'is-blooming', hold)" in _function(layer, "bloom")
    rules = _rules("scene/scene.css")
    frame = rules[".scene-frame"]
    assert frame["transition"] == "border-color var(--motion-hover) var(--motion-ease), box-shadow var(--motion-hover) var(--motion-ease)"
    assert rules[".scene-frame.is-glowing"] == {
        "border-color": "var(--lamp)", "box-shadow": "var(--elevation-vignette), var(--elevation-lamp-glow)"}
    path = rules[".hotspot-bloom"]
    assert path["fill"] == "var(--hotspot-outline)" and path["opacity"] == "0" and path["pointer-events"] == "none"
    assert path["transition"] == "opacity var(--motion-hover) var(--motion-ease)"
    assert rules[".hotspot.is-blooming .hotspot-bloom"] == {"opacity": "1"}
    assert "transform" not in _code(_ts("scene/scene.css"))  # fades and glows only


def test_the_contract_records_the_unlock_moment_and_its_hand_over():
    design = design_text()
    motion = design.split("**Motion.**", 1)[1].split("\n\n", 1)[0]
    assert "lock open" in motion and "pickup" in motion and "Wrong attempt" in motion and "2%" in motion
    hotspot = design.split("  hotspot:\n", 1)[1].split("\n  hotspot-label-chip:", 1)[0]
    assert "bloomFill: '{colors.hotspot-outline}'" in hotspot and "bloom: 300ms" in hotspot
    patterns = _section("Component Patterns")
    assert "**Opened (the unlock moment):**" in patterns and "It hands over to the solve beat 1100 ms later" in patterns
    assert "unlock aside" not in patterns
