# Monday, Oct 26: plug-in checklist

Goal: go from mock to live Meta models in under an hour, then spend
the hackathon on the project instead of the plumbing.

## 0. Before Monday (do this week, verified Oct 20)

The Meta Model API is already public (paid since July 9, 2026), so
Monday does not have to be your first touch of it. Do this now:

- [ ] Create a Meta Model API account at dev.meta.ai, configure
      billing, and generate an API key. New accounts start with $20
      in free credits.
- [ ] Copy the key into `.env` as `META_MODEL_API_KEY` and wire
      `src/providers/meta_api.py` against `muse-spark-1.3` this week.
      Prove the whole path against the mock-free API now; Monday's
      hackathon grant then only has to unlock the newest models
      (SAM 3.1, Muse Image), not your plumbing.
- [ ] Use the standard `muse-spark-1.3` tier, NOT
      `muse-spark-1.3-contributor`. The contributor tier is far
      cheaper (~$0.10/$0.20 per 1M tokens vs $1.25/$4.25) because Meta
      may use the data to improve its products. Your room photos go
      in, so pay the standard tier.
- [ ] Know the two SAM models by their real jobs:
      SAM 3.1 (via API) does segmentation and tracking only, text
      prompt ("sofa") to bounding boxes and masks, up to 16 objects
      per frame, 15,000 input frames max on video. It does NOT do 3D.
      SAM 3D Objects (open weights) is the actual 3D reconstruction
      model: single 2D image to 3D object, shape, texture, and
      spatial layout, built for object and scene reconstruction in
      everyday environments. That is the Architect's engine.
- [ ] SAM 3D Objects is NOT on the hackathon's API list (the page
      names the Muse Spark series, Muse Image, and SAM 3.1 via the
      API), so plan a GPU deployment for it: the open weights from
      Hugging Face, served via Modal or Baseten. The partner credits
      exist for exactly this (Modal $100, Baseten $100).
- [ ] Test SAM 3D Objects on a real room photo this week if you have
      any GPU path. The result decides the Day 7 go/no-go call on
      full 3D. Do not let Nov 2 be the first time you see whether a
      phone photo becomes a usable room mesh.
- [ ] Read your approval email (Cerebral Valley Events, Oct 20,
      5:43 AM EDT). That is where the Discord invite and the
      hackathon-specific credit claim path live. Join Discord now;
      workshops run Oct 27 to Nov 4 and office hours live there.

## 1. Get access (kickoff, 1:00 PM ET)

- [ ] Watch the kickoff livestream, note the API docs URL and anything
      about rate limits or model ids that differs from the placeholders
      in `src/providers/meta_api.py`.
- [ ] Accept the official rules (published at kickoff).
- [ ] Copy your Meta Model API key into `.env` as `META_MODEL_API_KEY`.
- [ ] Join the event Discord. Office hours and announcements live there.
- [ ] Claim partner credits if you will use open weights:
      Baseten $100, Modal $100, Fireworks $25.

## 2. Wire the Meta provider (the only code change)

In `src/providers/meta_api.py`, from the official docs:

- [ ] Confirm the base URL (set `META_MODEL_API_BASE_URL` if non-default).
- [ ] Confirm the auth header format in `_post()`.
- [ ] Fill in `chat()`: real endpoint path, request payload, and the
      response fields that map to `ChatResponse`.
- [ ] Fill in `generate_image()`: real endpoint path (Muse Image) and
      the response mapping to `ImageResponse`.
- [ ] Set the real default model ids (`CHAT_MODEL` / `IMAGE_MODEL` in
      `.env`, or the placeholders in the provider).

## 3. Smoke test before building anything else

```bash
MODEL_PROVIDER=meta .venv/bin/python main.py chat "Say hello in one sentence"
MODEL_PROVIDER=meta .venv/bin/python main.py image "a red convertible on a coastal road"
```

- [ ] Both commands return real model output.
- [ ] Update the two stub tests in `tests/test_providers.py`
      (`test_meta_provider_is_a_stub_until_oct_26`) to assert live
      behavior instead, or delete them now that the stub is wired.
- [ ] Run the full suite: `.venv/bin/python -m pytest`.

## 4. Then build

- [ ] Lock scope: working MVP by Nov 1.
- [ ] Nov 3 and 4 reserved for demo and submission polish.
- [ ] Submissions due Nov 4, 9:00 PM ET. Do not leave the upload to
      the last hour.
