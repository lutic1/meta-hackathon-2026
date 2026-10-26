# Hosted runbook: secrets, dev URL, deploy, warm window

Every command here needs a Modal account and token, so all of them are live-only. Their flags were checked with `--help` on modal 1.6.2 on 2026-10-21. None was run against Modal. A person runs them by hand. There is no CD: no workflow file, hook or script runs `modal deploy`.

## One-time setup

1. Install the pinned client (`modal==1.6.2`) and log in with `modal setup` on the builder's machine. Never put a Modal token in the repo or in `.env`.
2. Create a dev Environment so `modal serve` never touches judging data: `modal environment create dev`. Named Dicts, Volumes and Secrets resolve inside the Environment of the app that looks them up, so `-e dev` gets its own `keyframe-jobs`, `keyframe-data` and `keyframe` Secret (https://modal.com/docs/guide/environments.md).
3. Create the Secret once per Environment, from the dashboard (Secrets panel) or from a file kept outside the repo:
   `modal secret create keyframe --from-dotenv ~/keyframe-hosted.env` (add `-e dev` for the dev copy, and `--force` to replace it).
   - Put only hosted keys in it: `META_MODEL_API_KEY`, `FAL_KEY`, `ACCESS_CODE`, and `OPENAI_COMPATIBLE_API_KEY` if the Riddler fallback runs hosted.
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

1. Run the offline suite (`pytest`) and `scripts/selfcheck.py`, then `cd web && npm run build`, then `bash scripts/check.sh --predeploy` (keyframe-devops: `uv.lock` in sync, since the image installs it with `uv_sync`, which runs `--frozen`; CI's uv and `.python-version` match the image; clean tree; `web/dist` present).
2. Set `MIN_CONTAINERS` in the shell. Use 0 before Thu Nov 5, 1 from Thu Nov 5 to Mon Nov 9, and 0 again from Tue Nov 10. The decorator reads this value through `Settings` at deploy time.
3. `modal deploy -m src.api.modal_app` from the repo root.
   - The default `--strategy rolling` lets old containers finish their in-flight inputs while new ones start.
   - `--strategy recreate` kills them, and Modal retries their inputs on the new containers. That would restart a running build, so do not use it while a build is in flight.
4. The deploy output prints the permanent URL, `https://<workspace>--keyframe-web.modal.run`, with no `-dev`. If the default Environment has a web suffix, the source part reads `<workspace>-<suffix>`. That URL goes in the submission.
5. Smoke test: `GET /api/meta` returns 200 with the hosted Retention summary. One Demo room opens. `POST /api/access/check` with the code returns `builds_left`.

## Warm container, Thu Nov 5 to Mon Nov 9

- Without a redeploy: `modal function autoscaler update keyframe/web --min-containers 1` on Thu Nov 5, and `--min-containers 0` on Tue Nov 10.
- Check the result with `modal function autoscaler settings keyframe/web`. It shows the active overrides, and who set them and when.
- In Python the same call is `modal.Function.from_name("keyframe", "web").autoscaler.update(min_containers=1)`. `update_autoscaler()` is deprecated in 1.6.2.
- Any `modal deploy` resets overrides to the decorator value, so keep `MIN_CONTAINERS=1` in the deploy shell for the whole window.
- Cost: `budgets.md` assumes about 1 core and 2 GiB for 120 hours, roughly $8 at list price. `web` sets no `cpu` or `memory`, so it requests Modal's default 0.125 core and 128 MiB and is billed on the higher of request and use (https://modal.com/docs/guide/resources.md). For an idle container, $8 is an upper bound. An idle warm container is still billed.

## Scheduled functions

- `ledger_export` runs at 06:00 America/New_York and `session_sweep` at minute 17 of every hour, on the deployed app.
- After the first deploy, start one run by hand with the "run now" button on the app's dashboard page, so a snapshot exists before the next morning. Then `modal volume ls keyframe-data spend` lists `hosted-<date>.jsonl`.
- To pause the schedule, remove it from the decorator and redeploy. Modal schedules have no pause.

## Scripts on the Mac

- `seed_rooms.py`, `purge_judge_rooms.py` and `ledger.py export` pass `environment_name=` to every `from_name`. Check `modal environment list` and `MODAL_ENVIRONMENT` before running them anyway. A profile set to `dev` must not decide which Volume is seeded or purged.
- Run `purge_judge_rooms.py` against a dev judge room before Tue Nov 10.

## Inspect

- `modal app logs keyframe --since 2h` shows recent logs. `--function-call fc-...` filters to one build runner.
- `modal dict items keyframe-jobs 20` shows in-flight jobs (plain JSON dicts, per hosted-code.md).
- `modal volume ls keyframe-data rooms/demo` lists the seeded Demo rooms.
