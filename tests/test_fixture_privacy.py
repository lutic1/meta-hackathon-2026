"""Story 2.9: a recorded fixture holds the response only; no file under `tests/fixtures` carries a `data:` URL or JPEG bytes."""

import io
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests/fixtures"
FORBIDDEN = (b"data:image", b"\xff\xd8\xff")


def offenders(root: Path) -> list[str]:
    """Every file under `root` holding a forbidden marker, as `<path>: <marker>`."""
    found = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        data = path.read_bytes()
        found.extend(f"{path.relative_to(root)}: {marker!r}" for marker in FORBIDDEN if marker in data)
    return found


def test_no_file_under_tests_fixtures_holds_a_data_url_or_jpeg_magic_bytes():
    assert any(p.suffix == ".json" for p in (FIXTURES / "providers").rglob("*"))
    assert offenders(FIXTURES) == []


def test_the_scan_names_a_planted_data_url_and_a_planted_jpeg(tmp_path):
    (tmp_path / "providers/x").mkdir(parents=True)
    (tmp_path / "providers/x/clean.json").write_text('{"model": "x", "status": 200, "body": {"ok": true}}\n')
    (tmp_path / "providers/x/leak.json").write_text('{"body": {"url": "data:image/jpeg;base64,/9j/"}}\n')
    out = io.BytesIO()
    Image.new("RGB", (8, 8)).save(out, format="JPEG")
    (tmp_path / "photo.jpg").write_bytes(out.getvalue())
    assert offenders(tmp_path) == ["photo.jpg: b'\\xff\\xd8\\xff'", "providers/x/leak.json: b'data:image'"]
