---
title: Keyframe UAT sign-off record
status: final
created: 2026-10-21
updated: 2026-10-22
sources:
  - docs/implementation-artifacts/uat-acceptance-tests.md
  - docs/implementation-artifacts/sit-checklist.md
  - docs/implementation-artifacts/sprint-status.yaml
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md
  - docs/planning-artifacts/epics.md
  - docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
  - docs/specs/spec-keyframe/budgets.md
  - docs/specs/spec-keyframe/delivery-plan.md
  - docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md
---

# Keyframe UAT sign-off record

Luis Ticas completes this form Mon Nov 2 evening, after the last UAT run, using the test ids in `uat-acceptance-tests.md`. Evidence is listed by file name only: no raw room photo, HAR export or `.cache/` path is ever an evidence path or committed.

## 1. Header

| Field | Value |
|---|---|
| Product | Keyframe |
| Build commit (short hash) under test | |
| Date and time (ET) | Mon Nov 2, |
| Environment | Local mode, 16 GB M1, Chrome; `llama3.2:3b` on Ollama (absent under cut 3). Hosted URL (story 7.3) for UAT-14 A |
| `scripts/check.sh` on this commit | pass / fail |
| `python3 scripts/doctor.py` on the M1 | pass / fail |
| Day's `spend/exports/ledger-<date>.json` committed | yes / no |
| Cuts in force (0 to 8, as recorded in the sprint status) | |
| Demo timescale per test | 1 except UAT-05 part B, UAT-07 part A, UAT-08 step 5 (the demo-flag check, on dev), UAT-10 steps 1-3, UAT-13 (`DEMO_TIMESCALE=6`, disclosed) |
| `DEMO_TRICKSTER` | live / scripted / authored (cut 1) |
| PROFILE used | `playtest` (UAT-03), `demo` (Mon Nov 2 room-1 run only), `dev` (all others) |
| Signatory | Luis Ticas |
| SM-2 run by | Playtester name: ______ / Disclosed builder cold run of room 2 (§11.2 fallback) |

## 2. Results

Result is pass, fail or not run; the Cut variant run goes in Notes. Addenda are signed in their own rows of the §8 Addenda table: UAT-12 and UAT-13 (Tue Nov 3) before the submission; UAT-09 B Wed Nov 4 before story 6.9; the UAT-14 A live-link line Wed Nov 4 only if the Official Rules require a live link, after a SIT-10 pass against the deployed commit; UAT-14 B after the Thu Nov 5 redeploy and before judges are given the URL, only if the Official Rules allow changes to the hosted deployment after the deadline (otherwise not applicable, not failed).

| Id | Result | Evidence path | Notes (Cut variant, measured values) |
|---|---|---|---|
| UAT-01 Capture a room from your own photos | | | |
| UAT-02 Verified rooms, the Build view, zero solution tokens | | | |
| UAT-03 A non-builder finishes room 1 | | | |
| UAT-04 Persuasion opens nothing | | | |
| UAT-05 The Rung ladder and its triggers | | | |
| UAT-06 Local phrasing within 5 s, verbatim fallback | | | |
| UAT-07 The Trickster, accepted and rejected | | | |
| UAT-08 Room 2 remembers the player | | | |
| UAT-09 A Spend within the cap, cache and Ledger | | | |
| UAT-09 B Nov 3 and Nov 4 exports, final local, hosted and combined totals (addendum, Wed Nov 4) | | | |
| UAT-10 Disclosure, Privacy line, demo honesty | | | |
| UAT-11 Accessibility floor smoke test | | | |
| UAT-12 Capture proof on video (addendum, Tue Nov 3) | | | |
| UAT-13 Main demo carries every proof beat (addendum, Tue Nov 3) | | | |
| UAT-14 A Judge on the hosted URL (Tier 1) | | | |
| UAT-14 A live link (addendum, Wed Nov 4, only if the Official Rules require one) | | | |
| UAT-14 B Judge on the hosted URL (Tier 1.5, addendum after the Thu Nov 5 redeploy) | | | not applicable (the Official Rules forbid post-deadline hosted changes) / run |
| UAT-15 Tier 2 gate record (conditional) | | | not attempted / no-go (reason) / run |
| UAT-15b UJ-7 walk (only after the gate passed) | | | not in this submission / run |

