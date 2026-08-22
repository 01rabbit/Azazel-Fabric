"""Canonical Edge-decision transport signature (Fabric#9 signature reference)."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from azazel_fabric.deception_contracts import (
    DEFAULT_DECISION_SIGNATURE_FIELD,
    EnvironmentTransitionDecision,
    canonical_decision_bytes,
    compute_decision_signature,
    sign_decision,
    verify_decision_signature,
)

_KEY = "shared-operator-transport-key"


def _decision() -> dict:
    return EnvironmentTransitionDecision(
        decision_id="edge-decision-1",
        status="accepted",
        environment_id="env-1",
        current_state="baseline",
        target_state="smb-share-open",
        effective_at="2026-08-20T00:00:00+00:00",
        expires_at="2026-08-22T00:00:00+00:00",
    ).model_dump(mode="json")


def test_sign_then_verify_round_trips():
    signed = sign_decision(_decision(), _KEY)
    assert DEFAULT_DECISION_SIGNATURE_FIELD in signed
    assert verify_decision_signature(signed, _KEY) is True


def test_signature_excludes_only_the_signature_field():
    d = _decision()
    signed = sign_decision(d, _KEY)
    # Recomputing over the signed dict (which now carries the signature field)
    # yields the same signature -> the field is excluded from its own coverage.
    assert compute_decision_signature(signed, _KEY) == signed[DEFAULT_DECISION_SIGNATURE_FIELD]


def test_tamper_after_signing_fails_verification():
    signed = sign_decision(_decision(), _KEY)
    signed["target_state"] = "tampered-state"
    assert verify_decision_signature(signed, _KEY) is False


def test_wrong_key_fails_closed():
    signed = sign_decision(_decision(), _KEY)
    assert verify_decision_signature(signed, "different-key") is False


@pytest.mark.parametrize("bad", [{}, {"decision_signature": ""}, {"decision_signature": 123}])
def test_missing_or_malformed_signature_fails_closed(bad):
    d = _decision()
    d.update(bad)
    assert verify_decision_signature(d, _KEY) is False


def test_canonical_bytes_are_stable_and_sorted():
    d = _decision()
    # Key order in the input must not change the canonical bytes.
    shuffled = dict(reversed(list(d.items())))
    assert canonical_decision_bytes(d) == canonical_decision_bytes(shuffled)


def test_canonical_bytes_match_azdeception_transport_format():
    # Interop guarantee: the byte format is exactly what AZ-06's
    # azazel_deception.runtime.transport produces, so an Edge-side signature
    # verifies on the Deception side and vice versa. Reproduce that format
    # independently here (JSON, sort_keys, compact separators, ensure_ascii
    # False, allow_nan False, signature field excluded) and compare bytes +
    # HMAC.
    d = sign_decision(_decision(), _KEY)
    payload = {k: v for k, v in d.items() if k != DEFAULT_DECISION_SIGNATURE_FIELD}
    expected_bytes = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    assert canonical_decision_bytes(d) == expected_bytes
    expected_sig = hmac.new(_KEY.encode(), expected_bytes, hashlib.sha256).hexdigest()
    assert d[DEFAULT_DECISION_SIGNATURE_FIELD] == expected_sig
