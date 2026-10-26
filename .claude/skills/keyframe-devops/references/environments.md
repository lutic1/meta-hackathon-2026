# Environment matrix (full)

Four environments, one lock. The code files are authoritative; this page and the Stack table mirror them. Checked on 2026-10-21 unless a row says otherwise.

## Mac, local mode (Luis)

- **Machine:** MacBook M1, 16 GB, macOS 14 or later (Ollama needs Sonoma), arm64. A Rosetta shell reports `x86_64` and would pick the wrong wheels; `doctor.py` fails on it.
- **Python:** 3.13 through uv (`.python-version`); uv 0.11.32 or newer (`required-version`). If a newer uv rewrites `uv.lock` with an unrelated diff, run `uv self update 0.11.32`.
- **Node:** 24.x from `.nvmrc` (npm 11). `nvm use` in `web/`.
- **Ollama:** the macOS app, runtime 0.40.x (Stack: 0.40.6; the app auto-updates the patch), model `llama3.2:3b`, at `127.0.0.1:11434` unless `OLLAMA_HOST` is set. The adapter passes `keep_alive=-1` on every call, so nothing depends on `launchctl setenv OLLAMA_KEEP_ALIVE` surviving a reboot. Resident size is not published (estimates vary from 2.2 to 6.2 GB); `doctor.py` measures it from `/api/ps` after one warm-up call.
- **Provider:** `meta` per role, with the Baseten or Fireworks fallback by base URL; `mock` inside pytest (the conftest forces it).
- **Secrets:** `.env` (git-ignored, copied from `.env.example`): `MODEL_API_KEY`, `FAL_KEY`, optional `OLLAMA_HOST`; `MODE` and `GUIDE` stay at their defaults (`local`, `ollama`). The Modal token lives only in `~/.modal.toml` (`modal setup`). The hosted Secret's source file is `~/keyframe-hosted.env`, outside the repo.
- **Runs:** `uv sync --locked`, `npm ci`, `scripts/check.sh`, `scripts/doctor.py`, FastAPI serving `web/dist` or behind the Vite dev proxy, `scripts/sit.py`, dev-skill selfchecks, `modal serve -e dev`, manual `modal deploy`, the ledger export, video takes.
- **Never runs:** `uv sync --frozen`, `uv pip install`, `npm install` without an exact version, `modal secret create --from-dotenv .env`; never commits `.env` or raw photos.

## Cloud dev containers (coding agents)

- **Machine:** Linux x86_64, glibc 2.39, 4 vCPU, 15 GB RAM, no GPU, HTTPS through a proxy (`SSL_CERT_FILE`, `NODE_EXTRA_CA_CERTS` and friends are preset).
- **Python:** 3.13 through uv 0.11.32. `UV_NATIVE_TLS` deprecation warnings are harmless noise.
- **Node:** the image ships Node 22.22.0 and npm 10.9.4, first on a fixed `PATH`; `/opt/nvm` has no installed version. The SessionStart hook (templates.md) runs `nvm install 24` and writes Node 24's directory to `$CLAUDE_ENV_FILE`, which only SessionStart hooks receive. Under `engine-strict`, Node 22 fails `npm ci` with `EBADENGINE`. Repo hooks do not run in multi-repo sessions or project threads; there, use `source /opt/nvm/nvm.sh --no-use && nvm use 24` in the command.
- **Ollama:** none. **Provider:** `mock` and recorded fixtures only (AD-17).
- **Secrets:** none. No `.env` with values, no live keys, no Modal token, ever.
- **Runs:** the SessionStart hook (Node 24, `uv sync --locked`, `npm ci`, `doctor.py --cloud`; failures only print a note), `uv run pytest -q tests/<package>`, `scripts/check.sh` before every push, `npm run build`, offline dev-skill selfchecks when a story changes a pin.
- **Never runs:** Ollama, `sit.py`, live provider calls, `modal serve` or `deploy`, `uv lock --upgrade`, `npm update` or `npm audit fix`, any pin change outside a dependency PR.

## CI (GitHub Actions, one job `check`)

- **Machine:** `ubuntu-latest`, x86_64.
- **Python:** uv 0.11.32 from `astral-sh/setup-uv` pinned to the v10.3.0 commit; Python 3.13 from `.python-version`.
- **Node:** `actions/setup-node@v7` with `node-version-file: .nvmrc`.
- **Provider:** `mock` (job env plus conftest; non-loopback sockets blocked). **Secrets:** none.
- **Runs:** `bash scripts/check.sh`, which is the whole job.
- **Never runs:** secrets, deploy, CD, a matrix, live calls, `sit.py`, an audit as a gate.

## Modal hosted (`modal serve -e dev`, then `modal deploy` for the judge URL)

- **Machine:** Linux x86_64, `debian_slim` (renders as `python:3.13.3-slim-bookworm` under builder 2025.06; bookworm ships glibc 2.36), CPU only.
- **Python:** 3.13 from `debian_slim(python_version="3.13")`; packages from `uv_sync(uv_version="0.11.32", extra_options="--no-dev")`, which reads `uv.lock` with `--frozen`. So `uv lock --check` must pass before every deploy. Bookworm's glibc 2.36 is below the containers' 2.39, so `check.sh` compiles the lock for `manylinux_2_28`.
- **Node:** none at runtime; `web/dist` is built on the Mac and mounted with `add_local_dir`.
- **Ollama:** none (`GUIDE=verbatim`; Settings refuses `MODE=hosted` with `GUIDE=ollama`).
- **Provider:** `meta` for the Trickster and builds; rungs verbatim.
- **Secrets:** Modal Secret `keyframe`, with `required_keys` `MODEL_API_KEY`, `FAL_KEY`, `ACCESS_CODE` (plus `OPENAI_COMPATIBLE_API_KEY` if the hosted fallback is used). `MODE=hosted` and `GUIDE=verbatim` are set on the image with `.env()`. `MIN_CONTAINERS` comes from the deploy shell.
- **Runs:** the FastAPI `asgi_app` (`max_containers=1`), `run_build`, the `ledger_export` and `session_sweep` Crons, smoke checks after deploy.
- **Never runs:** Ollama, pytest (dev group excluded), `.env` (`add_local_python_source` ships only `.py` files), automatic deploys.
