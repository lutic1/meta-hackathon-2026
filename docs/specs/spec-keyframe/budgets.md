# Budgets: calls, latency, spend, memory

Companion to `SPEC.md`. Prices and limits were checked Oct 20 on the primary pages; cost arithmetic is marked [ASSUMPTION].

## Calls and latency per build (one room, 6 to 10 photos, Tier 1)

| Call | Count | Reasoning effort | Budget | Note |
|---|---|---|---|---|
| Spark vision (Architect) | 1 | low | 15 s | All photos in one request |
| SAM 3.1 segment | 1 per listed object, at most 12 | n/a | 10 s total | In parallel |
| Riddler | 1 | medium | 45 s | Past 45 s: retry at low, or split into graph then rungs |
| Dry run | 1 | low | 30 s | Never sees solutions |
| Scene build, hotspots | 0 | n/a | 10 s | Mask decode (`meta-sam-parser`) runs in the backend |
| Total | 3 Spark plus up to 12 SAM | | 110 s | Target 120 s or less, T0 Upload click to T1 first hotspot responding |

A regeneration repeats Riddler and dry run, about 75 s; the cap is 2, about 260 s in total, which serves CAP-2 integrity, not the video. A capture-proof take is kept only under 200 s (at most one visible retry). If the Oct 27 to 28 measurements miss 120 s, the target becomes measured p50 plus 25%.

Per session (15 to 25 minutes): Trickster at most 6 Spark calls; Guide phrasing on Ollama costs nothing; voice, if it ships, under $0.01.

## Prices and rate limits (checked Oct 20)

| Service | Price | Rate limit |
|---|---|---|
| `muse-spark-1.3`, standard tier | $1.25 per million input, $4.25 per million output (reasoning billed as output), $0.15 per million cached | 3,000 RPM, 4,000,000 TPM per team |
| `sam-3.1` | $2.50 per 1,000 images | 3,000 RPM |
| `muse-image-1.0` | $0.01 per image | 150 RPM |
| `muse-voice-transcribe-1.0` | $0.18 per audio hour | not budgeted |
| fal `fal-ai/sam-3/3d-objects` | $0.02 per call (from fal's developer guide) | none stated |
| Modal CPU | $0.047 per core-hour, $0.008 per GiB-hour; the Starter plan includes $30 per month of compute | none stated |

Contributor-tier Spark ($0.10 and $0.20 per million, 150 RPM) is never used: Meta may train on the data and the rooms are the builder's home.

## Cost [ASSUMPTION, arithmetic from the prices above]

- Clean build about $0.10 (vision $0.025, SAM $0.03, Riddler $0.022, dry run $0.024); $0.15 with one regeneration; under $0.25 with two.
- A full session about $0.21 (about 100k input and 20k output Spark tokens).
- Four portraits plus up to 12 clue cards: $0.16 once.
- Daily ceilings: Oct 26 $3, Oct 27 $5, Oct 28 $10, Oct 29 $10, Oct 30 $0, Oct 31 $5, Nov 1 $8, Nov 2 $10, Nov 3 $18, Nov 4 $10; total $79. Expected spend under them about $35.

## Spend rules

- `SPEND_CAP_USD` is a per-call refusal. The provider prices each call from returned usage and adds it to a counter persisted on disk (local) or the Volume (hosted); a call that would pass the cap is refused and surfaced. The pre-call estimate is the last observed cost of the same call kind or, before any observation, a seed per kind: vision $0.03, SAM $0.0025, Riddler $0.03, dry run $0.03, Trickster $0.01, image $0.01. The counter is corrected from returned usage after each call.
- Cap $80 through Wed Nov 4; from Thu Nov 5 the counter resets and the cap is $25 for judging and finals, which run pay-as-you-go with a card on file (the $150 credit states no issue date or expiry).
- Wed Oct 21 to Sun Oct 25: up to about $5 cash on the Meta API for verifications and spikes, outside the ceilings and any credit.
- fal: about $1 cash (5 test objects before Oct 26, then at most 20 GLBs plus retries in Tier 2); ceiling $6.
- Modal: a warm CPU container Thu Nov 5 to Mon Nov 9 (about 1 core plus 2 GiB for 120 hours) is about $8 at list price, inside the Starter plan's free $30; partner credits are not counted.
- Agent dev loops run against the mock provider with `CACHE=on`, so iteration never draws on the cap.

## Memory on the 16 GB M1

| Process | Development | Demo recording |
|---|---|---|
| macOS and WindowServer | 3.0 GB | 3.0 GB |
| IDE and extensions | 2.5 GB | 0 (closed) |
| Chrome game tab (Tier 3 splats add 0.5 to 1 GB) | 2.0 GB | 2.5 GB |
| Vite dev server and Node | 0.6 GB | 0.6 GB |
| Python backend (FastAPI, Pillow, mask decode) | 0.5 GB | 0.5 GB |
| Ollama, Llama 3.2 3B Q4_K_M, 4k context | 3.0 GB | 3.0 GB |
| whisper.cpp base (not planned) | 0.7 GB | 0 |
| Screen recorder (QuickTime about 0.3 GB, OBS about 1 GB) | 0 | 1.0 GB |
| Slack, Discord, other tabs | 1.5 GB | 0 |
| Total | about 13.8 GB (swap likely) | about 10.6 GB |

Llama 3.2 3B Instruct Q4_K_M is a 2.02 GB file, about 3 GB resident. Llama 3.1 8B Q4_K_M (4.92 GB, about 6 GB resident) is for quality comparisons only with the IDE closed; it pushes development near 17 GB and makes a recording stutter. Speed [ASSUMPTION, extrapolated from a measured 14.15 tok/s for a 7B Q4_0 on an M1 8-core GPU]: 25 to 35 tok/s decode for 3B, 10 to 13 for 8B; a 40-token hint at 25 tok/s is 1.6 s of decode. The Ollama benchmark before Oct 26 measures prefill and decode on a 400-token prompt. Muse Glimmer's smallest official quant needs about 19 GiB resident and does not fit.
