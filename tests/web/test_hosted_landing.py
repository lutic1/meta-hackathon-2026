"""Story 7.16: the Hosted landing with its Demo room cards (FR-31, UX-DR57, UX-DR58, UX-DR68, UX-DR81, NFR-10).

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
    assert "content = { name: 'landing', rooms, profile: place.profile, mode: meta.mode, onRetry: () => void render() }" in render
    # The banner and the top bar come from the same `GET /meta`, as on every surface.
    assert "const banner = disclosureBanner(disclosure)" in render and "const bar = topBar(meta, played)" in render
    shell = _code("shell.ts")
    assert "element.classList.add('landing-layout')" in shell
    assert "const landing = hostedLanding(content.rooms, content.profile, content.mode, content.onRetry)" in shell
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


# --- The title block -------------------------------------------------------------------


def test_the_landing_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["wordmark"] == "Keyframe"
    assert strings["landingSubtitle"] == "An escape room built from your own photos."
    assert strings["pipelineLine"] == (
        "muse-spark-1.3 reads your photos and writes the puzzles, sam-3.1 outlines every object, a test run that "
        "never sees the answers checks each puzzle can be solved, and the Guide hands out hints one at a time.")
    assert strings["landingLeadIn"] == "Short on time? See how a room is built and checked."
    assert strings["howARoomIsBuilt"] == "How a room is built"
    assert strings["demoRoomMeta"].format(n=5) == "5 puzzles · 15 to 25 min"
    assert strings["demoRoomPortraits"] == "The Architect, the Riddler, the Guide and the Trickster"
    assert strings["demoRoomsFailed"] == "Keyframe couldn't load the demo rooms."
    assert strings["noDemoRooms"] == (
        "No demo rooms are open right now. You can still build your own room with the access code.")
    assert strings["howBuilt"] == "How this room was built" and strings["tryAgain"] == "Try again"


def test_the_title_block_holds_the_title_subtitle_pipeline_line_and_the_lead_in_with_its_link():
    ts = _code("landing.ts")
    block = ts.split("function titleBlock(", 1)[1].split("\n}\n", 1)[0]
    assert "title.className = 'landing-heading display-lg'" in block and "title.textContent = strings.wordmark" in block
    assert "paragraph('landing-line body-md', strings.landingSubtitle)" in block
    assert "paragraph('landing-line body-md', strings.pipelineLine)" in block
    assert "paragraph('landing-lead-in body-md', strings.landingLeadIn)" in block
    # "How a room is built" (secondary) opens the first Demo room's Build view.
    assert "secondaryLink({ label: strings.howARoomIsBuilt, href: buildViewHref(first.job_id, profile) })" in block
    assert "const block = titleBlock(rooms?.[0], profile)" in ts
    rules = _landing_rules()
    assert rules[".landing-title"]["grid-column"] == "1 / -1"
    assert rules[".landing-heading,\n.landing-line"]["color"] == "var(--text)"
    assert rules[".landing-lead-in"]["color"] == "var(--text-muted)"


def test_with_no_demo_room_or_under_cut_0_the_lead_in_and_link_are_absent():
    block = _code("landing.ts").split("function titleBlock(", 1)[1].split("\n}\n", 1)[0]
    assert "if (first !== undefined && !CUT_0) {" in block
    guarded = block.split("if (first !== undefined && !CUT_0) {", 1)[1]
    assert "strings.landingLeadIn" in guarded and "strings.howARoomIsBuilt" in guarded


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
    assert "left.append(banners)" in ts and "left.append(list)" in ts
    assert "right.className = 'landing-right'" in ts and "children: [block, left, right]" in ts
    assert not re.search(r"\.sort\(|\.reverse\(|\.filter\(", ts), "the cards keep the served order"


# --- The Demo room card ----------------------------------------------------------------


def test_a_card_shows_the_cover_the_name_the_meta_line_and_the_four_portraits_under_one_name():
    ts = _code("components/demo-room-card.ts")
    assert "cover.src = photoUrl(room.room_id, room.cover_photo)" in ts and "cover.alt = ''" in ts
    assert "title.className = 'demo-room-title display-sm'" in ts and "title.textContent = roomTitle(room)" in ts
    assert "return room.name || BUILT_AT.format(new Date(room.built_at))" in _ts("components/stored-room-row.ts")
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
    for path in ("components/demo-room-card.css", "landing.css"):
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
    assert landing.index("left.append(banners)") < landing.index("left.append(list)")
    assert "element.focus()" in _ts("components/error-banner.ts")  # the banner takes focus


def test_initial_focus_is_on_the_first_demo_room_card():
    assert "cards[0].card.focus()" in _code("landing.ts")


# --- Failed and empty lists -------------------------------------------------------------


def test_a_failed_list_shows_the_failed_line_with_try_again_in_place_of_the_cards():
    ts = _code("landing.ts")
    failed = ts.split("if (rooms === null) {", 1)[1].split("\n  }\n", 1)[0]
    assert "paragraph('body-md', strings.demoRoomsFailed)" in failed
    assert "secondaryButton({ label: strings.tryAgain, onActivate: onRetry })" in failed
    assert "children: [block, left, right]" in failed  # the title block and the right column stay
    assert "demoRoomCard" not in failed
    assert "await listRooms().catch(() => null)" in _render()  # never the unreachable strip


def test_an_empty_list_shows_the_no_demo_rooms_line_and_hides_the_lead_in():
    ts = _code("landing.ts")
    empty = ts.split("if (rooms.length === 0) {", 1)[1].split("\n  }\n", 1)[0]
    assert "paragraph('landing-state body-md', strings.noDemoRooms)" in empty
    assert "titleBlock(rooms?.[0], profile)" in ts  # no first room, so no lead-in and no link


# --- Platform: contrast and the narrow screen -------------------------------------------


def test_every_landing_text_pair_meets_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "canvas"), ("text-muted", "canvas"), ("text", "chrome-raised"), ("text-muted", "chrome-raised"),
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
    view = client.get(f"/api/builds/{summary['job_id']}/view").json()
    assert [puzzle["id"] for puzzle in view["puzzles"]] == [puzzle.id for puzzle in demo.puzzles]
    assert any(photo["photo"] == summary["cover_photo"] for photo in view["photos"])
    started = client.post("/api/sessions", json={"room_id": summary["room_id"], "derived": Derived.fresh().model_dump(mode="json")})
    assert started.status_code == 200
    assert started.json()["opening_line"] == {"kind": "welcome", "text": "Welcome to someone else's room. Find what doesn't belong."}
