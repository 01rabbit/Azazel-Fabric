"""The two Fabric modules the release tools need, loaded straight from ``src/``.

``tools/rc_digest.py`` and ``tools/rc_signature.py`` need only the canonical
serialization in ``provisioning_contracts/integrity.py`` and the version string
in ``version.py``. Both are standard-library only. Importing them through the
package, though, runs ``azazel_fabric/__init__.py`` and
``provisioning_contracts/__init__.py``, which import the pydantic models -- so
a signer had to install pydantic (and a Python new enough for it) just to hash
and check a manifest. Preparing the ``v0.9.0rc6`` and ``v0.9.0`` signatures,
that requirement is what failed first, and an empty ``candidate.bin`` is what a
failed import looks like from the outside.

The files are loaded by path, under private module names, so the code that
runs is the code ``src/`` ships and the digest covers. Nothing is copied: a
second copy of the canonical serialization would be a second definition of
the bytes being signed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "azazel_fabric"


def _load(name: str, relative: str) -> ModuleType:
    path = _PACKAGE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - a missing src/ file
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


integrity = _load("_azazel_fabric_release_integrity", "provisioning_contracts/integrity.py")
version = _load("_azazel_fabric_release_version", "version.py")
