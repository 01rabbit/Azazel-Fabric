"""Published golden vectors for the external-security profile (Fabric#25).

**Experimental**, like the family: these bytes make no compatibility promise.

One chain, four producers' worth of records. An external EDR's fact is
normalized into an ``ExternalObservationEnvelope``; Knowledge advises on it in
an ``AdvisoryContextEnvelope``; Deception proposes exposing a deception surface
in an ``ExposureChangeProposal`` that names an Edge decision by opaque ref; a
device adapter reports what it saw in a ``DeviceChangeObservation`` -- with
partial telemetry coverage, named, because a golden vector that claimed
perfect coverage would teach consumers the wrong shape.

A second device observation reports the same change ``released`` after the
proposal expired, which is the only shape a post-expiry report may take.

Built from the validated models, with no wall-clock or randomness, so the
returned dicts are byte-stable across processes and repositories. Not imported
by ``azazel_fabric.testing``: the profile is optional, and importing the
general conformance kit must not pull it in.
"""

from __future__ import annotations

from typing import Any, Callable

from azazel_fabric.external_security_contracts import (
    AdvisoryContextEnvelope,
    DeviceChangeObservation,
    EventWindow,
    ExposureChangeProposal,
    ExternalObservationEnvelope,
    ExternalProvenance,
    FreshnessStatement,
    ProvenanceHop,
    RecommendedAction,
    RecommendedObservation,
    RollbackRequirement,
    TelemetryCoverage,
    VendorExtension,
    canonical_digest,
)

_T0 = "2026-10-01T00:00:00+00:00"
_T0A = "2026-10-01T00:00:05+00:00"
_T1 = "2026-10-01T00:01:00+00:00"
_T2 = "2026-10-01T00:05:00+00:00"
_T3 = "2026-10-01T00:10:00+00:00"
_T4 = "2026-10-01T01:00:00+00:00"
_T5 = "2026-10-01T04:00:00+00:00"
_T6 = "2026-10-01T04:02:00+00:00"

_TENANT = "tenant:golden-site-1"
_TRACE = "trace:golden-external-1"
_OBSERVATION = "external_observation:golden-edr-1"
_ADVISORY = "advisory:golden-knowledge-1"
_PROPOSAL = "proposal:golden-deception-1"
_DECISION = "decision:edge-golden-external-1"
_ENVIRONMENT = "environment:golden-decoy-1"
_SCOPE = "scope:golden-decoy-segment-1"
_RAW_DIGEST = "sha256:" + "c" * 64

_EDR_EXTENSION_BODY: dict[str, Any] = {
    "detection_family": "discovery_sim",
    "sensor_build": "7.12.3",
    "tactic_ids": ["TA0006"],
}


def _hop(product: str, node: str, version: str, role: str, at: str) -> ProvenanceHop:
    return ProvenanceHop(
        product=product,
        node_ref=node,
        product_version=version,
        tenant_ref=_TENANT,
        role=role,
        at=at,
        transport_identity_ref=f"transport:{product}-mtls-golden",
    )


