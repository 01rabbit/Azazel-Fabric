"""No contract encodes a RAM-to-tier threshold (Fabric#23, plan §15 OF-01).

The program plan records that the MiB-to-tier table is **unratified** and that
resolving it is an owner decision (Azazel#74): the plan's own table classifies
a 16095 MiB host as `core`, which contradicts the measurements. A contract that
carried a tier derived from that table would freeze an unratified number into
the one place every product reads, and a product disagreeing with it would be
disagreeing with the shared vocabulary rather than with a threshold it owns.

So the line this file holds is:

* a contract **may** carry **measured** capacity -- `usable_memory_mib` and the
  rest are facts about a host, and a fact is what Fabric is for;
* a contract **may** carry a package's **stated requirement** -- a deployment
  tier's `minimum` is what that package says it needs, which a product compares
  against its own measurements;
* a contract **may not** carry a tier *derived* from measured capacity, nor the
  threshold that would derive one.

The difference is who decided. Measured MiB and a declared minimum are inputs;
a capability tier is a verdict, and the verdict belongs to the product whose
deny-by-default admission policy has to live with it.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest
from pydantic import BaseModel

import azazel_fabric
from azazel_fabric.provisioning_contracts.validation import (
    BANNED_TIER_CLAIM_FIELDS,
    assert_no_resource_tier_claim,
)

PACKAGE_ROOT = Path(azazel_fabric.__file__).parent

FAMILIES = (
    "deception_contracts",
    "engagement_contracts",
    "provisioning_contracts",
    "mio_contracts",
    "outcome_contracts",
    "effect_contracts",
)

#: Capability states the unratified table would assign. A contract naming one
#: as a *value* is carrying the verdict, whatever the field is called.
CAPABILITY_STATES = ("CORE", "LITE", "FULL")

#: Tier-shaped fields that are not a RAM verdict, each with the reason it is
#: not. An exemption without a reason is where the next one gets parked.
TIER_FIELD_EXEMPTIONS: dict[str, str] = {
    # A package declares which tiers it offers and what each needs
    # (`minimum: ResourceBudget`). That is a stated requirement, not a
    # classification of a host -- the product compares it against its own
    # measurements and reaches its own answer.
    "DeploymentTier.tier_id": "package-declared tier, not a host classification",
    "DeceptionPackage.deployment_tiers": "the package's own declared tiers",
    # These record *which* declared tier a product selected. The selection is
    # the product's; recording it is provenance, not Fabric deciding.
    "PlacementPlan.selected_tier": "records a product's own selection",
    "EnvironmentActivationDecision.selected_tier": "records a product's own selection",
    "EnvironmentOutcome.selected_tier": "records a product's own selection",
    "RuntimeContext.selected_tier": "records a product's own selection",
}


def _contract_models() -> dict[str, type[BaseModel]]:
    models: dict[str, type[BaseModel]] = {}
    for family in FAMILIES:
        module = importlib.import_module(f"azazel_fabric.{family}")
        for name in getattr(module, "__all__", []):
            obj = getattr(module, name, None)
            if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
                models[name] = obj
    return models


def test_the_model_sweep_is_not_empty():
    assert len(_contract_models()) > 50


def test_no_contract_carries_a_tier_that_is_not_explicitly_exempt():
    offenders = []
    for model_name, model in sorted(_contract_models().items()):
        for field in model.model_fields:
            if "tier" not in field.lower():
                continue
            key = f"{model_name}.{field}"
            if key in TIER_FIELD_EXEMPTIONS:
                continue
            offenders.append(key)

    assert offenders == [], (
        f"these contract fields are tier-shaped and unexempted: {offenders}. "
        "A tier derived from measured capacity is a verdict, and the verdict "
        "belongs to the product. If the field records a product's own "
        "selection or a package's declared requirement, add it to "
        "TIER_FIELD_EXEMPTIONS with the reason."
    )


def test_every_exemption_still_names_a_real_field():
    """An exemption that outlives its field stops exempting and starts hiding."""
    models = _contract_models()
    stale = []
    for key in sorted(TIER_FIELD_EXEMPTIONS):
        model_name, _, field = key.partition(".")
        model = models.get(model_name)
        if model is None or field not in model.model_fields:
            stale.append(key)

    assert stale == [], f"TIER_FIELD_EXEMPTIONS names fields that no longer exist: {stale}"


def test_every_exemption_carries_a_reason():
    empty = sorted(k for k, reason in TIER_FIELD_EXEMPTIONS.items() if len(reason.strip()) < 15)
    assert empty == [], f"exemptions with no stated reason: {empty}"


#: The one module allowed to name the capability states, and why.
#:
#: `provisioning_contracts/registry.py` publishes them as an **open registry of
#: names**, so two products call the same summary the same thing. Registering a
#: word is not deciding with it -- the same reason `REGISTERED_PRODUCTS` may
#: list every product without Fabric admitting any of them. The module says so
#: itself: "deliberately NOT a field on any Fabric contract".
_CAPABILITY_STATE_REGISTRY = "provisioning_contracts/registry.py"


def test_only_the_registry_names_the_capability_states():
    """They may be *named* in one place; they may be a *value* nowhere else.

    Parsed rather than grepped: the models explain in prose why they carry no
    tier, and an explanation of a rule is not distinguishable from an instance
    of breaking it by text search.
    """

    offenders = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = str(path.relative_to(PACKAGE_ROOT))
        if relative == _CAPABILITY_STATE_REGISTRY:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {
            doc
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            for doc in [ast.get_docstring(node, clean=False)]
            if doc is not None
        }
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if node.value in docstrings:
                continue
            if node.value in CAPABILITY_STATES:
                offenders.append(f"{relative}: {node.value!r}")

    assert offenders == [], (
        f"a capability state appears as a value outside the registry: "
        f"{offenders}. One place may name them; anywhere else is a contract "
        "starting to carry one."
    )


def test_the_registry_defines_no_mapping_from_a_number_to_a_state():
    """The actual risk, stated precisely.

    Listing `CORE`/`LITE`/`FULL` is harmless. What would encode the unratified
    table is a *mapping* -- a dict, a comparison chain, any literal pairing a
    MiB figure with one of those names. The plan's own table calls a 16095 MiB
    host `core` while the measurements disagree (§15 OF-01, Azazel#74); putting
    either answer here would make an unratified number the shared vocabulary,
    and a product that disagreed would be disagreeing with the contract rather
    than with a threshold it owns.
    """

    path = PACKAGE_ROOT / _CAPABILITY_STATE_REGISTRY
    tree = ast.parse(path.read_text(encoding="utf-8"))

    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            values = [v.value for v in node.values if isinstance(v, ast.Constant)]
            paired = set(keys) | set(values)
            if paired & set(CAPABILITY_STATES) and any(
                isinstance(item, (int, float)) for item in keys + values
            ):
                offenders.append(
                    f"dict pairing a number with a capability state at line {node.lineno}"
                )

    # Any callable that can hand back a capability state is a classifier,
    # whatever it is called and whatever shape the threshold takes inside it.
    # Looking for "a comparison containing a state name and a digit" misses
    # `return "FULL" if mib >= 8192 else "CORE"` entirely -- the states are in
    # the conditional expression and the number is in the comparison, so
    # neither node holds both. The registry publishes names; a function that
    # returns one has stopped publishing and started deciding.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Return) or inner.value is None:
                continue
            returned = ast.unparse(inner.value)
            if any(f'"{state}"' in returned or f"'{state}'" in returned
                   for state in CAPABILITY_STATES):
                offenders.append(
                    f"{node.name}() returns a capability state at line {inner.lineno}"
                )

    assert offenders == [], (
        f"{_CAPABILITY_STATE_REGISTRY} classifies rather than publishes: "
        f"{offenders}. The MiB-to-tier table is unratified (plan §15 OF-01); "
        "the product that has to live with the verdict is the one that reaches it."
    )


def test_no_contract_model_declares_a_capability_state_as_an_allowed_value():
    """A `Literal["CORE", ...]` field would carry the verdict by its type."""
    import typing

    offenders = []
    for model_name, model in sorted(_contract_models().items()):
        for field_name, field in model.model_fields.items():
            args = typing.get_args(field.annotation)
            if set(args) & set(CAPABILITY_STATES):
                offenders.append(f"{model_name}.{field_name}")

    assert offenders == [], (
        f"these contract fields admit a capability state as a value: {offenders}"
    )


def test_a_measured_capacity_field_is_still_allowed():
    """The other half. A guard that refused capacity would refuse facts."""
    from azazel_fabric.provisioning_contracts import ResourceProfile

    measured = {f for f in ResourceProfile.model_fields if f.endswith("_mib")}

    # Pinned as a set, not a floor. "at least three" passes after one is
    # renamed away, and the one that goes is the one nobody noticed depended
    # on it. Fabric may not state a tier; it must still state what was
    # measured, or a product has nothing to reach its own verdict from.
    assert measured == {
        "usable_memory_mib",
        "installed_memory_mib",
        "firmware_reserved_memory_mib",
        "usable_storage_mib",
        "measured_core_reserve_mib",
    }, (
        f"ResourceProfile's measured-capacity fields are now {sorted(measured)}. "
        "Adding one is fine -- update this set. Removing one takes away input a "
        "product needs to classify its own host."
    )
    assert not any("tier" in f.lower() for f in ResourceProfile.model_fields)


@pytest.mark.parametrize("field", sorted(BANNED_TIER_CLAIM_FIELDS)[:20])
def test_the_tier_claim_guard_rejects_a_tier_nested_anywhere(field):
    with pytest.raises(ValueError):
        assert_no_resource_tier_claim({"a": [{"b": {field: "CORE"}}]})


def test_the_tier_claim_guard_permits_measured_capacity():
    assert_no_resource_tier_claim(
        {"usable_memory_mib": 16095, "installed_memory_mib": 16384, "nested": [{"a": 1}]}
    )
