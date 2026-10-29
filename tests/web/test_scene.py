"""FR-11, UX-DR22 to UX-DR25, AR-15, NFR-10, AD-11: photo Scenes with mask Hotspots and the Thumbnail strip.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The API checks serve the
four-lock fixture room the way the Play screen reads it.
"""

import io
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX
from tests.web.design import REPO, WEB_SRC, css_rules, design_text, source_ts
from tests.web.test_strings import _strings


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def test_the_play_route_mounts_the_scene_for_its_session_and_reads_the_effective_room():
    shell, play, scene, api = _ts("shell.ts"), _ts("play.ts"), _ts("scene/index.ts"), _ts("api/index.ts")
    assert "if (state !== null) content = { name, session: state, guide: meta.guide, mode: meta.mode, profile: place.profile }" in shell
    assert "mount: () => mountPlay(sceneColumn, sideColumn, content.session, frame)" in shell
    # Story 1.20: the Play screen reads the Room once and shares it with the Scene, the Inventory and the notes;
    # Story 4.6: it is the session's Effective room, never GET /rooms/<room_id>.
    assert "const room: Promise<PlayView> = getEffectiveRoom(session.id)" in play
    assert "mountScene(stage, stripRow, play, room)" in play and "rooms\n    .then((view) => {" in scene
    assert "return getJson<PlayView>(`/sessions/${encodeURIComponent(sessionId)}/room`)" in api
    assert "getRoom(" not in play
    assert "`/api/rooms/${encodeURIComponent(roomId)}/photos/${index}`" in api


def test_each_photo_is_a_textured_plane_drawn_as_served_and_contained():
    scene = _ts("scene/index.ts")
    assert "loader.loadAsync(photoUrl(play.roomId, index))" in scene
    assert "map.colorSpace = SRGBColorSpace" in scene
    # No light, no tone mapping, no tint: the photo's own pixels on a plane in its own pixel size.
    assert "new MeshBasicMaterial({ toneMapped: false })" in scene and "new PlaneGeometry(1, 1)" in scene
    assert "plane.scale.set(size.width, size.height, 1)" in scene and "new OrthographicCamera()" in scene
    assert not re.search(r"Light\b|toneMapping|\.color\s*=|color:", _code(scene))
    geometry = _ts("scene/geometry.ts")
    assert "const scale = Math.min(frame.width / photo.width, frame.height / photo.height)" in geometry
    assert "const fitted = contain(size, ground.getBoundingClientRect())" in scene
    assert "renderer.setSize(fitted.width, fitted.height)" in scene
    assert "new ResizeObserver(render)" in scene


def test_the_frame_shows_its_loading_line_until_the_photo_and_its_hotspots_are_live():
    scene = _ts("scene/index.ts")
    assert "frame.className = 'scene-frame is-loading'" in scene
    assert "loading.textContent = strings.sceneLoading" in scene and "loading.className = 'scene-loading body-sm'" in scene
    show = scene.split("async function show(", 1)[1].split("\n  }\n", 1)[0]
    live = show.index("frame.classList.remove('is-loading')")
    assert show.index("await texture(index)") < show.index("layHotspots(room, size, index)") < live
    lay = scene.split("function layHotspots(", 1)[1].split("\n  }\n", 1)[0]
    assert lay.index("layer = hotspotLayer(") < lay.index("photo.replaceChildren(renderer.domElement, ...layer.elements)")
    assert show.index("frame.classList.add('is-loading')") < show.index("await texture(index)")
    # The line leaves once the photo is live, so it never shows in a portrait photo's letterbox.
    assert show.index("loading.hidden = false") < show.index("await texture(index)")
    assert live < show.index("loading.hidden = true")


def test_the_scene_frame_is_the_gilt_rule_the_chrome_mat_and_the_canvas_ground():
    rules = _rules("scene/scene.css")
    frame = rules[".scene-frame"]
    assert frame["border"] == "1px solid var(--gilt)" and frame["background"] == "var(--chrome)"
    assert frame["padding"] == "var(--spacing-3)" and frame["box-shadow"] == "var(--elevation-vignette)"
    assert rules[".scene-ground"]["background"] == "var(--canvas)"
    assert rules[".scene-frame.is-loading .scene-ground"] == {"background": "none"}  # the mat alone with its line
    assert rules[".scene-loading"]["color"] == "var(--text-muted)"
    assert rules[".scene-photo canvas"] == {"border-radius": "var(--rounded-sm)"}
    column = css_rules((WEB_SRC / "shell.css").read_text())[".scene-column"]
    assert column["grid-template-rows"] == "minmax(0, 1fr) var(--spacing-thumbnail-strip)"
    assert column["row-gap"] == "var(--spacing-5)"


