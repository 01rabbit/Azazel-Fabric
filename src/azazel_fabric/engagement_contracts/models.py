"""Canonical adversary-engagement contracts (MITRE Engage-aligned).

These types describe engagement *intent, constraints, events, and outcomes*
across the Azazel System. They contain no planning, classification, or decision
logic: an :class:`EngagementCandidate` is a request for product-local
evaluation, never an executable command, and an :class:`EngagementAdvisory` is
advisory context that a deterministic arbiter may ignore.

Authority rule, unchanged:

    Engage expresses intent. Knowledge advises. Fabric describes.
    Edge decides and enforces.

The vocabulary is deliberately small and maps cleanly onto the bounded Azazel
actions (``observe``/``notify``/``throttle``/``redirect``/``isolate``) plus a
few decoy specializations, so a candidate can only ever request an action the
product already knows how to evaluate. Unknown enum values and unsupported
schema versions fail closed at command boundaries (see
:mod:`azazel_fabric.engagement_contracts.validation`) while staying preservable
in audit/forwarding paths. The initial wire family is ``*/v0.1`` and is additive
to existing Fabric contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# MITRE Engage-aligned operational approach the engagement pursues. Deliberately
# small; the full Engage catalog / ATT&CK<->Engage mapping lives in Knowledge
# (Azazel-Knowledge#60), not in the wire contract.
EngagementObjective = Literal[
    "collect", "detect", "prevent", "direct", "disrupt", "reassure"
]
EngagementApproach = Literal[
    "channel", "collect", "detect", "prevent", "disrupt", "reassure"
]

# Every executable activity maps 1:1 onto an existing bounded Azazel action
# (plus decoy specializations). A candidate cannot request anything the product
# arbiter does not already know how to gate.
EngagementActivity = Literal[
    "observe",
    "notify",
    "throttle",
    "redirect",
    "isolate",
    "redirect_to_decoy",
    "expose_decoy_surface",
    "collect_credentials",
]

# How the attacker behaved after a bounded action. Fact-only classification
# supplied by local evidence; never an inference about identity or intent
# (seed taxonomy: Azazel-Knowledge#29).
AttackerReaction = Literal[
    "decoy_engaged",
    "followed_decoy",
    "continued_scanning",
    "continued_slowed",
    "shifted_port",
    "shifted_protocol",
    "shifted_target",
    "auth_pattern_changed",
    "escalated",
    "disengaged",
    "unknown",
]

ADVISORY_NOTICE = (
    "Engagement advisory only. Final authority: the product-local deterministic "
    "arbiter (Azazel-Edge)."
)


class EngagementConstraint(BaseModel):
    """Hard safety bounds every executable activity must declare.

    Defaults are the safe posture: no attacker egress, no production access.
    """

    model_config = ConfigDict(extra="forbid")

    max_duration_seconds: int = Field(ge=0)
    outbound_allowed: bool = False
    production_access: bool = False
    scope: str | None = None
    termination_conditions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class EngagementTrigger(BaseModel):
    """The evidence that motivated an engagement — descriptive, not a directive."""

    model_config = ConfigDict(extra="forbid")

    attack_technique: str | None = None  # ATT&CK id (e.g. "T1110") when supported
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)


class EngagementCandidate(BaseModel):
    """A request for product-local evaluation. Never an executable command.

    ``authority="candidate_only"`` plus ``extra="forbid"`` and the directive
    scan (:func:`~azazel_fabric.engagement_contracts.validation.assert_candidate_not_executable`)
    keep this structurally incapable of authorizing an action: it names an
    objective/approach and the bounded activities it *requests*, and the
    deterministic arbiter accepts, modifies, downgrades, or rejects it.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["engagement-candidate/v0.1"] = "engagement-candidate/v0.1"
    candidate_id: str = Field(min_length=1)
    product: str = Field(min_length=1)
    objective: EngagementObjective
    approach: EngagementApproach
    activity: EngagementActivity
    attack_techniques: list[str] = Field(default_factory=list)
    requested_actions: list[EngagementActivity] = Field(default_factory=list)
    expected_observations: list[str] = Field(default_factory=list)
    trigger: EngagementTrigger | None = None
    constraints: EngagementConstraint
    evidence_refs: list[str] = Field(default_factory=list)
    authority: Literal["candidate_only"] = "candidate_only"


class PostureSuggestion(BaseModel):
    """A suggested bounded posture inside an advisory — never a command."""

    model_config = ConfigDict(extra="forbid")

    objective: EngagementObjective
    approach: EngagementApproach
    supported_activities: list[EngagementActivity] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class EngagementAdvisory(BaseModel):
    """Advisory-only engagement context for the arbiter/operator.

    ``authority="advisory_only"`` and ``executable=False`` are pinned by the
    ``Literal`` types; ``advisory_notice`` and ``limitations`` are always carried
    and must be surfaced, never collapsed. Nothing here can select or authorize
    an action.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["engagement-advisory/v0.1"] = "engagement-advisory/v0.1"
    advisory_id: str = Field(min_length=1)
    advisor: str = Field(min_length=1)
    seen_before: bool = False
    behavior_class: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    prior_outcomes: dict[str, dict[str, str | int | float | bool | None]] = Field(
        default_factory=dict
    )
    posture_suggestion: PostureSuggestion | None = None
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    authority: Literal["advisory_only"] = "advisory_only"
    executable: Literal[False] = False
    advisory_notice: str = ADVISORY_NOTICE


class EngagementOutcome(BaseModel):
    """The measured result of a bounded engagement action — facts only."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["engagement-outcome/v0.1"] = "engagement-outcome/v0.1"
    attacker_reaction: AttackerReaction
    reaction_window_s: int | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    termination_reason: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class EngagementEvent(BaseModel):
    """A recorded engagement: intent + constraints + (optional) outcome.

    Descriptive audit/forwarding shape. The product records what it selected and
    the reaction it observed; this contract never re-runs the action.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["engagement-event/v0.1"] = "engagement-event/v0.1"
    event_id: str = Field(min_length=1)
    product: str = Field(min_length=1)
    objective: EngagementObjective
    approach: EngagementApproach
    activity: EngagementActivity
    trigger: EngagementTrigger | None = None
    constraints: EngagementConstraint
    outcome: EngagementOutcome | None = None
    evidence_refs: list[str] = Field(default_factory=list)
