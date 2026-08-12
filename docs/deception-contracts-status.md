# AZ-06 Deception Contract Implementation Status

Status: `main` implements the first canonical AZ-06 contract baseline as
**unreleased `0.5.0.dev0`**. Latest stable release remains `v0.4.0`.

Implemented:

- canonical package/capability/tier/image/placement/decision/event/outcome models
- explicit `descriptive_only` authority for capability and placement data
- Edge-only activation/transition/termination decision authority
- finite package maximum resource budgets, including bandwidth ceiling
- package/tier minimum-vs-maximum validation
- SHA-256 image/package digest validation
- OCI provenance/SBOM/verification fields
- fail-closed directive-field validation
- unrestricted egress/production access unrepresentable in canonical safety policy
- shared ARM64/AMD64 golden factories consumed by Edge and AZ-06 CI
- termination-decision expiry

Not complete / do not close `Azazel-Fabric#9` yet:

- stable `v0.5.x` tag and migration window
- real signed OCI provenance/SBOM golden fixture rather than synthetic test values
- full artifact/persona/environment-state contract family for AZ-06 Phase 2
- Knowledge and Gadget adoption of the new contract subset
- cross-repository live/HIL safety orchestration

A development consumer must pin an exact reviewed commit. Do not pin `main` and
do not describe `0.5.0.dev0` as a release.
