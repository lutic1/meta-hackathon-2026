# Monday, Oct 26: plug-in checklist

Goal: go from mock to live Meta models in under an hour, then spend
the hackathon on the project instead of the plumbing.

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
