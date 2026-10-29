"""Story 7.16: the Hosted landing (FR-31, UX-DR57, UX-DR58, UX-DR68, UX-DR81, NFR-10). Owner decision Oct 29: the
hero-select chooser fills the first screen (test_chooser.py); below the fold, in the same scroll, the cast of four, a
page of the Riddler's notes and "How a room is built" in three steps, then any further Demo room cards.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The last checks run the hosted
app over plain dicts and a temporary Volume, so the three reads the landing makes, and the session start a card
sends, answer as the landing expects.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.meta import HOSTED_LINE
from src.domain.schema import Derived, Room
from tests.api.hosted import hosted_handles, make_hosted_app
from tests.domain.test_redact import done_job
from tests.infra.test_modal import seed_demo
from tests.web.design import WEB_SRC, css_rules, design_text
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


# --- The first screen, the strings and the cast -------------------------------------


def test_the_landing_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["wordmark"] == "Keyframe"
    assert strings["landingSubtitle"] == "An escape room built from your own photos."
    assert "landingTagline" not in strings  # the tagline went with the hero (owner decision Oct 29)
    assert strings["playSampleRoom"] == "Play the sample room"
    assert strings["sampleRoomSoon"] == "The sample room opens soon."
    assert strings["howARoomIsBuilt"] == "How a room is built"
    assert strings["theWizards"] == "The wizards"
    roles = [strings[key] for key in ("architectCastRole", "riddlerCastRole", "guideCastRole", "tricksterCastRole")]
    assert roles == ["Finds the objects", "Writes the locks", "Hints, never answers", "Changes the rules"]
    assert all(len(role.split()) <= 4 for role in roles)
    assert strings["riddlersNotes"] == "From the Riddler's notes"
    assert strings["howToPlay"] == "How to play" and strings["playThisRoom"] == "Play this room"
    assert strings["openingRoom"] == "Opening the room…"  # both play buttons' pending label
    assert strings["howArchitect"] == "reads your photos with muse-spark-1.3 and outlines every object with sam-3.1."
    assert strings["howRiddler"].format(locks="4 locks") == (
        "writes 4 locks from what was found; a test run that never sees the answers checks each one opens.")
    assert strings["howRiddlerUncounted"] == (
        "writes the locks from what was found; a test run that never sees the answers checks each one opens.")
    assert strings["howGuide"] == "hands out hints one rung at a time."
    assert strings["howTrickster"] == "changes the room between locks, if the Validator lets him."
    assert strings["demoRoomMeta"].format(puzzles=strings["puzzleCount"].format(n=5)) == "5 puzzles · 15 to 25 min"
    assert strings["demoRoomPortraits"] == "The Architect, the Riddler, the Guide and the Trickster"
    assert strings["demoRoomsFailed"] == "Keyframe couldn't load the demo rooms."
    assert strings["howBuilt"] == "How this room was built" and strings["tryAgain"] == "Try again"
    # No line promises a number of locks: the one count shown is the Demo room's own.
    assert not any(re.search(r"(?i)\b(?:five|four|six|\d+) locks\b", value) for value in strings.values())
    # The hero names no model and the no-demo-rooms sentence is gone for good.
    for key in ("landingSubtitle", "sampleRoomSoon"):
        assert "muse" not in strings[key] and "sam-" not in strings[key] and "Llama" not in strings[key]
    assert not any("No demo rooms are open" in value for value in strings.values())
    assert "pipelineLine" not in strings and "landingLeadIn" not in strings and "noDemoRooms" not in strings


def test_the_chooser_takes_the_first_screen_and_the_rest_follows_below_the_fold():
    ts = _code("landing.ts")
    assert "const screen = chooser({ first, failed: rooms === null, profile, start, banners, onRetry, onAccepted })" in ts
    assert "more.className = 'landing-more'" in ts and "more.append(cast())" in ts
    assert ts.count("children: [screen.element, more]") == 2  # with and without a Demo room
    # Nothing of the old title screen is left: no hero, no primary verb, no attract frame, no right column.
    for gone in ("function hero(", "function primaryVerb(", "attractFrame", "sampleClip", "landing-right", "landing-left"):
        assert gone not in ts, gone
    for name in ("components/attract-frame.ts", "components/attract-slides.ts", "components/attract-frame.css",
                 "components/sample-clip.ts"):
        assert not (WEB_SRC / name).exists(), name
    # One scroll: the chooser fills it exactly and the sections follow it; a chosen card locks it.
    rules = _landing_rules()
    assert rules[".landing-layout"] == {"position": "relative", "overflow-y": "auto"}
    assert rules[".landing-layout.is-locked"] == {"overflow": "hidden"}
    assert css_rules(_ts("chooser.css"))[".chooser"]["height"] == "100%"
    assert rules[".landing-more"]["padding"] == "var(--spacing-6) var(--spacing-frame-margin) var(--spacing-7)"


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
    assert "evidenceCard(view.id, interactable, card, false)" in notes  # no Session: the Riddler's notes
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
    assert "section('landing-how', 'landing-how-heading', strings.howARoomIsBuilt, numberedSteps(words))" in how
    assert "heading.textContent = title" in ts.split("function section(", 1)[1].split("\n}\n", 1)[0]
    steps = ts.split("function steps(locks: number | undefined)", 1)[1].split("\n}\n", 1)[0]
    assert "[strings.architect, strings.howArchitect]" in steps
    # The Riddler's step counts the first Demo room's locks, its Puzzle count, and names no number without one.
    assert ("? strings.howRiddlerUncounted\n      : "
            "fill(strings.howRiddler, { locks: locks === 1 ? strings.oneLock : fill(strings.locksCount, { n: locks }) })") in steps
    assert "[strings.riddler, riddler]" in steps
    assert "[strings.guide, strings.howGuide, strings.trickster, strings.howTrickster]" in steps
    assert "steps(locks).map(" in how
    assert "step.className = 'landing-how-step body-sm'" in ts.split("function numberedSteps(", 1)[1].split("\n}\n", 1)[0]
    rules = _landing_rules()
    assert rules[".landing-how-n"]["color"] == "var(--lamp)"


# --- Two states: a Demo room listed, or none ------------------------------------------


def test_with_a_demo_room_listed_the_sample_page_and_steps_sit_under_the_cast_then_the_further_cards():
    ts = _code("landing.ts")
    assert "below.className = 'landing-below'" in ts
    assert "below.append(notes, howARoomIsBuilt(first.puzzle_count))" in ts
    # The first Demo room is the Play card; further Demo rooms keep their cards three across, in served order, with
    # their own starter and banner slot above their list.
    assert "const others = rooms?.slice(1) ?? []" in ts
    assert "const startMore = roomStarter(profile, mode, moreBanners)" in ts
    assert "cards.push(...others.map((room) => demoRoomCard(room, profile, () => startMore(room))))" in ts
    assert "more.append(moreBanners, list)" in ts
    assert not re.search(r"\.sort\(|\.reverse\(|\.filter\(", ts), "the cards keep the served order"
    assert _card_rules()[".demo-room-list"]["grid-template-columns"] == "repeat(3, minmax(0, 1fr))"
    rules = _landing_rules()
    text = _ts("landing.css")
    assert ".landing-below {\n  display: grid;\n  grid-template-columns: repeat(2, minmax(0, 1fr));" in text
    assert rules[".landing-notes-slot"]["display"] == "contents"


def test_the_first_demo_room_s_play_view_gives_the_play_card_its_photos_and_the_sample_page():
    ts = _code("landing.ts")
    mounted = ts.split("mount: () => {", 1)[1]
    assert "const unmountChooser = screen.mount()" in mounted
    loaded = mounted.split("getRoom(first.room_id).then(", 1)[1].split("() => undefined,", 1)[0]
    assert "screen.showPhotos(view.photos.length)" in loaded and "notes.replaceChildren(sheet)" in loaded
    assert "unmountChooser()" in mounted.split("return () => {", 1)[1]


def test_with_no_demo_room_the_cast_and_the_steps_stay_and_no_no_demo_rooms_line_shows():
    ts = _code("landing.ts")
    empty = ts.split("if (first === undefined) {", 1)[1].split("\n  }\n", 1)[0]
    assert "more.append(howARoomIsBuilt())" in empty and "return { children: [screen.element, more], mount: screen.mount }" in empty
    assert "demoRoomCard" not in empty and "getRoom" not in empty
    assert "No demo rooms" not in _ts("landing.ts") and "No demo rooms" not in _ts("strings.ts")


# --- The Demo room card ----------------------------------------------------------------


def test_a_card_shows_the_cover_the_name_the_meta_line_and_the_four_portraits_under_one_name():
    ts = _code("components/demo-room-card.ts")
    assert "cover.src = photoUrl(room.room_id, room.cover_photo)" in ts and "cover.alt = ''" in ts
    assert "title.className = 'demo-room-title display-sm'" in ts and "title.textContent = roomTitle(room)" in ts
    assert "return room.name || buildTime(room.built_at)" in _ts("components/stored-room-row.ts")
    assert "meta.className = 'demo-room-meta body-sm'" in ts
    assert "meta.textContent = fill(strings.demoRoomMeta, { puzzles })" in ts
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
    assert "if (link !== null) actions.append(link)" in ts
    # The footer and its "Play this room" stand under cut 0 too; only the link and the thumbnail go.
    assert "card.append(body, footer)" in ts or "card.append(cover, body, footer)" in ts
    assert "card.addEventListener('click'" in ts.split("if (link !== null) actions.append(link)", 1)[1]


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
    # "Play this room" and the link are the card's Tab stops, each keeping the global two-tone ring; the card itself
    # is no Tab stop, so no control nests inside another.
    ts = _code("components/demo-room-card.ts")
    assert "tabIndex" not in ts and "card.setAttribute('aria-labelledby', title.id)" in ts
    assert not any("outline" in prop for rule in rules.values() for prop in rule)


def test_hover_and_state_fades_are_instant_under_reduced_motion():
    for path in ("components/demo-room-card.css", "landing.css"):
        for selector, declarations in css_rules((WEB_SRC / path).read_text()).items():
            for key, value in ((k, v) for k, v in declarations.items() if k.startswith("transition")):
                if key == "transition-delay":  # a motion token too, 0 ms under reduced motion
                    assert re.fullmatch(r"var\(--motion-\w+\)", value), (path, selector)
                    continue
                assert re.fullmatch(r"(?:[\w-]+ var\(--motion-\w+\) var\(--motion-ease\),? ?)+", value), (path, selector)


# --- Starting a Session from a card -----------------------------------------------------


def test_play_this_room_or_a_click_on_the_card_starts_a_session_and_the_link_does_not():
    ts = _code("components/demo-room-card.ts")
    assert "const play = secondaryButton({ label: strings.playThisRoom, pendingLabel: strings.openingRoom, onActivate: onStart })" in ts
    click = ts.split("card.addEventListener('click', (event) => {", 1)[1].split("})", 1)[0]
    # A click on the link or on "Play this room" is theirs alone, so a Session never starts twice; anywhere else on
    # the card goes through "Play this room", so its pending label shows.
    assert "event.target.closest('a, button') !== null) return" in click and "play.click()" in click
    assert "onStart()" not in click
    assert "keydown" not in ts  # Enter on "Play this room" is the button's own
    landing = _code("landing.ts")
    assert "const start = roomStarter(profile, mode, banners)" in landing
    assert "demoRoomCard(room, profile, () => startMore(room))" in landing


def test_a_start_in_flight_shows_opening_the_room_and_ignores_repeat_activation_until_the_play_screen_opens():
    button = _code("components/button.ts")
    options = button.split("export type SecondaryButtonOptions = {", 1)[1].split("\n)\n", 1)[0]
    assert "| { pendingLabel?: undefined; onActivate: () => void }" in options
    assert "pendingLabel: string\n      onActivate: () => Promise<void>" in options
    secondary = button.split("export function secondaryButton(", 1)[1].split("\n}\n", 1)[0]
    assert "activateWhilePending(element, options.pendingLabel, () => label, options.onActivate)" in secondary
    pending = button.split("function activateWhilePending(", 1)[1].split("\n}\n", 1)[0]
    assert "if (pending) return" in pending and "element.textContent = pendingLabel" in pending
    assert "element.setAttribute('aria-busy', 'true')" in pending and "element.textContent = settled()" in pending
    assert "activateWhilePending(element, pendingLabel, settled, onActivate)" in button.split("export function primaryButton(", 1)[1]
    assert css_rules((WEB_SRC / "components/button.css").read_text())[".button-secondary[aria-busy='true']"] == {"cursor": "progress"}
    # A start that went through never settles, so the pending label holds until the Play screen replaces the landing,
    # and no second start is posted in the meantime.
    starter = _code("stored-rooms.ts").split("export function roomStarter(", 1)[1].split("\n}\n", 1)[0]
    assert "if (starting || started) return" in starter
    routed = starter.split("const session = await startSession(", 1)[1].split("} catch {", 1)[0]
    assert routed.index("started = true") < routed.index("location.hash = ")
    assert routed.index("location.hash = ") < routed.index("return new Promise<never>(() => undefined)")


def test_the_start_sends_the_fresh_derived_block_and_a_refusal_shows_the_banner_in_the_play_back():
    starter = _code("stored-rooms.ts").split("export function roomStarter(", 1)[1].split("\n}\n", 1)[0]
    assert "await startSession(await sessionStart(room.room_id, profile, mode))" in starter
    assert "location.hash = placeHref({ route: { name: 'play', sessionId: session.id }, profile })" in starter
    refused = starter.split("} catch {", 1)[1].split("} finally {", 1)[0]
    assert "heading: strings.sessionStartRefused" in refused and "sentence: strings.sessionStartRefusedBody" in refused
    assert "actions: [{ label: strings.tryAgain, onActivate: () => void start(room) }]" in refused
    landing = _code("landing.ts")
    assert "const banners = bannerSlot()" in landing and "const start = roomStarter(profile, mode, banners)" in landing
    # One slot for the first Demo room, at the top of the Play back's details, where the click was.
    info = _code("chooser.ts").split("'chooser-play-info',", 1)[1]
    assert info.lstrip().startswith("banners,")
    assert "element.focus()" in _ts("components/error-banner.ts")  # the banner takes focus


# --- Failed and empty lists -------------------------------------------------------------


def test_a_failed_list_shows_the_failed_line_with_try_again_in_the_play_back():
    chooser = _code("chooser.ts")
    assert "playLine = [failed ? strings.demoRoomsFailed : strings.sampleRoomSoon]" in chooser
    assert "? secondaryButton({ label: strings.tryAgain, onActivate: onRetry })" in chooser
    assert "element('p', 'body-md', failed ? strings.demoRoomsFailed : strings.sampleRoomSoon), playFocus" in chooser
    assert "await listRooms().catch(() => null)" in _render()  # never the unreachable strip


# --- Platform: contrast and the narrow screen -------------------------------------------


def test_every_landing_text_pair_meets_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "canvas"), ("text-muted", "canvas"), ("text", "chrome"), ("text-muted", "chrome"),
             ("text", "chrome-raised"), ("text-muted", "chrome-raised"), ("lamp", "chrome"), ("lamp-strong", "chrome"),
             ("lamp", "chrome-raised"), ("error-text", "error-surface"), ("text", "error-surface"),
             ("lamp", "error-surface"), ("disclosure-text", "disclosure-surface")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    # The landing's links sit on the canvas, darker than the chrome the table's "links on dark" row measures.
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
    assert started.json()["opening_line"] == {"kind": "welcome", "text": "Welcome to someone else's room. Read a riddle, then click the thing it means."}


def test_the_hosted_app_with_no_demo_room_answers_an_empty_list_so_the_landing_shows_its_second_state(tmp_path: Path):
    client = TestClient(make_hosted_app(tmp_path, hosted_handles(tmp_path)))
    assert client.get("/api/meta").json()["mode"] == "hosted"
    assert client.get("/api/rooms").json() == []
