"""Story 2.21: one regeneration loop, the Riddler re-asked with the reasons only, the job ended `needs_recapture` after `REGEN_MAX` (AD-6, AD-13)."""

import json
import re
from pathlib import Path

import pytest

from src.council.riddler import DraftReason, build_regeneration_prompt
from src.domain.schema import JobState, SentBack
from src.domain.validator import RULES
from src.infra.clocks import BuildClock
from src.pipeline.author import (
    COUNT_MESSAGE,
    SHAPE_MESSAGE,
    assemble_provenance,
    author_stage,
    prompt_view,
    run_author,
    validate_stage,
)
from src.pipeline.build import Build, StageResult
from src.pipeline.ports import room_key
from src.pipeline.regenerate import (
    REASONS,
    FailedAttempt,
    read_reasons,
    reasons_key,
    riddler_prompt,
)
from src.providers.base import ModelProvider
from src.providers.cache import GuardedCalls
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import ChatCall, MockProvider, MockScript
from src.providers.spend import SpendLedger
from tests.pipeline.test_author_stage import (
    LEAKY,
    RECORDED,
    reply,
    riddler,
    store_interactables,
    with_puzzle,
)
from tests.pipeline.test_build import RunnerDied
from tests.providers.replay import transport
from tests.providers.test_cache import MemoryCache
from tests.providers.test_spend import MemoryLedgerStore

REPO = Path(__file__).resolve().parents[2]
DRY_MESSAGE = "A puzzle could not be solved from its clue and rungs."


class DryRunRefused(FailedAttempt):
    """A test double for the Dry run's refusal (2.24): a later gate's failed attempt."""

    gate = "dryrun"


def dry_run_fails(doubles, *, attempts: int) -> list[int]:
    """Make the dryrun double refuse the first `attempts` attempts; the returned list fills with the count each call saw."""
    seen: list[int] = []

    def gate(state: JobState) -> None:
        seen.append(state.regeneration_count)
        if state.regeneration_count < attempts:
            raise DryRunRefused([DRY_MESSAGE], StageResult(count=3))

    doubles.hooks["dryrun"] = gate
    return seen


@pytest.fixture
def loop(jobs, artifacts, ticker, doubles, four_lock_room):
    """A Build over the real author and validate stages, the four-lock room's Interactables and the doubles around them."""
    doubles.hooks["segment"] = lambda state: store_interactables(artifacts, state, four_lock_room)

    def make(provider: ModelProvider, *, regen_max: int = 2) -> Build:
        stages = doubles.stages()
        stages["author"] = author_stage(provider, artifacts)
        stages["validate"] = validate_stage(artifacts, MemoryLedgerStore())
        return Build(jobs=jobs, artifacts=artifacts, clock=BuildClock(monotonic_ns=ticker), stages=stages, regen_max=regen_max)

    return make


def chat_calls(provider) -> list[ChatCall]:
    return [call for call in provider.calls if isinstance(call, ChatCall)]


def draft_strings(text: str) -> list[str]:
    """Every Clue, Lore, Rung and code of a drafted reply; the `ix_` ids it names are in every prompt's object list anyway."""
    found: list[str] = []
    for puzzle in json.loads(text).values():
        if puzzle is not None:
            found += [puzzle["clue"], puzzle["lore"], *puzzle["rungs"].values()]
            found += [puzzle["solution"]["code"]] if puzzle["lock_type"] == "code" else []
    return found


# --- Regeneration with the reasons only, and the count recorded ----------------------


