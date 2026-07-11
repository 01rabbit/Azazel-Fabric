# Changelog

All notable changes to Azazel-Fabric (formerly Azazel-Common) are recorded
here. The project follows [Semantic Versioning](https://semver.org/). Each
release corresponds to a `vX.Y.Z` tag and GitHub Release on
`01rabbit/Azazel-Fabric`; consumers pin an exact tag (see
`docs/migration-plan.md`).

## [Unreleased]

### Added

- `LICENSE` — MIT (owner decision 2026-07-11: unlicensed series repos align
  to MIT). `pyproject.toml` `license` field and `README.md` updated from
  `TBD` to MIT accordingly.

## [0.4.0] — Phase 5 helpers + Phase 6 adoption tooling

Adds the five Phase-5/Phase-6 helper modules — the `paths`/`api`/`notify`/
`audit` helpers that were "design proposal / not frozen" since `v0.1.0`, plus
the `testing` module — as **additive, non-breaking** code. No change to
`schema`, `cti_contracts`, or `view` semantics; consumers on `v0.3.0` upgrade by
bumping the pin, with nothing to migrate.

Two owner decisions (2026-07-10/11) shaped this release:

- **Audit hash chains stay product-local.** `azazel_fabric.audit` ships the
  shared `AuditEvent` projection and JSONL format **only** — **no hash chain,
  no chain verification**. Edge's P0 hash-chain / tamper-evidence audit is
  deliberately out of Fabric's scope and lives in Edge. Stated explicitly in the
  module docstring and `docs/contracts.md` §1.
- **`contracts.md` §3 (api) / §4 (notify) / §5 (paths) are ratified as
  implemented** — built as specified, with deviations noted inline in that doc.

### Added

- `azazel_fabric.paths` — candidate-path **hints** per `contracts.md` §5:
  `candidate_runtime_dirs` / `candidate_config_dirs` / `candidate_log_dirs` /
  `candidate_dirs` / `preferred_dir`, `normalize_product` (legacy alias
  resolution: `azazel-pi`→`edge`, `azazel-zero`→`gadget`), and a **dry-run-only**
  `plan_migration` (`MigrationPlan`/`MigrationStep`) that describes a
  legacy→canonical move and never performs one. Pure/deterministic — no
  filesystem, environment, or clock reads. Hints, never authority: a product
  keeps its own path schema.
- `azazel_fabric.api` — framework-neutral security-posture helpers per
  `contracts.md` §3: the shared JSON error model (`ErrorEnvelope`/`ErrorBody`,
  `error_payload`, `fail_closed_error`), the ordered role vocabulary
  (`ROLES`, `role_rank`, `role_allows`, fail-closed), and token-header
  extraction (`TOKEN_HEADER`/`COMPAT_TOKEN_HEADER`, `extract_token`,
  constant-time `token_matches`). No Flask/FastAPI import in core — adapters
  stay optional extras.
- `azazel_fabric.notify` — the shared `NotificationEvent` payload model per
  `contracts.md` §4 (closed `info`/`warning`/`critical` severity), plus pure
  transport mappers `to_ntfy_payload` / `to_mattermost_payload` that build a
  payload and **never send** (no network in Fabric).
- `azazel_fabric.audit` — `AuditEvent` projection (`project_audit_event`,
  `make_event_id`) and JSONL formatters (`to_jsonl_line` / `from_jsonl_line` /
  `iter_jsonl` / `write_jsonl` / `read_jsonl`). **No chain, no verification**
  (owner decision above).
- `azazel_fabric.testing` — shared factories (`make_*` populated / `minimal_*`
  required-only for `StateSnapshot`, `ModeState`, `StatusView`, `AuditEvent`,
  `ActionIntent`, `CtiContextRequest`/`Response`) and invariant assertions
  (`assert_advisory_only`, `assert_behavioral_absent_not_null`). **No pytest
  dependency** — plain functions usable from any test framework.
- `docs/adoption-guide.md` — day-1 adoption playbook for a new series product
  (e.g. the reserved `Azazel-Boot`): tag-pinning, the guarded-import idiom,
  adopt-`view`-first, emit-alongside, using `azazel_fabric.testing`, the
  advisory-only doctrine, and the pointer to the umbrella naming spec. Linked
  from `README.md`.
- Unit tests for all five modules (46 new): path purity/determinism and legacy
  resolution, audit round-trips and the no-chain guard, error-shape building and
  fail-closed roles/token auth, notify round-trips and transport mapping, and
  testing-module factory validity + invariant assertions.

### Changed

- Docs synced to shipped reality: `contracts.md` §3–§5 headers moved from
  "design proposal / not frozen" to **ratified/implemented (`v0.4.0`)** with
  deviations noted inline; `design-principles.md` §2 module-table statuses;
  `repository-layout.md` tree marked real (and reconciled with the actual
  files); `migration-plan.md` Phase 5 → **Implemented (`v0.4.0`; consumer
  adoption follows as separate PRs)** and Phase 6 → **Complete** per the owner's
  definition (adoption guide + testing module); `README.md` module list and doc
  table updated.

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

[Unreleased]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/01rabbit/Azazel-Fabric/releases/tag/v0.2.0
[0.1.0]: https://github.com/01rabbit/Azazel-Fabric/releases/tag/v0.1.0
