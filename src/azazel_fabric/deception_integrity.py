"""Deterministic integrity helpers for AZ-06 deception packages.

This module defines representation-level canonicalization only.  It does not
make trust decisions, verify signatures, activate workloads, or grant runtime
authority.

``package_digest`` binds the complete package semantics except for the digest
field itself and the detached ``signature_ref`` pointer.  ``signer_ref`` is
included so changing the expected signer identity changes the content digest.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping

from azazel_fabric.deception_contracts import DeceptionPackage


class PackageIntegrityError(ValueError):
    pass


def package_signing_payload(value: DeceptionPackage | Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact semantic payload covered by ``package_digest``.

    The detached signature locator is excluded because it can only be known
    after an external signer/attestation service has signed the canonical
    bytes.  All other fields, including image verification state, safety
    policy, tiers, narrative, credentials, and ``signer_ref``, remain bound.
    """

    if isinstance(value, DeceptionPackage):
        payload = value.model_dump(mode="json")
    else:
        payload = deepcopy(dict(value))
    payload.pop("package_digest", None)
    payload.pop("signature_ref", None)
    return payload


def canonical_package_signing_bytes(
    value: DeceptionPackage | Mapping[str, Any],
) -> bytes:
    payload = package_signing_payload(value)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def package_content_digest(value: DeceptionPackage | Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_package_signing_bytes(value)).hexdigest()


def assert_package_content_digest(value: DeceptionPackage | Mapping[str, Any]) -> None:
    if isinstance(value, DeceptionPackage):
        declared = value.package_digest
    else:
        declared = str(value.get("package_digest") or "")
    calculated = package_content_digest(value)
    if declared != calculated:
        raise PackageIntegrityError(
            f"package_digest mismatch: declared={declared!r} calculated={calculated!r}"
        )
