"""Advisory-only building blocks for the CTI context response.

This module encodes the advisory-only boundary from design-principles.md
§4.2-§4.3: CTI may hand Edge/Gadget *information* (including
`suggested_posture` / `recommended_action`-shaped hints), but never a field
that reads as a command. Any directive-shaped field is rejected.
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

# Fields that read as an instruction rather than information. These must never
# appear in a CTI response. Enforced by CtiContextResponse and available here
# for reuse by CTI's own validation and by contract tests.
BANNED_DIRECTIVE_FIELDS = (
    "directive",
    "must_execute",
    "override",
    "required_action",
)


class BehavioralCtiBlock(BaseModel):
    """Behavioral CTI signal. Advisory only.

    Every field is optional. An instance carrying no signal is equivalent to
    the block being absent entirely (see `is_empty`) — consumers must treat
    "missing block" and "empty block" identically.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str | None = Field(default=None, description="Free-text behavioral summary.")
    suggested_posture: str | None = Field(
        default=None, description="Advisory posture hint; never a command."
    )
    recommended_action: str | None = Field(
        default=None, description="Advisory action hint; never a command."
    )
    indicators: list[str] = Field(
        default_factory=list, description="Indicators the behavioral signal relates to."
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Optional confidence, 0.0-1.0."
    )
    notes: list[str] = Field(default_factory=list, description="Additional advisory notes.")

    def is_empty(self) -> bool:
        """True when the block carries no behavioral signal.

        A block that is present but empty means the same as no block at all:
        "no behavioral signal available."
        """
        return self == BehavioralCtiBlock()


def is_advisory_only(data: Mapping[str, Any]) -> bool:
    """Return False if a mapping contains any directive-shaped field."""
    return not any(field in data for field in BANNED_DIRECTIVE_FIELDS)


def assert_advisory_only(data: Mapping[str, Any]) -> None:
    """Raise ValueError if a mapping contains any directive-shaped field."""
    present = [field for field in BANNED_DIRECTIVE_FIELDS if field in data]
    if present:
        raise ValueError(
            "CTI advisory-only invariant violated: directive-shaped field(s) "
            f"{present} are not permitted in a CTI response."
        )
