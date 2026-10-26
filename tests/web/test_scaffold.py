"""AR-1, AR-2, AR-5, AR-12: web/ from the Vite 8 vanilla-ts template, exact pins, one Node version file, the dev proxy."""

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "web"
PINS = {"three": "0.186.1"}
DEV_PINS = {"@types/three": "0.186.0", "json-schema-to-typescript": "16.0.0", "typescript": "6.0.3", "vite": "8.3.4"}
GENERATORS = ("json-schema-to-typescript", "quicktype")


def _package() -> dict:
    return json.loads((WEB / "package.json").read_text())


def _lock() -> dict:
    return json.loads((WEB / "package-lock.json").read_text())


def _tracked() -> list[str]:
    return subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()


def _ignored(path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO, check=False).returncode == 0


def test_package_pins_are_exact_and_node_is_24():
    pkg = _package()
    assert pkg["dependencies"] == PINS
    assert pkg["devDependencies"] == DEV_PINS
    assert pkg["engines"] == {"node": "24.x"}
    assert pkg["private"] is True and pkg["type"] == "module"
    assert pkg["scripts"] == {
        "dev": "vite",
        "build": "tsc && vite build",
        "preview": "vite preview",
        "types": "uv run --directory .. scripts/schema.py && node scripts/types.mjs",  # Story 1.15
    }


def test_exactly_one_type_generator_is_pinned():
    pkg = _package()
    assert [name for name in pkg["devDependencies"] if name in GENERATORS] == ["json-schema-to-typescript"]
    assert not any(p.startswith("node_modules/quicktype") for p in _lock()["packages"])
    assert not (WEB / "src/types").exists()  # generated types live in web/types (Story 1.15, tests/web/test_types.py)


def test_npmrc_saves_exact_and_is_engine_strict():
    assert (WEB / ".npmrc").read_text().split() == ["save-exact=true", "engine-strict=true"]


def test_root_nvmrc_is_the_only_node_version_file():
    assert (REPO / ".nvmrc").read_text().strip() == "24"
    names = (".nvmrc", ".node-version", ".tool-versions")
    assert [p for p in _tracked() if Path(p).name in names] == [".nvmrc"]
    assert not {"volta", "packageManager"} & set(_package())


def test_tsconfig_is_strict():
    text = re.sub(r"/\*.*?\*/", "", (WEB / "tsconfig.json").read_text(), flags=re.S)
    config = json.loads(text)
    assert config["compilerOptions"]["strict"] is True
    assert config["include"] == ["src", "types", "vite.config.ts"]


def test_lock_is_v3_matches_package_json_and_keeps_the_mac_bindings():
    lock = _lock()
    assert lock["lockfileVersion"] == 3
    packages = lock["packages"]
    assert packages[""]["dependencies"] == PINS and packages[""]["devDependencies"] == DEV_PINS
    for name, version in (PINS | DEV_PINS).items():
        assert packages[f"node_modules/{name}"]["version"] == version
    assert {"node_modules/@rolldown/binding-darwin-arm64", "node_modules/lightningcss-darwin-arm64"} <= set(packages)
    assert {"node_modules/@rolldown/binding-linux-x64-gnu", "node_modules/lightningcss-linux-x64-gnu"} <= set(packages)


@pytest.mark.parametrize("path", ["web/node_modules/three/package.json", "node_modules/a", "web/dist/index.html"])
def test_node_modules_and_dist_are_ignored(path):
    assert _ignored(path), f"{path} is not git-ignored"


def test_no_build_output_or_node_modules_is_tracked():
    assert "node_modules/" in (REPO / ".gitignore").read_text().splitlines()
    assert not [p for p in _tracked() if p.startswith(("web/node_modules/", "web/dist/"))]
    assert "web/package-lock.json" in _tracked()


def test_dev_server_proxies_api_to_uvicorn_without_cors():
    text = (WEB / "vite.config.ts").read_text()
    assert "'/api': 'http://127.0.0.1:8000'" in text
    assert re.search(r"\bcors\s*:", text) is None  # one origin: no CORS setting


def test_root_page_mounts_an_empty_three_scene_into_a_canvas():
    html = (WEB / "index.html").read_text()
    assert '<div id="app"></div>' in html and 'src="/src/main.ts"' in html
    # Story 1.17: the app shell owns #app and mounts the Scene in the Play layout's Scene column.
    assert "startShell(document.querySelector<HTMLDivElement>('#app')!)" in (WEB / "src/main.ts").read_text()
    assert "mount: () => mountScene(sceneColumn)" in (WEB / "src/shell.ts").read_text()
    scene = (WEB / "src/scene/index.ts").read_text()
    assert "from 'three'" in scene
    assert "new WebGLRenderer(" in scene and "new Scene()" in scene
    assert "root.append(renderer.domElement)" in scene and "renderer.render(scene, camera)" in scene
