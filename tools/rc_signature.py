"""Detached Ed25519 signature over an Azazel-Fabric release-candidate digest.

``tools/rc_digest.py`` produces the digest half of R1b (the Nexus/Boot program
plan, ``Azazel/docs/roadmaps/nexus-boot-program-plan.md`` §5 R1). This module is
the other half: it verifies that a release owner signed that digest, and it
prints the exact bytes an owner has to sign.

**It cannot sign.** Signing needs the release owner's private key, which is not
in this repository and must never be. ``--signable`` writes the bytes to sign to
stdout; the owner signs them on their own machine and commits the result.

What is signed
--------------

The **canonical bytes the digest covers** -- `digest_payload()` of the manifest
with ``content_digest`` and ``signature_ref`` removed, serialized by
``canonical_contract_bytes``. Not the file as it sits on disk.

That choice follows the digest tool's own design. It excludes ``signature_ref``
because "a locator assigned after signing cannot be covered by the bytes that
were signed" -- which only makes sense if what is signed is the covered payload.
It also makes the signature independent of how the JSON file happens to be
formatted: re-indenting the manifest, or adding the locator after signing,
leaves the signature valid, while changing any byte of the packaged surface
invalidates both the digest and the signature.

File layout
-----------

``release/<tag>.digest.json``      the manifest (written by rc_digest.py)
``release/<tag>.digest.json.sig``  detached signatures, one per line:
                                   ``<key_id>:<hex signature>``
``release/signing-keys.json``      trusted public keys: {"keys": {id: hex}}

The signature file format and the hex-keyed public-key map are Azazel-Knowledge's
(`src/azazel_knowledge/bundle/verify.py`, `manifest.sig`), reused on purpose: an
operator who can verify a Knowledge Lite bundle can verify this without learning
a second convention.

Fail-closed
-----------

No key file, no trusted keys, no signature file, an unknown ``key_id``, or a
signature that does not verify all mean **unsigned**, and ``--check`` exits
non-zero. A digest that merely matches the tree is not a signed digest; R1b asks
for both.

PyNaCl is imported only when a signature is actually checked, and it is not a
package dependency -- this file lives in ``tools/``, outside the installable
surface the digest covers, so nothing a consumer pins is affected.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from azazel_fabric.provisioning_contracts.integrity import (  # noqa: E402
    canonical_contract_bytes,
    digest_payload,
)

DIGEST_FIELD = "content_digest"
SIGNATURE_SUFFIX = ".sig"
KEYS_FILENAME = "signing-keys.json"


class SignatureError(Exception):
    """The digest is not signed by a trusted key. Always fail closed on this."""


def signable_bytes(manifest: dict) -> bytes:
    """Return the exact bytes a release owner signs for this manifest."""

    return canonical_contract_bytes(digest_payload(manifest, digest_field=DIGEST_FIELD))


def load_trusted_keys(keys_path: Path) -> dict[str, str]:
    """Return ``{key_id: hex public key}``; missing or empty is not an error here.

    Emptiness is reported by the caller as "unsigned" rather than raised here,
    so the distinction between "no key is trusted yet" and "a key is trusted and
    the signature is bad" survives into the error message. Both fail; only one
    of them means somebody tampered with something.
    """

    if not keys_path.is_file():
        return {}
    doc = json.loads(keys_path.read_text(encoding="utf-8"))
    keys = doc.get("keys")
    if not isinstance(keys, dict):
        raise SignatureError(f"{keys_path.name}: 'keys' must be an object of id -> hex")
    out: dict[str, str] = {}
    for key_id, hex_key in keys.items():
        if not isinstance(key_id, str) or not key_id.strip():
            raise SignatureError(f"{keys_path.name}: a key id must be a non-empty string")
        if not isinstance(hex_key, str):
            raise SignatureError(f"{keys_path.name}: key {key_id!r} must be a hex string")
        try:
            raw = bytes.fromhex(hex_key)
        except ValueError as exc:
            raise SignatureError(f"{keys_path.name}: key {key_id!r} is not hex: {exc}") from exc
        if len(raw) != 32:
            raise SignatureError(
                f"{keys_path.name}: key {key_id!r} is {len(raw)} bytes; "
                "an Ed25519 public key is 32"
            )
        out[key_id] = hex_key
    return out


def parse_signature_file(text: str) -> list[tuple[str, str]]:
    """Parse ``<key_id>:<hex>`` lines. Blank lines and ``#`` comments are skipped."""

    entries: list[tuple[str, str]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key_id, sep, hex_sig = line.partition(":")
        if not sep or not key_id.strip() or not hex_sig.strip():
            raise SignatureError(f"signature line {lineno} is not '<key_id>:<hex>'")
        entries.append((key_id.strip(), hex_sig.strip()))
    if not entries:
        raise SignatureError("signature file carries no signatures")
    return entries


def verify(manifest_path: Path, *, keys_path: Path | None = None) -> list[str]:
    """Return the key ids that signed this manifest, or raise `SignatureError`.

    A manifest is signed when at least one trusted key verifies it. Extra
    signatures from keys this repository does not trust are ignored rather than
    fatal -- an untrusted signer cannot make a release less signed -- but a
    signature that claims a trusted key and fails to verify is fatal.
    """

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = signable_bytes(manifest)

    sig_path = manifest_path.with_name(manifest_path.name + SIGNATURE_SUFFIX)
    keys_path = keys_path or manifest_path.parent / KEYS_FILENAME
    trusted = load_trusted_keys(keys_path)

    if not trusted:
        raise SignatureError(
            f"no trusted signing key: {keys_path} is absent or lists none. "
            "R1b asks for a signed candidate digest; this one is unsigned."
        )
    if not sig_path.is_file():
        raise SignatureError(
            f"{sig_path.name} is absent, so {manifest_path.name} is unsigned"
        )

    try:
        from nacl.exceptions import BadSignatureError
        from nacl.signing import VerifyKey
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise SignatureError(
            f"PyNaCl is required to verify Ed25519 signatures: {exc}"
        ) from exc

    signed_by: list[str] = []
    for key_id, hex_sig in parse_signature_file(sig_path.read_text(encoding="utf-8")):
        if key_id not in trusted:
            continue  # an untrusted signer is not an error; it is just not evidence
        try:
            signature = bytes.fromhex(hex_sig)
        except ValueError as exc:
            raise SignatureError(f"signature for {key_id!r} is not hex: {exc}") from exc
        try:
            VerifyKey(bytes.fromhex(trusted[key_id])).verify(payload, signature)
        except BadSignatureError as exc:
            raise SignatureError(
                f"signature for trusted key {key_id!r} does not verify "
                f"{manifest_path.name}"
            ) from exc
        signed_by.append(key_id)

    if not signed_by:
        raise SignatureError(
            f"{sig_path.name} carries no signature from a key listed in "
            f"{keys_path.name}"
        )
    return sorted(signed_by)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", type=Path, help="release/<tag>.digest.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="verify the detached signature; non-zero exit means unsigned",
    )
    group.add_argument(
        "--signable",
        action="store_true",
        help="write the bytes to sign to stdout (for the release owner)",
    )
    parser.add_argument(
        "--keys",
        type=Path,
        default=None,
        help=f"trusted public keys (default: <manifest dir>/{KEYS_FILENAME})",
    )
    args = parser.parse_args(argv)

    if args.signable:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        sys.stdout.buffer.write(signable_bytes(manifest))
        return 0

    try:
        signed_by = verify(args.manifest, keys_path=args.keys)
    except SignatureError as exc:
        print(f"UNSIGNED: {exc}", file=sys.stderr)
        return 1
    print(f"{args.manifest.name} signed by: {', '.join(signed_by)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
