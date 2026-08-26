"""Non-authoritative Outcome-as-Evidence contracts.

Fabric describes; product-local policy decides; product-local tools execute.
"""

from .models import (
    ExecutionRefV0,
    MechanismObservationV0,
    OutcomeObservationV0,
    TacticalEffectAssessmentRefV0,
)
from .validation import (
    assert_bounded_fact_payload,
    assert_evidence_chain_consistent,
    assert_no_runtime_directives,
    canonical_fact_json,
)

__all__ = [
    "ExecutionRefV0",
    "MechanismObservationV0",
    "OutcomeObservationV0",
    "TacticalEffectAssessmentRefV0",
    "assert_bounded_fact_payload",
    "assert_evidence_chain_consistent",
    "assert_no_runtime_directives",
    "canonical_fact_json",
]
