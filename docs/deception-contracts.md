# AZ-06 Deception-Environment Contracts

Status: **unreleased `0.5.0.dev0` development contract family**.

Tracking issues:

- `01rabbit/Azazel-Fabric#9`
- `01rabbit/Azazel#61`
- `01rabbit/Azazel-Edge#325`
- `01rabbit/Azazel-Deception#1`

## Authority boundary

> Fabric describes. Edge decides and enforces. Deception Host materializes,
> transitions, records, and resets. Knowledge analyzes and advises.

The contract family is intentionally incapable of turning a capability report,
package, placement plan, or advisory into runtime authority.

## Canonical types

The `azazel_fabric.deception_contracts` namespace contains:

- `DeceptionPackage`
- `NarrativeManifest`
- `NarrativeConsistencyReport`
- `CredentialLure`
- `DecoySurface`
- `ComponentManifest`
- `ImageManifest` / `ImagePlatform`
- `RuntimeRequirements`
- `HostCapabilities`
- `DeploymentTier`
- `PlacementPlan`
- `EnvironmentActivationDecision`
- `EnvironmentTransitionDecision`
- `EnvironmentTerminationDecision`
- `EnvironmentEvent`
- `EnvironmentOutcome`
- shared resource and safety models

## Required invariants

### Package safety

A canonical package cannot express:

- unrestricted decoy egress
- production access
- privileged attacker-facing containers
- host networking
- runtime-socket access from decoys
- Edge-control access from decoys

A deployment tier must include every component marked `required`. Fatal
narrative contradictions make the package invalid.

### Capability safety

`HostCapabilities.authority` is always `descriptive_only`.

Capabilities may explain what a host can support; they never authorize an
environment or select a response.

### Placement safety

`PlacementPlan.authority` is always `descriptive_only`.

The plan records package, host, architecture, adapter, tier, component set,
capability snapshot digest, and optionally the Edge decision it was calculated
for. It never carries a shell command, Docker command, firewall rule, or other
execution directive.

### Edge decision authority

Initial live AZ-06 runtime changes may be authorized only by the explicit Edge
decision contracts. Activation decisions bind package identity/digest, target
node, tier, budget, safety policy, effective time, expiry, evidence, and reason
codes.

This contract does not itself execute the decision.

## Supply-chain fields

`ImageManifest` carries:

- multi-architecture image identity
- manifest digest
- per-platform SHA-256 digests
- provenance reference
- SBOM reference
- verification state

AZ-06 may use `verified=false` for dry-run/bootstrap assets, but live execution
policy is expected to reject unverified component images.

## Architectures and deployment tiers

Initial architecture vocabulary:

- `arm64`
- `amd64`

Initial tier vocabulary:

- `lite`
- `standard`
- `heavy`
- `cluster`
- `gadget-lite`

A tier changes capacity or explicitly optional components. It must not change
required narrative truth or weaken safety constraints.

## Runtime-directive rejection

Fabric includes a generic recursive validation helper that rejects fields such
as:

- `docker_command`
- `podman_command`
- `shell_command`
- `runtime_command`
- firewall-rule fields
- `execute_now`
- `override_authority`
- `bypass_arbiter`

This is an additional API-boundary invariant, not a substitute for normal
Pydantic `extra="forbid"` model validation.

## Migration from AZ-06 bootstrap shapes

Azazel-Deception originally used:

- `deception-package/bootstrap-v0.1`
- `host-capabilities/bootstrap-v0.1`
- `placement-plan/bootstrap-v0.1`

AZ-06 now normalizes bootstrap package input immediately into canonical Fabric
models. The bootstrap external shapes are compatibility-only and should be
removed after a stable `v0.5.x` Fabric release and migration window.

## Release gate

Do not tag `v0.5.x` solely because the models exist. Before release:

- keep Fabric CI green
- add/retain cross-repository golden fixtures
- validate AZ-06 and Edge against the same fixtures
- replace placeholder OCI provenance in the reference package with real
  digests/provenance/SBOM data
- verify consumer documentation and exact pins
- run adversarial authority-bypass and unsupported-version tests

Until then, development consumers pin an exact reviewed commit and must not
present `0.5.0.dev0` as a stable release.
