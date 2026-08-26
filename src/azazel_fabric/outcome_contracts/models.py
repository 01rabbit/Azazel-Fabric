"""Shared Outcome-as-Evidence contracts.

Fabric describes facts and assessments produced by product-local authorities.
It never authorizes, executes, or upgrades an action.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .validation import assert_bounded_fact_payload, assert_no_runtime_directives


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExecutionRefV0(_StrictFrozenModel):
    """Reference to an execution fact produced by a local product.

    This is not an executable request.  ``action`` is the action that the
    producer attempted/applied; provider commands and arguments are
    intentionally absent from the shared contract.
    """

    schema_version: Literal["outcome-execution/v0.1"] = "outcome-execution/v0.1"
    producer_product: str = Field(min_length=1, max_length=64)
    producer_node: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    decision_ref: str = Field(min_length=1, max_length=256)
    execution_ref: str = Field(min_length=1, max_length=256)
    action: str = Field(min_length=1, max_length=64)
    status: Literal[
        "applied",
        "partial",
        "failed",
        "rejected",
        "unverified",
        "released",
    ]
    observed_at: str = Field(min_length=1, max_length=64)
    release_ref: str | None = Field(default=None, max_length=256)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority_class: Literal["producer_execution_fact"] = "producer_execution_fact"

    @model_validator(mode="after")
    def _validate_fact(self) -> "ExecutionRefV0":
        assert_no_runtime_directives(self.model_dump(mode="python"))
        return self


class MechanismObservationV0(_StrictFrozenModel):
    """Observed implementation mechanism, deliberately below tactical effect."""

    schema_version: Literal["outcome-mechanism/v0.1"] = "outcome-mechanism/v0.1"
    observation_id: str = Field(min_length=1, max_length=256)
    producer_product: str = Field(min_length=1, max_length=64)
    producer_node: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    decision_ref: str = Field(min_length=1, max_length=256)
    execution_ref: str = Field(min_length=1, max_length=256)
    mechanism_kind: Literal[
        "traffic_shaping",
        "redirection",
        "isolation",
        "notification",
        "observation_only",
        "unknown",
    ]
    status: Literal[
        "observed",
        "not_observed",
        "unverified",
        "released",
        "stale",
        "disputed",
    ]
    observed_parameters: dict[str, Any] = Field(default_factory=dict)
    observed_at: str = Field(min_length=1, max_length=64)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority_class: Literal["producer_mechanism_fact"] = "producer_mechanism_fact"

    @model_validator(mode="after")
    def _validate_fact(self) -> "MechanismObservationV0":
        payload = self.model_dump(mode="python")
        assert_no_runtime_directives(payload)
        assert_bounded_fact_payload(self.observed_parameters)
        return self


class OutcomeObservationV0(_StrictFrozenModel):
    """A bounded observation window.  It contains no success/causality verdict."""

    schema_version: Literal["outcome-observation/v0.1"] = "outcome-observation/v0.1"
    observation_id: str = Field(min_length=1, max_length=256)
    producer_product: str = Field(min_length=1, max_length=64)
    producer_node: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    decision_ref: str = Field(min_length=1, max_length=256)
    execution_ref: str = Field(min_length=1, max_length=256)
    mechanism_observation_ref: str | None = Field(default=None, max_length=256)
    subject_ref: str | None = Field(default=None, max_length=256)
    window_start: str = Field(min_length=1, max_length=64)
    window_end: str = Field(min_length=1, max_length=64)
    phase: Literal["before", "during", "after"]
    observation_class: str = Field(min_length=1, max_length=64)
    observation_values: dict[str, Any] = Field(default_factory=dict)
    telemetry_coverage: dict[str, Any] = Field(default_factory=dict)
    confounders: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    resource_impact: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    observed_at: str = Field(min_length=1, max_length=64)
    authority_class: Literal["producer_outcome_fact"] = "producer_outcome_fact"

    @model_validator(mode="after")
    def _validate_fact(self) -> "OutcomeObservationV0":
        payload = self.model_dump(mode="python")
        assert_no_runtime_directives(payload)
        assert_bounded_fact_payload(self.observation_values)
        assert_bounded_fact_payload(self.telemetry_coverage)
        assert_bounded_fact_payload(self.resource_impact)
        return self


class TacticalEffectAssessmentRefV0(_StrictFrozenModel):
    """A non-executable assessment fact, separate from mechanism and outcome facts."""

    schema_version: Literal["tactical-effect-assessment/v0.1"] = (
        "tactical-effect-assessment/v0.1"
    )
    assessment_id: str = Field(min_length=1, max_length=256)
    producer_product: str = Field(min_length=1, max_length=64)
    producer_node: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    decision_ref: str = Field(min_length=1, max_length=256)
    execution_ref: str = Field(min_length=1, max_length=256)
    mechanism_observation_ref: str = Field(min_length=1, max_length=256)
    outcome_observation_refs: tuple[str, ...] = Field(min_length=1, max_length=128)
    tactical_effect: Literal[
        "delay",
        "divert",
        "containment",
        "isolation",
        "observe",
        "restore",
    ]
    assessment: Literal["supported", "unsupported", "inconclusive"]
    evaluator: str = Field(min_length=1, max_length=128)
    policy_ref: str = Field(min_length=1, max_length=256)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    observed_at: str = Field(min_length=1, max_length=64)
    executable: Literal[False] = False
    authority_class: Literal["producer_assessment_fact"] = "producer_assessment_fact"

    @model_validator(mode="after")
    def _validate_fact(self) -> "TacticalEffectAssessmentRefV0":
        assert_no_runtime_directives(self.model_dump(mode="python"))
        return self
