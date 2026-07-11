# Azazel-Fabric (formerly Azazel-Common): Migration Plan

Status: **In progress, out of the originally planned order.** Phases 0 and
1 are done and tagged. Phase 4 (Gadget) is effectively done — ahead of
Phases 2/3 — because Gadget adopted the shared `view` module in `v0.2.0`
before either Edge or Knowledge integrated the package at all. `v0.3.0`
renamed the package itself (repository, distribution, and import
namespace) from `Azazel-Common`/`azazel_common` to
`Azazel-Fabric`/`azazel_fabric`; see the note under Phase 4 for what
that means for Gadget's existing pin. See the status table below; the
phase write-ups further down are kept as originally written for their
scope/non-goals, with a status line added to each.

### Status by phase

| Phase | What | Status |
|---|---|---|
| 0 | Design only | **Done** — design docs in this repo |
| 1 | Bootstrap package, schema-only | **Done** — `v0.1.0` tagged (`schema` + `cti_contracts`) |
| 2 | Introduce into Azazel-Knowledge | **Not started** — gated on a dependency-policy exception; Azazel-Knowledge's core dependency set (stdlib + PyYAML + idna + PyNaCl) excludes `pydantic` today, so adoption needs a `pyproject.toml` change plus an ADR and owner decision on the Knowledge side before any code lands |
| 3 | Introduce into Azazel-Edge | **Implemented & merged (2026-07-10, Azazel-Edge#309)** — Edge pins `azazel-fabric` (commit-pinned until the `v0.3.0` tag is published) and ships emit-alongside projections for `DecisionExplanation` / `TrustCapsule` / `AuditEvent` per its adapter plan §3, plus a `StatusView` emit + `/api/state` read-back beyond the original scope — making Edge the series' largest Fabric consumer. Edge↔Knowledge integration (real `cti_contracts` use) remains FY2027+ |
| 4 | Introduce into Azazel-Gadget | **Effectively done, ahead of order, migration to `v0.3.0` pending** — Azazel-Gadget currently pins `azazel-common @ git+...@v0.2.0` (the old distribution name) in `requirements.txt`, emits `StatusView` alongside its own snapshot (`py/azazel_gadget/common_view.py`), reads it back (`control_plane.py`), and surfaces it via its web API (`/api/state`, `status_view` key) using the `product_view={"gadget_snapshot": ...}` superset pattern. Note this happened via the `view` module (`v0.2.0`), which was not part of this phase's original scope (`StateSnapshot`/`ModeState`/`ActionIntent`/`AuditEvent`/notify) — the phase's *intent* (Gadget as a real Fabric consumer) is satisfied, but not via the exact schema list originally planned, and it landed before Phases 2/3. Gadget's migration to the `v0.3.0` `azazel-fabric`/`azazel_fabric` names is a follow-up, not yet done |
| 5 | path / auth / notify helper consolidation | **Implemented (`v0.4.0`)** — `paths`/`api`/`notify`/`audit` helper modules shipped in Fabric per `contracts.md` §3–§5 (ratified as implemented). Consumer adoption (removing real duplication in Edge/Gadget/Knowledge) follows as separate PRs on each product's own schedule |
| 6 | Future tools | **Complete (per owner definition, `v0.4.0`)** — defined as a day-1 adoption guide for future series products (`docs/adoption-guide.md`) plus the `azazel_fabric.testing` module; both shipped. Remains a standing policy for each new repository going forward |

This is an honest deviation from the plan's original sequencing (Phase 4
before Phase 2/3), not a silent one — flagged here per this repository's
own change-safety expectations.

## Guiding constraint

Every phase below is additive and reversible. No phase requires deleting
or rewriting a working code path in Edge, Gadget, or Knowledge. No phase
moves Edge's Deterministic Arbiter, Edge's NOC/SOC Evaluators, Knowledge's
Correlation Engine, or Gadget's Wi-Fi/USB control. No phase before Phase 2
touches an existing repository at all. BHUSA 2026 demo stability takes
priority over migration speed at every phase.

## Phase 0 — Design only (this task)

**Status: Done.**

Deliverables: the six documents in `docs/` in this repository
(`architecture.md`, `design-principles.md`, `contracts.md`,
`migration-plan.md`, `repository-layout.md`, `issue-breakdown.md`). No
package code, no dependency changes, no changes to any other Azazel
repository.

Exit condition: design reviewed and approved by the repository owner.

## Phase 1 — Bootstrap `Azazel-Fabric` package, schema-only

**Status: Done.** `v0.1.0` tagged; `schema` and `cti_contracts` shipped
exactly as scoped below (under the `Azazel-Common`/`azazel_common` name at
the time; renamed in `v0.3.0`, see the rename note below).

