"""Story mode, the walk (owner decision Oct 29; build spec sections 1.5, 1.6, 5 and 6): the walk graph from each
photo's served `area` and `pan`, the keyboard map, the wall poses, the map's view cone and the doorway sign's place.

walk.ts is pure (type imports only), so Node 24 runs the shipped module as it is.
"""

import json
import shutil
import subprocess

import pytest

from tests.web.design import REPO, WEB_SRC, css_rules

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's walk graph")

RUNNER = """
import { readFileSync } from 'node:fs'
const walk = await import(process.argv[1])
const calls = JSON.parse(readFileSync(0, 'utf8'))
// An argument {"graphOf": photos} stands for the walk graph of those photos.
const arg = (value) => value?.graphOf === undefined ? value : walk.walkGraph(value.graphOf)
process.stdout.write(JSON.stringify(calls.map(([name, ...args]) => walk[name](...args.map(arg)) ?? null)))
"""


def _run(*calls: list) -> list:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", RUNNER, (WEB_SRC / "walk.ts").as_uri()],
        cwd=REPO, input=json.dumps(calls), capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _photo(area: str | None, pan: int | None) -> dict:
    photo: dict = {"hash": "h", "size": 1, "pan": pan}
    if area is not None:
        photo["area"] = area
    return photo


# The Demo room as the spec seeds it (section 7): front hall [0, 1], lounge [3, 4, 5, 2, 6, 7].
DEMO = [_photo("front hall", 0), _photo("front hall", 1), _photo("lounge", 3), _photo("lounge", 0),
        _photo("lounge", 1), _photo("lounge", 2), _photo("lounge", 4), _photo("lounge", 5)]


@needs_node
def test_areas_follow_their_first_photo_each_ring_runs_by_pan_and_the_entry_is_the_middle_view():
    [areas] = _run(["walkGraph", DEMO])
    assert areas == [{"label": "front hall", "ring": [0, 1], "entry": 0},
                     {"label": "lounge", "ring": [3, 4, 5, 2, 6, 7], "entry": 5}]
    # An area's first photo decides its place, wherever its later photos sit; a null pan sorts as the photo index.
    mixed = [_photo("lounge", 3), _photo("hall", 0), _photo("lounge", None), _photo("hall", None), _photo("study", 0)]
    [areas] = _run(["walkGraph", mixed])
    assert [area["label"] for area in areas] == ["lounge", "hall", "study"]
    assert [area["ring"] for area in areas] == [[2, 0], [1, 3], [4]]
    assert [area["entry"] for area in areas] == [2, 1, 4]


@needs_node
def test_a_room_with_no_areas_is_one_ring_in_upload_order():
    # Old rooms are served as area "room", pan null; a photo with no area at all reads the same way.
    served = [_photo("room", None) for _ in range(8)]
    bare = [_photo(None, None) for _ in range(3)]
    [old, missing] = _run(["walkGraph", served], ["walkGraph", bare])
    assert old == [{"label": "room", "ring": list(range(8)), "entry": 3}]
    assert missing == [{"label": "room", "ring": [0, 1, 2], "entry": 1}]


@needs_node
def test_neighbours_are_the_previous_and_next_views_of_the_ring_which_never_wraps():
    calls = [["neighbours", {"graphOf": DEMO}, photo] for photo in (5, 3, 7, 0, 1)]
    assert _run(*calls) == [{"left": 4, "right": 2}, {"left": None, "right": 4}, {"left": 6, "right": None},
                            {"left": None, "right": 1}, {"left": 0, "right": None}]
    [alone] = _run(["neighbours", {"graphOf": [_photo("room", None)]}, 0])
    assert alone == {"left": None, "right": None}


@needs_node
def test_every_view_has_a_doorway_to_each_neighbouring_area_only():
    three = [_photo("hall", 0), _photo("lounge", 0), _photo("study", 0), _photo("lounge", 1)]
    graph = {"graphOf": three}
    hall, lounge, other, study = _run(["doorways", graph, 0], ["doorways", graph, 1], ["doorways", graph, 3],
                                      ["doorways", graph, 2])
    assert [area["label"] for area in hall] == ["lounge"]
    assert [area["label"] for area in lounge] == ["hall", "study"] == [area["label"] for area in other]
    assert [area["label"] for area in study] == ["lounge"]  # consecutive areas only: no door from the study to the hall
    demo, one = {"graphOf": DEMO}, {"graphOf": [_photo("room", None)]}
    [[front], [back], none] = _run(["doorways", demo, 1], ["doorways", demo, 2], ["doorways", one, 0])
    assert (front["label"], front["entry"], back["label"], back["entry"], none) == ("lounge", 5, "front hall", 0, [])


