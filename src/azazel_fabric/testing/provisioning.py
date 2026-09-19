"""Published golden provisioning / M.I.O. vectors (R1a conformance kit).

These are the canonical R1a scenarios, exposed as an importable API so Edge,
Knowledge, Deception, Nexus, and Boot candidate adapters can run the *same*
vectors Fabric ships instead of hand-rolling their own. Every vector is built
from the validated models (valid-by-construction) and is deterministic — no
wall clock, no randomness, no environment lookup — so the returned dicts are
byte-stable across processes and repositories.

Vectors whose name ends in a failure word (``_expired``, ``_mismatch``,
``_with_tier``, ``_inferred_role``, ``_directive``, ``_restricted``,
``_executable``, ``_followup``, ``_unknown_version``, ``_ambiguous``) are
**negative** vectors: a conforming consumer must reject them. They are produced
by mutating a valid vector, because that is exactly how a hostile or stale
payload reaches a real consumer.
"""

from __future__ import annotations

from typing import Any, Callable

from azazel_fabric.mio_contracts import (
    AdvisoryResult,
    AliasScope,
    Claim,
    ClaimSet,
    Disagreement,
    MergedAdvisory,
    RedactionRecord,
    SanitizedRemoteFrame,
    SituationFrame,
)
from azazel_fabric.provisioning_contracts import (
    ActivationReceipt,
    AssetManifest,
    AuditCheckpointProjection,
    CaptureSupport,
    CommissioningRecord,
    CompatibilityManifest,
    FeatureMinimum,
    HardwareInventory,
    InterfaceAssignment,
    InterfaceIdentity,
    InterfaceIdentitySelector,
    IsolationProperty,
    ModelManifest,
    OperatorConfirmation,
    PlatformIdentity,
    PowerBudget,
    ProductManifest,
    ProposedGenerationDescriptor,
    ResourceProfile,
    SecurityStateProjection,
    StorageDeviceIdentity,
    TestedCompatibilityTuple,
    ThermalBudget,
    TopologyProfile,
    content_digest,
)

_T0 = "2026-09-01T00:00:00+00:00"
_T1 = "2026-09-01T00:05:00+00:00"
_T2 = "2026-09-01T00:10:00+00:00"
_T_EXPIRY = "2026-09-08T00:00:00+00:00"
_PAST_EXPIRY = "2026-01-01T00:00:00+00:00"

# The reference instant the negative "expired" vector is expired against. It is
# a test marker, not a contract field, hence the leading underscore.
GOLDEN_REFERENCE_AS_OF = "2026-09-02T00:00:00+00:00"

_ZERO_DIGEST = "sha256:" + "0" * 64


def _sha(char: str) -> str:
    return "sha256:" + char * 64


# ---------------------------------------------------------------------------
# Positive vectors
# ---------------------------------------------------------------------------


def golden_hardware_inventory() -> dict[str, Any]:
    """A two-NIC rugged host, inventoried read-only, with no role assigned."""

    draft = HardwareInventory(
        inventory_id="inv-golden-1",
        product="azazel-nexus",
        node_id="node-golden-1",
        collected_at=_T0,
        platform=PlatformIdentity(
            vendor="GoldenFixture",
            product_name="rugged-reference-1",
            board_serial="BOARD-0001",
            firmware_vendor="GoldenFirmware",
            firmware_version="1.2.3",
        ),
        interfaces=(
            InterfaceIdentity(
                interface_key="if-a",
                bus_path="pci-0000:02:00.0",
                permanent_mac="02:00:00:00:00:0a",
                pci_id="8086:15b8",
                serial="NIC-A-0001",
                driver="e1000e",
                driver_version="3.2.6-k",
                firmware_version="0.8-4",
                physical_label="LAN1",
                kernel_name_observed="enp2s0",
            ),
            InterfaceIdentity(
                interface_key="if-b",
                bus_path="pci-0000:03:00.0",
                permanent_mac="02:00:00:00:00:0b",
                pci_id="8086:15b8",
                serial="NIC-B-0002",
                driver="e1000e",
                driver_version="3.2.6-k",
                firmware_version="0.8-4",
                physical_label="LAN2",
                kernel_name_observed="enp3s0",
            ),
        ),
        storage_devices=(
            StorageDeviceIdentity(
                device_key="disk-a",
                bus_path="pci-0000:00:17.0-ata-1",
                model_name="GOLDEN-SSD",
                serial="SSD-0001",
                size_bytes=512_110_190_592,
                rotational=False,
                removable=False,
            ),
        ),
        limitations=("wireless_phy_not_present",),
        inventory_digest=_ZERO_DIGEST,
    )
    digest = content_digest(draft, digest_field="inventory_digest")
    return draft.model_copy(update={"inventory_digest": digest}).model_dump(mode="json")


