"""Fabric#72: objective / hypothesis / frame refs on the outcome envelope.

An objective says what an observation was *for*. It is non-executable and does
not stand in for an Edge decision. These tests pin the additive shape, the
per-slot kind checks, and that a payload from before the fields existed still
validates and serializes to the same bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from azazel_fabric.effect_contracts import (
    AuthorityClass,
    OutcomeObservationEnvelope,
    RefKind,
    parse_ref,
)
from azazel_fabric.testing.effect import (
    golden_knowledge_objective_envelope,
    golden_knowledge_outcome_envelope,
)

FIXTURES = Path(__file__).parent / "fixtures" / "effect"
NEW_FIELDS = ("observation_objective_ref", "hypothesis_refs", "frame_ref", "limitations")


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_the_new_ref_kinds_exist_and_existing_kinds_are_untouched():
    assert RefKind.OBSERVATION_OBJECTIVE.value == "observation_objective"
    assert RefKind.HYPOTHESIS.value == "hypothesis"
    assert RefKind.FRAME.value == "frame"
    assert parse_ref("observation_objective:o1")[0] is RefKind.OBSERVATION_OBJECTIVE
    assert parse_ref("advisory:o1")[0] is RefKind.ADVISORY
    assert parse_ref("decision:d1")[0] is RefKind.DECISION


def test_an_rc5_payload_still_validates_and_round_trips_byte_for_byte():
    """The published rc5 envelope has none of the new keys and must stay exact."""
    stored = _load("effect_knowledge_outcome_envelope_v0.json")
    assert not set(NEW_FIELDS) & set(stored)
    model = OutcomeObservationEnvelope.model_validate(stored)
    assert model.observation_objective_ref is None
    assert model.frame_ref is None
    assert model.hypothesis_refs == ()
    assert model.limitations == ()
    assert model.model_dump(mode="json") == stored
    assert golden_knowledge_outcome_envelope() == stored


def test_the_new_fields_default_to_empty_and_are_omitted_from_a_dump():
    dumped = OutcomeObservationEnvelope.model_validate(
        _load("effect_knowledge_outcome_envelope_v0.json")
    ).model_dump(mode="json")
    for name in NEW_FIELDS:
        assert name not in dumped


def test_the_objective_vector_round_trips_with_every_new_field_present():
    stored = _load("effect_knowledge_objective_envelope_v0.json")
    assert set(NEW_FIELDS) <= set(stored)
    model = OutcomeObservationEnvelope.model_validate(stored)
    assert model.model_dump(mode="json") == stored
    assert golden_knowledge_objective_envelope() == stored


def test_an_objective_does_not_replace_the_decision_reference():
    model = OutcomeObservationEnvelope.model_validate(
        _load("effect_knowledge_objective_envelope_v0.json")
    )
    assert model.decision_ref == "decision-golden-effect-1"
    assert model.authority_class is AuthorityClass.OBSERVED_FACT


def _apply(base: dict, case: dict) -> dict:
    payload = json.loads(json.dumps(base))
    changes = dict(case["set"])
    repeat = changes.pop("__repeat_limitations", None)
    payload.update(changes)
    if repeat is not None:
        payload["limitations"] = [f"limit_{i}" for i in range(repeat)]
    return payload


_REJECTIONS = _load("effect_objective_envelope_rejections_v0.json")


def test_the_rejection_fixture_names_a_base_that_is_valid_as_published():
    OutcomeObservationEnvelope.model_validate(_load(_REJECTIONS["base"]))


@pytest.mark.parametrize("case", _REJECTIONS["cases"], ids=lambda c: c["name"])
def test_every_rejection_fixture_is_refused(case):
    with pytest.raises(ValidationError):
        OutcomeObservationEnvelope.model_validate(_apply(_load(_REJECTIONS["base"]), case))


def test_an_observed_fact_without_a_decision_is_allowed_with_an_objective():
    """The objective is context, not authority: observing without a decision is fine."""
    payload = _load("effect_knowledge_objective_envelope_v0.json")
    payload["decision_ref"] = None
    assert OutcomeObservationEnvelope.model_validate(payload).decision_ref is None


def test_planned_shadow_without_a_decision_is_allowed_with_an_objective():
    payload = _load("effect_knowledge_objective_envelope_v0.json")
    payload["decision_ref"] = None
    payload["authority_class"] = "planned_shadow"
    OutcomeObservationEnvelope.model_validate(payload)


def test_a_producer_decision_claim_is_refused_with_or_without_an_objective():
    """Already refused before rc6; pinned here so the objective cannot loosen it."""
    for with_objective in (True, False):
        payload = _load("effect_knowledge_objective_envelope_v0.json")
        if not with_objective:
            for name in NEW_FIELDS:
                payload.pop(name)
        payload["authority_class"] = "producer_decision_ref"
        with pytest.raises(ValidationError):
            OutcomeObservationEnvelope.model_validate(payload)


def test_the_limitations_bound_matches_effect_observation():
    from azazel_fabric.effect_contracts import EffectObservation

    assert (
        OutcomeObservationEnvelope.model_fields["limitations"].metadata[0].max_length
        == EffectObservation.model_fields["limitations"].metadata[0].max_length
    )


#: Tokens Azazel-Deception actually emits (convention C2). All must pass.
DECEPTION_LIMITATION_TOKENS = (
    "objective_content_not_bound",
    "objective_trace_differs_from_effect_trace",
    "objective_not_supplied",
    "desired_observations_not_hypothesis_specific",
    "desired_observations_not_specified",
    "no_interaction_observed_is_not_evidence_of_safety",
    "telemetry_gap:http_access_log",
    "stale",
    "lease_expired",
    "runtime_active_after_lease_end",
    "redirection_does_not_imply_diversion",
    "isolation_drift_observed",
    "isolation_not_asserted",
    "interactions_truncated",
    "unbound_interactions_excluded:3",
    "interactions_outside_lease:2",
    "runtime_state_not_independently_reverified",
    "session_ended_new_observations_belong_to_a_new_session",
    "presented_terrain_not_projected",
)


@pytest.mark.parametrize("token", DECEPTION_LIMITATION_TOKENS)
def test_every_token_deception_emits_is_accepted(token):
    payload = _load("effect_knowledge_objective_envelope_v0.json")
    payload["limitations"] = [token]
    assert OutcomeObservationEnvelope.model_validate(payload).limitations == (token,)


def test_existing_effect_observation_limitations_are_not_tightened():
    from azazel_fabric.effect_contracts import EffectObservation

    payload = json.loads(
        (FIXTURES / "effect_gadget_observation_v0.json").read_text(encoding="utf-8")
    )
    payload["limitations"] = ["Free text with spaces / slashes"]
    assert EffectObservation.model_validate(payload).limitations


@pytest.mark.parametrize("kind", ["observation_objective", "hypothesis", "frame"])
def test_an_advisory_kind_cannot_fill_a_decision_or_trace_slot(kind):
    from azazel_fabric.effect_contracts import DefensiveEffectRef, EffectClass
    from tests.test_effect_contracts import effect_ref  # noqa: F401  (builder)

    with pytest.raises(ValidationError):
        DefensiveEffectRef.model_validate(
            {
                **effect_ref().model_dump(mode="json"),
                "authority_class": "producer_decision_ref",
                "decision_ref": f"{kind}:x",
            }
        )
    with pytest.raises(ValidationError):
        DefensiveEffectRef.model_validate(
            {**effect_ref().model_dump(mode="json"), "trace_id": f"{kind}:x"}
        )
    assert EffectClass  # imported for the model's enum validation only


def test_the_imperative_set_has_the_35_agreed_words_including_the_r2_additions():
    from azazel_fabric.effect_contracts import COMMAND_SEGMENTS

    assert len(COMMAND_SEGMENTS) == 35
    assert {"override", "enforce", "grant", "granted", "bypass"} <= COMMAND_SEGMENTS


@pytest.mark.parametrize("word", ["override", "enforce", "grant", "granted", "bypass"])
def test_the_r2_words_are_refused_in_limitations_and_ref_bodies(word):
    payload = _load("effect_knowledge_objective_envelope_v0.json")
    with pytest.raises(ValidationError):
        OutcomeObservationEnvelope.model_validate({**payload, "limitations": [f"x_{word}_now"]})
    with pytest.raises(ValidationError):
        OutcomeObservationEnvelope.model_validate(
            {**payload, "observation_objective_ref": f"observation_objective:o.{word.upper()}"}
        )


def test_whole_segments_only_for_the_r2_words():
    payload = _load("effect_knowledge_objective_envelope_v0.json")
    payload["limitations"] = ["overridden_by_nothing", "enforcement_not_observed", "bypassed_not_seen"]
    assert OutcomeObservationEnvelope.model_validate(payload)


def test_existing_telemetry_gaps_and_confounders_validation_is_unchanged():
    """C2': Fabric does not tighten the rc5 fields (non-additive)."""
    payload = _load("effect_knowledge_outcome_envelope_v0.json")
    payload["telemetry_gaps"] = ["Free text / with: odd chars"]
    payload["confounders"] = ["Run now"]
    assert OutcomeObservationEnvelope.model_validate(payload)
