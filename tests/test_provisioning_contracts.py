"""Contract tests for the R1a provisioning family.

These test the *specification* the program plan's §5 R1 states, not the
implementation: a provisioning record describes and never authorizes, a
resource profile records an envelope and never a tier or a capability, an
interface role comes from explicit operator confirmation against a composite
identity and never from a name/link/route, and every canonical form round-trips
byte-identically.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from azazel_fabric.deception_integrity import canonical_package_signing_bytes
from azazel_fabric.outcome_contracts import canonical_fact_json
from azazel_fabric.provisioning_contracts import (
    ActivationReceipt,
    AssetManifest,
    CommissioningRecord,
    CompatibilityManifest,
    HardwareInventory,
    InterfaceAssignment,
    InterfaceIdentitySelector,
    InterfaceResolutionError,
    ModelManifest,
    ProductManifest,
    ProposedGenerationDescriptor,
    ProvisioningIntegrityError,
    ResourceProfile,
    TopologyProfile,
    assert_content_digest,
    assert_no_provisioning_directives,
    assert_no_resource_tier_claim,
    assert_no_role_inference,
    assert_not_expired,
    assert_selector_is_composite,
    canonical_contract_json,
    content_digest,
    interface_composite_key,
    matching_interfaces,
    resolve_interface_assignment,
)
from azazel_fabric.provisioning_contracts.registry import (
    CAPABILITY_STATES,
    REGISTERED_DEPLOYMENT_PROFILES,
    REGISTERED_PRODUCTS,
    is_registered_product,
)
from azazel_fabric.testing import load_golden_provisioning

AS_OF = datetime(2026, 9, 2, tzinfo=timezone.utc)


def inventory() -> HardwareInventory:
    return HardwareInventory.model_validate(load_golden_provisioning("hardware_inventory"))


def resource_profile() -> ResourceProfile:
    return ResourceProfile.model_validate(load_golden_provisioning("resource_profile"))


def topology_profile() -> TopologyProfile:
    return TopologyProfile.model_validate(load_golden_provisioning("topology_profile"))


def commissioning_record() -> CommissioningRecord:
    return CommissioningRecord.model_validate(load_golden_provisioning("commissioning_record"))


def descriptor() -> ProposedGenerationDescriptor:
    return ProposedGenerationDescriptor.model_validate(
        load_golden_provisioning("proposed_generation_descriptor")
    )


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------


def test_nexus_and_boot_are_registered_product_names():
    # R1 deliverable: "define Nexus and Boot product names in open extension
    # registries". Without this a consumer invents its own spelling.
    assert is_registered_product("azazel-nexus")
    assert is_registered_product("azazel-boot")
    assert "nexus-embedded-lite" in REGISTERED_DEPLOYMENT_PROFILES
    assert "boot-emergency-lite" in REGISTERED_DEPLOYMENT_PROFILES


def test_product_registry_is_open_not_a_closed_enum():
    # An unregistered product is descriptive data, not a validation error: the
    # registry documents names, it does not gate them.
    assert not is_registered_product("azazel-unknown")
    manifest = ProductManifest.model_validate(load_golden_provisioning("product_manifest_nexus"))
    assert manifest.model_copy(update={"product": "azazel-unknown"}).product == "azazel-unknown"
    assert set(REGISTERED_PRODUCTS) >= {"azazel-edge", "azazel-knowledge", "azazel-deception"}


# ---------------------------------------------------------------------------
# A ResourceProfile records an envelope, never a tier or a capability
# ---------------------------------------------------------------------------


def test_resource_profile_records_measured_usable_mib_and_no_tier():
    profile = resource_profile()
    # The exact host the program plan's selector gets wrong: nominal 16 GB,
    # 16095 MiB measured usable. Fabric records the measurement only.
    assert profile.usable_memory_mib == 16095
    assert profile.measurement_method == "measured_usable_after_firmware_reservation"
    payload = profile.model_dump(mode="json")
    for banned in ("tier", "resource_tier", "capability_state", "authority_level", "selected_tier"):
        assert banned not in payload


def test_resource_profile_rejects_a_smuggled_tier():
    payload = load_golden_provisioning("resource_profile_with_tier")
    assert payload["resource_tier"] == "core"
    with pytest.raises(ValidationError):
        ResourceProfile.model_validate(payload)
    with pytest.raises(ValueError, match="tier / capability state / authority level"):
        assert_no_resource_tier_claim(payload)


@pytest.mark.parametrize(
    "key",
    ["tier", "ramTier", "resource-tier", "capability_state", "authority_level", "effective_capability"],
)
def test_tier_and_capability_keys_are_rejected_in_any_spelling(key):
    with pytest.raises(ValueError):
        assert_no_resource_tier_claim({"nested": {key: "lite"}})


def test_no_contract_field_is_named_after_a_capability_state():
    # CORE/LITE/FULL are capability states a product computes from the
    # intersection of every admission dimension. No single record may imply one.
    import azazel_fabric.mio_contracts as mc
    import azazel_fabric.provisioning_contracts as pc

    assert CAPABILITY_STATES == ("CORE", "LITE", "FULL")
    lowered = {state.lower() for state in CAPABILITY_STATES}
    for module in (pc, mc):
        for name in module.__all__:
            model = getattr(module, name)
            for field in getattr(model, "model_fields", {}):
                assert field.lower() not in lowered, f"{name}.{field} names a capability state"


def test_resource_profile_arithmetic_must_be_consistent():
    payload = load_golden_provisioning("resource_profile")
    payload["usable_memory_mib"] = payload["installed_memory_mib"] + 1
    with pytest.raises(ValidationError):
        ResourceProfile.model_validate(payload)


# ---------------------------------------------------------------------------
# Interface roles: explicit confirmation, composite identity, fail closed
# ---------------------------------------------------------------------------


def test_composite_key_ignores_the_kernel_interface_name():
    # A kernel name is unstable across reboots and driver reloads; matching on it
    # is the inference the plan forbids. Renaming must not change identity.
    original = inventory().interfaces[0]
    renamed = original.model_copy(update={"kernel_name_observed": "eth7"})
    assert interface_composite_key(original) == interface_composite_key(renamed)


def test_mac_only_selector_is_rejected():
    with pytest.raises(ValidationError):
        InterfaceIdentitySelector(
            bus_path="pci-0000:02:00.0", permanent_mac="02:00:00:00:00:0a"
        )
    with pytest.raises(InterfaceResolutionError, match="MAC-only"):
        assert_selector_is_composite({"permanent_mac": "02:00:00:00:00:0a"})
    # A bus path plus a MAC is still not enough: without a PCI/USB identity or a
    # serial, a cloned MAC in the same slot would resolve.
    with pytest.raises(InterfaceResolutionError, match="pci_id"):
        assert_selector_is_composite(
            {"bus_path": "pci-0000:02:00.0", "permanent_mac": "02:00:00:00:00:0a"}
        )


def test_assignment_resolves_to_exactly_one_interface():
    assignment = InterfaceAssignment.model_validate(
        load_golden_provisioning("interface_assignment")
    )
    resolved = resolve_interface_assignment(inventory(), assignment)
    assert resolved.interface_key == "if-a"
    assert assignment.role == "observation"
    assert assignment.confirmation.method == "physical_port_label_confirmed"


def test_zero_matches_fail_closed():
    assignment = InterfaceAssignment.model_validate(
        load_golden_provisioning("interface_assignment")
    )
    absent = assignment.model_copy(
        update={
            "selector": assignment.selector.model_copy(
                update={"permanent_mac": "02:00:00:00:00:ff"}
            )
        }
    )
    with pytest.raises(InterfaceResolutionError, match="no inventory interface matches"):
        resolve_interface_assignment(inventory(), absent)


def test_multiple_matches_fail_closed():
    # Two interfaces sharing one composite identity must stop commissioning, not
    # let the resolver pick one.
    ambiguous = load_golden_provisioning("hardware_inventory_ambiguous")
    assignment = InterfaceAssignment.model_validate(
        load_golden_provisioning("interface_assignment")
    )
    with pytest.raises(InterfaceResolutionError, match="ambiguous"):
        resolve_interface_assignment(ambiguous, assignment)
    # ...and the inventory that contains them cannot even be constructed.
    with pytest.raises(ValidationError):
        HardwareInventory.model_validate(ambiguous)


def test_matching_requires_every_specified_selector_field():
    assignment = InterfaceAssignment.model_validate(
        load_golden_provisioning("interface_assignment")
    )
    wrong_serial = assignment.selector.model_copy(update={"serial": "NIC-B-0002"})
    assert matching_interfaces(inventory().interfaces, wrong_serial) == ()


@pytest.mark.parametrize(
    "key", ["inferred_role", "link_state", "has_default_route", "operstate", "autodetected_role"]
)
def test_role_inference_fields_are_rejected(key):
    with pytest.raises(ValueError, match="may not be inferred"):
        assert_no_role_inference({"assignments": [{key: "observation"}]})


def test_commissioning_record_rejects_an_inferred_role():
    payload = load_golden_provisioning("commissioning_record_inferred_role")
    with pytest.raises(ValidationError):
        CommissioningRecord.model_validate(payload)
    # ...and specifically because it infers a role, not merely because the field
    # was unexpected: the inference scanner must reject it on its own.
    with pytest.raises(ValueError, match="may not be inferred"):
        assert_no_role_inference(payload)


def test_an_assignment_must_be_bound_to_the_inventory_it_was_made_against():
    # A changed NIC identity must invalidate the commissioning, not silently
    # re-bind the role to whatever is there now.
    payload = load_golden_provisioning("commissioning_record")
    payload["assignments"][0]["inventory_digest"] = "sha256:" + "9" * 64
    with pytest.raises(ValidationError, match="bound to this record's hardware inventory"):
        CommissioningRecord.model_validate(payload)


def test_operator_confirmation_has_no_inference_method():
    from azazel_fabric.provisioning_contracts.models import OperatorConfirmation
    from typing import get_args

    methods = set(get_args(OperatorConfirmation.model_fields["method"].annotation))
    assert methods == {
        "physical_port_label_confirmed",
        "port_identify_blink_confirmed",
        "operator_console_confirmed",
        "signed_site_approval",
    }
    # Every value is something a person did; none is a property of the machine.
    machine_properties = {"name", "link", "carrier", "route", "operstate", "default"}
    for method in methods:
        assert not (set(method.split("_")) & machine_properties), method


# ---------------------------------------------------------------------------
# Directive / authority ban
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("shell_command", "systemctl start x"),
        ("systemd_unit", "azazel.service"),
        ("default_route", "0.0.0.0/0"),
        ("nft_rule", "add rule inet filter"),
        ("device_path", "/dev/sda"),
        ("executor", "azazel.exec"),
        ("authorized", True),
        ("approved", True),
        ("trusted", True),
        ("signature_valid", True),
        ("nexus_shell_command", "x"),
        ("edge_firewall_rule", "x"),
        ("deviceNode", "/dev/sdb"),
        ("device-path", "/dev/sdc"),
    ],
)
def test_directive_and_authority_fields_are_rejected(field, value):
    with pytest.raises(ValueError, match="provisioning authority invariant violated"):
        assert_no_provisioning_directives({"outer": {field: value}})


def test_bus_path_is_not_treated_as_a_device_path():
    # The plan mandates bus path as part of the composite identity; a PCI/USB
    # topology address is not an actionable device node.
    assert_no_provisioning_directives({"bus_path": "pci-0000:02:00.0"})


def test_product_manifest_rejects_a_smuggled_unit():
    payload = load_golden_provisioning("product_manifest_directive")
    with pytest.raises(ValidationError):
        ProductManifest.model_validate(payload)
    with pytest.raises(ValueError):
        assert_no_provisioning_directives(payload)


def test_every_provisioning_record_declares_a_descriptive_authority():
    for record in (
        inventory(),
        resource_profile(),
        topology_profile(),
        commissioning_record(),
        descriptor(),
    ):
        assert record.authority == "descriptive_only"
    receipt = ActivationReceipt.model_validate(load_golden_provisioning("activation_receipt"))
    assert receipt.authority == "observation_only"


def test_compatibility_manifest_is_a_claim_not_an_admission():
    manifest = CompatibilityManifest.model_validate(
        load_golden_provisioning("compatibility_manifest")
    )
    assert manifest.claim_scope == "descriptive_claim_only"
    assert manifest.authority == "descriptive_only"
    features = {row.feature_id for row in manifest.feature_minimums}
    assert {"provisioning-contracts/v0.1", "mio-contracts/v0.1"} <= features
    # Nothing on a tested tuple says "admitted", "approved", or "trusted".
    assert_no_provisioning_directives(manifest)


def test_model_manifest_pins_every_code_execution_escape_hatch():
    manifest = ModelManifest.model_validate(load_golden_provisioning("model_manifest"))
    assert manifest.model_supplied_code is False
    assert manifest.dynamic_loader is False
    assert manifest.native_plugins is False
    assert manifest.executable_serialization is False
    assert manifest.network_fetch_on_load is False
    payload = manifest.model_dump(mode="json")
    payload["model_supplied_code"] = True
    with pytest.raises(ValidationError):
        ModelManifest.model_validate(payload)


def test_asset_manifest_cannot_declare_non_regular_files():
    manifest = AssetManifest.model_validate(load_golden_provisioning("asset_manifest"))
    assert manifest.declared_regular_files_only is True
    payload = manifest.model_dump(mode="json")
    payload["declared_regular_files_only"] = False
    with pytest.raises(ValidationError):
        AssetManifest.model_validate(payload)


def test_delta_asset_must_declare_its_final_tree_digest():
    payload = load_golden_provisioning("asset_manifest")
    payload["base_digest"] = "sha256:" + "b" * 64
    with pytest.raises(ValidationError, match="final_tree_digest"):
        AssetManifest.model_validate(payload)


# ---------------------------------------------------------------------------
# Canonical bytes, digests, expiry
# ---------------------------------------------------------------------------


def test_canonical_json_round_trip_is_byte_identical():
    for name in (
        "hardware_inventory",
        "resource_profile",
        "topology_profile",
        "commissioning_record",
        "proposed_generation_descriptor",
        "activation_receipt",
        "compatibility_manifest",
    ):
        payload = load_golden_provisioning(name)
        once = canonical_contract_json(payload)
        twice = canonical_contract_json(json.loads(once))
        assert once == twice, name


def test_canonical_form_matches_every_other_contract_family():
    # One canonicalization across the repository: a record hashed by the
    # provisioning helper, the outcome helper, and the deception helper must
    # produce the same bytes, or two repositories would sign different things.
    payload = load_golden_provisioning("resource_profile")
    assert canonical_contract_json(payload) == canonical_fact_json(payload)
    assert canonical_contract_json(payload).encode("utf-8") == canonical_package_signing_bytes(
        payload
    )


def test_content_digest_binds_every_field_except_the_digest_itself():
    record = commissioning_record()
    assert_content_digest(record, digest_field="record_digest")
    tampered = record.model_dump(mode="json")
    tampered["site_ref"] = "site:tampered"
    with pytest.raises(ProvisioningIntegrityError, match="record_digest mismatch"):
        assert_content_digest(tampered, digest_field="record_digest")


def test_digest_mismatch_fixture_fails_closed():
    payload = load_golden_provisioning("commissioning_record_digest_mismatch")
    # It is still structurally valid -- which is exactly why the digest check is
    # the thing that has to catch it.
    CommissioningRecord.model_validate(payload)
    with pytest.raises(ProvisioningIntegrityError):
        assert_content_digest(payload, digest_field="record_digest")


def test_inventory_digest_changes_when_any_interface_changes():
    original = inventory()
    before = content_digest(original, digest_field="inventory_digest")
    renamed = original.model_copy(
        update={
            "interfaces": (
                original.interfaces[0].model_copy(update={"physical_label": "LAN9"}),
                original.interfaces[1],
            )
        }
    )
    assert content_digest(renamed, digest_field="inventory_digest") != before


def test_expiry_requires_an_explicit_reference_time():
    # Fabric holds no clock: the caller supplies `as_of`, so the result is
    # deterministic and replayable.
    assert_not_expired(descriptor(), as_of=AS_OF)
    expired = load_golden_provisioning("generation_descriptor_expired")
    assert expired["_reference_as_of"] == "2026-09-02T00:00:00+00:00"
    with pytest.raises(ValueError, match="expired"):
        assert_not_expired(expired, as_of=AS_OF)


def test_descriptor_expiry_must_follow_its_proposal():
    payload = load_golden_provisioning("proposed_generation_descriptor")
    payload["expires_at"] = payload["proposed_at"]
    with pytest.raises(ValidationError, match="later than proposed_at"):
        ProposedGenerationDescriptor.model_validate(payload)


def test_generation_counter_must_increase():
    payload = load_golden_provisioning("proposed_generation_descriptor")
    payload["previous_generation_counter"] = payload["generation_counter"]
    with pytest.raises(ValidationError, match="must increase"):
        ProposedGenerationDescriptor.model_validate(payload)


def test_unknown_schema_version_fails_closed():
    payload = load_golden_provisioning("generation_descriptor_unknown_version")
    with pytest.raises(ValidationError):
        ProposedGenerationDescriptor.model_validate(payload)


def test_extra_fields_fail_closed_on_every_provisioning_model():
    payload = load_golden_provisioning("topology_profile")
    payload["activate_now"] = True
    with pytest.raises(ValidationError):
        TopologyProfile.model_validate(payload)
