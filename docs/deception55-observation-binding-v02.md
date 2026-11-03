# Deception #55 — observation binding v0.2 (PROPOSAL)

Status: **proposal only. Not adopted, not released, no consumer has adopted it.**
Edge and Deception consumer adoption is pending; nothing here changes
`v0.1` behaviour or the release version. **This does not complete #55.**

## Scope

Fabric v0.2 is limited to the typed `observation_objective_ref` and the
cross-product join refs (environment, decision, trace, frame, hypotheses,
lease, session). It carries references, never payloads.

The **observation-objective payload** itself is a separate, M.I.O.-owned,
non-executable contract, to be delivered in a distinct M.I.O. PR. This Fabric
proposal does not duplicate that contract's semantic text, does not define its
fields, and does not constitute the M.I.O. implementation. Until that M.I.O. PR
lands, `observation_objective_ref` is an opaque name only.

Existing import gates are respected unchanged: no `mio_contracts` module
imports `effect_contracts` or `external_security_contracts`, and no guard test
is relaxed (only additive coverage). This proposal **introduces a new directed
dependency `deception_contracts.models_v02 → effect_contracts.refs`**, added
solely so the v0.2 models reuse the shared typed-ref grammar rather than define
a second one. It is not claimed to be previously permitted; the existing guards
simply do not forbid it, and the owner should confirm the edge is acceptable.

## Purpose

Let an `interaction-observation` be joined, by exact reference equality, to the
Edge activation decision and lease under which it was made — without Fabric
carrying any authority.

## Owner semantics

| Actor | May | May not |
|---|---|---|
| **Azazel-Edge** | issue, renew and revoke the lease; decide and withdraw the activation | — |
| **Fabric** | describe the references and check they agree | issue, extend, shorten, renew, revoke or choose anything |
| **Azazel-Deception** | record what it observed under a lease it was given, echoing the refs | authorize, extend or choose a lease, environment, tier or objective |
| **M.I.O.** | name an observation objective by reference (advisory) | cause activation |

Lease ownership is Edge-only: Edge alone issues, renews and revokes the lease.
No lease enforcement policy is introduced. This contract only carries Edge's
values — `lease_ref`, `effective_at` and `lease_expires_at` are what Edge wrote
into its decision; the cross-check only compares an observation time to them.

## Shapes (separate classes, not subclasses of v0.1)

* `environment-activation-decision/v0.2` → `EnvironmentActivationDecisionV02`
* `interaction-observation/v0.2` → `InteractionObservationV02`

Both are frozen, `extra="forbid"`, timezone-aware. All new fields are typed
opaque refs using the **existing** `effect_contracts.refs` grammar
(`OPAQUE_REF_PATTERN`, `require_ref_kind`); no second grammar. `RefKind` gains
only `frame`, `hypothesis`, `lease`, `observation_objective`. The v0.2-introduced fields are typed refs or
bounded machine values; the v0.2 observation has no unconstrained `metadata`. Fields reused unchanged from
v0.1 (notably `runtime_context`, with its unbounded free-text lists, dict-valued floats and `selected_tier`)
keep v0.1's looser constraints; see Residuals.

| Join key | Decision field | Observation field | Kind |
|---|---|---|---|
| environment | `environment_id` | `environment_id` | `environment:` |
| package | `package_id` | `package_id` | (retained, plain) |
| node | `target_node_id` | `node_id` | (retained, plain) |
| decision | `decision_id` | `decision_ref` | `decision:` |
| trace | `trace_id` | `trace_id` | `trace:` |
| observation objective | `observation_objective_ref` | `observation_objective_ref` | `observation_objective:` |
| frame | `frame_ref` | `frame_ref` | `frame:` |
| hypotheses | `hypothesis_refs` | `hypothesis_refs` | `hypothesis:` (set equality) |
| lease | `lease_ref` (+ `lease_expires_at`) | `lease_ref` | `lease:` |

The field is `observation_objective_ref`, never the Engage `objective`.
Observation additionally carries `session_ref` (`session:`) — opaque, minted by
the observing runtime **per runtime generation**; it must not embed a source
address, account/credential material or the lure identity. Structural screening is a
best-effort filter only: it rejects `@`, `=`, IPv4 text and a bare IP body, but
it can miss IPv6 embedded in text or hostnames. It is not a privacy guarantee
and must never be relied on as one. No lure/session substring heuristic is
applied (false positives, trivially evaded). Lure non-linkage and
the per-generation property are producer duties Fabric cannot verify — an
unresolved semantic binding. Lures are `lure_ref` (`artifact:`), evidence
`evidence:`.

## Time semantics

* `expires_at` (v0.1-compatible) is the **Edge activation-decision acceptance
  window**: it is what is used when accepting the activation.
* `lease_expires_at` is the **separate end of the runtime lease** Edge issued,
  with the invariant `effective_at < lease_expires_at <= expires_at`: the lease
  cannot outlive the signed authorization (equality is allowed).
* The binding cross-check uses `[effective_at, lease_expires_at)`.

No lease issuance, renewal or enforcement policy is created here.

## Cross-check and what it does NOT establish