def test_a_failing_draft_is_rewritten_from_the_reason_list_only_and_a_pass_proceeds_with_the_count(loop, uploads, artifacts, four_lock_room, doubles):
    leaky = reply(p2=LEAKY)
    provider = riddler(leaky, reply())
    runner = loop(provider)
    done = runner.run(runner.submit(uploads).id)
    assert (done.status, done.regeneration_count, done.error) == ("done", 1, None)
    first, second = chat_calls(provider)
    reasons = read_reasons(done.room_id, artifacts)
    assert [(r.rule, r.field, r.message) for r in reasons] == [(5, "clue", RULES[5].message), (5, "near_answer", RULES[5].message)]
    view = prompt_view(done.room_id, four_lock_room.interactables)
    assert second.messages == build_regeneration_prompt(view, reasons).messages()
    assert second.response_schema is first.response_schema and second.reasoning_effort == "medium"
    sent = "\n".join(message.content for message in second.messages)
    assert [text for text in draft_strings(leaky) if text in sent] == []
    assert "415" not in sent
    assert done.sent_back == [SentBack(attempt=0, stage="validate", messages=[RULES[5].message])]
    assert all(verdict.passed for verdict in done.validator)
    assert [record.stage for record in done.stages] == [
        "ingest", "architect", "segment", "author", "validate", "author", "validate", "dryrun", "story", "scene",
    ]
    assert len([row for row in done.calls if row.role == "riddler"]) == 2
    assert doubles.seen["dryrun"].regeneration_count == 1
    assert assemble_provenance(done, [], {}).regeneration_count == 1


def test_each_riddler_call_and_each_dry_run_carries_attempt_n(loop, uploads, doubles):
    provider = riddler(reply(), reply(), reply())
    seen = dry_run_fails(doubles, attempts=2)
    runner = loop(provider)
    done = runner.run(runner.submit(uploads).id)
    assert (done.status, done.regeneration_count) == ("done", 2)
    assert [call.attempt for call in chat_calls(provider)] == [0, 1, 2]
    assert seen == [0, 1, 2]


def test_under_cache_on_attempt_n_is_never_served_the_cached_answer_of_attempt_n_minus_1(loop, uploads, doubles, jobs, artifacts):
    store = MemoryLedgerStore()
    calls = GuardedCalls(MemoryCache(), SpendLedger(store, cap_usd=60.0), host="api.meta.ai")
    meta = MetaModelProvider("test-key", calls=calls, chat_kind="riddler", budget_s=45.0, transport=transport(RECORDED))
    dry_run_fails(doubles, attempts=3)
    runner = loop(meta)
    ended = runner.run(runner.submit(uploads).id)
    assert (ended.status, ended.stage) == ("needs_recapture", "dryrun")
    rows = [row for row in ended.calls if row.role == "riddler"]
    assert [row.cached for row in rows] == [False, False, False] and len({row.id for row in rows}) == 3
    assert len([entry for entry in store.entries() if entry.status == "settled"]) == 3

    # Attempts 1 and 2 sent the same prompt (each carries the Dry run's one fixed message and no Validator reasons); only
    # the attempt told them apart. A third regeneration over that prompt is billed again, and only a repeat of the same attempt is a hit.
    state = jobs.read(ended.id)
    assert read_reasons(state.room_id, artifacts) == []
    again = run_author(state.model_copy(update={"regeneration_count": 3}), provider=meta, artifacts=artifacts).calls[0]
    repeat = run_author(state, provider=meta, artifacts=artifacts).calls[0]
    assert (again.cached, repeat.cached) == (False, True)


def test_a_validator_reason_names_its_puzzle_by_the_riddlers_own_key_never_a_pz_id(loop, uploads):
    exit_leaks = with_puzzle("p5", clue="The way out wears 7342 on its face.")
    provider = riddler(reply(p5=None, p6=exit_leaks), reply())  # p5 left null, so p6 is the fifth puzzle drafted
    runner = loop(provider)
    done = runner.run(runner.submit(uploads).id)
    assert (done.status, done.regeneration_count) == ("done", 1)
    sent = chat_calls(provider)[1].messages[-1].content
    assert f"- rule 5, puzzle p6, field clue: {RULES[5].message}" in sent
    assert "pz_" not in sent and "7342" not in sent


