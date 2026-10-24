"""Fabric#25: the descriptive external-security profile. **Experimental.**

Organized by the issue's own list of negative tests, so a reader can check
each one off:

1. unknown fact/effect/status cannot be read as containment, redirect, or a
   stronger DefensiveState;
2. an advisory/proposal cannot masquerade as a valid decision;
3. an environment lifecycle reference cannot replace an Edge decision ref;
4. nested directive/route/firewall/command/executor/token/override fields are
   rejected at arbitrary depth (the guard-level sweep lives in
   ``test_directive_rejection_depth.py``; this file checks the models);
5. stale/replayed envelopes do not extend a proposal or environment;
6. telemetry loss/coverage omissions cannot serialize as success;
7. tenant/trace collision and oversized opaque extensions fail closed.

Plus the golden vectors, and the "optional profile is absent" property.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

import azazel_fabric
from azazel_fabric.deception_contracts.validation import BANNED_RUNTIME_DIRECTIVE_FIELDS
from azazel_fabric.effect_contracts import (
    EffectClass,
    coerce_effect_class,
    is_authoritative_decision_reference,
)
from azazel_fabric.effect_contracts.validation import (
    SECRET_MATERIAL_MARKERS as EFFECT_SECRET_MARKERS,
)
from azazel_fabric.external_security_contracts import (
    DEVICE_CHANGE_STATUSES,
    EXPOSURE_EFFECTS,
    FACT_CLASSES,
    MATURITY,
    PRIVACY_CLASSES,
    WEAKEST_EXPOSURE_EFFECT,
    AdvisoryContextEnvelope,
    DeviceChangeObservation,
    ExposureChangeProposal,
    ExternalObservationEnvelope,
    TelemetryCoverage,
    assert_device_observation_within_proposal,
    assert_no_external_security_directives,
    assert_no_replay_extension,
    assert_no_secret_material,
    assert_no_target_locators,
    assert_not_expired,
    assert_privacy_admitted,
    canonical_digest,
    canonical_external_security_json,
    coerce_device_change_status,
    coerce_exposure_effect,
    coerce_fact_class,
)
from azazel_fabric.external_security_contracts import models as es_models
from azazel_fabric.external_security_contracts.validation import (
    _CANONICAL_RUNTIME_DIRECTIVE_FIELDS,
)
from azazel_fabric.mio_contracts.validation import (
    _CANONICAL_RUNTIME_DIRECTIVE_FIELDS as MIO_CANONICAL,
)
from azazel_fabric.schema.defensive_state import DefensiveState, coerce_defensive_state
from azazel_fabric.testing.external_security import (
    GOLDEN_EXTERNAL_SECURITY_VECTORS,
    golden_advisory_context,
    golden_device_change_applied,
    golden_device_change_released,
    golden_exposure_proposal,
    golden_external_observation,
)

FIXTURES = Path(__file__).parent / "fixtures" / "external_security"
PACKAGE_ROOT = Path(azazel_fabric.__file__).parent
FAMILY = "external_security_contracts"

MODEL_FOR_FIXTURE = {
    "external_observation_envelope_v0.json": ExternalObservationEnvelope,
    "advisory_context_envelope_v0.json": AdvisoryContextEnvelope,
    "exposure_change_proposal_v0.json": ExposureChangeProposal,
    "device_change_observation_applied_v0.json": DeviceChangeObservation,
    "device_change_observation_released_v0.json": DeviceChangeObservation,
}

#: (builder, model) for each of the four families.
FAMILIES = {
    "observation": (golden_external_observation, ExternalObservationEnvelope),
    "advisory": (golden_advisory_context, AdvisoryContextEnvelope),
    "proposal": (golden_exposure_proposal, ExposureChangeProposal),
    "device": (golden_device_change_applied, DeviceChangeObservation),
}


def _canonical_sha256(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _with(payload: dict[str, Any], **changes: Any) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    out.update(changes)
    return out


def _extension(body: dict[str, Any], namespace: str = "vendor.edr-sim") -> dict[str, Any]:
    return {
        "schema_version": "external-vendor-extension/v0.1",
        "namespace": namespace,
        "body": body,
        "body_digest": canonical_digest(body),
        "evidence_ref": None,
    }


# ---------------------------------------------------------------------------
# Maturity and golden vectors
# ---------------------------------------------------------------------------


def test_the_family_declares_itself_experimental():
    """Fabric#23: no producer, no consumer, so no compatibility promise."""
    assert MATURITY == "experimental"
    init = (PACKAGE_ROOT / FAMILY / "__init__.py").read_text(encoding="utf-8")
    assert "**Experimental.**" in init.split("\n", 1)[0]


def test_every_published_vector_has_a_fixture_file_and_a_model():
    assert set(GOLDEN_EXTERNAL_SECURITY_VECTORS) == set(MODEL_FOR_FIXTURE)
    for name in GOLDEN_EXTERNAL_SECURITY_VECTORS:
        assert (FIXTURES / name).is_file(), f"published vector without a fixture: {name}"


