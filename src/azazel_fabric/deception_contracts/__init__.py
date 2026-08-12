"""Canonical AZ-06 deception-environment contracts.

This package is representation only.  It describes packages, host capability,
Edge decisions, placement, lifecycle events, and outcomes; it never starts a
container, changes a route, selects an engagement, or grants runtime authority.

Authority rule:

    Fabric describes. Edge decides. Deception Host materializes.

The initial wire family is ``*/v0.1`` and is additive to existing Fabric
contracts.
"""

from azazel_fabric.deception_contracts.models import (
    Architecture,
    ComponentManifest,
    CredentialLure,
    DecoySurface,
    DeceptionPackage,
    DeploymentTier,
    EnvironmentActivationDecision,
    EnvironmentEvent,
    EnvironmentOutcome,
    EnvironmentTerminationDecision,
    EnvironmentTransitionDecision,
    HostCapabilities,
    ImageManifest,
    ImagePlatform,
    NarrativeConsistencyReport,
    NarrativeManifest,
    PlacementPlan,
    ResourceBudget,
    RuntimeAdapter,
    RuntimeRequirements,
    SafetyPolicy,
)
from azazel_fabric.deception_contracts.validation import (
    BANNED_RUNTIME_DIRECTIVE_FIELDS,
    assert_no_runtime_directives,
    contains_runtime_directive,
)

__all__ = [
    "Architecture",
    "RuntimeAdapter",
    "ResourceBudget",
    "SafetyPolicy",
    "RuntimeRequirements",
    "HostCapabilities",
    "ImagePlatform",
    "ImageManifest",
    "ComponentManifest",
    "DeploymentTier",
    "NarrativeManifest",
    "NarrativeConsistencyReport",
    "CredentialLure",
    "DecoySurface",
    "DeceptionPackage",
    "PlacementPlan",
    "EnvironmentActivationDecision",
    "EnvironmentTransitionDecision",
    "EnvironmentTerminationDecision",
    "EnvironmentEvent",
    "EnvironmentOutcome",
    "BANNED_RUNTIME_DIRECTIVE_FIELDS",
    "contains_runtime_directive",
    "assert_no_runtime_directives",
]
