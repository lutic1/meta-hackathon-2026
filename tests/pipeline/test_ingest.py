"""Story 2.10: ingest validates the upload before any job exists and stores the accepted bytes as uploaded (AD-7, AD-13)."""

import hashlib
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from src.domain.schema import ErrorEnvelope, Photo
from src.infra.local import DiskArtifactStore
from src.pipeline.build import error_detail
from src.pipeline.ingest import (
    LONG_EDGE,
    MAX_DOWNSCALE_BYTES,
    MAX_ORIGINAL_BYTES,
    MAX_PHOTOS,
    MAX_UPLOAD_BYTES,
    PHOTOS_FILE,
    IngestRefused,
    UnsupportedImage,
    Upload,
    UploadTooLarge,
    photo_keys,
    read_photos,
    store_upload,
    validate_upload,
)
from tests.pipeline.uploads import (
    claiming_pixels,
    image_bytes,
    make_uploads,
    mpo_bytes,
    padded,
)
from tests.test_gitignore import _ignored

ROOM = "room_01ARZ3NDEKTSV4RRFFQ69G5FAV"
HEIC = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 64


@pytest.fixture(scope="module")
def uploads() -> list[Upload]:
    return make_uploads(6)


# --- Validation: the count, JPEG by bytes, the 1280 px long edge and the orientation ---


def test_six_to_ten_jpeg_photos_with_a_1280_px_long_edge_pass(uploads):
    validate_upload(uploads)
    validate_upload(make_uploads(10))


@pytest.mark.parametrize("count", [0, 5, 11])
def test_a_count_outside_6_to_10_is_refused_with_photo_count(count):
    with pytest.raises(IngestRefused, match="6 to 10") as info:
        validate_upload(make_uploads(count))
    assert info.value.code == "photo_count"


def test_a_multi_frame_mpo_is_a_jpeg_by_bytes_and_passes(uploads):
    original = mpo_bytes(2560, 1920)
    assert original[:2] == b"\xff\xd8" and Image.open(BytesIO(original)).format == "MPO"
    validate_upload([Upload(uploads[0].downscale, original), *uploads[1:]])
    validate_upload([Upload(mpo_bytes(LONG_EDGE, 960), uploads[0].original), *uploads[1:]])


@pytest.mark.parametrize("what", ["photo 4", "original 4"])
def test_a_header_claiming_more_pixels_than_pillow_reads_raises_unsupported_image(uploads, what):
    bomb = claiming_pixels(uploads[4].original, 16320, 12240)
    bad = [*uploads[:4], Upload(bomb, uploads[4].original) if what == "photo 4" else Upload(uploads[4].downscale, bomb), *uploads[5:]]
    with pytest.raises(UnsupportedImage, match=f"{what} claims more than") as info:
        validate_upload(bad)
    assert info.value.code == "unsupported_image"


def test_a_png_downscale_named_jpg_raises_unsupported_image(uploads):
    png = image_bytes(LONG_EDGE, 960, format="PNG")
    bad = [*uploads[:5], Upload(png, uploads[5].original)]
    with pytest.raises(UnsupportedImage, match="PNG") as info:
        validate_upload(bad)
    assert info.value.code == "unsupported_image"


def test_a_heic_original_raises_unsupported_image(uploads):
    bad = [Upload(uploads[0].downscale, HEIC), *uploads[1:]]
    with pytest.raises(UnsupportedImage, match="original 0"):
        validate_upload(bad)


def test_a_png_original_raises_unsupported_image(uploads):
    bad = [*uploads[:3], Upload(uploads[3].downscale, image_bytes(2560, 1920, format="PNG")), *uploads[4:]]
    with pytest.raises(UnsupportedImage, match="original 3"):
        validate_upload(bad)


@pytest.mark.parametrize("size", [(1024, 768), (1600, 1200), (1280, 1600)])
def test_a_downscale_whose_long_edge_is_not_1280_is_refused_with_bad_downscale(uploads, size):
    bad = [*uploads[:5], Upload(image_bytes(*size), uploads[5].original)]
    with pytest.raises(IngestRefused, match="long edge") as info:
        validate_upload(bad)
    assert info.value.code == "bad_downscale"


def test_a_downscale_with_an_orientation_tag_other_than_1_is_refused_with_bad_downscale(uploads):
    bad = [Upload(image_bytes(LONG_EDGE, 960, orientation=6), uploads[0].original), *uploads[1:]]
    with pytest.raises(IngestRefused, match="orientation 6") as info:
        validate_upload(bad)
    assert info.value.code == "bad_downscale"


def test_an_orientation_tag_of_1_passes(uploads):
    validate_upload([Upload(image_bytes(LONG_EDGE, 960, orientation=1), uploads[0].original), *uploads[1:]])


def test_the_count_is_checked_before_the_bytes():
    with pytest.raises(IngestRefused, match="6 to 10"):
        validate_upload([Upload(HEIC, HEIC)] * 3)


