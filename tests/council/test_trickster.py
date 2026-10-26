"""Story 4.3: the `TricksterSource` port, the recorded-proposals artifact and the scripted source (FR-25, AD-12, AD-15)."""

import ast
import inspect
import json
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from src.config import Settings
from src.council.trickster import (
    AUTHORED_PROPOSALS,
    RECORDED_PROPOSALS,
    SOURCES,
    RecordedProposals,
    ScriptedSource,
    TricksterProposal,
    TricksterSource,
    load_proposals,
)
from src.domain.edits import apply_edit, check_edit
from src.domain.redact import to_prompt_view
from src.domain.schema import Room, TricksterEdit, ValidatorResult
from src.domain.session import GameStateSummary, SessionStateMachine, game_state_summary
from src.domain.validator import BOUNDS_MESSAGE, RULES, _leaks, _solution_labels
from src.infra.local import ROOMS_ROOT
from src.pipeline.ports import room_key
from tests.domain.test_edits import window_state
from tests.domain.test_session import SESSION, click, code
from tests.domain.test_trickster_windows import WINDOW, skipped
from tests.fixtures.rooms import IX, PZ, ROOM_IDS

REPO = Path(__file__).resolve().parents[2]
FIXTURE_FILE = REPO / "tests/fixtures/proposals/four_lock.json"
"""The pre-authored file for the 1.6 four-lock room: window 0 passes, window 1 is written to fail."""
OTHER_ROOM = ROOM_IDS["code_and_find"]
NOT_CHECKED = ValidatorResult(ok=False, reasons=[])
FIXED_MESSAGES = {rule.message for rule in RULES.values()} | {BOUNDS_MESSAGE}

FIRST = {
    "type": "decoy", "puzzle": PZ["shelf_order"],
    "payload": {"type": "decoy", "interactable": IX["rug"], "visible_attribute": "faded red"},
}
SECOND = {
    "type": "loosen", "puzzle": PZ["clock_code"],
    "payload": {"type": "loosen", "puzzle": PZ["clock_code"], "rung": "direction"},
}


def artifact(room_id: str = ROOM_IDS["four_lock"], *proposals: dict[str, Any]) -> dict[str, Any]:
    return {"room_id": room_id, "proposals": list(proposals or (FIRST, SECOND))}


