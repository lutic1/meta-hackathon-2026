# Hosted runbook: secrets, dev URL, deploy, warm window

Every command here needs a Modal account and token, so all of them are live-only. Their flags were checked with `--help` on modal 1.6.2 on 2026-10-21. None was run against Modal. A person runs them by hand, or starts `.github/workflows/deploy.yml` or `.github/workflows/ops.yml` from the Actions tab or by a push to their dedicated branches (below). There is no CD: no merge, schedule, hook or push to master or a `keyframe/**` branch runs `modal deploy`.

## One-time setup

1. Install the pinned client (`modal==1.6.2`) and log in with `modal setup` on the builder's machine. Never put a Modal token in the repo or in `.env`.
2. Create a dev Environment so `modal serve` never touches judging data: `modal environment create dev`. Named Dicts, Volumes and Secrets resolve inside the Environment of the app that looks them up, so `-e dev` gets its own `keyframe-jobs`, `keyframe-data` and `keyframe` Secret (https://modal.com/docs/guide/environments.md).
3. Create the Secret once per Environment, from the dashboard (Secrets panel) or from a file kept outside the repo:
   `modal secret create keyframe --from-dotenv ~/keyframe-hosted.env` (add `-e dev` for the dev copy, and `--force` to replace it).
   - Put only hosted keys in it: `MODEL_API_KEY`, `FAL_KEY`, `ACCESS_CODE`, and `OPENAI_COMPATIBLE_API_KEY` if the Riddler fallback runs hosted.
   - `MODEL_API_KEY`, `FAL_KEY` and `ACCESS_CODE` are the Secret's `required_keys` in `src/api/modal_app.py`, so `modal serve` and `modal deploy` fail by name when one is missing (an old key name counts as missing); the Meta adapter runs keyless (AD-14), so nothing later refuses a keyless Secret before the first Build fails.
   - Add `SPEND_CAP_USD` with the hosted allocation (20 through Wed Nov 4, and whatever the reset sets after it). Under `MODE=hosted` an unset `SPEND_CAP_USD` already defaults to 20 (AD-6, AD-14).
   - Never pass `KEY=value` pairs on the command line, where they land in shell history.
   - Never point `--from-dotenv` at the repo's `.env`. It holds local-only values (`GUIDE=ollama`, `OLLAMA_HOST`), and `Settings` refuses `MODE=hosted` with `GUIDE=ollama` (AD-14).
   - Key names may contain only letters, digits and underscores, and cannot start with a digit (https://modal.com/docs/guide/secrets.md).

## Develop against the dev URL

- `cd web && npm run build` first, because the image mounts `web/dist`.
- `modal serve -e dev -m src.api.modal_app` from the repo root.
  - The URL label ends in `-dev`: `https://<workspace>-<env suffix>--keyframe-web-dev.modal.run`. The source part carries the dev Environment's web suffix (https://modal.com/docs/guide/webhook-urls.md).
  - Code changes hot-reload, and the app stops when the command exits.
  - Expect neither Cron function (ledger export, session sweep) to run under `serve`. The Cron page says only that a deploy activates a schedule, so confirm this on the first serve.
- Without `-e dev`, `serve` runs in the default Environment and reads and writes the same Dicts and Volume as the deployed judge app.

## Deploy the judge URL (manual)

The same steps run on demand from `.github/workflows/deploy.yml` (Actions tab, deploy, Run workflow, choosing the Environment and `MIN_CONTAINERS`); the token comes from the repository's Actions secrets `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, never from a file; the chosen Environment's `keyframe` Secret must exist first (step 3 of the one-time setup), since the workflow creates a missing Environment but not its Secret.

By the owner's decision of Oct 29, the workflow also runs on a push to `deploy/main`, `deploy/main-warm` or `deploy/dev`, so a deploy can be started by a push alone. Push a commit master already carries, fast-forward only: `git push origin <master-sha>:refs/heads/deploy/main`. `deploy/main` deploys the `main` Environment with `MIN_CONTAINERS=0`, `deploy/main-warm` deploys `main` with `MIN_CONTAINERS=1` (Thu Nov 5 to Mon Nov 9, since any deploy resets the autoscaler override), and `deploy/dev` deploys `dev` with 0. The first step refuses a pushed commit that `origin/master` does not contain; master only advances on a green CI run, so a pushed deploy is always a green commit. One deploy per Environment runs at a time.

By hand:

1. Run the offline suite (`pytest`) and `scripts/selfcheck.py`, then `cd web && npm run build`, then `bash scripts/check.sh --predeploy` (keyframe-devops: `uv.lock` in sync, since the image installs it with `uv_sync`, which runs `--frozen`; CI's uv and `.python-version` match the image; clean tree; `web/dist` present).
2. Set `MIN_CONTAINERS` in the shell. Use 0 before Thu Nov 5, 1 from Thu Nov 5 to Mon Nov 9, and 0 again from Tue Nov 10. The decorator reads this value through `Settings` at deploy time.
3. `modal deploy -m src.api.modal_app` from the repo root.
   - The deploy asserts the Secret's `required_keys` (`MODEL_API_KEY`, `FAL_KEY`, `ACCESS_CODE`) when it hydrates the Secret; a failure naming one of them means the Secret in this Environment lacks it. Recreate it with `--force` and deploy again.
   - The default `--strategy rolling` lets old containers finish their in-flight inputs while new ones start.
   - `--strategy recreate` kills them, and Modal retries their inputs on the new containers. That would restart a running build, so do not use it while a build is in flight.
4. The deploy output prints the permanent URL, `https://<workspace>--keyframe-web.modal.run`, with no `-dev`. If the default Environment has a web suffix, the source part reads `<workspace>-<suffix>`. That URL goes in the submission.
5. Smoke test: `GET /api/meta` returns 200 with the hosted Retention summary. One Demo room opens. `POST /api/access/check` with the code returns `builds_left`.

## Warm container, Thu Nov 5 to Mon Nov 9

- Without a redeploy: `modal function autoscaler update keyframe/web --min-containers 1` on Thu Nov 5, and `--min-containers 0` on Tue Nov 10.
- The same update, followed by the settings printout, runs from `.github/workflows/ops.yml` (Actions tab, ops, Run workflow, action `warm` on Thu Nov 5 and `cool` on Tue Nov 10; `autoscaler-settings` only prints them), with the token from the repository's Actions secrets.
- Check the result with `modal function autoscaler settings keyframe/web`. It shows the active overrides, and who set them and when.
- In Python the same call is `modal.Function.from_name("keyframe", "web").autoscaler.update(min_containers=1)`. `update_autoscaler()` is deprecated in 1.6.2.
- Any `modal deploy` resets overrides to the decorator value, so keep `MIN_CONTAINERS=1` in the deploy shell for the whole window.
- Cost: `budgets.md` assumes about 1 core and 2 GiB for 120 hours, roughly $8 at list price. `web` sets no `cpu` or `memory`, so it requests Modal's default 0.125 core and 128 MiB and is billed on the higher of request and use (https://modal.com/docs/guide/resources.md). For an idle container, $8 is an upper bound. An idle warm container is still billed.

## Scheduled functions

- `ledger_export` runs at 06:00 America/New_York and `session_sweep` at minute 17 of every hour, on the deployed app.
- The daily export of the ledger, `scripts/ledger.py export`, also runs from `.github/workflows/ops.yml` (action `ledger-export`), which uploads `spend/exports/` as a workflow artifact for the builder to download and commit; the workflow never commits.
- Every ops action also runs by a push, by the owner's decision of Oct 29: make a new branch `ops/<action>-<n>` from master with one commit that adds `.github/ops/request.json`, for example `{"action": "warm", "environment": "main"}` (keys `action`, `environment`, `room_id`, `room_name`, `confirm`; the same values and defaults as the dispatch inputs, all strings), and push it once. A first job without the Modal token refuses the request unless the commit's parent is on master and the commit changes only that file, then validates the file; the purge still needs `"confirm": "purge"`. The request branches can be deleted afterwards. The file is never committed to master.
- After the first deploy, start one run by hand with the "run now" button on the app's dashboard page, so a snapshot exists before the next morning. Then `modal volume ls keyframe-data spend` lists `hosted-<date>.jsonl`.
- To pause the schedule, remove it from the decorator and redeploy. Modal schedules have no pause.

## Scripts on the Mac

- `seed_rooms.py`, `purge_judge_rooms.py` and `ledger.py export` pass `environment_name=` to every `from_name`. Check `modal environment list` and `MODAL_ENVIRONMENT` before running them anyway. A profile set to `dev` must not decide which Volume is seeded or purged.
- Run `purge_judge_rooms.py` against a dev judge room before Tue Nov 10.
- `ledger.py export`, `purge_judge_rooms.py --dry-run` and the real purge run the same way from `.github/workflows/ops.yml` (actions `ledger-export`, `purge-dry-run` and `purge`, the last only when the `confirm` input is the word `purge`), with `--env` set from the workflow's Environment input.
- The Demo room is promoted from a Judge room built on the judge URL, not seeded from the Mac: the ops workflow's `promote` action runs `promote_room.py` with its `room_id` and `room_name` inputs (both required), copying the Room, photos, cards and job record to `rooms/demo/` and leaving the originals, `cache-keys.json` and the Judge copy in place. The Demo copy's photos name their downscaled key as `original_path` too, and every file the Room references is checked against the upload before anything is written, as `seed_rooms.py` does.
- The quota's live atomicity check is the ops workflow's `quota-probe` action: `quota_probe.py --env <Environment>` races 30 processes for the 20 slot keys on a `modal.Dict.ephemeral()` in that Environment (never `keyframe-jobs`), then 8 processes for the last slot with 19 prefilled, prints the counts and exits 1 unless exactly 20 and exactly 1 won. Run it on `dev` before judge uploads are enabled and record the result.

## Inspect

- `modal app logs keyframe --since 2h` shows recent logs. `--function-call fc-...` filters to one build runner.
- `modal dict items keyframe-jobs 20` shows in-flight jobs (plain JSON dicts, per hosted-code.md).
- `modal volume ls keyframe-data rooms/demo` lists the seeded Demo rooms.