def test_the_manifest_matches_every_fixture_byte_for_byte():
    manifest = json.loads(
        (FIXTURES / "external_security_manifest_v0.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == "external-security-golden-manifest/v0.1"
    assert set(manifest["canonical_sha256"]) == set(GOLDEN_EXTERNAL_SECURITY_VECTORS)
    for name, digest in manifest["canonical_sha256"].items():
        stored = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        assert _canonical_sha256(stored) == digest, f"fixture drifted from manifest: {name}"


@pytest.mark.parametrize("name", sorted(GOLDEN_EXTERNAL_SECURITY_VECTORS))
def test_the_builder_still_produces_the_bytes_on_disk(name):
    assert GOLDEN_EXTERNAL_SECURITY_VECTORS[name]() == json.loads(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("name", sorted(MODEL_FOR_FIXTURE))
def test_a_consumer_can_rebuild_the_model_from_the_fixture(name):
    stored = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert MODEL_FOR_FIXTURE[name].model_validate(stored).model_dump(mode="json") == stored


@pytest.mark.parametrize("name", sorted(GOLDEN_EXTERNAL_SECURITY_VECTORS))
def test_canonical_serialization_is_stable_across_a_round_trip(name):
    payload = GOLDEN_EXTERNAL_SECURITY_VECTORS[name]()
    model = MODEL_FOR_FIXTURE[name].model_validate(payload)
    first = canonical_external_security_json(model)
    restored = type(model).model_validate(json.loads(first))
    assert canonical_external_security_json(restored) == first
    assert canonical_digest(restored) == canonical_digest(model)
    assert GOLDEN_EXTERNAL_SECURITY_VECTORS[name]() == payload  # no clock, no randomness


def test_the_published_chain_correlates_end_to_end():
    proposal = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    applied = DeviceChangeObservation.model_validate(golden_device_change_applied())
    released = DeviceChangeObservation.model_validate(golden_device_change_released())
    advisory = AdvisoryContextEnvelope.model_validate(golden_advisory_context())
    observation = ExternalObservationEnvelope.model_validate(golden_external_observation())

    assert_device_observation_within_proposal(proposal, applied)
    assert_device_observation_within_proposal(proposal, released)
    assert observation.observation_id in advisory.source_fact_refs
    assert {observation.tenant_ref, advisory.tenant_ref, proposal.tenant_ref, applied.tenant_ref} == {
        proposal.tenant_ref
    }


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_every_record_is_pinned_non_executable(family):
    build, model = FAMILIES[family]
    record = model.model_validate(build())
    assert record.executable is False
    assert record.provenance.confers_authority is False
    with pytest.raises(ValidationError):
        model.model_validate(_with(build(), executable=True))


# ---------------------------------------------------------------------------
# 1. Unknown never maps stronger
# ---------------------------------------------------------------------------


def test_an_unknown_fact_class_stays_unknown_and_keeps_its_label():
    record = ExternalObservationEnvelope.model_validate(
        _with(golden_external_observation(), fact_class="edr_containment_success")
    )
    assert record.fact_class == "unknown"
    assert record.source_fact_label == "edr_containment_success"
    # ...and the coerced record is itself stable.
    again = ExternalObservationEnvelope.model_validate(record.model_dump(mode="json"))
    assert again == record


@pytest.mark.parametrize("hostile", ["containment", "REDIRECT", "ISOLATE", "", None, 0, ["dns_event"]])
def test_coercion_lands_on_the_weakest_reading(hostile):
    assert coerce_fact_class(hostile) == ("unknown", False)
    assert coerce_device_change_status(hostile) == ("unknown", False)
    assert coerce_exposure_effect(hostile) == (WEAKEST_EXPOSURE_EFFECT, False)


def test_an_unknown_device_status_stays_unknown():
    record = DeviceChangeObservation.model_validate(
        _with(golden_device_change_applied(), status="contained_successfully")
    )
    assert record.status == "unknown"
    assert record.source_status_label == "contained_successfully"


def test_an_unknown_requested_effect_is_refused_rather_than_guessed():
    with pytest.raises(ValidationError):
        ExposureChangeProposal.model_validate(
            _with(golden_exposure_proposal(), requested_effect="isolate_host")
        )


_ALL_VOCABULARY = sorted(
    set(FACT_CLASSES)
    | set(DEVICE_CHANGE_STATUSES)
    | set(EXPOSURE_EFFECTS)
    | set(get_args(es_models.AdvisoryActionClass))
    | set(get_args(es_models.RecommendedObservationClass))
)


@pytest.mark.parametrize("value", _ALL_VOCABULARY)
def test_no_family_value_reads_as_a_defensive_state_or_effect(value):
    """Fabric provides no mapping, and no value spells one by accident."""
    state, recognized = coerce_defensive_state(value)
    assert recognized is False and state is DefensiveState.OBSERVE
    effect, recognized = coerce_effect_class(value)
    assert recognized is False and effect is EffectClass.OBSERVE_ONLY
    lowered = value.lower()
    assert lowered not in {member.value.lower() for member in DefensiveState}
    assert lowered not in {member.value.lower() for member in EffectClass}


def test_no_device_status_claims_success():
    for status in DEVICE_CHANGE_STATUSES:
        assert not any(word in status for word in ("success", "contain", "effective"))


def test_the_family_imports_no_state_or_effect_vocabulary():
    """Structural: no module here can map to #14/#15 vocabularies."""
    for path in sorted((PACKAGE_ROOT / FAMILY).glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("azazel_fabric.schema"), path.name
                assert not node.module.startswith("azazel_fabric.effect_contracts"), path.name


# ---------------------------------------------------------------------------
# 2. Advisory/proposal cannot masquerade as a decision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family", ["advisory", "proposal"])
@pytest.mark.parametrize(
    "authority", ["producer_decision_ref", "observed_fact", "active_materialized", "approved"]
)
def test_an_advisory_or_proposal_cannot_claim_decision_authority(family, authority):
    build, model = FAMILIES[family]
    with pytest.raises(ValidationError):
        model.model_validate(_with(build(), authority_class=authority))


@pytest.mark.parametrize("family", ["advisory", "proposal"])
def test_the_pinned_authority_is_not_an_authoritative_decision(family):
    build, model = FAMILIES[family]
    record = model.model_validate(build())
    assert is_authoritative_decision_reference(record.authority_class) is False


def test_an_advisory_has_no_decision_ref_to_fill():
    with pytest.raises(ValidationError):
        AdvisoryContextEnvelope.model_validate(
            _with(golden_advisory_context(), decision_ref="decision:edge-1")
        )


@pytest.mark.parametrize("key", ["approved", "approval", "decision_valid", "authorized", "granted"])
def test_a_decision_verdict_cannot_be_smuggled_into_a_vendor_extension(key):
    payload = golden_external_observation()
    payload["vendor_extensions"] = [_extension({"meta": [{key: True}]})]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


def test_a_signature_does_not_confer_authority():
    payload = golden_external_observation()
    payload["provenance"]["confers_authority"] = True
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


def test_an_advisory_must_be_grounded_in_facts():
    with pytest.raises(ValidationError):
        AdvisoryContextEnvelope.model_validate(
            _with(golden_advisory_context(), source_fact_refs=[], normalized_fact_refs=[])
        )


# ---------------------------------------------------------------------------
# 3. A lifecycle reference cannot replace a decision reference
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "environment:golden-decoy-1",
        "lifecycle:env-golden-1.active",
        "presentation:golden-1",
        "advisory:golden-knowledge-1",
        "proposal:golden-deception-1",
        "decision-untyped-1",
        "decision:",
        "decision:has/slash",
    ],
)
@pytest.mark.parametrize("family", ["proposal", "device"])
def test_only_a_decision_ref_fills_the_decision_slot(family, value):
    build, model = FAMILIES[family]
    with pytest.raises(ValidationError):
        model.model_validate(_with(build(), decision_ref=value))


def test_the_environment_slot_takes_only_an_environment_ref():
    with pytest.raises(ValidationError):
        ExposureChangeProposal.model_validate(
            _with(golden_exposure_proposal(), environment_ref="decision:edge-golden-external-1")
        )


# ---------------------------------------------------------------------------
# 4. Directives at depth, through the models
# ---------------------------------------------------------------------------

#: One name per category the issue lists; the full name sweep is in
#: test_directive_rejection_depth.py.
_DIRECTIVE_SAMPLES = (
    "command",
    "shell_command",
    "static_route",
    "firewall_rule",
    "dns_rule",
    "rule_body",
    "executor",
    "auth_token",
    "credential_locator",
    "vault_path",
    "override",
    "execute_now",
    "auto_execute",
)


@pytest.mark.parametrize("name", _DIRECTIVE_SAMPLES)
def test_a_directive_in_the_fact_projection_is_refused_inside_a_list(name):
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), normalized_fact={"a": [{"b": {name: "x"}}]})
        )


