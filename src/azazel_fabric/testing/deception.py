"""Deterministic golden factories for AZ-06 cross-repository contract tests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from azazel_fabric.deception_contracts import (
    ComponentManifest,
    DeceptionPackage,
    DeploymentTier,
    EffectivenessAdvisory,
    HostCapabilities,
    ImageManifest,
    ImagePlatform,
    InteractionObservation,
    NarrativeConsistencyReport,
    NarrativeManifest,
    PlacementPlan,
    ResourceBudget,
    RuntimeRequirements,
    SafetyPolicy,
    TransitionCatalog,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def make_deception_host_capabilities(
    architecture: str = "amd64", **overrides: Any
) -> HostCapabilities:
    data: dict[str, Any] = {
        "node_id": f"az06-fixture-{architecture}",
        "architecture": architecture,
        "cpu_cores": 4,
        "memory_mb": 8192,
        "storage_free_mb": 65536,
        "runtime_adapters": {"docker_compose": True},
        "runtime_versions": {"docker_compose": "fixture"},
        "kvm_available": False,
        "gpu_available": False,
        "network_features": {"network_namespace": True, "nftables": True},
        "supported_profile_classes": ["static_linux", "low_interaction_services"],
    }
    data.update(overrides)
    return HostCapabilities(**data)


def make_deception_package(verified: bool = True, **overrides: Any) -> DeceptionPackage:
    minimum = ResourceBudget(
        cpu_cores=2,
        memory_mb=1024,
        storage_mb=2048,
        max_connections=100,
        max_duration_seconds=300,
    )
    maximum = ResourceBudget(
        cpu_cores=4,
        memory_mb=4096,
        storage_mb=8192,
        max_connections=500,
        max_duration_seconds=600,
        bandwidth_kbps=10000,
    )
    image = ImageManifest(
        image="example.invalid/az06/intranet-web:0.2",
        manifest_digest=_sha("a"),
        platforms=[
            ImagePlatform(architecture="arm64", digest=_sha("b")),
            ImagePlatform(architecture="amd64", digest=_sha("c")),
        ],
        provenance_ref="fixture:provenance",
        sbom_ref="fixture:sbom",
        verified=verified,
    )
    data: dict[str, Any] = {
        "package_id": "municipal-linux-v1",
        "package_version": "0.2.0",
        "package_digest": _sha("d"),
        "narrative": NarrativeManifest(
            narrative_id="municipal-public-health-v1",
            purpose="synthetic municipal reference deception environment",
            environment_profile_id="municipal-public-health",
            locale="ja-JP",
            timezone="Asia/Tokyo",
            engage_objective="collect",
            engage_approach="channel",
            engage_activities=["record_interaction"],
        ),
        "runtime_requirements": RuntimeRequirements(
            architectures=["arm64", "amd64"],
            runtime_adapter="docker_compose",
            minimum=minimum,
            required_runtime_features=["isolated_network", "resource_limits"],
            required_profile_classes=["static_linux"],
        ),
        "maximum_budget": maximum,
        "safety": SafetyPolicy(),
        "components": [
            ComponentManifest(
                component_id="intranet-web",
                required=True,
                image=image,
                read_only_rootfs=True,
            )
        ],
        "deployment_tiers": [
            DeploymentTier(
                tier_id="lite",
                minimum=minimum,
                include_components=["intranet-web"],
            )
        ],
        "consistency": NarrativeConsistencyReport(report_id="fixture-consistency"),
        "credentials": [],
        "signer_ref": "fixture:signer",
        "signature_ref": "fixture:signature",
    }
    data.update(overrides)
    return DeceptionPackage(**data)


def make_deception_placement(
    *,
    decision_id: str = "edge-shadow-fixture",
    architecture: str = "amd64",
    verified: bool = True,
    **overrides: Any,
) -> PlacementPlan:
    package = make_deception_package(verified=verified)
    host = make_deception_host_capabilities(architecture=architecture)
    data: dict[str, Any] = {
        "placement_id": f"az06-placement-{architecture}-fixture",
        "package_id": package.package_id,
        "package_digest": package.package_digest,
        "node_id": host.node_id,
        "architecture": host.architecture,
        "runtime_adapter": package.runtime_requirements.runtime_adapter,
        "selected_tier": "lite",
        "component_ids": ["intranet-web"],
        "capability_snapshot_digest": _json_digest(host.model_dump(mode="json")),
        "edge_decision_id": decision_id,
    }
    data.update(overrides)
    return PlacementPlan(**data)


def make_interaction_observation(
    *,
    observation_class: str = "reaction",
    surface: str = "credential_lure",
    reaction_kind: str | None = "authenticate",
    **overrides: Any,
) -> "InteractionObservation":
    """A deterministic fact-only effectiveness observation for cross-repo tests."""

    package = make_deception_package()
    host = make_deception_host_capabilities()
    data: dict[str, Any] = {
        "observation_id": "obs-fixture-1",
        "environment_id": "env-fixture",
        "package_id": package.package_id,
        "node_id": host.node_id,
        "observed_at": "2026-01-01T00:00:00+00:00",
        "observation_class": observation_class,
        "surface": surface,
        "reaction_kind": reaction_kind if observation_class != "interaction" else None,
        "lure_id": "lure-municipal-admin",
        "first_contact_latency_ms": 1200,
        "dwell_ms": 45000,
        "attempt_count": 3,
        "confounder_tags": [],
        "runtime_context": {
            "selected_tier": "lite",
            "architecture": host.architecture,
            "runtime_adapter": package.runtime_requirements.runtime_adapter,
            "active_components": ["intranet-web"],
            "omitted_components": [],
        },
        "evidence_refs": [],
        "metadata": {},
    }
    data.update(overrides)
    return InteractionObservation(**data)


def make_effectiveness_advisory(**overrides: Any) -> "EffectivenessAdvisory":
    """A deterministic advisory-only layer-4 effectiveness judgement for tests."""

    package = make_deception_package()
    host = make_deception_host_capabilities()
    data: dict[str, Any] = {
        "advisory_id": "advisory-fixture-1",
        "environment_id": "env-fixture",
        "package_id": package.package_id,
        "node_id": host.node_id,
        "produced_at": "2026-01-01T00:05:00+00:00",
        "assessment": "sustained credential-lure use after banner enumeration",
        "confidence": 0.6,
        "counter_evidence": ["overlaps with a known scanner signature window"],
        "observation_refs": ["obs-fixture-1"],
        "unknowns": ["attacker attribution", "whether lateral attempt was manual"],
        "metadata": {},
    }
    data.update(overrides)
    return EffectivenessAdvisory(**data)


def make_transition_catalog(**overrides: Any) -> "TransitionCatalog":
    """A deterministic, correctly-sealed transition catalog for tests."""

    from azazel_fabric.deception_integrity import catalog_content_digest

    package = make_deception_package()
    transition = {
        "transition_id": "open-smb-share",
        "from_state": "baseline",
        "to_state": "smb-share-open",
        "evidence_backed_trigger": "attacker enumerated the file service banner",
        "expected_observation": "attacker mounts the decoy SMB share",
        "bounds": {
            "cpu_cores": 1,
            "memory_mb": 256,
            "storage_mb": 512,
            "max_connections": 20,
            "max_duration_seconds": 600,
            "bandwidth_kbps": 2000,
        },
        "max_new_surfaces": 1,
        "rollback_state": "baseline",
        "termination_conditions": ["egress attempt", "duration exceeded"],
    }
    data: dict[str, Any] = {
        "catalog_id": "municipal-linux-transitions-v1",
        "package_id": package.package_id,
        "package_digest": package.package_digest,
        "transitions": [transition],
        "signer_ref": "fixture:catalog-signer",
        "signature_ref": "fixture:catalog-signature",
    }
    data.update(overrides)
    if "catalog_digest" in data:
        return TransitionCatalog(**data)
    # Seal over the *normalized* model (defaults applied), not the raw mapping,
    # so the digest is representation-invariant — mirrors package sealing.
    placeholder = TransitionCatalog(**data, catalog_digest=_sha("0"))
    data["catalog_digest"] = catalog_content_digest(placeholder)
    return TransitionCatalog(**data)
