# Changelog

All notable changes to Azazel-Fabric (formerly Azazel-Common) are recorded
here. The project follows [Semantic Versioning](https://semver.org/). Each
release corresponds to a `vX.Y.Z` tag and GitHub Release on
`01rabbit/Azazel-Fabric`; consumers pin an exact tag (see
`docs/migration-plan.md`).

## [Unreleased]

Nothing yet. The entries below moved into the tags that shipped them.

## [0.9.0rc5] — A terrain can bind to an effect that has no decision (Fabric#51)

**Additive.** Every `v0.9.0rc4` payload still validates and still chains.

### Added

- **A presented terrain can be bound to an effect that has no decision**
  (`effect_contracts`, Fabric#51). `PresentedTerrainRef` gains
  `source_effect_ref`, `trace_id`, `synthetic_identity_refs` and
  `synthetic_credential_refs`; `activation_decision_ref` becomes optional.

  **This is additive.** Every `v0.9.0rc4` terrain payload still validates and
  still chains, which `test_an_rc4_terrain_payload_still_validates` checks
  against the literal `rc4` field set rather than asserting it.

  What it fixes is a path that did not work at all. The chain check compared
  the terrain's `activation_decision_ref` against the effect's `decision_ref`,
  which is `None` for a `planned_shadow` effect, while the terrain's was
  required and non-empty — so the comparison could only ever fail. AZ-06 runs
  in that mode by default, so the family's own default producer could not
  produce a valid chain.

  The fix is not to skip the comparison. A terrain that chains to a
  decision-less effect binds through `source_effect_ref` **and** `trace_id`,
  both compared, because an effect id on its own is still satisfied by a
  cross-trace collision. Filling `activation_decision_ref` with something that
  is not a decision is refused: the effect has none, so whatever was named did
  not activate this terrain. A terrain carrying neither binding is refused at
  construction — "no reference" is not a weaker record, it is an
  unattributable one.

  Two golden vectors are published for the decision-less chain
  (`effect_shadow_defensive_effect_ref_v0.json`,
  `effect_shadow_presented_terrain_v0.json`), for the same reason the
  decision-bearing chain is published: so four repositories check the path
  against the same bytes rather than each inventing one.

  `synthetic_identity_refs` and `synthetic_credential_refs` take typed
  `identity:` and `credential:` references under the artifact rules — opaque,
  and refused if they carry recognizable secret material. The reference
  travels; the credential does not.

## [0.9.0rc4] — An observation may claim only what it observed (Fabric#52)

**Not additive.** A payload that validated under `v0.9.0rc3` is refused here.

### Changed


- **An `EffectObservation` may claim only `observed_fact` or
  `active_materialized`** (`effect_contracts/models.py`, Fabric#52). **This is
  not additive: a payload that validated under `v0.9.0rc3` is refused.**

  `DefensiveEffectRef` has refused those same two classes since the family
  shipped, with the stated reason that they are "an observation's to make". The
  converse was never enforced, so all six classes were accepted on the
  observation side. A record *reporting* an effect could therefore claim
  `producer_decision_ref` — asserting authority over the thing it reports — or
  `advisory_inference` and `planned_shadow`, which describe records where
  nothing was materialized and so nothing was observed, or `stale_or_unknown`,
  which claims nothing at all and must read to a consumer as a gap rather than
  as a weakly-labelled fact.

  The two sets now partition `AuthorityClass` exactly, and
  `test_every_authority_class_belongs_to_exactly_one_record` enumerates from
  the enum rather than from either model's constant, so a class added later has
  to be placed deliberately instead of defaulting to "effect-only" by silence.

  It lands in a candidate on purpose. The same correction after `v0.9.0` would
  break a stability promise; before it, it breaks a candidate that says it
  makes none. `azazel_fabric.effect_contracts.OBSERVABLE_AUTHORITY_CLASSES` is
  exported so a producer can check its own emission against the rule rather
  than discovering it at validation.

## [0.9.0rc3] — A typed reference's body may carry colons (Fabric#48)

Written after the fact. `v0.9.0rc3` was tagged while everything below sat
under `[Unreleased]`, and nothing noticed: this file's own opening line says
each release corresponds to a tag, and for one release it did not.
`tests/test_release_signature.py::test_every_published_candidate_has_a_changelog_section`
now checks that against `release/`, so the next candidate cannot be cut
without its section.

### Changed

- **`effect_contracts` has its first producer, and the adoption measured three
  things the family could not do** (`docs/release-compatibility.md`,
  `docs/effect-contracts.md`). Azazel-Deception#46 emits `PresentedTerrainRef`
  from the presented-terrain record AZ-06 already keeps. The row still reads
  `not met` — one producer, no consumer — but it is no longer empty for the
  reason it was.

  What the attempt found, recorded because the next adopter would otherwise
  find it again: the reference grammar refused every hierarchical id in the
  series (fixed below); `EffectObservation` and `OutcomeObservationEnvelope`
  are keyed on an `effect:` id **nothing in Azazel mints**, so they have no
  possible producer whoever adopts the family; and
  `assert_effect_chain_consistent` can only chain a presented terrain to a
  `producer_decision_ref` effect, so a `planned_shadow` one — AZ-06's default
  mode — cannot be chained at all.


- **A typed cross-series reference may carry further colons in its body**
  (`effect_contracts/refs.py`). The grammar shipped in `v0.9.0rc2` split on a
  colon and then forbade the body from containing one. That was measured
  against what the series actually mints, and the result was that
  `effect_contracts` **had no possible producer anywhere in Azazel**:
  `surface:http:8080`, `artifact:honey:invoice-2026` and `isolation:proof:1`
  (Azazel-Deception) and `edge:nft:1` (Azazel-Edge) were all refused by every
  slot that requires a typed ref. The alternative — a producer rewriting its
  own identifiers to fit — is not one: a rewritten identifier no longer
  resolves to the thing it named.

  The split point is still unambiguous, because the kind group cannot contain
  a colon. `require_ref_kind` therefore only ever accepts more than before,
  and `reject_ref_kinds` only ever rejects more — in the right direction,
  since a hierarchical value supplied in a `trace_id` slot was previously
  invisible to it and now is not.

  Opacity is unchanged where it was doing work: no slash, backslash,
  whitespace, quote or newline, so paths, URLs and PEM blocks stay out. The
  values the wider body now admits (`artifact:ssh-ed25519:AAAA`,
  `artifact:-----BEGIN:KEY`) are refused by the secret-material scan on
  presented-terrain reference fields, which is the layer that was always meant
  to screen them; a value rejected only as a punctuation accident was never
  being screened at all.

- **The package version moved to `0.9.0rc3.dev0`.** `v0.9.0rc2` is published
  and signed, so the first source change after it made
  `release/v0.9.0rc2.digest.json` disagree with the tree — which is exactly
  what that gate exists to report. Both published manifests and their
  signatures stay in the tree unchanged, describing their tags rather than
  `main`.

  That bump was the first time this package went back to a development version
  since the adoption-matrix and feature-minimum checks were written, and it
  broke three of them: they asked the compatibility document to describe
  `__version__` as "the latest **published** tag", which a `.devN` version is
  not. They now derive the published tag from `release/` — a record of an
  event rather than a statement of intent — and a new check refuses a package
  version that has fallen behind a tag it ships the manifest for.

- **The R1c adoption gate is recorded per contract family, and the record is
  enforced** (`docs/release-compatibility.md`,
  `tests/test_adoption_matrix.py`). R1c — the stable `v0.9.0` — waits on "at
  least one real producer and two real consumers", and that is a per-family
  condition: a release carrying five families does not clear it because one of
  them is well adopted. The new matrix states, per family, who produces and who
  consumes, citing `Repo:`path`` so a reader can check rather than take the
  word for it.

  Two findings it surfaces: `engagement_contracts` has **two producers and no
  consumer** (a contract that has only ever been serialized is not known to
  interoperate — the first read is where a disagreement shows), and
  `provisioning_contracts` / `mio_contracts` have **neither**. Azazel-Boot
  names the latter two in `PLANNED_FABRIC_MODULES` and probes whether they
  import; counting that probe as adoption would clear the gate with nothing
  exchanged.

  Fabric's CI cannot see the consumer repositories, so the test enforces only
  what is checkable here: every shipped `*_contracts` family has a row, no row
  names a family the package lacks, a verdict matches its own citation count in
  **both** directions, and every citation is shaped as a locator. Whether a
  cited file really produces what the row says is verified by reading it, and
  the test does not pretend otherwise.

- **`engagement_contracts` cleared the R1c gate** (adoption matrix in
  `docs/release-compatibility.md`). Both reads now exist, in opposite
  directions: Knowledge reads Edge's `EngagementEvent`
  (Azazel-Knowledge#105) and Edge reads Knowledge's `EngagementAdvisory`
  (Azazel-Edge#418). Producer and consumer are different products in both,
  which is what the gate is asking about — it is a round trip, not a count.

  Edge's `EngagementEvent` builder had said "for audit / Knowledge ingest" in
  its own docstring since it was written; Knowledge simply had no lane to put
  one in. Its new lane keeps the Engage vocabulary verbatim and mapped to
  nothing: three of the eight `activity` values coincide with Knowledge's
  `reaction.action_applied` and five do not, and inventing the missing five
  would make a product-local word canonical by the back door.

  Two things stay on the record now that the row reads **met**. Edge's
  advisory reader has no runtime caller yet — when Edge consults Knowledge is
  a product decision left with the product. And **Deception was considered and
  deliberately not used**: `PostureSuggestion.supported_activities` names
  AZ-06's own actions, so for Deception alone an advisory would be about what
  it does rather than what someone else does, which puts "read the advice" one
  step from "choose among the activities it lists". Clearing a gate is not
  worth thinning the boundary it sits behind.

  `deception_contracts` and `engagement_contracts` are now the two families
  with the evidence; five still have none.

- **`engagement_contracts` has its first reader** (adoption matrix in
  `docs/release-compatibility.md`). Until Azazel-Edge#418 the family had two
  producers and no consumer — Edge and Knowledge both wrote the Engage-aligned
  types and neither read what the other wrote. Edge now reads Knowledge's
  `EngagementAdvisory`, verified fail-closed against the canonical model and
  degrading fail-open so Edge's deterministic arbiter decides identically
  whether Knowledge answered or is absent.

  The row stays **not met**: the gate asks for two consumers and this is one.
  Recorded with what the citation does and does not mean — the reader has no
  runtime caller yet (when Edge consults Knowledge is a product decision left
  with the product), and the second consumer is an open doctrine question
  rather than a queued task.

- **No contract encodes a RAM-to-tier threshold** (`tests/test_no_ram_tier_encoding.py`,
  Fabric#23, plan §15 OF-01). The design was already right — this found no
  defect — but nothing held it. The line, stated precisely: a contract **may**
  carry measured capacity (`usable_memory_mib` and the rest are facts about a
  host), **may** carry a package's declared requirement (a deployment tier's
  `minimum` is what that package says it needs), and **may not** carry a tier
  derived from measured capacity or the threshold that would derive one. The
  difference is who decided — measurements and requirements are inputs; a
  capability tier is a verdict, and it belongs to the product whose
  deny-by-default admission policy has to live with it.

  `CORE`/`LITE`/`FULL` stay registered in `provisioning_contracts/registry.py`
  as an open registry of names, so two products call the same summary the same
  thing. Naming a word is not deciding with it — the same reason
  `REGISTERED_PRODUCTS` may list every product without Fabric admitting any of
  them. What the registry may not grow is a *mapping*: a dict pairing a MiB
  figure with a state, or a function that returns one.

  The tier-shaped fields in `deception_contracts` (`DeploymentTier.tier_id`,
  the four `selected_tier` fields) are exempt with the reason written down —
  they record a package's own declaration or a product's own selection, which
  is provenance, not Fabric classifying a host. An exemption naming a field
  that no longer exists fails, so the list cannot become somewhere to park the
  next one.

- **Round-trip coverage reaches every family, and the projections are pinned
  descriptive** (`tests/test_contract_roundtrip.py`, Fabric#23). The
  completeness guard — the one that fails when a contract ships with no
  round-trip or determinism check — enumerated two families. The package has
  six: 42 of its 73 contract models were outside it, including all three
  projections (`AuditCheckpointProjection`, `SecurityStateProjection`,
  `ClaimSet`). A self-extending guard that extends over part of the package is
  the shape this release keeps finding.

  Samples for the newly covered families come from the published vectors
  (`golden_provisioning_names`, `GOLDEN_EFFECT_VECTORS`) mapped to models by
  their `schema_version`, so the fixture and the model are checked together: a
  vector that no longer validates is as much a break as a model that no longer
  round-trips.

  The R1 gate also asks that a projection have "neither trust-decision nor
  chain-enforcement behaviour". That is now asserted: `authority` admits only
  `descriptive_only`, no field name reads as a verdict, and no method walks the
  checkpoint chain. `*_ref` and `*_refs` are deliberately not verdict markers —
  an opaque reference to a revocation list or a chain head is exactly the
  material a product needs to reach its own conclusion, and handing it over is
  not deciding for them.

- **Every banned field, in every family, at depth and inside collections**
  (`tests/test_directive_rejection_depth.py`, Fabric#23). The R1 exit gate asks
  for adversarial fixtures proving recursive directive rejection "at any
  nesting depth, including inside collections". The machinery was already
  sound — this found no bypass — but the proof reached nesting depth two, in
  mappings only, for one of six families. 258 banned names across eight guards
  are now exercised, in eight nesting shapes including lists, tuples and
  lists-of-lists.

  Two things it records rather than asserts. **Four guards walk unbounded**
  (`deception_contracts` ×2, `effect_contracts`, `engagement_contracts`): they
  find a directive at any depth, but past the interpreter's recursion limit
  (~1000 levels, measured) they raise `RecursionError` where the two R1a
  families raise a clean `ValueError`. A caller catching `ValueError` sees a
  refusal either way, but not the same one. Bounding those four changes their
  public behaviour and is a decision to take deliberately, so the split is
  pinned in `BOUNDED_GUARDS` — a family that gains or loses a bound makes the
  list wrong and someone looks.

  **`BANNED_FIELD_COUNTS` is literal**, because every other case enumerates the
  constant it checks: a name deleted from a guard would simply stop being
  tested, and the suite would pass with one fewer case. The counts are the only
  thing that notices — the same discipline as a test-count baseline.

- **The purity gate covers every module, not only the R1a families**
  (`tests/test_package_purity.py`). "Fabric describes; it never reaches the OS,
  the network, or a subprocess" was enforced only for `provisioning_contracts`
  and `mio_contracts`. `outcome_contracts`, `effect_contracts` and
  `schema.defensive_state` all shipped outside that gate, and a family outside
  R1 importing `subprocess` would be exactly as wrong.

  The R1a gate is not widened, because its other rules are genuinely
  R1a-specific — a narrow import allowlist that `effect_contracts` would fail
  for importing `enum`, and isolation from other families that
  `deception_contracts` legitimately breaks. The new file checks only the part
  that is true of every module, over a walked file list, catching a deferred
  import inside a function as well as a module-level one, and verifies at
  runtime that importing the whole package pulls in nothing banned.

  Measured, not assumed: pydantic alone pulls in `socket`, `urllib`,
  `platform` and nine more when its first model is built, so the runtime check
  is baseline-differential. Without that, the gate reports pydantic's imports
  as Fabric's and fails on a finding that is not Fabric's.

- **The feature-to-minimum-version matrix is complete and enforced**
  (`docs/provisioning-contracts.md`, `tests/test_feature_minimums.py`). The
  matrix is published so consumers converge deliberately instead of re-pinning
  in lockstep (Fabric#23), which only works if every shipped feature has a row.
  Two did not: `defensive-state/v0.1` and `effect-contracts/v0.1` shipped in
  `v0.9.0rc2` while the matrix still stopped at `rc1`. Both are added, and the
  test now fails if a `*_contracts` family ships without a row, if a row names
  a version newer than the package (the same gap seen from the other side), if
  a minimum is a range rather than an exact pin, or if a candidate row drops
  the caveat a reader decides on.

  It also corrects a false statement: "until `v0.9.0` is tagged, the `0.9.0`
  rows name a version no consumer can pin". `v0.9.0rc1` and `v0.9.0rc2` are
  published tags and four products are on one of them. What the `rc` suffix
  withholds is the stability promise, not the tag.

- **Documentation corrected against the tree.** The consumer table said every
  product was pinned to `v0.8.0`; four had moved and they do not agree on which
  candidate. `effect_contracts` was described as "unreleased … not in any tag"
  after shipping in `v0.9.0rc2`, and `provisioning-contracts.md` still named
  `v0.9.0rc1` as the current candidate — both left behind by the `v0.9.0rc2`
  release (#29). Azazel-Nexus was listed as a documentation-only repository; it
  now carries code with deliberately zero dependencies, which is why it appears
  in no pin table.

## [0.9.0rc2] — R1b candidate toward R1c

A **release candidate**, not the stable release. In the program plan's terms
this is **R1b** — the release-candidate digest (`release/v0.9.0rc2.digest.json`)
— cut so consumers can produce the evidence **R1c**, the stable `v0.9.0`,
requires. Everything below is additive over `v0.9.0rc1` and non-breaking: no released symbol changed, and a consumer
pinned to `v0.9.0rc1` keeps working unchanged.

It exists so the consumers waiting on this vocabulary can pin an exact tag
instead of `main` — Azazel-Knowledge#65, Azazel-Deception#28 and Azazel#62 each
hold a test that turns red the moment a pin carrying `DefensiveState` lands,
which is the signal that their remaining work became actionable.

A candidate makes no stability promise. `v0.9.0` is cut only after the plan's
"at least one real producer and two real consumers per non-experimental
contract" gate has linked evidence.

### Added

- **Canonical `DefensiveState` vocabulary** (`azazel_fabric.schema.defensive_state`,
  Fabric#14) — the five-value posture vocabulary shared across Edge, Knowledge
  and Deception, plus fail-safe coercion and `DefensiveStateProjection`. Fabric
  defines no mapping from a product's legacy mode names to it: inventing what a
  product-local word means would make that word canonical by the back door.
- **Cross-series effect / outcome / terrain contracts**
  (`azazel_fabric.effect_contracts`, Fabric#15) — `DefensiveEffectRef`,
  `EffectObservation`, `PresentedTerrainRef`, `OutcomeObservationEnvelope`, and
  `ReplayProvenance`, over typed opaque references (`RefKind`) and a six-way
  `AuthorityClass` whose unrecognized values coerce to the weakest reading.
  Additive: the released `outcome_contracts` family is untouched and the
  envelope correlates its records by reference rather than replacing them.
  Reference: `docs/effect-contracts.md`.
- **Published golden vectors** for the effect family
  (`azazel_fabric.testing.effect`, fixtures under `tests/fixtures/effect/`) —
  one chain across Edge, Gadget, Knowledge and AZ-06, including a competing
  advisory vector so a consumer that cannot distinguish advice from a decision
  fails against Fabric's own bytes.

### Changed

- `src/azazel_fabric/version.py` is `0.9.0rc2`, and
  `release/v0.9.0rc2.digest.json` records the reproducible manifest of `src/`
  and `pyproject.toml` at this tag. The release workflow verifies both: the tag
  must equal the package version, and the tree must match the manifest.
  Dropping the `.devN` suffix is what activates the release-digest gate — the
  seven tests that skipped while it was set now run.

## [0.9.0rc1] — R1b release candidate (Fabric#23)

A **release candidate**, not the stable release. The tag `v0.9.0rc1` and its
GitHub Release exist so consumers can pin an exact tag instead of `main`, which
is what the plan's "pin an exact release tag" discipline requires and what the
downstream evidence for R1c depends on. Everything below is additive over
`v0.8.0` and non-breaking.

A candidate makes no stability promise. `v0.9.0` is cut only after the plan's
"at least one real producer and two real consumers per non-experimental
contract" gate has linked evidence; until then a consumer that needs stability
stays on `v0.8.0`.

### Added

- **Outcome-as-Evidence shared contracts** (`azazel_fabric.outcome_contracts`,
  merged after `v0.8.0` in `2ccb2e6`/`1cabf11`/`190ffc2`) — `ExecutionRefV0`,
  `MechanismObservationV0`, `OutcomeObservationV0`, and
  `TacticalEffectAssessmentRefV0`, plus `assert_no_runtime_directives`,
  `assert_bounded_fact_payload`, `assert_evidence_chain_consistent`, and
  `canonical_fact_json`. The family keeps execution facts, observed mechanism,
  bounded observation windows, and tactical-effect assessment in four separate
  shapes so a stronger claim cannot hide inside a weaker layer: an observation
  carries no success or causality verdict, a mechanism fact may not carry an
  effect class, and the assessment pins `executable` to `False`. Cross-product
  golden fixtures live under `tests/fixtures/outcome/`. Documented in
  `docs/contracts.md` §6 — this changelog entry and that section close the gap
  where the code was on `main` while every document still described `v0.8.0`.

- **Provisioning contracts** (`azazel_fabric.provisioning_contracts`) — the
  R1a half of the Nexus/Boot program plan's §5 R1 deliverable:
  `InterfaceIdentity`, `StorageDeviceIdentity`, `PlatformIdentity`,
  `HardwareInventory`, `ResourceProfile` (+ `ThermalBudget` / `PowerBudget`),
  `OperatorConfirmation`, `InterfaceIdentitySelector`, `InterfaceAssignment`,
  `CaptureSupport`, `IsolationProperty`, `TopologyProfile`,
  `CommissioningRecord`, `ProductManifest`, `AssetManifest`, `ModelManifest`,
  `FeatureMinimum` / `TestedCompatibilityTuple` / `CompatibilityManifest`,
  `ProposedGenerationDescriptor`, observation-only `ActivationReceipt`,
  `AuditCheckpointProjection`, and `SecurityStateProjection`; canonical bytes
  and content digests (`integrity`); open extension registries naming
  `azazel-nexus` and `azazel-boot` (`registry`); and recursive fail-closed
  validation (`validation`).

- **M.I.O. contracts** (`azazel_fabric.mio_contracts`) — the other half of R1:
  `SituationFrame`, `AliasScope`, `RedactionRecord`, `SanitizedRemoteFrame`,
  `Claim`, `ClaimSet`, `Disagreement`, `AdvisoryResult`, and `MergedAdvisory`,
  plus `assert_advisory_inert`, `assert_frame_sanitized_for_egress`,
  `assert_claim_provenance_preserved`, `assert_no_mio_directives`, and
  `canonical_mio_json`.

- **R1a conformance kit** — `azazel_fabric.testing.load_golden_provisioning` /
  `golden_provisioning_names` / `GOLDEN_PROVISIONING_NEGATIVE` /
  `GOLDEN_REFERENCE_AS_OF`, with the same content committed under
  `tests/fixtures/provisioning/` and `tests/fixtures/mio/` so consumers reading
  the JSON and consumers importing the loader cannot diverge. Ten of the
  vectors are negative: directive-bearing, unknown-version, expired,
  digest-mismatched, ambiguous-identity, tier-claiming, inferred-role,
  restricted-egress, executable-advisory, and follow-up-requesting payloads that
  a conforming consumer must reject.

- **Static boundary gates** — `tests/test_provisioning_no_side_effects.py`
  (import allowlist, no module-level execution, no dangerous builtin call, and a
  subprocess import-delta proving the new modules pull in nothing that probes
  the OS, touches the network, spawns a process, installs, or controls a
  runtime), answering the program plan's SR-09 finding. The existing
  `tests/test_no_enforcement_bypass.py` surface now enumerates the
  `outcome_contracts`, `provisioning_contracts`, and `mio_contracts` families as
  well, so every new model is covered by the extra-field, directive-field-name,
  pinned-literal, safety-classification, and `Literal[bool]` discovery gates.

### Authority rules encoded in the shapes

*Fabric describes. Knowledge advises. Edge decides and enforces. Nexus and Boot
integrate without creating another decision authority.*

- A `ResourceProfile` records a **measured envelope** — `usable_memory_mib`
  after firmware reservation — and carries no tier, capability state, or
  authority level. The program plan's RAM-tier thresholds (§5 R2) are an open
  decision: they compare measured-usable MiB against nominal boundaries, so a
  nominal 16 GB host measuring 16095 MiB usable selects `core` rather than
  `lite`. That host is the golden fixture, and no contract records the
  conclusion, so ratifying corrected thresholds later changes no contract.
  `CORE`/`LITE`/`FULL` are capability states, never authority levels, and
  effective capability is the intersection of resource, topology, verified
  assets, and trust/health.
- An interface role is **confirmed, never inferred**. A selector requires bus
  path, permanent MAC, and at least one of PCI/USB identity or serial;
  MAC-only matching is structurally impossible; the composite key excludes the
  kernel interface name; and resolution fails closed on zero or multiple
  matches.
- `ProposedGenerationDescriptor` describes and `ActivationReceipt` observes.
  Neither authorizes. Command, unit, route, firewall, device-path, executor,
  boolean-authorization, and trust-decision fields are recursively rejected in
  any spelling.
- M.I.O. output is inert: `executable`, `may_request_followup`, and
  `contains_links` are pinned `False`, a sanitized frame cannot declare raw
  evidence or carry `sensitive`/`restricted` content off the node, and a merge
  keeps every claim's provenance and presents contradictions separately.
- Audit-checkpoint and security-state projections standardize the envelope
  only: **no chain, no chain verification, no trust decision** — the same
  boundary `azazel_fabric.audit` has held since `v0.4.0`.

### Documentation

- `docs/provisioning-contracts.md` — new family reference, authority rules, the
  feature-to-minimum-Fabric-version matrix, and the conformance kit.
- `docs/contracts.md` §6/§7, `docs/release-compatibility.md`, and `README.md`
  reconciled against the shipped tags and the re-verified consumer pins
  (Knowledge and Boot both declare `v0.8.0`; the previous `v0.6.0` / "no lock"
  entries were stale).

### Release-candidate digest (the R1b deliverable)

`release/v0.9.0rc1.digest.json` records a sha256 over every file a consumer
receives by pinning this tag — the packaged surface under `src/` plus
`pyproject.toml` — and a roll-up `content_digest` over that record. The file
list comes from `git ls-files`, so the manifest is reproducible from the commit
rather than from whatever happens to be on someone's disk. Regenerate or verify
it with `tools/rc_digest.py`, and `tests/test_release_candidate_digest.py`
fails closed when the manifest goes stale against the tree, when a releasable
(non-`.dev`) version carries no manifest, or when an entry in the file map is
altered or dropped.

**The detached signature over that digest is not in this release.** It requires
the release owner's key, which no automation here holds. `signature_ref` is
excluded from the digest for exactly that reason: a locator assigned after
signing cannot be covered by the bytes that were signed. R1b is therefore
complete as to the digest and open as to the signature.

### Still required before the stable `v0.9.0`

R1c: downstream evidence, meaning at least one real producer and two real
consumers per non-experimental cross-product contract, with the runs linked.
As of this candidate, no consumer imports `azazel_fabric.outcome_contracts`,
`provisioning_contracts`, or `mio_contracts` — that adoption is
[Edge#413](https://github.com/01rabbit/Azazel-Edge/issues/413),
[Nexus#15](https://github.com/01rabbit/Azazel-Nexus/issues/15), and
[Boot#16](https://github.com/01rabbit/Azazel-Boot/issues/16). The program-side
attestation aggregator that R1c also needs is Azazel-owned and does not exist.

## [0.8.0] — Canonical Edge-decision transport signature (Fabric#9)

Adds `azazel_fabric.deception_contracts.decision_signing`, the single
authoritative definition of the HMAC-SHA256 transport signature over an Edge
decision envelope: `canonical_decision_bytes`, `compute_decision_signature`,
`sign_decision`, `verify_decision_signature`, and
`DEFAULT_DECISION_SIGNATURE_FIELD`. Additive and non-breaking. Fabric describes
the wire format only — a signature proves origin/integrity, never authority.
The canonicalization is byte-identical to AZ-06's
`azazel_deception.runtime.transport`, so an Edge-side producer and the
Azazel-Deception consumer sign and verify the same bytes and interoperate
(covered by `tests/test_decision_signing.py`). Enables the Edge-side canonical
`EnvironmentTransitionDecision` producer to sign decisions the AZ-06
`TransitionExecutor` already verifies.

Hardening: the signing-key coercion now rejects a non-`str`/bytes-like key with
`TypeError` instead of falling through to `bytes(key)`, which for an integer
would silently return an all-zero (fully predictable) key. A misconfigured
numeric key now fails loudly rather than signing/verifying with degenerate key
material.

**`v0.8.0` also carries the engagement contracts described under `[0.7.0]`
below.** No `v0.7.0` tag was ever cut, so `v0.8.0` is the first — and only —
release a consumer can pin to obtain `azazel_fabric.engagement_contracts`. The
published `v0.8.0` release notes list both PRs (`Fabric#8` engagement contracts
and `Fabric#9` decision signing) and compare `v0.6.0...v0.8.0`.

## [0.7.0] — MITRE Engage-aligned engagement contracts — **NEVER RELEASED**

> **There is no `v0.7.0` tag and no `v0.7.0` GitHub Release, and none will be
> created.** Verified 2026-09-19 from both sides: the repository's tags are
> `v0.1.0`–`v0.6.0` and `v0.8.0`, the published releases are the same set, and
> `src/azazel_fabric/engagement_contracts/` is absent at `v0.6.0` and present at
> `v0.8.0`. **Pin `v0.8.0` to obtain the engagement contracts — pinning
> `v0.7.0` resolves to nothing.**
>
> This section is kept rather than folded into `[0.8.0]` because the changelog
> is the release-*history* record: the work below was prepared and reviewed as a
> `0.7.0` increment and then shipped inside `v0.8.0`, and rewriting that history
> would erase why the version numbers skip. `[0.8.0]` above points here, and
> `docs/release-compatibility.md` records the same correction. Azazel-Deception
> logged this as a Fabric-side defect in its `docs/fabric-pin.md`.

Adds one additive, non-breaking contract family, `engagement_contracts`
(Azazel-Fabric#8): `EngagementObjective`/`Approach`/`Activity`, `AttackerReaction`,
`EngagementConstraint`, `EngagementTrigger`, `EngagementCandidate`,
`PostureSuggestion`, `EngagementAdvisory`, `EngagementOutcome`, `EngagementEvent`,
and `validation` helpers (`assert_candidate_not_executable`,
`assert_engagement_advisory_only`, `assert_no_engagement_directives`). No change
to existing `schema`, `cti_contracts`, `deception_contracts`, `view`, or helper
modules; consumers on `v0.6.0` upgrade by bumping the pin with nothing to
migrate. Grounded in `Azazel-Edge#319` and `Azazel#60`.

Authority rule unchanged and encoded in the shapes: *Engage expresses intent.
Knowledge advises. Fabric describes. Edge decides and enforces.* A candidate is
`candidate_only` (a request, never a command), the advisory is `advisory_only`
and non-executable, activities map 1:1 onto bounded Azazel actions, and unknown
enum values / schema versions / smuggled runtime-directive or authority-bearing
fields fail closed.

## [0.6.0] — AZ-06 effectiveness observation + transition catalog

Adds two additive, non-breaking AZ-06 contract families. No change to existing
`schema`, `cti_contracts`, `view`, helper modules, or the `v0.5.0`
`deception_contracts`; consumers on `v0.5.0` upgrade by bumping the pin with
nothing to migrate. Grounded in `Azazel-Deception#6`, `Azazel-Knowledge#52`/`#58`,
and `Azazel#61`.

Authority rule unchanged and encoded in the shapes: *Fabric describes. Edge
decides. Deception Host materializes.* Observations are `descriptive_only`, the
effectiveness advisory is `advisory_only` and non-executable, and the transition
catalog is `descriptive_only` — none can select or authorize an action.

### Added

- **Effectiveness-observation contracts** (`azazel_fabric.deception_contracts`)
  — `InteractionObservation`, a **fact-only** event carrying the honesty ladder
  in its shape (`ObservationClass` = interaction / reaction / outcome; layer-4
  *inference* is deliberately absent), with `InteractionSurface`, `ReactionKind`,
  `ConfounderTag`, and a `RuntimeContext` (tier/architecture/adapter/active-omitted
  components/resource saturation/capability drift) so a consumer can separate
  narrative effectiveness from host-capacity effects. An `interaction`-class
  observation cannot carry a `reaction_kind` — a stronger claim can't hide in a
  weaker layer.
- **Effectiveness advisory** — `EffectivenessAdvisory`, Knowledge's layer-4
  output: `advisory_only`, `executable` pinned False, carrying an assessment
  with `confidence`, **`counter_evidence`**, `observation_refs`, and `unknowns`.
- **Honesty invariant guard** (`azazel_fabric.deception_contracts.validation`)
  — `assert_no_effectiveness_verdict` / `contains_effectiveness_verdict` /
  `BANNED_EFFECTIVENESS_VERDICT_FIELDS` reject belief / deception-success /
  effectiveness-verdict fields (including `confidence`) on a fact-only
  observation payload — *interaction does not prove attacker belief*.
- **Finite-state transition catalog** (`azazel_fabric.deception_contracts.transitions`)
  — `FiniteStateTransition` (mandatory current/target state, evidence-backed
  trigger, expected observation, resource/time bounds, `max_new_surfaces`,
  rollback state, non-empty termination conditions, `requires_edge_approval`
  pinned True, decoy egress pinned denied) and `TransitionCatalog`, a frozen set
  bound to one package identity by a normalize-first `catalog_digest`
  (`azazel_fabric.deception_integrity.catalog_content_digest` /
  `assert_catalog_content_digest`). `select_transition` fails closed on any
  pair not pre-authored into the catalog.
- Golden factories `make_interaction_observation`, `make_effectiveness_advisory`,
  `make_transition_catalog` in `azazel_fabric.testing`.

## [0.5.0] — AZ-06 canonical deception-environment contracts

Adds the canonical AZ-06 deception-environment contract family
(`Azazel-Fabric#9`) as **additive, non-breaking** code. No change to
`schema`, `cti_contracts`, `view`, or the Phase-5/6 helper modules;
consumers on `v0.4.0` upgrade by bumping the pin, with nothing to migrate.
AZ-06 (`Azazel-Deception#1`) replaces its bootstrap shapes by pinning this
tag; Edge (`Azazel-Edge#325`) consumes the same golden factories.

Authority rule, unchanged and now encoded in the models: *Fabric describes.
Edge decides and enforces. Deception Host materializes, transitions, records,
and resets.* The contract family is intentionally incapable of turning a
capability report, package, placement plan, or advisory into runtime
authority.

### Added

- `azazel_fabric.deception_contracts` — canonical `*/v0.1` wire family:
  `DeceptionPackage`, `NarrativeManifest`, `NarrativeConsistencyReport`,
  `CredentialLure`, `DecoySurface`, `ComponentManifest`, `ImageManifest` /
  `ImagePlatform`, `RuntimeRequirements`, `HostCapabilities`,
  `DeploymentTier`, `PlacementPlan`, the Edge-only
  `EnvironmentActivationDecision` / `EnvironmentTransitionDecision` /
  `EnvironmentTerminationDecision` (with expiry), `EnvironmentEvent`,
  `EnvironmentOutcome`, and shared `ResourceBudget` / `SafetyPolicy` models.
  `HostCapabilities` and `PlacementPlan` carry explicit `descriptive_only`
  authority; unrestricted decoy egress and production access are
  unrepresentable in the canonical safety policy.
- `azazel_fabric.deception_contracts.validation` — fail-closed
  directive-field rejection (`BANNED_RUNTIME_DIRECTIVE_FIELDS`,
  `contains_runtime_directive`, `assert_no_runtime_directives`).
- `azazel_fabric.deception_integrity` — canonical normalize-first package
  content-digest semantics (SHA-256) shared by signer and verifier.
- `azazel_fabric.testing.deception` — shared ARM64/AMD64 golden fixture
  factories consumed by Edge and AZ-06 CI.
- Package/tier minimum-vs-maximum budget validation, finite package maximum
  resource budgets including a bandwidth ceiling, and OCI
  provenance/SBOM/verification fields on `ImageManifest`.
- `docs/deception-contracts.md`, `docs/azazel-deception-contracts.md`, and
  `docs/deception-contracts-status.md` — contract family, ownership, and
  adoption status.
- `LICENSE` — MIT (owner decision 2026-07-11: unlicensed series repos align
  to MIT). `pyproject.toml` `license` field and `README.md` updated from
  `TBD` to MIT accordingly.

### Not in this release

The full artifact/persona/environment-state contract family for AZ-06
Phase 2, Knowledge/Gadget adoption of the new contract subset, and
cross-repository live/HIL safety orchestration remain tracked on
`Azazel-Fabric#9` and are not part of `v0.5.0`.

## [0.4.0] — Phase 5 helpers + Phase 6 adoption tooling

Adds the five Phase-5/Phase-6 helper modules — the `paths`/`api`/`notify`/
`audit` helpers that were "design proposal / not frozen" since `v0.1.0`, plus
the `testing` module — as **additive, non-breaking** code. No change to
`schema`, `cti_contracts`, or `view` semantics; consumers on `v0.3.0` upgrade by
bumping the pin, with nothing to migrate.

Two owner decisions (2026-07-10/11) shaped this release:

- **Audit hash chains stay product-local.** `azazel_fabric.audit` ships the
  shared `AuditEvent` projection and JSONL format **only** — **no hash chain,
  no chain verification**. Edge's P0 hash-chain / tamper-evidence audit is
  deliberately out of Fabric's scope and lives in Edge. Stated explicitly in the
  module docstring and `docs/contracts.md` §1.
- **`contracts.md` §3 (api) / §4 (notify) / §5 (paths) are ratified as
  implemented** — built as specified, with deviations noted inline in that doc.

### Added

- `azazel_fabric.paths` — candidate-path **hints** per `contracts.md` §5:
  `candidate_runtime_dirs` / `candidate_config_dirs` / `candidate_log_dirs` /
  `candidate_dirs` / `preferred_dir`, `normalize_product` (legacy alias
  resolution: `azazel-pi`→`edge`, `azazel-zero`→`gadget`), and a **dry-run-only**
  `plan_migration` (`MigrationPlan`/`MigrationStep`) that describes a
  legacy→canonical move and never performs one. Pure/deterministic — no
  filesystem, environment, or clock reads. Hints, never authority: a product
  keeps its own path schema.
- `azazel_fabric.api` — framework-neutral security-posture helpers per
  `contracts.md` §3: the shared JSON error model (`ErrorEnvelope`/`ErrorBody`,
  `error_payload`, `fail_closed_error`), the ordered role vocabulary
  (`ROLES`, `role_rank`, `role_allows`, fail-closed), and token-header
  extraction (`TOKEN_HEADER`/`COMPAT_TOKEN_HEADER`, `extract_token`,
  constant-time `token_matches`). No Flask/FastAPI import in core — adapters
  stay optional extras.
- `azazel_fabric.notify` — the shared `NotificationEvent` payload model per
  `contracts.md` §4 (closed `info`/`warning`/`critical` severity), plus pure
  transport mappers `to_ntfy_payload` / `to_mattermost_payload` that build a
  payload and **never send** (no network in Fabric).
- `azazel_fabric.audit` — `AuditEvent` projection (`project_audit_event`,
  `make_event_id`) and JSONL formatters (`to_jsonl_line` / `from_jsonl_line` /
  `iter_jsonl` / `write_jsonl` / `read_jsonl`). **No chain, no verification**
  (owner decision above).
- `azazel_fabric.testing` — shared factories (`make_*` populated / `minimal_*`
  required-only for `StateSnapshot`, `ModeState`, `StatusView`, `AuditEvent`,
  `ActionIntent`, `CtiContextRequest`/`Response`) and invariant assertions
  (`assert_advisory_only`, `assert_behavioral_absent_not_null`). **No pytest
  dependency** — plain functions usable from any test framework.
- `docs/adoption-guide.md` — day-1 adoption playbook for a new series product
  (e.g. the reserved `Azazel-Boot`): tag-pinning, the guarded-import idiom,
  adopt-`view`-first, emit-alongside, using `azazel_fabric.testing`, the
  advisory-only doctrine, and the pointer to the umbrella naming spec. Linked
  from `README.md`.
- Unit tests for all five modules (46 new): path purity/determinism and legacy
  resolution, audit round-trips and the no-chain guard, error-shape building and
  fail-closed roles/token auth, notify round-trips and transport mapping, and
  testing-module factory validity + invariant assertions.

### Changed

- Docs synced to shipped reality: `contracts.md` §3–§5 headers moved from
  "design proposal / not frozen" to **ratified/implemented (`v0.4.0`)** with
  deviations noted inline; `design-principles.md` §2 module-table statuses;
  `repository-layout.md` tree marked real (and reconciled with the actual
  files); `migration-plan.md` Phase 5 → **Implemented (`v0.4.0`; consumer
  adoption follows as separate PRs)** and Phase 6 → **Complete** per the owner's
  definition (adoption guide + testing module); `README.md` module list and doc
  table updated.

## [0.3.0] — renamed to Azazel-Fabric

**BREAKING:**

- Distribution name changed: `azazel-common` → `azazel-fabric`.
- Import namespace changed: `azazel_common` → `azazel_fabric`.
- Repository renamed: `01rabbit/Azazel-Common` → `01rabbit/Azazel-Fabric`
  (old repository URLs redirect).

`v0.1.0` and `v0.2.0` tags remain installable under the old
`azazel-common`/`azazel_common` names — pinning those tags is unaffected.
Consumers (currently Azazel-Gadget, which pins `v0.2.0`) migrate by bumping
their pin to `v0.3.0` and switching their imports from `azazel_common` to
`azazel_fabric`; no schema or behavior changes accompany the rename.

### Documentation

- Synced the six `docs/` design documents with shipped reality: they
  previously still read as a frozen Phase-0 "design proposal only, no
  implementation code has been written" snapshot despite `v0.1.0`/`v0.2.0`
  having shipped real, CI-tested code. Added accurate status headers,
  per-module/per-phase status lines, a consumer-status table in
  `README.md` (Gadget shipping, Edge plan-stage, CTI not adopted), and an
  honest note in `migration-plan.md` that Phase 4 (Gadget) landed ahead of
  Phases 2/3. No code, dependency, or test changes.

## [0.2.0] — shared status view-model

Adds `azazel_common.view`, the first shared *mechanism* beyond passive schemas:
a status view-model both Edge and Gadget derive and render from, so the two
products present the same status the same way. Common owns the view-model; each
product keeps its own renderer (see `docs/design-principles.md` §3.1).

### Added

- `azazel_common.view.StatusView` — the normalized data a status surface reads
  (mode, posture, headline, reasons, operator wording, current action, next
  actions, health dimensions, evidence), plus `HealthDimension`.
- `azazel_common.view.build_status_view` — the single shared builder both
  products call, with shared `derive_posture` / `derive_headline` logic and a
  `from_state_snapshot` convenience path.
- Edge-lineage but a **generalized superset**: every product-specific field
  rides in `StatusView.product_view`, so Gadget-only concepts (`deception`
  posture, `scapegoat` decoy state, canary telemetry) are never dropped;
  `posture` and `HealthDimension.status` are open enums.
- Unit tests for shared posture/headline derivation and superset preservation.

### Changed

- Charter update: `docs/design-principles.md` (§2, new §3.1) and
  `docs/architecture.md` now allow a shared display *view-model* in Common
  while keeping the *renderer* (Web/TUI/E-Paper) product-side. The
  sibling-not-subset invariant (§4.4) is preserved.

## [0.1.0] — schema-only / contract-only

First release. Ships the shared schema and the CTI advisory contract only, per
`docs/migration-plan.md` Phase 1. No `paths`/`audit`/`api`/`notify` helpers, no
execution logic, no product integration.

### Added

- `azazel_common.schema`: `StateSnapshot`, `ModeState`, `ActionIntent` (with
  abstract, data-only `ObservePlan`..`ReleasePlan` plan descriptions),
  `EvidenceRef`, `DecisionExplanation`, `AuditEvent`, `TrustCapsule`.
- `azazel_common.cti_contracts`: `CtiEventBatch`, `CtiFlowBatch`,
  `CtiReactionBatch`, `CtiContextRequest`, `CtiContextResponse`, `IocMatch`,
  `BehavioralCtiBlock`.
- Advisory-only invariant enforced in `CtiContextResponse`: directive-shaped
  fields (`directive`, `must_execute`, `override`, `required_action`) are
  rejected, and `behavioral_cti` is encoded as absent — never `null`, never an
  empty object — when there is nothing to report.
- Unit tests covering construction, (de)serialization round-trips, and the CTI
  advisory invariants.
- `pyproject.toml` (Pydantic-only runtime dependency; `flask`/`fastapi`/`test`
  optional extras) and GitHub Actions CI running the test suite.

[Unreleased]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.9.0rc1...HEAD
[0.9.0rc1]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.8.0...v0.9.0rc1
[0.8.0]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.6.0...v0.8.0
[0.4.0]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/01rabbit/Azazel-Fabric/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/01rabbit/Azazel-Fabric/releases/tag/v0.2.0
[0.1.0]: https://github.com/01rabbit/Azazel-Fabric/releases/tag/v0.1.0