`check_observation_binding(observation, decision)` is pure (no clock, I/O or
mutation) and raises `ObservationBindingError` unless: every join key above
matches; `decision.status` is `accepted`, `modified` or `downgraded`; and
`decision.effective_at <= observed_at < decision.lease_expires_at`. All three
datetimes are timezone-aware, compared by instant. Both arguments must be v0.2
types; a v0.1 record is rejected, never coerced.

It is a **structural cross-check only**. It does not:

* **Authenticate the decision.** Edge must verify the decision signature on the
  **original unnormalized signed mapping**, using the shared canonicalization
  (`verify_decision_signature`), **before Pydantic parsing**. Do not re-dump the
  normalized model for verification: defaults and datetime normalization can
  alter the canonical payload. This proves origin/integrity only, not
  authorization or liveness. Raw wire bytes are not what is signed.
* **Authenticate the observation.** `observed_at` is asserted by the producing
  runtime, not proven. The observation producer must be authenticated
  separately. **No mechanism exists yet — unresolved integration requirement.**
* **Show the lease is currently live.** It cannot see a later revoke,
  terminate or renewal. Edge must use its own current lease/decision state and
  its own receipt clock for current lease/revocation.
* **Bind the package digest.** `package_digest` substitution is a known gap:
  the observation carries no digest. Edge must confirm the package digest from
  the immutable artifact before activation. No digest field is added without a
  clear producer contract.

### Adoption checklist (Edge / Deception)

1. Verify decision signature on the original unnormalized signed mapping (shared canonicalization), then remove the signature field and parse.
2. Authenticate the observation producer (mechanism TBD).
3. Check current lease state: revocation, termination, renewal (Edge-side).
4. Judge currency with Edge's receipt clock, not `observed_at`.
5. Confirm package digest from the immutable artifact before activation.
6. Run `check_observation_binding` as the structural join only.

## Bounds

v0.2 `reason_codes` are machine codes (`[a-z][a-z0-9_]{0,63}`, unique, at most
16). `package_id`, `target_node_id`/`node_id`, `selected_tier` and
`observation_id` are at most 128 characters. Evidence and lure refs stay typed;
the v0.2 observation has no `metadata`. v0.1 is untouched.

## Parsing / versions

Order inside `parse_activation_decision_v02` / `parse_interaction_observation_v02`:
(1) the exact `schema_version` is checked; (2) runtime-directive scan (and, for
observations, the belief/verdict scan); (3) `model_validate`. The dispatching
`parse_activation_decision` / `parse_interaction_observation` route on
`schema_version` first. Unknown versions are rejected. With `require_binding=True`
a v0.1 payload is rejected. v0.1 classes and golden fixtures are unchanged, and
v0.1 strict readers reject v0.2 payloads.

**Signature handling.** The decision signature is verified on the original
unnormalized signed mapping, using the shared canonicalization
(`canonical_decision_bytes` / `verify_decision_signature`), **before** parsing
(see the cross-check section). Verification covers the canonical JSON of the
mapping (sorted keys, compact separators, `ensure_ascii=False`,
`allow_nan=False`, signature field excluded), not raw wire bytes. The signature
member is not a model field, and the models use `extra="forbid"`, so the caller
must remove the signature field from the mapping before calling any `parse_*`
function. Passing a signed envelope unchanged is rejected. This proves
origin/integrity only, not authorization or liveness.

## Open items needing a contract-owner decision (not invented here)

1. **Objective payload belongs to M.I.O.** It is delivered as a separate
   M.I.O.-owned, non-executable contract in a distinct M.I.O. PR, not here.
   Reusing `external_security_contracts.RecommendedObservation` from Fabric is
   not pursued: that family is optional and nothing outside it (except
   `testing/external_security.py`) may import it, and gated families
   (`mio_contracts`, `external_security_contracts`) may not import
   `effect_contracts`. No gate is amended; only the *reference*
   (`observation_objective_ref`) is in scope for Fabric v0.2.
2. **Objective ref kind.** A dedicated `observation_objective` `RefKind` is
   used so Engage/action `advisory:` refs cannot satisfy the slot; owner to confirm the name.
3. **Lure ref kind.** No `lure` kind; `artifact:` is used.
4. **Hypothesis match** is exact set equality (fail closed); whether an
   observation may cover a subset is undecided.
5. **Lease bounds.** Enforced structurally: `effective_at < lease_expires_at <=
   expires_at`. Renewal beyond `expires_at` requires a new signed decision.
6. **Accepting statuses** (`accepted`/`modified`/`downgraded`) mirror v0.1's
   non-rejecting set; Edge confirms.
7. **Residuals.** `session_ref` opacity is only best-effort structurally checked
   (see Scope; IPv6 in text/hostnames can pass), lure/session linkage and per-generation
   uniqueness are producer duties; observation authentication, live-lease
   state and package-digest binding are unresolved (see above); `RuntimeContext` reuses its
   existing descriptive v0.1 contract, with unbounded free-text lists and dict-valued floats;
   `check_observation_binding` does not compare the observation's `runtime_context.selected_tier`
   with `decision.selected_tier`, nor read `runtime_context` at all; Edge must confirm the accepting-status
   vocabulary and the lease/session producer semantics.
