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