@needs_node
def test_the_arrow_keys_turn_and_go_through_the_doorway_and_no_other_key_walks():
    keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Enter", " ", "Escape", "Home", "a"]
    assert _run(*[["walkKey", key] for key in keys]) == ["left", "right", "door", None, None, None, None, None, None]


@needs_node
def test_each_view_is_posed_by_its_offset_from_the_one_you_face():
    width = 600
    poses = _run(*[["wallPose", offset, width] for offset in (0, 1, -1, 2, -3)])
    assert poses[0] == {"transform": "translate3d(0px, 0px, 0px) rotateY(0deg)", "opacity": 1}
    assert poses[1] == {"transform": "translate3d(564px, 0px, -180px) rotateY(-52deg)", "opacity": 1}
    assert poses[2] == {"transform": "translate3d(-564px, 0px, -180px) rotateY(52deg)", "opacity": 1}
    assert poses[3] == {"transform": "translate3d(870px, 0px, -552px) rotateY(-62deg)", "opacity": 0}
    assert poses[4] == {"transform": "translate3d(-1200px, 0px, -852px) rotateY(62deg)", "opacity": 0}


@needs_node
def test_the_view_cone_swings_from_minus_50_to_50_degrees_across_a_ring():
    assert _run(["coneAngle", 0, 6], ["coneAngle", 5, 6], ["coneAngle", 2, 5], ["coneAngle", 0, 1]) == [-50, 50, 0, 0]


@needs_node
def test_the_doorway_sign_hangs_at_the_first_place_clear_of_every_hotspot():
    [clear] = _run(["signCentre", [], 960])
    # A box in the top band under x 480 moves the sign to x 640; one under both 480 and 640 moves it to 320.
    at_480 = {"x": 450, "y": 40, "width": 60, "height": 200}
    at_640 = {"x": 600, "y": 0, "width": 60, "height": 60}
    low = {"x": 0, "y": 121, "width": 960, "height": 900}  # below the sign's 120 px band: never in the way
    moved, twice, under = _run(["signCentre", [at_480], 960], ["signCentre", [at_480, at_640], 960],
                               ["signCentre", [low], 960])
    [everywhere] = _run(["signCentre", [{"x": 0, "y": 0, "width": 960, "height": 100}], 960])
    # Every value is in photo pixels for a 960-wide photo, scaled for any other width.
    [scaled] = _run(["signCentre", [{"x": 200, "y": 20, "width": 50, "height": 40}], 480])
    assert (clear, moved, twice, under, everywhere, scaled) == (480, 640, 320, 480, 480, 320)


# A stand-in `document` for the shipped walk map (stylesheet imports load as empty modules): elements keep their
# attributes, classes, children and click listeners, and the live region is one more of them.
MAP_RUNNER = """
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
    tag, id: '', textContent: '', children: [], attributes: {}, style: {}, listeners: {},
    set className(value) { classes.clear(); for (const name of value.split(' ').filter(Boolean)) classes.add(name) },
    get className() { return [...classes].join(' ') },
    classList: {
      contains: (name) => classes.has(name), add: (name) => classes.add(name),
      toggle: (name, on) => (on ?? !classes.has(name)) ? classes.add(name) : classes.delete(name),
    },
    setAttribute(name, value) { this.attributes[name] = String(value) },
    getAttribute(name) { return this.attributes[name] ?? null },
    removeAttribute(name) { delete this.attributes[name] },
    append(...children) { this.children.push(...children) },
    addEventListener(type, listener) { (this.listeners[type] ??= []).push(listener) },
    getBoundingClientRect: () => ({}),
  }
}
globalThis.document = { createElement: node, createElementNS: (_, tag) => node(tag), body: node('body') }
const { walkMap, viewDescription } = await import(process.argv[1])
const { walkGraph } = await import(process.argv[2])
const { photos, interactables } = JSON.parse(readFileSync(0, 'utf8'))
const areas = walkGraph(photos)
const walked = []
const map = walkMap(areas, (photo) => walked.push(photo))
const all = (tree) => [tree, ...tree.children.flatMap(all)]
const buttons = all(map.element).filter((n) => n.tag === 'button')
const read = () => ({
  current: buttons.map((b) => b.attributes['aria-current'] ?? null),
  lit: all(map.element).filter((n) => n.tag === 'circle' && n.classList.contains('is-current')).length,
  dots: all(map.element).filter((n) => n.tag === 'circle').length,
  cone: all(map.element).find((n) => n.tag === 'g').style.transform ?? null,
  live: document.body.children[0]?.textContent ?? null,
})
map.setCurrent(5)
const first = read()
map.setCurrent(0, viewDescription(areas, { interactables }, 0))
await new Promise((done) => setTimeout(done, 0))
const moved = read()
for (const button of buttons) for (const click of button.listeners.click) click()
process.stdout.write(JSON.stringify({
  tag: map.element.tag, labelledBy: map.element.attributes['aria-labelledby'],
  heading: all(map.element).find((n) => n.tag === 'h2'),
  names: buttons.map((b) => b.textContent), images: all(map.element).filter((n) => n.tag === 'img').length,
  first, moved, walked,
  descriptions: [3, 5, 2].map((photo) => viewDescription(areas, { interactables }, photo)),
}))
"""

