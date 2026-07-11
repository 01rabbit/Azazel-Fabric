"""Shared test factories + invariant assertions for Fabric consumers.

Lets each product's CI assert it still satisfies the shared contract without
depending on another product's test suite (design-principles §2). **No pytest
dependency** — every export is a plain function usable from any test framework
(a ``test`` extra exists for consumers that want pytest itself). Factories build
valid Fabric objects (``make_*`` populated, ``minimal_*`` required-only);
:func:`assert_advisory_only` and friends assert the safety invariants.
"""

from azazel_fabric.testing.factories import (
    FIXED_TS,
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
from azazel_fabric.testing.invariants import (
    assert_advisory_only,
    assert_behavioral_absent_not_null,
)

__all__ = [
    "FIXED_TS",
    # factories — make_*
    "make_mode_state",
    "make_state_snapshot",
    "make_action_intent",
    "make_status_view",
    "make_audit_event",
    "make_cti_context_request",
    "make_cti_context_response",
    # factories — minimal_*
    "minimal_mode_state",
    "minimal_state_snapshot",
    "minimal_status_view",
    "minimal_audit_event",
    "minimal_cti_context_request",
    "minimal_cti_context_response",
    # invariants
    "assert_advisory_only",
    "assert_behavioral_absent_not_null",
]
