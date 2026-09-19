"""Property tests: no Fabric contract can encode an enforcement bypass (Fabric#9).

Fabric *describes*; Edge decides; the product-local host materializes. The
whole system's safety rests on the fact that no Fabric payload can, by itself,
authorize or command a runtime action. These tests encode that doctrine as
structural invariants over the *entire* contract surface, enumerated from each
family's ``__all__`` so a future model is covered automatically:

* every contract model forbids extra fields (nothing can be smuggled in);
* no contract model declares a directive/authority-bearing *field name*;
* authority/egress/execution fields that the doctrine pins are pinned to their
  single safe value (a ``Literal``), so they cannot be escalated even by a
  well-formed payload;
* the remaining safety toggles default to their safe (denied) value.

These complement the existing payload-level directive scanners
(``assert_no_runtime_directives`` etc.), which check arbitrary dicts; here we
assert the *models themselves* cannot express an escalation.
"""

from __future__ import annotations

import inspect
from typing import Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

import azazel_fabric.deception_contracts as dc
import azazel_fabric.effect_contracts as fc
import azazel_fabric.engagement_contracts as ec
import azazel_fabric.mio_contracts as mc
import azazel_fabric.outcome_contracts as oc
import azazel_fabric.provisioning_contracts as pc
import azazel_fabric.schema.defensive_state as ds
from azazel_fabric.deception_contracts.validation import BANNED_RUNTIME_DIRECTIVE_FIELDS
from azazel_fabric.effect_contracts import (
    WEAKEST_AUTHORITY,
    AuthorityClass,
    coerce_authority_class,
    is_authoritative_decision_reference,
)
from azazel_fabric.engagement_contracts.validation import (
    BANNED_ENGAGEMENT_AUTHORITY_FIELDS,
)
from azazel_fabric.mio_contracts.validation import BANNED_MIO_DIRECTIVE_FIELDS
from azazel_fabric.provisioning_contracts.validation import BANNED_PROVISIONING_FIELDS

_BANNED_FIELD_NAMES = set(BANNED_RUNTIME_DIRECTIVE_FIELDS) | set(
    BANNED_ENGAGEMENT_AUTHORITY_FIELDS
)

# Every contract family on the surface. A new family added here is covered by
# every gate below automatically.
# `schema.defensive_state` is not a `*_contracts` package, so the family sweep
# below cannot find it. It is enumerated explicitly because a model that no
# cross-cutting gate sees is exactly the drift these tests exist to catch: the
# rest of `schema` predates `extra="forbid"` and stays off the surface, but a
# model added today has no excuse to.
_CONTRACT_MODULES = (dc, ec, fc, oc, pc, mc, ds)

# The provisioning/M.I.O. families ban more field *names* than the older
# families do (command / unit / route / firewall / device-path / executor /
# boolean-authorization / trust-decision, and tool-call / link / follow-up).
# That stricter ban applies only to them: `deception_contracts.ImageManifest`
# legitimately carries `verified`, which the provisioning ban forbids, because
# a provisioning record must not record a trust verdict at all.
_R1_MODULES = (pc, mc)

# Known gap, recorded rather than hidden. `cti_contracts` is a contract family
# but is NOT on this gated surface: `CtiEventBatch`, `CtiFlowBatch`,
# `CtiReactionBatch`, and `CtiContextRequest` predate the `extra="forbid"`
# convention (they shipped in v0.1.0), and tightening them is a breaking change
# to a published contract that needs its own decision and migration note, not a
# quiet test-side fix. The family's advisory-only invariants are covered by
# `tests/test_cti_contracts.py` in the meantime.
_UNGATED_FAMILIES = frozenset({"cti_contracts"})
_R1_BANNED_FIELD_NAMES = set(BANNED_PROVISIONING_FIELDS) | set(BANNED_MIO_DIRECTIVE_FIELDS)


def _contract_models() -> list[type[BaseModel]]:
    seen: dict[str, type[BaseModel]] = {}
    for module in _CONTRACT_MODULES:
        for name in getattr(module, "__all__", []):
            obj = getattr(module, name, None)
            if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
                seen[obj.__qualname__] = obj
    return [seen[k] for k in sorted(seen)]


