# R1b: signing a release-candidate digest

R1b is "a signed release-candidate digest" (`Azazel/docs/roadmaps/nexus-boot-program-plan.md`
§5 R1). It has two halves, and only one of them is a repository operation.

| Half | Who | State |
|---|---|---|
| The digest — what bytes the candidate is made of | anyone, reproducibly | **done** for `v0.9.0rc1` and `v0.9.0rc2` |
| The detached signature — who stands behind them | the release owner, with a private key | **not done for any release** |

`release/signing-keys.json` lists no key, so `tools/rc_signature.py --check`
reports every published candidate as unsigned. That is the accurate state, not
a gap in the tooling.

## Algorithm

**Ed25519**, detached, hex-encoded.

This matches Azazel-Knowledge, which signs its Lite bundles the same way
(`src/azazel_knowledge/bundle/verify.py`): the same `<key_id>:<hex>` line
format and the same hex public-key map, so one convention covers both products.

The series' other signing helper, `deception_contracts.decision_signing`, is
**HMAC-SHA256 and must not be used here.** It is symmetric: anyone who can
verify can also forge. That is right for a transport signature between two
parties who already share a secret, and wrong for a release signature, whose
whole purpose is that a consumer who has never met the signer can check it.

## What is signed

The **canonical bytes the digest covers** — not the file on disk:

```bash
python tools/rc_signature.py release/v0.9.0rc2.digest.json --signable > candidate.bin
```

For `v0.9.0rc2` that is 7915 bytes whose SHA-256 is exactly the manifest's own
`content_digest`, which is the property that keeps the two halves of R1b about
the same thing:

```bash
sha256sum candidate.bin
# 3876b6d1d103b4832274a91e9ec12e6697fab095723b17c940d68af3207961ae
python -c "import json;print(json.load(open('release/v0.9.0rc2.digest.json'))['content_digest'])"
# sha256:3876b6d1d103b4832274a91e9ec12e6697fab095723b17c940d68af3207961ae
```

Signing the payload rather than the file means re-indenting the manifest, or
adding a `signature_ref` locator after signing, leaves the signature valid —
while changing one byte of `src/` or `pyproject.toml` invalidates both the
digest and the signature. `rc_digest.py` excludes `signature_ref` from the
digest for the same reason: "a locator assigned after signing cannot be covered
by the bytes that were signed".

## Procedure

Steps 1–3 happen on the release owner's machine, with a key that must never
enter this repository. Steps 4–6 are ordinary repository work.

### 1. Create the signing key (once)

```bash
python - <<'PY'
from nacl.signing import SigningKey
key = SigningKey.generate()
open("fabric-release.key", "wb").write(bytes(key))   # PRIVATE — never commit
print("public key:", key.verify_key.encode().hex())
PY
chmod 600 fabric-release.key
```

Keep the private key off shared machines and out of CI. Nothing in this
repository or its workflows needs it; only the 64-hex public key is published.

### 2. Get the bytes to sign

```bash
git checkout v0.9.0rc2
python tools/rc_digest.py --check release/v0.9.0rc2.digest.json   # digest still describes the tag
python tools/rc_signature.py release/v0.9.0rc2.digest.json --signable > candidate.bin
```

Verify the digest before signing. Signing bytes you have not checked is signing
whatever happens to be in the working tree.

### 3. Sign

```bash
python - <<'PY'
from nacl.signing import SigningKey
key = SigningKey(open("fabric-release.key", "rb").read())
sig = key.sign(open("candidate.bin", "rb").read()).signature
print("release-owner:" + sig.hex())
PY
```

### 4. Commit the public key

`release/signing-keys.json`:

```json
{ "keys": { "release-owner": "<64 hex chars from step 1>" } }
```

The id is free-form and is what the `.sig` file names. Several keys may be
trusted at once, which is how a rotation happens without a flag day.

### 5. Commit the signature

`release/v0.9.0rc2.digest.json.sig`, one `<key_id>:<hex>` line per signer.
Blank lines and `#` comments are allowed.

### 6. Verify

```bash
python tools/rc_signature.py release/v0.9.0rc2.digest.json --check
# v0.9.0rc2.digest.json signed by: release-owner
```

`tests/test_release_signature.py` then fails, on purpose: it asserts this
repository trusts no key and that the published candidates report as unsigned.
Those two tests are the record of the current state, and updating them is the
deliberate act of saying the state changed.

## What the checks do

| Situation | Result |
|---|---|
| No `signing-keys.json`, or it lists no key | unsigned, exit 1 |
| No `.sig` file | unsigned, exit 1 |
| `.sig` names only keys this repository does not trust | unsigned, exit 1 |
| A signature claims a trusted key and fails to verify | **error**, exit 1 |
| A trusted key verifies; other signers also present | signed (extra signers ignored) |
| The manifest was edited after signing | error, exit 1 |

A malformed `signing-keys.json` is refused rather than read as "no keys": both
fail, but only one of them means somebody should look at the file.

`release.yml` runs `--check` on every tag. A **stable** `vX.Y.Z` tag fails
without a verified signature. A candidate is allowed through with a warning,
because `v0.9.0rc1` and `v0.9.0rc2` were published before this procedure
existed and re-running their workflow must not retroactively fail.

## Why PyNaCl is not a dependency

`tools/` is outside the installable surface the digest covers (`src/` plus
`pyproject.toml`), so the verifier adds nothing to what a consumer receives by
pinning the tag. CI installs PyNaCl alongside the test extra so the signature
guards actually run — a skipped guard reports success.

## What this does not do

A signature proves that the release owner signed these bytes. It does not make
the contracts authoritative, does not grant any runtime or decision authority,
and is not R1c: the stable tag additionally waits on per-family downstream
adoption, recorded in
[release compatibility](release-compatibility.md#contract-family-adoption-and-the-r1c-gate).
