# R1b: signing a release-candidate digest

R1b is "a signed release-candidate digest" (`Azazel/docs/roadmaps/nexus-boot-program-plan.md`
§5 R1). It has two halves, and only one of them is a repository operation.

| Half | Who | State |
|---|---|---|
| The digest — what bytes the candidate is made of | anyone, reproducibly | **done** for `v0.9.0rc1` … `v0.9.0rc4` |
| The detached signature — who stands behind them | the release owner, with a private key | **done** for `v0.9.0rc1` … `v0.9.0rc4` |

Neither half signs the git tag; see *What the signature covers* below.

`release/v0.9.0rc2.digest.json.sig` carries the release owner's signature and
`release/signing-keys.json` trusts the key that made it:

```bash
python3 tools/rc_signature.py release/v0.9.0rc2.digest.json --check
# v0.9.0rc2.digest.json signed by: release-owner
```

`v0.9.0rc1`'s digest was signed afterwards with the same key, for the same
reason it could not simply be ignored: Azazel-Boot pins that tag, and a
consumer pinning a candidate whose bytes nobody had stood behind is the gap
R1b exists to close.

```bash
python3 tools/rc_signature.py release/v0.9.0rc1.digest.json --check
# v0.9.0rc1.digest.json signed by: release-owner
```

The digests for `v0.9.0rc3`, `v0.9.0rc4` and `v0.9.0rc5` were signed the same
way, each before its tag existed.

```bash
python3 tools/rc_signature.py release/v0.9.0rc4.digest.json --check
# v0.9.0rc4.digest.json signed by: release-owner
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
| `v0.9.0rc4` | **7915** | `b02ee97bf7b7783567b070129144b1f84987384873c96eb34ff7f4105f33101d` |
| `v0.9.0rc5` | **7915** | `c183eb92dfd706cc2bcf69bad37641588f440c488b0264564c7a8e044647cc9d` |

`rc2` through `rc5` cover the same 66 files, so four payloads in a row are the
same length and only their contents differ. A size check cannot tell any of
them apart; the digest can. Signing `rc2`'s payload while believing it is
`rc4`'s would produce a signature that verifies — against the wrong candidate.

Four candidates at 7915 bytes is not a coincidence worth noting once. It is
this repository's standing condition: the file set has been stable across all
of them, so the length check is useless by construction and will stay that
way. Check the digest — the tagging chain for `rc5` was built around exactly
that check, and it is what confirmed the signer's tree matched.

## A candidate signs before its tag exists, not after

`rc1` and `rc2` were signed after their tags were cut, which is why step 2
below checks the digest against the tag. `rc3` was prepared the other way
round and `rc4` followed it: the manifest is signed on the branch, the branch
merges, and the tag is then cut at the merge commit.

One consequence is worth stating, because it was nearly got wrong while
preparing `rc4`. The manifest and the signature belong in the **same commit**.
Committing the manifest first — a claim that this tree is what the tag records
— and the signature afterwards recreates, on the branch, exactly the window
this order exists to close. `rc4`'s manifest was generated, reverted, and
regenerated once the signature existed, which costs nothing: the manifest is
derived from `src/` and `pyproject.toml`, so it is reproducible at any time
and the release owner regenerates it independently to sign it. That
independent regeneration is also the cross-check — if the signer's payload
digest does not match the one they were told to expect, the trees differ and
nothing should be signed.

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

## What the signature covers, and what it does not

**The signed thing is the release digest, never the git tag.** Say "the digest
is signed", not "the tag is signed": every published tag in this repository is
an unsigned annotated tag, which `git cat-file -p v0.9.0rc4` and GitHub's own
tag view both report as `unsigned`.

| Object | Signed? | What it establishes |
|---|---|---|
| `release/<tag>.digest.json` | **yes**, Ed25519 detached | the release owner stands behind these bytes of `src/` and `pyproject.toml` |
| the git tag `<tag>` | **no** | which commit the name resolves to, and nothing about who chose it |
| the commit the tag points at | **no** | — |

The distinction is not pedantry. It decides what a consumer may conclude from
`pip install ...@v0.9.0rc4` succeeding: that they fetched whatever that tag
currently names. Whether those bytes are the ones the release owner signed is a
**separate check** -- check out the tag and run `tools/rc_digest.py --check`
followed by the signature verification below. Both halves were needed to catch
`v0.9.0rc4` being cut at the wrong commit twice: the tag resolved fine, the
code was right, and the digest check is what said no.

Making the tag itself a trust boundary would need signed annotated tags from
the next candidate onward, which is [Fabric#56](https://github.com/01rabbit/Azazel-Fabric/issues/56)
and not something this document claims today.

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

## Where the key lives

**Outside this working tree, always.** The commands below use
`$AZAZEL_SIGNING_KEY`, an absolute path to a directory git has no reason to
look at:

```bash
mkdir -p ~/.azazel-signing && chmod 700 ~/.azazel-signing
export AZAZEL_SIGNING_KEY=~/.azazel-signing/fabric-release.key
```

This is the layer that matters, and the reason is mechanical. `.gitignore`
stops `git stash -u`; it does **not** stop `git stash -a`, `git clean -x`, an
editor's project-wide backup, or an archive of the working directory. A key
that is not in the working tree is out of reach of all of them, including the
ones nobody has thought of yet.

`tests/test_release_signature.py::test_the_procedure_keeps_the_key_outside_the_working_tree`
checks that this document's own commands read the key through that variable
rather than from a bare filename in the current directory. A procedure that
tells a signer to create the key where they are working is the procedure that
produced the incident below, and prose asking them not to is not a control.

**Never run `git stash -u` or `git stash -a` in this repository at all.**

`-u` takes untracked files. `-a` takes ignored ones too. Preparing
`v0.9.0rc4`, a `git stash -u` here — run to move a version bump out of the way
so a checkout could proceed — pulled the signing key into a stash entry, which
put a private key inside `.git`.

The objects were dropped and pruned. **That is removal from git's object
store, not a guarantee the key is unrecoverable**: backups, shell history,
swap, unallocated blocks and any copy of the directory made during the window
are all outside what `gc` touches. The key is treated as possibly exposed,
which is what #61 records and why signing with it is paused.

Use `git -c stash.showIncludeUntracked=false` habits aside — the working
instruction is simpler: move the change to a branch, or commit it. There is no
version of this procedure that needs a stash.

It is not possible now: `.gitignore` covers the key and the scratch files this
procedure creates, and `git stash -u` skips ignored files.
`tests/test_release_signature.py::test_gitignore_covers_every_file_the_signing_procedure_creates`
reads the filenames out of *this document* and fails if any of them is
uncovered, so a procedure that starts creating a new scratch file cannot leave
it exposed. `-a` overrides the ignore list, which is why it is named here as
well: that one has no mechanical guard and never will.

The instruction "PRIVATE — never commit" was already in this document when it
happened. A rule written in prose is a rule git does not apply.

### 1. Create the signing key (once)

Route A (PyNaCl):

```bash
./.venv-signing/bin/python - <<'PY'
from nacl.signing import SigningKey
key = SigningKey.generate()
import os
key_path = os.environ["AZAZEL_SIGNING_KEY"]   # PRIVATE — outside the repo
open(key_path, "wb").write(bytes(key))
print("public key:", key.verify_key.encode().hex())
PY
chmod 600 "$AZAZEL_SIGNING_KEY"
```

Route B (OpenSSL 3.x) — the key is a PEM here rather than 32 raw bytes, which
changes nothing for this repository: only the public key is ever published, and
it comes out as the same 64 hex characters either way.

```bash
openssl genpkey -algorithm ed25519 -out "$AZAZEL_SIGNING_KEY"   # PRIVATE, outside the repo
chmod 600 "$AZAZEL_SIGNING_KEY"
openssl pkey -in "$AZAZEL_SIGNING_KEY" -pubout -outform DER \
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
import os
key = SigningKey(open(os.environ["AZAZEL_SIGNING_KEY"], "rb").read())
sig = key.sign(open("candidate.bin", "rb").read()).signature
print("release-owner:" + sig.hex())
PY
```

Route B (OpenSSL 3.x):

```bash
openssl pkeyutl -sign -inkey "$AZAZEL_SIGNING_KEY" -rawin \
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

