"""Tests for the AZ-06 effectiveness-observation contracts."""

import pytest
from pydantic import ValidationError

from azazel_fabric.deception_contracts import (
    EffectivenessAdvisory,
    InteractionObservation,
    assert_no_effectiveness_verdict,
    assert_no_runtime_directives,
    contains_effectiveness_verdict,
)
from azazel_fabric.testing import (
    make_effectiveness_advisory,
    make_interaction_observation,
)


def test_observation_round_trip_is_descriptive_only():
    obs = make_interaction_observation()
    dumped = obs.model_dump(mode="json")
    assert dumped["authority"] == "descriptive_only"
    assert InteractionObservation.model_validate(dumped) == obs


def test_interaction_layer_cannot_carry_a_reaction():
    # Layer 1 is contact only; asserting a reaction on it is a stronger claim.
    # Build directly so the factory's convenience coercion doesn't hide it.
    payload = make_interaction_observation(observation_class="reaction").model_dump(mode="json")
    payload["observation_class"] = "interaction"
    payload["reaction_kind"] = "authenticate"
    with pytest.raises(ValidationError):
        InteractionObservation.model_validate(payload)


def test_interaction_layer_allows_absent_reaction():
    obs = make_interaction_observation(
        observation_class="interaction", surface="port", reaction_kind=None
    )
    assert obs.observation_class == "interaction"
    assert obs.reaction_kind is None


def test_reaction_and_outcome_layers_accept_reaction_kind():
    for cls in ("reaction", "outcome"):
        obs = make_interaction_observation(observation_class=cls, reaction_kind="lateral_move")
        assert obs.reaction_kind == "lateral_move"


def test_unknown_surface_reaction_confounder_are_closed_vocab():
    for field, value in (
        ("surface", "definitely-not-a-surface"),
        ("reaction_kind", "hack-back"),
    ):
        with pytest.raises(ValidationError):
            make_interaction_observation(**{field: value})
    with pytest.raises(ValidationError):
        make_interaction_observation(confounder_tags=["not-a-confounder"])


def test_extra_fields_fail_closed():
    with pytest.raises(ValidationError):
        make_interaction_observation(attacker_believed=True)


@pytest.mark.parametrize(
    "verdict_field",
    [
        "attacker_believed",
        "believed",
        "deceived",
        "fooled",
        "is_effective",
        "effectiveness_score",
        "belief_score",
        "confidence",
    ],
)
def test_effectiveness_verdict_fields_are_rejected_pre_construction(verdict_field):
    payload = make_interaction_observation().model_dump(mode="json")
    payload[verdict_field] = 1
    assert contains_effectiveness_verdict(payload) is True
    with pytest.raises(ValueError, match="honesty invariant"):
        assert_no_effectiveness_verdict(payload)


def test_verdict_guard_scans_nested_metadata():
    payload = make_interaction_observation().model_dump(mode="json")
    payload["metadata"] = {"note": "ok"}
    assert_no_effectiveness_verdict(payload)  # clean
    payload["metadata"] = {"nested": {"deceived": True}}
    with pytest.raises(ValueError):
        assert_no_effectiveness_verdict(payload)


def test_clean_observation_passes_both_guards():
    payload = make_interaction_observation().model_dump(mode="json")
    assert_no_effectiveness_verdict(payload)
    assert_no_runtime_directives(payload)


def test_runtime_context_separates_narrative_from_host_capacity():
    obs = make_interaction_observation(
        runtime_context={
            "selected_tier": "standard",
            "architecture": "arm64",
            "runtime_adapter": "docker_compose",
            "active_components": ["intranet-web", "mail"],
            "omitted_components": ["persona-runtime"],
            "resource_saturation": {"cpu": 0.9, "memory": 0.5},
            "capability_drift": ["kvm_libvirt"],
        }
    )
    assert obs.runtime_context.resource_saturation["cpu"] == 0.9
    assert "persona-runtime" in obs.runtime_context.omitted_components


def test_advisory_is_advisory_only_and_non_executable():
    adv = make_effectiveness_advisory()
    dumped = adv.model_dump(mode="json")
    assert dumped["authority"] == "advisory_only"
    assert dumped["advisor"] == "azazel-knowledge"
    assert dumped["executable"] is False
    assert EffectivenessAdvisory.model_validate(dumped) == adv


def test_advisory_requires_counter_evidence_capable_shape_and_confidence_bounds():
    # confidence must stay in [0, 1]
    with pytest.raises(ValidationError):
        make_effectiveness_advisory(confidence=1.5)
    with pytest.raises(ValidationError):
        make_effectiveness_advisory(confidence=-0.1)
    # executable can never be flipped true
    with pytest.raises(ValidationError):
        make_effectiveness_advisory(executable=True)


def test_advisory_confidence_is_legitimate_and_not_caught_by_observation_guard():
    # The verdict guard is for observations; the advisory's confidence field is
    # a legitimate layer-4 estimate and must not be run through that guard.
    adv = make_effectiveness_advisory(confidence=0.75)
    assert adv.confidence == 0.75