## 3. Counter-metric attestations

| Id | Attestation | yes / no | Evidence |
|---|---|---|---|
| SM-C1 | No Build was sped up by weakening the Validator or Dry run: no `DRY_RUN=off` without cut 4, no skipped Validator rule, `REGEN_MAX` not above 2, the Capture target not met only with `CACHE=on` | | UAT-01, UAT-02, UAT-12 |
| SM-C2 | No Rung arrived sooner than FR-15 allows: no nudge before the nudge threshold of Idle or 3 Wrong attempts, and no later Rung that arrives before a further stall equal to the nudge threshold or 3 further Wrong attempts, or less than 90 s after the previous Rung; an accepted Loosen Card is the only early Rung | | UAT-03, UAT-05 (Triggers panel, Event log) |
| SM-C3 | No Tier 1 traded for Tier 2: the Mon Nov 2 real room-1 run took place, no Tier 1 UAT regressed, no Tier 2 shot replaces a Tier 1 beat | | UAT-13, UAT-15, story 8.1 record |
| SM-C4 | No Rung made vaguer: every near-answer on a video Room let the Dry run reach the answer; n/a under cut 4 (no Dry run), disclosed in the README | | UAT-02 |

## 4. Known deviations and Disclosures

What the README (story 6.7) and the Disclosure banner (stories 6.2, 6.3) will say:

| Item | Entry |
|---|---|
| Cuts shipped (README names each of 0 to 8 as shipped or not) | 0 __ 1 __ 2 __ 3 __ 4 __ 5 __ 6 __ 7 __ 8 __ |
| Capture target | 120 s / re-based to p50 plus 25% on Wed Oct 28 (story 2.26): ___ s |
| NFR misses logged (stage over budget, phrasing over 5 s) | |
| Playtest outcome | Non-builder finished room 1 / builder cold run of room 2, non-builder criterion not met |
| Model table shipped status (cut 1: no live Trickster call; cut 3: no Ollama phrasing; cut 4: no Dry run) | |
| Phrasing claim in README | kept / dropped (cut 3) |
| Privacy line, verbatim | "the player profile stays on your machine." (stays under every Cut) |
| Retention summary | The Local `retention` text served by `GET /meta`, word for word; no fal.ai line unless Tier 2 ships |
| Tier 2 | not attempted / no-go / ships Tier 1 (missed criterion) / passed |
| Live link (only if the Official Rules require one) | Tue Oct 27 hosted smoke deployment, Demo rooms only, Rungs verbatim; SIT-10 passed against the deployed commit: hash ______ date ______ |
| Hosted changes after the deadline (checked at kickoff Mon Oct 26) | allowed / not allowed by the Official Rules; if not allowed, the Wed Nov 4 deployment is the final hosted state and UAT-14 B and every Nov 5 to 9 hosted item are not applicable, not failed |

Disclosure lines in force for the video settings (tick each; text as served by `src/api/meta.py`):

- [ ] "Hint and Trickster timings run at 6× speed; the build timer is real time."
- [ ] "Trickster proposals replayed from a recording; the Validator ran live." (scripted) or [ ] "Trickster proposals were written in advance; the Validator ran live on each." (cut 1)
- [ ] "This room was built earlier, on <date>."
- [ ] Hosted: "Hosted mode: hints are shown as written; no hint model runs here."

## 5. SIT status

From the run log in `sit-checklist.md` and the sprint status. No separate SIT sign-off exists; a green Sat Oct 31 full pass is a UAT entry criterion.

| Field | Value |
|---|---|
| Latest dated full pass | Sat Oct 31: cases run __ / pass __ / fail __ |
| Latest daily run before sign-off | date ______: pass __ / fail __ |
| Failing seams (SIT ids) and action taken | |
| Fallback applied for a red seam (Cut, Baseten, boxes-only Hotspots, placeholder art) | |
| SIT-08, SIT-09 (run by hand until a story adds their modules) and SIT-10 (module from story 7.23) | SIT-10 first run Thu Oct 29 (gates UAT-14 A; a live link needs a pass against the deployed commit): ___; SIT-08, SIT-09 after 7.8, 7.9 and 7.11 merge, before Thu Nov 5 (gate UAT-14 B only): ___ |
| SIT-12 fal SAM 3D | not run (Tier 2 not attempted) / result |

