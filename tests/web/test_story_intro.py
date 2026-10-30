"""The story intro on the Play screen (owner decision Oct 29; build spec 1.1, 1.2, 3.1, 5.4, 5.5 and 6): five beats on
the Story stage before play, once per Session: the Architect's welcome, the Trickster's trap with the lock seal on the
way out, the Riddler's entrance, the Guide and the glowing chest, and the Riddler's first riddle. The lines are pure and
run in Node; the rest reads the TypeScript and the stylesheets (the client has no test runner), and the browser run
proves the beats themselves.
"""

import re

from tests.web.design import WEB_SRC, css_rules
from tests.web.test_riddles import DEMO, STORY, TOLD, _photo, _run, needs_node
from tests.web.test_strings import _section, _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\n  }\n", 1)[0]


def _interactable(id: str, photo: int, outlined: bool = True) -> dict:
    return {"id": id, "label": id, "photo": photo, "polygons": [[[0, 0], [1, 0], [1, 1]]] if outlined else None,
            "instances": 1, "attributes": []}


THINGS = [_interactable(f"thing{k}", k % 8) for k in range(12)] + [_interactable("unseen", 0, outlined=False)]
OWN = {**DEMO, "name": None, "interactables": THINGS}
DEMO_ROOM = {**DEMO, "interactables": THINGS}


# --- The lines -------------------------------------------------------------------------------------------------------


@needs_node
def test_the_intro_lines_fill_the_templates_from_the_room_for_an_own_room_and_a_demo_room():
    own, demo = _run(["introLines", OWN, "pillows", None], ["introLines", DEMO_ROOM, "pillows", None])
    assert own == {
        "welcome": "Thank you for your photos. I built your front hall and lounge from them: 8 angles, 12 things "
                     "worth a closer look.",
        "trap": "Oh no, you seem to be trapped! I locked the way out and gave the key to the Riddler. Wicked of "
                     "me, I know.",
        "entrance": "Don't mind him; he thinks a locked room is a party. To escape, you must answer my riddles: 4 of "
                   "them, one at a time.",
        "guide": "Stuck? I keep 2 hints for the whole house. Choose your moment.",
        "first": "Start in the lounge. You must answer this.",
    }
    assert demo == {**own, "welcome": "Welcome to someone's front hall and lounge. I built it from their photos: "
                                        "8 angles, 12 things worth a closer look."}


@needs_node
def test_a_room_whose_photos_name_no_area_is_your_room():
    old = {**OWN, "photos": [_photo("room", None) for _ in OWN["photos"]]}
    demo = {**old, "name": "Someone's room"}
    own_line, demo_line = (lines["welcome"] for lines in _run(["introLines", old, "pillows", None],
                                                                ["introLines", demo, "pillows", None]))
    assert own_line.startswith("Thank you for your photos. I built your room from them: 8 angles")
    assert demo_line.startswith("Welcome to someone's room. I built it from their photos: 8 angles")
    three = {**OWN, "photos": [_photo("hall", 0), _photo("lounge", 0), _photo("kitchen", 0)]}
    assert "I built your hall, lounge and kitchen from them: 3 angles" in _run(["introLines", three, "pillows", None])[0]["welcome"]


@needs_node
def test_the_rooms_story_wins_and_the_first_riddles_opening_follows_its_where_line():
    told = {**TOLD, "name": None, "interactables": THINGS}
    assert _run(["introLines", told, "pillows", None])[0] == {
        "welcome": "a", "trap": "t", "entrance": "r", "guide": "g", "first": "Start in the lounge. Open.",
    }
    # The opening is the one written for that riddle, whatever its place in the story's list.
    riddles = [{**riddle, "opening": f"Mind the {riddle['puzzle_id']}."} for riddle in STORY["riddles"]]
    reordered = {**told, "story": {**STORY, "riddles": riddles[::-1]}}
    assert _run(["introLines", reordered, "vent", None])[0]["first"] == "Start in the front hall. Mind the vent."


@needs_node
def test_a_demo_room_is_welcomed_by_the_visitor_line_and_your_own_room_by_the_thank_you():
    visitor = {**STORY, "architect_welcome_visitor": "v"}
    demo, own = _run(["introLines", {**TOLD, "story": visitor, "interactables": THINGS}, "pillows", None],
                     ["introLines", {**TOLD, "story": visitor, "name": None, "interactables": THINGS}, "pillows", None])
    assert (demo["welcome"], own["welcome"]) == ("v", "a")
    # A story stored before the visitor line, or with it null, welcomes a Demo room with the Demo template.
    for story in (STORY, {**STORY, "architect_welcome_visitor": None}):
        line = _run(["introLines", {**TOLD, "story": story, "interactables": THINGS}, "pillows", None])[0]["welcome"]
        assert line == "Welcome to someone's front hall and lounge. I built it from their photos: 8 angles, 12 things " \
                       "worth a closer look."


