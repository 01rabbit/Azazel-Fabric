"""System state snapshot (`StateSnapshot`)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from azazel_common.schema.mode import ModeState

# Known products. Open enum: future tools (e.g. "boot") may emit snapshots,
# so the field type stays `str`. See architecture.md §1 and design-principles
# §4.4 (products extend, they are not a fixed set).
KNOWN_PRODUCTS = ("edge", "gadget", "cti")


class StateSnapshot(BaseModel):
    """The single shape every status surface reads to render current state."""

    schema_version: str = Field(..., description='Schema version, e.g. "1.0".')
    product: str = Field(
        ..., description="Emitting product; open enum, see KNOWN_PRODUCTS."
    )
    mode: ModeState = Field(..., description="Current operating mode.")
    generated_at: str = Field(..., description="ISO 8601 snapshot timestamp.")
    trace_id: str = Field(..., description="Correlates with AuditEvent/TrustCapsule.")
    summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Product-specific, loosely-typed status payload.",
    )
