# Check ladder (full)

Fastest to slowest. SKILL.md has the one-line summary of each rung; this page has the detail.

## 0. Agent inner loop

- **When:** every edit, in a container or on the Mac.
- **Command:** `uv run pytest -q tests/<package>`.
- **Catches:** logic regressions in the package the story owns.
- **Budget:** under 10 s.

## 1. Pre-push check (identical to CI)

- **When:** every agent before every push; Luis before every merge and after pulling a dependency PR.
- **Command:** `bash scripts/check.sh` (text in templates.md).
- **Runs:** the privacy grep over `git ls-files`; `uv lock --check`; `uv sync --locked`; `uv run pytest -q`; the Mac and `manylinux_2_28` wheel export compiles; once `src/api/modal_app.py` exists, its offline import and the image greps (`.uv_sync(uv_version=<ci.yml's>`, no `pip_install(`, `python_version` from `.python-version`); then, once `web/` exists, `npm ci`, `npm run build`, `npx tsc --noEmit` and the `@rolldown/binding-darwin-arm64` grep.
- **Catches:**
  - a tracked `.env*`, `*.env`, raw photo (also under `tests/fixtures/`) or private folder
  - `pyproject.toml` edited without re-locking, or a stale or uncommitted lock
  - a package that would build from source (`no-build`), one with no macOS arm64 wheel, or one whose Linux wheels need glibc above 2.28 (passes in the containers and CI, fails at the Modal build)
  - a Modal image that installs anything but `uv.lock`, or with a uv or Python version off CI's
  - offline test failures, including the boundary, AD-14 and type-staleness tests
  - live network use in a test (conftest socket guard)
  - a broken hosted module import
  - a TypeScript error or a missing `@types` package (TS7016)
  - a Vite build failure
  - `web/package-lock.json` out of sync with `package.json` (`npm ci` EUSAGE)
  - the wrong Node major (`engine-strict`, EBADENGINE)
  - macOS native npm bindings dropped from the lock
- **Budget:** 30 to 90 s warm (9.2 s measured on the scratch project with warm caches).

## 2. CI job

- **When:** push to master or a `keyframe/**` branch and every pull request (`.github/workflows/ci.yml`); branch protection requires `check` before merge. If the plan does not enforce branch protection on a private repo (GitHub Free may not), Luis keeps "CI green before merge" by hand.
- **Command:** checkout, setup-uv (0.11.32, cache), setup-node (`.nvmrc`, npm cache once `web/` exists), `bash scripts/check.sh`, with `MODEL_PROVIDER=mock` and no secrets.
- **Catches:** everything in rung 1 on a clean machine, which adds files that exist only locally (an uncommitted lock) and hand-modified virtualenvs.
- **Budget:** 2 to 4 min; `timeout-minutes: 10`.
- **Deploy and ops workflows:** `.github/workflows/deploy.yml` and `.github/workflows/ops.yml` are the only other workflows, both with the Modal token from the repository's Actions secrets, each started from the Actions tab (`workflow_dispatch`) or, by the owner's decision of Oct 29, by a push to its dedicated branches (never on a merge, a schedule or a push to master or `keyframe/**`). Deploy takes the Modal Environment and `MIN_CONTAINERS` as inputs, or on a push reads them from the branch (`deploy/main` and `deploy/main-warm` deploy `main` with 0 and 1, `deploy/dev` deploys `dev` with 0), refuses a pushed commit master does not already carry, and runs rung 7 (`bash scripts/check.sh --predeploy`), then `modal deploy -e <Environment> -m src.api.modal_app` and a `GET /api/meta` smoke test against the deployed URL. Ops runs on a push to `ops/**` with its inputs from `.github/ops/request.json`, accepted only as the one file changed by a commit on top of master. `ci.yml` still holds no secret and no deploy step.

## 3. Lock and platform checks

- **When:** inside rungs 1 and 2 on every run; by hand in every dependency PR (read the `uv.lock` and `package-lock.json` diffs: only the expected packages move).
- **Commands:** `uv lock --check`; `uv sync --locked` with `no-build = true`; the `aarch64-apple-darwin` and `x86_64-manylinux_2_28` `--only-binary :all:` export compiles; `npm ci`; the darwin binding grep. For diagnosis only: `uv tree`, `uv tree --outdated --depth 1`, `uv pip check`, `uv sync --locked --check` (reports a hand-modified venv).
- **Catches:** manifest and lock drift, source builds, a missing platform wheel, a lock regenerated from a polluted `node_modules`.
- **Budget:** under 10 s combined.

