"""Story 7.16: the Hosted landing (FR-31, UX-DR57, UX-DR58, UX-DR68, UX-DR81, NFR-10), as a title screen: the hero
line, one primary verb, the cast of four, then the first Demo room's card, a page of the Riddler's notes and "How a
room is built" in three steps, beside the Access-code build.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The last checks run the hosted
app over plain dicts and a temporary Volume, so the three reads the landing makes, and the session start a card
sends, answer as the landing expects.
"""

import json
import re
import shutil
import subprocess
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest

from fastapi.testclient import TestClient

from src.api.meta import HOSTED_LINE
from src.domain.redact import to_play_view
from src.domain.schema import Derived, PlayView, Room
from tests.api.hosted import hosted_handles, make_hosted_app
from tests.domain.test_redact import done_job
from tests.infra.test_modal import seed_demo
from tests.web.design import REPO, WEB_SRC, css_custom_properties, css_rules, design_text
from tests.web.test_contrast import PROPS, _hex, contrast
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", _ts(name), flags=re.DOTALL)


def _render() -> str:
    return _code("shell.ts").split("async function render()", 1)[1].split("\n  }\n", 1)[0]


def _card_rules() -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / "components/demo-room-card.css").read_text())


def _landing_rules() -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / "landing.css").read_text())


# --- Cold load: GET /meta, then GET /rooms ---------------------------------------------


def test_hosted_home_reads_meta_then_rooms_and_shows_the_landing():
    render = _render()
    assert render.index("getMeta(place.profile)") < render.index("await listRooms().catch(() => null)")
    assert "} else if (place.route.name === 'home' && meta.mode === 'local') {" in render
    assert "} else if (place.route.name === 'home') {" in render
    assert "content = { name: 'landing', rooms, profile: place.profile, mode: meta.mode, onRetry: () => void render(), onAccepted }" in render
    # The banner and the top bar come from the same `GET /meta`, as on every surface.
    assert "const banner = disclosureBanner(disclosure)" in render and "const bar = topBar(meta, played)" in render
    shell = _code("shell.ts")
    assert "element.classList.add('landing-layout')" in shell
    assert "const landing = hostedLanding(content.rooms, content.profile, content.mode, content.onRetry, content.onAccepted)" in shell
    assert "element.append(...landing.children)" in shell and "mount: landing.mount" in shell


def test_the_landing_top_bar_has_no_timer_and_no_play_control():
    shell = _code("shell.ts")
    owner = shell.split("function timerOwner(", 1)[1].split("\n}\n", 1)[0]
    assert "if (route.name === 'home') return null" in owner
    # Only the Play and Completion surfaces fill the controls slot.
    landing = _code("landing.ts") + _code("components/demo-room-card.ts")
    assert "controls" not in landing and "mountTimer" not in landing and "timer" not in landing
    assert "if (meta.mode === 'hosted') return strings.modeHosted" in _ts("components/top-bar.ts")


def test_the_disclosure_banner_renders_the_served_hosted_line():
    assert "Hosted mode: hints are shown" not in _ts("landing.ts")
    assert HOSTED_LINE == "Hosted mode: hints are shown as written; no hint model runs here."
    assert "let disclosure = meta.disclosure" in _render()


# --- The hero, the primary verb and the cast ------------------------------------------


def test_the_landing_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["wordmark"] == "Keyframe"
    assert strings["landingSubtitle"] == "An escape room built from your own photos."
    assert strings["landingTagline"] == "Six photos of one room go in. Five locks, four wizards and one way out come back."
    assert strings["playSampleRoom"] == "Play the sample room"
    assert strings["sampleRoomSoon"] == "The sample room opens soon."
    assert strings["howARoomIsBuilt"] == "How a room is built"
    assert strings["theWizards"] == "The wizards"
    roles = [strings[key] for key in ("architectCastRole", "riddlerCastRole", "guideCastRole", "tricksterCastRole")]
    assert roles == ["Finds the objects", "Writes the locks", "Hints, never answers", "Changes the rules"]
    assert all(len(role.split()) <= 4 for role in roles)
    assert strings["riddlersNotes"] == "From the Riddler's notes"
    assert strings["howArchitect"] == "reads your photos with muse-spark-1.3 and outlines every object with sam-3.1."
    assert strings["howRiddler"] == (
        "writes five locks from what was found; a test run that never sees the answers checks each one opens.")
    assert strings["howGuide"] == "hands out hints one rung at a time."
    assert strings["howTrickster"] == "changes the room between locks, if the Validator lets him."
    assert strings["demoRoomMeta"].format(n=5) == "5 puzzles · 15 to 25 min"
    assert strings["demoRoomPortraits"] == "The Architect, the Riddler, the Guide and the Trickster"
    assert strings["demoRoomsFailed"] == "Keyframe couldn't load the demo rooms."
    assert strings["howBuilt"] == "How this room was built" and strings["tryAgain"] == "Try again"
    # The hero names no model and the no-demo-rooms sentence is gone for good.
    for key in ("landingSubtitle", "landingTagline", "sampleRoomSoon"):
        assert "muse" not in strings[key] and "sam-" not in strings[key] and "Llama" not in strings[key]
    assert not any("No demo rooms are open" in value for value in strings.values())
    assert "pipelineLine" not in strings and "landingLeadIn" not in strings and "noDemoRooms" not in strings


