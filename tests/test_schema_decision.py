"""Tests for DecisionExplanation, ActionIntent, and action plans."""

import pytest
from pydantic import ValidationError

from azazel_common.schema import (
    ActionIntent,
    DecisionExplanation,
    EvidenceRef,
    ObservePlan,
    ReleasePlan,
)


def _intent() -> ActionIntent:
    return ActionIntent(
        kind="isolate",
        target="10.0.0.5",
        issued_by="edge.arbiter",
        evidence=[
            EvidenceRef(
                evidence_id="ev-1",
                source="noc_evaluator",
                trace_id="trace-1",
                observed_at="2026-07-09T00:00:00Z",
            )
        ],
        trace_id="trace-1",
    )


def test_decision_explanation_round_trip():
    decision = DecisionExplanation(
        selected_action=_intent(),
        why_chosen="host matched isolation policy",
        why_not_others=["throttle: insufficient", "observe: too passive"],
        release_condition="no further beaconing for 30m",
        confidence=0.8,
        trace_id="trace-1",
    )
    restored = DecisionExplanation.model_validate(decision.model_dump())
    assert restored == decision
    assert restored.selected_action.kind == "isolate"
    assert restored.selected_action.evidence[0].source == "noc_evaluator"


def test_action_kind_rejects_unknown():
    with pytest.raises(ValidationError):
        ActionIntent(kind="detonate", target="x", issued_by="y", trace_id="t")


def test_confidence_bounds_enforced():
    with pytest.raises(ValidationError):
        DecisionExplanation(
            selected_action=_intent(),
            why_chosen="x",
            confidence=1.5,
            trace_id="t",
        )


def test_action_plans_are_data_only():
    # Plans fix their kind and carry only a loosely-typed parameters body.
    assert ObservePlan().kind == "observe"
    plan = ReleasePlan(parameters={"after": "30m"})
    assert plan.kind == "release"
    assert plan.parameters["after"] == "30m"
