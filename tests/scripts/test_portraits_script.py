"""Story 3.6: `scripts/portraits.py` paints the four wizard portraits once through the `image` role, cached and priced (FR-23, UX-DR83, AD-6)."""

import ast
import base64
import importlib.util
import json
import subprocess
import sys
from functools import partial
from pathlib import Path

import httpx
import pytest

from src.api import wiring
from src.config import Settings
from src.domain.ledger import fold
from src.infra.local import LEDGER_PATH, JsonlLedgerStore
from src.providers.meta_api import IMAGE_MODEL, MetaModelProvider
from src.providers.mock import ImageCall, MockProvider
from tests.providers.replay import load

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/portraits.py"
IMAGE = load("muse-image-1.0/portrait-riddler")
WIZARDS = ("architect", "riddler", "guide", "trickster")


def _load():
    spec = importlib.util.spec_from_file_location("portraits_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


portraits = _load()


class Meta:
    """The Meta adapter as wiring builds it, over a transport that answers each request from `answers` (the image fixture by default)."""

    def __init__(self, monkeypatch, *answers: httpx.Response) -> None:
        self.seen: list[httpx.Request] = []
        self.answers = list(answers)
        transport = httpx.MockTransport(self._handle)
        monkeypatch.setattr(wiring, "MetaModelProvider", partial(MetaModelProvider, transport=transport, sleep=lambda s: None))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.seen.append(request)
        return self.answers.pop(0) if self.answers else httpx.Response(IMAGE.status, json=IMAGE.body)


def _json(request: httpx.Request) -> dict:
    return json.loads(request.content)


def meta_settings(**overrides) -> Settings:
    values = {"provider_image": "meta", "model_api_key": "test-key", "spend_cap_usd": 60, "cache": "on", **overrides}
    return Settings(**values)


def entries(root: Path):
    return fold(JsonlLedgerStore(root / LEDGER_PATH).entries())


def files(root: Path) -> dict[str, tuple[bytes, int]]:
    folder = root / portraits.PORTRAITS_ROOT
    return {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in sorted(folder.glob("*"))} if folder.is_dir() else {}


def seed(root: Path) -> dict[str, tuple[bytes, int]]:
    """Portraits from an earlier run, so a failed run can be seen to leave them alone."""
    for wizard in WIZARDS:
        path = root / portraits.portrait_path(wizard)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"RIFF\x00\x00\x00\x00WEBPearlier " + wizard.encode())
    return files(root)


# --- The four prompts ------------------------------------------------------------


def test_each_prompt_is_the_shared_style_block_plus_one_subject_line():
    assert tuple(portraits.SUBJECTS) == WIZARDS
    for wizard in WIZARDS:
        style, subject = portraits.prompt(wizard).split("\n")
        assert (style, subject) == (portraits.STYLE, portraits.SUBJECTS[wizard])


@pytest.mark.parametrize("phrase", [
    "Oil painting", "visible brushwork", "single candle from camera left", "Warm umber, ochre and lamp-amber palette",
    "Near-black background close to #14100C", "Head and shoulders in three-quarter view", "center 70% of the frame",
    "Square 1:1 at 1024 px", "No text", "no painted frame", "no resemblance to any real person",
])
def test_the_style_block_carries_every_element_of_the_art_direction(phrase):
    assert phrase in portraits.STYLE


@pytest.mark.parametrize(("wizard", "details"), [
    ("architect", ["The Architect", "brass loupe"]),
    ("riddler", ["The Riddler", "half-smile", "sealed folded note"]),
    ("guide", ["The Guide", "kind and patient", "small lantern held low"]),
    ("trickster", ["The Trickster", "sly grin", "one eyebrow up", "playing card"]),
])
def test_each_subject_line_names_its_wizard_and_props(wizard, details):
    assert all(detail in portraits.SUBJECTS[wizard] for detail in details)


def test_no_prompt_carries_room_content_a_photo_or_a_profile_field():
    tree = ast.parse(SCRIPT.read_text())
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not imported & {"src.domain.schema", "src.domain.redact", "src.domain.rungs", "src.pipeline.ports"}
    derived = ("sessions", "time_to_first_hint_s", "mean_rung_per_lock_type", "persistence", "room", "photo", "data:")
    for wizard in WIZARDS:
        text = portraits.prompt(wizard)
        assert not any(word in text.lower() for word in derived), text