def test_the_hero_holds_the_display_lg_line_the_tagline_the_verb_and_the_build_view_link():
    ts = _code("landing.ts")
    hero = ts.split("function hero(", 1)[1].split("\n}\n", 1)[0]
    assert "title.className = 'landing-heading display-lg'" in hero and "title.textContent = strings.landingSubtitle" in hero
    assert "paragraph('landing-line body-md', strings.landingTagline)" in hero
    assert "if (soon) words.append(paragraph('landing-note body-md', strings.sampleRoomSoon))" in hero
    assert "actions.append(verb)" in hero
    # "How a room is built" (secondary) opens the first Demo room's Build view; absent without one and under cut 0.
    assert "if (first !== undefined && !CUT_0) {" in hero
    guarded = hero.split("if (first !== undefined && !CUT_0) {", 1)[1]
    assert "secondaryLink({ label: strings.howARoomIsBuilt, href: buildViewHref(first.job_id, profile) })" in guarded
    assert "strings.pipelineLine" not in ts and "strings.landingLeadIn" not in ts and "strings.noDemoRooms" not in ts
    rules = _landing_rules()
    assert rules[".landing-heading"]["color"] == "var(--text)"
    assert rules[".landing-line"]["color"] == "var(--text-muted)"
    assert rules[".landing-hero-words"]["max-width"] == "60ch"


def test_with_a_demo_room_the_verb_plays_the_sample_room_through_the_card_s_own_start():
    ts = _code("landing.ts")
    assert "const start = roomStarter(profile, mode, banners)" in ts
    verb = ts.split("function primaryVerb(", 1)[1].split("\n}\n", 1)[0]
    assert "primaryButton({ label: strings.playSampleRoom, pendingLabel: strings.playSampleRoom, onActivate: () => start(first) })" in verb
    assert "demoRoomCard(first, profile, () => void start(first))" in ts  # the same start the card uses


def test_with_no_demo_room_the_verb_is_build_your_own_room_and_moves_focus_to_the_access_code_field():
    ts = _code("landing.ts")
    verb = ts.split("function primaryVerb(", 1)[1].split("\n}\n", 1)[0]
    assert "if (first === undefined) {" in verb
    none = verb.split("if (first === undefined) {", 1)[1].split("\n  }\n", 1)[0]
    assert "label: strings.buildYourOwnRoom" in none and "pendingLabel: strings.buildYourOwnRoom" in none
    assert "field()?.focus()" in none
    assert "`#${ACCESS_CODE_FIELD}`" in ts and "export const ACCESS_CODE_FIELD = 'access-code'" in _code("components/access-code-build.ts")
    assert "field.id = ACCESS_CODE_FIELD" in _code("components/access-code-build.ts")


def test_the_cast_is_the_four_96px_portraits_with_name_four_word_role_and_voice_line_on_hover_and_focus():
    ts = _code("landing.ts")
    cast = ts.split("function cast(", 1)[1].split("\n}\n", 1)[0]
    assert "list.setAttribute('aria-label', strings.theWizards)" in cast
    assert "wizardPortrait(wizard, 96)" in cast
    assert "item.tabIndex = 0" in cast  # each wizard is keyboard reachable, so its voice line shows on focus
    for wizard, role, voice in (("architect", "architectCastRole", "architectVoice"), ("riddler", "riddlerCastRole", "riddlerVoice"),
                                ("guide", "guideCastRole", "guideVoice"), ("trickster", "tricksterCastRole", "tricksterVoice")):
        assert f"wizard: '{wizard}', name: strings.{wizard}, role: strings.{role}, voice: strings.{voice}" in ts
    rules = _landing_rules()
    wizard = rules[".landing-wizard"]
    assert wizard["grid-template-columns"] == "96px minmax(0, 1fr)" and wizard["border-radius"] == "var(--rounded-lg)"
    # The name and the voice line share one cell: the line fades in where the name was, nothing moves or slides.
    who = rules[".landing-wizard-who,\n.landing-wizard-voice"]
    assert who["grid-column"] == "2" and who["grid-row"] == "1"
    assert who["transition"] == "opacity var(--motion-hover) var(--motion-ease)"
    assert rules[".landing-wizard-voice"]["opacity"] == "0"
    assert rules[".landing-wizard:hover .landing-wizard-voice,\n.landing-wizard:focus-visible .landing-wizard-voice"]["opacity"] == "1"
    assert rules[".landing-wizard:hover .landing-wizard-who,\n.landing-wizard:focus-visible .landing-wizard-who"]["opacity"] == "0"
    # Hover lifts the row to chrome with the lamp glow and turns the ring lamp; the focus ring keeps its inner ring.
    assert rules[".landing-wizard:hover"] == {"background-color": "var(--chrome)", "box-shadow": "var(--elevation-lamp-glow)"}
    assert rules[".landing-wizard:hover:focus-visible"]["box-shadow"].startswith("0 0 0 2px var(--focus-ring-inner)")
    assert rules[".landing-wizard:hover .wizard-portrait,\n.landing-wizard:focus-visible .wizard-portrait"] == {"border-color": "var(--lamp)"}
    # Two across, four from 1440 px (css_rules flattens media blocks, so the raw text is read for both).
    text = _ts("landing.css")
    assert ".landing-cast {\n  display: grid;\n  grid-template-columns: repeat(2, minmax(0, 1fr));" in text
    assert "@media (min-width: 1440px) {\n  .landing-cast {\n    grid-template-columns: repeat(4, minmax(0, 1fr));" in text