def _inventory_digest() -> str:
    return golden_hardware_inventory()["inventory_digest"]


def golden_resource_profile() -> dict[str, Any]:
    """A nominal 16 GB host that measures 16095 MiB usable — and records no tier.

    This is deliberately the exact host the program plan's RAM-tier selector gets
    wrong (16095 MiB falls in its 8192-16383 `core` band although the machine is
    a 16 GB class host). Fabric records the measurement and refuses to record the
    conclusion, so an unratified threshold change cannot invalidate this vector.
    """

    return ResourceProfile(
        profile_id="res-golden-1",
        node_id="node-golden-1",
        hardware_inventory_digest=_inventory_digest(),
        measured_at=_T0,
        measurement_method="measured_usable_after_firmware_reservation",
        cpu_architecture="amd64",
        cpu_logical_cores=8,
        cpu_physical_cores=4,
        usable_memory_mib=16095,
        installed_memory_mib=16384,
        firmware_reserved_memory_mib=289,
        usable_storage_mib=488_386,
        thermal_budget=ThermalBudget(
            sustained_power_watts=28.0,
            throttle_temperature_celsius=95.0,
            cooling_class="passive_rugged",
        ),
        power_budget=PowerBudget(supply="mains", sustained_draw_watts=24.0),
        measured_core_reserve_mib=1024,
        limitations=("measured_on_one_boot",),
    ).model_dump(mode="json")


def golden_interface_assignment() -> dict[str, Any]:
    """One observation role, bound to a composite identity by an operator."""

    return InterfaceAssignment(
        assignment_id="assign-golden-1",
        node_id="node-golden-1",
        role="observation",
        selector=InterfaceIdentitySelector(
            bus_path="pci-0000:02:00.0",
            permanent_mac="02:00:00:00:00:0a",
            pci_id="8086:15b8",
            serial="NIC-A-0001",
            driver="e1000e",
            physical_label="LAN1",
        ),
        inventory_digest=_inventory_digest(),
        confirmation=OperatorConfirmation(
            operator_ref="operator:golden-1",
            method="physical_port_label_confirmed",
            confirmed_at=_T1,
            evidence_refs=("commissioning:step:role-confirm-1",),
        ),
        assigned_at=_T1,
    ).model_dump(mode="json")


def golden_topology_profile() -> dict[str, Any]:
    """One commissioned observation interface; the second stays unassigned."""

    return TopologyProfile(
        profile_id="topo-golden-1",
        node_id="node-golden-1",
        hardware_inventory_digest=_inventory_digest(),
        observed_at=_T1,
        commissioned_assignments=(
            InterfaceAssignment.model_validate(golden_interface_assignment()),
        ),
        unassigned_interface_keys=("if-b",),
        capture_support=(
            CaptureSupport(
                interface_key="if-a",
                promiscuous_supported=True,
                monitor_mode_supported=False,
                hardware_offload_active=False,
                observed_at=_T1,
                evidence_refs=("capture:probe:1",),
            ),
        ),
        management_reachability="independent_path",
        isolation_properties=(
            IsolationProperty(
                property_id="decoy-cannot-reach-management",
                description="decoy bridge cannot reach the management zone over IPv4/IPv6",
                status="demonstrated",
                test_ref="hil:isolation:1",
                observed_at=_T1,
                evidence_refs=("hil:isolation:1:report",),
            ),
            IsolationProperty(
                property_id="decoy-cannot-reach-internet",
                description="decoy bridge egress to the Internet",
                status="not_tested",
                observed_at=_T1,
            ),
        ),
        limitations=("single_boot_observation",),
    ).model_dump(mode="json")


