# Monday, Oct 26: kickoff checklist

Goal: start the build behind the spend cap. The baseline is tagged,
the dependency foundation is in, and every live call goes through the
guarded SIT path. The day's build items are the Mon Oct 26 line of
`docs/specs/spec-keyframe/delivery-plan.md`.

## 1. Rules and access (kickoff, 1:00 PM ET)

- [ ] Read the Official Rules (published before today) and record the
      answers, dated, in the day's CHANGELOG entry: video length, repo
      visibility (ours is public throughout), whether a live link is
      required, the pre-existing-code policy, and whether changes to
      the hosted deployment are allowed after the Wed Nov 4 deadline.
      That last answer gates the Nov 5 to 9 hosted work: no means the
      Nov 4 deployment is the final hosted state, FR-32 and FR-33 are
      dropped and the README says so. Accept the Rules.
- [ ] Watch the kickoff livestream; note anything about rate limits or
      model ids that differs from `docs/specs/spec-keyframe/stack.md`.
- [ ] Claim the credits (Meta Model API; Baseten, Modal and Fireworks
      if used) and confirm the payment methods on dev.meta.ai, fal.ai
      and Modal.
- [ ] Keys go into `.env` only, never committed; `.env.example` lists
      the names (`META_MODEL_API_KEY`, `FAL_KEY` and the rest) with
      blank values.
- [ ] Join the event Discord. Office hours and announcements live there.

## 2. Baseline and foundation (stories 1.1, 1.2, then 1.3)

- [ ] Story 1.1: the `pre-hackathon-baseline` tag is pushed and the
      CHANGELOG baseline entry exists (planned for Sun Oct 25 night;
      run it first if it has not landed).
- [ ] Story 1.2, the deps foundation: uv with `uv.lock` and
      `.python-version`, `scripts/doctor.py`, the cloud hook and the
      scaffold fixes to `src/providers/meta_api.py` and
      `src/config.py`.
- [ ] Then story 1.3, `scripts/check.sh` and the one CI job.
- [ ] `uv run pytest` stays offline against the mock provider. Never
      edit the stub tests into live tests; live behavior is proven by
      SIT fixtures, not by the suite.

## 3. The ledger lands first; no live call today

- [ ] Stories 2.3 (spend ledger and cap), 2.4 (model-call cache), 2.5
      (local ledger file and disk cache) and 2.6 (ledger export and
      reset script) land before any real call. The cap is per mode:
      local 60 and hosted 20 through Wed Nov 4.
- [ ] No live call is made today. Stories 2.3, 2.4, 2.5 and 2.6 land
      first; the first live calls run Tue Oct 27 through
      `scripts/sit.py` (story 2.9), SIT-07 and SIT-06 first, per the
      SIT checklist; today's export is mock-only with a total of 0.
- [ ] `spend/exports/ledger-2026-10-26.json` is committed with the
      day's work.

## 4. Then build

- [ ] Schema v1 frozen; validator and state machine on the mock
      provider; the verified calls go into `src/providers/meta_api.py`
      only if the pre-kickoff verifications passed, else API wiring
      moves to Oct 27 and everything after slips a day.
- [ ] Submissions due Wed Nov 4, 9:00 PM ET; submit before 9:00 AM.