def test_unreadable_output_is_rewritten_from_its_fixed_message_only(loop, uploads, artifacts, four_lock_room):
    unreadable = "not json: the Riddler muses on CLUE-NOISE-QZX"
    provider = riddler(unreadable, reply())
    runner = loop(provider)
    done = runner.run(runner.submit(uploads).id)
    assert (done.status, done.regeneration_count) == ("done", 1)
    assert read_reasons(done.room_id, artifacts) == []
    second = chat_calls(provider)[1]
    view = prompt_view(done.room_id, four_lock_room.interactables)
    assert second.messages == build_regeneration_prompt(view, [SHAPE_MESSAGE]).messages()
    sent = "\n".join(message.content for message in second.messages)
    assert f"- {SHAPE_MESSAGE}" in sent
    assert "not json" not in sent and "CLUE-NOISE-QZX" not in sent


def test_a_dry_run_refusal_is_rewritten_from_its_fixed_message(loop, uploads, doubles):
    provider = riddler(reply(), reply())
    dry_run_fails(doubles, attempts=1)
    runner = loop(provider)
    runner.run(runner.submit(uploads).id)
    sent = "\n".join(message.content for message in chat_calls(provider)[1].messages)
    assert f"- {DRY_MESSAGE}" in sent


def test_a_count_refusal_carries_its_fixed_message_beside_the_validator_reasons(artifacts, four_lock_room):
    reasons = [DraftReason(rule=5, key=None, field="clue", message=RULES[5].message)]
    artifacts.put(reasons_key(four_lock_room.id), REASONS.dump_json(reasons))
    sent_back = [SentBack(attempt=0, stage="validate", messages=[COUNT_MESSAGE, RULES[5].message])]
    state = JobState(id="job_00000000000000000000000001", status="running", stage="author", room_id=four_lock_room.id,
                     regen_max=2, regeneration_count=1, sent_back=sent_back)
    view = prompt_view(four_lock_room.id, four_lock_room.interactables)
    prompt = riddler_prompt(state, view, artifacts)
    assert prompt.messages() == build_regeneration_prompt(view, [COUNT_MESSAGE, *reasons]).messages()
    assert prompt.user.count(RULES[5].message) == 1


def test_a_failed_attempt_the_loop_cannot_record_ends_the_job_failed(loop, uploads, artifacts, monkeypatch):
    put = artifacts.put

    def broken_put(key: str, data: bytes) -> None:
        if key.endswith("/reasons.json"):
            raise OSError("the volume is gone")
        put(key, data)

    monkeypatch.setattr(artifacts, "put", broken_put)
    provider = riddler(reply(p2=LEAKY))
    runner = loop(provider)
    ended = runner.run(runner.submit(uploads).id)
    assert (ended.status, ended.stage, ended.error.code) == ("failed", "validate", "o_s_error")
    assert ended.regeneration_count == 0 and ended.sent_back == []
    assert [record.stage for record in ended.stages][-1] == "validate"


# --- Exhaustion ends the job needs_recapture ------------------------------------------


@pytest.mark.parametrize(("regen_max", "riddler_calls"), [(2, 3), (1, 2), (0, 1)])
def test_every_attempt_failing_ends_the_job_needs_recapture_after_regen_max_plus_one_riddler_calls(
    loop, uploads, artifacts, doubles, regen_max, riddler_calls
):
    provider = riddler(*[reply(p2=LEAKY)] * riddler_calls)  # one more call would find the script empty and fail the job
    runner = loop(provider, regen_max=regen_max)
    ended = runner.run(runner.submit(uploads).id)
    assert (ended.status, ended.stage, ended.error.code) == ("needs_recapture", "validate", "validation_error")
    assert len(chat_calls(provider)) == riddler_calls and ended.regeneration_count == regen_max
    assert [call.attempt for call in chat_calls(provider)] == list(range(riddler_calls))
    assert ended.sent_back == [SentBack(attempt=n, stage="validate", messages=[RULES[5].message]) for n in range(riddler_calls)]
    assert "415" not in json.dumps(ended.model_dump(mode="json")["sent_back"]) and "415" not in ended.error.message
    assert "dryrun" not in doubles.calls and "scene" not in doubles.calls
    with pytest.raises(KeyError):
        artifacts.read(room_key(ended.room_id))
    assert runner.run(ended.id) == ended and len(chat_calls(provider)) == riddler_calls