def test_the_script_paints_the_four_prompts_through_the_image_roles_provider(tmp_path, monkeypatch):
    image = MockProvider("image")
    monkeypatch.setattr(wiring, "MockProvider", lambda role: image if role == "image" else MockProvider(role))
    with pytest.raises(SystemExit):  # the mock's canned reply is no webp
        portraits.main([], root=tmp_path, settings=Settings(provider_image="mock"))
    assert image.calls == [ImageCall(portraits.prompt("architect"))]


# --- Through the meta adapter on the recorded image fixture -------------------------


def test_the_first_run_makes_four_priced_calls_and_writes_the_four_portraits(tmp_path, monkeypatch, capsys):
    meta = Meta(monkeypatch)
    assert portraits.main([], root=tmp_path, settings=meta_settings()) == 0

    assert [str(r.url) for r in meta.seen] == ["https://api.meta.ai/v1/images/generations"] * 4
    bodies = [_json(r) for r in meta.seen]
    assert [b["prompt"] for b in bodies] == [portraits.prompt(w) for w in WIZARDS]
    assert {b["model"] for b in bodies} == {IMAGE_MODEL}
    assert [(e.kind, e.status, e.usd) for e in entries(tmp_path)] == [("image", "settled", 0.01)] * 4
    webp = base64.b64decode(IMAGE.body["data"][0]["b64_json"])
    assert {name: data for name, (data, _) in files(tmp_path).items()} == {f"{w}.webp": webp for w in WIZARDS}
    out = capsys.readouterr().out
    assert out.count("billed 0.01 USD") == 4 and "running total 0.04 USD" in out


def test_a_second_run_is_four_cache_hits_with_no_new_entry_and_no_file_changed(tmp_path, monkeypatch, capsys):
    meta = Meta(monkeypatch)
    assert portraits.main([], root=tmp_path, settings=meta_settings()) == 0
    before_entries, before_files = JsonlLedgerStore(tmp_path / LEDGER_PATH).entries(), files(tmp_path)
    capsys.readouterr()

    assert portraits.main([], root=tmp_path, settings=meta_settings(cache="on")) == 0

    assert len(meta.seen) == 4
    assert JsonlLedgerStore(tmp_path / LEDGER_PATH).entries() == before_entries
    assert files(tmp_path) == before_files
    out = capsys.readouterr().out
    assert out.count("cached") == 4 and out.count("unchanged") == 4 and "wrote" not in out


def test_a_refused_call_exits_non_zero_with_the_cap_and_total_and_is_never_made(tmp_path, monkeypatch):
    meta = Meta(monkeypatch)
    earlier = seed(tmp_path)
    with pytest.raises(SystemExit) as exit:
        portraits.main([], root=tmp_path, settings=meta_settings(spend_cap_usd=0.02))
    assert "spend cap 0.02 USD would be passed: running total 0.02 USD" in str(exit.value.code)
    assert len(meta.seen) == 2  # the third call was refused before any request
    assert len(entries(tmp_path)) == 2
    assert files(tmp_path) == earlier


def test_a_provider_error_exits_non_zero_printing_it_and_overwrites_nothing(tmp_path, monkeypatch):
    failure = httpx.Response(500, json={"error": {"message": "generation failed", "type": "server_error", "code": None}})
    meta = Meta(monkeypatch, httpx.Response(IMAGE.status, json=IMAGE.body), failure)
    earlier = seed(tmp_path)
    with pytest.raises(SystemExit) as exit:
        portraits.main([], root=tmp_path, settings=meta_settings())
    assert str(exit.value.code).startswith("riddler: 500 server_error: generation failed")
    assert len(meta.seen) == 2  # an image 500 is never retried (AD-13)
    assert files(tmp_path) == earlier


def test_a_reply_that_is_not_a_webp_exits_non_zero_and_overwrites_nothing(tmp_path, monkeypatch):
    earlier = seed(tmp_path)
    with pytest.raises(SystemExit) as exit:
        portraits.main([], root=tmp_path, settings=Settings(provider_image="mock"))
    assert "without a webp image" in str(exit.value.code)
    assert files(tmp_path) == earlier


def test_the_script_runs_from_any_directory_and_prints_its_usage():
    done = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, cwd="/")
    assert done.returncode == 0 and "painted once" in done.stdout
