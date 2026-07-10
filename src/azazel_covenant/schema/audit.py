"""Audit event (`AuditEvent`).

Standard JSONL audit-log record shape. Common standardizes the *envelope*;
the content and triggering of an audit event stays product-owned.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """One audit-log record."""

    event_id: str = Field(..., description="Opaque event identifier.")
    trace_id: str = Field(..., description="Correlates related records.")
    timestamp: str = Field(..., description="ISO 8601 event timestamp.")
    product: str = Field(..., description="Emitting product.")
    event_type: str = Field(..., description="Product-defined event type.")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Product-defined event body."
    )
    config_hash: str | None = Field(
        default=None, description="Optional hash of the active config."
    )
    hmac: str | None = Field(
        default=None, description="Optional tamper-evidence signature."
    )
