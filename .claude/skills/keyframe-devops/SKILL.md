---
name: keyframe-devops
description: Keeps Keyframe's environments and dependencies reproducible and the build unbroken. Covers uv with a committed uv.lock (Python 3.13, == pins, no-build), npm with web/package-lock.json and exact versions (Node 24, engine-strict), the dependency checklist and Oct 26 freeze, scripts/check.sh (pre-push check and the whole CI job), scripts/doctor.py, the cloud SessionStart hook, the offline pytest guard, Settings keys and secrets per environment, and the pre-deploy and Nov 4 hygiene checks. Use when choosing or changing the Python or Node environment, adding, upgrading or pinning a dependency, editing pyproject.toml, the lockfiles, .nvmrc, .python-version, .gitignore, .env.example or Settings keys, writing or debugging CI, preparing the Mac or a cloud container, or checking that a change does not break the build. Do not use for model API calls (keyframe-muse, keyframe-sam31, keyframe-sam3d-fal), Modal runtime code (keyframe-modal), generic SessionStart hook mechanics (session-start-hook), or product features.
when_to_use: Trigger phrases such as "add a dependency", "bump a dependency", "should we upgrade", "pin", "uv.lock", "uv sync --locked", "lock drift", "package-lock.json", "npm ci fails", "EBADENGINE", "no wheel for arm64", "builds from source", "glibc", "TS7016", "CI is red", "check.sh", "doctor", "set up the container", "Node 24", "Python 3.13", ".env.example", "missing env key", "committed a secret", "pre-deploy check", "dependency freeze", "license list", "npm audit", "hygiene".
paths:
  - "pyproject.toml"
  - "uv.lock"
  - "requirements*.txt"
  - ".python-version"
  - ".nvmrc"
  - "web/package.json"
  - "web/package-lock.json"
  - "web/.npmrc"
  - ".github/workflows/**"
  - ".env.example"
  - ".gitignore"
  - "src/config.py"
  - "scripts/check.sh"
  - "scripts/doctor.py"
  - ".claude/settings.json"
  - ".claude/hooks/**"
---

# Environments, dependencies and build checks for Keyframe

The skill loads automatically only when work touches the dependency, CI, environment or settings files in its `paths:` list; run `/keyframe-devops` to load it for a question that touches none of them. Facts here were checked on 2026-10-21 against the official uv, npm, Node, GitHub Actions, Modal and Ollama pages, and by running every command under Tested commands in a scratch copy of the repo. Keep it simple: this is a 9-day hackathon (code from Mon Oct 26, submit Wed Nov 4) built by coding agents in Linux containers around the clock plus Luis on one M1 MacBook. Files to copy are in [references/templates.md](references/templates.md), proven by [scripts/selfcheck.py](scripts/selfcheck.py). The full matrix is [references/environments.md](references/environments.md); the full check ladder, pre-deploy and hygiene steps are [references/check-ladder.md](references/check-ladder.md). The environment check is [scripts/doctor.py](scripts/doctor.py).

**Today vs from Oct 26.** The repo still has `requires-python = ">=3.11"`, a loose `requirements.txt` and no `uv.lock`, `.nvmrc`, `web/`, CI or `scripts/`. The deps-foundation story (the first providers story, Mon Oct 26) adds them from templates.md. Do not create those files before that story; `doctor.py` and this skill tolerate their absence.

## When to use

Use this skill for:
- Choosing or changing a tool or version: Python, uv, Node, npm, Ollama runtime, a GitHub Action.
- Any dependency change: adding, upgrading, pinning, removing, re-locking (`pyproject.toml`, `uv.lock`, `web/package.json`, `web/package-lock.json`).
- `scripts/check.sh`, `.github/workflows/ci.yml`, `tests/conftest.py`, `scripts/doctor.py`, the cloud SessionStart hook (`.claude/hooks/session-start.sh`).
- `.env.example`, `.gitignore` privacy entries, and which Settings keys and secrets exist where (AD-14).
- "Does this break the build?": run the ladder below.
- The Modal pre-deploy sequence and the Nov 4 hygiene checks (Luis runs both).

Do not use it for:
- Model calls: keyframe-muse, keyframe-sam31, keyframe-sam3d-fal.
- Modal runtime code in `src/api/modal_app.py` and `src/infra/modal.py`: keyframe-modal, which also owns the image block. This skill sets the rule for its dependency line (`uv_sync` of `uv.lock`) and checks it in `check.sh`.
- Product features, the domain, the pipeline, or the web UI.
- `scripts/sit.py` cases themselves (the SIT story owns them); this skill only says when SIT runs.
- Generic SessionStart hook mechanics: the session-start-hook skill. This skill owns only Keyframe's hook file.

Agents never run `modal serve`, `modal deploy`, `sit.py`, Ollama or any live provider call, and never hold keys.

## Environments