def test_the_riddlers_sample_page_shows_the_first_waiting_free_puzzle_from_the_play_view():
    ts = _code("landing.ts")
    notes = ts.split("function riddlersNotes(", 1)[1].split("\n}\n", 1)[0]
    assert "view.puzzles.find((puzzle) => puzzle.requires.length === 0)" in notes
    assert "sheet.setAttribute('aria-label', strings.riddlersNotes)" in notes
    assert "fill(strings.puzzleHeading, { n: view.puzzles.indexOf(puzzle) + 1 })" in notes
    assert "evidenceCard(view.id, interactable, card)" in notes
    assert "wizardPortrait('riddler', 32)" in notes and "speakerPrefix('riddler'), puzzle.clue" in notes
    assert "paragraph('landing-notes-lore lore', speakerPrefix('riddler'), puzzle.lore)" in notes
    assert "strings.current" not in ts  # the Active puzzle marker is never guessed; no Session is open
    # Read through the existing redaction view, which holds no solution and no Derived field.
    assert "getRoom(first.room_id).then(" in ts
    assert "return getJson<PlayView>(`/rooms/${encodeURIComponent(roomId)}`)" in _ts("api/index.ts")
    rules = _landing_rules()
    sheet = rules[".landing-notes"]
    assert sheet["background"] == "var(--parchment)" and sheet["color"] == "var(--ink)" and sheet["box-shadow"] == "var(--elevation-paper)"
    assert rules[".landing-notes-clue"]["grid-template-columns"] == "32px minmax(0, 1fr)"
    assert rules[".landing-notes-lore"]["color"] == "var(--ink-muted)"


def test_how_a_room_is_built_is_three_steps_naming_the_wizards_and_the_models():
    ts = _code("landing.ts")
    how = ts.split("function howARoomIsBuilt(", 1)[1].split("\n}\n", 1)[0]
    assert "heading.textContent = strings.howARoomIsBuilt" in how
    steps = ts.split("const STEPS: readonly (readonly string[])[] = [", 1)[1].split("\n]\n", 1)[0]
    assert "[strings.architect, strings.howArchitect]" in steps
    assert "[strings.riddler, strings.howRiddler]" in steps
    assert "[strings.guide, strings.howGuide, strings.trickster, strings.howTrickster]" in steps
    assert "step.className = 'landing-how-step body-sm'" in how and "STEPS.forEach(" in how
    rules = _landing_rules()
    assert rules[".landing-how-n"]["color"] == "var(--lamp)"


# --- Two states: a Demo room listed, or none ------------------------------------------


def test_with_a_demo_room_listed_the_card_the_sample_page_and_the_steps_sit_in_a_row_under_the_cast():
    ts = _code("landing.ts")
    assert "left.append(hero(first, profile, verb, rooms !== null && rooms.length === 0), attract, cast())" in ts
    listed = ts.split("const below = document.createElement('div')", 1)[1]
    assert "below.className = 'landing-below'" in listed
    assert "below.append(sample, notes, howARoomIsBuilt())" in listed
    # Further Demo rooms keep their cards three across under the row, in served order.
    assert "rooms.slice(1).map((room) => demoRoomCard(room, profile, () => void start(room)))" in listed
    rules = _landing_rules()
    text = _ts("landing.css")
    assert ".landing-below {\n  display: grid;\n  grid-template-columns: repeat(3, minmax(0, 1fr));" in text
    assert "@media (max-width: 1279px) {\n  .landing-below {\n    grid-template-columns: repeat(2, minmax(0, 1fr));" in text
    assert rules[".landing-below > .demo-room-list"]["grid-template-columns"] == "minmax(0, 1fr)"
    assert rules[".landing-notes-slot"]["display"] == "contents"


def test_with_no_demo_room_the_cast_and_the_hero_stay_and_no_no_demo_rooms_line_shows():
    ts = _code("landing.ts")
    empty = ts.split("if (first === undefined) {", 2)[2].split("\n  }\n", 1)[0]  # after the verb's own branch
    assert "children: [left, right]" in empty and "demoRoomCard" not in empty and "howARoomIsBuilt" in empty
    assert "landing-state" not in empty  # no plain line in place of the cards
    assert "No demo rooms" not in _ts("landing.ts") and "No demo rooms" not in _ts("strings.ts")


