"""Contract tests for the MITRE Engage-aligned engagement family (Fabric#8)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from azazel_fabric.engagement_contracts import (
    ADVISORY_NOTICE,
    EngagementAdvisory,
    EngagementCandidate,
    EngagementConstraint,
    EngagementEvent,
    EngagementOutcome,
    EngagementTrigger,
    PostureSuggestion,
    assert_candidate_not_executable,
    assert_engagement_advisory_only,
    assert_no_engagement_directives,
)


def _constraint() -> EngagementConstraint:
    return EngagementConstraint(
        max_duration_seconds=300,
        outbound_allowed=False,
        production_access=False,
        termination_conditions=["noc_health_degraded"],
    )


def _candidate(**over) -> EngagementCandidate:
    base = dict(
        candidate_id="cand-1",
        product="AZ-01",
        objective="collect",
        approach="channel",
        activity="redirect_to_decoy",
        attack_techniques=["T1110"],
        requested_actions=["redirect", "redirect_to_decoy"],
        constraints=_constraint(),
    )
    base.update(over)
    return EngagementCandidate(**base)


def _advisory(**over) -> EngagementAdvisory:
    base = dict(
        advisory_id="adv-1",
        advisor="azazel-knowledge",
        confidence=0.84,
        behavior_class="adaptive_probe",
        posture_suggestion=PostureSuggestion(
            objective="collect", approach="channel",
            supported_activities=["redirect_to_decoy"],
            reasons=["similar_patterns_previously_engaged_decoy"],
        ),
        limitations=["attacker intent unknown"],
    )
    base.update(over)
    return EngagementAdvisory(**base)


# -- shape + defaults --------------------------------------------------------

def test_candidate_defaults_to_candidate_only_authority():
    c = _candidate()
    assert c.authority == "candidate_only"
    assert c.schema_version == "engagement-candidate/v0.1"
    assert c.constraints.outbound_allowed is False
    assert c.constraints.production_access is False


def test_advisory_is_advisory_only_and_non_executable():
    a = _advisory()
    assert a.authority == "advisory_only"
    assert a.executable is False
    assert a.advisory_notice == ADVISORY_NOTICE
    assert a.limitations  # always carried


def test_event_round_trips_with_outcome():
    ev = EngagementEvent(
        event_id="ev-1", product="AZ-01", objective="collect", approach="channel",
        activity="redirect_to_decoy",
        trigger=EngagementTrigger(attack_technique="T1110", confidence=0.91),
        constraints=_constraint(),
        outcome=EngagementOutcome(attacker_reaction="decoy_engaged", reaction_window_s=42),
    )
    again = EngagementEvent.model_validate(ev.model_dump(mode="json"))
    assert again == ev


# -- fail-closed enums / versions -------------------------------------------

def test_unknown_activity_fails_closed():
    with pytest.raises(ValidationError):
        _candidate(activity="exfiltrate_production")


def test_unknown_reaction_fails_closed():
    with pytest.raises(ValidationError):
        EngagementOutcome(attacker_reaction="mind_controlled")


def test_confidence_bounds_enforced():
    with pytest.raises(ValidationError):
        EngagementTrigger(confidence=1.5)


# -- authority invariants ----------------------------------------------------

def test_extra_fields_forbidden_on_candidate_and_advisory():
    with pytest.raises(ValidationError):
        EngagementCandidate(
            candidate_id="x", product="AZ-01", objective="collect", approach="channel",
            activity="observe", constraints=_constraint(), execute_now=True,
        )
    with pytest.raises(ValidationError):
        _advisory(force_action="isolate")


def test_advisory_cannot_be_executable():
    with pytest.raises(ValidationError):
        _advisory(executable=True)


def test_directive_scan_rejects_smuggled_execution_field():
    payload = {
        "candidate_id": "c", "product": "AZ-01", "objective": "collect",
        "approach": "channel", "activity": "isolate",
        "constraints": {"max_duration_seconds": 60, "firewall_rule": "drop all"},
    }
    with pytest.raises(ValueError):
        assert_no_engagement_directives(payload)


def test_assert_candidate_not_executable_accepts_clean_and_rejects_authority():
    assert_candidate_not_executable(_candidate())  # clean
    with pytest.raises(ValueError):
        assert_candidate_not_executable(
            {"authority": "arbiter", "activity": "isolate"}
        )
    with pytest.raises(ValueError):
        assert_candidate_not_executable({"selected_action": "isolate"})


def test_assert_advisory_only_accepts_clean_and_rejects_executable():
    assert_engagement_advisory_only(_advisory())  # clean
    with pytest.raises(ValueError):
        assert_engagement_advisory_only({"authority": "advisory_only", "executable": True})
    with pytest.raises(ValueError):
        assert_engagement_advisory_only({"authority": "final"})
