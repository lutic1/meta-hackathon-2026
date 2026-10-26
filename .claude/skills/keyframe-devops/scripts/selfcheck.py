#!/usr/bin/env python3
"""Proves references/templates.md works as written. Standard library only.

    python3 .claude/skills/keyframe-devops/scripts/selfcheck.py

Builds a throwaway project in a temp dir from every `<!-- file: ... -->` block in
references/templates.md (plus a stand-in modal_app.py around the Modal image block),
then runs `scripts/check.sh --predeploy` and negative controls (pin drift, a tracked
private file, a .env leaking into module-level Settings, uv_version drift, a dirty tree,
a lost darwin binding). It also runs the SessionStart hook locally (must do nothing) and,
when nvm.sh is available, against an empty NVM_DIR (a fresh container). Needs uv on PATH
and network (the hook downloads Node 24) or warm uv and npm caches. The web part needs
Node 24 on PATH and is skipped, with a note, on another Node major. Never touches the
repo or any account.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATES = (SKILL / "references/templates.md").read_text()

SMOKE_TEST = '''\
import os
import httpx
import pytest


def test_live_host_is_blocked():
    with pytest.raises((httpx.ConnectError, OSError)):
        httpx.get("https://pypi.org/simple/", timeout=5)


def test_mock_transport_still_works():
    t = httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True}))
    assert httpx.Client(transport=t).get("https://api.meta.ai/v1/x").json() == {"ok": True}


def test_env_is_mock_without_secrets():
    assert os.environ["MODEL_PROVIDER"] == "mock" and not os.environ.get("FAL_KEY")
'''
CONFIG_STANDIN = '''\
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    provider: str
    meta_api_key: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(os.environ.get("MODEL_PROVIDER", "mock"), os.environ.get("MODEL_API_KEY") or None)
'''
SETTINGS_TEST = '''\
from src.settings_user import SETTINGS


def test_module_level_settings_is_mock():
    assert SETTINGS.provider == "mock" and SETTINGS.meta_api_key is None
'''
WEB_FILES = {
    "web/tsconfig.json": '{"compilerOptions": {"target": "es2023", "module": "esnext", "lib": ["ES2023", "DOM"],'
                         ' "types": ["vite/client"], "skipLibCheck": true, "moduleResolution": "bundler",'
                         ' "noEmit": true, "noUnusedLocals": true}, "include": ["src"]}\n',
    "web/index.html": '<!doctype html><html><body><div id="app"></div>'
                      '<script type="module" src="/src/main.ts"></script></body></html>\n',
    "web/src/main.ts": 'import * as THREE from "three";\n'
                       'const scene = new THREE.Scene();\n'
                       'document.querySelector<HTMLDivElement>("#app")!.textContent = String(scene.children.length);\n',
}


def sh(cmd: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)


def ok(msg: str) -> None:
    print(f"ok   {msg}")


def expect(cond: bool, msg: str, detail: str = "") -> None:
    if not cond:
        print(f"FAIL {msg}\n{detail[-3000:]}")
        sys.exit(1)
    ok(msg)


def main() -> int:
    blocks = dict(re.findall(r"<!-- file: (\S+) -->\n```[a-z]*\n(.*?)\n```", TEMPLATES, re.S))
    expect({"pyproject.toml", "scripts/check.sh", "tests/conftest.py", ".github/workflows/ci.yml",
            "web/package.json", "web/.npmrc", ".nvmrc", ".python-version"} <= set(blocks),
           f"templates.md has the {len(blocks)} file blocks")
    image = re.search(r"## Modal image.*?```python\n(.*?)\n```", TEMPLATES, re.S).group(1)

    node = sh("node --version", Path.cwd()).stdout.strip()
    with_web = node.startswith("v24.")
    root = Path(tempfile.mkdtemp(prefix="kf-devops-"))
    for rel, text in blocks.items():
        if rel.startswith("web/") and not with_web:
            continue
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text + "\n")
    if with_web:
        for rel, text in WEB_FILES.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
    else:
        print(f"note web steps skipped: node is {node or 'missing'}, not v24")
    (root / "src/api").mkdir(parents=True)
    (root / "src/__init__.py").write_text("")
    (root / "src/api/__init__.py").write_text("")
    (root / "src/api/modal_app.py").write_text(f"import modal\n\n{image}\napp = modal.App('keyframe', image=image, secrets=[secret])\n")
    (root / "tests/test_smoke.py").write_text(SMOKE_TEST)
    (root / "src/config.py").write_text(CONFIG_STANDIN)
    (root / "src/settings_user.py").write_text("from src.config import Settings\n\nSETTINGS = Settings.from_env()\n")
    (root / "tests/test_settings_user.py").write_text(SETTINGS_TEST)
    (root / ".env").write_text("MODEL_PROVIDER=meta\nMODEL_API_KEY=fake-not-a-key\n")  # the Mac's .env, faked
    (root / ".gitignore").write_text(".venv/\nnode_modules/\ndist/\n.env\n.env.*\n!.env.example\n*.env\n"
                                     "__pycache__/\n.pytest_cache/\n")

    if with_web:  # the one-time lock generation from a clean tree, as templates.md says
        r = sh("npm install --no-audit --no-fund", root / "web")
        expect(r.returncode == 0, "web/package-lock.json generated from a clean tree under Node 24", r.stdout + r.stderr)
    r = sh("uv lock -q && git init -q -b master && git add -A && "
           "git -c user.email=s@s -c user.name=s commit -qm base", root)
    expect(r.returncode == 0, "scratch project locks and commits", r.stdout + r.stderr)

    hook = root / ".claude/hooks/session-start.sh"
    cfg = json.loads((root / ".claude/settings.json").read_text())["hooks"]["SessionStart"][0]
    expect(cfg["matcher"] == "startup|resume" and "session-start.sh" in cfg["hooks"][0]["command"],
           ".claude/settings.json registers the hook for startup|resume")
    envfile = root.parent / f"{root.name}-envfile"
    base = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_REMOTE", "CLAUDE_ENV_FILE")}
    r = subprocess.run(["bash", str(hook)], cwd=root, capture_output=True, text=True,
                       env={**base, "CLAUDE_ENV_FILE": str(envfile), "NVM_DIR": str(root / "no-nvm")})
    expect(r.returncode == 0 and not envfile.exists(), "hook does nothing in a local session (no CLAUDE_CODE_REMOTE)",
           r.stdout + r.stderr)
    nvm_sh = Path(os.environ.get("NVM_DIR", "/opt/nvm")) / "nvm.sh"
    if nvm_sh.exists():
        fresh = Path(tempfile.mkdtemp(prefix="kf-nvm-"))
        shutil.copy(nvm_sh, fresh / "nvm.sh")  # a fresh container: nvm.sh, no alias, no versions
        r = subprocess.run(["bash", str(hook)], cwd=root, capture_output=True, text=True,
                           env={**base, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_ENV_FILE": str(envfile),
                                "CLAUDE_PROJECT_DIR": str(root), "NVM_DIR": str(fresh)})
        later = sh(f"bash -c 'source {envfile} && node --version && npm --version'", root)
        expect(r.returncode == 0 and later.stdout.startswith("v24."),
               f"hook on an empty NVM_DIR puts Node 24 on later shells' PATH ({later.stdout.split()[:2]})",
               r.stdout + r.stderr + later.stdout + later.stderr)
        shutil.rmtree(fresh, ignore_errors=True)
        envfile.unlink(missing_ok=True)
        sh("git checkout -q . && git clean -qfd -e .venv -e node_modules -e .env", root)
    else:
        print(f"note fresh-container hook run skipped: no {nvm_sh}")

    modal_doc = SKILL.parent / "keyframe-modal/references/hosted-code.md"
    if modal_doc.exists():
        dep_line = re.search(r"\.uv_sync\([^)]*\)", image).group(0)
        expect(dep_line in modal_doc.read_text(), f"keyframe-modal's image block uses the same {dep_line}")

    pre = " --predeploy" if with_web else ""  # --predeploy needs web/dist
    r = sh("env -u MODAL_TOKEN_ID -u MODAL_TOKEN_SECRET bash scripts/check.sh" + pre, root)
    expect(r.returncode == 0 and "check.sh: all green" in r.stdout,
           f"check.sh{pre} is green (privacy, lock, sync, offline pytest, Mac and glibc 2.28 wheels, modal import and image mirrors"
           + (", web build and type check)" if with_web else ")"), r.stdout + r.stderr)
    expect("4 passed" in r.stdout, "conftest blocks a live host, keeps MockTransport, forces the mock, "
           "and keeps a fake .env out of module-level Settings", r.stdout)

    conftest = root / "tests/conftest.py"
    conftest.write_text(re.sub(r"\n# Runs before.*?\n\n", "\n", conftest.read_text(), flags=re.S))
    r = sh("uv run pytest -q tests/test_settings_user.py", root)
    expect(r.returncode != 0, "negative: without the import-time block, the fake .env reaches module-level Settings",
           r.stdout)
    sh("git checkout -q tests/conftest.py", root)

    (root / "tests/fixtures/sam31").mkdir(parents=True)
    (root / "tests/fixtures/sam31/living-room-1.jpg").write_bytes(b"\xff\xd8\xff")
    (root / "keyframe-hosted.env").write_text("FAL_KEY=fake\n")
    sh("git add -f tests/fixtures keyframe-hosted.env && git -c user.email=s@s -c user.name=s commit -qm leak", root)
    r = sh("bash scripts/check.sh", root)
    expect(r.returncode != 0 and "tracked private files" in r.stdout and "living-room-1.jpg" in r.stdout,
           "negative: a committed room photo and a hosted env file fail the privacy step", r.stdout + r.stderr)
    sh("git reset -q --hard HEAD~1", root)

    pyproject = root / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('"httpx==0.28.1"', '"httpx==0.28.0"'))
    r = sh("bash scripts/check.sh", root)
    expect(r.returncode != 0 and "needs to be updated" in r.stdout + r.stderr,
           "negative: a pin edited without re-locking fails at `uv lock --check`", r.stdout + r.stderr)
    sh("git checkout -q pyproject.toml", root)

    if not with_web:
        shutil.rmtree(root, ignore_errors=True)
        print("selfcheck passed (Python half only; rerun under Node 24 for the web and predeploy half)")
        return 0

    app = root / "src/api/modal_app.py"
    app.write_text(app.read_text().replace('uv_version="0.11.32"', 'uv_version="0.13.4"'))
    sh("git -c user.email=s@s -c user.name=s commit -qam drift", root)
    r = sh("bash scripts/check.sh", root)
    expect(r.returncode != 0 and "must install uv.lock" in r.stdout, "negative: modal_app uv_version off ci.yml fails check.sh", r.stdout)
    sh("git reset -q --hard HEAD~1", root)

    sh("echo x > stray.txt", root)
    r = sh("bash scripts/check.sh --predeploy", root)
    expect(r.returncode != 0 and "not clean" in r.stdout, "negative: a dirty tree fails --predeploy", r.stdout)
    (root / "stray.txt").unlink()

    lock = root / "web/package-lock.json"
    text = lock.read_text()
    cut = re.sub(r'\n    "node_modules/@rolldown/binding-darwin-arm64": \{.*?\n    \},', "", text, count=1, flags=re.S)
    expect(cut != text, "web lock records @rolldown/binding-darwin-arm64 (generated on Linux)")
    lock.write_text(cut)
    r = sh("bash scripts/check.sh", root)
    expect(r.returncode != 0, "negative: a lock without the macOS arm64 binding fails", r.stdout + r.stderr)

    shutil.rmtree(root, ignore_errors=True)
    print("selfcheck passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