@pytest.mark.parametrize("name", _DIRECTIVE_SAMPLES)
def test_a_directive_in_a_vendor_extension_is_refused_even_with_a_valid_digest(name):
    payload = golden_device_change_applied()
    payload["vendor_extensions"] = [_extension({"x": [[{name: "y"}]]})]
    with pytest.raises(ValidationError):
        DeviceChangeObservation.model_validate(payload)


def test_an_execute_flag_is_refused_wherever_it_appears():
    payload = golden_external_observation()
    payload["normalized_fact"] = {"steps": [{"executable": True}]}
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


@pytest.mark.parametrize("field", ["target_ip", "hostname", "device_object_id"])
def test_a_recommended_action_cannot_carry_a_target_locator(field):
    payload = golden_advisory_context()
    payload["recommended_actions"][0][field] = "10.0.0.5"
    with pytest.raises(ValidationError):
        AdvisoryContextEnvelope.model_validate(payload)


def test_the_target_locator_guard_refuses_at_depth():
    with pytest.raises(ValueError):
        assert_no_target_locators({"a": [{"b": ({"vendor_object_id": "obj-77"},)}]})
    assert_no_target_locators({"subject_refs": ["host:golden-1"]})


@pytest.mark.parametrize(
    "secret",
    [
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "password=hunter2",
        "credential:switch-admin",
        "vault:kv-switch-admin",
        "token:abc123",
    ],
)
@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_secret_material_and_credential_locators_are_refused_in_every_family(family, secret):
    """`producer_version` is free text in all four, so only the guard stops it."""
    build, model = FAMILIES[family]
    model.model_validate(_with(build(), producer_version="0.0.1-ok"))
    with pytest.raises(ValidationError, match="secret material|credential locator"):
        model.model_validate(_with(build(), producer_version=secret))


def test_the_secret_guard_reaches_into_collections():
    with pytest.raises(ValueError):
        assert_no_secret_material({"a": [({"b": ["ok", "ssh-ed25519 AAAA"]},)]})
    assert_no_secret_material({"a": ["evidence:1", "host:2"]})


def test_the_directive_set_restates_the_series_canon():
    """Restated, not imported (strict gate); this keeps the copies aligned."""
    assert _CANONICAL_RUNTIME_DIRECTIVE_FIELDS == MIO_CANONICAL
    assert set(BANNED_RUNTIME_DIRECTIVE_FIELDS) <= set(_CANONICAL_RUNTIME_DIRECTIVE_FIELDS)
    for name in BANNED_RUNTIME_DIRECTIVE_FIELDS:
        with pytest.raises(ValueError):
            assert_no_external_security_directives({"x": [{name: 1}]})


def test_the_secret_markers_cover_the_effect_family_markers():
    from azazel_fabric.external_security_contracts.validation import SECRET_MATERIAL_MARKERS

    assert set(EFFECT_SECRET_MARKERS) <= set(SECRET_MATERIAL_MARKERS)


