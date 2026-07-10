"""Shared Pydantic schemas for the Azazel series.

Pure data shapes for state, mode, action intent, evidence, decision
explanation, audit event, and trust capsule. Describing a decision that
already happened is not the same as making it — see design-principles.md §1.
"""

from azazel_covenant.schema.action import (
    ActionIntent,
    ActionKind,
    ActionPlan,
    DecoyPlan,
    IsolatePlan,
    NotifyPlan,
    ObservePlan,
    RedirectPlan,
    ReleasePlan,
    ThrottlePlan,
)
from azazel_covenant.schema.audit import AuditEvent
from azazel_covenant.schema.decision import DecisionExplanation
from azazel_covenant.schema.evidence import EvidenceRef
from azazel_covenant.schema.mode import KNOWN_MODE_NAMES, ModeState
from azazel_covenant.schema.state import KNOWN_PRODUCTS, StateSnapshot
from azazel_covenant.schema.trust import TrustCapsule

__all__ = [
    "ActionIntent",
    "ActionKind",
    "ActionPlan",
    "ObservePlan",
    "NotifyPlan",
    "ThrottlePlan",
    "RedirectPlan",
    "IsolatePlan",
    "DecoyPlan",
    "ReleasePlan",
    "AuditEvent",
    "DecisionExplanation",
    "EvidenceRef",
    "ModeState",
    "KNOWN_MODE_NAMES",
    "StateSnapshot",
    "KNOWN_PRODUCTS",
    "TrustCapsule",
]
