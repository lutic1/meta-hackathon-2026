"""Story 2.20: the author stage turns one Riddler call into a mapped draft, and the Validator judges every draft (AD-12, AD-16, AD-18)."""

import hashlib
import json
import re
from typing import Any

import pytest

from src.council import architect as architect_prompt
from src.council.riddler import build_author_prompt, response_schema
from src.domain.ledger import LedgerEntry
from src.domain.schema import JobState, Puzzle, RoomDraft, StageRecord
from src.domain.validator import RULES
from src.infra.clocks import BuildClock
from src.pipeline.author import (
    COUNT_MESSAGE,
    ID_MESSAGE,
    PUZZLES,
    SHAPE_MESSAGE,
    DraftRefused,
    ValidationError,
    assemble_provenance,
    author_stage,
    draft_key,
    map_draft,
    parse_draft,
    prompt_hashes,
    prompt_view,
    puzzles_key,
    read_draft,
    read_puzzles,
    run_author,
    run_validate,
    validate_stage,
)
from src.pipeline.build import Build, new_id
from src.pipeline.ports import room_key
from src.pipeline.segment import INTERACTABLES, interactables_key
from src.providers.base import ProviderError
from src.providers.cache import GuardedCalls
from src.providers.meta_api import CHAT_MODEL, MetaModelProvider
from src.providers.mock import ChatCall, MockProvider, MockScript
from src.providers.spend import SpendLedger
from tests.fixtures.rooms import IX
from tests.providers.replay import load, transport
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

PZ = re.compile(r"pz_[0-9A-HJKMNP-TV-Z]{26}")
RECORDED = "muse-spark-1.3/chat-riddler-author"
REPLY: dict[str, Any] = json.loads(load(RECORDED).body["choices"][0]["message"]["content"])
"""The recorded SIT-13 reply over the synthetic four-lock room: five puzzles `p1`..`p5`, `p5` the exit."""


def reply(**changes: Any) -> str:
    """The recorded reply with puzzles replaced or removed (`None`), as the Riddler's JSON text."""
    return json.dumps({**REPLY, **changes})


def with_puzzle(key: str, **fields: Any) -> dict[str, Any]:
    return {**REPLY[key], **fields}


def riddler(*texts: str) -> MockProvider:
    return MockProvider("riddler", MockScript(chat=list(texts)))


@pytest.fixture
def build(jobs, artifacts, ticker, doubles, four_lock_room):
    """A Build whose segment double stores the four-lock room's Interactables, then the real author and validate stages."""
    doubles.hooks["segment"] = lambda state: store_interactables(artifacts, state, four_lock_room)

    def make(provider: MockProvider, ledger: MemoryLedgerStore | None = None) -> Build:
        stages = doubles.stages()
        stages["author"] = author_stage(provider, artifacts)
        stages["validate"] = validate_stage(artifacts, ledger or MemoryLedgerStore())
        return Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=2)

    return make


def store_interactables(artifacts, state: JobState, room) -> None:
    artifacts.put(interactables_key(state.room_id), INTERACTABLES.dump_json(room.interactables))


@pytest.fixture
def seeded(jobs, artifacts, ticker, doubles, uploads, four_lock_room) -> JobState:
    """A queued job whose photos are ingested and whose Interactables are the four-lock room's, ready for `run_author`."""
    runner = Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=doubles.stages(), regen_max=2)
    state = runner.submit(uploads)
    store_interactables(artifacts, state, four_lock_room)
    return state


# --- One Riddler call, the RoomDraft and one call row --------------------------