# ---------------------------------------------------------------------------
# 5. Stale and replayed records extend nothing
# ---------------------------------------------------------------------------


def test_a_replayed_proposal_cannot_extend_its_expiry():
    original = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    replay = ExposureChangeProposal.model_validate(
        _with(golden_exposure_proposal(), expires_at="2026-10-01T05:00:00+00:00")
    )
    with pytest.raises(ValueError):
        assert_no_replay_extension(original, replay)
    assert_no_replay_extension(original, ExposureChangeProposal.model_validate(golden_exposure_proposal()))


def test_a_replayed_proposal_cannot_widen_its_scope():
    original = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    wider = ExposureChangeProposal.model_validate(
        _with(golden_exposure_proposal(), target_scope_ref="scope:whole-site")
    )
    with pytest.raises(ValueError):
        assert_no_replay_extension(original, wider)


@pytest.mark.parametrize("status", ["applied", "observed", "accepted_by_device"])
def test_a_stale_device_observation_cannot_keep_an_exposure_alive(status):
    proposal = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    late = golden_device_change_released()
    late["status"] = status
    late = DeviceChangeObservation.model_validate(late)
    with pytest.raises(ValueError):
        assert_device_observation_within_proposal(proposal, late)


def test_an_observation_before_the_window_cannot_report_the_change_in_place():
    proposal = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    early = golden_device_change_applied()
    early["observed_at"] = "2026-10-01T00:04:00+00:00"
    early["observation_window"] = {
        "schema_version": "external-event-window/v0.1",
        "start": "2026-10-01T00:03:00+00:00",
        "end": "2026-10-01T00:04:00+00:00",
    }
    with pytest.raises(ValueError):
        assert_device_observation_within_proposal(
            proposal, DeviceChangeObservation.model_validate(early)
        )


def test_an_expired_advisory_is_refused_at_the_callers_instant():
    advisory = AdvisoryContextEnvelope.model_validate(golden_advisory_context())
    assert_not_expired(advisory, as_of="2026-10-01T00:30:00+00:00")
    with pytest.raises(ValueError):
        assert_not_expired(advisory, as_of=advisory.expires_at)


def test_a_proposal_window_is_bounded():
    with pytest.raises(ValidationError):
        ExposureChangeProposal.model_validate(
            _with(golden_exposure_proposal(), expires_at="2026-11-01T00:05:00+00:00")
        )
    with pytest.raises(ValidationError):
        ExposureChangeProposal.model_validate(
            _with(golden_exposure_proposal(), expires_at=golden_exposure_proposal()["not_before"])
        )


def test_an_exposing_proposal_must_require_rollback():
    payload = golden_exposure_proposal()
    payload["rollback_requirement"] = {
        "schema_version": "external-rollback-requirement/v0.1",
        "required": False,
        "triggers": [],
        "max_rollback_seconds": None,
    }
    with pytest.raises(ValidationError):
        ExposureChangeProposal.model_validate(payload)


def test_the_device_observation_carries_no_expiry_to_extend():
    assert "expires_at" not in DeviceChangeObservation.model_fields
    with pytest.raises(ValidationError):
        DeviceChangeObservation.model_validate(
            _with(golden_device_change_applied(), expires_at="2026-12-01T00:00:00+00:00")
        )


# ---------------------------------------------------------------------------
# 6. Coverage loss cannot serialize as success
# ---------------------------------------------------------------------------


def test_incomplete_coverage_must_name_its_gaps():
    with pytest.raises(ValidationError):
        TelemetryCoverage(coverage_complete=False)


def test_complete_coverage_cannot_hide_missing_sources():
    with pytest.raises(ValidationError):
        TelemetryCoverage(coverage_complete=True, sources_expected=40, sources_reporting=38)
    with pytest.raises(ValidationError):
        TelemetryCoverage(coverage_complete=True, gaps=("one sensor down",))


@pytest.mark.parametrize("family", ["observation", "device"])
def test_coverage_is_required_not_defaulted(family):
    build, model = FAMILIES[family]
    payload = build()
    payload.pop("telemetry_coverage")
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize("key", ["success", "successful", "contained", "tactical_success", "block_success"])
def test_a_success_verdict_is_refused_anywhere(key):
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), normalized_fact={"result": [{key: True}]})
        )


def test_a_device_observation_cannot_claim_a_tactical_outcome():
    with pytest.raises(ValidationError):
        DeviceChangeObservation.model_validate(
            _with(golden_device_change_applied(), tactical_outcome_claimed=True)
        )


def test_the_published_applied_vector_states_its_gap():
    record = DeviceChangeObservation.model_validate(golden_device_change_applied())
    assert record.status == "applied"
    assert record.telemetry_coverage.coverage_complete is False
    assert record.telemetry_coverage.gaps
    assert "success" not in json.dumps(record.model_dump(mode="json"))


def test_a_failed_change_must_say_why():
    with pytest.raises(ValidationError):
        DeviceChangeObservation.model_validate(_with(golden_device_change_applied(), status="failed"))


# ---------------------------------------------------------------------------
# 7. Tenant/trace collision and oversized extensions fail closed
# ---------------------------------------------------------------------------


def test_a_provenance_hop_from_another_tenant_is_refused():
    payload = golden_external_observation()
    payload["provenance"]["chain"][0]["tenant_ref"] = "tenant:other-site"
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_a_cross_tenant_reference_is_refused_in_every_family(family):
    build, model = FAMILIES[family]
    payload = build()
    payload["evidence_refs"] = ["tenant:other-site"]
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_a_provenance_chain_must_end_at_the_producer():
    payload = golden_external_observation()
    payload["producer_product"] = "knowledge"
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


