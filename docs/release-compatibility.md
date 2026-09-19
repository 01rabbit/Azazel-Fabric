# Release Compatibility and Support Truth

Status: **R0 coordination baseline, 2026-09-19; re-verified 2026-09-19 against
the consumer repositories.** This document records the published Fabric release
and observed consumer dependency declarations. An observed pin is not, by
itself, an interoperability certification.

## Current Fabric release

The latest **published** release is `v0.8.0`. The source package version on
`main` is `0.9.0.dev0`: an explicitly unreleased development version carrying
additive contract work (`outcome_contracts`, and the R1a `provisioning_contracts`
/ `mio_contracts` families) on top of `v0.8.0`.

The package version in `src/azazel_fabric/version.py`, release tag, and GitHub
release must agree before a release is described as stable. A `.devN` version is
never a release: consumers pin `v0.8.0` until `v0.9.0` is tagged and published.

| Release | Contract addition | Compatibility effect |
|---|---|---|
| `v0.5.0` | Canonical AZ-06 package, capability, placement, decision, event, and outcome contracts | Additive baseline for the AZ-06 contract family |
| `v0.6.0` | Effectiveness-observation and finite-state transition catalog contracts | Additive |
| `v0.7.0` | **Never released.** No tag, no GitHub Release. The advisory-only engagement contracts it describes shipped inside `v0.8.0` | Not pinnable — a consumer that pins `v0.7.0` resolves to nothing |
| `v0.8.0` | Canonical HMAC-SHA256 Edge-decision transport signature helpers **and** the advisory-only engagement contracts | Additive; signatures prove integrity/origin, not authority |
| `0.9.0.dev0` (unreleased) | Outcome-as-Evidence shared facts (`outcome_contracts`); R1a provisioning and M.I.O. contract families (`provisioning_contracts`, `mio_contracts`) | Additive; **not a release** — no tag, no GitHub Release, no supported pin |

All consumer deployments MUST pin an exact compatible Fabric tag or immutable
image lock. They MUST NOT pin a branch. A product chooses when to adopt a newer
compatible tag and must demonstrate its own integration tests before claiming
support.

## Observed consumer declarations

| Consumer | Observed declaration | Interpretation |
|---|---|---|
| Azazel-Edge | `v0.8.0` in `requirements/fabric.txt` | Current reference authority consumer |
| Azazel-Gadget | `v0.4.0` in `requirements.txt` | Earlier consumer baseline; no automatic upgrade implied |
| Azazel-Knowledge | `v0.8.0` in the `api` optional dependency (`pyproject.toml`) | Advisory API boundary only; core stays dependency-minimal |
| Azazel-Deception | `v0.8.0` in `pyproject.toml` | Current AZ-06 runtime declaration |
| Azazel-Nexus | no pin yet (documentation-only repository) | Must select and test an exact pin before an implementation release |
| Azazel-Boot | `v0.8.0` in the `fabric` optional extra (`pyproject.toml`, ADR-0004) | Exact-tag source pin; an image lock is still required before a Boot implementation release |

Verification note (2026-09-19): the Edge, Knowledge, Deception, Boot, and Nexus
rows were read directly from each repository's dependency declaration. The
Gadget row is carried forward from the previous audit and has **not** been
re-verified from the Gadget repository in this pass.

The R0 program currently treats `v0.8.0` as the reference candidate because the
latest published tag and the Edge/Knowledge/Deception/Boot declarations agree on
`v0.8.0`. This does not alter the existing Gadget pin and does not make
unsupported combinations supported.

## Release and support rules

- `CHANGELOG.md` is the release-history record; historical references to an
  earlier release describe that release, not the current recommendation. A
  changelog section is not evidence that a tag exists: `[0.7.0]` is retained
  there and explicitly marked never released, because the work it describes
  shipped in `v0.8.0`. Verified 2026-09-19 against both `git tag` and the
  published GitHub releases (`v0.1.0`-`v0.6.0`, `v0.8.0`).
- Before a release is described as available, the tag, the GitHub Release, and
  `src/azazel_fabric/version.py` must all be checked — not just the changelog.
- Product documentation that names a current release or consumer pin must be
  updated together with the relevant dependency declaration.
- Breaking schema or import changes require a major version, migration note,
  and consumer-specific evidence.
- Fabric remains descriptive. Capability reports, advisory data, placement
  plans, and signatures never grant runtime, decision, or enforcement authority.
- Release support claims require CI evidence for the published package and the
  documented cross-product conformance scope.
