"""Committed R1a golden fixtures — the shared conformance vectors.

``tests/fixtures/provisioning/*.json`` and ``tests/fixtures/mio/*.json`` are
stable, committed canonical instances of the scenarios the program plan's R1
exit gate enumerates. They are generated from the validated models
(valid-by-construction) and published through
``azazel_fabric.testing.load_golden_provisioning`` so Edge, Knowledge,
Deception, Nexus, and Boot candidate adapters run the *same* vectors.

This module asserts each fixture behaves exactly as its name claims — every
positive vector round-trips, and every negative vector fails closed for the
stated reason — so a contract change that would silently alter one of these
behaviors fails here.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from azazel_fabric.mio_contracts import (
    AdvisoryResult,
    MergedAdvisory,
    SanitizedRemoteFrame,
    SituationFrame,
    assert_frame_sanitized_for_egress,
)
from azazel_fabric.provisioning_contracts import (
    ActivationReceipt,
    AssetManifest,
    AuditCheckpointProjection,
    CommissioningRecord,
    CompatibilityManifest,
    HardwareInventory,
    InterfaceAssignment,
    ModelManifest,
    ProductManifest,
    ProposedGenerationDescriptor,
    ProvisioningIntegrityError,
    ResourceProfile,
    SecurityStateProjection,
    TopologyProfile,
    assert_content_digest,
    assert_not_expired,
    canonical_contract_json,
)
from azazel_fabric.testing import (
    GOLDEN_PROVISIONING_NEGATIVE,
    GOLDEN_REFERENCE_AS_OF,
    golden_provisioning_names,
    load_golden_provisioning,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_PROVISIONING = _FIXTURES / "provisioning"
_MIO = _FIXTURES / "mio"

AS_OF = datetime.fromisoformat(GOLDEN_REFERENCE_AS_OF)

# Every vector and the model that owns it. A negative vector names the model
# that must reject it.
MODELS = {
    "activation_receipt": ActivationReceipt,
    "advisory_result_executable": AdvisoryResult,
    "advisory_result_followup": AdvisoryResult,
    "advisory_result_local": AdvisoryResult,
    "advisory_result_remote": AdvisoryResult,
    "asset_manifest": AssetManifest,
    "audit_checkpoint_projection": AuditCheckpointProjection,
    "commissioning_record": CommissioningRecord,
    "commissioning_record_digest_mismatch": CommissioningRecord,
    "commissioning_record_inferred_role": CommissioningRecord,
    "compatibility_manifest": CompatibilityManifest,
    "generation_descriptor_expired": ProposedGenerationDescriptor,
    "generation_descriptor_unknown_version": ProposedGenerationDescriptor,
    "hardware_inventory": HardwareInventory,
    "hardware_inventory_ambiguous": HardwareInventory,
    "interface_assignment": InterfaceAssignment,
    "merged_advisory": MergedAdvisory,
    "model_manifest": ModelManifest,
    "product_manifest_boot": ProductManifest,
    "product_manifest_directive": ProductManifest,
    "product_manifest_nexus": ProductManifest,
    "proposed_generation_descriptor": ProposedGenerationDescriptor,
    "resource_profile": ResourceProfile,
    "resource_profile_with_tier": ResourceProfile,
    "sanitized_remote_frame": SanitizedRemoteFrame,
    "sanitized_remote_frame_restricted": SanitizedRemoteFrame,
    "security_state_projection": SecurityStateProjection,
    "situation_frame": SituationFrame,
    "topology_profile": TopologyProfile,
}

# Negative vectors that are structurally valid on purpose. A stale or tampered
# record is well-formed by definition -- it is the digest check and the expiry
# check that must catch it, and each has its own test below.
_CAUGHT_OUTSIDE_THE_SCHEMA = {
    "commissioning_record_digest_mismatch",
    "generation_descriptor_expired",
}

_MIO_VECTORS = {
    "advisory_result_executable",
    "advisory_result_followup",
    "advisory_result_local",
    "advisory_result_remote",
    "merged_advisory",
    "sanitized_remote_frame",
    "sanitized_remote_frame_restricted",
    "situation_frame",
}


def _committed(name: str) -> dict:
    directory = _MIO if name in _MIO_VECTORS else _PROVISIONING
    return json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))


def test_every_vector_has_a_committed_fixture_and_a_model():
    # Guard: if the published loader and the committed files ever diverge, the
    # parametrized tests below would silently cover less. Fail loudly instead.
    committed = {p.stem for p in _PROVISIONING.iterdir() if p.suffix == ".json"} | {
        p.stem for p in _MIO.iterdir() if p.suffix == ".json"
    }
    published = set(golden_provisioning_names())
    assert committed == published
    assert set(MODELS) == published
    assert len(published) >= 29, f"only {len(published)} vectors published"
    assert GOLDEN_PROVISIONING_NEGATIVE < published


def test_packaged_loader_agrees_with_committed_fixtures():
    # Consumers importing the loader and readers of the JSON files must never
    # diverge.
    for name in golden_provisioning_names():
        assert load_golden_provisioning(name) == _committed(name), name


def test_loader_fails_closed_on_an_unknown_vector():
    with pytest.raises(KeyError, match="unknown golden provisioning vector"):
        load_golden_provisioning("no_such_vector")


@pytest.mark.parametrize(
    "name", sorted(set(golden_provisioning_names()) - set(GOLDEN_PROVISIONING_NEGATIVE))
)
def test_positive_vector_validates_and_round_trips(name):
    payload = load_golden_provisioning(name)
    model = MODELS[name].model_validate(payload)
    assert json.loads(canonical_contract_json(model)) == payload
    assert canonical_contract_json(model) == canonical_contract_json(payload)


@pytest.mark.parametrize(
    "name", sorted(GOLDEN_PROVISIONING_NEGATIVE - _CAUGHT_OUTSIDE_THE_SCHEMA)
)
def test_negative_vector_is_rejected_by_its_model(name):
    payload = load_golden_provisioning(name)
    with pytest.raises(ValidationError):
        MODELS[name].model_validate(payload)


def test_digest_mismatch_vector_is_caught_by_the_digest_not_the_schema():
    payload = load_golden_provisioning("commissioning_record_digest_mismatch")
    CommissioningRecord.model_validate(payload)  # structurally fine on purpose
    with pytest.raises(ProvisioningIntegrityError):
        assert_content_digest(payload, digest_field="record_digest")


def test_expired_vector_fails_against_the_published_reference_time():
    payload = load_golden_provisioning("generation_descriptor_expired")
    assert payload.pop("_reference_as_of") == GOLDEN_REFERENCE_AS_OF
    # The record itself is well formed; only the expiry check rejects it, and it
    # takes an explicit reference time rather than a clock.
    descriptor = ProposedGenerationDescriptor.model_validate(payload)
    with pytest.raises(ValueError, match="expired"):
        assert_not_expired(descriptor, as_of=AS_OF)


def test_restricted_frame_vector_is_rejected_by_the_egress_check_too():
    payload = load_golden_provisioning("sanitized_remote_frame_restricted")
    with pytest.raises(ValueError, match="must not leave the node"):
        assert_frame_sanitized_for_egress(payload)


def test_positive_and_negative_vectors_cover_every_exit_gate_case():
    # The plan's R1 exit gate: "malformed, directive-bearing, unknown-version,
    # expired, and digest-mismatched fixtures fail closed".
    assert {
        "product_manifest_directive",  # directive-bearing
        "generation_descriptor_unknown_version",  # unknown version
        "generation_descriptor_expired",  # expired
        "commissioning_record_digest_mismatch",  # digest mismatch
        "hardware_inventory_ambiguous",  # malformed / ambiguous identity
        "resource_profile_with_tier",  # unratified tier claim
        "commissioning_record_inferred_role",  # inferred role
        "sanitized_remote_frame_restricted",  # restricted egress
        "advisory_result_executable",  # executability escalation
        "advisory_result_followup",  # follow-up disclosure request
    } == set(GOLDEN_PROVISIONING_NEGATIVE)


def test_committed_fixtures_are_sorted_canonical_json():
    for path in sorted(_PROVISIONING.iterdir()) + sorted(_MIO.iterdir()):
        if path.suffix != ".json":
            continue
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        expected = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        assert text == expected, f"{path.name} is not canonically formatted"
