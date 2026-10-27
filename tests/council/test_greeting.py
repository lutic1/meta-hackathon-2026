"""Story 5.5: the Greeting composer over the Derived block (AD-3, AD-5, AD-8)."""

import ast
import inspect
import json
import socket
from pathlib import Path

import pytest

from src.api.wiring import hint_phraser
from src.config import Settings
from src.council.architect import build_architect_prompt
from src.council.dryrun import build_dry_run_prompt
from src.council.greeting import Greeting, compose_greeting
from src.council.riddler import DraftReason, build_author_prompt, build_regeneration_prompt
from src.domain.ledger import LedgerEntry
from src.domain.redact import to_prompt_view
from src.domain.schema import (
    CodeInput,
    Derived,
    DryRunAnswers,
    GuideModel,
    HintRequestEvent,
    LockInputEvent,
    OpeningLineEvent,
    Room,
    SessionStart,
)
from src.domain.session import SessionStateMachine
from src.providers.base import HintPhraser, PhraserResponse
from src.providers.cache import cache_key
from src.providers.verbatim import GREETING_TEMPLATES, VerbatimPhraser, greeting_template
from tests.fixtures.rooms import SENTINEL_CODE, SENTINEL_FIND, SENTINEL_ORDER, SENTINEL_PAIR, with_sentinel_solutions

REPO = Path(__file__).resolve().parents[2]
SESSION_ID = f"sess_{'0' * 25}1"
SENTINEL_DERIVED = Derived(
    sessions=8641, persistence=0.4173, time_to_first_hint_s=137.9, mean_rung_per_lock_type={"code": 2.71, "find": 1.37}
)
SENTINEL_VALUES = ("8641", "0.4173", "137.9", "2.71", "1.37")
DERIVED_KEYS = ("derived", *Derived.model_fields)
PHRASED_LINE = "Back again. You outlasted my first nudge last time; let's see if this room is as patient as you."

# Where the Derived block may be named under src/: its schema, the Guide port and its two adapters, the
# composer, the rung selection and the domain and API code that carry it from the session start to those.
DERIVED_MODULES = {
    "src.domain.schema",
    "src.domain.session",
    "src.domain.rungs",
    "src.providers.base",
    "src.providers.verbatim",
    "src.providers.ollama",
    "src.council.greeting",
}
DERIVED_PACKAGES = ("src.api",)


def _derived(persistence: float, time_to_first_hint_s: float | None = 42.5) -> Derived:
    return Derived(sessions=1, persistence=persistence, time_to_first_hint_s=time_to_first_hint_s,
                   mean_rung_per_lock_type={"code": 1.5, "find": 0.5})


class GuidePhraser(HintPhraser):
    """What the Ollama adapter looks like to the composer: a Guide model that phrases, or falls back at 5 s."""

    name = "ollama"
    guide_model = GuideModel(id="llama3.2:3b", host="this Mac")

    def __init__(self, *, fallback: bool = False) -> None:
        self.fallback = fallback
        self.calls: list[tuple[str, tuple, dict]] = []

    def phrase(self, *args, **kwargs) -> PhraserResponse:
        self.calls.append(("phrase", args, kwargs))
        return PhraserResponse(text=args[0], phrased=False, latency_ms=0)

    def greet(self, *args, **kwargs) -> PhraserResponse:
        self.calls.append(("greet", args, kwargs))
        if self.fallback:
            return PhraserResponse(text=greeting_template(args[0]), phrased=False, latency_ms=5000)
        return PhraserResponse(text=PHRASED_LINE, phrased=True, latency_ms=1800)


def _verbatim_guide() -> HintPhraser:
    return hint_phraser(Settings.from_env({"GUIDE": "verbatim"}))


