"""Pydantic data models for the AZ-06 deception-environment boundary.

The models deliberately encode safety/authority invariants in the wire shape.
They describe what was requested/approved/materialized; they contain no
runtime or network execution code.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Architecture = Literal["arm64", "amd64"]
RuntimeAdapter = Literal["docker_compose", "podman", "kvm_libvirt", "k3s"]
DecisionStatus = Literal["accepted", "modified", "downgraded", "rejected", "terminated"]

_DIGEST_PREFIX = "sha256:"


def _valid_sha256(value: str) -> str:
    if not value.startswith(_DIGEST_PREFIX):
        raise ValueError("digest must use sha256:<64 lowercase hex> format")
    digest = value[len(_DIGEST_PREFIX) :]
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("digest must use sha256:<64 lowercase hex> format")
    return value


class ResourceBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_cores: float = Field(gt=0)
    memory_mb: int = Field(gt=0)
    storage_mb: int = Field(gt=0)
    max_connections: int = Field(gt=0, default=100)
    max_duration_seconds: int = Field(gt=0, default=300)
    bandwidth_kbps: int | None = Field(default=None, gt=0)

    def is_within(
        self,
        maximum: "ResourceBudget",
        *,
        require_bounded_bandwidth: bool = False,
    ) -> bool:
        """Return whether this budget fits within ``maximum``.

        ``bandwidth_kbps=None`` has two intentionally different meanings:

        - for a *minimum requirement* it means no minimum bandwidth is required;
        - for a live *allocation* it is unsafe/unspecified and is rejected when
          ``require_bounded_bandwidth=True``.
        """

        if self.cpu_cores > maximum.cpu_cores:
            return False
        if self.memory_mb > maximum.memory_mb or self.storage_mb > maximum.storage_mb:
            return False
        if self.max_connections > maximum.max_connections:
            return False
        if self.max_duration_seconds > maximum.max_duration_seconds:
            return False

        if require_bounded_bandwidth and self.bandwidth_kbps is None:
            return False
        if maximum.bandwidth_kbps is not None and self.bandwidth_kbps is not None:
            if self.bandwidth_kbps > maximum.bandwidth_kbps:
                return False
        return True


class SafetyPolicy(BaseModel):
    """Safety policy deliberately cannot express unrestricted live access."""

    model_config = ConfigDict(extra="forbid")

    outbound_allowed: Literal[False] = False
    production_access: Literal[False] = False
    privileged_containers: Literal[False] = False
    host_network: Literal[False] = False
    runtime_socket_exposed_to_decoys: Literal[False] = False
    edge_control_access_from_decoys: Literal[False] = False


class RuntimeRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    architectures: list[Architecture] = Field(min_length=1)
    runtime_adapter: RuntimeAdapter = "docker_compose"
    minimum: ResourceBudget
    kvm_required: bool = False
    gpu_required: bool = False
    required_runtime_features: list[str] = Field(default_factory=list)
    required_profile_classes: list[str] = Field(default_factory=list)

    @field_validator("architectures")
    @classmethod
    def architectures_unique(cls, value: list[Architecture]) -> list[Architecture]:
        if len(set(value)) != len(value):
            raise ValueError("architectures must be unique")
        return value


class HostCapabilities(BaseModel):
    """Descriptive host state. Presence of capabilities never grants authority."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["host-capabilities/v0.1"] = "host-capabilities/v0.1"
    node_id: str = Field(min_length=1)
    architecture: Architecture
    cpu_cores: int = Field(gt=0)
    memory_mb: int = Field(gt=0)
    storage_free_mb: int = Field(ge=0)
    runtime_adapters: dict[str, bool] = Field(default_factory=dict)
    runtime_versions: dict[str, str] = Field(default_factory=dict)
    kvm_available: bool = False
    gpu_available: bool = False
    network_features: dict[str, bool] = Field(default_factory=dict)
    supported_profile_classes: list[str] = Field(default_factory=list)
    authority: Literal["descriptive_only"] = "descriptive_only"


