"""AR-24: one CI job `check` that installs uv 0.11.32, takes Node from .nvmrc and runs only scripts/check.sh."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github/workflows/ci.yml"
SETUP_UV = "astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0"


def _text() -> str:
    return WORKFLOW.read_text()


def _jobs() -> list[str]:
    """Job names: the keys indented by exactly two spaces after `jobs:`."""
    body = _text().split("\njobs:\n", 1)[1]
    return re.findall(r"^  ([A-Za-z_][\w-]*):$", body, re.MULTILINE)


def _steps() -> list[tuple[str, str]]:
    return re.findall(r"^      - (uses|run): (.*)$", _text(), re.MULTILINE)


def test_triggers_on_master_and_keyframe_pushes_and_pull_requests():
    text = _text()
    assert 'on:\n  push:\n    branches: [master, "keyframe/**"]\n  pull_request:\n' in text
    assert "permissions:\n  contents: read\n" in text
    assert "schedule:" not in text and "workflow_dispatch" not in text


def test_exactly_one_job_check_on_ubuntu_with_timeout_and_mock_provider():
    assert _jobs() == ["check"]
    text = _text()
    assert "    runs-on: ubuntu-latest\n" in text
    assert "    timeout-minutes: 10\n" in text
    assert "    env:\n      MODEL_PROVIDER: mock\n" in text
    assert "strategy:" not in text and "matrix:" not in text


def test_steps_are_checkout_uv_node_then_check_sh():
    assert _steps() == [
        ("uses", "actions/checkout@v7"),
        ("uses", SETUP_UV),
        ("uses", "actions/setup-node@v7"),
        ("run", "bash scripts/check.sh"),
    ]
    text = _text()
    assert 'version: "0.11.32"' in text
    assert "node-version-file: .nvmrc" in text
    assert "setup-python" not in text


def test_npm_cache_lines_only_once_the_web_lock_is_committed():
    text = _text()
    has_cache = "cache: npm" in text and "cache-dependency-path: web/package-lock.json" in text
    assert has_cache == (REPO / "web/package-lock.json").exists()


def test_no_secret_no_deploy_no_cd():
    text = _text()
    assert "secrets." not in text
    assert "modal" not in text.lower() and "deploy" not in text.lower()
    assert "coverage" not in text.lower() and "codecov" not in text.lower()
