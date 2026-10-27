"""FR-11, UX-DR22 to UX-DR25, AR-15, NFR-10, AD-11: photo Scenes with mask Hotspots and the Thumbnail strip.

The client has no test runner (a runner is added only through bmad-correct-course), so most checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The API checks serve the
four-lock fixture room the way the Play screen reads it.
"""

import io
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.domain.schema import Room
from tests.api.test_app import make_app
from tests.fixtures.rooms import IX
from tests.web.design import WEB_SRC, css_rules, design_text, source_ts


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _rules(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


@pytest.fixture
def client(tmp_path: Path, four_lock_room: Room) -> TestClient:
    return TestClient(make_app(tmp_path, four_lock_room))


def test_the_play_route_mounts_the_scene_for_its_session_and_reads_the_room_from_get_rooms():
    shell, play, scene, api = _ts("shell.ts"), _ts("play.ts"), _ts("scene/index.ts"), _ts("api/index.ts")
    assert "if (state !== null) content = { name, session: state, guide: meta.guide, mode: meta.mode, profile: place.profile }" in shell
    assert "mount: () => mountPlay(sceneColumn, sideColumn, content.session, frame)" in shell
    # Story 1.20: the Play screen reads the Room once and shares it with the Scene, the Inventory and the notes.
    assert "const room: Promise<PlayView> = getRoom(session.room_id)" in play
    assert "mountScene(stage, stripRow, play, room)" in play and "rooms\n    .then((view) => {" in scene
    assert "return getJson<PlayView>(`/rooms/${encodeURIComponent(roomId)}`)" in api
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
    assert show.index("await texture(index)") < show.index("layer = hotspotLayer(") < live
    assert show.index("photo.replaceChildren(renderer.domElement, ...layer.elements)") < live
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
    assert "room.interactables.filter((interactable) => interactable.photo === index)" in scene
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


def test_hover_reveals_the_outline_halo_and_glow_within_150_ms_with_a_pointer_cursor():
    rules = _rules("scene/scene.css")
    assert rules[".hotspot-hit"] == {"fill": "transparent", "pointer-events": "fill", "cursor": "pointer"}
    reveal = rules[".hotspot-reveal"]
    assert reveal["opacity"] == "0" and reveal["transition"] == "opacity var(--motion-hover) var(--motion-ease)"
    assert rules[".hotspot:hover .hotspot-reveal,\n.hotspot:focus-visible .hotspot-reveal"] == {"opacity": "1"}
    assert rules[".hotspot-outline"] == {"fill": "none", "stroke": "var(--hotspot-outline)", "stroke-width": "2px"}
    # Story 1.21: the glow fill is its own path under the halo, so a collected find target's glow alone can fade.
    assert rules[".hotspot-glow"]["fill"] == "var(--hotspot-glow)"
    assert rules[".hotspot-halo"] == {"fill": "none", "stroke": "var(--hotspot-halo)", "stroke-width": "4px"}
    assert rules[".hotspot-halo,\n.hotspot-outline"]["vector-effect"] == "non-scaling-stroke"
    assert rules[".hotspot:hover .hotspot-glow"] == {"opacity": "1"}
    assert "reveal.append(path('hotspot-glow', d), path('hotspot-halo', d), path('hotspot-outline', d))" in _ts("scene/hotspots.ts")
    # No label on hover: the chip shows after a click whose reply opened nothing, or on keyboard focus (Story 1.25).
    layer = _ts("scene/hotspots.ts")
    assert "hotspot.addEventListener('pointerenter', handlers.onPointerEnter)" in layer
    loop = layer.split("for (const { interactable, d } of shown)", 1)[1].split("let hide", 1)[0]
    assert "showLabel" not in loop and loop.count("showChip(") == 1
    assert "if (hotspot.matches(':focus-visible')) showChip(interactable, interactable.label)" in loop


def test_a_click_inside_a_polygon_posts_exactly_one_click_and_a_click_outside_posts_nothing():
    layer, scene, api = _ts("scene/hotspots.ts"), _ts("scene/index.ts"), _ts("api/index.ts")
    assert layer.count("addEventListener('click'") == 1
    assert "hotspot.addEventListener('click', () => handlers.onActivate(interactable))" in layer
    assert "play.post({ type: 'click', interactable_id: interactable.id })" in scene
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
    assert activate.index("const before = play.state().locks_open") < activate.index("await play.post(")
    assert "const opened = reply.locks_open.some((id) => !before.includes(id))" in activate
    assert "if (mounted && !opened) layer?.showLabel(interactable)" in activate
    assert "export const CHIP_OFFSET_PX = 8" in layer and "export const CHIP_MS = 2000" in layer
    assert "showChip(interactable, held ? fill(strings.inHand, { label: interactable.label }) : interactable.label)" in layer
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
    assert "thumbnailStrip(play.roomId, view.photos.length, (index) => void show(index))" in scene
    assert "Array.from({ length: count }, (_, index) => {" in strip
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


def test_the_first_pointer_response_is_signalled_once_per_session_and_never_by_the_keyboard():
    scene, layer = _ts("scene/index.ts"), _ts("scene/hotspots.ts")
    assert "export const FIRST_POINTER_RESPONSE = 'first-pointer-response'" in scene
    once = scene.split("function firstPointerResponse(", 1)[1].split("\n}\n", 1)[0]
    assert "if (responded.has(sessionId)) return" in once and "responded.add(sessionId)" in once
    assert "window.dispatchEvent(new CustomEvent<FirstPointerResponseDetail>(FIRST_POINTER_RESPONSE" in once
    assert "const responded = new Set<string>()" in scene  # module level: one signal per session, not per Scene
    assert "onPointerEnter: () => firstPointerResponse(play.id)" in scene
    assert "hotspot.addEventListener('pointerenter', handlers.onPointerEnter)" in layer
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
