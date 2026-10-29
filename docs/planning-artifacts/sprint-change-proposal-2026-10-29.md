# Correct-course record: accepted departures, 29 Oct 2026

- Date: Thu 29 Oct 2026
- Prepared by: Luis Ticas
- Base: `1e8578a` (origin/master and origin/keyframe/bmad-brief, "Fix: play never blanks: idempotent completion, storage fallbacks, profile file opt-in, the Build screen at 1024"). Entries were first checked at `1eb9f51`, `18ec75a` or `42d3253`. The commits after `42d3253` are `d4e1a1c` and `f330810` (lane I1) and `1e8578a` (lane B4b), all in section 5. They touch `src/domain/session.py`, files under `web/src`, EXPERIENCE.md, DESIGN.md and tests, and no schema, port, route or workflow file. Every test node this record cites was re-run at `1e8578a`, offline, on the mock provider, and passes.
- Deployed: the hosted URL https://luis-ticas1--keyframe-web.modal.run serves `c9d0d61` (deploy run 6, GitHub run 40802005305). It is 19 commits behind the base.
- Answers: the owner's numbered decision record of Oct 28 and the owner's decisions of Oct 29 on the fix lanes (D, F, P, T, B, S, I). It is the "one correct-course record" that decision 33 asks for the post-freeze schema shapes, that decision 34 asks for the port signatures, and that decision 41 asks for the copied messages. Decision 47 asks for three enumerations, each stated once with verification links: the final accepted schema (item 33), the actual CI triggers (item 15) and the narrow import exceptions (item 35). `src/domain/schema.py` says later schema changes go through correct-course; before this record, no such file existed under `docs/`.
- Rule: this record reconciles documentation with what shipped. It never turns an unrun gate into a pass. A gate listed as unrun stays unrun until its owner records a result in the sprint status, the SIT checklist or the UAT sign-off.
- Planning docs are not edited here. Section 6 lists every lagging doc section so a later edit can fix it.

## Summary

Status values:
- implemented: the code does what the decision or lane asks, and its offline tests pass. It claims no live gate. Live gates (the M1 browser pass, a redeploy, a hosted run) are listed in each entry and in section 7, and none of them has passed.
- partial: part of what the decision asks is not done, in code or in docs, or a verification the decision itself names has not been done (item 46: "verify no cache write occurs"; item 1 in B1: "Change / verify").
- open: not done.
- record-only: nothing to change, recorded for reference.

For a lane, the status covers the code and the UX contract docs the lane edited (EXPERIENCE.md, DESIGN.md). Where epics.md lags a lane, the lag is a section 6 row with its own status. The exception is P4: its decision changes FR-15 and FR-16, so the unedited epics and spine text makes P4 partial.

| Item | Title | Decision | Status | Verification |
|---|---|---|---|---|
| 32 | Order `sequence_length` in the public play projection | Keep / record | implemented | 54efe36; 5 tests pass |
| 33 | Post-freeze schema additions | Approve with contract review | partial | 7 commits; schema, profile, edits tests pass; planning docs unedited |
| 36 | Replay references, t_ms ordering, rung evaluation | Keep / specify | partial | rungs and trigger-event tests pass; spine AD-4 contradicts code |
| 44 | DryRunResult location and strict rule 5 | Keep both | implemented | 8baf54e; validator tests; hosted job job_01M61TZ74F6F3AVVEMPRAS4V1G (deploy run 4) |
| 34 | Model and phraser ports | Keep useful changes / reconcile | partial | port and cache tests pass; spine AD-5 and AR-8 stale |
| 35 | Boundary allowances, clocked ids, domain purity | Accept narrow imports / fix purity | partial | 35 boundary tests pass; pipeline still mints ids |
| 38 | New ports and storage layouts | Keep / record | partial | quota live (run 40821411610); purge offline only |
| 42 | `phraser_fallback` as structured logging | Keep structured logs | partial | fallback tests pass; AD-5 not amended |
| 46 | Hosted Trickster cache off | Keep / record | partial | 80e7740; offline test; deployed in c9d0d61; live no-cache-write check unrun |
| 37 | Expanded HTTP surface | Document / correct wrong status | partial | 409/410/404 tests pass; dict-key echo found |
| 40 | Bounded in-request ingest | Accept bounded ingest | partial | ingest tests pass; no byte cap |
| 41 | Copied validator messages with a drift check | Accept pinned copy | implemented | drift test passes |
| 45 | Compile-time cut 0 and the direct Build-view route | Keep / close direct route | partial | link guards tested; direct route unguarded |
| 15 | CI trigger documentation | Keep behavior / reconcile | partial | CI runs green; AR-24 stale |
| 47 | Repeated schema, CI and import changes | One record | partial | enumerated in 33, 15, 35; AD-1, AR-24 unedited |
| 43 | Ledger export cap configuration | Fix hidden assumption / record shape | open | defaults tested; hosted 20 hard-coded |
| deploy-push-trigger | deploy.yml dispatch plus guarded push | Record (Oct 29, F29) | implemented | GitHub run 40802005305 |
| ops-push-trigger | ops.yml dispatch plus guarded push | Record (Oct 29, F26, F27, F29) | implemented | GitHub run 40821411610 |
| ops-actions | Every ops action as shipped | Record | implemented | 2 of 8 actions run live |
| settings-unnamed-keys | Settings keys the spec and spine do not name | Record | record-only | config tests pass |
| build-quota-probe | Hosted build quota and its live probe | Record (decisions 18, 23; B5) | implemented | GitHub run 40821411610 passed |
| modal-objects | Modal Dicts, Volume layout, Secret keys | Record | implemented | modal_app tests; deploy run 6 |
| D1 | Hosted landing is a title screen | lane fix | implemented | 68b5842; deployed |
| D2 | Trickster in local demo play; fail fast on missing proposals | lane fix | implemented | 9463aeb |
| D3 | Hotspot hover, glow, dwell and pending chips | lane fix | implemented | 795c324; deployed |
| D4 | The unlock moment | lane fix | implemented | 77f4f2a, 7dabbd0 |
| D5 | Sample room from every dead end | lane fix | implemented | 6cca9c2 |
| D6 | Disclosure footer, Triggers collapsed, role line by mode | lane fix | implemented | 2f0d050 |
| D7 | Architect reads visible attributes | lane fix | implemented | c78eb85, bff6cee; live Build passed 8 rules |
| D8 | Build view names where the Validator ran | lane fix | implemented | 2b6f067, 3a0dd65 |
| D9 | Attract frame on the Hosted landing | lane fix | implemented | cd15a3e |
| D10 | Attract frame never lights a lock's object | lane fix | implemented | c9d0d61; checked live |
| F21 | SIT transport honours HTTPS_PROXY and NO_PROXY | lane fix | implemented | 53a4efd |
| F22 | Replay tests hold under any valid SIT recording | lane fix | implemented | bbd5efd, 50b5bf1, 2a4dfce, 6bfd79b |
| F23 | Fixture scenes draw the code-puzzle evidence | lane fix | implemented | d5ad217 |
| F29 | Deploy and ops on push to dedicated branches | lane fix | implemented | 5c1f56b; runs 40802005305, 40821411610 |
| P1 | Three-step how-to-play, copy about the player | lane fix | implemented | e2a7fc1, 055bf88; not deployed |
| P2 | Every click answers in one feedback line | lane fix | implemented | ad598f0; not deployed |
| P3 | Evidence cards stop handing over the answer | lane fix | implemented | 4d05acb; not deployed |
| P4 | Asking the Guide opens a hint | lane fix (Oct 29) | partial | 65c8bac, 4ae3dca; code done; AD-4, epics unedited; not deployed |
| P5 | Thumbnail object counts, notes follow the puzzle | lane fix | implemented | 1eb9f51; not deployed |
| P6 | Landing fills the fold with the game | lane fix | implemented | e4fe83b; not deployed |
| T7 | Completion screen | lane fix | implemented | 9801e6a; not deployed |
| B4a | Player wording (items 62, 66, 70, 71, 72) | see entry | implemented | 18ec75a; not deployed |
| B4b | Play never blanks (items 27, 48, 54, 64, 67) | see entry | implemented | 1e8578a; not deployed |
| B1 | Retention summary states verified facts (items 1, 31) | Change / verify; Reconcile | partial | 85a4afa; provider facts unverified; not deployed |
| B2 | Game rules (items 22, 28, 29, 30, 68) | see entry | implemented | 5863a59; not deployed |
| B3 | API correctness (items 24, 35, 37, 56, 58, 61, 63) | see entry | partial | b161d99, 72d6bfb; 35 and 37 partial; not deployed |
| B5 | Hosted reliability (items 9, 18, 23, 57) | see entry | partial | 69c269a; run 40821411610 |
| S1 | Small objects keep their SAM outline | lane fix | implemented | 42d3253 (on master); not deployed |
| I1 | Only objects a later puzzle uses go into the Inventory | lane fix | implemented | d4e1a1c, f330810; not deployed |
| 39 | SVG hotspots, Tier 1 kept | Keep Tier 1 SVG (amend spine) | partial | scene tests pass; AD-11 not amended |
| epics-1.14 | Story 1.14 lags status, retention, listing | Record | open | meta tests pass |
| epics-7.16 | Story 7.16 describes the old card grid | Record | open | landing tests pass |
| epics-UX-DR23-24 | Hotspot and label chip rows predate D3, D4, P2 | Record | open | scene tests pass |
| epics-live-region-1480 | "Puzzle {n}: open." replaced by the feedback line | Record | open | feedback-line tests pass |
| epics-oct29-rows | Other epics rows the Oct 29 fixes changed | Record | open | play and completion tests pass |
| EXPERIENCE-rows | Four EXPERIENCE.md rows lag | Record | open | test_strings.py passes |
| hosted-redeploy | Hosted URL serves c9d0d61 | Verify | open | CI green on 1e8578a; no deploy since run 6 |
| 13 | Doctor run on the M1 | Record actual choice | open | none |
| 16 | M1 browser verification | Verify remaining paths | open | none |
| 17 | Live SAM wire format | Verify | partial | 558da8a recordings |
| 18 | Quota atomicity | Verify before uploads | partial | GitHub run 40821411610; not recorded |
| 19 | Hosted stores, Crons, proxy, purge | Verify before uploads | partial | run 40795627220; Cron and purge unrun |
| 20 | Real CI | Verify / defer optimization | partial | CI runs 40828349988, 40828171360 |
| 21 | Baseten fallback | Verify if shipped | open | none live |
| SIT-rows | SIT checklist unrun and failed rows | Verify | open | see section 7 |
| UAT-rows | UAT tests and sign-off | Verify | open | every row unrun |

Earlier F lanes that changed a contract, by the entry that holds the contract. Lanes F21, F22, F23 and F29 have their own entries.

| Lane | Commit | Contract changed | Entry |
|---|---|---|---|
| F1 | e638cd9 | SessionStore gains `put_header` and `read_header`; a restarted process reopens a session from the header and the log | 38 |
| F2 | f784ac7 | GET /api/sessions/{id}/room answers 410 room_deleted once the session's Judge room is deleted | 37 |
| F4 | 2091398 | `segment` takes `job_id` and `stage` and returns SegmentResponse (polygons, receipt); Architect and segment rows carry their receipts | 34 |
| F6 | 80e7740 | Hosted Trickster provider runs with the cache off | 46 |
| F7 | 16ebde4 | `TricksterCard.puzzle_id` on a merge names the waiting puzzle | 33 |
| F14 | a349def | GET /rooms skips and logs an unparseable job record instead of failing | epics-1.14 |
| F15 | 5c5625d | An Architect reply off the response shape ends the Build `failed` with provider_error, not validation_error | 37 |
| F16 | 2f7bb82 | Secret `keyframe` declares `required_keys` | modal-objects |
| F20 | c652116 | Judge-room deletion takes every Session whose stored header names the Room | 37, 38 |
| F26, F27 | 0e99b54, 4d3367a | ops.yml and the promote action | ops-push-trigger, ops-actions |

## 1 Schema and public projection

Freeze baseline: `2cb23e3` (Story 1.5, Mon 26 Oct 17:16 UTC), the first commit of `src/domain/schema.py`. Every post-freeze schema commit (3b6566d, ed8d0ab, 988c10a, 54efe36, bf98411, 16ebde4, 5863a59, 65c8bac) is on the base.

### 32 Order `sequence_length` in the public play projection
Decision: Keep / record. Status: implemented.

- Contract: schema-v1.md (last edited 22 Oct, b4a21a7) names PlayView only by reference to spine AD-3 and lists no `sequence_length`. The freeze PlayPuzzle is {id, lock_type, requires, is_exit, clue, lore, evidence_cards}. Shipped (54efe36, 27 Oct): `PlayPuzzle.sequence_length: int >= 1 | null`, a required key, the length of an order solution and null for code, use_on and find. Public through PlayView (GET /rooms/<id>, GET /sessions/<id>/room) and in `web/types/index.ts` as `sequence_length: number | null;`. Solution members and order stay server-only.
- Affected: Stories 1.26, 1.5, 1.15; PlayPuzzle, PlayView; `src/domain/schema.py`, `src/domain/redact.py` (`_sequence_length`, `to_play_view`), `web/types/schema.json`, `web/types/index.ts`, `web/src/components/order-progress.ts`.
- Behavior: `redact._sequence_length` returns `len(puzzle.solution.interactables)` for an OrderSolution only, else None. `to_play_view` narrows every other Puzzle field to PlayPuzzle's declared fields, so no solution, interactable ids or order reach the client. `order-progress.ts` draws `puzzle.sequence_length ?? 0` pips and fills them from `state.order_buffer` only, never comparing clicks with anything.
- Verification: 54efe36. `tests/web/test_order_use_on.py::test_the_play_view_gives_an_order_puzzle_its_length_and_nothing_of_its_sequence`; `tests/domain/test_schema.py::test_room_view_and_play_view_declare_no_solution_or_profile_field`; `tests/web/test_types.py::test_web_types_match_what_get_schema_serves`, `::test_index_ts_was_generated_from_the_committed_schema_by_the_committed_script`, `::test_no_generated_type_declares_a_solution_field`. All pass.
- Remaining gates: the pips are checked by source-text tests only. The owner's M1 browser pass on a real order puzzle is unrun.

### 33 Post-freeze schema additions
Decision: Approve with contract review. Status: partial.

- Contract: every addition after `2cb23e3`, compared with `src/domain/schema.py` at `1eb9f51`:

| Shape | Public or internal | Commit | Notes |
|---|---|---|---|
| `Profile {results: dict[RoomId, RoomResult], derived: Derived}` | Public (web/types; cut 2 local GET and PUT /api/profile/<name>) | 3b6566d | Validator rejects a result keyed under another room_id; in API_MODELS |
| `HintReply {puzzle_id \| null, rung 0..3, text, next_hint_ms \| null}` | Public, as `SessionState.hint_reply` (default null, set only on the reply to a hint_request, never replayed) | ed8d0ab; `next_hint_ms` in 65c8bac | Not in API_MODELS; reaches GET /schema and web/types as a $def of SessionState |
| `TriggerEvent {type: one of the 7 event types, t_ms}` | Public, as `SessionState.trigger_events: dict[int, TriggerEvent]` keyed by log position | bf98411 | Served on top of replay, never written by apply; not in API_MODELS |
| `EditBounds = Literal['edit_bounds']` in `ValidatorReason.rule` | Internal (ValidatorReason sits only under server-only TricksterEdit) | 5863a59 | Filtered out of web types |
| `EditBounds` in `CardReason` | Public through `TricksterCard.reason`: `number \| "edit_bounds" \| "provider_unavailable" \| null` | 5863a59 | |
| `PlayPuzzle.sequence_length` | Public | 54efe36 | See item 32 |
| `ErrorDetail.status: JobStatus \| null` | Public | 988c10a | Moved from `ErrorEnvelope.status` into `error`; dropped from the dump when null; allowed only on build_not_ready |
| `TricksterCard.puzzle_id` meaning | Public, shape unchanged | 16ebde4 (lane F7) | On a merge it names the waiting puzzle (puzzle_b); docstring only |

  Unchanged since the freeze: `PostedEvent` (ClickBody | LockInputBody | HintRequestBody). `ShortcutPayload` is {type, puzzle, requires} in the freeze code already; schema-v1.md still says `shortcut: {puzzle}`.
- Affected: Stories 1.5, 1.15, 3.3, 3.5, 5.3, 2.28, 4.1; the shapes above; `src/domain/schema.py`, `src/api/app.py` (trigger_events, hint_reply, profile_routes), `src/domain/edits.py`, `web/scripts/types.mjs`, `web/types/index.ts`, `web/types/schema.json`.
- Behavior: GET and PUT /api/profile/<name> parse with `Profile.model_validate_json`. A result keyed by another room, a key that is not a room id, or out-of-bounds Derived fields answer 422 invalid_profile and leave the file byte for byte unchanged. The browser re-keys stored results by `result.room_id` (`web/src/profile/file.ts`). The `trigger_events` helper serves {log position: (type, t_ms)} for every index a rung_change names, with no payload. `hint_reply` is attached only to the POST response for a hint_request. `types.mjs` drops server-only types and their union members, so the web Event union has no TricksterCardEvent and no ValidatorReason, TricksterEdit or `*Payload` type is generated. Shortcut stays bounded: `_payload_bounds` refuses with edit_bounds unless `payload.puzzle == edit.puzzle` and `requires` is an existing edge of that puzzle; `apply_edit` removes exactly that edge; the result goes through rules 1 to 9, and a shortcut that strands a use_on item fails rule 8. No path replaces the graph.
- Verification: 3b6566d, ed8d0ab, bf98411, 988c10a, 16ebde4, 5863a59, 65c8bac. `tests/domain/test_schema.py::test_profile_keys_each_room_result_by_its_room_id`, `::test_session_state_fields`, `::test_posted_bodies_forbid_t_ms_and_extra_fields`, `::test_room_summary_access_check_session_start_and_error_envelope`; `tests/api/test_profile.py::test_an_out_of_bounds_or_unparseable_body_answers_422_and_leaves_the_file_unchanged`; `tests/api/test_trigger_events.py::test_a_state_with_no_rung_change_names_nothing_and_replay_never_writes_the_field`; `tests/web/test_types.py::test_unions_are_discriminated_on_their_literal_type`, `::test_play_view_is_generated_and_server_only_types_are_not`; `tests/domain/test_edits.py::test_bounds_refusals_carry_the_named_edit_bounds_category_and_never_a_rule_number`, `::test_payload_bounds_refuse_with_structured_reasons_and_the_fixed_message`, `::test_a_shortcut_removing_the_find_an_item_depends_on_is_rejected_on_rule_8`, `::test_apply_edit_returns_a_new_room_per_type_and_leaves_the_input_untouched`; `tests/domain/test_redact.py::test_a_merge_card_names_the_waiting_puzzle_first_whichever_the_proposal_named`; `tests/api/test_hints.py`, whole file (28 collected). All pass.
- Remaining gates: code meets every behavioral condition. This record supplies the shape list; schema-v1.md, spine AD-4 and AD-13 and epics Stories 3.3 and 3.5 still need the edit (section 6). The hint and Triggers UI wait on the owner's M1 browser pass.

### 36 Replay references (`triggered_by`), t_ms ordering and rung evaluation
Decision: Keep / specify. Status: partial.

