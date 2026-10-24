# ADR-0001: Ownership and authority of the external-security contracts

- **Status:** Accepted — **experimental** family (Fabric#23 program decision)
- **Date:** 2026-10-24
- **Issue:** Fabric#25 (parent program Azazel#83; depends on Fabric#15, Fabric#23)
- **Family:** `azazel_fabric.external_security_contracts`
- **Minimum Fabric version:** `0.9.0rc6` — the next candidate, **unpublished**

This repository otherwise records contract ownership in each family's
reference document (`effect-contracts.md` §2 says so). Fabric#25 asks for an
ADR because these four records sit at the boundary with systems Azazel does
**not** own — EDRs, firewalls, routers, switches, DNS, NDR, SIEM, asset and
vulnerability systems — and with device adapters that can change real network
state. Who owns each record, and what it may and may not mean, is decided here
and is not left to be inferred from the schema.

## Context

The series needs one shared, descriptive language so that:

1. an external security system's observation can be normalized once and read
   by Knowledge and Edge without each repository inventing a parser;
2. Knowledge can advise on those facts without its advice being mistaken for a
   decision;
3. Deception can ask for a deception surface to be exposed, redirected,
   withdrawn or observed **through the product that owns the device**, without
   that request being mistaken for an approval or a command;
4. a device adapter can report what the device did after a separately approved
   action, without its report being mistaken for tactical success.

Fabric's First Principle governs all four: *Fabric describes; products
decide.* Design principles §4 forbids moving Edge's arbiter into Fabric, makes
Knowledge advisory-only, and keeps Fabric schema-only.

## Decision

### Ownership and authority meaning

| Contract | Owner (who may produce it) | Expected consumers | `authority_class` | What it means | What it can never mean |
| --- | --- | --- | --- | --- | --- |
| `ExternalObservationEnvelope/v0.1` | The product whose ingest adapter normalized the external fact (Edge, Nexus, Gadget, or a Knowledge ingest) — never the external system itself, which is not a Fabric adopter | Knowledge (Knowledge#95), Edge, replay tooling | `observed_fact` (pinned) | "This external system reported this fact, normalized this way, with this coverage" | a detection verdict, a containment result, or a request to act |
| `AdvisoryContextEnvelope/v0.1` | AZ-04 Knowledge | Edge, Nexus, an external consumer | `advisory_only` (pinned) | "Given these cited facts, Knowledge suggests these observations and these *considerations*" | a decision, an approval, a command, or a target list |
| `ExposureChangeProposal/v0.1` | AZ-06 Deception (Deception#39) | the owning Edge/Nexus change process, or an external change process | `proposal_only` (pinned) | "Deception asks the owner to consider this bounded change to a deception surface, under this decision reference" | an approval, a command, a device configuration, or a credential |
| `DeviceChangeObservation/v0.1` | The device adapter's owning product (Nexus#16 admits and confines adapters) | Deception, Knowledge, Edge, replay tooling | `observed_fact` (pinned) | "After a separately approved action, the device / its telemetry showed this status" | tactical success, containment, or a request to start/extend/end a change |

`executable` is pinned `False` on **every** record. The pins are enforced by
`Literal` types and registered in `tests/test_no_enforcement_bypass.py`, so a
well-formed payload cannot escalate them.

### Decision references are opaque and owner-validated

`ExposureChangeProposal.decision_ref` and `DeviceChangeObservation.decision_ref`
are opaque typed references (`decision:<opaque>`). Fabric checks **only their
shape**: that the slot holds a `decision:` reference and not an
`environment:`, `lifecycle:`, `presentation:`, `advisory:`, `proposal:`,
`effect:` or `surface:` one. Whether the referenced decision exists, is valid,
is unexpired and covers the requested change is verified **only by the owning
product** — Edge/Nexus or an external change process. A proposal carrying a
well-formed `decision_ref` is still a proposal.

`AdvisoryContextEnvelope` has **no** `decision_ref` field at all. Advice that
names a decision is how advice is mistaken for one.

### Signatures and mTLS prove origin, never authority

`ExternalProvenance.signature_ref` and `ProvenanceHop.transport_identity_ref`
record a detached signature and a transport (mTLS) identity. Verifying them
tells a consumer **who produced or relayed the bytes and that they were not
altered**. It never tells the consumer that anyone may act on them:
`ExternalProvenance.confers_authority` is pinned `False`. This is the same rule
`ReplayProvenance` (Fabric#15) and the Edge-decision transport signature
(`v0.8.0`) follow.

### Closed vocabularies, weakest fallback

- `fact_class` is closed; an unrecognized class becomes `unknown`, and the
  source's label is preserved in `source_fact_label`. `unknown` maps to
  nothing — Fabric provides no function from a fact class to a
  `DefensiveState`, an `EffectClass`, or a containment claim.
- `DeviceChangeObservation.status` is `requested`, `accepted_by_device`,
  `applied`, `observed`, `released`, `failed`, `stale` or `unknown`; an
  unrecognized status becomes `unknown`. **No status implies tactical
  success**, and `tactical_outcome_claimed` is pinned `False`.
- `requested_effect` is closed and an unknown value is **refused** rather than
  coerced: a proposal nobody can read must not be considered.
- `privacy_class` is closed (`public`, `internal`, `sensitive`, `restricted`).
  A consumer rejects or sanitizes a class it is not admitted to receive
  (`assert_privacy_admitted`, with the admission set supplied by the consumer).

### What is checked: allowlists first, denylists as a belt

The family is **closed by construction**, the same way its vocabularies are:
what may be written is listed, and everything else is unrepresentable. Two
rounds of review showed that denylists over open strings keep leaking
(abbreviations, suffixed kinds, encodings, lookalikes); allowlists do not.

| Surface | Allowlist |
| --- | --- |
| Every ref slot (`*_ref`, `*_refs`, ids) | a per-slot set of kinds (e.g. `subject_refs`: `asset` `account` `user` `identity` `process` `file` `flow` `service` `vulnerability` `case`; `evidence_refs`: `evidence` `artifact`; `decision_ref`: `decision`; `environment_ref`: `environment`; `target_scope_ref`: `scope`; ...) and a body of `[a-z0-9][a-z0-9_-]{0,127}` — no dot, colon, slash, `%` or upper case, so FQDNs, IPs, URLs, paths and encoded forms cannot be refs |
| Free text (advisory summary/limitations/unknowns/rationale/constraints; observation and device limitations, gaps, confounders, failure reason) | ASCII letters, digits, space and `. , ( ) ' -`, 1–2048 characters; a dot must be followed by a space or the end; no run of 7+ digits; no hex literal. `: ; \| & > < $ / \\ = %`, backtick, tab, newline and non-ASCII are unrepresentable |
| Product names | `[a-z][a-z0-9-]{0,63}` |
| Versions | `1`, `1.2`, `1.2.3`, optionally `-tag` / `+build` (`[0-9a-z]` identifiers) |
| `normalized_fact` and vendor-extension **keys** | `[a-z][a-z0-9_]{0,63}`, and no `_`-separated token (trailing digits dropped) in `OPAQUE_KEY_DENY_TOKENS` (execution, secrets/sessions, rules/routes/DNS, authority/verdict, envelope-owned words); `key` alone or next to `priv`/`private`/`ssh`/`signing`/`api`/`secret`/`access`/`auth` |
| `normalized_fact` and vendor-extension **values** | `None`, strict bool, int, finite float, or ≤256 characters of letters, digits, space and `. _ , ( ) ' @ + -` without a word in `OPAQUE_VALUE_DENY_WORDS` or a JWT-like `eyJ...` word |
| Tenancy | `tenant_ref` is the only place a tenant can be written; refs elsewhere cannot be `tenant:` kinds and free text/values cannot hold `:` |
| Numbers | strict ints and bools for counts, flags and bounds; NaN/Inf refused |

The denylist guards from the first version stay on as a belt over the whole
record: directive/secret key names (normalized, ASCII-only keys), target
locator key names in advisory/proposal records, secret markers, credential
locator prefixes, inline `tenant:` mentions, and a command-word list for
advisory text (`COMMAND_TEXT_TOKENS`). `canonical_external_security_json`,
`canonical_digest` and `assert_no_replay_extension` re-validate a model from
its python dump first, so a record mutated after construction (or made with
`model_copy(update=...)`) cannot be canonicalized or digested.

**Not checked:** the meaning of prose that stays inside the allowlist. A
plain-words instruction ("please block that machine") is representable; it is
still advice, and the consumer's own authority decides.

**Intended allowances:** a version field accepts `10.1` (it is a valid
version); an observation's `normalized_fact` may carry a dotted IPv4 address
or hostname as a value, because observing one is a fact. Anything with `:` or
`/` (IPv6, URLs, paths) must go digest-only.

Vendor-specific material is confined to `VendorExtension`: a dotted namespace,
depth ≤ 4, ≤ 32 items per collection, ≤ 1024-character strings, ≤ 8 KiB
canonical, at most 4 per record, unique namespaces, and a `body_digest` that
must equal the canonical digest of the body. Raw vendor payload never travels;
`payload_digest` and `evidence_ref` point at it.

### Maturity

The family is **experimental** under the Fabric#23 program decision: a family
is `stable` only with one producer, two independent consumers, and
success/rejection/degradation interoperability tests. It has none yet. It
therefore:

- is marked `**experimental**` in `docs/release-compatibility.md` and in the
  feature-to-minimum-version matrix;
- does **not** block the stable `v0.9.0` tag;
- makes **no compatibility promise**: its shape may change without a candidate
  bump;
- is **optional**: no other Fabric module imports it, so Edge, Knowledge,
  Deception, Nexus and Boot stay compatible when they do not.

## Consequences

- Downstream order: Knowledge#95 and Deception#39 consume/produce the profile;
  Nexus#16 admits and confines their adapters. Promotion to stable is a
  separate decision once those round-trips exist.
- A producer that today mints untyped decision ids (the `outcome_contracts`
  style, e.g. `decision-golden-redirect-1`) must type them to place them here
  (`decision:decision-golden-redirect-1`). The body stays opaque; the kind is
  what lets the slot refuse a lifecycle id.
- **Owner-facing defaults** (chosen by the implementer, to be confirmed by the
  owner): proposal window ≤ 7 days; vendor extension depth ≤ 4, ≤ 32 items per
  collection, strings ≤ 1024 characters, ≤ 8 KiB canonical, ≤ 4 per record;
  fact projection depth ≤ 4, ≤ 64 items, ≤ 16 KiB. These are contract limits,
  not policy recommendations; a product may impose tighter ones.
- The closed checks have **known false positives**, accepted rather than
  loosened: see [`external-security-contracts.md`](../external-security-contracts.md) §9.

## Non-goals

No vendor API, network client, device adapter, admission, approval, decision,
installer, container, or model-execution behaviour is added to Fabric, now or
by this ADR. Fabric does not decide whether a proposal is accepted, whether a
consumer is admitted to a privacy class, or whether a decision reference is
valid.
