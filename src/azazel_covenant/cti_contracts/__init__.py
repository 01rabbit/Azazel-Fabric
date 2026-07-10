"""CTI advisory contract: Edge/Gadget <-> CTI wire format.

The highest-priority contract in v0.1.0: the only place two different
repositories (Edge/Gadget and CTI) must agree on wire format across a network
boundary. Fixing the *shape* of advice does not grant CTI authority over
Edge/Gadget — the response is advisory only. See design-principles.md §4.2.
"""

from azazel_covenant.cti_contracts.advisory import (
    BANNED_DIRECTIVE_FIELDS,
    BehavioralCtiBlock,
    assert_advisory_only,
    is_advisory_only,
)
from azazel_covenant.cti_contracts.context import (
    CtiContextRequest,
    CtiContextResponse,
    IocMatch,
)
from azazel_covenant.cti_contracts.ingest import (
    CtiEventBatch,
    CtiFlowBatch,
    CtiReactionBatch,
    SourceProduct,
)

__all__ = [
    "CtiEventBatch",
    "CtiFlowBatch",
    "CtiReactionBatch",
    "SourceProduct",
    "CtiContextRequest",
    "CtiContextResponse",
    "IocMatch",
    "BehavioralCtiBlock",
    "BANNED_DIRECTIVE_FIELDS",
    "is_advisory_only",
    "assert_advisory_only",
]