- Contract: `RungChangeEvent.triggered_by: list[int >= 0]` means positions in the session log, as in the freeze code. Spine AD-4 still says `triggered_by: [event ids]` and `select_rung(events, derived, thresholds)`. Shipped signature: `select_rung(events, thresholds, *, loosen, asked)`, with no `derived` since 943f912. Hint rule changed by owner decision on Oct 29 (65c8bac, lane P4): a hint_request runs `select_rung` with `asked=True`. With no rung showing it opens the next rung at once; past the rung spacing since that puzzle's last rung_change it opens the next; otherwise it repeats the current rung. Spine AD-4 and epics Story 3.3 still state the old rule. The 65c8bac message says it changes FR-15/16 as written in the PRD, epics and spine AD-4, but it edited only EXPERIENCE.md and DESIGN.md.
- Affected: Stories 3.1, 3.3, 3.5, 1.5; RungChangeEvent, HintReply, Judged, RungStep; `src/domain/rungs.py` (`select_rung`), `src/domain/session.py` (`_judge`, `_record_rung`, `next_hint_ms`), `src/api/app.py` (stamp, append, hint_reply).
- Behavior: `SessionStateMachine._judge` calls `select_rung` after every event except a rung_change, and evaluates nothing again after one, so there is no recursion. That covers click, lock_input, hint_request (asked), idle_tick, opening_line and trickster_card (the loosen hook). At most one rung opens, on the active puzzle. API `append()` stamps `t_ms = max(elapsed, last.t_ms + 1)`, strictly increasing for posted and server events. The selected rung_change is appended right after its trigger and shares its t_ms, so log t_ms is nondecreasing. Replay replaces rather than repeats a stored selection (`_record_rung`). The domain does not reject a log with decreasing t_ms; ordering rests on the API stamp and append order. The nudge threshold formula lives only in `rungs.nudge_threshold_ms`. The persistence score is computed only in `web/src/profile/derive.ts`; only rungs and the phrasers read `.persistence`.
- Verification: 2cb23e3, 943f912, bf98411, 65c8bac. `tests/api/test_sessions.py::test_twenty_concurrent_events_all_land_in_append_order_with_strictly_increasing_t_ms`; `tests/domain/test_rungs.py::test_replay_reaches_exactly_the_rungs_appended_live_and_appends_none`, `::test_asks_replay_to_exactly_the_rungs_appended_live`, `::test_an_ask_with_no_rung_showing_opens_the_nudge_on_the_active_puzzle_at_once`, `::test_an_ask_inside_the_spacing_repeats_the_rung_and_reports_the_wait_and_past_it_opens_the_next`, `::test_idle_counts_from_the_last_hint_request_too`, `::test_an_idle_tick_never_resets_idle`, `::test_no_other_module_under_src_computes_the_nudge_threshold`; `tests/api/test_trigger_events.py::test_a_rung_an_ask_opened_names_the_hint_request_alone`, `::test_a_loosen_card_names_the_trickster_card_it_was_triggered_by`; `tests/test_boundaries.py::test_only_rungs_and_the_phrasers_read_derived_persistence`; `tests/web/test_player_profile.py::test_the_fixture_profile_derives_persistence_0_25_a_60_s_median_and_2_rungs_on_code`; `tests/api/test_hints.py::test_at_rung_0_an_ask_opens_the_nudge_at_once_worded_once_and_logged_as_an_early_ask`. All pass.
- Remaining gates: no test targets "a rung_change never itself evaluates escalation"; it is covered only indirectly. Nondecreasing t_ms is enforced only at the API stamp; replay does not validate it. `tests/domain/test_session.py::test_a_hint_request_never_opens_a_lock_counts_a_wrong_attempt_or_changes_a_rung` still passes only because its hint (t_ms 0) lands inside the spacing after a rung at 500 ms; its name states the pre-Oct 29 rule. The live hint behavior is part of the owner's M1 browser pass.

### 44 DryRunResult location and the strict clue rule (rule 5)
Decision: Keep both. Status: implemented.

- Contract: spine AD-12 places `check_dry_run(room, answers) -> DryRunResult` in `domain/validator.py`; the code matches. `DryRunResult {ok, verdicts: list[DryRunVerdict]}` is validator-local since Story 1.6 (8baf54e), not in `schema.py` or API_MODELS, absent from web types. Internal. Rule 5 follows schema-v1.md: nudge, direction, clue and `evidence.visible_attribute` get no solution token; only near_answer gets an allowance (one label for order and use_on, zero for code and find), and near_answer is also checked together with the clue.
- Affected: Stories 1.6, 2.23; DryRunResult, DryRunVerdict; `src/domain/validator.py` (`_rule_5`, `_leaks`, `check_dry_run`), `src/council/riddler.py`.
- Behavior: `_rule_5` checks {nudge, direction, clue, visible_attribute} strictly and near_answer against `allowance = 1 if lock_type in (order, use_on) else 0`, alone and concatenated with the clue. `_rule_5` and `_leaks` are byte-identical to 8baf54e. Matching: code strings and digits as whole tokens, label words longer than 3 characters as whole words, case-folded. `check_dry_run` is called only by the pipeline dryrun stage.
- Verification: 8baf54e. `tests/domain/test_validator.py::test_near_answer_may_name_one_label_of_an_order_sequence_but_not_two`, `::test_near_answer_may_name_one_label_of_a_use_on_pair_but_not_both`, `::test_the_near_answer_allowance_is_also_checked_against_the_clue`, `::test_the_code_string_as_a_whole_token_fails_in_every_checked_field`, `::test_evidence_naming_a_find_target_fails_on_visible_attribute`, `::test_a_mismatched_answer_fails_its_puzzle_only`; `tests/test_boundaries.py::test_the_dryrun_stage_is_the_only_caller_of_check_dry_run_so_the_only_place_answers_meet_solutions`. Live: hosted job job_01M61TZ74F6F3AVVEMPRAS4V1G on the judge URL (deploy run 4, GitHub run 40741283292, bff6cee; SIT-03 and SIT-08 cells, c032b61) built room_01M61TZ74F0FP3X9HHTMXGTPB9, done after 182 s with one Regeneration, 8 rules passed unweakened, Dry run reached all 4 locks blind; ops run 1 (GitHub run 40795627220) later promoted it.
- Remaining gates: none.

## 2 Ports, purity and storage

### 34 Model and phraser ports
Decision: Keep useful changes / reconcile. Status: partial.

- Contract: spine AD-5 Rule (line 71) and epics AR-8 (line 96) state `chat(messages, *, images=[], response_schema=None, reasoning_effort='low', model=None)`, `segment(label, image) -> list[Polygon] | None`, `phrase(rung_text, derived) -> str`, `greet(derived) -> str`. Shipped signatures (`src/providers/base.py` at `1eb9f51`), recorded once here:
  - `ModelProvider.chat(self, messages: list[ChatMessage], *, images: list[bytes] = [], response_schema: type[BaseModel] | None = None, reasoning_effort: ReasoningEffort = 'low', model: str | None = None, attempt: int = 0, job_id: JobId | None = None, stage: Stage | None = None, session_id: SessionId | None = None) -> ChatResponse`
  - `ModelProvider.segment(self, label: str, image: bytes, *, job_id: JobId | None = None, stage: Stage | None = None) -> SegmentResponse` (polygons: `list[Polygon] | None`, receipt: `CallReceipt | None`). Lane F4 (2091398) made this change, from `segment(label, image) -> list[Polygon] | None`, so the Architect and segment call rows carry their real receipts and their ledger entries name job and stage.
  - `ModelProvider.generate_image(self, prompt: str) -> ImageResponse`
  - `ChatResponse(text, model, usage, raw, receipt: CallReceipt | None)`; `CallReceipt(call_id, model, host, cached, spend_usd)`
  - `HintPhraser.phrase(self, rung_text: str, derived: Derived) -> PhraserResponse`; `HintPhraser.greet(self, derived: Derived) -> PhraserResponse`; `PhraserResponse(text: str, phrased: bool, latency_ms: int)`; `HintPhraser.guide_model: GuideModel | None`
  - `cache_key(model, *, messages, response_schema=None, reasoning_effort=None, images=(), attempt=0)` in `src/providers/cache.py`, with `str(attempt)` last in the digest.
  The spine already says chat "also takes attempt, job_id, stage and session_id"; its segment and phrase/greet return types are the old ones.
- Affected: Stories 2.1, 2.4, 2.20, 2.21, 2.24, 3.2, 3.7, 4.8, 5.5; `src/providers/base.py`, `cache.py`, `meta_api.py`, `openai_compatible.py`, `mock.py`; `src/council/trickster.py` (`LiveSource.propose`); `src/pipeline/author.py`, `src/pipeline/dryrun.py`.
- Behavior: the chat port has no temperature or max_tokens. meta_api sends model, messages, reasoning_effort and an optional response_format. openai_compatible sends max_tokens from its own constructor argument (MAX_TOKENS by default), so the limit is adapter configuration. The Riddler call (`author.py:272`) and the Dry run call (`dryrun.py:64`) pass `attempt=state.regeneration_count`. `LiveSource.propose` passes `attempt=window` and session_id. Segment keys carry attempt 0; segment is never retried by regeneration. The verbatim and Ollama phrasers return `phrased` and `latency_ms`.
- Verification: 7125fbd, d7b576d, 43b35a1, 41e8f7d, 2091398, b161d99. `tests/providers/test_base.py::test_chat_signature`, `::test_chat_dropped_the_scaffold_arguments`, `::test_segment_signature`, `::test_phraser_response_carries_the_text_the_flag_and_the_latency`; `tests/providers/test_cache.py::test_the_key_is_sha256_over_model_schema_prompt_effort_image_hashes_and_attempt`, `::test_attempt_n_is_never_served_attempt_n_minus_one_answer`; `tests/providers/test_meta_api.py::test_attempt_joins_the_cache_key_so_a_regeneration_is_never_served_the_earlier_answer`; `tests/council/test_trickster_live.py::test_the_live_source_makes_exactly_one_chat_call_at_low_with_the_window_as_attempt`; `tests/pipeline/test_regenerate.py::test_each_riddler_call_and_each_dry_run_carries_attempt_n`, `::test_under_cache_on_attempt_n_is_never_served_the_cached_answer_of_attempt_n_minus_1`; `tests/pipeline/test_author_stage.py::test_the_call_carries_the_regeneration_count_as_attempt`; `tests/pipeline/test_dryrun_stage.py::test_run_dry_run_sends_the_attempt_and_the_stored_photo_bytes`; `tests/pipeline/test_stage_receipts.py::test_architect_and_segment_rows_carry_their_receipts_and_their_ledger_entries_name_job_and_stage` (F4). All pass.
- Remaining gates: spine AD-5 and epics AR-8 still need the edit. Nobody has inspected cache keys across Regenerations on the hosted Volume; job job_01M61TZ74F6F3AVVEMPRAS4V1G ran one Regeneration, but its keys were not checked.

### 35 Boundary allowances, clocked ids and domain purity
Decision: Accept narrow imports / fix purity. Status: partial.

- Contract: the decision allows same-package imports and the shared spend and cache guard imports, refuses a domain wall-clock exception, and wants time-based ids minted at the API or infra boundary. Spine AD-1 Rule was amended in b161d99: no module in `src/domain` reads the wall clock or mints an id; `tests/test_boundaries.py` walks every module's imports and every domain module's clock reads. AD-1 does not record the allowances the test enforces: same-package imports, pipeline importing council, adapters importing `GUARDS = {src.providers.spend, src.providers.cache}`.
- Affected: Stories 1.2, 1.11, 1.12, 2.4, 2.10; `tests/test_boundaries.py`; `src/domain/*` (10 modules); `src/providers/spend.py` (`new_ulid`, `new_call_id`); `src/api/app.py` (`new_session_id`); `src/pipeline/build.py` (`new_id`); `src/pipeline/author.py`.
- Behavior: domain purity holds and is enforced. No `src/domain` module imports time, secrets, random, uuid, zoneinfo or calendar, or calls now, utcnow, today, fromtimestamp, time, time_ns, monotonic or perf_counter. `clock_reads()` walks every `*.py` under `src/domain` and asserts at least 10 modules; `schema.py` imports datetime as a type only. Outside the domain, ids are not all minted at the boundary: `src/pipeline/build.py new_id()` reads `time.time_ns()` and secrets and mints room_, job_, ix_ (`segment.py:91`), pz_ (`author.py:183`) and fallback call_ ids; `src/pipeline/author.py:255` stamps `Room.created` with `datetime.now(UTC)`. Both bypass the Clock port (AD-10: "a Clock port supplies all time"). There are two ULID minters: `spend.new_ulid` calls itself "the one minter", and `build.new_id` is a second.
- Verification: b161d99, df666b2. `tests/test_boundaries.py::test_no_domain_module_reads_the_wall_clock_or_mints_an_id`, `::test_a_domain_clock_read_or_minter_is_named`, `::test_ratified_scaffold_has_no_violation`, `::test_adapters_may_import_the_guarded_call_path`, `::test_pipeline_may_import_its_own_modules`, `::test_pipeline_importing_the_guarded_call_path_is_named`; the whole file (35 collected) passes.
- Remaining gates: no live gate. Open in code: pipeline id minting and the `Room.created` clock read. Open in docs: AD-1 allowances, AD-10. b161d99 is not in the deployed `c9d0d61`; that has no effect on runtime purity.

### 38 New ports and storage layouts
Decision: Keep / record. Status: partial.

- Contract: shipped ports in `src/pipeline/ports.py`, recorded here:
  - ArtifactStore: `put(key: str, data: bytes) -> None`; `read(key: str) -> bytes`; `list_rooms() -> list[Room]`; `is_demo_room(room_id: str) -> bool`; `is_judge_room(room_id: str) -> bool`; `deleted_room(id_: str) -> RoomId | None`.
  - JobStore: `put(state: JobState) -> None`; `read(job_id: JobId) -> JobState`; `list_ids() -> list[JobId]`; `reserve_build(job_id: JobId) -> None` (raises `BuildQuotaExceeded(quota)`); `builds_left() -> int | None`.
  - AttemptStore: `read(key: str) -> list[int]`; `write(key: str, times: list[int]) -> None`.
  - JobRunner: `start(job_id: JobId) -> None`.
  - SessionStore: append, read_all, list_ids, delete, `put_header(session_id, header: SessionHeader)`, `read_header(session_id) -> SessionHeader`. Lane F1 (e638cd9) added the header pair: the header is stored once at session start, never listed, deleted with the log, and a restarted process reopens a session from header and log.
  - LedgerStore: append, entries. Cache: `get(key) -> dict | None`; `put(key, value: dict) -> None`.
  - Layouts: `<room_id>/room.json`, `<room_id>/photos/<i>.jpg`, `<room_id>/reasons.json`, `<room_id>/cache-keys.json`; hosted final job record `rooms/judge/<room_id>/job.json`; deletion records `rooms/deleted/<room_id>.json`; keyframe-jobs keys `<job_id>`, `call:<job_id>`, `build:1` to `build:20`, `attempts:<ip>`; session header key `<session_id>:header`; local `rooms/jobs/<job_id>.json` and `rooms/sessions/headers/`.
  Spine AD-9 lists SessionStore as (append, read_all, list_ids, delete) and documents list_rooms, builds_left, the skip_if_exists slot claim and the deletion record. Neither the spine nor epics.md names AttemptStore, reserve_build, is_demo_room, is_judge_room, deleted_room, put_header, read_header, reasons.json, job.json or the local jobs and headers layout.
- Affected: Stories 1.10, 2.10, 2.11, 2.21, 7.10, 7.12, 7.15, 7.20, 7.21; the ports above; `src/infra/local.py`, `src/infra/modal.py`, `src/pipeline/regenerate.py`, `scripts/purge_judge_rooms.py`, `scripts/quota_probe.py`.
- Behavior: every method listed exists, has a docstring and is implemented by both the local and the Dict and Volume adapters. Atomic put is defined only for the hosted quota claim: `Dict.put(key, job_id, skip_if_exists=True)` per slot. The ArtifactStore.put and Cache.put docstrings say nothing about atomicity. Locally every put writes a temp file and `os.replace()`s it. Hosted `VolumeFiles.write` writes in place under a process-wide `VOLUME_LOCK` and then commits, so a write is atomic per container and visible to others at commit. `delete_judge_room` removes every Session whose stored header names the Room or whose events name one of its interactables or puzzles (headers included; the header test is lane F20, c652116), every Cache entry listed in cache-keys.json and the whole `rooms/judge/<room_id>/` folder, pops `<job_id>` and `call:<job_id>`, and keeps the `build:N` slot by design (A-25). `purge_judge_rooms` enumerates every judge directory, including a Build that ended without a Room. Gap: `attempts:<ip>` keys hold client IPs with timestamps and only the 7-day idle Dict expiry removes them, while the `src/infra/modal.py` docstring says "no retention rule relies on that expiry (AD-8)".
- Verification: 4432282, c5467fa, 35d3f0b, 29fa0f5, a4ec8ab, 08af81d, 01f7212, e638cd9 (F1), c652116 (F20), 69c269a. `tests/infra/test_modal_quota.py::test_forty_concurrent_claimers_take_each_of_the_twenty_slots_once`, `::test_concurrent_claimers_over_19_claimed_slots_produce_exactly_one_more_claim`; `tests/infra/test_modal_retention.py::test_a_judge_room_goes_with_its_photos_originals_sessions_and_listed_cache_entries_and_the_volume_is_committed`, `::test_a_judge_build_that_ended_without_a_room_keeps_its_job_id_after_the_dict_entry_expires`, `::test_a_session_whose_header_names_the_deleted_room_goes_with_it_header_included_even_when_its_events_name_nothing` (F20); `tests/pipeline/test_ports.py::test_session_store_declares_the_header_beside_the_log` (F1); `tests/infra/test_local.py::test_a_header_is_stored_beside_the_log_read_by_a_new_instance_never_listed_and_deleted_with_it` (F1); `tests/api/test_session_restart.py::test_every_session_route_answers_for_a_session_a_restarted_app_never_opened` (F1); `tests/api/test_access_check.py::test_the_dict_attempt_store_shares_the_jobs_dict_and_never_names_a_job`; `tests/scripts/test_quota_probe.py`, whole file (9 collected). All pass. Live: ops run 2 (GitHub run 40821411610), 30 racing claimers took exactly 20 unique slots, 8 racers for the last slot got exactly 1.
- Remaining gates: `delete_judge_room` and `purge_judge_rooms` have run only against offline fakes, not the real keyframe-data Volume and keyframe-jobs Dict. Cross-container VolumeFiles visibility is unverified. No atomic-put definition for ArtifactStore and Cache. `attempts:<ip>` has no cleanup path other than Dict expiry.

### 42 `phraser_fallback` as structured operational logging
Decision: Keep structured logs (amend AD-5). Status: partial.

- Contract: spine AD-5 Rule (line 71) says that after the 5 s timeout "the event log records `phraser_fallback`". Epics Story 3.7 (line 3050) says it "is logged with its cause"; the greeting story (line 3702) says "the session Event log records `phraser_fallback` once". The decision keeps a log line and adds no game event; it wants the displayed template text, `phrased=false` and latency stored in existing outputs and events, cause and identifiers logged, and no infrastructure error text shown to the player.
- Affected: Stories 3.2, 3.7, 5.5, 5.6; `src/providers/ollama.py` (`_log_fallback`), `src/api/app.py` (greet, worded), `src/council/greeting.py`; RungChangeEvent, OpeningLineEvent, OpeningLine, HintReply.
- Behavior: no phraser_fallback game event exists. OllamaPhraser logs one JSON warning line {event: 'phraser_fallback', call, cause (timeout | unreachable | error), duration_ms, error} and returns `PhraserResponse(fallback text, phrased=False, latency_ms)`. The greeting path logs {session_id, event: 'phraser_fallback', duration_ms} plus error when the composer raised, and appends the template as `OpeningLineEvent(kind='greeting', text)`. For Rungs, `worded()` stores the text as shown and `phrased=False`; `phrasing_ms` is set only when phrased, so a fallback's latency reaches only the log. OpeningLineEvent and OpeningLine carry no phrased flag and no latency. HintReply carries neither. The hint fallback line has no session_id or puzzle_id; for a greeting fallback the cause is on the adapter's line (no session_id) and the session_id on the app's line (no cause). Players see only the verbatim Rung or Greeting template.
- Verification: 27a57df, ce3cd57. `tests/providers/test_ollama.py::test_phrase_falls_back_to_the_verbatim_rung_and_logs_phraser_fallback_with_its_cause`; `tests/api/test_greeting_path.py::test_past_5_s_or_unreachable_the_template_is_the_opening_line_and_phraser_fallback_is_logged_once`, `::test_a_composer_that_raises_falls_back_to_the_template_and_logs_phraser_fallback_once`; `tests/providers/test_verbatim.py`, whole file (31 collected). All pass.
- Remaining gates: open in code: fallback latency not kept in rung_change or opening_line; opening_line has no phrased flag; hint fallback log has no session or puzzle id. Open in docs: the AD-5 amendment. Live: SIT-05 (real Ollama within 5 s, then unreachable with cause unreachable) is unrun; the owner runs it on the M1 with Ollama and llama3.2:3b, with the M1 doctor run and browser pass.

### 46 Hosted Trickster cache off
Decision: Keep / record. Status: partial (the decision says "verify no cache write occurs"; that check has run offline only).