class ImagePlatform(BaseModel):
    model_config = ConfigDict(extra="forbid")

    architecture: Architecture
    digest: str

    _digest = field_validator("digest")(_valid_sha256)


class ImageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image: str = Field(min_length=1)
    manifest_digest: str
    platforms: list[ImagePlatform] = Field(min_length=1)
    provenance_ref: str = Field(min_length=1)
    sbom_ref: str = Field(min_length=1)
    verified: bool = False

    _manifest_digest = field_validator("manifest_digest")(_valid_sha256)

    @model_validator(mode="after")
    def unique_platforms(self) -> "ImageManifest":
        architectures = [item.architecture for item in self.platforms]
        if len(set(architectures)) != len(architectures):
            raise ValueError("image platforms must contain unique architectures")
        return self


class DecoySurface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface_id: str = Field(min_length=1)
    protocol: Literal["tcp", "udp"] = "tcp"
    port: int = Field(ge=1, le=65535)
    service: str = Field(min_length=1)


class ComponentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: str = Field(min_length=1)
    required: bool = True
    image: ImageManifest
    privileged: Literal[False] = False
    host_network: Literal[False] = False
    read_only_rootfs: bool = True
    surfaces: list[DecoySurface] = Field(default_factory=list)


class DeploymentTier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier_id: Literal["lite", "standard", "heavy", "cluster", "gadget-lite"]
    minimum: ResourceBudget
    include_components: list[str] = Field(min_length=1)

    @field_validator("include_components")
    @classmethod
    def components_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("include_components must be unique")
        return value


class NarrativeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narrative_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    environment_profile_id: str = Field(min_length=1)
    synthetic_only: Literal[True] = True
    locale: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    engage_objective: str | None = None
    engage_approach: str | None = None
    engage_activities: list[str] = Field(default_factory=list)


class NarrativeConsistencyReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(min_length=1)
    fatal_contradictions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    waivers: list[str] = Field(default_factory=list)

    @property
    def activatable(self) -> bool:
        return not self.fatal_contradictions


class CredentialLure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential_id: str = Field(min_length=1)
    owner_persona_id: str = Field(min_length=1)
    target_surface_id: str = Field(min_length=1)
    source_artifact_id: str | None = None
    decoy_only: Literal[True] = True
    expires_at: datetime


class DeceptionPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["deception-package/v0.1"] = "deception-package/v0.1"
    package_id: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    package_digest: str
    narrative: NarrativeManifest
    runtime_requirements: RuntimeRequirements
    maximum_budget: ResourceBudget
    safety: SafetyPolicy = Field(default_factory=SafetyPolicy)
    components: list[ComponentManifest] = Field(min_length=1)
    deployment_tiers: list[DeploymentTier] = Field(min_length=1)
    consistency: NarrativeConsistencyReport
    credentials: list[CredentialLure] = Field(default_factory=list)
    signer_ref: str = Field(min_length=1)
    signature_ref: str = Field(min_length=1)

    _package_digest = field_validator("package_digest")(_valid_sha256)

    @model_validator(mode="after")
    def package_invariants(self) -> "DeceptionPackage":
        if self.maximum_budget.bandwidth_kbps is None:
            raise ValueError("package maximum budget must declare finite bandwidth_kbps")
        if not self.runtime_requirements.minimum.is_within(self.maximum_budget):
            raise ValueError("runtime minimum exceeds package maximum budget")

        component_ids = [item.component_id for item in self.components]
        if len(set(component_ids)) != len(component_ids):
            raise ValueError("component_id values must be unique")
        tier_ids = [item.tier_id for item in self.deployment_tiers]
        if len(set(tier_ids)) != len(tier_ids):
            raise ValueError("deployment tier IDs must be unique")

        known = set(component_ids)
        required = {item.component_id for item in self.components if item.required}
        for tier in self.deployment_tiers:
            included = set(tier.include_components)
            unknown = included - known
            if unknown:
                raise ValueError(f"tier {tier.tier_id} references unknown components: {sorted(unknown)}")
            missing = required - included
            if missing:
                raise ValueError(f"tier {tier.tier_id} omits required components: {sorted(missing)}")
            if not tier.minimum.is_within(self.maximum_budget):
                raise ValueError(f"tier {tier.tier_id} minimum exceeds package maximum budget")
        if self.consistency.fatal_contradictions:
            raise ValueError("package has unresolved fatal narrative contradictions")
        return self