SQUARE = [[[0, 0], [10, 0], [10, 10], [0, 10]]]


def _ix(label: str, photo: int, polygons: list | None = SQUARE) -> dict:
    return {"id": label, "label": label, "photo": photo, "polygons": polygons, "instances": 1, "attributes": []}


@needs_node
def test_the_walk_map_is_a_plan_with_one_button_per_area_that_walks_to_its_entry():
    interactables = [_ix("entryway rug", 0), _ix("floor vent", 0), _ix("ceiling light fixture", 0),
                     _ix("wall-mounted TV", 3), _ix("TV stand", 3), _ix("unmasked", 3, None), _ix("throw pillows", 2)]
    result = subprocess.run(
        ["node", "--input-type=module", "-e", MAP_RUNNER, (WEB_SRC / "components/walk-map.ts").as_uri(),
         (WEB_SRC / "walk.ts").as_uri()],
        cwd=REPO, input=json.dumps({"photos": DEMO, "interactables": interactables}), capture_output=True, text=True,
        check=True,
    )
    out = json.loads(result.stdout)
    # A <nav> named by its "Where you are" heading; one button per area, no thumbnails, no Tab stop per photo.
    assert out["tag"] == "nav" and out["labelledBy"] == out["heading"]["id"]
    assert out["heading"]["textContent"] == "Where you are"
    assert out["names"] == ["Front hall", "Lounge"] and out["images"] == 0
    # One dot per photo, the one you stand on lit; the area you stand in is the current button.
    assert out["first"]["dots"] == 8 and out["first"]["lit"] == 1
    assert out["first"]["current"] == [None, "true"] and out["moved"]["current"] == ["true", None]
    assert out["first"]["cone"].endswith("rotate(-10deg)")  # photo 5 is view 3 of 6: -50 + 100 * 2 / 5
    assert out["moved"]["cone"].endswith("rotate(-50deg)")
    # Only a move is announced, with the view description.
    assert out["first"]["live"] is None
    assert out["moved"]["live"] == "Front hall, view 1 of 2. Here: entryway rug, floor vent and ceiling light fixture."
    assert out["walked"] == [0, 5]  # each area's entry view
    assert out["descriptions"] == ["Lounge, view 1 of 6. Here: wall-mounted TV and TV stand.",
                                   "Lounge, view 3 of 6. Nothing outlined here.",
                                   "Lounge, view 4 of 6. Here: throw pillows."]


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _block(text: str, start: str) -> str:
    return text.split(start, 1)[1].split("\n  }\n", 1)[0]


def test_only_the_photo_you_face_is_drawn_and_interactive_and_its_neighbours_are_inert_walls():
    scene = _ts("scene/index.ts")
    # The walls: plain images posed by `wallPose`, inert and hidden from assistive technology unless faced.
    lay = _block(scene, "function layArea(index: number): void {")
    assert "image.src = photoUrl(play.roomId, shown)" in lay and "image.alt = ''" in lay
    pose = _block(scene, "function pose(): void {")
    assert "const { transform, opacity } = wallPose(offset, width)" in pose
    assert "element.inert = offset !== 0" in pose and "element.setAttribute('aria-hidden', 'true')" in pose
    # One three plane draws the photo you face; its view (zones, Hotspots, signs) rides that wall alone.
    assert scene.count("new Mesh(") == 1 and "walls.get(index)?.rest.append(view)" in scene
    assert "renderer.domElement.setAttribute('aria-label', fill(strings.photoView, name))" in scene
    # A move hides the Hotspots first and lays them again on arrival, the next views fetched ahead.
    walk = _block(scene, "async function walk(to: number, via?: HTMLElement, quiet = false): Promise<void> {")
    assert walk.index("view.hidden = true") < walk.index("current = to") < walk.index("await arrive(to, !quiet)")
    assert "if (room === undefined || moving || to === current || areaOf(areas, to) < 0) return" in walk
    arrive = _block(scene, "async function arrive(index: number, moved: boolean): Promise<boolean> {")
    assert "void texture(next).catch(() => undefined)" in arrive
    assert "zones.left.hidden = turns.left.hidden = side.left === null" in arrive
    assert "zones.right.hidden = turns.right.hidden = side.right === null" in arrive
    # The walls take no pointer of their own: the photo lets the zones under it answer, the Hotspots above them.
    rules = css_rules(_ts("scene/scene.css"))
    assert rules[".scene-photo"]["pointer-events"] == "none"
    assert rules[".hotspot-hit"]["pointer-events"] == "fill"


