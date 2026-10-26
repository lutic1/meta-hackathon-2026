"""The ingest stage (AD-7): the photos exactly as uploaded, checked before any job exists.

`validate_upload` is what `POST /builds` calls first: the count (6 to 10,
else `photo_count`), JPEG by bytes for the downscale and the original alike
(anything else raises `UnsupportedImage`, code `unsupported_image`; a
multi-frame MPO, which phone cameras write as a JPEG with a depth or
thumbnail frame, counts as JPEG, and a header claiming more pixels than
Pillow reads does not), and a downscale whose long edge is 1280 px with no
EXIF orientation other than 1 (else `bad_downscale`). A refusal is raised
before anything is stored, so no job is created or queued for it (AD-13).
`store_upload` then writes each downscale and original byte for byte under
`<room_id>/` and records the photos, `hash` being the sha256 of the stored
downscale, so every model call, cache key and mask reads the same bytes.
Nothing here re-encodes an image: Pillow reads the header only.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from PIL import Image, UnidentifiedImageError
from pydantic import TypeAdapter

from src.domain.schema import Photo, RoomId
from src.pipeline.ports import ArtifactStore

MIN_PHOTOS, MAX_PHOTOS = 6, 10
LONG_EDGE = 1280
ORIENTATION_TAG = 0x0112
PHOTOS_FILE = "photos.json"
"""The ingest artifact under `<room_id>/`: the stored `Photo` records in upload order."""
PHOTOS = TypeAdapter(list[Photo])
JPEG_FORMATS = frozenset({"JPEG", "MPO"})
"""What Pillow reports for a JPEG by bytes: `MPO` is a JPEG carrying more than one frame."""

IngestCode = Literal["photo_count", "bad_downscale"]


class UnsupportedImage(Exception):
    """A file that is not a JPEG by its bytes, or claims too many pixels to read (AD-7, AD-13); code `unsupported_image`."""

    code = "unsupported_image"


class IngestRefused(Exception):
    """A request refusal outside the typed classes (AD-13): 422 `photo_count` or 422 `bad_downscale`."""

    def __init__(self, code: IngestCode, message: str) -> None:
        super().__init__(message)
        self.code: IngestCode = code


@dataclass(frozen=True)
class Upload:
    """One photo as `POST /builds` receives it: the client-made downscale and the original."""

    downscale: bytes
    original: bytes


def _open_jpeg(data: bytes, what: str) -> Image.Image:
    """The image header of a JPEG; any other format, by its bytes, or a pixel count past Pillow's limit raises `UnsupportedImage`."""
    try:
        image = Image.open(BytesIO(data))
    except UnidentifiedImageError:
        raise UnsupportedImage(f"{what} is not a JPEG") from None
    except Image.DecompressionBombError:
        raise UnsupportedImage(f"{what} claims more than {Image.MAX_IMAGE_PIXELS} pixels") from None
    if image.format not in JPEG_FORMATS:
        raise UnsupportedImage(f"{what} is {image.format}, not a JPEG")
    return image


def validate_upload(uploads: Sequence[Upload]) -> None:
    """Refuse the upload before any job exists: the count, JPEG by bytes, the 1280 px long edge and the orientation."""
    if not MIN_PHOTOS <= len(uploads) <= MAX_PHOTOS:
        raise IngestRefused("photo_count", f"Keyframe needs {MIN_PHOTOS} to {MAX_PHOTOS} JPEG photos, got {len(uploads)}")
    for index, upload in enumerate(uploads):
        downscale = _open_jpeg(upload.downscale, f"photo {index}")
        _open_jpeg(upload.original, f"original {index}")
        if max(downscale.size) != LONG_EDGE:
            raise IngestRefused("bad_downscale", f"photo {index} has a long edge of {max(downscale.size)} px, not {LONG_EDGE}")
        orientation = downscale.getexif().get(ORIENTATION_TAG, 1)
        if orientation != 1:
            raise IngestRefused("bad_downscale", f"photo {index} carries EXIF orientation {orientation}, not 1")


def photo_keys(room_id: RoomId, index: int) -> tuple[str, str]:
    """The artifact keys of photo `index`: its downscale and its original."""
    return f"{room_id}/photos/{index}.jpg", f"{room_id}/originals/{index}.jpg"


def store_upload(uploads: Sequence[Upload], room_id: RoomId, artifacts: ArtifactStore) -> list[Photo]:
    """Store an accepted upload byte for byte under `<room_id>/` and persist the `Photo` records in upload order."""
    photos: list[Photo] = []
    for index, upload in enumerate(uploads):
        downscaled_path, original_path = photo_keys(room_id, index)
        artifacts.put(downscaled_path, upload.downscale)
        artifacts.put(original_path, upload.original)
        photos.append(Photo(
            hash=hashlib.sha256(upload.downscale).hexdigest(),
            size=len(upload.downscale),
            downscaled_path=downscaled_path,
            original_path=original_path,
        ))
    artifacts.put(f"{room_id}/{PHOTOS_FILE}", PHOTOS.dump_json(photos))
    return photos


def read_photos(room_id: RoomId, artifacts: ArtifactStore) -> list[Photo]:
    """The `Photo` records ingest stored for `room_id`, for the stages that read the photo bytes."""
    return PHOTOS.validate_json(artifacts.read(f"{room_id}/{PHOTOS_FILE}"))
