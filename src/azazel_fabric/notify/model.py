"""Shared notification payload model (`contracts.md` §4).

`NotificationEvent` is the one payload shape every Azazel notification transport
(ntfy, Mattermost, an SSE bridge) consumes. Transports do not each invent their
own competing shape — they map *this* shape onto their wire format (see
:mod:`azazel_fabric.notify.transports`). This is payload shape only: no
product-specific copy, tone, or UI, and no transport/network logic.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Severity vocabulary (contracts.md §4). Closed set on purpose: a notification
# severity that a transport cannot map is worse than one that is constrained.
Severity = Literal["info", "warning", "critical"]
SEVERITIES: tuple[str, ...] = ("info", "warning", "critical")


class NotificationEvent(BaseModel):
    """One notification, transport-agnostic."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., description="Opaque notification identifier.")
    product: str = Field(..., description="Emitting product.")
    severity: Severity = Field(..., description='"info" | "warning" | "critical".')
    title: str = Field(..., description="Short, operator-facing headline.")
    body: str = Field(..., description="Longer operator-facing detail.")
    trace_id: str | None = Field(
        default=None, description="Correlates with audit/state records, if any."
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp.")
