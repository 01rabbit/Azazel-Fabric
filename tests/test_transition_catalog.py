"""Tests for the AZ-06 finite-state transition catalog."""

import pytest
from pydantic import ValidationError

from azazel_fabric.deception_contracts import (
    FiniteStateTransition,
    TransitionCatalog,
    TransitionNotInCatalog,
    select_transition,
)
from azazel_fabric.deception_integrity import (
    CatalogIntegrityError,
    assert_catalog_content_digest,
    catalog_content_digest,
)
from azazel_fabric.testing import make_transition_catalog


def test_catalog_round_trip_and_descriptive_only():
    catalog = make_transition_catalog()
    dumped = catalog.model_dump(mode="json")
    assert dumped["authority"] == "descriptive_only"
    assert TransitionCatalog.model_validate(dumped) == catalog


def test_sealed_digest_is_representation_invariant():
    catalog = make_transition_catalog()
    assert_catalog_content_digest(catalog)
    # Recompute from a JSON round-trip: same meaning, same digest.
    reloaded = TransitionCatalog.model_validate(catalog.model_dump(mode="json"))
    assert catalog_content_digest(reloaded) == catalog.catalog_digest


def test_tampering_with_a_transition_breaks_the_digest():
    data = make_transition_catalog().model_dump(mode="json")
    data["transitions"][0]["to_state"] = "smb-share-open-tampered"
    with pytest.raises(CatalogIntegrityError):
        assert_catalog_content_digest(data)


def test_signature_ref_is_excluded_from_the_digest():
    a = make_transition_catalog(signature_ref="fixture:sig-a")
    b = make_transition_catalog(signature_ref="fixture:sig-b")
    # Rotating the detached locator must not change the content digest.
    assert a.catalog_digest == b.catalog_digest


def test_signer_ref_is_bound_into_the_digest():
    base = make_transition_catalog().model_dump(mode="json")
    base.pop("catalog_digest")
    rotated = dict(base, signer_ref="fixture:other-signer")
    assert catalog_content_digest(base) != catalog_content_digest(rotated)


def test_transition_requires_all_declared_fields():
    good = make_transition_catalog().transitions[0].model_dump(mode="json")
    for missing in (
        "evidence_backed_trigger",
        "expected_observation",
        "bounds",
        "rollback_state",
        "termination_conditions",
    ):
        broken = {k: v for k, v in good.items() if k != missing}
        with pytest.raises(ValidationError):
            FiniteStateTransition.model_validate(broken)


def test_termination_conditions_cannot_be_empty():
    good = make_transition_catalog().transitions[0].model_dump(mode="json")
    good["termination_conditions"] = []
    with pytest.raises(ValidationError):
        FiniteStateTransition.model_validate(good)


def test_edge_approval_and_no_egress_are_pinned():
    good = make_transition_catalog().transitions[0].model_dump(mode="json")
    with pytest.raises(ValidationError):
        FiniteStateTransition.model_validate({**good, "requires_edge_approval": False})
    with pytest.raises(ValidationError):
        FiniteStateTransition.model_validate({**good, "network_egress_allowed": True})


def test_states_must_differ():
    good = make_transition_catalog().transitions[0].model_dump(mode="json")
    with pytest.raises(ValidationError):
        FiniteStateTransition.model_validate({**good, "from_state": "x", "to_state": "x"})


def test_duplicate_transition_ids_rejected():
    data = make_transition_catalog().model_dump(mode="json")
    dup = dict(data["transitions"][0])
    data["transitions"] = [data["transitions"][0], dup]
    data.pop("catalog_digest")
    data["catalog_digest"] = catalog_content_digest(data)
    with pytest.raises(ValidationError):
        TransitionCatalog.model_validate(data)


def test_select_transition_returns_catalog_entry():
    catalog = make_transition_catalog()
    t = select_transition(catalog, current_state="baseline", target_state="smb-share-open")
    assert t.transition_id == "open-smb-share"


def test_select_transition_fails_closed_for_unknown_pair():
    catalog = make_transition_catalog()
    with pytest.raises(TransitionNotInCatalog):
        select_transition(catalog, current_state="baseline", target_state="root-shell")


def test_extra_fields_fail_closed():
    data = make_transition_catalog().model_dump(mode="json")
    data["execute_now"] = True
    with pytest.raises(ValidationError):
        TransitionCatalog.model_validate(data)
