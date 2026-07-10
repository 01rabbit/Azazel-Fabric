"""Shared status view-model (`StatusView`).

`StatusView` is the normalized data an Azazel status surface (Web UI, TUI,
E-Paper) reads to present "what is the system doing right now" — the *view-model*,
not the renderer. Common owns this data contract so Edge and Gadget can present
the same status the same way; each product keeps its own renderer.

Design stance (see `docs/design-principles.md` §3.1):

- **Edge-lineage vocabulary.** The first-class fields (posture, headline,
  reasons, operator wording, next actions, current action, health dimensions,
  evidence) follow Edge's more mature status model.
- **Generalized superset, never a subset.** Every product-specific field that
  does not (yet) warrant a shared shape rides in `product_view`, so Gadget-only
  concepts (`DECEPTION` posture, `scapegoat` decoy state, canary-delay
  telemetry) survive round-tripping. `posture` and `HealthDimension.status`
  are open `str` enums for the same reason.
- **No judgment.** This describes a status that already exists; it does not
  decide anything. Deriving it is `build_status_view` (see `build.py`).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from azazel_covenant.schema.action import ActionIntent
from azazel_covenant.schema.mode import ModeState

# Known overall-posture words. Open enum: products may use additional values,
# so the field type stays `str`. `deception` is Gadget-specific and is a first
# member here precisely to show the superset is not Edge-only.
KNOWN_POSTURES = (
    "normal",
    "degraded",
    "contain",
    "deception",
    "lockdown",
    "unknown",
)

# Known health-dimension status words. Open enum.
KNOWN_HEALTH_STATUSES = ("ok", "warn", "critical", "unknown")


class HealthDimension(BaseModel):
    """One named health/scoring dimension a display can render as a row.

    Generalizes Edge's NOC/SOC dimension labels and Gadget's probe/degrade
    signals into a single render-agnostic row.
    """

    key: str = Field(
        ..., description='Dimension id, e.g. "availability", "security_visibility".'
    )
    label: str = Field(..., description="Human-readable label or status word.")
    status: str = Field(
        default="unknown",
        description="Status word; open enum, see KNOWN_HEALTH_STATUSES.",
    )
    detail: str | None = Field(default=None, description="Optional extra detail.")


class StatusView(BaseModel):
    """The normalized status a display reads. Edge-lineage generalized superset."""

    schema_version: str = Field(..., description='View-model version, e.g. "1.0".')
    product: str = Field(
        ..., description="Emitting product; open enum (edge/gadget/cti/...)."
    )
    generated_at: str = Field(..., description="ISO 8601 timestamp of this view.")
    trace_id: str | None = Field(
        default=None,
        description="Correlates with audit/state records; optional — not every "
        "product threads a trace_id.",
    )
    mode: ModeState = Field(..., description="Current operating mode.")
    posture: str = Field(
        default="unknown",
        description="Overall posture word; open enum, see KNOWN_POSTURES.",
    )
    headline: str = Field(
        default="", description="One-line, operator-facing status summary."
    )
    reasons: list[str] = Field(
        default_factory=list, description="Why the system is in this posture."
    )
    operator_wording: str | None = Field(
        default=None, description="Longer operator-facing narration, if any."
    )
    current_action: ActionIntent | None = Field(
        default=None, description="The action currently in effect, if any."
    )
    next_actions: list[str] = Field(
        default_factory=list,
        description="Suggested next checks/actions for the operator.",
    )
    health: list[HealthDimension] = Field(
        default_factory=list, description="Named health/scoring dimensions."
    )
    evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence references behind this status."
    )
    product_view: dict[str, Any] = Field(
        default_factory=dict,
        description="Product-specific display payload that has no shared shape "
        "yet (e.g. Gadget attack/connection blocks, Edge machine/soc_states). "
        "Carried verbatim so no product is narrowed to a subset.",
    )
