"""R1b is a *signed* candidate digest, and both published candidates carry one.

`tools/rc_digest.py` produces the digest; `tools/rc_signature.py` is the half
that says a release owner stood behind it. The program plan
(`Azazel/docs/roadmaps/nexus-boot-program-plan.md` §5 R1) asks for both.

These tests hold two things: that the signatures on `v0.9.0rc1` and
`v0.9.0rc2` are real, distinct, and each over its own candidate's bytes, and
that everything the verifier should refuse is still refused.
A verifier that quietly passes when nothing is signed is worse than no
verifier -- it converts a missing signature into a green check -- so most of
what follows is about the refusals.

The happy path is exercised with a throwaway keypair generated in the test, not
with a committed key. A private key that can sign a real release must not exist
in this repository, and a fixture key that can would be exactly that.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO_ROOT / "release"

sys.path.insert(0, str(REPO_ROOT / "tools"))

from rc_signature import (  # noqa: E402
    KEYS_FILENAME,
    SIGNATURE_SUFFIX,
    SignatureError,
    load_trusted_keys,
    parse_signature_file,
    signable_bytes,
    verify,
)

nacl_signing = pytest.importorskip(
    "nacl.signing",
    reason="PyNaCl verifies the Ed25519 signatures; CI installs it alongside the test extra",
)


@pytest.fixture
def manifest() -> dict:
    """A real published manifest, so the shapes under test are the real ones."""

    return json.loads((RELEASE_DIR / "v0.9.0rc2.digest.json").read_text(encoding="utf-8"))


@pytest.fixture
def signed(tmp_path: Path, manifest: dict):
    """A manifest, a throwaway key trusted for it, and a valid signature."""

    key = nacl_signing.SigningKey.generate()
    manifest_path = tmp_path / "v9.9.9.digest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    signature = key.sign(signable_bytes(manifest)).signature
    (tmp_path / (manifest_path.name + SIGNATURE_SUFFIX)).write_text(
        f"release-owner:{signature.hex()}\n", encoding="utf-8"
    )
    (tmp_path / KEYS_FILENAME).write_text(
        json.dumps({"keys": {"release-owner": key.verify_key.encode().hex()}}),
        encoding="utf-8",
    )
    return manifest_path, key


# --------------------------------------------------------------------------
# what gets signed
# --------------------------------------------------------------------------


def test_the_signature_covers_exactly_what_the_digest_covers(manifest):
    """The two halves of R1b must be about the same bytes.

    If the signable payload and the digested payload could differ, a release
    could carry a valid signature over something other than the surface the
    digest names, and neither check would notice.
    """

    digested = "sha256:" + hashlib.sha256(signable_bytes(manifest)).hexdigest()
    assert digested == manifest["content_digest"]


def test_signing_cannot_change_the_thing_it_signs(manifest):
    """Adding the locator after signing must leave the signature valid.

    `rc_digest.py` excludes `signature_ref` because "a locator assigned after
    signing cannot be covered by the bytes that were signed". That is only
    true if the signable payload ignores it too.
    """

    before = signable_bytes(manifest)
    after = signable_bytes({**manifest, "signature_ref": "release/v0.9.0rc2.digest.json.sig"})
    assert before == after


def test_the_signature_files_are_outside_the_packaged_surface():
    """A signature must not perturb the digest, or signing becomes circular.

    `rc_digest.py` covers `src/` and `pyproject.toml`. `release/` is neither,
    so committing a `.sig` or a key cannot change the digest being signed.
    """

    from rc_digest import COVERED_FILES, COVERED_ROOTS

    assert COVERED_ROOTS == ("src",)
    assert COVERED_FILES == ("pyproject.toml",)
    for path in (RELEASE_DIR / KEYS_FILENAME, RELEASE_DIR / "v0.9.0rc2.digest.json.sig"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        assert not rel.startswith(COVERED_ROOTS)
        assert rel not in COVERED_FILES


# --------------------------------------------------------------------------
# the state this repository is actually in
# --------------------------------------------------------------------------


#: The keys this repository trusts, written out rather than read from the
#: file. A trusted signing key is not something that should be able to appear,
#: change, or vanish without a test saying so.
EXPECTED_TRUSTED_KEYS = {
    "release-owner": "0d572c5abb49ebb09566a68a4143ed867d445e4f91b80ec69f6d02d479ef17bf",
}


def test_the_trusted_key_set_is_exactly_what_it_should_be():
    """Pinned, not merely non-empty.

    This test used to assert the opposite -- that no key was trusted -- and it
    failed the day the release owner's key landed, which was the point. It
    now records the state that replaced it, and it will fail again on any
    further change.
    """

    assert load_trusted_keys(RELEASE_DIR / KEYS_FILENAME) == EXPECTED_TRUSTED_KEYS


#: Every published candidate, written out rather than globbed. A candidate
#: that lost its signature, or one added without one, has to be visible here.
SIGNED_CANDIDATES = ("v0.9.0rc1", "v0.9.0rc2")


def test_this_file_covers_every_published_candidate():
    """Globbing `release/*.digest.json` would make a new unsigned candidate
    invisible: it would simply not be in the list. The list is written out, so
    adding a candidate means deciding, in this file, whether it is signed."""

    published = {p.name[: -len(".digest.json")] for p in RELEASE_DIR.glob("*.digest.json")}
    assert published == set(SIGNED_CANDIDATES)


@pytest.mark.parametrize("candidate", SIGNED_CANDIDATES)
def test_the_candidate_is_signed(candidate):
    """R1b's signature half is done for both published candidates.

    `rc1` was signed after `rc2`, with the same key: it predates the procedure
    but Azazel-Boot pins it, so leaving it unsigned would have meant a
    consumer pinning a candidate nobody had stood behind.
    """

    assert verify(RELEASE_DIR / f"{candidate}.digest.json") == ["release-owner"]


@pytest.mark.parametrize("candidate", SIGNED_CANDIDATES)
def test_the_signature_is_over_the_digest_that_tag_ships(candidate):
    """Signed, and signed over the right thing.

    `verify()` returning a key id says a trusted key signed *something this
    file derived*. This says what that something was: the canonical bytes
    whose SHA-256 is the manifest's own `content_digest`, which is the number
    `tools/rc_digest.py --check` compares against the tag's tree.
    """

    manifest = json.loads(
        (RELEASE_DIR / f"{candidate}.digest.json").read_text(encoding="utf-8")
    )
    signed = hashlib.sha256(signable_bytes(manifest)).hexdigest()
    assert manifest["content_digest"] == f"sha256:{signed}"


def test_each_signature_belongs_to_its_own_candidate():
    """Two candidates, two signatures, and neither covers the other.

    Both are signed by the same key over payloads that differ only in
    content, so a copied or swapped `.sig` file would still parse, still name
    a trusted key, and still look right in a diff. What it would not do is
    verify -- and that is the only thing that distinguishes a real signature
    from a plausible one.
    """

    from nacl.exceptions import BadSignatureError

    key = nacl_signing.VerifyKey(bytes.fromhex(EXPECTED_TRUSTED_KEYS["release-owner"]))
    payloads, signatures = {}, {}
    for candidate in SIGNED_CANDIDATES:
        manifest = json.loads(
            (RELEASE_DIR / f"{candidate}.digest.json").read_text(encoding="utf-8")
        )
        payloads[candidate] = signable_bytes(manifest)
        sig_path = RELEASE_DIR / f"{candidate}.digest.json{SIGNATURE_SUFFIX}"
        (_, hex_sig), = parse_signature_file(sig_path.read_text(encoding="utf-8"))
        signatures[candidate] = bytes.fromhex(hex_sig)

    assert len(set(payloads.values())) == len(SIGNED_CANDIDATES), "payloads collide"
    assert len(set(signatures.values())) == len(SIGNED_CANDIDATES), "the same signature twice"

    for signed_candidate, signature in signatures.items():
        for other, payload in payloads.items():
            if other == signed_candidate:
                key.verify(payload, signature)  # must not raise
                continue
            with pytest.raises(BadSignatureError):
                key.verify(payload, signature)


# --------------------------------------------------------------------------
# fail-closed
# --------------------------------------------------------------------------


def test_a_valid_signature_from_a_trusted_key_verifies(signed):
    manifest_path, _ = signed
    assert verify(manifest_path) == ["release-owner"]


def test_a_tampered_manifest_no_longer_verifies(signed):
    """The point of the whole exercise."""

    manifest_path, _ = signed
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    doc["files"]["pyproject.toml"] = "sha256:" + "0" * 64
    manifest_path.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(SignatureError, match="does not verify"):
        verify(manifest_path)


def test_an_untrusted_signer_cannot_make_a_release_look_signed(signed, tmp_path):
    manifest_path, _ = signed
    intruder = nacl_signing.SigningKey.generate()
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    (tmp_path / (manifest_path.name + SIGNATURE_SUFFIX)).write_text(
        f"somebody-else:{intruder.sign(signable_bytes(doc)).signature.hex()}\n",
        encoding="utf-8",
    )
    with pytest.raises(SignatureError, match="no signature from a key listed"):
        verify(manifest_path)


def test_an_untrusted_signature_beside_a_trusted_one_is_ignored(signed, tmp_path):
    """Extra signers are not evidence, but they are not sabotage either."""

    manifest_path, key = signed
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = signable_bytes(doc)
    intruder = nacl_signing.SigningKey.generate()
    (tmp_path / (manifest_path.name + SIGNATURE_SUFFIX)).write_text(
        f"somebody-else:{intruder.sign(payload).signature.hex()}\n"
        f"release-owner:{key.sign(payload).signature.hex()}\n",
        encoding="utf-8",
    )
    assert verify(manifest_path) == ["release-owner"]


def test_a_forged_signature_claiming_a_trusted_key_is_fatal(signed, tmp_path):
    """Claiming the owner's id and failing to verify is tampering, not noise."""

    manifest_path, _ = signed
    intruder = nacl_signing.SigningKey.generate()
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    (tmp_path / (manifest_path.name + SIGNATURE_SUFFIX)).write_text(
        f"release-owner:{intruder.sign(signable_bytes(doc)).signature.hex()}\n",
        encoding="utf-8",
    )
    with pytest.raises(SignatureError, match="does not verify"):
        verify(manifest_path)


