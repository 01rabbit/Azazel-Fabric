"""Edge/Gadget -> CTI ingest batch envelopes.

`CtiEventBatch`, `CtiFlowBatch`, and `CtiReactionBatch` share one envelope
shape. The per-item field lists are intentionally left as `list[dict]` in
v0.1.0: the product-typed sub-schema is layered on during Issue 3 against the
real Azazel-Knowledge API, without breaking its existing consumers (see
contracts.md §2).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SourceProduct = Literal["edge", "gadget"]


class _CtiBatch(BaseModel):
    """Common ingest envelope shared by the three batch kinds."""

    batch_id: str = Field(..., description="Opaque batch identifier.")
    source_product: SourceProduct = Field(..., description="Emitting product.")
    source_device_id: str = Field(..., description="Emitting device identifier.")
    generated_at: str = Field(..., description="ISO 8601 batch timestamp.")
    items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Batch items; product-typed sub-schema layered on later.",
    )


class CtiEventBatch(_CtiBatch):
    """A batch of events sent to CTI (`POST /v1/events`)."""


class CtiFlowBatch(_CtiBatch):
    """A batch of flows sent to CTI (`POST /v1/flows`)."""


class CtiReactionBatch(_CtiBatch):
    """A batch of reactions sent to CTI (`POST /v1/reactions`)."""
