"""Tests for AuditEvent, TrustCapsule, and EvidenceRef round-trips."""

from azazel_common.schema import AuditEvent, EvidenceRef, TrustCapsule


def test_audit_event_round_trip():
    event = AuditEvent(
        event_id="e-1",
        trace_id="trace-1",
        timestamp="2026-07-09T00:00:00Z",
        product="edge",
        event_type="decision.recorded",
        payload={"action": "isolate"},
        config_hash="abc123",
    )
    restored = AuditEvent.model_validate_json(event.model_dump_json())
    assert restored == event
    assert restored.hmac is None  # optional, defaults to None


def test_trust_capsule_round_trip():
    capsule = TrustCapsule(
        trace_id="trace-1",
        config_hash="abc123",
        hmac="deadbeef",
        issued_at="2026-07-09T00:00:00Z",
    )
    assert TrustCapsule.model_validate(capsule.model_dump()) == capsule


def test_evidence_ref_round_trip():
    ref = EvidenceRef(
        evidence_id="ev-1",
        source="cti_advisory",
        trace_id="trace-1",
        observed_at="2026-07-09T00:00:00Z",
    )
    assert EvidenceRef.model_validate(ref.model_dump()) == ref
