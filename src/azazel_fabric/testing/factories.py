"""Factory functions for Fabric contract objects, for consumer test suites.

Plain functions — **no pytest dependency**. A consumer's CI (pytest, unittest,
or anything else) calls these to get a valid, filled-in Fabric object without
re-deriving the field list, so a schema change surfaces in one place. Every
factory accepts keyword overrides and returns a fully-valid model.

Two flavours per shape:

- ``make_*`` — a realistic, fully-populated valid instance.
- ``minimal_*`` — only the required fields, everything optional left at default.

Timestamps are fixed constants, never ``datetime.now()`` — factory output is
deterministic so a consumer's golden tests do not flake.
"""

from __future__ import annotations

from typing import Any

from azazel_fabric.cti_contracts.advisory import BehavioralCtiBlock
from azazel_fabric.cti_contracts.context import (
    CtiContextRequest,
    CtiContextResponse,
    IocMatch,
)
from azazel_fabric.schema.action import ActionIntent
from azazel_fabric.schema.audit import AuditEvent
from azazel_fabric.schema.mode import ModeState
from azazel_fabric.schema.state import StateSnapshot
from azazel_fabric.view.status import HealthDimension, StatusView

# A fixed instant used across all factories, so output is deterministic.
FIXED_TS = "2026-07-10T00:00:00Z"


def make_mode_state(**overrides: Any) -> ModeState:
    """A valid :class:`ModeState` (defaults to ``shield`` since ``FIXED_TS``)."""
    data: dict[str, Any] = {
        "name": "shield",
        "since": FIXED_TS,
        "reason": "factory default",
    }
    data.update(overrides)
    return ModeState(**data)


def minimal_mode_state(**overrides: Any) -> ModeState:
    """A :class:`ModeState` with only its required fields set."""
    data: dict[str, Any] = {"name": "portal", "since": FIXED_TS}
    data.update(overrides)
    return ModeState(**data)


def make_state_snapshot(**overrides: Any) -> StateSnapshot:
    """A valid, populated :class:`StateSnapshot`."""
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "product": "edge",
        "mode": make_mode_state(),
        "generated_at": FIXED_TS,
        "trace_id": "trace-fixture",
        "summary": {"stage": "NORMAL"},
    }
    data.update(overrides)
    return StateSnapshot(**data)


def minimal_state_snapshot(**overrides: Any) -> StateSnapshot:
    """A :class:`StateSnapshot` with only required fields (empty ``summary``)."""
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "product": "edge",
        "mode": minimal_mode_state(),
        "generated_at": FIXED_TS,
        "trace_id": "trace-fixture",
    }
    data.update(overrides)
    return StateSnapshot(**data)


def make_action_intent(**overrides: Any) -> ActionIntent:
    """A valid :class:`ActionIntent` (an ``isolate`` intent by default)."""
    data: dict[str, Any] = {
        "kind": "isolate",
        "target": "10.0.0.5",
        "issued_by": "edge.arbiter",
        "trace_id": "trace-fixture",
    }
    data.update(overrides)
    return ActionIntent(**data)


def make_status_view(**overrides: Any) -> StatusView:
    """A valid, populated :class:`StatusView`."""
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "product": "edge",
        "generated_at": FIXED_TS,
        "trace_id": "trace-fixture",
        "mode": make_mode_state(),
        "posture": "normal",
        "headline": "edge · shield · normal",
        "reasons": ["factory default"],
        "health": [HealthDimension(key="availability", label="ok", status="ok")],
        "evidence_ids": ["ev-1"],
    }
    data.update(overrides)
    return StatusView(**data)


def minimal_status_view(**overrides: Any) -> StatusView:
    """A :class:`StatusView` with only its required fields set."""
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "product": "edge",
        "generated_at": FIXED_TS,
        "mode": minimal_mode_state(),
    }
    data.update(overrides)
    return StatusView(**data)


def make_audit_event(**overrides: Any) -> AuditEvent:
    """A valid, populated :class:`AuditEvent`."""
    data: dict[str, Any] = {
        "event_id": "edge:decision.recorded:" + FIXED_TS,
        "trace_id": "trace-fixture",
        "timestamp": FIXED_TS,
        "product": "edge",
        "event_type": "decision.recorded",
        "payload": {"action": "isolate"},
        "config_hash": "cfg-abc123",
    }
    data.update(overrides)
    return AuditEvent(**data)


def minimal_audit_event(**overrides: Any) -> AuditEvent:
    """An :class:`AuditEvent` with only required fields (empty ``payload``)."""
    data: dict[str, Any] = {
        "event_id": "e-1",
        "trace_id": "trace-fixture",
        "timestamp": FIXED_TS,
        "product": "edge",
        "event_type": "heartbeat",
    }
    data.update(overrides)
    return AuditEvent(**data)


def make_cti_context_request(**overrides: Any) -> CtiContextRequest:
    """A valid :class:`CtiContextRequest` with indicators."""
    data: dict[str, Any] = {
        "request_id": "req-fixture",
        "source_product": "edge",
        "indicators": ["1.2.3.4", "evil.example"],
        "trace_id": "trace-fixture",
    }
    data.update(overrides)
    return CtiContextRequest(**data)


def minimal_cti_context_request(**overrides: Any) -> CtiContextRequest:
    """A :class:`CtiContextRequest` with only required fields (no indicators)."""
    data: dict[str, Any] = {
        "request_id": "req-fixture",
        "source_product": "edge",
        "trace_id": "trace-fixture",
    }
    data.update(overrides)
    return CtiContextRequest(**data)


def make_cti_context_response(**overrides: Any) -> CtiContextResponse:
    """A valid, populated :class:`CtiContextResponse` (advisory only).

    Includes a match and a non-empty ``behavioral_cti`` block whose fields are
    all advisory hints — never a directive — so the object exercises the
    advisory-only path while staying valid.
    """
    data: dict[str, Any] = {
        "request_id": "req-fixture",
        "matches": [IocMatch(indicator="1.2.3.4", confidence=0.9, reason=["known c2"])],
        "behavioral_cti": BehavioralCtiBlock(
            summary="repeated scans", suggested_posture="watch"
        ),
        "advisory_notice": "informational only",
        "limitations": ["feed stale > 24h"],
        "generated_at": FIXED_TS,
    }
    data.update(overrides)
    return CtiContextResponse(**data)


def minimal_cti_context_response(**overrides: Any) -> CtiContextResponse:
    """A :class:`CtiContextResponse` with only required fields.

    No matches and no ``behavioral_cti`` — the "Knowledge said nothing" shape,
    which is a normal, expected state, not an error.
    """
    data: dict[str, Any] = {
        "request_id": "req-fixture",
        "generated_at": FIXED_TS,
    }
    data.update(overrides)
    return CtiContextResponse(**data)
