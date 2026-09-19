"""Canonical bytes and content digests for provisioning records.

Representation-level canonicalization only. This module makes no trust
decision, verifies no signature, admits no artifact, and grants no runtime
authority: it answers "what exactly do these bytes say" so a producer and a
consumer in two repositories agree on the same answer.

The canonical form is byte-identical to the one the existing contract families
already use (``azazel_fabric.deception_integrity``,
``azazel_fabric.outcome_contracts.canonical_fact_json``): JSON with sorted keys,
no insignificant whitespace, non-ASCII preserved, and NaN/Infinity rejected.
``tests/test_provisioning_contracts.py`` pins that equivalence.

A digest binds everything about a record *except* the digest field itself and
any detached ``signature_ref``-style locator, which can only be known after an
external signer has signed the canonical bytes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

# Fields excluded from every content digest: a self-referential digest field
# cannot cover itself, and a detached signature locator is assigned afterwards.
DEFAULT_DIGEST_EXCLUSIONS: tuple[str, ...] = ("signature_ref",)


class ProvisioningIntegrityError(ValueError):
    """A declared digest does not match the record's canonical bytes."""


def _as_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return dict(value)
    return value


def canonical_contract_json(value: Any) -> str:
    """Return the canonical JSON text for a provisioning record or mapping."""

    return json.dumps(
        _as_payload(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_contract_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 bytes for a provisioning record or mapping."""

    return canonical_contract_json(value).encode("utf-8")


def digest_payload(
    value: Any,
    *,
    digest_field: str | None = None,
    exclude: Iterable[str] = DEFAULT_DIGEST_EXCLUSIONS,
) -> dict[str, Any]:
    """Return the exact payload a content digest covers.

    ``digest_field`` (the record's own digest, when it carries one) and every
    name in ``exclude`` are removed; everything else stays bound, so changing any
    other field changes the digest. A record with no self-digest field passes
    ``digest_field=None`` and is covered whole.
    """

    payload = _as_payload(value)
    if not isinstance(payload, dict):
        raise TypeError("a provisioning digest payload must be a mapping")
    payload = dict(payload)
    if digest_field is not None:
        payload.pop(digest_field, None)
    for name in exclude:
        payload.pop(name, None)
    return payload


def content_digest(
    value: Any,
    *,
    digest_field: str | None = None,
    exclude: Iterable[str] = DEFAULT_DIGEST_EXCLUSIONS,
) -> str:
    """Return ``sha256:<hex>`` over the canonical bytes of the covered payload."""

    payload = digest_payload(value, digest_field=digest_field, exclude=exclude)
    return "sha256:" + hashlib.sha256(canonical_contract_bytes(payload)).hexdigest()


def assert_content_digest(
    value: Any,
    *,
    digest_field: str,
    exclude: Iterable[str] = DEFAULT_DIGEST_EXCLUSIONS,
) -> None:
    """Fail closed when a record's declared digest does not match its content."""

    payload = _as_payload(value)
    if isinstance(payload, dict):
        declared = str(payload.get(digest_field) or "")
    else:
        declared = str(getattr(value, digest_field, "") or "")
    calculated = content_digest(value, digest_field=digest_field, exclude=exclude)
    if declared != calculated:
        raise ProvisioningIntegrityError(
            f"{digest_field} mismatch: declared={declared!r} calculated={calculated!r}"
        )


__all__ = [
    "DEFAULT_DIGEST_EXCLUSIONS",
    "ProvisioningIntegrityError",
    "assert_content_digest",
    "canonical_contract_bytes",
    "canonical_contract_json",
    "content_digest",
    "digest_payload",
]
