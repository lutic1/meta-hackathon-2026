"""FR-38, UX-DR49, UX-DR50, UX-DR67, UX-DR71: the Build view's puzzle graph and mask overlays.

As in test_build_view_surface.py, most checks read the TypeScript and the stylesheets (the client has no test runner);
`npm run build` and `tsc --noEmit` prove they compile. The graph layout, its edge routes and the chip placement are pure
modules with no DOM or CSS, so Node (which strips the types) runs them as they ship and the geometry is checked here. The
sentinel check builds the `BuildView` the page renders from a Room with sentinel solutions, and the client modules are
checked to read nothing else.
"""

import json
import random
import re
import shutil
import subprocess
from functools import cache
from itertools import pairwise
from typing import Any

import pytest

from src.domain.redact import to_build_view
from src.domain.schema import Room
from tests.domain.test_redact import done_job
from tests.fixtures.rooms import SENTINEL_CODE, SENTINEL_IX, with_sentinel_solutions
from tests.web.design import REPO, source_css
from tests.web.test_build_view_surface import COMPONENTS, _code, _css, _ts
from tests.web.test_contrast import PROPS, _hex, _over, contrast

GRAPH = (COMPONENTS / "puzzle-graph.ts").read_text()
LAYOUT = (COMPONENTS / "graph-layout.ts").read_text()
MASKS = (COMPONENTS / "mask-overlays.ts").read_text()
CHIPS = (COMPONENTS / "chip-layout.ts").read_text()

NODE_W, NODE_H = 168, 64
EXIT_RING = 6
# The left column at 1440 px (as in mockups/build-view.html) and at 1280 px, the graph panel's inner width there.
WIDTH_1440 = 864
WIDTH_1280 = int((1280 - 2 * 24 - 24) * 2 / 3 - 2 * 24)