## 6. Decision

Circle one: **accept** / **accept with conditions** / **reject**

| Decision | Tue Nov 3 (video only) | Wed Nov 4 (submit before 9:00 AM ET) |
|---|---|---|
| Accept | Capture proof and three Main demo takes (story 6.6); UAT-12 and UAT-13 signed as addenda | README final (6.7), repo hygiene (6.8), submit (6.9) |
| Accept with conditions | Same, filmed under the conditions below; no feature work, so a condition is a Cut, a Disclosure or a re-take, never new code | Each condition is reflected in the README Cuts and Disclosures before 6.8 |
| Reject | No feature work Tue Nov 3. A failing test is fixed or its Cut taken that night (§11.2) and the test re-run and re-signed before the takes. Tue Nov 3: the Capture proof (UAT-12) is still recorded; only the main demo falls back to the backup | If not re-signed, the Sun Nov 1 2:00 PM backup is the submission video; 6 to 9 PM is the slack |
| Addendum: UAT-12 or UAT-13 still failing at the end of Tue Nov 3 | Re-takes only; no feature work | Re-shoot Wed Nov 4 before 9:00 AM. If UAT-13 still fails, submit the Sun Nov 1 2:00 PM backup as the main demo. If UAT-12 still fails, submit the best kept take with its measured T1 − T0 disclosed in the README as an SM-1 miss, never an edited take. Use the 6 to 9 PM slack only for the upload or the live link |

Conditions (each with the Cut or Disclosure it implies and the test re-run under it):

1.
2.
3.

## 7. Tier 2 gate input

Story 8.1 cites this record. The delivery plan's condition: Tier 2 is attempted Sun Nov 1 only if the Tier 1 backup video already existed Sat Oct 31 night, and gated Mon Nov 2; any miss ships Tier 1.

| Input | yes / no / value |
|---|---|
| Backup video v1 existed Sat Oct 31 night (story 6.4 record) | |
| NFR-10 DOM-only fallback taken (forces no-go) | |
| Sun Nov 1 2:00 PM backup exists | |
| Tier 1 UAT passed (UAT-01 to UAT-11, UAT-14 A) | |
| Real room-1 run on `PROFILE=demo` at Demo timescale 1 done Mon Nov 2 | |
| Spike ran Sun Nov 1 (10 objects through `fal-ai/sam-3/3d-objects`) | |
| Interactables recognizable in position (pass at 7 of 10) | __ of 10 |
| Frame rate on the M1 (pass at 30 fps or better) | __ fps |
| Every Puzzle triggered by raycast | |
| Pre-Oct 26 five-object fal cash | $__ |
| Sun Nov 1 spike fal cash from the `reconstruct3d` entries in `spend/exports/ledger-<date>.json` (fal receipts attached to the Spend log) | $__ |
| Total within $6 | yes / no |
| Gate decision (story 8.1) | not attempted / no-go (reason) / ships Tier 1 (missed criterion) / passed |

## 8. Sign-off

Luis Ticas: I ran every test marked run in §2 at the commit in §1; addenda are attested in their own rows below. I accept the decision in §6.

Signature: ____________________  Date and time (ET): ____________________

Addenda (one row each; the result reads pass, fail or not applicable):

| Test id | Commit short hash or deployment URL | Settings and Cuts in force | Date | Result | Evidence | Signature |
|---|---|---|---|---|---|---|
| UAT-12 | | | | | | |
| UAT-13 | | | | | | |
| UAT-09 B | | | | | | |
| UAT-14 A live link (only if the Official Rules require one; SIT-10 passed against this commit) | | | | | | |
| UAT-14 B (only if the Official Rules allow post-deadline hosted changes; otherwise not applicable) | | | | | | |

Playtester attestation for SM-2: "I did not build Keyframe. I finished room 1 on a fresh profile on <date> with no help from the builder; the Guide's hints were the only help."

Name: ____________________  Signature: ____________________  Date: ____________________

(The unassisted cold run of room 2 is recorded as soon as room 2 reaches `done`, before anyone reads room 2, whether or not a playtester is confirmed; it is used only if the non-builder criterion is missed and discarded otherwise. If the §11.2 fallback was used, the playtester line is left blank and Luis initials here: ______ builder cold run of room 2, disclosed in the README.)
