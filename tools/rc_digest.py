"""Reproducible release-candidate digest for Azazel-Fabric.

The Nexus/Boot program plan (``Azazel/docs/roadmaps/nexus-boot-program-plan.md``
§5 R1) splits the contract release into R1a (draft schema plus conformance kit),
**R1b (a signed release-candidate digest)**, and R1c (a stable tag once
downstream evidence exists). This module produces the digest half of R1b.

What the digest covers is the *installable surface*: every tracked file that
``setuptools`` packages out of ``src/``, plus ``pyproject.toml``, which decides
what that package is and what it depends on. Anything a consumer would receive
by pinning the tag is bound; nothing else is. Tests, fixtures, and documentation
are deliberately outside it — they are evidence about the release, not the
release.

Reproducibility comes from ``git ls-files``: the file list is whatever the
commit records, sorted, with no filesystem enumeration order and no build step
in between. Two people running this against the same commit get byte-identical
output.

The manifest is a descriptive record. It states what bytes a candidate is made
of. It admits nothing, trusts nothing, and authorizes nothing — the signature
that makes R1b *signed* is detached and applied by the release owner, which is
why ``signature_ref`` is excluded from the digest by
``DEFAULT_DIGEST_EXCLUSIONS``: a locator assigned after signing cannot be
covered by the bytes that were signed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from azazel_fabric.provisioning_contracts.integrity import (  # noqa: E402
    canonical_contract_json,
    content_digest,
)
from azazel_fabric.version import __version__  # noqa: E402

SCHEMA_VERSION = "fabric-release-candidate-digest/v0.1"

# The installable surface, as setuptools sees it (`packages.find where=["src"]`)
# plus the file that defines the distribution itself.
COVERED_ROOTS: tuple[str, ...] = ("src",)
COVERED_FILES: tuple[str, ...] = ("pyproject.toml",)

DIGEST_FIELD = "content_digest"


def _tracked_files(repo_root: Path) -> list[str]:
    """Return the covered paths exactly as the commit records them, sorted."""

    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z", *COVERED_ROOTS, *COVERED_FILES],
        check=True,
        capture_output=True,
    )
    paths = [p for p in result.stdout.decode("utf-8").split("\0") if p]
    if not paths:
        raise SystemExit("no tracked files under the covered surface; wrong directory?")
    return sorted(paths)


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(repo_root: Path, *, candidate: str) -> dict[str, object]:
    """Return the release-candidate manifest for ``repo_root`` at its current commit."""

    files = {
        rel: _file_digest(repo_root / rel) for rel in _tracked_files(repo_root)
    }
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "release_candidate": candidate,
        "package_version": __version__,
        "covered": {"roots": list(COVERED_ROOTS), "files": list(COVERED_FILES)},
        "files": files,
    }
    manifest[DIGEST_FIELD] = content_digest(manifest, digest_field=DIGEST_FIELD)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--candidate",
        default=f"v{__version__}",
        help="release-candidate tag name (default: derived from the package version)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the manifest here instead of stdout",
    )
    parser.add_argument(
        "--check",
        type=Path,
        default=None,
        help="compare against an existing manifest and fail on any difference",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    manifest = build_manifest(repo_root, candidate=args.candidate)
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if args.check is not None:
        recorded = json.loads(args.check.read_text(encoding="utf-8"))
        if canonical_contract_json(recorded) != canonical_contract_json(manifest):
            print(
                f"{args.check} does not match the current tree", file=sys.stderr
            )
            return 1
        print(f"{args.check} matches: {manifest[DIGEST_FIELD]}")
        return 0

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}: {manifest[DIGEST_FIELD]}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