# Runs the shipped layout modules on the cases read from stdin and prints what they return.
RUNNER = """
import { readFileSync } from 'node:fs'
const [graph, chips] = await Promise.all(process.argv.slice(1).map((url) => import(url)))
const { graphs, tiles } = JSON.parse(readFileSync(0, 'utf8'))
process.stdout.write(JSON.stringify({
  graphs: graphs.map(({ puzzles, width }) => {
    const layout = graph.layoutGraph(puzzles, width)
    return { layout, edges: graph.graphEdges(puzzles, layout) }
  }),
  tiles: tiles.map(({ masks, chips: sizes, photo, tile }) => chips.placeChips(masks, sizes, photo, tile)),
}))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the client's layout modules")


def _function(text: str, signature: str) -> str:
    return text.split(signature, 1)[1].split("\n}\n", 1)[0]


def _run(graphs: list[dict[str, Any]], tiles: list[dict[str, Any]]) -> dict[str, list[Any]]:
    modules = [(COMPONENTS / name).as_uri() for name in ("graph-layout.ts", "chip-layout.ts")]
    result = subprocess.run(
        ["node", "--input-type=module", "-e", RUNNER, *modules],
        input=json.dumps({"graphs": graphs, "tiles": tiles}), cwd=REPO, capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _puzzle(id: str, requires: list[str], lock_type: str = "code", is_exit: bool = False) -> dict[str, Any]:
    return {"id": id, "lock_type": lock_type, "requires": requires, "is_exit": is_exit}


# P1 find, P2 code after P1, P3 use_on after both, then the Exit: P1 -> P3 skips P2's column.
SKIP_CHAIN = [_puzzle("p1", []), _puzzle("p2", ["p1"]), _puzzle("p3", ["p1", "p2"]), _puzzle("p4", ["p3"], is_exit=True)]
# A use_on puzzle (rule 8) after its find puzzle and a second prerequisite, beside an order puzzle the Exit needs.
SKIP_ROOM = [
    _puzzle("p1", [], "find"), _puzzle("p2", ["p1"], "code"), _puzzle("p3", [], "order"),
    _puzzle("p4", ["p1", "p2"], "use_on"), _puzzle("p5", ["p4", "p3"], "code", is_exit=True),
]


def _random_graphs(count: int) -> list[dict[str, Any]]:
    """`count` valid shapes of 4 to 6 Puzzles, each requiring only earlier ones, listed in a shuffled order."""
    rng = random.Random(230)
    graphs = []
    for _ in range(count):
        n = rng.randint(4, 6)
        puzzles = [
            _puzzle(f"p{i}", [f"p{j}" for j in range(i) if rng.random() < 0.4], rng.choice(["code", "order", "use_on", "find"]))
            for i in range(n - 1)
        ]
        puzzles.append(_puzzle(f"p{n - 1}", [f"p{j}" for j in rng.sample(range(n - 1), rng.randint(1, n - 1))], is_exit=True))
        rng.shuffle(puzzles)
        graphs.append({"puzzles": puzzles, "width": rng.choice([WIDTH_1280, WIDTH_1440, rng.randint(587, 864)])})
    return graphs


GRAPHS = [{"puzzles": shape, "width": width} for shape in (SKIP_CHAIN, SKIP_ROOM) for width in (WIDTH_1440, WIDTH_1280)]
GRAPHS += [{"puzzles": [_puzzle(f"p{i}", [f"p{i - 1}"] if i else [], is_exit=i == 5) for i in range(6)], "width": WIDTH_1280}]
GRAPHS += _random_graphs(1500)

# Photo 4 of the fixture rooms: wax candle, iron lantern and sand hourglass on one shelf (tests/fixtures/rooms.py), in a
# tile at 1280 px and at 1024 px. Chips are 21 px tall; widths are the label type's, about 7 px a letter and 16 px padding.
SHELF = [(160, 360, 300, 640), (540, 300, 740, 640), (980, 380, 1120, 640)]
SHELF_CHIPS = [{"width": 7 * len(label) + 16, "height": 21} for label in ("wax candle", "iron lantern", "sand hourglass")]
TILES = [
    {
        "masks": [{"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0} for x0, y0, x1, y1 in SHELF],
        "chips": SHELF_CHIPS,
        "photo": {"width": 1280, "height": 960},
        "tile": {"width": width, "height": width * 3 / 4},
    }
    for width in (((1280 - 48 - 24) * 2 / 3 - 32) / 3, ((1024 - 48 - 24) * 2 / 3 - 32) / 3)
]


@cache
def _shipped() -> dict[str, list[Any]]:
    return _run(GRAPHS, TILES)


def _crosses(p: list[float], q: list[float], box: tuple[float, float, float, float]) -> bool:
    """Whether the segment p-q runs through the inside of `box` (left, top, right, bottom)."""
    enter, leave = 0.0, 1.0
    for start, delta, low, high in ((p[0], q[0] - p[0], box[0], box[2]), (p[1], q[1] - p[1], box[1], box[3])):
        if delta == 0:
            if not low < start < high:
                return False
            continue
        a, z = (low - start) / delta, (high - start) / delta
        enter, leave = max(enter, min(a, z)), min(leave, max(a, z))
    return leave - enter > 1e-9


def _box(node: dict[str, float], pad: float = 0) -> tuple[float, float, float, float]:
    return node["x"] - pad, node["y"] - pad, node["x"] + NODE_W + pad, node["y"] + NODE_H + pad


# --- Puzzle graph ------------------------------------------------------------------------------------------------


def test_the_graph_sits_at_the_top_of_the_left_column_over_the_mask_overlays():
    view = _ts("build-view.ts")
    assert "left.append(puzzleGraph(state.view), maskOverlays(state.view))" in view
    # The right column comes first in the page for Tab order and is placed in the right third by the stylesheet.
    assert "columns.append(right, left)" in view
    rules = _css("shell.css")
    assert rules[".build-view-left"]["grid-column"] == "1" and rules[".build-view-right"]["grid-column"] == "2"
    assert rules[".build-view-left, .build-view-right"]["grid-row"] == "1"


@needs_node
def test_the_graph_runs_left_to_right_with_the_exit_puzzle_alone_rightmost():
    for case, shipped in zip(GRAPHS, _shipped()["graphs"], strict=True):
        nodes = shipped["layout"]["nodes"]
        exit_x = next(node["x"] for node, puzzle in zip(nodes, case["puzzles"]) if puzzle["is_exit"])
        others = [node["x"] for node, puzzle in zip(nodes, case["puzzles"]) if not puzzle["is_exit"]]
        assert exit_x > max(others), case
        # Every required Puzzle sits in a column left of the Puzzle requiring it.
        x = {puzzle["id"]: node["x"] for node, puzzle in zip(nodes, case["puzzles"])}
        for puzzle in case["puzzles"]:
            assert all(x[required] < x[puzzle["id"]] for required in puzzle["requires"]), case


@needs_node
def test_no_two_nodes_overlap():
    for case, shipped in zip(GRAPHS, _shipped()["graphs"], strict=True):
        boxes = [_box(node) for node in shipped["layout"]["nodes"]]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], case


@needs_node
def test_no_edge_runs_under_a_node_it_does_not_join():
    for case, shipped in zip(GRAPHS, _shipped()["graphs"], strict=True):
        nodes, puzzles = shipped["layout"]["nodes"], case["puzzles"]
        ids = [puzzle["id"] for puzzle in puzzles]
        expected = sorted((ids.index(required), to) for to, puzzle in enumerate(puzzles) for required in puzzle["requires"])
        assert sorted((edge["from"], edge["to"]) for edge in shipped["edges"]) == expected, case
        for edge in shipped["edges"]:
            points = edge["points"]
            # It starts on the required node's edge and stops short of the requiring node, past the Exit's ring.
            assert _crosses(points[0], points[1], _box(nodes[edge["from"]], 1)), case
            margin = 9 if puzzles[edge["to"]]["is_exit"] else 3
            assert not _crosses(points[-2], points[-1], _box(nodes[edge["to"]], margin - 0.5)), case
            assert _crosses(points[-2], points[-1], _box(nodes[edge["to"]], margin + 0.5)), case
            for k, node in enumerate(nodes):
                if k in (edge["from"], edge["to"]):
                    continue
                keep = _box(node, 4 + (EXIT_RING if puzzles[k]["is_exit"] else 0))
                assert not any(_crosses(p, q, keep) for p, q in pairwise(points)), (case, edge, k)


@needs_node
def test_a_skipped_column_edge_bends_round_the_node_between():
    chain = _shipped()["graphs"][0]
    assert GRAPHS[0] == {"puzzles": SKIP_CHAIN, "width": WIDTH_1440}
    p1_to_p3 = next(edge for edge in chain["edges"] if (edge["from"], edge["to"]) == (0, 2))
    p1, p2, p3 = chain["layout"]["nodes"][:3]
    centres = [[node["x"] + NODE_W / 2, node["y"] + NODE_H / 2] for node in (p1, p3)]
    assert _crosses(*centres, _box(p2)), "a straight line would run under Puzzle 2"
    points = p1_to_p3["points"]
    assert not any(_crosses(p, q, _box(p2, 7.9)) for p, q in pairwise(points)), "it keeps 8 px clear of it"


def test_nodes_are_168_by_64_parchment_with_the_order_number_and_lock_type_in_mono_sm():
    assert "export const NODE_WIDTH = 168" in LAYOUT and "export const NODE_HEIGHT = 64" in LAYOUT
    node = _css("components/puzzle-graph.css")[".graph-node"]
    assert (node["width"], node["height"]) == ("168px", "64px")
    assert node["background"] == "var(--graph-node)" and node["color"] == "var(--graph-node-ink)"
    assert node["border-radius"] == "var(--rounded-md)"
    graph_node = _function(GRAPH, "function graphNode(")
    assert "line('graph-node-number mono-sm', fill(strings.puzzleHeading, { n }))" in graph_node
    assert "line('graph-node-type mono-sm', puzzle.lock_type)" in graph_node


def test_requires_edges_are_graph_edge_lines_with_8px_arrowheads():
    rules = _css("components/puzzle-graph.css")
    assert rules[".graph-edge"]["stroke"] == "var(--graph-edge)" and rules[".graph-edge"]["stroke-width"] == "1.5px"
    assert rules[".graph-arrowhead"]["fill"] == "var(--graph-edge)"
    assert "markerWidth: 8," in GRAPH and "markerHeight: 8," in GRAPH and "markerUnits: 'userSpaceOnUse'" in GRAPH
    assert "d: 'M0,0 L8,4 L0,8 z'" in GRAPH
    graph = _function(GRAPH, "export function puzzleGraph(")
    assert "graphEdges(view.puzzles, layout).map(({ points }) =>" in graph
    assert "svg('path', { class: 'graph-edge', d: `M${points.join(' L')}`, 'marker-end': 'url(#graph-arrowhead)' })" in graph
    assert rules[".graph-edge"]["fill"] == "none"
    edges = _function(LAYOUT, "export function graphEdges(")
    assert "puzzle.requires.flatMap((id) => {" in edges


def test_the_exit_node_has_a_3px_lamp_double_ring_and_an_exit_label_in_lamp_ink():
    rules = _css("components/puzzle-graph.css")
    ring = rules[".graph-node-exit::after"]
    assert ring["border"] == "3px double var(--graph-node-exit)" and ring["inset"] == "-6px"
    assert rules[".graph-node-exit-label"]["color"] == "var(--lamp-ink)"
    graph_node = _function(GRAPH, "function graphNode(")
    assert "puzzle.is_exit ? 'graph-node graph-node-exit' : 'graph-node'" in graph_node
    assert "exit.textContent = strings.exit" in graph_node


def test_each_node_shows_its_dry_run_marker_top_right_as_an_8px_dot_and_the_verdict():
    rules = _css("components/puzzle-graph.css")
    marker = rules[".graph-dry-run"]
    assert marker["position"] == "absolute" and marker["right"] == "var(--spacing-3)" and "top" in marker
    dot = rules[".graph-dry-run::before"]
    assert (dot["width"], dot["height"], dot["border-radius"]) == ("8px", "8px", "var(--rounded-full)")
    assert rules[".graph-dry-run-pass"]["color"] == "var(--success-ink)"
    assert rules[".graph-dry-run-fail"]["color"] == "var(--wrong-ink)"
    assert rules[".graph-dry-run-skipped"]["color"] == "var(--ink-muted)"
    assert "line(`graph-dry-run graph-dry-run-${verdict} label`, verdict)" in GRAPH
    # One verdict per Puzzle from `BuildView.dry_run`, "skipped" for a Puzzle the test run did not reach.
    assert "verdicts.get(puzzle.id) ?? 'skipped'" in GRAPH


def test_nodes_are_tab_stops_in_puzzle_order_with_their_accessible_names():
    graph = _function(GRAPH, "export function puzzleGraph(")
    assert "view.puzzles.map((puzzle, index) =>" in graph and "graphNode(index + 1, puzzle," in graph
    assert "stage.append(edges, ...nodes)" in graph
    graph_node = _function(GRAPH, "function graphNode(")
    assert "node.tabIndex = 0" in graph_node
    assert "node.setAttribute('aria-label', nodeName(n, puzzle, requires, verdict))" in graph_node
    name = _function(GRAPH, "export function nodeName(")
    assert "requires: list.length === 0 ? strings.requiresNone : LIST.format(list)" in name
    assert "return puzzle.is_exit ? `${name}, ${strings.exit}` : name" in name
    assert "new Intl.ListFormat('en-US', { style: 'long', type: 'conjunction' })" in GRAPH
    assert "tabIndex = -1" not in _code(GRAPH)


def test_enter_on_a_node_acts_as_a_click_which_only_focuses_it():
    graph_node = _function(GRAPH, "function graphNode(")
    assert "if (event.key === 'Enter') node.click()" in graph_node
    assert "node.addEventListener('click', () => node.focus())" in graph_node
    assert len(re.findall(r"addEventListener\(", graph_node)) == 2


@needs_node
def test_the_graph_fits_its_column_at_1280px():
    for case, shipped in zip(GRAPHS, _shipped()["graphs"], strict=True):
        layout = shipped["layout"]
        assert layout["width"] <= case["width"], case
        assert all(0 <= node["x"] and node["x"] + NODE_W <= layout["width"] for node in layout["nodes"]), case
        assert layout["height"] == max(node["y"] for node in layout["nodes"]) + NODE_H
    six_deep = _shipped()["graphs"][4]
    assert GRAPHS[4]["width"] == WIDTH_1280 and len({node["x"] for node in six_deep["layout"]["nodes"]}) == 6
    assert "new ResizeObserver(" in GRAPH


# --- Mask overlays -----------------------------------------------------------------------------------------------


def test_the_mask_overlays_show_the_photos_three_across_at_4_3():
    rules = _css("components/mask-overlays.css")
    assert rules[".mask-overlays"]["grid-template-columns"] == "repeat(3, minmax(0, 1fr))"
    assert rules[".mask-tile"]["aspect-ratio"] == "4 / 3"
    assert rules[".mask-tile-photo"]["object-fit"] == "contain"
    assert "grid.append(...view.photos.map((photo) => maskTile(view.room_id, photo)))" in MASKS
    assert "image.src = photoUrl(roomId, photo)" in MASKS


def test_each_mask_is_filled_and_stroked_2px_lamp_over_a_dark_halo():
    rules = _css("components/mask-overlays.css")
    mask, halo = rules[".build-view-mask"], rules[".build-view-mask-halo"]
    assert mask["fill"] == "var(--mask-overlay-fill)" and mask["stroke"] == "var(--mask-overlay-stroke)"
    assert mask["stroke-width"] == "2px"
    # A 4 px halo under the 2 px line shows 1 px of dark each side: DESIGN.md `halo: 1px {colors.hotspot-halo}`.
    assert halo["stroke"] == "var(--hotspot-halo)" and halo["stroke-width"] == "4px" and halo["fill"] == "none"
    assert rules[".build-view-mask-halo, .build-view-mask"]["vector-effect"] == "non-scaling-stroke"


def test_box_fallbacks_draw_the_same_as_any_polygon():
    # Every mask is the union of its polygons through the Scene's own path; the client never reads `box`.
    assert "const d = hotspotPath(mask.polygons)" in MASKS
    assert "mask.box" not in MASKS and "fallback" not in _code(MASKS)


def test_each_label_sits_on_a_focusable_parchment_chip():
    tile = _function(MASKS, "function maskTile(")
    assert "chip.className = 'mask-chip label'" in tile and "chip.tabIndex = 0" in tile
    assert "chip.textContent = mask.label" in tile
    chip = _css("components/mask-overlays.css")[".mask-chip"]
    assert chip["background"] == "var(--parchment)" and chip["color"] == "var(--ink)"
    assert chip["border-radius"] == "var(--rounded-sm)"


@needs_node
def test_label_chips_never_cover_each_other_and_stay_in_their_tile():
    for case, boxes in zip(TILES, _shipped()["tiles"], strict=True):
        tile = case["tile"]
        assert [(b["width"], b["height"]) for b in boxes] == [(c["width"], c["height"]) for c in case["chips"]]
        for i, a in enumerate(boxes):
            assert 0 <= a["x"] and a["x"] + a["width"] <= tile["width"] + 1e-9
            assert 0 <= a["y"] and a["y"] + a["height"] <= tile["height"] + 1e-9
            for b in boxes[i + 1:]:
                assert (
                    a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"]
                    or a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"]
                ), (a, b)
    # The first chip keeps its place just above its mask: 4 px over the wax candle's top edge, centred on it.
    first, tile = _shipped()["tiles"][0][0], TILES[0]["tile"]
    assert first["y"] == pytest.approx(360 / 960 * tile["height"] - 21 - 4)
    assert first["x"] + first["width"] / 2 == pytest.approx(230 / 1280 * tile["width"])
    tile_ts = _function(MASKS, "function maskTile(")
    assert "placeChips(drawn.map(([mask]) => bounds(mask.polygons)), sizes, photoSize, tileSize)" in tile_ts


# --- No answer anywhere ------------------------------------------------------------------------------------------


def test_the_build_view_of_a_sentinel_room_carries_no_answer_and_the_page_reads_nothing_else(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    view = to_build_view(room, done_job(room)).model_dump_json()
    for sentinel in (SENTINEL_CODE, *SENTINEL_IX):
        assert sentinel not in view
    # Every label the overlays draw and every Lock type the graph names comes from that same projection.
    data = json.loads(view)
    assert {mask["label"] for photo in data["photos"] for mask in photo["masks"]} <= {i.label for i in room.interactables}
    modules = {"build-view.ts": _ts("build-view.ts"), "puzzle-graph.ts": GRAPH, "graph-layout.ts": LAYOUT,
               "mask-overlays.ts": MASKS, "chip-layout.ts": CHIPS}
    for path, text in modules.items():
        code = _code(text)
        assert not re.search(r"solution|answer|clue", code, re.IGNORECASE), path
        assert not re.search(r"\b(getRoom|listRooms|getSession|startSession)\b", code), f"{path} requests a Room"


# --- Accessibility floor -----------------------------------------------------------------------------------------


def test_every_node_and_chip_shows_the_focus_ring_with_its_inner_ring():
    rules = _css("components/puzzle-graph.css")
    # The paper shadow would hide the global inner ring, so the node's focus rule lays it back on top.
    assert rules[".graph-node:focus-visible"]["box-shadow"].startswith("0 0 0 2px var(--focus-ring-inner),")
    # On the Exit the ring clears the 3 px double ring, which sits 3 px outside the node.
    assert rules[".graph-node-exit:focus-visible"] == {"outline-offset": "8px"}
    masks = (COMPONENTS / "mask-overlays.css").read_text()
    assert "outline" not in masks and "box-shadow" not in masks, "the chip keeps the global focus ring"
    # A focused chip and its ring sit over any neighbouring chip.
    assert _css("components/mask-overlays.css")[".mask-chip:focus-visible"] == {"z-index": "1"}


def test_graph_and_chip_text_and_markers_meet_aa():
    parchment = _hex(PROPS["parchment"])[0]
    for ink in ("graph-node-ink", "success-ink", "wrong-ink", "ink-muted", "lamp-ink", "ink"):
        assert contrast(_hex(PROPS[ink])[0], parchment) >= 4.5, ink
    chrome = _hex(PROPS["chrome"])[0]
    assert contrast(_hex(PROPS["graph-edge"])[0], chrome) >= 3.0, "graph-edge on chrome (non-text)"
    assert contrast(_hex(PROPS["lamp"])[0], _hex(PROPS["hotspot-halo"])[0]) >= 3.0, "lamp line on its halo"
    assert contrast(_hex(PROPS["focus-ring"])[0], chrome) >= 3.0
    # The fill is lamp at 25%: a tint over the photo, never text.
    assert _over("mask-overlay-fill", chrome) != chrome


def test_the_graph_and_overlays_add_no_motion():
    for path, text in source_css().items():
        if "puzzle-graph" in path or "mask-overlays" in path:
            assert not re.search(r"transition|animation|@keyframes", text), path
    assert all("animate(" not in text for text in (GRAPH, LAYOUT, MASKS, CHIPS))
