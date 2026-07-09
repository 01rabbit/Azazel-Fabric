"""Evidence reference (`EvidenceRef`)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    """A pointer to a piece of evidence, not the evidence content itself."""

    evidence_id: str = Field(..., description="Opaque evidence identifier.")
    source: str = Field(
        ...,
        description='Producer, e.g. "noc_evaluator", "soc_evaluator", "cti_advisory".',
    )
    trace_id: str = Field(..., description="Correlates with AuditEvent/TrustCapsule.")
    observed_at: str = Field(..., description="ISO 8601 observation timestamp.")
