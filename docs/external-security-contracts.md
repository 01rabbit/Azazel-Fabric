# External-security observation, advisory, and exposure contracts

Status: **experimental** (`azazel_fabric.external_security_contracts`,
Fabric#25). The minimum version is the release candidate `0.9.0rc6`. No
producer, no consumer, **no
compatibility promise**, and outside the R1c stable gate (Fabric#23 program
decision). Additive and optional: no existing model changed, and nothing else
in Fabric imports this family.

Ownership and authority meaning are decided in
[ADR-0001](adr/0001-external-security-contract-ownership.md).

Related: [contracts](contracts.md) · [effect contracts](effect-contracts.md) ·
[design principles](design-principles.md) ·
[release compatibility](release-compatibility.md)

## 1. The four records

| Schema | Model | `authority_class` | Owner |
| --- | --- | --- | --- |
| `external-observation-envelope/v0.1` | `ExternalObservationEnvelope` | `observed_fact` | the normalizing ingest adapter's product |
| `advisory-context-envelope/v0.1` | `AdvisoryContextEnvelope` | `advisory_only` | AZ-04 Knowledge |
| `exposure-change-proposal/v0.1` | `ExposureChangeProposal` | `proposal_only` | AZ-06 Deception |
| `device-change-observation/v0.1` | `DeviceChangeObservation` | `observed_fact` | the device adapter's owning product |

`executable` is pinned `False` on all four. Every record also carries
`producer_product`, `producer_node_ref`, `producer_version`, `tenant_ref`,
`privacy_class`, and an `ExternalProvenance` chain whose last hop must be the
producer itself. `confers_authority` is pinned `False` on the provenance: a
signature or an mTLS identity proves origin and integrity, never authority.

Shared parts: `EventWindow`, `FreshnessStatement`, `TelemetryCoverage`,
`ProvenanceHop`, `ExternalProvenance`, `VendorExtension`,
`RecommendedObservation`, `RecommendedAction`, `RollbackRequirement`.

## 2. Mapping to `DefensiveState` (#14) and effect/outcome/terrain (#15)

These types **sit beside** the #14 and #15 vocabularies. They do not extend,
replace, or translate them, and Fabric publishes **no function** from any value
here to any value there. The tests pin both directions: no value in this family
is recognized by `coerce_defensive_state` or `coerce_effect_class`, no value
spells a `DefensiveState` or `EffectClass` member in any letter case, and no
module in this family imports `schema` or `effect_contracts`.

| Here | Nearest #14 / #15 concept | Relationship | Why the semantics are not merged |
| --- | --- | --- | --- |
| `ExternalObservationEnvelope` (`observed_fact`) | `EffectObservation` (#15), `OutcomeObservationEnvelope` (#15) | *Input* to a product that may later build a #15 chain. An external fact is about the world; an `EffectObservation` is about an effect Azazel built | An EDR detection is not an observation of an Azazel effect. Reading one as the other would let a vendor alert claim an effect was active |
| `fact_class` | — (none) | No counterpart. `network_policy_event` is a fact that a policy event occurred, not a `DefensiveState` | A firewall reporting a block is not Azazel being in `ISOLATE` |
| `AdvisoryContextEnvelope` (`advisory_only`) | `DefensiveEffectRef` with `advisory_inference` (#15); `CtiContextResponse` (§2 of contracts) | Same authority position — advice — expressed for external-security facts | An advisory `DefensiveEffectRef` names an effect class; this envelope names only *considerations* (`review_containment`, `review_deception_redirect`) and never an effect or a posture |
| `RecommendedAction.action_class` | `DefensiveState`, `EffectClass` | Disjoint vocabulary on purpose | `review_containment` is a request to a human/arbiter to think, not the `ISOLATE` state or the `network_isolation` effect |
| `ExposureChangeProposal` (`proposal_only`) | `DefensiveEffectRef` with `producer_decision_ref` (#15) | Upstream of it. A proposal *names* a decision by opaque ref; only the owning product can turn it into an effect, and that effect is then described by #15 | A proposal with a `decision_ref` is not a decision reference record. `is_authoritative_decision_reference("proposal_only")` is `False` |
| `requested_effect` | `EffectClass.REDIRECT_TO_PRESENTED_TERRAIN` (#15), `DefensiveState.REDIRECT` (#14) | Deliberately different words (`redirect_to_deception_surface`) | So that a proposal value can never be read as an effect that exists or a posture that is in force |
| `environment_ref` | AZ-06 environment lifecycle (`deception_contracts`), `PresentedTerrainRef.lifecycle_state_ref` (#15) | Names the environment the proposal is about | It can never fill `decision_ref`; the slot refuses `environment:` and `lifecycle:` refs |
| `DeviceChangeObservation` (`observed_fact`) | `EffectObservation.status` (#15), `outcome_contracts.MechanismObservationV0` | A device-level report that a product may cite as evidence when it writes its own #15 `EffectObservation` | `applied` means "the device accepted the configuration", not "the effect is active" and certainly not "the effect worked". `tactical_outcome_claimed` is pinned `False` |
| `TelemetryCoverage` | `OutcomeObservationEnvelope.coverage_complete` / `telemetry_gaps` (#15) | Same rule, restated: incomplete coverage must name its gaps | Kept as its own type so that neither family's change silently changes the other's |
| `ExternalProvenance` | `ReplayProvenance` (#15) | Same rule: `confers_authority` pinned `False` | Different job: transport chain across organizations vs. replay reproducibility |

**Decision references across the two families.** #15 inherits untyped decision
ids from `outcome_contracts` (`decision-golden-redirect-1`). This family
requires a typed `decision:` ref, because the whole point of the slot is to
refuse a lifecycle id that looks the same. A producer correlating the two
types the id (`decision:decision-golden-redirect-1`); the body stays opaque.

## 3. Closed vocabularies

| Field | Values | Unknown input |
| --- | --- | --- |
| `fact_class` | `endpoint_process`, `endpoint_file`, `network_flow`, `network_policy_event`, `dns_event`, `identity_event`, `asset_posture`, `vulnerability_posture`, `siem_case`, `unknown` | becomes `unknown`; original kept in `source_fact_label` |
| `source_system` | `edr`, `firewall`, `router`, `switch`, `dns`, `ndr`, `siem`, `asset_inventory`, `vulnerability_scanner`, `unknown` | refused |
| `privacy_class` | `public`, `internal`, `sensitive`, `restricted` | refused |
| `DeviceChangeObservation.status` | `requested`, `accepted_by_device`, `applied`, `observed`, `released`, `failed`, `stale`, `unknown` | becomes `unknown`; original kept in `source_status_label` |
| `requested_effect` | `observe_deception_surface`, `expose_deception_surface`, `redirect_to_deception_surface`, `withdraw_deception_surface` | **refused** (`coerce_exposure_effect` gives the weakest, for display only) |
| `RecommendedAction.action_class` | `observe_more`, `notify_operator`, `review_exposure`, `review_containment`, `review_deception_redirect`, `review_rate_limit`, `no_change` | refused |

No status means success. `failed` must carry `failure_reason`; `observed` must
cite evidence; `stale` and `unknown` must state a limitation or the source's
label.

## 4. What may be written: allowlists, then a denylist belt

The family is closed by construction. ADR-0001 holds the full table; in short:

| Surface | Allowlist (`validation.py` / `models.py`) |
| --- | --- |
| ref slots | per-slot kind set (`SUBJECT_REF_KINDS`, `EVIDENCE_REF_KINDS`, `FACT_REF_KINDS`, `CORRELATION_REF_KINDS`, and single kinds such as `decision`, `environment`, `scope`, `capability`, `adapter`, `node`, `tenant`, `trace`); body `[a-z0-9][a-z0-9_-]{0,127}` |
| free text (all four families) | `[A-Za-z0-9 .,()'-]{1,2048}`, a dot only before a space or the end, no 7+ digit run, no hex literal; advisory text also checked against `COMMAND_TEXT_TOKENS` |
| product names / versions | `[a-z][a-z0-9-]{0,63}` / `N[.N[.N]][-tag][+build]` |
| `normalized_fact`, vendor-extension body | keys `[a-z][a-z0-9_]{0,63}` without a token in `OPAQUE_KEY_DENY_TOKENS`; values bool/int/finite float/None or `[A-Za-z0-9 ._,()'@+-]{0,256}` without a word in `OPAQUE_VALUE_DENY_WORDS` or `eyJ...` |
| labels (`source_fact_label`, `source_status_label`) | `[A-Za-z0-9_.-]{1,128}`; an unrepresentable source label becomes the marker `unrepresentable` |
| numbers | strict ints/bools; NaN/Inf refused |

The belt that stays on over every record (`assert_no_external_security_directives`,
`assert_no_target_locators`, `assert_no_secret_material`, `assert_tenant_confined`,
`assert_no_locator_values`) refuses directive/secret/locator key names
(camelCase-split, separator-folded, ASCII-only keys), secret markers, credential
locator prefixes in any case, and `tenant:` mentions of another tenant. All walks
recurse into mappings, lists and tuples and are **bounded** (both guards are in
`BOUNDED_GUARDS` in `tests/test_directive_rejection_depth.py`).

`canonical_external_security_json`, `canonical_digest` and
`assert_no_replay_extension` re-validate a model from its python dump, so a
mutated record or a `model_copy(update=...)` cannot be canonicalized or
digested. Typed refs and digests use `fullmatch`.

What is **not** checked: the meaning of prose inside the allowlist.

The family is on the strict R1 boundary gate
(`tests/test_provisioning_no_side_effects.py`): only `__future__`,
`collections.abc`, `datetime`, `hashlib`, `json`, `re`, `typing` and `pydantic`
may be imported, no module-level execution, no dangerous builtin, and a fresh
interpreter importing it pulls in nothing outside that set. No OS probe,
network, subprocess, installer, or runtime-control import is possible.

## 5. Bounded opaque vendor extension

`VendorExtension`: dotted `namespace` (`vendor.product`, 2–4 labels), `body`
of depth ≤ 4, ≤ 32 items per collection, strings ≤ 1024 characters, ≤ 8 KiB
canonical; `body_digest` must equal `canonical_digest(body)`; at most 4 per
record with unique namespaces. It may not reuse a key the envelope owns
(`authority_class`, `executable`, `decision_ref`, `tenant_ref`, `status`, ...).
The normalized fact projection (`normalized_fact`) is bounded the same way
(depth ≤ 4, ≤ 64 items, ≤ 16 KiB).

## 6. Freshness, replay, and correlation

Pure helpers, no clock — the caller supplies `as_of`:

- `assert_not_expired(record, as_of=...)` — a stale record extends nothing.
- `assert_no_replay_extension(original, candidate)` — a re-sent proposal with
  the same `proposal_id` must be canonically identical; a later `expires_at` or
  wider scope is refused.
- `assert_device_observation_within_proposal(proposal, observation)` — same
  proposal, tenant, trace and decision; an in-place status
  (`accepted_by_device`, `applied`, `observed`) outside
  `[not_before, expires_at]`, or reported over an `observation_window` that
  leaves that interval, is refused. After expiry only `released`,
  `failed`, `stale` or `unknown` may be reported.
- `assert_privacy_admitted(record, admitted)` — the consumer's own admission
  set; Fabric decides nothing about it.

A proposal window is at most 7 days, and `expose_deception_surface` /
`redirect_to_deception_surface` must require rollback `on_expiry` and
`on_failure` and carry the `bounded_duration` constraint.

## 7. Golden vectors

`azazel_fabric.testing.external_security.GOLDEN_EXTERNAL_SECURITY_VECTORS`
publishes one chain — EDR fact → Knowledge advisory → Deception proposal →
device `applied` (partial coverage, named) → device `released` after expiry —
mirrored byte-for-byte under `tests/fixtures/external_security/` with a
canonical-SHA-256 manifest. Experimental like the family: the bytes make no
compatibility promise. `azazel_fabric.testing` does not import them, so the
general conformance kit stays free of the optional profile.

## 8. Owner-facing defaults

Chosen by the implementer, to be confirmed by the owner — including every
allowlist and deny-token set in §4: proposal window ≤ 7 days; vendor extension depth ≤ 4, ≤ 32 items, strings ≤ 1024, ≤ 8 KiB, ≤ 4 per
record; fact projection depth ≤ 4, ≤ 64 items, ≤ 16 KiB; record walk depth ≤
12. Complete coverage requires `sources_expected` and `sources_reporting`,
with at least one source reporting.

## 9. Known false positives and intended allowances

The allowlists refuse some legitimate content. That loss is accepted rather
than loosened; the documented home for such data is **digest-only**: keep the
raw value at the source, put its digest in `payload_digest` or behind an
`evidence:` ref, and keep it out of the record. Pinned by
`test_known_false_positives_stay_refused` and the allowlist tests.

| Refused | Why |
| --- | --- |
| `command_line`, `cmdline`, `argv` in an EDR process fact | execution tokens in an opaque-map key |
| `executable`, `session_id`, `dns_query`, `policy_name`, `auth_method` keys | `executable`, `session`, `dns`, `policy`, `auth` are deny tokens |
| `"Slovakia"` anywhere | contains the `AKIA` access-key-id marker, case-folded |
| IPv6 addresses, URLs and paths as fact values | `:` and `/` are outside the value allowlist |
| `Foo::Bar`, `0.5`, `cmd.exe`, `ssh brute force` in advisory text | `:` is unrepresentable; a dot must be followed by a space; `ssh` is a command word |
| hostnames as refs (`asset:db01.corp`) | dots are outside the ref body allowlist; mint an opaque id instead |

| any `*_status` key (`patch_status`, `http_status`) | `status` is envelope-owned |
| `payload_bytes`, `rule_id`, `firewall_zone`, `run_as`, `policy_name` | `payload`, `rule`, `firewall`, `run`, `policy` are deny tokens |
| SIEM case titles containing `:` (`Suspicious login: admin`) | `:` is outside the value allowlist |
| Windows and POSIX paths (`C:\\Windows\\x.exe`, `/etc/shadow`) | `:`, `\\` and `/` are outside the value allowlist |
| file hashes as fact values (`sha256` of 64 hex) | the long-token shape rule; put the digest behind an `evidence:` ref |
| any 32+ character token in a value, label or free text | the shape rule (keys, secrets, blobs) |

Intended allowances: `10.1` in a version field (a valid version); a dotted
IPv4 address, hostname or e-mail address as an observation fact value
(observing one is a fact); an observed command described in observation or
device free text (`iptables -F` — a fact, still without metacharacters, paths
or long tokens); opaque ref bodies that happen to spell a dashed hostname or
address (`asset:db01-corp-example-com`) — the grammar cannot tell an opaque id
from one; short secrets below the 32-character shape threshold that match no
known format (a 16-character base32 seed); spaced digits or prose such as
`10 0 0 1` in advisory text.

**Owner decision pending: fact vocabulary vs. deny tokens.** Under the
opaque-key deny tokens, `network_policy_event` and `endpoint_process` lose
their natural vocabulary: `rule_id`, `policy_name`, `acl_entry`,
`firewall_zone`, `*_status`, `run_as`, `payload_bytes` and `cmdline` are all
refused, so a firewall policy event can say little more than `action` and a
matched entry, and a process fact cannot carry its command line. Two options,
**neither applied here**:

1. **Keep it closed** (current). Such detail goes digest-only behind an
   `evidence:` ref. Simple and leak-proof; the projection stays thin.
2. **A per-`fact_class` key allowlist** that admits named opaque identifiers
   for that class only — e.g. `rule_id` / `policy_name` / `firewall_zone` for
   `network_policy_event`, still with the value allowlist and long-token rule
   applied. More useful facts, at the cost of a vocabulary to maintain per
   class and a review whenever it grows.
 Plain-words prose inside the allowlist is representable and is still
only advice.

## 10. Not in scope

Vendor APIs, network clients, device adapters, decision/admission/approval
logic, installers, containers and model execution. Promotion to stable needs
one real producer and two independent consumers round-tripping each envelope
(Fabric#25 acceptance item 5), which is downstream work (Knowledge#95,
Deception#39, Nexus#16).
