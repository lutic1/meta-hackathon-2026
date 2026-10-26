"""Story 2.9: `scripts/sit.py` discovers the cases under `tests/sit/`, runs them on the real cache and ledger, records fixtures and exits non-zero on a failure."""

import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from PIL import Image

from src.config import Settings
from src.domain.ledger import spark_cost_usd
from src.domain.schema import JobState, MaskPreview
from src.infra.local import CACHE_ROOT, LEDGER_PATH
from src.providers.base import ChatMessage
from tests.fixtures.rooms import INTERACTABLES, IX, PZ
from tests.providers.replay import Fixture, load

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/sit.py"
CASES = REPO / "tests/sit"
SHIPPED_CASES = [
    "test_00_cap_refusal", "test_01_cache_hit", "test_02_architect", "test_03_segment", "test_04_image", "test_05_fallback_chat",
    "test_06_ollama_guide", "test_07_riddler", "test_08_dry_run", "test_09_full_build",
]
CHAT = load("muse-spark-1.3/chat-three-objects")
MESSAGES = [ChatMessage(role="user", content="Say ok.")]


def _load():
    spec = importlib.util.spec_from_file_location("sit_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve the module's annotations through sys.modules
    spec.loader.exec_module(module)
    return module


sit_script = _load()


def chat_transport(body: dict | None = None, status: int = 200) -> sit_script.RecordingTransport:
    return sit_script.RecordingTransport(httpx.MockTransport(lambda request: httpx.Response(status, json=body or CHAT.body)))


def harness(root: Path, transport: sit_script.RecordingTransport | None = None) -> sit_script.Sit:
    return sit_script.Sit(root, Settings(model_api_key="test-key", spend_cap_usd=60), transport or chat_transport())


def write_case(folder: Path, name: str, body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.py"
    path.write_text(f'"""{name}."""\n\n\ndef run(sit):\n{body}\n')
    return path


def jpeg(width: int, height: int, colour: str = "#a0b0c0") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(out, format="JPEG")
    return out.getvalue()


# --- Discovery and the exit code, offline on fake case modules ----------------------


def test_discovery_finds_every_test_module_in_file_name_order_and_nothing_else(tmp_path):
    cases = tmp_path / "sit"
    write_case(cases, "test_10_later", "    return None")
    write_case(cases, "test_00_first", "    return None")
    (cases / "helper.py").write_text("x = 1\n")
    (cases / "__init__.py").write_text("")
    assert [p.name for p in sit_script.discover(cases)] == ["test_00_first.py", "test_10_later.py"]
    assert sit_script.discover(tmp_path / "missing") == []


def test_every_case_runs_with_pass_or_fail_printed_and_a_failure_exits_non_zero_naming_the_failed_cases(tmp_path, capsys):
    cases = tmp_path / "sit"
    write_case(cases, "test_00_ok", "    return 'fine'")
    write_case(cases, "test_01_broken", "    raise AssertionError('the seam is red')")
    write_case(cases, "test_02_after", "    return None")
    write_case(cases, "test_03_error", "    raise RuntimeError('boom')")

    assert sit_script.main([], root=tmp_path, cases_root=cases, transport=chat_transport()) == 1

    out = capsys.readouterr()
    lines = out.out.splitlines()
    assert lines[0].startswith("sit ") and "4 cases" in lines[0] and "0.0000 USD against the 60.00 USD local cap" in lines[0]
    assert lines[1].startswith("PASS test_00_ok: ") and lines[1].endswith("spend +0.0000 USD (fine)")
    assert lines[2] == "FAIL test_01_broken: AssertionError: the seam is red"
    assert lines[3].startswith("PASS test_02_after: ") and not lines[3].endswith(")")
    assert lines[4] == "FAIL test_03_error: RuntimeError: boom"
    assert lines[-1] == "sit: 2 pass, 2 fail; running total 0.0000 USD"
    assert "failed: test_01_broken, test_03_error" in out.err
    assert "Traceback" in out.err and "the seam is red" in out.err


def test_a_run_with_every_case_green_exits_zero(tmp_path, capsys):
    cases = tmp_path / "sit"
    write_case(cases, "test_00_ok", "    return None")
    assert sit_script.main([], root=tmp_path, cases_root=cases, transport=chat_transport()) == 0
    out = capsys.readouterr()
    assert "sit: 1 pass, 0 fail" in out.out and out.err == ""


def test_a_module_without_run_is_a_failed_case_and_no_case_dir_exits_non_zero(tmp_path, capsys):
    cases = tmp_path / "sit"
    cases.mkdir()
    (cases / "test_00_no_run.py").write_text("x = 1\n")
    assert sit_script.main([], root=tmp_path, cases_root=cases, transport=chat_transport()) == 1
    assert "FAIL test_00_no_run: TypeError: test_00_no_run.py defines no run(sit) function" in capsys.readouterr().out
    assert sit_script.main([], root=tmp_path, cases_root=tmp_path / "none", transport=chat_transport()) == 1
    assert "no case under tests/sit/" in capsys.readouterr().err


def test_a_case_sees_the_harness_and_its_spend_is_printed(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-key")  # the Settings the run builds come from the environment
    cases = tmp_path / "sit"
    write_case(cases, "test_00_call", "    from src.providers.base import ChatMessage\n"
               "    sit.meta('vision', 15.0).chat([ChatMessage(role='user', content='Say ok.')])\n"
               "    return f'{sit.running_total_usd():.6f}'")
    assert sit_script.main([], root=tmp_path, cases_root=cases, transport=chat_transport()) == 0
    cost = spark_cost_usd(CHAT.body["usage"])
    out = capsys.readouterr().out
    assert f"spend +{cost:.4f} USD ({cost:.6f})" in out
    assert out.splitlines()[-1] == f"sit: 1 pass, 0 fail; running total {cost:.4f} USD"


# --- The shipped cases and the offline suite -----------------------------------------


def test_the_shipped_cases_are_discovered_in_order_and_each_defines_run():
    paths = sit_script.discover(CASES)
    assert [p.stem for p in paths] == SHIPPED_CASES
    for path in paths:
        module = sit_script.load_case(path)
        assert module.__doc__ and module.__doc__.startswith("SIT-"), path.name


def test_the_offline_pytest_run_never_collects_a_sit_case():
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/sit", "tests/scripts/test_sit_script.py"],
                            cwd=REPO, capture_output=True, text=True, timeout=120, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "tests/sit/" not in result.stdout and "tests/scripts/test_sit_script.py::" in result.stdout


def test_the_script_runs_from_any_working_directory(tmp_path):
    result = subprocess.run([sys.executable, str(SCRIPT), "--help"], cwd=tmp_path, capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert "live-seam case" in result.stdout


# --- Every live call takes the real cache and ledger ---------------------------------


def test_a_live_call_goes_through_the_disk_cache_and_the_jsonl_ledger_under_the_root(tmp_path):
    sit = harness(tmp_path)
    provider = sit.meta("vision", 15.0, cache=True)

    first = provider.chat(MESSAGES)

    cost = spark_cost_usd(CHAT.body["usage"])
    rows = [json.loads(line) for line in (tmp_path / LEDGER_PATH).read_text().splitlines()]
    assert [(r["kind"], r["status"]) for r in rows] == [("vision", "reserved"), ("vision", "settled")]
    assert rows[1]["usd"] == cost and sit.running_total_usd() == pytest.approx(cost)
    assert len(list((tmp_path / CACHE_ROOT).glob("*.json"))) == 1
    assert len(sit.transport.responses) == 1

    second = provider.chat(MESSAGES)
    assert second.text == first.text
    assert len(sit.transport.responses) == 1 and sit.running_total_usd() == pytest.approx(cost)
    assert len((tmp_path / LEDGER_PATH).read_text().splitlines()) == 2


def test_cache_off_skips_the_cache_and_never_the_ledger(tmp_path):
    sit = harness(tmp_path)
    provider = sit.meta("vision", 15.0, cache=False)
    provider.chat(MESSAGES)
    provider.chat(MESSAGES)
    assert len(sit.transport.responses) == 2
    assert not (tmp_path / CACHE_ROOT).exists()
    assert sit.running_total_usd() == pytest.approx(2 * spark_cost_usd(CHAT.body["usage"]))


def test_the_cap_is_the_local_allocation_and_a_case_may_guard_with_its_own_ledger(tmp_path):
    sit = harness(tmp_path)
    assert sit.ledger.cap_usd == 60
    assert sit.meta("vision", 15.0)._calls._ledger is sit.ledger
    assert sit.meta("vision", 15.0, ledger=sit.ledger)._calls._cache is sit.cache


def test_the_fallback_adapter_takes_the_same_guarded_path_with_its_host(tmp_path):
    sit = sit_script.Sit(
        tmp_path,
        Settings(openai_compatible_api_key="k", openai_compatible_base_url="https://inference.baseten.co/v1"),
        chat_transport(),
    )
    provider = sit.openai_compatible(kind="riddler")
    assert provider._calls._ledger is sit.ledger and provider._calls.host == "inference.baseten.co"
    provider.chat(MESSAGES)
    assert [e.kind for e in sit.store.entries()] == ["riddler", "riddler"]


# --- Photos come from photos/, fixtures hold the response only -----------------------


def test_photos_are_read_from_the_git_ignored_photos_folder_and_downscaled_to_1280(tmp_path):
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "b.jpg").write_bytes(jpeg(4032, 3024))
    (photos / "a.jpeg").write_bytes(jpeg(640, 480))
    (photos / "c.heic").write_bytes(b"not a jpeg")
    small, big = harness(tmp_path).photos(2)
    assert small == (photos / "a.jpeg").read_bytes()
    with Image.open(io.BytesIO(big)) as image:
        assert image.format == "JPEG" and image.size == (1280, 960)


def test_too_few_photos_is_refused_naming_the_folder(tmp_path):
    with pytest.raises(FileNotFoundError, match=r"photos/ holds 0 JPEG\(s\); the SIT needs 2"):
        harness(tmp_path).photos(2)
    (tmp_path / "photos").mkdir()
    with pytest.raises(FileNotFoundError, match="holds 0"):
        harness(tmp_path).photos(1)


def test_the_sit_reads_no_photo_from_tests():
    source = SCRIPT.read_text()
    assert 'PHOTOS_ROOT = Path("photos")' in source
    assert "tests/fixtures" not in source.replace("tests/fixtures/providers", "").replace("tests/fixtures/jobs", "")


def test_record_writes_the_last_live_response_in_the_replay_shape(tmp_path):
    sit = harness(tmp_path)
    sit.meta("vision", 15.0).chat(MESSAGES)

    path = sit.record("chat-sit", model="muse-spark-1.3")

    assert path == tmp_path / "tests/fixtures/providers/muse-spark-1.3/chat-sit.json"
    fixture = Fixture.model_validate_json(path.read_bytes())
    assert (fixture.model, fixture.status, fixture.body) == ("muse-spark-1.3", 200, CHAT.body)
    assert set(json.loads(path.read_text())) == {"model", "status", "body"}


def test_record_is_refused_when_no_live_call_was_made(tmp_path):
    with pytest.raises(LookupError, match="served from the cache or never made"):
        harness(tmp_path).record("chat-sit", model="muse-spark-1.3")
    assert not (tmp_path / "tests").exists()


def test_record_refuses_a_response_holding_a_data_url(tmp_path):
    sit = harness(tmp_path, chat_transport({**CHAT.body, "echo": "data:image/jpeg;base64,/9j/4AAQ"}))
    sit.meta("vision", 15.0).chat(MESSAGES)
    with pytest.raises(ValueError, match="refusing to record"):
        sit.record("chat-sit", model="muse-spark-1.3")
    assert not (tmp_path / "tests").exists()


def test_record_writes_a_named_response_and_record_job_writes_the_job_record(tmp_path):
    sit = harness(tmp_path)
    own = sit.recording()
    sit.meta("vision", 15.0, transport=own).chat(MESSAGES)
    sit.meta("vision", 15.0).chat([ChatMessage(role="user", content="Say ok again.")])
    assert len(own.responses) == 1 and len(sit.transport.responses) == 2

    path = sit.record("chat-own", model="muse-spark-1.3", response=(200, {"named": True}))
    assert Fixture.model_validate_json(path.read_bytes()).body == {"named": True}

    state = JobState(id="job_01JA0000000000000000000000", status="done", regen_max=2)
    path = sit.record_job("full-build", state)
    assert path == tmp_path / "tests/fixtures/jobs/full-build.json"
    assert JobState.model_validate_json(path.read_bytes()) == state


def test_record_job_refuses_a_job_record_holding_a_data_url(tmp_path):
    preview = MaskPreview(id="ix_01JA0000000000000000000000", label="data:image/png", photo=0, polygons=[])
    state = JobState(id="job_01JA0000000000000000000000", status="done", regen_max=2, mask_preview=[preview])
    with pytest.raises(ValueError, match="refusing to record jobs/full-build"):
        harness(tmp_path).record_job("full-build", state)
    assert not (tmp_path / "tests").exists()


def test_the_recording_transport_keeps_status_and_body_and_passes_the_response_through():
    transport = sit_script.RecordingTransport(httpx.MockTransport(lambda r: httpx.Response(503, text="overloaded")))
    with httpx.Client(transport=transport) as client:
        response = client.get("https://api.meta.ai/v1/x")
    assert response.status_code == 503 and response.text == "overloaded"
    assert transport.responses == [(503, "overloaded")]


# --- The shipped cases, end to end on replayed responses -----------------------------


ARCHITECT_REPLY = {
    "candidates": [
        {"label": "brass lamp", "plural": False, "photo": 1, "box": [100, 100, 400, 500], "attributes": [], "confidence": 0.9},
        {"label": "blue mug", "plural": False, "photo": 0, "box": [500, 600, 700, 800], "attributes": ["KF"], "confidence": 0.6},
    ]
}


def _riddler_reply() -> str:
    """The Baseten room-draft fixture's puzzle under the Riddler's ordinal keys `p1`..`p4`."""
    draft = json.loads(load("muse-spark-open/chat-room-draft").body["choices"][0]["message"]["content"])
    puzzle = {k: v for k, v in draft["puzzles"][0].items() if k != "key"}
    return json.dumps({key: {**puzzle, "is_exit": key == "p1"} for key in ("p1", "p2", "p3", "p4")})


FIXTURE_LABELS = {IX[name]: label for name, (label, *_) in INTERACTABLES.items()}
"""The synthetic room's fixed `ix_` ids by label, as the recorded Riddler reply names them."""
BUILD_REPLY = {
    "candidates": [
        {"label": label, "plural": False, "photo": photo, "attributes": attributes, "confidence": round(0.95 - i * 0.01, 2),
         "box": [min(1000, round(x0 / 1.28)), min(1000, round(y0 / 0.96)), min(1000, round(x1 / 1.28)), min(1000, round(y1 / 0.96))]}
        for i, (label, photo, (x0, y0, x1, y1), attributes) in enumerate(INTERACTABLES.values())
    ]
}
"""The full Build's Architect reply: the synthetic room's objects, boxes on the 0 to 1000 grid of a 1280 by 960 photo."""
BUILD_PHOTOS = 6


def load_from(root: Path, name: str) -> Fixture:
    """A fixture a run under `root` recorded, from `muse-spark-1.3`."""
    return Fixture.model_validate_json((root / f"tests/fixtures/providers/muse-spark-1.3/{name}.json").read_bytes())


def _user_text(body: dict) -> str:
    content = next(m["content"] for m in body["messages"] if m["role"] == "user")
    return content if isinstance(content, str) else "".join(part.get("text", "") for part in content)


def _images(body: dict) -> int:
    content = next(m["content"] for m in body["messages"] if m["role"] == "user")
    return 0 if isinstance(content, str) else sum(part["type"] == "image_url" for part in content)


def _chat(text: str) -> dict:
    return {**CHAT.body, "choices": [{**CHAT.body["choices"][0], "message": {"role": "assistant", "content": text}}]}


class Vendors:
    """One handler for every host: Meta's chat, segment and image endpoints, the Baseten chat endpoint and Ollama's generate.

    The Riddler's recorded reply is replayed with its fixed `ix_` ids rewritten, by label, to the ids
    the prompt lists, so the full Build's minted ids match; the Dry run replays its recorded reply
    over the synthetic room, and over a Build's room answers each listed Puzzle with the last draft's solution.
    """

    def __init__(self) -> None:
        self.segments = 0
        self.paths: list[str] = []
        self.draft: dict = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(f"{request.url.host}{request.url.path}")
        if request.url.path == "/api/generate":
            if request.url.port == 1:  # the unreachable leg of the Ollama case
                raise httpx.ConnectError("connection refused")
            name = "generate-phrase-longest" if "\nLine:\n" in json.loads(request.content)["prompt"] else "generate-greet"
            return httpx.Response(200, json=load(f"llama3.2-3b/{name}").body)
        if request.url.host == "inference.baseten.co":
            draft = load("muse-spark-open/chat-room-draft").body
            choice = {**draft["choices"][0], "message": {"role": "assistant", "content": _riddler_reply()}}
            return httpx.Response(200, json={**draft, "choices": [choice]})
        if request.url.path.endswith("/responses"):
            if json.loads(request.content)["input"][0]["content"][0]["text"] in FIXTURE_LABELS.values():
                return httpx.Response(200, json=load("sam-3.1/segment-no-mask").body)  # the Build's objects keep their boxes
            self.segments += 1
            return httpx.Response(200, json=load("sam-3.1/segment-two-masks" if self.segments % 2 else "sam-3.1/segment-no-mask").body)
        if request.url.path.endswith("/images/generations"):
            return httpx.Response(200, json=load("muse-image-1.0/portrait-riddler").body)
        body = json.loads(request.content)
        schema = (body.get("response_format") or {}).get("json_schema", {}).get("name")
        if schema == "RiddlerResponse":
            return httpx.Response(200, json=self.riddler(_user_text(body)))
        if schema == "DryRunAnswers":
            return httpx.Response(200, json=self.dry_run(_user_text(body)))
        if schema == "ArchitectResponse" and _images(body) == BUILD_PHOTOS:
            return httpx.Response(200, json=_chat(json.dumps(BUILD_REPLY)))
        return httpx.Response(200, json=_chat(json.dumps(ARCHITECT_REPLY) if body.get("response_format") else "ok"))

    def riddler(self, prompt: str) -> dict:
        recorded = load("muse-spark-1.3/chat-riddler-author").body
        listed = {label: ix for ix, label in re.findall(r'"id": "(ix_\w+)",\s*"label": "([^"]+)"', prompt)}
        text = recorded["choices"][0]["message"]["content"]
        for fixed, label in FIXTURE_LABELS.items():
            text = text.replace(fixed, listed.get(label, fixed))
        self.draft = json.loads(text)
        return {**recorded, "choices": [{**recorded["choices"][0], "message": {"role": "assistant", "content": text}}]}

    def dry_run(self, prompt: str) -> dict:
        if PZ["find_key"] in prompt:
            return load("muse-spark-1.3/chat-dry-run").body
        puzzles = re.findall(r"^Puzzle (pz_\w+)$", prompt, re.MULTILINE)
        solutions = [puzzle["solution"] for puzzle in self.draft.values() if puzzle is not None]
        answers = [{"puzzle_id": pid, "answer": solution} for pid, solution in zip(puzzles, solutions, strict=True)]
        return _chat(json.dumps({"answers": answers}))


BUILD_PATHS = [
    "api.meta.ai/v1/chat/completions",  # the full Build's Architect
    *["api.meta.ai/v1/responses"] * len(INTERACTABLES),  # one segment call per object
    "api.meta.ai/v1/chat/completions",  # its Riddler
    "api.meta.ai/v1/chat/completions",  # its Dry run
]


def test_the_shipped_cases_pass_end_to_end_on_replayed_responses_and_record_their_fixtures(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "https://inference.baseten.co/v1")
    (tmp_path / "photos").mkdir()
    (tmp_path / "photos/a.jpg").write_bytes(jpeg(1280, 960))
    (tmp_path / "photos/b.jpg").write_bytes(jpeg(960, 1280))
    for name, colour in zip("cdef", ("#b7a98a", "#cfd6dc", "#a8b59a", "#c9b7b0"), strict=True):
        (tmp_path / f"photos/{name}.jpg").write_bytes(jpeg(1280, 960, colour))
    vendors = Vendors()
    transport = sit_script.RecordingTransport(httpx.MockTransport(vendors))

    assert sit_script.main([], root=tmp_path, cases_root=CASES, transport=transport) == 0

    out = capsys.readouterr()
    assert out.err == "", out.err
    statuses = [line.split(":")[0] for line in out.out.splitlines() if line.startswith(("PASS", "FAIL"))]
    assert statuses == [f"PASS {name}" for name in SHIPPED_CASES]
    recorded = sorted(str(p.relative_to(tmp_path / "tests/fixtures/providers")) for p in (tmp_path / "tests/fixtures/providers").rglob("*.json"))
    assert recorded == [
        "llama3.2-3b/generate-greet.json",
        "llama3.2-3b/generate-phrase-longest.json",
        "muse-image-1.0/image-sit-clue-card.json",
        "muse-spark-1.3/chat-architect-two-photos.json",
        "muse-spark-1.3/chat-dry-run.json",
        "muse-spark-1.3/chat-full-build-architect.json",
        "muse-spark-1.3/chat-full-build-dry-run.json",
        "muse-spark-1.3/chat-full-build-riddler.json",
        "muse-spark-1.3/chat-riddler-author.json",
        "muse-spark-1.3/chat-sit-ok.json",
        "muse-spark-open/chat-riddler-author.json",
        "sam-3.1/segment-absent-label.json",
        "sam-3.1/segment-present-label.json",
    ]
    assert vendors.paths == [
        "api.meta.ai/v1/chat/completions",  # the cache-hit case's first call; the repeat is a hit
        "api.meta.ai/v1/chat/completions",  # the Architect
        "api.meta.ai/v1/responses", "api.meta.ai/v1/responses",
        "api.meta.ai/v1/images/generations",
        "inference.baseten.co/v1/chat/completions",
        "127.0.0.1/api/generate", "127.0.0.1/api/generate",  # phrase, greet
        "127.0.0.1/api/generate",  # the unreachable leg, refused
        "api.meta.ai/v1/chat/completions",  # the Riddler
        "api.meta.ai/v1/chat/completions",  # the Dry run
        *BUILD_PATHS,
    ]
    entries = sit_script.JsonlLedgerStore(tmp_path / LEDGER_PATH).entries()
    kinds = [(e.kind, e.status) for e in entries]
    calls = ("vision", "vision", "sam", "sam", "image", "riddler", "riddler", "dryrun")
    assert kinds[: 2 * len(calls)] == [(k, s) for k in calls for s in ("reserved", "settled")]
    built = [e for e in entries[2 * len(calls):] if e.status == "settled"]
    assert [e.kind for e in built if e.kind != "sam"] == ["vision", "riddler", "dryrun"] and len(built) == 3 + len(INTERACTABLES)
    tagged = [(e.kind, e.stage) for e in built if e.job_id is not None]
    assert tagged == [("riddler", "author"), ("dryrun", "dryrun")]  # the Build's own calls, tagged for provenance
    for name in ("chat-architect-two-photos", "chat-sit-ok"):
        assert Fixture.model_validate_json((tmp_path / f"tests/fixtures/providers/muse-spark-1.3/{name}.json").read_bytes()).status == 200
    full_build = {
        role: json.loads(load_from(tmp_path, f"chat-full-build-{role}").body["choices"][0]["message"]["content"])
        for role in ("architect", "riddler", "dry-run")
    }
    assert full_build["architect"] == BUILD_REPLY and full_build["riddler"] == vendors.draft
    assert len(full_build["dry-run"]["answers"]) == 5
    job = JobState.model_validate_json((tmp_path / "tests/fixtures/jobs/full-build.json").read_bytes())
    assert job.status == "done" and [v.verdict for v in job.dry_run] == ["pass"] * 5
    assert [p.label for p in job.mask_preview] == list(FIXTURE_LABELS.values())
    assert "PASS test_00_cap_refusal: " in out.out and "refused at cap 0.0000 USD, no entry, no request" in out.out
    assert "'brass lamp': 2 polygon(s)" in out.out and "'a live penguin': none" in out.out
    assert "billed 0.01 USD, recorded" in out.out
    assert "meta-models/muse-spark-open: 4 puzzles" in out.out
    assert "PASS test_06_ollama_guide: " in out.out and "21 tokens out in" in out.out and "decode 20 tok/s" in out.out
    assert "PASS test_07_riddler: " in out.out and "5 puzzles in" in out.out and "rules 8 of 8 passed; 3174 out" in out.out
    lines = {line.split(":")[0]: line for line in out.out.splitlines() if line.startswith("PASS")}
    assert "(reached 5 of 5 answers in " in lines["PASS test_08_dry_run"] and "; 10120 in, 2650 out)" in lines["PASS test_08_dry_run"]
    assert "(done in " in lines["PASS test_09_full_build"]
    assert "; reached 5 of 5 answers; 0 of 2 regenerations; every stage within budget)" in lines["PASS test_09_full_build"]

    # A second run on the same day: the image and the cache-hit calls are served from the cache, the rest run again.
    first = len(vendors.paths)
    assert sit_script.main([], root=tmp_path, cases_root=CASES, transport=transport) == 0
    again = capsys.readouterr().out
    assert "served from the cache" in again and "first call already cached" in again
    assert vendors.paths[first:] == [
        "api.meta.ai/v1/chat/completions",
        "api.meta.ai/v1/responses", "api.meta.ai/v1/responses",
        "inference.baseten.co/v1/chat/completions",
        "127.0.0.1/api/generate", "127.0.0.1/api/generate", "127.0.0.1/api/generate",
        "api.meta.ai/v1/chat/completions",
        "api.meta.ai/v1/chat/completions",
        *BUILD_PATHS,
    ]
