"""Fabric#15: the published cross-product chain is byte-stable and replayable.

The vectors exist so Edge, Gadget, Knowledge and AZ-06 test against the same
bytes Fabric ships. That is only worth anything if the bytes do not move and
if a consumer can rebuild the models from them, so both are asserted here
rather than assumed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from azazel_fabric.effect_contracts import (
    AuthorityClass,
    DefensiveEffectRef,
    EffectObservation,
    OutcomeObservationEnvelope,
    PresentedTerrainRef,
    ReplayProvenance,
    assert_effect_chain_consistent,
    assert_observation_within_effect_window,
    is_authoritative_decision_reference,
)
from azazel_fabric.testing.effect import (
    GOLDEN_EFFECT_VECTORS,
    golden_advisory_effect_ref,
    golden_deception_effect_observation,
    golden_deception_presented_terrain,
    golden_edge_effect_ref,
    golden_gadget_effect_observation,
    golden_knowledge_outcome_envelope,
    golden_replay_provenance,
)

FIXTURES = Path(__file__).parent / "fixtures" / "effect"

MODEL_FOR_FIXTURE = {
    "effect_edge_defensive_effect_ref_v0.json": DefensiveEffectRef,
    "effect_knowledge_advisory_ref_v0.json": DefensiveEffectRef,
    "effect_deception_presented_terrain_v0.json": PresentedTerrainRef,
    "effect_deception_observation_v0.json": EffectObservation,
    "effect_gadget_observation_v0.json": EffectObservation,
    "effect_knowledge_outcome_envelope_v0.json": OutcomeObservationEnvelope,
}


def _canonical_sha256(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_every_published_vector_has_a_fixture_file_and_a_model():
    assert set(GOLDEN_EFFECT_VECTORS) == set(MODEL_FOR_FIXTURE)
    for name in GOLDEN_EFFECT_VECTORS:
        assert (FIXTURES / name).is_file(), f"published vector without a fixture: {name}"


def test_the_manifest_matches_every_fixture_byte_for_byte():
    manifest = json.loads((FIXTURES / "effect_manifest_v0.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "effect-golden-manifest/v0.1"
    assert set(manifest["canonical_sha256"]) == set(GOLDEN_EFFECT_VECTORS)
    for name, digest in manifest["canonical_sha256"].items():
        stored = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        assert _canonical_sha256(stored) == digest, f"fixture drifted from manifest: {name}"


@pytest.mark.parametrize("name", sorted(GOLDEN_EFFECT_VECTORS))
def test_the_builder_still_produces_the_bytes_on_disk(name):
    """The fixture is the contract; the builder must not drift away from it."""
    assert GOLDEN_EFFECT_VECTORS[name]() == json.loads(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("name", sorted(MODEL_FOR_FIXTURE))
def test_a_consumer_can_rebuild_the_model_from_the_fixture(name):
    model = MODEL_FOR_FIXTURE[name]
    stored = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert model.model_validate(stored).model_dump(mode="json") == stored


@pytest.mark.parametrize("name", sorted(GOLDEN_EFFECT_VECTORS))
def test_a_vector_is_deterministic_across_calls(name):
    """No wall-clock, no randomness -- otherwise cross-repo comparison is noise."""
    factory = GOLDEN_EFFECT_VECTORS[name]
    assert factory() == factory()


def test_the_published_chain_correlates_end_to_end():
    ref = DefensiveEffectRef.model_validate(golden_edge_effect_ref())
    deception = EffectObservation.model_validate(golden_deception_effect_observation())
    gadget = EffectObservation.model_validate(golden_gadget_effect_observation())
    presented = PresentedTerrainRef.model_validate(golden_deception_presented_terrain())
    envelope = OutcomeObservationEnvelope.model_validate(golden_knowledge_outcome_envelope())

    assert_effect_chain_consistent(ref, [deception, gadget], envelope, presented)
    assert_observation_within_effect_window(ref, deception)
    assert_observation_within_effect_window(ref, gadget)


def test_the_advisory_vector_is_distinguishable_from_the_decision_vector():
    """Both describe the same trace. Only one is a decision, and a consumer
    that cannot tell them apart has an authority bug this vector exposes."""
    authoritative = DefensiveEffectRef.model_validate(golden_edge_effect_ref())
    advisory = DefensiveEffectRef.model_validate(golden_advisory_effect_ref())

    assert authoritative.trace_id == advisory.trace_id
    assert is_authoritative_decision_reference(authoritative.authority_class) is True
    assert is_authoritative_decision_reference(advisory.authority_class) is False
    assert advisory.decision_ref is None
    assert authoritative.advisory_ref is None


def test_the_published_envelope_states_its_telemetry_gap():
    """A golden vector that claimed perfect coverage would teach consumers the
    wrong shape. The realistic case is partial coverage, named."""
    envelope = OutcomeObservationEnvelope.model_validate(golden_knowledge_outcome_envelope())
    assert envelope.coverage_complete is False
    assert envelope.telemetry_gaps
    assert envelope.authority_class is AuthorityClass.OBSERVED_FACT


def test_the_published_provenance_confers_nothing():
    provenance = ReplayProvenance.model_validate(golden_replay_provenance())
    assert provenance.confers_authority is False
    assert provenance.model_ref is not None