def _profile_digests() -> tuple[str, str]:
    resource = content_digest(golden_resource_profile())
    topology = content_digest(golden_topology_profile())
    return resource, topology


def golden_commissioning_record() -> dict[str, Any]:
    """What the operator commissioned, bound to all three admission dimensions."""

    resource_digest, topology_digest = _profile_digests()
    draft = CommissioningRecord(
        record_id="comm-golden-1",
        product="azazel-nexus",
        node_id="node-golden-1",
        created_at=_T2,
        hardware_inventory_digest=_inventory_digest(),
        resource_profile_digest=resource_digest,
        topology_profile_digest=topology_digest,
        assignments=(InterfaceAssignment.model_validate(golden_interface_assignment()),),
        operator_confirmation=OperatorConfirmation(
            operator_ref="operator:golden-1",
            method="operator_console_confirmed",
            confirmed_at=_T2,
            evidence_refs=("commissioning:session:1",),
        ),
        site_ref="site:golden-lab",
        limitations=("deception_bridge_not_commissioned",),
        record_digest=_ZERO_DIGEST,
    )
    digest = content_digest(draft, digest_field="record_digest")
    return draft.model_copy(update={"record_digest": digest}).model_dump(mode="json")


def golden_product_manifest_nexus() -> dict[str, Any]:
    return ProductManifest(
        manifest_id="pm-golden-nexus",
        product="azazel-nexus",
        product_version="0.1.0",
        source_revision="0000000000000000000000000000000000000001",
        architecture="amd64",
        deployment_profile="nexus-embedded-lite",
        artifact_digest=_sha("1"),
        sbom_ref="sbom:nexus:1",
        provenance_ref="provenance:nexus:1",
        signature_refs=("signature:nexus:1",),
        schema_features=("provisioning-contracts/v0.1", "mio-contracts/v0.1"),
        released_at=_T0,
    ).model_dump(mode="json")


def golden_product_manifest_boot() -> dict[str, Any]:
    return ProductManifest(
        manifest_id="pm-golden-boot",
        product="azazel-boot",
        product_version="0.1.0",
        source_revision="0000000000000000000000000000000000000002",
        architecture="amd64",
        deployment_profile="boot-emergency-lite",
        artifact_digest=_sha("2"),
        sbom_ref="sbom:boot:1",
        provenance_ref="provenance:boot:1",
        signature_refs=("signature:boot:1",),
        schema_features=("provisioning-contracts/v0.1",),
        released_at=_T0,
    ).model_dump(mode="json")


def golden_asset_manifest() -> dict[str, Any]:
    return AssetManifest(
        manifest_id="am-golden-1",
        asset_id="asset:edge-package:1",
        asset_kind="edge_package",
        content_digest=_sha("3"),
        compressed_size_bytes=12_582_912,
        expanded_size_bytes=41_943_040,
        file_count=1843,
        max_file_size_bytes=8_388_608,
        max_path_depth=9,
        inode_count=1902,
        sbom_ref="sbom:edge:1",
        provenance_ref="provenance:edge:1",
        signature_refs=("signature:edge:1",),
        observed_at=_T0,
    ).model_dump(mode="json")


def golden_model_manifest() -> dict[str, Any]:
    return ModelManifest(
        manifest_id="mm-golden-1",
        model_id="model:local-cognition:1",
        asset_manifest_ref="am-golden-model-1",
        model_format="gguf",
        tokenizer_format="tokenizers_json",
        runtime_id="golden-runtime",
        runtime_version="1.0.0",
        parser_version="1.0.0",
        quantization="Q4_K_M",
        context_size_tokens=4096,
        required_memory_mib=3072,
    ).model_dump(mode="json")