@pytest.mark.parametrize("field,value", [("trace_ref", "trace:other"), ("tenant_ref", "tenant:other")])
def test_a_device_observation_from_another_chain_does_not_correlate(field, value):
    proposal = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    observation = golden_device_change_applied()
    observation[field] = value
    if field == "tenant_ref":
        for hop in observation["provenance"]["chain"]:
            hop["tenant_ref"] = value
    with pytest.raises(ValueError):
        assert_device_observation_within_proposal(
            proposal, DeviceChangeObservation.model_validate(observation)
        )


def test_a_device_observation_for_another_proposal_does_not_correlate():
    proposal = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    observation = DeviceChangeObservation.model_validate(
        _with(golden_device_change_applied(), proposal_ref="proposal:someone-else")
    )
    with pytest.raises(ValueError):
        assert_device_observation_within_proposal(proposal, observation)


def _deep(depth: int) -> dict[str, Any]:
    node: dict[str, Any] = {"leaf": 1}
    for _ in range(depth - 1):
        node = {"n": node}
    return node


@pytest.mark.parametrize(
    "body",
    [
        _deep(5),  # deeper than the extension bound
        {f"k{i}": i for i in range(33)},  # more items than the bound
        {"blob": ["x" * 1000 for _ in range(9)]},  # over the byte bound
        {"long": "x" * 1025},  # over the string bound
    ],
    ids=["depth", "cardinality", "bytes", "string"],
)
def test_an_oversized_vendor_extension_fails_closed(body):
    payload = golden_external_observation()
    payload["vendor_extensions"] = [_extension(body)]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


def test_a_vendor_extension_body_must_match_its_digest():
    payload = golden_external_observation()
    payload["vendor_extensions"][0]["body"]["sensor_build"] = "7.12.4"
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


@pytest.mark.parametrize("key", ["authority_class", "executable", "decision_ref", "tenant_ref", "status"])
def test_a_vendor_extension_cannot_restate_a_reserved_key(key):
    payload = golden_external_observation()
    payload["vendor_extensions"] = [_extension({"nested": {key: "observed_fact"}})]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


def test_vendor_extensions_are_bounded_in_number_and_unique_by_namespace():
    payload = golden_external_observation()
    payload["vendor_extensions"] = [_extension({"a": i}, f"vendor.sim{i}") for i in range(5)]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)
    payload["vendor_extensions"] = [_extension({"a": 1}), _extension({"a": 2})]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


@pytest.mark.parametrize("namespace", ["edr", "Vendor.X", "vendor..x", "vendor/x", "a.b.c.d.e"])
def test_a_vendor_namespace_must_be_dotted_and_plain(namespace):
    payload = golden_external_observation()
    payload["vendor_extensions"] = [_extension({"a": 1}, namespace)]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


def test_an_oversized_fact_projection_fails_closed():
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), normalized_fact=_deep(6))
        )


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------


def test_privacy_class_is_closed():
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), privacy_class="tlp_amber")
        )


def test_a_consumer_rejects_a_class_it_is_not_admitted_to():
    record = ExternalObservationEnvelope.model_validate(golden_external_observation())
    assert_privacy_admitted(record, frozenset({"public", "internal"}))
    with pytest.raises(ValueError):
        assert_privacy_admitted(record, frozenset({"public"}))
    with pytest.raises(ValueError):
        assert_privacy_admitted(record, frozenset({"internal", "tlp_red"}))
    assert set(PRIVACY_CLASSES) == {"public", "internal", "sensitive", "restricted"}


# ---------------------------------------------------------------------------
# The profile is optional
# ---------------------------------------------------------------------------


def test_nothing_outside_the_profile_imports_it():
    """Edge, Knowledge, Deception, Nexus and Boot stay compatible without it.

    Statically: no Fabric module except the family itself and its published
    vectors names it in an import.
    """

    allowed = {PACKAGE_ROOT / "testing" / "external_security.py"}
    offenders = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if FAMILY in path.parts or path in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(FAMILY in name or "external_security" in name for name in names):
                offenders.append(str(path.relative_to(PACKAGE_ROOT)))
    assert offenders == [], f"modules import the optional profile: {offenders}"


def test_every_other_module_loads_without_the_profile():
    """Dynamically: importing everything else never pulls the profile in."""
    # Names come from the filesystem: `pkgutil.walk_packages` imports every
    # package it recurses into, which would load the profile to skip it.
    names = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if FAMILY in path.parts or path.name == "external_security.py":
            continue
        parts = path.relative_to(PACKAGE_ROOT.parent).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.append(".".join(parts))
    script = (
        "import importlib, json, sys\n"
        f"names = {names!r}\n"
        "for name in names:\n"
        "    importlib.import_module(name)\n"
        "print(json.dumps({'loaded': len(names), 'present': sorted(\n"
        "    n for n in sys.modules if 'external_security' in n)}))\n"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["loaded"] > 20
    assert report["present"] == []


def test_the_general_conformance_kit_does_not_export_the_profile():
    import azazel_fabric.testing as kit

    assert not any("external" in name for name in kit.__all__)


def test_every_family_model_is_exported():
    """A model left out of __all__ escapes every cross-cutting gate."""
    import inspect

    from pydantic import BaseModel

    declared = {
        name
        for name, obj in vars(es_models).items()
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and not name.startswith("_")
        and obj.__module__ == es_models.__name__
    }
    import azazel_fabric.external_security_contracts as family

    assert declared <= set(family.__all__), sorted(declared - set(family.__all__))


# ---------------------------------------------------------------------------
# Review follow-up: spellings, values, and the edges of the closed choices
# ---------------------------------------------------------------------------

#: Spellings of banned names that a lower-case-and-fold normalizer missed.
_EVASIVE_DIRECTIVE_KEYS = (
    "shellCommand",
    "firewallRule",
    "accessToken",
    "executeNow",
    "authorityOverride",
    "commandLine",
    "comm-and",
    "Shell Command",
    "fire_wall_rule",
    "ＣＯＭＭＡＮＤ",  # fullwidth
    "cоmmand",  # Cyrillic о
    "com​mand",  # zero-width space
    "exec­ute",  # soft hyphen
    "token⁠",  # word joiner
)


@pytest.mark.parametrize("key", _EVASIVE_DIRECTIVE_KEYS)
def test_an_evasive_spelling_is_refused_in_the_fact_projection(key):
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), normalized_fact={"a": [{key: "x"}]})
        )


