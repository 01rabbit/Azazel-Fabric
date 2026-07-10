"""CTI context request/response (`/v1/context`).

`CtiContextResponse` is the concrete encoding of the advisory-only boundary.
Two invariants are enforced here, not just documented:

1. **Advisory only.** Directive-shaped fields are rejected (extra fields are
   forbidden, and the banned names raise a clear error).
2. **`behavioral_cti` is absent, never null, when there is nothing to
   report.** An empty block is normalized to absent, and serialization omits
   `None` fields, so "no behavioral signal" is always encoded as a missing
   key — never `null` and never an empty object on the wire.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from azazel_fabric.cti_contracts.advisory import (
    BehavioralCtiBlock,
    assert_advisory_only,
)
from azazel_fabric.cti_contracts.ingest import SourceProduct


class CtiContextRequest(BaseModel):
    """Edge/Gadget -> CTI request for advisory context on indicators."""

    request_id: str = Field(..., description="Opaque request identifier.")
    source_product: SourceProduct = Field(..., description="Requesting product.")
    indicators: list[str] = Field(
        default_factory=list, description="IPs, hashes, domains, etc. being queried."
    )
    trace_id: str = Field(..., description="Correlates with audit/state records.")


class IocMatch(BaseModel):
    """A single indicator match within a context response."""

    model_config = ConfigDict(extra="forbid")

    indicator: str = Field(..., description="The matched indicator.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence, 0.0-1.0.")
    reason: list[str] = Field(
        default_factory=list, description="Why the indicator matched."
    )
    source_freshness: str | None = Field(
        default=None, description="ISO 8601 freshness of the matching source."
    )


class CtiContextResponse(BaseModel):
    """CTI -> Edge/Gadget advisory response. Advisory only; never directive.

    A response that fails validation, times out, or is unreachable must be
    treated by the caller as "no advisory context available" and must never
    halt the caller's own decision path (see contracts.md §2 failure-mode
    contract). This schema only fixes the shape; the fail-closed handling is
    the caller's responsibility.
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., description="Echoes the request.")
    matches: list[IocMatch] = Field(
        default_factory=list, description="Indicator matches; may be empty."
    )
    behavioral_cti: BehavioralCtiBlock | None = Field(
        default=None,
        description=(
            "Behavioral signal. Absent (never null, never empty object) when "
            "there is nothing to report."
        ),
    )
    advisory_notice: str | None = Field(
        default=None, description="Free-text advisory framing; explicitly non-directive."
    )
    limitations: list[str] = Field(
        default_factory=list,
        description='e.g. "feed stale > 24h", "partial coverage".',
    )
    source_freshness: str | None = Field(
        default=None, description="ISO 8601 freshness of the response as a whole."
    )
    generated_at: str = Field(..., description="ISO 8601 response timestamp.")

    @model_validator(mode="before")
    @classmethod
    def _reject_directive_fields(cls, data: Any) -> Any:
        """Enforce the advisory-only invariant with a clear error message.

        `extra="forbid"` already rejects unknown fields, but this runs first
        to give a precise, invariant-named error for directive-shaped fields.
        """
        if isinstance(data, dict):
            assert_advisory_only(data)
        return data

    @model_validator(mode="after")
    def _normalize_empty_behavioral(self) -> "CtiContextResponse":
        """Collapse an empty behavioral block to absent.

        Guarantees "missing key" and "empty object" are indistinguishable
        downstream: both become `None`, and `None` is omitted on serialization.
        """
        if self.behavioral_cti is not None and self.behavioral_cti.is_empty():
            self.behavioral_cti = None
        return self

    @property
    def has_behavioral_cti(self) -> bool:
        """True only when a non-empty behavioral signal is present."""
        return self.behavioral_cti is not None

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Dump with `exclude_none=True` by default so absent fields are omitted."""
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        """Dump JSON with `exclude_none=True` by default so no field is `null`."""
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(**kwargs)
