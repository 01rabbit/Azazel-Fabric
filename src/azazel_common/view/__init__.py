"""Shared status view-model for the Azazel series.

The normalized data an Azazel status surface reads (`StatusView`), plus the one
shared builder (`build_status_view`) that derives it — so Edge and Gadget
present the same status the same way. Common owns the view-model; each product
keeps its own renderer (see `docs/design-principles.md` §3.1).
"""

from azazel_common.view.build import (
    build_status_view,
    derive_headline,
    derive_posture,
    from_state_snapshot,
)
from azazel_common.view.status import (
    KNOWN_HEALTH_STATUSES,
    KNOWN_POSTURES,
    HealthDimension,
    StatusView,
)

__all__ = [
    "StatusView",
    "HealthDimension",
    "KNOWN_POSTURES",
    "KNOWN_HEALTH_STATUSES",
    "build_status_view",
    "from_state_snapshot",
    "derive_posture",
    "derive_headline",
]
