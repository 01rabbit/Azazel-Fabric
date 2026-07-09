"""Azazel-Common: shared contracts for the Azazel series.

This package holds representation, not behavior — Pydantic schemas and the
Edge/Gadget <-> CTI advisory contract. It contains no decision, execution,
or arbitration logic. See ``docs/`` for the design record.

``v0.1.0`` ships schema-only: :mod:`azazel_common.schema` and
:mod:`azazel_common.cti_contracts`. The ``paths``/``audit``/``api``/
``notify`` helpers are later phases and are intentionally not present yet.
"""

from azazel_common.version import __version__

__all__ = ["__version__"]