Add the `src/azazel_fabric` package to this repository per
`repository-layout.md`. First release is `v0.1.0` and contains **only**:

- `azazel_fabric.schema` (`StateSnapshot`, `ModeState`, `ActionIntent`,
  `EvidenceRef`, `DecisionExplanation`, `AuditEvent`, `TrustCapsule`)
- `azazel_fabric.cti_contracts` (`CtiEventBatch`, `CtiFlowBatch`,
  `CtiReactionBatch`, `CtiContextRequest`, `CtiContextResponse`)
- unit tests validating the schemas construct/(de)serialize correctly
  (no product integration yet)

No execution logic. No path/audit/api/notify helpers yet — those are
Phase 5. This keeps the first release small enough to review completely
and stable enough to tag immediately.

Exit condition: `v0.1.0` tagged. Nothing outside `Azazel-Fabric` depends on
it yet.

### Rename note (not a phase — a `v0.3.0` housekeeping event)

`v0.3.0` renamed the repository from `01rabbit/Azazel-Common` to
`01rabbit/Azazel-Fabric`, the distribution from `azazel-common` to
`azazel-fabric`, and the import namespace from `azazel_common` to
`azazel_fabric`. This is a breaking change to every consumer's import
statements and dependency pin, but changes no schema, no field, and no
behavior — it does not correspond to any phase above and does not move any
phase's status. `v0.1.0`/`v0.2.0` tags remain installable forever under the
old names; only new tags (`v0.3.0`+) use the new names. See `CHANGELOG.md`.

## Phase 2 — Introduce into Azazel-Knowledge

**Status: Not started.** Blocked on a dependency-policy exception on the
Knowledge side (see status table above) — this phase's description below is
still the intended approach once that gate clears.

Azazel-Knowledge adopts `azazel_fabric.cti_contracts` for payload
*validation* on `/v1/events`, `/v1/flows`, `/v1/reactions`, `/v1/context`.

Approach: wrap the existing endpoint handlers with validation against the
Fabric schema, running **alongside** (not replacing) existing validation
until parity is confirmed by contract tests (Issue 4). Existing API
consumers (including current Edge integration) must continue to work
unchanged — this phase is a validation-layer swap, not an API redesign.
`CtiContextResponse.behavioral_cti` omission-when-absent behavior must be
preserved exactly (see `contracts.md` §2).

Exit condition: Knowledge's four endpoints validate against Fabric schemas
in CI; no observed behavior change for existing callers; existing Knowledge
test suite still passes unmodified.

## Phase 3 — Introduce into Azazel-Edge

