"""`scripts/story_demo_room.py` writes the story stage's lines onto a Demo room built before story mode: room.json only, read back after the write.

No test reaches Modal: the Dicts are plain dicts, the Volume a temporary
directory behind a stub that logs `commit` and `reload`, the storyteller the
mock provider, and the container run is replaced by `story_demo_room` over
those handles.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from src.config import Settings
from src.domain.schema import Room
from src.infra.modal import ModalHandles, VolumeCache
from src.pipeline.ports import room_key
from src.pipeline.story import template_story
from src.providers.mock import MockProvider, MockScript
from src.providers.spend import SpendLedger
from tests.infra.test_modal import RecordingDict, StubVolume, seed_demo
from tests.pipeline.test_story_stage import GOOD, story_reply
from tests.scripts.test_seed_rooms import JOB, full_job, snapshot

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/story_demo_room.py"


def _load():
    spec = importlib.util.spec_from_file_location("story_demo_room_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


teller = _load()


@pytest.fixture
def handles(tmp_path: Path) -> ModalHandles:
    return ModalHandles(jobs=RecordingDict(), sessions=RecordingDict(), ledger=RecordingDict(), volume=StubVolume([]), root=tmp_path / "data")


@pytest.fixture
def demo(handles: ModalHandles, four_lock_room: Room) -> Room:
    """A Demo room built before story mode: its Room with no story, its photos and its `done` job record."""
    assert four_lock_room.story is None
    seed_demo(handles, four_lock_room, full_job(four_lock_room))
    return four_lock_room


def storyteller(*texts: str) -> MockProvider:
    return MockProvider("storyteller", MockScript(chat=list(texts)))


def run(monkeypatch, handles: ModalHandles, provider: MockProvider, *argv: str) -> tuple[int, list[str]]:
    """`main` with the container run replaced by `story_demo_room` over `handles` and `provider`; the status and the Environments it ran in."""
    environments: list[str] = []

    def run_remote(environment: str, *, room_id: str, dry_run: bool) -> int:
        environments.append(environment)
        return teller.story_demo_room(handles, room_id, provider=provider, dry_run=dry_run)

    monkeypatch.setattr(teller, "run_remote", run_remote)
    return teller.main(list(argv)), environments


def stored(handles: ModalHandles, room: Room) -> Room:
    return Room.model_validate_json((handles.root / "rooms/demo" / room_key(room.id)).read_bytes())


# --- The dry run ------------------------------------------------------------------


def test_the_dry_run_prints_the_brief_every_slot_its_path_and_the_spend_and_writes_nothing(monkeypatch, handles, demo, capsys):
    before = snapshot(handles.root)
    provider = storyteller(story_reply())
    status, environments = run(monkeypatch, handles, provider, "--env", "dev", "--room", demo.id, "--dry-run")
    assert status == 0 and environments == ["dev"]
    out = capsys.readouterr().out
    assert out.startswith("Modal Environment: dev\nbrief: StoryBrief(")
    for slot in ("architect_welcome", "trickster_trap", "riddler_entrance", "guide_chest", "trickster_closing",
                 "riddler_closing", "guide_closing_no_hints", "guide_closing_hints"):
        assert f"{slot}: {GOOD[slot]}\n" in out, slot
    for n, riddle in enumerate(GOOD["riddles"], start=1):
        assert f") opening: {riddle['opening']}\n" in out and f"riddle {n} (pz_" in out
    assert "story from model attempt 0 (mock-chat-1); spend $0.0000 over 1 calls (0 cached)" in out
    assert "dry run: nothing written" in out
    assert snapshot(handles.root) == before


# --- The write ------------------------------------------------------------------


def test_a_real_run_writes_the_story_onto_room_json_alone_and_reads_it_back(monkeypatch, handles, demo, capsys):
    folder = handles.root / "rooms/demo" / demo.id
    before = snapshot(folder)
    provider = storyteller(story_reply())
    status, _ = run(monkeypatch, handles, provider, "--room", demo.id)
    assert status == 0
    after = snapshot(folder)
    assert {name for name in after if after[name] != before[name]} == {"room.json"} and after.keys() == before.keys()
    room = stored(handles, demo)
    assert room.story is not None and room.story.architect_welcome == GOOD["architect_welcome"]
    assert room == demo.model_copy(update={"story": room.story})
    assert [riddle.puzzle_id for riddle in room.story.riddles] == [p.id for p in sorted(demo.puzzles, key=lambda p: p.is_exit)]
    assert [(call.job_id, call.stage, call.attempt) for call in provider.calls] == [(JOB, "story", 0)]
    out = capsys.readouterr().out
    assert f"storied {demo.id}: " in out and "read back equal" in out and "Modal Environment: main\n" in out


def test_a_refused_reply_is_sent_back_once_then_the_templates_are_written(monkeypatch, handles, demo, capsys):
    leaky = story_reply(guide_chest="Stuck? Look inside the model for the answer!")
    provider = storyteller(leaky, leaky)
    status, _ = run(monkeypatch, handles, provider, "--room", demo.id)
    assert status == 0
    assert [call.attempt for call in provider.calls] == [0, 1]
    assert stored(handles, demo).story == template_story(demo)
    assert "story from the fixed templates" in capsys.readouterr().out


def test_a_retried_reply_that_passes_is_kept_and_named_as_attempt_1(monkeypatch, handles, demo, capsys):
    provider = storyteller(story_reply(riddler_closing=""), story_reply())
    assert run(monkeypatch, handles, provider, "--room", demo.id, "--dry-run")[0] == 0
    assert "story from model attempt 1 (mock-chat-1); spend $0.0000 over 2 calls" in capsys.readouterr().out


# --- Refusals: exit 1, no call, nothing written -----------------------------------


@pytest.mark.parametrize("room_id", ["room_01JBDEM0R00M00000000000000", "../judge/x", "not-a-room"])
@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_an_id_that_is_not_a_demo_room_is_refused(monkeypatch, handles, demo, capsys, room_id, flags):
    before = snapshot(handles.root)
    provider = storyteller(story_reply())
    assert run(monkeypatch, handles, provider, "--room", room_id, *flags)[0] == 1
    assert "refused, nothing written" in capsys.readouterr().err
    assert provider.calls == [] and snapshot(handles.root) == before


def test_a_judge_room_is_not_a_demo_room(monkeypatch, handles, code_and_find_room, capsys):
    folder = handles.root / "rooms/judge" / code_and_find_room.id
    folder.mkdir(parents=True)
    (folder / "room.json").write_bytes(code_and_find_room.model_dump_json().encode())
    provider = storyteller(story_reply())
    assert run(monkeypatch, handles, provider, "--room", code_and_find_room.id)[0] == 1
    assert "no Demo room" in capsys.readouterr().err
    assert provider.calls == [] and (folder / "room.json").read_bytes() == code_and_find_room.model_dump_json().encode()


def test_a_demo_room_without_its_job_record_is_refused(monkeypatch, handles, four_lock_room, capsys):
    seed_demo(handles, four_lock_room)
    provider = storyteller(story_reply())
    assert run(monkeypatch, handles, provider, "--room", four_lock_room.id)[0] == 1
    assert "no job record" in capsys.readouterr().err and provider.calls == []


# --- The hosted provider and the container --------------------------------------


def test_the_storyteller_is_the_hosted_builds_over_the_hosted_cache_and_ledger(monkeypatch, handles):
    seen: dict[str, Any] = {}

    def model_providers(settings, cache, ledger):
        seen.update(settings=settings, cache=cache, ledger=ledger)
        return {"storyteller": "the storyteller"}

    monkeypatch.setattr(teller, "model_providers", model_providers)
    settings = Settings(mode="hosted")
    assert teller.storyteller(settings, handles) == "the storyteller"
    assert seen["settings"] is settings and isinstance(seen["cache"], VolumeCache)
    assert isinstance(seen["ledger"], SpendLedger) and seen["ledger"]._store.ledger is handles.ledger


def test_the_container_app_mounts_the_volume_and_the_secret_from_the_named_environment_without_contacting_modal(monkeypatch):
    import modal

    named: list[tuple[str, str, dict[str, Any]]] = []
    volume, secret = modal.Volume.from_name, modal.Secret.from_name
    monkeypatch.setattr(modal.Volume, "from_name", lambda name, **kw: named.append(("Volume", name, kw)) or volume(name, **kw))
    monkeypatch.setattr(modal.Secret, "from_name", lambda name, **kw: named.append(("Secret", name, kw)) or secret(name, **kw))

    app, function = teller.story_app("dev")

    assert app.name == "keyframe-story" and isinstance(function, modal.Function)
    assert named == [("Volume", "keyframe-data", {"environment_name": "dev"}), ("Secret", "keyframe", {"environment_name": "dev"})]
    source = SCRIPT.read_text()
    assert "create_if_missing=" not in source and '"MODE": "hosted"' in source
