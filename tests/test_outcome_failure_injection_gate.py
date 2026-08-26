from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from azazel_fabric.outcome_contracts import (
    ExecutionRefV0,
    MechanismObservationV0,
    OutcomeObservationV0,
    assert_evidence_chain_consistent,
    assert_no_runtime_directives,
)
from azazel_fabric.outcome_contracts.validation import assert_no_tactical_claim_fields


FIXTURES = Path(__file__).parent / "fixtures" / "outcome"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def validated_chain():
    return (
        ExecutionRefV0.model_validate(load("cross_product_redirect_execution_v0.json")),
        MechanismObservationV0.model_validate(load("cross_product_redirection_mechanism_v0.json")),
        OutcomeObservationV0.model_validate(load("cross_product_presented_terrain_outcome_v0.json")),
    )


def test_cross_trace_outcome_join_fails_closed():
    execution, mechanism, _ = validated_chain()
    mutated = load("cross_product_presented_terrain_outcome_v0.json")
    mutated["trace_id"] = "trace-poisoned"
    outcome = OutcomeObservationV0.model_validate(mutated)
    with pytest.raises(ValueError, match="does not belong"):
        assert_evidence_chain_consistent(execution, mechanism, outcomes=(outcome,))


def test_wrong_mechanism_reference_fails_closed():
    execution, mechanism, _ = validated_chain()
    mutated = load("cross_product_presented_terrain_outcome_v0.json")
    mutated["mechanism_observation_ref"] = "mechanism-other"
    outcome = OutcomeObservationV0.model_validate(mutated)
    with pytest.raises(ValueError, match="different mechanism"):
        assert_evidence_chain_consistent(execution, mechanism, outcomes=(outcome,))


def test_tactical_effect_cannot_be_smuggled_into_descriptive_outcome_fact():
    mutated = copy.deepcopy(load("cross_product_presented_terrain_outcome_v0.json"))
    mutated["observation_values"]["nested"] = {"tactical-effect": "divert"}
    with pytest.raises(ValueError, match="tactical claim"):
        assert_no_tactical_claim_fields(mutated["observation_values"])


def test_runtime_command_cannot_be_smuggled_into_shared_fact():
    mutated = copy.deepcopy(load("cross_product_presented_terrain_outcome_v0.json"))
    mutated["resource_impact"]["provider-command"] = "do-not-execute"
    with pytest.raises(ValueError, match="runtime/authority"):
        assert_no_runtime_directives(mutated)


def test_clean_golden_chain_still_passes_after_failure_injection_cases():
    execution, mechanism, outcome = validated_chain()
    assert_evidence_chain_consistent(execution, mechanism, outcomes=(outcome,))
