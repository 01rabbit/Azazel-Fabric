# Azazel-Covenant (formerly Azazel-Common): Issue Breakdown

Status: **Proposed at design time; work has proceeded without these being
filed as tracked GitHub issues in this repository.** Issues 1 and 2's
deliverables shipped (this design record, plus `v0.1.0`). Issue 5's
deliverable exists as a document in the `Azazel-Edge` repository
(`AZAZEL_COMMON_EDGE_ADAPTER_PLAN.md`, 2026-07-09) rather than as a
tracked GitHub issue here — see its note below. Issues 3, 4, 6, 7, 8 remain
unstarted. The numbering and content below are kept as originally proposed
(not renumbered or rewritten) — this status note is the only change.

Each issue below states target repository, goal, deliverables, explicit
non-goals, and the acceptance condition that closes it. Ordering follows
`migration-plan.md`.

## Issue 1 — Design Azazel-Covenant (this task)

**Repository:** `Azazel-Covenant` (design record, this repository).
**Goal:** Produce the design documents this task delivers.
**Deliverables:** `docs/architecture.md`, `design-principles.md`,
`contracts.md`, `migration-plan.md`, `repository-layout.md`,
`issue-breakdown.md`.
**Non-goals:** No package code. No changes to any other Azazel
repository.
**Acceptance:** Repository owner reviews and approves the design.

## Issue 2 — Bootstrap Azazel-Covenant v0.1.0, schema-only

**Repository:** `Azazel-Covenant` (this repository).
**Goal:** Add the `src/azazel_covenant` package per
`repository-layout.md` and ship
`azazel_covenant.schema` + `azazel_covenant.cti_contracts` only, per
`migration-plan.md` Phase 1.
**Deliverables:** repository scaffold, `pyproject.toml`, the seven schema
modules, the four CTI contract modules, unit tests, `v0.1.0` tag.
**Non-goals:** no `paths`/`audit`/`api`/`notify` modules yet; no product
integration; no execution logic of any kind.
**Acceptance:** `pip install`-able package; `pytest` green; tag pushed;
no dependency from any existing Azazel product yet.

## Issue 3 — Define CTI advisory contracts for Edge-Grimoire integration

**Repository:** `Azazel-Covenant` (schema definition) with review input from
`Azazel-Grimoire` and `Azazel-Edge` maintainers.
**Goal:** Finalize `CtiContextRequest`/`CtiContextResponse` (and the three
ingest batch shapes) against Azazel-Grimoire's actual current API, per
`contracts.md` §2.
**Deliverables:** finalized field lists, explicit confirmation that
`behavioral_cti` omission-when-absent semantics match Grimoire's existing
behavior, explicit confirmation no directive-shaped field exists in the
response.
**Non-goals:** no change to Azazel-Grimoire's running API in this issue —
schema-definition only.
**Acceptance:** schema reviewed against real Grimoire request/response
samples (recorded as fixtures in `azazel_covenant.testing.contract_cases`);
advisory-only invariant confirmed by both Edge and Grimoire maintainers.

## Issue 4 — Add contract tests for CTI context and reaction payloads

**Repository:** `Azazel-Covenant` (test authorship), exercised against
`Azazel-Grimoire` in CI.
**Goal:** Catch payload drift between what Edge/Gadget send and what
Grimoire accepts, and between what Grimoire returns and what Edge/Gadget
expect.
**Deliverables:** `azazel_covenant.testing.contract_cases` populated with
canonical valid/invalid payloads; a CI job (in `Azazel-Grimoire`, consuming
Covenant) that validates live endpoint behavior against these cases.
**Non-goals:** does not change Grimoire's existing validation logic — sits
alongside it.
**Acceptance:** CI job passes against current Grimoire `main`; a
deliberately introduced payload-shape drift in a test branch is caught by
the job.

## Issue 5 — Prepare Azazel-Edge adapter plan for common decision and audit schemas