def test_a_hotspot_is_the_union_of_its_polygons_in_photo_pixels_with_the_interactable_id():
    layer, geometry, scene = _ts("scene/hotspots.ts"), _ts("scene/geometry.ts"), _ts("scene/index.ts")
    assert "view.interactables.filter((interactable) => interactable.photo === index)" in scene
    assert ".map((interactable) => ({ interactable, d: hotspotPath(interactable.polygons ?? []) }))" in layer
    assert "hotspot.id = interactable.id" in layer
    # The photo's own pixel space is the viewBox, so the browser scales every polygon to the rendered size.
    assert "svg.setAttribute('viewBox', `0 0 ${photo.width} ${photo.height}`)" in layer
    assert "size = { width: map.image.width, height: map.image.height }" in scene
    # One path per Hotspot, every polygon wound alike, so the nonzero rule fills and hit-tests the union.
    assert "(signedArea(polygon) < 0 ? [...polygon].reverse() : polygon)" in geometry
    assert "`M${polygon.map(([x, y]) => `${x} ${y}`).join(' L')} Z`" in geometry
    for path, text in source_ts().items():
        if path.endswith("types/index.ts"):
            continue
        assert not re.search(r"\.box\b|\bbox:|\['box'\]", _code(text)), f"{path} reads `box`"


def test_hover_reveals_the_3px_outline_halo_fill_and_lamp_shadow_in_150_ms_and_the_label_after_a_400_ms_dwell():
    rules = _rules("scene/scene.css")
    assert rules[".hotspot-hit"] == {"fill": "transparent", "pointer-events": "fill", "cursor": "pointer"}
    reveal = rules[".hotspot-reveal"]
    assert reveal["opacity"] == "0" and reveal["transition"] == "opacity var(--motion-hover) var(--motion-ease)"
    # The glow a player can feel on a real photo: the lamp drop shadow around the whole reveal, fading with it.
    assert reveal["filter"] == ("drop-shadow(0 0 4px var(--hotspot-outline)) drop-shadow(0 0 12px var(--hotspot-outline)) "
                                "drop-shadow(var(--elevation-lamp-glow))")
    assert rules[".hotspot:hover .hotspot-reveal,\n.hotspot:focus-visible .hotspot-reveal"] == {"opacity": "1"}
    assert rules[".hotspot-outline"] == {"fill": "none", "stroke": "var(--hotspot-outline)", "stroke-width": "3px"}
    # Story 1.21: the glow fill is its own path under the halo, so a collected find target's glow alone can fade.
    assert rules[".hotspot-glow"]["fill"] == "var(--hotspot-glow)"
    # 1 px of halo outside the 3 px outline.
    assert rules[".hotspot-halo"] == {"fill": "none", "stroke": "var(--hotspot-halo)", "stroke-width": "5px"}
    assert rules[".hotspot-halo,\n.hotspot-outline"]["vector-effect"] == "non-scaling-stroke"
    assert rules[".hotspot:hover .hotspot-glow"] == {"opacity": "1"}
    # Keyboard focus traces its ring without the lamp shadow (UX-DR11: the ring is never replaced by the glow).
    assert rules[".hotspot:focus-visible .hotspot-reveal"] == {"filter": "none"}
    design = design_text()
    assert "hoverStroke: '3px {colors.hotspot-outline}'" in design
    assert ("hoverGlow: 'drop-shadow(0 0 4px {colors.hotspot-outline}) drop-shadow(0 0 12px {colors.hotspot-outline}) "
            "drop-shadow({elevation.lamp-glow})'") in design
    assert "labelDwell: 400ms" in design
    layer = _ts("scene/hotspots.ts")
    assert "reveal.append(path('hotspot-glow', d), path('hotspot-halo', d), path('hotspot-outline', d))" in layer
    # The label chip after a 400 ms dwell, held until the pointer leaves; keyboard focus shows it at once (1.25).
    assert "export const DWELL_MS = 400" in layer
    loop = layer.split("for (const { interactable, d } of shown)", 1)[1].split("let hide", 1)[0]
    enter = loop.split("hotspot.addEventListener('pointerenter', () => {", 1)[1].split("})", 1)[0]
    assert "handlers.onPointerEnter()" in enter
    assert "dwell = setTimeout(() => showLabel(interactable, 'dwell'), DWELL_MS)" in enter
    assert "hotspot.addEventListener('pointerleave', () => clearTimeout(dwell))" in loop
    assert "if (hotspot.matches(':focus-visible')) showChip(interactable, interactable.label)" in loop
    chip = layer.split("function showChip(", 1)[1].split("\n  }\n", 1)[0]
    assert "if (hold === 'click') timer = setTimeout(() => hide?.(), CHIP_MS)" in chip
    assert chip.index("if (hold === 'click') timer") < chip.index("hotspot.addEventListener('pointerleave', done)")


