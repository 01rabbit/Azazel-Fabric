"""The release tools run without pydantic, and produce the same bytes as before.

A signer's machine needs PyNaCl to sign and nothing else. Until
`tools/_fabric_src.py`, `rc_digest.py` and `rc_signature.py` imported the
canonical serialization through the `azazel_fabric` package, whose `__init__`
pulls in the pydantic models; preparing the `v0.9.0rc6` and `v0.9.0` signatures,
that import is what failed first.

Each tool is run here in a fresh interpreter where `import pydantic` raises, so
a regression that reaches the package again fails here rather than on the
release owner's machine. The bytes are compared with what this process computes
through the normal import path, so "runs without pydantic" cannot drift into
"runs, and signs something else".
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / "tools"
RELEASE_DIR = REPO_ROOT / "release"

sys.path.insert(0, str(TOOLS))

from rc_digest import build_manifest  # noqa: E402
from rc_signature import signable_bytes  # noqa: E402

#: Makes `import pydantic` (and so `import azazel_fabric.provisioning_contracts`,
#: which the tools used to go through) fail in the child interpreter, then
#: runs the tool as `python tools/<tool>.py ...`.
_WITHOUT_PYDANTIC = (
    "import runpy, sys\n"
    "sys.modules['pydantic'] = None\n"
    "tool = sys.argv[1]\n"
    "sys.argv = sys.argv[1:]\n"
    "runpy.run_path(tool, run_name='__main__')\n"
)

MANIFESTS = sorted(RELEASE_DIR.glob("*.digest.json"))


def _run(tool: str, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-I", "-c", _WITHOUT_PYDANTIC, str(TOOLS / tool), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )


def test_the_child_interpreter_really_has_no_pydantic():
    """The guard itself: the import path the tools used to take must fail in a
    child set up this way, or the tests below would prove nothing."""

    probe = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); sys.modules['pydantic'] = None; "
            "import azazel_fabric.provisioning_contracts",
            str(REPO_ROOT / "src"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert probe.returncode != 0
    assert b"pydantic" in probe.stderr


@pytest.mark.parametrize("manifest", MANIFESTS, ids=lambda p: p.name)
def test_signable_bytes_need_no_pydantic_and_are_unchanged(manifest):
    result = _run("rc_signature.py", str(manifest.relative_to(REPO_ROOT)), "--signable")
    assert result.returncode == 0, result.stderr.decode()
    expected = signable_bytes(json.loads(manifest.read_text(encoding="utf-8")))
    assert result.stdout, "an empty payload is what a failed import used to produce"
    assert hashlib.sha256(result.stdout).hexdigest() == hashlib.sha256(expected).hexdigest()


def test_the_tree_digest_needs_no_pydantic_and_is_unchanged():
    result = _run("rc_digest.py", "--candidate", "v0.0.0-standalone-check")
    assert result.returncode == 0, result.stderr.decode()
    produced = json.loads(result.stdout)
    expected = build_manifest(REPO_ROOT, candidate="v0.0.0-standalone-check")
    assert produced == expected
