# Templates for the deps-foundation story and the first web story

Copy these files as written. Every block marked `<!-- file: ... -->` is extracted and run by [../scripts/selfcheck.py](../scripts/selfcheck.py), which builds a scratch project from them and runs `scripts/check.sh` with negative controls. If you change a block here, rerun the selfcheck.

Who adds what:
- **Deps-foundation story (first providers story, Mon Oct 26):** `pyproject.toml` changes, `.python-version`, `.nvmrc`, `uv.lock`, `tests/conftest.py`, `scripts/check.sh`, `scripts/doctor.py` (copied from this skill's `scripts/doctor.py`), `.github/workflows/ci.yml` (without the npm cache lines), `.claude/hooks/session-start.sh` with its `.claude/settings.json` entry, and the deletion of `requirements.txt`.
- **First web story:** `web/package.json`, `web/.npmrc`, `web/package-lock.json`, `node_modules/` in `.gitignore`, and the two npm cache lines in `ci.yml`.
- **First hosted story:** the Modal image block, as amended in keyframe-modal.

Shipped code never imports from `.claude/`. `scripts/doctor.py` is a copy, not a reference, because the skill folder is removed on Nov 4.

## pyproject.toml

Keep the existing `name`, `version` and `description`. There is no `[build-system]`, so uv treats the project as virtual and never builds it.

<!-- file: pyproject.toml -->
```toml
[project]
name = "meta-hackathon-2026"
version = "0.1.0"
description = "Meta Global AI Developer Hackathon project (Cerebral Valley, Oct 26 to Nov 4, 2026)"
requires-python = ">=3.13"
dependencies = [
    "fastapi==0.156.4",
    "uvicorn==0.54.0",
    "pydantic==2.14.1",
    "httpx==0.28.1",
    "Pillow==13.0.0",
    "meta-sam-parser==0.1.0",
    "fal-client==1.0.3",
    "ollama==0.6.3",
    "modal==1.6.2",
    "python-dotenv==1.2.4",
]

[dependency-groups]
dev = ["pytest==9.1.1"]

[tool.uv]
environments = [
    "sys_platform == 'darwin' and platform_machine == 'arm64'",
    "sys_platform == 'linux' and platform_machine == 'x86_64'",
]
required-environments = [
    "sys_platform == 'darwin' and platform_machine == 'arm64'",
    "sys_platform == 'linux' and platform_machine == 'x86_64'",
]
no-build = true
required-version = ">=0.11.32"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Then run `uv lock`, commit `uv.lock`, and `git rm requirements.txt`.

`environments` limits resolution to the two platforms; `required-environments` is the documented setting that makes `uv lock` fail when one of them has no wheel. Neither encodes glibc, so `check.sh` also compiles the lock for `x86_64-manylinux_2_28`.

<!-- file: .python-version -->
```text
3.13
```

## tests/conftest.py (AD-17 offline guard)

`src/config.py` calls `load_dotenv()` on import, so on the Mac a real `.env` (with `MODEL_PROVIDER=meta` and live keys) would leak into pytest. A module that builds `Settings` at import time (`modal_app.py` does) runs during collection, before any fixture. So the conftest sets the mock and blank secrets in `os.environ` when it is imported, before any `src` import: `load_dotenv()` never overrides a variable that is already set, and `Settings` maps `""` to `None`. The autouse fixture repeats this per test. CI and the containers have network, so a test that calls a live host would pass there and flake later; the fixture refuses every non-loopback connection. `httpx.MockTransport` opens no socket, so fixture-based adapter tests still work.

<!-- file: tests/conftest.py -->
```python
"""Offline guard for every test (AD-17)."""

import ipaddress
import os
import socket

import pytest

SECRET_KEYS = ("META_MODEL_API_KEY", "FAL_KEY", "OPENAI_COMPATIBLE_API_KEY", "ACCESS_CODE")
ROLES = ("ARCHITECT", "RIDDLER", "DRYRUN", "TRICKSTER", "IMAGE")

# Runs before any test module imports src.config, so .env cannot reach module-level Settings.
os.environ["MODEL_PROVIDER"] = "mock"
for _role in ROLES:
    os.environ[f"PROVIDER_{_role}"] = "mock"
for _key in SECRET_KEYS:
    os.environ[_key] = ""  # set but blank: load_dotenv() keeps it, Settings reads None

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex


def _is_loopback(address) -> bool:
    if not isinstance(address, tuple):  # AF_UNIX path
        return True
    host = address[0]
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _guard(real):
    def connect(self, address):
        if not _is_loopback(address):
            raise OSError(f"tests run offline (AD-17); blocked connect to {address!r}")
        return real(self, address)
    return connect


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    for role in ROLES:
        monkeypatch.setenv(f"PROVIDER_{role}", "mock")
    for key in SECRET_KEYS:
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(socket.socket, "connect", _guard(_real_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", _guard(_real_connect_ex))
```

## scripts/check.sh (pre-push check and the whole CI job)

<!-- file: scripts/check.sh -->
```bash
#!/usr/bin/env bash
# Pre-push check and the whole CI job. Usage: scripts/check.sh [--predeploy]
set -euo pipefail
cd "$(dirname "$0")/.."
export MODEL_PROVIDER=mock
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
step() { printf '\n== %s\n' "$*"; }

step "privacy: no secret, env file, raw photo or cache tracked"
private=$(git ls-files \
  | grep -Ei '\.env$|(^|/)\.env\.|\.(jpe?g|heic|png)$|^(rooms|photos|captures|uploads|\.cache|cache)/' \
  | grep -Ev '(^|/)\.env\.example$|^(web/public|docs/screenshots)/' || true)
[ -z "$private" ] || { printf 'tracked private files (git rm --cached them; rotate any key that was pushed):\n%s\n' "$private"; exit 1; }

step "python: lock, sync, tests"
uv lock --check
uv sync --locked
uv run pytest -q

step "python: every locked package has wheels for macOS arm64 and for Linux x86_64 with glibc 2.28"
uv export --frozen --no-hashes --no-emit-project -q -o "$tmp/req.txt"
uv pip compile "$tmp/req.txt" --python-version 3.13 --python-platform aarch64-apple-darwin \
  --only-binary :all: -q -o "$tmp/mac.txt"
uv pip compile "$tmp/req.txt" --python-version 3.13 --python-platform x86_64-manylinux_2_28 \
  --only-binary :all: -q -o "$tmp/linux.txt"

if [ -f src/api/modal_app.py ]; then
  step "hosted module: imports offline; the image installs uv.lock with CI's uv and Python"
  uv run python -c 'import src.api.modal_app'
  ci_uv=$(sed -nE 's/^ *version: *"?([0-9.]+)"?.*/\1/p' .github/workflows/ci.yml | head -1)
  grep -q "\.uv_sync(uv_version=\"$ci_uv\"" src/api/modal_app.py \
    || { echo "modal_app.py must install uv.lock with .uv_sync(uv_version=\"$ci_uv\", ...) (keyframe-modal)"; exit 1; }
  if grep -q 'pip_install(' src/api/modal_app.py; then echo "modal_app.py has a pip_install list; uv.lock is the only package list"; exit 1; fi
  grep -q "python_version=\"$(cat .python-version)\"" src/api/modal_app.py \
    || { echo "modal_app.py python_version differs from .python-version"; exit 1; }
fi

if [ -f web/package.json ]; then
  step "web: install, build, type check"
  (cd web && npm ci --no-audit --no-fund && npm run build && npx tsc --noEmit)
  grep -q '"node_modules/@rolldown/binding-darwin-arm64"' web/package-lock.json \
    || { echo "web/package-lock.json lost the macOS arm64 bindings; regenerate it from a clean tree"; exit 1; }
fi

if [ "${1:-}" = "--predeploy" ]; then
  step "predeploy"
  [ -z "$(git status --porcelain)" ] || { echo "commit or stash first: the tree is not clean"; exit 1; }
  [ -f web/dist/index.html ] || { echo "web/dist is missing: run the web build"; exit 1; }
fi
echo; echo "check.sh: all green"
```

Notes:
- The privacy step is the gate; `doctor.py` uses the same pattern. To commit an image on purpose, put it under `web/public/` or `docs/screenshots/`, or widen the allow-list in a reviewed PR. Room photos never go in `tests/fixtures/`: record masks and JSON, not photos.
- The wheel steps write to scratch files. Never `-o /dev/null`: uv replaces the target by renaming, which turns `/dev/null` into a regular file for the whole machine (this happened in a cloud container on Oct 21; `doctor.py` checks for it).
- `uv lock` already refuses a package with no macOS arm64 or Linux x86_64 wheel (`required-environments` plus `no-build`), so the Mac step re-proves that from the committed lock. The Linux step adds what the markers cannot say: wheels for glibc 2.28, below Modal's bookworm (2.36). The containers and CI have glibc 2.39, so without it a `manylinux_2_39`-only package would pass there and fail only at the Modal image build.
- The `modal_app.py` greps run on every check, not only before deploy, so an image that drifts from `uv.lock`, CI's uv or `.python-version` fails at rung 1. keyframe-modal owns the image block.
- `npx tsc --noEmit` repeats the `tsc` in `npm run build`; it stays because it is cheap and the build script may change.

## .github/workflows/ci.yml

The deps-foundation story adds this file without the two npm cache lines, because `setup-node` fails when `cache-dependency-path` does not exist yet. The first web story adds them.

<!-- file: .github/workflows/ci.yml -->
```yaml
name: ci
on:
  push:
    branches: [master]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      MODEL_PROVIDER: mock
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
        with:
          version: "0.11.32"
          enable-cache: true
      - uses: actions/setup-node@v7
        with:
          node-version-file: .nvmrc
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: bash scripts/check.sh
```

- The one third-party action, `setup-uv`, is pinned to the v10.3.0 commit, as GitHub's secure-use guide and the setup-uv README recommend; `@v10` would not resolve anyway (no floating major tag after v7). GitHub's own `checkout` and `setup-node` stay on major tags.
- uv reads `.python-version` and downloads Python 3.13 itself; no `setup-python` step.
- The deps-foundation story adds `.nvmrc` with this file, so `setup-node` has its version file from the first run; with no `web/` yet, `check.sh` skips the web steps.
- After the first green run on master, turn on branch protection: Settings, Branches, require the `check` status before merging. If the plan does not enforce it for a private repo (GitHub Free may not), "CI green before merge" is a rule Luis keeps by hand.

## Node files

`.nvmrc` comes with the deps-foundation story; the rest with the first web story.

<!-- file: .nvmrc -->
```text
24
```

<!-- file: web/package.json -->
```json
{
  "name": "keyframe-web",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "engines": {
    "node": "24.x"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "three": "0.186.1"
  },
  "devDependencies": {
    "@types/three": "0.186.0",
    "typescript": "6.0.3",
    "vite": "8.3.4"
  }
}
```

Two lines here follow the Stack (SKILL.md, Spine changes): `"typescript": "6.0.3"` exact, as `save-exact`, `check.sh` and `doctor.py` expect, and `"@types/three": "0.186.0"`, without which the build fails with TS7016.

If the first web story picks `json-schema-to-typescript` (Deferred), add `"json-schema-to-typescript": "16.0.0"` to `devDependencies` with `npm install -D json-schema-to-typescript@16.0.0`.

<!-- file: web/.npmrc -->
```ini
save-exact=true
engine-strict=true
```

Generate the lock once, from a clean tree, under Node 24: `cd web && rm -rf node_modules package-lock.json && npm install`. Commit `package-lock.json`. Add `node_modules/` to the root `.gitignore` in the same commit (it is not there today; `dist/` already covers `web/dist`). npm 11 kept the macOS bindings even when regenerating over a populated `node_modules` (tested Oct 21); older npm versions could drop optional platform packages, so the clean tree and the `check.sh` grep stay as cheap insurance.

## Cloud container setup (SessionStart hook)

Use a SessionStart hook: `.claude/hooks/session-start.sh` registered in `.claude/settings.json` (both are hackathon tooling on the Nov 4 hygiene path list in `docs/specs/spec-keyframe/delivery-plan.md`; if `.claude/settings.json` existed before, only the hook entry is removed). The tool shell in these containers has a fixed `PATH` with Node 22 first, so `nvm alias default` alone does not reach later commands. Only SessionStart hooks get `$CLAUDE_ENV_FILE`, which carries Node 24's directory into later shells.

- Hooks in the repo's settings also run in Luis's local sessions, so the script exits at once unless `CLAUDE_CODE_REMOTE` is `true`.
- `matcher: "startup|resume"` re-runs it on resume, where `npm ci` is skipped while `node_modules` is newer than the lock.
- `uv sync` and `npm ci` failures only print a note: a broken lock surfaces in `check.sh`, not at session start.
- `nvm.sh --no-use` matters: in a fresh container `/opt/nvm` has no default alias or installed version, and a plain `source` returns 3, which stops the script under `set -e`.
- Repo hooks do not run in a session with several repositories or in a project's cloud thread. There, the environment's setup script can run `source /opt/nvm/nvm.sh --no-use && nvm install 24 || true`. That only installs Node 24; it cannot put it on `PATH`, so agents prefix web commands with `source /opt/nvm/nvm.sh --no-use && nvm use 24 >/dev/null &&`. A setup script that exits non-zero stops the session from starting.

<!-- file: .claude/hooks/session-start.sh -->
```bash
#!/usr/bin/env bash
# SessionStart hook: Node 24 and dependencies for cloud sessions. Local sessions exit at once.
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
set -euo pipefail
cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
export NVM_DIR="${NVM_DIR:-/opt/nvm}"
source "$NVM_DIR/nvm.sh" --no-use
nvm install 24 >/dev/null && nvm alias default 24 >/dev/null
NODE24_BIN="$(dirname "$(nvm which 24)")"
export PATH="$NODE24_BIN:$PATH"
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$NODE24_BIN:\$PATH\"" >> "$CLAUDE_ENV_FILE"
else
  echo "session-start: CLAUDE_ENV_FILE is not set, so later shells keep Node 22 (run this as a SessionStart hook)" >&2
fi
if [ -f uv.lock ]; then uv sync --locked -q || echo "session-start: uv sync --locked failed; run scripts/check.sh" >&2; fi
if [ -f web/package.json ] && ! [ web/node_modules/.package-lock.json -nt web/package-lock.json ]; then
  (cd web && npm ci --no-audit --no-fund --loglevel=error) || echo "session-start: npm ci failed; run scripts/check.sh" >&2
fi
if [ -f scripts/doctor.py ]; then python3 scripts/doctor.py --cloud || true; fi   # diagnosis only
```

<!-- file: .claude/settings.json -->
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/session-start.sh" } ]
      }
    ]
  }
}
```

If `.claude/settings.json` already exists, merge the `hooks` key into it.

## .gitignore additions

The repo used to ignore `.env` but not `.env.local` or `keyframe-hosted.env`. These lines were added on Oct 21; keep them:

```text
.env.*
!.env.example
*.env
```

## Modal image (first hosted story; keyframe-modal owns the block)

keyframe-modal's `references/hosted-code.md` is the single source for the image block; the copy below is what this skill's selfcheck renders and what `check.sh` greps for. If the two differ, keyframe-modal wins and this copy is updated.

`uv_sync` copies `pyproject.toml` and `uv.lock` into the build and runs `uv sync --frozen`, so the image installs exactly the tested lock. It does not pass `--no-dev`, and without `uv_version` it copies `uv:latest`.

```python
image = (
    modal.Image.debian_slim(python_version="3.13")
    .uv_sync(uv_version="0.11.32", extra_options="--no-dev")
    .env({"MODE": "hosted", "GUIDE": "verbatim"})
    .add_local_python_source("src")
    .add_local_dir("web/dist", "/root/web/dist")
)
secret = modal.Secret.from_name(
    "keyframe", required_keys=["META_MODEL_API_KEY", "FAL_KEY", "ACCESS_CODE"]
)  # plus "OPENAI_COMPATIBLE_API_KEY" if the hosted fallback is used
```

Rendered offline on Oct 21 (modal 1.6.2, builder 2025.06), the dependency layer is `COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /.uv/uv` then `RUN /.uv/uv sync --project=/.uv --no-install-workspace --compile-bytecode --no-dev --frozen`, on `FROM python:3.13.3-slim-bookworm`.

## Third-party license list (run once on Tue Nov 3)

Run it with the project environment (`uv run python licenses.py`, from a scratch location outside the repo) and paste the output into the README's third-party licenses section. It lists the dev group too; leave pytest and its helpers out of the README. `fal-client` prints `UNKNOWN`: its bundled LICENSE file is Apache-2.0, so write that by hand.

```python
import importlib.metadata as m

rows = []
for d in m.distributions():
    md = d.metadata
    lic = md.get("License-Expression") or ""
    if not lic:
        cls = [c.split(" :: ")[-1] for c in (md.get_all("Classifier") or []) if c.startswith("License ::")]
        raw = (md.get("License") or "").strip().splitlines()
        lic = "; ".join(cls) or (raw[0][:40] if raw else "UNKNOWN")
    rows.append((md["Name"], md["Version"], lic))
for r in sorted(rows, key=lambda r: r[0].lower()):
    print(f"{r[0]:<22} {r[1]:<20} {r[2]}")
```

On the Oct 21 lock it printed 55 packages: MIT, BSD, Apache-2.0, PSF, MIT-CMU (Pillow) and MPL-2.0 (certifi), plus `SAM License` (meta-sam-parser) and `UNKNOWN` (fal-client).