def _refuse_sockets(monkeypatch):
    def refuse(self, address):
        raise AssertionError(f"a Guide model was called at {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


# --- GUIDE=verbatim, or the Guide model past 5 s or unreachable: the template ------------------


@pytest.mark.parametrize("guide", ["verbatim", "fallback"])
@pytest.mark.parametrize(("derived", "template"), [
    (_derived(0.9, None), GREETING_TEMPLATES[0]),
    (_derived(0.34), GREETING_TEMPLATES[1]),
    (_derived(1.0), GREETING_TEMPLATES[1]),
    (_derived(0.33), GREETING_TEMPLATES[2]),
    (_derived(0.0), GREETING_TEMPLATES[2]),
    (_derived(-0.33), GREETING_TEMPLATES[2]),
    (_derived(-0.34), GREETING_TEMPLATES[3]),
    (_derived(-1.0), GREETING_TEMPLATES[3]),
])
def test_the_template_answers_verbatim_in_the_contract_order(guide, derived, template):
    phraser = _verbatim_guide() if guide == "verbatim" else GuidePhraser(fallback=True)
    greeting = compose_greeting(phraser, derived)
    assert greeting.text == template
    assert greeting.path == "template"


def test_under_guide_verbatim_the_path_is_the_template_because_no_guide_model_runs(monkeypatch):
    _refuse_sockets(monkeypatch)
    phraser = _verbatim_guide()
    assert isinstance(phraser, VerbatimPhraser) and phraser.guide_model is None
    greeting = compose_greeting(phraser, _derived(0.5))
    assert greeting == Greeting(text=GREETING_TEMPLATES[1], reason="no_guide_model", latency_ms=greeting.latency_ms)
    assert greeting.path == "template"


def test_a_guide_model_that_fell_back_is_reported_as_the_template_by_fallback():
    phraser = GuidePhraser(fallback=True)
    greeting = compose_greeting(phraser, _derived(0.5))
    assert greeting.text == GREETING_TEMPLATES[1]
    assert (greeting.path, greeting.reason, greeting.latency_ms) == ("template", "phraser_fallback", 5000)
    assert [kind for kind, _, _ in phraser.calls] == ["greet"]


@pytest.mark.parametrize("persistence", [1 / 3, -1 / 3, 0.34, -0.34])
@pytest.mark.parametrize("guide", ["verbatim", "fallback"])
def test_the_edge_fixtures_each_give_exactly_one_template(persistence, guide):
    phraser = _verbatim_guide() if guide == "verbatim" else GuidePhraser(fallback=True)
    greeting = compose_greeting(phraser, _derived(persistence))
    assert sum(greeting.text == template for template in GREETING_TEMPLATES) == 1
    expected = GREETING_TEMPLATES[2] if abs(persistence) < 0.34 else GREETING_TEMPLATES[1 if persistence > 0 else 3]
    assert greeting.text == expected


# --- GUIDE=ollama: one greet call, the phrased line ---------------------------------------------


def test_the_guide_model_is_called_exactly_once_and_its_phrased_line_is_returned():
    phraser = GuidePhraser()
    derived = _derived(0.5)
    greeting = compose_greeting(phraser, derived)
    assert greeting == Greeting(text=PHRASED_LINE, reason="guide_model", latency_ms=1800)
    assert greeting.path == "phrased"
    assert phraser.calls == [("greet", (derived,), {})]


def test_the_composer_takes_the_phraser_and_the_derived_block_and_nothing_else():
    assert list(inspect.signature(compose_greeting).parameters) == ["phraser", "derived"]
    assert inspect.get_annotations(compose_greeting, eval_str=True) == {
        "phraser": HintPhraser, "derived": Derived, "return": Greeting,
    }


# --- AD-3: the greet input is exactly the Derived block; the text names no object or solution ----


def _started(room: Room, derived: Derived) -> SessionStart:
    """The session start as the client posts it: the room id and the Derived block, nothing else."""
    SessionStateMachine(room).initial(SESSION_ID)
    return SessionStart(room_id=room.id, derived=derived)


def _room_tokens(room: Room) -> set[str]:
    ids = {ix.id for ix in room.interactables} | {pz.id for pz in room.puzzles} | {room.id}
    labels = {ix.label for ix in room.interactables} | {w for ix in room.interactables for w in ix.label.split()}
    texts = {pz.clue for pz in room.puzzles} | {pz.lore for pz in room.puzzles}
    rungs = {getattr(pz.rungs, name) for pz in room.puzzles for name in ("nudge", "direction", "near_answer")}
    return ids | labels | texts | rungs


def _solution_tokens() -> set[str]:
    return {SENTINEL_CODE, json.dumps(SENTINEL_ORDER), " ".join(SENTINEL_ORDER), ", ".join(SENTINEL_ORDER),
            " ".join(SENTINEL_PAIR), SENTINEL_FIND}


@pytest.mark.parametrize("guide", ["verbatim", "ollama"])
def test_greet_receives_exactly_the_derived_block_of_the_session_start(four_lock_room: Room, guide):
    room = with_sentinel_solutions(four_lock_room)
    assert len({ix.label for ix in room.interactables}) == len(room.interactables)
    derived = _derived(0.4173, 137.9)
    start = _started(room, derived)
    phraser = GuidePhraser() if guide == "ollama" else GuidePhraser(fallback=True)

    compose_greeting(phraser, start.derived)

    assert phraser.calls == [("greet", (derived,), {})]
    (seen,) = phraser.calls[0][1]
    assert type(seen) is Derived
    blob = seen.model_dump_json()
    assert set(json.loads(blob)) == set(Derived.model_fields)
    assert not any(token in blob for token in _room_tokens(room) | _solution_tokens())
    assert not any(marker in blob for marker in ("room_", "ix_", "pz_", "solution", "clue", "lore", "label"))


@pytest.mark.parametrize("guide", ["verbatim", "ollama", "fallback"])
def test_the_greeting_text_names_no_label_id_or_solution(four_lock_room: Room, guide):
    room = with_sentinel_solutions(four_lock_room)
    start = _started(room, _derived(0.4173, 137.9))
    phraser = {"verbatim": _verbatim_guide, "ollama": GuidePhraser, "fallback": lambda: GuidePhraser(fallback=True)}[guide]()

    text = compose_greeting(phraser, start.derived).text

    words = set(text.lower().replace(";", "").replace(".", "").replace(",", "").split())
    labels = {w.lower() for ix in room.interactables for w in ix.label.split()}
    assert not words & labels, words & labels
    assert not any(ix.label in text for ix in room.interactables)
    assert "ix_" not in text and "pz_" not in text and "room_" not in text
    assert not any(token in text for token in _solution_tokens() | {*SENTINEL_ORDER, *SENTINEL_PAIR})


# --- The Derived block reaches only greet, phrase and domain/rungs.py -----------------------------


def _captured_surfaces(room: Room, greeting: Greeting) -> dict[str, str]:
    """Every model prompt, cache key, ledger entry and session write a played Session produces today."""
    view = to_prompt_view(room)
    photos = [Path(p.downscaled_path).read_bytes() for p in room.photos]
    reasons = [DraftReason(rule=5, key="p1", field="rungs.nudge", message="a rung holds a token")]
    architect = build_architect_prompt(photos)
    author = build_author_prompt(view)
    regeneration = build_regeneration_prompt(view, reasons)
    dry_run = build_dry_run_prompt(view, DryRunAnswers)
    prompts = {
        "architect prompt": json.dumps([[m.role, m.content] for m in architect.messages]),
        "riddler prompt": json.dumps([[m.role, m.content] for m in author.messages()]),
        "regeneration prompt": json.dumps([[m.role, m.content] for m in regeneration.messages()]),
        "dry run prompt": json.dumps([[m.role, m.content] for m in dry_run.messages]),
    }
    keys = {
        "architect key": cache_key("muse-spark-1.3", messages=architect.messages, response_schema=architect.response_schema,
                                   reasoning_effort=architect.reasoning_effort, images=photos),
        "riddler key": cache_key("muse-spark-1.3", messages=author.messages(), response_schema=author.response_schema,
                                 reasoning_effort=author.reasoning_effort, attempt=1),
        "dry run key": cache_key("muse-spark-1.3", messages=dry_run.messages, response_schema=DryRunAnswers,
                                 reasoning_effort=dry_run.reasoning_effort, images=photos),
    }
    entry = LedgerEntry(call_id=f"call_{'0' * 26}", kind="trickster", status="settled", usd=0.01, session_id=SESSION_ID)
    machine = SessionStateMachine(room)
    code_puzzle = next(pz for pz in room.puzzles if pz.lock_type == "code")
    events = [
        OpeningLineEvent(type="opening_line", kind="greeting", text=greeting.text, t_ms=1800),
        HintRequestEvent(type="hint_request", t_ms=4000),
        LockInputEvent(type="lock_input", input=CodeInput(type="code", puzzle_id=code_puzzle.id, code="0000"), t_ms=7000),
    ]
    state = machine.replay(SESSION_ID, events)
    result = machine.result(SESSION_ID, events)
    return {
        **prompts,
        **keys,
        "ledger entry": entry.model_dump_json(),
        "session events": json.dumps([e.model_dump(mode="json") for e in events]),
        "session state": state.model_dump_json(),
        "room result": result.model_dump_json(),
        "room artifact": room.model_dump_json(),
    }


@pytest.mark.parametrize("guide", ["verbatim", "ollama"])
def test_no_prompt_cache_key_ledger_entry_or_stored_artifact_carries_a_derived_key_or_value(four_lock_room: Room, guide):
    room = with_sentinel_solutions(four_lock_room)
    phraser = _verbatim_guide() if guide == "verbatim" else GuidePhraser()
    greeting = compose_greeting(phraser, SENTINEL_DERIVED)
    assert any(value in SENTINEL_DERIVED.model_dump_json() for value in SENTINEL_VALUES)

    for surface, text in _captured_surfaces(room, greeting).items():
        assert not any(f'"{key}"' in text or f"'{key}'" in text for key in DERIVED_KEYS), surface
        assert not any(value in text for value in SENTINEL_VALUES), surface
    assert "derived" not in inspect.signature(cache_key).parameters
    assert not set(DERIVED_KEYS) & set(LedgerEntry.model_fields)


def _names_derived(path: Path) -> bool:
    """Whether the module names `Derived` or `derived` as an identifier, attribute or string key."""
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        match node:
            case ast.Name(id=name) | ast.arg(arg=name) | ast.Attribute(attr=name) | ast.keyword(arg=name):
                if name in ("Derived", "derived"):
                    return True
            case ast.Constant(value="derived"):
                return True
    return False


def test_only_the_guide_port_its_adapters_the_composer_the_rungs_and_their_carriers_name_the_derived_block():
    src = REPO / "src"
    naming = set()
    for path in sorted(src.rglob("*.py")):
        if _names_derived(path):
            parts = ("src", *path.relative_to(src).with_suffix("").parts)
            naming.add(".".join(parts[:-1] if parts[-1] == "__init__" else parts))
    allowed = {m for m in naming if m in DERIVED_MODULES or m.startswith(tuple(p + "." for p in DERIVED_PACKAGES))}
    assert naming == allowed, naming - allowed
    assert {"src.domain.schema", "src.providers.base", "src.providers.verbatim", "src.council.greeting"} <= naming
