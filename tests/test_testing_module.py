"""Tests for `azazel_fabric.testing` — factories and invariant assertions.

Load-bearing properties: every factory produces a valid model (make_* populated,
minimal_* required-only), factories are deterministic and override-friendly, the
advisory-only assertion catches directive fields, and the module imports without
pytest present in its own dependency surface.
"""

import pytest

from azazel_fabric.cti_contracts import CtiContextRequest, CtiContextResponse
from azazel_fabric.schema import AuditEvent, ModeState, StateSnapshot
from azazel_fabric.testing import (
    FIXED_TS,
    assert_advisory_only,
    assert_behavioral_absent_not_null,
    make_action_intent,
    make_audit_event,
    make_cti_context_request,
    make_cti_context_response,
    make_mode_state,
    make_state_snapshot,
    make_status_view,
    minimal_audit_event,
    minimal_cti_context_request,
    minimal_cti_context_response,
    minimal_mode_state,
    minimal_state_snapshot,
    minimal_status_view,
)
from azazel_fabric.view import StatusView


def test_make_factories_produce_valid_models():
    assert isinstance(make_mode_state(), ModeState)
    assert isinstance(make_state_snapshot(), StateSnapshot)
    assert isinstance(make_status_view(), StatusView)
    assert isinstance(make_audit_event(), AuditEvent)
    assert isinstance(make_cti_context_request(), CtiContextRequest)
    assert isinstance(make_cti_context_response(), CtiContextResponse)
    assert make_action_intent().kind == "isolate"


def test_minimal_factories_produce_valid_models():
    assert isinstance(minimal_mode_state(), ModeState)
    assert isinstance(minimal_state_snapshot(), StateSnapshot)
    assert isinstance(minimal_status_view(), StatusView)
    assert isinstance(minimal_audit_event(), AuditEvent)
    assert isinstance(minimal_cti_context_request(), CtiContextRequest)
    assert isinstance(minimal_cti_context_response(), CtiContextResponse)


def test_factories_round_trip_through_json():
    for obj in (
        make_state_snapshot(),
        make_status_view(),
        make_audit_event(),
        make_cti_context_request(),
    ):
        restored = type(obj).model_validate_json(obj.model_dump_json())
        assert restored == obj


def test_factories_are_deterministic():
    assert make_state_snapshot() == make_state_snapshot()
    assert make_audit_event().timestamp == FIXED_TS


def test_overrides_apply():
    snap = make_state_snapshot(product="gadget")
    assert snap.product == "gadget"
    ev = minimal_audit_event(event_type="heartbeat", product="cti")
    assert ev.event_type == "heartbeat"
    assert ev.product == "cti"


def test_make_response_is_advisory_and_has_behavioral_signal():
    resp = make_cti_context_response()
    assert_advisory_only(resp)  # does not raise
    assert resp.has_behavioral_cti is True


def test_minimal_response_has_absent_behavioral_signal():
    resp = minimal_cti_context_response()
    assert_advisory_only(resp)
    assert_behavioral_absent_not_null(resp)  # does not raise


def test_assert_advisory_only_catches_directive_field_in_mapping():
    with pytest.raises(AssertionError):
        assert_advisory_only({"must_execute": True})


def test_assert_behavioral_absent_not_null_fails_when_present():
    resp = make_cti_context_response()  # has a behavioral block
    with pytest.raises(AssertionError):
        assert_behavioral_absent_not_null(resp)


def test_testing_module_has_no_pytest_dependency():
    # The module itself must be importable without pytest — its functions are
    # plain, framework-agnostic. (pytest is present here only because this test
    # file runs under it; assert the module doesn't import it at module scope.)
    import inspect

    import azazel_fabric.testing.factories as factories
    import azazel_fabric.testing.invariants as invariants

    for mod in (factories, invariants):
        src = inspect.getsource(mod)
        assert "import pytest" not in src
