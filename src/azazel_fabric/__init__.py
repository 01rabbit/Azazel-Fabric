"""Azazel-Fabric (formerly Azazel-Common): shared contracts for the Azazel series.

This package holds representation, not behavior — Pydantic schemas and the
Edge/Gadget <-> CTI advisory contract. It contains no decision, execution,
or arbitration logic. See ``docs/`` for the design record.

``v0.1.0`` shipped schema-only: :mod:`azazel_fabric.schema` and
:mod:`azazel_fabric.cti_contracts`. ``v0.2.0`` adds :mod:`azazel_fabric.view`,
the shared status view-model (``StatusView`` + ``build_status_view``) that lets
Edge and Gadget present the same status the same way — Fabric owns the
view-model, each product keeps its own renderer. ``v0.3.0`` renames the
distribution and import namespace from ``azazel-common``/``azazel_common`` to
``azazel-fabric``/``azazel_fabric`` (breaking; see ``CHANGELOG.md``). The
``paths``/``audit``/``api``/``notify`` helpers are later phases and are
intentionally not present yet.
"""

from azazel_fabric.version import __version__

__all__ = ["__version__"]
