"""Canonical effectiveness-observation contracts for AZ-06.

These types carry the *facts* AZ-06 emits while an engagement is live so that
Azazel-Knowledge can analyze deception effectiveness. They encode the honesty
ladder in the wire shape:

    (1) interaction  — the attacker contacted the decoy
    (2) reaction     — behavior changed after contact
    (3) outcome      — measured quantities (dwell, attempts, resource spent)
    (4) inference    — belief/intent estimate  ← NOT here; Knowledge's output

Layers 1-3 are facts emitted by the Deception Host. Layer 4 is a probabilistic
judgement and is carried separately by :class:`EffectivenessAdvisory`, which is
Knowledge's advisory output. The split is deliberate: *interaction does not
prove attacker belief* (Azazel-Deception#6, Azazel-Knowledge#58), so the
observation shape is structurally incapable of asserting belief, deception
success, or an effectiveness verdict — those fields fail closed
(:func:`assert_no_effectiveness_verdict`).

Runtime context (tier, architecture, adapter, active/omitted components,
saturation, capability drift) travels with each observation so a consumer can
separate narrative effectiveness from host-capacity/runtime effects
(Azazel-Knowledge#58).

Authority rule, unchanged: observations are ``descriptive_only``; the advisory
is ``advisory_only`` and non-executable. Neither can select or authorize any
action.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Architecture = Literal["arm64", "amd64"]
RuntimeAdapter = Literal["docker_compose", "podman", "kvm_libvirt", "k3s"]

# The three fact layers AZ-06 may emit. "inference" is intentionally absent:
# it is Knowledge's advisory judgement, not an observed fact.
ObservationClass = Literal["interaction", "reaction", "outcome"]

# What the attacker touched. Deliberately closed and synthetic-oriented.
InteractionSurface = Literal[
    "service",
    "port",
    "file",
    "document",
    "credential_lure",
    "config_breadcrumb",
    "service_history",
    "persona_artifact",
    "unknown",
]

# How the attacker acted after contact. Only meaningful for reaction/outcome.
ReactionKind = Literal[
    "read",
    "enumerate",
    "authenticate",
    "lateral_move",
    "exfiltrate",
    "modify",
    "execute",
    "escalate",
    "unknown",
]

# Signals that must be subtracted before effectiveness is claimed.
ConfounderTag = Literal[
    "scanner_noise",
    "internal_health_check",
    "heartbeat_traffic",
    "host_capacity",
    "architecture_context",
    "replayed_traffic",
    "unknown",
]


class RuntimeContext(BaseModel):
    """Runtime conditions that let a consumer separate narrative effectiveness
    from host-capacity/runtime effects (Azazel-Knowledge#58). Descriptive."""

    model_config = ConfigDict(extra="forbid")

    selected_tier: str = Field(min_length=1)
    architecture: Architecture
    runtime_adapter: RuntimeAdapter
    active_components: list[str] = Field(default_factory=list)
    omitted_components: list[str] = Field(default_factory=list)
    # e.g. {"cpu": 0.62, "memory": 0.40}; a fraction in [0, 1] per resource.
    resource_saturation: dict[str, float] | None = None
    capability_drift: list[str] = Field(default_factory=list)


class InteractionObservation(BaseModel):
    """A single fact-only effectiveness observation (layer 1-3).

    It records that/what/how-much, never whether the attacker was deceived.
    ``extra="forbid"`` plus :func:`assert_no_effectiveness_verdict` keep belief
    and verdict fields structurally out of the wire shape.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["interaction-observation/v0.1"] = "interaction-observation/v0.1"
    observation_id: str = Field(min_length=1)
    environment_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    observed_at: datetime
    observation_class: ObservationClass
    surface: InteractionSurface
    # Only meaningful once the attacker reacts; must be absent for pure contact.
    reaction_kind: ReactionKind | None = None
    lure_id: str | None = None
    first_contact_latency_ms: int | None = Field(default=None, ge=0)
    dwell_ms: int | None = Field(default=None, ge=0)
    attempt_count: int | None = Field(default=None, ge=0)
    confounder_tags: list[ConfounderTag] = Field(default_factory=list)
    runtime_context: RuntimeContext | None = None
    authority: Literal["descriptive_only"] = "descriptive_only"
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _interaction_has_no_reaction(self) -> "InteractionObservation":
        # Pure interaction is contact only; asserting a reaction_kind on it
        # would smuggle a stronger claim into a weaker layer.
        if self.observation_class == "interaction" and self.reaction_kind is not None:
            raise ValueError(
                "observation_class 'interaction' cannot carry a reaction_kind; "
                "use 'reaction' or 'outcome' for post-contact behavior"
            )
        return self


class EffectivenessAdvisory(BaseModel):
    """Knowledge's layer-4 output: a probabilistic effectiveness judgement.

    Advisory-only and non-executable (Azazel-Knowledge#52): it carries an
    assessment with confidence and **counter-evidence**, references the
    observations it summarizes, and names remaining unknowns. It cannot select
    or authorize anything; ``executable`` is pinned False and fails closed.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["effectiveness-advisory/v0.1"] = "effectiveness-advisory/v0.1"
    advisory_id: str = Field(min_length=1)
    environment_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    produced_at: datetime
    advisor: Literal["azazel-knowledge"] = "azazel-knowledge"
    authority: Literal["advisory_only"] = "advisory_only"
    assessment: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    counter_evidence: list[str] = Field(default_factory=list)
    observation_refs: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    executable: Literal[False] = False
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
