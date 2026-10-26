"""AR-29: raw room photos and env files never enter the repo; .env.example lists every key blank."""

import subprocess
from pathlib import Path

import pytest

from src.config import ENV_KEYS, SECRET_KEYS

REPO = Path(__file__).resolve().parents[1]
IGNORED = ("rooms/a.jpg", "rooms/profiles/demo.json", "photos/a.jpg", "captures/a.jpg", "uploads/a.jpg",
           "a.heic", "a.HEIC", ".cache/a", ".env", ".env.local", "keyframe-hosted.env", "spend/ledger.jsonl")


def _ignored(path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO, check=False).returncode == 0


@pytest.mark.parametrize("path", IGNORED)
def test_private_path_is_ignored(path):
    assert _ignored(path), f"{path} is not git-ignored"


def test_env_example_is_not_ignored():
    assert not _ignored(".env.example")


def test_the_daily_ledger_exports_are_not_ignored():
    assert not _ignored("spend/exports/ledger-2026-10-26.json")
    assert _ignored("spend/ledger.jsonl")


def test_gitignore_keeps_the_env_lines():
    lines = (REPO / ".gitignore").read_text().splitlines()
    assert {".env.*", "!.env.example", "*.env"} <= set(lines)


def _example_keys() -> dict[str, str]:
    pairs = {}
    for line in (REPO / ".env.example").read_text().splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            pairs[key.strip()] = value.strip()
    return pairs


def test_env_example_lists_every_settings_key_blank():
    pairs = _example_keys()
    assert set(pairs) == set(ENV_KEYS)
    assert all(value == "" for value in pairs.values()), {k: v for k, v in pairs.items() if v}
    assert {"MODEL_API_KEY", "FAL_KEY"} <= set(pairs)
    assert set(SECRET_KEYS) <= set(pairs)
