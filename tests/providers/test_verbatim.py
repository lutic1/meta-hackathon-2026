"""Story 3.2: the verbatim adapter, the Greeting template and the AD-3 phraser boundary (AD-3, AD-5)."""

import ast
import importlib
import json
import pkgutil
import socket
import time
from pathlib import Path

import pytest

import src.providers
from src.domain.schema import Derived, Room
from src.providers.base import HintPhraser, PhraserResponse
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import MockProvider
from src.providers.verbatim import (
    GREETING_ASKED_EARLY,
    GREETING_HELD_OUT,
    GREETING_KEPT_GOING,
    GREETING_NEVER_ASKED,
    GREETING_TEMPLATES,
    VerbatimPhraser,
    greeting_template,
)
from tests.fixtures.rooms import (
    SENTINEL_CODE,
    SENTINEL_FIND,
    SENTINEL_ORDER,
    SENTINEL_PAIR,
    with_sentinel_solutions,
)

REPO = Path(__file__).resolve().parents[2]
PHRASER_MODULES = {"src.providers.verbatim", "src.providers.ollama"}
RUNG_NAMES = ("nudge", "direction", "near_answer")
OTHER_CLOCKS = ("time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "process_time", "thread_time")


def _derived(persistence: float, time_to_first_hint_s: float | None = 42.5) -> Derived:
    return Derived(sessions=3, persistence=persistence, time_to_first_hint_s=time_to_first_hint_s,
                   mean_rung_per_lock_type={"code": 1.5, "find": 0.5})


def _refuse_sockets(monkeypatch):
    def refuse(self, address):
        raise AssertionError(f"the verbatim adapter opened a socket to {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


class FakeClock:
    """`perf_counter_ns` replacement: counts reads and advances 1.6 s per read."""

    def __init__(self) -> None:
        self.reads = 0

    def __call__(self) -> int:
        self.reads += 1
        return self.reads * 1_600_000_000


# --- phrase ---------------------------------------------------------------


@pytest.mark.parametrize("rung_text", ["Look by the hooks.", "  two  spaces\tand a tab\n", "", "ünïcödé — ‘quotes’ 7342"])
def test_phrase_returns_the_rung_text_byte_for_byte_not_phrased(rung_text, monkeypatch):
    _refuse_sockets(monkeypatch)
    reply = VerbatimPhraser().phrase(rung_text, _derived(0.9))
    assert isinstance(reply, PhraserResponse)
    assert reply.text == rung_text and reply.text.encode() == rung_text.encode()
    assert reply.phrased is False
    assert isinstance(reply.latency_ms, int) and reply.latency_ms >= 0


def test_phrase_ignores_the_derived_block():
    texts = {VerbatimPhraser().phrase("Check the time.", d).text for d in (_derived(1), _derived(-1), _derived(0, None))}
    assert texts == {"Check the time."}


def test_the_adapter_is_the_verbatim_guide_with_no_model():
    phraser = VerbatimPhraser()
    assert isinstance(phraser, HintPhraser)
    assert phraser.name == "verbatim" and phraser.guide_model is None


# --- no network, no clock beyond the latency ------------------------------


@pytest.mark.parametrize("call", ["phrase", "greet"])
def test_each_call_reads_the_clock_twice_for_its_latency_and_nothing_else(call, monkeypatch):
    _refuse_sockets(monkeypatch)
    clock = FakeClock()
    monkeypatch.setattr("src.providers.verbatim.perf_counter_ns", clock)
    for name in OTHER_CLOCKS:
        monkeypatch.setattr(time, name, lambda *a, name=name: pytest.fail(f"the verbatim adapter read time.{name}"))
    args = ("Study the shelf.", _derived(0.2)) if call == "phrase" else (_derived(0.2),)
    reply = getattr(VerbatimPhraser(), call)(*args)
    assert clock.reads == 2
    assert reply.latency_ms == 1600 and reply.phrased is False


def test_the_module_imports_only_perf_counter_ns_as_a_clock_and_no_http_client():
    tree = ast.parse((REPO / "src/providers/verbatim.py").read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    clocks = {name for name in imported if name.split(".")[0] in ("time", "datetime")}
    assert clocks == {"time.perf_counter_ns"}
    assert not {name for name in imported if name.split(".")[0] in ("httpx", "socket", "ollama", "urllib", "requests")}


# --- greet: the Greeting template ------------------------------------------


@pytest.mark.parametrize(("persistence", "template"), [
    (0.34, GREETING_KEPT_GOING),
    (0.335, GREETING_KEPT_GOING),  # rounds to 0.34
    (0.33, GREETING_HELD_OUT),
    (-0.33, GREETING_HELD_OUT),
    (-0.335, GREETING_ASKED_EARLY),  # rounds to -0.34
    (-0.34, GREETING_ASKED_EARLY),
    (1 / 3, GREETING_HELD_OUT),
    (-1 / 3, GREETING_HELD_OUT),
    (1.0, GREETING_KEPT_GOING),
    (0.0, GREETING_HELD_OUT),
    (-1.0, GREETING_ASKED_EARLY),
])
def test_greet_chooses_the_band_on_persistence_rounded_to_two_decimals(persistence, template):
    reply = VerbatimPhraser().greet(_derived(persistence))
    assert reply.text == template and greeting_template(_derived(persistence)) == template
    assert reply.phrased is False and isinstance(reply.latency_ms, int)


@pytest.mark.parametrize("persistence", [1.0, 0.34, 0.0, -0.34, -1.0])
def test_a_null_time_to_first_hint_wins_over_every_persistence_band(persistence):
    assert VerbatimPhraser().greet(_derived(persistence, None)).text == GREETING_NEVER_ASKED


def test_a_fresh_profile_also_reads_as_never_asked():
    assert VerbatimPhraser().greet(Derived.fresh()).text == GREETING_NEVER_ASKED


def test_the_four_templates_are_the_ux_contract_lines():
    assert GREETING_TEMPLATES == (
        "Welcome back. Last time you never asked me once; let's see what this room makes of you.",
        "Welcome back. Last time you kept going long past my first nudge; let's see what this room makes of you.",
        "Welcome back. Last time you held out a good while before asking; let's see what this room makes of you.",
        (
            "Welcome back. Last time you held out just long enough to get your bearings before asking; "
            "let's see what this room makes of you."
        ),
    )


def test_no_template_names_an_object_or_a_solution(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    words = {w for ix in room.interactables for w in ix.label.split()}
    ids = {ix.id for ix in room.interactables} | {pz.id for pz in room.puzzles} | {room.id}
    for template in GREETING_TEMPLATES:
        lowered = template.lower()
        assert not any(w in lowered.split() for w in words), template
        assert not any(token in template for token in (*ids, SENTINEL_CODE, *SENTINEL_ORDER, SENTINEL_FIND))
        assert "ix_" not in template and "pz_" not in template and "room_" not in template
        assert not any(ch.isdigit() for ch in template)


# --- only the verbatim and Ollama adapters implement the port ------------


def _phraser_classes() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for info in pkgutil.iter_modules(src.providers.__path__, "src.providers."):
        module = importlib.import_module(info.name)
        names = [name for name, obj in vars(module).items()
                 if isinstance(obj, type) and issubclass(obj, HintPhraser) and obj is not HintPhraser
                 and obj.__module__ == info.name]
        if names:
            found[info.name] = names
    return found


def test_only_the_verbatim_and_ollama_adapters_implement_the_port():
    implementers = _phraser_classes()
    assert set(implementers) <= PHRASER_MODULES, implementers
    assert implementers["src.providers.verbatim"] == ["VerbatimPhraser"]
    for adapter in (MockProvider, MetaModelProvider):
        assert not issubclass(adapter, HintPhraser) and not hasattr(adapter, "phrase")


# --- AD-3: the phraser sees exactly (rung_text, derived) ------------------


class RecordingPhraser(HintPhraser):
    name = "recording"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def phrase(self, *args, **kwargs) -> PhraserResponse:
        self.calls.append(("phrase", args, kwargs))
        return PhraserResponse(text="recorded", phrased=True, latency_ms=1)

    def greet(self, *args, **kwargs) -> PhraserResponse:
        self.calls.append(("greet", args, kwargs))
        return PhraserResponse(text="recorded", phrased=True, latency_ms=1)


def _caller(room: Room, phraser: HintPhraser, derived: Derived) -> None:
    """What a play caller does with the Room it holds: one `phrase` per Rung, then `greet`."""
    for puzzle in room.puzzles:
        for name in RUNG_NAMES:
            phraser.phrase(getattr(puzzle.rungs, name), derived)
    phraser.greet(derived)


def test_phrase_and_greet_receive_exactly_the_rung_text_and_the_derived_block(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    derived = _derived(0.4173, 137.9)
    rungs = [getattr(pz.rungs, name) for pz in room.puzzles for name in RUNG_NAMES]
    phraser = RecordingPhraser()
    _caller(room, phraser, derived)

    phrase_calls = [c for c in phraser.calls if c[0] == "phrase"]
    greet_calls = [c for c in phraser.calls if c[0] == "greet"]
    assert len(phrase_calls) == len(rungs) == 15 and len(greet_calls) == 1
    assert [args for _, args, _ in phrase_calls] == [(rung, derived) for rung in rungs]
    assert all(kwargs == {} for _, _, kwargs in phraser.calls)
    assert greet_calls[0][1] == (derived,)
    for _, args, _ in phrase_calls:
        assert type(args[0]) is str and type(args[1]) is Derived
    assert type(greet_calls[0][1][0]) is Derived


def test_no_sentinel_solution_label_clue_lore_other_rung_or_id_reaches_the_phraser(four_lock_room: Room):
    room = with_sentinel_solutions(four_lock_room)
    phraser = RecordingPhraser()
    _caller(room, phraser, _derived(0.4173, 137.9))

    rungs = {getattr(pz.rungs, name) for pz in room.puzzles for name in RUNG_NAMES}
    ids = {ix.id for ix in room.interactables} | {pz.id for pz in room.puzzles} | {room.id}
    labels = {ix.label for ix in room.interactables}
    clues_and_lore = {pz.clue for pz in room.puzzles} | {pz.lore for pz in room.puzzles}
    solutions = {SENTINEL_CODE, json.dumps(SENTINEL_ORDER), " ".join(SENTINEL_ORDER), " ".join(SENTINEL_PAIR), SENTINEL_FIND}

    for kind, args, _ in phraser.calls:
        seen = [a if isinstance(a, str) else a.model_dump_json() for a in args]
        blob = json.dumps(seen)
        assert not any(token in blob for token in ids | clues_and_lore | solutions), (kind, seen)
        assert "ix_" not in blob and "pz_" not in blob and "room_" not in blob and "solution" not in blob
        if kind == "phrase":  # the Rung text itself, whole, and nothing of the room around it
            assert seen[0] in rungs
            assert not any(other in seen[0] for other in rungs - {seen[0]}), seen[0]
        derived_json = seen[-1]
        assert set(json.loads(derived_json)) == set(Derived.model_fields)
        assert not any(label in derived_json or label.split()[-1] in derived_json for label in labels)
