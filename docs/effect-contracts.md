# Cross-series effect, outcome, and presented-terrain contracts

Status: **shipped in the candidate `v0.9.0rc2`, not stable**
(`azazel_fabric.effect_contracts`). Introduced for Fabric#15 on top of
`v0.9.0rc1`. **One producer, no consumer** — Azazel-Deception emits
`PresentedTerrainRef` (Azazel-Deception#46); nothing reads one yet, and a
contract that has never been read is not known to interoperate, so the R1c gate
counts it as unmet. See [release compatibility](release-compatibility.md) for
what the first adoption measured, including two records of this family that
**no product can produce today**.
Additive: a product that never imports this family is unaffected, and the
released `outcome_contracts` family is untouched.

Related: [contracts](contracts.md) · [design principles](design-principles.md) ·
[deception contracts](deception-contracts.md) ·
[release compatibility](release-compatibility.md)

## 1. What this family is for

The next-generation Azazel series needs to correlate one chain across
repositories:

```text
authoritative decision/effect -> materialization -> reaction/outcome -> replay
```

Each product already produces its part. What was missing was the minimum shared
language for the parts to refer to *the same* event. This family supplies that
language and nothing else.

> **Fabric describes; products decide.**

No type here becomes an execution token by carrying an effect name. A receiving
product still applies its own authority rules to everything it reads.

## 2. Ownership

There is no separate ADR series in this repository; contract ownership is
recorded here, in the reference document for the family, in the same place as
the schema it governs.

| Type | Who may produce it | Who consumes it | What it must never become |
| --- | --- | --- | --- |
| `DefensiveEffectRef` | AZ-01 Edge (decision), AZ-04 Knowledge (advisory) | AZ-06, AZ-02 Gadget, AZ-04 | a plan, a ranking, or a provider command |
| `EffectObservation` | whichever product materialized or observed the effect | AZ-04, replay tooling | a request to start, extend, or end an effect |
| `PresentedTerrainRef` | AZ-06 Deception (or an approved local materializer) | AZ-01, AZ-04 | a record of what the adversary believed |
| `OutcomeObservationEnvelope` | AZ-04 Knowledge, or any correlating consumer | replay and research tooling | a success verdict or a causal claim |
| `ReplayProvenance` | whichever product produced the chain | replay and research tooling | evidence of authorization |

**Authority stays where it already was.** Azazel-Edge's deterministic arbiter is
the only decision and enforcement authority in the series. Nothing in this
family moves, shares, or delegates any part of it.

## 3. Three vocabularies, deliberately distinct

This is the confusion the family exists to prevent, so it is worth stating
flatly. Fabric provides **no** function from any one of these to another.

| Vocabulary | Answers | Owner | Example values |
| --- | --- | --- | --- |
| `DefensiveState` (Fabric#14) | *What posture is this product in?* | `azazel_fabric.schema.defensive_state` | `OBSERVE`, `THROTTLE`, `ISOLATE` |
| `EffectClass` (this family) | *What kind of bounded effect was built?* | `azazel_fabric.effect_contracts` | `rate_limit`, `network_isolation` |
| Environment lifecycle | *Where is this materialized environment in its own life?* | `azazel_fabric.deception_contracts` | `baseline`, `active`, `terminated` |

A `DefensiveState` name in an `EffectClass` field is refused, and an
`EffectClass` value can never be read as a posture, because there is nothing to
read it through. Collapsing any two of them would let a value from one carry
authority in another.

## 4. Typed, opaque references

A cross-series reference is `"<kind>:<opaque>"` — for example
`effect:golden-effect-1`, `presentation:p1`, `lifecycle:env-1.active`.

Two properties follow, and both are enforced rather than documented:

**The kind travels with the value.** An AZ-06 environment-lifecycle id supplied
where an Edge decision reference is required announces itself as a `lifecycle:`
ref and is refused. Nothing about the two bare strings would have distinguished
them.

**The body is structurally opaque.** No slash, backslash, whitespace, quote, or
newline. That excludes filesystem paths, URLs, PEM blocks and command fragments
from every slot requiring a typed ref, which is the enforcement behind
"opaque; no secret material" for presented-terrain artifact references.

### 4.1 A known, deliberate limit

The guard is **asymmetric**. Ids this family introduces (effect, effect
observation, presented terrain, envelope, scope) must be typed. Ids it inherits
from the released `outcome_contracts` family (trace, decision, execution) accept
the untyped form — those records use ids such as `decision-golden-redirect-1`,
and correlation with them has to keep working. An inherited slot rejects a value
typed as a *different* kind, but cannot validate a bare string as belonging
there.

Closing that gap would mean breaking correlation with a released family. The
limit is stated here rather than left to be discovered.

Likewise, the secret-material scan recognizes what it recognizes — PEM headers,
key prefixes, `token=` style assignments. It cannot tell that `cred:hunter2` is
a password, and nothing at this layer can. The contract is that these fields
carry references; the scan catches the obvious violations of it loudly.

## 5. Authority classification

Every shared record carries an `authority_class` making six readings
distinguishable:

| Class | How a consumer should read the record |
| --- | --- |
| `observed_fact` | Something was observed. No decision, no inference. |
| `producer_decision_ref` | The producing product's authority decided this, and names the decision. |
| `advisory_inference` | Advice or inference. Never a decision. |
| `planned_shadow` | Considered or shadow-run. Nothing materialized. |
| `active_materialized` | Live, as asserted by its materializer. |
| `stale_or_unknown` | Expired, replayed, or not understood. Claims nothing. |

**Unknown never escalates.** An unrecognized value coerces to
`stale_or_unknown` — the class that claims least — and
`coerce_authority_class` returns a second element saying whether the value was
recognized, so "claims the weakest" stays distinguishable from "could not be
read". The same rule governs `EffectClass`: an unrecognized effect coerces to
`observe_only`, never to isolation or redirection.

**The claim must be substantiated.** A `producer_decision_ref` must name its
decision and must not also carry an advisory reference; an `advisory_inference`
must name its advisory and must not carry a decision reference at all. A
schema-valid advisory therefore cannot reach
`is_authoritative_decision_reference`, whatever else it carries.

**The two record kinds partition the six classes** (`v0.9.0rc4`, Fabric#52).
A `DefensiveEffectRef` may claim any class except `observed_fact` and
`active_materialized`, because those are an observation's to make. An
`EffectObservation` may claim *only* those two, because the other four describe
something nobody observed: `producer_decision_ref` would make a report of an
effect an assertion of authority over it, `advisory_inference` and
`planned_shadow` describe records where nothing was materialized, and
`stale_or_unknown` claims nothing — which a consumer must see as a gap rather
than as a fact with a weak label.

The second half of that rule was prose until `v0.9.0rc4`, and prose is not a
gate: an observation claiming `producer_decision_ref` validated. Correcting it
refuses input `v0.9.0rc3` accepted, which is why it lands in a candidate rather
than after `v0.9.0`. The partition is total and disjoint, and a test enumerates
it from `AuthorityClass` itself so that a class added later has to be placed by
someone rather than by omission.

**Provenance is not authorization.** `ReplayProvenance.confers_authority` is
pinned to `False`. Carrying a model reference makes a run reproducible; it does
not give the model's output authority.

## 6. What stays product-local, by design

Issue #15 assigns these to their owning products or to research tooling. They
have no shared authoritative contract, and
`BANNED_EFFECT_AUTHORITY_FIELDS` refuses them recursively anywhere in a
payload:

- adversary belief state;
- M.I.O. council voting and synthesis;
- counterfactual ranking;
- operator doctrine acceptance;
- utility and initiative scoring;
- model confidence as a probability;
- provider-specific `tc` / `nft` / Docker / KVM / EDR commands;
- arbitrary tool calls;
- `execute`, `approve`, `must_apply`, `override` and equivalents.

A shared, authoritative contract for any of these would move a product decision
into the contract layer. That is the one thing this repository must not do.

## 7. Coverage instead of success

There is no universal `success` field, and the shared walk rejects one wherever
it appears. What replaces it is **coverage**: an envelope states how much of the
world it could see. An envelope reporting `coverage_complete=False` must name
its `telemetry_gaps`, and one claiming complete coverage may not name any.
Unnamed telemetry loss is how a partial observation comes to read as a whole
one.

## 8. Golden vectors

`azazel_fabric.testing.effect` publishes one chain across four producers —
Edge's decision, Knowledge's competing advisory, AZ-06's presented terrain and
observation, Gadget's second vantage point, and Knowledge's correlating
envelope — plus the replay provenance. Fixture bytes and a canonical digest
manifest live in `tests/fixtures/effect/`.

The advisory vector is published deliberately alongside the decision vector.
Both describe the same trace; a consumer that cannot tell them apart has an
authority bug, and this is the cheapest way for it to find out.

The envelope vector reports **incomplete** coverage with the gap named, because
a golden vector claiming perfect telemetry would teach consumers the wrong
shape.

## 9. Adopting this family

1. Pin the tag that ships it: `v0.9.0rc2` or later. It is not in `v0.9.0rc1`.
   A candidate promises no stability, so expect to re-pin to `v0.9.0`; see
   [release compatibility](release-compatibility.md).
2. Keep producing your existing `outcome_contracts` records. The envelope
   references them by id; it does not replace or re-interpret them.
3. Emit typed ids for anything this family introduces. Your existing trace,
   decision and execution ids need no change.

   A typed ref's body may contain further colons — the split point is the
   first one — so a hierarchical id like `surface:http:8080` is a valid
   `surface` reference. That was **not** true in `v0.9.0rc2`, where the body
   excluded colons and consequently refused every hierarchical reference in
   the series. If you are pinned to `rc2`, this step is the one that will stop
   you; re-pin rather than rewriting your identifiers, because a rewritten
   identifier no longer resolves to the thing it named.

4. Do not fill a slot you have no fact for. Where your record cannot supply
   something this family requires — a bounded `expires_at` is the usual one —
   refuse to emit rather than defaulting. A plausible default produces a record
   that validates and misreports, and the consumer has no way to tell.
5. Read `authority_class` before acting on any record, and apply your own
   authority rules to what it claims. Fabric having validated a record means
   the record is well-formed, not that it is authorized.

   Which class you may claim depends on which record you are emitting, and the
   two sets do not overlap: see §5. If you emit an `EffectObservation`, derive
   its class from what you observed, never from the effect record you are
   reporting on — copying the effect's class across is how a report acquires
   the authority of the thing it reports.
6. Treat an unrecognized enum value as the weakest reading. The coercion
   helpers already do; do not add a mapping that does otherwise.

Nothing about this family is required. A product that does not adopt it keeps
working, which is the compatibility condition issue #15 sets.
