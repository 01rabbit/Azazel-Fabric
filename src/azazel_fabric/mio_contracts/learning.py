"""Experimental descriptive-only M.I.O. learning provenance contracts.

These records keep Knowledge snapshot assertions, teacher proposals, human
review, observed outcomes, and offline evaluation/model lineage separate.
They do not decide truth, training eligibility, installation, or admission.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from azazel_fabric.mio_contracts.validation import (
    assert_bounded_mio_payload,
    assert_no_mio_directives,
)


class _LearningRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def _assert_descriptive(self) -> None:
        payload = self.model_dump(mode="python")
        assert_no_mio_directives(payload)
        assert_bounded_mio_payload(payload)


class KnowledgeSnapshotRefV0(_LearningRecord):
    """A reference to snapshot evidence; state is producer-reported, not verified here."""

    schema_version: Literal["mio-knowledge-snapshot-ref/v0.1"] = "mio-knowledge-snapshot-ref/v0.1"
    snapshot_ref: str = Field(min_length=1, max_length=256)
    source_ref: str = Field(min_length=1, max_length=256)
    generation_ref: str = Field(min_length=1, max_length=128)
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    as_of: str = Field(min_length=1, max_length=64)
    observed_at: str = Field(min_length=1, max_length=64)
    reported_state: Literal["unknown", "reported_current", "stale", "revoked", "mismatched"]
    revocation_ref: str | None = Field(default=None, max_length=256)
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=64)
    authority_class: Literal["descriptive_snapshot_reference"] = "descriptive_snapshot_reference"

    @model_validator(mode="after")
    def _validate(self) -> "KnowledgeSnapshotRefV0":
        if self.reported_state == "revoked" and not self.revocation_ref:
            raise ValueError("a producer-reported revoked snapshot must include revocation evidence")
        self._assert_descriptive()
        return self


class TeacherLabelCandidateV0(_LearningRecord):
    """An LLM-proposed label with evidence and prompt/model lineage, never a fact."""

    schema_version: Literal["mio-teacher-label-candidate/v0.1"] = "mio-teacher-label-candidate/v0.1"
    candidate_ref: str = Field(min_length=1, max_length=256)
    trace_ref: str = Field(min_length=1, max_length=256)
    task_ref: str = Field(min_length=1, max_length=256)
    proposed_label: str = Field(min_length=1, max_length=128)
    teacher_model_ref: str = Field(min_length=1, max_length=256)
    teacher_model_version: str = Field(min_length=1, max_length=128)
    prompt_version_ref: str = Field(min_length=1, max_length=256)
    snapshot_ref: str | None = Field(default=None, max_length=256)
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=64)
    proposed_at: str = Field(min_length=1, max_length=64)
    authority_class: Literal["teacher_candidate_only"] = "teacher_candidate_only"

    @model_validator(mode="after")
    def _validate(self) -> "TeacherLabelCandidateV0":
        self._assert_descriptive()
        return self


class TeacherReviewDispositionV0(_LearningRecord):
    """Review state for a proposal; retention is for evaluation only."""

    schema_version: Literal["mio-teacher-review-disposition/v0.1"] = "mio-teacher-review-disposition/v0.1"
    disposition_ref: str = Field(min_length=1, max_length=256)
    candidate_ref: str = Field(min_length=1, max_length=256)
    state: Literal["pending", "retained_for_evaluation", "rejected", "revision_requested"]
    reviewer_ref: str | None = Field(default=None, max_length=256)
    reviewed_at: str | None = Field(default=None, max_length=64)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority_class: Literal["review_record_only"] = "review_record_only"

    @model_validator(mode="after")
    def _validate(self) -> "TeacherReviewDispositionV0":
        pending = self.state == "pending"
        if pending and (self.reviewer_ref is not None or self.reviewed_at is not None):
            raise ValueError("pending review cannot carry a completed reviewer or timestamp")
        if not pending and (not self.reviewer_ref or not self.reviewed_at):
            raise ValueError("a completed disposition requires reviewer and review time")
        self._assert_descriptive()
        return self


class IndependentOutcomeRefV0(_LearningRecord):
    """A reference to an independently observed result, not a derived label."""

    schema_version: Literal["mio-independent-outcome-ref/v0.1"] = "mio-independent-outcome-ref/v0.1"
    outcome_ref: str = Field(min_length=1, max_length=256)
    candidate_ref: str = Field(min_length=1, max_length=256)
    observation_ref: str = Field(min_length=1, max_length=256)
    observer_ref: str = Field(min_length=1, max_length=256)
    observed_state: Literal["observed", "not_observed", "unknown", "disputed"]
    observed_at: str = Field(min_length=1, max_length=64)
    evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=64)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority_class: Literal["independent_observation_reference"] = "independent_observation_reference"

    @model_validator(mode="after")
    def _validate(self) -> "IndependentOutcomeRefV0":
        self._assert_descriptive()
        return self


class DatasetExampleLineageV0(_LearningRecord):
    """One joined example; deliberately has no label or training-eligibility field."""

    schema_version: Literal["mio-dataset-example-lineage/v0.1"] = "mio-dataset-example-lineage/v0.1"
    candidate_ref: str = Field(min_length=1, max_length=256)
    disposition_ref: str = Field(min_length=1, max_length=256)
    outcome_ref: str = Field(min_length=1, max_length=256)
    feature_record_ref: str = Field(min_length=1, max_length=256)
    split_group_ref: str = Field(min_length=1, max_length=256)
    split: Literal["train", "validation", "test"]

    @model_validator(mode="after")
    def _validate(self) -> "DatasetExampleLineageV0":
        self._assert_descriptive()
        return self


class OfflineDatasetLineageV0(_LearningRecord):
    """Immutable dataset/feature lineage metadata, without labels or promotion."""

    schema_version: Literal["mio-offline-dataset-lineage/v0.1"] = "mio-offline-dataset-lineage/v0.1"
    dataset_ref: str = Field(min_length=1, max_length=256)
    dataset_version: str = Field(min_length=1, max_length=128)
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    task_ref: str = Field(min_length=1, max_length=256)
    extraction_version_ref: str = Field(min_length=1, max_length=256)
    feature_schema_ref: str = Field(min_length=1, max_length=256)
    split_policy_ref: str = Field(min_length=1, max_length=256)
    examples: tuple[DatasetExampleLineageV0, ...] = Field(min_length=1, max_length=128)
    frozen_at: str = Field(min_length=1, max_length=64)
    authority_class: Literal["descriptive_dataset_lineage"] = "descriptive_dataset_lineage"

    @model_validator(mode="after")
    def _validate(self) -> "OfflineDatasetLineageV0":
        group_splits: dict[str, str] = {}
        for example in self.examples:
            existing = group_splits.setdefault(example.split_group_ref, example.split)
            if existing != example.split:
                raise ValueError("one split group cannot cross train/validation/test partitions")
        self._assert_descriptive()
        return self


class OfflineModelLineageV0(_LearningRecord):
    """A model/evaluation record; it cannot admit or activate the described artifact."""

    schema_version: Literal["mio-offline-model-lineage/v0.1"] = "mio-offline-model-lineage/v0.1"
    model_ref: str = Field(min_length=1, max_length=256)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trainer_version_ref: str = Field(min_length=1, max_length=256)
    feature_schema_ref: str = Field(min_length=1, max_length=256)
    training_dataset_ref: str = Field(min_length=1, max_length=256)
    evaluation_dataset_ref: str = Field(min_length=1, max_length=256)
    baseline_model_ref: str = Field(min_length=1, max_length=256)
    evaluation_report_ref: str = Field(min_length=1, max_length=256)
    rollback_parent_ref: str | None = Field(default=None, max_length=256)
    recorded_at: str = Field(min_length=1, max_length=64)
    authority_class: Literal["descriptive_model_lineage"] = "descriptive_model_lineage"

    @model_validator(mode="after")
    def _validate(self) -> "OfflineModelLineageV0":
        if self.training_dataset_ref == self.evaluation_dataset_ref:
            raise ValueError("training and evaluation datasets must be distinct")
        self._assert_descriptive()
        return self


class LearningProvenanceBundleV0(_LearningRecord):
    """A bounded join of the distinct records; it derives no accepted label."""

    schema_version: Literal["mio-learning-provenance-bundle/v0.1"] = "mio-learning-provenance-bundle/v0.1"
    bundle_ref: str = Field(min_length=1, max_length=128)
    snapshots: tuple[KnowledgeSnapshotRefV0, ...] = Field(default_factory=tuple, max_length=64)
    candidates: tuple[TeacherLabelCandidateV0, ...] = Field(min_length=1, max_length=128)
    reviews: tuple[TeacherReviewDispositionV0, ...] = Field(min_length=1, max_length=128)
    outcomes: tuple[IndependentOutcomeRefV0, ...] = Field(min_length=1, max_length=128)
    datasets: tuple[OfflineDatasetLineageV0, ...] = Field(default_factory=tuple, max_length=64)
    models: tuple[OfflineModelLineageV0, ...] = Field(default_factory=tuple, max_length=64)
    recorded_at: str = Field(min_length=1, max_length=64)
    authority_class: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "LearningProvenanceBundleV0":
        candidates = {item.candidate_ref: item for item in self.candidates}
        reviews = {item.disposition_ref: item for item in self.reviews}
        outcomes = {item.outcome_ref: item for item in self.outcomes}
        snapshots = {item.snapshot_ref for item in self.snapshots}
        dataset_by_ref = {item.dataset_ref: item for item in self.datasets}
        if (
            len(snapshots) != len(self.snapshots)
            or len(candidates) != len(self.candidates)
            or len(reviews) != len(self.reviews)
            or len(outcomes) != len(self.outcomes)
            or len(dataset_by_ref) != len(self.datasets)
            or len({item.model_ref for item in self.models}) != len(self.models)
        ):
            raise ValueError("bundle record references must be unique")
        for item in self.candidates:
            if item.snapshot_ref is not None and item.snapshot_ref not in snapshots:
                raise ValueError("candidate references a snapshot outside the bundle")
        for item in self.reviews:
            if item.candidate_ref not in candidates:
                raise ValueError("review references a candidate outside the bundle")
        for item in self.outcomes:
            if item.candidate_ref not in candidates:
                raise ValueError("outcome references a candidate outside the bundle")
        dataset_refs = {item.dataset_ref for item in self.datasets}
        for dataset in self.datasets:
            for example in dataset.examples:
                candidate = candidates.get(example.candidate_ref)
                review = reviews.get(example.disposition_ref)
                outcome = outcomes.get(example.outcome_ref)
                if candidate is None or review is None or outcome is None:
                    raise ValueError("dataset example has incomplete candidate/review/outcome lineage")
                if review.candidate_ref != candidate.candidate_ref or review.state != "retained_for_evaluation":
                    raise ValueError("dataset example needs a retained-for-evaluation review of its candidate")
                if outcome.candidate_ref != candidate.candidate_ref:
                    raise ValueError("dataset outcome does not correspond to its teacher candidate")
                if candidate.task_ref != dataset.task_ref:
                    raise ValueError("dataset example task differs from its teacher candidate task")
        for model in self.models:
            if (
                model.training_dataset_ref not in dataset_refs
                or model.evaluation_dataset_ref not in dataset_refs
            ):
                raise ValueError("model lineage references a dataset outside the bundle")
            training = dataset_by_ref[model.training_dataset_ref]
            evaluation = dataset_by_ref[model.evaluation_dataset_ref]
            if model.feature_schema_ref not in (
                training.feature_schema_ref,
                evaluation.feature_schema_ref,
            ) or training.feature_schema_ref != evaluation.feature_schema_ref:
                raise ValueError("model feature schema differs from dataset lineage")
            if not any(example.split == "train" for example in training.examples):
                raise ValueError("training dataset has no train partition")
            if any(example.split == "test" for example in training.examples):
                raise ValueError("training dataset cannot include a test partition")
            if not all(example.split == "test" for example in evaluation.examples):
                raise ValueError("evaluation dataset must contain only test partitions")
        group_splits: dict[str, str] = {}
        for dataset in self.datasets:
            for example in dataset.examples:
                existing = group_splits.setdefault(example.split_group_ref, example.split)
                if existing != example.split:
                    raise ValueError("one split group cannot cross dataset partitions")
        self._assert_descriptive()
        return self
