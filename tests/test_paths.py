"""Tests for `azazel_fabric.paths` — candidate-path hints and dry-run migration.

Load-bearing properties: the helpers are pure and deterministic, honor the
contracts.md §5 convention, resolve legacy aliases, and the migration planner
never performs any filesystem action (it only describes).
"""

import pytest

from azazel_fabric.paths import (
    LEGACY_ALIASES,
    MigrationPlan,
    candidate_config_dirs,
    candidate_dirs,
    candidate_log_dirs,
    candidate_runtime_dirs,
    normalize_product,
    plan_migration,
    preferred_dir,
)


def test_convention_matches_contracts_section5():
    assert candidate_runtime_dirs("edge")[0] == "/run/azazel-edge"
    assert candidate_config_dirs("edge")[0] == "/etc/azazel-edge"
    assert candidate_log_dirs("edge")[0] == "/var/log/azazel-edge"


def test_preferred_dir_is_first_candidate():
    assert preferred_dir("gadget", "runtime") == "/run/azazel-gadget"
    assert preferred_dir("gadget", "config") == "/etc/azazel-gadget"


def test_normalize_resolves_legacy_and_prefixed_names():
    # legacy aliases (contracts.md §5)
    assert normalize_product("azazel-pi") == "edge"
    assert normalize_product("azazel-zero") == "gadget"
    assert normalize_product("pi") == "edge"
    assert normalize_product("zero") == "gadget"
    # canonical + azazel- prefix
    assert normalize_product("edge") == "edge"
    assert normalize_product("azazel-edge") == "edge"
    # unknown future product passes through (hint, not a gate)
    assert normalize_product("Azazel-Boot") == "boot"


def test_legacy_alias_surfaces_as_lower_priority_candidate():
    runtime = candidate_runtime_dirs("edge")
    assert runtime[0] == "/run/azazel-edge"
    assert "/run/azazel-pi" in runtime  # legacy hint, present but not first
    assert runtime.index("/run/azazel-edge") < runtime.index("/run/azazel-pi")


def test_legacy_name_resolves_to_canonical_schema():
    # Asking by the legacy name yields the canonical directory first.
    assert candidate_runtime_dirs("azazel-pi")[0] == "/run/azazel-edge"


def test_candidate_lists_are_pure_and_deterministic():
    # Same input -> identical output, repeatedly (no fs/env/clock/order effects).
    a = candidate_dirs("edge", "log")
    b = candidate_dirs("edge", "log")
    assert a == b
    assert a is not b  # a fresh list each call, not shared mutable state
    a.append("mutated")
    assert candidate_dirs("edge", "log") == b  # mutation did not leak


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        candidate_dirs("edge", "nonsense")  # type: ignore[arg-type]


def test_product_without_legacy_has_single_candidate():
    # cti has no legacy alias -> exactly one candidate.
    assert candidate_runtime_dirs("cti") == ["/run/azazel-cti"]


def test_plan_migration_describes_legacy_moves():
    plan = plan_migration("edge")
    assert isinstance(plan, MigrationPlan)
    assert plan.dry_run is True
    assert plan.product == "edge"
    sources = {s.source for s in plan.steps}
    dests = {s.destination for s in plan.steps}
    assert "/run/azazel-pi" in sources
    assert "/run/azazel-edge" in dests
    # one step per kind (runtime/config/log)
    assert {s.kind for s in plan.steps} == {"runtime", "config", "log"}


def test_plan_migration_is_noop_without_legacy_alias():
    plan = plan_migration("cti")
    assert plan.is_noop is True
    assert plan.steps == []


def test_plan_migration_accepts_legacy_name_and_kind_subset():
    plan = plan_migration("azazel-zero", kinds=("runtime",))
    assert plan.product == "gadget"
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.source == "/run/azazel-zero"
    assert step.destination == "/run/azazel-gadget"


def test_legacy_aliases_table_is_exposed():
    # Consumers can inspect the alias map.
    assert LEGACY_ALIASES["azazel-pi"] == "edge"