- Contract: lane F6. Spine AD-8 Rule amended in 80e7740: the hosted Trickster's provider runs with the cache off (guarded and priced, AD-6, never stored), so a live window on a Judge room leaves no cache entry outside the listed keys. Departs from epics FR-27 ("Every paid cloud call can be served from the Cache") and from the default CACHE=on, for this one role in Hosted mode.
- Affected: Stories 4.8, 7.20; FR-27, FR-33; `src/api/wiring.py` (hosted branch, `Wiring.trickster`), `src/providers/cache.py` (`GuardedCalls enabled=False`), `src/infra/modal.py` (`delete_judge_room`, `CacheKeyLog`).
- Behavior: in Hosted mode `wire()` builds the Trickster provider with `GuardedCalls(hosted.cache, ledger, host=host, enabled=False)`, sharing the build providers' SpendLedger, so every window is guarded and priced but neither reads nor writes the Cache. Reason: a Judge room window would otherwise write room ids and decoy attributes from the judge's photos to `/data/cache/` under a key no cache-keys.json lists, which `delete_judge_room` would never remove. Keys never repeat anyway because the prompt carries elapsed_ms. Local mode keeps the shared cache. The fix is in the deployed `c9d0d61`.
- Verification: 80e7740. `tests/api/test_live_trickster_route.py::test_a_hosted_live_window_on_a_judge_room_is_priced_but_leaves_no_cache_entry_the_purge_cannot_list` passes (CACHE=on and DEMO_TRICKSTER=live hosted settings, one accepted card, no `/data/cache` directory, one ledger entry). Deploy run 6 put `c9d0d61` on the hosted URL.
- Remaining gates: no hosted Trickster window has run on the real keyframe-data Volume; the only proof is the offline test. The decision's no-cache-write check is unrun live (section 7).

## 3 HTTP surface

### 37 Expanded HTTP surface
Decision: Document / correct wrong status. Status: partial.

- Contract: spine AD-13 (line 119), amended in b161d99: 409 build_not_ready with the job status on GET /builds/<job_id>/room for a known job not yet done (was 404 room_not_found); 404 job_not_found; 422 invalid_request, never echoing a sent value. The Conventions HTTP surface row (line 157) gained the /room 409 and the session-route 410 and 404. Not documented anywhere: multipart field names `downscale` and `original`, the pairing rule (the i-th downscale with the i-th original; a count mismatch is 422 photo_count), and the POST /builds success body. Docs say POST "returns a job_id" (epics Story 2.12, `docs/specs/spec-keyframe/stack.md` line 38); the route returns a whole JobState.
- Routes as shipped, all under /api, envelope `{error: {code, message, stage}}`, any request-validation failure 422 invalid_request:

| Route | Success | Refusals |
|---|---|---|
| GET /meta?profile= | 200 Meta | 422 invalid_profile_name |
| GET /schema | 200 JSON Schema | |
| POST /access/check (hosted only; 404 in Local) | 200 AccessCheck {ok, builds_left} | 429 too_many_attempts + Retry-After |
| POST /builds (multipart) | 202 JobState queued with the ingest record; 200 JobState failed if the in-request store fails | hosted 403 access_denied, 429 before the body is read; 422 photo_count, unsupported_image, bad_downscale (stage ingest); 403 build_quota_exceeded (stage null) |
| GET /builds/{job_id} | 202 queued or running, 200 terminal | 404 job_not_found; 410 room_deleted; 500 if the job record does not parse |
| GET /builds/{job_id}/room | 200 Room | hosted 403, 429 first; 404 job_not_found; 410; 409 build_not_ready + status; 404 room_not_found |
| GET /builds/{job_id}/view (never guarded) | 200 BuildView | 404 job_not_found; 410; 409 build_not_ready + status; 404 room_not_found |
| GET /rooms | 200 list[RoomSummary] | rooms without a job record left out; unparseable job records skipped and logged |
| GET /rooms/{room_id} | 200 PlayView | 404 room_not_found; 410 room_deleted |
| GET /rooms/{room_id}/photos/{index} | 200 image/jpeg | 404 room_not_found or photo_not_found; 410; 422 non-integer index |
| GET /profile/{name} (Local only, not gated on a cut flag) | 200 Profile | 404 profile_not_found; 422 invalid_profile_name |
| PUT /profile/{name} (Local only) | 200 Profile | 422 invalid_profile, invalid_profile_name |
| Session routes | 200 | 404 session_not_found; 410 room_deleted for Sessions a deletion took, GET /sessions/{id}/room included (lane F2) |

