"""Story 2.13: mask selection and box conversion as pure domain functions (AD-11, AD-18)."""

import ast
import math
import sys
from pathlib import Path

from pydantic import TypeAdapter

from src.domain import masks
from src.domain.masks import (
    MAX_INTERACTABLES,
    Selection,
    box_polygon,
    box_to_frame,
    cap_by_confidence,
    iou_with_box,
    select_instances,
    simplify,
)
from src.domain.schema import ArchitectCandidate, Box, FindSolution, Interactable, Polygon

W, H = 1280, 960
FRAME_AREA = W * H
ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def square(x0: float, y0: float, x1: float, y1: float) -> Polygon:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def circle(cx: float, cy: float, r: float, n: int = 120) -> Polygon:
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def candidate(confidence: float, label: str = "lamp") -> ArchitectCandidate:
    return ArchitectCandidate(label=label, plural=False, photo=0, box=(0, 0, 100, 100), attributes=[], confidence=confidence)


# --- Box conversion --------------------------------------------------------


def test_grid_box_becomes_frame_pixels():
    assert box_to_frame((0, 0, 1000, 1000), W, H) == (0, 0, W, H)
    assert box_to_frame((250, 500, 750, 1000), W, H) == (320, 480, 960, 960)
    assert TypeAdapter(Box).validate_python(box_to_frame((100, 100, 300, 300), W, H)) == (128, 96, 384, 288)


def test_coordinates_outside_the_frame_are_clamped():
    assert box_to_frame((-50, -10, 1100, 1200), W, H) == (0, 0, W, H)
    assert box_to_frame((1000, 1000, 1000, 1000), 640, 480) == (640, 480, 640, 480)


# --- Selection -------------------------------------------------------------


def test_singular_label_keeps_the_best_iou_mask():
    box = box_to_frame((100, 100, 300, 300), W, H)  # 128,96 .. 384,288
    best = square(130, 100, 380, 285)
    overlapping = square(300, 200, 600, 500)
    elsewhere = square(700, 500, 1100, 900)
    picked = select_instances([elsewhere, overlapping, best], box, W, H, plural=False)
    assert picked == Selection(polygons=[best], instances=1)
    assert iou_with_box(best, box) > iou_with_box(overlapping, box) > iou_with_box(elsewhere, box)


def test_plural_label_groups_every_mask_above_iou_0_2_as_instances():
    box = box_to_frame((100, 100, 400, 500), W, H)  # 128,96 .. 512,480
    books = [square(128 + 96 * i, 96, 224 + 96 * i, 480) for i in range(4)]  # IoU 0.25 each
    stray = square(600, 600, 900, 900)
    picked = select_instances([stray, *books], box, W, H, plural=True)
    assert picked.instances == 4 and picked.polygons == books
    assert all(iou_with_box(b, box) > 0.2 for b in books) and iou_with_box(stray, box) == 0


def test_plural_label_with_nothing_above_0_2_falls_back_to_the_best_mask():
    box = box_to_frame((100, 100, 400, 500), W, H)
    thin = [square(128 + 64 * i, 96, 160 + 64 * i, 480) for i in range(6)]  # IoU 1/12 each
    best = square(130, 100, 300, 470)
    picked = select_instances([*thin, best], box, W, H, plural=True)
    assert picked == Selection(polygons=[best], instances=1)


def test_a_speck_under_both_floors_is_dropped_and_the_box_stands_in():
    box = box_to_frame((100, 100, 300, 300), W, H)  # 256 x 192, 49,152 px
    speck = square(130, 100, 150, 120)  # 400 px, under 1% of the frame and under 10% of the box
    assert abs(masks.area(speck)) < 0.01 * FRAME_AREA and abs(masks.area(speck)) < 0.1 * 256 * 192
    assert select_instances([speck], box, W, H, plural=False) == Selection(polygons=[box_polygon(box)], instances=1)


def test_a_mask_under_one_percent_of_the_frame_but_over_a_tenth_of_its_small_box_is_kept():
    box = (146.0, 991.0, 234.0, 1106.0)  # 88 x 115, a floor vent's size
    vent = square(150, 995, 230, 1100)  # 8,400 px, under 1% of 1,228,800
    assert abs(masks.area(vent)) < 0.01 * FRAME_AREA
    assert select_instances([vent], box, H, W, plural=False).polygons == [vent]


def test_a_mask_under_a_tenth_of_a_large_box_and_under_one_percent_of_the_frame_is_dropped():
    box = box_to_frame((100, 100, 600, 700), W, H)  # 640 x 576, 368,640 px
    small = square(130, 100, 230, 200)  # 10,000 px, under both floors
    over_one_percent = square(130, 100, 250, 210)  # 13,200 px, over 1% of the frame
    assert select_instances([small], box, W, H, plural=False) == Selection(polygons=[box_polygon(box)], instances=1)
    assert select_instances([small, over_one_percent], box, W, H, plural=False).polygons == [over_one_percent]