MODELS = _contract_models()


def _r1_models() -> list[type[BaseModel]]:
    seen: dict[str, type[BaseModel]] = {}
    for module in _R1_MODULES:
        for name in getattr(module, "__all__", []):
            obj = getattr(module, name, None)
            if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
                seen[obj.__qualname__] = obj
    return [seen[k] for k in sorted(seen)]


R1_MODELS = _r1_models()

# Fields the doctrine PINS to one safe value (a Literal), keyed by model name.
# Verified against the wire shape; a pin means the field cannot be escalated by
# any well-formed payload.
_PINNED_LITERALS: dict[tuple[str, str], object] = {
    ("SafetyPolicy", "outbound_allowed"): False,
    ("SafetyPolicy", "production_access"): False,
    ("SafetyPolicy", "privileged_containers"): False,
    ("SafetyPolicy", "host_network"): False,
    ("SafetyPolicy", "runtime_socket_exposed_to_decoys"): False,
    ("SafetyPolicy", "edge_control_access_from_decoys"): False,
    ("ComponentManifest", "privileged"): False,
    ("ComponentManifest", "host_network"): False,
    ("FiniteStateTransition", "network_egress_allowed"): False,
    ("FiniteStateTransition", "requires_edge_approval"): True,
    ("CredentialLure", "decoy_only"): True,
    ("NarrativeManifest", "synthetic_only"): True,
    ("EnvironmentActivationDecision", "decision_authority"): "azazel-edge",
    ("EnvironmentTransitionDecision", "decision_authority"): "azazel-edge",
    ("EnvironmentTerminationDecision", "decision_authority"): "azazel-edge",
    # A defensive-state projection reports a posture a product-local authority
    # already selected. Pinned so the word itself can never carry a warrant.
    ("DefensiveStateProjection", "authority"): "descriptive_only",
    ("HostCapabilities", "authority"): "descriptive_only",
    ("PlacementPlan", "authority"): "descriptive_only",
    ("TransitionCatalog", "authority"): "descriptive_only",
    ("EngagementCandidate", "authority"): "candidate_only",
    ("EngagementAdvisory", "authority"): "advisory_only",
    ("EngagementAdvisory", "executable"): False,
    ("EffectivenessAdvisory", "authority"): "advisory_only",
    ("EffectivenessAdvisory", "executable"): False,
    ("InteractionObservation", "authority"): "descriptive_only",
    # Outcome-as-Evidence facts (v0.9.0rc1): a producer states a fact or a
    # non-executable assessment; neither carries action authority.
    ("ExecutionRefV0", "authority_class"): "producer_execution_fact",
    ("MechanismObservationV0", "authority_class"): "producer_mechanism_fact",
    ("OutcomeObservationV0", "authority_class"): "producer_outcome_fact",
    ("TacticalEffectAssessmentRefV0", "authority_class"): "producer_assessment_fact",
    # Cross-series effect family (Fabric#15). `directive` is pinned False on
    # every shared record so that carrying an effect name can never make one an
    # execution token; `describes` keeps presented terrain on the defender's
    # side of the surface; `confers_authority` keeps provenance from reading as
    # authorization.
    ("DefensiveEffectRef", "directive"): False,
    ("EffectObservation", "directive"): False,
    ("PresentedTerrainRef", "directive"): False,
    ("PresentedTerrainRef", "describes"): "defender_presented_surface",
    ("OutcomeObservationEnvelope", "directive"): False,
    ("ReplayProvenance", "confers_authority"): False,
    ("TacticalEffectAssessmentRefV0", "executable"): False,
    # R1a provisioning family: every record describes, and the receipt only
    # observes. Nothing in the family can be escalated to an authorization.
    ("ActivationReceipt", "authority"): "observation_only",
    ("AssetManifest", "authority"): "descriptive_only",
    ("AssetManifest", "declared_regular_files_only"): True,
    ("AuditCheckpointProjection", "authority"): "descriptive_only",
    ("CommissioningRecord", "authority"): "descriptive_only",
    ("CompatibilityManifest", "authority"): "descriptive_only",
    ("HardwareInventory", "authority"): "descriptive_only",
    ("InterfaceAssignment", "authority"): "descriptive_only",
    ("ModelManifest", "authority"): "descriptive_only",
    ("ModelManifest", "model_supplied_code"): False,
    ("ModelManifest", "dynamic_loader"): False,
    ("ModelManifest", "native_plugins"): False,
    ("ModelManifest", "executable_serialization"): False,
    ("ModelManifest", "network_fetch_on_load"): False,
    ("ProductManifest", "authority"): "descriptive_only",
    ("ProposedGenerationDescriptor", "authority"): "descriptive_only",
    ("ResourceProfile", "authority"): "descriptive_only",
    ("SecurityStateProjection", "authority"): "descriptive_only",
    ("TopologyProfile", "authority"): "descriptive_only",
    # R1a M.I.O. family: model output is advisory and inert, and a sanitized
    # frame structurally cannot carry raw evidence off the node.
    ("AdvisoryResult", "authority"): "advisory_only",
    ("AdvisoryResult", "executable"): False,
    ("AdvisoryResult", "may_request_followup"): False,
    ("AdvisoryResult", "contains_links"): False,
    ("ClaimSet", "authority"): "descriptive_only",
    ("MergedAdvisory", "authority"): "advisory_only",
    ("MergedAdvisory", "executable"): False,
    ("SanitizedRemoteFrame", "authority"): "descriptive_only",
    ("SanitizedRemoteFrame", "contains_raw_evidence"): False,
    ("SituationFrame", "authority"): "descriptive_only",
}