def golden_compatibility_manifest() -> dict[str, Any]:
    """Feature-to-minimum-version rows plus one exact tested tuple."""

    return CompatibilityManifest(
        manifest_id="cm-golden-1",
        generated_at=_T0,
        feature_minimums=(
            FeatureMinimum(
                feature_id="provisioning-contracts/v0.1",
                minimum_fabric_version="0.9.0",
                notes="HardwareInventory / ResourceProfile / TopologyProfile / CommissioningRecord",
            ),
            FeatureMinimum(
                feature_id="mio-contracts/v0.1",
                minimum_fabric_version="0.9.0",
                notes="situation frames, sanitized remote frames, advisory results, merge output",
            ),
            FeatureMinimum(
                feature_id="deception-contracts/v0.1",
                minimum_fabric_version="0.5.0",
                notes="canonical AZ-06 contract family",
            ),
        ),
        tested_tuples=(
            TestedCompatibilityTuple(
                tuple_id="tt-golden-1",
                product="azazel-nexus",
                product_version="0.1.0",
                artifact_digest=_sha("1"),
                adapter_digest=_sha("4"),
                fabric_version="0.9.0",
                schema_features=("provisioning-contracts/v0.1", "mio-contracts/v0.1"),
                os_abi="linux-gnu-x86_64",
                cpu_features=("sse4_2", "avx2"),
                architecture="amd64",
                deployment_profile="nexus-embedded-lite",
                overlay_schema_version="0.1",
                evidence_ref="ci:conformance:1",
            ),
        ),
    ).model_dump(mode="json")


def golden_proposed_generation_descriptor() -> dict[str, Any]:
    """A proposed generation. It describes; it does not activate."""

    draft = ProposedGenerationDescriptor(
        descriptor_id="gen-golden-1",
        product="azazel-nexus",
        node_id="node-golden-1",
        generation_counter=7,
        previous_generation_counter=6,
        commissioning_record_digest=golden_commissioning_record()["record_digest"],
        product_manifest_digests=(_sha("1"),),
        asset_manifest_digests=(_sha("3"),),
        overlay_digest=_sha("5"),
        renderer_digest=_sha("6"),
        policy_digest=_sha("7"),
        security_epoch=3,
        proposed_at=_T2,
        expires_at=_T_EXPIRY,
        declared_irreversible_effects=(
            "packets already forwarded cannot be recalled",
            "external observations of the decoy surface cannot be withdrawn",
        ),
        limitations=("rollback_restores_only_owned_resources",),
        descriptor_digest=_ZERO_DIGEST,
    )
    digest = content_digest(draft, digest_field="descriptor_digest")
    return draft.model_copy(update={"descriptor_digest": digest}).model_dump(mode="json")


def golden_activation_receipt() -> dict[str, Any]:
    return ActivationReceipt(
        receipt_id="receipt-golden-1",
        product="azazel-nexus",
        node_id="node-golden-1",
        generation_descriptor_digest=golden_proposed_generation_descriptor()["descriptor_digest"],
        generation_counter=7,
        observed_state="activated",
        observed_at=_T_EXPIRY,
        audit_checkpoint_ref="checkpoint:golden:1",
        irreversible_effects_observed=("packets already forwarded cannot be recalled",),
        limitations=("observation_window_60s",),
        evidence_refs=("activation:verify:1",),
    ).model_dump(mode="json")


def golden_audit_checkpoint_projection() -> dict[str, Any]:
    return AuditCheckpointProjection(
        checkpoint_id="checkpoint:golden:1",
        product="azazel-nexus",
        node_id="node-golden-1",
        boot_id="boot-golden-1",
        log_epoch=2,
        security_epoch=3,
        monotonic_sequence=1041,
        previous_checkpoint_ref="checkpoint:golden:0",
        head_ref="head:golden:1041",
        policy_generation=7,
        inventory_generation=1,
        wall_time=_T2,
        monotonic_time_ns=600_000_000_000,
        assurance_profile="local_continuity_only",
        anchor_refs=(),
    ).model_dump(mode="json")


