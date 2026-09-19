"""Published golden vectors for the cross-series effect family (Fabric#15).

One chain, four producers. Edge constructs the effect, AZ-06 materializes the
presented terrain and observes it, Gadget contributes a second observation from
a different vantage point, and Knowledge correlates the whole thing into one
envelope.

Exposed as an importable API for the same reason the Fabric#9 decision vectors
are: so Edge, Gadget, Knowledge and AZ-06 test against the *same* bytes Fabric
ships instead of each hand-rolling a chain that agrees only with itself. Every
vector is built from the validated models and contains no wall-clock or
randomness, so the returned dicts are byte-stable across processes and repos.
"""

from __future__ import annotations

from typing import Any, Callable

from azazel_fabric.effect_contracts import (
    AuthorityClass,
    DefensiveEffectRef,
    EffectClass,
    EffectObservation,
    OutcomeObservationEnvelope,
    PresentedTerrainRef,
    ReplayProvenance,
)

#: Fixed instants. The chain is deterministic; nothing here reads a clock.
_T0 = "2026-08-20T00:00:00+00:00"
_T1 = "2026-08-20T00:05:00+00:00"
_T2 = "2026-08-20T00:30:00+00:00"
_T3 = "2026-08-22T00:00:00+00:00"

_TRACE = "trace-golden-effect-1"
_DECISION = "decision-golden-effect-1"
_EFFECT = "effect:golden-effect-1"
_PRESENTATION = "presentation:golden-effect-1"
_CONFIG_DIGEST = "sha256:" + "b" * 64


def golden_edge_effect_ref() -> dict[str, Any]:
    """AZ-01 Edge: the arbiter's own decision, expressed as a shared reference."""

    return DefensiveEffectRef(
        effect_id=_EFFECT,
        effect_class=EffectClass.REDIRECT_TO_PRESENTED_TERRAIN,
        producer_product="edge",
        producer_node="edge-golden-1",
        trace_id=_TRACE,
        decision_ref=_DECISION,
        target_scope_ref="scope:session-golden-1",
        policy_ref="policy-golden-redirect-v3",
        profile_ref="profile:pi4-2gb",
        config_digest=_CONFIG_DIGEST,
        created_at=_T0,
        expires_at=_T3,
        authority_class=AuthorityClass.PRODUCER_DECISION_REF,
    ).model_dump(mode="json")


def golden_advisory_effect_ref() -> dict[str, Any]:
    """AZ-04 Knowledge: advice about the same trace, carrying no decision.

    Published deliberately. A consumer that cannot tell this apart from
    ``golden_edge_effect_ref`` has an authority bug, and this vector is the
    cheapest way for it to find out.
    """

    return DefensiveEffectRef(
        effect_id="effect:golden-effect-advisory-1",
        effect_class=EffectClass.RATE_LIMIT,
        producer_product="knowledge",
        producer_node="knowledge-golden-1",
        trace_id=_TRACE,
        advisory_ref="advisory:golden-effect-1",
        target_scope_ref="scope:session-golden-1",
        policy_ref="policy-golden-advice-v1",
        created_at=_T0,
        expires_at=_T3,
        authority_class=AuthorityClass.ADVISORY_INFERENCE,
    ).model_dump(mode="json")


def golden_deception_presented_terrain() -> dict[str, Any]:
    """AZ-06 Deception: what the defender presented, and under whose decision."""

    return PresentedTerrainRef(
        presentation_id=_PRESENTATION,
        presentation_version=1,
        producer_product="deception",
        activation_decision_ref=_DECISION,
        lifecycle_state_ref="lifecycle:env-golden-1.active",
        active_surface_refs=("surface:http-8080", "surface:smb-445"),
        synthetic_artifact_refs=("artifact:golden-invoice-pdf",),
        isolation_assertion_ref="evidence:isolation-assert-golden-1",
        isolation_result_ref="evidence:isolation-result-golden-1",
        created_at=_T0,
        expires_at=_T3,
        evidence_refs=("evidence:deception-runtime-golden-1",),
        authority_class=AuthorityClass.ACTIVE_MATERIALIZED,
    ).model_dump(mode="json")


