"""Story 1.15: `scripts/schema.py` writes the `GET /schema` body to `web/types/schema.json`, the input `npm run types` compiles (AD-2)."""

import importlib.util
import json
from pathlib import Path

import pytest

from src.api.app import api_schema

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/schema.py"


def _load():
    spec = importlib.util.spec_from_file_location("schema_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _load()


def test_writes_the_get_schema_body_with_a_trailing_newline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target = tmp_path / "web/types/schema.json"
    monkeypatch.setattr(script, "SCHEMA_JSON", target)
    monkeypatch.setattr(script, "REPO", tmp_path)
    script.main()
    text = target.read_text(encoding="utf-8")
    assert json.loads(text) == api_schema()
    assert text == json.dumps(api_schema(), indent=2, ensure_ascii=False) + "\n"


def test_writes_into_web_types():
    assert script.SCHEMA_JSON == REPO / "web/types/schema.json"
