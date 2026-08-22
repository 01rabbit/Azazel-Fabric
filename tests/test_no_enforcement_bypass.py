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
import azazel_fabric.engagement_contracts as ec
from azazel_fabric.deception_contracts.validation import BANNED_RUNTIME_DIRECTIVE_FIELDS
from azazel_fabric.engagement_contracts.validation import (
    BANNED_ENGAGEMENT_AUTHORITY_FIELDS,
)

_BANNED_FIELD_NAMES = set(BANNED_RUNTIME_DIRECTIVE_FIELDS) | set(
    BANNED_ENGAGEMENT_AUTHORITY_FIELDS
)


def _contract_models() -> list[type[BaseModel]]:
    seen: dict[str, type[BaseModel]] = {}
    for module in (dc, ec):
        for name in getattr(module, "__all__", []):
            obj = getattr(module, name, None)
            if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
                seen[obj.__qualname__] = obj
    return [seen[k] for k in sorted(seen)]


MODELS = _contract_models()

# Fields the doctrine PINS to one safe value (a Literal), keyed by model name.
# Verified against the wire shape; a pin means the field cannot be escalated by
# any well-formed payload.
_PINNED_LITERALS: dict[tuple[str, str], object] = {
    ("SafetyPolicy", "outbound_allowed"): False,
    ("SafetyPolicy", "production_access"): False,
    ("FiniteStateTransition", "network_egress_allowed"): False,
    ("EnvironmentActivationDecision", "decision_authority"): "azazel-edge",
    ("EnvironmentTransitionDecision", "decision_authority"): "azazel-edge",
    ("EnvironmentTerminationDecision", "decision_authority"): "azazel-edge",
    ("HostCapabilities", "authority"): "descriptive_only",
    ("PlacementPlan", "authority"): "descriptive_only",
    ("TransitionCatalog", "authority"): "descriptive_only",
    ("EngagementCandidate", "authority"): "candidate_only",
    ("EngagementAdvisory", "authority"): "advisory_only",
    ("EngagementAdvisory", "executable"): False,
    ("EffectivenessAdvisory", "authority"): "advisory_only",
    ("EffectivenessAdvisory", "executable"): False,
    ("InteractionObservation", "authority"): "descriptive_only",
}

# Safety toggles that default to the safe value but are not Literal-pinned.
_SAFE_DEFAULTS: dict[tuple[str, str], object] = {
    ("EngagementConstraint", "outbound_allowed"): False,
    ("EngagementConstraint", "production_access"): False,
}


def test_enumeration_is_non_empty():
    # Guard: if the __all__-walk silently returned nothing, the parametrized
    # tests below would vacuously pass -- fail loudly instead.
    assert len(MODELS) >= 25, f"only found {len(MODELS)} contract models"


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


_SAFETY_NAME_HINTS = ("authority", "egress", "outbound", "production_access", "executable")


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
            assert key in _PINNED_LITERALS or key in _SAFE_DEFAULTS, (
                f"{model.__name__}.{field} looks safety-sensitive but is unclassified; "
                "add it to _PINNED_LITERALS (if it gates egress/authority/execution -- "
                "and pin it Literal) or _SAFE_DEFAULTS, so it cannot silently ship escalatable"
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
