"""Canonical adversary-engagement contracts (MITRE Engage-aligned).

Additive, versioned (``*/v0.1``) description of engagement intent, constraints,
events, and outcomes. Fabric describes; the product-local deterministic arbiter
decides. A candidate is a request, an advisory is context — neither can
authorize or execute an action.
"""

from azazel_fabric.engagement_contracts.models import (
    ADVISORY_NOTICE,
    AttackerReaction,
    EngagementActivity,
    EngagementAdvisory,
    EngagementApproach,
    EngagementCandidate,
    EngagementConstraint,
    EngagementEvent,
    EngagementObjective,
    EngagementOutcome,
    EngagementTrigger,
    PostureSuggestion,
)
from azazel_fabric.engagement_contracts.validation import (
    BANNED_ENGAGEMENT_AUTHORITY_FIELDS,
    assert_candidate_not_executable,
    assert_engagement_advisory_only,
    assert_no_engagement_directives,
)

__all__ = [
    "ADVISORY_NOTICE",
    "AttackerReaction",
    "EngagementActivity",
    "EngagementAdvisory",
    "EngagementApproach",
    "EngagementCandidate",
    "EngagementConstraint",
    "EngagementEvent",
    "EngagementObjective",
    "EngagementOutcome",
    "EngagementTrigger",
    "PostureSuggestion",
    "BANNED_ENGAGEMENT_AUTHORITY_FIELDS",
    "assert_candidate_not_executable",
    "assert_engagement_advisory_only",
    "assert_no_engagement_directives",
]
