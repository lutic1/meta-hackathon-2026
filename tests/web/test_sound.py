"""Sound (owner request Oct 30): background music and interactive sounds, synthesized in the browser with the Web Audio
API (no audio file, no new dependency), behind a sound toggle at the right end of the top bar on every screen.

The pure parts (the stored choice, the scale and level constants, the cue a reply plays) run in Node as they ship;
the wiring is read from the TypeScript; the levels and the AudioContext's states are proved in the browser run.
"""

import json
import re
import shutil
import subprocess

import pytest

from tests.web.design import REPO, WEB_SRC, css_rules, design_text
from tests.web.test_strings import _section, _strings

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's pure modules")
EXPERIENCE = REPO / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md"
AMENDED = "(amended 30 Oct 2026, owner request)"


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _node(script: str, module: str, stdin: str = "") -> object:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, (WEB_SRC / module).as_uri()],
        input=stdin, cwd=REPO, capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


STORAGE = """
const store = new Map()
let refuse = false
globalThis.localStorage = {
  getItem: (key) => { if (refuse) throw new Error('refused'); return store.has(key) ? store.get(key) : null },
  setItem: (key, value) => { if (refuse) throw new Error('refused'); store.set(key, String(value)) },
}
const audio = await import(process.argv[1])
const seen = [audio.soundOn()]
audio.setSoundOn(false)
seen.push(audio.soundOn(), store.get(audio.SOUND_KEY))
audio.setSoundOn(true)
seen.push(audio.soundOn(), store.get(audio.SOUND_KEY))
store.set(audio.SOUND_KEY, 'off')
seen.push(audio.readSoundOn())
refuse = true
seen.push(audio.readSoundOn())
audio.setSoundOn(false)
// Without Web Audio (Node has none) every cue and mood change is a quiet no-op.
audio.setMood('play'); audio.cue('knock'); audio.cue('cardHover', -0.6); audio.startSound()
process.stdout.write(JSON.stringify({ seen, key: audio.SOUND_KEY }))
"""


@needs_node
def test_the_choice_is_remembered_per_browser_on_by_default_and_storage_never_throws():
    out = _node(STORAGE, "audio.ts")
    assert out["key"] == "keyframe.sound.v1"
    # Default on; off is stored and read back; a refused storage reads as the default and is never thrown.
    assert out["seen"] == [True, False, "off", True, "on", False, True]


CONSTANTS = """
const audio = await import(process.argv[1])
const { BPM, SCALE, MUSIC_RMS_DBFS, MUSIC_PEAK_DBFS, EFFECT_PEAK_DBFS, FADE_IN_S, CROSSFADE_S, HOVER_GAP_MS, CUES } = audio
process.stdout.write(JSON.stringify({ BPM, SCALE, MUSIC_RMS_DBFS, MUSIC_PEAK_DBFS, EFFECT_PEAK_DBFS, FADE_IN_S, CROSSFADE_S,
  HOVER_GAP_MS, CUES }))
"""


@needs_node
def test_the_scale_tempo_and_levels_are_the_quiet_candlelit_ones():
    c = _node(CONSTANTS, "audio.ts")
    assert 60 <= c["BPM"] <= 70
    assert c["SCALE"] in ([0, 3, 5, 7, 10], [0, 2, 3, 5, 7, 9, 10])  # minor pentatonic or dorian
    assert c["MUSIC_RMS_DBFS"] == -26 and c["MUSIC_PEAK_DBFS"] == -10 and c["EFFECT_PEAK_DBFS"] == -6
    assert c["FADE_IN_S"] == 1.5 and c["CROSSFADE_S"] == 2
    # The two hover sounds are the only ones a pointer plays by moving, each throttled; the Hotspot tick every 250 ms.
    assert set(c["HOVER_GAP_MS"]) == {"cardHover", "hotspotHover"} and c["HOVER_GAP_MS"]["hotspotHover"] == 250
    assert set(c["CUES"]) == {"cardHover", "cardChoose", "cardClose", "pageTurn", "trap", "hotspotHover", "knock",
                              "pickUp", "packSelect", "solve", "chestOpen", "hintPinned", "step", "escape", "playIntro"}


