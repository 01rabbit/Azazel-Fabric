"""Round-trip + deterministic-serialization property tests (Fabric#9).

Fabric#9 acceptance items: "deterministic serialization/content digest
stability" and "schema round-trip". For a representative instance of each major
contract family this asserts:

* **schema round-trip**: ``model_validate(model_dump(mode="json"))`` reproduces
  an equal model (no field lost or coerced across a JSON boundary);
* **deterministic serialization**: ``model_dump_json`` is byte-stable across
  repeated dumps and across a dump -> validate -> dump cycle, so a contract
  serialized on one host/process is byte-identical on another (portability
  baseline); and
* **content-digest stability** (where a contract carries a content digest): the
  digest recomputed after a JSON round-trip is unchanged.

Instances come from the shipped ``azazel_fabric.testing`` factories where they
exist (guaranteed-valid, and the same fixtures AZ-06/Edge/Knowledge consume),
plus minimal valid instances of the decision/engagement families.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from datetime import datetime, timezone

from azazel_fabric.deception_contracts import (
    CredentialLure,
    DecoySurface,
    EnvironmentActivationDecision,
    EnvironmentEvent,
    EnvironmentOutcome,
    EnvironmentTerminationDecision,
    EnvironmentTransitionDecision,
    ResourceBudget,
)
from azazel_fabric.engagement_contracts import (
    EngagementAdvisory,
    EngagementCandidate,
    EngagementConstraint,
    EngagementEvent,
    EngagementOutcome,
    EngagementTrigger,
    PostureSuggestion,
)
from azazel_fabric.deception_integrity import (
    catalog_content_digest,
    package_signing_payload,
)
from azazel_fabric.testing import (
    make_deception_host_capabilities,
    make_deception_package,
    make_deception_placement,
    make_effectiveness_advisory,
    make_interaction_observation,
    make_transition_catalog,
)


def _transition_decision() -> EnvironmentTransitionDecision:
    return EnvironmentTransitionDecision(
        decision_id="edge-decision-1", status="accepted", environment_id="env-1",
        current_state="baseline", target_state="smb-share-open",
        effective_at="2026-08-20T00:00:00+00:00", expires_at="2026-08-22T00:00:00+00:00",
    )


def _engagement_candidate() -> EngagementCandidate:
    return EngagementCandidate(
        candidate_id="cand-1", product="AZ-01", objective="collect", approach="channel",
        activity="redirect_to_decoy", attack_techniques=["T1110"],
        requested_actions=["redirect_to_decoy"],
        trigger=EngagementTrigger(attack_technique="T1110", confidence=0.9),
        constraints=EngagementConstraint(
            max_duration_seconds=300, outbound_allowed=False, production_access=False,
            termination_conditions=["noc_health_degraded"],
        ),
    )


def _engagement_advisory() -> EngagementAdvisory:
    return EngagementAdvisory(
        advisory_id="adv-1", advisor="azazel-knowledge", confidence=0.8,
        behavior_class="adaptive_probe",
        posture_suggestion=PostureSuggestion(
            objective="collect", approach="channel",
            supported_activities=["redirect_to_decoy"], reasons=["similar_pattern"],
        ),
        limitations=["intent unknown"],
    )


_DT_A = datetime(2026, 8, 20, 0, 0, 0, tzinfo=timezone.utc)
_DT_B = datetime(2026, 8, 22, 0, 0, 0, tzinfo=timezone.utc)
_SHA = "sha256:" + "a" * 64


def _activation_decision() -> EnvironmentActivationDecision:
    return EnvironmentActivationDecision(
        decision_id="edge-act-1", status="accepted", package_id="pkg-1",
        package_digest=_SHA, target_node_id="node-1", selected_tier="minimal",
        budget=ResourceBudget(cpu_cores=1.0, memory_mb=256, storage_mb=512),
        effective_at=_DT_A, expires_at=_DT_B,
    )


def _termination_decision() -> EnvironmentTerminationDecision:
    return EnvironmentTerminationDecision(
        decision_id="edge-term-1", environment_id="env-1", reason="operator_terminate",
        issued_at=_DT_A, expires_at=_DT_B,
    )


def _environment_event() -> EnvironmentEvent:
    # Populated metadata deliberately exercises the dict[str, str|int|float|bool|
    # None] union round-trip (the classic pydantic bool-vs-int coercion footgun).
    return EnvironmentEvent(
        event_id="ev-1", environment_id="env-1", package_id="pkg-1", node_id="node-1",
        event_type="activated", observed_at=_DT_A,
        metadata={"flag": True, "count": 5, "ratio": 0.5, "label": "x", "empty": None},
    )


def _environment_outcome() -> EnvironmentOutcome:
    placement = make_deception_placement()
    return EnvironmentOutcome(
        outcome_id="out-1", environment_id="env-1", package_id="pkg-1",
        package_digest=_SHA, node_id="node-1",
        architecture=placement.architecture, runtime_adapter=placement.runtime_adapter,
        selected_tier="minimal", termination_reason="max_duration_reached",
        reset_succeeded=True,
    )


def _engagement_outcome() -> EngagementOutcome:
    return EngagementOutcome(attacker_reaction="decoy_engaged", reaction_window_s=42)


def _engagement_event() -> EngagementEvent:
    return EngagementEvent(
        event_id="engev-1", product="AZ-01", objective="collect", approach="channel",
        activity="redirect_to_decoy",
        constraints=EngagementConstraint(
            max_duration_seconds=300, outbound_allowed=False, production_access=False,
            termination_conditions=["noc_health_degraded"],
        ),
        outcome=_engagement_outcome(),
    )


def _samples() -> list[BaseModel]:
    return [
        make_deception_package(),
        make_transition_catalog(),
        make_interaction_observation(),
        make_effectiveness_advisory(),
        make_deception_placement(),
        make_deception_host_capabilities(),
        _transition_decision(),
        _engagement_candidate(),
        _engagement_advisory(),
        # Previously-uncovered contract models (adversarial-review finding #5):
        DecoySurface(surface_id="s1", protocol="tcp", port=8080, service="smb"),
        CredentialLure(
            credential_id="c1", owner_persona_id="p1", target_surface_id="s1",
            expires_at=_DT_B,
        ),
        _activation_decision(),
        _termination_decision(),
        _environment_event(),
        _environment_outcome(),
        _engagement_outcome(),
        _engagement_event(),
    ]


#: Every contract family, not the two this file started with. The completeness
#: guard below enumerates these, so a family left out of the tuple is a family
#: whose models may ship with no round-trip coverage and nothing to say so --
#: which is how `provisioning_contracts`, `mio_contracts`, `outcome_contracts`
#: and `effect_contracts` came to hold 42 of the package's 73 contract models
#: outside the guard, including all three projections.
COVERED_FAMILIES = (
    "deception_contracts",
    "engagement_contracts",
    "provisioning_contracts",
    "mio_contracts",
    "outcome_contracts",
    "effect_contracts",
)


def _model_by_schema_version() -> dict[str, type[BaseModel]]:
    """Map each `schema_version` literal to the model that declares it.

    Derived from the models rather than written down: a mapping kept by hand
    would go stale on the contract it was not updated for, and that contract is
    the one whose fixture would then quietly stop being validated.
    """

    import importlib
    import inspect
    import typing

    mapping: dict[str, type[BaseModel]] = {}
    for family in COVERED_FAMILIES:
        module = importlib.import_module(f"azazel_fabric.{family}")
        for name in getattr(module, "__all__", []):
            obj = getattr(module, name, None)
            if not (inspect.isclass(obj) and issubclass(obj, BaseModel)):
                continue
            field = obj.model_fields.get("schema_version")
            if field is None:
                continue
            args = typing.get_args(field.annotation)
            if args:
                mapping[args[0]] = obj
    return mapping


def _golden_provisioning_samples() -> list[BaseModel]:
    """The published R1a vectors, as models.

    These are the same bytes every consumer runs against, so round-tripping
    them here checks the fixture and the model together: a fixture that no
    longer validates is as much a break as a model that no longer round-trips.
    Negative vectors are excluded by name -- they exist to be rejected.
    """

    from azazel_fabric.testing import (
        GOLDEN_PROVISIONING_NEGATIVE,
        golden_provisioning_names,
        load_golden_provisioning,
    )

    mapping = _model_by_schema_version()
    samples: list[BaseModel] = []
    for name in golden_provisioning_names():
        if name in GOLDEN_PROVISIONING_NEGATIVE:
            continue
        payload = load_golden_provisioning(name)
        model = mapping.get(payload.get("schema_version"))
        assert model is not None, (
            f"golden vector {name!r} declares schema_version "
            f"{payload.get('schema_version')!r}, which no contract model claims"
        )
        samples.append(model.model_validate(payload))
    return samples


def _golden_effect_samples() -> list[BaseModel]:
    """The published cross-series effect vectors, as models."""
    from azazel_fabric.testing.effect import GOLDEN_EFFECT_VECTORS

    mapping = _model_by_schema_version()
    samples: list[BaseModel] = []
    for name, factory in sorted(GOLDEN_EFFECT_VECTORS.items()):
        payload = factory()
        model = mapping.get(payload.get("schema_version"))
        assert model is not None, (
            f"effect vector {name!r} declares schema_version "
            f"{payload.get('schema_version')!r}, which no contract model claims"
        )
        samples.append(model.model_validate(payload))
    return samples


def _outcome_samples() -> list[BaseModel]:
    """Outcome-as-Evidence records.

    Built from `test_outcome_contracts`' own constructors rather than a second
    set here: two ways of building the same record drift, and the copy is the
    one that stops matching the contract. Imported by bare module name because
    `tests/` is not a package -- pytest puts that directory on `sys.path`, and
    a `tests.` prefix resolves only under `python -m pytest`, not the bare
    `pytest` CI runs.
    """

    from test_outcome_contracts import assessment, execution, mechanism, outcome

    return [execution(), mechanism(), outcome(), assessment()]


SAMPLES = (
    _samples()
    + _golden_provisioning_samples()
    + _golden_effect_samples()
    + _outcome_samples()
)


@pytest.mark.parametrize("model", SAMPLES, ids=lambda m: type(m).__name__)
def test_schema_round_trip_is_lossless(model: BaseModel):
    restored = type(model).model_validate(model.model_dump(mode="json"))
    assert restored == model


@pytest.mark.parametrize("model", SAMPLES, ids=lambda m: type(m).__name__)
def test_serialization_is_deterministic(model: BaseModel):
    first = model.model_dump_json()
    second = model.model_dump_json()
    assert first == second  # stable across repeated dumps
    # ...and stable across a dump -> validate -> dump cycle (portability).
    restored = type(model).model_validate(model.model_dump(mode="json"))
    assert restored.model_dump_json() == first


def _reachable_model_types(instance: BaseModel, seen: set[type] | None = None) -> set[type]:
    """Every BaseModel type actually present in ``instance`` (self + nested).

    Walks live field values (not annotations), recursing through nested models,
    lists, tuples, and dict values, so a type counts as covered only if a sample
    genuinely instantiates it -- a nested model is round-tripped as part of its
    parent, so reaching it here means it is exercised.
    """
    seen = seen if seen is not None else set()
    seen.add(type(instance))
    for name in type(instance).model_fields:
        value = getattr(instance, name, None)
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, BaseModel):
                if type(item) not in seen:
                    _reachable_model_types(item, seen)
            elif isinstance(item, (list, tuple)):
                stack.extend(item)
            elif isinstance(item, dict):
                stack.extend(item.values())
    return seen


def test_every_contract_model_is_round_trip_covered():
    # Self-extending guard (adversarial-review finding #5): every contract model
    # in either family's __all__ must be exercised by the round-trip samples --
    # directly as a top-level SAMPLE or reachable as a nested field of one -- so
    # a future contract cannot ship with zero round-trip/determinism coverage.
    import inspect

    enumerated: dict[str, type] = {}
    for family in COVERED_FAMILIES:
        module = __import__(f"azazel_fabric.{family}", fromlist=["_"])
        for name in getattr(module, "__all__", []):
            obj = getattr(module, name, None)
            if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
                enumerated[obj.__name__] = obj

    covered: set[type] = set()
    for sample in SAMPLES:
        _reachable_model_types(sample, covered)

    missing = sorted(n for n, t in enumerated.items() if t not in covered)
    assert not missing, (
        "contract models with no round-trip/determinism coverage (add a sample "
        f"or nest them in one): {missing}"
    )


def test_package_digest_stable_across_round_trip():
    pkg = make_deception_package()
    from_pkg = package_signing_payload(pkg)
    restored = type(pkg).model_validate(pkg.model_dump(mode="json"))
    assert package_signing_payload(restored) == from_pkg


def test_catalog_content_digest_stable_across_round_trip():
    catalog = make_transition_catalog()
    before = catalog_content_digest(catalog)
    restored = type(catalog).model_validate(catalog.model_dump(mode="json"))
    assert catalog_content_digest(restored) == before


# ---------------------------------------------------------------------------
# Projections: descriptive, and nothing more (Fabric#23)
# ---------------------------------------------------------------------------
#
# The R1 exit gate asks that each projection "exists, round-trips canonically,
# and has neither trust-decision nor chain-enforcement behaviour". The first
# two are covered above, now that the completeness guard reaches every family.
# This is the third, which is a claim about what a projection must *not* do.
#
# A projection carries the material a product needs to reach its own verdict:
# a checkpoint's head and previous refs, an epoch, a revocation-list reference.
# The temptation is to also answer the question that material is for -- is this
# chain intact, is this node trusted -- and the moment Fabric answers it, a
# product that reads the answer has delegated a trust decision to a package
# that describes rather than decides.

PROJECTIONS = (
    ("provisioning_contracts", "AuditCheckpointProjection"),
    ("provisioning_contracts", "SecurityStateProjection"),
    ("mio_contracts", "ClaimSet"),
)

#: Names that would mean the projection reached a verdict rather than carrying
#: the material for one. `*_ref` and `*_refs` are deliberately absent: an
#: opaque reference to a revocation list or a chain head is exactly the
#: material a product needs, and naming it is not deciding about it.
_VERDICT_MARKERS = (
    "is_trusted",
    "trusted",
    "trust_decision",
    "verified",
    "is_valid",
    "valid",
    "chain_intact",
    "chain_verified",
    "attested",
    "accepted",
    "admitted",
)


@pytest.mark.parametrize(
    ("family", "model_name"), PROJECTIONS, ids=[f"{f}.{m}" for f, m in PROJECTIONS]
)
def test_the_projection_exists_and_declares_itself_descriptive(family, model_name):
    import importlib

    module = importlib.import_module(f"azazel_fabric.{family}")
    model = getattr(module, model_name, None)

    assert model is not None, f"{family} no longer exports {model_name}"
    authority = model.model_fields.get("authority")
    assert authority is not None, f"{model_name} carries no authority field"

    import typing

    allowed = typing.get_args(authority.annotation)
    assert allowed == ("descriptive_only",), (
        f"{model_name}.authority permits {allowed}. A projection describes; a "
        "second permitted value is a projection that can claim to decide."
    )


@pytest.mark.parametrize(
    ("family", "model_name"), PROJECTIONS, ids=[f"{f}.{m}" for f, m in PROJECTIONS]
)
def test_the_projection_states_no_verdict(family, model_name):
    import importlib

    module = importlib.import_module(f"azazel_fabric.{family}")
    model = getattr(module, model_name)

    offenders = [
        field
        for field in model.model_fields
        if any(marker in field.lower() for marker in _VERDICT_MARKERS)
    ]

    assert offenders == [], (
        f"{model_name} carries {offenders}. A projection hands a product the "
        "material for a trust decision -- refs, epochs, a revocation list -- "
        "and never the decision. A product that reads Fabric's verdict has "
        "delegated its own."
    )


@pytest.mark.parametrize(
    ("family", "model_name"), PROJECTIONS, ids=[f"{f}.{m}" for f, m in PROJECTIONS]
)
def test_the_projection_enforces_no_chain(family, model_name):
    """No method that walks or verifies a chain.

    Shape-validating a reference is fine and is what `_validate` does. What a
    projection must not grow is a method that follows `previous_checkpoint_ref`
    to another checkpoint and reports whether the chain holds -- that is the
    product's audit store's job, and it is the one place a caller would stop
    doing it for themselves.
    """

    import importlib
    import inspect

    module = importlib.import_module(f"azazel_fabric.{family}")
    model = getattr(module, model_name)

    offenders = []
    for name, attribute in vars(model).items():
        if name.startswith("__") or not callable(attribute):
            continue
        low = name.lower()
        if any(marker in low for marker in ("chain", "verify", "attest", "resolve")):
            offenders.append(name)
            continue
        try:
            source = inspect.getsource(attribute)
        except (OSError, TypeError):
            continue
        if "previous_checkpoint_ref" in source and "head_ref" in source:
            offenders.append(f"{name} (walks the checkpoint chain)")

    assert offenders == [], (
        f"{model_name} grew chain-enforcement behaviour: {offenders}"
    )


def test_the_verdict_marker_list_has_not_been_narrowed():
    """Pinned as a literal, for the reason the count baselines are.

    The guard above asserts an absence over this list, so a marker quietly
    dropped from it widens what a projection may carry and every case still
    passes. A "does it catch something" self-check does not see that: with ten
    markers, nine of them still catch things. Only the exact set does.
    """

    assert set(_VERDICT_MARKERS) == {
        "is_trusted",
        "trusted",
        "trust_decision",
        "verified",
        "is_valid",
        "valid",
        "chain_intact",
        "chain_verified",
        "attested",
        "accepted",
        "admitted",
    }, (
        "the verdict-marker list changed. Adding a marker is fine -- update "
        "this set. Removing one means a projection may now carry a field "
        "shaped like a verdict, and no other test here can see that."
    )

    # A reference is material, not a verdict, and must not be caught.
    for allowed in ("previous_checkpoint_ref", "revocation_list_ref", "anchor_refs"):
        assert not any(marker in allowed for marker in _VERDICT_MARKERS), (
            f"the marker list would reject {allowed!r}, which is the material a "
            "product needs rather than a decision about it"
        )


def test_every_projection_in_the_package_is_under_these_guards():
    """The list above is a list; derive what it must contain.

    A projection dropped from PROJECTIONS stops being checked and nothing
    says so -- the suite just runs three cases instead of four. This asks the
    package which models are projections and requires each to be listed.
    """

    import importlib
    import inspect

    from pydantic import BaseModel

    listed = {name for _, name in PROJECTIONS}
    found: set[str] = set()
    for family in COVERED_FAMILIES:
        module = importlib.import_module(f"azazel_fabric.{family}")
        for name in getattr(module, "__all__", []):
            obj = getattr(module, name, None)
            if inspect.isclass(obj) and issubclass(obj, BaseModel) and name.endswith("Projection"):
                found.add(name)

    missing = sorted(found - listed)
    assert missing == [], (
        f"these projections ship without the descriptive-only guards: {missing}"
    )

    # `ClaimSet` is listed although its name does not end in `Projection`: the
    # program plan counts the structured claim set among the projections, and
    # it carries the same `authority` field for the same reason. Pinned so the
    # exemption cannot become a place to park anything else.
    assert listed - found == {"ClaimSet"}, (
        f"PROJECTIONS lists {sorted(listed - found)} which the package does not "
        "name a projection. ClaimSet is the one deliberate entry; anything else "
        "needs its reason written down here."
    )