def test_a_missing_signature_file_is_unsigned(signed, tmp_path):
    manifest_path, _ = signed
    (tmp_path / (manifest_path.name + SIGNATURE_SUFFIX)).unlink()
    with pytest.raises(SignatureError, match="unsigned"):
        verify(manifest_path)


@pytest.mark.parametrize(
    "content",
    ["", "\n\n", "# only a comment\n", "no-colon-here\n", "missing-sig:\n", ":only-a-sig\n"],
)
def test_an_unusable_signature_file_is_refused(signed, tmp_path, content):
    manifest_path, _ = signed
    (tmp_path / (manifest_path.name + SIGNATURE_SUFFIX)).write_text(content, encoding="utf-8")
    with pytest.raises(SignatureError):
        verify(manifest_path)


def test_comments_and_blank_lines_are_allowed_beside_a_real_signature():
    parsed = parse_signature_file("# owner key, rotated 2026-01-01\n\nowner:abcd\n")
    assert parsed == [("owner", "abcd")]


@pytest.mark.parametrize(
    ("keys_doc", "match"),
    [
        ({"keys": []}, "must be an object"),
        ({"keys": {"owner": "nothex!!"}}, "not hex"),
        ({"keys": {"owner": "aabb"}}, "an Ed25519 public key is 32"),
        ({"keys": {"": "00" * 32}}, "non-empty string"),
        ({"keys": {"owner": 7}}, "hex string"),
    ],
)
def test_a_malformed_key_file_is_refused_rather_than_ignored(tmp_path, keys_doc, match):
    """A key file that cannot be read must not silently become "no keys".

    Both end in a failed verification, but only one of them means somebody
    should look at the file.
    """

    keys_path = tmp_path / KEYS_FILENAME
    keys_path.write_text(json.dumps(keys_doc), encoding="utf-8")
    with pytest.raises(SignatureError, match=match):
        load_trusted_keys(keys_path)