def test_a_pressed_hotspot_fills_solid_lamp_and_a_click_shows_checking_beside_it_until_the_reply():
    rules = _rules("scene/scene.css")
    assert rules[".hotspot:active .hotspot-glow"] == {"fill": "var(--hotspot-outline)"}
    css = (WEB_SRC / "scene/scene.css").read_text()
    assert css.index(".hotspot:active .hotspot-glow") < css.index(".hotspot.is-collected .hotspot-glow")  # never on a collected one
    assert "pressedFill: '{colors.hotspot-outline}'" in design_text()
    scene = _ts("scene/index.ts")
    activate = scene.split("async function activate(", 1)[1].split("\n  }\n", 1)[0]
    assert "const pending = layer?.showPending(interactable)" in activate
    assert "const click: PostedEvent = { type: 'click', interactable_id: interactable.id }" in activate
    assert "const reply = await play.post(click).finally(pending)" in activate
    assert activate.index("const pending = layer?.showPending(") < activate.index("await play.post(")
    # The same held chip as a use_on: no dwell, timeout, pointer leave or blur clears it before the reply.
    layer = _ts("scene/hotspots.ts")
    assert "return showChip(interactable, [interactable.label, checking], 'pending')" in layer
    assert "(release !== undefined && hold !== 'pending')) return () => undefined" in layer


def test_a_click_inside_a_polygon_posts_exactly_one_click_and_a_click_outside_posts_nothing():
    layer, scene, api = _ts("scene/hotspots.ts"), _ts("scene/index.ts"), _ts("api/index.ts")
    assert layer.count("addEventListener('click'") == 1
    assert "hotspot.addEventListener('click', () => handlers.onActivate(interactable))" in layer
    assert "const click: PostedEvent = { type: 'click', interactable_id: interactable.id }" in scene
    assert "play.post(click)" in scene
    # The one other post is a select-then-click's or a drop's `use_on` (Story 1.26), which never sends a click.
    assert scene.count("play.post(") == 2 and "postEvent(" not in scene
    play = _ts("play.ts")
    assert "const reply = await postEvent(session.id, body)" in play and play.count("postEvent(") == 1
    assert "return postJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}/events`, body)" in api
    for text in (layer, scene, api, play):
        assert "t_ms" not in _code(text) and "Date.now" not in text and "performance.now" not in text
    # Only the hit paths take the pointer: the overlay, the reveal and the chip let it through to nothing.
    rules = _rules("scene/scene.css")
    assert rules[".scene-hotspots"]["pointer-events"] == "none"
    assert rules[".hotspot-reveal"]["pointer-events"] == "none"
    assert rules[".hotspot-label-chip"]["pointer-events"] == "none"
    assert "addEventListener('click'" not in scene