@needs_node
def test_a_returning_players_greeting_replaces_the_guides_line_and_nothing_else():
    greeted, told = _run(["introLines", OWN, "pillows", "Back again. Two hints wait."],
                         ["introLines", {**TOLD, "name": None, "interactables": THINGS}, "pillows", "Back again."])
    assert greeted["guide"] == "Back again. Two hints wait." and told["guide"] == "Back again."
    assert greeted["welcome"].startswith("Thank you for your photos.") and told["welcome"] == "a"


def test_the_intro_strings_are_the_experience_lines_and_only_the_trap_line_exclaims():
    strings = _strings()
    assert strings["introTrap"] == ("Oh no, you seem to be trapped! I locked the way out and gave the key to the "
                                    "Riddler. Wicked of me, I know.")
    assert [key for key, value in strings.items() if "!" in value] == ["introTrap"]
    assert (strings["roleArchitect"], strings["roleTrickster"], strings["roleRiddler"], strings["roleGuide"]) == (
        "Built this room", "Locked you in", "Holds the key", "Keeps the chest")
    assert (strings["next"], strings["startLooking"], strings["introSkip"]) == ("Next", "Start looking", "Skip intro")
    voice = _section("Voice and Tone")
    assert "Welcome to someone's {areas}. I built it from their photos: {photos} angles, {things} things worth a " \
           "closer look." in voice


# --- The Story stage -------------------------------------------------------------------------------------------------


def test_the_stage_casts_two_tall_portraits_the_speaker_lit_and_the_other_dimmed():
    stage = _ts("components/story-stage.ts")
    cast = _function(stage, "takeStage")
    assert "const cast = beat.cast ?? { left: beat.speaker }" in stage
    assert "slot.figure.classList.toggle('is-quiet', wizard !== beat.speaker)" in cast
    assert "box.classList.toggle('is-right', beat.cast?.right === beat.speaker && beat.cast.left === undefined" in stage
    rules = css_rules(_ts("components/story-stage.css"))
    assert rules[".story-portrait.is-right"]["right"] == "max(2vw, 14px)"
    quiet = rules[".story-portrait.is-in.is-quiet"]
    assert quiet["filter"] == "brightness(0.42) saturate(0.7)" and quiet["transform"] == "translateY(18px) scale(0.97)"
    assert rules[".story-box.is-right::before"]["right"] == "110px"


def test_the_intro_beats_carry_page_dots_the_first_riddle_inset_and_skip_intro():
    stage = _ts("components/story-stage.ts")
    play, show = _function(stage, "play"), _function(stage, "show")
    assert "pips.hidden = beat.page === undefined" in show
    assert "riddle.hidden = beat.riddle === undefined" in show
    assert "skip.hidden = beat.page === undefined" in play
    assert "skip.textContent = strings.introSkip" in stage
    assert "skip.addEventListener('click', () => settle('skip'))" in stage
    # Each beat's line goes to the live region once, the first riddle's clue with it.
    assert "announce(`${NAMES[beat.speaker]}: ${beat.line}${beat.riddle === undefined ? '' : ` ${beat.riddle.heading}: ${beat.riddle.clue}`}`)" in play
    keys = _function(stage, "onKey")
    assert "event.target === next || event.target === skip" in keys


def test_the_guides_beat_lights_the_chest_through_the_scrim():
    stage = _ts("components/story-stage.ts")
    assert "element.classList.toggle('is-spotlit', beat.spot !== undefined)" in _function(stage, "play")
    # The hole sits on the chest, and the speech box ends 12 px short of it where the two would overlap.
    light = _function(stage, "light")
    assert "element.style.setProperty('--spot-x', `${lit.left + lit.width / 2 - stage.left}px`)" in light
    fit = _function(stage, "fit")
    assert "const covers = said.right > lit.left && said.left < lit.right" in fit
    assert "width: `${lit.left - 12 - said.left}px`" in fit
    rules = css_rules(_ts("components/story-stage.css"))
    assert "radial-gradient(" in rules[".story-stage.is-spotlit .story-scrim"]["mask-image"]
    assert rules[".treasure-chest.is-beckoning .chest"]["box-shadow"] == "0 0 0 1px var(--lamp), 0 0 30px #E9A94BA6"



