"""Tests for the CTI advisory contract.

The advisory-only boundary and the `behavioral_cti` omission-when-absent
semantics are the load-bearing invariants of v0.1.0, so they are covered
explicitly here.
"""

import pytest
from pydantic import ValidationError

from azazel_fabric.cti_contracts import (
    BANNED_DIRECTIVE_FIELDS,
    BehavioralCtiBlock,
    CtiContextRequest,
    CtiContextResponse,
    CtiEventBatch,
    CtiFlowBatch,
    CtiReactionBatch,
    IocMatch,
    assert_advisory_only,
    is_advisory_only,
)


def test_ingest_batches_round_trip():
    for cls in (CtiEventBatch, CtiFlowBatch, CtiReactionBatch):
        batch = cls(
            batch_id="b-1",
            source_product="gadget",
            source_device_id="dev-1",
            generated_at="2026-07-09T00:00:00Z",
            items=[{"k": "v"}],
        )
        assert cls.model_validate(batch.model_dump()) == batch


def test_batch_rejects_unknown_source_product():
    with pytest.raises(ValidationError):
        CtiEventBatch(
            batch_id="b-1",
            source_product="cti",  # only edge/gadget send batches
            source_device_id="dev-1",
            generated_at="2026-07-09T00:00:00Z",
        )


def test_context_request_round_trip():
    req = CtiContextRequest(
        request_id="req-1",
        source_product="edge",
        indicators=["1.2.3.4", "evil.example"],
        trace_id="trace-1",
    )
    assert CtiContextRequest.model_validate(req.model_dump()) == req


def test_behavioral_absent_is_omitted_not_null():
    resp = CtiContextResponse(request_id="req-1", generated_at="2026-07-09T00:00:00Z")
    dumped = resp.model_dump()
    # Absent, never null: the key must not be present at all.
    assert "behavioral_cti" not in dumped
    assert "null" not in resp.model_dump_json()
    assert resp.has_behavioral_cti is False


def test_empty_behavioral_block_normalizes_to_absent():
    resp = CtiContextResponse(
        request_id="req-1",
        generated_at="2026-07-09T00:00:00Z",
        behavioral_cti=BehavioralCtiBlock(),
    )
    assert resp.behavioral_cti is None
    assert "behavioral_cti" not in resp.model_dump()
    assert resp.has_behavioral_cti is False


def test_missing_and_empty_block_are_indistinguishable():
    missing = CtiContextResponse(request_id="r", generated_at="t")
    empty = CtiContextResponse(
        request_id="r", generated_at="t", behavioral_cti=BehavioralCtiBlock()
    )
    assert missing.model_dump() == empty.model_dump()


def test_non_empty_behavioral_block_is_present():
    resp = CtiContextResponse(
        request_id="req-1",
        generated_at="2026-07-09T00:00:00Z",
        behavioral_cti=BehavioralCtiBlock(suggested_posture="watch"),
    )
    assert resp.has_behavioral_cti is True
    assert resp.model_dump()["behavioral_cti"]["suggested_posture"] == "watch"


@pytest.mark.parametrize("field", BANNED_DIRECTIVE_FIELDS)
def test_directive_fields_rejected(field):
    with pytest.raises(ValidationError):
        CtiContextResponse(
            request_id="req-1",
            generated_at="2026-07-09T00:00:00Z",
            **{field: "do this"},
        )


def test_advisory_only_helpers():
    assert is_advisory_only({"matches": []}) is True
    assert is_advisory_only({"must_execute": True}) is False
    with pytest.raises(ValueError):
        assert_advisory_only({"override": "x"})


def test_ioc_match_confidence_bounds():
    with pytest.raises(ValidationError):
        IocMatch(indicator="1.2.3.4", confidence=2.0)


def test_context_response_round_trip_with_matches():
    resp = CtiContextResponse(
        request_id="req-1",
        matches=[IocMatch(indicator="1.2.3.4", confidence=0.9, reason=["known c2"])],
        advisory_notice="informational only",
        limitations=["feed stale > 24h"],
        generated_at="2026-07-09T00:00:00Z",
    )
    restored = CtiContextResponse.model_validate_json(resp.model_dump_json())
    assert restored == resp
    assert restored.matches[0].indicator == "1.2.3.4"
