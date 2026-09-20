# R1b: signing a release-candidate digest

R1b is "a signed release-candidate digest" (`Azazel/docs/roadmaps/nexus-boot-program-plan.md`
§5 R1). It has two halves, and only one of them is a repository operation.

| Half | Who | State |
|---|---|---|
| The digest — what bytes the candidate is made of | anyone, reproducibly | **done** for `v0.9.0rc1` and `v0.9.0rc2` |
| The detached signature — who stands behind them | the release owner, with a private key | **done for `v0.9.0rc1` and `v0.9.0rc2`** |

`release/v0.9.0rc2.digest.json.sig` carries the release owner's signature and
`release/signing-keys.json` trusts the key that made it:

```bash
python3 tools/rc_signature.py release/v0.9.0rc2.digest.json --check
# v0.9.0rc2.digest.json signed by: release-owner
```

`v0.9.0rc1` was signed afterwards with the same key, for the same reason it
could not simply be ignored: Azazel-Boot pins it, and a consumer pinning a
candidate nobody had stood behind is the gap R1b exists to close.

```bash
python3 tools/rc_signature.py release/v0.9.0rc1.digest.json --check
# v0.9.0rc1.digest.json signed by: release-owner
```

The steps below remain the procedure for the next candidate and for the
stable tag.

**Verify the payload's sha256, not its size.** Each candidate's payload
differs, but not always in length:

| Candidate | payload bytes | payload sha256 |
|---|---|---|
| `v0.9.0rc1` | 7071 | `cdfb735c002eb26ef5e0f31ea617b2576a3b9a4a938f04b27f6a353a4f1b06fe` |
| `v0.9.0rc2` | 7915 | `3876b6d1d103b4832274a91e9ec12e6697fab095723b17c940d68af3207961ae` |
| `v0.9.0rc3` | **7915** | `0210f96783248aa64f392cd73c987fa119aa0d7918589f393d4f5a0a0f855d8e` |

`rc2` and `rc3` cover the same 66 files, so their payloads are the same length
and only their contents differ. A size check cannot tell them apart; the
digest can. Signing `rc2`'s payload while believing it is `rc3`'s would produce
a signature that verifies — against the wrong candidate.

## `v0.9.0rc3` signs before its tag exists, not after

`rc1` and `rc2` were signed after their tags were cut, which is why step 2
below checks the digest against the tag. `rc3` is being prepared the other way
round: the manifest is signed on the branch, the branch merges, and the tag is
then cut at the merge commit.

That is the better order and it is worth saying why. Signing after the tag
means a window in which a published tag has no signature, which is exactly the
gap `rc1` sat in — Azazel-Boot pinned it while nobody had stood behind it.
Signing first closes the window: the tag, when it appears, already carries its
signature.

It changes one thing in step 2. There is no tag to check against, so
`tools/rc_digest.py --check` runs on the branch — the tree that will *become*
the tag. The manifest covers `src/` and `pyproject.toml` only, so any further
documentation change before the tag leaves it valid, and `--check` at the tag
afterwards must still pass. If it does not, the tag was cut from a different
tree than the one that was signed, and the signature belongs to neither.

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

## Prerequisites on the signing machine

The signing steps need an Ed25519 implementation. Either route below works, and
both were rehearsed end to end against `tools/rc_signature.py`; pick whichever
is less trouble on the machine that holds the key.

### Route A — PyNaCl in a throwaway virtualenv (recommended)

Matches the verifier and Azazel-Knowledge's tooling, and works wherever Python
does. A plain `pip install pynacl` often fails on a current macOS or Linux with
`externally-managed-environment` (PEP 668), so use a virtualenv:

```bash
python3 -m venv .venv-signing
./.venv-signing/bin/pip install pynacl
./.venv-signing/bin/python -c "import nacl; print(nacl.__version__)"
```

Then run the signing steps with `./.venv-signing/bin/python` in place of
`python`. `.venv-signing/` is scratch — delete it afterwards; the key is the
thing worth keeping, and it is a separate file.

### Route B — OpenSSL 3.x, no Python dependency

