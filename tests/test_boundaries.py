"""AD-1: pure domain, inward dependencies. Walks every module's imports under src/."""

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PORTS = {"src.providers.base", "src.pipeline.ports", "src.domain.clock"}
GUARDS = {"src.providers.spend", "src.providers.cache"}
"""The guarded-call path (AD-6) lives inside src/providers, so adapters may import it."""
ADAPTER_PACKAGES = ("src.providers", "src.infra")
ADAPTER_IMPORTERS = ("src.providers", "src.infra", "src.api")


def _module_name(path: Path, src_root: Path) -> str:
    parts = ("src", *path.relative_to(src_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_module(name: str, src_root: Path) -> bool:
    rel = Path(*name.split(".")[1:])
    return (src_root / rel).with_suffix(".py").exists() or (src_root / rel / "__init__.py").exists()


def _imports(path: Path, module: str, src_root: Path) -> set[str]:
    """Absolute names of every module `module` imports; `from pkg import mod` resolves to `pkg.mod`."""
    found: set[str] = set()
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                up = package.split(".")[: len(package.split(".")) - node.level + 1]
                base = ".".join([*up, base]) if base else ".".join(up)
            for alias in node.names:
                candidate = f"{base}.{alias.name}"
                found.add(candidate if _is_module(candidate, src_root) else base)
    return found


def _package(module: str) -> str:
    return ".".join(module.split(".")[:2])


def _is_adapter(module: str) -> bool:
    return module.startswith(ADAPTER_PACKAGES) and module not in PORTS and module not in ADAPTER_PACKAGES


def _in(module: str, *packages: str) -> bool:
    return any(module == p or module.startswith(p + ".") for p in packages)


def violations(src_root: Path) -> list[str]:
    stdlib = sys.stdlib_module_names
    out: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        module = _module_name(path, src_root)
        package = _package(module)
        for name in sorted(_imports(path, module, src_root)):
            top = name.split(".")[0]
            internal = top == "src"
            if package == "src.domain":
                if internal and not _in(name, "src.domain"):
                    out.append(f"{module} imports {name}; src/domain imports only src/domain")
                elif not internal and top not in stdlib and top != "pydantic":
                    out.append(f"{module} imports {name}; src/domain allows only stdlib and pydantic")
            elif package in ("src.council", "src.pipeline") and internal:
                allowed = _in(name, "src.domain", package) or name in PORTS
                if package == "src.pipeline":
                    allowed = allowed or _in(name, "src.council")
                if not allowed:
                    out.append(f"{module} imports {name}; {package} imports only the domain and ports")
            elif _is_adapter(module) and internal and not (_in(name, "src.domain") or name in PORTS | GUARDS):
                out.append(f"{module} imports {name}; adapters import only ports and the domain")
            if internal and _is_adapter(name) and not _in(module, *ADAPTER_IMPORTERS):
                out.append(f"{module} imports the adapter {name}")
    return out


def test_ratified_scaffold_has_no_violation():
    assert violations(REPO / "src") == []


def greet_callers(src_root: Path) -> list[str]:
    """Every module under `src_root` that calls `greet` on anything (AD-3: the Greeting composer alone may)."""
    out: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        calls = (node.func for node in ast.walk(tree) if isinstance(node, ast.Call))
        if any(isinstance(func, ast.Attribute) and func.attr == "greet" for func in calls):
            out.append(_module_name(path, src_root))
    return out


def test_the_greeting_composer_is_the_only_module_that_calls_greet():
    # The Ollama adapter calls `greet` only on the verbatim adapter it falls back to (AD-5), with the same Derived block.
    assert greet_callers(REPO / "src") == ["src.council.greeting", "src.providers.ollama"]


def test_pipeline_imports_only_the_domain_the_council_and_ports():
    src = REPO / "src"
    modules = sorted(src.glob("pipeline/*.py"))
    assert {path.name for path in modules} >= {"build.py", "ingest.py", "ports.py"}
    for path in modules:
        internal = {n for n in _imports(path, _module_name(path, src), src) if n.startswith("src.")}
        assert all(_in(n, "src.domain", "src.council", "src.pipeline") or n in PORTS for n in internal), (path.name, internal)


def test_schema_imports_only_stdlib_and_pydantic():
    src = REPO / "src"
    path = src / "domain" / "schema.py"
    tops = {name.split(".")[0] for name in _imports(path, "src.domain.schema", src)}
    assert tops and tops <= set(sys.stdlib_module_names) | {"pydantic"}, tops


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    src = tmp_path / "src"
    for rel, text in files.items():
        target = src / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    for pkg in {p.parent for p in src.rglob("*.py")} | {src}:
        (pkg / "__init__.py").touch()
    return src


def test_domain_importing_httpx_is_named(tmp_path):
    src = _tree(tmp_path, {"domain/schema.py": "import httpx\n"})
    assert violations(src) == ["src.domain.schema imports httpx; src/domain allows only stdlib and pydantic"]


def test_domain_importing_a_port_is_named(tmp_path):
    src = _tree(tmp_path, {"domain/x.py": "from src.providers.base import ModelProvider\n", "providers/base.py": ""})
    assert violations(src) == ["src.domain.x imports src.providers.base; src/domain imports only src/domain"]


def test_domain_allows_stdlib_pydantic_and_itself(tmp_path):
    src = _tree(tmp_path, {"domain/a.py": "import json\nfrom pydantic import BaseModel\nfrom . import b\n", "domain/b.py": ""})
    assert violations(src) == []


def test_council_importing_an_adapter_is_named(tmp_path):
    src = _tree(tmp_path, {"council/riddler.py": "from src.providers import mock\n", "providers/mock.py": ""})
    assert violations(src) == [
        "src.council.riddler imports src.providers.mock; src.council imports only the domain and ports",
        "src.council.riddler imports the adapter src.providers.mock",
    ]


def test_council_importing_pipeline_is_named(tmp_path):
    src = _tree(tmp_path, {"council/x.py": "from src.pipeline import build\n", "pipeline/build.py": ""})
    assert violations(src) == ["src.council.x imports src.pipeline.build; src.council imports only the domain and ports"]


def test_pipeline_may_import_council_domain_and_ports(tmp_path):
    src = _tree(tmp_path, {
        "pipeline/build.py": "from src.council import riddler\nfrom src.domain import schema\nfrom .ports import JobStore\nfrom src.providers.base import ModelProvider\n",
        "pipeline/ports.py": "from src.domain.clock import Clock\n",
        "council/riddler.py": "", "domain/schema.py": "", "domain/clock.py": "", "providers/base.py": "",
    })
    assert violations(src) == []


def test_pipeline_may_import_its_own_modules(tmp_path):
    src = _tree(tmp_path, {"pipeline/build.py": "from src.pipeline.ingest import validate_upload\n", "pipeline/ingest.py": ""})
    assert violations(src) == []


def test_adapter_importing_config_is_named(tmp_path):
    src = _tree(tmp_path, {"providers/meta_api.py": "from ..config import Settings\n", "config.py": ""})
    assert violations(src) == ["src.providers.meta_api imports src.config; adapters import only ports and the domain"]


def test_adapters_may_import_the_guarded_call_path(tmp_path):
    src = _tree(tmp_path, {
        "providers/meta_api.py": "from .cache import GuardedCalls\nfrom .spend import SpendLedger\n",
        "providers/cache.py": "from .spend import SpendLedger\n",
        "providers/spend.py": "", "infra/local.py": "from src.providers.spend import SpendLedger\n",
    })
    assert violations(src) == []


def test_pipeline_importing_the_guarded_call_path_is_named(tmp_path):
    src = _tree(tmp_path, {"pipeline/build.py": "from src.providers.cache import GuardedCalls\n", "providers/cache.py": ""})
    assert violations(src) == [
        "src.pipeline.build imports src.providers.cache; src.pipeline imports only the domain and ports",
        "src.pipeline.build imports the adapter src.providers.cache",
    ]


def test_infra_adapter_importing_council_is_named(tmp_path):
    src = _tree(tmp_path, {"infra/local.py": "import src.council.riddler\n", "council/riddler.py": ""})
    assert violations(src) == ["src.infra.local imports src.council.riddler; adapters import only ports and the domain"]


def test_config_importing_an_adapter_is_named(tmp_path):
    src = _tree(tmp_path, {"config.py": "from src.infra.local import JsonJobStore\n", "infra/local.py": ""})
    assert violations(src) == ["src.config imports the adapter src.infra.local"]


def test_api_may_import_adapters_and_config(tmp_path):
    src = _tree(tmp_path, {
        "api/wiring.py": "from src.config import Settings\nfrom src.providers.mock import MockProvider\nfrom src.infra import local\n",
        "config.py": "", "providers/mock.py": "", "infra/local.py": "",
    })
    assert violations(src) == []


def test_ledger_imports_only_stdlib_and_pydantic_and_no_clock():
    src = REPO / "src"
    path = src / "domain" / "ledger.py"
    names = _imports(path, "src.domain.ledger", src)
    tops = {name.split(".")[0] for name in names if not _in(name, "src.domain")}
    assert tops and tops <= set(sys.stdlib_module_names) | {"pydantic"}, tops
    assert all(_in(name, "src.domain") for name in names if name.startswith("src.")), names
    assert not tops & {"datetime", "time", "zoneinfo", "calendar"}, tops
    assert "src.domain.clock" not in names


def test_a_second_greet_caller_is_named(tmp_path):
    src = _tree(tmp_path, {
        "council/greeting.py": "def compose(phraser, derived):\n    return phraser.greet(derived)\n",
        "api/app.py": "def start(phraser, derived):\n    return phraser.greet(derived)\n",
        "providers/verbatim.py": "class VerbatimPhraser:\n    def greet(self, derived):\n        return derived\n",
    })
    assert greet_callers(src) == ["src.api.app", "src.council.greeting"]


def test_pipeline_importing_the_mock_is_named(tmp_path):
    src = _tree(tmp_path, {"pipeline/build.py": "from src.providers.mock import MockProvider\n", "providers/mock.py": ""})
    assert violations(src) == [
        "src.pipeline.build imports src.providers.mock; src.pipeline imports only the domain and ports",
        "src.pipeline.build imports the adapter src.providers.mock",
    ]


# --- Demo settings reach only timing and the Trickster source (AD-10, AD-15) -------


def readers(src_root: Path, attr: str) -> dict[str, list[ast.AST]]:
    """Each module under `src_root` that reads `<x>.<attr>`, with the expression each read sits in (a call or a keyword)."""
    out: dict[str, list[ast.AST]] = {}
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == attr:
                holder: ast.AST = node
                while holder in parents and not isinstance(holder, (ast.Call, ast.keyword, ast.stmt)):
                    holder = parents[holder]
                out.setdefault(_module_name(path, src_root), []).append(holder)
    return out


def test_demo_timescale_reaches_the_session_only_through_the_session_clock_thresholds():
    src = REPO / "src"
    reads = readers(src, "demo_timescale")
    assert set(reads) == {"src.api.meta", "src.api.wiring", "src.api.app"}
    # wiring builds the session clock from it; app flags the RoomResult `demo` (AD-8); meta reports it (AD-15).
    assert all(isinstance(r, ast.Call) and getattr(r.func, "id", None) == "SessionClock" for r in reads["src.api.wiring"])
    assert all(isinstance(r, ast.keyword) and r.arg == "demo" for r in reads["src.api.app"])
    # Only the `Meta` model in schema.py names the reported field; no session, council, pipeline or provider code does.
    for path in src.rglob("*.py"):
        if path.relative_to(src).parts[0] in ("domain", "council", "pipeline", "providers") and path.name != "schema.py":
            assert "timescale" not in _identifiers(path), path


def _identifiers(path: Path) -> str:
    """Every name, attribute and argument the module's code spells, docstrings and comments aside."""
    names = {
        getattr(node, "id", None) or getattr(node, "attr", None) or getattr(node, "arg", None)
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path)))
    }
    return " ".join(sorted(name for name in names if isinstance(name, str)))


