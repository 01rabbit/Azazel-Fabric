# ADR-0002 — M.I.O. learning provenance schema proposal

- **Status:** Proposed; not owner-approved
- **Date:** 2026-11-02
- **Issue:** Fabric #72, coordinated by Azazel-MIO #1

## Context

The M.I.O. architecture needs to keep Knowledge snapshots, LLM teacher
suggestions, reviewer actions, independently observed practice outcomes, frozen
datasets, and evaluated model artifacts distinct. Existing `mio_contracts`
records claims and model provenance. Existing `outcome_contracts` records
execution, mechanism, observation, and tactical assessment, but it is not a
learning dataset or a Knowledge snapshot/revocation contract.

Knowledge's current context response does not bind each claim to an immutable
snapshot generation plus per-claim expiry/revocation. No immutable reviewed
training snapshot export is present. This proposal must not make these gaps
appear solved.

## Decision proposed

Add optional types to the existing experimental `mio_contracts` family rather
than create a parallel top-level family. Reuse outcome observations by
reference. Use separate closed record types for snapshot references, teacher
candidates, reviewer dispositions, independently observed outcomes, dataset
example/feature lineage, and offline model/evaluation lineage. Do not represent
an accepted training label or a model-admission state.

The new feature ID is `mio-learning-provenance/v0.1`, with minimum
`0.9.0rc7`. The local package version advances from `0.9.0rc6.dev0` to
`0.9.0rc7.dev0`; the candidate is not cut, signed, published, or stable.

Dataset joins must be task-consistent and must keep candidate, trace, review,
outcome, observation, feature-record, and split-group identities within one
partition across the bundle. Model lineage declares its task and must match
both datasets. The timestamp syntax is a bounded RFC3339 UTC subset; chronology
checks apply only to direct provenance links and do not infer outcome freshness.

## Consequences

- Existing schemas remain unchanged; consumers can omit the addendum.
- A producer-reported snapshot state is not a Fabric-verified trust decision.
- `retained_for_evaluation` is not label acceptance and does not qualify data
  for training by itself.
- Dataset records require references to candidate, completed review,
  independent outcome, feature record, and one split-group assignment. The same
  group cannot cross partitions inside a dataset.
- Model lineage requires distinct training and evaluation dataset references,
  a baseline, feature schema, trainer version, artifact digest, and report.
- Fabric remains free of network/authentication clients, training loops,
  inference, installation, and admission behavior.
- The profile remains experimental until a producer, two independent consumers,
  and failure/degradation interoperability tests exist.

## Unresolved decisions

Knowledge must own its snapshot generation and revocation semantics, per-claim
expiry, rights, and query privacy contract. Product owners must define reviewer
independence, independent outcome adequacy, retention, leakage controls,
evaluation measures, reference grammar, and consumer behavior for absent,
unknown, stale, revoked, or unsupported records. This proposal does not decide
those matters.

## Alternatives considered

1. Add fields to existing `Claim` or `OutcomeObservationV0`: rejected because a
   teacher suggestion, review decision, and independently observed outcome
   would collapse into existing claim/fact meanings.
2. Add a separate top-level `learning_contracts` package: rejected because the
   learning provenance is an M.I.O. extension and a separate family would
   duplicate adoption/version bookkeeping before any real consumer exists.
3. Call a signed snapshot current: rejected because a signature establishes
   origin/integrity only and does not establish freshness or revocation state.
