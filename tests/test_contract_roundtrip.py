"""Round-trip + deterministic-serialization property tests (Fabric#9).

Fabric#9 acceptance items: "deterministic serialization/content digest
stability" and "schema round-trip". For a representative instance of each major
contract family this asserts:

* **schema round-trip**: ``model_validate(model_dump(mode="json"))`` reproduces
  an equal model (no field lost or coerced across a JSON boundary);
* **deterministic serialization**: ``model_dump_json`` is byte-stable across
  repeated dumps and across a dump -> validate -> dump cycle, so a contract
  serialized on one host/process is byte-identical on another (portability
  baseline); and
* **content-digest stability** (where a contract carries a content digest): the
  digest recomputed after a JSON round-trip is unchanged.

Instances come from the shipped ``azazel_fabric.testing`` factories where they
exist (guaranteed-valid, and the same fixtures AZ-06/Edge/Knowledge consume),
plus minimal valid instances of the decision/engagement families.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from azazel_fabric.deception_contracts import EnvironmentTransitionDecision
from azazel_fabric.engagement_contracts import (
    EngagementAdvisory,
    EngagementCandidate,
    EngagementConstraint,
    EngagementTrigger,
    PostureSuggestion,
)
from azazel_fabric.deception_integrity import (
    catalog_content_digest,
    package_signing_payload,
)
from azazel_fabric.testing import (
    make_deception_host_capabilities,
    make_deception_package,
    make_deception_placement,
    make_effectiveness_advisory,
    make_interaction_observation,
    make_transition_catalog,
)


def _transition_decision() -> EnvironmentTransitionDecision:
    return EnvironmentTransitionDecision(
        decision_id="edge-decision-1", status="accepted", environment_id="env-1",
        current_state="baseline", target_state="smb-share-open",
        effective_at="2026-08-20T00:00:00+00:00", expires_at="2026-08-22T00:00:00+00:00",
    )


def _engagement_candidate() -> EngagementCandidate:
    return EngagementCandidate(
        candidate_id="cand-1", product="AZ-01", objective="collect", approach="channel",
        activity="redirect_to_decoy", attack_techniques=["T1110"],
        requested_actions=["redirect_to_decoy"],
        trigger=EngagementTrigger(attack_technique="T1110", confidence=0.9),
        constraints=EngagementConstraint(
            max_duration_seconds=300, outbound_allowed=False, production_access=False,
            termination_conditions=["noc_health_degraded"],
        ),
    )


def _engagement_advisory() -> EngagementAdvisory:
    return EngagementAdvisory(
        advisory_id="adv-1", advisor="azazel-knowledge", confidence=0.8,
        behavior_class="adaptive_probe",
        posture_suggestion=PostureSuggestion(
            objective="collect", approach="channel",
            supported_activities=["redirect_to_decoy"], reasons=["similar_pattern"],
        ),
        limitations=["intent unknown"],
    )


def _samples() -> list[BaseModel]:
    return [
        make_deception_package(),
        make_transition_catalog(),
        make_interaction_observation(),
        make_effectiveness_advisory(),
        make_deception_placement(),
        make_deception_host_capabilities(),
        _transition_decision(),
        _engagement_candidate(),
        _engagement_advisory(),
    ]


SAMPLES = _samples()


@pytest.mark.parametrize("model", SAMPLES, ids=lambda m: type(m).__name__)
def test_schema_round_trip_is_lossless(model: BaseModel):
    restored = type(model).model_validate(model.model_dump(mode="json"))
    assert restored == model


@pytest.mark.parametrize("model", SAMPLES, ids=lambda m: type(m).__name__)
def test_serialization_is_deterministic(model: BaseModel):
    first = model.model_dump_json()
    second = model.model_dump_json()
    assert first == second  # stable across repeated dumps
    # ...and stable across a dump -> validate -> dump cycle (portability).
    restored = type(model).model_validate(model.model_dump(mode="json"))
    assert restored.model_dump_json() == first


def test_package_digest_stable_across_round_trip():
    pkg = make_deception_package()
    from_pkg = package_signing_payload(pkg)
    restored = type(pkg).model_validate(pkg.model_dump(mode="json"))
    assert package_signing_payload(restored) == from_pkg


def test_catalog_content_digest_stable_across_round_trip():
    catalog = make_transition_catalog()
    before = catalog_content_digest(catalog)
    restored = type(catalog).model_validate(catalog.model_dump(mode="json"))
    assert catalog_content_digest(restored) == before