def test_one_riddler_chat_call_over_the_2_19_prompt_persists_the_room_draft_and_one_call_row(build, uploads, four_lock_room, artifacts):
    provider = riddler(reply())
    runner = build(provider)
    done = runner.run(runner.submit(uploads).id)
    assert done.status == "done" and done.error is None
    assert len(provider.calls) == 1
    call = provider.calls[0]
    prompt = build_author_prompt(prompt_view(done.room_id, four_lock_room.interactables))
    assert isinstance(call, ChatCall)
    assert call.messages == prompt.messages() and call.images == []
    assert call.response_schema is response_schema() and call.reasoning_effort == "medium" and call.attempt == 0
    rows = [row for row in done.calls if row.role == "riddler"]
    assert len(rows) == 1 and (rows[0].model, rows[0].host, rows[0].cached) == ("mock-chat-1", "mock", False)
    assert read_draft(done.room_id, artifacts) == parse_draft(reply(), response_schema())
    assert [p.key for p in read_draft(done.room_id, artifacts).puzzles] == ["p1", "p2", "p3", "p4", "p5"]
    author = next(record for record in done.stages if record.stage == "author")
    assert author == StageRecord(stage="author", duration_ms=0, count=5, model="mock-chat-1")


def test_the_call_carries_the_regeneration_count_as_attempt(seeded, artifacts):
    provider = riddler(reply())
    run_author(seeded.model_copy(update={"regeneration_count": 2}), provider=provider, artifacts=artifacts)
    assert provider.calls[0].attempt == 2


def test_the_prompt_view_carries_the_interactables_only(four_lock_room):
    view = prompt_view(four_lock_room.id, four_lock_room.interactables)
    assert view.puzzles == [] and [ix.id for ix in view.interactables] == [ix.id for ix in four_lock_room.interactables]
    assert set(view.interactables[0].model_dump()) == {"id", "label", "attributes", "instances", "photo"}


def test_the_stage_needs_a_room(seeded, artifacts):
    provider = riddler(reply())
    with pytest.raises(ValueError, match="names no room"):
        run_author(seeded.model_copy(update={"room_id": None}), provider=provider, artifacts=artifacts)
    assert provider.calls == []


def test_a_provider_error_ends_the_build_failed_at_author(build, uploads, doubles):
    class Failing(MockProvider):
        def chat(self, *args, **kwargs):
            raise ProviderError(503, "service_overloaded", "still overloaded after the retry")

    runner = build(Failing("riddler"))
    failed = runner.run(runner.submit(uploads).id)
    assert (failed.status, failed.stage, failed.error.code) == ("failed", "author", "provider_error")
    assert "validate" not in doubles.calls


# --- Mapping: p-keys to pz_ ULIDs, ix_ ids by exact match ------------------------


def test_every_p_key_including_those_in_requires_becomes_a_pz_ulid_before_validate(build, uploads, artifacts):
    runner = build(riddler(reply()))
    done = runner.run(runner.submit(uploads).id)
    puzzles = read_puzzles(done.room_id, artifacts)
    ids = [puzzle.id for puzzle in puzzles]
    assert len(ids) == 5 and len(set(ids)) == 5 and all(PZ.fullmatch(i) for i in ids)
    by_key = dict(zip(["p1", "p2", "p3", "p4", "p5"], ids, strict=True))
    assert [puzzle.requires for puzzle in puzzles] == [
        [by_key[key] for key in REPLY[f"p{n}"]["requires"]] for n in range(1, 6)
    ]
    assert puzzles[4].requires == [by_key["p3"], by_key["p4"]] and puzzles[4].is_exit
    raw = artifacts.read(puzzles_key(done.room_id)).decode()
    assert not re.search(r'"p[1-6]"', raw)


def test_the_draft_keeps_every_ix_reference_as_given():
    puzzles = map_draft(parse_draft(reply(), response_schema()), set(IX.values()))
    assert puzzles[3].solution.model_dump() == {"lock_type": "use_on", "item": IX["key"], "target": IX["chest"]}
    assert puzzles[2].evidence.interactable == IX["candle"]


