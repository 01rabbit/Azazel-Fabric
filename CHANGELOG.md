# Changelog

All notable changes to Azazel-Common are recorded here. The project follows
[Semantic Versioning](https://semver.org/). Each release corresponds to a
`vX.Y.Z` tag and GitHub Release on `01rabbit/Azazel-Common`; consumers pin an
exact tag (see `docs/migration-plan.md`).

## [Unreleased]

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

[Unreleased]: https://github.com/01rabbit/Azazel-Common/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/01rabbit/Azazel-Common/releases/tag/v0.1.0