def test_the_session_clock_scales_thresholds_and_never_t_ms():
    tree = ast.parse((REPO / "src" / "infra" / "clocks.py").read_text())
    clock = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SessionClock")
    methods = {n.name: n for n in clock.body if isinstance(n, ast.FunctionDef)}
    uses = {name for name, fn in methods.items() if any(isinstance(n, ast.Attribute) and n.attr == "timescale" for n in ast.walk(fn))}
    assert uses == {"__init__", "thresholds"}
    assert "now_ms" in methods


def test_demo_trickster_is_read_only_by_the_proposal_source_and_meta():
    reads = readers(REPO / "src", "demo_trickster")
    assert "src.api.meta" in reads and set(reads) <= {"src.api.meta", "src.council.trickster"}


def test_a_second_demo_timescale_reader_is_named(tmp_path):
    src = _tree(tmp_path, {"domain/session.py": "def apply(settings):\n    return settings.demo_timescale\n"})
    assert set(readers(src, "demo_timescale")) == {"src.domain.session"}


# --- Rung selection (Story 3.1, AD-8, AD-10) ------------------------------------------------

PHRASERS = {"src.providers.verbatim", "src.providers.ollama"}
"""The `HintPhraser` implementations, which see the Derived block with each Rung text (AD-3)."""