def test_a_requires_key_with_no_puzzle_maps_to_an_id_no_puzzle_has_and_rule_2_refuses_it(build, uploads, artifacts):
    runner = build(riddler(reply(p2=with_puzzle("p2", requires=["p6"]))))
    stopped = runner.run(runner.submit(uploads).id)
    assert (stopped.status, stopped.stage) == ("needs_recapture", "validate")
    assert [v.rule for v in stopped.validator if not v.passed] == [2]
    puzzles = read_puzzles(stopped.room_id, artifacts)
    assert PZ.fullmatch(puzzles[1].requires[0]) and puzzles[1].requires[0] not in {p.id for p in puzzles}


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param("brass key", id="a label"),
        pytest.param(IX["key"][:-1] + "9", id="one character off"),
        pytest.param(IX["key"].upper(), id="upper case prefix"),
        pytest.param(" " + IX["key"], id="leading space"),
    ],
)
def test_an_interactable_named_by_anything_but_its_exact_id_is_a_failed_attempt_with_the_id_reason(build, uploads, doubles, artifacts, bad):
    runner = build(riddler(reply(p1=with_puzzle("p1", solution={"lock_type": "find", "target": bad}))))
    stopped = runner.run(runner.submit(uploads).id)
    assert (stopped.status, stopped.stage, stopped.error.code) == ("needs_recapture", "author", "validation_error")
    assert stopped.sent_back[-1].messages == [ID_MESSAGE] and stopped.sent_back[-1].attempt == 0
    assert "validate" not in doubles.calls and stopped.validator == []
    assert len([row for row in stopped.calls if row.role == "riddler"]) == 1
    with pytest.raises(KeyError):
        read_puzzles(stopped.room_id, artifacts)
    assert bad not in stopped.model_dump_json()


def test_an_unknown_id_in_evidence_is_refused_before_validate():
    draft = parse_draft(reply(p2=with_puzzle("p2", evidence={"interactable": IX["rug"][:-1] + "0", "visible_attribute": "woven"})), response_schema())
    with pytest.raises(DraftRefused, match=re.escape(ID_MESSAGE)):
        map_draft(draft, set(IX.values()))


# --- Schema failures: a failed attempt with a fixed reason, never a failed Build -----


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("The Riddler shrugs.", id="not JSON"),
        pytest.param(reply(p4=None), id="three puzzles"),
        pytest.param(json.dumps({**REPLY, "p7": REPLY["p1"]}), id="a seventh key"),
        pytest.param(reply(p1=with_puzzle("p1", lock_type="code")), id="lock type and solution disagree"),
        pytest.param(reply(p2=with_puzzle("p2", requires=["p9"])), id="an unknown key in requires"),
    ],
)
def test_output_failing_the_response_schema_is_a_failed_attempt_with_the_shape_reason(build, uploads, doubles, artifacts, text):
    runner = build(riddler(text))
    stopped = runner.run(runner.submit(uploads).id)
    assert stopped.status == "needs_recapture" and stopped.status != "failed"
    assert stopped.stage == "author" and stopped.error.code == "validation_error"
    assert stopped.sent_back[-1].messages == [SHAPE_MESSAGE]
    assert "validate" not in doubles.calls and "dryrun" not in doubles.calls
    assert [r.stage for r in stopped.stages][-1] == "author"
    with pytest.raises(KeyError):
        read_draft(stopped.room_id, artifacts)
    with pytest.raises(KeyError):
        artifacts.read(room_key(stopped.room_id))


def test_the_failed_attempt_is_raised_for_the_regeneration_loop_with_its_messages(seeded, artifacts):
    with pytest.raises(ValidationError) as caught:
        run_author(seeded, provider=riddler("not json"), artifacts=artifacts)
    assert caught.value.messages == [SHAPE_MESSAGE] and caught.value.status == "needs_recapture"
    assert len(caught.value.result.calls) == 1 and caught.value.result.sent_back[0].stage == "validate"


# --- validate on every draft ------------------------------------------------------