## 4. Doctor

- **When:** on the Mac at the start of each work session, after a reboot or an Ollama auto-update, and before SIT; right before each video take on Tue Nov 3 and before the finals (Mon Nov 9): `python3 scripts/doctor.py` with the warm-up, and a FAIL or a guide model that is not resident stops the take (the HintPhraser falls back to verbatim after 5 s and only logs `phraser_fallback`, so a cold or stopped Ollama would ship unnoticed). In containers as the last step of the SessionStart hook, or whenever something environment-shaped fails.
- **Command:** `python3 scripts/doctor.py` (Mac), `python3 scripts/doctor.py --cloud` (containers), `--ci` to skip machine-only checks, `--json` for machine output, `--no-warm` to skip the Ollama warm-up. `scripts/doctor.py` exists since the deps-foundation story (Oct 26). (amended 29 Oct 2026, correct-course record)
- **Both modes:** `.python-version` is 3.13, uv at 0.11.32 or newer, Python 3.13 findable by uv, Node major from `.nvmrc` and npm 11 (WARN before `.nvmrc` or `web/` exist, FAIL after; still reported when uv is missing), `uv lock --check --offline`, web lock valid JSON and in sync, exact versions, darwin bindings and `.npmrc`, `.gitignore` covers `.env`, `.env.*`, `*.env` and the privacy paths, nothing private tracked or staged (the `check.sh` pattern), Settings imports, the architecture the OS needs (arm64 on macOS in any mode), `/dev/null` is a character device, free disk.
- **Mac adds:** `.env` exists with every key name from `.env.example` (WARN only); port 8000 free; `ollama --version` is 0.40.x (WARN on a patch other than 0.40.6, FAIL off 0.40); `/api/version`; `GUIDE_MODEL` in `/api/tags`; one chat with `keep_alive=-1`, then `/api/ps` shows SIZE, the GPU share and a far-future `expires_at`.
- **Cloud adds:** x86_64, glibc 2.28 or newer, no `.env` with secret values; Ollama absent is a WARN.
- **Budget:** under 10 s (the Mac warm-up under 30 s).

## 5. Dev-skill selfchecks after a bump

- **When:** in any dependency PR that moves a pin a skill covers, and once on Mon Oct 26 after the deps-foundation story merges.
- **Commands:** (offline, from uv's cache; `--no-project` keeps uv away from the repo's venv)
  - modal: `uv run --no-project --with modal==<new> python .claude/skills/keyframe-modal/scripts/selfcheck.py`
  - httpx or pydantic: `uv run --no-project --with httpx==<x> --with pydantic==<y> python .claude/skills/keyframe-muse/scripts/selfcheck.py`
  - meta-sam-parser or httpx: `uv run --no-project --with meta-sam-parser==<x> --with httpx==<y> python .claude/skills/keyframe-sam31/scripts/selfcheck.py`
  - fal-client, httpx or Pillow: `uv run --no-project --with fal-client==<x> --with httpx==<y> --with pillow==<z> --with jsonschema==4.26.0 python .claude/skills/keyframe-sam3d-fal/scripts/selfcheck.py`
  - uv, Node, Vite, TypeScript, three, or any template here: `python3 .claude/skills/keyframe-devops/scripts/selfcheck.py` under Node 24
- Then update the pin and the result in that skill's Tested commands table.
- **Catches:** API facts a skill asserts (signatures, retry sets, wire shapes, decorator rules) going stale under a new version.
- **Budget:** 10 to 60 s each.

## 6. `scripts/sit.py` live seams

- **When:** Luis on the Mac, after the doctor passes, at the end of each build day from Tue Oct 27 (about 10 cases), a full pass Sat Oct 31, and once against the Modal dev URL after the first `modal serve -e dev`.
- **Command:** `uv run python scripts/sit.py` (uses the `.env` keys; `SPEND_CAP_USD` enforced; responses recorded as fixtures for the offline suite, AR-25).
- **Catches:** live Meta API, SAM and fal contract drift, bad or expired keys, Ollama phrasing and keep-alive, cache behaviour, the real build round trip: everything mocks and fixtures cannot see.
- **Budget:** 5 to 10 min per daily run, about 30 min for the full pass; spend logged.