def write(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


def summary(elapsed_ms: int = 0, rungs_used: int = 0) -> GameStateSummary:
    return GameStateSummary(locks_open=[], elapsed_ms=elapsed_ms, rungs_used=rungs_used)


def as_edit(proposal: TricksterProposal, window: int) -> TricksterEdit:
    """The edit the route builds around a proposal, before the Validator has run."""
    return TricksterEdit.model_validate({
        **proposal.model_dump(), "id": f"te_{window + 1:026d}",
        "validator_result": NOT_CHECKED.model_dump(), "accepted": False, "window": window,
    })


# --- The artifact ------------------------------------------------------------------


def test_an_artifact_loads_one_room_id_and_its_proposals_in_window_order(tmp_path: Path):
    loaded = load_proposals(write(tmp_path / "recorded.json", artifact()))
    assert loaded.room_id == ROOM_IDS["four_lock"]
    assert [p.model_dump() for p in loaded.proposals] == [FIRST, SECOND]
    assert [p.type for p in loaded.proposals] == ["decoy", "loosen"]


@pytest.mark.parametrize("edit_type", ["decoy", "merge", "loosen", "shortcut"])
def test_each_edit_type_loads_with_its_payload(edit_type: str):
    payloads = {
        "decoy": FIRST["payload"],
        "merge": {"type": "merge", "puzzle_a": PZ["find_key"], "puzzle_b": PZ["clock_code"]},
        "loosen": SECOND["payload"],
        "shortcut": {"type": "shortcut", "puzzle": PZ["door_code"], "requires": PZ["shelf_order"]},
    }
    proposal = TricksterProposal.model_validate({"type": edit_type, "puzzle": PZ["clock_code"], "payload": payloads[edit_type]})
    assert proposal.payload.type == edit_type


@pytest.mark.parametrize("verdict", [{"validator_result": NOT_CHECKED.model_dump()}, {"accepted": True}])
def test_an_artifact_carrying_a_verdict_fails_to_load(tmp_path: Path, verdict: dict[str, Any]):
    in_a_proposal = write(tmp_path / "proposal.json", artifact(ROOM_IDS["four_lock"], {**FIRST, **verdict}, SECOND))
    at_the_top = write(tmp_path / "top.json", {**artifact(), **verdict})
    for path in (in_a_proposal, at_the_top):
        with pytest.raises(ValidationError):
            load_proposals(path)


def test_a_payload_of_another_type_fails_to_load():
    with pytest.raises(ValidationError):
        TricksterProposal.model_validate({**FIRST, "type": "merge"})


# --- The scripted source -----------------------------------------------------------


def scripted_on(tmp_path: Path) -> TricksterSource:
    """`DEMO_TRICKSTER=scripted` resolved through the source table over a two-proposal artifact for the four-lock room."""
    write(tmp_path / RECORDED_PROPOSALS, artifact())
    settings = Settings.from_env({"DEMO_TRICKSTER": "scripted"})
    return SOURCES[settings.demo_trickster](tmp_path)


def test_the_scripted_source_yields_each_windows_proposal_in_a_session_on_its_room(tmp_path: Path, four_lock_room: Room):
    source = scripted_on(tmp_path)
    machine = SessionStateMachine(four_lock_room)
    view = to_prompt_view(four_lock_room)

    first = machine.replay(SESSION, [click("key", WINDOW)])
    second = machine.replay(SESSION, [click("key", WINDOW), skipped(WINDOW + 1), code("clock_code", "415", 2 * WINDOW + 1)])
    assert (first.trickster_window.index, second.trickster_window.index) == (0, 1)

    yielded = [
        source.propose(four_lock_room.id, state.trickster_window.index or 0, view, game_state_summary(state, t))
        for state, t in ((first, WINDOW), (second, 2 * WINDOW + 1))
    ]
    assert [p.model_dump() if p else None for p in yielded] == [FIRST, SECOND]


def test_the_room_view_and_summary_never_change_what_the_scripted_source_yields(tmp_path: Path, four_lock_room: Room, code_and_find_room: Room):
    source = scripted_on(tmp_path)
    room_id = four_lock_room.id
    for window, expected in ((0, FIRST), (1, SECOND)):
        answers = [
            source.propose(room_id, window, to_prompt_view(room), state)
            for room in (four_lock_room, code_and_find_room)
            for state in (summary(), summary(elapsed_ms=900_000, rungs_used=5))
            for _ in range(2)
        ]
        assert all(answer is not None and answer.model_dump() == expected for answer in answers)


def test_another_room_or_a_used_up_recording_yields_no_proposal(tmp_path: Path, four_lock_room: Room):
    source = scripted_on(tmp_path)
    view = to_prompt_view(four_lock_room)
    assert source.propose(OTHER_ROOM, 0, view, summary()) is None
    assert source.propose(OTHER_ROOM, 1, view, summary()) is None
    assert source.propose(four_lock_room.id, 2, view, summary()) is None
    assert source.propose(four_lock_room.id, 7, view, summary()) is None


def test_a_fresh_session_on_the_room_starts_at_window_0_and_gets_the_first_proposal_again(tmp_path: Path, four_lock_room: Room):
    source = scripted_on(tmp_path)
    view = to_prompt_view(four_lock_room)
    for window in (0, 1, 2):
        source.propose(four_lock_room.id, window, view, summary())
    fresh = SessionStateMachine(four_lock_room).replay("sess_01ARZ3NDEKTSV4RRFFQ69G5FAW", [click("key", WINDOW)])
    assert fresh.trickster_window.index == 0
    again = source.propose(four_lock_room.id, fresh.trickster_window.index, view, game_state_summary(fresh, WINDOW))
    assert again is not None and again.model_dump() == FIRST


def test_changing_a_yielded_proposal_never_changes_a_later_answer(tmp_path: Path, four_lock_room: Room):
    source = scripted_on(tmp_path)
    view = to_prompt_view(four_lock_room)
    first = source.propose(four_lock_room.id, 0, view, summary())
    assert first is not None
    first.puzzle = PZ["clock_code"]
    first.payload.visible_attribute = "changed"  # type: ignore[union-attr]
    again = source.propose(four_lock_room.id, 0, view, summary())
    assert again is not None and again.model_dump() == FIRST


def test_the_scripted_source_holds_nothing_but_its_recording():
    assert [field for field in ScriptedSource.__dataclass_fields__] == ["recording"]
    assert ScriptedSource.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_the_scripted_source_makes_no_model_call_and_writes_no_ledger_entry(tmp_path: Path, monkeypatch, four_lock_room: Room):
    tree = ast.parse((REPO / "src/council/trickster.py").read_text())
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    } | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not [name for name in imported if name.startswith(("src.providers", "src.infra", "src.pipeline", "src.api"))]
    assert list(inspect.signature(SOURCES["scripted"]).parameters) == ["root"]

    monkeypatch.chdir(tmp_path)
    source = scripted_on(tmp_path)
    before = sorted(tmp_path.rglob("*"))
    for window in range(3):
        source.propose(four_lock_room.id, window, to_prompt_view(four_lock_room), summary())
    assert sorted(tmp_path.rglob("*")) == before  # no spend/ledger.jsonl, nothing written