**Status: deliverable exists.** `Azazel-Edge`'s
`docs/AZAZEL_COMMON_EDGE_ADAPTER_PLAN.md` (dated 2026-07-09) is this
issue's plan-note deliverable, covering `DecisionExplanation`/
`TrustCapsule`/`AuditEvent` emit-alongside adapters. It was written as a
repository doc rather than a filed GitHub issue, and it explicitly defers
real Edge↔Grimoire integration to FY2027+; no adapter code has landed yet.

**Repository:** `Azazel-Edge`.
**Goal:** Concrete adapter plan (not yet the adapter itself, unless the
plan review clears it) for serializing Edge's existing Decision
Explanation and Audit Logger output through `azazel_covenant.schema`, and
for sending CTI payloads through `azazel_covenant.cti_contracts`, per
`migration-plan.md` Phase 3.
**Deliverables:** a short design note identifying exact call sites in
Edge's existing Decision Logger / Grimoire client code that would wrap
Covenant schemas, with an explicit statement of which files/functions are
*not* touched (Action Arbiter, NOC/SOC Evaluator, Evidence Plane).
**Non-goals:** does not modify Edge's decision logic. Does not relocate
any arbiter code.
**Acceptance:** plan reviewed; confirms zero behavior change to Edge's
BHUSA-relevant demo paths; identifies a rollback point per adapter commit.

## Issue 6 — Prepare Azazel-Gadget adapter plan for common state, mode, and audit schemas

**Repository:** `Azazel-Gadget`.
**Goal:** Equivalent adapter plan for Gadget's state/mode/audit/
notification payloads, per `migration-plan.md` Phase 4.
**Deliverables:** design note identifying call sites; explicit statement
that Wi-Fi control, USB gadget control, and captive portal viewer are
untouched; note on how Gadget's existing path-schema/legacy-migration
design should inform (not be replaced wholesale by) Issue 7.
**Non-goals:** does not modify Gadget's hardware-control logic.
**Acceptance:** plan reviewed; confirms Gadget is treated as a sibling
product with its own field extensions where needed, not as "Edge minus
features."

## Issue 7 — Define common path schema and legacy compatibility policy

**Repository:** `Azazel-Covenant`, informed by `Azazel-Gadget`'s existing
path/legacy-migration design.
**Goal:** `azazel_covenant.paths` design and implementation, per
`migration-plan.md` Phase 5.
**Deliverables:** runtime/config/log dir convention for all products;
`azazel-pi`→`azazel-edge` and `azazel-zero`→`azazel-gadget` legacy mapping;
dry-run migration helper; active-schema discovery helper.
**Non-goals:** does not perform any migration against a running system as
part of this issue — helper only.
**Acceptance:** unit tests cover legacy-path detection and dry-run
migration output for representative Edge/Gadget/Grimoire path layouts; no
destructive operation possible without explicit non-dry-run opt-in by the
calling product.

## Issue 8 — Define shared notification event model

**Repository:** `Azazel-Covenant`.
**Goal:** `azazel_covenant.notify` design and implementation, per
`migration-plan.md` Phase 5.
**Deliverables:** shared notification event schema; thin ntfy send
helper; thin Mattermost send helper; SSE bridge model.
**Non-goals:** does not define product-specific notification copy, tone,
or UI rendering.
**Acceptance:** at least one existing duplicated notification-payload
implementation (Edge or Gadget) can be expressed through the shared model
without loss of information, verified by a round-trip test.

## Sequencing note

Issues 2 and 3 can proceed in parallel once Issue 1 is approved (both
operate inside the new `Azazel-Covenant` repository, on largely independent
schema surfaces). Issue 4 depends on both. Issues 5 and 6 depend on Issue
2 (need `v0.1.0` to exist) but not on each other, and not on Issues 7/8.
Issues 7 and 8 depend on Issue 2's package scaffold existing but are
otherwise independent of the Edge/Gadget/Grimoire integration issues — they can
start as soon as the package skeleton is in place, per
`migration-plan.md` Phase 5's stated precondition ("once Phase 2-4 prove
the schema layer is stable") being treated as a soft gate: design work on
7/8 may start early, but adoption in a product repository waits for that
precondition.