def test_the_engine_waits_for_a_gesture_ducks_under_a_sounding_video_and_suspends_when_hidden_or_off():
    audio = _code(_ts("audio.ts"))
    # One lazily created context, made or resumed on the first pointerdown or keydown anywhere.
    assert audio.count("new Context(") == 1
    assert "document.addEventListener('pointerdown', wake, true)" in audio
    assert "document.addEventListener('keydown', wake, true)" in audio
    assert "document.addEventListener('visibilitychange', onVisibility)" in audio
    assert "void context.suspend()" in audio and "void context.resume()" in audio
    # Every media event on the page is heard at the document, so any video with its sound on ducks the music.
    for event in ("play", "pause", "ended", "volumechange"):
        assert f"'{event}'" in audio, event
    assert "!video.paused && !video.ended && !video.muted && video.volume > 0" in audio
    # A generated decaying-noise impulse, no file.
    assert "createConvolver()" in audio and "fetch(" not in audio and ".mp3" not in audio and ".wav" not in audio



def _block(text: str, start: str) -> str:
    """The block from `start` to the first line closing it at the indent of its opening line."""
    at = text.index(start)
    indent = at - text.rfind("\n", 0, at) - 1
    return text[at:text.index("\n" + " " * indent + "}", at)]


def test_the_first_gesture_only_makes_the_context_and_the_reverb_and_music_wait_out_the_card_turn():
    audio = _code(_ts("audio.ts"))
    # The gesture makes the context (browsers want it there) and the light effects graph, so its own sound still plays;
    # the reverb's impulse and the music, the heavy part, wait for an idle stretch the card turn never leaves.
    wake = _block(audio, "function wake(): void {")
    assert "const mix = createMixer(live, seeded(Date.now()))" in wake
    later = _block(wake, "whenIdle(() => {")
    for line in ("mix.start()", "mix.fade(true, FADE_IN_S)", "setInterval("):
        assert line in later and wake.count(line) == 1, line
    idle = _block(audio, "function whenIdle(work: () => void): void {")
    assert "deadline.timeRemaining() >= IDLE_BUDGET_MS || deadline.didTimeout" in idle
    assert "setTimeout(work, IDLE_FALLBACK_MS)" in idle
    # One deadline for every retry, so a page that never idles (the landing in full motion) still gets its music.
    assert "const until = performance.now() + IDLE_WAIT_MS" in idle
    assert idle.count("idle(wait, { timeout: Math.max(0, until - performance.now()) })") == 2
    # In the mixer the impulse and the two moods' drones are built by start() alone, once.
    mixer = _block(audio, "export function createMixer(context: BaseAudioContext, random: () => number): Mixer {")
    start = _block(mixer, "start: () => {")
    for line in ("reverb.buffer = impulse(context, 3.2, random)", "moodBus('landing')", "moodBus('play')"):
        assert line in start and audio.count(line) == 1, line

def test_no_sound_on_plain_mouse_movement_and_every_hover_sound_is_throttled():
    hover = re.compile(r"addEventListener\('(pointermove|mousemove|pointerover|mouseover)'")
    for path in WEB_SRC.rglob("*.ts"):
        text = _code(path.read_text())
        for match in hover.finditer(text):
            handler = text[match.end():].split("\n    })", 1)[0]
            assert "cue(" not in handler, f"{path}: a sound on plain mouse movement"
    audio = _code(_ts("audio.ts"))
    assert "if (gap !== undefined && now - (lastHover.get(name) ?? -Infinity) < gap) return" in audio
    chooser = _code(_ts("chooser.ts"))
    enter = chooser.split("slot.addEventListener('pointerenter', () => {", 1)[1].split("\n    })", 1)[0]
    assert "cue('cardHover', PAN[i])" in enter
    hotspots = _code(_ts("scene/hotspots.ts"))
    enter = hotspots.split("hotspot.addEventListener('pointerenter', () => {", 1)[1].split("\n    })", 1)[0]
    assert "cue('hotspotHover')" in enter


