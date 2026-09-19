"""Authority classification for cross-series effect records (Fabric#15).

**Fabric describes; products decide.** Nothing in this module grants anything.
Its job is to make a *claim* legible so that a receiving product can apply its
own authority rules to it -- and to make the weakest reading the default when
the claim is not understood.

Two separate ideas are kept apart on purpose:

``AuthorityClass``
    What the record claims to be. A claim, made by whoever built the record.

provenance (signatures, digests, SBOM locators)
    Who vouches for the bytes. This says nothing about authority, and
    ``ReplayProvenance.confers_authority`` is pinned to ``False`` so that the
    presence of provenance can never be read as authorization.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "AuthorityClass",
    "UNKNOWN_AUTHORITY_FALLBACK",
    "WEAKEST_AUTHORITY",
    "coerce_authority_class",
    "is_authoritative_decision_reference",
]


class AuthorityClass(str, Enum):
    """The distinctions every shared envelope must make possible (issue #15).

    Each member answers one question: *how should a consumer read this record
    if it reads nothing else?*
    """

    #: Something was observed. No decision and no inference is claimed.
    OBSERVED_FACT = "observed_fact"
    #: The producing product's own authority decided this, and names the decision.
    PRODUCER_DECISION_REF = "producer_decision_ref"
    #: Advice or inference. Never a decision, whatever else the record carries.
    ADVISORY_INFERENCE = "advisory_inference"
    #: Considered or shadow-run. Nothing was materialized.
    PLANNED_SHADOW = "planned_shadow"
    #: Materialized and currently in effect, as observed by its materializer.
    ACTIVE_MATERIALIZED = "active_materialized"
    #: Expired, replayed, or not understood. Claims nothing.
    STALE_OR_UNKNOWN = "stale_or_unknown"


#: Where an unrecognized authority value lands.
#:
#: It must be the class that claims *least*. An unknown value that landed on
#: ``ACTIVE_MATERIALIZED`` would let an unparseable record assert that
#: something is live -- an unknown input escalating by being unknown.
UNKNOWN_AUTHORITY_FALLBACK = AuthorityClass.STALE_OR_UNKNOWN

#: Named separately so a test can pin the intent rather than the value.
WEAKEST_AUTHORITY = AuthorityClass.STALE_OR_UNKNOWN


def coerce_authority_class(raw: object) -> tuple[AuthorityClass, bool]:
    """Return ``(class, recognized)``. Unknown input never escalates.

    The second element exists so a caller can tell "this record claims the
    weakest class" from "this record claimed something I could not read",
    which are different facts and must not be collapsed.
    """

    if isinstance(raw, AuthorityClass):
        return raw, True
    if isinstance(raw, str):
        try:
            return AuthorityClass(raw), True
        except ValueError:
            return UNKNOWN_AUTHORITY_FALLBACK, False
    return UNKNOWN_AUTHORITY_FALLBACK, False


def is_authoritative_decision_reference(authority_class: object) -> bool:
    """True only for a record that names a producer-local authoritative decision.

    This is the function an adversarial payload would want to fool. It returns
    True for exactly one class, so a schema-valid advisory cannot reach it by
    carrying extra fields, a signature, or a plausible-looking decision id --
    it would have to declare ``PRODUCER_DECISION_REF``, which the models then
    require it to substantiate.
    """

    coerced, recognized = coerce_authority_class(authority_class)
    return recognized and coerced is AuthorityClass.PRODUCER_DECISION_REF