def test_a_non_target_click_shows_only_the_label_chip_8px_above_for_2s_or_until_pointer_leave():
    scene, layer = _ts("scene/index.ts"), _ts("scene/hotspots.ts")
    activate = scene.split("async function activate(", 1)[1].split("\n  }\n", 1)[0]
    # Judged against the state before this click was posted, so a poll landing in between cannot hide the chip.
    assert activate.index("const before = play.state()") < activate.index("await play.post(")
    assert "const opened = reply.locks_open.some((id) => !before.locks_open.includes(id))" in activate
    assert "if (mounted && !opened) layer?.showLabel(interactable)" in activate
    assert "export const CHIP_OFFSET_PX = 8" in layer and "export const CHIP_MS = 2000" in layer
    assert "? fill(strings.inHand, { label: interactable.label })" in layer
    assert ": foundIds.includes(interactable.id) ? fill(strings.found, { label: interactable.label }) : interactable.label" in layer
    assert "showChip(interactable, text, hold)" in layer
    assert "chip.textContent = text" in layer
    assert "rendered.height - top * scale + CHIP_OFFSET_PX" in layer
    assert "setTimeout(() => hide?.(), CHIP_MS)" in layer
    assert "hotspot.addEventListener('pointerleave', done)" in layer
    assert "chip.className = 'hotspot-label-chip label'" in layer
    rules = _rules("scene/scene.css")
    chip = rules[".hotspot-label-chip"]
    assert chip["background"] == "var(--parchment)" and chip["color"] == "var(--ink)"
    assert chip["border-radius"] == "var(--rounded-sm)" and chip["opacity"] == "0"
    assert chip["transition"] == "opacity var(--motion-state) var(--motion-ease)"
    assert rules[".hotspot-label-chip.is-shown"] == {"opacity": "1"}


def test_the_thumbnail_strip_has_one_96_by_72_button_per_photo_in_upload_order():
    strip, scene = _ts("components/thumbnail-strip.ts"), _ts("scene/index.ts")
    assert "thumbnailStrip(play.roomId, objectCounts(view), (index) => void show(index))" in scene
    assert "const thumbnails = counts.map((_, index) => {" in strip
    assert "image.src = photoUrl(roomId, index)" in strip
    assert "image.alt = fill(strings.photoThumbnail, { n: index + 1 })" in strip
    assert "image.width = 96" in strip and "image.height = 72" in strip
    assert "thumbnail.type = 'button'" in strip and "tabIndex" not in strip  # native: Tab reaches it, Enter clicks
    assert "thumbnail.addEventListener('click', () => onSelect(index))" in strip
    assert "thumbnail.setAttribute('aria-current', 'true')" in strip and "removeAttribute('aria-current')" in strip
    assert "strip?.setCurrent(index)" in scene and "import './thumbnail-strip.css'" in strip
    assert "stripRow.prepend(strip.element)" in scene  # the row's left part; the Inventory is its right
    rules = _rules("components/thumbnail-strip.css")
    row = rules[".thumbnail-strip"]
    assert row["gap"] == "var(--spacing-2)" and row["overflow-x"] == "auto" and row["overflow-y"] == "hidden"
    thumbnail = rules[".thumbnail"]
    assert (thumbnail["width"], thumbnail["height"]) == ("96px", "72px")
    assert thumbnail["border-radius"] == "var(--rounded-sm)" and thumbnail["opacity"] == "0.8"
    assert thumbnail["border"] == "2px solid transparent" and thumbnail["box-sizing"] == "border-box"
    assert rules[".thumbnail:hover"] == {"border-color": "var(--lamp-strong)"}
    assert rules[".thumbnail[aria-current='true']"] == {"border-color": "var(--lamp)", "opacity": "1"}