def test_initial_focus_is_on_the_primary_verb_the_first_tab_stop_after_the_top_bar():
    ts = _code("landing.ts")
    assert ts.count("verb.focus()") == 2  # the listed and the empty states; the failed state focuses "Try again"
    # The verb comes before the cast and the row in the left area, which comes before the right column.
    assert ts.index("left.append(hero(") < ts.index("left.append(below")
    assert "tabIndex" not in _code("components/top-bar.ts")  # the top bar has no Tab stop on the landing


# --- The attract frame: the Demo room plays itself above the fold ----------------------


def _attract() -> str:
    return _code("components/attract-frame.ts")


def _attract_rules() -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / "components/attract-frame.css").read_text())


def test_the_attract_frame_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["attractFrame"] == "Play {name}"
    assert strings["lockOfM"].format(n=1, m=5) == "Lock 1 of 5"


# Runs the shipped `attractSlides` on the PlayViews read from stdin and prints the slides it returns.
SLIDES_RUNNER = """
import { readFileSync } from 'node:fs'
const { attractSlides } = await import(process.argv[1])
const views = JSON.parse(readFileSync(0, 'utf8'))
process.stdout.write(JSON.stringify(views.map((view) => attractSlides(view))))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's attract slides module")


def _slides(*views: PlayView) -> list[list[dict[str, Any]]]:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", SLIDES_RUNNER, (WEB_SRC / "components/attract-slides.ts").as_uri()],
        input=json.dumps([view.model_dump(mode="json") for view in views]), cwd=REPO, capture_output=True, text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _front_hall() -> PlayView:
    """Shaped like the Demo room "The front hall and the lounge": eight photos, every lock's object on its own photo."""
    def ix(n: int, label: str, photo: int) -> dict[str, Any]:
        square = [[100 * n, 100], [100 * n + 80, 100], [100 * n + 80, 180], [100 * n, 180]]
        return {"id": f"ix_{n:026d}", "label": label, "photo": photo, "polygons": [square], "instances": 1, "attributes": []}

    def pz(n: int, lock_type: str, evidence: int, is_exit: bool = False) -> dict[str, Any]:
        return {
            "id": f"pz_{n:026d}", "lock_type": lock_type, "requires": [], "is_exit": is_exit, "clue": f"clue {n}",
            "lore": "", "evidence_cards": [{"interactable": f"ix_{evidence:026d}", "visible_attribute": "seen"}],
            "sequence_length": None,
        }

    return PlayView.model_validate({
        "id": f"room_{1:026d}", "created": "2026-10-29T12:00:00Z", "name": "The front hall and the lounge",
        "photos": [{"hash": f"{n:064x}", "size": 1} for n in range(8)],
        "interactables": [
            ix(1, "entryway rug", 0), ix(2, "floor vent", 0), ix(3, "ceiling light", 0), ix(4, "double front door", 1),
            ix(5, "throw pillows", 2), ix(6, "potted tree", 3), ix(7, "sectional sofa", 5),
        ],
        "puzzles": [pz(1, "find", 5), pz(2, "find", 2), pz(3, "use_on", 7), pz(4, "find", 4, is_exit=True)],
    })


def _assert_spoils_nothing(view: PlayView, slides: list[dict[str, Any]]) -> None:
    """No lit Interactable is named by an Evidence card, and no photo's clue has its Evidence on that photo."""
    photo_of = {interactable.id: interactable.photo for interactable in view.interactables}
    named = {card.interactable for puzzle in view.puzzles for card in puzzle.evidence_cards}
    assert [slide["photo"] for slide in slides] == list(range(len(view.photos)))
    for slide in slides:
        if slide["interactable"] is not None:
            assert slide["interactable"]["id"] not in named, slide
        if slide["puzzle"] is not None:
            assert all(photo_of[card["interactable"]] != slide["photo"] for card in slide["puzzle"]["evidence_cards"]), slide


@needs_node
def test_the_frame_never_lights_a_lock_s_object_or_pairs_a_clue_with_the_photo_that_holds_its_answer(four_lock_room: Room):
    hall, four_lock = _front_hall(), to_play_view(four_lock_room)
    hall_slides, four_lock_slides = _slides(hall, four_lock)
    _assert_spoils_nothing(hall, hall_slides)
    _assert_spoils_nothing(four_lock, four_lock_slides)
    # Scenery is lit where a photo has it (the rug, the tree); a photo holding only a lock's object shows no outline.
    lit = [slide["interactable"] and slide["interactable"]["label"] for slide in hall_slides]
    assert lit == ["entryway rug", None, None, "potted tree", None, None, None, None]
    assert [slide["interactable"] and slide["interactable"]["label"] for slide in four_lock_slides] == [
        None, None, None, "iron lantern", None, "woven rug",
    ]
    # Every photo has a clue, never the Exit's while another lock's is eligible, and successive photos show different ones.
    clues = [slide["puzzle"]["clue"] for slide in hall_slides]
    assert "clue 4" not in clues and all(a != b for a, b in pairwise(clues)), clues
    four_lock_clues = [slide["puzzle"]["clue"] for slide in four_lock_slides]
    assert all(a != b for a, b in pairwise(four_lock_clues)), four_lock_clues
    assert not any(slide["puzzle"]["is_exit"] for slide in four_lock_slides)