@pytest.mark.parametrize("key", _EVASIVE_DIRECTIVE_KEYS)
def test_an_evasive_spelling_is_refused_in_a_vendor_extension(key):
    payload = golden_device_change_applied()
    payload["vendor_extensions"] = [_extension({"x": [{key: "y"}]})]
    with pytest.raises(ValidationError):
        DeviceChangeObservation.model_validate(payload)


@pytest.mark.parametrize("key", _EVASIVE_DIRECTIVE_KEYS)
def test_the_directive_guard_refuses_evasive_spellings_at_depth(key):
    with pytest.raises(ValueError):
        assert_no_external_security_directives({"a": [({"b": {key: 1}},)]})


@pytest.mark.parametrize(
    "key", ["targetIp", "Target-Hostname", "deviceObjectId", "ｈｏｓｔｎａｍｅ", "host​name"]
)
def test_the_locator_guard_refuses_evasive_spellings(key):
    with pytest.raises(ValueError):
        assert_no_target_locators({"a": [{key: "x"}]})


@pytest.mark.parametrize(
    "key", ["authorityClass", "decisionRef", "Tenant-Ref", "STATUS", "authority class", "exe_cutable"]
)
@pytest.mark.parametrize("where", ["normalized_fact", "vendor_extension"])
def test_a_reserved_key_is_refused_in_any_ascii_spelling(key, where):
    payload = golden_external_observation()
    if where == "normalized_fact":
        payload["normalized_fact"] = {"nested": [{key: "observed_fact"}]}
    else:
        payload["vendor_extensions"] = [_extension({"nested": {key: "observed_fact"}})]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "value",
    [
        "vault:secret/data/db",
        "secret:projects/p/secrets/s",
        "Credential:foo",
        "TOKEN:abc",
        " key : x",
        "fetch it from vault:kv/switch-admin first",
        "password: hunter2 was reused",
    ],
)
def test_a_credential_locator_is_refused_in_any_case_and_grammar(value):
    with pytest.raises(ValidationError, match="credential locator"):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), limitations=[value])
        )


@pytest.mark.parametrize(
    "value", ["Tenant:other", "tenant:other/x", "seen in tenant:other-site last week", "TENANT : other"]
)
def test_a_cross_tenant_reference_is_refused_in_any_case_and_inside_text(value):
    with pytest.raises(ValidationError, match="cross-tenant"):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), limitations=[value])
        )


def test_no_tenant_can_be_named_in_free_text_at_all():
    """Allowlist, not a comparison: free text takes no ``:``, so even the
    record's own tenant cannot be written there. The tenant lives in one field."""
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), limitations=["scoped to tenant:golden-site-1 only"])
        )


@pytest.mark.parametrize(
    "ref", ["ip:10.0.0.5", "hostname:ws-17", "Host:ws-17", "mac:aa-bb", "fqdn:a.example", "url:x"]
)
def test_an_advisory_subject_cannot_be_a_locator(ref):
    with pytest.raises(ValidationError, match="target locator"):
        AdvisoryContextEnvelope.model_validate(_with(golden_advisory_context(), subject_refs=[ref]))


@pytest.mark.parametrize(
    "scope", ["scope:10.0.0.5", "scope:fe80::1", "scope:2001:db8:0:0:0:0:0:1"]
)
def test_a_proposal_scope_cannot_be_an_address(scope):
    with pytest.raises(ValidationError, match="target_scope_ref must be an opaque typed reference"):
        ExposureChangeProposal.model_validate(_with(golden_exposure_proposal(), target_scope_ref=scope))


def test_an_observation_may_carry_ipv4_and_hostnames_as_fact_values():
    """Observing a flow between two addresses is a fact; only advice/proposals are closed.

    The fact-value allowlist has no ``:`` or ``/``, so IPv6 addresses, URLs and
    paths cannot be inline facts: they go digest-only (documented allowance).
    """
    ExternalObservationEnvelope.model_validate(
        _with(golden_external_observation(), normalized_fact={"src": "10.0.0.5", "dst": "db01.corp.example"})
    )
    for value in ("fe80::1", "https://db01/x", "/etc/passwd"):
        with pytest.raises(ValidationError):
            ExternalObservationEnvelope.model_validate(
                _with(golden_external_observation(), normalized_fact={"dst": value})
            )


@pytest.mark.parametrize(
    "text",
    [
        "run iptables -A INPUT -s 10.1.1.1 -j DROP",
        "nft add rule inet filter input drop",
        "use ip route add blackhole",
        "ufw deny 22",
        "firewall-cmd --add-rich-rule",
        "sudo systemctl stop sshd",
        "curl the payload",
        "rm -rf the share",
        "echo ok && reboot",
        "$(whoami)",
    ],
)
@pytest.mark.parametrize("field", ["rationale", "constraints"])
def test_a_recommended_action_cannot_carry_command_text(text, field):
    payload = golden_advisory_context()
    payload["recommended_actions"][0][field] = text if field == "rationale" else [text]
    with pytest.raises(ValidationError):
        AdvisoryContextEnvelope.model_validate(payload)


