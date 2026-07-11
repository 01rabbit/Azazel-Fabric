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
``azazel-fabric``/``azazel_fabric`` (breaking; see ``CHANGELOG.md``). ``v0.4.0``
adds the Phase-5 helper modules — :mod:`azazel_fabric.paths` (candidate-path
hints), :mod:`azazel_fabric.audit` (AuditEvent projection + JSONL formatters;
**no hash chain — chains stay product-local**), :mod:`azazel_fabric.api`
(framework-neutral error/role/token helpers), :mod:`azazel_fabric.notify`
(notification payload model + transport mappers) — plus the Phase-6
:mod:`azazel_fabric.testing` factories and invariant assertions. Every helper
is import-light (no heavy imports at module scope) to stay Pi-friendly, and no
web framework is imported in any core module.

Submodules are imported on demand (``import azazel_fabric.api``), not eagerly
from this package root, so a consumer only pays for what it uses.
"""

from azazel_fabric.version import __version__

__all__ = ["__version__"]
