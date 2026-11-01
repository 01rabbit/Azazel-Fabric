from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from azazel_fabric.mio_contracts import (
    LearningProvenanceBundleV0,
    TeacherLabelCandidateV0,
    TeacherReviewDispositionV0,
)
from azazel_fabric.mio_contracts import canonical_mio_json


FIXTURE = Path(__file__).parent / "fixtures" / "learning" / "mio_learning_provenance_bundle_v0.json"


def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_bundle_keeps_proposals_reviews_observations_and_lineage_distinct():
    bundle = LearningProvenanceBundleV0.model_validate(payload())
    restored = LearningProvenanceBundleV0.model_validate(bundle.model_dump(mode="json"))
    assert restored == bundle
    assert "accepted_label" not in bundle.model_dump(mode="json")
    assert "training_eligible" not in bundle.model_dump(mode="json")
    assert bundle.candidates[0].authority_class == "teacher_candidate_only"
    assert bundle.reviews[0].state == "retained_for_evaluation"
    assert bundle.outcomes[1].observed_state == "unknown"


def test_canonical_round_trip_preserves_bytes():
    first = canonical_mio_json(LearningProvenanceBundleV0.model_validate(payload()))
    second = canonical_mio_json(LearningProvenanceBundleV0.model_validate(json.loads(first)))
    assert first == second


@pytest.mark.parametrize("schema", ["mio-learning-provenance-bundle/v9", "mio-teacher-label-candidate/v9"])
def test_unknown_version_fails_closed(schema):
    data = payload()
    if schema.startswith("mio-learning"):
        data["schema_version"] = schema
    else:
        data["candidates"][0]["schema_version"] = schema
    with pytest.raises(ValidationError):
        LearningProvenanceBundleV0.model_validate(data)


def test_revoked_snapshot_requires_explicit_revocation_reference():
    data = payload()
    data["snapshots"][0]["reported_state"] = "revoked"
    data["snapshots"][0]["revocation_ref"] = None
    with pytest.raises(ValidationError, match="revocation evidence"):
        LearningProvenanceBundleV0.model_validate(data)


def test_snapshot_state_is_recorded_as_report_not_verified_truth():
    data = payload()
    snapshot = data["snapshots"][0]
    assert snapshot["reported_state"] == "reported_current"
    snapshot["is_verified"] = True
    with pytest.raises(ValidationError):
        LearningProvenanceBundleV0.model_validate(data)


def test_pending_review_cannot_be_given_a_completed_reviewer_or_time():
    with pytest.raises(ValidationError, match="pending review"):
        TeacherReviewDispositionV0(
            disposition_ref="review-pending",
            candidate_ref="candidate-1",
            state="pending",
            reviewer_ref="reviewer-1",
            reviewed_at="2026-10-30T00:00:00Z",
        )


def test_completed_review_requires_reviewer_and_time():
    with pytest.raises(ValidationError, match="completed disposition"):
        TeacherReviewDispositionV0(
            disposition_ref="review-complete",
            candidate_ref="candidate-1",
            state="retained_for_evaluation",
        )


def test_pending_or_rejected_proposal_cannot_enter_dataset_manifest():
    data = payload()
    data["reviews"][0]["state"] = "pending"
    data["reviews"][0]["reviewer_ref"] = None
    data["reviews"][0]["reviewed_at"] = None
    with pytest.raises(ValidationError, match="retained-for-evaluation"):
        LearningProvenanceBundleV0.model_validate(data)


def test_dataset_example_requires_complete_candidate_review_outcome_chain():
    data = payload()
    data["datasets"][0]["examples"][0]["outcome_ref"] = "missing-outcome"
    with pytest.raises(ValidationError, match="incomplete candidate/review/outcome"):
        LearningProvenanceBundleV0.model_validate(data)


def test_dataset_rejects_same_incident_group_across_splits():
    data = payload()
    data["datasets"][0]["examples"].append({
        **data["datasets"][0]["examples"][0],
        "candidate_ref": "candidate-2",
        "disposition_ref": "review-2",
        "outcome_ref": "outcome-2",
        "feature_record_ref": "feature-record-2",
        "split": "test",
    })
    with pytest.raises(ValidationError, match="one split group"):
        LearningProvenanceBundleV0.model_validate(data)


def test_training_and_evaluation_datasets_must_differ():
    data = payload()
    data["models"][0]["evaluation_dataset_ref"] = "dataset-train-1"
    with pytest.raises(ValidationError, match="must be distinct"):
        LearningProvenanceBundleV0.model_validate(data)


def test_model_cannot_be_marked_admitted_or_activated():
    data = payload()
    data["models"][0]["admitted"] = True
    with pytest.raises(ValidationError):
        LearningProvenanceBundleV0.model_validate(data)


def test_candidate_has_no_accepted_label_field():
    data = payload()["candidates"][0]
    data["accepted_label"] = data["proposed_label"]
    with pytest.raises(ValidationError):
        TeacherLabelCandidateV0.model_validate(data)
