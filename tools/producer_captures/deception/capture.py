"""Capture real Azazel-Deception producer output with deterministic inputs.

Usage: python capture.py [OUT_DIR]   (default: this file's directory)
Inputs are borrowed from Deception's own tests (see README.md). No clock,
no randomness: every timestamp is a fixed literal.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from azazel_fabric.deception_contracts import InteractionObservation, PlacementPlan
from azazel_fabric.effect_contracts import (
    AuthorityClass, DefensiveEffectRef, EffectClass, EffectObservation, PresentedTerrainRef,
)
from azazel_fabric.outcome_contracts import OutcomeObservationV0

from azazel_deception.package import load_package, parse_package
from azazel_deception.planner import build_placement_plan
from azazel_deception.runtime.effect_projection import (
    EffectProjectionRefused, EffectRefRejected, accept_defensive_effect_ref,
    observe_effect, project_presented_terrain,
)
from azazel_deception.runtime.observation import InteractionObserver, build_runtime_context
from azazel_deception.runtime.observation_export import export_observations
from azazel_deception.runtime.outcome_export import presented_terrain_lifecycle_outcome
from azazel_deception.runtime.presented_terrain import (
    PresentedTerrainSnapshotV0, ProducerRedirectionEvidence, build_presented_terrain_snapshot,
)
from azazel_deception.runtime.state import RuntimeStateStore

# Usage: capture.py <Azazel-Deception checkout> <output dir>
DECEPTION = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
PACKAGE = DECEPTION / "examples/packages/municipal-linux-v1/package.yaml"

written: dict[str, str] = {}
refusals: dict[str, dict] = {}


def dump(name: str, obj) -> None:
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (OUT / name).write_text(text, encoding="utf-8")
    written[name] = text


def refused(case: str, exc_type, fn) -> None:
    try:
        fn()
    except exc_type as e:
        refusals[case] = {"exception": type(e).__name__, "message": str(e)}
    else:
        raise AssertionError(f"{case}: expected {exc_type.__name__}")


# ---- deception_contracts: InteractionObservation (tests/test_observation_export.py) ----
host = {  # tests/test_runtime.py::_host
    "node_id": "az06-test", "architecture": "amd64", "cpu_cores": 4, "memory_mb": 8192,
    "storage_free_mb": 65536, "runtime_adapters": {"docker_compose": True},
    "kvm_available": False, "gpu_available": False,
}
raw = load_package(PACKAGE)
package = parse_package(raw)
plan = PlacementPlan.model_validate(
    build_placement_plan(raw, host, requested_tier="lite", edge_decision_id="edge-1"))
with tempfile.TemporaryDirectory() as td:
    state = RuntimeStateStore(Path(td))
    env = "env-export-1"
    ctx = build_runtime_context(package, plan)
    obs = InteractionObserver(state, environment_id=env, package_id=package.package_id,
                              node_id=plan.node_id, runtime_context=ctx)
    state.append_evidence(env, {  # lifecycle noise that must be filtered out
        "schema_version": "environment-event/v0.1", "event_id": f"{env}-activated",
        "environment_id": env, "package_id": "pkg", "node_id": "node",
        "event_type": "activated", "observed_at": "2026-01-01T00:00:00+00:00",
        "evidence_refs": [], "metadata": {}})
    obs.record(observation_class="interaction", surface="port",
               observed_at=datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc))
    obs.record(observation_class="reaction", surface="service", reaction_kind="enumerate",
               first_contact_latency_ms=120, dwell_ms=3000, attempt_count=2,
               confounder_tags=["scanner_noise"], evidence_refs=["evidence:obs:1"],
               observed_at=datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc))
    exported = export_observations(state, env)
assert len(exported) == 2
for i, rec in enumerate(exported, 1):
    InteractionObservation.model_validate(rec)
dump("deception_contracts_interaction_observation_interaction_port.json", exported[0])
dump("deception_contracts_interaction_observation_reaction_service.json", exported[1])
dump("deception_contracts_interaction_observation_export_list.json", exported)

# ---- effect_contracts (tests/test_effect_contracts_producer.py) ----
def producer():
    return ProducerRedirectionEvidence(
        producer_product="azazel-edge", producer_node="edge-1", trace_id="trace-1",
        decision_ref="decision-1", execution_ref="execution-1",
        mechanism_observation_ref="mechanism-1", evidence_refs=["edge-nft-1"])

def snap(**ov):
    d = dict(
        environment_id="env-1", producer=producer(),
        runtime_state={"environment_id": "env-1", "state": "active",
                       "package_id": "municipal-linux-v1", "package_digest": "sha256:abc123",
                       "node_id": "deception-node-1", "activated_at": "2026-08-26T00:00:00+00:00"},
        expected_package_id="municipal-linux-v1", expected_package_digest="sha256:abc123",
        package_version="1.0.0", observed_at="2026-08-26T00:00:02+00:00",
        active_surface_refs=("surface:http:8080",),
        isolation_assertion_refs=("isolation-net-none",), runtime_verified_active=True,
        evidence_refs=("runtime-inspect-1",), expires_at="2026-08-26T01:00:00+00:00")
    d.update(ov)
    return build_presented_terrain_snapshot(**d)

def effect(**ov):
    d = dict(effect_id="effect:e1", effect_class=EffectClass.REDIRECT_TO_PRESENTED_TERRAIN,
             producer_product="azazel-edge", producer_node="edge-1", trace_id="trace-1",
             target_scope_ref="scope:s1", policy_ref="policy-1",
             created_at="2026-08-26T00:00:00+00:00", expires_at="2026-08-26T01:00:00+00:00",
             authority_class=AuthorityClass.PLANNED_SHADOW)
    d.update(ov)
    return DefensiveEffectRef(**d)

def decided(**ov):
    return effect(authority_class=AuthorityClass.PRODUCER_DECISION_REF, decision_ref="decision-1", **ov)

SHADOW = {"runtime_verified_active": False, "active_surface_refs": ()}
terr = lambda p: PresentedTerrainRef.model_validate(p.ref.model_dump(mode="json"))

dump("effect_contracts_presented_terrain_ref_live.json",
     project_presented_terrain(snap(), presentation_version=0).ref.model_dump(mode="json"))
dump("effect_contracts_presented_terrain_ref_live_bound_to_decided_effect.json",
     project_presented_terrain(snap(), presentation_version=0, source_effect=decided()).ref.model_dump(mode="json"))
dump("effect_contracts_presented_terrain_ref_shadow_stale.json",
     project_presented_terrain(snap(**SHADOW), presentation_version=0, source_effect=effect()).ref.model_dump(mode="json"))
dump("effect_contracts_presented_terrain_ref_synthetic_refs.json",
     project_presented_terrain(snap(
         synthetic_artifact_refs=("artifact:honey:invoice-2026",),
         synthetic_identity_refs=("identity:finance:clerk-1",),
         synthetic_credential_refs=("credential:smb:clerk-1",)),
         presentation_version=0, source_effect=decided()).ref.model_dump(mode="json"))

# EffectObservation (an_edge_effect, tests line 818)
edge = accept_defensive_effect_ref({
    "effect_id": "effect:cff74a8556ff401bc72249812018afcc",
    "effect_class": "redirect_to_presented_terrain", "producer_product": "azazel-edge",
    "producer_node": "edge-1", "trace_id": "trace-1", "decision_ref": "decision-1",
    "target_scope_ref": "scope:6617f9307d832d50e04395e5604619cd", "policy_ref": "policy:soc-default",
    "created_at": "2026-09-20T12:00:00+00:00", "expires_at": "2026-09-20T13:00:00+00:00",
    "authority_class": "producer_decision_ref"})
dump("effect_contracts_effect_observation_active.json",
     observe_effect(edge, status="active", observed_at="2026-09-20T12:05:00+00:00").model_dump(mode="json"))
dump("effect_contracts_effect_observation_terminated.json",
     observe_effect(edge, status="terminated", observed_at="2026-09-20T12:30:00+00:00",
                    termination_reason="expired", evidence_refs=("runtime-inspect-2",)).model_dump(mode="json"))

# refusals (no output JSON)
refused("effect_projection_no_expiry", EffectProjectionRefused,
        lambda: project_presented_terrain(snap(expires_at=None), presentation_version=0))
refused("effect_projection_two_isolation_assertions", EffectProjectionRefused,
        lambda: project_presented_terrain(snap(isolation_assertion_refs=("isolation-a", "isolation-b")), presentation_version=0))
refused("effect_projection_untyped_identity", EffectProjectionRefused,
        lambda: project_presented_terrain(snap(synthetic_identity_refs=("finance-clerk",)), presentation_version=0))
refused("effect_projection_non_snapshot", EffectProjectionRefused,
        lambda: project_presented_terrain({"presentation_id": "x"}, presentation_version=0))
refused("effect_ref_shadow_effect_on_live_terrain", EffectRefRejected,
        lambda: project_presented_terrain(snap(), presentation_version=0, source_effect=effect()))
for auth, extra in (("planned_shadow", {}), ("advisory_inference", {"advisory_ref": "advisory:a1"})):
    refused(f"accept_effect_{auth}", EffectRefRejected, lambda a=auth, x=extra: accept_defensive_effect_ref({
        "effect_id": "effect:cff74a8556ff401bc72249812018afcc", "effect_class": "redirect_to_presented_terrain",
        "producer_product": "azazel-edge", "producer_node": "edge-1", "trace_id": "trace-1",
        "target_scope_ref": "scope:6617f9307d832d50e04395e5604619cd", "policy_ref": "policy:soc-default",
        "created_at": "2026-09-20T12:00:00+00:00", "expires_at": "2026-09-20T13:00:00+00:00",
        "authority_class": a, **x}))

# ---- outcome_contracts (tests/test_cross_product_golden_outcome.py, test_presented_terrain_outcome_export.py) ----
def psnap(**ov):
    v = dict(
        presentation_id="presentation-golden-1", environment_id="env-golden-1",
        producer_product="azazel-edge", producer_node="edge-golden-1",
        trace_id="trace-golden-redirect-1", producer_decision_ref="decision-golden-redirect-1",
        producer_execution_ref="execution-golden-redirect-1",
        producer_mechanism_ref="mechanism-golden-redirection-1", producer_mechanism_kind="redirection",
        package_id="municipal-linux-v1", package_version="1.0.0", package_digest="sha256:goldenabc123",
        runtime_node_id="deception-golden-1", lifecycle_state="active",
        active_surface_refs=("surface:http:8080",), synthetic_artifact_refs=(),
        synthetic_identity_refs=(), synthetic_credential_refs=(),
        started_at="2026-08-26T06:10:02Z", isolation_assertion_refs=("isolation:golden:1",),
        evidence_refs=("deception:runtime:golden:1",), observed_at="2026-08-26T06:10:03Z")
    v.update(ov)
    return PresentedTerrainSnapshotV0(**v)

dump("outcome_contracts_presented_terrain_lifecycle_during.json",
     presented_terrain_lifecycle_outcome(psnap(), observed_at="2026-08-26T06:10:03Z"))
dump("outcome_contracts_presented_terrain_lifecycle_after_reset.json",
     presented_terrain_lifecycle_outcome(
         psnap(lifecycle_state="reset", active_surface_refs=(), ended_at="2026-08-26T06:20:00Z",
               reset_ref="reset:proof:1"), observed_at="2026-08-26T06:20:01Z"))
refused("outcome_stale_snapshot", ValueError, lambda: presented_terrain_lifecycle_outcome(
    psnap(lifecycle_state="stale", active_surface_refs=(),
          limitations=("runtime_active_not_independently_verified",)),
    observed_at="2026-08-26T06:10:03Z"))
refused("outcome_forbidden_claim_in_coverage", ValueError, lambda: presented_terrain_lifecycle_outcome(
    psnap(), observed_at="2026-08-26T06:10:03Z", telemetry_coverage={"attacker_belief": True}))

dump("refusals.json", refusals)

# ---- validate against Fabric models ----
MODELS = {"deception_contracts_interaction_observation": InteractionObservation,
          "effect_contracts_presented_terrain_ref": PresentedTerrainRef,
          "effect_contracts_effect_observation": EffectObservation,
          "outcome_contracts_presented_terrain_lifecycle": OutcomeObservationV0}
for name, text in written.items():
    for prefix, model in MODELS.items():
        if name.startswith(prefix):
            data = json.loads(text)
            for item in (data if isinstance(data, list) else [data]):
                model.model_validate(item)
            print("valid", model.__name__, name)