| | Mac, local mode (Luis) | Cloud containers (agents) | CI (one job `check`) | Modal hosted |
|---|---|---|---|---|
| OS, arch | macOS 14+, M1 arm64, 16 GB | Linux x86_64, glibc 2.39, no GPU, HTTPS proxy | `ubuntu-latest` x86_64 | `debian_slim` bookworm x86_64, CPU |
| Python | 3.13 via uv (`.python-version`), uv >= 0.11.32 | 3.13 via uv 0.11.32 | uv 0.11.32 from setup-uv, 3.13 from `.python-version` | 3.13; packages from `uv_sync(uv_version="0.11.32", extra_options="--no-dev")` |
| Node | 24.x (`.nvmrc`), npm 11 | 22 by default; the SessionStart hook installs 24 | setup-node from `.nvmrc` | none at runtime (`web/dist` mounted) |
| Ollama | 0.40.x app, `llama3.2:3b`, `keep_alive=-1` from the adapter | none | none | none (`GUIDE=verbatim`) |
| Provider | `meta` per role; `mock` inside pytest | `mock` and fixtures only | `mock` | `meta` |
| Secrets | `.env` (ignored), `~/.modal.toml`, `~/keyframe-hosted.env` | none | none | Secret `keyframe` |
| Runs | everything, incl. SIT, selfchecks, `modal serve -e dev`, manual deploy | SessionStart hook, `uv run pytest -q tests/<pkg>`, `check.sh` before push | `bash scripts/check.sh` | web, runner, two Crons |

## Dependencies

### Where each pin lives

One source per fact. Every mirror is checked, so a mismatch fails instead of drifting. The Stack table is the human-readable mirror; the code files win.

