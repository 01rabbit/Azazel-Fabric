from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from azazel_fabric.deception_contracts import (
    ComponentManifest,
    DeceptionPackage,
    DeploymentTier,
    EnvironmentActivationDecision,
    HostCapabilities,
    ImageManifest,
    ImagePlatform,
    NarrativeConsistencyReport,
    NarrativeManifest,
    ResourceBudget,
    RuntimeRequirements,
    SafetyPolicy,
    assert_no_runtime_directives,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _budget() -> ResourceBudget:
    return ResourceBudget(
        cpu_cores=2,
        memory_mb=1024,
        storage_mb=2048,
        max_connections=100,
        max_duration_seconds=300,
    )


def _package() -> DeceptionPackage:
    image = ImageManifest(
        image="ghcr.io/01rabbit/azazel-deception/intranet-web:0.1",
        manifest_digest=_sha("a"),
        platforms=[
            ImagePlatform(architecture="arm64", digest=_sha("b")),
            ImagePlatform(architecture="amd64", digest=_sha("c")),
        ],
        provenance_ref="https://example.invalid/provenance/1",
        sbom_ref="https://example.invalid/sbom/1",
        verified=True,
    )
    component = ComponentManifest(component_id="intranet-web", image=image)
    minimum = _budget()
    return DeceptionPackage(
        package_id="municipal-linux-v1",
        package_version="0.1.0",
        package_digest=_sha("d"),
        narrative=NarrativeManifest(
            narrative_id="municipal-public-health-v1",
            purpose="synthetic municipal intranet decoy",
            environment_profile_id="municipal-public-health",
            locale="ja-JP",
            timezone="Asia/Tokyo",
        ),
        runtime_requirements=RuntimeRequirements(
            architectures=["arm64", "amd64"],
            minimum=minimum,
            required_runtime_features=["isolated_network", "resource_limits"],
        ),
        safety=SafetyPolicy(),
        components=[component],
        deployment_tiers=[
            DeploymentTier(
                tier_id="lite",
                minimum=minimum,
                include_components=["intranet-web"],
            )
        ],
        consistency=NarrativeConsistencyReport(report_id="consistency-1"),
        signer_ref="operator:test",
        signature_ref="sigstore:test",
    )


def test_valid_package_round_trip() -> None:
    package = _package()
    restored = DeceptionPackage.model_validate_json(package.model_dump_json())
    assert restored.package_id == package.package_id
    assert {p.architecture for p in restored.components[0].image.platforms} == {"arm64", "amd64"}
    assert restored.safety.outbound_allowed is False
    assert restored.safety.production_access is False


def test_tier_cannot_omit_required_component() -> None:
    package = _package().model_dump()
    package["components"].append(
        {
            "component_id": "required-db",
            "required": True,
            "image": package["components"][0]["image"],
            "privileged": False,
            "host_network": False,
            "read_only_rootfs": True,
            "surfaces": [],
        }
    )
    with pytest.raises(ValidationError, match="omits required components"):
        DeceptionPackage.model_validate(package)


def test_unrestricted_egress_is_unrepresentable() -> None:
    with pytest.raises(ValidationError):
        SafetyPolicy(outbound_allowed=True)
    with pytest.raises(ValidationError):
        SafetyPolicy(production_access=True)


def test_capabilities_are_descriptive_only() -> None:
    host = HostCapabilities(
        node_id="az06-test",
        architecture="amd64",
        cpu_cores=4,
        memory_mb=8192,
        storage_free_mb=100000,
        runtime_adapters={"docker_compose": True},
    )
    assert host.authority == "descriptive_only"
    with pytest.raises(ValidationError):
        HostCapabilities(
            node_id="az06-test",
            architecture="amd64",
            cpu_cores=4,
            memory_mb=8192,
            storage_free_mb=100000,
            authority="execute",
        )


def test_activation_decision_requires_edge_authority_and_expiry() -> None:
    now = datetime.now(timezone.utc)
    decision = EnvironmentActivationDecision(
        decision_id="edge-decision-1",
        status="accepted",
        package_id="municipal-linux-v1",
        package_digest=_sha("d"),
        target_node_id="az06-test",
        selected_tier="lite",
        budget=_budget(),
        effective_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    assert decision.decision_authority == "azazel-edge"

    with pytest.raises(ValidationError):
        EnvironmentActivationDecision(
            decision_id="bad",
            decision_authority="azazel-knowledge",
            status="accepted",
            package_id="municipal-linux-v1",
            package_digest=_sha("d"),
            target_node_id="az06-test",
            selected_tier="lite",
            budget=_budget(),
            effective_at=now,
            expires_at=now + timedelta(minutes=5),
        )


def test_nested_runtime_directive_is_rejected() -> None:
    assert_no_runtime_directives({"package_id": "ok", "metadata": {"reason": "test"}})
    with pytest.raises(ValueError, match="authority invariant"):
        assert_no_runtime_directives({"metadata": {"docker_command": "docker run ..."}})