def test_a_mutated_record_cannot_canonicalize():
    record = ExternalObservationEnvelope.model_validate(golden_external_observation())
    record.normalized_fact["shellCommand"] = "rm -rf /"  # frozen model, mutable dict
    with pytest.raises(ValidationError):
        canonical_external_security_json(record)


@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_number_is_refused_rather_than_becoming_null(number):
    with pytest.raises(ValidationError, match="non-finite"):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), normalized_fact={"score": number})
        )


@pytest.mark.parametrize("field", ["observation_id", "source_event_ref", "tenant_ref"])
def test_a_ref_with_a_trailing_newline_is_refused(field):
    payload = golden_external_observation()
    payload[field] = payload[field] + "\n"
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


def test_a_namespace_with_a_trailing_newline_is_refused():
    payload = golden_external_observation()
    payload["vendor_extensions"] = [_extension({"a": 1}, "vendor.edr-sim\n")]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"coverage_complete": True},
        {"coverage_complete": True, "sources_expected": 0, "sources_reporting": 0},
        {"coverage_complete": True, "sources_expected": 3},
        {"coverage_complete": "true", "sources_expected": 1, "sources_reporting": 1},
        {"coverage_complete": 1, "sources_expected": 1, "sources_reporting": 1},
        {"coverage_complete": True, "sources_expected": "1", "sources_reporting": 1},
    ],
)
def test_complete_coverage_must_be_counted_and_strictly_typed(kwargs):
    with pytest.raises(ValidationError):
        TelemetryCoverage(**kwargs)


def test_an_observation_window_starting_before_the_proposal_is_refused():
    proposal = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    payload = golden_device_change_applied()
    payload["observation_window"]["start"] = "2026-10-01T00:03:00+00:00"  # before not_before
    with pytest.raises(ValueError, match="observation window"):
        assert_device_observation_within_proposal(
            proposal, DeviceChangeObservation.model_validate(payload)
        )


@pytest.mark.parametrize(
    "fact",
    [
        {"country": "Slovakia"},  # contains the AKIA key-id marker, case-folded
        {"file_flags": {"executable": True}},  # an endpoint_file fact
        {"command_line": "office_sim.exe /q"},  # an EDR process fact
    ],
    ids=["akia-substring", "executable-flag", "command-line"],
)
def test_known_false_positives_stay_refused(fact):
    """Documented limitation, pinned so it is not loosened by accident.

    These are legitimate facts the closed checks refuse. The documented home
    for such data is a digest-only reference: carry the raw value at the
    source, put its digest in `payload_digest` / an `evidence:` ref, and keep
    it out of the projection. See docs/external-security-contracts.md §9.
    """
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), normalized_fact=fact)
        )


# ---------------------------------------------------------------------------
# Allowlists: the contract is closed by construction (second review)
# ---------------------------------------------------------------------------

_DENIED_OPAQUE_KEYS = (
    "cmd_1", "cmd1", "Cmd", "c-m-d", "shell_cmd", "shellCmd", "cmd_line", "cmdline", "exec_now",
    "autoExec", "argv0", "run", "script_body", "scripts", "pwd", "pass", "passphrase", "bearer",
    "jwt", "sshkey", "ssh_key", "privkey", "priv_key", "signing_key", "api_key", "key", "cookie",
    "session_cookie", "auth_header", "otp", "firewall_rule_v2", "rule2", "nft_rules_list",
    "iptables", "nftables", "acls", "acl_entries", "is_approved", "approved_by", "is_authorized",
    "succeeded_at", "force_apply", "authority_level", "authorityClass2", "tenant_id", "-", "  ", "",
    "x" * 65,
)


@pytest.mark.parametrize("key", _DENIED_OPAQUE_KEYS)
@pytest.mark.parametrize("where", ["normalized_fact", "vendor_extension"])
def test_an_opaque_map_key_outside_the_allowlist_is_refused(key, where):
    payload = golden_external_observation()
    if where == "normalized_fact":
        payload["normalized_fact"] = {key: "v"}
    else:
        payload["vendor_extensions"] = [_extension({key: "v"})]
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(payload)


def test_an_opaque_map_still_takes_ordinary_snake_case_keys():
    ExternalObservationEnvelope.model_validate(
        _with(golden_external_observation(), normalized_fact={"parent_pid": 1, "image_hash_band": "x", "key_count": 2})
    )


_DENIED_OPAQUE_VALUES = (
    "vault : x", "vault%3Asecret/db", "secret_ref:db", "credential_ref:x", "apikey:abcd",
    "env:DB_PASSWORD", "keyvault:prod", "op://Private/db", "kv:prod/db", "Bearer eyJhbGciOi.x.y",
    "eyJhbGciOiJIUzI1NiJ9", "tenant:other", "tenant%3Aother", "tenants:other", "Tenant : other",
    "line\nbreak", "x" * 257,
)


@pytest.mark.parametrize("value", _DENIED_OPAQUE_VALUES)
def test_an_opaque_map_value_outside_the_allowlist_is_refused(value):
    with pytest.raises(ValidationError):
        ExternalObservationEnvelope.model_validate(
            _with(golden_external_observation(), normalized_fact={"k": value})
        )