@needs_node
def test_a_photo_holding_every_lock_s_evidence_shows_no_clue_and_the_exit_s_clue_is_the_last_choice():
    hall = _front_hall()

    def moved(door_photo: int) -> PlayView:
        """Two photos: every object on photo 0 but the front door, which is on `door_photo`."""
        interactables = [
            ix.model_copy(update={"photo": door_photo if ix.label == "double front door" else 0}) for ix in hall.interactables
        ]
        return hall.model_copy(update={"photos": hall.photos[:2], "interactables": interactables})

    crowded, exit_left = _slides(moved(0), moved(1))
    # Photo 0 holds every lock's object: no clue; photo 1 holds none, so its clue is a lock's, not the Exit's.
    assert crowded[0]["puzzle"] is None and crowded[0]["interactable"]["label"] == "entryway rug"
    assert crowded[1]["puzzle"] is not None and crowded[1]["puzzle"]["is_exit"] is False
    # Photo 0 holds every lock's object but the Exit's, so the Exit's clue is the only one it may show.
    assert exit_left[0]["puzzle"]["is_exit"] is True and exit_left[1]["puzzle"]["is_exit"] is False


def test_the_frame_reads_the_play_view_alone():
    ts = _code("components/attract-slides.ts") + _attract()
    # Drawn from the PlayView alone: the modules name no solution, rung or Derived field, and never a box.
    assert "solution" not in ts and "rung" not in ts and "derived" not in ts.lower() and ".box" not in ts
    assert "import type { PlayInteractable, PlayPuzzle, PlayView } from '../../types'" in _code("components/attract-slides.ts")
    assert "import { attractSlides, type AttractSlide } from './attract-slides.ts'" in _attract()


def test_the_frame_draws_the_scene_s_hotspot_reveal_and_label_chip_over_each_photo():
    ts = _attract()
    assert "hotspotReveal(hotspotPath(interactable.polygons ?? []))" in ts
    assert "svg.setAttribute('class', 'scene-hotspots')" in ts and "svg.setAttribute('preserveAspectRatio', 'none')" in ts
    assert "slide.svg?.setAttribute('viewBox', `0 0 ${slide.size.width} ${slide.size.height}`)" in ts  # the photo's pixel space
    assert "chip.className = 'hotspot-label-chip label is-shown'" in ts and "chip.textContent = interactable.label" in ts
    hotspots = _code("scene/hotspots.ts")
    assert "export function hotspotReveal(d: string): SVGGElement" in hotspots
    assert "reveal.append(path('hotspot-glow', d), path('hotspot-halo', d), path('hotspot-outline', d))" in hotspots
    rules = _attract_rules()
    assert rules[".attract-frame .hotspot-reveal"] == {"opacity": "1"}  # lit, as the Scene lights a hovered Hotspot
    assert "import '../scene/scene.css'" in _ts("components/attract-frame.ts")


def test_the_clue_sits_on_parchment_under_the_frame_with_the_lock_tag():
    ts = _attract()
    assert "wizardPortrait('riddler', 32)" in ts and "speakerPrefix('riddler'), puzzle.clue" in ts
    assert "fill(strings.lockOfM, { n: view.puzzles.indexOf(puzzle) + 1, m: view.puzzles.length })" in ts
    assert "tag.className = 'chip chip-current label'" in ts
    rules = _attract_rules()
    clue = rules[".attract-clue"]
    assert clue["background"] == "var(--parchment)" and clue["color"] == "var(--ink)" and clue["box-shadow"] == "var(--elevation-paper)"
    assert rules[".chip-current"] == {"border": "1px solid var(--lamp-ink)", "color": "var(--lamp-ink)"}


def test_the_photos_crossfade_on_the_attract_token_about_every_four_seconds_and_pause_on_hover_focus_and_a_hidden_tab():
    ts = _attract()
    assert "export const HOLD_MS = 4000" in ts
    assert "timer = setTimeout(() => void next(), HOLD_MS)" in ts
    assert "if (reduced || hovered || focused || document.hidden || slides.length < 2) return" in ts
    assert "const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches" in ts
    for event in ("pointerenter", "pointerleave", "focusin", "focusout"):
        assert f"frame.addEventListener('{event}'" in ts, event
    assert "document.addEventListener('visibilitychange', schedule)" in ts
    assert "document.removeEventListener('visibilitychange', schedule)" in ts
    props = css_custom_properties()
    assert props["motion-attract"] == "600ms"
    tokens = (WEB_SRC / "tokens.css").read_text()
    assert "--motion-attract: 0ms;" in tokens.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    rules = _attract_rules()
    assert rules[".attract-slide"]["opacity"] == "0" and rules[".attract-slide"]["transition"] == "opacity var(--motion-attract) var(--motion-ease)"
    assert rules[".attract-slide.is-shown"] == {"opacity": "1"}
    assert "@keyframes" not in (WEB_SRC / "components/attract-frame.css").read_text()


