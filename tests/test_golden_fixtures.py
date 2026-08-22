"""Golden decision fixtures (Fabric#9) — committed, cross-repo-consumable vectors.

`tests/fixtures/golden/decisions/*.json` are stable, committed canonical
instances of the Edge-decision scenarios Fabric#9 enumerates. They are generated
from the validated models (valid-by-construction) and serve as shared test
vectors AZ-06 / Edge / Knowledge can load directly. This module asserts each
fixture behaves exactly as its scenario name claims — so a contract change that
would silently alter one of these canonical behaviors fails here.

`DECISION_SIGNATURE_KEY` below is a documented, non-secret key used ONLY to sign
the signature vectors reproducibly; it is never a real transport key.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from azazel_fabric.deception_contracts import (
    DEFAULT_DECISION_SIGNATURE_FIELD,
    EnvironmentActivationDecision,
    EnvironmentTransitionDecision,
    verify_decision_signature,
)

_GOLDEN = Path(__file__).parent / "fixtures" / "golden" / "decisions"
# Must match the key the generator signed the signature vectors with.
DECISION_SIGNATURE_KEY = "golden-fixture-transport-key-v1"
_EXECUTABLE = {"accepted", "modified"}


def _load(name: str) -> dict:
    return json.loads((_GOLDEN / name).read_text(encoding="utf-8"))


def test_all_golden_fixtures_are_valid_json():
    files = sorted(p.name for p in _GOLDEN.iterdir() if p.suffix == ".json")
    assert len(files) >= 7, f"expected the golden decision vectors, found {files}"
    for name in files:
        assert isinstance(_load(name), dict)


def test_activation_accepted_validates_and_is_executable():
    d = EnvironmentActivationDecision.model_validate(_load("activation_accepted.json"))
    assert d.status in _EXECUTABLE
    assert d.decision_authority == "azazel-edge"


def test_transition_modified_validates_as_modified():
    d = EnvironmentTransitionDecision.model_validate(_load("transition_modified.json"))
    assert d.status == "modified"
    assert d.status in _EXECUTABLE


def test_transition_rejected_is_valid_contract_but_not_executable():
    d = EnvironmentTransitionDecision.model_validate(_load("transition_rejected.json"))
    assert d.status == "rejected"
    assert d.status not in _EXECUTABLE  # a valid contract that must NOT be acted on


def test_stale_decision_is_detectable_as_expired():
    raw = _load("decision_stale.json")
    reference_as_of = raw.pop("_reference_as_of")  # test marker, not a contract field
    d = EnvironmentTransitionDecision.model_validate(raw)
    # The decision's window is entirely before the reference-time -> stale.
    assert d.expires_at <= datetime.fromisoformat(reference_as_of)


def test_signed_decision_verifies_and_body_validates():
    raw = _load("decision_signed_valid.json")
    assert verify_decision_signature(raw, DECISION_SIGNATURE_KEY) is True
    body = {k: v for k, v in raw.items() if k != DEFAULT_DECISION_SIGNATURE_FIELD}
    d = EnvironmentTransitionDecision.model_validate(body)
    assert d.decision_id == "golden-trans-signed"


def test_tampered_signature_fails_verification():
    raw = _load("decision_signature_tampered.json")
    assert verify_decision_signature(raw, DECISION_SIGNATURE_KEY) is False


def test_unsupported_schema_version_fails_closed():
    with pytest.raises(ValidationError):
        EnvironmentTransitionDecision.model_validate(_load("transition_unsupported_schema.json"))
