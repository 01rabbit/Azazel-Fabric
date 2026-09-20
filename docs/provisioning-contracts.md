# Provisioning and M.I.O. Contracts (R1a)

Status: **R1a draft schema and conformance kit, offered in the signed release
candidate `v0.9.0rc2` (R1b complete).**
These are the contract families the Nexus/Boot program plan
(`Azazel/docs/roadmaps/nexus-boot-program-plan.md` §5 R1) assigns to Fabric.
R1a is the draft schema plus conformance kit. **R1b is complete for
`v0.9.0rc2`**: `release/v0.9.0rc2.digest.json` covers the packaged surface and
is verified by `tests/test_release_candidate_digest.py`, and
`release/v0.9.0rc2.digest.json.sig` carries the release owner's detached
Ed25519 signature over the bytes that digest covers — see
[release signing](release-signing.md), and check it with
`python3 tools/rc_signature.py release/v0.9.0rc2.digest.json --check`.
`v0.9.0rc1` predates the procedure but was signed afterwards with the same
key, because Azazel-Boot pins it. **R1c** —
the stable `v0.9.0` — waits on downstream evidence.

**No product produces or consumes these two families yet**, so R1c is unmet for
them. Azazel-Boot names them in `PLANNED_FABRIC_MODULES` and checks whether
they import, which is a presence probe rather than adoption — its own module
says as much ("a module Boot would consume and cannot is reported, never
assumed"). Counting that probe would clear the gate with nothing exchanged. The
per-family record is in
[release compatibility](release-compatibility.md#contract-family-adoption-and-the-r1c-gate).

Tracking: `Azazel` program plan §5 R1, §6.2, findings SR-02, SR-04, SR-09,
AR-01, AR-12, AR-14.

## Authority boundary

> Fabric describes. Knowledge advises. Edge decides and enforces. Deception
> materializes an Edge-approved environment. Nexus and Boot integrate these
> products without creating another decision authority.

A provisioning record says what a host **is** and what an operator
**commissioned**. It never says what to run, what to trust, or what a host is
allowed to do. An M.I.O. record says what a model **said** and where that came
from. It never says what to do about it.

## Canonical types

### `azazel_fabric.provisioning_contracts`

| Type | Records |
|---|---|
| `InterfaceIdentity` | composite identity of one NIC from read-only inventory; carries no role |
| `StorageDeviceIdentity` / `PlatformIdentity` | storage and chassis/firmware identity |
| `HardwareInventory` | what a product observed on a node, `collection_method` pinned `read_only_inventory` |
| `ResourceProfile` | measured resource envelope — **no tier, no capability, no authority level** |
| `ThermalBudget` / `PowerBudget` | thermal and power envelope |
| `OperatorConfirmation` | the explicit operator act that gives an interface a role |
| `InterfaceIdentitySelector` | composite selector; MAC-only is structurally rejected |
| `InterfaceAssignment` | a role bound to a composite identity by an operator confirmation |
| `CaptureSupport` / `IsolationProperty` | observed capture support; demonstrated / not demonstrated / not tested isolation |
| `TopologyProfile` | commissioned interfaces, capture support, management reachability, isolation |
| `CommissioningRecord` | what was commissioned, bound to all three admission-dimension digests |
| `ProductManifest` | identity of a released product artifact; signature/provenance **locators** only |
| `AssetManifest` | bounded-artifact projection; `declared_regular_files_only` pinned `True` |
| `ModelManifest` | inert model-format description; every code-execution escape hatch pinned `False` |
| `FeatureMinimum` / `TestedCompatibilityTuple` / `CompatibilityManifest` | compatibility **claims**; no admission decision |
| `ProposedGenerationDescriptor` | a proposed generation, with declared irreversible effects |
| `ActivationReceipt` | observation-only record of what was observed after activating |
| `AuditCheckpointProjection` | the shared checkpoint envelope — **no chain, no chain verification** |
| `SecurityStateProjection` | security epoch, rollback ceiling, key roles, device-key state |

### `azazel_fabric.mio_contracts`

| Type | Records |
|---|---|
| `SituationFrame` | the local situation a cognitive router assembled |
| `AliasScope` / `RedactionRecord` | alias lifetime and per-field sanitizer actions |
| `SanitizedRemoteFrame` | the only shape that may reach a remote model |
| `Claim` / `ClaimSet` | structured claims frozen with full provenance before any narrative text |
| `Disagreement` | a contradiction, kept separate — `resolution` pinned `presented_separately` |
| `AdvisoryResult` | one cognition path's answer; inert by construction |
| `MergedAdvisory` | provenance-preserving merge output |

## Required invariants

### A resource envelope is not a capability, and not a tier

`ResourceProfile` records `usable_memory_mib` **measured after firmware
reservation**, plus CPU, storage, thermal, and power. It carries no tier.

This is deliberate and it is not a simplification. The program plan's RAM-tier
selector (§5 R2) reads:

> detect usable RAM in MiB after firmware reservation through one product-local
> selector: less than 8192 diagnostic, 8192–16383 `core`, 16384–32767 `lite`,
> and 32768 or more `standard`

Those thresholds compare *measured usable* MiB against *nominal* boundaries, so
a nominally 16 GB host that measures 16095 MiB usable selects `core`, not
`lite`. That is an open program decision, and the golden fixture
`tests/fixtures/provisioning/resource_profile.json` is exactly that host.
Fabric records the measurement and refuses to record the conclusion, so
ratifying a corrected threshold table later changes no contract and invalidates
no fixture.

`CORE` / `LITE` / `FULL` are **capability states**, never authority levels, and
effective capability is

```text
resource profile ∩ topology profile ∩ verified asset set ∩ trust/health state
```

No single record may imply it. `registry.CAPABILITY_STATES` exists so two
products name the same summary the same way; no contract field uses it, and a
test asserts none ever does. `validation.assert_no_resource_tier_claim`
recursively rejects `tier` / `capability_state` / `authority_level` fields in
any spelling.

### An interface role is confirmed, never inferred

A role comes from read-only inventory plus an explicit operator confirmation
against a composite identity — bus path, permanent MAC, PCI/USB identity,
serial, driver/firmware, wireless PHY, physical label.

- `InterfaceIdentitySelector` requires `bus_path`, `permanent_mac`, **and** at
  least one of `pci_id` / `usb_vid_pid` / `serial`. MAC-only matching is
  structurally impossible.
- `interface_composite_key` deliberately excludes `kernel_name_observed`: a
  kernel interface name is unstable across reboots and driver reloads, and it is
  the inference source AR-12 names. Renaming an interface cannot change which
  physical device an assignment refers to.
- `resolve_interface_assignment` fails closed on **zero** matches and on
  **multiple** matches. A `HardwareInventory` containing two interfaces with the
  same composite identity cannot even be constructed.
- `OperatorConfirmation.method` values are all human acts. There is no value
  meaning "matched by name", "had carrier", or "held the default route", and
  `validation.assert_no_role_inference` rejects such fields recursively.
- Every role is `unassigned` until commissioning, and an assignment names the
  `inventory_digest` it was made against, so a changed NIC identity invalidates
  it instead of silently re-binding.

### Nothing authorizes

`ProposedGenerationDescriptor` replaces the activation-plan shape AR-01
rejected. It names digests and declares irreversible effects; it carries no step
list, no unit, no route, no command, and no approval. `ActivationReceipt` is
`observation_only`.

`validation.assert_no_provisioning_directives` recursively rejects **command,
unit, route, firewall, device-path, executor, boolean-authorization, and
trust-decision** fields, in any spelling (`deviceNode`, `device-path`, and
`Device Path` all normalize to the same banned key). `bus_path` is explicitly
*not* a device path: the plan mandates it as part of the composite identity, and
a PCI/USB topology address is not an actionable device node.

`CompatibilityManifest` records that a tuple was **tested**. It does not admit
it. A broad version range is a descriptive claim and cannot authorize
activation; deny-by-default admission stays product-local.

### M.I.O. output is inert

`AdvisoryResult` pins `executable`, `may_request_followup`, and
`contains_links` to `False`, and `rendering` to `inert_text`. A remote answer
cannot request follow-up disclosure — every follow-up must be a new, locally
constructed, audited sanitized frame (AR-14).

`SanitizedRemoteFrame` pins `contains_raw_evidence` to `False` and
`ambiguity_resolution` to `deny_on_ambiguity`, and a frame classified
`sensitive` or `restricted` is rejected outright, so restricted content cannot
leave the node.

A merge freezes a `ClaimSet` **before** producing narrative text; each claim
keeps source, model, generation, inputs, freshness, confidence, and limitations,
and a contradiction becomes a `Disagreement` whose resolution is pinned to
`presented_separately`. A merge cannot drop a claim it reports a disagreement
about.

**What Fabric does not do:** judge the prose. `narrative_text` is model output,
and no schema can prove a sentence is non-imperative. The contract guarantees
nothing downstream can *act* on it.

### Projections, not enforcement

`AuditCheckpointProjection` and `SecurityStateProjection` standardize the
*envelope*. Fabric computes no chain, verifies no chain, and makes no trust
decision — the same boundary `azazel_fabric.audit` already holds
(`contracts.md` §1). Chain enforcement and trust decisions stay product-local.

## Canonical bytes and digests

`provisioning_contracts.integrity` and `mio_contracts.canonical_mio_json`
produce JSON with sorted keys, compact separators, `ensure_ascii=False`, and
`allow_nan=False` — byte-identical to
`azazel_fabric.deception_integrity.canonical_package_signing_bytes` and
`azazel_fabric.outcome_contracts.canonical_fact_json`. Tests pin that
equivalence, so a record canonicalized in one repository hashes identically in
another.

`content_digest(record, digest_field=...)` binds every field except the record's
own digest and any detached `signature_ref`. `assert_content_digest` fails
closed on a mismatch. Expiry is checked by `assert_not_expired(record,
as_of=...)`: `as_of` is **required**, because Fabric holds no clock and the
result must be deterministic and replayable.

## Open extension registries

`provisioning_contracts.registry` defines `azazel-nexus` and `azazel-boot` (with
the other series products), the neutral deployment profiles
`nexus-embedded-lite`, `boot-emergency-lite`, `knowledge-full-node`,
`deception-full-host`, and the interface roles. Registries are *open*: an
unregistered value is descriptive data, not a validation error. Registration
documents a name; it grants nothing.

## Feature-to-minimum-Fabric-version matrix

Published so products converge deliberately instead of being forced into a
simultaneous untested pin change.

| Feature ID | Minimum Fabric version | Notes |
|---|---|---|
| `schema/v1.0` | `0.1.0` | `StateSnapshot` / `DecisionExplanation` / `AuditEvent` |
| `cti-contracts/v1.0` | `0.1.0` | advisory-only CTI exchange |
| `view/v1.0` | `0.2.0` | shared `StatusView` |
| `deception-contracts/v0.1` | `0.5.0` | canonical AZ-06 contract family |
| `deception-observation/v0.1` | `0.6.0` | effectiveness observation + transition catalog |
| `engagement-contracts/v0.1` | `0.8.0` | MITRE Engage-aligned engagement contracts (see `CHANGELOG.md` — there is no `v0.7.0` tag) |
| `decision-signing/v0.1` | `0.8.0` | canonical Edge-decision transport signature |
| `outcome-contracts/v0.1` | `0.9.0rc1` | Outcome-as-Evidence shared facts (candidate) |
| `provisioning-contracts/v0.1` | `0.9.0rc1` | this family (candidate) |
| `mio-contracts/v0.1` | `0.9.0rc1` | M.I.O. cognition family (candidate) |
| `defensive-state/v0.1` | `0.9.0rc2` | canonical `DefensiveState` vocabulary and `coerce_defensive_state` (candidate) |
| `effect-contracts/v0.1` | `0.9.0rc2` | cross-series effect / outcome / presented-terrain family (candidate) |

A minimum version is a compatibility claim, not an admission decision.

A candidate row names a version a consumer **can** pin: `v0.9.0rc1` and
`v0.9.0rc2` are published tags and four products are on one of them. What the
`rc` suffix withholds is the stability promise, not the tag. The rows stay
marked `(candidate)` until `v0.9.0` is cut, at which point each one's minimum
becomes `0.9.0` — a consumer already on a candidate needs no code change for
that, only a re-pin.

Completeness is enforced: `tests/test_feature_minimums.py` fails if a
`*_contracts` family ships without a row here. A family with no stated minimum
is a family a consumer cannot plan around, which is what publishing this matrix
was for.

## Conformance kit

`azazel_fabric.testing` publishes the R1a vectors so every consumer runs the
same ones:

```python
from azazel_fabric.testing import (
    GOLDEN_PROVISIONING_NEGATIVE,
    GOLDEN_REFERENCE_AS_OF,
    golden_provisioning_names,
    load_golden_provisioning,
)
```

Every vector is deterministic (no clock, no randomness, no environment lookup)
and byte-stable across processes and repositories; the same content is committed
under `tests/fixtures/provisioning/` and `tests/fixtures/mio/`. Vectors in
`GOLDEN_PROVISIONING_NEGATIVE` must be **rejected** by a conforming consumer:

| Negative vector | Must fail because |
|---|---|
| `product_manifest_directive` | directive-bearing (`systemd_unit`) |
| `generation_descriptor_unknown_version` | unknown schema version |
| `generation_descriptor_expired` | expired against `GOLDEN_REFERENCE_AS_OF` |
| `commissioning_record_digest_mismatch` | content digest mismatch |
| `hardware_inventory_ambiguous` | two interfaces, one composite identity |
| `resource_profile_with_tier` | carries an unratified RAM-derived tier |
| `commissioning_record_inferred_role` | role inferred from a kernel name |
| `sanitized_remote_frame_restricted` | restricted content would leave the node |
| `advisory_result_executable` | advisory claims executability |
| `advisory_result_followup` | remote answer requests further disclosure |

## Static boundary gates

- `tests/test_no_enforcement_bypass.py` — every model in every family forbids
  extra fields, declares no directive/authority field name, and has each
  safety-sensitive field either `Literal`-pinned or explicitly classified. The
  provisioning/M.I.O. families additionally reject the stricter R1a field-name
  ban.
- `tests/test_provisioning_no_side_effects.py` — the SR-09 answer: an import
  allowlist, a no-module-level-execution check, a no-dangerous-builtin check,
  and a subprocess import-delta check proving the new modules pull in nothing
  that probes the OS, touches the network, spawns a process, installs, or
  controls a runtime.

## What R1a does not include

- **R1c.** R1b is done — the candidate digest exists and `v0.9.0rc2` carries
  the release owner's detached signature over it ([release
  signing](release-signing.md)). There
  is no stable tag, and no downstream evidence *for these two families* —
  other families have some, which is why the gate is tracked per family.
- **Consumer adoption.** Edge, Knowledge, Deception, Nexus, and Boot adapters
  are out of scope here; the plan's "at least one real producer and two real
  consumers" gate is an R1c requirement.
- **The RAM-tier threshold table.** Open program decision; see above.
- **Any installer, decision, network, container, or model-execution code.**
