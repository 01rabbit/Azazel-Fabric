"""Canonical provisioning and commissioning contracts (R1a).

These types describe *what a host is, what was commissioned on it, what was
released for it, and what was observed afterwards*. They contain no installer,
decision, network, container, or model-execution logic, perform no I/O, and have
no import-time side effects.

Authority rule, unchanged:

    Fabric describes. Knowledge advises. Edge decides and enforces. Deception
    materializes an Edge-approved environment. Nexus and Boot integrate these
    products without creating another decision authority.

Three invariants are structural rather than advisory, because each one is a
place where a descriptive record could quietly become an authority:

* **No effective capability in one record.** Effective capability is

      resource profile n topology profile n verified asset set n trust/health

  so :class:`ResourceProfile` records a measured envelope and nothing else, and
  :class:`TopologyProfile` records commissioned interfaces, capture support,
  management reachability, and demonstrated isolation and nothing else. Neither
  carries a tier, a capability state, or an authority level — ``CORE``/``LITE``/
  ``FULL`` are capability states a *product* computes, never authority levels,
  and the MiB-to-tier threshold table is a product-local, currently unratified
  decision that is deliberately absent from these contracts.
* **No inferred interface role.** A role is never derived from a kernel name, a
  link state, or a default route. :class:`InterfaceAssignment` binds a role to a
  composite hardware identity plus an explicit :class:`OperatorConfirmation`,
  and resolution against an inventory fails closed on zero or multiple matches
  (``validation.resolve_interface_assignment``).
* **No activation authority.** :class:`ProposedGenerationDescriptor` *proposes*
  and :class:`ActivationReceipt` *observes*. Neither authorizes; both pin
  ``authority`` to a descriptive/observational literal, and the recursive
  directive ban keeps commands, units, routes, firewall rules, device paths,
  executors, boolean authorizations, and trust decisions out of every payload.

The initial wire family is ``*/v0.1`` and is additive to existing Fabric
contracts.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from azazel_fabric.provisioning_contracts.validation import (
    assert_no_provisioning_directives,
    assert_no_resource_tier_claim,
    assert_no_role_inference,
    interface_composite_key,
)

Architecture = Literal["amd64", "arm64"]

# An interface role. ``unassigned`` is the state every interface holds until an
# operator confirms a role during commissioning.
InterfaceRole = Literal[
    "asset_acquisition",
    "deception_bridge",
    "management",
    "observation",
    "unassigned",
]

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAC = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")


def _valid_sha256(value: str) -> str:
    if not _SHA256.match(value):
        raise ValueError("digest must be a lowercase 'sha256:<64 hex>' string")
    return value


def _optional_sha256(value: str | None) -> str | None:
    return None if value is None else _valid_sha256(value)


class _Descriptive(BaseModel):
    """Base for every provisioning record: closed, immutable, describe-only."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Hardware inventory (read-only observation)
# ---------------------------------------------------------------------------


class InterfaceIdentity(_Descriptive):
    """Composite identity of one network interface, from read-only inventory.

    Carries no role. ``kernel_name_observed`` is recorded because an operator
    sees it on screen, but it is unstable across reboots and driver reloads and
    is excluded from the composite key used for matching — deriving a role from
    it is exactly the failure mode the program plan's AR-12 finding names.
    """

    schema_version: Literal["interface-identity/v0.1"] = "interface-identity/v0.1"
    interface_key: str = Field(min_length=1, max_length=128)
    bus_path: str = Field(min_length=1, max_length=128)
    permanent_mac: str = Field(min_length=17, max_length=17)
    pci_id: str | None = Field(default=None, max_length=32)
    usb_vid_pid: str | None = Field(default=None, max_length=32)
    serial: str | None = Field(default=None, max_length=128)
    driver: str = Field(min_length=1, max_length=64)
    driver_version: str | None = Field(default=None, max_length=64)
    firmware_version: str | None = Field(default=None, max_length=64)
    wireless_phy: str | None = Field(default=None, max_length=64)
    physical_label: str | None = Field(default=None, max_length=64)
    kernel_name_observed: str | None = Field(default=None, max_length=64)

    @field_validator("permanent_mac")
    @classmethod
    def _normalized_mac(cls, value: str) -> str:
        if not _MAC.match(value):
            raise ValueError("permanent_mac must be lowercase colon-separated (aa:bb:cc:dd:ee:ff)")
        return value


