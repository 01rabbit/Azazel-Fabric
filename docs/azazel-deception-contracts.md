# AZ-06 Azazel-Deception Contract Boundary

Repository: https://github.com/01rabbit/Azazel-Deception
Tracker: https://github.com/01rabbit/Azazel-Fabric/issues/9
Parent doctrine: https://github.com/01rabbit/Azazel/issues/61

## Role

Azazel-Fabric owns the canonical shared wire contracts used to describe AZ-06 packages, host capabilities, lifecycle decisions, evidence, and outcomes. Fabric contains **no deception generation, runtime orchestration, classification, or enforcement authority**.

> Fabric describes. Edge decides and authorizes. AZ-06 materializes and executes only inside the approved boundary. Knowledge analyzes and advises.

## Current AZ-06 bootstrap shapes

AZ-06 currently uses temporary local development shapes:

- `deception-package/bootstrap-v0.1`
- `host-capabilities/bootstrap-v0.1`
- `placement-plan/bootstrap-v0.1`

They exist only to make Phase 0 code testable. They are not canonical series contracts and must migrate behind a compatibility layer when Fabric publishes the corresponding released schemas.

## Canonical contract target

The AZ-06 contract family tracked in #9 includes:

- `DeceptionPackage`
- `NarrativeManifest`
- `EnvironmentProfile`
- `ArtifactManifest`
- `PersonaProfile`
- `CredentialLure`
- `DecoySurface`
- `EnvironmentState`
- activation / transition / termination decisions
- environment events / outcomes / consistency reports
- `HostCapabilities`
- `RuntimeRequirements`
- `DeploymentTier`
- `RuntimeAdapterDescriptor`
- descriptive `PlacementPlan`
- `ImageManifest`
- evidence, audit, signature, provenance, SBOM, and reset references

These compose with the generic Engage contracts in `Azazel-Fabric#8`.

## Authority invariants

- package content is declarative only
- host capability reports are descriptive only
- placement plans are descriptive only
- candidates/advisories are non-executable
- only valid product-local Edge decisions authorize AZ-06 live changes in the initial architecture
- no contract can express unrestricted egress or production access
- unsupported command-boundary schema/enum values fail closed
- runtime-specific IDs never replace portable package/decision/audit identifiers
- LLM availability is optional preparation metadata, not a live authority field

## Portability requirements

Phase 1 fixtures must cover equivalent package semantics on `linux/arm64` and `linux/amd64`, Docker Compose as the first runtime adapter, package-authored deployment tiers, and per-platform OCI digest/provenance information.

Tier selection may omit only explicitly optional components; it must not weaken required narrative or safety invariants.

## Adoption sequence

1. Land and release canonical AZ-06 contracts.
2. Publish golden fixtures for AZ-06, Edge, Knowledge, and Gadget's constrained static subset.
3. AZ-06 migrates bootstrap shapes (`Azazel-Deception#1`).
4. Edge shadow/replay integration consumes the released contract before live activation.
