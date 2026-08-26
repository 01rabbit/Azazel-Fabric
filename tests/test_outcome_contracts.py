from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from azazel_fabric.outcome_contracts import (
    ExecutionRefV0,
    MechanismObservationV0,
    OutcomeObservationV0,
    TacticalEffectAssessmentRefV0,
    assert_evidence_chain_consistent,
    canonical_fact_json,
)


def execution(**overrides):
    data = {
        "producer_product": "azazel-edge",
        "producer_node": "edge-1",
        "trace_id": "trace-1",
        "decision_ref": "decision-1",
        "execution_ref": "execution-1",
        "action": "throttle",
        "status": "applied",
        "observed_at": "2026-08-26T00:00:00Z",
        "evidence_refs": ["rust:event:1"],
    }
    data.update(overrides)
    return ExecutionRefV0(**data)


def mechanism(**overrides):
    data = {
        "observation_id": "mechanism-1",
        "producer_product": "azazel-edge",
        "producer_node": "edge-1",
        "trace_id": "trace-1",
        "decision_ref": "decision-1",
        "execution_ref": "execution-1",
        "mechanism_kind": "traffic_shaping",
        "status": "observed",
        "observed_parameters": {"rate": "256kbit", "burst_bytes": 4096},
        "observed_at": "2026-08-26T00:00:01Z",
        "evidence_refs": ["tc:qdisc:1"],
    }
    data.update(overrides)
    return MechanismObservationV0(**data)


def outcome(**overrides):
    data = {
        "observation_id": "outcome-1",
        "producer_product": "azazel-edge",
        "producer_node": "edge-1",
        "trace_id": "trace-1",
        "decision_ref": "decision-1",
        "execution_ref": "execution-1",
        "mechanism_observation_ref": "mechanism-1",
        "subject_ref": "src-ip:198.51.100.9",
        "window_start": "2026-08-25T23:59:30Z",
        "window_end": "2026-08-26T00:00:30Z",
        "phase": "after",
        "observation_class": "network_activity",
        "observation_values": {"source_ip_event_count": 4, "source_ip_event_rate_hz": 0.13},
        "telemetry_coverage": {"sample_ratio": 1.0},
        "confounders": ["source_ip_is_not_actor_identity"],
        "resource_impact": {"load1_mean": 0.42},
        "evidence_refs": ["outcome:window:1"],
        "observed_at": "2026-08-26T00:00:30Z",
    }
    data.update(overrides)
    return OutcomeObservationV0(**data)


def assessment(**overrides):
    data = {
        "assessment_id": "assessment-1",
        "producer_product": "azazel-edge",
        "producer_node": "edge-1",
        "trace_id": "trace-1",
        "decision_ref": "decision-1",
        "execution_ref": "execution-1",
        "mechanism_observation_ref": "mechanism-1",
        "outcome_observation_refs": ["outcome-1"],
        "tactical_effect": "delay",
        "assessment": "inconclusive",
        "evaluator": "azazel-edge:effect-assessor/v1",
        "policy_ref": "policy:research-1",
        "evidence_refs": ["outcome:window:1"],
        "limitations": ["causal_support_inconclusive"],
        "observed_at": "2026-08-26T00:00:31Z",
    }
    data.update(overrides)
    return TacticalEffectAssessmentRefV0(**data)


def test_complete_chain_is_non_executable_and_consistent():
    e = execution()
    m = mechanism()
    o = outcome()
    a = assessment()
    assert_evidence_chain_consistent(e, m, [o], a)
    assert a.executable is False
    assert m.mechanism_kind == "traffic_shaping"
    assert a.tactical_effect == "delay"
    assert a.assessment == "inconclusive"


def test_execution_has_no_effect_class_or_provider_command_surface():
    payload = execution().model_dump()
    assert "effect_class" not in payload
    assert "command" not in payload
    assert "provider_command" not in payload


@pytest.mark.parametrize(
    "field,value",
    [
        ("success", True),
        ("execute", True),
        ("provider_command", "tc qdisc replace ..."),
        ("attacker_belief", "fooled"),
        ("model_recommendation", "delay"),
        ("select_action", "isolate"),
    ],
)
def test_nested_authority_or_overclaim_fields_are_rejected(field, value):
    with pytest.raises((ValueError, ValidationError)):
        outcome(observation_values={"nested": {field: value}})


def test_unknown_schema_fails_closed():
    payload = execution().model_dump()
    payload["schema_version"] = "outcome-execution/v9"
    with pytest.raises(ValidationError):
        ExecutionRefV0.model_validate(payload)


def test_unknown_mechanism_does_not_upgrade_to_tactical_effect():
    m = mechanism(mechanism_kind="unknown", status="unverified")
    assert m.mechanism_kind == "unknown"
    assert "tactical_effect" not in m.model_dump()


def test_cross_trace_join_is_rejected():
    with pytest.raises(ValueError, match="outcome does not belong"):
        assert_evidence_chain_consistent(execution(), mechanism(), [outcome(trace_id="other")])


def test_cross_mechanism_join_is_rejected():
    with pytest.raises(ValueError, match="different mechanism"):
        assert_evidence_chain_consistent(
            execution(), mechanism(), [outcome(mechanism_observation_ref="other")]
        )


def test_assessment_cannot_reference_unsupplied_outcome():
    with pytest.raises(ValueError, match="outside the supplied evidence chain"):
        assert_evidence_chain_consistent(
            execution(), mechanism(), [outcome()], assessment(outcome_observation_refs=["other"])
        )


def test_payload_bounds_fail_closed():
    with pytest.raises(ValueError, match="map exceeds"):
        outcome(observation_values={f"k{i}": i for i in range(65)})
    with pytest.raises(ValueError, match="oversized string"):
        outcome(observation_values={"message": "x" * 2049})


def test_extra_fields_fail_closed():
    payload = outcome().model_dump()
    payload["effect_class"] = "DELAY"
    with pytest.raises(ValidationError):
        OutcomeObservationV0.model_validate(payload)


def test_canonical_serialization_is_byte_stable():
    one = canonical_fact_json(outcome())
    two = canonical_fact_json(OutcomeObservationV0.model_validate(json.loads(one)))
    assert one == two
