"""Non-authoritative cross-series effect / outcome / terrain contracts (#15).

    **Fabric describes; products decide.**

This family gives Edge, AZ-06, Gadget and Knowledge the minimum shared
language to correlate

    authoritative decision/effect -> materialization -> reaction/outcome -> replay

without moving scoring, planning, belief, or authority into Fabric. No type
here becomes an execution token by carrying an effect name, and every product
that consumes one still applies its own authority rules to it.

It is **additive**. The released ``outcome_contracts`` family (``v0.9.0rc1``)
is untouched: ``OutcomeObservationEnvelope`` correlates
``OutcomeObservationV0`` records by reference rather than replacing them, so a
consumer pinned to the released family keeps working and a product that never
adopts this family keeps working too.
"""

from .authority import (
    UNKNOWN_AUTHORITY_FALLBACK,
    WEAKEST_AUTHORITY,
    AuthorityClass,
    coerce_authority_class,
    is_authoritative_decision_reference,
)
from .models import (
    UNKNOWN_EFFECT_CLASS_FALLBACK,
    DefensiveEffectRef,
    EffectClass,
    EffectObservation,
    EffectStatus,
    OutcomeObservationEnvelope,
    PresentedTerrainRef,
    ReplayProvenance,
    coerce_effect_class,
    parse_timestamp,
)
from .refs import (
    OPAQUE_REF_PATTERN,
    RefKind,
    parse_ref,
    reject_ref_kinds,
    require_ref_kind,
)
from .validation import (
    BANNED_EFFECT_AUTHORITY_FIELDS,
    SECRET_MATERIAL_MARKERS,
    assert_bounded_fact_payload,
    assert_effect_chain_consistent,
    assert_no_effect_authority_fields,
    assert_no_runtime_directives,
    assert_no_secret_material,
    assert_observation_within_effect_window,
    canonical_fact_json,
)

__all__ = [
    "BANNED_EFFECT_AUTHORITY_FIELDS",
    "OPAQUE_REF_PATTERN",
    "SECRET_MATERIAL_MARKERS",
    "UNKNOWN_AUTHORITY_FALLBACK",
    "UNKNOWN_EFFECT_CLASS_FALLBACK",
    "WEAKEST_AUTHORITY",
    "AuthorityClass",
    "DefensiveEffectRef",
    "EffectClass",
    "EffectObservation",
    "EffectStatus",
    "OutcomeObservationEnvelope",
    "PresentedTerrainRef",
    "RefKind",
    "ReplayProvenance",
    "assert_bounded_fact_payload",
    "assert_effect_chain_consistent",
    "assert_no_effect_authority_fields",
    "assert_no_runtime_directives",
    "assert_no_secret_material",
    "assert_observation_within_effect_window",
    "canonical_fact_json",
    "coerce_authority_class",
    "coerce_effect_class",
    "is_authoritative_decision_reference",
    "parse_ref",
    "parse_timestamp",
    "reject_ref_kinds",
    "require_ref_kind",
]