def test_rungs_imports_only_stdlib_pydantic_and_the_domain_with_no_clock_network_or_filesystem():
    src = REPO / "src"
    names = _imports(src / "domain" / "rungs.py", "src.domain.rungs", src)
    tops = {name.split(".")[0] for name in names if not _in(name, "src.domain")}
    assert tops <= set(sys.stdlib_module_names) | {"pydantic"}, tops
    assert not tops & {"datetime", "time", "zoneinfo", "calendar", "os", "pathlib", "io", "shutil", "socket", "http", "urllib"}, tops
    assert "src.domain.clock" not in names


def persistence_readers(src_root: Path) -> set[str]:
    """Every module under `src_root` that reads a `.persistence` attribute."""
    out: set[str] = set()
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        if any(isinstance(node, ast.Attribute) and node.attr == "persistence" for node in ast.walk(tree)):
            out.add(_module_name(path, src_root))
    return out


def test_only_rungs_and_the_phrasers_read_derived_persistence():
    readers = persistence_readers(REPO / "src")
    assert "src.domain.rungs" in readers and readers <= {"src.domain.rungs"} | PHRASERS, readers


def test_a_second_persistence_reader_is_named(tmp_path):
    src = _tree(tmp_path, {"domain/rungs.py": "def f(d):\n    return d.persistence\n",
                           "api/app.py": "def g(body):\n    return body.derived.persistence\n"})
    assert persistence_readers(src) == {"src.domain.rungs", "src.api.app"}


