#!/usr/bin/env python3
"""Keyframe environment doctor. Standard library only, so it runs before `uv sync`.

    python3 scripts/doctor.py            # default: Mac checks on macOS, cloud checks on Linux
    python3 scripts/doctor.py --cloud    # coding-agent container
    python3 scripts/doctor.py --ci       # skip machine-only checks (.env, Ollama, port, warm-up)
    python3 scripts/doctor.py --json     # machine-readable output

Prints PASS, WARN or FAIL per line and exits 1 on any FAIL. It diagnoses; it is not a CI gate.
It reads key names from .env, never values (except OLLAMA_HOST). It is exempt from AD-14 (it runs
before `uv sync`, stdlib only, so it cannot import Settings for OLLAMA_HOST). It tolerates the files the
deps-foundation story adds on Mon Oct 26 (uv.lock, .nvmrc, web/) being absent before then.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

UV_PINNED = (0, 11, 32)        # mirror of ci.yml `version:`
OLLAMA_MINOR = "0.40"          # source of truth for the Ollama runtime minor
OLLAMA_STACK = "0.40.6"        # mirror of the Stack table
GUIDE_MODEL_DEFAULT = "llama3.2:3b"  # used until src/providers/ollama.py defines GUIDE_MODEL
SECRET_KEYS = ("META_MODEL_API_KEY", "FAL_KEY", "OPENAI_COMPATIBLE_API_KEY", "ACCESS_CODE")
IGNORE_PROBES = (".env", ".env.local", "keyframe-hosted.env", "rooms/a.jpg", "photos/a.jpg",
                 "captures/a.jpg", "uploads/a.jpg", "a.heic", "a.HEIC", ".cache/a")
# Mirror of the privacy step in scripts/check.sh: env files, raw photos, private folders.
PRIVATE_PATH = re.compile(r"\.env$|(^|/)\.env\.|\.(jpe?g|heic|png)$|^(rooms|photos|captures|uploads|\.cache|cache)/", re.I)
PRIVATE_ALLOW = re.compile(r"(^|/)\.env\.example$|^(web/public|docs/screenshots)/")

results: list[dict] = []


def report(status: str, name: str, detail: str = "") -> None:
    results.append({"status": status, "check": name, "detail": detail})


def run(*cmd: str, cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
    """Run a command; return (exit code, stdout+stderr). 127 when the tool is missing."""
    if shutil.which(cmd[0]) is None:
        return 127, f"{cmd[0]} not found"
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    lines = (p.stdout + p.stderr).splitlines()
    return p.returncode, "\n".join(x for x in lines if "UV_NATIVE_TLS" not in x).strip()  # known-harmless noise


def version(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(x) for x in m.groups(default="0")) if m else ()


def dotenv_keys(path: Path) -> dict[str, bool]:
    """Key name -> has a non-empty value. Values are never returned."""
    keys = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
        if m:
            keys[m.group(1)] = m.group(2).strip().strip("'\"") != ""
    return keys


def ollama_host(root: Path) -> str:
    host = os.environ.get("OLLAMA_HOST", "")
    env = root / ".env"
    if not host and env.exists():
        m = re.search(r"^\s*OLLAMA_HOST\s*=\s*(\S+)", env.read_text(errors="replace"), re.M)
        host = m.group(1).strip("'\"") if m else ""
    host = host or "127.0.0.1:11434"
    return host if host.startswith("http") else f"http://{host}"


def http_json(url: str, body: dict | None = None, timeout: float = 5) -> dict:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never via a proxy
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read() or b"{}")


# ---------------------------------------------------------------- checks

def check_tools(root: Path, cloud: bool) -> None:
    pv = root / ".python-version"
    if pv.exists():
        want = pv.read_text().strip()
        report("PASS" if want == "3.13" else "FAIL", ".python-version", f"{want} (Stack: 3.13)")
    code, out = run("uv", "--version")
    pinned = ".".join(map(str, UV_PINNED))
    if code == 127:
        report("FAIL", "uv", "missing: curl -LsSf https://astral.sh/uv/install.sh | sh")
    else:
        have = version(out)
        if have < UV_PINNED:
            report("FAIL", "uv", f"{out}; need >= {pinned}: uv self update {pinned}")
        elif have > UV_PINNED:
            report("WARN", "uv", f"{out}; CI and Modal use {pinned}. If uv.lock churns: uv self update {pinned}")
        else:
            report("PASS", "uv", out)
        code, out = run("uv", "python", "find", "3.13", cwd=root)
        report("PASS" if code == 0 else "WARN", "python 3.13 for uv",
               out.splitlines()[-1] if code == 0 else "none found; uv sync downloads it (or: uv python install 3.13)")

    nvmrc = root / ".nvmrc"
    node_needed = nvmrc.exists() or (root / "web/package.json").exists()
    want_major = nvmrc.read_text().strip().lstrip("v").split(".")[0] if nvmrc.exists() else "24"
    miss = "FAIL" if node_needed else "WARN"  # before the first web story nothing uses Node yet
    code, out = run("node", "--version")
    hint = "source $NVM_DIR/nvm.sh --no-use && nvm install 24 (then rerun .claude/hooks/session-start.sh)" if cloud else "nvm use"
    if code != 0:
        report(miss, "node", f"missing; {hint}")
    else:
        ok = str(version(out)[0]) == want_major
        report("PASS" if ok else miss, "node", f"{out} (want {want_major}.x)" + ("" if ok else f"; {hint}"))
    code, out = run("npm", "--version")
    ok = code == 0 and version(out)[:1] >= (11,)
    report("PASS" if ok else miss, "npm", f"{out} (want >= 11, ships with Node 24)")


def check_locks(root: Path) -> None:
    pyproject = root / "pyproject.toml"
    has_deps = pyproject.exists() and re.search(r"^dependencies\s*=", pyproject.read_text(), re.M)
    lock = root / "uv.lock"
    if lock.exists():
        code, out = run("uv", "lock", "--check", "--offline", cwd=root)
        if code == 127:
            report("WARN", "uv.lock in sync", "uv missing; not checked")
        else:
            report("PASS" if code == 0 else "FAIL", "uv.lock in sync",
                   "matches pyproject.toml" if code == 0 else "drift: run `uv lock` in a dependency PR, never --frozen")
        if (root / "requirements.txt").exists():
            report("WARN", "requirements.txt", "the deps-foundation story deletes it; uv.lock is the lock")
    else:
        report("FAIL" if has_deps else "WARN", "uv.lock",
               "missing: run `uv lock` and commit it" if has_deps else "absent (the deps-foundation story adds it Mon Oct 26)")

    pkg = root / "web/package.json"
    if not pkg.exists():
        return
    plock = root / "web/package-lock.json"
    if not plock.exists():
        report("FAIL", "web lock", "web/package-lock.json missing: npm install from a clean tree, commit the lock")
        return
    try:
        manifest, locked = json.loads(pkg.read_text()), json.loads(plock.read_text())
    except (ValueError, OSError):
        report("FAIL", "web lock", "web/package.json or package-lock.json is not valid JSON (merge conflict?): "
               "regenerate from a clean tree")
        return
    top = locked.get("packages", {}).get("", {})
    declared = {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}
    in_lock = {**top.get("dependencies", {}), **top.get("devDependencies", {})}
    loose = [f"{k}@{v}" for k, v in declared.items() if not re.fullmatch(r"\d+\.\d+\.\d+", v)]
    report("PASS" if declared == in_lock else "FAIL", "web lock in sync",
           "package.json matches the lock" if declared == in_lock else "differs: npm install <pkg>@<exact> and commit both")
    report("PASS" if not loose else "FAIL", "web exact versions", ", ".join(loose) or "all exact")
    has_mac = "node_modules/@rolldown/binding-darwin-arm64" in locked.get("packages", {})
    report("PASS" if has_mac else "FAIL", "web lock has macOS arm64 bindings",
           "present" if has_mac else "lost: rm -rf node_modules package-lock.json && npm install")
    npmrc = root / "web/.npmrc"
    text = npmrc.read_text() if npmrc.exists() else ""
    ok = "save-exact=true" in text and "engine-strict=true" in text
    report("PASS" if ok else "WARN", "web/.npmrc", "save-exact and engine-strict set" if ok else "add save-exact=true and engine-strict=true")


def check_git_privacy(root: Path) -> None:
    if run("git", "rev-parse", "--git-dir", cwd=root)[0] != 0:
        report("WARN", "git", "not a git checkout; privacy checks skipped")
        return
    probes = list(IGNORE_PROBES) + (["web/node_modules/a"] if (root / "web").exists() else [])
    not_ignored = [p for p in probes if run("git", "check-ignore", "-q", "--no-index", p, cwd=root)[0] != 0]
    report("PASS" if not not_ignored else "FAIL", ".gitignore privacy entries",
           "covers .env, .env.*, *.env, rooms/, photos/, captures/, uploads/, *.heic, .cache/" if not not_ignored
           else "not ignored: " + ", ".join(not_ignored))
    tracked = run("git", "ls-files", cwd=root)[1].splitlines()
    staged = run("git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", cwd=root)[1].splitlines()
    bad = sorted({p for p in tracked + staged if PRIVATE_PATH.search(p) and not PRIVATE_ALLOW.search(p)})
    report("PASS" if not bad else "FAIL", "no private path tracked or staged",
           "clean" if not bad else "git rm --cached (and rotate a pushed key): " + ", ".join(bad[:5])
           + (" ..." if len(bad) > 5 else ""))


def check_env_file(root: Path, cloud: bool) -> None:
    env, example = root / ".env", root / ".env.example"
    if cloud:
        live = [k for k, filled in dotenv_keys(env).items() if filled and k in SECRET_KEYS] if env.exists() else []
        report("PASS" if not live else "FAIL", "no live keys in this container",
               "no secret values (expected: mock provider only)" if not live
               else "remove values for " + ", ".join(live) + "; containers never hold keys")
        return
    if not env.exists():
        report("WARN", ".env", "missing: cp .env.example .env (mock provider works without it)")
        return
    have = dotenv_keys(env)
    missing = [k for k in (dotenv_keys(example) if example.exists() else {}) if k not in have]
    report("PASS" if not missing else "WARN", ".env keys",
           "every .env.example key present" if not missing else "missing names: " + ", ".join(missing))


def check_settings(root: Path) -> None:
    py = root / ".venv/bin/python"
    if not py.exists():
        report("WARN", "Settings loads", "no .venv yet: uv sync --locked")
        return
    code, out = run(str(py), "-c", "import src.config as c; S = c.Settings; "
                    "S.from_env() if hasattr(S, 'from_env') else S()", cwd=root)
    report("PASS" if code == 0 else "FAIL", "Settings loads", "ok" if code == 0 else out.splitlines()[-1][:160])


def check_machine(root: Path, ci: bool) -> None:
    arch = platform.machine()
    darwin = sys.platform == "darwin"
    want = "arm64" if darwin else "x86_64"
    report("PASS" if arch == want else ("FAIL" if darwin else "WARN"), "architecture",
           arch + ("" if arch == want else f" (want {want}" + ("; a Rosetta shell)" if darwin else ")")))
    if sys.platform.startswith("linux"):
        lib, ver = platform.libc_ver()
        ok = lib == "glibc" and version(ver) >= (2, 28)
        report("PASS" if ok else "FAIL", "glibc", f"{lib} {ver} (Pillow 13 wheels need >= 2.28)")
    try:
        dev_null_ok = stat.S_ISCHR(Path("/dev/null").stat().st_mode)
    except OSError:
        dev_null_ok = False
    report("PASS" if dev_null_ok else "FAIL", "/dev/null is a character device",
           "ok" if dev_null_ok else "replaced by a file (a tool wrote -o /dev/null): sudo rm -f /dev/null && sudo mknod -m 666 /dev/null c 1 3")
    free_gb = shutil.disk_usage(root).free / 2**30
    report("PASS" if free_gb >= 5 else ("WARN" if free_gb >= 1 else "FAIL"), "free disk", f"{free_gb:.1f} GiB")
    if ci:
        return
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", 8000))
            report("PASS", "port 8000", "free")
        except OSError:
            report("WARN", "port 8000", "in use: another uvicorn running? lsof -i :8000")


def check_ollama(root: Path, mac: bool, warm: bool) -> None:
    miss = "FAIL" if mac else "WARN"  # cloud containers never run Ollama
    src = root / "src/providers/ollama.py"
    m = re.search(r'^GUIDE_MODEL\s*=\s*["\']([^"\']+)', src.read_text(), re.M) if src.exists() else None
    model = m.group(1) if m else GUIDE_MODEL_DEFAULT
    code, out = run("ollama", "--version")
    if code == 127:
        report(miss, "ollama runtime", "not installed" + ("" if mac else " (expected in a container)"))
    else:
        v = ".".join(map(str, version(out)))
        status = "PASS" if v == OLLAMA_STACK else ("WARN" if v.startswith(OLLAMA_MINOR + ".") else "FAIL")
        report(status, "ollama runtime", f"{v} (Stack {OLLAMA_STACK}; {OLLAMA_MINOR}.x accepted, auto-update may move the patch)")
    base = ollama_host(root)
    try:
        server = http_json(f"{base}/api/version").get("version", "?")
        tags = [x.get("name") for x in http_json(f"{base}/api/tags").get("models", [])]
    except Exception as exc:  # noqa: BLE001 - any failure means "not reachable"
        report(miss, "ollama server", f"{base} unreachable ({type(exc).__name__}); "
               + ("open Ollama.app" if mac else "expected in a container"))
        return
    report("PASS", "ollama server", f"{base} version {server}")
    if model not in tags:
        report(miss, "guide model pulled", f"{model} missing: ollama pull {model}")
        return
    report("PASS", "guide model pulled", model)
    if not warm:
        return
    t0 = time.monotonic()
    try:
        http_json(f"{base}/api/chat", {"model": model, "stream": False, "keep_alive": -1,
                                       "messages": [{"role": "user", "content": "Say ok."}],
                                       "options": {"num_predict": 4}}, timeout=60)
        loaded = [x for x in http_json(f"{base}/api/ps").get("models", []) if x.get("name") == model]
    except Exception as exc:  # noqa: BLE001
        report(miss, "guide model resident", f"warm-up failed ({type(exc).__name__})")
        return
    if not loaded:
        report(miss, "guide model resident", "not listed by /api/ps after warm-up")
        return
    x = loaded[0]
    size, vram = x.get("size", 0), x.get("size_vram", 0)
    proc = f"{round(100 * vram / size)}% GPU" if size else "?"
    far = x.get("expires_at", "")[:4] > str(time.gmtime().tm_year + 1)
    report("PASS" if far else "WARN", "guide model resident",
           f"SIZE {size / 2**30:.1f} GiB, {proc}, expires {x.get('expires_at', '?')[:19]}, warm-up {time.monotonic() - t0:.1f} s"
           + ("" if far else "; keep_alive=-1 did not stick"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cloud", action="store_true", help="coding-agent container checks (default on Linux)")
    ap.add_argument("--ci", action="store_true", help="skip machine-only checks")
    ap.add_argument("--json", action="store_true", help="print JSON")
    ap.add_argument("--no-warm", action="store_true", help="skip the Ollama warm-up call on the Mac")
    args = ap.parse_args()
    top = run("git", "rev-parse", "--show-toplevel")
    root = Path(top[1]) if top[0] == 0 else Path.cwd()
    cloud = args.cloud or (sys.platform != "darwin" and not args.ci)
    mac = sys.platform == "darwin" and not args.cloud and not args.ci

    check_tools(root, cloud)
    check_locks(root)
    check_git_privacy(root)
    if not args.ci:
        check_env_file(root, cloud)
    check_settings(root)
    check_machine(root, args.ci)
    if not args.ci:
        check_ollama(root, mac, warm=mac and not args.no_warm)

    counts = {s: sum(r["status"] == s for r in results) for s in ("PASS", "WARN", "FAIL")}
    mode = "ci" if args.ci else ("mac" if mac else "cloud")
    if args.json:
        print(json.dumps({"mode": mode, "root": str(root), "counts": counts, "results": results}, indent=2))
    else:
        for r in results:
            print(f"{r['status']:<5} {r['check']:<44} {r['detail']}")
        print(f"\ndoctor ({mode}): {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
