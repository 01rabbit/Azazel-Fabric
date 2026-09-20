# Release Compatibility and Support Truth

Status: **R0 coordination baseline, 2026-09-19; re-verified 2026-09-19 against
the consumer repositories.** This document records the published Fabric release
and observed consumer dependency declarations. An observed pin is not, by
itself, an interoperability certification.

## Current Fabric release

The latest **stable** release is `v0.8.0`. The latest **published** tag is the
release candidate `v0.9.0rc4`, which narrows what an `EffectObservation` may
claim on top of `v0.9.0rc3` — the widened `effect_contracts` reference grammar
— which sits on `v0.9.0rc2`, the canonical `DefensiveState` vocabulary and the
cross-series `effect_contracts` family, which in turn sits on `v0.9.0rc1`,
itself additive contract work (`outcome_contracts`, and the R1a
`provisioning_contracts` / `mio_contracts` families) over `v0.8.0`.

A candidate is pinnable but makes no stability promise. It exists so a consumer
can pin an exact tag — never a branch — while producing the downstream evidence
`v0.9.0` requires. A consumer that needs stability stays on `v0.8.0`; a consumer
adopting the new contract families pins the newest candidate, `v0.9.0rc4`, and
expects to re-pin to `v0.9.0`.

**A consumer adopting `effect_contracts` should move to `v0.9.0rc3`, and this
is the first candidate move in this series that is not optional for its
adopter.** Under the `rc2` grammar a typed reference's body could not contain a
colon, so every hierarchical reference the series mints — `surface:http:8080`
and `artifact:honey:invoice-2026` from Azazel-Deception, `edge:nft:1` from
Azazel-Edge — was refused by every slot requiring a typed ref. That family had
no possible producer at `rc2`. A consumer on `rc1` or `rc2` that does not use
`effect_contracts` is unaffected: no released symbol changed, and the grammar
only ever accepts more in the slots that require a typed ref.