# --- MODE selects adapters in one place (AD-9) ------------------------------------------


MODE_BRANCH_OWNERS = ("src.api.wiring", "src.infra", "src.config")
"""Where a mode branch may live: the `src/api` wiring and `src/infra` (AD-9), and `src/config`'s per-mode refusals (AD-14)."""


def _is_mode_read(node: ast.AST) -> bool:
    """`<x>.mode`, or `<x>.get("mode", ...)`."""
    if isinstance(node, ast.Attribute):
        return node.attr == "mode"
    return (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"
        and bool(node.args) and isinstance(node.args[0], ast.Constant) and node.args[0].value == "mode"
    )


def _mode_aliases(tree: ast.AST) -> set[str]:
    """Every local name bound to a value that reads the mode, as in `mode = settings.mode`."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign | ast.AnnAssign | ast.NamedExpr) or node.value is None:
            continue
        if any(_is_mode_read(sub) for sub in ast.walk(node.value)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names |= {sub.id for target in targets for sub in ast.walk(target) if isinstance(sub, ast.Name)}
    return names


def _reads_mode(node: ast.AST, aliases: set[str]) -> bool:
    return any(
        _is_mode_read(sub) or (isinstance(sub, ast.Name) and sub.id in aliases) for sub in ast.walk(node)
    )


def mode_branches(src_root: Path) -> list[str]:
    """Every module that compares the mode, or tests or matches on it, read directly or through a local name.

    Reading it as a value or a table key is no branch.
    """
    out: set[str] = set()
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        aliases = _mode_aliases(tree)
        for node in ast.walk(tree):
            tested = (
                [node] if isinstance(node, ast.Compare)
                else [node.test] if isinstance(node, ast.If | ast.IfExp | ast.While | ast.Assert)
                else [node.subject] if isinstance(node, ast.Match)
                else node.values if isinstance(node, ast.BoolOp)
                else []
            )
            if any(_reads_mode(expr, aliases) for expr in tested):
                out.add(_module_name(path, src_root))
    return sorted(out)


def test_no_mode_branch_outside_the_wiring_and_infra():
    branches = mode_branches(REPO / "src")
    assert branches == ["src.api.wiring", "src.config"]
    assert all(_in(module, *MODE_BRANCH_OWNERS) for module in branches)


def test_meta_reads_the_mode_without_branching_on_it():
    reads = readers(REPO / "src", "mode")
    assert "src.api.meta" in reads and "src.api.meta" not in mode_branches(REPO / "src")


def test_a_mode_branch_in_a_route_module_is_named(tmp_path):
    src = _tree(tmp_path, {
        "api/app.py": "def routes(settings):\n    if settings.mode == 'hosted':\n        return []\n",
        "api/meta.py": "def text(settings):\n    return 'a' if settings.mode else 'b'\n",
        "api/wiring.py": "def wire(settings):\n    match settings.mode:\n        case 'hosted':\n            return 1\n",
        "infra/modal.py": "def pick(settings):\n    return settings.mode == 'hosted'\n",
        "api/ok.py": "TEXT = {'local': 'a'}\ndef text(settings):\n    mode = settings.mode\n    return TEXT[mode]\n",
    })
    assert mode_branches(src) == ["src.api.app", "src.api.meta", "src.api.wiring", "src.infra.modal"]


def test_a_mode_branch_through_a_local_name_is_named(tmp_path):
    src = _tree(tmp_path, {
        "api/app.py": "def routes(settings):\n    mode = settings.mode\n    if mode == 'hosted':\n        return []\n",
        "api/meta.py": "def text(data):\n    return 'a' if data.get('mode') == 'hosted' else 'b'\n",
        "api/session.py": "def text(info):\n    if (mode := info.data.get('mode')) is not None:\n        return mode\n",
    })
    assert mode_branches(src) == ["src.api.app", "src.api.meta", "src.api.session"]
