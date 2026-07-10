"""Decision explanation (`DecisionExplanation`).

The shared shape for "why did the system do this," independent of which
product's arbiter produced it. This standardizes how a decision is *written
down*; it does not make the decision. See architecture.md §3.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from azazel_fabric.schema.action import ActionIntent


class DecisionExplanation(BaseModel):
    """Serialization shape for a decision an arbiter already made."""

    selected_action: ActionIntent = Field(..., description="The chosen action intent.")
    why_chosen: str = Field(..., description="Why this action was selected.")
    why_not_others: list[str] = Field(
        default_factory=list, description="Why the alternatives were not selected."
    )
    release_condition: str | None = Field(
        default=None,
        description="Condition under which this decision should be revisited.",
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Optional confidence, 0.0-1.0."
    )
    trace_id: str = Field(..., description="Correlates with audit/state records.")