def golden_deception_effect_observation() -> dict[str, Any]:
    """AZ-06 Deception: the effect is live, asserted by its materializer."""

    return EffectObservation(
        observation_id="effect_observation:golden-deception-1",
        effect_ref=_EFFECT,
        trace_id=_TRACE,
        status="active",
        observed_at=_T1,
        materialization_producer="deception",
        execution_ref="execution-golden-effect-1",
        evidence_refs=("evidence:deception-runtime-golden-1",),
        authority_class=AuthorityClass.ACTIVE_MATERIALIZED,
    ).model_dump(mode="json")


def golden_gadget_effect_observation() -> dict[str, Any]:
    """AZ-02 Gadget: a second vantage point, and an honest limitation."""

    return EffectObservation(
        observation_id="effect_observation:golden-gadget-1",
        effect_ref=_EFFECT,
        trace_id=_TRACE,
        status="completed",
        observed_at=_T2,
        materialization_producer="gadget",
        execution_ref="execution-golden-effect-1",
        evidence_refs=("evidence:gadget-capture-golden-1",),
        limitations=("span_port_saw_one_direction_only",),
        authority_class=AuthorityClass.OBSERVED_FACT,
    ).model_dump(mode="json")


def golden_replay_provenance() -> dict[str, Any]:
    """What it takes to reproduce the chain. It authorizes nothing."""

    return ReplayProvenance(
        software_revision="azazel-fabric-golden-effect-1",
        runtime_profile="pi4-2gb",
        policy_config_digest=_CONFIG_DIGEST,
        model_ref="model:golden-advisor-v1",
        playbook_ref="playbook:golden-redirect-v1",
        fixture_scenario_id="fixture:golden-effect-1",
        capture_generation=7,
        as_of=_T0,
    ).model_dump(mode="json")


def golden_knowledge_outcome_envelope() -> dict[str, Any]:
    """AZ-04 Knowledge: correlation, with the telemetry gap stated, not hidden."""

    return OutcomeObservationEnvelope(
        envelope_id="envelope:golden-effect-1",
        producer_product="knowledge",
        producer_node="knowledge-golden-1",
        producer_version="golden-1",
        trace_id=_TRACE,
        decision_ref=_DECISION,
        effect_ref=_EFFECT,
        environment_ref="environment:env-golden-1",
        presentation_ref=_PRESENTATION,
        actor_session_ref="session:golden-actor-1",
        outcome_observation_refs=(
            "deception-outcome-99ee2bf20a9b563e245f44f0",
            "gadget-outcome-golden-1",
        ),
        window_start=_T0,
        window_end=_T2,
        observation_class="presented_terrain_engagement",
        telemetry_coverage={"deception_runtime": "full", "gadget_span": "partial"},
        coverage_complete=False,
        telemetry_gaps=("gadget_span_saw_one_direction_only",),
        confounders=("concurrent_maintenance_window",),
        impact_observations={
            "noc": {"tickets_opened": 0},
            "business": {"user_visible_disruption": "none_observed"},
            "resource": {"peak_memory_mb": 412},
        },
        evidence_refs=("evidence:deception-runtime-golden-1", "evidence:gadget-capture-golden-1"),
        provenance=ReplayProvenance.model_validate(golden_replay_provenance()),
        observed_at=_T2,
        authority_class=AuthorityClass.OBSERVED_FACT,
    ).model_dump(mode="json")


#: Every published vector, by the name its fixture file carries.
GOLDEN_EFFECT_VECTORS: dict[str, Callable[[], dict[str, Any]]] = {
    "effect_edge_defensive_effect_ref_v0.json": golden_edge_effect_ref,
    "effect_knowledge_advisory_ref_v0.json": golden_advisory_effect_ref,
    "effect_deception_presented_terrain_v0.json": golden_deception_presented_terrain,
    "effect_deception_observation_v0.json": golden_deception_effect_observation,
    "effect_gadget_observation_v0.json": golden_gadget_effect_observation,
    "effect_knowledge_outcome_envelope_v0.json": golden_knowledge_outcome_envelope,
}

__all__ = [
    "GOLDEN_EFFECT_VECTORS",
    "golden_advisory_effect_ref",
    "golden_deception_effect_observation",
    "golden_deception_presented_terrain",
    "golden_edge_effect_ref",
    "golden_gadget_effect_observation",
    "golden_knowledge_outcome_envelope",
    "golden_replay_provenance",
]
