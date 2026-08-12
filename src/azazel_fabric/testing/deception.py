"""Deterministic golden factories for AZ-06 cross-repository contract tests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from azazel_fabric.deception_contracts import (
    ComponentManifest,
    DeceptionPackage,
    DeploymentTier,
    HostCapabilities,
    ImageManifest,
    ImagePlatform,
    NarrativeConsistencyReport,
    NarrativeManifest,
    PlacementPlan,
    ResourceBudget,
    RuntimeRequirements,
    SafetyPolicy,
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
    budget = ResourceBudget(
        cpu_cores=2,
        memory_mb=1024,
        storage_mb=2048,
        max_connections=100,
        max_duration_seconds=300,
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
            minimum=budget,
            required_runtime_features=["isolated_network", "resource_limits"],
            required_profile_classes=["static_linux"],
        ),
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
                minimum=budget,
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
