# Player profile v1 and adaptive thresholds

Companion to `SPEC.md` (CAP-4, CAP-5, CAP-6, CAP-8, CAP-13).

## Stored per room

Timings; per puzzle {`lock_type`, `attempts`, `wrong_attempts`, `rungs_used`, `time_to_first_hint`, `solved`}; Trickster edits seen and accepted; the raw event log (clicks, wrong codes, idle seconds, hint requests).

## Derived block

Recomputed after each room: `time_to_first_hint` (median seconds), `mean_rung_per_lock_type` (0 to 3), `persistence` (-1 to 1: positive when the player keeps trying past the nudge threshold, negative when they ask early), `sessions`. The derived block is all the Guide model and the room-2 greeting may see; raw events and room contents never leave the selection code.

## Thresholds, applied in code

- Nudge threshold = 90 s × (1 + 0.5 × persistence), so 45 to 135 s, then clamped to 60 to 180 s. A new profile has persistence 0, threshold 90 s.
- A nudge also fires on 3 wrong attempts at one lock, whichever comes first.
- Direction and near-answer follow at least 90 s apart, each needing a further stall or 3 further wrong attempts. The 90 s spacing is fixed; only the nudge threshold scales.
- Rung selection is code over the event log; the Guide model only phrases the selected rung (about 40 tokens from a prompt under 400 tokens with a fixed prefix). Under cut 3 the rung text is shown verbatim and the privacy line still holds.

## Trickster bounds

At most one change per 3-minute window, only between puzzles, from the fixed menu (`decoy`, `merge`, `loosen`, `shortcut` in `schema-v1.md`) and a game-state summary (open locks, time, rungs used), never the profile. At most 6 Spark calls per session. Every proposal is re-validated with the eight validator rules; a failing proposal is shown as the rejected card and the room is unchanged.

## Demo timescale

`DEMO_TIMESCALE=n` divides the nudge threshold, the rung spacing, and the Trickster window by n; it never changes the capture timer. At 6x the three rungs take 30 s when the nudge fires on 3 wrong codes, 45 s on idle alone; the video uses wrong codes.

## Profiles

`PROFILE=dev|playtest|demo` selects the IndexedDB database name (a JSON file under cut 2). The video and the playtest use fresh profiles. Room 1 is played for real on `PROFILE=demo` on Mon Nov 2 so room 2's greeting has a true record to cite. The greeting is phrased from the derived block only and names no object and no solution.
