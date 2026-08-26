from __future__ import annotations

import json
from pathlib import Path

from azazel_fabric.outcome_contracts import (
    ExecutionRefV0,
    MechanismObservationV0,
    OutcomeObservationV0,
    assert_evidence_chain_consistent,
    canonical_fact_json,
)


FIXTURES = Path(__file__).parent / "fixtures" / "outcome"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_cross_product_edge_to_deception_chain_validates_without_effect_claim():
    execution = ExecutionRefV0.model_validate(load("cross_product_redirect_execution_v0.json"))
    mechanism = MechanismObservationV0.model_validate(load("cross_product_redirection_mechanism_v0.json"))
    outcome = OutcomeObservationV0.model_validate(load("cross_product_presented_terrain_outcome_v0.json"))

    assert_evidence_chain_consistent(execution, mechanism, outcomes=(outcome,))
    assert mechanism.mechanism_kind == "redirection"
    assert outcome.producer_product == "azazel-deception"
    encoded = canonical_fact_json(outcome).lower()
    assert "tactical_effect" not in encoded
    assert "effect_class" not in encoded
    assert "attacker_belief" not in encoded
    assert '"success"' not in encoded


def test_cross_product_fixture_ids_are_one_chain_not_cross_trace_join():
    execution = ExecutionRefV0.model_validate(load("cross_product_redirect_execution_v0.json"))
    mechanism = MechanismObservationV0.model_validate(load("cross_product_redirection_mechanism_v0.json"))
    outcome = OutcomeObservationV0.model_validate(load("cross_product_presented_terrain_outcome_v0.json"))
    assert (execution.trace_id, execution.decision_ref, execution.execution_ref) == (
        mechanism.trace_id,
        mechanism.decision_ref,
        mechanism.execution_ref,
    ) == (outcome.trace_id, outcome.decision_ref, outcome.execution_ref)
    assert outcome.mechanism_observation_ref == mechanism.observation_id
