# sam-3.1 masks to Keyframe polygons

The code blocks marked `python` here are executed and tested by `scripts/selfcheck.py`.

## What a mask is

- Each record is an object id, then one box, then one mask. The parser turns that into a `SegmentationBoxRecord`, then a `SegmentationMaskRecord` with the same half-open `bounds`. On the wire `x2` and `y2` are inclusive. The parser sets `right = x2 + 1` and `bottom = y2 + 1`.
- The mask header is `data=H,W,<marker>payload`, height first. Read `record.mask.height` and `record.mask.width` from each mask. Never assume the frame size.
- **The raster covers the box, not the frame.** In every documented example, H equals the box height and W equals the box width. Examples:
  - the 537x561 image: box x 353..453 gives a 46x101 mask;
  - the cookbook's live `duck` run: box width 174, height 203, and the mask is 174 by 203;
  - Meta's captured live case: an 11x11 box on a 1440x900 frame gives an 11x11 mask.

  So a mask maps to the frame by offsetting it to `(bounds.left, bounds.top)`. The code below also scales it by `box size / mask size`, so it stays correct if a mask ever arrives at a different resolution.
- Ids are strings, stable, and not dense (`"0"`, `"2"`). Key everything by `object_id`, never by position.
- The payload is base85, not base64. Pass it to the decoders unchanged. The marker is `~` for lossless (the default) or `!` for one_bit. Read `record.mask.encoding` rather than assuming which one you asked for.
- What the decoders return:
  - `decode_mask_to_raster(mask)`: row-major `bytes` of 0 and 1, length `height * width`.
  - `decode_mask_to_rle(mask)`: a COCO `RLEObject(size=(height, width), counts=str)` in column-major order. It is compact enough for a cache or a Dict.
  - `decode_mask_to_svg_path(mask)`: an `M`/`L`/`Z` path in mask raster coordinates, with pixel centers on integers (an edge sits at `-0.5`). No doc states this convention; it was verified by running the parser on the docs' 27x60 mask, where raster columns 0 to 59 give SVG x from -0.5 to 59.5. It can hold several subpaths, and is `""` for an empty mask.
  - On a bad payload, all three raise `InvalidSegmentationMaskError` (code `invalid_mask_payload`).
- Parsed records do not carry the wire `w`/`h` (the source size). Because Keyframe sends the stored 1280 px JPEG, box coordinates are already in frame pixels (AD-18). `result.raw_output` keeps the exact wire text for logging.

## Geometry (`src/domain/masks.py`, pure)

```python
"""Pure geometry for sam-3.1 masks: SVG path to frame polygon, IoU, selection, simplify."""

import re

Point = tuple[float, float]
Polygon = list[Point]
Box = tuple[float, float, float, float]  # left, top, right, bottom (half-open), frame px

_COMMAND = re.compile(r"([MLZ])([^MLZ]*)")


def svg_rings(path: str) -> list[Polygon]:
    rings: list[Polygon] = []
    for command, args in _COMMAND.findall(path):
        if command == "M":
            rings.append([])
        if command in "ML":
            x, y = map(float, args.split())
            rings[-1].append((x, y))
    return rings


def mask_polygon(svg_path: str, bounds: Box, mask_w: int, mask_h: int) -> Polygon | None:
    """Largest ring of one mask, mapped from mask raster to frame pixels."""
    rings = svg_rings(svg_path)
    if not rings:
        return None
    left, top, right, bottom = bounds
    sx, sy = (right - left) / mask_w, (bottom - top) / mask_h
    ring = max(rings, key=lambda r: abs(area(r)))
    return [(left + (x + 0.5) * sx, top + (y + 0.5) * sy) for x, y in ring]


def area(poly: Polygon) -> float:
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))


def clip_to_box(poly: Polygon, box: Box) -> Polygon:
    left, top, right, bottom = box
    edges = [
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


def _at_x(a: Point, b: Point, x: float) -> Point:
    t = (x - a[0]) / (b[0] - a[0])
    return x, a[1] + t * (b[1] - a[1])


def _at_y(a: Point, b: Point, y: float) -> Point:
    t = (y - a[1]) / (b[1] - a[1])
    return a[0] + t * (b[0] - a[0]), y


def iou_with_box(poly: Polygon, box: Box) -> float:
    mask_area = abs(area(poly))
    box_area = (box[2] - box[0]) * (box[3] - box[1])
    inter = abs(area(clip_to_box(poly, box)))
    union = mask_area + box_area - inter
    return inter / union if union > 0 else 0.0


def select_instances(polys: list[Polygon], box: Box, frame_w: int, frame_h: int,
                     plural: bool) -> list[Polygon]:
    """Schema v1 'SAM mask selection' for one label; [] means fall back to the box."""
    min_area = 0.01 * frame_w * frame_h
    scored = [(iou_with_box(p, box), p) for p in polys if abs(area(p)) >= min_area]
    if not scored:
        return []
    if plural:
        grouped = [p for iou, p in scored if iou > 0.2]
        if grouped:
            return grouped
    return [max(scored, key=lambda s: s[0])[1]]


def simplify(poly: Polygon, tolerance: float = 1.0) -> Polygon:
    """Ramer-Douglas-Peucker on a closed ring; keeps at least 3 points."""
    if len(poly) <= 3:
        return poly
    far = max(range(len(poly)), key=lambda i: _dist2(poly[i], poly[0]))
    ring = _rdp(poly[: far + 1], tolerance)[:-1] + _rdp(poly[far:] + poly[:1], tolerance)[:-1]
    return ring if len(ring) >= 3 else poly


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


def _dist2(a: Point, b: Point) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
```

## Adapter side: parsed result to the port's return value

```python
from meta_sam_parser import ImageSegmentationResult, decode_mask_to_svg_path


def polygons_from_result(result: ImageSegmentationResult) -> list[Polygon] | None:
    """One frame-pixel polygon per SAM instance; None when SAM found nothing (AD-5)."""
    polygons = []
    for record in result.records:
        if record.kind != "mask":
            continue
        bounds = (record.bounds.left, record.bounds.top, record.bounds.right, record.bounds.bottom)
        polygon = mask_polygon(decode_mask_to_svg_path(record.mask), bounds,
                               record.mask.width, record.mask.height)
        if polygon is not None:
            polygons.append(simplify(polygon))
    return polygons or None
```

## Selection rules (schema v1, "SAM mask selection")

Run these in the segment stage over each label's polygons, on that label's clearest photo:

1. Drop polygons whose area is under 1% of the frame (`0.01 * W * H` in frame pixels).
2. Singular label: keep the polygon with the best IoU against the vision box. Convert the box from the 0..1000 grid to frame pixels first (AD-18).
3. Plural label: group every polygon with IoU above 0.2 as instances of one interactable (`instances = len(group)`).
4. Nothing left, or `segment` returned `None`: write the box rectangle as the single polygon.
5. Across the room, sort by vision confidence and keep at most 12. Then mint `ix_` ids (AD-18). If fewer than 5 survive, end with `needs_more_photos` before any Riddler call (AD-7).

Choices this code makes that the schema leaves open:

- **One polygon per instance** means the largest SVG subpath. Holes and small islands are dropped.
- **Plural with no polygon above 0.2** falls back to the best single polygon.
- **Simplification tolerance** is 1 px.

**Known issue with rule 3:** one instance's IoU against a box drawn around the whole group is about that instance's share of the box. Five equal books in one box score 0.2 each, so none passes. The selfcheck shows this. If plural rooms come back as single instances, raise it at the schema review. One option is the fraction of each mask inside the box (`intersection / mask area`) instead of IoU.
