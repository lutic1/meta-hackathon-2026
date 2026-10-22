# Monday, Oct 26: kickoff checklist

Goal: start the build behind the spend cap. The baseline is tagged,
the dependency foundation is in, and every live call goes through the
guarded SIT path. The day's build items are the Mon Oct 26 line of
`docs/specs/spec-keyframe/delivery-plan.md`.

## 0. Before Monday (Oct 21 to 25, verified Oct 20)

The Meta Model API is already public (paid since July 9, 2026), so
Monday is not the first touch of it. This week:

- [ ] Create a Meta Model API account at dev.meta.ai, configure
      billing, and generate an API key. New accounts start with $20
      in free credits.
- [ ] Copy the key into `.env` as `META_MODEL_API_KEY`. Pre-kickoff
      verifications (the Architect vision call, `sam-3.1` masks, one
      Riddler call) run as scratch scripts against the live API, up to
      about $5 cash (`docs/specs/spec-keyframe/budgets.md`); the
      scaffold itself is not expanded before Mon Oct 26 (story 1.2
      wires `src/providers/meta_api.py` then).
- [ ] Use the standard `muse-spark-1.3` tier, NOT
      `muse-spark-1.3-contributor`. The contributor tier is far
      cheaper (about $0.10/$0.20 per 1M tokens vs $1.25/$4.25) because
      Meta may use the data to improve its products. Room photos go
      in, so pay the standard tier.
- [ ] Know the two SAM models by their real jobs. `sam-3.1` (via the
      API) does segmentation and tracking only: a text prompt
      ("sofa") to boxes and masks (the 16-object cap applies only to
      box and point prompts; a text prompt returns every match). It
      does NOT do 3D. SAM 3D Objects is the single-image 3D
      reconstruction model, Keyframe's Tier 2 engine.
- [ ] SAM 3D Objects is NOT on the hackathon's API list (the page
      names the Muse Spark series, Muse Image, and SAM 3.1 via the
      API). Keyframe runs it cloud-only on fal.ai
      (`fal-ai/sam-3/3d-objects`, $0.02 per call), Tier 2 only and
      gated Mon Nov 2; no GPU deployment of the open weights.
- [ ] Run the pre-Oct 26 fal spike (five objects from a real room
      photo) so the Mon Nov 2 go/no-go on full 3D is not the first
      time a phone photo becomes a mesh.
- [ ] Read the approval email (Cerebral Valley Events, Oct 20,
      5:43 AM EDT). That is where the Discord invite and the
      hackathon-specific credit claim path live. Join Discord now;
      workshops run Oct 27 to Nov 4 and office hours live there.

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
