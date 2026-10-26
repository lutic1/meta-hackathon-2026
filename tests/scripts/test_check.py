"""scripts/check.sh: the privacy gate, the step order, the hosted greps and --predeploy, run with a stub uv."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "scripts/check.sh"
IMAGE_BLOCK = 'modal.Image.debian_slim(python_version="3.13").uv_sync(uv_version="0.11.32", extra_options="--no-dev")\n'


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    """A clean git repo with check.sh, ci.yml and .python-version, and a stub uv on PATH that logs its calls."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / "scripts/check.sh").write_text(CHECK.read_text())
    (repo / ".github/workflows/ci.yml").write_text((REPO / ".github/workflows/ci.yml").read_text())
    (repo / ".python-version").write_text("3.13\n")
    (repo / ".gitignore").write_text("dist/\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text('#!/usr/bin/env bash\necho "uv $*" >> "$UV_LOG"\nexit "${UV_EXIT:-0}"\n')
    uv.chmod(uv.stat().st_mode | stat.S_IXUSR)
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return repo


def _run(repo: Path, *args: str, uv_exit: int = 0) -> tuple[subprocess.CompletedProcess, list[str]]:
    log = repo.parent / "uv.log"
    log.write_text("")
    env = {**os.environ, "PATH": f"{repo.parent / 'bin'}:{os.environ['PATH']}",
           "UV_LOG": str(log), "UV_EXIT": str(uv_exit)}
    result = subprocess.run(["bash", "scripts/check.sh", *args], cwd=repo, env=env,
                            capture_output=True, text=True, check=False)
    return result, log.read_text().splitlines()


def _commit(repo: Path, *paths: str) -> None:
    for rel in paths:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-f", *paths)
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "add")


def test_check_sh_is_executable_and_fails_fast():
    assert CHECK.stat().st_mode & stat.S_IXUSR
    assert "set -euo pipefail" in CHECK.read_text()
    assert subprocess.run(["bash", "-n", str(CHECK)], check=False).returncode == 0


def test_tracked_photo_or_hosted_env_fails_the_privacy_step_before_uv_runs(scratch):
    _commit(scratch, "tests/fixtures/sam31/living-room-1.jpg", "keyframe-hosted.env")
    result, calls = _run(scratch)
    assert result.returncode == 1
    assert "tracked private files" in result.stdout
    assert "tests/fixtures/sam31/living-room-1.jpg" in result.stdout and "keyframe-hosted.env" in result.stdout
    assert calls == []


def test_allowed_images_and_env_example_pass_the_privacy_step(scratch):
    _commit(scratch, ".env.example", "web/public/logo.png", "docs/screenshots/play.jpg")
    result, _ = _run(scratch)
    assert "tracked private files" not in result.stdout
    assert result.returncode == 0


def test_steps_run_in_order_and_stop_at_the_first_failure(scratch):
    result, calls = _run(scratch, uv_exit=3)
    assert result.returncode == 3
    assert calls == ["uv lock --check"]
    assert "check.sh: all green" not in result.stdout


def test_green_run_without_web_skips_the_web_step(scratch):
    result, calls = _run(scratch)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls[:3] == ["uv lock --check", "uv sync --locked", "uv run pytest -q"]
    assert calls[3].startswith("uv export --frozen --no-hashes --no-emit-project -q -o ")
    assert "--python-platform aarch64-apple-darwin --only-binary :all:" in calls[4]
    assert "--python-platform x86_64-manylinux_2_28 --only-binary :all:" in calls[5]
    assert all("/dev/null" not in call for call in calls)
    assert len(calls) == 6
    assert "== web:" not in result.stdout and "== hosted" not in result.stdout
    assert result.stdout.rstrip().endswith("check.sh: all green")


def test_hosted_step_greps_the_image_against_ci_uv_and_python_version(scratch):
    _commit(scratch, "src/api/modal_app.py")
    (scratch / "src/api/modal_app.py").write_text(IMAGE_BLOCK)
    result, calls = _run(scratch)
    assert result.returncode == 0, result.stdout
    assert "uv run python -c import src.api.modal_app" in calls
    (scratch / "src/api/modal_app.py").write_text(IMAGE_BLOCK.replace('uv_version="0.11.32"', 'uv_version="0.13.4"'))
    result, _ = _run(scratch)
    assert result.returncode == 1 and 'must install uv.lock with .uv_sync(uv_version="0.11.32"' in result.stdout
    (scratch / "src/api/modal_app.py").write_text(IMAGE_BLOCK + 'image.pip_install("x")\n')
    result, _ = _run(scratch)
    assert result.returncode == 1 and "has a pip_install list" in result.stdout
    (scratch / "src/api/modal_app.py").write_text(IMAGE_BLOCK.replace('python_version="3.13"', 'python_version="3.12"'))
    result, _ = _run(scratch)
    assert result.returncode == 1 and "python_version differs from .python-version" in result.stdout


def test_web_step_text_runs_npm_ci_build_and_type_check():
    text = CHECK.read_text()
    assert 'if [ -f web/package.json ]; then' in text
    assert "(cd web && npm ci --no-audit --no-fund && npm run build && npx tsc --noEmit)" in text
    assert '"node_modules/@rolldown/binding-darwin-arm64"' in text


def test_predeploy_needs_a_clean_tree_and_the_web_build(scratch):
    (scratch / "notes.txt").write_text("wip")
    result, _ = _run(scratch, "--predeploy")
    assert result.returncode == 1 and "commit or stash first" in result.stdout
    (scratch / "notes.txt").unlink()
    result, _ = _run(scratch, "--predeploy")
    assert result.returncode == 1 and "web/dist is missing" in result.stdout
    (scratch / "web/dist").mkdir(parents=True)
    (scratch / "web/dist/index.html").write_text("<!doctype html>")
    result, _ = _run(scratch, "--predeploy")
    assert result.returncode == 0 and result.stdout.rstrip().endswith("check.sh: all green")