**`v0.9.0rc4` is the first non-additive candidate in this series, and a
consumer cannot treat a candidate move as free from here on.** An
`EffectObservation` may claim only `observed_fact` or `active_materialized`
(Fabric#52); the four other authority classes were accepted, which let a record
*reporting* an effect assert authority *over* it — the exact confusion
`DefensiveEffectRef` has refused in the other direction since the family
shipped. A payload that was valid at `rc3` and claims `producer_decision_ref`,
`advisory_inference`, `planned_shadow` or `stale_or_unknown` is refused at
`rc4`. This lands before `v0.9.0` because the alternative is carrying it into a
stable release, where the same correction would break a stability promise
instead of a candidate one.

The package version in `src/azazel_fabric/version.py`, release tag, and GitHub
release must agree before any release — candidate or stable — is described as
available. A `.devN` version is never a release.

| Release | Contract addition | Compatibility effect |
|---|---|---|
| `v0.5.0` | Canonical AZ-06 package, capability, placement, decision, event, and outcome contracts | Additive baseline for the AZ-06 contract family |
| `v0.6.0` | Effectiveness-observation and finite-state transition catalog contracts | Additive |
| `v0.7.0` | **Never released.** No tag, no GitHub Release. The advisory-only engagement contracts it describes shipped inside `v0.8.0` | Not pinnable — a consumer that pins `v0.7.0` resolves to nothing |
| `v0.8.0` | Canonical HMAC-SHA256 Edge-decision transport signature helpers **and** the advisory-only engagement contracts | Additive; signatures prove integrity/origin, not authority |
| `v0.9.0rc1` (candidate) | Outcome-as-Evidence shared facts (`outcome_contracts`); R1a provisioning and M.I.O. contract families (`provisioning_contracts`, `mio_contracts`) | Additive; pinnable, **not stable** — adopt to produce R1c evidence, expect to re-pin to `v0.9.0` |
| `v0.9.0rc2` (candidate) | Canonical `DefensiveState` vocabulary (`schema.defensive_state`, Fabric#14); cross-series effect / outcome / terrain family (`effect_contracts`, Fabric#15) | Additive; pinnable, **not stable**. No released symbol changed, so a consumer on `v0.9.0rc1` may stay there |
| `v0.9.0rc3` (candidate) | A typed cross-series reference may carry further colons in its body (`effect_contracts/refs.py`) | Additive for every consumer; **required for an `effect_contracts` adopter** — at `rc2` the grammar refused every hierarchical reference in the series, so the family had no possible producer |
| `v0.9.0rc4` (candidate) | An `EffectObservation` may claim only `observed_fact` or `active_materialized` (`effect_contracts/models.py`, Fabric#52) | **Non-additive — the first in this series.** Input accepted at `rc3` is refused at `rc4`. Required before `v0.9.0` stable; a producer that emitted an observation under any other authority class must correct it, not re-pin around it |
| `v0.9.0rc5` (candidate, unpublished) | Presented-terrain provenance: `source_effect_ref`, `trace_id`, `synthetic_identity_refs`, `synthetic_credential_refs`; `activation_decision_ref` becomes optional (`effect_contracts`, Fabric#51) | **Additive.** Every `rc4` terrain payload still validates and still chains — checked by `test_an_rc4_terrain_payload_still_validates`. What changes is that a decision-less effect can be chained to a terrain **at all**, which `rc4` made structurally impossible |

All consumer deployments MUST pin an exact compatible Fabric tag or immutable
image lock. They MUST NOT pin a branch. A product chooses when to adopt a newer
compatible tag and must demonstrate its own integration tests before claiming
support.

## Observed consumer declarations

| Consumer | Observed declaration | Interpretation |
|---|---|---|
| Azazel-Edge | `v0.9.0rc2` in `requirements/fabric.txt` | Current reference authority consumer. An **optional** extra: Edge's arbiter runs with no Fabric installed |
| Azazel-Gadget | `v0.8.0` in `requirements.txt` | The only consumer on the latest **stable** tag. It uses `view` + `schema.mode` and none of the candidate families, so it has no reason to carry a candidate (Azazel-Gadget#22) |
| Azazel-Knowledge | `v0.9.0rc2` in the `api` optional dependency (`pyproject.toml`) | Advisory API boundary only; core stays dependency-minimal |
| Azazel-Deception | `v0.9.0rc2` in `pyproject.toml` | Current AZ-06 runtime declaration |
| Azazel-Nexus | **no declaration** | No longer documentation-only — it carries code with deliberately zero dependencies. Its absence from this table is a design choice, not an omission |
| Azazel-Boot | `v0.9.0rc1` in the `fabric` optional extra (`pyproject.toml`, ADR-0004) | Exact-tag source pin, one release behind. An image lock is still required before a Boot implementation release |

Verification note (2026-09-20): every row was read directly from that
repository's dependency declaration. The Gadget row had been carried forward
from an earlier audit and was stale by four releases; it is now read from
`requirements.txt:19` at Azazel-Gadget `main` `7aeb923`, and that repository's
CI installs the manifest, so the tag it names is exercised rather than only
declared.

`v0.8.0` is no longer the point the consumers agree on: four of them declare a
`v0.9.0` candidate and they do not agree on which one. That is the expected
shape while candidates circulate — each product adopts on its own schedule —
but it means "the reference release" is not a single answer right now, and a
statement that names one is wrong until `v0.9.0` is cut.

## Contract family adoption and the R1c gate

R1c — the stable `v0.9.0` — waits on downstream evidence: **at least one real
producer and two real consumers** per non-experimental contract family
(`Azazel/docs/roadmaps/nexus-boot-program-plan.md` §5 R1, Fabric#23). The gate
is per family, not per release: a release carrying five families does not clear
it because one of them is well adopted.

A **producer** constructs an instance of the contract for another product to
read. A **consumer** parses or validates one it received. A module that only
imports a constant or a guard function is neither: it is using Fabric as a
library, not exchanging a contract through it.

| Family | Producers | Consumers | R1c gate |
|---|---|---|---|
| `cti_contracts` | — | Azazel-Knowledge:`src/azazel_knowledge/api/contracts.py` | not met |
| `deception_contracts` | Azazel-Edge:`py/azazel_edge/deception_transition.py`, Azazel-Deception:`src/azazel_deception/runtime/observation_export.py` | Azazel-Deception:`src/azazel_deception/runtime/transitions.py`, Azazel-Knowledge:`src/azazel_knowledge/api/contracts.py` | **met** |
| `effect_contracts` | Azazel-Deception:`src/azazel_deception/runtime/effect_projection.py` | — | not met |
| `engagement_contracts` | Azazel-Edge:`py/azazel_edge/engagement/candidate.py`, Azazel-Knowledge:`src/azazel_knowledge/api/contracts.py` | Azazel-Knowledge:`src/azazel_knowledge/api/contracts.py`, Azazel-Edge:`py/azazel_edge/engagement_advisory_client.py` | **met** |
| `mio_contracts` | — | — | not met |
| `outcome_contracts` | Azazel-Edge:`py/azazel_edge/outcome/shared_export.py`, Azazel-Deception:`src/azazel_deception/runtime/outcome_export.py` | Azazel-Knowledge:`src/azazel_knowledge/api/contracts.py`, Azazel-Deception:`src/azazel_deception/runtime/producer_evidence.py` | **met** |
| `provisioning_contracts` | — | — | not met |

Three families clear the gate, and each does so on a real round trip rather
than a count. `deception_contracts`: Edge constructs and signs an
`EnvironmentTransitionDecision` that Deception verifies, and Deception emits
`InteractionObservation` records that Knowledge validates at its API boundary.
Producer and consumer are different products in both directions, which is what
the gate is asking about. `engagement_contracts` and `outcome_contracts` are
the others, for the reasons set out below.

Five patterns in that table are worth naming rather than leaving to be
noticed.

**`engagement_contracts` cleared the gate on a round trip, not a count.**
Until Azazel-Edge#418 this family had two producers and no consumer: Edge and
Knowledge both wrote the Engage-aligned types and neither read what the other
wrote. A contract that has only ever been serialized is not known to
interoperate — the first read is where a disagreement surfaces.

Both reads now exist, in opposite directions:

| Direction | Contract | Reader |
| --- | --- | --- |
| Edge → Knowledge | `EngagementEvent` | Azazel-Knowledge#105 |
| Knowledge → Edge | `EngagementAdvisory` | Azazel-Edge#418 |

Edge's `EngagementEvent` builder had said "for audit / Knowledge ingest" in
its own docstring since it was written; Knowledge simply had no lane to put
one in. It has one now, and the lane keeps the Engage vocabulary **verbatim
and mapped to nothing**: three of the eight `activity` values coincide with
Knowledge's `reaction.action_applied` and five do not, and deciding that
`redirect_to_decoy` "is" `deception` would invent a correspondence between two
product vocabularies. An engagement event is its own lane there, not a
reaction in disguise.

One caveat stays on the record rather than being quietly dropped now that the
row reads **met**: Edge's advisory reader has **no runtime caller yet**. When
Edge consults Knowledge for engagement context — on what trigger, about which
entity — is a product decision that was left with the product, and the module
takes a caller-supplied request body. It is a consumer in the sense the gate
means (it parses and validates an instance it received, against Knowledge's
own contract shape); it is not yet a live path.

**Deception was considered for this and deliberately not used.** It is the
obvious candidate by proximity, but `PostureSuggestion.supported_activities`
names `redirect_to_decoy`, `expose_decoy_surface` and `collect_credentials` —
AZ-06's own actions. For every other consumer an advisory is about somebody
else's actions; for Deception alone it would be about its own, which puts
"read the advice" one step from "choose among the activities it lists". AZ-06
materializes an Edge-approved environment and does not select. Clearing a gate
is not worth thinning the boundary it sits behind.

**`outcome_contracts` cleared the gate by finding its second consumer, not by
building one.** Edge's `outcome/shared_export.py` builds these four records
from Fabric's models and dumps them with, in its own words, "deliberately no
fallback" — a record Fabric did not validate must not travel as one that it
did. Nothing had ever held up the other end. Azazel-Knowledge#106 is the
reader.

The second consumer was already running. Azazel-Deception's
`runtime/producer_evidence.py` says so in its own first line — "Deception
consumes an already-observed REDIRECTION mechanism fact" — and it had never
imported Fabric to do it. It restated the contract instead: a 14-name field
list identical to `MechanismObservationV0`'s, a copy of the banned-key set,
and five bound constants matching `outcome_contracts/validation.py`
byte-for-byte. `runtime/outcome_export.py` was in the same state on the
producer side, assembling the `OutcomeObservationV0` wire shape by hand.
Azazel-Deception#45 routed both ends through the models. AZ-06 can import
Fabric — it is a core dependency there, not an optional extra — so unlike
Knowledge it was fixed by construction rather than by a drift test.

What makes that row worth reading twice is what it looked like *before*.
Knowledge already had the whole storage lane — four tables since its migration
`0005`, plus a module validating the wire shapes on its own — and would have
looked like an obvious consumer to anyone grepping for the record names. It was
not one: no Fabric model had ever seen those payloads. **Storing a shape that
happens to match is not consuming a contract**, which is the same distinction
Azazel-Edge#413 drew about Edge's own producer side ("byte-for-byte identical
to Fabric's models by coincidence of maintenance rather than by construction").
The row stayed empty until a Fabric model actually decided what got in.

That coincidence had already cost something measurable, and in two products at
once. Knowledge's independent copy of the rules was missing `effectiveness`
and `initiative_score`, which Fabric had added to the tactical-claim refusals
— so a producer barred from writing `tactical_effect` into a descriptive fact
map could have written `effectiveness: 0.9` and meant the same thing.
Deception's independent copy was missing **the same two keys**. Neither
product had done anything wrong that the other had not; both were maintaining
a second statement of somebody else's contract, and the same addition passed
both by.

Deception's copy is gone. Knowledge cannot import Fabric in the module that
stores these (its worker runs without the `api` extra), so the second
statement is permanent there; it is now pinned field-for-field against these
models by a drift test instead of by maintenance.

**A citation can be missing because the adoption looks like something else.**
The `outcome_contracts` consumer column read `—` for as long as it did while
two consumers were running, and neither was hiding: Knowledge had four tables
and a validator for these records, Deception had an adapter that said
"consumes" in its first line. What neither had was an import. This is the
sibling of the `grep` warning below — there, a name match was mistaken for
adoption; here, real adoption went uncounted because it was spelled without
the contract's name. Both are answered the same way: read the import and the
direction.

**`cti_contracts` has a consumer and no producer, and that is the schedule
rather than an oversight.** This row is the opposite shape to the one above,
so it was checked the same way and the answer came out the other way: there is
no unrecorded producer to find.

The contract names who may be one. `SourceProduct = Literal["edge", "gadget"]`
is on every ingest envelope and on `CtiContextRequest`, so exactly two
products can legally produce here, and neither does:

- **Azazel-Edge has no such code, by its own plan.** Its adapter plan calls the
  CTI integration "a next-fiscal-year-onward (FY2027+) plan ... not a
  near-term deliverable", and says the request builders would be "new code,
  not adaptations of existing sites". Edge does push data upstream today —
  `integrations/upstream.py` emits an Edge-local `format_version: v1`
  envelope and `integrations/taxii_push.py` pushes STIX 2.1 bundles — but
  neither is a Fabric contract, and Edge's own plan names them as templates a
  builder would grow *from*.
- **Azazel-Gadget does not use this family.** It imports `schema.mode` and
  `view` only. `cti_contracts` has shipped since `v0.1.0`, so the module is
  present in its pin and simply unused.

Outside this package and its own tests, nothing in the series constructs a
`CtiEventBatch`, `CtiFlowBatch`, `CtiReactionBatch` or `CtiContextRequest`.

**The return direction is a ratified non-adoption, not a missing citation.**
`CtiContextResponse` is the CTI → Edge/Gadget half, and Azazel-Knowledge
decided in its ADR-0010 not to emit it, "not forced where shapes genuinely
diverge". Measured, the divergence is not a near miss: Knowledge's context
response and `CtiContextResponse` share 2 field names out of 18, both of those
two differ in type, `CtiContextResponse` is `extra="forbid"` so Knowledge's
other thirteen fields would each be rejected, and `IocMatch.confidence` is
bounded 0.0–1.0 against Knowledge's 0–100 score. Knowledge consumes this
family at its ingest boundary and uses the advisory-only primitives; making it
produce the response model would mean changing a published wire shape, which
is a decision for a new ADR and not something an adoption table should imply
is owed.

**`effect_contracts` had no possible producer at all, and finding that out is
what the gate is for.** This row stayed `— | —` while the family shipped a full
set of models, an authority classification and an adversarial test suite. The
reason was not that nobody had got to it. Azazel-Deception#46 tried, against
the record AZ-06 already keeps, and measured that **every hierarchical
reference the series mints was refused by every slot requiring a typed ref**:
`surface:http:8080`, `artifact:honey:invoice-2026` and `isolation:proof:1` from
AZ-06, `edge:nft:1` from Edge. The grammar split on a colon and then forbade
the body from containing one, so the family was unproducible by construction.
Azazel-Fabric#48 widened the body; `v0.9.0rc2` still carries the narrow form.

AZ-06 is now the producer, for `PresentedTerrainRef` — the record that says
what the defender presented. What it will not do is fill a gap: Fabric requires
a bounded presentation and AZ-06 commonly declares no expiry, so the projection
**refuses** rather than inventing one. An invented bound would report that AZ-06
time-boxed a presentation it did not, in a record that validates. Each
projection also returns the local fields that reach no Fabric slot, because a
lossy projection that says nothing is how a consumer comes to read the Fabric
record as the whole of what AZ-06 observed.

Two of the family's records remain unproducible, and by a cause outside any one
repository: `EffectObservation` and `OutcomeObservationEnvelope` are keyed on an
`effect:`-typed id minted by whoever constructed the effect, and **nothing in
the series mints one**. AZ-06 receives an `EnvironmentActivationDecision`, which
carries none. AZ-06 is the materializer, so those observations are its records
to make — it has nothing to make them against. The chain head
(`DefensiveEffectRef`, `authority_class = producer_decision_ref`) belongs to
Edge, and until Edge mints effect ids this row cannot reach two consumers
however many products adopt it.

One more measurement is on the record because it constrains who can adopt this
family next: `assert_effect_chain_consistent` compares a presented terrain to
`effect_ref.decision_ref`, which is `None` for every authority class except
`producer_decision_ref`, while the terrain's own `activation_decision_ref` is
required and non-empty. A `planned_shadow` effect therefore cannot be chained
to a terrain at all — and shadow is AZ-06's default mode.

**`provisioning_contracts` and `mio_contracts` have neither.** Azazel-Boot
names them in `PLANNED_FABRIC_MODULES` and checks whether they can be imported,
which is a presence probe, not adoption; its own module says so ("a module Boot
would consume and cannot is reported, never assumed"). Counting that probe as a
consumer would clear the R1c gate with nothing exchanged, which is the specific
mistake this table exists to prevent.

### What this table is, and what Fabric can check about it

It is a set of **citations**, not a certification. Fabric's CI cannot see the
consumer repositories, so `tests/test_adoption_matrix.py` enforces only what is
checkable from here:

* every `*_contracts` family in the package has a row, so a family cannot ship
  without its adoption being stated;
* no row names a family the package does not have;
* a row marked **met** lists at least one producer and at least two consumers,
  and a row marked **not met** does not — the verdict cannot drift from its own
  evidence in either direction;
* every cited location is shaped as `Repo:path`, so a claim points somewhere a
  reader can go rather than asserting adoption in the abstract.

Whether a cited file really produces or consumes what this table says is
verified by reading it. The test cannot do that and does not pretend to.

**Do not build a row from `grep` alone.** The first draft of this table cited
`Azazel-Knowledge:src/azazel_knowledge/ingest/validators.py` as a consumer of
`deception_contracts`. That file imports no Fabric at all — Knowledge confines
the import to its API boundary (ADR-0010/0011) and that validator *mirrors* the
closed sets structurally, naming the family only in a comment explaining why.
A name match is evidence that somebody wrote the word, not that a contract
crosses a boundary there. Read the import and the direction.

## Families outside the `*_contracts` set

These are consumed but are not contract families in the R1c sense, so they
carry no gate. Recorded because "who uses this" is otherwise unanswerable.

| Module | Used by |
|---|---|
| `schema.defensive_state` | Azazel-Knowledge:`src/azazel_knowledge/api/contracts.py`, Azazel-Deception:`src/azazel_deception/runtime/presented_terrain.py`. Azazel-Edge keeps its own vocabulary — its arbiter must run with Fabric absent — and cross-checks the two in `tests/test_defensive_state_vocabulary.py` |
| `schema.mode`, `view` | Azazel-Edge:`py/azazel_edge/fabric_view.py`, Azazel-Boot:`src/azazel_boot/fabric_projection.py` |
| `audit` | Azazel-Edge:`py/azazel_edge/audit/fabric_adapter.py` |
| `deception_integrity` | Azazel-Deception:`src/azazel_deception/package.py` and the runtime verifier/transition modules |

## Release and support rules

- `CHANGELOG.md` is the release-history record; historical references to an
  earlier release describe that release, not the current recommendation. A
  changelog section is not evidence that a tag exists: `[0.7.0]` is retained
  there and explicitly marked never released, because the work it describes
  shipped in `v0.8.0`. Verified 2026-09-19 against both `git tag` and the
  published GitHub releases (`v0.1.0`-`v0.6.0`, `v0.8.0`).
- Before a release is described as available, the tag, the GitHub Release, and
  `src/azazel_fabric/version.py` must all be checked — not just the changelog.
- Product documentation that names a current release or consumer pin must be
  updated together with the relevant dependency declaration.
- Breaking schema or import changes require a major version, migration note,
  and consumer-specific evidence.
- Fabric remains descriptive. Capability reports, advisory data, placement
  plans, and signatures never grant runtime, decision, or enforcement authority.
- Release support claims require CI evidence for the published package and the
  documented cross-product conformance scope.