def test_a_passing_draft_records_every_rule_as_passed_and_writes_no_room(build, uploads, artifacts):
    runner = build(riddler(reply()))
    done = runner.run(runner.submit(uploads).id)
    assert [(v.rule, v.name, v.passed) for v in done.validator] == [(n, rule.name, True) for n, rule in RULES.items()]
    assert done.sent_back == []
    with pytest.raises(KeyError):
        artifacts.read(room_key(done.room_id))  # the scene stage (a double here) writes it


LEAKY = with_puzzle("p2", clue="The clock says 415, if you listen.")
"""The code puzzle's clue gives its code away: rule 5."""


def test_a_failing_draft_yields_structured_reasons_with_the_fixed_messages(seeded, artifacts):
    run_author(seeded, provider=riddler(reply(p2=LEAKY)), artifacts=artifacts)
    with pytest.raises(ValidationError) as caught:
        run_validate(seeded, artifacts=artifacts, ledger=MemoryLedgerStore())
    puzzle_id = read_puzzles(seeded.room_id, artifacts)[1].id
    assert [(r.rule, r.puzzle_id, r.field, r.message) for r in caught.value.reasons] == [
        (5, puzzle_id, "clue", RULES[5].message),
        (5, puzzle_id, "near_answer", RULES[5].message),  # the near-answer is read with its clue
    ]
    assert caught.value.messages == [RULES[5].message]  # one line per fixed message


def test_a_failing_draft_records_per_rule_verdicts_quotes_no_token_and_writes_no_room(build, uploads, artifacts, doubles):
    runner = build(riddler(reply(p2=LEAKY)))
    stopped = runner.run(runner.submit(uploads).id)
    assert (stopped.status, stopped.stage, stopped.error.code) == ("needs_recapture", "validate", "validation_error")
    assert [(v.rule, v.passed) for v in stopped.validator] == [(n, n != 5) for n in RULES]
    assert stopped.sent_back == [stopped.sent_back[0]] and stopped.sent_back[0].messages == [RULES[5].message]
    assert "415" not in json.dumps(stopped.model_dump(mode="json")["sent_back"]) and "415" not in stopped.error.message
    assert "dryrun" not in doubles.calls
    with pytest.raises(KeyError):
        artifacts.read(room_key(stopped.room_id))


@pytest.mark.parametrize("count", [3, 7])
def test_a_draft_with_fewer_than_4_or_more_than_6_puzzles_never_passes(seeded, artifacts, count):
    state = seeded
    run_author(state, provider=riddler(reply()), artifacts=artifacts)
    puzzles = read_puzzles(state.room_id, artifacts)
    exit_puzzle = puzzles[4]
    if count == 3:
        chosen = [puzzles[0], puzzles[1], exit_puzzle.model_copy(update={"requires": [puzzles[0].id, puzzles[1].id]})]
    else:
        extra = [puzzles[0].model_copy(update={"id": new_id("pz")}) for _ in range(2)]
        chosen = [*puzzles[:4], *extra, exit_puzzle.model_copy(update={"requires": [p.id for p in puzzles[:4] + extra]})]
    artifacts.put(puzzles_key(state.room_id), PUZZLES.dump_json(chosen))
    with pytest.raises(ValidationError) as caught:
        run_validate(state, artifacts=artifacts, ledger=MemoryLedgerStore())
    assert caught.value.messages[0] == COUNT_MESSAGE


# --- Provenance (AD-16) ----------------------------------------------------------


