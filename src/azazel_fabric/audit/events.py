"""Projection helpers for the shared `AuditEvent` (`contracts.md` §1).

These helpers standardize the *envelope* an audit event is written in and the
*conventions* for its identifiers. The content and triggering of an audit event
stay product-owned — Fabric only fixes the shape.

Non-goals (owner decision, 2026-07-10/11), stated so no future reader mistakes
this module for more than it is:

- **No hash chain.** This module does not link one event to the previous one,
  does not compute a rolling digest, and does not maintain any chain state.
- **No chain verification.** There is no "verify the chain is intact" function
  here, and there never will be in Fabric.
- **Chains stay product-local.** Edge's P0 hash-chain / tamper-evidence audit
  is deliberately out of scope for Fabric and lives entirely in Edge. Fabric
  ships only the shared `AuditEvent` projection (this module) — the format the
  event is written in, not the integrity mechanism protecting the log.

The ``config_hash`` and ``hmac`` fields on :class:`AuditEvent` are carried
verbatim if a product supplies them; this module neither computes nor checks
them.
"""

from __future__ import annotations

from typing import Any

from azazel_fabric.schema.audit import AuditEvent


def make_event_id(product: str, event_type: str, timestamp: str, *, suffix: str = "") -> str:
    """Build a conventional, deterministic ``event_id`` from its parts.

    Convention: ``<product>:<event_type>:<timestamp>[:<suffix>]``. Deterministic
    — the same inputs always produce the same id, and no clock or randomness is
    read here (a product that wants a random component passes it as ``suffix``).
    This is only a naming convention; a product may use its own id scheme and
    still emit a valid :class:`AuditEvent`.
    """
    parts = [product, event_type, timestamp]
    if suffix:
        parts.append(suffix)
    return ":".join(parts)


def project_audit_event(
    *,
    product: str,
    event_type: str,
    timestamp: str,
    trace_id: str,
    payload: dict[str, Any] | None = None,
    event_id: str | None = None,
    config_hash: str | None = None,
    hmac: str | None = None,
) -> AuditEvent:
    """Project product-native audit fields onto the shared :class:`AuditEvent`.

    ``event_id`` defaults to :func:`make_event_id` when not supplied. This is a
    pure shape-projection: it computes no integrity value (``config_hash`` and
    ``hmac`` are passed through untouched — see this module's non-goals).
    """
    return AuditEvent(
        event_id=event_id or make_event_id(product, event_type, timestamp),
        trace_id=trace_id,
        timestamp=timestamp,
        product=product,
        event_type=event_type,
        payload=dict(payload or {}),
        config_hash=config_hash,
        hmac=hmac,
    )
