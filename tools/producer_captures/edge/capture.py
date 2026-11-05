"""Capture real Azazel-Edge producer output with deterministic inputs.

Usage: python capture.py [EDGE_REPO] [OUT_DIR]
Inputs are borrowed from Edge's own tests (see README.md). No clock, no RNG.
Writes <family>_<case>.json (validated Fabric-model records) and
refusals.json (producer cases that deliberately emit nothing).
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Usage: capture.py <Azazel-Edge checkout> <output dir>
EDGE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(EDGE / "py"))
sys.path.insert(0, str(EDGE / "tests"))  # to borrow the tests' own input builders

import azazel_fabric  # noqa: E402
from azazel_fabric.effect_contracts import DefensiveEffectRef  # noqa: E402
from azazel_fabric.engagement_contracts import EngagementCandidate, EngagementEvent  # noqa: E402
from azazel_fabric.deception_contracts import (  # noqa: E402
    EnvironmentTransitionDecision, verify_decision_signature)
from azazel_fabric.outcome_contracts import (  # noqa: E402
    ExecutionRefV0, MechanismObservationV0, OutcomeObservationV0,
    TacticalEffectAssessmentRefV0)

from azazel_edge.outcome.contracts import (  # noqa: E402
    AppliedMechanism, ExecutionStatus, MechanismKind, MechanismStatus)
from azazel_edge.outcome.adapter import from_rust_event  # noqa: E402
from azazel_edge.outcome.effect_export import (  # noqa: E402
    EffectExportRefused, export_defensive_effect_ref)
from azazel_edge.outcome.shared_export import (  # noqa: E402
    SharedOutcomeExportError, assessment_to_shared_v0, execution_to_shared_v0,
    mechanism_to_shared_v0, outcome_to_shared_v0)
from azazel_edge.engagement import (  # noqa: E402
    build_engagement_candidate, engagement_event, evaluate_engagement)
from azazel_edge.deception_transition import (  # noqa: E402
    TransitionDecisionError, build_transition_decision,
    transition_decision_from_arbiter)

import test_outcome_effect_export as t_effect  # noqa: E402
import test_outcome_shared_export as t_shared  # noqa: E402
import test_engagement_candidate as t_eng  # noqa: E402
import test_deception_transition as t_dec  # noqa: E402

records: dict[str, tuple[object, dict]] = {}  # filename stem -> (model, payload)
refusals: dict[str, dict] = {}


def rec(stem, model, payload):
    records[stem] = (model, payload)


def refuse(name, exc_type, fn):
    try:
        out = fn()
    except exc_type as e:
        refusals[name] = {"producer_output": None, "exception": type(e).__name__, "message": str(e)}
    else:
        refusals[name] = {"producer_output": out, "exception": None}


# ---- effect_contracts ------------------------------------------------------
rec("effect_traffic_shaping", DefensiveEffectRef, t_effect.export())
rec("effect_isolation", DefensiveEffectRef, t_effect.export(mechanism_kind="ISOLATION"))
refuse("effect_no_lease", EffectExportRefused, lambda: t_effect.export(receipt=t_effect.a_receipt(expires_at="")))
refuse("effect_route_change", EffectExportRefused, lambda: t_effect.export(mechanism_kind=MechanismKind.ROUTE_CHANGE.value))
refuse("effect_unknown_mechanism", EffectExportRefused, lambda: t_effect.export(mechanism_kind=MechanismKind.UNKNOWN.value))

# ---- engagement_contracts --------------------------------------------------
soc, noc = t_eng._soc(), t_eng._noc()
for action in ("redirect", "isolate"):
    cand = build_engagement_candidate(soc, noc, t_eng._decision(action), enabled=True)
    rec(f"engagement_candidate_{action}", EngagementCandidate, cand.model_dump(mode="json"))
cand = build_engagement_candidate(soc, noc, t_eng._decision("redirect"), enabled=True)
rec("engagement_event_redirect_accepted", EngagementEvent,
    engagement_event(cand, t_eng._decision("redirect"), attacker_reaction="decoy_engaged").model_dump(mode="json"))
rec("engagement_event_redirect_downgraded_to_notify", EngagementEvent,
    engagement_event(cand, t_eng._decision("notify", reason="soc_high_but_noc_fragile"),
                     attacker_reaction="disengaged").model_dump(mode="json"))
refusals["engagement_disabled"] = {
    "producer_output": build_engagement_candidate(soc, noc, t_eng._decision("redirect"), enabled=False),
    "exception": None, "note": "enabled=False returns None (no candidate)"}
# evaluate_engagement returns a plain dict (no Fabric model): recorded, not model-validated
refusals["engagement_evaluation_downgraded_plain_dict"] = {
    "producer_output": evaluate_engagement(cand, t_eng._decision("notify", reason="soc_high_but_noc_fragile")),
    "exception": None, "note": "plain dict; Edge-local, no Fabric model"}

# ---- deception_contracts ---------------------------------------------------
# Fabric の既存の golden 用鍵に揃える（Edge テストの _KEY ではなく）。
from azazel_fabric.testing.golden import GOLDEN_DECISION_SIGNATURE_KEY as KEY
rec("deception_transition_unsigned", EnvironmentTransitionDecision, build_transition_decision(**t_dec._kw()))
signed = build_transition_decision(**t_dec._kw(), key=KEY)
assert verify_decision_signature(signed, KEY)
rec("deception_transition_signed", EnvironmentTransitionDecision, signed)
arb = {"chosen_evidence_ids": ["ev-soc-1", "ev-noc-1"], "reason": "soc_high_confidence_redirect_is_preferred"}
rec("deception_transition_from_arbiter", EnvironmentTransitionDecision,
    transition_decision_from_arbiter(arb, environment_id="env-1", current_state="baseline",
                                     target_state="smb-share-open", as_of=t_dec.AS_OF))
refuse("deception_transition_rejected_status", TransitionDecisionError,
       lambda: build_transition_decision(**t_dec._kw(status="rejected")))

# ---- outcome_contracts -----------------------------------------------------
MODELS = {"execution": ExecutionRefV0, "mechanism": MechanismObservationV0,
          "outcome": OutcomeObservationV0, "assessment": TacticalEffectAssessmentRefV0}
for action in ("throttle", "redirect"):
    bundle = from_rust_event(t_shared.rust_event(action))
    obj = t_shared._objective(bundle.correlation.decision_id)
    oc = t_shared._outcome(bundle, obj)
    asm = t_shared._assessment(bundle, obj, oc)
    corr = replace(bundle.correlation, objective_id=obj.objective_id,
                   outcome_id=oc.outcome_id, effect_assessment_id=asm.effect_assessment_id)
    out = {
        "execution": execution_to_shared_v0(bundle.correlation, bundle.execution, producer_node="edge-1"),
        "mechanism": mechanism_to_shared_v0(bundle.correlation, bundle.mechanism, producer_node="edge-1"),
        "outcome": outcome_to_shared_v0(corr, oc, producer_node="edge-1"),
        "assessment": assessment_to_shared_v0(corr, asm, obj, oc, producer_node="edge-1"),
    }
    for k, v in out.items():
        rec(f"outcome_{k}_{action}", MODELS[k], v)
    if action == "throttle":
        observed = replace(bundle.mechanism, status=MechanismStatus.OBSERVED,
                           observed_parameters={"verification_basis": "independent_postcondition"})
        rec("outcome_mechanism_throttle_observed", MechanismObservationV0,
            mechanism_to_shared_v0(bundle.correlation, observed, producer_node="edge-1"))
        route = AppliedMechanism(
            mechanism_id=bundle.correlation.mechanism_id, execution_id=bundle.correlation.execution_id,
            decision_id=bundle.correlation.decision_id, mechanism_kind=MechanismKind.ROUTE_CHANGE,
            scope={"scope_kind": "route"}, observed_parameters={}, status=MechanismStatus.UNVERIFIED,
            observed_at="2026-08-26T00:00:01Z")
        rec("outcome_mechanism_route_change_degraded_to_unknown", MechanismObservationV0,
            mechanism_to_shared_v0(bundle.correlation, route, producer_node="edge-1"))
        refuse("outcome_execution_expired", SharedOutcomeExportError,
               lambda: execution_to_shared_v0(bundle.correlation,
                                              replace(bundle.execution, status=ExecutionStatus.EXPIRED),
                                              producer_node="edge-1"))

# ---- validate + write ------------------------------------------------------
def dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"

for stem, (model, payload) in records.items():
    # A signed decision carries the transport MAC beside the model fields
    # (extra=forbid on the model), so validate the body and verify the MAC.
    body = {k: v for k, v in payload.items() if k != "decision_signature"}
    model.model_validate(body)  # raises if Fabric disagrees
    (OUT / f"{stem}.json").write_text(dump(payload), encoding="utf-8")
(OUT / "refusals.json").write_text(dump(refusals), encoding="utf-8")
print(f"fabric {azazel_fabric.__version__}: wrote {len(records)} records + refusals.json; all model_validate OK")