# --- The source table --------------------------------------------------------------


def test_scripted_and_authored_map_to_the_scripted_source_over_their_own_files(tmp_path: Path, four_lock_room: Room):
    write(tmp_path / RECORDED_PROPOSALS, artifact(ROOM_IDS["four_lock"], FIRST))
    write(tmp_path / AUTHORED_PROPOSALS, artifact(ROOM_IDS["four_lock"], SECOND))
    view = to_prompt_view(four_lock_room)
    scripted, authored = SOURCES["scripted"](tmp_path), SOURCES["authored"](tmp_path)
    assert isinstance(scripted, ScriptedSource) and isinstance(authored, ScriptedSource)
    assert scripted.propose(four_lock_room.id, 0, view, summary()).model_dump() == FIRST  # type: ignore[union-attr]
    assert authored.propose(four_lock_room.id, 0, view, summary()).model_dump() == SECOND  # type: ignore[union-attr]


def test_the_source_table_holds_the_scripted_values_and_leaves_live_and_record_to_the_live_source():
    values = set(get_args(Settings.model_fields["demo_trickster"].annotation))
    assert values == {"live", "record", "scripted", "authored"}
    assert set(SOURCES) == {"scripted", "authored"}
    assert values - set(SOURCES) == {"live", "record"}


# --- Pre-authored files through the live Validator -------------------------------------


def window_outcomes(room: Room, recording: RecordedProposals) -> list[ValidatorResult]:
    """Each proposal through the bounds and `validate(apply_edit(...))` in window order, folding the accepted ones."""
    results = []
    for window, proposal in enumerate(recording.proposals):
        edit = as_edit(proposal, window)
        result = check_edit(room, window_state(room, "open", window), edit)
        if result.ok:
            room = apply_edit(room, edit)
        results.append(result)
    return results


def assert_no_solution(room: Room, path: Path, recording: RecordedProposals) -> None:
    text = path.read_text()
    assert "solution" not in text
    for proposal in recording.proposals:
        strings = _strings(proposal.model_dump())
        for puzzle in room.puzzles:
            labels = _solution_labels(room, puzzle)
            assert not [s for s in strings if _leaks(s, puzzle, labels)], (puzzle.id, strings)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


def assert_one_passes_and_one_is_rejected(room: Room, path: Path) -> list[ValidatorResult]:
    recording = load_proposals(path)
    assert recording.room_id == room.id and len(recording.proposals) == 2
    results = window_outcomes(room, recording)
    assert sorted(result.ok for result in results) == [False, True]
    rejected = next(result for result in results if not result.ok)
    assert rejected.reasons and {reason.message for reason in rejected.reasons} <= FIXED_MESSAGES
    assert_no_solution(room, path, recording)
    return results


def test_the_fixture_file_passes_window_0_and_rejects_window_1_with_a_fixed_message(four_lock_room: Room):
    results = assert_one_passes_and_one_is_rejected(four_lock_room, FIXTURE_FILE)
    assert [result.ok for result in results] == [True, False]
    assert results[1].reasons[0].message == RULES[1].message  # the merge would make two locks wait on each other


def test_the_demo_rooms_cut_1_file_passes_one_and_rejects_one():
    path = REPO / AUTHORED_PROPOSALS
    if not path.exists():
        # Open follow-up (sprint-status, 4.3 AC 4): once the demo Room is captured, commit this file
        # with one passing and one failing proposal and drop this branch, so only a missing Room skips.
        pytest.skip(f"{AUTHORED_PROPOSALS} is an open 4.3 follow-up, blocked on capturing the demo Room")
    room_path = REPO / ROOMS_ROOT / room_key(load_proposals(path).room_id)
    if not room_path.exists():
        pytest.skip("the demo Room is not in the local rooms/")
    assert_one_passes_and_one_is_rejected(Room.model_validate_json(room_path.read_text()), path)


def test_the_cut_1_file_lives_outside_the_git_ignored_rooms_folder():
    assert AUTHORED_PROPOSALS.parts[0] not in {"rooms", "photos", "captures", "uploads", ".cache", "cache"}
    assert RECORDED_PROPOSALS.parts[0] not in {"rooms", "photos", "captures", "uploads", ".cache", "cache"}
