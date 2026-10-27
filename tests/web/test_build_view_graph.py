"""FR-38, UX-DR49, UX-DR50, UX-DR67, UX-DR71: the Build view's puzzle graph and mask overlays.

As in test_build_view_surface.py, these checks read the TypeScript and the stylesheets (the client has no test runner);
`npm run build` and `tsc --noEmit` prove they compile. The sentinel check builds the `BuildView` the page renders from a
Room with sentinel solutions, and the client modules are checked to read nothing else.
"""

import json
import re

from src.domain.redact import to_build_view
from src.domain.schema import Room
from tests.domain.test_redact import done_job
from tests.fixtures.rooms import SENTINEL_CODE, SENTINEL_IX, with_sentinel_solutions
from tests.web.design import source_css
from tests.web.test_build_view_surface import COMPONENTS, _code, _css, _ts
from tests.web.test_contrast import PROPS, _hex, _over, contrast

GRAPH = (COMPONENTS / "puzzle-graph.ts").read_text()
MASKS = (COMPONENTS / "mask-overlays.ts").read_text()


def _function(text: str, signature: str) -> str:
    return text.split(signature, 1)[1].split("\n}\n", 1)[0]


# --- Puzzle graph ------------------------------------------------------------------------------------------------


def test_the_graph_sits_at_the_top_of_the_left_column_over_the_mask_overlays():
    view = _ts("build-view.ts")
    assert "left.append(puzzleGraph(state.view), maskOverlays(state.view))" in view
    # The right column comes first in the page for Tab order and is placed in the right third by the stylesheet.
    assert "columns.append(right, left)" in view
    rules = _css("shell.css")
    assert rules[".build-view-left"]["grid-column"] == "1" and rules[".build-view-right"]["grid-column"] == "2"
    assert rules[".build-view-left, .build-view-right"]["grid-row"] == "1"


def test_the_graph_runs_left_to_right_with_the_exit_puzzle_alone_rightmost():
    columns = _function(GRAPH, "function columns(")
    # A Puzzle's column is one past the deepest Puzzle it requires; the Exit takes the column after every other.
    assert "Math.max(-1, ...before.map((required) => level(required, new Set([...path, puzzle.id])))) + 1" in columns
    assert "const exit = Math.max(-1, ...ranks) + 1" in columns
    assert "return ranks.map((rank, index) => (puzzles[index].is_exit ? exit : rank))" in columns
    layout = _function(GRAPH, "export function layoutGraph(")
    assert "x: k * step," in layout


def test_nodes_are_168_by_64_parchment_with_the_order_number_and_lock_type_in_mono_sm():
    assert "export const NODE_WIDTH = 168" in GRAPH and "export const NODE_HEIGHT = 64" in GRAPH
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
    assert "puzzle.requires.flatMap((id) => {" in graph
    assert "svg('line', { class: 'graph-edge', x1, y1, x2, y2, 'marker-end': 'url(#graph-arrowhead)' })" in graph


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


def test_the_graph_fits_its_column_at_1280px():
    constants = {name: int(value) for name, value in re.findall(r"const (STEP_MIN|GAP_MIN) = (\d+)", GRAPH)}
    layout = _function(GRAPH, "export function layoutGraph(")
    assert "Math.max(STEP_MIN, Math.min(STEP_MAX, (width - NODE_WIDTH) / (count - 1)))" in layout
    # Columns closer than a node's width drop into separate bands, so no two nodes overlap.
    assert "Math.ceil((NODE_WIDTH + GAP_MIN) / step)" in layout
    graph_panel = (1280 - 2 * 24 - 24) * 2 / 3 - 2 * 24
    assert (6 - 1) * constants["STEP_MIN"] + 168 <= graph_panel, "a six-deep chain fits the 1280 px left column"
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


# --- No answer anywhere ------------------------------------------------------------------------------------------


def test_the_build_view_of_a_sentinel_room_carries_no_answer_and_the_page_reads_nothing_else(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    view = to_build_view(room, done_job(room)).model_dump_json()
    for sentinel in (SENTINEL_CODE, *SENTINEL_IX):
        assert sentinel not in view
    # Every label the overlays draw and every Lock type the graph names comes from that same projection.
    data = json.loads(view)
    assert {mask["label"] for photo in data["photos"] for mask in photo["masks"]} <= {i.label for i in room.interactables}
    for path, text in (("build-view.ts", _ts("build-view.ts")), ("puzzle-graph.ts", GRAPH), ("mask-overlays.ts", MASKS)):
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
    assert "animate(" not in GRAPH and "animate(" not in MASKS
