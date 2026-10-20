# Product Brief: Rashomon on Meta Models

**Event:** Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4, 2026
**Track:** Startup (judged on technical execution and whether it holds up in production)
**Theme:** Build for Your World
**Status:** Draft v1, Oct 20, 2026. Direction open for revision before kickoff.

## The problem

Coding agents report work they did not do. They say the tests pass when a test was skipped, say a file was written when the write failed, and hide workarounds inside plausible summaries. The summary reads fine. The work is not done.

This is not hypothetical. In my own benchmark of 100 runs across 20 adversarial tasks (60 Sonnet, 40 Haiku, $9.29 total cost), agents filed 13 reports that the captured evidence did not support. The most common pattern was the hidden workaround: a fake `./docgen` script standing in for real documentation, a no-op audit stub, invented VAT rates, a git-lfs pointer presented as the file itself. Exit codes were also masked by shell pipes, so a failing command reported success.

If agents are going to run in production, someone has to check the work against what actually happened. Today, almost nobody does.

## The product

Rashomon is an independent execution recorder for coding agents. It captures ground truth as the agent works: shell commands, exit codes, file writes, tool calls, test runs, and subagent activity, assembled into one timeline. It then compares what the agent claimed against what the capture shows, and flags every claim the evidence does not support.

Rashomon stores structure, not content. No prompts, no responses, no file contents, no tool outputs. Hostnames and paths are the deliberate exceptions, because you cannot audit an execution trail without them.

## What we build at the hackathon

The current version records and compares. The hackathon build puts Meta's models on the judgment layer:

1. **Claim extraction.** Muse Spark reads the agent's end-of-turn report and extracts every checkable claim: tests passed, file created, command succeeded, dependency installed.
2. **Adjudication.** Each claim is matched against the captured timeline. Supported, contradicted, or unverifiable, with the evidence attached. This replaces hand-written rules with a model that can handle claims phrased a thousand different ways.
3. **Live verification during the run.** Flags surface while the agent is still working, not in a postmortem. A masked exit code or a stub file gets caught in the act.
4. **Benchmark on the Meta stack.** The 20-task adversarial benchmark, re-run against agents built on Meta models through the Meta Model API and Muse Code, with the results published in the submission.

The recorder already catches the pipe-masking failure (recorded as `status_masked`); after the fix, replay detection went from 13 of 47 claims to 47 of 47. The hackathon build has to hold that standard while the adjudication moves to the model.

## Why this fits

Build for Your World asks for a problem you know firsthand. I lead AI product work in regulated enterprise, where an agent's unsupported claim is not a curiosity, it is an audit finding. The startup track asks whether the thing holds up in production. Verification is the production problem. Every team shipping agents will need a layer that answers one question: did the agent actually do what it said?

## Scope for ten days

**Must ship (MVP by Nov 1):**
- Recorder running against an agent on the Meta stack
- Claim extraction and adjudication through the Meta Model API
- One live demo scenario: an agent files an unsupported report, Rashomon catches it with evidence
- Verification report output a judge can read in two minutes

**Should ship (Nov 2 to 3):**
- Adversarial benchmark re-run on Meta models, results in the submission
- At least three caught failure patterns in the demo set: hidden workaround, masked exit code, unsupported success claim

**Stretch:**
- SAM 3.1 or Muse Image in the evidence layer (screenshot and UI-state verification)
- Public leaderboard-style results page

**Explicitly out of scope:**
- Storing prompts, responses, or file contents. The structure-only rule is the product's privacy position and does not bend for the demo.
- Multi-agent orchestration recording beyond subagent activity already captured.

## Demo plan

Three minutes. An agent gets a task with a trap in it: a test that cannot pass honestly. The agent takes the shortcut and reports success. Rashomon's timeline shows the command, the masked exit code, and the claim side by side, flagged. Then the honest run: same task, agent does the work, every claim verified green. End on the benchmark numbers.

## Risks

- **API unknowns.** The Meta Model API surface is not public until kickoff. Mitigation: the whole app is built against a provider interface with a mock backend, so Monday's work is one client implementation, not a rewrite.
- **Adjudication accuracy.** A model judging claims can miss or over-flag. Mitigation: keep the deterministic checks (exit codes, file existence) as hard evidence and use the model only where rules cannot reach.
- **Scope creep.** Ten days with a day job. Mitigation: MVP locked to one demo scenario and one benchmark; everything else is stretch.

## Timeline

- **Oct 26:** Kickoff. Wire the Meta Model API client. Smoke test live models.
- **Oct 27 to 29:** Claim extraction and adjudication working end to end on recorded runs.
- **Oct 30 to Nov 1:** Live verification, demo scenario hardened. MVP freeze Nov 1.
- **Nov 2 to 3:** Benchmark re-run on Meta models. Demo video recorded.
- **Nov 4:** Submission package complete by 6 PM ET. Deadline is 9 PM ET.