def golden_external_observation() -> dict[str, Any]:
    """An EDR process fact, normalized by an Edge-side ingest adapter."""

    return ExternalObservationEnvelope(
        observation_id=_OBSERVATION,
        source_system="edr",
        source_product_version="7.12.3",
        source_event_ref="source_event:edr-golden-000017",
        producer_product="edge",
        producer_node_ref="node:edge-golden-1",
        producer_version="0.0.0-golden",
        tenant_ref=_TENANT,
        trace_ref=_TRACE,
        observed_at=_T0,
        received_at=_T0A,
        fact_class="endpoint_process",
        subject_refs=("asset:golden-workstation-17", "process:golden-17-4242"),
        event_window=EventWindow(start=_T0, end=_T0),
        payload_digest=_RAW_DIGEST,
        normalized_fact={
            "process_name": "lsass_reader_sim",
            "parent_process_name": "office_sim",
            "severity_band": "high",
        },
        evidence_refs=("evidence:edr-golden-raw-17",),
        freshness=FreshnessStatement(state="fresh", as_of=_T0A, stale_after=_T4),
        telemetry_coverage=TelemetryCoverage(
            coverage_complete=False,
            gaps=("edr sensor offline on 2 of 40 endpoints",),
            sources_expected=40,
            sources_reporting=38,
        ),
        limitations=("process lineage truncated at depth 2 by the source",),
        privacy_class="internal",
        provenance=ExternalProvenance(
            chain=(
                _hop("edr-vendor", "node:edr-cloud-golden", "7.12.3", "observed", _T0),
                _hop("edge", "node:edge-golden-1", "0.0.0-golden", "normalized", _T0A),
            ),
            signature_ref="signature:edge-golden-external-1",
        ),
        vendor_extensions=(
            VendorExtension(
                namespace="vendor.edr-sim",
                body=_EDR_EXTENSION_BODY,
                body_digest=canonical_digest(_EDR_EXTENSION_BODY),
                evidence_ref="evidence:edr-golden-raw-17",
            ),
        ),
    ).model_dump(mode="json")


def golden_advisory_context() -> dict[str, Any]:
    """Knowledge's advice about the fact above. Advisory-only, carries no decision."""

    return AdvisoryContextEnvelope(
        advisory_id=_ADVISORY,
        producer_product="knowledge",
        producer_node_ref="node:knowledge-golden-1",
        producer_version="0.0.0-golden",
        tenant_ref=_TENANT,
        trace_ref=_TRACE,
        subject_refs=("asset:golden-workstation-17",),
        generated_at=_T1,
        expires_at=_T4,
        source_fact_refs=(_OBSERVATION,),
        normalized_fact_refs=("fact:golden-credential-access-1",),
        inference_refs=("inference:golden-credential-access-1",),
        assessment_summary=(
            "Process behaviour matches simulated credential access, lineage is "
            "partial and two sensors were offline."
        ),
        confidence_band="moderate",
        recommended_observations=(
            RecommendedObservation(
                observation_class="verify_coverage",
                subject_refs=("asset:golden-workstation-17",),
                rationale="two sensors were offline during the event window",
                evidence_refs=("evidence:edr-golden-raw-17",),
            ),
        ),
        recommended_actions=(
            RecommendedAction(
                action_class="review_deception_redirect",
                rationale="credential-access behaviour is a fit for a decoy share",
                constraints=("operator review required", "bounded duration"),
                evidence_refs=("evidence:edr-golden-raw-17",),
            ),
            RecommendedAction(
                action_class="notify_operator",
                rationale="moderate confidence with named coverage gaps",
            ),
        ),
        limitations=("no network telemetry correlated",),
        unknowns=("whether the process was operator-initiated",),
        freshness=FreshnessStatement(state="fresh", as_of=_T1, stale_after=_T4),
        privacy_class="internal",
        provenance=ExternalProvenance(
            chain=(_hop("knowledge", "node:knowledge-golden-1", "0.0.0-golden", "inferred", _T1),),
        ),
    ).model_dump(mode="json")


def golden_exposure_proposal() -> dict[str, Any]:
    """Deception asks the owning adapter to expose a decoy surface. Proposal only."""

    return ExposureChangeProposal(
        proposal_id=_PROPOSAL,
        producer_product="deception",
        producer_node_ref="node:deception-golden-1",
        producer_version="0.0.0-golden",
        tenant_ref=_TENANT,
        trace_ref=_TRACE,
        environment_ref=_ENVIRONMENT,
        decision_ref=_DECISION,
        requested_effect="expose_deception_surface",
        target_scope_ref=_SCOPE,
        adapter_capability_ref="capability:switch-vlan-exposure-v1",
        not_before=_T2,
        expires_at=_T5,
        rollback_requirement=RollbackRequirement(
            required=True,
            triggers=("on_expiry", "on_failure", "on_withdraw"),
            max_rollback_seconds=120,
        ),
        safety_constraints=(
            "bounded_duration",
            "no_production_access",
            "no_outbound_egress",
            "isolation_verified_before_exposure",
        ),
        evidence_refs=("evidence:deception-isolation-golden-1",),
        privacy_class="internal",
        provenance=ExternalProvenance(
            chain=(_hop("deception", "node:deception-golden-1", "0.0.0-golden", "proposed", _T1),),
        ),
    ).model_dump(mode="json")