def test_the_photos_load_lazily_and_the_frame_is_skipped_without_a_first_photo():
    ts = _attract()
    assert "if (slides.length === 0) return null" in ts
    assert "const first = await load(0).catch(() => null)" in ts and "if (first === null) return null" in ts
    # One photo ahead, never all at once: the next slide is asked for once the current one shows.
    assert "void load((index + 1) % slides.length).catch(() => undefined)" in ts
    landing = _code("landing.ts")
    assert "attractFrame(view, roomTitle(first), () => void start(first)).then(" in landing
    assert "playing = frame\n              attract.replaceChildren(frame.element)" in landing
    assert "if (!mounted) {\n                frame.unmount()" in landing  # a frame that answers after the landing left
    assert "playing?.unmount()" in landing.split("return () => {", 1)[1]
    assert "attract.className = 'landing-attract-slot'" in landing
    assert _landing_rules()[".landing-attract-slot"]["display"] == "contents"


def test_the_frame_is_one_focusable_control_named_for_the_room_that_starts_a_session_on_click_or_enter():
    ts = _attract()
    assert "frame.setAttribute('role', 'button')" in ts and "frame.tabIndex = 0" in ts
    assert "frame.setAttribute('aria-label', fill(strings.attractFrame, { name }))" in ts
    assert "frame.addEventListener('click', onStart)" in ts
    assert "if (event.key === 'Enter' && event.target === frame) onStart()" in ts
    assert "img.alt = ''" in ts  # the photos are decorative under the one accessible name
    landing = _code("landing.ts")
    assert "left.append(hero(first, profile, verb, rooms !== null && rooms.length === 0), attract, cast())" in landing
    rules = _attract_rules()
    frame = rules[".attract-frame"]
    assert frame["cursor"] == "pointer"
    assert rules[".attract-frame:hover"]["border-color"] == "var(--lamp)"
    assert rules[".attract-frame:hover:focus-visible"]["box-shadow"].startswith("0 0 0 2px var(--focus-ring-inner)")


