"""The unlock moment (owner decision, Oct 28): one `lockOpened` routine, fed the states the server sends, fires when
a Puzzle moves to open: the solved Hotspot blooms, the Scene frame glows once, the Open chip fades in lifted on the
paper shadow and the Guide speaks one aside per lock type; a Wrong attempt glows the Guide's ring once with its own
line. The asides are client-side presentation: never a Rung, never counted, never logged, never announced and never
shown again on reload. Source-reading checks, as the client has no test runner; the browser run proves the rest.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import EXPERIENCE, _section, _strings

ASIDES = {
    "asideFind": "That was the latch.",
    "asideCode": "Right on the number.",
    "asideOrder": "Each in its turn. The room approves.",
    "asideUseOn": "The right thing in the right place.",
    "asideExit": "The way out is open.",
    "notThatOne": "Not that one. The room is patient.",
}


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n  }\n", 1)[0]


def test_the_asides_are_the_experience_lines_and_name_no_solution():
    strings = _strings()
    for key, line in ASIDES.items():
        assert strings[key] == line, key
    play = _section("Voice and Tone").split("**Play screen**", 1)[1]
    for line in ASIDES.values():
        assert f'"{line}"' in play, line
    # Each aside is one fixed line per lock type: no object, place, number or Puzzle content ever reaches it.
    words = " ".join(ASIDES.values()).lower()
    for token in ("key", "clock", "chest", "shelf", "door", "415", "7342", "{"):
        assert token not in words, token


def test_the_routine_picks_the_hotspot_and_the_aside_per_lock_type():
    opened = _ts("lock-opened.ts")
    # The last clicked target for find, use_on and order; for code the frame alone blooms.
    assert "return puzzle.lock_type === 'code' ? null : lastTarget" in _function(opened, "bloomTarget")
    aside = _function(opened, "asideFor")
    assert "if (puzzle.is_exit) return strings.asideExit" in aside and "return ASIDES[puzzle.lock_type]" in aside
    assert re.search(r"find: strings\.asideFind,\s+code: strings\.asideCode,\s+order: strings\.asideOrder,\s+use_on: strings\.asideUseOn,", opened)
    routine = _function(opened, "lockOpened")
    assert "stage.bloom(bloomTarget(last, stage.lastTarget()))" in routine and "voice.aside(asideFor(last))" in routine
    # A Rung the same state carries holds the Hint area: the Scene blooms, neither aside is spoken.
    assert "const rung = state.rung_changes.length > seen.rung_changes.length" in routine
    assert routine.index("const rung =") < routine.index("seen = state") < routine.index("if (rung) return")
    assert routine.index("stage.bloom(") < routine.index("if (rung) return") < routine.index("voice.aside(")
    # The target is the Interactable the latest click or use_on named, recorded where each is posted.
    scene = _ts("scene/index.ts")
    assert "lastTarget = interactable.id" in _function(scene, "activate")
    assert "lastTarget = target.id" in _function(scene, "useOn")
    assert "return { unmount, reshape, lastTarget: () => lastTarget, bloom }" in scene


def test_a_wrong_attempt_glows_the_ring_once_with_its_line():
    routine = _function(_ts("lock-opened.ts"), "lockOpened")
    assert "(state.wrong_attempts[puzzle.id] ?? 0) > (seen.wrong_attempts[puzzle.id] ?? 0)" in routine
    assert "else if (wrong) voice.notThat()" in routine
    assert routine.index("if (rung) return") < routine.index("voice.notThat()")
    hint = _ts("components/hint-area.ts")
    assert "notThat: () => present({ label: null, text: strings.notThatOne, shown: null }, true)" in hint
    assert "aside: (line) => present({ label: null, text: line, shown: null }, false)" in hint


def test_nothing_blooms_or_speaks_on_reload_and_nothing_is_announced_logged_or_counted():
    opened = _ts("lock-opened.ts")
    routine = _function(opened, "lockOpened")
    assert "let seen = first" in routine and "seen = state" in routine
    code = _code(opened)
    for banned in ("announce(", ".post(", "hint_request", "localStorage"):
        assert banned not in code, banned
    # The routine only reads `rung_changes` to yield to a Rung: it never makes, posts or announces one.
    assert re.findall(r"\w*rung\w*", code) == ["rung", "rung_changes", "rung_changes", "rung"]
    play = _ts("play.ts")
    assert "parts.push(lockOpened(view, latest, scene, hints))" in play
    behind = play.split("export function mountPlayBehind(", 1)[1]
    assert "lockOpened(" not in behind  # the Completion screen's dimmed Scene plays nothing


def test_the_bloom_the_frame_glow_and_the_chip_lift_stay_inside_the_motion_rule():
    fade = _ts("fade.ts")
    assert "export function glowOnce(element: Element, className: string, hold: number): void" in fade
    glow = _function(fade, "glowOnce")
    assert "element.classList.add(className)" in glow and "element.classList.remove(className), hold)" in glow
    scene = _ts("scene/index.ts")
    bloom = _function(scene, "bloom")
    assert "matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS" in bloom
    assert "glowOnce(frame, 'is-glowing', hold)" in bloom and "layer?.bloom(target, hold)" in bloom
    layer = _ts("scene/hotspots.ts")
    assert "hotspot.append(reveal, path('hotspot-bloom', d), path('hotspot-hit', d))" in layer
    assert "glowOnce(hotspot, 'is-blooming', hold)" in _function(layer, "bloom")
    rules = _rules("scene/scene.css")
    frame = rules[".scene-frame"]
    assert frame["transition"] == "border-color var(--motion-hover) var(--motion-ease), box-shadow var(--motion-hover) var(--motion-ease)"
    assert rules[".scene-frame.is-glowing"] == {
        "border-color": "var(--lamp)", "box-shadow": "var(--elevation-vignette), var(--elevation-lamp-glow)"}
    path = rules[".hotspot-bloom"]
    assert path["fill"] == "var(--hotspot-outline)" and path["opacity"] == "0" and path["pointer-events"] == "none"
    assert path["transition"] == "opacity var(--motion-hover) var(--motion-ease)"
    assert path["filter"] == "drop-shadow(0 0 12px var(--hotspot-outline)) drop-shadow(var(--elevation-lamp-glow))"
    assert rules[".hotspot.is-blooming .hotspot-bloom"] == {"opacity": "1"}
    notes = _rules("components/wizard-notes.css")
    chip = notes[".notes-lock .chip-open"]
    assert chip["box-shadow"] == "var(--elevation-paper)"
    assert chip["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert notes[".notes-lock .chip-open.is-arriving"] == {"opacity": "0"}
    assert "fadeIn(chip)" in _function(_ts("components/wizard-notes.ts"), "opening")
    # Fades and glows only (test_tokens bans every transform and keyframe across the client).
    for name in ("scene/scene.css", "components/wizard-notes.css"):
        assert "transform" not in _code((WEB_SRC / name).read_text())


def test_the_contract_records_the_unlock_moment():
    design = design_text()
    motion = design.split("**Motion.**", 1)[1].split("\n\n", 1)[0]
    assert "lock open" in motion and "Wrong attempt" in motion and "2%" in motion
    hotspot = design.split("  hotspot:\n", 1)[1].split("\n  hotspot-label-chip:", 1)[0]
    assert "bloomFill: '{colors.hotspot-outline}'" in hotspot and "bloom: 300ms" in hotspot
    frame = design.split("  scene-frame:\n", 1)[1].split("\n  hotspot:", 1)[0]
    assert "openRule: '1px solid {colors.lamp}'" in frame and "openGlow: '{elevation.lamp-glow}'" in frame
    chip = design.split("  chip-open:\n", 1)[1].split("\n  evidence-card:", 1)[0]
    assert "openLift: '{elevation.paper}'" in chip and "scale" not in chip
    experience = EXPERIENCE.read_text()
    patterns = _section("Component Patterns")
    assert "**Opened (the unlock moment):**" in patterns and "unlock aside" in patterns
    floor = _section("Accessibility Floor")
    assert "asides" in floor and "never written" in floor
    assert experience.count('"Not that one. The room is patient."') >= 1
