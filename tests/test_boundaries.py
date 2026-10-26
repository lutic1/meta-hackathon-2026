"""AD-1: pure domain, inward dependencies. Walks every module's imports under src/."""

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PORTS = {"src.providers.base", "src.pipeline.ports", "src.domain.clock"}
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
                allowed = _in(name, "src.domain") or name in PORTS
                if package == "src.pipeline":
                    allowed = allowed or _in(name, "src.council")
                if not allowed:
                    out.append(f"{module} imports {name}; {package} imports only the domain and ports")
            elif _is_adapter(module) and internal and not (_in(name, "src.domain") or name in PORTS):
                out.append(f"{module} imports {name}; adapters import only ports and the domain")
            if internal and _is_adapter(name) and not _in(module, *ADAPTER_IMPORTERS):
                out.append(f"{module} imports the adapter {name}")
    return out


def test_ratified_scaffold_has_no_violation():
    assert violations(REPO / "src") == []


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


def test_adapter_importing_config_is_named(tmp_path):
    src = _tree(tmp_path, {"providers/meta_api.py": "from ..config import Settings\n", "config.py": ""})
    assert violations(src) == ["src.providers.meta_api imports src.config; adapters import only ports and the domain"]


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