def test_the_contract_records_the_attract_frame_and_the_motion_carve_out():
    experience = (REPO / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md").read_text()
    design = design_text()
    assert "attract frame" in experience and "attract frame" in design
    motion = design.split("**Motion.**", 1)[1].split("\n\n", 1)[0]
    assert "600 ms" in motion and "4 s" in motion and "reduced motion" in motion
    assert "Nothing loops" in motion and "attract frame" in motion


# --- Layout: cards three across beside the 400 px right column -----------------------


def test_cards_sit_three_across_in_the_left_area_beside_the_right_column():
    rules = _landing_rules()
    layout = rules[".landing-layout"]
    assert layout["grid-template-columns"] in {"minmax(0, 1fr) var(--spacing-side-column)", "minmax(0, 1fr) 340px"}
    assert layout["padding"] == "var(--spacing-frame-margin)" and layout["column-gap"] == "var(--spacing-column-gap)"
    text = (WEB_SRC / "landing.css").read_text()
    assert "@media (max-width: 1439px) {\n  .landing-layout {\n    grid-template-columns: minmax(0, 1fr) 360px;" in text
    assert "@media (max-width: 1279px) {\n  .landing-layout {\n    grid-template-columns: minmax(0, 1fr) 340px;" in text
    assert _card_rules()[".demo-room-list"]["grid-template-columns"] == "repeat(3, minmax(0, 1fr))"
    ts = _code("landing.ts")
    assert "left.append(banners)" in ts and "left.append(below" in ts
    assert "right.className = 'landing-right'" in ts and "children: [left, right]" in ts
    assert not re.search(r"\.sort\(|\.reverse\(|\.filter\(", ts), "the cards keep the served order"


# --- The Demo room card ----------------------------------------------------------------


def test_a_card_shows_the_cover_the_name_the_meta_line_and_the_four_portraits_under_one_name():
    ts = _code("components/demo-room-card.ts")
    assert "cover.src = photoUrl(room.room_id, room.cover_photo)" in ts and "cover.alt = ''" in ts
    assert "title.className = 'demo-room-title display-sm'" in ts and "title.textContent = roomTitle(room)" in ts
    assert "return room.name || buildTime(room.built_at)" in _ts("components/stored-room-row.ts")
    assert "meta.className = 'demo-room-meta body-sm'" in ts
    assert "meta.textContent = fill(strings.demoRoomMeta, { n: room.puzzle_count })" in ts
    assert "const WIZARDS: readonly Wizard[] = ['architect', 'riddler', 'guide', 'trickster']" in ts
    assert "portraits.append(...WIZARDS.map((wizard) => wizardPortrait(wizard, 24)))" in ts
    assert "portraits.setAttribute('role', 'img')" in ts
    assert "portraits.setAttribute('aria-label', strings.demoRoomPortraits)" in ts
    cover = _card_rules()[".demo-room-cover"]
    assert cover["aspect-ratio"] == "4 / 3" and cover["object-fit"] == "cover"
    assert cover["border-radius"].startswith("calc(var(--rounded-lg)")


def test_the_footer_holds_the_decorative_96px_thumbnail_and_the_build_view_link():
    ts = _code("components/demo-room-card.ts")
    assert "const link = buildViewLink(room.job_id, profile)" in ts
    assert "if (link !== null) footer.prepend(buildThumbnail(view, room.cover_photo))" in ts
    assert "thumb.setAttribute('aria-hidden', 'true')" in ts and "image.alt = ''" in ts
    thumb = _card_rules()[".demo-room-thumb"]
    assert (thumb["width"], thumb["height"]) == ("96px", "72px")
    # The cover's masks and the puzzle graph, drawn as the Build view draws them, from the BuildView alone.
    assert "view.photos.find(({ photo }) => photo === coverPhoto)?.masks ?? []" in ts
    assert "hotspotPath(polygons)" in ts and "layoutGraph(view.puzzles, GRAPH_WIDTH)" in ts
    assert "graphEdges(view.puzzles, layout)" in ts
    assert "export function buildThumbnail(view: BuildView, coverPhoto: number): HTMLElement" in ts


def test_the_thumbnail_comes_from_the_build_view_and_a_failed_read_leaves_the_card_working():
    ts = _code("landing.ts")
    assert "getBuildView(room.job_id).then(" in ts
    assert "if (mounted) cards[index].showThumbnail(view)" in ts
    assert "() => undefined," in ts  # a failed read draws nothing; the card keeps its start handler
    assert "if (!CUT_0) {" in ts.split("mount: () => {", 1)[1]
    assert "return getJson<BuildView>(`/builds/${encodeURIComponent(jobId)}/view`)" in _ts("api/index.ts")


def test_under_cut_0_the_card_has_no_link_no_thumbnail_and_still_starts_sessions():
    ts = _code("components/demo-room-card.ts")
    assert "if (CUT_0) return null" in _ts("build-view.ts")
    assert "if (link !== null) {\n    footer.append(link)\n    card.append(footer)\n  }" in ts
    assert "card.addEventListener('click'" in ts.split("if (link !== null) {", 1)[1]  # outside the cut-0 branch


def test_hover_rings_the_card_in_lamp_with_the_glow_and_keeps_the_focus_ring():
    rules = _card_rules()
    card = rules[".demo-room-card"]
    assert card["background"] == "var(--chrome-raised)" and card["border-radius"] == "var(--rounded-lg)"
    assert card["border"] == "2px solid transparent"
    assert card["transition"] == ("border-color var(--motion-hover) var(--motion-ease), "
                                  "box-shadow var(--motion-hover) var(--motion-ease)")
    assert rules[".demo-room-card:hover"] == {"border-color": "var(--lamp)", "box-shadow": "var(--elevation-lamp-glow)"}
    assert rules[".demo-room-card:hover:focus-visible"] == {
        "box-shadow": "0 0 0 2px var(--focus-ring-inner), var(--elevation-lamp-glow)"}
    # The card and the link are separate Tab stops, each keeping the global two-tone ring.
    ts = _code("components/demo-room-card.ts")
    assert "card.tabIndex = 0" in ts and "card.setAttribute('aria-labelledby', title.id)" in ts
    assert not any("outline" in prop for rule in rules.values() for prop in rule)


def test_hover_and_state_fades_are_instant_under_reduced_motion():
    for path in ("components/demo-room-card.css", "components/attract-frame.css", "landing.css"):
        for selector, declarations in css_rules((WEB_SRC / path).read_text()).items():
            for value in (v for k, v in declarations.items() if k.startswith("transition")):
                assert re.fullmatch(r"(?:[\w-]+ var\(--motion-\w+\) var\(--motion-ease\),? ?)+", value), (path, selector)


# --- Starting a Session from a card -----------------------------------------------------


def test_click_or_enter_on_the_card_starts_a_session_and_the_link_does_not():
    ts = _code("components/demo-room-card.ts")
    click = ts.split("card.addEventListener('click', (event) => {", 1)[1].split("})", 1)[0]
    assert "event.target.closest('a') !== null) return" in click and "onStart()" in click
    assert "if (event.key === 'Enter' && event.target === card) onStart()" in ts
    landing = _code("landing.ts")
    assert "const start = roomStarter(profile, mode, banners)" in landing
    assert "demoRoomCard(room, profile, () => void start(room))" in landing


def test_the_start_sends_the_fresh_derived_block_and_a_refusal_shows_the_banner_at_the_top_of_the_left_area():
    starter = _code("stored-rooms.ts").split("export function roomStarter(", 1)[1].split("\n}\n", 1)[0]
    assert "await startSession(await sessionStart(room.room_id, profile, mode))" in starter
    assert "location.hash = placeHref({ route: { name: 'play', sessionId: session.id }, profile })" in starter
    refused = starter.split("} catch {", 1)[1].split("} finally {", 1)[0]
    assert "heading: strings.sessionStartRefused" in refused and "sentence: strings.sessionStartRefusedBody" in refused
    assert "actions: [{ label: strings.tryAgain, onActivate: () => void start(room) }]" in refused
    landing = _code("landing.ts")
    assert "const banners = bannerSlot()" in landing
    assert landing.index("left.append(banners)") < landing.index("left.append(hero(")
    assert "element.focus()" in _ts("components/error-banner.ts")  # the banner takes focus


# --- Failed and empty lists -------------------------------------------------------------


def test_a_failed_list_shows_the_failed_line_with_try_again_in_place_of_the_cards():
    ts = _code("landing.ts")
    failed = ts.split("if (rooms === null) {", 1)[1].split("\n  }\n", 1)[0]
    assert "paragraph('body-md', strings.demoRoomsFailed)" in failed
    assert "secondaryButton({ label: strings.tryAgain, onActivate: onRetry })" in failed
    assert "children: [left, right]" in failed  # the hero, the cast and the right column stay
    assert "demoRoomCard" not in failed and "retry.focus()" in failed
    assert "await listRooms().catch(() => null)" in _render()  # never the unreachable strip


# --- Platform: contrast and the narrow screen -------------------------------------------


def test_every_landing_text_pair_meets_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "canvas"), ("text-muted", "canvas"), ("text", "chrome"), ("text-muted", "chrome"),
             ("text", "chrome-raised"), ("text-muted", "chrome-raised"),
             ("lamp", "chrome-raised"), ("error-text", "error-surface"), ("text", "error-surface"),
             ("lamp", "error-surface"), ("disclosure-text", "disclosure-surface")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    # The title block's link sits on the canvas, darker than the chrome the table's "links on dark" row measures.
    canvas = _hex(PROPS["canvas"])[0]
    assert contrast(_hex(PROPS["lamp"])[0], canvas) >= contrast(_hex(PROPS["lamp"])[0], _hex(PROPS["chrome"])[0]) >= 4.5
    for bg in ("canvas", "chrome-raised"):
        assert contrast(_hex(PROPS["focus-ring"])[0], _hex(PROPS[bg])[0]) >= 3


