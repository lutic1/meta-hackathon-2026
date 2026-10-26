"""Synthetic uploads for the ingest and build tests: JPEGs drawn with Pillow, never a real room photo."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from src.pipeline.ingest import LONG_EDGE, ORIENTATION_TAG, Upload

COLOURS = ("#d9c6a5", "#b7a98a", "#cfd6dc", "#a8b59a", "#c9b7b0", "#bfc8a0", "#e0d2b8", "#a9b4c2", "#c4a98e", "#9fb3a0")


def image_bytes(width: int, height: int, colour: str = "#d9c6a5", *, format: str = "JPEG", orientation: int | None = None) -> bytes:
    """An encoded image of `width` by `height`; `orientation` writes that EXIF tag."""
    buffer = BytesIO()
    image = Image.new("RGB", (width, height), colour)
    if orientation is None:
        image.save(buffer, format, quality=85)
    else:
        exif = Image.Exif()
        exif[ORIENTATION_TAG] = orientation
        image.save(buffer, format, quality=85, exif=exif.tobytes())
    return buffer.getvalue()


def make_uploads(count: int = 6, *, portrait_at: int = 2) -> list[Upload]:
    """`count` accepted uploads: a 1280 px downscale (one portrait) and a 2560 px original, each a distinct JPEG."""
    uploads = []
    for index in range(count):
        colour = COLOURS[index % len(COLOURS)]
        width, height = (960, LONG_EDGE) if index == portrait_at else (LONG_EDGE, 960)
        uploads.append(Upload(image_bytes(width, height, colour), image_bytes(width * 2, height * 2, colour)))
    return uploads