OpenSSL 3 produces a raw 64-byte Ed25519 signature, which is exactly the
encoding `tools/rc_signature.py` expects. Verified: a signature made this way
verifies under the checker with no PyNaCl on the signing machine at all.

**macOS ships LibreSSL, which cannot do this.** Check first:

```bash
openssl version
# OpenSSL 3.x            -> usable
# LibreSSL 2.8.3 (macOS) -> not usable; brew install openssl@3, then use
#                           /opt/homebrew/opt/openssl@3/bin/openssl below
```

The commands for this route are given inline with each step.

## Procedure

Steps 1–3 happen on the release owner's machine, with a key that must never
enter this repository. Steps 4–6 are ordinary repository work.

### 1. Create the signing key (once)

Route A (PyNaCl):

```bash
./.venv-signing/bin/python - <<'PY'
from nacl.signing import SigningKey
key = SigningKey.generate()
open("fabric-release.key", "wb").write(bytes(key))   # PRIVATE — never commit
print("public key:", key.verify_key.encode().hex())
PY
chmod 600 fabric-release.key
```

Route B (OpenSSL 3.x) — the key is a PEM here rather than 32 raw bytes, which
changes nothing for this repository: only the public key is ever published, and
it comes out as the same 64 hex characters either way.

```bash
openssl genpkey -algorithm ed25519 -out fabric-release.key   # PRIVATE
chmod 600 fabric-release.key
openssl pkey -in fabric-release.key -pubout -outform DER \
  | tail -c 32 | od -An -tx1 -v | tr -d ' \n'; echo
```

(The public key is the last 32 bytes of the DER `SubjectPublicKeyInfo`.)

Keep the private key off shared machines and out of CI. Nothing in this
repository or its workflows needs it; only the 64-hex public key is published.

### 2. Get the bytes to sign

Two commands on two different refs, and the order matters.

**`tools/rc_signature.py` does not exist at `v0.9.0rc2`.** The tag was cut
before the signing tooling was written, and a tag is not rewritten to acquire
it. Running `--signable` from a checkout of the tag produces an empty
`candidate.bin`, and signing that would sign nothing.

```bash
# 1. At the tag: confirm the digest still describes what the tag ships.
git checkout v0.9.0rc2
python3 tools/rc_digest.py --check release/v0.9.0rc2.digest.json
# release/v0.9.0rc2.digest.json matches: sha256:3876b6d1...961ae

# 2. Back on a ref that carries the tool: produce the bytes to sign.
git switch main && git pull
python3 tools/rc_signature.py release/v0.9.0rc2.digest.json --signable > candidate.bin
```

Step 2 is correct from `main` because `--signable` reads the **manifest file**,
not the working tree, and `release/v0.9.0rc2.digest.json` is byte-identical on
`main` and at the tag. Step 1 is what ties the manifest to the tag's actual
contents, and it has to happen at the tag to mean anything.

Neither command needs PyNaCl. Check the result before signing — for
`v0.9.0rc2` it is 7915 bytes:

```bash
shasum -a 256 candidate.bin   # macOS; sha256sum elsewhere
# 3876b6d1d103b4832274a91e9ec12e6697fab095723b17c940d68af3207961ae
```

An empty file hashes to `e3b0c442...b855`. If you see that, `--signable` wrote
nothing — you are on a ref without the tool. **Do not sign it.**

Verify the digest before signing. Signing bytes you have not checked is signing
whatever happens to be in the working tree.

### 3. Sign

Route A (PyNaCl):

```bash
./.venv-signing/bin/python - <<'PY'
from nacl.signing import SigningKey
key = SigningKey(open("fabric-release.key", "rb").read())
sig = key.sign(open("candidate.bin", "rb").read()).signature
print("release-owner:" + sig.hex())
PY
```

Route B (OpenSSL 3.x):

```bash
openssl pkeyutl -sign -inkey fabric-release.key -rawin \
  -in candidate.bin -out candidate.sig
printf 'release-owner:%s\n' "$(od -An -tx1 -v candidate.sig | tr -d ' \n')"
```

`-rawin` is what makes this Ed25519 over the message itself rather than over a
pre-hash, and it is why the output verifies under the checker unchanged.

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