# Builds the shipped Thumbnail strip with a stand-in `document` (stylesheet imports load as empty modules) and prints,
# per thumbnail, its badge, whether it is dimmed and its description, before and after `setCounts`.
STRIP_RUNNER = """
import { register } from 'node:module'
import { readFileSync } from 'node:fs'
register('data:text/javascript,' + encodeURIComponent(`
  export async function load(url, context, next) {
    return url.endsWith('.css') ? { format: 'module', source: '', shortCircuit: true } : next(url, context)
  }
`))
const node = (tag) => {
  const classes = new Set()
  return {
    tag, id: '', textContent: '', hidden: false, children: [], attributes: {}, style: {},
    get className() { return [...classes].join(' ') },
    set className(value) { classes.clear(); for (const name of value.split(' ').filter(Boolean)) classes.add(name) },
    classList: {
      contains: (name) => classes.has(name),
      toggle: (name, on) => (on ?? !classes.has(name)) ? classes.add(name) : classes.delete(name),
    },
    setAttribute(name, value) { this.attributes[name] = String(value) },
    removeAttribute(name) { delete this.attributes[name] },
    append(...children) { this.children.push(...children) },
    addEventListener() {},
  }
}
globalThis.document = { createElement: node }
const { objectCounts, thumbnailStrip } = await import(process.argv[1])
const { view, later } = JSON.parse(readFileSync(0, 'utf8'))
const counts = objectCounts(view)
const strip = thumbnailStrip('room', counts, () => undefined)
const byId = (id) => strip.element.children.flatMap((thumbnail) => thumbnail.children).find((child) => child.id === id)
const read = () => strip.element.children.map((thumbnail) => {
  const badge = thumbnail.children.find((child) => child.className.includes('thumbnail-count'))
  return {
    badge: badge === undefined || badge.hidden ? null : badge.textContent,
    hiddenBadge: badge?.attributes['aria-hidden'] ?? null,
    empty: thumbnail.classList.contains('is-empty'),
    description: byId(thumbnail.attributes['aria-describedby'])?.textContent ?? null,
  }
})
const first = read()
strip.setCounts(objectCounts(later))
process.stdout.write(JSON.stringify({ counts, first, after: read() }))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's Thumbnail strip")

SQUARE = [[[0, 0], [10, 0], [10, 10], [0, 10]]]


def _ix(id: str, photo: int, polygons: list | None = SQUARE) -> dict:
    return {"id": id, "label": id, "photo": photo, "polygons": polygons, "instances": 1, "attributes": []}


@needs_node
def test_each_thumbnail_carries_a_badge_counting_the_objects_on_its_photo_and_a_photo_with_none_is_dimmed():
    """Playtest Oct 29: objects are outlined on one photo each and the lounge photos look alike, so nothing told the
    player which photo holds things. Each thumbnail counts the Hotspots its photo draws (an Interactable with no
    drawable polygon draws none); a photo with none has no badge, is dimmed and is described as having no objects."""
    # The owner's room in miniature: three objects in the entryway, one at the door, none on photo 2, two on photo 3.
    interactables = [_ix("rug", 0), _ix("vent", 0), _ix("light", 0), _ix("door", 1), _ix("tree", 3), _ix("tv", 3),
                     _ix("unmasked", 2, None), _ix("sliver", 2, [[[0, 0], [5, 5]]])]
    view = {"photos": [{"hash": str(i), "size": 1} for i in range(4)], "interactables": interactables}
    later = {**view, "interactables": [*interactables, _ix("decoy", 2)]}  # an accepted edit adds an object
    result = subprocess.run(
        ["node", "--input-type=module", "-e", STRIP_RUNNER, (WEB_SRC / "components/thumbnail-strip.ts").as_uri()],
        cwd=REPO, input=json.dumps({"view": view, "later": later}), capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["counts"] == [3, 1, 0, 2]
    assert [t["badge"] for t in out["first"]] == ["3", "1", None, "2"]
    assert [t["empty"] for t in out["first"]] == [False, False, True, False]
    assert [t["description"] for t in out["first"]] == ["3 objects", "1 object", "no objects", "2 objects"]
    assert all(t["hiddenBadge"] == "true" for t in out["first"] if t["badge"] is not None)  # the description says it
    # The refetched Effective room redraws the counts in place.
    assert [t["badge"] for t in out["after"]] == ["3", "1", "1", "2"]
    assert [t["empty"] for t in out["after"]] == [False, False, False, False]
    assert out["after"][2]["description"] == "1 object"


def test_the_count_badge_is_a_parchment_caption_chip_and_a_photo_with_no_objects_sits_at_half_opacity():
    strip, scene = _ts("components/thumbnail-strip.ts"), _ts("scene/index.ts")
    assert "strip?.setCounts(objectCounts(view))" in scene.split("function reshape(", 1)[1].split("\n  }\n", 1)[0]
    assert "thumbnail.setAttribute('aria-describedby', description.id)" in strip
    # Both stay out of the name, "Photo {n}": the badge is aria-hidden, the description hidden and only referenced.
    assert "description.hidden = true" in strip and "badge.setAttribute('aria-hidden', 'true')" in strip
    text = (WEB_SRC / "components/thumbnail-strip.css").read_text()
    rules = _rules("components/thumbnail-strip.css")
    assert rules[".thumbnail"]["position"] == "relative"
    badge = rules[".thumbnail-count"]
    assert badge["position"] == "absolute" and badge["background"] == "var(--parchment)" and badge["color"] == "var(--ink)"
    assert badge["border-radius"] == "var(--rounded-sm)" and badge["pointer-events"] == "none"
    assert rules[".thumbnail.is-empty"] == {"opacity": "0.5"}
    # The current photo stays at full opacity even when it holds nothing: its rule comes after the dimmed one.
    assert text.index(".thumbnail.is-empty {") < text.index(".thumbnail[aria-current='true'] {")
    strings = _strings()
    assert (strings["photoObjects"].format(k=3), strings["photoObject"], strings["photoNoObjects"]) == (
        "3 objects", "1 object", "no objects")
    row = design_text().split("| Thumbnail strip |", 1)[1].split("\n", 1)[0]
    assert "count badge" in row and "50% opacity" in row


def test_the_first_pointer_response_is_signalled_once_per_session_and_never_by_the_keyboard():
    scene, layer = _ts("scene/index.ts"), _ts("scene/hotspots.ts")
    assert "export const FIRST_POINTER_RESPONSE = 'first-pointer-response'" in scene
    once = scene.split("function firstPointerResponse(", 1)[1].split("\n}\n", 1)[0]
    assert "if (responded.has(sessionId)) return" in once and "responded.add(sessionId)" in once
    assert "window.dispatchEvent(new CustomEvent<FirstPointerResponseDetail>(FIRST_POINTER_RESPONSE" in once
    assert "const responded = new Set<string>()" in scene  # module level: one signal per session, not per Scene
    assert "onPointerEnter: () => firstPointerResponse(play.id)" in scene
    assert "hotspot.addEventListener('pointerenter', () => {\n      handlers.onPointerEnter()" in layer
    assert scene.count("firstPointerResponse(") == 2 and layer.count("onPointerEnter") == 2


def test_every_hotspot_is_a_focusable_button_that_enter_activates_with_the_ring_traced_along_it():
    layer = _ts("scene/hotspots.ts")
    assert "hotspot.setAttribute('role', 'button')" in layer and "hotspot.setAttribute('tabindex', '0')" in layer
    assert "hotspot.setAttribute('aria-label', interactable.label)" in layer
    assert "if (event.key === 'Enter') handlers.onActivate(interactable)" in layer
    rules = _rules("scene/scene.css")
    # Outside the edge: 2 px focus-ring-inner against the polygon, 2 px focus-ring beyond it, as on every element.
    assert rules[".hotspot:focus-visible .hotspot-halo"] == {"stroke": "var(--focus-ring)", "stroke-width": "8px"}
    assert rules[".hotspot:focus-visible .hotspot-glow"] == {"opacity": "0"}
    assert rules[".hotspot:focus-visible .hotspot-outline"] == {"stroke": "var(--focus-ring-inner)",
                                                               "stroke-width": "4px"}


def test_every_scene_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text-muted", "chrome"), ("ink", "parchment"), ("hotspot-outline", "hotspot-halo"),
             ("lamp", "chrome"), ("lamp-strong", "chrome"), ("focus-ring", "chrome")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"


def test_the_four_lock_room_serves_every_polygon_inside_its_photo_and_no_box(client: TestClient, four_lock_room: Room):
    view = client.get(f"/api/rooms/{four_lock_room.id}").json()
    assert "box" not in {key for interactable in view["interactables"] for key in interactable}
    sizes = []
    for index in range(len(view["photos"])):
        response = client.get(f"/api/rooms/{four_lock_room.id}/photos/{index}")
        assert response.status_code == 200 and response.headers["content-type"] == "image/jpeg"
        sizes.append(Image.open(io.BytesIO(response.content)).size)
    assert sizes[2] == (960, 1280) and max(max(size) for size in sizes) == 1280  # one portrait, letterboxed
    for interactable in view["interactables"]:
        width, height = sizes[interactable["photo"]]
        for polygon in interactable["polygons"]:
            assert all(0 <= x <= width and 0 <= y <= height for x, y in polygon), interactable["id"]


def test_only_a_click_that_opens_a_lock_is_a_target(client: TestClient, four_lock_room: Room):
    session = client.post("/api/sessions", json={"room_id": four_lock_room.id}).json()
    events = f"/api/sessions/{session['id']}/events"
    rug = client.post(events, json={"type": "click", "interactable_id": IX["rug"]}).json()
    assert rug["locks_open"] == session["locks_open"] == []  # a non-target: the label chip shows
    key = client.post(events, json={"type": "click", "interactable_id": IX["key"]}).json()
    assert len(key["locks_open"]) == 1  # the find target opened its lock: no chip
