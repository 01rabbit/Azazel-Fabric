"""Published golden Edge-decision vectors (Fabric#9), consumable cross-repo.

These are the canonical decision scenarios Fabric#9 enumerates, exposed as an
importable API so AZ-06 / Edge / Knowledge tests can consume the *same* vectors
Fabric ships (rather than each hand-rolling their own). Every vector is built
from the validated models (valid-by-construction) and is deterministic — no
wall-clock or randomness — so the returned dicts are byte-stable across
processes and repos.

``GOLDEN_DECISION_SIGNATURE_KEY`` is a documented, non-secret key used ONLY to
sign the signature vectors reproducibly; it is never a real transport key.
"""

from __future__ import annotations

from typing import Any, Callable

from azazel_fabric.deception_contracts import (
    DEFAULT_DECISION_SIGNATURE_FIELD,
    EnvironmentActivationDecision,
    EnvironmentTransitionDecision,
    ResourceBudget,
    sign_decision,
)

GOLDEN_DECISION_SIGNATURE_KEY = "golden-fixture-transport-key-v1"

_A = "2026-08-20T00:00:00+00:00"
_B = "2026-08-22T00:00:00+00:00"
_SHA = "sha256:" + "a" * 64


def golden_activation_accepted() -> dict[str, Any]:
    return EnvironmentActivationDecision(
        decision_id="golden-act-accepted", status="accepted", package_id="pkg-golden",
        package_digest=_SHA, target_node_id="node-1", selected_tier="minimal",
        budget=ResourceBudget(cpu_cores=1.0, memory_mb=256, storage_mb=512),
        effective_at=_A, expires_at=_B, reason_codes=["soc_high_confidence"],
    ).model_dump(mode="json")


def golden_transition_modified() -> dict[str, Any]:
    return EnvironmentTransitionDecision(
        decision_id="golden-trans-modified", status="modified", environment_id="env-1",
        current_state="baseline", target_state="smb-share-open",
        effective_at=_A, expires_at=_B, reason_codes=["noc_fragile_downgrade"],
    ).model_dump(mode="json")


def golden_transition_rejected() -> dict[str, Any]:
    return EnvironmentTransitionDecision(
        decision_id="golden-trans-rejected", status="rejected", environment_id="env-1",
        current_state="baseline", target_state="smb-share-open",
        effective_at=_A, expires_at=_B, reason_codes=["blast_radius_too_wide"],
    ).model_dump(mode="json")


def golden_decision_stale() -> dict[str, Any]:
    stale = EnvironmentTransitionDecision(
        decision_id="golden-trans-stale", status="accepted", environment_id="env-1",
        current_state="baseline", target_state="smb-share-open",
        effective_at="2020-01-01T00:00:00+00:00", expires_at="2020-01-02T00:00:00+00:00",
    ).model_dump(mode="json")
    # Non-contract test marker: a reference time the decision is stale against.
    stale["_reference_as_of"] = "2026-08-21T00:00:00+00:00"
    return stale


def golden_decision_signed_valid() -> dict[str, Any]:
    return sign_decision(
        EnvironmentTransitionDecision(
            decision_id="golden-trans-signed", status="accepted", environment_id="env-1",
            current_state="baseline", target_state="smb-share-open",
            effective_at=_A, expires_at=_B,
        ).model_dump(mode="json"),
        GOLDEN_DECISION_SIGNATURE_KEY,
    )


def golden_decision_signature_tampered() -> dict[str, Any]:
    tampered = golden_decision_signed_valid()
    tampered["target_state"] = "isolate"  # changed after signing -> verify fails
    return tampered


def golden_transition_unsupported_schema() -> dict[str, Any]:
    bad = EnvironmentTransitionDecision(
        decision_id="golden-trans-badschema", status="accepted", environment_id="env-1",
        current_state="baseline", target_state="smb-share-open",
        effective_at=_A, expires_at=_B,
    ).model_dump(mode="json")
    bad["schema_version"] = "environment-transition-decision/v9.9"
    return bad


_GOLDEN_DECISIONS: dict[str, Callable[[], dict[str, Any]]] = {
    "activation_accepted": golden_activation_accepted,
    "transition_modified": golden_transition_modified,
    "transition_rejected": golden_transition_rejected,
    "decision_stale": golden_decision_stale,
    "decision_signed_valid": golden_decision_signed_valid,
    "decision_signature_tampered": golden_decision_signature_tampered,
    "transition_unsupported_schema": golden_transition_unsupported_schema,
}


def golden_decision_names() -> list[str]:
    """Names of every published golden decision vector, sorted."""
    return sorted(_GOLDEN_DECISIONS)


def load_golden_decision(name: str) -> dict[str, Any]:
    """Return a fresh copy of the named golden decision vector (fail-closed)."""
    try:
        builder = _GOLDEN_DECISIONS[name]
    except KeyError:
        raise KeyError(
            f"unknown golden decision {name!r}; available: {golden_decision_names()}"
        ) from None
    return builder()


__all__ = [
    "GOLDEN_DECISION_SIGNATURE_KEY",
    "DEFAULT_DECISION_SIGNATURE_FIELD",
    "golden_decision_names",
    "load_golden_decision",
] + [f.__name__ for f in _GOLDEN_DECISIONS.values()]
