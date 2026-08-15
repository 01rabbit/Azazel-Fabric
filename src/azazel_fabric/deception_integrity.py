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


# ---------------------------------------------------------------------------
# Transition-catalog integrity (same normalize-first pattern as packages).
# ---------------------------------------------------------------------------


class CatalogIntegrityError(ValueError):
    pass


def catalog_signing_payload(value: "Any") -> dict[str, Any]:
    """Return the semantic payload covered by ``catalog_digest``.

    Excludes the digest field itself and the detached ``signature_ref``
    locator; binds everything else, including ``signer_ref``, the bound
    ``package_id`` / ``package_digest`` identity, and every transition.
    """

    from azazel_fabric.deception_contracts.transitions import TransitionCatalog

    if isinstance(value, TransitionCatalog):
        payload = value.model_dump(mode="json")
    else:
        payload = deepcopy(dict(value))
    payload.pop("catalog_digest", None)
    payload.pop("signature_ref", None)
    return payload


def canonical_catalog_signing_bytes(value: "Any") -> bytes:
    payload = catalog_signing_payload(value)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def catalog_content_digest(value: "Any") -> str:
    return "sha256:" + hashlib.sha256(canonical_catalog_signing_bytes(value)).hexdigest()


def assert_catalog_content_digest(value: "Any") -> None:
    from azazel_fabric.deception_contracts.transitions import TransitionCatalog

    if isinstance(value, TransitionCatalog):
        declared = value.catalog_digest
    else:
        declared = str(value.get("catalog_digest") or "")
    calculated = catalog_content_digest(value)
    if declared != calculated:
        raise CatalogIntegrityError(
            f"catalog_digest mismatch: declared={declared!r} calculated={calculated!r}"
        )