def test_turns_push_ins_and_rest_follow_the_spec_timings_and_are_cuts_under_reduced_motion():
    scene, css = _ts("scene/index.ts"), _ts("scene/walk.css")
    assert "export const TURN_MS = 780" in scene and "export const PUSH_OUT_MS = 720" in scene
    assert "export const PUSH_IN_DELAY_MS = 260" in scene and "export const PUSH_IN_MS = 640" in scene
    rules = css_rules(css)
    assert rules[".scene-world"]["perspective"] == "1500px"
    turning = rules[".scene-world.is-turning .scene-wall"]
    assert turning["transition"] == "transform 780ms cubic-bezier(0.55, 0.05, 0.25, 1), opacity 780ms ease"
    assert turning["animation"] == "walk-blur 780ms ease-in-out 1"
    assert rules[".scene-wall.is-centre .scene-wall-rest.is-resting"]["animation"] == (
        "walk-rest 26s cubic-bezier(0.3, 0, 0.4, 1) forwards")
    assert rules[".scene-wall-drift"]["transition"] == "transform 500ms ease"
    walk = _block(scene, "async function walk(to: number, via?: HTMLElement, quiet = false): Promise<void> {")
    assert "const instant = reduced()" in walk and "else if (instant) pose()" in walk
    push = _block(scene, "async function pushIn(to: number, via: HTMLElement | undefined, instant: boolean): Promise<void> {")
    assert push.startswith("\n    if (instant) return layArea(to)")
    assert "{ duration: PUSH_OUT_MS, easing: 'cubic-bezier(.5,0,.75,.2)', fill: 'forwards' }" in push
    assert "{ duration: PUSH_IN_MS, delay: PUSH_IN_DELAY_MS, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards' }" in push
    # No rest push-in and no pointer drift under reduced motion; the stylesheet stops both animations too.
    assert "if (centre === undefined || reduced()) return" in _block(scene, "function restAgain(): void {")
    assert "if (drift !== 0 || reduced()) return" in scene
    reduced = css.split("@media (prefers-reduced-motion: reduce) {", 1)[1]
    assert ".scene-world.is-turning .scene-wall,\n  .scene-wall.is-centre .scene-wall-rest.is-resting {\n    animation: none;" in reduced
    cone = _ts("components/walk-map.css").split("@media (prefers-reduced-motion: reduce) {", 1)[1]
    assert ".walk-map-cone.is-shown {\n    transition: none;" in cone


def test_the_arrow_keys_walk_only_from_the_scene_a_button_or_the_page_and_never_while_it_is_held():
    scene = _ts("scene/index.ts")
    key = _block(scene, "function onKey(event: KeyboardEvent): void {")
    assert "const move = walkKey(event.key)" in key
    assert "if (frame.closest('[inert]') !== null || !walksFrom(event.target, frame) || current < 0) return" in key
    assert "if (move !== 'door') return void turn(move)" in key and "void walk(area.entry, signs[0])" in key
    assert "window.addEventListener('keydown', onKey)" in scene and "window.removeEventListener('keydown', onKey)" in scene
    walks_from = scene.split("function walksFrom(", 1)[1].split("\n}\n", 1)[0]
    assert "frame.contains(target) || target.closest('button, a') !== null" in walks_from
    # The turn discs, the doorway sign and the map are buttons with their names; the discs hide at the ring's ends.
    assert "disc.setAttribute('aria-label', label)" in scene and "tip.setAttribute('aria-hidden', 'true')" in scene
    assert "sign.setAttribute('aria-label', fill(strings.toAreaThroughDoorway, { area: area.label }))" in scene
    assert "label.textContent = fill(strings.toArea, { area: area.label })" in scene
    # A move that took focus from the Scene gives it back to the new view.
    assert "refocus(focused)" in _block(scene, "async function walk(to: number, via?: HTMLElement, quiet = false): Promise<void> {")


def test_a_reload_opens_on_the_active_riddles_start_photo():
    play = _ts("play.ts")
    assert ("view.puzzles.find((puzzle) => puzzle.id === latest.active_puzzle_id)?.start_photo ?? 0") in play
    assert "const scene: MountedScene = mountScene(stage, play, room, start)" in play
    assert "return show(areaOf(areas, start) < 0 ? areas[0].ring[0] : start)" in _ts("scene/index.ts")
