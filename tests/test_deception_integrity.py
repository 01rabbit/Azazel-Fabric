import copy

import pytest

from azazel_fabric.deception_contracts import DeceptionPackage
from azazel_fabric.deception_integrity import (
    PackageIntegrityError,
    assert_package_content_digest,
    canonical_package_signing_bytes,
    package_content_digest,
)
from azazel_fabric.testing import make_deception_package


def _canonical_package() -> dict:
    payload = make_deception_package().model_dump(mode="json")
    payload["signer_ref"] = "github:01rabbit/Azazel-Deception/.github/workflows/reference-package.yml"
    payload["signature_ref"] = "github-attestation:detached"
    payload["package_digest"] = package_content_digest(payload)
    return payload


def test_content_digest_round_trip():
    payload = _canonical_package()
    model = DeceptionPackage.model_validate(payload)
    assert_package_content_digest(model)
    assert canonical_package_signing_bytes(model) == canonical_package_signing_bytes(payload)


def test_signature_locator_is_detached_from_content_digest():
    payload = _canonical_package()
    original = package_content_digest(payload)
    payload["signature_ref"] = "github-attestation:replacement"
    assert package_content_digest(payload) == original


def test_signer_identity_is_bound_to_content_digest():
    payload = _canonical_package()
    original = package_content_digest(payload)
    payload["signer_ref"] = "github:unexpected/repository/.github/workflows/other.yml"
    assert package_content_digest(payload) != original


def test_semantic_mutation_changes_digest_and_is_rejected():
    payload = _canonical_package()
    mutated = copy.deepcopy(payload)
    mutated["narrative"]["purpose"] = "mutated narrative"
    with pytest.raises(PackageIntegrityError, match="package_digest mismatch"):
        assert_package_content_digest(mutated)


def test_image_verification_state_is_bound():
    payload = _canonical_package()
    original = package_content_digest(payload)
    payload["components"][0]["image"]["verified"] = not payload["components"][0]["image"]["verified"]
    assert package_content_digest(payload) != original