- Lanes: F2 (f784ac7) made the session room read answer 410 room_deleted when the session's Judge room is deleted while the session is open (before, that read did not check for a deletion record). F20 (c652116) widened which Sessions a deletion takes, and so which ones answer 410: every Session whose stored header names the Room, even when its events name nothing. F15 (5c5625d) keeps an AD-13 code to its meaning: an Architect reply that does not parse as the response shape is a `malformed` ProviderError, so the Build ends `failed` with provider_error; validation_error stays a draft the Validator sent back.
- Affected: Stories 1.11, 1.12, 1.24, 2.12, 5.3, 7.11, 2.28; `src/api/app.py`, `src/api/errors.py`, `src/council/architect.py` (F15), `src/infra/modal.py` (F20); ErrorEnvelope, ErrorDetail, JobState, AccessCheck.
- Behavior: outcomes stay distinct: 410 room_deleted is checked only after the lookup misses; 403 access_denied is checked before the body is read or the job looked up; 429 is checked before the code is compared. `_failure()` in `errors.py` drops a sent union tag, an extra key, or a value that appears inside the message. Gaps found by probing with TestClient: (1) a key the client sends inside a dict field is echoed through the error location (POST /api/sessions with `derived.mean_rung_per_lock_type {"sk-live-0123456789abcdef": 1}` answers 422 with that key in the message); (2) PUT /api/profile/{name} uses pydantic's raw loc and msg unscrubbed, echoing a sent results key, and Profile's cross-check echoes both sent room ids; (3) an unknown /api/* path answers 404 `{"detail": "Not Found"}`, outside the envelope; (4) a stored job, room or profile that fails to parse is a bare 500 (deliberate for job records); (5) a POST /builds whose in-request ingest store fails answers 200 with a failed JobState after a slot was claimed.
- Verification: b161d99, 72d6bfb, 08af81d, 1444af0, f784ac7 (F2), c652116 (F20), 5c5625d (F15). `tests/api/test_builds.py::test_the_room_route_answers_409_build_not_ready_with_the_status_until_the_job_is_done`, `::test_a_downscale_without_its_original_is_refused_as_photo_count`, `::test_multipart_parts_round_trip_bytes_that_look_like_boundaries_and_line_ends`, `::test_a_body_that_is_not_multipart_holds_no_photos`, `::test_an_unknown_job_answers_404`, `::test_job_state_answers_202_while_queued_or_running_and_200_when_terminal`; `tests/api/test_build_view.py::test_a_job_not_yet_done_answers_409_build_not_ready_with_its_status`, `::test_status_appears_on_build_not_ready_only`; `tests/api/test_app.py::test_the_envelope_carries_a_null_stage_and_no_status`, `::test_an_unknown_room_answers_404_with_the_envelope`; `tests/api/test_hints.py::test_a_refused_body_is_never_echoed_in_the_message`; `tests/api/test_room_deleted.py::test_a_deleted_judge_room_id_answers_410_room_deleted_on_every_room_keyed_route`, `::test_the_deleted_rooms_job_id_answers_410_room_deleted_on_every_job_keyed_route`, `::test_every_session_route_of_a_session_still_open_on_a_deleted_judge_room_answers_410`, `::test_a_session_still_open_on_a_deleted_judge_room_answers_410_on_its_room_read` (F2), `::test_an_unknown_room_id_answers_404_room_not_found_beside_a_deletion_record`, `::test_an_unknown_session_stays_404_session_not_found_beside_a_deletion_record`, `::test_an_unknown_job_id_keeps_its_404_job_not_found`, `::test_the_guarded_room_route_still_refuses_a_missing_code_before_answering_410`; `tests/api/test_access.py::test_a_build_without_the_right_code_is_refused_before_any_photo_job_or_slot`, `::test_the_guard_runs_before_the_job_lookup_so_an_unknown_job_is_refused_alike`, `::test_the_full_room_without_the_right_code_is_refused_and_returns_no_part_of_it`, `::test_the_21st_build_with_the_right_code_is_refused_with_the_quota_and_stores_nothing`, `::test_the_quota_refusal_still_needs_the_right_code_first`; `tests/infra/test_modal_retention.py::test_a_session_whose_header_names_the_deleted_room_goes_with_it_header_included_even_when_its_events_name_nothing` (F20); `tests/pipeline/test_architect_stage.py::test_a_reply_off_the_response_shape_ends_the_build_failed_at_architect_as_a_provider_error` (F15); `tests/api/test_access_check.py::test_a_guarded_route_past_the_limit_is_refused_with_429_before_the_code`, `::test_local_mode_does_not_serve_the_check_the_only_route_difference_it_adds`; `tests/api/test_profile.py::test_the_422_message_names_the_failing_field_and_not_the_body`. All pass.
- Remaining gates: open in code: dict keys echoed in invalid_request and invalid_profile, and the Profile cross-check message; no test catches it. The unknown /api path 404 is outside the envelope. Hosted 403, 429 and quota paths are proven offline only; live, only the quota claim was proven (GitHub run 40821411610).

### 40 Bounded in-request ingest
Decision: Accept bounded ingest. Status: partial.

- Contract: epics Story 2.10 and spine AD-7 (line 83) run ingest as the first stage "in order through JobRunner.start(job_id)", with the job "queued before the runner starts, running with stage set to the stage in progress". Story 2.18 has the "Reading your photos" row go pending, running, done from polled state. Shipped: upload validation and storage run inside POST /builds (`Build.submit`), and the runner starts at architect.
- Affected: Stories 2.10, 2.12, 2.16, 2.18, 7.8; `src/pipeline/build.py` (`Build.submit`), `src/pipeline/ingest.py`, `src/api/app.py` (`post_build`, `read_uploads`), `web/src/capture.ts`, `web/src/build-stages.ts`; JobState.
- Behavior: order in POST /api/builds: (a) access guard in the thread pool, before the body is read; (b) `request.body()` read whole; (c) `read_uploads` pairs downscale and original parts; (d) `validate_upload` checks 6 to 10 photos, JPEG or MPO by bytes for both files, Pillow DecompressionBomb as unsupported_image, a 1280 px long edge and EXIF orientation 1, before any id, slot or file exists; (e) `jobs.reserve_build` claims a slot; (f) `store_upload` writes downscales, originals and photos.json under `<room_id>/` as the ingest stage; (g) the job is persisted queued with stage null and stages [ingest]; (h) `runner.start` and 202. `Build.run` resumes after the last persisted stage, so it starts at architect. No model or paid stage runs in the request. The job is never persisted as running ingest. The client shows "Reading your photos" as Upload's pending label, then the polled Stage list shows it done with the photo count. "Bounded" holds only for the photo count (at most 10 pairs) and Pillow's pixel limit: no byte cap on the body or a single file, and the whole body is read into memory before validation.
- Verification: 66a3b29, f62d2f3, bb2b174. `tests/api/test_builds.py::test_post_builds_returns_a_job_id_while_a_stage_is_held_open` (runner ran `STAGES[1:]` only), `::test_an_upload_ingest_refuses_answers_422_at_ingest_and_queues_no_job`; `tests/api/test_hosted_build.py::test_post_builds_commits_the_photos_writes_the_queued_record_then_spawns_and_answers_at_once`; `tests/api/test_access.py::test_an_upload_ingest_refuses_claims_no_slot_and_stores_nothing`; `tests/web/test_capture.py::test_while_the_upload_is_pending_upload_shows_its_pending_label_and_the_dropzone_is_disabled`; `tests/web/test_strings.py::test_the_capture_strings_are_the_experience_lines`. All pass. Live: hosted job job_01M61TZ74F6F3AVVEMPRAS4V1G done after 182 s.
- Remaining gates: no request-size cap in app code and no test of an oversized body; any Modal platform limit unchecked. A failed in-request store gives 200 with a failed JobState and the slot stays claimed (untested). The pending label in a real browser waits on the owner's M1 browser pass.

### 41 Copied validator messages with a drift check
Decision: Accept pinned copy. Status: implemented.

- Contract: Story 2.31 and UX-DR51: the verdict table shows the fixed message on fail rows. `RULES` in `src/domain/validator.py` is the only source of check names and fixed messages. The web keeps a copy of the rule 1 to 8 fail messages (`strings.rule1Failed` to `rule8Failed`, mapped in `verdict-table.ts FIXED_MESSAGES`) and of `rule9Name`. No public schema field carries the messages: RuleVerdict is {rule, name, passed}. Tradeoff recorded here: the copy saves a schema field and a round trip; the drift test is the guard; RULES is the authority.
- Affected: Stories 2.31, 2.29; `web/src/strings.ts`, `web/src/components/verdict-table.ts`, `src/domain/validator.py` RULES; RuleVerdict; EXPERIENCE.md Voice and Tone rule table.
- Behavior: pass rows show the server's `RuleVerdict.name`; fail rows add the copied message by rule number; rule 9 shows apart as "not applicable" with `rule9Name`. The drift test asserts, for each rule, that `strings[ruleNFailed]` equals `RULES[n].message`, that the EXPERIENCE.md row equals the RULES name and message, that `verdict-table.ts` maps n to `strings.ruleNFailed`, and that `rule9Name` equals `RULES[9].name`. Trickster card messages and Sent-back lines come from the server and are not copied.
- Verification: 62a3535, 5863a59. `tests/web/test_build_view_verification.py::test_the_check_names_and_fixed_messages_are_the_validators_and_the_experience_lines`, `::test_rule_9_shows_apart_as_not_applicable_and_the_rules_line_counts_the_base_checks_only`. Both pass.
- Remaining gates: rendering in a real browser waits on the owner's M1 browser pass.

### 45 Compile-time cut 0 and the direct Build-view route
Decision: Keep / close direct route. Status: partial.

- Contract: epics Stories 2.27 to 2.31 and UX-DR84: cut 0 drops the Build view and every link to it. Story 2.29 (line 2673): "under cut 0 the route and surface are absent". Story 6.2 (line 3889): "under cut 0 no BuildView route exists". The decision keeps a documented build-time flag and, when set, guards the direct route with an existing unavailable or not-found view.
- Affected: Stories 2.29, 2.31, 7.16, 6.2; `web/src/router.ts` (`CUT_0`), `web/src/build-view.ts` (`buildViewLink`), `web/src/landing.ts`, `web/src/shell.ts`; GET /api/builds/{job_id}/view.
- Behavior: `export const CUT_0: boolean = false` in `web/src/router.ts`, fixed at build time. Every entry link is guarded: `buildViewLink` returns null under CUT_0; `landing.ts` guards the hero "How a room is built" link and the Demo card thumbnail and link. The direct route is not guarded: `parsePlace` maps `#/build/<job_id>/view` to the view route whatever CUT_0 is, and `shell.ts render()` shows it with no CUT_0 check. The server route is registered unconditionally. The flag is documented only in a code comment. CUT_0 is false today, so the gap is latent until the cut is taken.
- Verification: 62a3535, 3f6a427. `tests/web/test_build_view_verification.py::test_the_link_opens_the_build_view_of_that_job_and_cut_0_drops_every_one`; `tests/web/test_hosted_landing.py::test_the_hero_holds_the_display_lg_line_the_tagline_the_verb_and_the_build_view_link`, `::test_under_cut_0_the_card_has_no_link_no_thumbnail_and_still_starts_sessions`. All pass.
- Remaining gates: no guard and no test for `#/build/<job_id>/view` under CUT_0. Flag undocumented outside source. Taking cut 0 would also need the disclosures and README Model table checked; not done because the cut is not taken.

## 4 Build, CI, deploy and ops

### 15 CI trigger documentation
Decision: Keep behavior / reconcile. Status: partial.

- Contract: epics AR-24 (line 112): one job `check` "on push to master and on every pull request ... no secrets, no deploy step, no CD; `modal deploy` stays a manual step". Story 1.3 AC 1: "When a commit is pushed to master or a pull request is opened". Final CI triggers, stated once (`.github/workflows/ci.yml`): `on: push: branches: [master, "keyframe/**"]` and `pull_request:` with no branch filter; `permissions: contents: read`; concurrency group `ci-<ref>` with cancel-in-progress; one job `check` (ubuntu-latest, timeout 10, MODEL_PROVIDER=mock) running `bash scripts/check.sh` only. The keyframe/** push came in f61147d (26 Oct) and is pinned by 23d8ea2.
- Affected: Stories 1.3, 1.2; AR-24, AR-32; `.github/workflows/ci.yml`, README.md, epics.md, the spine; the keyframe-devops notes (SKILL.md, check-ladder.md, templates.md) and the keyframe-modal runbook; `tests/test_ci_workflow.py`, `tests/test_workflow_docs.py`.
- Behavior: no schedule, no workflow_dispatch, no secret, no modal or deploy reference. The check name stays `check`. README (lines 66-67, 116-117) and the keyframe-devops notes match since 2fd873a; templates.md holds a ci.yml block byte-identical to the real file, enforced by test. The keyframe-modal runbook says no merge, schedule or push to master or keyframe/** runs modal deploy. Not reconciled: AR-24, Story 1.3, AR-32, the spine source tree (line 213) and Deferred list (line 311).
- Verification: f61147d, 23d8ea2, 2fd873a. `tests/test_ci_workflow.py::test_triggers_on_master_and_keyframe_pushes_and_pull_requests`, `::test_exactly_one_job_check_on_ubuntu_with_timeout_and_mock_provider`, `::test_no_secret_no_deploy_no_cd`; `tests/test_workflow_docs.py::test_readme_names_both_workflows_and_the_keyframe_branch_trigger`, `::test_devops_skill_describes_the_real_ci_trigger`, `::test_templates_ci_yml_block_matches_the_real_workflow`. All pass. CI green with check-run name `check` on 18ec75a (runs 40823265601, 40823022242), on 42d3253 (runs 40824024032, 40823800471), on f330810 (runs 40827276075, 40826918938) and on 1e8578a (runs 40828349988, 40828171360).
- Remaining gates: branch protection cannot be seen from the repo; Story 1.3 wants the sprint status to record either required `check` or "CI green before merge kept by hand" (owner, item 20). Docs edit in section 6.

### 47 Repeated schema, CI and import changes
Decision: One record. Status: partial.

- Contract: the decision asks this record to state three things once, each with verification links: the final accepted schema, the actual CI triggers and the narrow import exceptions. Other entries point here rather than restating them.
- Affected: `src/domain/schema.py`, `web/types/schema.json`, `.github/workflows/ci.yml`, `tests/test_boundaries.py`; schema-v1.md, spine AD-1, epics AR-24.
- Behavior:
  - Schema: the post-freeze shape list is the item 33 table (section 1), checked against `src/domain/schema.py`, which no commit after `1eb9f51` changes.
  - CI triggers: item 15 (section 4) quotes `.github/workflows/ci.yml`: push to master and keyframe/**, every pull request, one job `check`, no secret, no deploy.
  - Import allowances: item 35 (section 2) names those `tests/test_boundaries.py` enforces: same-package imports, pipeline importing council, adapters importing `GUARDS = {src.providers.spend, src.providers.cache}`.
- Verification: the links in items 33, 15 and 35. In short: `tests/web/test_types.py::test_web_types_match_what_get_schema_serves`; `tests/test_ci_workflow.py::test_triggers_on_master_and_keyframe_pushes_and_pull_requests`; `tests/test_boundaries.py::test_pipeline_may_import_its_own_modules`, `::test_pipeline_may_import_council_domain_and_ports`, `::test_adapters_may_import_the_guarded_call_path`. All pass.
- Remaining gates: no live gate. The record now exists, but the planning docs are not edited: spine AD-1 still omits the allowances, epics AR-24 still states the old CI triggers, and schema-v1.md still lacks the post-freeze shapes (section 6).

### 43 Ledger export cap configuration
Decision: Fix hidden assumption / record shape. Status: open.

- Contract: spine AD-6 (line 77): local 60 and hosted 20 through Wed Nov 4 (80 in all), local 5 and hosted 20 from Thu Nov 5 (25 in all); Settings reads the override per mode (the Modal Secret `keyframe` carries the hosted value); moving dollars between allocations is a Settings change. Story 7.9: totals against the combined ceiling. The decision: both allocations authoritative and configurable, or the hosted allocation and epoch carried in the snapshot; no hard-coded 20 standing in for the hosted cap; source and staleness documented.
- Affected: Stories 2.6, 7.9, 2.3, 2.12; AD-6, AD-14; LedgerExport (`src/infra/local.py`), `Settings.hosted_spend_cap_usd` (`src/config.py`), `scripts/ledger.py` export, `src/api/wiring.py` ledger_export, `src/infra/modal.py` export_hosted_ledger, `spend/exports/ledger-<date>.json`.
- Behavior: the ceiling is `settings.spend_cap_usd + settings.hosted_spend_cap_usd` (`scripts/ledger.py:135`, `src/api/wiring.py:345`). `spend_cap_usd` reads SPEND_CAP_USD with mode defaults 60 local and 20 hosted. `hosted_spend_cap_usd` is fixed at 20 with no environment key (not in ENV_KEYS or .env.example); its docstring says the local process cannot see the hosted value. The hosted process enforces its own SPEND_CAP_USD from the Secret, which can differ silently from the 20 the export adds. LedgerExport records `ceiling_usd` only: no separate allocations, no source, no staleness marker. `spend/hosted-<date>.jsonl` holds bare LedgerEntry lines, each with its epoch, and no metadata. The invariant holds by coincidence of defaults. No commit since 5ab9309, c7a255f and f4a6296 touched it, and no fix lane covers item 43.
- Verification: 5ab9309, c7a255f, f4a6296. `tests/test_config.py::test_defaults_when_nothing_is_set`, `::test_values_are_read_and_blank_means_unset`; `tests/scripts/test_ledger_script.py::test_the_ceiling_is_the_sum_of_the_two_allocations_settings_knows_with_no_date_logic`, `::test_export_writes_todays_file_and_prints_the_three_totals_beside_the_ceiling`. All pass (they pin the defaults, not the fix).
- Remaining gates: fix not implemented. Needed: a hosted allocation env key, or the allocation and epoch written into the snapshot by the hosted process; separate local and hosted fields and the hosted source in LedgerExport; a test that a changed hosted allocation changes the ceiling. No live ledger-export ops run; the Nov 5 reset (SPEND_CAP_USD=5 locally) has not run.

### deploy-push-trigger: deploy.yml dispatch plus guarded push
Decision: Record (owner decision Oct 29, lane F29). Status: implemented.

- Contract: AR-24 and Story 1.3 say no CD and manual `modal deploy`. Shipped: `.github/workflows/deploy.yml` (794cf3d, 0452a4c) starts from the Actions tab (inputs environment main | dev, min_containers 0 | 1), and since 5c1f56b on a push to deploy/main (main, 0), deploy/main-warm (main, 1) or deploy/dev (dev, 0). Not triggered by merges, schedules or pushes to master or keyframe/**.
- Affected: Stories 7.3, 7.22; AR-24; `.github/workflows/deploy.yml`, `src/api/modal_app.py`, README.md, `tests/test_deploy_workflow.py`, keyframe-modal runbook, keyframe-devops check-ladder.
- Behavior: on push, the first step after a full-history checkout runs `git merge-base --is-ancestor $GITHUB_SHA origin/master` and refuses any commit master does not carry; any older master ancestor is accepted, which allows a rollback. Then setup-uv 0.11.32, setup-node from .nvmrc, `bash scripts/check.sh --predeploy`, `modal environment list` with create-if-missing, `modal deploy -e $MODAL_ENVIRONMENT -m src.api.modal_app`, the URL from the log, and a `GET /api/meta` smoke retried 12 times every 10 s. Token from MODAL_TOKEN_ID and MODAL_TOKEN_SECRET only; MODEL_PROVIDER=mock; one concurrency group per Environment, never cancelled. The guard lives in the pushed commit's own workflow file: an accident rail, not a security boundary. Dispatch from the build container answers 403, which is why the push path exists. origin/deploy/main is at `c9d0d61`, an ancestor of origin/master.
- Verification: 794cf3d, 0452a4c, 5c1f56b. `tests/test_deploy_workflow.py`, whole file (7 collected): `::test_runs_when_started_by_hand_or_on_a_push_to_the_three_deploy_branches_only`, `::test_the_environment_and_min_containers_follow_the_inputs_or_the_pushed_branch`, `::test_a_push_deploys_only_a_commit_master_already_carries_before_any_other_step`, `::test_the_token_comes_from_the_repository_secrets_and_nowhere_else`, `::test_the_predeploy_ladder_runs_before_one_modal_deploy_of_the_app_module`, `::test_the_deploy_ends_with_a_smoke_test_of_the_meta_route`, `::test_ci_still_holds_no_secret_and_no_deploy`. All pass. GitHub run 40802005305 (push to deploy/main, `c9d0d61`): success.
- Remaining gates: deploy/main-warm and deploy/dev never pushed; the warm window (MIN_CONTAINERS=1, Thu Nov 5 to Mon Nov 9) not exercised; the refusal path tested offline only.

### ops-push-trigger: ops.yml dispatch plus guarded push
Decision: Record (owner decision Oct 29, lanes F26, F27, F29). Status: implemented.

- Contract: no epics, spine or spec text names an ops workflow; runbook items were Mac-run by hand. Shipped: `.github/workflows/ops.yml` (0e99b54; promote in 4d3367a; push path in 5c1f56b; quota-probe in 69c269a). Inputs: action, environment main | dev (default main), confirm, room_id, room_name. Also starts on a push to ops/**.
- Affected: `.github/workflows/ops.yml`, `.github/ops/request.json` (request branches only), README.md, `tests/test_ops_workflow.py`, keyframe-modal SKILL.md and runbook, keyframe-devops check-ladder.
- Behavior: job `request` holds no secret. On push it refuses unless the commit's parent is an ancestor of origin/master and the commit changes exactly `.github/ops/request.json`, then validates the file: one JSON object with only action, environment, room_id, room_name and confirm, all one-line strings, defaults environment=main and the rest empty, action one of the 8 listed, environment main or dev; bad input fails with a named reason. On dispatch the same validation runs over the inputs. Job `ops` needs `request`, takes the token from secrets, serialises per Environment (group `ops-<env>`, no cancel), runs `uv sync --locked`, then one env-guarded step. The request file is never tracked on master. As with deploy.yml, the guard is an accident rail, not a security boundary.
- Verification: 0e99b54, 4d3367a, 5c1f56b, 25c2479. `tests/test_ops_workflow.py::test_runs_when_started_by_hand_or_on_a_push_to_an_ops_branch_only`, `::test_the_request_job_holds_no_secret_and_guards_a_push_to_one_request_file_on_top_of_master`, `::test_the_ops_job_waits_for_the_request_and_serialises_per_modal_environment`, `::test_a_dispatch_takes_the_inputs_and_a_push_the_request_file_with_the_same_defaults`, `::test_a_bad_or_missing_request_file_fails_clearly`, `::test_the_request_file_lives_only_on_request_branches`. All pass. GitHub run 40821411610 (push to ops/quota-probe-1, request commit 25c2479 on parent 69c269a, {action quota-probe, environment main}): success.
- Remaining gates: push-path refusals (parent off master, extra file, bad JSON) tested offline only; one push-triggered ops run exists.

### ops-actions: every ops action as shipped
Decision: Record. Status: implemented.

- Contract: runbook commands formerly Mac-only (Stories 2.6 and 7.9 export, 7.19 purge, 7.22 warm window, 7.13 Demo seeding replaced by promotion per the owner decision of Oct 28, 7.10 atomicity check) run in the ops job with `--env` from the Environment input.
- Affected: `.github/workflows/ops.yml`, `scripts/ledger.py`, `scripts/purge_judge_rooms.py`, `scripts/promote_room.py`, `scripts/quota_probe.py`; Stories 2.6, 7.9, 7.10, 7.13, 7.19, 7.22.

| Action | Command | Guard | Run live |
|---|---|---|---|
| ledger-export | `uv run scripts/ledger.py export --env $ENV`, then upload-artifact (pinned v7.0.2 SHA) of `spend/exports/` as `ledger-export-<env>`, if-no-files-found error; never commits | | no |
| purge-dry-run | `scripts/purge_judge_rooms.py --env $ENV --dry-run` | | no |
| purge | `scripts/purge_judge_rooms.py --env $ENV` | CONFIRM exactly `purge` | no |
| warm | `modal function autoscaler update -e $ENV keyframe/web --min-containers 1`, then print settings | | no |
| cool | same with `--min-containers 0` | | no |
| autoscaler-settings | `modal function autoscaler settings -e $ENV keyframe/web` | | no |
| promote | `scripts/promote_room.py --env $ENV --room $ROOM_ID $ROOM_NAME` | both ROOM_ID and ROOM_NAME non-empty | yes, ops run 1 (GitHub run 40795627220, dispatch) |
| quota-probe | `scripts/quota_probe.py --env $ENV` | ephemeral Dict only | yes, ops run 2 (GitHub run 40821411610, push) |

- Behavior: promote copies room.json (named, at most 40 chars), photos, cards and the done job.json to `rooms/demo/<id>/`, leaves originals, cache-keys.json and the Judge copy in place, rewrites each photo's original_path to the downscaled key (decision 9, 69c269a), and refuses before writing if a referenced file is missing. Ops run 1 promoted room_01M61TZ74F0FP3X9HHTMXGTPB9 from hosted job job_01M61TZ74F6F3AVVEMPRAS4V1G. `gh run list --workflow ops.yml` shows only those two runs.
- Verification: 0e99b54, 4d3367a, 69c269a. `tests/test_ops_workflow.py::test_every_runbook_command_is_present_once_with_the_environment_variable`, `::test_the_ledger_export_is_uploaded_as_an_artifact_and_never_committed`, `::test_the_real_purge_runs_only_when_confirm_is_the_word_purge`, `::test_the_promotion_runs_only_when_both_room_values_are_given`, `::test_the_quota_probe_runs_from_a_dispatch_or_a_request_file_on_an_ephemeral_dict_only`, `::test_no_deploy_and_no_unpinned_third_party_action`; `tests/scripts/test_promote_room.py`, whole file (22 collected). All pass.
- Remaining gates: six actions never run live. The Nov 10 purge path is unproven, and Story 7.19 wants a dev Judge room purged in a non-judging Environment first. The Nov 5 warm override is not applied, and Story 7.22 makes it conditional on the Official Rules.

### settings-unnamed-keys: Settings keys the spec and spine do not name
Decision: Record. Status: record-only.

- Contract: spine AD-14 names MODEL_PROVIDER, PROVIDER_<ROLE> "with per-role model ids", MODEL_API_KEY, META_MODEL_API_BASE_URL, OPENAI_COMPATIBLE_BASE_URL, OPENAI_COMPATIBLE_API_KEY, FAL_KEY, OLLAMA_HOST, ACCESS_CODE, and the flags MODE, MIN_CONTAINERS, CACHE, SPEND_CAP_USD, DEMO_TIMESCALE, DEMO_TRICKSTER, DRY_RUN, REGEN_MAX, GUIDE. Neither the spine nor `docs/specs/spec-keyframe/*.md` names the keys below.
- Affected: `src/config.py` (Settings, ENV_KEYS, MODE_DEFAULTS, MODE_REFUSED), `.env.example`, `src/api/wiring.py`, `scripts/ledger.py`, `tests/test_config.py`, `tests/test_gitignore.py`.
- Behavior:
  - DEMO_PROPOSALS_DIR: optional path, default unset (wiring then reads `proposals/` at the repo root). Folder holding recorded.json and authored.json for DEMO_TRICKSTER=scripted | authored replay and =record writes (AD-15). `scripts/load_fixtures.py` installs the four-lock recording under `rooms/proposals/` and prints the value to set. Added in 9463aeb (28 Oct). Not a secret.
  - MODEL_ARCHITECT, MODEL_RIDDLER, MODEL_DRYRUN, MODEL_TRICKSTER, MODEL_IMAGE: per-role model ids, defaults muse-spark-1.3 for the four council roles and muse-image-1.0 for image. Added in 41e8f7d (Story 1.2).
  - `hosted_spend_cap_usd`: Settings field, no environment variable, fixed at 20 (item 43).
  - Policy: MODE_DEFAULTS (SPEND_CAP_USD 60 and GUIDE=ollama local; 20 and verbatim hosted); MODE_REFUSED (hosted refuses GUIDE=ollama and DEMO_TRICKSTER=record); SECRET_KEYS (MODEL_API_KEY, FAL_KEY, OPENAI_COMPATIBLE_API_KEY, ACCESS_CODE) must be blank in .env.example. Every ENV_KEYS entry appears blank in .env.example.
- Verification: 41e8f7d, 9463aeb. `tests/test_config.py::test_demo_proposals_dir_is_read_as_a_path_and_unset_leaves_the_default_folder_to_wiring`, `::test_defaults_when_nothing_is_set`, `::test_model_provider_is_the_default_for_each_role`, `::test_reads_each_key_exactly_once_and_nothing_else`; `tests/test_gitignore.py::test_env_example_lists_every_settings_key_blank`. All pass.
- Remaining gates: none.

### build-quota-probe: hosted build quota and its live atomicity probe
Decision: Record (decisions 18 and 23, lane B5). Status: implemented.

- Contract: spine (line 95) and AR-12: 20 slot keys claimed with `Dict.put(key, value, skip_if_exists=True)`, the 21st refused with build_quota_exceeded; atomicity verified before the quota is relied on. The spine was amended Oct 29 to name `scripts/quota_probe.py` via the ops quota-probe action on an ephemeral Dict, never keyframe-jobs, expecting 20 of 30 and 1 of 8. Story 7.10 AC 4 says "checked live in a non-judging Modal Environment ... result recorded in the sprint status".
- Affected: Stories 7.10, 7.11; AD-9, AR-12; `src/infra/modal.py` (`DictJobStore.reserve_build`, `builds_left`, `BUILD_QUOTA`, `slot_key`), `scripts/quota_probe.py`, `.github/workflows/ops.yml`, sprint-status.yaml, sit-checklist.md.
- Behavior: BUILD_QUOTA=20, keys build:1 to build:20 in keyframe-jobs. `reserve_build` takes the first free slot with `put(slot, job_id, skip_if_exists=True)` and raises BuildQuotaExceeded having written nothing when all are taken. No slot is released; failed, needs_more_photos and needs_recapture builds count. `builds_left` = 20 minus present slot keys; it survives restarts. A slot key can still expire after 7 idle days, which frees a build. The probe defaults to Environment dev, takes `--env`, creates `modal.Dict.ephemeral()` per race and spawns separate processes behind a barrier. Race 1: 30 claimers, exactly 20 unique wins. Race 2: 19 prefilled, 8 claimers, exactly 1 win, no prefilled slot overwritten. Exits 1 otherwise. Departure accepted here for record: the live probe ran in `main`, the judging Environment, not a non-judging one, on an ephemeral Dict, so no real slot was claimed.
- Verification: 69c269a, 25c2479. GitHub run 40821411610: "quota probe passed". `tests/infra/test_modal_quota.py::test_twenty_claims_succeed_and_the_21st_raises_and_writes_nothing`, `::test_each_claim_is_one_conditional_put_per_slot_until_a_free_one`, `::test_every_accepted_build_counts_whatever_its_end_status`, `::test_the_count_lives_in_the_dict_and_reading_it_claims_nothing`; `tests/scripts/test_quota_probe.py::test_claim_takes_the_same_slots_in_the_same_order_as_reserve_build`, `::test_a_claim_that_is_not_atomic_fails_both_races_and_exits_1`, `::test_the_script_never_names_a_real_dict_and_races_in_separate_spawned_processes`. All pass.
- Remaining gates: the probe did not exercise the named keyframe-jobs Dict or `reserve_build` through the web container, and raced processes on one runner, not separate containers. The result is not yet in sprint-status.yaml or the SIT checklist row (item 18).

### modal-objects: Dicts, Volume layout, Secret required keys
Decision: Record. Status: implemented.

- Contract: spine AD-9 (line 95) names Dicts keyframe-jobs, keyframe-sessions, keyframe-ledger, Volume keyframe-data at `/data`, Secret keyframe, functions web, run_build, ledger_export, session_sweep, and partitions rooms/demo, rooms/judge, rooms/deleted. AD-14: the Secret carries the hosted keys. Shipped addition (lane F16, 2f7bb82): `modal.Secret.from_name('keyframe', required_keys=['MODEL_API_KEY', 'FAL_KEY', 'ACCESS_CODE'])`, so a Secret missing one fails at hydration.
- Affected: Stories 7.1, 7.2, 7.8, 7.14, 7.18; AD-9, AD-14; `src/api/modal_app.py`, `src/infra/modal.py`.
- Behavior: lazy handles for the Volume and three Dicts, all create_if_missing; Volume at `/data`; Secret attached at App level. Image: debian_slim 3.13, uv_sync of uv.lock (uv 0.11.32, --no-dev), env MODE=hosted and GUIDE=verbatim, src and web/dist, plus proposals/ when present. web: min_containers from Settings, max_containers=1. run_build: timeout 900, max_containers 1. ledger_export: Cron 06:00 America/New_York. session_sweep: Cron `17 * * * *`. Volume: `rooms/demo/<room_id>/` (room.json, photos, cards, job.json; the only partition list_rooms lists); `rooms/judge/<room_id>/` (artifacts, originals, cache-keys.json, job.json for every terminal status, failed included since 69c269a); `rooms/deleted/<room_id>.json` (ids only); `cache/<key>.json`; `spend/hosted-<date>.jsonl`. keyframe-jobs: job state, `call:<job_id>`, 20 `build:<n>` slots. keyframe-ledger: one key per entry plus `epoch`. SPEND_CAP_USD and OPENAI_COMPATIBLE_API_KEY are optional Secret keys. Scripts resolve objects with `from_name(..., environment_name=--env)`.
- Verification: 2f7bb82 (F16), 69c269a. `tests/api/test_modal_app.py::test_the_secret_declares_the_hosted_keys_so_a_deploy_without_one_fails_before_a_build_does` (F16), `::test_the_secret_and_the_volume_are_attached_and_no_gpu_is_requested`, `::test_the_app_defines_web_run_build_ledger_export_and_session_sweep`, `::test_web_is_one_container_of_20_concurrent_inputs_with_min_containers_from_settings`, `::test_session_sweep_is_an_hourly_cron_with_no_web_endpoint`, `::test_ledger_export_writes_todays_snapshot_in_new_york`, `::test_the_image_runs_hosted_with_the_verbatim_guide`, `::test_the_image_carries_proposals_beside_src_when_the_folder_exists_so_a_scripted_trickster_has_a_source`; `tests/infra/test_modal_partitions.py::test_list_rooms_returns_a_summary_for_each_demo_room_and_none_for_any_judge_room`, `::test_every_path_a_judge_build_writes_is_under_its_judge_folder_whatever_its_end_status`; `tests/infra/test_modal_quota.py::test_the_quota_is_twenty_slot_keys_in_the_jobs_dict`. All pass. Deploy run 6: the Secret hydrated and the app served /api/meta.
- Remaining gates: refusal of a deploy whose Secret lacks a key shown offline only. rooms/deleted and the purge never exercised live. Household consent for real photos beyond the owner's own home is the owner's.

### F29 Deploy and ops run on a push to their dedicated branches
Decision: lane fix. Status: implemented.

- Contract: departure from AR-24 and from F26's "workflow_dispatch only". Details under deploy-push-trigger and ops-push-trigger. ci.yml unchanged. README and the keyframe-modal and keyframe-devops references updated.
- Affected: AR-24, Story 7.3, the ops runbook stories; `.github/workflows/deploy.yml`, `ops.yml`, `tests/test_deploy_workflow.py`, `tests/test_ops_workflow.py`, README.md.
- Behavior: deploy.yml lines 15-38 and ops.yml lines 26-80 carry the triggers, expressions and guards as stated above. Reason: workflow_dispatch from the build container answers 403.
- Verification: 5c1f56b. `tests/test_deploy_workflow.py::test_a_push_deploys_only_a_commit_master_already_carries_before_any_other_step`, `::test_the_environment_and_min_containers_follow_the_inputs_or_the_pushed_branch`; `tests/test_ops_workflow.py::test_the_request_job_holds_no_secret_and_guards_a_push_to_one_request_file_on_top_of_master`. All pass. GitHub runs 40802005305 and 40821411610: success.
- Remaining gates: deploy/main-warm and deploy/dev push paths not exercised live.

## 5 Play and UX departures from lanes

Unless stated, each lane's EXPERIENCE.md and DESIGN.md rows were changed in the same commit, and epics.md was not (section 6). "Not deployed" means on the base but not in the hosted `c9d0d61`. Every UI lane waits on the owner's M1 browser pass.

### D1 The Hosted landing is a title screen
Decision: lane fix. Status: implemented.
- Contract: the "no separate band of wizards" rule gains the landing cast as its one exception; hero, primary verb ("Play the sample room" / "Build your own room"), cast roles, sample page and three steps replace title, pipeline line and "Short on time?"; "No demo rooms are open right now." removed; initial focus moves to the primary verb.
- Affected: Hosted landing (UX-DR57, UX-DR68, UX-DR74); `web/src/landing.ts`, `landing.css`, `components/access-code-build.ts`, `strings.ts` (drops pipelineLine, landingLeadIn, noDemoRooms).
- Behavior: hero line, a tagline naming no model, one primary verb (first Tab stop, initial focus), four 96 px wizard portraits whose voice line fades in on hover and focus. With a Demo room the verb starts a Session on the first one; with none it reads "Build your own room" and focuses the Access code field. Later reshaped by D9, P1, P6.
- Verification: 68b5842. `tests/web/test_hosted_landing.py::test_with_a_demo_room_the_verb_plays_the_sample_room_through_the_card_s_own_start`, `::test_with_no_demo_room_the_verb_is_build_your_own_room_and_moves_focus_to_the_access_code_field`, `::test_the_cast_is_the_four_96px_portraits_with_name_four_word_role_and_voice_line_on_hover_and_focus`. Deployed in `c9d0d61`.
- Remaining gates: M1 browser pass.

### D2 The Trickster shows up in local demo play
Decision: lane fix. Status: implemented.
- Contract: AD-14 and AD-15 addition (owner decision Oct 28), recorded in the commit body only: Settings key DEMO_PROPOSALS_DIR; wiring refuses startup naming the file when DEMO_TRICKSTER is scripted or authored and the file is missing (before: every window ended trickster_source_unavailable silently).
- Affected: Stories 4.3, 4.4; AD-12, AD-14, AD-15; `src/api/wiring.py`, `src/config.py`, `src/council/trickster.py`, `scripts/load_fixtures.py`, `.env.example`.
- Behavior: `wiring.trickster_source` raises at startup naming the missing path; live and record start without a file; `load_fixtures.py` installs `tests/fixtures/proposals/four_lock.json` under git-ignored `rooms/proposals/` and prints the env line; the Validator still judges every Card live.
- Verification: 9463aeb. `tests/api/test_trickster_route.py::test_a_missing_proposals_file_refuses_startup_naming_its_path`, `::test_the_live_values_start_without_any_proposals_file`; `tests/scripts/test_load_fixtures.py::test_the_loader_installs_the_four_lock_recording_beside_the_rooms_for_the_stored_fixture_room`, `::test_the_recording_is_not_installed_before_its_room_is_stored`; `tests/test_config.py::test_demo_proposals_dir_is_read_as_a_path_and_unset_leaves_the_default_folder_to_wiring`.
- Remaining gates: local scripted demo on the M1 unrun; `tests/council/test_trickster.py:280` still skips (authored.json for the real Demo room is an open 4.3 follow-up).

### D3 Hover you can feel
Decision: lane fix. Status: implemented.
- Contract: DESIGN hotspot tokens hoverStroke 3px, hoverGlow, pressedFill, labelDwell 400ms; label chip after a 400 ms hover dwell (was never on hover alone); pressed state solid lamp; "Checking" chip while a click is pending.
- Affected: Stories 1.19, 1.21, 1.25 (UX-DR23, UX-DR24); `web/src/scene/hotspots.ts`, `index.ts`, `scene.css`.
- Behavior: hover draws a 3 px lamp outline over a 5 px halo with a lamp drop shadow (150 ms, instant under reduced motion); label chip after `DWELL_MS` 400 ms, at once on keyboard focus; pressed fill solid lamp; a click shows label and "Checking" until the reply.
- Verification: 795c324. `tests/web/test_scene.py::test_hover_reveals_the_3px_outline_halo_fill_and_lamp_shadow_in_150_ms_and_the_label_after_a_400_ms_dwell`, `::test_a_pressed_hotspot_fills_solid_lamp_and_a_click_shows_checking_beside_it_until_the_reply`. Deployed in `c9d0d61`.
- Remaining gates: M1 browser pass.

### D4 The unlock moment
Decision: lane fix. Status: implemented.
- Contract: DESIGN Motion names a lock open and a Wrong attempt as glow triggers; new tokens for frame glow, bloom and chip lift; EXPERIENCE gains one Unlock aside per lock type; a Rung arriving in the same state holds the Hint area over the aside (7dabbd0). The Exit and Wrong attempt asides were later dropped by P2.
- Affected: Stories 1.20, 1.21 (UX-DR38); `web/src/lock-opened.ts`, `web/src/scene/*`, `components/hint-area.ts`, `components/wizard-notes.ts`, `fade.ts`, `strings.ts`.
- Behavior: from server states only, a newly open Puzzle blooms the last-named target Hotspot (code: frame only), the frame glows once, the chip fades in, and one client-side aside per lock type shows (not a Rung, not logged, counted or announced). Nothing plays on reload.
- Verification: 77f4f2a, 7dabbd0. `tests/web/test_unlock_moment.py`, whole file (6 collected).
- Remaining gates: M1 browser pass.

### D5 Play the sample room on every dead end
Decision: lane fix. Status: implemented.
- Contract: Hosted Capture dropzone gains "No photos handy? Play the sample room" (absent with no Demo room; Local unchanged). Narrow-screen card gains the Guide's portrait and "Copy link for your laptop", confirming "Link copied. The room will wait." or "Keyframe couldn't copy the link. It's in the address bar."; the confirmation joins the live-region writers.
- Affected: UX-DR14, UX-DR60; `web/src/capture.ts`, `components/capture-dropzone.ts`, `components/narrow-screen-message.ts`, `shell.ts`, `strings.ts`.
- Behavior: the Hosted Capture screen reads GET /rooms once; the button starts a Session on the first Demo room and is disabled with "Choose photos" while an upload is pending. The narrow card copies the page URL and confirms under the button and in the live region; no control leaves the page.
- Verification: 6cca9c2. `tests/web/test_capture.py::test_in_hosted_mode_the_dropzone_offers_the_sample_room_under_choose_photos`, `::test_the_sample_button_starts_a_session_on_the_first_demo_room_by_the_landing_s_path`; `tests/web/test_narrow_screen.py::test_copy_link_copies_this_page_s_address_and_confirms_in_the_live_region_and_under_the_button`.
- Remaining gates: M1 browser pass.

### D6 Quiet the chrome
Decision: lane fix. Status: implemented.
- Contract: the Disclosure moves from the top edge to a 32 px footer under the body; the Triggers panel opens by itself only once a row exists; the welcome role line follows the mode (Hosted ends "shown as written"). P4 later removed the Triggers panel from the default Play view.
- Affected: FR-16, FR-26; UX-DR56, UX-DR33; `web/src/shell.ts` and `.css`, `components/triggers-panel.ts`, `welcome.ts`, `components/disclosure-banner.css`.
- Behavior: the banner is a footer on every screen that shows it, without covering controls; scrolling bodies stop above it.
- Verification: 2f0d050. `tests/web/test_disclosure_banner.py::test_the_banner_is_the_footer_under_the_body_and_every_scrim_is_inside_the_body_above_it`; `tests/web/test_greeting_card.py::test_the_role_line_follows_the_mode_and_the_guide_setting`.
- Remaining gates: M1 browser pass.

### D7 The Architect reads visible attributes
Decision: lane fix. Status: implemented.
- Contract: FR-2's "readable attributes" is read as attributes a player can see (colour, material, shape, size, count, placement, readable text as written), two to four per object, each at most four words, lower case except readable text, no brand names, never a person. ArchitectResponse shape unchanged; pinned prefix hash moved.
- Affected: FR-2, Validator rule 4; `src/council/architect.py`; `tests/fixtures/providers/muse-spark-1.3/chat-architect-two-photos.json` (re-recorded live, bff6cee).
- Behavior: the instruction (`architect.py` line 38) asks for two to four short visible attributes; `validate()` passes rule 4 over drafts citing them and fails rule 4 for every Puzzle when attributes are empty.
- Verification: c78eb85, bff6cee, c812738. `tests/council/test_architect.py::test_the_instructions_ask_for_visible_descriptive_attributes_and_bound_them`, `::test_validate_passes_over_a_draft_whose_evidence_cites_a_visible_attribute`. Live: hosted job job_01M61TZ74F6F3AVVEMPRAS4V1G (deploy run 4 on bff6cee) done after 182 s, one Regeneration, 8 rules passed, Dry run reached all 4 locks blind.
- Remaining gates: none for the prompt. SIT-13 and SIT-15 from the Mac or the hosted URL remain owner items (the container proxy cuts at 30 s).

### D8 The Build view names where the Validator ran
Decision: lane fix. Status: implemented.
- Contract: the Build view Hosts list gains "this server" for the Validator in Hosted mode. Mask-overlay chips placed without overlap (no wording change).
- Affected: Story 2.28 (UX-DR53); `web/src/components/model-table.ts`, `build-view.ts`, `components/chip-layout.ts`, `components/mask-overlays.ts` and `.css`.
- Behavior: Validator "Where it ran" follows GET /meta mode; mask tiles have their own classes; chips are placed top-down at the nearest clear place with a 4 px gap. B4a later relabels the Validator "deterministic code, no model".
- Verification: 2b6f067, 3a0dd65. `tests/web/test_build_view_graph.py::test_label_chips_never_cover_each_other_and_stay_in_their_tile`; `tests/web/test_build_view_surface.py::test_the_wire_values_the_model_table_keys_on_are_the_servers`.
- Remaining gates: M1 browser pass.

### D9 The Hosted landing's attract frame
Decision: lane fix. Status: implemented.
- Contract: DESIGN Motion "Nothing loops" gains the attract frame as its one carve-out (4 s holds, 600 ms crossfade on `--motion-attract`, pauses on hover, focus and hidden tab; reduced motion shows the first photo only); EXPERIENCE copy "Play {name}", "Lock {n} of {m}", a new Attract frame state row, focus order verb, link, frame, cast. Selection rule replaced by D10, sizing by P6.
- Affected: UX-DR57; `web/src/components/attract-frame.ts` and `.css`, `landing.ts`, `scene/hotspots.ts`, `tokens.css`.
- Behavior: with a Demo room listed, a Scene-styled frame crossfades its photos from the PlayView alone (GET /rooms/<id>), draws one lit Hotspot and a clue; click or Enter starts a Session.
- Verification: cd15a3e. `tests/web/test_hosted_landing.py::test_the_photos_crossfade_on_the_attract_token_about_every_four_seconds_and_pause_on_hover_focus_and_a_hidden_tab`, `::test_the_contract_records_the_attract_frame_and_the_motion_carve_out`, `::test_the_frame_reads_the_play_view_alone`.
- Remaining gates: M1 browser pass.

### D10 The attract frame never lights a lock's object
Decision: lane fix. Status: implemented.
- Contract: the lit Hotspot is the first Interactable with polygons on the photo that no Puzzle's Evidence names (none if the photo has none); the clue comes from a Puzzle whose Evidence names nothing on that photo, preferring non-Exit, cycling so successive photos differ, with no clue line (row height kept) when every Puzzle's Evidence is on the photo; "Lock n of m" follows the clue.
- Affected: UX-DR57; `web/src/components/attract-slides.ts` (new), `attract-frame.ts`.
- Behavior: `attractSlides` builds the set of Evidence-named Interactables from the PlayView and lights only others. The frame reads the public PlayView only, so "scenery" means "named by no Evidence card"; a lock target no Evidence names would still count as scenery. On the real Demo room every lock target is an Evidence object.
- Verification: c9d0d61. `tests/web/test_hosted_landing.py::test_the_frame_never_lights_a_lock_s_object_or_pairs_a_clue_with_the_photo_that_holds_its_answer`, `::test_a_photo_holding_every_lock_s_evidence_shows_no_clue_and_the_exit_s_clue_is_the_last_choice`. Live: deployed by run 6 and checked against room_01M61TZ74F0FP3X9HHTMXGTPB9's answers; it lights no lock object.
- Remaining gates: none for the real Demo room; a future room whose lock target no Evidence cites is not covered.

### F21 The SIT's recording transport honours HTTPS_PROXY and NO_PROXY
Decision: lane fix. Status: implemented.
- Contract: Story 2.9 and AD-14: `scripts/sit.py main()` used a bare `httpx.HTTPTransport`, skipping the container's egress proxy (Meta answered 401). Now `EnvironmentTransport` routes like `httpx.Client(trust_env=True)`: via HTTPS_PROXY (HTTP_PROXY for http) unless NO_PROXY covers the host, direct when no proxy variable is set. `src/providers` untouched.
- Affected: Story 2.9; `scripts/sit.py`; sit-checklist.md run log.
- Behavior: SIT requests to api.meta.ai go through the proxy in the container and direct to NO_PROXY hosts (Ollama at 127.0.0.1).
- Verification: 53a4efd. `tests/scripts/test_sit_script.py::test_the_environment_transport_proxies_every_host_no_proxy_does_not_cover`, `::test_without_proxy_variables_every_request_goes_direct`, `::test_the_run_records_over_the_environment_transport`.
- Remaining gates: the owner's Mac SIT run (direct path) is not recorded.

### F22 Offline replay tests hold under any valid SIT recording
Decision: lane fix. Status: implemented.
- Contract: replay tests assert shape and invariants (one of the four edits naming four-lock ids, request shape, cache and ledger behavior, no leak) instead of sample content; the hand-written Riddler draft moves to `tests/fixtures/drafts/four_lock.json`; live recordings replace samples byte for byte.
- Affected: Stories 2.9, 2.20, 2.24, 4.8; `tests/council/test_trickster_live.py`, `tests/pipeline/test_author_stage.py`, `tests/pipeline/test_dryrun_stage.py`, `tests/scripts/test_sit_script.py`; recordings under `tests/fixtures/providers/`.
- Behavior: the live Trickster recording (a merge proposal) replays offline and passes; Riddler and Dry run recordings are live bodies.
- Verification: bbd5efd, 50b5bf1, 2a4dfce, 6bfd79b. `tests/council/test_trickster_live.py::test_the_recording_is_one_of_the_four_edits_naming_only_ids_the_four_lock_room_has`, `::test_on_meta_the_one_request_goes_to_muse_spark_1_3_at_low_with_the_proposal_schema`.
- Remaining gates: Fireworks fallback recording not made (`tests/api/test_live_trickster_route.py:330` skips); SIT-05 and SIT-11 not run.

### F23 The fixture scenes draw the code-puzzle evidence
Decision: lane fix. Status: implemented.
- Contract: `tests/fixtures/rooms.py`: the clock scene draws a face stopped at a quarter past four; the door scene draws "7 3 4 2" in brass above the door. Scene count, size, format, clues, rungs, solutions and the Dry run prompt contract unchanged.
- Affected: fixture rooms, Story 2.24, SIT-14; `tests/fixtures/rooms.py`, `tests/fixtures/test_rooms.py`.
- Behavior: live SIT-14 reached 5 of 5 after this (3 of 5 before), per the sit-checklist run log.
- Verification: d5ad217. `tests/fixtures/test_rooms.py::test_code_scenes_draw_the_evidence_the_clues_point_at`.
- Remaining gates: none.

### P1 A three-step how-to-play and copy about the player
Decision: lane fix. Status: implemented, not deployed.
- Contract: Guide voice line "Ask as often as you like. I'll help, a little at a time."; Hosted tagline names no lock count; "How a room is built" step 2 "writes {n} locks" from the first Demo room ("writes the locks" with none); both welcome lines replace "Find what doesn't belong" with "Read a riddle, then click the thing it means."; the First-room welcome gains the numbered three steps; UJ-1 step 5 and UJ-5 step 3 follow.
- Affected: UX-DR45, UX-DR74, UX-DR57; `src/api/app.py` (DEMO_ROOM_WELCOME, FIRST_ROOM_WELCOME), `web/src/components/greeting-overlay.ts`, `landing.ts`, `welcome.ts`, `strings.ts`.
- Behavior: every Hosted welcome card shows the three steps between the served line and the voice line; a returning player's Greeting does not.
- Verification: e2a7fc1, 055bf88. `tests/web/test_hosted_landing.py::test_the_landing_strings_are_the_experience_lines`, `::test_how_a_room_is_built_is_three_steps_naming_the_wizards_and_the_models`.
- Remaining gates: redeploy. C1 (step 1 wording "on the right") is a separate, unlanded item. M1 browser pass and playtester results are the owner's.

### P2 Every click answers
Decision: lane fix. Status: implemented, not deployed.
- Contract: a Feedback line (parchment strip with the Guide's 32 px portrait over the bottom of the Scene frame, held 2.5 s, written once to the live region as "The Guide: {line}"): "{label}. Not this one.", "{label} · in hand", "You pick up the {label}." then "Puzzle {n} solved.", Exit "The way out is open.", wrong code, order or use_on "Puzzle {n}: not this, {count}.". The "Open" chip becomes "Solved"; the Exit and Wrong attempt asides are dropped; the Inventory slot glows once on a pickup.
- Affected: UX-DR38, UX-DR27, NFR-14, Story 1.21; `web/src/feedback.ts` (new), `components/feedback-line.ts` and `.css`, `play.ts`, `lock-outcomes.ts` (removed), `components/inventory.ts`, `components/wizard-notes.ts`.
- Behavior: `feedbackFor(room, input, before, after)` picks one line per reply. Every click on a Hotspot answers except an armed order click; order start and stop and Hint requests read no line; a click off every Hotspot posts nothing. As shipped in ad598f0, every solved find target entered the Inventory, so solving a fixed object read "You pick up the {label}. Puzzle {n} solved."; since I1 (d4e1a1c) a target no use_on needs reads "Puzzle {n} solved." alone.
- Verification: ad598f0. `tests/web/test_feedback_line.py`, whole file (8 collected, I1's test included).
- Remaining gates: redeploy. M1 browser pass and playtest replay are the owner's.

### P3 Evidence cards stop handing over the answer
Decision: lane fix. Status: implemented, not deployed.
- Contract: was UX-DR39, one state with 64 px crop, label and attribute beside the Clue. Now an unsolved Puzzle's card shows only the attribute as "The Riddler's note"; the whole card fades in (200 ms on `--motion-state`) when the lock is solved. Decoy cards follow the same rule. PlayView unchanged.
- Affected: UX-DR39, Stories 1.20, 4.6; `web/src/components/evidence-card.ts` and `.css`, `wizard-notes.ts`, `landing.ts`, `strings.ts` (riddlerNote).
- Behavior: `evidenceCard(roomId, interactable, evidence, solved)` returns only the filled note when not solved. The landing's sample page shows notes only.
- Verification: 4d05acb. `tests/web/test_play.py::test_an_unsolved_puzzle_s_evidence_card_is_the_riddler_s_note_alone_and_the_solved_one_names_the_object`, `::test_evidence_cards_are_inset_rows_a_note_until_solved_then_a_64px_crop_cut_from_the_polygons_bounds`.
- Remaining gates: redeploy; M1 browser pass.

### P4 Asking the Guide always gets a hint
Decision: lane fix (owner decision Oct 29, approved in 65c8bac as an FR-15/16 change). Status: partial (code done; FR-15/16 text in epics and spine AD-4 not edited); not deployed.
- Contract: a hint_request for the Active puzzle opens the next Rung at once when none is showing; when one is showing it opens the next once the Rung spacing (RUNG_SPACING_MS 90 s, divided by the timescale) has passed since that Puzzle's last Rung change, else repeats the current Rung with a countdown. Nothing follows the near-answer. The request still counts as a hint used, and an ask with no Rung showing is still an Early ask. HintReply gains `next_hint_ms`. The No-hint line answers only once no Puzzle is active. UI: one primary button "Get a hint for Puzzle {n}", "The Guide is thinking" while pending, "Next hint in m:ss" when not due; the Triggers toggle becomes a "How hints work" panel; `#/triggers` keeps the content. 65c8bac edited only EXPERIENCE.md and DESIGN.md; spine AD-4 and epics still state the old rule.
- Affected: FR-14, FR-15, FR-16; Stories 3.1, 3.3, 3.4, 3.5 (UX-DR30, UX-DR32, UX-DR33); AD-4; HintReply; `src/domain/rungs.py`, `src/domain/session.py`, `src/api/app.py`, `web/src/components/hint-area.ts`, `triggers-panel.ts`, `web/types/*`.
- Behavior: `select_rung(..., asked=True)` returns RungStep(next) when no Rung is open or the spacing has passed, else None (repeat). `SessionStateMachine.next_hint_ms` gives the wait from the log alone, so replay equals live. 4ae3dca: an asked-for Rung is announced once and never glows.
- Verification: 65c8bac, 4ae3dca. `tests/domain/test_rungs.py::test_an_ask_with_no_rung_showing_opens_the_nudge_on_the_active_puzzle_at_once`, `::test_an_ask_inside_the_spacing_repeats_the_rung_and_reports_the_wait_and_past_it_opens_the_next`, `::test_asks_replay_to_exactly_the_rungs_appended_live`; `tests/web/test_hint_area.py::test_the_label_names_the_active_puzzle_and_counts_down_the_servers_wait`, `::test_no_triggers_or_nudge_after_text_in_the_default_play_view`; `tests/api/test_hints.py::test_ten_hint_requests_inside_the_spacing_at_rung_2_each_answer_the_direction_and_the_wait_then_one_opens_the_next`.
- Remaining gates: redeploy; M1 browser pass; no live playtest of the new rule. SM-C2 in uat-signoff.md section 3 is worded against the old rule; the owner re-reads it before signing. Docs edit in section 6.

### P5 Thumbnails count their objects and the notes follow the puzzle
Decision: lane fix. Status: implemented, not deployed.
- Contract: Thumbnail strip gains an object count badge ("{k} objects", "1 object", "no objects"); a photo with none is dimmed to 50% unless current; counts follow the Effective room. The notes sheet scrolls to the Current entry when active_puzzle_id moves, without moving focus.
- Affected: UX-DR25, UX-DR27; `web/src/components/thumbnail-strip.ts` and `.css`, `wizard-notes.ts`, `scene/index.ts`.
- Behavior: each thumbnail carries a count badge (accessible description); the sheet scrolls after the Solved hold, never taking focus. "Show all objects" tip unchanged. The floor-vent outline offset was traced to mask data (box-rectangle fallback), fixed by S1.
- Verification: 1eb9f51. `tests/web/test_play.py::test_the_sheet_scrolls_to_the_current_entry_when_active_puzzle_id_moves_without_taking_focus`.
- Remaining gates: redeploy. The live Demo room keeps the box rectangle for the floor vent and four other small objects until rebuilt after S1.

### P6 The landing fills the screen with the game
Decision: lane fix. Status: implemented, not deployed.
- Contract: new "How to play" row (the welcome's three steps); Demo room card "Play this room"; stage beside the frame, card in the right column under the Access-code build, cast and steps below the fold; the card has two Tab stops and is not itself one; frame sized to its first photo's aspect via `--attract-aspect`.
- Affected: UX-DR57, UX-DR58; `web/src/landing.ts` and `.css`, `components/attract-frame.ts` and `.css`, `components/demo-room-card.ts` and `.css`.
- Behavior: above the fold at 1440x900, 1536x864 and 1920x1080: pitch, verb, attract frame, clue and How to play beside it, Demo room card under the access-code card; cast, sample page and "How a room is built" below. No-Demo-room state unchanged.
- Verification: e4fe83b. `tests/web/test_hosted_landing.py::test_the_attract_frame_takes_its_photos_aspect_so_a_portrait_room_shows_no_wide_bars`, `::test_with_a_demo_room_listed_how_to_play_sits_beside_the_attract_frame_in_the_welcome_s_three_steps`, `::test_play_this_room_or_a_click_on_the_card_starts_a_session_and_the_link_does_not`.
- Remaining gates: redeploy. Above-the-fold layout at each size is a browser check; none recorded.

### T7 The Completion screen
Decision: lane fix. Status: implemented, not deployed.
- Contract: Completion copy ("Copy your result", shared line, copied confirmation, "Built by", filmstrip name); confirmation joins the live-region writers; stats final at once under reduced motion; DESIGN `scrim-soft #0A080680`, completion-sheet tokens, one-time count-up on `--motion-count` (800 ms; 0 under reduced motion).
- Affected: UX-DR44, UX-DR66; `web/src/completion.ts` and `.css`, `completion-line.ts`, `components/filmstrip.ts` and `.css`, `tokens.css`.
- Behavior: soft scrim; stats count up once; the filmstrip lights solved objects' outlines (final Inventory plus unlock targets seen this page); Built by row with 32 px portraits; "Copy your result" copies "Keyframe - {room} - {n} locks - m:ss - {h} hints - {w} wrong - <url>" and confirms; no solution text.
- Verification: 9801e6a. `tests/web/test_completion.py`, whole file (24 collected).
- Remaining gates: redeploy; M1 browser pass.

### B4a Player wording everywhere (items 62, 66, 70, 71, 72)
Decision: 62 Approve ordinary copy / fix defects; 66 Keep simple flow / fix feedback; 70 Keep role / make claims exact; 71 Approve after focused check; 72 Use durable room truth. Status: implemented, not deployed.
- Contract: Capture ("1 photo chosen"; Timer "Waiting to build", "Build stopped", "Add more photos", "Try clearer photos"; "1 puzzle"; Validator "deterministic code, no model"); Hosted landing ("{n} locks" / "1 lock"; card meta "{puzzles} · 15 to 25 min"; "Checking code…"; "We couldn't check the code. Try again."; "That code doesn't open anything."; count is the server's builds_left); Build view dates in ET; earlier-builds Disclosure from Room provenance only; new "Replay: this room has been played before." in Play only.
- Affected: UX-DR17, UX-DR59, UX-DR53, UX-DR79; `src/api/app.py`, `src/api/meta.py`, `web/src/access-code.ts`, `capture-timer.ts`, `components/model-table.ts`, `components/build-view-header.ts`, `strings.ts`.
- Behavior: the access check shows pending and tells a wrong code (also 403 on Upload) from no answer or 5xx; the tab re-asks POST /access/check on re-entry instead of decrementing its own count; no raw status reaches the player; build times format Room.created in ET; Muse Image row reads one-time portrait generation; Validator "checked 8 rules" only when verdicts are recorded; Build view no longer reads the session store.
- Verification: 18ec75a. `tests/web/test_player_wording.py`, whole file (8 collected).
- Remaining gates: redeploy; M1 browser pass.

### B4b Play never blanks (items 27, 48, 54, 64, 67)
Decision: 27 Fix; 48 Keep subject to consent; 54 Fix; 64 Change presentation; 67 Fix. Status: implemented, not deployed.
- Contract: decision 27/48 reverses part of F17: under cut 2 the profile file is neither read nor written before "Open profile file"; results stay in the page and "Save profile file" downloads them. Opening merges the file's results with this page's (a demo result never replaces a counted one) and writes a changed merge back. EXPERIENCE.md and DESIGN.md were edited in the same commit: Cut 2 placeholder, the new Capture, Play and Completion strings, the Mask preview and Completion screen rows, the Capture cold load, Build status done, Play Error, Completion Not saved and Temporary profile states, Privacy and Retention, the Capture screen layout, Stage list row, Scene frame state and a new Profile name refused row. Landed in 1e8578a, after the rest of this record was checked.
- Affected: Stories 5.1, 5.2, 5.4, 2.18, 1.17; `web/src/profile/file.ts`, `web/src/profile/index.ts`, `web/src/completion.ts` and `.css`, `web/src/capture.ts`, `build-progress.ts`, `build-stages.ts`, `components/stage-list.ts`, `play.ts`, `scene/index.ts`.
- Behavior, per the commit: a Room result is recorded once per Session, and this page load's Sessions are ordered by id, so remounting `#/done/<id>` records nothing and an older Session's Done page never replaces a newer result. A Done page not reached from the Exit in this page load fills a Room the profile lacks but never replaces a stored or opened result (54). An IndexedDB that throws, will not open or refuses a write moves the profile to memory, marked temporary, and the sheet says the progress lasts until the page closes (54). A failed file write keeps the result and shows "Progress is still here, but the profile file wasn't saved. Try again." with "Try again" (27, 48). A 422 invalid_profile_name from GET /meta stops the retry loop and offers "Use the dev profile" (67). A WebGL renderer that fails to start leaves an error banner with "Reload" in the Scene frame (67). "Finding objects" keeps the found-objects line from the first poll with the Mask preview, and the done Build's actions sit above the Stage list, so "Play this room" is in view at 1024 x 768 (64).
- Verification: 1e8578a. `tests/web/test_profile_file.py::test_until_a_file_is_opened_the_profile_lives_in_the_page_and_nothing_is_read_or_written`, `::test_saving_before_a_file_is_opened_writes_nothing`, `::test_opening_merges_the_files_results_with_the_ones_this_page_recorded`, `::test_a_failed_save_keeps_the_result_in_the_page_and_try_again_writes_it`; `tests/web/test_player_profile.py::test_a_completion_is_recorded_once_per_session`, `::test_reopening_an_older_sessions_done_page_never_overwrites_a_newer_result`; `tests/web/test_profile_indexeddb.py::test_a_failing_database_keeps_play_going_in_memory_with_its_temporary_notice`; `tests/web/test_shell.py::test_a_profile_name_the_server_refuses_stops_the_retry_loop_and_offers_the_dev_profile`; `tests/web/test_scene.py::test_a_browser_without_webgl_gets_an_actionable_error_in_the_frame_never_a_blank_page`; `tests/web/test_build_progress.py::test_the_found_objects_line_stays_on_finding_objects_from_the_first_poll_with_the_preview_on`; `tests/web/test_completion.py::test_the_result_is_recorded_once_per_session_and_a_failed_save_or_temporary_profile_says_so`. All pass.
- Remaining gates: redeploy; a local-mode browser check of the profile file; the 1024 x 768 Build screen and the WebGL failure banner in a real browser; the M1 browser pass. epics Stories 5.1, 5.2, 5.4, 2.18 and 1.17 have not been compared with 1e8578a in this record.

### B1 The Retention summary states verified provider facts (items 1, 31)
Decision: 1 Change / verify; 31 Reconcile. Status: partial (code done; the provider and account facts decision 1 asks to verify are unverified); not deployed.
- Contract: EXPERIENCE Privacy and retention, UJ Priya step 4 (deletion "scheduled for" Tue Nov 10), mode differences row, Q3 settled; DESIGN policy URLs as lamp links; spine AD-8 (summary composed from Settings, fal never named).
- Affected: FR-6, Story 1.14 (UX-DR20, UX-DR79); AD-8; `src/api/meta.py` (`retention_summary`), `web/src/components/retention-summary.ts`.
- Behavior: Meta Standard service (no training, retention for operation, security, safety and policy review, not zero retention); the Baseten/Fireworks sentence and Baseten link only when a role's provider is openai_compatible; Local: profile and room files stay until deleted; Hosted: photos and room on the hosted volume, scheduled for deletion after judging, sessions deleted 24 h after the last move; then Meta terms and ZDR links. The faces and documents reminder stays a separate Capture line.
- Verification: 85a4afa. `tests/api/test_meta.py::test_retention_states_only_verified_facts`, `::test_the_fallback_is_named_only_when_settings_switch_a_role_to_it`, `::test_the_hosted_retention_summary_replaces_the_local_storage_sentence`.
- Remaining gates: redeploy (the live site serves pre-B1 text). Hosted purge unverified live (hence "scheduled"); session sweep Cron registration unverified live (decision 19). Provider and account facts behind the wording (Standard tier, no ZDR enablement, whether a Baseten fallback is configured) are the owner's.

### B2 Game rules (items 22, 28, 29, 30, 68)
Decision: 22 Fix now; 28 Choose order-only; 29 Fix naming and scope; 30 Close on completion; 68 Accept deterministic order. Status: implemented, not deployed.
- Contract: spine AD-4 (find is a click made while no order sequence is armed; opening the Exit closes any open window and none follows); AD-12 (rules 1 to 8 are base build checks; a validate_edit refusal carries edit_bounds, never a rule number; `BOUNDS_RULE` replaced by `EDIT_BOUNDS`); EXPERIENCE edit_bounds row, verdict caption, rule 9 "not applicable", notes in Room order, announced never focused ("Puzzle {n} is now in the notes."). The Dry run prompt adds each Puzzle's lock_type (SHA-256 pin 75108eec..., was 0fcb60a0...), invalidating old cached Dry run entries.
- Affected: Stories 1.8, 1.9, 1.21, 2.23, 4.1, 4.2 (UX-DR27); AD-4, AD-12; `src/domain/session.py`, `validator.py`, `edits.py`, `schema.py`, `src/council/dryrun.py`, `src/api/app.py`, `web/src/components/verdict-table.ts`, `wizard-notes.ts`.
- Behavior: an armed click fills only the order buffer; Exit open closes the window with no card or call; the Dry run prompt names lock types, no solutions; the verdict table shows rule 9 apart; notes in `Room.puzzles` order, a newly available entry announced once, focus never moved to it.
- Verification: 5863a59. `tests/domain/test_session.py::test_an_armed_click_on_a_find_target_belongs_only_to_the_order_attempt`; `tests/domain/test_trickster_windows.py::test_opening_the_exit_closes_a_window_still_open_and_no_window_opens_after`; `tests/api/test_trickster_route.py::test_a_window_still_open_when_the_exit_opens_closes_and_never_calls_the_source`; `tests/council/test_dryrun.py::test_the_prompt_is_pinned_so_a_change_to_it_is_seen_as_a_new_cache_key`; `tests/domain/test_edits.py::test_bounds_refusals_carry_the_named_edit_bounds_category_and_never_a_rule_number`; `tests/web/test_build_view_verification.py::test_rule_9_shows_apart_as_not_applicable_and_the_rules_line_counts_the_base_checks_only`; `tests/web/test_play.py::test_the_wizard_notes_draw_one_entry_per_available_puzzle_in_room_order`.
- Remaining gates: redeploy. The changed Dry run prompt has not run live (the committed recording is not keyed by prompt).

### B3 API correctness (items 24, 35, 37, 56, 58, 61, 63)
Decision: 24 Change conservatively; 35 Accept narrow imports / fix purity; 37 Document / correct wrong status; 56 Fix; 58 Fix before deletion promise; 61 Keep instances / fix construction; 63 Fix. Status: partial (items 35 and 37 stay partial in their own entries: pipeline id minting, echoed dict keys); not deployed.
- Contract: spine AD-1 (pure domain clock), AD-5 (paid adapters built on first call, not_configured refusal, chat ledger tags include session_id), AD-6 (zero settlement for a call never sent; estimator skips zero-cost settlements), AD-9 (deletion record carries session_ids; session routes 410 room_deleted), AD-13 (409 on /room, 404 job_not_found, 422 invalid_request never echoing a value), HTTP surface row; EXPERIENCE Deleted Judge room notice for a session route's 410.
- Affected: Stories 1.12, 2.3, 2.4, 2.12, 4.8, 6.2, 7.15, 7.21; AD-1, AD-5, AD-6, AD-9, AD-13; `src/api/app.py`, `errors.py`, `meta.py`, `wiring.py`, `src/providers/lazy.py` (new), `cache.py`, `spend.py`, `src/domain/ledger.py`, `src/infra/modal.py`, `web/src/shell.ts`, `completion.ts`.
- Behavior: unfinished job /room answers 409 with status; session routes answer 410 for Sessions a deletion took and 404 for unknown; the earlier-builds line keys on `ArtifactStore.is_demo_room`; `LazyProvider` builds paid adapters on first call, so a keyless checkout plays; a call proven never sent settles at 0 USD with its entry kept, timeouts keep the estimate; 72d6bfb stops 422 messages echoing a sent tag, extra key or value (dict keys still echo, item 37).
- Verification: b161d99, 72d6bfb. `tests/api/test_builds.py::test_the_room_route_answers_409_build_not_ready_with_the_status_until_the_job_is_done`; `tests/api/test_room_deleted.py::test_every_session_route_of_a_session_still_open_on_a_deleted_judge_room_answers_410`, `::test_an_unknown_session_stays_404_session_not_found_beside_a_deletion_record`; `tests/api/test_room_disclosure.py::test_a_named_room_the_store_calls_no_demo_room_gets_no_earlier_builds_line_from_its_name`; `tests/api/test_keyless.py::test_a_keyless_checkout_starts_and_plays_a_stored_room_with_no_paid_adapter_built`, `::test_a_live_trickster_windows_ledger_entry_names_its_session`; `tests/providers/test_cache.py::test_a_provider_error_settles_at_zero_only_when_the_call_never_left`; `tests/domain/test_ledger.py::test_a_zero_cost_settlement_never_seeds_the_estimate`; `tests/test_boundaries.py::test_no_domain_module_reads_the_wall_clock_or_mints_an_id`; `tests/api/test_hints.py::test_a_refused_body_is_never_echoed_in_the_message`.
- Remaining gates: redeploy. Bookmarked Play and Done paths after a real hosted deletion not verified live (needs the purge run).

### B5 Hosted reliability before more judge uploads (items 9, 18, 23, 57)
Decision: 9 Fix; 18 Verify before uploads; 23 Same as 18; 57 Fix before uploads. Status: partial.
- Contract: spine AD-7 (any terminal status other than done also writes its final record beside the Room on the Volume; the Demo copy holds no originals; each photo's original_path names its downscaled key; every referenced file checked before upload); AD-9 (slot atomicity verified by `quota_probe.py` via the ops action on an ephemeral Dict; the purge finishes a lingering deletion from its record before any stale job entry); ops.yml gains quota-probe.
- Affected: Stories 7.7, 7.10, 7.13, 7.14, 7.18, 7.20; AD-7, AD-9; `src/infra/modal.py`, `scripts/seed_rooms.py`, `promote_room.py`, `purge_judge_rooms.py`, `quota_probe.py` (new), the ops workflow.
- Behavior: items 57, 9, 23 and the atomicity half of 18 are implemented. Decision 18 also asks that claims be preserved through judging so Dict expiry cannot replenish the quota; `src/infra/modal.py` (lines 36-40) still says a slot key can expire after 7 idle days, and `reserve_build` and `builds_left` count Dict slot keys only. The live Demo room was promoted by ops run 1 (head c032b61, before 69c269a), so its stored original_path values come from the old promote script until it is re-promoted.
- Verification: 69c269a. `tests/infra/test_modal_runner.py::test_every_terminal_record_reaches_the_volume_so_lookup_outlives_the_dict_entry`; `tests/infra/test_modal_retention.py::test_a_rerun_reads_the_deletion_record_before_a_stale_job_entry_and_pops_it`; `tests/scripts/test_purge_judge_rooms.py::test_a_deletion_whose_job_keys_lingered_is_finished_from_its_record_before_the_stale_job_entry`; `tests/scripts/test_seed_rooms.py::test_every_asset_the_seeded_room_references_is_a_file_in_its_demo_folder_and_no_original_is_copied`; `tests/scripts/test_promote_room.py::test_every_asset_the_promoted_room_references_is_a_file_in_its_demo_folder`; `tests/scripts/test_quota_probe.py::test_a_claim_that_is_not_atomic_fails_both_races_and_exits_1`; `tests/test_ops_workflow.py::test_the_quota_probe_runs_from_a_dispatch_or_a_request_file_on_an_ephemeral_dict_only`. Live: GitHub run 40821411610, quota probe passed.
- Remaining gates: slot expiry over the judging period; re-promotion of the live Demo room with the 69c269a script; a full dev-room purge and failed-job lookup after Dict expiry, live; redeploy.

### S1 Small objects keep their SAM outline
Decision: lane fix. Status: implemented, not deployed.
- Contract: departure from schema-v1 "masks under 1% of the image are dropped" (also epics FR-3 and the spine's "1% and 12 caps"): a mask is dropped only when under 1% of the frame and under `MIN_BOX_FRACTION` 0.1 of its own box, i.e. `min_area = min(MIN_AREA_FRACTION * frame_w * frame_h, MIN_BOX_FRACTION * box_area)`. Every other rule unchanged (best IoU singular, IoU above 0.2 plural with best-mask fallback, box rectangle when nothing survives, simplify and clamp, cap 12, MIN_INTERACTABLES 5). schema-v1.md and the spine left unedited by design; the commit body records the departure.
- Affected: FR-3, schema-v1 Interactable polygons, AD-7 segment rule; `src/domain/masks.py`, `tests/domain/test_masks.py`, `tests/pipeline/test_segment_stage.py`.
- Behavior: `masks.py` line 167 computes min_area as stated. A floor-vent-shaped case keeps the SAM polygon; a speck under both floors falls back to the box.
- Verification: 42d3253, now origin/master (it was not an ancestor of master when first checked). `tests/domain/test_masks.py::test_a_small_object_like_the_floor_vent_keeps_its_sam_outline_offset_from_its_box`, `::test_a_mask_under_one_percent_of_the_frame_but_over_a_tenth_of_its_small_box_is_kept`, `::test_a_speck_under_both_floors_is_dropped_and_the_box_stands_in`, `::test_a_mask_under_a_tenth_of_a_large_box_and_under_one_percent_of_the_frame_is_dropped`.
- Remaining gates: redeploy. The real Demo room room_01M61TZ74F0FP3X9HHTMXGTPB9 keeps box rectangles for five small objects (ceiling light fixture, wall clock, floor vent, throw pillows, tray) until a new live Build and re-promotion; no live Build has exercised the new floor.

### I1 Only objects a later puzzle uses go into the Inventory
Decision: lane fix. Status: implemented, not deployed.
- Contract: departure from schema-v1 line 29 ("solving a `find` puzzle moves its interactable into the inventory") and epics FR-12 (line 42, "solving a `find` Puzzle visibly moves its Interactable into the Inventory"). Now a solved find moves its target into the Inventory only when a use_on Puzzle of the Effective room names it as its item. Any other target is found, not carried: its lock opens and nothing enters the hand. Validator rule 8 and the use_on refusal of an item not carried are unchanged. EXPERIENCE.md gains a found-target Voice and Tone row ("{label} · found") and updates the Feedback line, Hotspot, Inventory and Completion screen rows. Schema and PlayView unchanged.
- Affected: FR-12, Story 1.21 (its find AC at epics line 1341: the target's "item fades into the Inventory"), UX-DR26; AD-4 (`SessionStateMachine.apply` is the sole writer of `inventory`); `src/domain/session.py`, `web/src/feedback.ts`, `play.ts`, `scene/hotspots.ts`, `scene/index.ts`, `strings.ts`.
- Behavior: the Session engine applies the rule after every event, an accepted Trickster edit included. Every open find target a use_on names is held, in lock order; nothing held leaves; replay gives the same Inventory. On the real Demo room the floor vent and the Exit's front door are found, not carried. When nothing is carried, Play reads "Puzzle {n} solved." with no pickup clause. A found target's Hotspot settles like a collected one, and a later click reads "{label} · found" on the chip and in the feedback line. f330810 keeps the found and bloomed targets in sessionStorage per session id (`keyframe-found:`, `keyframe-solved:`), falling back to memory when storage refuses, so they survive a reload and the Completion filmstrip still lights every solved target.
- Verification: d4e1a1c, f330810. `tests/domain/test_session.py::test_a_find_target_a_later_use_on_needs_is_carried_in_the_inventory`, `::test_a_find_target_no_use_on_needs_is_found_its_lock_opens_and_nothing_is_carried`, `::test_the_exit_find_is_found_never_carried_and_replay_reproduces_the_inventory`; `tests/domain/test_edits.py::test_after_every_accepted_edit_each_open_find_target_a_use_on_names_is_carried_and_nothing_held_leaves`; `tests/web/test_feedback_line.py::test_a_find_that_carries_nothing_is_found_and_every_other_reply_finds_nothing`; `tests/web/test_locks.py::test_a_found_target_no_use_on_needs_settles_like_a_collected_one_and_answers_found`, `::test_found_and_solved_targets_outlive_a_reload_of_the_tab`. All pass. CI green on f330810 (runs 40827276075, 40826918938).
- Remaining gates: redeploy; M1 browser pass. schema-v1 and epics FR-12 not edited (section 6).

## 6 Documentation that lags

### 6.1 Documentation entries

#### 39 SVG hotspots, Tier 1 kept
Decision: Keep Tier 1 SVG (amend the spine). Status: partial.
- Contract: spine AD-11 (line 107): "Tier 1 scenes are Three.js textured planes with polygon hotspots in the scene graph Tier 2 reuses". The decision: the polygon data and ids are reusable, not the SVG elements; build raycast meshes only if the Tier 2 gate opens.
- Affected: AD-11, Stories 1.19, 2.30, NFR-10, SIT-12; `web/src/scene/index.ts`, `hotspots.ts`.
- Behavior: each photo is a Three.js `Mesh(PlaneGeometry)` texture under an OrthographicCamera; Hotspots are an SVG overlay (viewBox in stored-JPEG pixels, one `<g role=button id=interactable.id>` per Interactable). No hotspot meshes, no Raycaster.
- Verification: c6b06e5. `tests/web/test_scene.py::test_each_photo_is_a_textured_plane_drawn_as_served_and_contained`, `::test_a_hotspot_is_the_union_of_its_polygons_in_photo_pixels_with_the_interactable_id`.
- Remaining gates: Tier 2 gate (story 8.1, UAT-15) unrun and backlog.

#### epics-1.14 Story 1.14 (GET /meta, /schema, /rooms)
Decision: Record (items 1 and 31 retention, 53 and 73 complete-room catalog, 72 durable disclosure). Status: open.
- Contract: epics Story 1.14 (line 1028 on): `mode` constant "local"; Disclosure lines only timescale and scripted or cut1; Local retention names the Meta standard tier, the Baseten or Fireworks fallback, the faces request and "A copy of your photos is also kept on this computer."; GET /api/rooms returns one RoomSummary per stored Room. Meta and RoomSummary fields match exactly.
- Affected: Stories 1.14, 7.2, 7.14; UX-DR20; Meta, RoomSummary; `src/api/meta.py`, `src/api/app.py`.
- Behavior: `mode` comes from Settings.mode. `disclosure_lines()` adds the Hosted line "Hosted mode: hints are shown as written; no hint model runs here."; a Room-scoped list adds "This room was built earlier, on {date}." (Room.created in ET) when `is_demo_room` or a job call was cached, otherwise "Replay: this room has been played before.". `retention_summary()` is as in B1; the sentence "A copy of your photos is also kept on this computer." no longer exists. GET /api/meta?profile= refuses names the profile routes refuse. GET /api/rooms lists only Rooms a parseable job record names; an unparseable record is logged as job_unreadable and skipped (lane F14, a349def); a Room with no job record is omitted silently; no tool reports such folders (item 73 part open). In Hosted mode the list is Demo rooms only.
- Verification: 85a4afa, a349def (F14), 99eff19. `tests/api/test_meta.py::test_meta_reads_the_mode_from_settings`, `::test_hosted_meta_reports_verbatim_with_no_guide_model_and_the_hosted_line`, `::test_meta_refuses_a_profile_name_the_profile_routes_refuse`, `::test_the_hosted_retention_summary_replaces_the_local_storage_sentence`, `::test_the_local_retention_summary`, `::test_rooms_lists_one_summary_per_stored_room_newest_first`, `::test_a_stored_room_without_a_job_record_is_not_listed`, `::test_one_job_record_that_does_not_parse_is_skipped_and_every_other_room_is_still_listed` (F14), `::test_a_hosted_final_record_that_does_not_parse_is_skipped_and_the_demo_room_is_still_listed` (F14).
- Remaining gates: the live site serves pre-B1 retention text until redeploy. Provider and account facts are the owner's.

#### epics-7.16 Story 7.16 hosted landing
Decision: Record (D1, D6, D9, P1, P6; item 70). Status: open.
- Contract: epics Story 7.16 (line 4830), UX-DR57, UX-DR58, UX-DR68: Disclosure at the top; "Keyframe" title block, subtitle, pipeline line and "Short on time?" lead-in; cards three across; no separate band of wizards; initial focus on the first card; empty list "No demo rooms are open right now. You can still build your own room with the access code."
- Affected: Story 7.16; UX-DR57, UX-DR58, UX-DR68, UX-DR75; `web/src/landing.ts`, `components/demo-room-card.ts`, `components/attract-frame.ts`, `shell.ts`.
- Behavior: h1 "An escape room built from your own photos." (wordmark only in the top bar); tagline "Snap a room. Four wizards hide riddles in your photos, and you play by clicking the objects they point at."; primary verb "Play the sample room" and secondary "How a room is built"; attract frame and "How to play"; cast of four 96 px wizards; sample page and three steps with the lock count from puzzle_count; first card under the Access-code build, others three across; "Play this room" button; focus on the verb. Empty list: "The sample room opens soon.", verb "Build your own room". Failed load: "Keyframe couldn't load the demo rooms." with Try again. Banner is a footer. Thumbnail and cut 0 omissions match the AC.
- Verification: 68b5842, cd15a3e, e2a7fc1, e4fe83b, 2f0d050. `tests/web/test_hosted_landing.py`, whole file (39 collected).
- Remaining gates: live URL lacks P1 and P6 until redeploy. Story 7.16 browser AC (Chrome, Safari, Firefox at 1280+, keyboard, contrast) is UAT-14, owner, hosted URL. EXPERIENCE.md already matches.

#### epics-UX-DR23-24 Hotspot and label chip rows
Decision: Record (D3, D4, P2). Status: open.
- Contract: UX-DR23 (line 146): 2 px hover outline, label chip only on a non-target click. UX-DR24 (line 147): chip "never shown on hover alone". Story 1.19 hover AC: "2 px ... shows no label".
- Affected: UX-DR23, UX-DR24, Stories 1.19, 1.21; `web/src/scene/hotspots.ts`, `scene.css`, `web/src/feedback.ts`.
- Behavior: as D3, D4 and P2: 3 px outline over a 5 px halo, 400 ms dwell chip, instant on `:focus-visible`, pressed solid lamp, "Checking…" while pending, bloom on solve, "{label}. Not this one." on a non-target click. Hotspot structure, Show-all and "{label} · in hand" match. EXPERIENCE.md and DESIGN.md already reconciled.
- Verification: 795c324, 77f4f2a, ad598f0. `tests/web/test_scene.py`, whole file (18 collected).
- Remaining gates: keyboard and focus at 1024, 1280 and 1440 on the M1 (item 16).

#### epics-live-region-1480 Live-region lock outcome
Decision: Record (P2). Status: open.
- Contract: epics line 1480 (Story 1.25) and UX-DR70 (line 193): the polite region receives "Puzzle {n}: not this, {count}." and "Puzzle {n}: open."; UX-DR34 "open shows the Open chip".
- Affected: Story 1.25; UX-DR70, UX-DR34; `web/src/feedback.ts`, `play.ts`, `components/wizard-notes.ts`, `completion.ts`.
- Behavior: one line per reply, announced as "The Guide: {line}": "Puzzle {n} solved." (with "You pick up the {label}." when an item was added), "The way out is open.", "Puzzle {n}: not this, {count}.", "{label}. Not this one.", "{label} · in hand". No "Puzzle {n}: open." string exists in `web/src`; the chip reads "Solved". The region also receives "Puzzle {n} is now in the notes.", copy confirmations and every hint reply. EXPERIENCE.md matches.
- Verification: ad598f0. `tests/web/test_feedback_line.py::test_each_reply_reads_one_line_per_outcome`, `::test_the_line_is_chosen_once_per_reply_and_written_once_to_the_live_region`.
- Remaining gates: no screen-reader pass; UAT-11, owner, M1.

#### epics-oct29-rows Other epics rows changed on Oct 29
Decision: Record (P3, P4, T7, D6). Status: open.
- Contract: epics.md last changed in 5f0a351, before every Oct 29 UX fix. Stale rows: UX-DR32 (hint field, "Ask the Guide", helper line, "Asking"), UX-DR33 ("Triggers ({n})" auto-opening), UX-DR39 (evidence card one state), UX-DR40 (focus to "the hint field"), UX-DR44 (Completion without count-up, filmstrip, Built by, copy), Story 3.4 hint-area ACs (line 2910 on).
- Affected: UX-DR32, UX-DR33, UX-DR39, UX-DR40, UX-DR44, UX-DR75; Stories 3.4, 3.5, 1.20, the Completion story (line 1398); `web/src/components/hint-area.ts`, `evidence-card.ts`, `web/src/completion.ts`.
- Behavior: as P4, P3 and T7. Dismissing a Card moves focus to the next Card, else the one above, else the hint button. EXPERIENCE.md and DESIGN.md updated; epics.md not.
- Verification: 65c8bac, 4d05acb, 9801e6a. `tests/web/test_play.py::test_an_unsolved_puzzle_s_evidence_card_is_the_riddler_s_note_alone_and_the_solved_one_names_the_object`; `tests/web/test_completion.py`, whole file (24 collected).
- Remaining gates: none of the three commits is on `c9d0d61`; no M1 browser run.

#### EXPERIENCE-rows Four EXPERIENCE.md rows lag
Decision: Record (approve ordinary copy, item 62; fix stale rows). Status: open.
- Contract: EXPERIENCE.md was rewritten by the Oct 29 commits, and `tests/web/test_strings.py` enforces that every string in `web/src/strings.ts` appears verbatim there. A reverse scan found only the rows below.
- Affected: EXPERIENCE.md Component Patterns lines 391, 395, 400 and Open Items (lines 726-747); `web/src/components/hint-area.ts`.
- Behavior: see the table in 6.2. Rows checked and matching code: feedback line, Hotspot, Wizard notes order and Current scroll, Evidence card, Hint button countdown, Completion, Hosted landing and attract frame.
- Verification: `tests/web/test_strings.py` (16 tests) pass; 65c8bac; `tests/api/test_hints.py::test_ten_hint_requests_inside_the_spacing_at_rung_2_each_answer_the_direction_and_the_wait_then_one_opens_the_next`.
- Remaining gates: C1 is not on master; its row cannot be checked yet. B4b (1e8578a) edited the Cut 2, Capture, Play, Completion and State Patterns rows after this scan; `tests/web/test_strings.py` holds its strings, and no reverse scan has covered them. I1's rows (Feedback line, Hotspot, Inventory, Completion screen, found-target line) landed with d4e1a1c and f330810 and are held by `tests/web/test_strings.py`.

### 6.2 Lagging doc sections

One row per doc section. "Says" is the current text; "Shipped" is the base. Abbreviations: SPINE = `docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md`; EPICS = `docs/planning-artifacts/epics.md`; SCHEMA = `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md`; EXP = `docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md`; STACK = `docs/specs/spec-keyframe/stack.md`; SIT = `docs/implementation-artifacts/sit-checklist.md`; SPRINT = `docs/implementation-artifacts/sprint-status.yaml`; UAT = `docs/implementation-artifacts/uat-signoff.md`.

| Doc and section | Says | Shipped | Items |
|---|---|---|---|
| SCHEMA §Fields / §API models | No sequence_length, Profile, HintReply, TriggerEvent, SessionState.trigger_events or hint_reply, edit_bounds, ErrorDetail.status | All present (section 1, item 33 table) | 32, 33, P4 |
| SCHEMA §TricksterEdit payloads | shortcut: {puzzle} | {type, puzzle, requires} | 33 |
| SCHEMA line 51 | Masks under 1% of the image are dropped | Dropped only if under 1% of the frame and under 0.1 of its box | S1 |
| SCHEMA play rules | find is a click on the target hotspot | find is a click made while no order sequence is armed | B2 |
| SCHEMA line 29 (Inventory) | Solving a find puzzle moves its interactable into the inventory | Only a target a use_on names as its item is carried; others are found | I1 |
| SPINE AD-1 Rule (line 47) | council and pipeline import only domain and ports; adapters only ports and domain | Also allowed: same-package imports, pipeline to council, adapters to spend and cache (GUARDS) | 35 |
| SPINE AD-3 | PlayView without sequence_length | PlayPuzzle.sequence_length | 32 |
| SPINE AD-4 (line 65) | `triggered_by: [event ids]`; `select_rung(events, derived, thresholds)`; a hint_request returns the current rung or a no-hint line | Log positions; `select_rung(events, thresholds, *, loosen, asked)`; a hint_request opens the next rung when none shows or past the spacing | 36, P4 |
| SPINE AD-4 session state list | No trigger_events or hint_reply | Both on SessionState | 33 |
| SPINE AD-5 Rule (line 71) | `segment(label, image) -> list[Polygon] \| None`; `phrase/greet -> str`; "the event log records phraser_fallback" | SegmentResponse with job_id and stage; PhraserResponse; phraser_fallback is a log line, not an event | 34, 42 |
| SPINE AD-6 Rule (line 77) | Moving dollars between allocations is a Settings change | Hosted allocation fixed at 20 in the local export; no env key | 43 |
| SPINE AD-6 Rule | CACHE=off sentence | No cross-reference to the AD-8 hosted Trickster exemption | 46 |
| SPINE AD-7 Rule (line 83) | Stages ingest to scene run in order through JobRunner.start | Ingest runs inside POST /builds; the runner starts at architect | 40 |
| SPINE AD-7 Rule | Mask selection with "the 1% and 12 caps" | 1% and box-fraction floor, cap 12 | S1 |
| SPINE AD-9 Rule (line 95) | SessionStore (append, read_all, list_ids, delete) | Plus put_header, read_header; AttemptStore, reserve_build, is_demo_room, is_judge_room, deleted_room; reasons.json, rooms/judge/<id>/job.json, rooms/jobs/, rooms/sessions/headers/ | 38 |
| SPINE AD-9 Rule | No atomic-put definition | Atomic only for the Dict slot claim; local temp file plus os.replace; Volume per container then commit | 38 |
| SPINE AD-9 / AD-14 | Secret carries hosted keys | `required_keys` MODEL_API_KEY, FAL_KEY, ACCESS_CODE | modal-objects |
| SPINE AD-10 Rule | A Clock port supplies all time | `pipeline/build.py new_id` and `author.py` Room.created read the wall clock | 35 |
| SPINE AD-11 Rule (line 107) | Polygon hotspots in the scene graph Tier 2 reuses | SVG overlay; polygon data and ids are what Tier 2 reuses | 39 |
| SPINE AD-13 (line 119) | Envelope `{error: {code, message, stage}}` plus status; used by build, access, session-creation and room-keyed routes only | status sits inside error, build_not_ready only; every session route, the profile routes and GET /meta use it; the unknown /api 404 does not | 33, 37 |
| SPINE AD-14 adapter settings | "per-role model ids"; no DEMO_PROPOSALS_DIR | MODEL_ARCHITECT, MODEL_RIDDLER, MODEL_DRYRUN, MODEL_TRICKSTER, MODEL_IMAGE; DEMO_PROPOSALS_DIR | settings-unnamed-keys, D2 |
| SPINE Conventions HTTP surface (line 157) | No multipart names or pairing, no POST /builds body, missing codes | `downscale` and `original` paired by index; 202 queued or 200 failed JobState; 403 build_quota_exceeded, 422 invalid_request, 404 photo_not_found, job_not_found, profile codes | 37 |
| SPINE source tree (line 213) | Only `.github/workflows/ci.yml` | Also deploy.yml, ops.yml, `scripts/promote_room.py`, `scripts/quota_probe.py` | 15, deploy-push-trigger, ops-push-trigger |
| SPINE Deferred (line 311) | "CD" and "CI beyond the single job" | deploy.yml and ops.yml exist | 15, deploy-push-trigger |
| SPINE / README | No CUT_0 flag | `CUT_0` constant in `web/src/router.ts` | 45 |
| EPICS FR-2 | "readable attributes"; stored verbatim as read | Two to four visible attributes | D7 |
| EPICS FR-3 (line 33), mask-selection story (lines 2046, 2059) | Masks under 1% of the image dropped | 1% and box-fraction floor | S1 |
| EPICS FR-6 | Hosted "deleted Tue Nov 10" as fact; fal.ai named | "scheduled for deletion"; fal never named | B1 |
| EPICS FR-12 (line 42); Story 1.21 find AC (line 1341) | Solving a find Puzzle moves its Interactable into the Inventory; the item fades into the Inventory | Only a target a use_on needs is carried; others read "{label} · found" | I1 |
| EPICS FR-14, FR-15, FR-16 | Typed hint field; a hint request repeats only; Triggers panel auto-opens | One hint button; asks open rungs; "How hints work" panel | P4, D6 |
| EPICS FR-26 | Disclosure banner at the top edge | Footer | D6 |
| EPICS FR-27 (line 57) | Every paid cloud call can be served from the Cache | Hosted Trickster runs cache off | 46 |
| EPICS AR-7 | Event ids | Log positions | 36 |
| EPICS AR-8 (line 96) | chat without attempt, job_id, stage, session_id; segment -> list[Polygon] \| None | Section 2, item 34 | 34 |
| EPICS AR-24 (line 112) | Push to master and every PR; no secrets, no deploy step, no CD | Push to master and keyframe/**, every PR; deploy.yml and ops.yml run modal with secrets | 15, deploy-push-trigger, F29 |
| EPICS AR-32 (line 120) | CI beyond AR-24 deferred | deploy.yml and ops.yml exist | 15, ops-push-trigger |
| EPICS Story 1.3 AC 1 (~line 586) | Pushed to master or a PR opened; modal deploy stays manual | keyframe/** too; deploy.yml exists | 15, deploy-push-trigger |
| EPICS Story 1.14 ACs | mode constant; Disclosure composition; Local retention wording; rooms "per stored Room" | Section 6.1, epics-1.14 | epics-1.14 |
| EPICS Story 1.19 hover and non-target ACs; UX-DR23 (line 146); UX-DR24 (line 147) | 2 px outline; no label on hover | 3 px, 400 ms dwell chip, pending chip | D3, epics-UX-DR23-24 |
| EPICS Story 1.21 ACs | "Open" held 1200 ms; focus moves to the next entry's heading | "Solved"; feedback line; notes announced, never focused | P2, B2, D4 |
| EPICS Story 1.25 AC (line 1480); UX-DR70 (line 193); UX-DR34 | "Puzzle {n}: open."; Open chip | "Puzzle {n} solved."; Solved chip | P2, epics-live-region-1480 |
| EPICS Story 1.26 AC | "3 to 5 pips", no source field | Pips from `sequence_length` | 32 |
| EPICS Story 2.10 AC | Queued before the runner starts, then running with stage | Ingest never observable as running | 40 |
| EPICS Story 2.12; STACK line 38 | POST /builds returns a job id | Returns a JobState | 37, 40 |
| EPICS Story 2.18 AC (line 2251) | "Reading your photos" pending and running from polled state | Upload's pending label, then done | 40 |
| EPICS Story 2.23 prompt fields | No lock_type | lock_type per Puzzle | B2 |
| EPICS Story 2.29 AC (line 2673); Story 6.2 (line 3889) | Under cut 0 the route is absent | Client and API routes not guarded | 45 |
| EPICS Story 3.1 AC | triggered_by is "the id of the event" | Log position | 36 |
| EPICS Story 3.3 AC | A hint_request never triggers a Rung; no HintReply or next_hint_ms | Asks open rungs; HintReply with next_hint_ms | 33, 36, P4 |
| EPICS Story 3.4 ACs; UX-DR30, UX-DR31, UX-DR32, UX-DR33 | Hint field, "Ask the Guide", helper line, "Asking", Triggers toggle | One button, "The Guide is thinking", countdown, "How hints work" | P4, epics-oct29-rows |
| EPICS Story 3.5 | No TriggerEvent shape | TriggerEvent {type, t_ms} | 33 |
| EPICS Story 3.7 AC (line 3050); line 3702 | phraser_fallback logged; the session Event log records it once | Log line only | 42 |
| EPICS Story 5.3 | 404 and 422 only; built only when cut 2 is taken | profile_not_found, invalid_profile, invalid_profile_name; registered in every Local app | 37 |
| EPICS Story 7.9 export AC | Ceiling is the sum of the two allocations | Hosted one hard-coded, no source or staleness | 43 |
| EPICS Story 7.10 AC 4 | Checked live in a non-judging Modal Environment | Probe ran in main on an ephemeral Dict | build-quota-probe |
| EPICS Story 7.16 ACs; UX-DR57, UX-DR58, UX-DR68, UX-DR74, UX-DR75 | Title block, card grid, no wizard band, focus on first card, empty-list copy, top banner | Section 6.1, epics-7.16 | D1, D6, D9, P1, P6 |
| EPICS UX-DR14; UX-DR60 | No sample-room button; no portrait or copy button | D5 | D5 |
| EPICS UX-DR17; UX-DR59 | Old Timer and Access-code wording | B4a wording | B4a |
| EPICS UX-DR20; UX-DR79 | Old retention copy | B1 | B1, epics-1.14 |
| EPICS UX-DR25; UX-DR27 | No count badge; availability order, no scroll-to-Current | Count badge; Room order; scroll to Current | P5, B2 |
| EPICS UX-DR38 | Bare "Open" chip | Bloom, feedback line, "Solved" | D4, P2 |
| EPICS UX-DR39; UX-DR40; UX-DR44; UX-DR66 | Evidence one state; focus to hint field; plain Completion | Note until solved; focus to hint button; count-up, filmstrip, Built by, copy | P3, P4, T7 |
| EPICS UX-DR45, text near line 3707 | "Welcome to your own room. Find what doesn't belong." | "Read a riddle, then click the thing it means." plus three steps | P1 |
| EPICS UX-DR56 | Disclosure banner at top | Footer | D6 |
| EPICS line 81 (NFR-10 note) | Scenes in the scene graph Tier 2 reuses | SVG overlay | 39 |
| EPICS HTTP surface (line 101) | 409 build_not_ready for /view only; no session-route 410 | /room 409 too; session 410 | B3 |
| EXP line 443 and Stage list row (line 372) | Pending (uploading); no link to "Reading your photos" | Upload pending label is "Reading your photos"; ingest done on acceptance | 40 |
| EXP line 400 | On Card dismiss focus moves "else to the hint field" | Next Card, else above, else the hint button | EXPERIENCE-rows |
| EXP line 391 | Every request counts as a hint used | Recorded as hint_requested; "Hints used" is rungs_used, so a repeat press inside the spacing changes nothing visible | EXPERIENCE-rows |
| EXP line 395 | Stray double comma | | EXPERIENCE-rows |
| EXP Open Items (lines 726-747) | Per-attempt fixed messages, Rung provenance, Help timing, Demo room welcome, Hint area cap and first Card, Hint field placeholder listed open | Shipped (JobState/BuildView sent_back; RungChangeEvent.phrased and phrasing_ms; DEMO_ROOM_WELCOME) or moot (P4) or settled (item 65, F10) | EXPERIENCE-rows |
| EXP, SPINE, EPICS Story 2.31 | Nothing on the pinned message copy | Copy in `web/src/strings.ts`, RULES authoritative, drift test guards | 41 |
| README.md | No ops actions or request.json keys; points to the keyframe-modal runbook, removed at the Nov 4 hygiene step | ops.yml offers 8 actions | ops-push-trigger, ops-actions |
| README.md | No Modal objects, no Secret required keys, no DEMO_PROPOSALS_DIR or MODEL_<ROLE> | modal-objects, settings-unnamed-keys | modal-objects, settings-unnamed-keys |
| keyframe-devops SKILL.md "Today vs from Oct 26" | Repo has no uv.lock, CI or scripts/ | All exist | 15 |
| keyframe-devops SKILL.md Settings and secrets | No DEMO_PROPOSALS_DIR or MODEL_<ROLE>; "the first providers story removes the two direct reads" | Done 26 Oct; keys exist; only three Secret keys are required | settings-unnamed-keys, modal-objects |
| keyframe-modal SKILL.md line 190; runbook line 67 | 20 concurrent reserve_build calls on the dev Dict; run it on dev | Separate processes on an ephemeral Dict, run in main | build-quota-probe |
| keyframe-modal runbook one-time setup | Hosted allocation set in the Secret | Local export ignores it | 43 |
| `src/domain/schema.py` module docstring | Later changes go through correct-course | This record is the first | 33 |
| `src/infra/modal.py` module docstring | No retention rule relies on Dict expiry (AD-8) | attempts:<ip> rely on it | 38 |
| `src/config.py` hosted_spend_cap_usd docstring | Records the limit | No planning doc does | 43 |
| `tests/domain/test_session.py::test_a_hint_request_never_opens_a_lock_counts_a_wrong_attempt_or_changes_a_rung` | Name states the pre-Oct 29 rule | Passes only because the hint lands inside the spacing | 36 |
| SPRINT lines 166-169 | 7.10 AC 4 live check PENDING | Probe passed, GitHub run 40821411610 | 18, build-quota-probe |
| SPRINT | No record of deploy run 6, `c9d0d61`, ops run 1 promote or an M1 browser pass | Deploy run 6 and ops runs 1 and 2 happened; no M1 pass | hosted-redeploy, 16, 19 |
| SIT line 94 and dated item "Before Thu Nov 5" | Quota atomicity with empty result | GitHub run 40821411610 passed | 18 |
| SIT Live-only items (SIT-02 rows) | No outcome | Present and absent recorded; latency, parallel and H/W unrecorded | 17 |
| SIT SIT-08 "Still to run", SIT-09, SIT-11, Tue Oct 27 Baseten item | Blank | Unrun | 19, 21 |
| SIT dated Done column and run log from Thu Oct 29 | Blank; first manual deploy blank although done (0452a4c) | Deploy run 6, ops runs 1 and 2 unrecorded | SIT-rows |
| SIT "Before Tue Nov 10" purge row; "Thu Nov 5" autoscaler row | No result | Correctly blank; neither has run | ops-actions |
| UAT §1 doctor field | Blank | Unrun | 13 |
| UAT §3 SM-C2 | No Rung sooner than FR-15 allows (old rule) | Asks open rungs | P4, UAT-rows |
| UAT §4 Live link row | Assumes the Thu Oct 29 redeploy | Live site is `c9d0d61` | hosted-redeploy, UAT-rows |

## 7 Remaining live gates

None of these has passed. Each stays unrun until its owner records a result. "Owner" is Luis Ticas.

### hosted-redeploy The hosted URL serves `c9d0d61`
Decision: Verify (items 16, 19). Status: open.
- Contract: deploy run 6 (GitHub run 40802005305, push to deploy/main) put `c9d0d61` on the hosted URL. origin/master is `1e8578a`.
- Affected: deploy.yml, the hosted URL, UAT-14, SIT-10.
- Behavior: `git log c9d0d61..origin/master` lists 19 undeployed commits: 85a4afa (B1), e2a7fc1 (P1), 055bf88, ad598f0 (P2), 5863a59 (B2), 4d05acb (P3), e4fe83b (P6), b161d99 (B3), 72d6bfb, 65c8bac (P4), 4ae3dca, 9801e6a (T7), 69c269a (B5), 1eb9f51 (P5), 18ec75a (B4a), 42d3253 (S1), d4e1a1c (I1), f330810 (I1), 1e8578a (B4b). Re-checked after fetch: origin/deploy/main is still `c9d0d61`.
- Verification: GitHub runs 40802005305 (deploy), 40828349988 (CI master, 1e8578a), 40828171360 (CI keyframe/bmad-brief, 1e8578a): success.
- Remaining gates: push master to deploy/main, then a hosted smoke and SIT-10 parity on the deployed commit (owner, hosted URL). No claim about the live page holds for master's behavior until then.

### 13 Doctor run on the M1
Decision: Record actual choice. Status: open.
- Contract: `python3 scripts/doctor.py` must pass on the M1 before SIT and every UAT run; UAT §1 field blank.
- Affected: Story 1.2, `scripts/doctor.py`, UAT §1, SIT preconditions.
- Behavior: no result recorded anywhere.
- Verification: none.
- Remaining gates: owner on the M1 (real Ollama, real RAM, arm64, model resident near 3 GB). Gates SIT-05 and every UAT row.

### 16 M1 browser verification
Decision: Verify remaining paths. Status: open.
- Contract: keyboard and focus, Capture and EXIF, reload and reconnect, first-card readability and a clean arm64 install at 1024, 1280 and 1440, recording commit, browser, viewport and result.
- Affected: Stories 1.4, 1.16 to 1.20, 1.22, 1.23, 1.27, 2.16; UAT-01, UAT-11.
- Behavior: offline web tests pass; the landing, sample room and attract frame were exercised against the hosted URL and real room data. No M1 pass recorded.
- Verification: none.
- Remaining gates: owner on the M1 in Chrome at 1024, 1280 and 1440, on the commit under test.

### 17 Live SAM wire format
Decision: Verify. Status: partial.
- Contract: a real SIT-02 recording covering request mode, store:false acceptance, present and absent masks, coordinate decoding and latency; also mask H/W against box and frame, 12 parallel calls against the 10 s budget, the zero-match stream close.
- Affected: SIT-02, Stories 2.7, 2.9, `src/providers/meta_api.py`.
- Behavior: SIT-02 passed Wed 28 Oct from the container on real photos: present decoded to one polygon, absent returned none; recordings committed (558da8a). No latency, parallel or H/W record. S1 changed small-mask handling after the recording.
- Verification: 558da8a.
- Remaining gates: owner re-runs SIT-02 from the M1 or hosted for latency, 12-call parallel and H/W. store:false acceptance is not proof of provider-wide retention.

### 18 Quota atomicity
Decision: Verify before uploads. Status: partial.
- Contract: race more than 20 callers across processes or containers on an isolated quota, then 19 prefilled and a race for the last; preserve claims through judging.
- Affected: Stories 7.10, 7.11; `scripts/quota_probe.py`, `DictJobStore.reserve_build`, SPRINT.
- Behavior: GitHub run 40821411610 passed (20 of 30, 1 of 8) on an ephemeral Dict with the same keys and `put(skip_if_exists=True)`; result not in the repo.
- Verification: 69c269a; run 40821411610; `tests/scripts/test_quota_probe.py::test_the_script_never_names_a_real_dict_and_races_in_separate_spawned_processes`, `::test_an_atomic_claim_passes_both_races_and_prints_the_counts`; `tests/test_ops_workflow.py::test_the_quota_probe_runs_from_a_dispatch_or_a_request_file_on_an_ephemeral_dict_only`.
- Remaining gates: processes on one runner, not separate containers; claim preservation against expiry unverified; SPRINT and SIT rows to be updated with run 40821411610.

### 19 Hosted stores, Crons, proxy and purge
Decision: Verify before uploads. Status: partial.
- Contract: durable sessions, a long queued Build, required Secret keys, complete seed assets, snapshot and epoch behavior, Cron registration and invocation, a full dev-room purge; forwarded identity only through a documented trusted-proxy path.
- Affected: SIT-08, SIT-09; Stories 7.2, 7.8, 7.9, 7.11, 7.12, 7.13, 7.19, 7.20; `src/api/app.py` client_ip, `scripts/purge_judge_rooms.py`, ops.yml.
- Behavior: proven live: deploys with the Secret; hosted job job_01M61TZ74F6F3AVVEMPRAS4V1G done after 182 s; ops run 1 promoted room_01M61TZ74F0FP3X9HHTMXGTPB9. Sessions survive a restart in code (F1). `client_ip()` keys attempts on `request.client.host` and reads no forwarded header; what that is on Modal is unverified.
- Verification: GitHub run 40741283292 (deploy run 4, bff6cee: the deployment the hosted job ran on); GitHub run 40795627220 (ops run 1: the promotion); `tests/api/test_session_restart.py::test_a_local_session_is_replayed_by_a_restarted_app_and_its_clock_resumes_after_the_last_event`; `tests/test_ops_workflow.py::test_the_request_job_holds_no_secret_and_guards_a_push_to_one_request_file_on_top_of_master`.
- Remaining gates: owner via ops or Modal: SIT-08 second set queued behind max_containers=1, the `call:<job_id>` key, volume.reload latency; SIT-09 Cron snapshot; a dev judge room purge before Tue Nov 10; a hosted session surviving a container restart; `request.client.host` behind Modal's proxy.

### 20 Real CI
Decision: Verify / defer optimization. Status: partial.
- Contract: inspect GitHub results, show a controlled failure goes red on a disposable branch if no evidence exists, and require the check or record the manual rule.
- Affected: Story 1.3, `.github/workflows/ci.yml`.
- Behavior: recent runs on 42d3253, f330810 and 1e8578a green for both branches.
- Verification: GitHub runs 40824024032, 40823800471 (42d3253); 40827276075, 40826918938 (f330810); 40828349988, 40828171360 (1e8578a).
- Remaining gates: no controlled-red run; no required-check or manual-rule record (owner).

### 21 Baseten fallback
Decision: Verify if shipped. Status: open.
- Contract: choose strict-schema or plain-JSON mode from a live RoomDraft, or label an unused fallback unverified. SIT-11 and the Tue Oct 27 item blank.
- Affected: SIT-11, Story 2.8, `src/providers/openai_compatible.py`, RETENTION_FALLBACK.
- Behavior: the Retention summary names Baseten/Fireworks only when a role uses openai_compatible. No SIT-11 run (no OPENAI_COMPATIBLE_API_KEY on Oct 27).
- Verification: `tests/api/test_meta.py::test_the_fallback_is_named_only_when_settings_switch_a_role_to_it`.
- Remaining gates: owner runs SIT-11 with the Baseten key, or labels the fallback unverified and leaves it off.

### SIT-rows SIT checklist
Decision: Verify. Status: open.
- Contract: SIT (updated 28 Oct): case table, Live-only items, dated builder items, run log.
- Affected: SIT, `scripts/sit.py`, `tests/sit/*`.
- Behavior: passed: SIT-04, SIT-06, SIT-07, SIT-15 (27 Oct); SIT-01, SIT-02, SIT-13 (synthetic), SIT-14 (28 Oct). Failed and open: SIT-13 (test_07) and SIT-03 (test_09) on real photos from the container (proxy 30 s cut, not a Meta error). SIT-03 Local CACHE=off unrun; the hosted Build took 182 s, over budget, logged as an NFR-1 miss, with no stage fixtures. Unrun: SIT-05, SIT-08 second set, SIT-09, SIT-10 (story 7.23 backlog), SIT-11, SIT-12 (Tier 2 only), SIT-16 (voice, unscheduled), the Fireworks Trickster fixture. Dated items with blank Done: SIT-0 pre-kickoff; Fireworks id (26 Oct); first ledger export (only `spend/exports/ledger-2026-10-28.json`, 643f564); Baseten test (27 Oct); first manual deploy (done per sprint status, 0452a4c); SIT-10 Thu 29 Oct; Capture measured (2.26, five live Builds); M1 Ollama benchmark; Sat 31 Oct live Trickster and Fireworks fixture; Sat 31 Oct full pass; quota atomicity; Nov 5 autoscaler; dev purge before Nov 10; daily ledger exports. Run-log rows Thu 29 Oct to Wed 4 Nov blank.
- Verification: `tests/test_sit_checklist.py` (2 tests) pass; 643f564; 558da8a.
- Remaining gates: see the table below.

### UAT-rows UAT acceptance tests and sign-off
Decision: Verify. Status: open.
- Contract: `docs/implementation-artifacts/uat-acceptance-tests.md` §2 and UAT §1 to §8 (both last updated 22 Oct); every result, evidence, attestation, SIT-status, decision and signature field blank.
- Affected: UAT-01 to UAT-16, SM-C1 to SM-C4.
- Behavior: not run. SM-C2's wording predates P4.
- Verification: none.
- Remaining gates: every row and attestation is unrun and must not be reported as passed (table below). Household consent for real photos beyond the owner's own home is unverified and gates UAT-01, UAT-12 and UAT-13 evidence and any hosted Demo room built from other homes.

### 7.1 Gate table

| Gate | Who | Where | Items |
|---|---|---|---|
| Push master to deploy/main; hosted smoke | Owner | GitHub push, hosted URL | hosted-redeploy, P1 to P6, T7, B1 to B5, S1, I1 |
| SIT-10 parity (Local and hosted in the browser) | Owner | M1 and hosted URL | hosted-redeploy, SIT-rows |
| Doctor run | Owner | M1 | 13 |
| M1 browser pass at 1024, 1280, 1440 | Owner | M1, Chrome | 16, 32, 33, 36, 40, 41, D1 to D9, P1 to P6, T7, B4a, B4b, I1 |
| SIT-05 Ollama phrase and fallback; Ollama benchmark | Owner | M1 with Ollama and llama3.2:3b | 42, SIT-rows |
| SIT-03 Local CACHE=off; SIT-13 on real photos | Owner | M1 or hosted URL (not the container, 30 s proxy cut) | D7, SIT-rows |
| SIT-02 latency, 12-call parallel, mask H/W | Owner | M1 or hosted | 17, S1 |
| Live Build after S1 and re-promotion of the Demo room | Owner | Hosted URL, ops promote | S1, P5, B5 |
| Daily ledger exports; ledger-export ops action; Nov 5 reset | Owner | M1 and ops workflow | 43, ops-actions |
| SIT-08 second queued set, `call:<job_id>`, volume.reload | Owner | Modal dev, ops workflow | 19 |
| SIT-09 Cron snapshot; session sweep Cron | Owner | Modal | 19, B1 |
| Purge dry run and purge on a dev judge room before Tue Nov 10 | Owner | Ops workflow, dev Environment | 38, 19, ops-actions, B3, B5 |
| Hosted Trickster window, check no cache write on the Volume (named by decision 46) | Owner | Hosted URL | 46 |
| Cache keys across Regenerations on the hosted Volume | Owner | Hosted | 34 |
| Warm and cool (Nov 5 to Nov 9), conditional on the Official Rules | Owner | Ops workflow, deploy/main-warm | ops-actions, deploy-push-trigger |
| deploy/dev push; refusal paths for deploy and ops pushes | Owner | GitHub | deploy-push-trigger, ops-push-trigger |
| Record quota probe run 40821411610 in SPRINT and SIT | Owner | Repo docs | 18, build-quota-probe |
| Controlled-red CI run; required check or manual rule | Owner | GitHub | 20, 15 |
| SIT-11 Baseten, Fireworks Trickster fixture | Owner with keys | M1 | 21, F22 |
| UAT-01, UAT-02, UAT-04 to UAT-13 | Owner | M1, Local mode, Chrome | UAT-rows |
| UAT-03 | Non-builder playtester plus SM-2 attestation, or disclosed builder cold-run fallback | M1 | UAT-rows |
| UAT-14 A, live-link addendum after SIT-10; UAT-14 B if the Rules allow | Owner | Hosted URL; Chrome, Safari, Firefox at 1280+ | UAT-rows, epics-7.16 |
| UAT-15, UAT-15b | Owner, if the Tier 2 gate opens | | 39, UAT-rows |
| UAT-16 dry run (Sun Nov 1) and final pass (Wed Nov 4) | Owner | Fresh clone, logged-out browser | UAT-rows |
| SM-C1 to SM-C4 attestations; SM-C2 re-read against P4 | Owner | UAT §3 | P4, UAT-rows |
| Household consent for real photos beyond the owner's home | Owner | | modal-objects, UAT-rows |
| Provider and account facts behind the retention wording (named by decision 1) | Owner | Provider accounts | B1, epics-1.14 |
