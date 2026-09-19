"""Canonical M.I.O. dual-cognition contracts (R1a).

Local situation frames, sanitized remote frames, advisory results, and
provenance-preserving merge output. Every shape is advisory and inert: Fabric
describes what a model said and where it came from, and nothing downstream can
act on it without a product's own arbiter.

See ``docs/provisioning-contracts.md`` for the family reference.
"""

from azazel_fabric.mio_contracts.models import (
    AdvisoryResult,
    AliasScope,
    Claim,
    ClaimSet,
    ClaimSource,
    CognitionState,
    Disagreement,
    MergedAdvisory,
    PrivacyClass,
    RedactionRecord,
    SanitizedRemoteFrame,
    SituationFrame,
)
from azazel_fabric.mio_contracts.validation import (
    BANNED_MIO_DIRECTIVE_FIELDS,
    NON_EGRESSIBLE_PRIVACY_CLASSES,
    assert_advisory_inert,
    assert_bounded_mio_payload,
    assert_claim_provenance_preserved,
    assert_frame_sanitized_for_egress,
    assert_no_mio_directives,
    canonical_mio_json,
    contains_mio_directive,
)

__all__ = [
    # models
    "AdvisoryResult",
    "AliasScope",
    "Claim",
    "ClaimSet",
    "ClaimSource",
    "CognitionState",
    "Disagreement",
    "MergedAdvisory",
    "PrivacyClass",
    "RedactionRecord",
    "SanitizedRemoteFrame",
    "SituationFrame",
    # validation
    "BANNED_MIO_DIRECTIVE_FIELDS",
    "NON_EGRESSIBLE_PRIVACY_CLASSES",
    "assert_advisory_inert",
    "assert_bounded_mio_payload",
    "assert_claim_provenance_preserved",
    "assert_frame_sanitized_for_egress",
    "assert_no_mio_directives",
    "canonical_mio_json",
    "contains_mio_directive",
]
