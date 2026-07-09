"""Operating-mode state (`ModeState`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Known mode names across the series. This is an *open* enum: products may
# use additional values (registered via a documented extension list), so the
# field type stays `str` rather than a strict Literal that would reject a
# sibling product's mode. See design-principles.md §4.4.
KNOWN_MODE_NAMES = (
    "portal",
    "shield",
    "scapegoat",
    "observe",
    "lockdown",
)


class ModeState(BaseModel):
    """Current operating mode of an Azazel product."""

    name: str = Field(
        ...,
        description="Mode name; open enum, see KNOWN_MODE_NAMES for base values.",
    )
    since: str = Field(..., description="ISO 8601 timestamp the mode was entered.")
    reason: str | None = Field(
        default=None, description="Optional human-readable reason for the mode."
    )
