"""Static no-side-effect boundary gate for the R1a modules (plan SR-09 / R1).

The program plan's R1 exit gate requires:

    static checks confirm that the new modules do not import operating-system
    probing, network, subprocess, installer, or runtime-control code

and the SR-09 finding ("Fabric could grow into an installer/runtime") is
answered by this file. Fabric holds representation, not behavior: a provisioning
contract describes a host, it never inspects one.

Four independent checks, because each catches something the others miss:

1. **Import allowlist (AST).** Every import in the new packages must resolve to
   a small set of pure stdlib modules plus ``pydantic`` and the family's own
   modules. A transitive escape (importing a Fabric module that itself probes
   the OS) is caught because the allowlist names the exact intra-package modules.
2. **No module-level execution (AST).** Only a docstring, imports, assignments,
   class definitions, and function definitions may appear at module scope, so
   importing the package cannot do anything.
3. **No dangerous builtin call anywhere (AST).** ``open``/``exec``/``eval``/
   ``compile``/``__import__``/``input`` are rejected at any nesting depth, which
   the import allowlist alone would not catch.
4. **Subprocess import delta (runtime).** A fresh interpreter imports
   ``pydantic`` first, snapshots ``sys.modules``, then imports the new packages.
   Nothing in the banned set may appear in the delta — this covers anything the
   AST scan cannot see.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

import azazel_fabric

_PACKAGE_ROOT = Path(azazel_fabric.__file__).parent

# The modules this gate governs. Adding a third R1 module means adding it here.
GATED_PACKAGES = ("provisioning_contracts", "mio_contracts")

# Everything a pure contract module legitimately needs.
ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "collections",  # collections.abc only -- checked below
        "datetime",
        "hashlib",
        "json",
        "re",
        "typing",
        "pydantic",
    }
)

# Intra-Fabric imports the gated packages may make: only their own family.
ALLOWED_FABRIC_PREFIXES = tuple(f"azazel_fabric.{name}" for name in GATED_PACKAGES)

# Modules that would mean Fabric had grown into an installer or a runtime.
BANNED_MODULES = frozenset(
    {
        "os", "os.path", "sys", "io", "pathlib", "shutil", "tempfile", "glob", "fnmatch",
        "subprocess", "multiprocessing", "threading", "signal", "resource", "ctypes",
        "socket", "ssl", "http", "urllib", "urllib3", "ftplib", "telnetlib", "asyncio",
        "selectors", "select", "requests", "httpx", "aiohttp",
        "platform", "psutil", "pwd", "grp", "fcntl", "termios", "tty", "pty",
        "sqlite3", "pickle", "marshal", "shelve", "dbm", "shlex",
        "importlib", "pkgutil", "runpy", "site", "sysconfig", "distutils", "setuptools", "pip",
    }
)

BANNED_BUILTINS = frozenset({"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"})


def _gated_files() -> list[Path]:
    files: list[Path] = []
    for package in GATED_PACKAGES:
        directory = _PACKAGE_ROOT / package
        assert directory.is_dir(), f"{package} is missing from the gated set"
        files.extend(sorted(directory.rglob("*.py")))
    assert files, "gate found no files to scan"
    return files


FILES = _gated_files()


def _imported_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import inside the family
                names.append(f"azazel_fabric.{GATED_PACKAGES[0]}.<relative>")
            elif node.module:
                names.append(node.module)
    return names


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_module_imports_only_pure_contract_dependencies(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for name in _imported_names(tree):
        if name.startswith("azazel_fabric"):
            assert name.startswith(ALLOWED_FABRIC_PREFIXES), (
                f"{path.name} imports {name}; a gated module may only import its own family"
            )
            continue
        root = name.split(".")[0]
        assert root not in BANNED_MODULES, (
            f"{path.name} imports {name}: OS-probing / network / subprocess / installer / "
            "runtime-control code does not belong in a Fabric contract module"
        )
        assert root in ALLOWED_IMPORT_ROOTS, (
            f"{path.name} imports {name}, which is not on the contract-module allowlist; "
            "add it deliberately or drop the dependency"
        )
        if root == "collections":
            assert name in ("collections.abc",), f"{path.name} imports {name}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_module_has_no_import_time_side_effects(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    allowed = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.ClassDef, ast.FunctionDef)
    for index, node in enumerate(tree.body):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            assert index == 0, f"{path.name} has a bare expression at module scope"
            continue
        assert isinstance(node, allowed), (
            f"{path.name} executes {type(node).__name__} at module scope; importing a "
            "Fabric contract module must do nothing"
        )


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_module_never_calls_a_dangerous_builtin(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in BANNED_BUILTINS, (
                f"{path.name} calls {node.func.id}(); a contract module performs no I/O "
                "and executes no code"
            )


def test_importing_the_gated_packages_pulls_in_no_banned_module():
    # Baseline-differential. pydantic loads much of its machinery lazily, so the
    # baseline first exercises a model shaped like ours; whatever appears after
    # that is genuinely what the two R1a families pulled in.
    script = """
import json, sys
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import azazel_fabric  # noqa: F401


class _Baseline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    a: Literal["x"] = "x"
    b: datetime
    c: tuple[str, ...] = ()
    d: dict[str, object] = Field(default_factory=dict)

    @field_validator("c")
    @classmethod
    def _c(cls, value):
        return value

    @model_validator(mode="after")
    def _m(self):
        return self


_Baseline(b="2026-01-01T00:00:00+00:00").model_dump(mode="json")
baseline = set(sys.modules)
import azazel_fabric.provisioning_contracts  # noqa: F401
import azazel_fabric.mio_contracts  # noqa: F401
print(json.dumps(sorted(set(sys.modules) - baseline)))
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    added = json.loads(result.stdout.strip().splitlines()[-1])
    assert any(name.startswith("azazel_fabric.provisioning_contracts") for name in added)
    assert any(name.startswith("azazel_fabric.mio_contracts") for name in added)

    roots = {
        name.split(".")[0]
        for name in added
        if not name.startswith("azazel_fabric") and not name.startswith("_")
    }
    offending = sorted(roots & BANNED_MODULES)
    assert not offending, (
        f"importing the R1a contract modules pulled in {offending}; Fabric must not "
        "reach the operating system, the network, or a subprocess"
    )
    # Stronger than "nothing banned": nothing outside the allowlist at all.
    unexpected = sorted(roots - ALLOWED_IMPORT_ROOTS)
    assert not unexpected, (
        f"importing the R1a contract modules pulled in {unexpected}, which is not on the "
        "contract-module allowlist"
    )


def test_gate_covers_every_r1_module():
    # Self-extending guard: every R1a contract package -- identified by its own
    # "(R1a)" module docstring, not by a hand-maintained list -- must be in
    # GATED_PACKAGES. A future R1 family that forgets to register here fails
    # rather than shipping ungated.
    declared = set()
    for init in sorted(_PACKAGE_ROOT.glob("*/__init__.py")):
        header = init.read_text(encoding="utf-8")[:400]
        if "(R1a)" in header:
            declared.add(init.parent.name)
    assert declared, "no package declares itself an R1a contract family"
    missing = sorted(declared - set(GATED_PACKAGES))
    assert not missing, f"R1a package(s) {missing} are not covered by the no-side-effect gate"
    for package in GATED_PACKAGES:
        assert (_PACKAGE_ROOT / package / "__init__.py").exists()
