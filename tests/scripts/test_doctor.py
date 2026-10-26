"""scripts/doctor.py: standard library only, no src import, valid JSON output."""

import ast
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCTOR = REPO / "scripts/doctor.py"


def _imports() -> set[str]:
    tree = ast.parse(DOCTOR.read_text())
    names = {alias.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names}
    names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    return names


def test_doctor_is_stdlib_only_and_imports_no_src_module():
    imported = _imports()
    assert imported <= set(sys.stdlib_module_names), imported - set(sys.stdlib_module_names)
    assert "src" not in imported


def test_doctor_json_is_valid(tmp_path):
    result = subprocess.run([sys.executable, str(DOCTOR), "--ci", "--json"], cwd=REPO,
                            capture_output=True, text=True, timeout=120, check=False)
    report = json.loads(result.stdout)
    assert report["mode"] == "ci"
    assert {"PASS", "WARN", "FAIL"} == set(report["counts"])
    assert all({"status", "check", "detail"} <= set(r) for r in report["results"])
    assert (result.returncode == 1) == (report["counts"]["FAIL"] > 0)
    checks = {r["check"]: r["status"] for r in report["results"]}
    assert checks["uv.lock in sync"] == "PASS"
    assert checks[".gitignore privacy entries"] == "PASS"
    assert checks["no private path tracked or staged"] == "PASS"
    assert checks["Settings loads"] == "PASS"
