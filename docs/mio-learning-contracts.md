# M.I.O. learning provenance addendum — proposal

**Status: experimental proposal, not owner-approved.** This optional descriptive
schema extends `mio_contracts` for Fabric #72. It is carried in the local
`0.9.0rc7.dev0` candidate tree; that version is unpublished and unsigned. It is
not a Knowledge producer, a training pipeline, or a model-admission contract.

## Reuse and gaps

| Meaning | Existing canonical contract | Addendum role | Owner boundary |
|---|---|---|---|
| M.I.O. input and claim provenance | `mio_contracts.SituationFrame`, `Claim`, `ClaimSet` | Reuse their opaque evidence and trace references | M.I.O. product adapters build frames and claims |
| Observed mechanism and outcome | `outcome_contracts.ExecutionRefV0`, `MechanismObservationV0`, `OutcomeObservationV0`, `TacticalEffectAssessmentRefV0` | `IndependentOutcomeRefV0` points to an existing observation; it does not copy or upgrade it | The observing product owns the observation; Knowledge owns ingest and retention |
| Knowledge snapshot | No shared per-snapshot generation/revocation reference in the existing M.I.O. family | `KnowledgeSnapshotRefV0` records a source, generation, digest, as-of time, and producer-reported state | Knowledge must define authentication, generation, expiry, revocation, licensing, and privacy |
| Teacher suggestion | No existing teacher-label record | `TeacherLabelCandidateV0` records model, prompt, candidate value, and evidence refs | A teacher output is untrusted and is never an observation or fact |
| Human disposition | No existing disposition record | `TeacherReviewDispositionV0` records pending/retained/rejected/revision-requested | Retention means evaluation consideration only; it does not approve a label or a model |
| Dataset/feature lineage | Existing claims and model refs lack a frozen learning-dataset lineage record | `OfflineDatasetLineageV0` links a candidate, disposition, observation, feature record, and split group | The dataset owner defines extraction, rights, leakage controls, and evaluation protocol |
| Model and evaluation lineage | Existing M.I.O. claims can name models, but not a training/evaluation chain | `OfflineModelLineageV0` links distinct train/evaluation datasets, feature schema, trainer, baseline, artifact digest, report, and optional rollback parent | A product still decides whether any model may run; Fabric cannot install or admit it |

## Semantics and limits

All new records are frozen, closed-schema, bounded, and descriptive only. The
bundle preserves separate records for snapshot evidence, an LLM proposal, a
review disposition, an independent observation, dataset lineage, and model
evaluation lineage. It contains no `accepted_label`, training-eligibility,
installation, activation, or admission field, and Fabric exposes no conversion
from a proposal to a fact or accepted training label.

`KnowledgeSnapshotRefV0.reported_state` is what the producer reports. In
particular `reported_current` is not verified by Fabric. This profile does not
define an expiry clock, a revocation feed, signature verification, or what
happens when a consumer cannot query the producer. A revoked report must include
a revocation reference, but the reference is not verified here.

A dataset example must link an existing candidate, a completed
`retained_for_evaluation` review, and a separately referenced outcome. The
outcome can still be `unknown` or `disputed`. `split_group_ref` cannot span the
train/validation/test partitions within one dataset. The record stores no
feature values or teacher chain-of-thought, only bounded provenance references.

A model record must refer to distinct training and evaluation datasets and a
baseline. It describes an artifact and evaluation report; it does not assert
that a model is useful, calibrated, eligible, admitted, or deployed.

## Compatibility

The addendum is optional and additive. It leaves every existing
`mio_contracts` and `outcome_contracts` schema unchanged. Consumers that do not
import the new types remain compatible. The feature-to-minimum matrix records
`mio-learning-provenance/v0.1` at `0.9.0rc7` as experimental and unpublished;
there is no compatibility promise while it is a candidate.

No product is credited as a producer or consumer by this schema proposal.
Fabric #72 remains open until its mapping, producer/consumer version matrix,
Knowledge-owned snapshot contract, real producer and two independent consumers,
and adversarial interoperability evidence are supplied.

## Owner decisions still needed

1. Knowledge defines snapshot identity, generation, per-claim expiry/revocation,
   source licensing, query scope, and how current-generation status is asserted.
2. Product owners define reviewer independence and what observed outcomes are
   sufficient for a task-specific label. `retained_for_evaluation` is not
   sufficient by itself.
3. The dataset owner defines time/entity partitioning, deduplication, leakage
   checks, retention, rights, and the evaluation cost/abstention measures.
4. Consumers agree on exact cross-product reference syntax and unknown-version,
   stale, revoked, and absent-profile degradation behavior.
