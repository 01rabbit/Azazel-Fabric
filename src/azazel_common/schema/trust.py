"""Trust capsule (`TrustCapsule`)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrustCapsule(BaseModel):
    """Tamper-evidence capsule binding a trace to a config hash and signature."""

    trace_id: str = Field(..., description="Correlates with audit/state records.")
    config_hash: str = Field(..., description="Hash of the active config.")
    hmac: str = Field(..., description="Tamper-evidence signature.")
    issued_at: str = Field(..., description="ISO 8601 issuance timestamp.")