WIRING = {
    "chooser.ts": ["cue('cardHover', PAN[i])", "cue('cardChoose')", "cue('cardClose')", "cue('playIntro')"],
    "story.ts": ["cue('pageTurn')"],
    "scene/index.ts": ["cue('trap')", "cue('step')"],
    "scene/hotspots.ts": ["cue('hotspotHover')"],
    "use-on.ts": ["cue('packSelect')"],
    "components/treasure-chest.ts": ["cue('chestOpen')"],
    "components/riddle-note.ts": ["cue('hintPinned')"],
    "play.ts": ["for (const name of soundFor(shown, body, before, reply, foundTargets(session.id))) cue(name)", "cue('escape')"],
}


def test_each_sound_is_one_call_where_its_action_already_happens():
    for path, calls in WIRING.items():
        text = _code(_ts(path))
        assert "from './audio.ts'" in text or "from '../audio.ts'" in text, path
        for call in calls:
            assert text.count(call) == 1, (path, call)
    # The music follows the route: the play mood on the Play screen, the landing mood everywhere else.
    assert "setMood(place.route.name === 'play' ? 'play' : 'landing')" in _code(_ts("shell.ts"))
    assert "startSound()" in _code(_ts("shell.ts"))


SOUND_FOR = """
import { readFileSync } from 'node:fs'
const { soundFor } = await import(process.argv[1])
const { room, cases } = JSON.parse(readFileSync(0, 'utf8'))
process.stdout.write(JSON.stringify(cases.map(([input, before, after]) => soundFor(room, input, before, after, ['vent']))))
"""


@needs_node
def test_a_reply_plays_the_knock_the_pop_or_the_chime_and_the_way_out_waits_for_its_fanfare():
    from tests.web.test_feedback_line import CASES, ROOM

    cases = [[input, before, after] for _, input, before, after, _ in CASES]
    got = dict(zip((name for name, *_ in CASES), _node(SOUND_FOR, "feedback.ts", json.dumps({"room": ROOM, "cases": cases})),
                   strict=True))
    assert got["a click that opens nothing"] == ["knock"]
    assert got["a pickup that solves a find lock"] == ["pickUp", "solve"]
    assert got["a find no use_on needs: found, with no pickup clause"] == ["solve"]
    assert got["a use_on that opens its lock"] == ["solve"]
    assert got["the Exit, found and never carried"] == []  # the escape's fanfare plays on the way out
    assert got["a wrong use_on"] == ["knock"] and got["a wrong code"] == ["knock"] and got["a wrong order"] == ["knock"]
    assert got["a use_on that resolves to no Puzzle"] == ["knock"]
    for quiet in ("an order click mid-sequence: the Order click progress answers", "arming an order sequence",
                  "a hint request", "a click on an item in hand", "a click on a found target"):
        assert got[quiet] == [], quiet


