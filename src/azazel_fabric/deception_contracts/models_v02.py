"""PROPOSAL (not adopted): v0.2 Deception #55 observation-binding shapes.

Separate classes, not subclasses: a v0.2 payload is never an instance of a v0.1
class and vice versa. Every reference reuses the shared typed-ref grammar
(``effect_contracts.refs``); nothing here defines a second one.

Owner semantics (see ``docs/deception55-observation-binding-v02.md``): Edge alone
issues, renews and revokes the lease and decides or withdraws the activation.
Fabric only *describes* the references. Deception never authorizes, extends or
chooses; it records what it observed under a lease it was given.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from azazel_fabric.deception_contracts.models import (
    DecisionStatus,
    ResourceBudget,
    SafetyPolicy,
    _valid_sha256,
)
from azazel_fabric.deception_contracts.observation import (
    ConfounderTag,
    InteractionSurface,
    ObservationClass,
    ReactionKind,
    RuntimeContext,
)
from azazel_fabric.deception_contracts.validation import (
    assert_no_effectiveness_verdict,
    assert_no_runtime_directives,
)
from azazel_fabric.effect_contracts.ref_annotations import require_unique, typed_ref
from azazel_fabric.effect_contracts.refs import RefKind, parse_ref

MAX_HYPOTHESIS_REFS = 16
MAX_EVIDENCE_REFS = 32

DECISION_V02 = "environment-activation-decision/v0.2"
OBSERVATION_V02 = "interaction-observation/v0.2"
DECISION_V01 = "environment-activation-decision/v0.1"
OBSERVATION_V01 = "interaction-observation/v0.1"

EnvironmentRef = typed_ref(RefKind.ENVIRONMENT)
DecisionRef = typed_ref(RefKind.DECISION)
TraceRef = typed_ref(RefKind.TRACE)
# A dedicated kind, so an Engage/action ``advisory:`` ref cannot fill this slot.
# Only the reference lives here: the objective payload is a separate, M.I.O.-owned,
# non-executable contract delivered in a distinct M.I.O. PR, not by this module.
ObservationObjectiveRef = typed_ref(RefKind.OBSERVATION_OBJECTIVE)
FrameRef = typed_ref(RefKind.FRAME)
HypothesisRef = typed_ref(RefKind.HYPOTHESIS)
LeaseRef = typed_ref(RefKind.LEASE)
SessionRef = typed_ref(RefKind.SESSION)
EvidenceRef = typed_ref(RefKind.EVIDENCE)
# A lure is a synthetic artifact the terrain presented; no "lure" kind exists.
LureRef = typed_ref(RefKind.ARTIFACT)

MAX_REASON_CODES = 16
MAX_ID_LENGTH = 128
_REASON_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_IPV4_IN_TEXT = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")


def _bounded_codes(value: tuple[str, ...]) -> tuple[str, ...]:
    for code in value:
        if not _REASON_CODE.fullmatch(code):
            raise ValueError("reason_codes entries must match [a-z][a-z0-9_]{0,63}")
    return require_unique(value, field="reason_codes")


class _V02(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EnvironmentActivationDecisionV02(_V02):
    """Edge's decision, carrying the join keys an observation must echo.

    ``expires_at`` (v0.1-compatible) is the Edge activation-decision acceptance
    window, used when accepting the activation. ``lease_expires_at`` is the
    separate end of the runtime lease Edge issued. The lease cannot outlive the
    signed authorization: ``effective_at < lease_expires_at <= expires_at``.
    """

    schema_version: Literal["environment-activation-decision/v0.2"] = DECISION_V02
    decision_id: DecisionRef
    decision_authority: Literal["azazel-edge"] = "azazel-edge"
    status: DecisionStatus
    package_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    package_digest: str
    target_node_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    selected_tier: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    budget: ResourceBudget
    safety: SafetyPolicy = Field(default_factory=SafetyPolicy)
    effective_at: AwareDatetime
    expires_at: AwareDatetime
    evidence_refs: tuple[EvidenceRef, ...] = Field(default=(), max_length=MAX_EVIDENCE_REFS)
    reason_codes: tuple[str, ...] = Field(default=(), max_length=MAX_REASON_CODES)
    # --- v0.2 binding (all required, all opaque refs; no free text) ---
    environment_id: EnvironmentRef
    trace_id: TraceRef
    observation_objective_ref: ObservationObjectiveRef
    frame_ref: FrameRef
    hypothesis_refs: tuple[HypothesisRef, ...] = Field(min_length=1, max_length=MAX_HYPOTHESIS_REFS)
    lease_ref: LeaseRef
    lease_expires_at: AwareDatetime

    _package_digest = field_validator("package_digest")(_valid_sha256)

    @field_validator("hypothesis_refs")
    @classmethod
    def _hyp_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return require_unique(value, field="hypothesis_refs")

    _reason_codes = field_validator("reason_codes")(_bounded_codes)

    @model_validator(mode="after")
    def _time_invariants(self) -> "EnvironmentActivationDecisionV02":
        if self.expires_at <= self.effective_at:
            raise ValueError("expires_at must be later than effective_at")
        if self.lease_expires_at <= self.effective_at:
            raise ValueError("lease_expires_at must be later than effective_at")
        if self.lease_expires_at > self.expires_at:
            raise ValueError("lease_expires_at must not be later than expires_at")
        return self


class InteractionObservationV02(_V02):
    """A fact-only observation bound to one decision/lease. No metadata bag."""

    schema_version: Literal["interaction-observation/v0.2"] = OBSERVATION_V02
    observation_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    environment_id: EnvironmentRef
    package_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    node_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    observed_at: AwareDatetime
    observation_class: ObservationClass
    surface: InteractionSurface
    reaction_kind: ReactionKind | None = None
    lure_ref: LureRef | None = None
    first_contact_latency_ms: int | None = Field(default=None, ge=0)
    dwell_ms: int | None = Field(default=None, ge=0)
    attempt_count: int | None = Field(default=None, ge=0)
    confounder_tags: tuple[ConfounderTag, ...] = ()
    runtime_context: RuntimeContext | None = None
    authority: Literal["descriptive_only"] = "descriptive_only"
    evidence_refs: tuple[EvidenceRef, ...] = Field(default=(), max_length=MAX_EVIDENCE_REFS)
    # --- v0.2 provenance (all required) ---
    decision_ref: DecisionRef
    trace_id: TraceRef
    observation_objective_ref: ObservationObjectiveRef
    frame_ref: FrameRef
    hypothesis_refs: tuple[HypothesisRef, ...] = Field(min_length=1, max_length=MAX_HYPOTHESIS_REFS)
    lease_ref: LeaseRef
    #: Opaque, minted per runtime generation by the observing runtime. Must carry
    #: no source address, credential material or lure identity; only address and
    #: credential shapes are rejected structurally. Lure/session non-linkage and
    #: per-generation uniqueness are producer duties (unresolved semantic binding).
    session_ref: SessionRef

    @field_validator("hypothesis_refs")
    @classmethod
    def _hyp_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return require_unique(value, field="hypothesis_refs")

    @field_validator("session_ref")
    @classmethod
    def _session_is_not_identity(cls, value: str) -> str:
        _, body = parse_ref(value)
        if "@" in body or "=" in body or _IPV4_IN_TEXT.search(body):
            raise ValueError("session_ref must not embed an address or account identity")
        try:
            ipaddress.ip_address(body)
        except ValueError:
            return value
        raise ValueError("session_ref must not be an IP address")

    @model_validator(mode="after")
    def _invariants(self) -> "InteractionObservationV02":
        if self.observation_class == "interaction" and self.reaction_kind is not None:
            raise ValueError(
                "observation_class 'interaction' cannot carry a reaction_kind; "
                "use 'reaction' or 'outcome' for post-contact behavior"
            )
        return self


# ---------------------------------------------------------------------------
# Pure cross-check
# ---------------------------------------------------------------------------


class ObservationBindingError(ValueError):
    """The observation does not belong to the decision/lease it claims."""


def check_observation_binding(
    observation: InteractionObservationV02, decision: EnvironmentActivationDecisionV02
) -> None:
    """Raise :class:`ObservationBindingError` unless ``observation`` is
    structurally consistent with ``decision``. Pure: no clock, I/O or mutation.

    This is a structural cross-check only (equality and ordering). It does NOT:

    * authenticate the decision. Edge must verify the decision signature on the
      original unnormalized signed mapping, using the shared canonicalization
      (``verify_decision_signature``), before Pydantic parsing. The signature
      member is then removed before parsing because the models use
      ``extra="forbid"``. Do not re-dump the normalized model for verification:
      defaults and datetime normalization can alter the canonical payload. This
      proves origin/integrity only, not authorization or liveness. Raw wire
      bytes are not what is signed.
    * authenticate the observation or its ``observed_at``. ``observed_at`` is
      asserted by the producing runtime; the observation producer must be
      authenticated separately. No such mechanism exists yet -- an unresolved
      integration requirement.
    * establish that the lease is currently live. It cannot see a later
      revoke, terminate or renewal, nor check the package digest. Edge must
      consult its own current lease/decision state, use its own receipt clock
      for current lease/revocation, and confirm the package digest from the
      immutable artifact before activation.

    It grants, extends and renews nothing. The accepted window is
    ``[decision.effective_at, decision.lease_expires_at)`` (the lease, not the
    acceptance window ``expires_at``, though the lease cannot exceed it). All
    datetimes are timezone-aware, so comparison is by instant.
    """

    if not isinstance(observation, InteractionObservationV02) or not isinstance(
        decision, EnvironmentActivationDecisionV02
    ):
        raise ObservationBindingError(
            "binding requires v0.2 types; a v0.1 record cannot stand in for a v0.2 one"
        )
    pairs = (
        ("environment_id", observation.environment_id, decision.environment_id),
        ("package_id", observation.package_id, decision.package_id),
        ("node_id", observation.node_id, decision.target_node_id),
        ("decision_ref", observation.decision_ref, decision.decision_id),
        ("trace_id", observation.trace_id, decision.trace_id),
        (
            "observation_objective_ref",
            observation.observation_objective_ref,
            decision.observation_objective_ref,
        ),
        ("frame_ref", observation.frame_ref, decision.frame_ref),
        ("lease_ref", observation.lease_ref, decision.lease_ref),
    )
    for name, got, want in pairs:
        if got != want:
            raise ObservationBindingError(f"{name} does not match the activation decision")
    if set(observation.hypothesis_refs) != set(decision.hypothesis_refs):
        raise ObservationBindingError("hypothesis_refs do not match the activation decision")
    if decision.status not in ("accepted", "modified", "downgraded"):
        raise ObservationBindingError(
            f"activation decision status {decision.status!r} does not accept observation"
        )
    if observation.observed_at < decision.effective_at:
        raise ObservationBindingError("observation was made before the decision took effect")
    if observation.observed_at >= decision.lease_expires_at:
        raise ObservationBindingError("observation was made at or after lease expiry")


# ---------------------------------------------------------------------------
# Explicit parsers / dispatch
# ---------------------------------------------------------------------------


def _version(raw: Mapping[str, Any], what: str) -> Any:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{what} must be a mapping")
    return raw.get("schema_version")


def parse_activation_decision_v02(raw: Mapping[str, Any]) -> EnvironmentActivationDecisionV02:
    version = _version(raw, "activation decision")
    if version != DECISION_V02:
        raise ValueError(f"expected {DECISION_V02}, got schema_version {version!r}")
    assert_no_runtime_directives(raw)
    return EnvironmentActivationDecisionV02.model_validate(raw)


def parse_interaction_observation_v02(raw: Mapping[str, Any]) -> InteractionObservationV02:
    version = _version(raw, "interaction observation")
    if version != OBSERVATION_V02:
        raise ValueError(f"expected {OBSERVATION_V02}, got schema_version {version!r}")
    assert_no_runtime_directives(raw)
    assert_no_effectiveness_verdict(raw)
    return InteractionObservationV02.model_validate(raw)


def parse_activation_decision(raw: Mapping[str, Any], *, require_binding: bool = False):
    """Dispatch on ``schema_version``. Unknown versions are rejected; with
    ``require_binding`` a v0.1 decision is rejected too."""

    from azazel_fabric.deception_contracts.models import EnvironmentActivationDecision

    version = _version(raw, "activation decision")
    if version == DECISION_V02:
        return parse_activation_decision_v02(raw)
    if version == DECISION_V01 and not require_binding:
        assert_no_runtime_directives(raw)
        return EnvironmentActivationDecision.model_validate(raw)
    raise ValueError(
        f"unsupported activation decision schema_version {version!r}"
        + (" (v0.2 binding required)" if require_binding else "")
    )


def parse_interaction_observation(raw: Mapping[str, Any], *, require_binding: bool = False):
    from azazel_fabric.deception_contracts.observation import InteractionObservation

    version = _version(raw, "interaction observation")
    if version == OBSERVATION_V02:
        return parse_interaction_observation_v02(raw)
    if version == OBSERVATION_V01 and not require_binding:
        assert_no_runtime_directives(raw)
        assert_no_effectiveness_verdict(raw)
        return InteractionObservation.model_validate(raw)
    raise ValueError(
        f"unsupported interaction observation schema_version {version!r}"
        + (" (v0.2 binding required)" if require_binding else "")
    )
