"""AR-2: the Stack pins and the uv settings, as the Dependencies convention states them."""

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNTIME_PINS = {
    "fastapi": "0.156.4", "uvicorn": "0.54.0", "pydantic": "2.14.1", "httpx": "0.28.1",
    "Pillow": "13.0.0", "meta-sam-parser": "0.1.0", "fal-client": "1.0.3", "ollama": "0.6.3",
    "modal": "1.6.2", "python-dotenv": "1.2.4",
}
PLATFORMS = [
    "sys_platform == 'darwin' and platform_machine == 'arm64'",
    "sys_platform == 'linux' and platform_machine == 'x86_64'",
]


def _pyproject() -> dict:
    return tomllib.loads((REPO / "pyproject.toml").read_text())


def test_runtime_pins_are_exact():
    project = _pyproject()["project"]
    assert project["requires-python"] == ">=3.13"
    assert sorted(project["dependencies"]) == sorted(f"{k}=={v}" for k, v in RUNTIME_PINS.items())


def test_pytest_is_in_the_dev_group_only():
    data = _pyproject()
    assert data["dependency-groups"]["dev"] == ["pytest==9.1.1"]
    assert not any(dep.startswith("pytest") for dep in data["project"]["dependencies"])


def test_uv_settings_and_no_build_system():
    data = _pyproject()
    uv = data["tool"]["uv"]
    assert uv["environments"] == PLATFORMS and uv["required-environments"] == PLATFORMS
    assert uv["no-build"] is True and uv["required-version"] == ">=0.11.32"
    assert "build-system" not in data
    assert data["tool"]["pytest"]["ini_options"] == {"testpaths": ["tests"], "pythonpath": ["."]}


def test_version_files_and_no_requirements_txt():
    assert (REPO / ".python-version").read_text().strip() == "3.13"
    assert (REPO / ".nvmrc").read_text().strip() == "24"
    assert (REPO / "uv.lock").exists()
    assert not (REPO / "requirements.txt").exists()
    assert "requirements.txt" not in (REPO / "README.md").read_text()