# Safety toggles that default to the safe value but are intentionally NOT
# Literal-pinned. EngagementConstraint is attached to a candidate_only-authority
# EngagementCandidate (a *request* the arbiter evaluates), not to SafetyPolicy
# (which governs what AZ-06 itself will build and is therefore pinned). Per
# "Fabric describes, Edge decides", a candidate asking for outbound is not a
# grant -- nothing in Fabric turns this field into an egress action -- so it is
# a bounded, escalatable-by-request declaration that defaults denied, not a pin.
_SAFE_DEFAULTS: dict[tuple[str, str], object] = {
    ("EngagementConstraint", "outbound_allowed"): False,
    ("EngagementConstraint", "production_access"): False,
}

# A third, narrower classification, for a safety-sensitive field that is a
# *distinction* rather than a toggle.
#
# The cross-series effect family (Fabric#15) requires every shared record to
# make six readings distinguishable -- observed fact, producer decision,
# advisory inference, planned/shadow, active/materialized, stale/unknown. A
# field whose whole job is to tell those apart cannot be pinned to one value
# without destroying what it is for.
#
# So the safety property is different in kind, and is verified rather than
# asserted: the enum must declare where an *unrecognized* value lands, and that
# landing place must be the member that claims least. Membership in this dict
# is not an exemption -- `test_a_classified_authority_enum_fails_safe` below
# runs that check against every entry, and a field listed here without a
# fail-safe fallback fails just as loudly as an unclassified one would.
_CLASSIFIED_AUTHORITY_ENUMS: dict[tuple[str, str], tuple[object, object]] = {
    ("DefensiveEffectRef", "authority_class"): (AuthorityClass, WEAKEST_AUTHORITY),
    ("EffectObservation", "authority_class"): (AuthorityClass, WEAKEST_AUTHORITY),
    ("PresentedTerrainRef", "authority_class"): (AuthorityClass, WEAKEST_AUTHORITY),
    ("OutcomeObservationEnvelope", "authority_class"): (AuthorityClass, WEAKEST_AUTHORITY),
}


@pytest.mark.parametrize(
    "key,spec",
    sorted(_CLASSIFIED_AUTHORITY_ENUMS.items()),
    ids=lambda x: x if isinstance(x, str) else None,
)
def test_a_classified_authority_enum_fails_safe(key, spec):
    model_name, field = key
    enum_type, weakest = spec

    model = next((m for m in MODELS if m.__name__ == model_name), None)
    assert model is not None, f"{model_name} is not on the gated surface"
    assert field in model.model_fields, f"{model_name}.{field} no longer exists"
    assert model.model_fields[field].annotation is enum_type, (
        f"{model_name}.{field} is no longer a {enum_type.__name__}; "
        "re-classify it rather than leaving it here"
    )

    # The point of the classification: an unreadable value claims the least.
    for hostile in ("", "ACTIVE_MATERIALIZED", "producer_decision_ref ", None, 0, []):
        coerced, recognized = coerce_authority_class(hostile)
        assert recognized is False
        assert coerced is weakest

    # And "the least" must really be the least -- a future reordering that made
    # the fallback a stronger member must fail here, not in production.
    assert weakest is AuthorityClass.STALE_OR_UNKNOWN
    assert is_authoritative_decision_reference(weakest) is False


