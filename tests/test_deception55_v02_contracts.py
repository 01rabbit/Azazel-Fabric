"""PROPOSAL tests: Deception #55 v0.2 observation binding (not adopted)."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from azazel_fabric.deception_contracts import (
    EnvironmentActivationDecision,
    EnvironmentActivationDecisionV02,
    InteractionObservation,
    InteractionObservationV02,
    ObservationBindingError,
    check_observation_binding,
    parse_activation_decision,
    parse_activation_decision_v02,
    parse_interaction_observation,
    parse_interaction_observation_v02,
    sign_decision,
    verify_decision_signature,
)
from azazel_fabric.effect_contracts import RefKind
from azazel_fabric.effect_contracts.refs import OPAQUE_REF_PATTERN
from azazel_fabric.testing import make_interaction_observation

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
KEY = "unit-test-key"


def _decision(**over):
    data = {
        "decision_id": "decision:d-1", "status": "accepted", "package_id": "pkg",
        "package_digest": "sha256:" + "a" * 64, "target_node_id": "n1",
        "selected_tier": "lite",
        "budget": {"cpu_cores": 1, "memory_mb": 256, "storage_mb": 256, "bandwidth_kbps": 100},
        "effective_at": NOW.isoformat(), "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "schema_version": "environment-activation-decision/v0.2",
        "environment_id": "environment:env-1", "trace_id": "trace:t-1",
        "observation_objective_ref": "observation_objective:obj-1", "frame_ref": "frame:f-1",
        "hypothesis_refs": ["hypothesis:h-1"], "lease_ref": "lease:l-1",
        "lease_expires_at": (NOW + timedelta(minutes=3)).isoformat(),
    }
    data.update(over)
    return data


def _obs(**over):
    data = {
        "schema_version": "interaction-observation/v0.2",
        "observation_id": "obs-1", "environment_id": "environment:env-1",
        "package_id": "pkg", "node_id": "n1",
        "observed_at": (NOW + timedelta(minutes=1)).isoformat(),
        "observation_class": "reaction", "surface": "credential_lure",
        "reaction_kind": "authenticate", "lure_ref": "artifact:lure-1",
        "evidence_refs": ["evidence:e-1"],
        "decision_ref": "decision:d-1", "trace_id": "trace:t-1",
        "observation_objective_ref": "observation_objective:obj-1", "frame_ref": "frame:f-1",
        "hypothesis_refs": ["hypothesis:h-1"], "lease_ref": "lease:l-1",
        "session_ref": "session:gen3-a1b2",
    }
    data.update(over)
    return data


def _bound():
    return (parse_interaction_observation_v02(_obs()), parse_activation_decision_v02(_decision()))


# ---- ref reuse ----

def test_new_ref_kinds_extend_shared_enum_only():
    assert {RefKind.FRAME.value, RefKind.HYPOTHESIS.value, RefKind.LEASE.value,
            RefKind.OBSERVATION_OBJECTIVE.value} == {
        "frame", "hypothesis", "lease", "observation_objective"}
    assert OPAQUE_REF_PATTERN.pattern.startswith("^(?P<kind>")


# ---- v0.2 models ----

def test_v02_valid_roundtrip_and_distinct_types():
    o, d = _bound()
    assert InteractionObservationV02.model_validate(o.model_dump(mode="json")) == o
    assert not isinstance(o, InteractionObservation) and not isinstance(d, EnvironmentActivationDecision)
    assert "metadata" not in InteractionObservationV02.model_fields
    assert "lure_id" not in InteractionObservationV02.model_fields


@pytest.mark.parametrize("field", [
    "environment_id", "trace_id", "observation_objective_ref", "frame_ref", "hypothesis_refs",
    "lease_ref", "lease_expires_at"])
def test_decision_binding_fields_required(field):
    data = _decision()
    del data[field]
    with pytest.raises(ValidationError):
        EnvironmentActivationDecisionV02.model_validate(data)


@pytest.mark.parametrize("field", [
    "decision_ref", "trace_id", "observation_objective_ref", "frame_ref", "hypothesis_refs",
    "lease_ref", "session_ref", "environment_id"])
def test_observation_binding_fields_required(field):
    data = _obs()
    del data[field]
    with pytest.raises(ValidationError):
        InteractionObservationV02.model_validate(data)


@pytest.mark.parametrize("bad", [
    {"decision_ref": "d-1"}, {"decision_ref": "trace:t-1"}, {"lease_ref": "decision:l"},
    {"trace_id": "t-1"}, {"trace_id": "trace:x\n"}, {"frame_ref": "frame:a/b"},
    {"environment_id": "env-1"}, {"session_ref": "sess-1"}, {"session_ref": "lease:x"},
    {"lure_ref": "lure-1"}, {"evidence_refs": ["e-1"]}, {"hypothesis_refs": ["h-1"]},
    {"hypothesis_refs": []}, {"hypothesis_refs": [f"hypothesis:h{i}" for i in range(17)]},
    {"observed_at": "2026-01-01T00:01:00"},
])
def test_observation_untyped_or_wrong_kind_rejected(bad):
    with pytest.raises(ValidationError):
        InteractionObservationV02.model_validate(_obs(**bad))


@pytest.mark.parametrize("session", [
    "session:203.0.113.9", "session:gen3-203.0.113.9-x", "session:user@host",
    "session:token=abc", "session:::1",
])
def test_session_ref_carries_no_address_credential_or_lure(session):
    with pytest.raises(ValidationError):
        InteractionObservationV02.model_validate(_obs(session_ref=session))


@pytest.mark.parametrize("extra", [
    "metadata", "lure_id", "verdict", "confidence", "command", "shell_command", "executable"])
def test_observation_rejects_unconstrained_and_authority_fields(extra):
    with pytest.raises(ValidationError):
        InteractionObservationV02.model_validate(_obs(**{extra: "x"}))
    with pytest.raises(ValueError):
        parse_interaction_observation_v02(_obs(**{extra: "x"}))


def test_decision_invariants():
    for bad in ({"decision_authority": "azazel-knowledge"}, {"expires_at": NOW.isoformat()},
                {"lease_expires_at": NOW.isoformat()}, {"lease_expires_at": "2026-01-01T00:03:00"},
                {"lease_expires_at": (NOW + timedelta(minutes=5, microseconds=1)).isoformat()},
                {"shell_command": "x"}, {"decision_id": "d-1"}, {"evidence_refs": ["raw"]}):
        with pytest.raises(ValueError):
            parse_activation_decision_v02(_decision(**bad))
    with pytest.raises(ValidationError):
        _bound()[0].authority = "advisory_only"


def test_signing_binds_v02_fields():
    signed = sign_decision(_bound()[1].model_dump(mode="json"), KEY)
    assert verify_decision_signature(signed, KEY)
    for field, value in (("lease_ref", "lease:l-2"), ("observation_objective_ref", "observation_objective:o2"),
                         ("schema_version", "environment-activation-decision/v0.1")):
        assert not verify_decision_signature({**signed, field: value}, KEY)


# ---- cross-check ----

def test_binding_ok():
    check_observation_binding(*_bound())


@pytest.mark.parametrize("obs_over", [
    {"environment_id": "environment:other"}, {"package_id": "other"}, {"node_id": "other"},
    {"decision_ref": "decision:other"}, {"trace_id": "trace:other"},
    {"observation_objective_ref": "observation_objective:other"}, {"frame_ref": "frame:other"},
    {"hypothesis_refs": ["hypothesis:other"]},
    {"hypothesis_refs": ["hypothesis:h-1", "hypothesis:h-2"]},
    {"lease_ref": "lease:other"},
])
def test_binding_mismatch_per_join_key(obs_over):
    o = parse_interaction_observation_v02(_obs(**obs_over))
    with pytest.raises(ObservationBindingError):
        check_observation_binding(o, parse_activation_decision_v02(_decision()))


@pytest.mark.parametrize("status", ["rejected", "terminated"])
def test_binding_requires_accepting_decision(status):
    d = parse_activation_decision_v02(_decision(status=status))
    with pytest.raises(ObservationBindingError):
        check_observation_binding(parse_interaction_observation_v02(_obs()), d)


@pytest.mark.parametrize("at", [NOW + timedelta(minutes=3), NOW + timedelta(minutes=4)])
def test_binding_observed_at_must_precede_lease_expiry(at):
    o = parse_interaction_observation_v02(_obs(observed_at=at.isoformat()))
    with pytest.raises(ObservationBindingError):
        check_observation_binding(o, parse_activation_decision_v02(_decision()))


def test_binding_rejects_observation_before_effective_at():
    o = parse_interaction_observation_v02(
        _obs(observed_at=(NOW - timedelta(microseconds=1)).isoformat()))
    with pytest.raises(ObservationBindingError, match="before the decision took effect"):
        check_observation_binding(o, parse_activation_decision_v02(_decision()))


def test_binding_window_endpoints_timezone_aware():
    """Window is [effective_at, lease_expires_at); offsets must not shift it."""
    jst = timezone(timedelta(hours=9))
    pst = timezone(timedelta(hours=-8))
    eff = NOW.astimezone(jst)
    lease_exp = (NOW + timedelta(minutes=3)).astimezone(pst)
    d = parse_activation_decision_v02(
        _decision(effective_at=eff.isoformat(), lease_expires_at=lease_exp.isoformat()))
    assert d.effective_at.utcoffset() == timedelta(hours=9)
    assert d.lease_expires_at.utcoffset() == timedelta(hours=-8)

    def obs_at(at):
        return parse_interaction_observation_v02(_obs(observed_at=at.isoformat()))

    one = timedelta(microseconds=1)
    # effective_at endpoint: inclusive (same instant, written in a third offset).
    check_observation_binding(obs_at(NOW), d)
    check_observation_binding(obs_at(NOW.astimezone(pst)), d)
    with pytest.raises(ObservationBindingError, match="before the decision took effect"):
        check_observation_binding(obs_at((NOW - one).astimezone(pst)), d)
    # lease_expires_at endpoint: exclusive.
    check_observation_binding(obs_at((NOW + timedelta(minutes=3) - one).astimezone(jst)), d)
    with pytest.raises(ObservationBindingError, match="at or after lease expiry"):
        check_observation_binding(obs_at((NOW + timedelta(minutes=3)).astimezone(jst)), d)
    with pytest.raises(ObservationBindingError, match="at or after lease expiry"):
        check_observation_binding(obs_at(NOW + timedelta(minutes=3)), d)


def test_v01_types_cannot_substitute_in_binding():
    v1 = make_interaction_observation()
    with pytest.raises(ObservationBindingError):
        check_observation_binding(v1, _bound()[1])
    with pytest.raises(ObservationBindingError):
        check_observation_binding(_bound()[0], v1)


# ---- versions / dispatch ----

def test_v01_readers_reject_v02_and_vice_versa():
    with pytest.raises(ValidationError):
        EnvironmentActivationDecision.model_validate(_decision())
    with pytest.raises(ValidationError):
        InteractionObservation.model_validate(_obs())
    with pytest.raises(ValidationError):  # version rewritten: extra provenance still refused
        InteractionObservation.model_validate(_obs(schema_version="interaction-observation/v0.1"))
    with pytest.raises(ValidationError):
        InteractionObservationV02.model_validate(make_interaction_observation().model_dump(mode="json"))


@pytest.mark.parametrize("version", [None, "", "interaction-observation/v0.3", "interaction-observation/v1"])
def test_unsupported_version_rejected(version):
    with pytest.raises(ValueError):
        parse_interaction_observation(_obs(schema_version=version))
    with pytest.raises(ValueError):
        parse_activation_decision(_decision(schema_version=version))
    with pytest.raises(ValueError):
        parse_interaction_observation_v02(_obs(schema_version=version))


def test_dispatch_routes_and_binding_required_rejects_v01():
    assert isinstance(parse_interaction_observation(_obs()), InteractionObservationV02)
    assert isinstance(parse_activation_decision(_decision()), EnvironmentActivationDecisionV02)
    v1 = make_interaction_observation().model_dump(mode="json")
    assert isinstance(parse_interaction_observation(v1), InteractionObservation)
    with pytest.raises(ValueError):
        parse_interaction_observation(v1, require_binding=True)
    with pytest.raises(ValueError):
        parse_activation_decision({**_decision(), "schema_version": "environment-activation-decision/v0.1"},
                                  require_binding=True)


@pytest.mark.parametrize("field", ["shell_command", "execute_now", "override_authority"])
def test_dispatch_rejects_directive_injection_in_both_versions(field):
    with pytest.raises(ValueError):
        parse_interaction_observation({**_obs(), field: "x"})
    v1 = make_interaction_observation().model_dump(mode="json")
    with pytest.raises(ValueError):
        parse_interaction_observation({**v1, field: "x"})


# ---- v0.1 unchanged ----

def test_v01_shapes_unchanged():
    assert set(EnvironmentActivationDecision.model_fields) == {
        "schema_version", "decision_id", "decision_authority", "status", "package_id",
        "package_digest", "target_node_id", "selected_tier", "budget", "safety",
        "effective_at", "expires_at", "evidence_refs", "reason_codes"}
    assert set(InteractionObservation.model_fields) == {
        "schema_version", "observation_id", "environment_id", "package_id", "node_id",
        "observed_at", "observation_class", "surface", "reaction_kind", "lure_id",
        "first_contact_latency_ms", "dwell_ms", "attempt_count", "confounder_tags",
        "runtime_context", "authority", "evidence_refs", "metadata"}
    assert make_interaction_observation().schema_version == "interaction-observation/v0.1"


@pytest.mark.parametrize("bad", ["advisory:obj-1", "objective:o", "obj-1", "frame:f-1"])
def test_objective_ref_wrong_kind_rejected(bad):
    with pytest.raises(ValidationError):
        InteractionObservationV02.model_validate(_obs(observation_objective_ref=bad))
    with pytest.raises(ValidationError):
        EnvironmentActivationDecisionV02.model_validate(_decision(observation_objective_ref=bad))


@pytest.mark.parametrize("bad", [
    ["Bad"], ["has space"], ["x" * 65], ["a", "a"], [f"c{i}" for i in range(17)], ["free text."], [""],
])
def test_reason_codes_bounded(bad):
    with pytest.raises(ValidationError):
        EnvironmentActivationDecisionV02.model_validate(_decision(reason_codes=bad))
    assert EnvironmentActivationDecisionV02.model_validate(_decision(reason_codes=["ok_code1"]))


@pytest.mark.parametrize("over", [
    {"package_id": "p" * 129}, {"target_node_id": "n" * 129}, {"selected_tier": "t" * 129}])
def test_decision_identifiers_bounded(over):
    with pytest.raises(ValidationError):
        EnvironmentActivationDecisionV02.model_validate(_decision(**over))


@pytest.mark.parametrize("over", [
    {"observation_id": "o" * 129}, {"package_id": "p" * 129}, {"node_id": "n" * 129}])
def test_observation_identifiers_bounded(over):
    with pytest.raises(ValidationError):
        InteractionObservationV02.model_validate(_obs(**over))


def test_lease_cannot_outlive_signed_decision_expiry():
    exp = NOW + timedelta(minutes=5)
    d = parse_activation_decision_v02(_decision(lease_expires_at=exp.isoformat()))  # == allowed
    assert d.lease_expires_at == d.expires_at
    parse_activation_decision_v02(
        _decision(lease_expires_at=(exp - timedelta(microseconds=1)).isoformat()))
    with pytest.raises(ValueError, match="not be later than expires_at"):
        parse_activation_decision_v02(
            _decision(lease_expires_at=(exp + timedelta(microseconds=1)).isoformat()))
    # lease must still start after effective_at
    with pytest.raises(ValueError):
        parse_activation_decision_v02(_decision(lease_expires_at=NOW.isoformat()))


def test_refkind_value_set_is_pinned():
    assert {k.value for k in RefKind} == {
        "trace", "decision", "execution", "effect", "effect_observation", "lifecycle",
        "presentation", "environment", "advisory", "evidence", "session", "surface",
        "artifact", "identity", "credential", "policy", "profile", "scope", "outcome",
        "envelope", "fixture", "frame", "hypothesis", "lease", "observation_objective"}


def test_exports():
    import azazel_fabric.deception_contracts as d
    for name in ("EnvironmentActivationDecisionV02", "InteractionObservationV02",
                 "check_observation_binding", "parse_activation_decision"):
        assert name in d.__all__
