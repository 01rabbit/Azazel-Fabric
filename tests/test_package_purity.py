"""Fabric describes. It never reaches the OS, the network, or a subprocess.

`tests/test_provisioning_no_side_effects.py` enforces that for the two R1a
families, with additional rules that are specific to them (a narrow import
allowlist, and isolation from other families). Those extra rules are why it
cannot simply be widened: `effect_contracts` legitimately imports `enum`, and
`deception_contracts` legitimately imports another family.

The *purity* half of it is not R1a-specific at all. A family outside R1 that
imported `subprocess` would be exactly as wrong, and until this file nothing
caught it: `outcome_contracts`, `effect_contracts` and `schema.defensive_state`
all shipped ungated by that rule.

So this covers **every** module in the package and checks only the thing that
is true of all of them.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

import azazel_fabric
from tests.test_provisioning_no_side_effects import BANNED_MODULES

PACKAGE_ROOT = Path(azazel_fabric.__file__).parent

#: Every module Fabric ships. Walked, never listed: a hand-kept list omits the
#: module somebody added last, which is the one that has not been looked at.
FILES = sorted(
    path
    for path in PACKAGE_ROOT.rglob("*.py")
    if "__pycache__" not in path.parts
)


def _imported_roots(tree: ast.AST) -> set[str]:
    """Top-level package of every import, at any nesting depth.

    `ast.walk` rather than a scan of the module body, because an import inside
    a function is still an import -- and a deferred one is how a module that
    must stay pure at import time reaches for a subprocess at call time.
    """

    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and not node.level:
                roots.add(node.module.split(".")[0])
    return roots


def test_the_sweep_is_not_empty_and_reaches_every_family():
    """A guard over a file list that silently became empty guards nothing."""
    assert len(FILES) > 20, f"only {len(FILES)} modules found under {PACKAGE_ROOT}"

    swept = {path.relative_to(PACKAGE_ROOT).parts[0] for path in FILES}
    for family in ("provisioning_contracts", "effect_contracts", "schema", "view"):
        assert family in swept, f"{family} is not in the purity sweep"


@pytest.mark.parametrize(
    "path", FILES, ids=lambda p: str(p.relative_to(PACKAGE_ROOT))
)
def test_no_module_imports_the_operating_system_or_the_network(path: Path):
    offending = sorted(_imported_roots(ast.parse(path.read_text(encoding="utf-8")))
                       & BANNED_MODULES)

    assert offending == [], (
        f"{path.relative_to(PACKAGE_ROOT)} imports {offending}. Fabric describes: "
        "it defines the words products exchange and never reaches the operating "
        "system, the network, a subprocess, an installer, or a runtime control "
        "path. A product does those things with its own authority."
    )


def test_importing_the_whole_package_pulls_in_no_banned_module():
    """The static sweep's blind spot: what an import actually loads.

    A module can stay clean in its own source and still pull a banned module in
    through something it imports. Run in a subprocess so the check sees a fresh
    interpreter rather than whatever this test session already loaded.

    **Baseline-differential**, for the reason
    `test_provisioning_no_side_effects.py` gives: pydantic loads much of its
    machinery lazily, and building the first model pulls in `socket`, `urllib`,
    `platform` and nine more — measured, not assumed. Snapshotting before that
    happens attributes pydantic's imports to Fabric and fails on a finding that
    is not Fabric's. The walking machinery (`importlib`, `pkgutil`) is imported
    before the snapshot for the same reason: the harness must not appear in its
    own measurement.
    """

    script = (
        "import json, sys, importlib, pkgutil\n"
        "from typing import Any\n"
        "from pydantic import BaseModel, ConfigDict, Field\n"
        "\n"
        "class _Baseline(BaseModel):\n"
        "    model_config = ConfigDict(extra='forbid', frozen=True)\n"
        "    a: str = 'x'\n"
        "    b: dict[str, Any] = Field(default_factory=dict)\n"
        "\n"
        "_Baseline().model_dump(mode='json')\n"
        "baseline = set(sys.modules)\n"
        "import azazel_fabric\n"
        "for info in pkgutil.walk_packages(\n"
        "    azazel_fabric.__path__, azazel_fabric.__name__ + '.'\n"
        "):\n"
        "    importlib.import_module(info.name)\n"
        "print(json.dumps(sorted(set(sys.modules) - baseline)))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr

    added = json.loads(result.stdout.strip().splitlines()[-1])
    assert any(name.startswith("azazel_fabric.") for name in added), (
        "the walk imported no submodule, so this proved nothing"
    )

    roots = {
        name.split(".")[0]
        for name in added
        if not name.startswith("azazel_fabric") and not name.startswith("_")
    }
    offending = sorted(roots & BANNED_MODULES)

    assert offending == [], (
        f"importing every Fabric module pulled in {offending}; Fabric must not "
        "reach the operating system, the network, or a subprocess"
    )
