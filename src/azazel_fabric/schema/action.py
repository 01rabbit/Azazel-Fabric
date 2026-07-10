"""Action intent and abstract action-plan descriptions.

`ActionIntent` describes an *intended* action shape. The plan classes
(`ObservePlan`..`ReleasePlan`) are abstract, data-only descriptions of what a
plan of that kind looks like. Neither carries execution logic: converting a
plan into an nft/tc/OpenCanary action stays entirely inside the Edge/Gadget
adapters. See architecture.md §4 and design-principles.md §3.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from azazel_fabric.schema.evidence import EvidenceRef

ActionKind = Literal[
    "observe",
    "notify",
    "throttle",
    "redirect",
    "isolate",
    "decoy",
    "release",
]


class ActionIntent(BaseModel):
    """An intended action shape — not an executor, not a device command."""

    kind: ActionKind = Field(..., description="The kind of action intended.")
    target: str = Field(
        ...,
        description="Opaque, product-defined identifier (IP, session id, device id).",
    )
    issued_by: str = Field(..., description="Component/product that issued the intent.")
    evidence: list[EvidenceRef] = Field(
        default_factory=list, description="Supporting evidence references."
    )
    trace_id: str = Field(..., description="Correlates with audit/decision records.")


class ActionPlan(BaseModel):
    """Abstract, data-only base for a plan of a given action kind.

    Holds no execution logic. `parameters` is a loosely-typed, product-defined
    body; product adapters interpret it when they turn a plan into a real
    action.
    """

    kind: ActionKind
    parameters: dict[str, Any] = Field(default_factory=dict)


class ObservePlan(ActionPlan):
    kind: Literal["observe"] = "observe"


class NotifyPlan(ActionPlan):
    kind: Literal["notify"] = "notify"


class ThrottlePlan(ActionPlan):
    kind: Literal["throttle"] = "throttle"


class RedirectPlan(ActionPlan):
    kind: Literal["redirect"] = "redirect"


class IsolatePlan(ActionPlan):
    kind: Literal["isolate"] = "isolate"


class DecoyPlan(ActionPlan):
    kind: Literal["decoy"] = "decoy"


class ReleasePlan(ActionPlan):
    kind: Literal["release"] = "release"
