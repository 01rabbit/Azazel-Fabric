# Release Compatibility and Support Truth

Status: **R0 coordination baseline, 2026-09-19.** This document records the
published Fabric release and observed consumer dependency declarations. An
observed pin is not, by itself, an interoperability certification.

## Current Fabric release

The source package version is `0.8.0`, and the corresponding published release
is `v0.8.0`. The package version in `src/azazel_fabric/version.py`, release tag,
and GitHub release must agree before a release is described as stable.

| Release | Contract addition | Compatibility effect |
|---|---|---|
| `v0.5.0` | Canonical AZ-06 package, capability, placement, decision, event, and outcome contracts | Additive baseline for the AZ-06 contract family |
| `v0.6.0` | Effectiveness-observation and finite-state transition catalog contracts | Additive |
| `v0.7.0` | Advisory-only engagement contracts | Additive |
| `v0.8.0` | Canonical HMAC-SHA256 Edge-decision transport signature helpers | Additive; signatures prove integrity/origin, not authority |

All consumer deployments MUST pin an exact compatible Fabric tag or immutable
image lock. They MUST NOT pin a branch. A product chooses when to adopt a newer
compatible tag and must demonstrate its own integration tests before claiming
support.

## Observed consumer declarations

| Consumer | Observed declaration | Interpretation |
|---|---|---|
| Azazel-Edge | `v0.8.0` in `requirements/fabric.txt` | Current reference authority consumer |
| Azazel-Gadget | `v0.4.0` in `requirements.txt` | Earlier consumer baseline; no automatic upgrade implied |
| Azazel-Knowledge | `v0.6.0` in the API optional dependency | Advisory API boundary only; core stays dependency-minimal |
| Azazel-Deception | `v0.8.0` in `pyproject.toml` | Current AZ-06 runtime declaration |
| Azazel-Nexus | no pin yet | Must select and test an exact pin before an implementation release |
| Azazel-Boot | no image lock yet | Must select and test an exact image lock before an implementation release |

The R0 program currently treats `v0.8.0` as the reference candidate because
the source package and Edge/Deception declarations agree. This does not alter
existing Gadget or Knowledge pins and does not make unsupported combinations
supported.

## Release and support rules

- `CHANGELOG.md` is the release-history record; historical references to an
  earlier release describe that release, not the current recommendation.
- Product documentation that names a current release or consumer pin must be
  updated together with the relevant dependency declaration.
- Breaking schema or import changes require a major version, migration note,
  and consumer-specific evidence.
- Fabric remains descriptive. Capability reports, advisory data, placement
  plans, and signatures never grant runtime, decision, or enforcement authority.
- Release support claims require CI evidence for the published package and the
  documented cross-product conformance scope.