def golden_security_state_projection() -> dict[str, Any]:
    return SecurityStateProjection(
        state_id="secstate-golden-1",
        product="azazel-nexus",
        node_id="node-golden-1",
        observed_at=_T2,
        security_epoch=3,
        minimum_security_epoch=3,
        maximum_rollback_version="0.0.9",
        revocation_list_ref="revocation:golden:1",
        key_roles_present=("policy_signing", "update_signing", "audit_checkpoint"),
        device_key_state="installed_local_only",
        limitations=("no_site_identity_enrolled",),
    ).model_dump(mode="json")


def golden_situation_frame() -> dict[str, Any]:
    return SituationFrame(
        frame_id="frame-golden-1",
        product="azazel-nexus",
        node_id="node-golden-1",
        trace_id="trace-golden-mio-1",
        created_at=_T0,
        deadline_budget_ms=1500,
        memory_budget_mib=512,
        privacy_class="internal",
        evidence_refs=("edge:evidence:1", "edge:decision:1"),
        content={
            "observed_event_class": "repeated_auth_failure",
            "observed_event_count": 14,
            "window_seconds": 300,
        },
        limitations=("single_source_window",),
    ).model_dump(mode="json")


def golden_sanitized_remote_frame() -> dict[str, Any]:
    return SanitizedRemoteFrame(
        frame_id="sframe-golden-1",
        source_frame_ref="frame-golden-1",
        trace_id="trace-golden-mio-1",
        created_at=_T1,
        alias_scope=AliasScope(
            scope_kind="request",
            scope_id="request-golden-1",
            key_generation=4,
            expires_at=_T_EXPIRY,
        ),
        privacy_class="internal",
        redactions=(
            RedactionRecord(
                field_ref="content.source_address",
                privacy_class="restricted",
                action="aliased",
                alias_ref="alias:subject:a",
                reason="network identifier is restricted outside the node",
            ),
            RedactionRecord(
                field_ref="content.observed_event_count",
                privacy_class="internal",
                action="bucketed",
                reason="exact counts are reduced to coarse buckets",
            ),
        ),
        content={
            "observed_event_class": "repeated_auth_failure",
            "observed_event_bucket": "10-19",
            "subject": "alias:subject:a",
        },
        content_size_bytes=118,
        sanitizer_ref="sanitizer:allowlist:1",
    ).model_dump(mode="json")


def _local_claim_set() -> ClaimSet:
    return ClaimSet(
        claim_set_id="claims-local-1",
        trace_id="trace-golden-mio-1",
        frozen_at=_T1,
        claims=(
            Claim(
                claim_id="claim-local-1",
                statement="the observed pattern resembles credential stuffing",
                source="local_model",
                model_ref="model:local-cognition:1",
                model_generation="g4",
                input_refs=("frame-golden-1",),
                freshness="2026-09-01T00:00:00+00:00",
                confidence=0.55,
                limitations=("single_window",),
            ),
        ),
    )


def golden_advisory_result_local() -> dict[str, Any]:
    return AdvisoryResult(
        result_id="advisory-local-1",
        trace_id="trace-golden-mio-1",
        request_ref="frame-golden-1",
        origin="local",
        model_ref="model:local-cognition:1",
        model_generation="g4",
        produced_at=_T1,
        claim_set=_local_claim_set(),
        narrative_text="Repeated authentication failures from one subject within five minutes.",
        limitations=("no_external_context",),
    ).model_dump(mode="json")


def golden_advisory_result_remote() -> dict[str, Any]:
    return AdvisoryResult(
        result_id="advisory-remote-1",
        trace_id="trace-golden-mio-1",
        request_ref="sframe-golden-1",
        origin="remote",
        model_ref="model:remote-cognition:1",
        model_generation="r9",
        produced_at=_T2,
        claim_set=ClaimSet(
            claim_set_id="claims-remote-1",
            trace_id="trace-golden-mio-1",
            frozen_at=_T2,
            claims=(
                Claim(
                    claim_id="claim-remote-1",
                    statement="the observed pattern resembles a misconfigured client retry loop",
                    source="remote_model",
                    model_ref="model:remote-cognition:1",
                    model_generation="r9",
                    input_refs=("sframe-golden-1",),
                    confidence=0.4,
                    limitations=("sanitized_input_only",),
                ),
            ),
        ),
        narrative_text="The bucketed retry pattern is also consistent with a client misconfiguration.",
        limitations=("sanitized_input_only",),
    ).model_dump(mode="json")


