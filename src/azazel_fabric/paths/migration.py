"""Dry-run-first legacy-path migration *planning* (`contracts.md` §5).

This helper only *describes* a migration from a legacy directory layout to the
canonical one — it never moves, copies, or deletes a file. It returns a plan;
executing the plan is the product's responsibility, and the product is free to
reject it. Per contracts.md §5: "dry-run-first helper; never silently
moves/deletes files." There is deliberately no ``execute`` function here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from azazel_fabric.paths.schema import (
    PathKind,
    _BASE_BY_KIND,
    _LEGACY_SEGMENTS,
    _segment,
    normalize_product,
)


class MigrationStep(BaseModel):
    """One proposed directory move, from a legacy path to the canonical path.

    Data only. Producing this object performs no filesystem action.
    """

    kind: str = Field(..., description='Path kind: "runtime" | "config" | "log".')
    source: str = Field(..., description="Legacy directory that may hold files today.")
    destination: str = Field(..., description="Canonical directory it maps to.")
    reason: str = Field(..., description="Why this move is proposed (legacy alias).")


class MigrationPlan(BaseModel):
    """A described, unexecuted migration for one product.

    ``dry_run`` is always ``True``: this package plans, it never performs. A
    plan with no ``steps`` means the product already uses the canonical layout
    (or has no known legacy alias) — a normal, expected outcome, not an error.
    """

    product: str = Field(..., description="Canonical product the plan targets.")
    dry_run: bool = Field(
        default=True,
        description="Always true — Fabric describes the migration, never runs it.",
    )
    steps: list[MigrationStep] = Field(
        default_factory=list, description="Proposed legacy->canonical moves."
    )

    @property
    def is_noop(self) -> bool:
        """True when there is nothing to migrate."""
        return not self.steps


def plan_migration(
    product: str,
    *,
    kinds: tuple[PathKind, ...] = ("runtime", "config", "log"),
) -> MigrationPlan:
    """Describe (do not perform) the legacy->canonical directory migration.

    For each requested ``kind`` and each legacy alias segment known for the
    product, emit a :class:`MigrationStep` from the legacy directory to the
    canonical one. Pure and deterministic: no filesystem access, no clock, no
    environment. The caller decides whether to act on the returned plan.
    """
    canonical = normalize_product(product)
    steps: list[MigrationStep] = []
    for kind in kinds:
        base = _BASE_BY_KIND[kind]
        destination = f"{base}/{_segment(product)}"
        for legacy in _LEGACY_SEGMENTS.get(canonical, ()):
            source = f"{base}/{legacy}"
            if source == destination:
                continue
            steps.append(
                MigrationStep(
                    kind=kind,
                    source=source,
                    destination=destination,
                    reason=f"legacy alias {legacy!r} maps to canonical {canonical!r}",
                )
            )
    return MigrationPlan(product=canonical, dry_run=True, steps=steps)
