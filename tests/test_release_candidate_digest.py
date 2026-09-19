"""The R1b release-candidate digest must describe the tree it ships with.

A digest that is written once and never re-checked is decoration. These tests
make the manifest under ``release/`` a gate: a version that claims to be
releasable has to carry a manifest, and that manifest has to match the bytes a
consumer would actually receive by pinning the tag.

The gate deliberately does not fire on ``.dev`` versions. Between releases the
tree moves constantly and no candidate is being offered, so demanding a
regenerated manifest on every commit would be noise, not safety.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from azazel_fabric.provisioning_contracts.integrity import (
    ProvisioningIntegrityError,
    assert_content_digest,
    canonical_contract_json,
)
from azazel_fabric.version import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO_ROOT / "release"

sys.path.insert(0, str(REPO_ROOT / "tools"))

from rc_digest import DIGEST_FIELD, SCHEMA_VERSION, build_manifest  # noqa: E402

IS_DEV_VERSION = ".dev" in __version__
MANIFEST_PATH = RELEASE_DIR / f"v{__version__}.digest.json"

requires_release_version = pytest.mark.skipif(
    IS_DEV_VERSION,
    reason="a .dev version offers no candidate, so it carries no digest",
)


def _recorded() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@requires_release_version
def test_a_releasable_version_carries_a_manifest_named_after_it() -> None:
    assert MANIFEST_PATH.is_file(), (
        f"version {__version__} is not a .dev version, so {MANIFEST_PATH.name} "
        "must exist — regenerate with tools/rc_digest.py --out"
    )


@requires_release_version
def test_the_recorded_manifest_matches_the_tree_it_ships_with() -> None:
    recorded = _recorded()
    rebuilt = build_manifest(REPO_ROOT, candidate=recorded["release_candidate"])
    assert canonical_contract_json(recorded) == canonical_contract_json(rebuilt), (
        "release/ is stale against src/ or pyproject.toml — "
        "regenerate with tools/rc_digest.py --out"
    )


@requires_release_version
def test_the_manifest_declares_the_version_it_is_named_for() -> None:
    recorded = _recorded()
    assert recorded["package_version"] == __version__
    assert recorded["release_candidate"] == f"v{__version__}"
    assert recorded["schema_version"] == SCHEMA_VERSION


@requires_release_version
def test_the_declared_digest_covers_the_manifests_own_contents() -> None:
    assert_content_digest(_recorded(), digest_field=DIGEST_FIELD)


@requires_release_version
def test_a_tampered_file_entry_breaks_the_declared_digest() -> None:
    """The digest binds the file map, so editing one entry must fail closed."""

    tampered = _recorded()
    first = sorted(tampered["files"])[0]
    tampered["files"][first] = "sha256:" + "0" * 64
    with pytest.raises(ProvisioningIntegrityError):
        assert_content_digest(tampered, digest_field=DIGEST_FIELD)


@requires_release_version
def test_a_dropped_file_entry_breaks_the_declared_digest() -> None:
    """Removing a covered file from the map must not go unnoticed either."""

    tampered = _recorded()
    del tampered["files"][sorted(tampered["files"])[0]]
    with pytest.raises(ProvisioningIntegrityError):
        assert_content_digest(tampered, digest_field=DIGEST_FIELD)


@requires_release_version
def test_the_manifest_covers_the_installable_surface_and_nothing_else() -> None:
    """Tests, fixtures, and docs are evidence about a release, not the release."""

    covered = sorted(_recorded()["files"])
    assert covered, "an empty covered set would make the digest meaningless"
    for path in covered:
        assert path == "pyproject.toml" or path.startswith("src/"), path
    assert "src/azazel_fabric/version.py" in covered
    assert not any(p.startswith("tests/") or p.startswith("docs/") for p in covered)


def test_the_digest_is_reproducible_across_repeated_builds() -> None:
    """Two builds of the same tree must agree; no enumeration order leaks in."""

    first = build_manifest(REPO_ROOT, candidate="v0.0.0rc0")
    second = build_manifest(REPO_ROOT, candidate="v0.0.0rc0")
    assert first[DIGEST_FIELD] == second[DIGEST_FIELD]
    assert list(first["files"]) == sorted(first["files"])


def test_the_candidate_name_is_bound_by_the_digest() -> None:
    """A manifest cannot be relabelled for another candidate without re-digesting."""

    one = build_manifest(REPO_ROOT, candidate="v0.0.0rc0")
    other = build_manifest(REPO_ROOT, candidate="v0.0.0rc1")
    assert one[DIGEST_FIELD] != other[DIGEST_FIELD]