def golden_merged_advisory() -> dict[str, Any]:
    """Local and remote disagree; the merge keeps both claims and says so."""

    return MergedAdvisory(
        merge_id="merge-golden-1",
        trace_id="trace-golden-mio-1",
        merged_at=_T2,
        input_result_refs=("advisory-local-1", "advisory-remote-1"),
        claim_set=ClaimSet(
            claim_set_id="claims-merged-1",
            trace_id="trace-golden-mio-1",
            frozen_at=_T2,
            claims=(
                _local_claim_set().claims[0],
                Claim(
                    claim_id="claim-remote-1",
                    statement="the observed pattern resembles a misconfigured client retry loop",
                    source="remote_model",
                    model_ref="model:remote-cognition:1",
                    model_generation="r9",
                    input_refs=("sframe-golden-1",),
                    confidence=0.4,
                    limitations=("sanitized_input_only",),
                ),
            ),
        ),
        disagreements=(
            Disagreement(
                topic="cause of the repeated authentication failures",
                claim_refs=("claim-local-1", "claim-remote-1"),
            ),
        ),
        narrative_text="Two cognition paths disagree; both readings are shown with their sources.",
        cognition_state="hybrid",
        limitations=("no_decision_implied",),
    ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Negative vectors (a conforming consumer must reject each one)
# ---------------------------------------------------------------------------


def golden_resource_profile_with_tier() -> dict[str, Any]:
    """A resource profile that smuggles in a RAM-derived tier."""

    bad = golden_resource_profile()
    bad["resource_tier"] = "core"
    return bad


def golden_commissioning_record_digest_mismatch() -> dict[str, Any]:
    bad = golden_commissioning_record()
    bad["site_ref"] = "site:tampered-after-digest"
    return bad


def golden_commissioning_record_inferred_role() -> dict[str, Any]:
    """A commissioning record that derives a role from a kernel name."""

    bad = golden_commissioning_record()
    bad["assignments"][0]["inferred_from_name"] = "enp2s0"
    return bad


def golden_product_manifest_directive() -> dict[str, Any]:
    """A product manifest carrying a systemd unit — a descriptive object turning
    into an instruction."""

    bad = golden_product_manifest_nexus()
    bad["systemd_unit"] = "azazel-nexus.service"
    return bad


def golden_hardware_inventory_ambiguous() -> dict[str, Any]:
    """Two interfaces with one composite identity — commissioning must fail closed."""

    bad = golden_hardware_inventory()
    duplicate = dict(bad["interfaces"][0])
    duplicate["interface_key"] = "if-c"
    duplicate["kernel_name_observed"] = "enp4s0"
    bad["interfaces"] = [*bad["interfaces"], duplicate]
    return bad


def golden_generation_descriptor_expired() -> dict[str, Any]:
    """A descriptor already expired against ``GOLDEN_REFERENCE_AS_OF``."""

    draft = ProposedGenerationDescriptor(
        descriptor_id="gen-golden-expired",
        product="azazel-nexus",
        node_id="node-golden-1",
        generation_counter=5,
        previous_generation_counter=4,
        commissioning_record_digest=golden_commissioning_record()["record_digest"],
        renderer_digest=_sha("6"),
        policy_digest=_sha("7"),
        security_epoch=2,
        proposed_at="2025-12-01T00:00:00+00:00",
        expires_at=_PAST_EXPIRY,
        descriptor_digest=_ZERO_DIGEST,
    )
    digest = content_digest(draft, digest_field="descriptor_digest")
    expired = draft.model_copy(update={"descriptor_digest": digest}).model_dump(mode="json")
    # Non-contract test marker: the reference time this descriptor is expired against.
    expired["_reference_as_of"] = GOLDEN_REFERENCE_AS_OF
    return expired


def golden_generation_descriptor_unknown_version() -> dict[str, Any]:
    bad = golden_proposed_generation_descriptor()
    bad["schema_version"] = "proposed-generation-descriptor/v9.9"
    return bad


def golden_sanitized_remote_frame_restricted() -> dict[str, Any]:
    """A frame classified restricted — it must never reach a remote endpoint."""

    bad = golden_sanitized_remote_frame()
    bad["privacy_class"] = "restricted"
    return bad


def golden_advisory_result_executable() -> dict[str, Any]:
    bad = golden_advisory_result_remote()
    bad["executable"] = True
    return bad


def golden_advisory_result_followup() -> dict[str, Any]:
    """A remote answer trying to request more disclosure."""

    bad = golden_advisory_result_remote()
    bad["follow_up_request"] = "send the unredacted source address"
    return bad


_GOLDEN_PROVISIONING: dict[str, Callable[[], dict[str, Any]]] = {
    "activation_receipt": golden_activation_receipt,
    "advisory_result_executable": golden_advisory_result_executable,
    "advisory_result_followup": golden_advisory_result_followup,
    "advisory_result_local": golden_advisory_result_local,
    "advisory_result_remote": golden_advisory_result_remote,
    "asset_manifest": golden_asset_manifest,
    "audit_checkpoint_projection": golden_audit_checkpoint_projection,
    "commissioning_record": golden_commissioning_record,
    "commissioning_record_digest_mismatch": golden_commissioning_record_digest_mismatch,
    "commissioning_record_inferred_role": golden_commissioning_record_inferred_role,
    "compatibility_manifest": golden_compatibility_manifest,
    "generation_descriptor_expired": golden_generation_descriptor_expired,
    "generation_descriptor_unknown_version": golden_generation_descriptor_unknown_version,
    "hardware_inventory": golden_hardware_inventory,
    "hardware_inventory_ambiguous": golden_hardware_inventory_ambiguous,
    "interface_assignment": golden_interface_assignment,
    "merged_advisory": golden_merged_advisory,
    "model_manifest": golden_model_manifest,
    "product_manifest_boot": golden_product_manifest_boot,
    "product_manifest_directive": golden_product_manifest_directive,
    "product_manifest_nexus": golden_product_manifest_nexus,
    "proposed_generation_descriptor": golden_proposed_generation_descriptor,
    "resource_profile": golden_resource_profile,
    "resource_profile_with_tier": golden_resource_profile_with_tier,
    "sanitized_remote_frame": golden_sanitized_remote_frame,
    "sanitized_remote_frame_restricted": golden_sanitized_remote_frame_restricted,
    "security_state_projection": golden_security_state_projection,
    "situation_frame": golden_situation_frame,
    "topology_profile": golden_topology_profile,
}

# Vectors a conforming consumer must REJECT. Everything else must validate.
GOLDEN_PROVISIONING_NEGATIVE: frozenset[str] = frozenset(
    {
        "advisory_result_executable",
        "advisory_result_followup",
        "commissioning_record_digest_mismatch",
        "commissioning_record_inferred_role",
        "generation_descriptor_expired",
        "generation_descriptor_unknown_version",
        "hardware_inventory_ambiguous",
        "product_manifest_directive",
        "resource_profile_with_tier",
        "sanitized_remote_frame_restricted",
    }
)


def golden_provisioning_names() -> list[str]:
    """Names of every published R1a vector, sorted."""

    return sorted(_GOLDEN_PROVISIONING)


def load_golden_provisioning(name: str) -> dict[str, Any]:
    """Return a fresh copy of the named R1a vector (fail-closed on an unknown name)."""

    try:
        builder = _GOLDEN_PROVISIONING[name]
    except KeyError:
        raise KeyError(
            f"unknown golden provisioning vector {name!r}; "
            f"available: {golden_provisioning_names()}"
        ) from None
    return builder()


__all__ = [
    "GOLDEN_PROVISIONING_NEGATIVE",
    "GOLDEN_REFERENCE_AS_OF",
    "golden_provisioning_names",
    "load_golden_provisioning",
] + [f.__name__ for f in _GOLDEN_PROVISIONING.values()]