# --------------------------------------------------------------------------
# the procedure document has to describe this repository, not a past one
# --------------------------------------------------------------------------


DOC = REPO_ROOT / "docs" / "release-signing.md"


def test_the_documented_checksum_is_the_one_a_signer_would_see(manifest):
    """`docs/release-signing.md` tells the owner what `candidate.bin` must hash to.

    That number is the last thing standing between the owner and a signature
    over the wrong bytes, and it earned its place: a first attempt at the
    procedure produced an empty `candidate.bin`, and this check is what caught
    it before anything was signed. A stale number would have waved it through.
    """

    import re

    expected = hashlib.sha256(signable_bytes(manifest)).hexdigest()
    text = DOC.read_text(encoding="utf-8")

    # Every full checksum in the document, not just one of them. The number
    # appears in several places, and `expected in text` passes while the
    # others say something else -- a partial update is exactly how a document
    # ends up disagreeing with itself.
    shown = set(re.findall(r"\b[0-9a-f]{64}\b", text))
    assert shown, "docs/release-signing.md shows no checksum at all"
    assert shown == {expected}, (
        f"docs/release-signing.md shows {sorted(shown - {expected})}; "
        f"`--signable` now produces {expected} for release/v0.9.0rc2.digest.json"
    )


def test_the_document_warns_about_the_empty_file(manifest):
    """The failure mode that actually happened, named with its hash.

    `tools/rc_signature.py` does not exist at the `v0.9.0rc2` tag, so running
    `--signable` from a checkout of the tag writes nothing. Signing an empty
    file produces a signature that verifies — over nothing at all — so this is
    a case the procedure has to name rather than leave to be rediscovered.
    """

    empty = hashlib.sha256(b"").hexdigest()
    assert empty.startswith("e3b0c442")
    text = DOC.read_text(encoding="utf-8")
    assert "e3b0c442" in text, "the empty-file hash is not called out in the procedure"
    assert "Do not sign it" in text


def test_the_signing_tool_is_absent_from_the_tag_the_procedure_signs():
    """Pins the reason step 2 needs two refs.

    If a future tag ever ships the tool, this fails and the procedure can be
    simplified back to a single checkout — deliberately, rather than by
    someone assuming it was always fine.
    """

    import subprocess

    present = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "cat-file", "-e", "v0.9.0rc2:tools/rc_signature.py"],
        capture_output=True,
    )
    assert present.returncode != 0, (
        "v0.9.0rc2 now carries tools/rc_signature.py; step 2 of "
        "docs/release-signing.md no longer needs to switch refs"
    )