def test_below_1024px_the_narrow_screen_message_replaces_the_landing():
    css = (WEB_SRC / "shell.css").read_text()
    assert "@media (max-width: 1023px) {\n  #app {\n    display: none;" in css
    assert "root.after(narrowScreenMessage())" in _ts("shell.ts")


# --- The reads the landing makes, against the hosted app --------------------------------


def test_the_hosted_app_answers_each_read_the_landing_makes_and_a_card_start_opens_the_demo_welcome(
    tmp_path: Path, code_and_find_room: Room
):
    handles = hosted_handles(tmp_path)
    demo = code_and_find_room.model_copy(update={"name": "The Reading Room"})
    job = done_job(demo)
    seed_demo(handles, demo, job)
    client = TestClient(make_hosted_app(tmp_path, handles))

    meta = client.get("/api/meta").json()
    assert meta["mode"] == "hosted" and HOSTED_LINE in meta["disclosure"]
    [summary] = client.get("/api/rooms").json()
    assert summary == {"room_id": demo.id, "name": "The Reading Room", "cover_photo": summary["cover_photo"],
                       "puzzle_count": len(demo.puzzles), "job_id": job.id, "built_at": summary["built_at"]}
    assert client.get(f"/api/rooms/{demo.id}/photos/{summary['cover_photo']}").status_code == 200
    page = client.get(f"/api/rooms/{demo.id}").json()  # the Riddler's sample page: the PlayView, no solution
    free = next(puzzle for puzzle in page["puzzles"] if puzzle["requires"] == [])
    assert set(free) >= {"clue", "lore", "evidence_cards"} and "solution" not in free and "derived" not in page
    view = client.get(f"/api/builds/{summary['job_id']}/view").json()
    assert [puzzle["id"] for puzzle in view["puzzles"]] == [puzzle.id for puzzle in demo.puzzles]
    assert any(photo["photo"] == summary["cover_photo"] for photo in view["photos"])
    started = client.post("/api/sessions", json={"room_id": summary["room_id"], "derived": Derived.fresh().model_dump(mode="json")})
    assert started.status_code == 200
    assert started.json()["opening_line"] == {"kind": "welcome", "text": "Welcome to someone else's room. Find what doesn't belong."}


def test_the_hosted_app_with_no_demo_room_answers_an_empty_list_so_the_landing_shows_its_second_state(tmp_path: Path):
    client = TestClient(make_hosted_app(tmp_path, hosted_handles(tmp_path)))
    assert client.get("/api/meta").json()["mode"] == "hosted"
    assert client.get("/api/rooms").json() == []