def test_the_toggle_reads_sound_on_or_off_and_sits_at_the_right_end_of_every_top_bar():
    strings = _strings()
    assert strings["soundOn"] == "Sound on" and strings["soundOff"] == "Sound off"
    toggle = _code(_ts("components/sound-toggle.ts"))
    assert "button.className = 'button-secondary top-bar-sound'" in toggle
    assert "button.setAttribute('aria-pressed', String(on))" in toggle
    assert "label.textContent = on ? strings.soundOn : strings.soundOff" in toggle
    assert "setSoundOn(on)" in toggle and "soundOn()" in toggle
    bar = _code(_ts("components/top-bar.ts"))
    # Outside the controls slot, so the Completion screen's inert controls leave it live.
    assert "end.append(controls, soundToggle())" in bar and "element.append(start, timer, end)" in bar
    rules = css_rules(_ts("components/top-bar.css"))
    assert rules[".top-bar-end,\n.top-bar-controls"]["justify-content"] == "flex-end"
    sound = rules[".top-bar-end > .top-bar-sound"]
    assert sound["color"] == "var(--text)" and sound["border"] == "1px solid var(--hairline)" and sound["background"] == "transparent"
    lit = rules[".top-bar-end > .top-bar-sound:hover,\n.top-bar-end > .top-bar-sound:focus-visible"]
    assert lit == {"color": "var(--lamp-strong)", "border-color": "var(--lamp)", "background": "var(--lamp-hover-fill)"}
    # Over a chooser card back the bar's right end ("Play intro" and the toggle) stays live while the rest is held
    # inert, and the dialog's Tab ring runs the panel, "Play intro", then the toggle.
    chooser = _code(_ts("chooser.ts"))
    outside = chooser.split("  function outside(): HTMLElement[] {", 1)[1].split("\n  }", 1)[0]
    assert "!node.contains(introButton)" in outside
    trap = chooser.split("  function trapTab(event: KeyboardEvent): void {", 1)[1].split("\n  }", 1)[0]
    assert "const sound = document.querySelector<HTMLElement>('.top-bar-sound')" in trap
    assert "[introButton, sound]" in trap and "const ring = [...controls, ...bar]" in trap
    # "Play intro" plays its own sound where it opens the intro.
    assert "cue('playIntro')" in chooser.split("  function reopenIntro(): void {", 1)[1].split("\n  }", 1)[0]


def test_the_toggle_stays_live_through_the_story_intro_and_its_enter_never_turns_the_page():
    """Review Oct 31: the story intro held the whole top bar inert, so its music could not be stopped for five beats
    (WCAG 1.4.2). It holds the bar's start, Timer and controls slot only; the toggle at the right end stays live."""
    play = _code(_ts("play.ts"))
    assert "const barHeld = [...frame.topBar.querySelectorAll<HTMLElement>('.top-bar-start, .top-bar-timer, .top-bar-controls')]" in play
    hold = play.split("  function holdForIntro(on: boolean): void {", 1)[1].split("\n  }", 1)[0]
    assert "for (const part of barHeld) part.inert = on" in hold and "frame.topBar.inert" not in hold
    assert "for (const part of barHeld) part.inert = false" in play.split("return () => {\n    mounted = false", 1)[1]
    # The stage's Enter answers only on the page or inside the stage, so Enter on the toggle toggles and turns no page.
    stage = _code(_ts("components/story-stage.ts"))
    key = stage.split("  function onKey(event: KeyboardEvent): void {", 1)[1].split("\n  }", 1)[0]
    assert "if (event.target !== document.body && !(event.target instanceof Node && element.contains(event.target))) return" in key


def test_the_ban_on_sound_excepts_the_one_audio_module():
    from tests.web.test_banned_interactions import BANS

    for path in WEB_SRC.rglob("*.ts"):
        if path.name == "audio.ts":
            continue
        assert not re.search(BANS["plays audio"], path.read_text()), path


def test_the_docs_record_the_sound_section_and_row():
    design = design_text()
    sound = design.split("\n## Sound\n", 1)[1].split("\n## ", 1)[0]
    assert AMENDED in sound
    for word in ("-26 dBFS", "-10 dBFS", "-6 dBFS", "Web Audio", "keyframe.sound.v1"):
        assert word in sound, word
    experience = EXPERIENCE.read_text()
    row = next(line for line in experience.splitlines() if line.startswith("| Sound |"))
    assert AMENDED in row and '"Sound on"' in row and '"Sound off"' in row and "keyframe.sound.v1" in row
    assert "No sound in v1" not in _section("Foundation") or AMENDED in _section("Foundation")
