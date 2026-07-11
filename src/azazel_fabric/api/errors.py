"""Shared JSON error shape + fail-closed helpers (`contracts.md` §3).

The one error envelope every Azazel API returns::

    {"error": {"code": str, "message": str, "trace_id": str | None}}

Framework-neutral: this module models and builds the *payload* only. It imports
no web framework; a Flask/FastAPI adapter (optional extra) is responsible for
attaching an HTTP status code and returning it. The default posture is
fail-closed — a caller that cannot say what went wrong still has a well-formed
rejection to return, never a default-allow.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Conventional error codes for the fail-closed auth/authorization posture
# (contracts.md §3). Products may add their own codes; these are the shared,
# security-relevant ones so every product rejects the same way.
UNAUTHENTICATED = "unauthenticated"
FORBIDDEN = "forbidden"
INVALID_REQUEST = "invalid_request"
INTERNAL_ERROR = "internal_error"


class ErrorBody(BaseModel):
    """The inner error object: a code, a human message, and an optional trace."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Stable, machine-readable error code.")
    message: str = Field(..., description="Human-readable explanation.")
    trace_id: str | None = Field(
        default=None, description="Correlates with audit/state records, if known."
    )


class ErrorEnvelope(BaseModel):
    """The top-level error shape: ``{"error": {...}}`` and nothing else."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorBody = Field(..., description="The single error object.")


def error_payload(
    code: str, message: str, trace_id: str | None = None
) -> dict[str, Any]:
    """Build the shared error dict ``{"error": {code, message, trace_id}}``.

    ``trace_id`` is omitted from the inner object when ``None`` so the wire
    payload carries no ``null`` — matching the series' absent-not-null habit.
    Returns a plain ``dict`` so any framework can serialize it directly.
    """
    envelope = ErrorEnvelope(error=ErrorBody(code=code, message=message, trace_id=trace_id))
    return envelope.model_dump(exclude_none=True)


def fail_closed_error(
    trace_id: str | None = None,
    *,
    code: str = UNAUTHENTICATED,
    message: str = "missing or invalid credentials",
) -> dict[str, Any]:
    """The default rejection payload for a fail-closed default posture.

    Use this when a request cannot be authenticated/authorized and there is no
    more specific error — the series never default-allows, so the safe default
    response is a well-formed rejection (contracts.md §3).
    """
    return error_payload(code, message, trace_id)