def test_a_small_object_like_the_floor_vent_keeps_its_sam_outline_offset_from_its_box():
    box = (146.0, 991.0, 234.0, 1106.0)  # the Architect box sits above and left of the real vent
    vent = square(170, 1015, 250, 1125)  # SAM's vent, down and right, overlapping the box
    assert 0 < iou_with_box(vent, box) and abs(masks.area(vent)) < 0.01 * 960 * 1280
    picked = select_instances([vent], box, 960, 1280, plural=False)
    assert picked == Selection(polygons=[vent], instances=1)
    assert picked.polygons != [box_polygon(box)]


def test_no_mask_gives_the_box_rectangle_as_the_single_unflagged_polygon():
    box = box_to_frame((100, 100, 300, 300), W, H)
    for polygons in (None, []):
        picked = select_instances(polygons, box, W, H, plural=True)
        assert picked.model_dump() == {"polygons": [[(128, 96), (384, 96), (384, 288), (128, 288)]], "instances": 1}
    from_mask = select_instances([square(130, 100, 380, 285)], box, W, H, plural=False)
    assert type(picked.polygons[0]) is type(from_mask.polygons[0]) and len(picked.polygons[0]) == 4
    assert TypeAdapter(list[Polygon]).validate_python(picked.polygons) == picked.polygons


def test_fallback_polygon_fits_an_interactable_that_a_find_puzzle_can_target():
    box = box_to_frame((100, 100, 300, 300), W, H)
    picked = select_instances(None, box, W, H, plural=False)
    ix = Interactable(id=f"ix_{ULID}", label="rug", photo=0, box=box, polygons=picked.polygons,
                      instances=picked.instances, attributes=[])
    assert FindSolution(lock_type="find", target=ix.id).target == ix.id
    assert ix.polygons == [box_polygon(box)]


# --- The 12 cap --------------------------------------------------------------


def test_more_than_12_candidates_keep_the_12_most_confident():
    confidences = [0.5, 0.9, 0.1, 0.8, 0.3, 0.7, 0.95, 0.2, 0.6, 0.4, 0.85, 0.15, 0.75, 0.65]
    candidates = [candidate(c, label=f"object {i}") for i, c in enumerate(confidences)]
    kept = cap_by_confidence(candidates, lambda c: c.confidence)
    assert MAX_INTERACTABLES == 12 and len(kept) == 12
    assert [c.confidence for c in kept] == sorted(confidences, reverse=True)[:12]
    assert {c.label for c in kept} == {c.label for c in candidates} - {"object 2", "object 11"}
    assert kept == cap_by_confidence(candidates, lambda c: c.confidence)


def test_cap_keeps_at_most_12_and_leaves_ties_in_list_position():
    few = [candidate(0.5, label=f"object {i}") for i in range(5)]
    assert cap_by_confidence(few, lambda c: c.confidence) == few
    paired = [(c, i) for i, c in enumerate([candidate(0.5)] * 13)]
    assert [i for _, i in cap_by_confidence(paired, lambda p: p[0].confidence)] == list(range(12))


# --- Simplification --------------------------------------------------------


def test_simplify_never_adds_vertices_keeps_at_least_3_and_stays_inside_the_frame():
    dense = circle(640, 480, 200)
    simple = simplify(dense, W, H)
    assert 3 <= len(simple) < len(dense) and set(simple) <= set(dense)
    triangle = [(10.0, 10.0), (100.0, 10.0), (10.0, 100.0)]
    assert simplify(triangle, W, H) == triangle
    assert simplify(square(0, 0, 50, 50), W, H) == square(0, 0, 50, 50)
    spilling = [(-5.0, -5.0), (1300.0, -5.0), (1300.0, 1000.0), (-5.0, 1000.0)]
    assert simplify(spilling, W, H) == square(0, 0, W, H)


def test_selected_polygons_are_simplified_and_inside_the_frame():
    box = box_to_frame((400, 400, 700, 700), W, H)
    blob = circle(704, 528, 190)
    picked = select_instances([blob], box, W, H, plural=False)
    (polygon,) = picked.polygons
    assert 3 <= len(polygon) < len(blob)
    assert all(0 <= x <= W and 0 <= y <= H for x, y in polygon)
    assert abs(masks.area(polygon)) > 0.9 * abs(masks.area(blob))


# --- Purity and identity ---------------------------------------------------


def test_selection_carries_no_id_and_no_label():
    assert set(Selection.model_fields) == {"polygons", "instances"}
    assert not {"id", "label", "object_id"} & set(Selection.model_fields)
    picked = select_instances([square(130, 100, 380, 285)], box_to_frame((100, 100, 300, 300), W, H), W, H, False)
    assert "id" not in picked.model_dump_json()


def test_masks_imports_only_stdlib_and_pydantic():
    path = Path(masks.__file__)
    tops: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            tops.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0 and node.module, ast.dump(node)
            tops.add(node.module.split(".")[0])
    assert tops and tops <= set(sys.stdlib_module_names) | {"pydantic"}, tops
