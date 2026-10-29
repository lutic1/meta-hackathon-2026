"""Mask selection and box conversion for the segment stage (AD-18), pure.

Spark boxes on the 0 to 1000 grid become frame pixels, clamped to the frame;
SAM polygons for one label are selected against that box (schema v1 "SAM mask
selection"), a mask dropped only when under 1% of the frame and under a tenth
of its box; a label with no mask gets its box rectangle as its one polygon
(AD-11); candidates are capped at 12 by Architect confidence. Polygons are in
the pixel space of the stored downscaled 1280 px JPEG, the shapes of
`schema.py`. No id is minted here. This module imports only the standard
library and pydantic (AD-1).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Point = tuple[float, float]
Polygon = list[Point]
Box = tuple[float, float, float, float]
"""`[x0, y0, x1, y1]` in frame pixels."""
GridBox = tuple[int, int, int, int]
"""`[x0, y0, x1, y1]` on the vision call's 0 to 1000 grid."""

GRID = 1000
MIN_AREA_FRACTION = 0.01
MIN_BOX_FRACTION = 0.1
PLURAL_IOU = 0.2
MAX_INTERACTABLES = 12
SIMPLIFY_TOLERANCE_PX = 1.0


class Selection(BaseModel):
    """One label's Hotspot geometry: one polygon per instance, and no id (AD-18)."""

    model_config = ConfigDict(extra="forbid")

    polygons: list[Polygon]
    instances: Annotated[int, Field(ge=1)]


# --- Boxes -----------------------------------------------------------------


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def box_to_frame(box: GridBox, frame_w: int, frame_h: int) -> Box:
    """A Spark box on the 0 to 1000 grid as `[x0, y0, x1, y1]` frame pixels, clamped to the frame."""
    x0, y0, x1, y1 = box
    return (
        _clamp(x0 * frame_w / GRID, 0, frame_w),
        _clamp(y0 * frame_h / GRID, 0, frame_h),
        _clamp(x1 * frame_w / GRID, 0, frame_w),
        _clamp(y1 * frame_h / GRID, 0, frame_h),
    )


def box_polygon(box: Box) -> Polygon:
    """The box rectangle as a polygon, the fallback when SAM yields nothing (AD-11)."""
    x0, y0, x1, y1 = box
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# --- Geometry --------------------------------------------------------------


def area(poly: Polygon) -> float:
    """Signed shoelace area."""
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))


def _at_x(a: Point, b: Point, x: float) -> Point:
    t = (x - a[0]) / (b[0] - a[0])
    return x, a[1] + t * (b[1] - a[1])


def _at_y(a: Point, b: Point, y: float) -> Point:
    t = (y - a[1]) / (b[1] - a[1])
    return a[0] + t * (b[0] - a[0]), y


def clip_to_box(poly: Polygon, box: Box) -> Polygon:
    """Sutherland-Hodgman clip of a polygon to a box."""
    left, top, right, bottom = box
    edges: list[tuple[Callable[[Point], bool], Callable[[Point, Point], Point]]] = [
        (lambda p: p[0] >= left, lambda a, b: _at_x(a, b, left)),
        (lambda p: p[0] <= right, lambda a, b: _at_x(a, b, right)),
        (lambda p: p[1] >= top, lambda a, b: _at_y(a, b, top)),
        (lambda p: p[1] <= bottom, lambda a, b: _at_y(a, b, bottom)),
    ]
    out = poly
    for inside, cross in edges:
        src, out = out, []
        for i, cur in enumerate(src):
            prev = src[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
        if not out:
            break
    return out


def iou_with_box(poly: Polygon, box: Box) -> float:
    """Intersection over union of a polygon and a box."""
    mask_area = abs(area(poly))
    box_area = abs((box[2] - box[0]) * (box[3] - box[1]))
    inter = abs(area(clip_to_box(poly, box)))
    union = mask_area + box_area - inter
    return inter / union if union > 0 else 0.0


# --- Simplification --------------------------------------------------------


def _dist2(a: Point, b: Point) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _rdp(points: Polygon, tolerance: float) -> Polygon:
    (x0, y0), (x1, y1) = points[0], points[-1]
    dx, dy = x1 - x0, y1 - y0
    norm = (dx * dx + dy * dy) ** 0.5 or 1.0
    best, index = 0.0, 0
    for i in range(1, len(points) - 1):
        d = abs(dy * (points[i][0] - x0) - dx * (points[i][1] - y0)) / norm
        if d > best:
            best, index = d, i
    if best <= tolerance:
        return [points[0], points[-1]]
    return _rdp(points[: index + 1], tolerance)[:-1] + _rdp(points[index:], tolerance)


def simplify(poly: Polygon, frame_w: int, frame_h: int, tolerance: float = SIMPLIFY_TOLERANCE_PX) -> Polygon:
    """Ramer-Douglas-Peucker on a closed ring: never adds a vertex, keeps at least 3, all inside the frame."""
    ring = poly
    if len(poly) > 3:
        far = max(range(len(poly)), key=lambda i: _dist2(poly[i], poly[0]))
        ring = _rdp(poly[: far + 1], tolerance)[:-1] + _rdp(poly[far:] + poly[:1], tolerance)[:-1]
        if len(ring) < 3:
            ring = poly
    return [(_clamp(x, 0, frame_w), _clamp(y, 0, frame_h)) for x, y in ring]


# --- Selection (schema v1 "SAM mask selection") ----------------------------


def select_instances(
    polygons: list[Polygon] | None, box: Box, frame_w: int, frame_h: int, plural: bool
) -> Selection:
    """Pick one label's polygons against its converted box; no mask leaves the box rectangle.

    A mask is dropped when it is under 1% of the frame and under a tenth of
    the box's area, so a small object keeps its outline. A singular label keeps the best
    IoU against the box; a plural label keeps every mask with IoU above 0.2,
    falling back to the best one when none passes. The result carries one
    polygon per instance, simplified and clamped to the frame.
    """
    box_area = abs((box[2] - box[0]) * (box[3] - box[1]))
    min_area = min(MIN_AREA_FRACTION * frame_w * frame_h, MIN_BOX_FRACTION * box_area)
    scored = [(iou_with_box(p, box), p) for p in polygons or [] if abs(area(p)) >= min_area]
    kept = [p for iou, p in scored if iou > PLURAL_IOU] if plural else []
    if not kept and scored:
        kept = [max(scored, key=lambda s: s[0])[1]]
    if not kept:
        kept = [box_polygon(box)]
    kept = [simplify(p, frame_w, frame_h) for p in kept]
    return Selection(polygons=kept, instances=len(kept))


def cap_by_confidence[T](items: Iterable[T], confidence: Callable[[T], float]) -> list[T]:
    """At most 12 items, highest Architect confidence first; ties keep their list position."""
    return sorted(items, key=confidence, reverse=True)[:MAX_INTERACTABLES]