## 7. Pre-deploy (Modal)

- **When:** Luis, before every manual `modal deploy` (first Tue Oct 27; redeploys Nov 5 to 8). Also after any merged dependency PR and in the Sat Oct 31 full SIT pass: `check.sh --predeploy` plus a `modal serve -e dev` smoke, so a dependency that breaks the image between deploys shows up before submission. Both are manual; CI stays one job.
- **Sequence:**
  1. `bash scripts/check.sh --predeploy`: rung 1 (which already checks the image's `uv_sync`, uv and Python mirrors), plus a clean git tree and `web/dist/index.html` after the build.
  2. The keyframe-modal selfcheck.
  3. `modal serve -e dev -m src.api.modal_app`, then smoke it.
  4. `modal deploy -m src.api.modal_app`.
  5. Smoke: `GET /api/meta` is 200, one Demo room opens, `POST /api/access/check` returns `builds_left`.
- **Catches:** a stale lock shipped by `uv_sync --frozen`, a missing `web/dist` (checked by Modal only at image build), pytest in the image, `uv:latest` drift, a missing Secret key (`required_keys`), deploying uncommitted code, builder-version surprises.
- **In the workflow:** `.github/workflows/deploy.yml` runs steps 1, 4 (as `modal deploy -e <Environment>`, creating a missing Environment but not its Secret) and the `GET /api/meta` part of step 5, with no `modal serve` and no selfcheck. The first deploy ran through it on Wed Oct 28 (run 3, `0452a4c`); deploy runs 7 and 8 on Thu Oct 29 put `1e8578a` and `02965dd` on the judge URL. Its ops twin, `.github/workflows/ops.yml`, runs `ledger-export`, `purge-dry-run`, `purge` (only with `confirm` set to `purge`), `warm`, `cool`, `autoscaler-settings`, `promote`, `patch-demo-room` (a dry run unless `confirm` is `patch`), `story-demo-room` (a dry run unless `confirm` is `story`) and `quota-probe`. (amended 29 Oct 2026, correct-course record)
- **Budget:** about 5 min plus the image build.

## 8. Nov 4 hygiene

- **When:** Wed Nov 4 morning, before the repo goes public; rehearse steps 3 to 5 on Sat Oct 31 (in a scratch clone, so nothing is committed early).
- **Sequence:**
  1. The delivery-plan command: `git rm -r --cached --ignore-unmatch _bmad .claude/skills/modal .claude/skills/bmad-* .claude/skills/keyframe-*`, plus the delivery plan's `.gitignore` entries (`_bmad/`, `.claude/skills/bmad-*/`, `.claude/skills/keyframe-*/`, `.claude/skills/modal/`). delivery-plan.md, Repo hygiene, is the source of truth; if it changes, follow it.
  2. `git diff --cached --name-status` lists only `D` entries under those paths.
  3. `git ls-files | grep -Ei '\.env$|(^|/)\.env\.|\.(jpe?g|heic|png)$|^(rooms|photos|captures|uploads|\.cache|cache)/' | grep -Ev '(^|/)\.env\.example$|^(web/public|docs/screenshots)/'` prints nothing (the `check.sh` privacy pattern). If anything private was ever pushed, `git rm --cached` is not enough: rotate the key, then purge history or publish from a fresh history before going public.
  4. `grep -rnsE '\.claude/skills|_bmad/' src tests scripts web/src` prints nothing (no shipped code depends on removed tooling; `-s` keeps missing directories silent; `.claude/hooks` stays).
  5. Commit the hygiene change, then check a fresh clone of that commit: `d=$(mktemp -d) && git clone -q . "$d/k" && (cd "$d/k" && bash scripts/check.sh)`. Before the commit, HEAD still contains the skills and the clone proves nothing.
  6. Push; CI is green on the hygiene commit.
  7. By hand, non-blocking: `uv audit` and `cd web && npm audit --omit=dev`.
  8. The README third-party licenses section has the generated list (templates.md), the SAM License, the Llama 3.2 license, the Meta Model API and fal terms, and fal-client as Apache-2.0.
- **Catches:** removed tooling that shipped code depends on, files never committed, a tracked `.env` or raw photo, a stray `.claude/` path in the staged diff, missing license disclosures.
- **Budget:** about 15 min.
