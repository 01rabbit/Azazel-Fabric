"""Canonical HMAC transport signature for Edge decision envelopes.

Fabric describes the *wire format* only: how the bytes an Edge decision is
signed over are canonicalized, and how the HMAC-SHA256 signature is computed
and verified. It makes no trust decision and grants no authority -- a signature
proves origin/integrity of the decision on the transport, nothing more. The
shared key is supplied by the operator/integration boundary and is never stored
in the repository.

This is the single authoritative definition both the Edge-side producer and the
AZ-06 (Azazel-Deception) consumer sign/verify against, so their signatures
interoperate byte-for-byte. The canonicalization is deliberately identical to
AZ-06's ``azazel_deception.runtime.transport`` (JSON, ``sort_keys``, compact
separators, ``ensure_ascii=False``, ``allow_nan=False``, signature field
excluded).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any

DEFAULT_DECISION_SIGNATURE_FIELD = "decision_signature"


def _as_key(key: str | bytes) -> bytes:
    return key.encode("utf-8") if isinstance(key, str) else bytes(key)


def canonical_decision_bytes(
    decision: Mapping[str, Any],
    *,
    signature_field: str = DEFAULT_DECISION_SIGNATURE_FIELD,
) -> bytes:
    """Return the deterministic bytes an Edge signature covers.

    The signature field itself is excluded; every other field is bound. The
    encoding is stable across processes/architectures so a signature minted on
    one host verifies on another.
    """

    payload = {k: v for k, v in dict(decision).items() if k != signature_field}
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def compute_decision_signature(
    decision: Mapping[str, Any],
    key: str | bytes,
    *,
    signature_field: str = DEFAULT_DECISION_SIGNATURE_FIELD,
) -> str:
    return hmac.new(
        _as_key(key),
        canonical_decision_bytes(decision, signature_field=signature_field),
        hashlib.sha256,
    ).hexdigest()


def sign_decision(
    decision: Mapping[str, Any],
    key: str | bytes,
    *,
    signature_field: str = DEFAULT_DECISION_SIGNATURE_FIELD,
) -> dict[str, Any]:
    """Return a copy of ``decision`` with an HMAC signature attached.

    Signing grants no authority; it only proves origin/integrity. A signed
    decision is still subject to every product-local authorization gate.
    """

    signed = dict(decision)
    signed[signature_field] = compute_decision_signature(
        decision, key, signature_field=signature_field
    )
    return signed


def verify_decision_signature(
    decision: Mapping[str, Any],
    key: str | bytes,
    *,
    signature_field: str = DEFAULT_DECISION_SIGNATURE_FIELD,
) -> bool:
    """Constant-time verify the signature over the canonical decision bytes.

    Fail-closed: a missing/empty/non-string signature, a mismatch, or any error
    returns ``False``.
    """

    try:
        provided = decision.get(signature_field)
        if not isinstance(provided, str) or not provided:
            return False
        expected = compute_decision_signature(
            decision, key, signature_field=signature_field
        )
        return hmac.compare_digest(provided, expected)
    except Exception:
        return False
