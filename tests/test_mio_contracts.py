"""Contract tests for the R1a M.I.O. dual-cognition family.

The specification these encode: a model's answer is advisory and inert, a
sanitized frame cannot carry restricted content off the node, and a merge keeps
every claim's provenance and presents contradictions separately instead of
resolving them.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from azazel_fabric.deception_contracts.validation import BANNED_RUNTIME_DIRECTIVE_FIELDS
from azazel_fabric.mio_contracts import (
    BANNED_MIO_DIRECTIVE_FIELDS,
    AdvisoryResult,
    AliasScope,
    Claim,
    ClaimSet,
    Disagreement,
    MergedAdvisory,
    RedactionRecord,
    SanitizedRemoteFrame,
    SituationFrame,
    assert_advisory_inert,
    assert_claim_provenance_preserved,
    assert_frame_sanitized_for_egress,
    assert_no_mio_directives,
    canonical_mio_json,
)
from azazel_fabric.provisioning_contracts import canonical_contract_json
from azazel_fabric.testing import load_golden_provisioning


def situation_frame() -> SituationFrame:
    return SituationFrame.model_validate(load_golden_provisioning("situation_frame"))


def sanitized_frame() -> SanitizedRemoteFrame:
    return SanitizedRemoteFrame.model_validate(load_golden_provisioning("sanitized_remote_frame"))


def local_result() -> AdvisoryResult:
    return AdvisoryResult.model_validate(load_golden_provisioning("advisory_result_local"))


def remote_result() -> AdvisoryResult:
    return AdvisoryResult.model_validate(load_golden_provisioning("advisory_result_remote"))


def merged() -> MergedAdvisory:
    return MergedAdvisory.model_validate(load_golden_provisioning("merged_advisory"))


# ---------------------------------------------------------------------------
# Advisory results are inert
# ---------------------------------------------------------------------------


def test_advisory_result_is_advisory_inert_and_link_free():
    for result in (local_result(), remote_result()):
        assert result.authority == "advisory_only"
        assert result.executable is False
        assert result.rendering == "inert_text"
        assert result.may_request_followup is False
        assert result.contains_links is False
        assert_advisory_inert(result)


def test_advisory_result_cannot_be_made_executable():
    payload = load_golden_provisioning("advisory_result_executable")
    assert payload["executable"] is True
    with pytest.raises(ValidationError):
        AdvisoryResult.model_validate(payload)
    with pytest.raises(ValueError, match="claims to be executable"):
        assert_advisory_inert(payload)


def test_remote_answer_cannot_request_follow_up_disclosure():
    # A remote response must not be able to ask for more data; every follow-up
    # is a new locally constructed and audited sanitized frame.
    payload = load_golden_provisioning("advisory_result_followup")
    assert "follow_up_request" in payload
    with pytest.raises(ValidationError):
        AdvisoryResult.model_validate(payload)
    with pytest.raises(ValueError, match="directive/tool-call/link/follow-up"):
        assert_no_mio_directives(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tool_call", {"name": "shell"}),
        ("function_call", {"name": "fetch"}),
        ("url", "https://example.invalid/x"),
        ("link", "https://example.invalid/y"),
        ("file_path", "/etc/shadow"),
        ("instructions", "run this"),
        ("required_action", "isolate"),
        ("request_disclosure", "source address"),
        ("shell_command", "rm -rf /"),
    ],
)
def test_directive_tool_call_and_link_fields_are_rejected(field, value):
    with pytest.raises(ValueError, match="directive/tool-call/link/follow-up"):
        assert_no_mio_directives({"content": {field: value}})


def test_mio_ban_never_drifts_from_the_canonical_runtime_directive_ban():
    # The mio module restates these names to stay import-light; this keeps the
    # two definitions from diverging.
    assert BANNED_RUNTIME_DIRECTIVE_FIELDS <= BANNED_MIO_DIRECTIVE_FIELDS


def test_narrative_text_is_not_policed_but_cannot_become_actionable():
    # Fabric bounds the shape, not the prose. An imperative-sounding sentence is
    # still valid data -- what must be impossible is a machine-actionable field.
    result = remote_result().model_copy(
        update={"narrative_text": "Isolate 198.51.100.9 immediately."}
    )
    assert_advisory_inert(result)
    payload = result.model_dump(mode="json")
    payload["required_action"] = "isolate"
    with pytest.raises(ValidationError):
        AdvisoryResult.model_validate(payload)


# ---------------------------------------------------------------------------
# Sanitizer boundary
# ---------------------------------------------------------------------------


def test_sanitized_frame_declares_no_raw_evidence_and_denies_on_ambiguity():
    frame = sanitized_frame()
    assert frame.contains_raw_evidence is False
    assert frame.ambiguity_resolution == "deny_on_ambiguity"
    assert frame.privacy_class in ("public", "internal")
    assert_frame_sanitized_for_egress(frame)


def test_restricted_frame_cannot_be_a_sanitized_remote_frame():
    payload = load_golden_provisioning("sanitized_remote_frame_restricted")
    assert payload["privacy_class"] == "restricted"
    with pytest.raises(ValidationError):
        SanitizedRemoteFrame.model_validate(payload)
    with pytest.raises(ValueError, match="must not leave the node"):
        assert_frame_sanitized_for_egress(payload)


def test_sanitized_frame_cannot_claim_to_carry_raw_evidence():
    payload = load_golden_provisioning("sanitized_remote_frame")
    payload["contains_raw_evidence"] = True
    with pytest.raises(ValidationError):
        SanitizedRemoteFrame.model_validate(payload)


def test_redaction_records_are_complete_and_unambiguous():
    frame = sanitized_frame()
    aliased = [r for r in frame.redactions if r.action == "aliased"]
    assert aliased and all(r.alias_ref for r in aliased)
    with pytest.raises(ValidationError, match="alias_ref"):
        RedactionRecord(
            field_ref="content.x",
            privacy_class="restricted",
            action="aliased",
            reason="missing alias",
        )


def test_two_subjects_cannot_collapse_into_one_alias():
    payload = load_golden_provisioning("sanitized_remote_frame")
    payload["redactions"][1]["action"] = "aliased"
    payload["redactions"][1]["alias_ref"] = payload["redactions"][0]["alias_ref"]
    with pytest.raises(ValidationError, match="share one alias_ref"):
        SanitizedRemoteFrame.model_validate(payload)


def test_alias_scope_is_bounded_to_a_mission_or_request_generation():
    scope = sanitized_frame().alias_scope
    assert scope.scope_kind in ("mission", "request")
    assert scope.key_generation >= 0
    with pytest.raises(ValidationError):
        AliasScope(scope_kind="global", scope_id="x", key_generation=0, expires_at="2026-09-08T00:00:00+00:00")


def test_local_situation_frame_carries_evidence_refs_not_raw_evidence():
    frame = situation_frame()
    assert frame.evidence_refs
    assert frame.authority == "descriptive_only"
    assert_no_mio_directives(frame.model_dump(mode="json"))


def test_unbounded_model_payload_fails_closed():
    payload = load_golden_provisioning("situation_frame")
    payload["content"] = {f"k{i}": i for i in range(65)}
    with pytest.raises(ValidationError):
        SituationFrame.model_validate(payload)


# ---------------------------------------------------------------------------
# Provenance-preserving merge
# ---------------------------------------------------------------------------


def test_merge_keeps_every_claim_and_its_provenance():
    output = merged()
    sources = {claim.source for claim in output.claim_set.claims}
    assert sources == {"local_model", "remote_model"}
    for claim in output.claim_set.claims:
        assert claim.model_ref and claim.input_refs
    assert output.cognition_state == "hybrid"
    assert_claim_provenance_preserved(output.claim_set)


def test_contradictions_stay_separate_and_are_never_resolved_away():
    output = merged()
    assert len(output.disagreements) == 1
    disagreement = output.disagreements[0]
    assert disagreement.resolution == "presented_separately"
    assert set(disagreement.claim_refs) == {"claim-local-1", "claim-remote-1"}
    payload = output.model_dump(mode="json")
    payload["disagreements"][0]["resolution"] = "remote_wins"
    with pytest.raises(ValidationError):
        MergedAdvisory.model_validate(payload)


def test_a_merge_cannot_drop_a_claim_it_reports_a_disagreement_about():
    payload = load_golden_provisioning("merged_advisory")
    payload["claim_set"]["claims"] = [payload["claim_set"]["claims"][0]]
    with pytest.raises(ValidationError, match="outside the merged claim set"):
        MergedAdvisory.model_validate(payload)


def test_a_model_sourced_claim_must_name_its_model():
    with pytest.raises(ValidationError, match="model_ref"):
        Claim(claim_id="c1", statement="x", source="remote_model")


def test_claim_set_rejects_repeated_claim_ids():
    payload = load_golden_provisioning("merged_advisory")["claim_set"]
    payload["claims"] = [payload["claims"][0], payload["claims"][0]]
    with pytest.raises(ValidationError, match="repeats claim_id"):
        ClaimSet.model_validate(payload)


def test_merged_output_is_still_advisory_and_inert():
    output = merged()
    assert output.authority == "advisory_only"
    assert output.executable is False
    assert output.rendering == "inert_text"
    payload = output.model_dump(mode="json")
    payload["executable"] = True
    with pytest.raises(ValidationError):
        MergedAdvisory.model_validate(payload)


def test_disagreement_needs_at_least_two_claims():
    with pytest.raises(ValidationError):
        Disagreement(topic="x", claim_refs=("only-one",))


# ---------------------------------------------------------------------------
# Canonical bytes
# ---------------------------------------------------------------------------


def test_mio_canonical_round_trip_is_byte_identical():
    for name in (
        "situation_frame",
        "sanitized_remote_frame",
        "advisory_result_local",
        "advisory_result_remote",
        "merged_advisory",
    ):
        payload = load_golden_provisioning(name)
        once = canonical_mio_json(payload)
        assert once == canonical_mio_json(json.loads(once)), name


def test_mio_canonical_form_matches_the_provisioning_canonical_form():
    payload = load_golden_provisioning("situation_frame")
    assert canonical_mio_json(payload) == canonical_contract_json(payload)