def test_the_speech_box_keeps_one_place_on_all_five_intro_beats_so_next_never_moves():
    # Live replay, Oct 30: the box narrowed only on the Guide's beat, so Next jumped 73 px left. Every intro beat keeps
    # the box clear of the chest's box, measured at the first beat and held from beat to beat, and measured again only
    # when the chest moves (at intro start the first photo has not loaded, so the chest has no place yet).
    intro = _ts("story.ts").split("export async function playIntro(", 1)[1]
    assert "beats.play({ ...beat, page: { at, of: intro.length }, clear: chest.element })" in intro
    stage = _ts("components/story-stage.ts")
    fit = _function(stage, "fit")
    assert "if (clear !== clearing) {" in fit and "if (clear !== undefined) refit.observe(clear)" in fit
    assert "if (clear !== undefined && fitted === null) {" in fit
    assert "box.style.width = fitted?.width ?? ''" in fit
    assert "const refit = new ResizeObserver(() => {\n    fitted = null\n    fit(clearing)\n    reserve()\n  })" in stage
    play = _function(stage, "play")
    assert "fit(beat.clear)" in play and "unlight()" not in stage
    close = _function(stage, "close")
    assert "refit.disconnect()" in close and "fitted = null" in close
    # The chest's box runs from the chest to the frame's edge, so its width changes when the chest moves.
    assert css_rules(_ts("components/treasure-chest.css"))[".treasure-chest"]["right"] == "16px"

def test_the_intro_holds_the_box_at_its_tallest_beat_and_next_at_its_widest_label_so_neither_moves():
    # Live replay, Oct 30: on the last beat Next grew 61 px left for "Start looking" and the box rose 134 px for the
    # riddle inset. The intro hands the stage all five beats up front; the stage lays each out once at the box's held
    # width and keeps the tallest box and the widest button until it closes, laying them out again when the box refits.
    intro = _ts("story.ts").split("export async function playIntro(", 1)[1]
    assert intro.index("beats.hold(intro.map(({ beat }) => beat))") < intro.index("for (const [at, { beat, move }]")
    stage = _ts("components/story-stage.ts")
    assert "hold: (beats: StoryBeat[]) => void" in stage
    reserve = _function(stage, "reserve")
    assert "box.style.minHeight = ''" in reserve and "next.style.minWidth = ''" in reserve
    assert "for (const beat of held) {" in reserve and "show(beat)" in reserve
    assert "box.style.minHeight = `${tall}px`" in reserve and "next.style.minWidth = `${wide}px`" in reserve
    assert reserve.rstrip().endswith("if (shown !== undefined) show(shown)")
    play = _function(stage, "play")
    assert play.index("show(beat)") < play.index("element.hidden = false") < play.index("fit(beat.clear)")
    assert play.index("fit(beat.clear)") < play.index("reserve()")
    assert "reserved = false" in _function(stage, "fit")
    close = _function(stage, "close")
    assert "held = []" in close and "box.style.minHeight = next.style.minWidth = ''" in close
    # The held height goes above the line: the footer, and Next in it, stays on the box's bottom edge.
    rules = css_rules(_ts("components/story-stage.css"))
    assert rules[".story-box"]["display"] == "flex" and rules[".story-box"]["flex-direction"] == "column"
    assert rules[".story-foot"]["margin-top"] == "auto" and rules[".story-foot"]["padding-top"] == "14px"
    assert rules[".story-next"]["justify-content"] == "center"


def test_the_trap_seal_lands_in_the_middle_of_the_photo_above_the_held_box():
    # Review of the hold, Oct 30: the box held at beat 5's height rose over the middle of the photo at 1024x768 to
    # 1366x768 and hid up to half of beat 2's lock seal. The seal now lands midway between the photo's top and the box's
    # held top (its name plate's), which the stage reports; a resize of the Scene places it again.
    stage = _ts("components/story-stage.ts")
    assert "top: () => number" in stage and "top: () => plate.getBoundingClientRect().top" in stage
    assert "if (!skipped) scene.lockSeal(true, beats.top)" in _ts("story.ts")
    scene = _ts("scene/index.ts")
    assert "lockSeal: (on: boolean, above?: () => number) => void" in scene
    seal = _function(scene, "lockSeal")
    assert "sealAbove = above" in seal and seal.index("view.append(seal)") < seal.index("placeSeal()")
    place = _function(scene, "placeSeal")
    assert "if (seal === undefined || sealAbove === undefined) return" in place
    assert "const photo = view.getBoundingClientRect()" in place
    assert "const line = Math.max(photo.top, Math.min(photo.bottom, sealAbove()))" in place
    assert "seal.style.top = `${(line - photo.top) / 2}px`" in place
    assert "placeSeal()" in _function(scene, "render")
    # Without a line it stays on the middle of the photo.
    assert css_rules(_ts("scene/walk.css"))[".scene-seal"]["top"] == "50%"


# --- The intro on the Play screen ------------------------------------------------------------------------------------


