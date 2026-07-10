"""Reaction-specific ingest shapes.

In v0.1.0 the reaction batch does not diverge from the common ingest
envelope, so `CtiReactionBatch` is defined in :mod:`ingest` and re-exported
here. This module is the stable import location for reaction sub-shapes: if
reactions grow fields that events/flows do not have (Issue 3), those
divergent shapes are added here without changing the import path consumers
already use.
"""

from __future__ import annotations

from azazel_fabric.cti_contracts.ingest import CtiReactionBatch

__all__ = ["CtiReactionBatch"]
