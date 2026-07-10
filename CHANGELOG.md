# Changelog

All notable changes to Azazel-Fabric (formerly Azazel-Common) are recorded
here. The project follows [Semantic Versioning](https://semver.org/). Each
release corresponds to a `vX.Y.Z` tag and GitHub Release on
`01rabbit/Azazel-Fabric`; consumers pin an exact tag (see
`docs/migration-plan.md`).

## [Unreleased]

### Documentation

- Consumer-status sync: Azazel-Edge implemented Phase 3 (2026-07-10) —
  emit-alongside `DecisionExplanation`/`TrustCapsule`/`AuditEvent`
  projections plus a `StatusView` emit/read-back, making Edge the series'
  largest Fabric consumer. Migration-plan Phase 3 status updated.

## [0.3.0] — renamed to Azazel-Fabric

**BREAKING:**

- Distribution name changed: `azazel-common` → `azazel-fabric`.
- Import namespace changed: `azazel_common` → `azazel_fabric`.
- Repository renamed: `01rabbit/Azazel-Common` → `01rabbit/Azazel-Fabric`
  (old repository URLs redirect).

`v0.1.0` and `v0.2.0` tags remain installable under the old
`azazel-common`/`azazel_common` names — pinning those tags is unaffected.
Consumers (currently Azazel-Gadget, which pins `v0.2.0`) migrate by bumping
their pin to `v0.3.0` and switching their imports from `azazel_common` to
`azazel_fabric`; no schema or behavior changes accompany the rename.

### Documentation

- Synced the six `docs/` design documents with shipped reality: they
  previously still read as a frozen Phase-0 "design proposal only, no
  implementation code has been written" snapshot despite `v0.1.0`/`v0.2.0`
  having shipped real, CI-tested code. Added accurate status headers,
  per-module/per-phase status lines, a consumer-status table in
  `README.md` (Gadget shipping, Edge plan-stage, CTI not adopted), and an
  honest note in `migration-plan.md` that Phase 4 (Gadget) landed ahead of
  Phases 2/3. No code, dependency, or test changes.

## [0.2.0] — shared status view-model

Adds `azazel_common.view`, the first shared *mechanism* beyond passive schemas:
a status view-model both Edge and Gadget derive and render from, so the two
products present the same status the same way. Common owns the view-model; each
product keeps its own renderer (see `docs/design-principles.md` §3.1).

### Added

- `azazel_common.view.StatusView` — the normalized data a status surface reads
  (mode, posture, headline, reasons, operator wording, current action, next
  actions, health dimensions, evidence), plus `HealthDimension`.
- `azazel_common.view.build_status_view` — the single shared builder both
  products call, with shared `derive_posture` / `derive_headline` logic and a
  `from_state_snapshot` convenience path.
- Edge-lineage but a **generalized superset**: every product-specific field
  rides in `StatusView.product_view`, so Gadget-only concepts (`deception`
  posture, `scapegoat` decoy state, canary telemetry) are never dropped;
  `posture` and `HealthDimension.status` are open enums.
- Unit tests for shared posture/headline derivation and superset preservation.

### Changed

- Charter update: `docs/design-principles.md` (§2, new §3.1) and
  `docs/architecture.md` now allow a shared display *view-model* in Common
  while keeping the *renderer* (Web/TUI/E-Paper) product-side. The
  sibling-not-subset invariant (§4.4) is preserved.

## [0.1.0] — schema-only / contract-only

First release. Ships the shared schema and the CTI advisory contract only, per
`docs/migration-plan.md` Phase 1. No `paths`/`audit`/`api`/`notify` helpers, no
execution logic, no product integration.

### Added

- `azazel_common.schema`: `StateSnapshot`, `ModeState`, `ActionIntent` (with
  abstract, data-only `ObservePlan`..`ReleasePlan` plan descriptions),
  `EvidenceRef`, `DecisionExplanation`, `AuditEvent`, `TrustCapsule`.
- `azazel_common.cti_contracts`: `CtiEventBatch`, `CtiFlowBatch`,
  `CtiReactionBatch`, `CtiContextRequest`, `CtiContextResponse`, `IocMatch`,
  `BehavioralCtiBlock`.
- Advisory-only invariant enforced in `CtiContextResponse`: directive-shaped
  fields (`directive`, `must_execute`, `override`, `required_action`) are
  rejected, and `behavioral_cti` is encoded as absent — never `null`, never an
  empty object — when there is nothing to report.
- Unit tests covering construction, (de)serialization round-trips, and the CTI
  advisory invariants.
- `pyproject.toml` (Pydantic-only runtime dependency; `flask`/`fastapi`/`test`
  optional extras) and GitHub Actions CI running the test suite.

[Unreleased]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/01rabbit/Azazel-Fabric/releases/tag/v0.2.0
[0.1.0]: https://github.com/01rabbit/Azazel-Fabric/releases/tag/v0.1.0
