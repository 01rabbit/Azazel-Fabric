# External-security observation, advisory, and exposure contracts

Status: **experimental** (`azazel_fabric.external_security_contracts`,
Fabric#25). On `main` as `0.9.0rc6.dev0`; the minimum version is the next
candidate, `0.9.0rc6`, which is **unpublished**. No producer, no consumer, **no
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

## 4. What is refused, and where

| Guard | Applies to | Looks at | Refuses |
| --- | --- | --- | --- |
| `assert_no_external_security_directives` | all four, whole record | **keys** | command/provider syntax, route/firewall/DNS rule bodies, executors, tokens/credentials/credential locators, overrides, approvals/verdicts, success verdicts — by exact name and by pattern (`*command*` prefix/suffix, `*rule(s)`, `execute*`, `*override*`, `executor`, any `token`/`password`/`secret`/`credential`/`apikey` substring, `*success*` prefix/suffix), compared after camelCase splitting and with separators removed; any key that is not printable ASCII; an `executable` key whose value is not `false`; non-finite numbers |
| `assert_no_target_locators` | advisory and proposal | **keys** | hostname, IP, MAC, FQDN, interface/port/VLAN and device-/vendor-object ids, same normalization |
| reserved-key check | `normalized_fact`, `VendorExtension.body` | **keys** | `authority_class`, `executable`, `decision_ref`, `tenant_ref`, `schema_version`, `privacy_class`, `fact_class`, `status`, `provenance` in any ASCII spelling |
| `assert_no_secret_material` | all four | **keys and string values** | PEM blocks, key prefixes, `token=`-style assignments; a string *starting* with `credential`/`secret`/`token`/`key`/`vault`/`password`/`keychain` + `:` (any case, any body); the same kinds except `key` + `:` + non-space *inside* text |
| `assert_tenant_confined` | all four | **string values** | any `tenant:` reference (any case, any body, anywhere inside a string) other than the record's own |
| `assert_no_locator_values` | advisory and proposal | **string values** | locator-kind refs (`ip:` `host:` `hostname:` `mac:` `fqdn:` `url:` `uri:` `domain:`, any case); IPv4 / IPv6-shaped values (not in `*version` fields) |
| `assert_no_command_text` | advisory free text (summary, limitations, unknowns, rationale, constraints) | **string values** | closed command-token denylist (`COMMAND_TEXT_TOKENS`) and shell metacharacter sequences (`SHELL_METACHARACTER_SEQUENCES`) |

What is **not** checked: the meaning of prose (an instruction in plain words
without a denylisted token passes), and confusable characters inside values
(only keys are closed to ASCII). Observation and device records may carry
addresses and command-like strings as values of non-banned keys — observing
them is a fact. Every field is still input to the consumer's own authority.

`canonical_external_security_json` re-validates a model before serializing
it, so a frozen record whose mutable dict was changed after construction
cannot canonicalize. Typed refs and digests are matched with `fullmatch`, so a
trailing newline is refused.

All walks recurse into mappings, lists and tuples and are **bounded**: past the
nesting limit a payload is refused with a clean `ValueError` (both guards are
in `BOUNDED_GUARDS` in `tests/test_directive_rejection_depth.py`).

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

Chosen by the implementer, to be confirmed by the owner: proposal window ≤ 7
days; vendor extension depth ≤ 4, ≤ 32 items, strings ≤ 1024, ≤ 8 KiB, ≤ 4 per
record; fact projection depth ≤ 4, ≤ 64 items, ≤ 16 KiB; record walk depth ≤
12. Complete coverage requires `sources_expected` and `sources_reporting`,
with at least one source reporting.

## 9. Known false positives (accepted, not loosened)

The checks are closed, so some legitimate facts are refused. Pinned by
`test_known_false_positives_stay_refused`:

| Refused | Why | Where such data goes instead |
| --- | --- | --- |
| `"Slovakia"` anywhere | contains the `AKIA` access-key-id marker, case-folded | keep it at the source; cite it by `evidence:` ref / `payload_digest` |
| `{"executable": true}` in an `endpoint_file` fact | `executable` with any value but `false` is an execute flag | carry the file attribute under a non-banned key (`file_mode_bits`) or by digest |
| `command_line` in an EDR process fact | any key beginning or ending with `command` | a digest-only reference: hash the command line into an `evidence:` record held by the producer, and put only its digest in the projection |
| `ssh brute force` in advisory text | `ssh` is a command token | name the fact class or cite the observation; advisory text is not where tool names go |

## 10. Not in scope

Vendor APIs, network clients, device adapters, decision/admission/approval
logic, installers, containers and model execution. Promotion to stable needs
one real producer and two independent consumers round-tripping each envelope
(Fabric#25 acceptance item 5), which is downstream work (Knowledge#95,
Deception#39, Nexus#16).