def _device_provenance(at: str) -> ExternalProvenance:
    return ExternalProvenance(
        chain=(
            _hop("switch-sim", "node:switch-golden-1", "15.2", "observed", at),
            _hop("nexus", "node:nexus-golden-1", "0.0.0-golden", "reported", at),
        ),
    )


def golden_device_change_applied() -> dict[str, Any]:
    """The adapter saw the change applied. Not a success claim -- coverage is partial."""

    return DeviceChangeObservation(
        observation_id="device_observation:golden-applied-1",
        producer_product="nexus",
        producer_node_ref="node:nexus-golden-1",
        producer_version="0.0.0-golden",
        tenant_ref=_TENANT,
        trace_ref=_TRACE,
        decision_ref=_DECISION,
        proposal_ref=_PROPOSAL,
        adapter_ref="adapter:switch-vlan-golden",
        target_scope_ref=_SCOPE,
        status="applied",
        observed_at=_T3,
        observation_window=EventWindow(start=_T2, end=_T3),
        evidence_refs=("evidence:switch-config-diff-golden-1",),
        correlation_refs=(_OBSERVATION, _ADVISORY),
        telemetry_coverage=TelemetryCoverage(
            coverage_complete=False,
            gaps=("no flow telemetry from the decoy segment yet",),
        ),
        confounders=("scheduled maintenance window overlapped",),
        limitations=("device reported config acceptance, traffic not yet observed",),
        privacy_class="internal",
        provenance=_device_provenance(_T3),
    ).model_dump(mode="json")


def golden_device_change_released() -> dict[str, Any]:
    """After expiry the adapter reports the change released -- the only post-expiry shape."""

    return DeviceChangeObservation(
        observation_id="device_observation:golden-released-1",
        producer_product="nexus",
        producer_node_ref="node:nexus-golden-1",
        producer_version="0.0.0-golden",
        tenant_ref=_TENANT,
        trace_ref=_TRACE,
        decision_ref=_DECISION,
        proposal_ref=_PROPOSAL,
        adapter_ref="adapter:switch-vlan-golden",
        target_scope_ref=_SCOPE,
        status="released",
        observed_at=_T6,
        observation_window=EventWindow(start=_T5, end=_T6),
        evidence_refs=("evidence:switch-config-diff-golden-2",),
        correlation_refs=("device_observation:golden-applied-1",),
        telemetry_coverage=TelemetryCoverage(coverage_complete=True, sources_expected=1, sources_reporting=1),
        privacy_class="internal",
        provenance=_device_provenance(_T6),
    ).model_dump(mode="json")


GOLDEN_EXTERNAL_SECURITY_VECTORS: dict[str, Callable[[], dict[str, Any]]] = {
    "external_observation_envelope_v0.json": golden_external_observation,
    "advisory_context_envelope_v0.json": golden_advisory_context,
    "exposure_change_proposal_v0.json": golden_exposure_proposal,
    "device_change_observation_applied_v0.json": golden_device_change_applied,
    "device_change_observation_released_v0.json": golden_device_change_released,
}

__all__ = [
    "GOLDEN_EXTERNAL_SECURITY_VECTORS",
    "golden_advisory_context",
    "golden_device_change_applied",
    "golden_device_change_released",
    "golden_exposure_proposal",
    "golden_external_observation",
]