def test_enumeration_is_non_empty():
    # Guard: if the __all__-walk silently returned nothing, the parametrized
    # tests below would vacuously pass -- fail loudly instead.
    assert len(MODELS) >= 25, f"only found {len(MODELS)} contract models"
    assert len(R1_MODELS) >= 20, f"only found {len(R1_MODELS)} R1a contract models"


def test_every_contract_family_is_on_the_gated_surface():
    # Self-extending guard, discovered from the package rather than from the
    # list under test: every `*_contracts` subpackage must be enumerated in
    # _CONTRACT_MODULES, so a new family cannot ship ungated -- and dropping one
    # from the list fails here rather than quietly shrinking the surface.
    from pathlib import Path

    import azazel_fabric

    families = {
        path.parent.name
        for path in Path(azazel_fabric.__file__).parent.glob("*_contracts/__init__.py")
    }
    assert families, "no contract family found in the package"
    enumerated = {module.__name__.rsplit(".", 1)[-1] for module in _CONTRACT_MODULES}
    missing = sorted(families - enumerated - _UNGATED_FAMILIES)
    assert not missing, (
        f"contract famil(ies) {missing} are not on the gated surface; add them to "
        "_CONTRACT_MODULES, or record why not in _UNGATED_FAMILIES"
    )

    for module in _CONTRACT_MODULES:
        contributed = [
            name
            for name in getattr(module, "__all__", [])
            if any(m.__name__ == name for m in MODELS)
        ]
        assert contributed, f"{module.__name__} contributed no model to the gate"


@pytest.mark.parametrize("model", R1_MODELS, ids=lambda m: m.__name__)
def test_r1_model_declares_no_provisioning_or_cognition_directive_field(model):
    # The stricter R1a ban: no command, unit, route, firewall rule, device path,
    # executor, boolean authorization, trust decision, tool call, link, or
    # follow-up request may appear as a FIELD NAME on a provisioning/M.I.O.
    # record, not merely be rejected inside a payload.
    offending = set(model.model_fields) & _R1_BANNED_FIELD_NAMES
    assert not offending, (
        f"{model.__name__} declares directive/authorization/trust-decision field(s): "
        f"{sorted(offending)}"
    )


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_model_forbids_extra_fields(model: type[BaseModel]):
    assert model.model_config.get("extra") == "forbid", (
        f"{model.__name__} must set extra='forbid' so no field can be smuggled in"
    )


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_model_declares_no_directive_field(model: type[BaseModel]):
    offending = set(model.model_fields) & _BANNED_FIELD_NAMES
    assert not offending, (
        f"{model.__name__} declares directive/authority-bearing field(s): {sorted(offending)}"
    )


def _literal_values(model: type[BaseModel], field: str) -> set[object] | None:
    ann = model.model_fields[field].annotation
    if get_origin(ann) is Literal:
        return set(get_args(ann))
    return None


@pytest.mark.parametrize(
    "key,expected", sorted(_PINNED_LITERALS.items()), ids=lambda x: x if isinstance(x, str) else None
)
def test_pinned_authority_and_egress_fields_are_literal_safe(key, expected):
    model_name, field = key
    model = next((m for m in MODELS if m.__name__ == model_name), None)
    assert model is not None, f"{model_name} not found in the contract surface"
    assert field in model.model_fields, f"{model_name}.{field} no longer exists"
    values = _literal_values(model, field)
    assert values == {expected}, (
        f"{model_name}.{field} must be Literal[{expected!r}] (pinned, non-escalatable); "
        f"got {values!r}"
    )


