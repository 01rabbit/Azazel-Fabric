"""ARM64/AMD64 portability equivalence (Fabric#9 portability baseline).

Fabric#9 requires "one equivalent static Linux package on both architectures,
package identity preserved across hardware classes, per-platform OCI
digests/provenance". These tests assert exactly that on the shipped reference
fixture: a single package (one identity/digest) declares support for both
`arm64` and `amd64`, carries distinct per-platform image digests, and is
accepted against a host-capability report of either architecture — while its
portable identity never depends on which hardware class it targets.
"""

from __future__ import annotations

import pytest

from azazel_fabric.deception_contracts import ResourceBudget
from azazel_fabric.deception_integrity import package_signing_payload
from azazel_fabric.testing import (
    make_deception_host_capabilities,
    make_deception_package,
)

_ARCHES = ("arm64", "amd64")


def test_single_package_declares_both_architectures():
    pkg = make_deception_package()
    assert set(pkg.runtime_requirements.architectures) >= set(_ARCHES)


def test_per_platform_digests_are_distinct_and_valid():
    pkg = make_deception_package()
    platforms = {p.architecture: p for p in pkg.components[0].image.platforms}
    assert set(platforms) >= set(_ARCHES)
    arm, amd = platforms["arm64"].digest, platforms["amd64"].digest
    # Real multi-arch: the per-platform OCI digests differ...
    assert arm != amd
    # ...and each is a well-formed sha256 digest.
    for digest in (arm, amd):
        assert digest.startswith("sha256:") and len(digest) == len("sha256:") + 64


def test_package_identity_is_architecture_independent():
    # The portable identity (what package_digest binds) is the SAME regardless
    # of hardware class -- architecture lives in per-platform image data and the
    # requirements list, never in the package's identity.
    pkg = make_deception_package()
    identity = package_signing_payload(pkg)
    assert pkg.package_digest == make_deception_package().package_digest
    assert package_signing_payload(make_deception_package()) == identity


@pytest.mark.parametrize("arch", _ARCHES)
def test_host_of_either_arch_satisfies_the_package_requirement(arch: str):
    pkg = make_deception_package()
    caps = make_deception_host_capabilities(arch)
    assert caps.architecture == arch
    # A host's architecture must be one the (single) package supports.
    assert caps.architecture in pkg.runtime_requirements.architectures
    # ...and the package's minimum resources fit the reference host.
    host_budget = ResourceBudget(
        cpu_cores=caps.cpu_cores, memory_mb=caps.memory_mb, storage_mb=caps.storage_free_mb,
    )
    assert pkg.runtime_requirements.minimum.is_within(host_budget)


def test_multi_arch_platform_set_survives_round_trip():
    pkg = make_deception_package()
    before = {p.architecture: p.digest for p in pkg.components[0].image.platforms}
    restored = type(pkg).model_validate(pkg.model_dump(mode="json"))
    after = {p.architecture: p.digest for p in restored.components[0].image.platforms}
    assert after == before
    assert restored.package_digest == pkg.package_digest  # identity preserved