**Status: Implemented & merged (2026-07-10, Azazel-Edge#309).** Edge ships the three
emit-alongside adapters plus a `StatusView` emit/read-back extension; the
description below is the original plan target, now realized (CTI-side usage
still FY2027+).

Edge adopts Fabric schemas for:

- the payloads it sends to Knowledge (`CtiEventBatch`/`CtiFlowBatch`/
  `CtiReactionBatch`/`CtiContextRequest`) and how it parses
  `CtiContextResponse`,
- `DecisionExplanation` and `AuditEvent` as the *serialization* shape for
  its existing Decision Explanation and Audit Logger output.

Explicitly out of scope for this phase: Edge's Action Arbiter, NOC/SOC
Evaluator internals, and Evidence Plane logic. Only the boundary — what
gets sent to Knowledge, and what shape decisions/audit records are
serialized into — changes. The arbiter still decides; Fabric only
standardizes how that decision is written down and transmitted.

Exit condition: Edge's outbound CTI payloads and audit/decision log output
validate against Fabric schemas in CI; existing demo flows (including
BHUSA prep) verified unaffected via the project's `/verify` and `/run`
checks before merge.

## Phase 4 — Introduce into Azazel-Gadget

**Status: Effectively done, ahead of order (`v0.2.0`); pin migration to
`v0.3.0` pending.** Gadget shipped a real integration via the shared
`StatusView` view-model (emit-alongside its snapshot, plus readback and
web-API surfacing) before Phases 2/3 started — see the status table above.
That satisfies this phase's intent (a real Gadget consumer) but via `view`,
not the exact schema list below, which was the original, not-yet-realized
plan for this phase. Gadget currently pins `v0.2.0` under the old
`azazel-common` name; migrating that pin to `v0.3.0`
(`azazel-fabric`/`azazel_fabric`) is a small follow-up in the Gadget
repository, not yet done.

Gadget adopts Fabric schemas for `StateSnapshot`, `ModeState`,
`ActionIntent`, `AuditEvent`, and notification payloads.

Explicitly out of scope: `wlan0` control, USB gadget control, captive
portal viewer. Gadget's existing path-schema/legacy-migration logic is
reviewed as *input* to `azazel_fabric.paths` design (Phase 5), not
replaced in this phase.

Exit condition: Gadget's state/mode/audit/notification payloads validate
against Fabric schemas in CI; Gadget's existing hardware-control code
paths untouched.

## Phase 5 — path / auth / notify helper consolidation

**Status: Implemented in Fabric (`v0.4.0`); consumer adoption follows as
separate PRs.** The helper modules are built and released; `contracts.md`
§3–§5 moved from "design proposal / not frozen" to ratified/implemented. The
originally-planned helpers, now shipped:

- `azazel_fabric.paths` (candidate-path **hints** + legacy-alias resolution +
  dry-run-only migration planner; generalized from Gadget's path-schema/
  legacy-migration design without copying its product-specific assumptions —
  hints only, never authoritative, so Edge's legacy-compat paths are not forced
  through it)
- `azazel_fabric.api` (token/role/fail-closed helpers; framework-neutral)
- `azazel_fabric.notify` (`NotificationEvent` + pure ntfy/Mattermost payload
  mappers; the SSE bridge is the same `NotificationEvent` shape)
- `azazel_fabric.audit` (shared `AuditEvent` projection + JSONL formatters;
  **no hash chain / no chain verification** — owner decision, chains stay
  product-local)

Each repository adopts these incrementally and only where it removes actual
duplication — not as a mandate to touch code that isn't already duplicated.

Exit condition (Fabric side, met): the helper modules ship with full unit
tests, additively, breaking no existing `schema`/`cti_contracts`/`view`
semantics. Exit condition (adoption side, ongoing): at least one real
duplicated implementation removed from at least two of {Edge, Gadget,
Knowledge} in favor of the Fabric helper, with contract tests passing —
tracked in each product's repository, not gated on this release.

## Phase 6 — Future tools

**Status: Complete (per owner definition, `v0.4.0`).** Scoped by owner
decision (2026-07-10/11) to two concrete deliverables, both now shipped:

- `docs/adoption-guide.md` — a day-1 adoption playbook for a new series product
  (e.g. the reserved `Azazel-Boot`): tag-pinning, the guarded-import idiom,
  which module to adopt first (`view`/`StatusView`), emit-alongside without
  coupling, using `azazel_fabric.testing`, the advisory-only doctrine, and the
  pointer that the umbrella naming spec (`docs/specs/naming.md`) governs product
  names/codenames.
- `azazel_fabric.testing` — shared factories and invariant assertions so a new
  product's CI can assert it satisfies the shared contract from its first
  commit, without depending on another product's test suite.

`Azazel-Boot` and any new Azazel-series tool depend on `Azazel-Fabric` from
their first commit, rather than inventing their own state/audit/CTI formats.
Beyond the two deliverables above, this remains a standing policy for new
repositories going forward — it has no recurring exit condition of its own.

## Versioning and consumption policy (applies to every phase)

- SemVer. Proposed progression:
  - `v0.1.0` — schema-only / contract-only (Phase 1)
  - `v0.2.0` — shared status view-model added
  - `v0.3.0` — repository/distribution/import namespace renamed to
    Azazel-Fabric/`azazel_fabric` (breaking; no schema change)
  - `v0.4.0` — Phase 5 helper modules (`paths`/`api`/`notify`/`audit`) +
    Phase 6 adoption tooling (`docs/adoption-guide.md` + `testing`) added
  - `v0.5.0` — CTI contract stabilized against real Edge↔Knowledge traffic
  - `v1.0.0` — after Edge, Gadget, and Knowledge each pass their contract
    test suite against Fabric
- Consumers pin an exact tag via
  `azazel-fabric @ git+https://github.com/01rabbit/Azazel-Fabric.git@vX.Y.Z`
  (or, for `v0.2.0` and earlier, the old `azazel-common` name against the
  same, redirected repository URL). No submodules, no floating branch
  dependency.
- Any breaking schema change is a major version bump, ships with a
  migration note in `Azazel-Fabric`'s own `CHANGELOG.md`, and is adopted
  by consumers on their own schedule — never forced by a Fabric release
  alone. The `v0.3.0` rename itself shipped as a minor version per the
  project's pre-`1.0.0` SemVer convention (breaking changes are called out
  in `CHANGELOG.md` rather than gated behind a major bump) — see
  `CHANGELOG.md`'s `v0.3.0` entry for the exact consumer-facing break.

## Rollback posture

Because every phase is additive (new validation/serialization layered
alongside existing logic until parity is shown), rolling back any single
phase is a matter of reverting that phase's adapter commit(s) in the
consuming repository — it does not require unwinding schema changes in
`Azazel-Fabric` itself, and does not touch any other phase.