def test_the_provenance_of_a_passing_draft_holds_ids_hashes_timings_count_spend_and_no_edits(seeded, four_lock_room):
    state = seeded.model_copy(update={
        "regeneration_count": 1,
        "stages": [
            *seeded.stages,
            StageRecord(stage="architect", duration_ms=12_000, count=9, model="muse-spark-1.3"),
            StageRecord(stage="segment", duration_ms=8_000, count=9, model="sam-3.1"),
            StageRecord(stage="author", duration_ms=30_000, count=5, model="muse-spark-1.3"),
            StageRecord(stage="author", duration_ms=20_000, count=5, model="muse-spark-1.3"),
        ],
    })
    other_job = new_id("job")
    call_a, call_b = new_id("call"), new_id("call")
    entries = [
        LedgerEntry(call_id=call_a, kind="riddler", status="reserved", usd=0.03, job_id=state.id, stage="author"),
        LedgerEntry(call_id=call_a, kind="riddler", status="settled", usd=0.02, job_id=state.id, stage="author"),
        LedgerEntry(call_id=call_b, kind="riddler", status="settled", usd=0.01, job_id=state.id, stage="author"),
        LedgerEntry(call_id=new_id("call"), kind="vision", status="settled", usd=0.025, job_id=state.id, stage="architect"),
        LedgerEntry(call_id=new_id("call"), kind="riddler", status="settled", usd=9.0, job_id=other_job, stage="author"),
        LedgerEntry(call_id=new_id("call"), kind="riddler", status="settled", usd=5.0),
    ]
    view = prompt_view(state.room_id, four_lock_room.interactables)
    provenance = assemble_provenance(state, entries, prompt_hashes(view))
    riddler_hash = hashlib.sha256(build_author_prompt(view).system.encode()).hexdigest()
    assert provenance.prompt_hashes == {"architect": architect_prompt.prompt_hash(), "riddler": riddler_hash}
    assert provenance.model_ids == {"architect": "muse-spark-1.3", "riddler": "muse-spark-1.3"}
    assert provenance.stage_timings_ms == {"ingest": 0, "architect": 12_000, "segment": 8_000, "author": 50_000}
    assert provenance.regeneration_count == 1
    assert provenance.spend_per_stage_usd == pytest.approx({"ingest": 0.0, "architect": 0.025, "segment": 0.0, "author": 0.03})
    assert provenance.applied_edits == []


def test_model_ids_follow_the_stage_records_by_role_and_the_latest_attempt_wins(seeded, four_lock_room):
    state = seeded.model_copy(update={"stages": [
        StageRecord(stage="architect", duration_ms=1, model="muse-spark-1.3"),
        StageRecord(stage="segment", duration_ms=1, model="sam-3.1"),
        StageRecord(stage="author", duration_ms=1, model="muse-spark-1.3"),
        StageRecord(stage="author", duration_ms=1, model="meta-models/muse-spark-open"),
    ]})
    provenance = assemble_provenance(state, [], prompt_hashes(prompt_view(state.room_id, four_lock_room.interactables)))
    assert provenance.model_ids == {"architect": "muse-spark-1.3", "riddler": "meta-models/muse-spark-open"}


# --- The recorded SIT-13 response replays offline --------------------------------


def test_the_recorded_riddler_response_replays_through_the_meta_adapter_into_a_passing_draft(seeded, artifacts):
    store = MemoryLedgerStore()
    meta = MetaModelProvider(
        "test-key",
        calls=GuardedCalls(MemoryCache(), SpendLedger(store, cap_usd=60.0), host="api.meta.ai"),
        chat_kind="riddler",
        budget_s=45.0,
        transport=transport(RECORDED),
    )
    state = seeded
    result = run_author(state, provider=meta, artifacts=artifacts)
    assert (result.count, result.model, result.calls[0].host) == (5, CHAT_MODEL, "meta")
    assert [(entry.kind, entry.status) for entry in store.entries()] == [("riddler", "reserved"), ("riddler", "settled")]
    assert isinstance(read_draft(state.room_id, artifacts), RoomDraft)
    assert all(isinstance(puzzle, Puzzle) for puzzle in read_puzzles(state.room_id, artifacts))
    validated = run_validate(state, artifacts=artifacts, ledger=store)
    assert all(verdict.passed for verdict in validated.validator) and len(validated.validator) == len(RULES)
    assert draft_key(state.room_id).endswith("/draft.json")