_DENIED_FREE_TEXT = (
    "/sbin/iptables -F", "IPTABLES", "sudo\tx", "pfctl -f /etc/pf.conf", "ipset add blk x",
    "ip link set eth0 down", "reboot now", "x; reboot", "a|b", "echo x > /etc/hosts",
    "python3 -c 'import os'", "Invoke-Expression x", "New-NetFirewallRule -Action Block",
    "ｓｕｄｏ rm", "su​do", "isolate host:db01", "see https://db01.corp.example.com/x",
    "db01.corp.example.com", "10.0.0.1", "010.000.000.001", "167772161", "0x0a000001", "10.1",
    "10%2E0%2E0%2E1", "FE80::1", "[::FFFF:a00:1]", "host%3Adb01", "host：db01", "secret_ref:db",
    "tenant:other", "Foo::Bar resolution path", "a = b", "",
)


@pytest.mark.parametrize("text", _DENIED_FREE_TEXT)
@pytest.mark.parametrize("field", ["assessment_summary", "limitations", "unknowns", "rationale", "constraints"])
def test_advisory_free_text_outside_the_allowlist_is_refused(field, text):
    payload = golden_advisory_context()
    if field == "assessment_summary":
        payload[field] = text
    elif field in ("limitations", "unknowns"):
        payload[field] = [text]
    elif field == "rationale":
        payload["recommended_actions"][0]["rationale"] = text
    else:
        payload["recommended_actions"][0]["constraints"] = [text]
    with pytest.raises(ValidationError):
        AdvisoryContextEnvelope.model_validate(payload)


_DENIED_REFS = (
    "asset:db01.corp.example.com", "asset:10.0.0.1", "asset:DB01", "Host:db01", "dns:evil",
    "endpoint:db01", "vault_path:x", "credential_locator:x", "keychain_ref:x", "secret-ref:x",
    "SECRET_REF:x", "password_file:x", "asset:a/b", "asset:a%2Fb", "asset:a:b", "asset:",
)


@pytest.mark.parametrize("ref", _DENIED_REFS)
@pytest.mark.parametrize("family", ["observation", "advisory"])
def test_a_subject_ref_outside_the_kind_and_body_allowlist_is_refused(family, ref):
    build, model = FAMILIES[family]
    with pytest.raises(ValidationError):
        model.model_validate(_with(build(), subject_refs=[ref]))


@pytest.mark.parametrize("ref", ["evidence:db01.corp.example.com", "scope:x", "evidence:a:b"])
def test_an_evidence_ref_outside_the_allowlist_is_refused(ref):
    with pytest.raises(ValidationError):
        ExposureChangeProposal.model_validate(_with(golden_exposure_proposal(), evidence_refs=[ref]))


@pytest.mark.parametrize(
    "value", ["sudo iptables -F && reboot", "db01.corp.example.com", "10.0.0.1", "1.2.3.4", "v1", ""]
)
@pytest.mark.parametrize("field", ["producer_version", "hop.product_version"])
@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_a_version_field_takes_only_a_version(family, field, value):
    build, model = FAMILIES[family]
    payload = build()
    if field == "producer_version":
        payload["producer_version"] = value
    else:
        payload["provenance"]["chain"][-1]["product_version"] = value
    with pytest.raises(ValidationError):
        model.model_validate(payload)


@pytest.mark.parametrize("value", ["sudo rm -rf / && x", "Edge", "edge.corp", "e" * 65])
def test_a_product_name_takes_only_an_identity_name(value):
    payload = golden_advisory_context()
    payload["producer_product"] = value
    payload["provenance"]["chain"][-1]["product"] = value
    with pytest.raises(ValidationError):
        AdvisoryContextEnvelope.model_validate(payload)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.normalized_fact.__setitem__("command", "x"),
        lambda r: r.normalized_fact.__setitem__("x", float("nan")),
        lambda r: r.vendor_extensions[0].body.__setitem__("x", 1),
    ],
    ids=["directive", "nan", "extension-digest"],
)
def test_a_mutated_record_cannot_be_canonicalized_digested_or_replay_compared(mutate):
    record = ExternalObservationEnvelope.model_validate(golden_external_observation())
    mutate(record)
    with pytest.raises(ValidationError):
        canonical_external_security_json(record)
    with pytest.raises(ValidationError):
        canonical_digest(record)


def test_model_copy_cannot_bypass_validation_into_a_digest():
    record = ExposureChangeProposal.model_validate(golden_exposure_proposal())
    copied = record.model_copy(update={"decision_ref": "environment:golden-decoy-1"})
    with pytest.raises(ValidationError):
        assert_no_replay_extension(record, copied)


@pytest.mark.parametrize("value", [True, "60", 60.0])
def test_max_rollback_seconds_is_a_strict_int(value):
    payload = golden_exposure_proposal()
    payload["rollback_requirement"]["max_rollback_seconds"] = value
    with pytest.raises(ValidationError):
        ExposureChangeProposal.model_validate(payload)


@pytest.mark.parametrize("gaps", [("",), ("a\nb",), ("see host:db01",)])
def test_a_coverage_gap_must_be_non_empty_free_text(gaps):
    with pytest.raises(ValidationError):
        TelemetryCoverage(coverage_complete=False, gaps=gaps)


def test_counts_cannot_be_bools():
    with pytest.raises(ValidationError):
        TelemetryCoverage(coverage_complete=True, sources_expected=True, sources_reporting=True)


def test_an_unrepresentable_source_label_is_kept_as_a_marker_not_as_text():
    record = DeviceChangeObservation.model_validate(
        _with(golden_device_change_applied(), status="rm -rf /; contained")
    )
    assert record.status == "unknown"
    assert record.source_status_label == "unrepresentable"
