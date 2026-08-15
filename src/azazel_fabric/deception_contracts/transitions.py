"""Finite-state transition catalog for AZ-06.

A live decoy is never hand-edited. When a change is wanted mid-engagement it is
the *selection* of a pre-authored, frozen, signed transition — never an ad-hoc
mutation. This module defines that catalog: a bounded set of
:class:`FiniteStateTransition` entries, each declaring — per Azazel-Deception#6
and Azazel#61 — its current/target state, an evidence-backed trigger, the
expected observation, resource/time/network bounds, rollback and termination
conditions, and a mandatory Edge-approval requirement.

The catalog is bound to one package identity and is frozen by a normalize-first
content digest (:mod:`azazel_fabric.deception_integrity`), so its transitions
cannot drift after signing. AZ-06 executes only catalog entries authorized by
Edge; :func:`select_transition` fails closed on anything not in the catalog.

Authority rule: the catalog is ``descriptive_only``. It enumerates what *may* be
transitioned to; Edge alone decides *whether*, via an
``EnvironmentTransitionDecision``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from azazel_fabric.deception_contracts.models import ResourceBudget

_DIGEST_PREFIX = "sha256:"


def _valid_sha256(value: str) -> str:
    if not value.startswith(_DIGEST_PREFIX):
        raise ValueError("digest must use sha256:<64 lowercase hex> format")
    digest = value[len(_DIGEST_PREFIX) :]
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("digest must use sha256:<64 lowercase hex> format")
    return value


class FiniteStateTransition(BaseModel):
    """One pre-authored, bounded transition between two decoy states.

    Every field the doctrine requires a transition to declare is mandatory in
    the wire shape, so a transition that omits its trigger, expected
    observation, bounds, rollback, or termination conditions fails closed at
    construction. ``requires_edge_approval`` is pinned True — a catalog can
    never express a self-authorizing transition. Decoy egress is denied by
    construction (``network_egress_allowed`` is pinned False).
    """

    model_config = ConfigDict(extra="forbid")

    transition_id: str = Field(min_length=1)
    from_state: str = Field(min_length=1)
    to_state: str = Field(min_length=1)
    evidence_backed_trigger: str = Field(min_length=1)
    expected_observation: str = Field(min_length=1)
    bounds: ResourceBudget
    # Bounded structural change: how many new decoy surfaces this may open.
    max_new_surfaces: int = Field(ge=0, default=0)
    network_egress_allowed: Literal[False] = False
    rollback_state: str = Field(min_length=1)
    termination_conditions: list[str] = Field(min_length=1)
    requires_edge_approval: Literal[True] = True

    @model_validator(mode="after")
    def _states_must_differ(self) -> "FiniteStateTransition":
        if self.from_state == self.to_state:
            raise ValueError("from_state and to_state must differ")
        return self


class TransitionCatalog(BaseModel):
    """A frozen, signed set of transitions bound to one package identity."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transition-catalog/v0.1"] = "transition-catalog/v0.1"
    catalog_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    package_digest: str
    transitions: list[FiniteStateTransition] = Field(min_length=1)
    catalog_digest: str
    signer_ref: str = Field(min_length=1)
    signature_ref: str | None = None
    authority: Literal["descriptive_only"] = "descriptive_only"

    _package_digest = field_validator("package_digest")(_valid_sha256)
    _catalog_digest = field_validator("catalog_digest")(_valid_sha256)

    @model_validator(mode="after")
    def _transition_ids_unique(self) -> "TransitionCatalog":
        ids = [t.transition_id for t in self.transitions]
        if len(ids) != len(set(ids)):
            raise ValueError("transition_id values must be unique within a catalog")
        return self


class TransitionNotInCatalog(ValueError):
    """Raised when a requested transition is absent from the frozen catalog."""


def select_transition(
    catalog: TransitionCatalog,
    *,
    current_state: str,
    target_state: str,
) -> FiniteStateTransition:
    """Return the catalog transition matching a current->target request.

    Fail-closed: a request whose (current_state, target_state) pair has no
    frozen catalog entry raises :class:`TransitionNotInCatalog`. This is how
    "AZ-06 executes only catalog entries authorized by Edge" is enforced — an
    Edge ``EnvironmentTransitionDecision`` can only resolve to a transition
    that was pre-authored and signed into the catalog.
    """

    for transition in catalog.transitions:
        if transition.from_state == current_state and transition.to_state == target_state:
            return transition
    raise TransitionNotInCatalog(
        f"no frozen transition {current_state!r} -> {target_state!r} in catalog "
        f"{catalog.catalog_id!r}"
    )
