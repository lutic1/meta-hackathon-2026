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