def test_no_error_class_or_code_for_an_exhausted_loop_exists_anywhere_in_the_codebase():
    needle = re.compile("regen" + "_?exhausted", re.IGNORECASE)
    roots = [REPO / "src", REPO / "scripts", REPO / "tests", REPO / "web" / "src"]
    files = [REPO / "main.py", *(path for root in roots for path in root.rglob("*") if path.suffix in {".py", ".ts", ".tsx", ".sh"})]
    assert [str(path.relative_to(REPO)) for path in files if needle.search(path.read_text())] == []


# --- One count across every gate, and its one writer ----------------------------------


def test_a_later_gate_and_unreadable_output_each_count_as_one_more_failed_attempt(loop, uploads, doubles):
    provider = riddler("The Riddler shrugs.", reply(p2=LEAKY), reply())
    seen = dry_run_fails(doubles, attempts=3)
    runner = loop(provider)
    ended = runner.run(runner.submit(uploads).id)
    assert (ended.status, ended.stage, ended.error.code) == ("needs_recapture", "dryrun", "dry_run_refused")
    assert ended.regeneration_count == 2 and seen == [2]
    assert ended.sent_back == [
        SentBack(attempt=0, stage="validate", messages=[SHAPE_MESSAGE]),
        SentBack(attempt=1, stage="validate", messages=[RULES[5].message]),
        SentBack(attempt=2, stage="dryrun", messages=[DRY_MESSAGE]),
    ]
    assert [record.stage for record in ended.stages][3:] == ["author", "author", "validate", "author", "validate", "dryrun"]


def test_a_dry_run_failure_sends_the_job_back_to_author_and_a_pass_proceeds(loop, uploads, doubles):
    provider = riddler(reply(), reply())
    dry_run_fails(doubles, attempts=1)
    runner = loop(provider)
    done = runner.run(runner.submit(uploads).id)
    assert (done.status, done.regeneration_count) == ("done", 1)
    assert done.sent_back == [SentBack(attempt=0, stage="dryrun", messages=[DRY_MESSAGE])]
    assert [record.stage for record in done.stages][3:] == ["author", "validate", "dryrun", "author", "validate", "dryrun", "story", "scene"]


def test_regenerate_is_the_only_writer_of_the_count():
    pipeline = REPO / "src" / "pipeline"
    assert "regeneration_count" not in (pipeline / "build.py").read_text()
    writes = re.compile(r"""["']regeneration_count["']\s*:|\.regeneration_count\s*[+-]?=(?!=)""")
    writers = [path.name for path in (REPO / "src").rglob("*.py") if writes.search(path.read_text())]
    assert writers == ["regenerate.py"]


class DiesOnTheFirstRewrite(MockProvider):
    """The Riddler's mock, whose process stops once, as attempt 1 begins."""

    died = False

    def chat(self, *args, **kwargs):
        if kwargs.get("attempt") == 1 and not self.died:
            self.died = True
            raise RunnerDied()
        return super().chat(*args, **kwargs)


def test_a_new_runner_resumes_a_regeneration_at_author_with_the_advanced_count(loop, uploads, jobs):
    provider = DiesOnTheFirstRewrite("riddler", MockScript(chat=[reply(p2=LEAKY), reply()]))
    queued = loop(provider).submit(uploads)
    with pytest.raises(RunnerDied):
        loop(provider).run(queued.id)
    left = jobs.read(queued.id)
    assert (left.status, left.stage, left.regeneration_count) == ("running", "author", 1)
    resumed = loop(provider).run(queued.id)
    assert (resumed.status, resumed.regeneration_count) == ("done", 1)
    assert [call.attempt for call in chat_calls(provider)] == [0, 1]
    assert [record.stage for record in resumed.stages][3:] == ["author", "validate", "author", "validate", "dryrun", "story", "scene"]