def test_the_play_screen_plays_the_five_beats_once_per_session_and_the_welcome_card_is_retired():
    play = _ts("play.ts")
    assert "mountWelcome" not in play and not (WEB_SRC / "welcome.ts").exists()
    assert not (WEB_SRC / "components/greeting-overlay.ts").exists()
    begin = _function(play, "begin")
    assert begin.index("holdForIntro(true)") < begin.index("await playIntro(") < begin.index("holdForIntro(false)")
    assert begin.index("holdForIntro(false)") < begin.index("note.focus()")
    assert "let introducing = introDue(session)" in play and "introducing ? introPhoto(view)" in play
    story = _ts("story.ts")
    assert "const INTRO_KEY = 'kf.story.'" in story
    assert "sessionStorage.setItem(INTRO_KEY + sessionId, 'done')" in story
    assert "export function introDue(state: SessionState): boolean" in story
    intro = story.split("export async function playIntro(", 1)[1]
    for beat in ("speaker: 'architect'", "speaker: 'trickster'", "speaker: 'riddler'", "speaker: 'guide'"):
        assert beat in intro, beat
    assert "cast: { left: 'riddler', right: 'trickster' }" in intro and "cast: { right: 'trickster' }" in intro
    assert "button: strings.startLooking" in intro and "spot: chest.button" in intro
    # A returning player's Greeting (Local mode), as far as the poll has brought it, is the Guide's line.
    assert "introLines(view, first.id, opening?.kind === 'greeting' ? opening.text : null)" in intro
    assert intro.index("skipped = true") < intro.index("markIntroDone(shown.id)")


def test_the_trap_turns_to_the_way_out_and_slams_the_seal_which_lifts_on_the_first_riddle():
    intro = _ts("story.ts").split("export async function playIntro(", 1)[1]
    assert intro.index("await scene.walkTo(exit.start_photo, true)") < intro.index("scene.lockSeal(true, beats.top)")
    assert intro.index("scene.lockSeal(false)") < intro.index("await scene.walkTo(first.start_photo, true)")
    scene = _ts("scene/index.ts")
    # The beat's line is what is said: a walk under a beat announces no view.
    assert "async function walk(to: number, via?: HTMLElement, quiet = false): Promise<void> {" in scene
    assert "await arrive(to, !quiet)" in scene
    seal = _function(scene, "lockSeal")
    assert "world.animate(FLICKER, { duration: FLICKER_MS })" in seal and "if (reduced()) return" in seal
    assert "export const FLICKER_MS = 700" in scene
    walk = css_rules(_ts("scene/walk.css").split("@media (prefers-reduced-motion: reduce) {", 1)[0])
    assert walk[".scene-seal"]["width"] == "22%"
    assert walk[".scene-seal.is-slamming"]["animation"] == "scene-seal-slam 500ms cubic-bezier(0.3, 1.6, 0.5, 1) 260ms both"


def test_a_press_during_a_walk_is_held_until_the_walk_ends():
    loop = _ts("story.ts").split("for (const [at, { beat, move }] of intro.entries()) {", 1)[1]
    assert loop.index("const moved = move?.()") < loop.index("await beats.play(") < loop.index("await moved")
    # "Skip intro" waits for nothing: the stage closes and the Scene walks on to the first riddle; no seal lands late.
    assert loop.index("skipped = true") < loop.index("await moved")
    assert "if (!skipped) scene.lockSeal(true, beats.top)" in _ts("story.ts")
    assert "void scene.walkTo(first.start_photo)" in loop


def test_the_intro_holds_the_scene_and_the_top_bar_and_hides_the_play_parts_until_play_starts():
    play = _ts("play.ts")
    assert "stage.classList.toggle('is-intro', on)" in play
    rules = css_rules(_ts("components/story-stage.css"))
    hidden = rules[".scene-stage.is-intro :is(.riddle-note, .inventory, .walk-map, .walk-turn, .walk-door, .coach-pill)"]
    assert hidden == {"visibility": "hidden"}
    assert rules[".scene-stage.is-intro .treasure-chest:not(.is-shown)"] == {"visibility": "hidden"}
    assert "modalOpen: () => introducing || cardLog.isOpen()" in play


def test_every_intro_motion_is_off_under_reduced_motion():
    for name in ("components/story-stage.css", "scene/walk.css"):
        text = _ts(name)
        reduced = text.split("@media (prefers-reduced-motion: reduce) {", 1)[1]
        assert "animation: none" in reduced, name
    stage = _ts("components/story-stage.css").split("@media (prefers-reduced-motion: reduce) {", 1)[1]
    assert ".story-box.is-swapping" in stage and ".scene-seal.is-slamming" in _ts("scene/walk.css").split(
        "@media (prefers-reduced-motion: reduce) {", 1)[1]
    assert "typing" not in _code(_ts("components/story-stage.ts"))  # lines appear whole