**`--check` needs PyNaCl, and route B does not install it.** That is not a
detail: a release owner who signed with OpenSSL alone could not verify their
own signature, and it stopped the `v0.9.0rc4` tagging chain mid-way with
`UNSIGNED: PyNaCl is required to verify Ed25519 signatures`. The two halves of
this document offered a choice for signing and no choice for verifying.

The OpenSSL equivalent, which needs no PyNaCl. The public key is turned into
a DER `SubjectPublicKeyInfo` by prefixing the 32 raw bytes with the twelve
fixed bytes Ed25519's encoding always has:

```bash
python3 tools/rc_signature.py release/v0.9.0rc4.digest.json --signable > /tmp/rc4.bin
python3 -c "
import binascii, json, pathlib
key = json.load(open('release/signing-keys.json'))['keys']['release-owner']
sig = [l.split(':',1)[1].strip() for l in open('release/v0.9.0rc4.digest.json.sig')
       if l.startswith('release-owner:')][0]
pathlib.Path('/tmp/rc4.pub.der').write_bytes(binascii.unhexlify('302a300506032b6570032100' + key))
pathlib.Path('/tmp/rc4.sig.bin').write_bytes(binascii.unhexlify(sig))
"
openssl pkeyutl -verify -pubin -inkey /tmp/rc4.pub.der -keyform DER \
  -rawin -in /tmp/rc4.bin -sigfile /tmp/rc4.sig.bin
# Signature Verified Successfully
```

Only the hex decoding uses Python, and only the standard library; the
verification itself is OpenSSL's. This was checked in both directions before
being written down — altering one byte of the payload, and flipping one bit of
the signature, each produce `Signature Verification Failure` and exit 1. A
verification command that has only ever been seen to succeed is not known to
be a verification.

`--signable` still needs Fabric's own dependencies, which the signing machine
already has: producing `candidate.bin` in step 2 is the same command.

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
