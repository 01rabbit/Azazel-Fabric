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


def test_candidate_cannot_precede_its_referenced_snapshot_observation():
    data = payload()
    data["candidates"][0]["proposed_at"] = "2026-10-29T23:59:00Z"
    with pytest.raises(
        ValidationError,
        match="candidate.proposed_at precedes its referenced record",
    ):
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


def test_same_candidate_outcome_cannot_cross_train_and_test_with_new_group_ref():
    data = payload()
    train_example = data["datasets"][0]["examples"][0]
    test_example = {
        **train_example,
        "split_group_ref": "attacker-changed-group",
        "split": "test",
    }
    data["datasets"][1]["examples"] = [test_example]
    with pytest.raises(ValidationError, match="identity crosses dataset partitions"):
        LearningProvenanceBundleV0.model_validate(data)


def test_model_task_must_match_both_dataset_tasks():
    data = payload()
    data["models"][0]["task_ref"] = "task-different"
    with pytest.raises(ValidationError, match="model task differs"):
        LearningProvenanceBundleV0.model_validate(data)


@pytest.mark.parametrize(
    "record_path,field",
    [
        (("snapshots", 0), "as_of"),
        (("snapshots", 0), "observed_at"),
        (("candidates", 0), "proposed_at"),
        (("reviews", 0), "reviewed_at"),
        (("outcomes", 0), "observed_at"),
        (("datasets", 0), "frozen_at"),
        (("models", 0), "recorded_at"),
        ((), "recorded_at"),
    ],
)
def test_all_time_fields_require_bounded_rfc3339_utc(record_path, field):
    data = payload()
    target = data
    for part in record_path:
        target = target[part]
    target[field] = "not-a-timestamp"
    with pytest.raises(ValidationError, match="RFC3339 UTC"):
        LearningProvenanceBundleV0.model_validate(data)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-10-30T09:06:00+09:00",
        "2026-10-30T00:06:00",
        "2026-10-30T00:06:00.1234567Z",
        "2026-02-30T00:06:00Z",
    ],
)
def test_timestamp_profile_rejects_offsets_naive_precision_and_invalid_calendar(timestamp):
    data = payload()
    data["candidates"][0]["proposed_at"] = timestamp
    with pytest.raises(ValidationError):
        LearningProvenanceBundleV0.model_validate(data)


@pytest.mark.parametrize(
    "mutate,match",
    [
        (
            lambda d: d["snapshots"][0].update(
                as_of="2026-10-30T00:06:00Z",
                observed_at="2026-10-30T00:05:00Z",
            ),
            "snapshot.observed_at precedes its referenced record",
        ),
        (
            lambda d: d["reviews"][0].update(reviewed_at="2026-10-30T00:05:00Z"),
            "reviewed_at precedes its referenced record",
        ),
        (
            lambda d: d["datasets"][0].update(frozen_at="2026-10-30T00:09:00Z"),
            "dataset.frozen_at precedes its referenced record",
        ),
        (
            lambda d: d["models"][0].update(recorded_at="2026-10-30T00:11:00Z"),
            "model.recorded_at precedes its referenced record",
        ),
        (
            lambda d: d.update(recorded_at="2026-10-30T00:12:30Z"),
            "bundle.recorded_at precedes its referenced record",
        ),
    ],
)
def test_impossible_record_ordering_fails_closed(mutate, match):
    data = payload()
    mutate(data)
    with pytest.raises(ValidationError, match=match):
        LearningProvenanceBundleV0.model_validate(data)


def test_outcome_may_precede_teacher_proposal_without_implying_freshness():
    data = payload()
    data["outcomes"][0]["observed_at"] = "2026-10-30T00:04:00Z"
    assert LearningProvenanceBundleV0.model_validate(data).outcomes[0].observed_at == (
        "2026-10-30T00:04:00Z"
    )


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
