"""Canonical outward Defensive State, and the things it is deliberately not.

Azazel-Fabric#14. One shared word for the defensive posture an Azazel product
is *already in*, so Edge, Gadget and any sibling describe the same thing the
same way.

**Fabric describes; it never decides.** Holding or transmitting a
``DefensiveState`` grants no execution authority whatsoever. The value is a
representation of a state a product-local authority already selected;
Azazel-Edge's deterministic arbiter decides and enforces, and a record carrying
one of these words does not and cannot change that.

Two properties are load-bearing, and both are tested rather than asserted:

*An unknown value never escalates.* A newer product may emit a state this
version has never heard of. Interpreting it as something stronger than what is
understood would let an unrecognized word widen a response, so an unrecognized
value resolves to the weakest state and is flagged as unrecognized. Forward
compatibility that fails toward more action is not compatibility, it is a
vulnerability.

*Authority and provenance stay separate from the value.* ``defensive_state``
says what the posture is. ``state_source_ref`` and ``decision_ref`` say who
decided it and under what record. Merging them would make the word itself look
like a warrant.

### What this is not

- **Not the Deception lifecycle.** ``REDIRECT`` is an outward defensive state.
  An AZ-06 environment's lifecycle — proposed, activated, terminated, reset —
  is a different axis with a different owner, and a product in ``REDIRECT`` may
  have no engagement environment at all.
- **Not an AI runtime tier.** What cognition a node runs is independent of the
  posture it is in. A ``CORE`` node with no model can be in ``ISOLATE``.
- **Not a threat level, severity, risk score, or policy profile.** Those are
  inputs a product weighs; this is the outcome it is already in.
- **Not a generic ``mode``.** ``schema.mode.ModeState`` remains for the
  product-local operating modes that predate this vocabulary. Where one of the
  meanings above is intended, that meaning is named — a field called ``mode``
  that sometimes means posture and sometimes means something else is how the
  separations above get lost.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DefensiveState(str, Enum):
    """The canonical outward defensive posture. Five values, no more."""

    OBSERVE = "OBSERVE"
    NOTIFY = "NOTIFY"
    THROTTLE = "THROTTLE"
    REDIRECT = "REDIRECT"
    ISOLATE = "ISOLATE"


#: Ordered weakest to strongest, by how much the posture interferes. The order
#: exists for exactly one purpose — deciding what an *unrecognized* value may
#: resolve to — and is not an escalation policy. Which state a product should
#: be in is a product-local decision that Fabric does not participate in.
ESCALATION_ORDER: tuple[DefensiveState, ...] = (
    DefensiveState.OBSERVE,
    DefensiveState.NOTIFY,
    DefensiveState.THROTTLE,
    DefensiveState.REDIRECT,
    DefensiveState.ISOLATE,
)

#: What an unrecognized value becomes. The weakest state, always.
UNKNOWN_FALLBACK = DefensiveState.OBSERVE

#: Legacy product vocabularies that predate this one. Listed so a reader can
#: recognize them as legacy, **not** so they can be translated: Fabric does not
#: define what `portal` means as a defensive state, because inventing that
#: meaning here would make a product-local word canonical by the back door.
#: A product that needs a mapping owns it, states it, and carries the original
#: value in `legacy_mode` so nothing is lost.
KNOWN_LEGACY_MODE_NAMES: tuple[str, ...] = ("portal", "shield", "scapegoat")

#: Concepts that must not ride inside a defensive-state record. Each is a
#: separate axis with its own owner; a field for one of them appearing here
#: would merge two meanings into one record and lose the separation.
SEPARATE_CONCEPT_FIELDS: frozenset[str] = frozenset(
    {
        "threat_level",
        "severity",
        "risk",
        "risk_score",
        "policy_profile",
        "ai_runtime_tier",
        "runtime_tier",
        "engagement_state",
        "presentation_state",
        "capability",
        "capability_state",
        "mode",
    }
)

#: Field names that would turn a description into an instruction. Same rule the
#: other contract families apply, stated here so this record carries it too.
DIRECTIVE_FIELDS: frozenset[str] = frozenset(
    {
        "execute",
        "command",
        "commands",
        "apply",
        "must_apply",
        "approve",
        "approved",
        "override",
        "authorize",
        "authorized",
        "enforce",
        "action",
        "executor",
    }
)


def rank(state: DefensiveState) -> int:
    """Position in :data:`ESCALATION_ORDER`. Comparison only; not a policy."""

    return ESCALATION_ORDER.index(state)


def coerce_defensive_state(raw: Any) -> tuple[DefensiveState, bool]:
    """Resolve any input to a state, never to a stronger one than understood.

    Returns ``(state, recognized)``. An unrecognized value — a newer product's
    vocabulary, a typo, a hostile payload — resolves to
    :data:`UNKNOWN_FALLBACK` with ``recognized=False``, so a caller can both
    keep operating and tell that it did not understand.

    Matching is exact on the canonical spelling. A value differing only in case
    is *not* silently accepted: two spellings of one state in the wire format
    is how a vocabulary starts to drift.
    """

    if isinstance(raw, DefensiveState):
        return raw, True
    if isinstance(raw, str):
        try:
            return DefensiveState(raw), True
        except ValueError:
            return UNKNOWN_FALLBACK, False
    return UNKNOWN_FALLBACK, False


def defensive_state_of_action(action_kind: str) -> DefensiveState | None:
    """The outward state an action kind corresponds to, when there is one.

    ``schema.action.ActionKind`` carries seven values; five are also outward
    defensive states. ``decoy`` and ``release`` are **not**: a decoy belongs to
    the engagement axis this module explicitly separates, and a release is a
    lifecycle transition rather than a posture. Both return ``None`` — a caller
    that needs a state for them has to say what it means, and Fabric will not
    guess on its behalf.
    """

    try:
        return DefensiveState(action_kind.upper())
    except (ValueError, AttributeError):
        return None


class DefensiveStateProjection(BaseModel):
    """What one product reports its outward defensive state to be.

    A projection of a state a product-local authority already selected. It
    authorizes nothing, requests nothing, and instructs nothing.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["defensive-state/v0.1"] = "defensive-state/v0.1"
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    defensive_state: DefensiveState
    #: False when the producer reported something this version does not know and
    #: the value was resolved down to the fallback. Carried so a consumer can
    #: see that a translation happened rather than inferring agreement.
    state_recognized: bool = True
    #: Who decided, kept separate from what was decided.
    state_source_ref: str = Field(min_length=1, max_length=256)
    #: The product-local decision record this state came from, when there is one.
    decision_ref: str | None = Field(default=None, max_length=256)
    observed_at: str = Field(min_length=1, max_length=64)
    #: The product's own vocabulary for the same situation, if it has one.
    #: Explicitly legacy context, never canonical, never authority.
    legacy_mode: str | None = Field(default=None, max_length=64)
    #: Product-specific descriptive context. Bounded, and held to the same two
    #: rules as the record itself.
    product_view: dict[str, Any] = Field(default_factory=dict)
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _stays_descriptive_and_separate(self) -> "DefensiveStateProjection":
        keys = {str(key).lower() for key in self.product_view}

        directives = sorted(keys & DIRECTIVE_FIELDS)
        if directives:
            raise ValueError(
                f"product_view carries directive-shaped fields {directives}; a "
                "defensive-state projection describes a posture and instructs "
                "nothing"
            )

        merged = sorted(keys & SEPARATE_CONCEPT_FIELDS)
        if merged:
            raise ValueError(
                f"product_view carries {merged}, which name separate concepts "
                "with their own owners; merging them into this record loses the "
                "separation it exists to keep"
            )

        if self.legacy_mode is not None and not self.legacy_mode.strip():
            raise ValueError("legacy_mode must be absent or a non-empty value")

        return self


__all__ = [
    "DIRECTIVE_FIELDS",
    "ESCALATION_ORDER",
    "KNOWN_LEGACY_MODE_NAMES",
    "SEPARATE_CONCEPT_FIELDS",
    "UNKNOWN_FALLBACK",
    "DefensiveState",
    "DefensiveStateProjection",
    "coerce_defensive_state",
    "defensive_state_of_action",
    "rank",
]