| Fact | Source of truth | Mirrors (checked by) |
|---|---|---|
| Python minor | `.python-version` (`3.13`) | `requires-python >= 3.13`; `debian_slim(python_version="3.13")` (`check.sh`); CI via uv |
| Direct Python packages | `pyproject.toml` `[project.dependencies]` (`==`) and `[dependency-groups] dev` | Stack table, same PR |
| Transitive Python packages | `uv.lock` | Modal reads it through `uv_sync`; no second list (`check.sh` fails on `pip_install(` in `modal_app.py`) |
| uv | `ci.yml` `version: "0.11.32"` | `modal_app.py` `uv_version` (`check.sh`); `required-version` floor (uv itself) |
| Node major | `.nvmrc` (`24`) | `engines.node` `"24.x"` (`engine-strict`); CI `node-version-file` |
| Direct npm packages | `web/package.json`, exact | Stack table |
| Transitive npm packages | `web/package-lock.json` (lockfileVersion 3) | `npm ci` |
| Ollama model id | `GUIDE_MODEL = "llama3.2:3b"` in `src/providers/ollama.py` | `doctor.py` reads it |
| Ollama runtime | `OLLAMA_MINOR = "0.40"` in `doctor.py` | Stack table |
| GitHub Actions | `ci.yml` (setup-uv by commit SHA, GitHub's own actions by major tag) | none |

The Python Stack today: fastapi 0.156.4, uvicorn 0.54.0, pydantic 2.14.1, httpx 0.28.1, Pillow 13.0.0, meta-sam-parser 0.1.0, fal-client 1.0.3, ollama 0.6.3, modal 1.6.2, python-dotenv 1.2.4; pytest 9.1.1 in `dev`. npm: three 0.186.1; vite 8.3.4, typescript 6.0.3, @types/three 0.186.0 (and json-schema-to-typescript 16.0.0 if the first web story picks it). These resolve together on Python 3.13 to 55 packages, wheels only, identical on macOS arm64 and Linux x86_64. Only `uv.lock` pins Starlette (1.9.0), pydantic-core (2.50.1) and the rest, so review it like code.

### Commands

- Install: `uv sync --locked` and `cd web && npm ci`. Test: `uv run pytest -q`.
- Change a pin, only in a dependency PR: `uv add pkg==X` (writes `==X` and re-locks) or `npm install pkg@X` / `npm install -D pkg@X` (exact, through `save-exact`), and commit the lock in the same commit.
- Never: `uv sync --frozen` (installs a stale lock silently), `uv pip install`, `uv lock --upgrade`, `uv add pkg` without `==X` (writes `>=`), `npm update`, `npm audit fix`, `npm create vite@latest`, a bare `npm install <pkg>`.
- Regenerate `web/package-lock.json` only from a clean tree, under Node 24: `rm -rf node_modules package-lock.json && npm install`. npm 11 kept the macOS bindings even over a populated `node_modules` (tested); older npm versions could drop optional platform packages, so the clean tree and the `check.sh` grep stay as cheap insurance.

### Adding or upgrading a dependency (checklist)

A dependency change is its own PR, touching only `pyproject.toml` and `uv.lock` (or `web/package.json` and `web/package-lock.json`), plus the Stack table, the README license line and the affected skill pins. Luis approves it.
1. **Needed?** It must solve something the stdlib, an existing dependency or 30 lines of code cannot. Name the story.
2. **License:** MIT, BSD, Apache-2.0, PSF, ISC and MPL-2.0 are fine. Anything else (the SAM License, the Llama license) gets named in the README third-party licenses section. No metadata means reading the bundled LICENSE (fal-client: Apache-2.0).
3. **Wheels on both platforms:** a cp313, abi3 or py3-none-any wheel for macOS arm64 and for manylinux x86_64 with glibc <= 2.28. `uv add` refuses a package with no wheel for either platform (`required-environments` plus `no-build`); it cannot see glibc. `check.sh` compiles the lock wheels-only for `aarch64-apple-darwin` and for `x86_64-manylinux_2_28`, which catches both (the containers and CI have glibc 2.39, Modal's bookworm 2.36). For npm, the darwin-arm64 and linux-x64 native bindings must appear in the lock.
4. **Python 3.13:** its `requires-python` allows 3.13.
5. **Size:** under about 20 MB installed, or a stated reason; it lands in the Modal image.
6. **Stack table** updated in the same PR (the architect owner edits the spine, or the PR notes the follow-up).
7. **Lock:** add with an exact version, then read the lock diff: only the expected packages move.
8. **README** license line if step 2 flagged it.
9. **Selfchecks:** rerun the skills that cover the moved pin and update their Tested commands tables (modal: keyframe-modal; httpx or pydantic: keyframe-muse; meta-sam-parser or httpx: keyframe-sam31; fal-client, httpx or Pillow: keyframe-sam3d-fal; uv, Node, Vite, TypeScript or three: keyframe-devops). Commands in check-ladder.md, rung 5.
10. `bash scripts/check.sh` green locally, then CI green.

### Freeze (from the deps-foundation merge on Mon Oct 26 through Nov 9)

- No pinned version moves (Python, npm, Node major, uv, Ollama minor) except for a **blocking bug** (a story cannot be finished, or a demo path fails, and the new version fixes it) or a **security fix** that applies to how Keyframe uses the package. Even then: one package per PR, the full checklist, the affected selfchecks, and Luis's explicit approval in the PR.
- Nothing checks the freeze mechanically; Luis spots a lock diff outside a dependency PR in review.
- New dependencies only through the checklist and only when a story cannot be done otherwise. `@sparkjsdev/spark` 2.4.0 is pre-approved for Tier 3 only.
- Nothing moves Nov 2 to 4 except a security fix. No pre-freeze bumps either: today's pins are the ones the skills verified.
- Deliberately not adopted: FastAPI 0.156.8, Vite 8.3.5 (published Oct 21), TypeScript 7.x, Node 26 (Active LTS from Oct 28), uv 0.13.x (0.13.4 is one day old).
- Ollama's macOS auto-update is outside the repo: `doctor.py` fails off 0.40.x and warns on a patch other than 0.40.6 (0.40.7 shipped Oct 18).

## Check ladder

Run the cheapest rung that can see the change; detail in [references/check-ladder.md](references/check-ladder.md).

| Rung | When | Command | Catches | Budget |
|---|---|---|---|---|
| 0 Inner loop | every edit | `uv run pytest -q tests/<package>` | logic regressions in the owned package | < 10 s |
| 1 Pre-push | every push (agents), every merge (Luis) | `bash scripts/check.sh` | tracked secrets, env files or photos, lock drift, source builds, missing Mac or glibc 2.28 wheels, offline test failures, live calls in tests, hosted import errors, image drift from `uv.lock`, TS and Vite errors, npm lock drift, wrong Node, lost Mac bindings | 30 to 90 s warm |
| 2 CI | push to master, every PR; required by branch protection where the plan allows (else by hand) | one job `check` running `bash scripts/check.sh` | rung 1 on a clean machine: uncommitted files, hand-edited venvs | 2 to 4 min, timeout 10 |
| 3 Lock and platform | inside rungs 1 and 2; by hand in dependency PRs | `uv lock --check`, `uv sync --locked`, the darwin and `manylinux_2_28` export compiles, `npm ci`, the binding grep; `uv tree`, `uv pip check` to diagnose | manifest and lock drift, missing platform wheels, a glibc floor above Modal's | < 10 s |
| 4 Doctor | Mac: each session, after reboot or Ollama update, before SIT, right before each video take (Tue Nov 3) and before the finals; containers: end of the SessionStart hook | `python3 scripts/doctor.py` (`--cloud`, `--ci`, `--json`) | wrong Node or uv, Ollama off-pin or not resident, missing model, leaked `.env`, tracked photos, old glibc, broken `/dev/null` | < 10 s (+30 s warm-up) |
| 5 Selfchecks | dependency PRs that move a covered pin; once Mon Oct 26 | the sibling skills' `selfcheck.py` with `--with pkg==new`; this skill's selfcheck | skill facts going stale under a new version | 10 to 60 s each |
| 6 SIT | Luis, end of each build day from Tue Oct 27; full pass Sat Oct 31 | `uv run python scripts/sit.py` | live API, key, Ollama and cache drift that fixtures cannot see | 5 to 10 min |
| 7 Pre-deploy | before every `modal deploy` (first Tue Oct 27); also after any merged dependency PR and in the Sat Oct 31 SIT pass (`check.sh --predeploy` plus a `modal serve -e dev` smoke, Luis) | `check.sh --predeploy`, keyframe-modal selfcheck, `modal serve -e dev`, deploy, smoke | stale lock in the image, missing `web/dist`, missing Secret key, dirty tree, an image broken by a dependency merged between deploys | ~5 min + build |
| 8 Hygiene | Wed Nov 4 morning (rehearse Sat Oct 31) | delivery-plan `git rm` command, staged-diff check, privacy grep, `.claude/skills` grep, commit, fresh-clone `check.sh`, CI green | shipped code depending on removed skills, uncommitted files, tracked private files | ~15 min |

Until `scripts/doctor.py` exists in the repo, run `python3 .claude/skills/keyframe-devops/scripts/doctor.py`. The deps-foundation story copies it to `scripts/doctor.py`, which stays after Nov 4.

## Settings and secrets

- **AD-14:** `Settings` (`src/config.py`) reads the environment once; no other module reads `os.environ`. `scripts/doctor.py` is exempt (stdlib, runs before `uv sync`; it reads `OLLAMA_HOST` and `.env` key names itself). The first providers story removes the two direct reads in `src/providers/meta_api.py` (lines 41 and 49) and adds `FAL_KEY` to `Settings` and `.env.example`.
- **The AD-14 test** asserts every Settings key is in `.env.example`, secret keys there are blank, and `.env` is git-ignored. Add a key to all three (Settings, `.env.example`, the test's list) in one commit; a hosted key also goes into the Secret's `required_keys`.
- **Mac:** `.env` from `.env.example` with `MODEL_PROVIDER=meta`, `META_MODEL_API_KEY`, `FAL_KEY`, optional `OLLAMA_HOST`. Modal token only in `~/.modal.toml`. Hosted Secret source in `~/keyframe-hosted.env`, created with `modal secret create keyframe --from-dotenv ~/keyframe-hosted.env` (never the repo `.env`, never `KEY=VALUE` on the command line; see the keyframe-modal runbook).
- **Containers and CI:** no `.env` values, no keys, `MODEL_PROVIDER=mock`. Agents never get Meta, fal or Modal credentials.
- **Modal:** Secret `keyframe` with `META_MODEL_API_KEY`, `FAL_KEY`, `ACCESS_CODE` (and `OPENAI_COMPATIBLE_API_KEY` if the hosted fallback is used); `MODE=hosted` and `GUIDE=verbatim` on the image via `.env()`; `MIN_CONTAINERS` from the deploy shell.
- **pytest:** `tests/conftest.py` sets `MODEL_PROVIDER=mock`, `PROVIDER_<ROLE>=mock` and the four secret keys to `""` in `os.environ` when it is imported (before any `src` import, so module-level `Settings` never sees the Mac's `.env`: `load_dotenv()` does not override a set variable), repeats that per test, and blocks every non-loopback socket.
- **Never committed:** `.env`, `.env.*` (except `.env.example`), `*.env` such as `keyframe-hosted.env`, raw room photos (`rooms/`, `photos/`, `captures/`, `uploads/`, any `.jpg`, `.jpeg`, `.png` or `.heic` outside `web/public/` and `docs/screenshots/`, including under `tests/fixtures/`), `.cache/`, `spend/*.jsonl`. `check.sh` fails on a tracked one of these (so does CI), except `spend/*.jsonl`, which only `.gitignore` covers; `doctor.py` uses the same pattern and also checks the ignore rules.
- **A leaked secret or photo that reached GitHub** is not fixed by `git rm --cached`: the file stays in history, and the repo goes public on Nov 4. Rotate the key at once (Meta, fal, Modal), then before Nov 4 purge the history or publish from a fresh history. Luis decides which.

## Failure scenarios

| Symptom | Cause | Fix |
|---|---|---|
| `uv add` or `uv lock`: "has no `platform_machine == 'arm64' and sys_platform == 'darwin'`-compatible wheels" (reported for the `python_full_version >= '3.15'` split, with a hint to limit `requires-python`) | the package has no macOS arm64 wheel; the `requires-python` hint is a red herring | pick another version or package (checklist step 3); never drop `environments` or `required-environments` |
| `check.sh`, Linux wheel step: "No solution found ... has no wheels with a matching platform tag" | the package's Linux wheels need glibc newer than 2.28 (fine in the containers and CI, fails at the Modal image build) | pick a version with `manylinux_2_28` or older wheels |
| `check.sh`: "tracked private files" | a `.env*`, `*.env`, photo or private folder is committed | `git rm --cached <path>`, commit; if it was pushed, rotate the key and plan the history purge (Settings and secrets) |
| `check.sh`: "modal_app.py must install uv.lock with .uv_sync(...)" or "has a pip_install list" | the image drifted from `uv.lock` or CI's uv | use keyframe-modal's image block (`.uv_sync(uv_version="0.11.32", extra_options="--no-dev")`) |
| "Wheels are required for `X` because building from source is disabled" | only an sdist for cp313 on one platform (`no-build`) | pick a version with cp313 or abi3 wheels; never remove `no-build` |
| A package with no cp313 wheel, or `requires-python` excluding 3.13 | Python 3.13 incompatibility | choose a release that supports 3.13; the Stack stays on 3.13 |
| "The lockfile at `uv.lock` needs to be updated, but `--check` was provided" (or `--locked`) | `pyproject.toml` changed without `uv lock` | in the dependency PR run `uv lock` and commit; never `--frozen` |
| "Unable to find lockfile ... but `--locked` was provided" | `uv.lock` not committed | `uv lock`, commit it |
| `ModuleNotFoundError: No module named 'src'` under `uv run pytest` | pytest's console script does not add the repo root | `pythonpath = ["."]` in `[tool.pytest.ini_options]` |
| A large unrelated `uv.lock` diff from the Mac | a newer uv rewrote the lock format | `uv self update 0.11.32`, `git checkout uv.lock` |
| `npm error code EBADENGINE ... Required: {"node":"24.x"}` | Node 22 (container default) under `engine-strict`: the hook did not run (several repos in the session, a project thread) or ran outside SessionStart | containers: `source /opt/nvm/nvm.sh --no-use && nvm use 24` in the same command, or rerun the hook; Mac: `nvm use` |
| the hook exits 3 right after `source nvm.sh` | `source` without `--no-use` in a container whose nvm has no installed version | use the template line `source "$NVM_DIR/nvm.sh" --no-use` |
| `npm ci`: "package.json and package-lock.json ... are in sync ... Invalid" or "Missing: ... from lock file" | `package.json` edited without the lock, or the lock lost an entry | `npm install pkg@exact` and commit both; regenerate from a clean tree if bindings are missing |
| `check.sh`: "lost the macOS arm64 bindings" | the lock lost optional platform packages (older npm, or a hand edit) | `rm -rf node_modules package-lock.json && npm install` under Node 24 |
| doctor FAIL "web lock ... not valid JSON (merge conflict?)" | conflict markers in `package.json` or the lock | regenerate the lock from a clean tree; never hand-merge it |
| `TS7016: Could not find a declaration file for module 'three'` | `@types/three` missing (three ships no types) | `npm install -D @types/three@0.186.0` |
| `TS2322`, `TS6133` and other `tsc` errors in `npm run build` | type errors; TS 6 is strict by default | fix the code; never loosen `tsconfig` |
| CI green but `modal deploy` fails | `web/dist` missing, a Secret key missing (`required_keys`), or the builder version | follow rung 7: `check.sh --predeploy`, then `modal serve -e dev` first |
| Image has old packages | `uv_sync` runs `--frozen` and shipped a stale lock | `uv lock --check` (inside `check.sh`) before every deploy |
| pytest in the image, or `uv:latest` | `uv_sync` without `extra_options="--no-dev"` or `uv_version` | use the image block in templates.md |
| doctor: "ollama server ... unreachable" / "guide model ... missing" | Ollama.app not running, or the model not pulled | open Ollama.app; `ollama pull llama3.2:3b` |
| doctor: "keep_alive=-1 did not stick", or a slow first hint | model unloaded | the adapter must pass `keep_alive=-1`; rerun doctor |
| doctor WARN on the Ollama patch, FAIL off 0.40 | the macOS app auto-updated | a patch WARN is accepted; off 0.40, reinstall 0.40.6 from the GitHub releases |
| `Settings` fails at startup on a missing or invalid key | a key added in code but not in `.env` or the Secret | add it to `.env.example`, `.env` and `required_keys`; doctor lists missing key names |
| doctor FAIL "no private path tracked or staged" | `.env`, a photo or a cache file staged | `git rm --cached <path>`; check `.gitignore` |
| Live calls in tests pass in CI, then flake | a test reached a real host | the conftest guard raises `OSError("tests run offline")`; use `httpx.MockTransport` and fixtures |
| TLS or 403/407 errors in a container | the HTTPS proxy | uv and npm already trust the proxy's CA (`UV_NATIVE_TLS`, `NODE_EXTRA_CA_CERTS`); see `/root/.ccr/README.md`; never disable TLS verification |
| `No space left on device` | uv or npm caches, `node_modules`, `.venv` | `uv cache prune`, `npm cache clean --force`, delete `web/node_modules` and `.venv`, then `uv sync --locked` |
| `/dev/null` is a regular file; odd shell output | a tool wrote `-o /dev/null` and uv replaced it by renaming | `sudo rm -f /dev/null && sudo mknod -m 666 /dev/null c 1 3`; always write uv output to a scratch file |
| `setup-uv@v10` "unable to resolve action" | setup-uv has no floating major tag after v7 | the template's commit pin, `astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0` |

## Tested commands

All run on 2026-10-21 with uv 0.11.32, Python 3.13.16, Node 24.22.1 and npm 11.19.1 (a checksum-verified binary from nodejs.org) unless the row says Node 22, in scratch projects outside the repo. Mac and deploy rows are marked.

| Command | What it proves | Result | Where |
|---|---|---|---|
| `python3 .claude/skills/keyframe-devops/scripts/selfcheck.py` (Node 24) | every file block in templates.md works as written: the hook (local no-op; fresh `NVM_DIR` gives Node 24), keyframe-modal's image line matches, `check.sh --predeploy` green, conftest guard incl. module-level `Settings` with a fake `.env`, and six negatives (no import-time block, tracked photo and hosted env file, pin drift, uv_version drift, dirty tree, lost darwin binding) | 16 `ok` lines, `selfcheck passed`, exit 0, 40 s | here (network for the Node download) |
| same, on Node 22 | the Python half (and the hook) runs anywhere; the web half is skipped with a note | 11 `ok` lines, `selfcheck passed (Python half only ...)`, 15 s | here |
| `uv lock` with the templates.md `pyproject.toml` (`environments` and `required-environments`) | the Stack resolves on 3.13 for both platforms; `required-markers` recorded in the lock | `Resolved 56 packages` (55 plus the project), 0.2 s | here |
| `uv pip compile req.txt --python-version 3.13 --python-platform <t> --only-binary :all:` for `aarch64-apple-darwin`, `x86_64-manylinux_2_28`, `x86_64-unknown-linux-gnu` | wheels only, identical set on Mac and Linux | each exit 0 with 55 pins; `diff` identical | here |
| same for `pillow==13.0.0` on `x86_64-manylinux_2_17` | Pillow 13 needs glibc >= 2.28 | unsatisfiable ("Wheels are required for `pillow`") | here |
| `uv sync --locked`, `uv run pytest -q` | install and offline tests with `pythonpath = ["."]` | 12 passed (the repo's 7 plus 5 guard tests) | here |
| `uv sync --locked --check` | the venv matches the lock | "Would make no changes", exit 0 | here |
| pin edited without re-locking: `uv lock --check`, then `uv sync --frozen` | `--check` fails loudly; `--frozen` hides it | exit 1 "needs to be updated"; `--frozen` exit 0 | here |
| `uv lock --check --offline` with an empty cache | the doctor's lock check needs no network | exit 0 in sync; exit 1 on drift | here |
| add `pyyaml==6.0.1` (sdist only for cp313), `uv lock` | `no-build` refuses at lock time | exit 1 "Wheels are required ... `--no-build`" | here |
| add `nvidia-nvjitlink-cu12==12.9.86` (no Mac wheel), `uv lock`, with `required-environments` | a package with no macOS arm64 wheel is refused | exit 1 "no `platform_machine == 'arm64' and sys_platform == 'darwin'`-compatible wheels", reported for the `python_full_version >= '3.15'` split | here |
| fake `glibcnew 1.0.0` (wheels `manylinux_2_39_x86_64` and `macosx_11_0_arm64`) via `find-links`, `uv add`, then `check.sh` | the markers miss the glibc floor; the `manylinux_2_28` compile catches it | `uv add` exit 0; `check.sh` exit 1 at the Linux wheel step, "has no wheels with a matching platform tag"; the step takes 0.07 s on the real lock (55 pins) | here |
| add `pyyaml==6.0.2` (cp313 wheels only, no cp314) | the 3.14 and 3.15 lock forks do not demand newer wheels | exit 0 | here |
| `uv add --no-sync "pyyaml==6.0.3"` vs `uv add --no-sync pyyaml` | exact pin only with `==X` | writes `pyyaml==6.0.3` vs `pyyaml>=6.0.3` | here |
| `uv export --frozen --no-hashes --no-emit-project \| uv pip compile - ... --python-platform aarch64-apple-darwin --only-binary :all: -o <scratch>` | the committed lock has Mac wheels | exit 0, 55 pins | here |
| conftest with a fake `.env` (`MODEL_PROVIDER=meta`, a fake key) and a module that builds `Settings` at import | the guard forces mock and blank keys before collection, blocks `httpx.get("https://pypi.org")`, keeps MockTransport | 4 passed in the selfcheck; without the import-time block the module-level test fails (negative) | here |
| a committed `tests/fixtures/sam31/living-room-1.jpg` and `keyframe-hosted.env` (force-added), then `check.sh` | the privacy step gates CI | exit 1 "tracked private files" listing both | here |
| `npm install` from a clean tree with the templates.md `package.json` and `.npmrc` | exact pins install; lock v3 records `@rolldown/binding-darwin-arm64`, `lightningcss-darwin-arm64` | added 24 packages, 13 s cold | here (Mac `npm ci` not run) |
| `rm package-lock.json && npm install` over a populated `node_modules` (only the linux binding installed) | whether regenerating over `node_modules` drops the Mac bindings | npm 11.19.1 still records both darwin bindings (reviewer run, Oct 21) | here |
| `npm ci` on Node 22.22.0 with `engine-strict` | a wrong Node fails loudly | exit 1 `EBADENGINE`, `Required: {"node":"24.x"}` | here, Node 22 |
| `npm ci` after changing `vite` to `8.3.5` in `package.json` only | lock drift fails | exit 1 `EUSAGE` "lock file's vite@8.3.4 does not satisfy vite@8.3.5" | here |
| `npm ci` with the darwin binding removed from the lock | npm 11 and the grep both catch it | exit 1 `EUSAGE` "Missing: @rolldown/binding-darwin-arm64@1.2.15"; grep exit 1 | here |
| `npx tsc --noEmit` without `@types/three`; `npm run build` with a type error | TS7016 and strict errors break the build | exit 2 TS7016; exit 2 TS2322 | here |
| `bash scripts/check.sh` | the whole CI job passes on the full stack | `check.sh: all green`, 9.2 s warm (11.4 s first run) | here |
| `check.sh` and `--predeploy` with a stand-in `modal_app.py` (image block as written), no Modal token | hosted import offline, image mirrors on every run, clean tree | green; `uv_version="0.13.4"` fails plain `check.sh` "must install uv.lock with .uv_sync"; dirty tree fails `--predeploy` | here |
| keyframe-modal selfcheck after its image block moved to `uv_sync` | the sibling skill still passes with the shared image line | `selfcheck passed`, same 62 `ok` lines as before the change, 0.7 s | here, offline |
| offline render of the image block (modal 1.6.2) | `--no-dev` and `uv:0.11.32` reach the build | `COPY --from=ghcr.io/astral-sh/uv:0.11.32`, `uv sync ... --no-dev --frozen`, `FROM python:3.13.3-slim-bookworm` | here (no build) |
| `actionlint` 1.7.12 on the templates.md `ci.yml` (setup-uv pinned by SHA) | the workflow is valid | exit 0 | here |
| SessionStart hook with `CLAUDE_CODE_REMOTE=true`, an empty `NVM_DIR` holding only a copy of `/opt/nvm/nvm.sh` (a fresh container), and `CLAUDE_ENV_FILE` | Node 24 installs and reaches later shells | exit 0 in 13.9 s (download, `uv sync`, `npm ci`, doctor 19 pass); a new shell sourcing the file prints v24.22.1, npm 11.19.1. Without `--no-use`: exit 3 in 0.16 s. Without `CLAUDE_ENV_FILE`: the warning, exit 0. Without `CLAUDE_CODE_REMOTE`: exit 0, nothing done | here |
| hygiene steps 3 to 6 in the scratch project: privacy grep, `.claude/skills` grep, hygiene commit, then fresh clone plus `check.sh` | nothing private tracked; no skill dependency; committed files suffice | greps print nothing (scratch and real repo, missing directories silent); the clone has only `.claude/hooks` and `settings.json`; green in 9.6 s | here |
| `uv audit`; `npm audit --omit=dev`; `uv tree --depth 1` | audits are clean; dev group shown | "no known vulnerabilities ... in 55 packages" (with an experimental warning); "found 0 vulnerabilities"; pytest shown as `(group: dev)` | here |
| license script in templates.md | the README list can be generated | 55 rows; SAM License (meta-sam-parser), UNKNOWN (fal-client), MIT-CMU, MPL-2.0 | here |
| `python3 .claude/skills/keyframe-devops/scripts/doctor.py` in the real repo (cloud mode) | doctor tolerates the pre-Oct 26 repo | 10 pass, 6 warn (Node 22, npm 10, no `uv.lock`, no `.venv`, Ollama absent twice), 0 fail, exit 0 | here, after `/dev/null` was repaired |
| same in the post-foundation scratch repo, Node 24 | every lock, web and privacy check passes | cloud 19 pass, 2 warn (Ollama), 0 fail; `--ci` 17 pass. Negatives: conflict markers in the lock give FAIL "web lock ... not valid JSON" and `--json` stays valid; `PATH=/usr/bin:/bin` gives FAIL for uv, node and npm; a tracked `.env.local`, `keyframe-hosted.env` and fixture `.jpg` FAIL while `web/public/logo.png` passes. Earlier on Oct 21: pin drift, `^8.3.4`, package.json drift, a staged `.HEIC`, `FAL_KEY` in `.env` each FAIL | here |
| doctor architecture with `sys.platform` faked to darwin | the wanted arch follows the OS, not the mode | arm64 PASS under `--ci` and `--cloud`; x86_64 FAIL "want arm64; a Rosetta shell" | simulated |
| doctor Mac path, with `sys.platform` and `platform.machine` faked and a fake Ollama server and CLI | version, tags, warm-up with `keep_alive=-1`, `/api/ps` parsing | 0.40.7 WARN, model resident, `SIZE 3.0 GiB, 100% GPU`; missing model FAIL; no server FAIL | simulated; confirm on the Mac |
| `python3 scripts/doctor.py` on the M1 | real Ollama, real RAM, arm64 | not run | Mac only |
| `npm ci` and `npm run build` on the M1 from the Linux-made lock | the recorded darwin bindings install | not run | Mac only |
| `modal serve -e dev`, `modal deploy` from the image block | image builds; `required_keys` enforced | not run | deploy only (keyframe-modal) |
| the CI job on GitHub | setup-uv, setup-node cache, runner overhead | not run | first deps-foundation PR |

## Spine changes (applied)

Luis approved these on Oct 21 and they are in `ARCHITECTURE-SPINE.md` (docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/):
- **Consistency Conventions:** the Dependencies row; the Code style row's first-providers-story clause (Python pins, `.python-version`, `uv.lock`, `pythonpath`).
- **AD-14:** `scripts/doctor.py` is exempt (stdlib, runs before uv sync).
- **Stack:** uv 0.11.32, Node 24.22, TypeScript 6.0.3 exact, `@types/three` 0.186.0, Ollama v0.40.6 (0.40.x accepted).
- **Structural Seed:** `check.sh`, `doctor.py`, `sit.py` in `scripts/`; root `.python-version`, `.nvmrc`, `uv.lock`, `.github/workflows/ci.yml`; `web/package-lock.json`, `web/.npmrc`.
- **Deferred:** CI beyond the single `scripts/check.sh` job; CD.

Outside the spine, also applied Oct 21: the `delivery-plan.md` hygiene list and post-checks; keyframe-modal `references/hosted-code.md`, its selfcheck (`.uv_sync(uv_version="0.11.32", extra_options="--no-dev")`) and `runbook.md` (`check.sh --predeploy`); the repo `.gitignore` (`.env.*`, `!.env.example`, `*.env`).

## Known issues

- **`node_modules/` is not in `.gitignore`.** The first web story adds it (`dist/` already covers `web/dist`); `doctor.py` fails on `web/node_modules` once `web/` exists.
- **Mac rows are unproven.** No Mac was available: the darwin npm bindings in a Linux-made lock, Ollama's real `/api/ps` output and the RAM use of `llama3.2:3b` on 16 GB (estimates range from 2.2 to 6.2 GB) are confirmed by the first `doctor.py` and `check.sh` run on the M1.
- **`/dev/null` in this container was a regular file** (48 bytes), left by an earlier `-o /dev/null` on Oct 21. Repaired on Oct 21 with `rm -f /dev/null && mknod -m 666 /dev/null c 1 3`; `doctor.py` checks it.
- **`uv audit` is experimental.** It prints a preview warning; that it queries OSV comes from third-party guides only. It stays a manual, non-blocking check.
- **The SessionStart hook assumes nvm at `/opt/nvm`**, as in today's containers. If an image drops nvm, `doctor.py --cloud` fails on Node and the hint names the fix. Repo hooks do not run in multi-repo sessions or project threads (templates.md has the setup-script fallback).
- **The ci.yml npm cache lines** go in with the first web story, because `setup-node` fails when `web/package-lock.json` does not exist.

## References

- https://docs.astral.sh/uv/concepts/projects/sync/: `--locked`, `--frozen`, `--check` and what each verifies.
- https://docs.astral.sh/uv/reference/settings/: `environments`, `required-environments`, `no-build`, `required-version`.
- https://docs.astral.sh/uv/concepts/projects/dependencies/: dependency groups; the `dev` group syncs by default; `--no-dev`.
- https://docs.astral.sh/uv/concepts/resolution/: universal resolution, forks and markers.
- https://docs.astral.sh/uv/guides/integration/github/: setup-uv, caching, `uv sync --locked` in CI.
- https://docs.astral.sh/uv/reference/cli/: `uv lock --check`, `uv export`, `uv pip compile --python-platform`.
- https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/: manylinux and glibc tags.
- https://docs.pytest.org/en/stable/reference/reference.html#confval-pythonpath: `pythonpath`.
- https://docs.npmjs.com/cli/v11/commands/npm-ci: `npm ci` refuses a lock out of sync and never writes it.
- https://docs.npmjs.com/cli/v11/using-npm/config: `save-exact`, `engine-strict`.
- https://docs.npmjs.com/cli/v11/configuring-npm/package-json#engines: `engines.node`.
- https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json: lockfile v3 and optional platform packages.
- https://raw.githubusercontent.com/nodejs/Release/main/schedule.json: Node 24 Maintenance LTS from 2026-10-20 to 2028-04-30; Node 26 LTS from 2026-10-28.
- https://vite.dev/guide/: Vite's Node requirement (20.19+, 22.12+).
- https://github.com/astral-sh/setup-uv: inputs `version`, `enable-cache`; exact tags only after v7.
- https://github.com/actions/setup-node and https://github.com/actions/checkout: v7, `node-version-file`, `cache-dependency-path`.
- https://docs.github.com/en/actions/reference/security/secure-use: pinning third-party actions to a full commit SHA; setup-uv's README uses `@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0` (the v10.3.0 release commit).
- https://code.claude.com/docs/en/hooks: SessionStart matchers (`startup`, `resume`, ...), `CLAUDE_ENV_FILE` only for SessionStart hooks, a failing SessionStart hook does not block the session.
- https://code.claude.com/docs/en/cloud-environments: setup script (non-zero exit stops the session), SessionStart hooks run locally and in the cloud, `CLAUDE_CODE_REMOTE` scoping, no repo hooks in multi-repo sessions or project threads.
- https://modal.com/docs/reference/modal.Image.md: `uv_sync` (frozen, `extra_options`, `uv_version`), `add_local_python_source`, `add_local_dir`.
- https://docs.ollama.com/faq and https://docs.ollama.com/api/ps: keep-alive, `OLLAMA_HOST`, auto-update, loaded models and `expires_at`.
- https://docs.ollama.com/macos: macOS 14+ requirement, app install.
- https://github.com/ollama/ollama/releases: v0.40.6 (Oct 16) and v0.40.7 (Oct 18).
