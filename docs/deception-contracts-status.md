# AZ-06 Deception Contract Implementation Status

Status: the first canonical AZ-06 contract baseline is **released as
`v0.5.0`** (owner-approved 2026-08-14). Consumers pin the `v0.5.0` tag.

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

- real signed OCI provenance/SBOM golden fixture rather than synthetic test values
- full artifact/persona/environment-state contract family for AZ-06 Phase 2
- Knowledge and Gadget adoption of the new contract subset
- cross-repository live/HIL safety orchestration

Consumers must pin the exact `v0.5.0` tag. Do not pin `main`.