class PlacementPlan(BaseModel):
    """AZ-06-local descriptive placement; never an activation instruction."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["placement-plan/v0.1"] = "placement-plan/v0.1"
    placement_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    package_digest: str
    node_id: str = Field(min_length=1)
    architecture: Architecture
    runtime_adapter: RuntimeAdapter
    selected_tier: str = Field(min_length=1)
    component_ids: list[str] = Field(min_length=1)
    capability_snapshot_digest: str
    edge_decision_id: str | None = None
    authority: Literal["descriptive_only"] = "descriptive_only"

    _package_digest = field_validator("package_digest")(_valid_sha256)
    _cap_digest = field_validator("capability_snapshot_digest")(_valid_sha256)


class EnvironmentActivationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["environment-activation-decision/v0.1"] = "environment-activation-decision/v0.1"
    decision_id: str = Field(min_length=1)
    decision_authority: Literal["azazel-edge"] = "azazel-edge"
    status: DecisionStatus
    package_id: str = Field(min_length=1)
    package_digest: str
    target_node_id: str = Field(min_length=1)
    selected_tier: str = Field(min_length=1)
    budget: ResourceBudget
    safety: SafetyPolicy = Field(default_factory=SafetyPolicy)
    effective_at: datetime
    expires_at: datetime
    evidence_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)

    _package_digest = field_validator("package_digest")(_valid_sha256)

    @model_validator(mode="after")
    def expiry_after_effective(self) -> "EnvironmentActivationDecision":
        if self.expires_at <= self.effective_at:
            raise ValueError("expires_at must be later than effective_at")
        return self


class EnvironmentTransitionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["environment-transition-decision/v0.1"] = "environment-transition-decision/v0.1"
    decision_id: str = Field(min_length=1)
    decision_authority: Literal["azazel-edge"] = "azazel-edge"
    status: DecisionStatus
    environment_id: str = Field(min_length=1)
    current_state: str = Field(min_length=1)
    target_state: str = Field(min_length=1)
    effective_at: datetime
    expires_at: datetime
    evidence_refs: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def expiry_after_effective(self) -> "EnvironmentTransitionDecision":
        if self.expires_at <= self.effective_at:
            raise ValueError("expires_at must be later than effective_at")
        return self


class EnvironmentTerminationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["environment-termination-decision/v0.1"] = "environment-termination-decision/v0.1"
    decision_id: str = Field(min_length=1)
    decision_authority: Literal["azazel-edge"] = "azazel-edge"
    environment_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def expiry_after_issued(self) -> "EnvironmentTerminationDecision":
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        return self


class EnvironmentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["environment-event/v0.1"] = "environment-event/v0.1"
    event_id: str = Field(min_length=1)
    environment_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    event_type: Literal[
        "planned",
        "activation_requested",
        "activated",
        "interaction",
        "transitioned",
        "terminated",
        "reset_started",
        "reset_completed",
        "failure",
    ]
    observed_at: datetime
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class EnvironmentOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["environment-outcome/v0.1"] = "environment-outcome/v0.1"
    outcome_id: str = Field(min_length=1)
    environment_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    package_digest: str
    node_id: str = Field(min_length=1)
    architecture: Architecture
    runtime_adapter: RuntimeAdapter
    selected_tier: str = Field(min_length=1)
    termination_reason: str = Field(min_length=1)
    reset_succeeded: bool
    credentials_invalidated: bool | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    measured_reactions: list[str] = Field(default_factory=list)
    runtime_confounders: list[str] = Field(default_factory=list)

    _package_digest = field_validator("package_digest")(_valid_sha256)
