"""Candidate-path *hints* for the Azazel series (`contracts.md` §5).

Pure helpers that return the series' conventional runtime/config/log directory
names as candidate lists, plus a dry-run-only legacy-migration planner. These
are hints, never authority: a product keeps its own path schema and may ignore
every candidate returned here. Nothing in this package touches the filesystem,
the environment, or the clock — see :mod:`azazel_fabric.paths.schema`.
"""

from azazel_fabric.paths.migration import (
    MigrationPlan,
    MigrationStep,
    plan_migration,
)
from azazel_fabric.paths.schema import (
    KNOWN_PRODUCTS,
    LEGACY_ALIASES,
    PathKind,
    candidate_config_dirs,
    candidate_dirs,
    candidate_log_dirs,
    candidate_runtime_dirs,
    normalize_product,
    preferred_dir,
)

__all__ = [
    "PathKind",
    "KNOWN_PRODUCTS",
    "LEGACY_ALIASES",
    "normalize_product",
    "candidate_dirs",
    "candidate_runtime_dirs",
    "candidate_config_dirs",
    "candidate_log_dirs",
    "preferred_dir",
    "MigrationStep",
    "MigrationPlan",
    "plan_migration",
]
