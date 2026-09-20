"""Cross-series effect / outcome / presented-terrain contracts (Fabric#15).

    **Fabric describes; products decide.**

Nothing here becomes an execution token by carrying an effect name. Every
model is frozen, forbids unknown fields, and is walked for directive and
product-owned-authority keys on construction.

Three vocabularies stay distinct, and the tests pin that they do:

``DefensiveState`` (Fabric#14)
    What posture a product is in. A *state*.
``EffectClass`` (here)
    What kind of bounded effect was constructed or observed. An *effect*.
AZ-06 environment lifecycle (``deception_contracts``)
    Where a materialized environment is in its own life. A *lifecycle*.

Collapsing any two of them would let a value from one be read as authority in
another, which is the confusion this family exists to prevent.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from azazel_fabric.schema.defensive_state import DefensiveState

from .authority import AuthorityClass
from .refs import RefKind, reject_ref_kinds, require_ref_kind
from .validation import (
    assert_bounded_fact_payload,
    assert_no_effect_authority_fields,
    assert_no_runtime_directives,
    assert_no_secret_material,
)

__all__ = [
    "UNKNOWN_EFFECT_CLASS_FALLBACK",
    "DefensiveEffectRef",
    "EffectClass",
    "EffectObservation",
    "EffectStatus",
    "OBSERVABLE_AUTHORITY_CLASSES",
    "OutcomeObservationEnvelope",
    "PresentedTerrainRef",
    "ReplayProvenance",
    "coerce_effect_class",
    "parse_timestamp",
]


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def parse_timestamp(raw: str, *, field: str) -> datetime:
    """Parse an ISO-8601 instant, requiring an explicit offset.

    A naive timestamp is rejected rather than assumed UTC: two products in
    different zones writing naive instants into the same chain would produce
    an ordering that looks valid and is wrong.
    """

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field} is not an ISO-8601 timestamp: {raw!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must carry an explicit UTC offset: {raw!r}")
    return parsed


class EffectClass(str, Enum):
    """Bounded kinds of defensive effect that several products must name alike.

    Deliberately small. Fabric names an effect so two products can talk about
    the same one; it does not enumerate every effect a product can build, and
    it never says which is better.
    """

    OBSERVE_ONLY = "observe_only"
    NOTIFY_ONLY = "notify_only"
    RATE_LIMIT = "rate_limit"
    REDIRECT_TO_PRESENTED_TERRAIN = "redirect_to_presented_terrain"
    NETWORK_ISOLATION = "network_isolation"
    SESSION_TERMINATION = "session_termination"


#: Where an unrecognized effect class lands.
#:
#: ``OBSERVE_ONLY`` is the effect that does least. An unknown value that landed
#: on ``NETWORK_ISOLATION`` or ``REDIRECT_TO_PRESENTED_TERRAIN`` would mean an
#: unparseable record could describe a stronger effect than any product chose
#: -- issue #15 lists exactly that as an adversarial case.
UNKNOWN_EFFECT_CLASS_FALLBACK = EffectClass.OBSERVE_ONLY

#: Effect class names that must never be confusable with a ``DefensiveState``.
#:
#: Fabric provides **no** function from one to the other. They answer different
#: questions, and a mapping would let an effect value be read as a posture (or
#: the reverse) by anything that followed the mapping instead of the field.
_DEFENSIVE_STATE_NAMES = frozenset(member.value for member in DefensiveState)


def coerce_effect_class(raw: object) -> tuple[EffectClass, bool]:
    """Return ``(effect_class, recognized)``. Unknown input never escalates."""

    if isinstance(raw, EffectClass):
        return raw, True
    if isinstance(raw, str):
        try:
            return EffectClass(raw), True
        except ValueError:
            return UNKNOWN_EFFECT_CLASS_FALLBACK, False
    return UNKNOWN_EFFECT_CLASS_FALLBACK, False


EffectStatus = Literal[
    "eligible",
    "selected",
    "rejected",
    "started",
    "active",
    "completed",
    "terminated",
    "failed",
]

#: The only two claims an observation is allowed to make (Fabric#52).
#:
#: ``DefensiveEffectRef`` already refuses exactly these two, on the grounds
#: that they are "an observation's to make". The converse was written down and
#: never enforced, so an ``EffectObservation`` could arrive claiming
#: ``producer_decision_ref`` -- a report of an effect asserting authority over
#: it -- or ``advisory_inference`` or ``planned_shadow``, which describe
#: records where nothing was materialized and therefore nothing was observed.
#: ``stale_or_unknown`` claims nothing at all, and an observation that claims
#: nothing is not an observation; it is a gap, and a consumer must see it as
#: one rather than as a fact with a weak label.
#:
#: The two sets partition ``AuthorityClass`` exactly, which is what
#: ``test_every_authority_class_belongs_to_exactly_one_record`` pins. A member
#: added later belongs to one side or the other, and that test refuses to let
#: the choice be made by omission.
OBSERVABLE_AUTHORITY_CLASSES = frozenset(
    {
        AuthorityClass.OBSERVED_FACT,
        AuthorityClass.ACTIVE_MATERIALIZED,
    }
)

#: Kinds that must never stand in for an inherited decision/trace/execution id.
_NOT_A_DECISION = frozenset(
    {
        RefKind.LIFECYCLE,
        RefKind.PRESENTATION,
        RefKind.ADVISORY,
        RefKind.EFFECT,
        RefKind.EFFECT_OBSERVATION,
        RefKind.ENVIRONMENT,
        RefKind.SURFACE,
        RefKind.ARTIFACT,
    }
)


class DefensiveEffectRef(_StrictFrozenModel):
    """A constructed or selected effect context. Not a plan, not a command.

    What this is *not*: a cross-product planner. Fabric does not say how an
    effect becomes eligible, and it does not rank effects. This record says
    only "an effect of this class exists, in this scope, under this authority,
    until this instant".
    """

    schema_version: Literal["defensive-effect-ref/v0.1"] = "defensive-effect-ref/v0.1"
    effect_id: str = Field(min_length=1, max_length=256)
    effect_class: EffectClass
    producer_product: str = Field(min_length=1, max_length=64)
    producer_node: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    #: Present only when ``authority_class`` is ``producer_decision_ref``.
    decision_ref: str | None = Field(default=None, min_length=1, max_length=256)
    #: Present only when ``authority_class`` is ``advisory_inference``.
    advisory_ref: str | None = Field(default=None, min_length=1, max_length=256)
    #: An opaque, typed handle on what the effect applies to -- never a
    #: provider command and never an address the receiver is expected to act on.
    target_scope_ref: str = Field(min_length=1, max_length=256)
    policy_ref: str = Field(min_length=1, max_length=256)
    profile_ref: str | None = Field(default=None, max_length=256)
    config_digest: str | None = Field(default=None, max_length=128)
    created_at: str = Field(min_length=1, max_length=64)
    expires_at: str = Field(min_length=1, max_length=64)
    authority_class: AuthorityClass
    #: Pinned. A reference describes; it never instructs.
    directive: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "DefensiveEffectRef":
        payload = self.model_dump(mode="python")
        assert_no_runtime_directives(payload)
        assert_no_effect_authority_fields(payload)

        require_ref_kind(self.effect_id, RefKind.EFFECT, field="effect_id")
        require_ref_kind(self.target_scope_ref, RefKind.SCOPE, field="target_scope_ref")
        reject_ref_kinds(self.trace_id, _NOT_A_DECISION, field="trace_id")
        reject_ref_kinds(self.decision_ref, _NOT_A_DECISION, field="decision_ref")

        if self.effect_class.value in _DEFENSIVE_STATE_NAMES:
            raise ValueError("effect_class must not reuse a DefensiveState name")

        created = parse_timestamp(self.created_at, field="created_at")
        expires = parse_timestamp(self.expires_at, field="expires_at")
        if expires <= created:
            raise ValueError("expires_at must be after created_at; an effect is bounded")

        # An effect reference may claim a decision, advice, a shadow run, or
        # nothing. It may never claim to be an observed fact or a live
        # materialization -- those are an EffectObservation's to make.
        if self.authority_class in (
            AuthorityClass.OBSERVED_FACT,
            AuthorityClass.ACTIVE_MATERIALIZED,
        ):
            raise ValueError(
                f"{self.authority_class.value!r} is an observation's claim to make, "
                "not an effect reference's"
            )
        if self.authority_class is AuthorityClass.PRODUCER_DECISION_REF:
            if self.decision_ref is None:
                raise ValueError(
                    "a producer_decision_ref must name the decision it refers to"
                )
            if self.advisory_ref is not None:
                raise ValueError(
                    "a producer_decision_ref must not also carry an advisory reference; "
                    "a decision and an inference are different claims"
                )
        if self.authority_class is AuthorityClass.ADVISORY_INFERENCE:
            if self.advisory_ref is None:
                raise ValueError("an advisory_inference must name its advisory")
            if self.decision_ref is not None:
                raise ValueError(
                    "an advisory_inference must not carry a decision reference; "
                    "advice that names a decision is how advice is mistaken for one"
                )
            require_ref_kind(self.advisory_ref, RefKind.ADVISORY, field="advisory_ref")
        return self


class EffectObservation(_StrictFrozenModel):
    """What a materializer observed about an effect. A fact, not a request."""

    schema_version: Literal["effect-observation/v0.1"] = "effect-observation/v0.1"
    observation_id: str = Field(min_length=1, max_length=256)
    effect_ref: str = Field(min_length=1, max_length=256)
    trace_id: str = Field(min_length=1, max_length=256)
    status: EffectStatus
    observed_at: str = Field(min_length=1, max_length=64)
    materialization_producer: str = Field(min_length=1, max_length=64)
    execution_ref: str | None = Field(default=None, max_length=256)
    termination_reason: str | None = Field(default=None, max_length=256)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    authority_class: AuthorityClass
    directive: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "EffectObservation":
        payload = self.model_dump(mode="python")
        assert_no_runtime_directives(payload)
        assert_no_effect_authority_fields(payload)

        require_ref_kind(
            self.observation_id, RefKind.EFFECT_OBSERVATION, field="observation_id"
        )
        require_ref_kind(self.effect_ref, RefKind.EFFECT, field="effect_ref")
        reject_ref_kinds(self.execution_ref, _NOT_A_DECISION, field="execution_ref")
        parse_timestamp(self.observed_at, field="observed_at")

        if self.authority_class not in OBSERVABLE_AUTHORITY_CLASSES:
            raise ValueError(
                f"{self.authority_class.value!r} is not something an observation "
                "can have observed; an EffectObservation may claim only "
                "observed_fact or active_materialized"
            )

        if self.status in ("terminated", "failed") and self.termination_reason is None:
            raise ValueError(
                f"status {self.status!r} must name why it ended; an unexplained "
                "termination is indistinguishable from a lost observation"
            )
        if self.status in ("started", "active"):
            if self.authority_class is not AuthorityClass.ACTIVE_MATERIALIZED:
                raise ValueError(
                    "an observation reporting a live effect must claim "
                    "active_materialized, so that a consumer can see who is asserting it"
                )
        elif self.authority_class is AuthorityClass.ACTIVE_MATERIALIZED:
            raise ValueError(
                f"status {self.status!r} is not a live effect and must not claim "
                "active_materialized"
            )
        return self


class PresentedTerrainRef(_StrictFrozenModel):
    """What the defender presented. Never what the adversary perceived.

    Adversary belief is a product-owned research concept and has no shared
    authoritative contract (issue #15, "What MUST NOT go into Fabric"). The
    ``describes`` literal is pinned so that this record cannot be re-read as a
    belief record by a later, well-meaning additive change.
    """

    schema_version: Literal["presented-terrain-ref/v0.1"] = "presented-terrain-ref/v0.1"
    presentation_id: str = Field(min_length=1, max_length=256)
    presentation_version: int = Field(ge=0)
    producer_product: str = Field(min_length=1, max_length=64)
    #: Optional since `v0.9.0rc5` (Fabric#51). A terrain activated by a
    #: producer decision names it here. One that was not -- a shadow run, an
    #: observation, a stale record -- has no decision to name, and filling
    #: this with something that is not one is the failure the change exists to
    #: stop. Such a terrain binds through `source_effect_ref` + `trace_id`
    #: instead, and a terrain carrying *neither* binding is refused.
    activation_decision_ref: str | None = Field(default=None, min_length=1, max_length=256)
    #: The effect this terrain was presented for. Typed `effect:`.
    #:
    #: This is the binding a decision-less effect has, and it is a reference
    #: to the effect itself rather than to a decision that does not exist.
    source_effect_ref: str | None = Field(default=None, min_length=1, max_length=256)
    #: The incident this terrain belongs to. Additive and optional, so that a
    #: producer pinned to `v0.9.0rc4` keeps working; required alongside
    #: `source_effect_ref` when that is the binding in use, because an effect
    #: reference on its own can still be a cross-trace collision.
    trace_id: str | None = Field(default=None, min_length=1, max_length=256)
    lifecycle_state_ref: str = Field(min_length=1, max_length=256)
    active_surface_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    synthetic_artifact_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    #: Synthetic identities and credentials the terrain exposes, as typed
    #: references. The same rules as artifacts: opaque, no secret material,
    #: and never the thing itself. A credential that travelled in a contract
    #: would be a real credential wherever the contract went.
    synthetic_identity_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    synthetic_credential_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    isolation_assertion_ref: str = Field(min_length=1, max_length=256)
    isolation_result_ref: str | None = Field(default=None, max_length=256)
    created_at: str = Field(min_length=1, max_length=64)
    expires_at: str = Field(min_length=1, max_length=64)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    authority_class: AuthorityClass
    #: Pinned. This record is about the defender's side of the surface.
    describes: Literal["defender_presented_surface"] = "defender_presented_surface"
    directive: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "PresentedTerrainRef":
        payload = self.model_dump(mode="python")
        assert_no_runtime_directives(payload)
        assert_no_effect_authority_fields(payload)

        require_ref_kind(
            self.presentation_id, RefKind.PRESENTATION, field="presentation_id"
        )
        require_ref_kind(
            self.lifecycle_state_ref, RefKind.LIFECYCLE, field="lifecycle_state_ref"
        )
        reject_ref_kinds(
            self.activation_decision_ref,
            _NOT_A_DECISION,
            field="activation_decision_ref",
        )
        reject_ref_kinds(self.trace_id, _NOT_A_DECISION, field="trace_id")
        if self.source_effect_ref is not None:
            require_ref_kind(
                self.source_effect_ref, RefKind.EFFECT, field="source_effect_ref"
            )

        # A terrain names what put it there, one way or the other. Neither is
        # not a weaker record; it is an unattributable one, and Fabric#51's
        # non-goal is exactly "treat a missing reference as a valid chain".
        if self.activation_decision_ref is None and self.source_effect_ref is None:
            raise ValueError(
                "a presented terrain must name either the decision that "
                "activated it or the effect it was presented for; a terrain "
                "that names neither cannot be attributed to anything"
            )
        if self.source_effect_ref is not None and self.trace_id is None:
            raise ValueError(
                "source_effect_ref requires trace_id; an effect reference on "
                "its own is still satisfied by a cross-trace collision, which "
                "is the failure typed references exist to prevent"
            )

        for field_name, values, expected in (
            ("active_surface_refs", self.active_surface_refs, RefKind.SURFACE),
            ("synthetic_artifact_refs", self.synthetic_artifact_refs, RefKind.ARTIFACT),
            ("synthetic_identity_refs", self.synthetic_identity_refs, RefKind.IDENTITY),
            (
                "synthetic_credential_refs",
                self.synthetic_credential_refs,
                RefKind.CREDENTIAL,
            ),
        ):
            for value in values:
                require_ref_kind(value, expected, field=field_name)
            assert_no_secret_material(values, field=field_name)

        created = parse_timestamp(self.created_at, field="created_at")
        expires = parse_timestamp(self.expires_at, field="expires_at")
        if expires <= created:
            raise ValueError("expires_at must be after created_at; a presentation is bounded")

        if self.authority_class is AuthorityClass.ADVISORY_INFERENCE:
            raise ValueError(
                "a presented terrain is materialized or planned, never inferred"
            )
        return self


class ReplayProvenance(_StrictFrozenModel):
    """What it takes to reproduce a record. Never what authorizes one.

    ``confers_authority`` is pinned to ``False`` because issue #15 names
    "signature/provenance presence is mistaken for authorization" as an
    adversarial case. A field that is structurally incapable of being ``True``
    is a stronger answer than a convention that it should not be read that way.
    """

    schema_version: Literal["replay-provenance/v0.1"] = "replay-provenance/v0.1"
    software_revision: str = Field(min_length=1, max_length=128)
    runtime_profile: str = Field(min_length=1, max_length=128)
    policy_config_digest: str = Field(min_length=1, max_length=128)
    #: A locator for the model that produced advice, if any. Carrying it does
    #: not give the model's output authority -- it makes the run reproducible.
    model_ref: str | None = Field(default=None, max_length=256)
    playbook_ref: str | None = Field(default=None, max_length=256)
    fixture_scenario_id: str | None = Field(default=None, max_length=256)
    capture_generation: int = Field(ge=0)
    as_of: str = Field(min_length=1, max_length=64)
    confers_authority: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "ReplayProvenance":
        payload = self.model_dump(mode="python")
        assert_no_runtime_directives(payload)
        assert_no_effect_authority_fields(payload)
        parse_timestamp(self.as_of, field="as_of")
        if not self.policy_config_digest.startswith("sha256:"):
            raise ValueError("policy_config_digest must be a sha256: digest")
        return self


class OutcomeObservationEnvelope(_StrictFrozenModel):
    """Correlates already-produced outcome facts. It adds no verdict.

    It deliberately has **no** ``success`` field -- the walk rejects one, and
    the shipped ``outcome_contracts`` family made the same choice. What
    replaces it is coverage: an envelope must say how much of the world it
    could see, and an envelope that admits partial coverage must name the gaps.
    """

    schema_version: Literal["outcome-observation-envelope/v0.1"] = (
        "outcome-observation-envelope/v0.1"
    )
    envelope_id: str = Field(min_length=1, max_length=256)
    producer_product: str = Field(min_length=1, max_length=64)
    producer_node: str = Field(min_length=1, max_length=128)
    producer_version: str = Field(min_length=1, max_length=64)
    trace_id: str = Field(min_length=1, max_length=256)
    decision_ref: str | None = Field(default=None, max_length=256)
    effect_ref: str | None = Field(default=None, max_length=256)
    environment_ref: str | None = Field(default=None, max_length=256)
    presentation_ref: str | None = Field(default=None, max_length=256)
    actor_session_ref: str | None = Field(default=None, max_length=256)
    #: Ids of ``outcome_contracts.OutcomeObservationV0`` records. The envelope
    #: correlates them; it does not restate or re-interpret them.
    outcome_observation_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    window_start: str = Field(min_length=1, max_length=64)
    window_end: str = Field(min_length=1, max_length=64)
    observation_class: str = Field(min_length=1, max_length=64)
    telemetry_coverage: dict[str, Any] = Field(default_factory=dict)
    #: Explicit, never inferred from an empty gap list.
    coverage_complete: bool
    telemetry_gaps: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    confounders: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    impact_observations: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    provenance: ReplayProvenance | None = None
    observed_at: str = Field(min_length=1, max_length=64)
    authority_class: AuthorityClass
    directive: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "OutcomeObservationEnvelope":
        payload = self.model_dump(mode="python")
        assert_no_runtime_directives(payload)
        assert_no_effect_authority_fields(payload)
        for fact_map in (self.telemetry_coverage, self.impact_observations):
            assert_bounded_fact_payload(fact_map)

        require_ref_kind(self.envelope_id, RefKind.ENVELOPE, field="envelope_id")
        reject_ref_kinds(self.decision_ref, _NOT_A_DECISION, field="decision_ref")
        if self.effect_ref is not None:
            require_ref_kind(self.effect_ref, RefKind.EFFECT, field="effect_ref")
        if self.presentation_ref is not None:
            require_ref_kind(
                self.presentation_ref, RefKind.PRESENTATION, field="presentation_ref"
            )

        start = parse_timestamp(self.window_start, field="window_start")
        end = parse_timestamp(self.window_end, field="window_end")
        if end < start:
            raise ValueError("window_end must not precede window_start")
        parse_timestamp(self.observed_at, field="observed_at")

        if not self.coverage_complete and not self.telemetry_gaps:
            raise ValueError(
                "an envelope that reports incomplete coverage must name the gaps; "
                "unnamed telemetry loss is how a partial observation reads as a whole one"
            )
        if self.coverage_complete and self.telemetry_gaps:
            raise ValueError(
                "an envelope cannot claim complete coverage and also name gaps"
            )

        if self.authority_class is AuthorityClass.PRODUCER_DECISION_REF:
            raise ValueError(
                "an outcome envelope observes; it never carries a decision's authority"
            )
        return self