@pytest.mark.parametrize(
    "key,expected", sorted(_SAFE_DEFAULTS.items()), ids=lambda x: x if isinstance(x, str) else None
)
def test_safety_toggles_default_denied(key, expected):
    model_name, field = key
    model = next((m for m in MODELS if m.__name__ == model_name), None)
    assert model is not None, f"{model_name} not found"
    default = model.model_fields[field].default
    assert default is expected, (
        f"{model_name}.{field} must default to {expected!r} (safe/denied by default); "
        f"got {default!r}"
    )


_SAFETY_NAME_HINTS = (
    "authority", "egress", "outbound", "production_access", "executable",
    # container/host-isolation escalation vectors (privileged, host networking,
    # runtime-socket / edge-control exposure to decoys)
    "privileged", "host_network", "socket", "control_access",
)


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_safety_sensitive_fields_are_classified(model: type[BaseModel]):
    # Self-extending guard: any field whose name looks like it gates authority,
    # egress, or execution MUST be explicitly classified as either Literal-pinned
    # or safe-default above. A future model that adds such a field (and forgets to
    # pin/classify it) fails here, forcing a conscious safety decision rather than
    # silently shipping an escalatable field.
    for field in model.model_fields:
        low = field.lower()
        if any(hint in low for hint in _SAFETY_NAME_HINTS):
            key = (model.__name__, field)
            assert (
                key in _PINNED_LITERALS
                or key in _SAFE_DEFAULTS
                or key in _CLASSIFIED_AUTHORITY_ENUMS
            ), (
                f"{model.__name__}.{field} looks safety-sensitive but is unclassified; "
                "add it to _PINNED_LITERALS (if it gates egress/authority/execution -- "
                "and pin it Literal), _SAFE_DEFAULTS, or _CLASSIFIED_AUTHORITY_ENUMS "
                "(only for a distinction with a verified weakest fallback), so it "
                "cannot silently ship escalatable"
            )


def test_every_bool_literal_field_is_pinned_and_registered():
    # Definitive, self-discovering guard: EVERY single-value Literal[bool] field
    # in any contract is a safety toggle pinned in the wire shape. Enumerate them
    # directly (not by name) and assert each is registered in _PINNED_LITERALS
    # with its actual pinned value. This closes the name-based blind spot that
    # let decoy_only / requires_edge_approval / synthetic_only slip past the
    # hint scanner, and auto-flags any future bool-Literal safety field.
    discovered: dict[tuple[str, str], bool] = {}
    for model in MODELS:
        for field, info in model.model_fields.items():
            ann = info.annotation
            if get_origin(ann) is Literal:
                args = get_args(ann)
                if len(args) == 1 and isinstance(args[0], bool):
                    discovered[(model.__name__, field)] = args[0]

    unregistered = sorted(k for k in discovered if k not in _PINNED_LITERALS)
    assert not unregistered, (
        "single-value Literal[bool] safety fields missing from _PINNED_LITERALS "
        f"(register each with its pinned value): {unregistered}"
    )
    for key, value in discovered.items():
        assert _PINNED_LITERALS[key] == value, (
            f"{key[0]}.{key[1]} is Literal[{value}] in the model but registered as "
            f"{_PINNED_LITERALS[key]!r}"
        )


def test_engagement_advisory_cannot_be_made_executable():
    # Concrete escalation attempt: the model must reject executable=True.
    with pytest.raises(ValidationError):
        ec.EngagementAdvisory(
            advisory_id="a",
            advisor="azazel-knowledge",
            confidence=0.5,
            behavior_class="adaptive_probe",
            posture_suggestion=ec.PostureSuggestion(
                objective="collect", approach="channel",
                supported_activities=["redirect_to_decoy"], reasons=["r"],
            ),
            limitations=["x"],
            executable=True,  # escalation -> Literal[False] rejects it
        )


def test_transition_decision_authority_cannot_be_forged():
    # A payload naming a different authority must be rejected by the Literal.
    with pytest.raises(ValidationError):
        dc.EnvironmentTransitionDecision(
            decision_id="d", status="accepted", environment_id="e",
            current_state="a", target_state="b",
            effective_at="2026-08-20T00:00:00+00:00",
            expires_at="2026-08-22T00:00:00+00:00",
            decision_authority="attacker",  # not "azazel-edge"
        )