class StorageDeviceIdentity(_Descriptive):
    """Identity of one storage device. Deliberately carries no device path."""

    schema_version: Literal["storage-device-identity/v0.1"] = "storage-device-identity/v0.1"
    device_key: str = Field(min_length=1, max_length=128)
    bus_path: str = Field(min_length=1, max_length=128)
    model_name: str | None = Field(default=None, max_length=128)
    serial: str | None = Field(default=None, max_length=128)
    size_bytes: int = Field(ge=0)
    rotational: bool
    removable: bool


class PlatformIdentity(_Descriptive):
    """Chassis/firmware identity as reported by the platform."""

    schema_version: Literal["platform-identity/v0.1"] = "platform-identity/v0.1"
    vendor: str | None = Field(default=None, max_length=128)
    product_name: str | None = Field(default=None, max_length=128)
    board_serial: str | None = Field(default=None, max_length=128)
    firmware_vendor: str | None = Field(default=None, max_length=128)
    firmware_version: str | None = Field(default=None, max_length=64)


class HardwareInventory(_Descriptive):
    """Read-only record of the hardware a product observed on one node.

    Collection is pinned to ``read_only_inventory``: an inventory is something a
    product *looked at*, never something it changed. Interface keys are unique so
    a commissioning record can reference exactly one of them.
    """

    schema_version: Literal["hardware-inventory/v0.1"] = "hardware-inventory/v0.1"
    inventory_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    collected_at: datetime
    collection_method: Literal["read_only_inventory"] = "read_only_inventory"
    platform: PlatformIdentity
    interfaces: tuple[InterfaceIdentity, ...] = Field(default_factory=tuple, max_length=64)
    storage_devices: tuple[StorageDeviceIdentity, ...] = Field(default_factory=tuple, max_length=64)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    inventory_digest: str
    authority: Literal["descriptive_only"] = "descriptive_only"

    _digest = field_validator("inventory_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "HardwareInventory":
        payload = self.model_dump(mode="json")
        assert_no_provisioning_directives(payload)
        assert_no_role_inference(payload)
        assert_no_resource_tier_claim(payload)
        keys = [item.interface_key for item in self.interfaces]
        if len(set(keys)) != len(keys):
            raise ValueError("hardware inventory interface keys must be unique")
        composites = [interface_composite_key(item) for item in self.interfaces]
        if len(set(composites)) != len(composites):
            raise ValueError(
                "hardware inventory contains two interfaces with the same composite "
                "identity; an ambiguous identity must fail closed, not be recorded as distinct"
            )
        return self


# ---------------------------------------------------------------------------
# Admission dimension 1: measured resource envelope
# ---------------------------------------------------------------------------


class ThermalBudget(_Descriptive):
    schema_version: Literal["thermal-budget/v0.1"] = "thermal-budget/v0.1"
    sustained_power_watts: float | None = Field(default=None, ge=0)
    throttle_temperature_celsius: float | None = Field(default=None)
    cooling_class: str | None = Field(default=None, max_length=64)


class PowerBudget(_Descriptive):
    schema_version: Literal["power-budget/v0.1"] = "power-budget/v0.1"
    supply: Literal["mains", "battery", "mains_with_battery", "unknown"] = "unknown"
    battery_capacity_wh: float | None = Field(default=None, ge=0)
    sustained_draw_watts: float | None = Field(default=None, ge=0)


class ResourceProfile(_Descriptive):
    """A measured resource envelope. Never a capability, never an authority level.

    ``usable_memory_mib`` is what the host actually offers **after firmware
    reservation** — for a nominally 16 GB machine that is a number like 16095,
    not 16384. Fabric records that measurement and stops there: the thresholds
    that would turn it into ``core``/``lite``/``standard`` are an open program
    decision (the plan's own table classifies that 16095 MiB host as ``core``),
    so no tier is representable here. A product applies its own ratified
    thresholds, and effective capability additionally requires the topology
    profile, the verified asset set, and current trust/health.
    """

    schema_version: Literal["resource-profile/v0.1"] = "resource-profile/v0.1"
    profile_id: str = Field(min_length=1, max_length=128)
    node_id: str = Field(min_length=1, max_length=128)
    hardware_inventory_digest: str
    measured_at: datetime
    measurement_method: Literal[
        "measured_usable_after_firmware_reservation",
        "declared_nominal",
        "unknown",
    ]
    cpu_architecture: Architecture
    cpu_logical_cores: int = Field(ge=1)
    cpu_physical_cores: int | None = Field(default=None, ge=1)
    usable_memory_mib: int = Field(ge=0)
    installed_memory_mib: int | None = Field(default=None, ge=0)
    firmware_reserved_memory_mib: int | None = Field(default=None, ge=0)
    usable_storage_mib: int = Field(ge=0)
    thermal_budget: ThermalBudget | None = None
    power_budget: PowerBudget | None = None
    measured_core_reserve_mib: int | None = Field(default=None, ge=0)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority: Literal["descriptive_only"] = "descriptive_only"

    _inventory_digest = field_validator("hardware_inventory_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "ResourceProfile":
        payload = self.model_dump(mode="json")
        assert_no_provisioning_directives(payload)
        assert_no_resource_tier_claim(payload)
        if self.installed_memory_mib is not None and self.usable_memory_mib > self.installed_memory_mib:
            raise ValueError("usable_memory_mib cannot exceed installed_memory_mib")
        if (
            self.measured_core_reserve_mib is not None
            and self.measured_core_reserve_mib > self.usable_memory_mib
        ):
            raise ValueError("measured_core_reserve_mib cannot exceed usable_memory_mib")
        return self


# ---------------------------------------------------------------------------
# Admission dimension 2: commissioned topology
# ---------------------------------------------------------------------------


class OperatorConfirmation(_Descriptive):
    """An explicit operator act. The only way an interface acquires a role.

    Every ``method`` value is something a person did. There is deliberately no
    value meaning "matched by name", "had carrier", or "held the default route".
    """

    schema_version: Literal["operator-confirmation/v0.1"] = "operator-confirmation/v0.1"
    operator_ref: str = Field(min_length=1, max_length=128)
    method: Literal[
        "physical_port_label_confirmed",
        "port_identify_blink_confirmed",
        "operator_console_confirmed",
        "signed_site_approval",
    ]
    confirmed_at: datetime
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)


class InterfaceIdentitySelector(_Descriptive):
    """Composite selector an assignment resolves against. MAC-only is rejected.

    ``bus_path`` and ``permanent_mac`` are both required, plus at least one of
    ``pci_id`` / ``usb_vid_pid`` / ``serial``, so a cloned or spoofed MAC alone
    can never resolve an assignment.
    """

    schema_version: Literal["interface-identity-selector/v0.1"] = "interface-identity-selector/v0.1"
    bus_path: str = Field(min_length=1, max_length=128)
    permanent_mac: str = Field(min_length=17, max_length=17)
    pci_id: str | None = Field(default=None, max_length=32)
    usb_vid_pid: str | None = Field(default=None, max_length=32)
    serial: str | None = Field(default=None, max_length=128)
    driver: str | None = Field(default=None, max_length=64)
    firmware_version: str | None = Field(default=None, max_length=64)
    wireless_phy: str | None = Field(default=None, max_length=64)
    physical_label: str | None = Field(default=None, max_length=64)

    @field_validator("permanent_mac")
    @classmethod
    def _normalized_mac(cls, value: str) -> str:
        if not _MAC.match(value):
            raise ValueError("permanent_mac must be lowercase colon-separated (aa:bb:cc:dd:ee:ff)")
        return value

    @model_validator(mode="after")
    def _composite_enough(self) -> "InterfaceIdentitySelector":
        if not (self.pci_id or self.usb_vid_pid or self.serial):
            raise ValueError(
                "interface selector must pin at least one of pci_id / usb_vid_pid / "
                "serial; MAC-only matching is insufficient"
            )
        return self


class InterfaceAssignment(_Descriptive):
    """A role bound to a composite identity by an explicit operator confirmation.

    The assignment names the inventory it was made against (``inventory_digest``)
    so a changed NIC identity invalidates it instead of silently re-binding.
    """

    schema_version: Literal["interface-assignment/v0.1"] = "interface-assignment/v0.1"
    assignment_id: str = Field(min_length=1, max_length=128)
    node_id: str = Field(min_length=1, max_length=128)
    role: InterfaceRole
    selector: InterfaceIdentitySelector
    inventory_digest: str
    confirmation: OperatorConfirmation
    assigned_at: datetime
    authority: Literal["descriptive_only"] = "descriptive_only"

    _inventory_digest = field_validator("inventory_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "InterfaceAssignment":
        payload = self.model_dump(mode="json")
        assert_no_provisioning_directives(payload)
        assert_no_role_inference(payload)
        return self


class CaptureSupport(_Descriptive):
    """What one interface was observed to support for capture. A fact, not a grant."""

    schema_version: Literal["capture-support/v0.1"] = "capture-support/v0.1"
    interface_key: str = Field(min_length=1, max_length=128)
    promiscuous_supported: bool
    monitor_mode_supported: bool
    hardware_offload_active: bool
    observed_at: datetime
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=32)


class IsolationProperty(_Descriptive):
    """One isolation property and whether a test demonstrated it.

    ``status`` is a tri-state test outcome, never a boolean grant: an untested
    property is ``not_tested``, which a product must treat as "not available".
    """

    schema_version: Literal["isolation-property/v0.1"] = "isolation-property/v0.1"
    property_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)
    status: Literal["demonstrated", "not_demonstrated", "not_tested"]
    test_ref: str | None = Field(default=None, max_length=256)
    observed_at: datetime
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=32)

    @model_validator(mode="after")
    def _demonstrated_needs_evidence(self) -> "IsolationProperty":
        if self.status == "demonstrated" and not self.evidence_refs:
            raise ValueError("a demonstrated isolation property must cite evidence")
        return self