def test_each_refusal_fits_the_error_envelope_at_stage_ingest(uploads):
    refusals = {
        "photo_count": make_uploads(5),
        "unsupported_image": [Upload(HEIC, uploads[0].original), *uploads[1:]],
        "bad_downscale": [Upload(image_bytes(640, 480), uploads[0].original), *uploads[1:]],
    }
    for code, bad in refusals.items():
        with pytest.raises((IngestRefused, UnsupportedImage)) as info:
            validate_upload(bad)
        envelope = ErrorEnvelope(error=error_detail(info.value, "ingest"))
        assert (envelope.error.code, envelope.error.stage, envelope.error.status) == (code, "ingest", None)
        assert envelope.error.message


def test_validation_touches_no_store(tmp_path, uploads):
    root = tmp_path / "rooms"
    DiskArtifactStore(root)
    validate_upload(uploads)
    with pytest.raises(IngestRefused):
        validate_upload(make_uploads(4))
    assert not root.exists()



# --- Byte caps: 2 MiB a downscale, 20 MiB an original (item 40) ---


def test_the_body_cap_is_ten_photos_at_both_file_caps_plus_1_mib_of_multipart_overhead():
    assert (MAX_DOWNSCALE_BYTES, MAX_ORIGINAL_BYTES) == (2 * 2**20, 20 * 2**20)
    assert MAX_UPLOAD_BYTES == MAX_PHOTOS * (MAX_DOWNSCALE_BYTES + MAX_ORIGINAL_BYTES) + 2**20


def test_a_downscale_and_an_original_exactly_at_their_caps_pass(uploads):
    at_caps = Upload(padded(uploads[0].downscale, MAX_DOWNSCALE_BYTES), padded(uploads[0].original, MAX_ORIGINAL_BYTES))
    validate_upload([at_caps, *uploads[1:]])


@pytest.mark.parametrize("over", ["downscale", "original"])
def test_a_file_one_byte_over_its_cap_is_refused_with_upload_too_large_at_ingest(uploads, over):
    downscale, original = uploads[3].downscale, uploads[3].original
    if over == "downscale":
        downscale = padded(downscale, MAX_DOWNSCALE_BYTES + 1)
    else:
        original = padded(original, MAX_ORIGINAL_BYTES + 1)
    with pytest.raises(UploadTooLarge) as info:
        validate_upload([*uploads[:3], Upload(downscale, original), *uploads[4:]])
    detail = error_detail(info.value, "ingest")
    assert (detail.code, detail.stage) == ("upload_too_large", "ingest")
    assert detail.message == str(UploadTooLarge())  # fixed: nothing the client sent is echoed

# --- Storing: byte for byte, hashed from the stored downscale, in upload order ---


def test_both_files_are_stored_byte_for_byte_under_rooms_and_hashed_from_the_downscale(tmp_path, uploads):
    root = tmp_path / "rooms"
    store = DiskArtifactStore(root)
    photos = store_upload(uploads, ROOM, store)
    assert len(photos) == 6
    for index, (upload, photo) in enumerate(zip(uploads, photos, strict=True)):
        downscaled_path, original_path = photo_keys(ROOM, index)
        assert (photo.downscaled_path, photo.original_path) == (downscaled_path, original_path)
        assert (root / downscaled_path).read_bytes() == upload.downscale
        assert (root / original_path).read_bytes() == upload.original
        assert photo.hash == hashlib.sha256(upload.downscale).hexdigest()
        assert photo.size == len(upload.downscale)
        assert downscaled_path.startswith(f"{ROOM}/") and original_path.startswith(f"{ROOM}/")
    assert all(path.is_relative_to(root) for path in tmp_path.rglob("*") if path.is_file())


def test_the_photo_records_are_an_artifact_the_next_stage_reads_back(tmp_path, uploads):
    store = DiskArtifactStore(tmp_path / "rooms")
    photos = store_upload(uploads, ROOM, store)
    assert read_photos(ROOM, store) == photos
    assert (tmp_path / "rooms" / ROOM / PHOTOS_FILE).exists()
    assert all(isinstance(photo, Photo) for photo in photos)
    assert store.read(photos[2].downscaled_path) == uploads[2].downscale


def test_the_stored_hashes_differ_per_photo_and_follow_upload_order(tmp_path, uploads):
    store = DiskArtifactStore(tmp_path / "rooms")
    reversed_photos = store_upload(list(reversed(uploads)), ROOM, store)
    hashes = [hashlib.sha256(upload.downscale).hexdigest() for upload in reversed(uploads)]
    assert [photo.hash for photo in reversed_photos] == hashes
    assert len(set(hashes)) == 6


def test_the_stored_photo_paths_are_git_ignored():
    downscaled_path, original_path = photo_keys(ROOM, 0)
    assert _ignored(str(Path("rooms") / downscaled_path)) and _ignored(str(Path("rooms") / original_path))
