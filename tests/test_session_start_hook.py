"""The cloud SessionStart hook: registered, a no-op locally, and the cloud steps as written."""

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude/hooks/session-start.sh"


def test_hook_is_registered_for_startup_and_resume():
    settings = json.loads((REPO / ".claude/settings.json").read_text())
    entries = settings["hooks"]["SessionStart"]
    assert [e["matcher"] for e in entries] == ["startup|resume"]
    commands = [h["command"] for h in entries[0]["hooks"]]
    assert commands == ['bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/session-start.sh']
    assert HOOK.exists()


def test_hook_does_nothing_outside_cloud_sessions(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_REMOTE"}
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)  # an empty dir: any step that ran would fail loudly
    result = subprocess.run(["bash", str(HOOK)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""
    assert list(tmp_path.iterdir()) == []


def test_hook_cloud_steps_are_the_template():
    text = HOOK.read_text()
    assert '[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0' in text
    assert 'source "$NVM_DIR/nvm.sh" --no-use' in text
    assert "nvm install 24" in text and 'echo "export PATH=\\"$NODE24_BIN:\\$PATH\\"" >> "$CLAUDE_ENV_FILE"' in text
    assert 'if [ -f uv.lock ]; then uv sync --locked -q || echo "session-start: uv sync --locked failed' in text
    assert "web/node_modules/.package-lock.json -nt web/package-lock.json" in text
    assert 'npm ci --no-audit --no-fund --loglevel=error) || echo "session-start: npm ci failed' in text
    assert "python3 scripts/doctor.py --cloud || true" in text