class TopologyProfile(_Descriptive):
    """The commissioned network topology of one node. Independent of resources.

    A 32 GB host with one unsuitable NIC has a generous resource profile and a
    restrictive topology profile; the product intersects them. This record never
    states the result of that intersection.
    """

    schema_version: Literal["topology-profile/v0.1"] = "topology-profile/v0.1"
    profile_id: str = Field(min_length=1, max_length=128)
    node_id: str = Field(min_length=1, max_length=128)
    hardware_inventory_digest: str
    observed_at: datetime
    commissioned_assignments: tuple[InterfaceAssignment, ...] = Field(
        default_factory=tuple, max_length=64
    )
    unassigned_interface_keys: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    capture_support: tuple[CaptureSupport, ...] = Field(default_factory=tuple, max_length=64)
    management_reachability: Literal[
        "independent_path", "shared_path", "local_console_only", "unknown"
    ]
    isolation_properties: tuple[IsolationProperty, ...] = Field(default_factory=tuple, max_length=64)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority: Literal["descriptive_only"] = "descriptive_only"

    _inventory_digest = field_validator("hardware_inventory_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "TopologyProfile":
        payload = self.model_dump(mode="json")
        assert_no_provisioning_directives(payload)
        assert_no_role_inference(payload)
        assert_no_resource_tier_claim(payload)
        ids = [item.assignment_id for item in self.commissioned_assignments]
        if len(set(ids)) != len(ids):
            raise ValueError("commissioned assignment ids must be unique")
        for assignment in self.commissioned_assignments:
            if assignment.inventory_digest != self.hardware_inventory_digest:
                raise ValueError(
                    "a commissioned assignment must be bound to this profile's hardware inventory"
                )
        return self


# ---------------------------------------------------------------------------
# Commissioning
# ---------------------------------------------------------------------------


class CommissioningRecord(_Descriptive):
    """What an operator commissioned on one node, and against which inventory.

    Binds the three admission-dimension digests it was made against. It records
    the commissioning; it does not perform or authorize it, and it never states
    an effective capability.
    """

    schema_version: Literal["commissioning-record/v0.1"] = "commissioning-record/v0.1"
    record_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    created_at: datetime
    hardware_inventory_digest: str
    resource_profile_digest: str
    topology_profile_digest: str
    assignments: tuple[InterfaceAssignment, ...] = Field(default_factory=tuple, max_length=64)
    operator_confirmation: OperatorConfirmation
    site_ref: str | None = Field(default=None, max_length=256)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    record_digest: str
    authority: Literal["descriptive_only"] = "descriptive_only"

    _hw = field_validator("hardware_inventory_digest")(_valid_sha256)
    _rp = field_validator("resource_profile_digest")(_valid_sha256)
    _tp = field_validator("topology_profile_digest")(_valid_sha256)
    _rd = field_validator("record_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "CommissioningRecord":
        payload = self.model_dump(mode="json")
        assert_no_provisioning_directives(payload)
        assert_no_role_inference(payload)
        assert_no_resource_tier_claim(payload)
        ids = [item.assignment_id for item in self.assignments]
        if len(set(ids)) != len(ids):
            raise ValueError("commissioning assignment ids must be unique")
        selectors = [interface_composite_key(item.selector) for item in self.assignments]
        if len(set(selectors)) != len(selectors):
            raise ValueError("two assignments select the same composite interface identity")
        for assignment in self.assignments:
            if assignment.inventory_digest != self.hardware_inventory_digest:
                raise ValueError(
                    "a commissioned assignment must be bound to this record's hardware inventory"
                )
        return self


# ---------------------------------------------------------------------------
# Released artifacts
# ---------------------------------------------------------------------------


class ProductManifest(_Descriptive):
    """Identity of one released product artifact.

    Carries signature/provenance/SBOM **locators**, never a verification verdict:
    whether a signature is acceptable is a product-local admission decision.
    """

    schema_version: Literal["product-manifest/v0.1"] = "product-manifest/v0.1"
    manifest_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    product_version: str = Field(min_length=1, max_length=64)
    source_revision: str = Field(min_length=1, max_length=128)
    architecture: Architecture
    deployment_profile: str | None = Field(default=None, max_length=64)
    artifact_digest: str
    sbom_ref: str | None = Field(default=None, max_length=256)
    provenance_ref: str | None = Field(default=None, max_length=256)
    signature_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    schema_features: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    released_at: datetime
    authority: Literal["descriptive_only"] = "descriptive_only"

    _artifact_digest = field_validator("artifact_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "ProductManifest":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        return self


class AssetManifest(_Descriptive):
    """Bounded-artifact projection for one installable asset.

    The bounds an extractor must enforce are recorded here as *declared* values a
    consumer checks its own extraction against. ``declared_regular_files_only`` is
    pinned: a Fabric asset manifest cannot declare symlinks, hardlinks, devices,
    FIFOs, or nested archives. A delta bundle must name both an exact base digest
    and the declared final tree digest.
    """

    schema_version: Literal["asset-manifest/v0.1"] = "asset-manifest/v0.1"
    manifest_id: str = Field(min_length=1, max_length=128)
    asset_id: str = Field(min_length=1, max_length=128)
    asset_kind: Literal[
        "os_image",
        "edge_package",
        "knowledge_bundle",
        "deception_package",
        "model",
        "emergency_overlay",
        "config_overlay",
    ]
    content_digest: str
    compressed_size_bytes: int = Field(ge=0)
    expanded_size_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    max_file_size_bytes: int = Field(ge=0)
    max_path_depth: int = Field(ge=0)
    inode_count: int = Field(ge=0)
    base_digest: str | None = None
    final_tree_digest: str | None = None
    sbom_ref: str | None = Field(default=None, max_length=256)
    provenance_ref: str | None = Field(default=None, max_length=256)
    signature_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    declared_regular_files_only: Literal[True] = True
    observed_at: datetime
    authority: Literal["descriptive_only"] = "descriptive_only"

    _content_digest = field_validator("content_digest")(_valid_sha256)
    _base_digest = field_validator("base_digest")(_optional_sha256)
    _final_tree_digest = field_validator("final_tree_digest")(_optional_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "AssetManifest":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        if self.base_digest is not None and self.final_tree_digest is None:
            raise ValueError("a delta asset must declare its final_tree_digest")
        if self.expanded_size_bytes < self.compressed_size_bytes:
            raise ValueError("expanded_size_bytes cannot be smaller than compressed_size_bytes")
        return self


class ModelManifest(_Descriptive):
    """Inert-format description of one local cognition model asset.

    Every escape hatch a model file could use to execute code is pinned to
    ``False`` in the wire shape, so a Fabric model manifest cannot describe a
    model that carries code, loads a native plugin, uses pickle-like executable
    serialization, or fetches from the network at load time. Whether to admit the
    model remains a product-local decision.
    """

    schema_version: Literal["model-manifest/v0.1"] = "model-manifest/v0.1"
    manifest_id: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=128)
    asset_manifest_ref: str = Field(min_length=1, max_length=256)
    model_format: Literal["gguf", "safetensors", "onnx"]
    tokenizer_format: Literal["sentencepiece", "tokenizers_json", "bpe_vocab"]
    runtime_id: str = Field(min_length=1, max_length=64)
    runtime_version: str = Field(min_length=1, max_length=64)
    parser_version: str | None = Field(default=None, max_length=64)
    quantization: str | None = Field(default=None, max_length=32)
    context_size_tokens: int = Field(ge=1)
    required_memory_mib: int = Field(ge=0)
    model_supplied_code: Literal[False] = False
    dynamic_loader: Literal[False] = False
    native_plugins: Literal[False] = False
    executable_serialization: Literal[False] = False
    network_fetch_on_load: Literal[False] = False
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "ModelManifest":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        return self


# ---------------------------------------------------------------------------
# Compatibility claims
# ---------------------------------------------------------------------------


class FeatureMinimum(_Descriptive):
    """One row of the feature-to-minimum-Fabric-version matrix."""

    schema_version: Literal["feature-minimum/v0.1"] = "feature-minimum/v0.1"
    feature_id: str = Field(min_length=1, max_length=128)
    minimum_fabric_version: str = Field(min_length=1, max_length=32)
    notes: str | None = Field(default=None, max_length=512)


class TestedCompatibilityTuple(_Descriptive):
    """An exact combination that was tested together.

    Recording that a tuple was tested is not admitting it. A product's
    deny-by-default admission policy decides what it will run; a broad version
    range is a descriptive claim and cannot authorize activation.
    """

    schema_version: Literal["tested-compatibility-tuple/v0.1"] = "tested-compatibility-tuple/v0.1"
    tuple_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    product_version: str = Field(min_length=1, max_length=64)
    artifact_digest: str
    adapter_digest: str
    fabric_version: str = Field(min_length=1, max_length=32)
    schema_features: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    os_abi: str = Field(min_length=1, max_length=64)
    cpu_features: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    architecture: Architecture
    deployment_profile: str | None = Field(default=None, max_length=64)
    overlay_schema_version: str | None = Field(default=None, max_length=32)
    evidence_ref: str | None = Field(default=None, max_length=256)

    _artifact_digest = field_validator("artifact_digest")(_valid_sha256)
    _adapter_digest = field_validator("adapter_digest")(_valid_sha256)


class CompatibilityManifest(_Descriptive):
    """Product-neutral compatibility claims. It makes no admission decision."""

    schema_version: Literal["compatibility-manifest/v0.1"] = "compatibility-manifest/v0.1"
    manifest_id: str = Field(min_length=1, max_length=128)
    generated_at: datetime
    feature_minimums: tuple[FeatureMinimum, ...] = Field(default_factory=tuple, max_length=128)
    tested_tuples: tuple[TestedCompatibilityTuple, ...] = Field(default_factory=tuple, max_length=128)
    claim_scope: Literal["descriptive_claim_only"] = "descriptive_claim_only"
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "CompatibilityManifest":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        features = [item.feature_id for item in self.feature_minimums]
        if len(set(features)) != len(features):
            raise ValueError("feature_minimums must not repeat a feature_id")
        tuple_ids = [item.tuple_id for item in self.tested_tuples]
        if len(set(tuple_ids)) != len(tuple_ids):
            raise ValueError("tested_tuples must not repeat a tuple_id")
        return self


# ---------------------------------------------------------------------------
# Proposal and observation (never authorization)
# ---------------------------------------------------------------------------


class ProposedGenerationDescriptor(_Descriptive):
    """A description of a generation a product *proposes* to activate.

    This replaces the activation-plan shape the program plan's AR-01 finding
    rejected: it names digests and declares irreversible effects, and it contains
    no step list, no unit, no route, no command, and no approval. Nothing here
    activates anything — a product's own activation controller decides, and this
    descriptor is one of its inputs.
    """

    schema_version: Literal["proposed-generation-descriptor/v0.1"] = (
        "proposed-generation-descriptor/v0.1"
    )
    descriptor_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    generation_counter: int = Field(ge=0)
    previous_generation_counter: int | None = Field(default=None, ge=0)
    commissioning_record_digest: str
    product_manifest_digests: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    asset_manifest_digests: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    overlay_digest: str | None = None
    renderer_digest: str
    policy_digest: str
    security_epoch: int = Field(ge=0)
    proposed_at: datetime
    expires_at: datetime
    declared_irreversible_effects: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    descriptor_digest: str
    authority: Literal["descriptive_only"] = "descriptive_only"

    _commissioning = field_validator("commissioning_record_digest")(_valid_sha256)
    _overlay = field_validator("overlay_digest")(_optional_sha256)
    _renderer = field_validator("renderer_digest")(_valid_sha256)
    _policy = field_validator("policy_digest")(_valid_sha256)
    _descriptor = field_validator("descriptor_digest")(_valid_sha256)

    @field_validator("product_manifest_digests", "asset_manifest_digests")
    @classmethod
    def _digest_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for item in value:
            _valid_sha256(item)
        return value

    @model_validator(mode="after")
    def _validate(self) -> "ProposedGenerationDescriptor":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        if self.expires_at <= self.proposed_at:
            raise ValueError("expires_at must be later than proposed_at")
        if (
            self.previous_generation_counter is not None
            and self.previous_generation_counter >= self.generation_counter
        ):
            raise ValueError("generation_counter must increase past previous_generation_counter")
        return self


class ActivationReceipt(_Descriptive):
    """Observation-only record of what a product observed after activating.

    A receipt reports; it never authorizes, re-authorizes, or extends anything.
    ``rollback_incomplete`` is a first-class observed state, because the program
    plan requires a product to keep reporting it until observed state matches.
    """

    schema_version: Literal["activation-receipt/v0.1"] = "activation-receipt/v0.1"
    receipt_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    generation_descriptor_digest: str
    generation_counter: int = Field(ge=0)
    observed_state: Literal[
        "activated",
        "partially_activated",
        "not_activated",
        "rolled_back",
        "rollback_incomplete",
    ]
    observed_at: datetime
    audit_checkpoint_ref: str | None = Field(default=None, max_length=256)
    irreversible_effects_observed: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority: Literal["observation_only"] = "observation_only"

    _descriptor = field_validator("generation_descriptor_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _validate(self) -> "ActivationReceipt":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        return self


# ---------------------------------------------------------------------------
# Projections (envelope only — chain enforcement stays product-local)
# ---------------------------------------------------------------------------


class AuditCheckpointProjection(_Descriptive):
    """The shared envelope of a product audit checkpoint.

    Fabric projects the checkpoint fields so two products name them the same
    way. It computes no chain, verifies no chain, and makes no trust decision —
    the same boundary ``azazel_fabric.audit`` already holds (``docs/contracts.md``
    §1): chains and their enforcement stay product-local.
    """

    schema_version: Literal["audit-checkpoint-projection/v0.1"] = (
        "audit-checkpoint-projection/v0.1"
    )
    checkpoint_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    boot_id: str = Field(min_length=1, max_length=128)
    log_epoch: int = Field(ge=0)
    security_epoch: int = Field(ge=0)
    monotonic_sequence: int = Field(ge=0)
    previous_checkpoint_ref: str | None = Field(default=None, max_length=256)
    head_ref: str = Field(min_length=1, max_length=256)
    policy_generation: int = Field(ge=0)
    inventory_generation: int = Field(ge=0)
    wall_time: datetime
    monotonic_time_ns: int = Field(ge=0)
    assurance_profile: Literal["rollback_anchored", "local_continuity_only"]
    anchor_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "AuditCheckpointProjection":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        return self


class SecurityStateProjection(_Descriptive):
    """The shared envelope of a product's security state. Not a trust decision."""

    schema_version: Literal["security-state-projection/v0.1"] = "security-state-projection/v0.1"
    state_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    observed_at: datetime
    security_epoch: int = Field(ge=0)
    minimum_security_epoch: int = Field(ge=0)
    maximum_rollback_version: str | None = Field(default=None, max_length=64)
    revocation_list_ref: str | None = Field(default=None, max_length=256)
    key_roles_present: tuple[str, ...] = Field(default_factory=tuple, max_length=32)
    device_key_state: Literal["absent", "installed_local_only", "enrolled_to_site"]
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "SecurityStateProjection":
        assert_no_provisioning_directives(self.model_dump(mode="json"))
        return self
