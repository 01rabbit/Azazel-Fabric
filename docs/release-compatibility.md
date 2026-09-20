# Release Compatibility and Support Truth

Status: **R0 coordination baseline, 2026-09-19; re-verified 2026-09-19 against
the consumer repositories.** This document records the published Fabric release
and observed consumer dependency declarations. An observed pin is not, by
itself, an interoperability certification.

## Current Fabric release

The latest **stable** release is `v0.8.0`. The latest **published** tag is the
release candidate `v0.9.0rc2`, which carries the canonical `DefensiveState`
vocabulary and the cross-series `effect_contracts` family on top of
`v0.9.0rc1` — itself additive contract work (`outcome_contracts`, and the R1a
`provisioning_contracts` / `mio_contracts` families) over `v0.8.0`.

A candidate is pinnable but makes no stability promise. It exists so a consumer
can pin an exact tag — never a branch — while producing the downstream evidence
`v0.9.0` requires. A consumer that needs stability stays on `v0.8.0`; a consumer
adopting the new contract families pins the newest candidate, `v0.9.0rc2`, and
expects to re-pin to `v0.9.0`. A consumer already on `v0.9.0rc1` needs no
urgent move: `v0.9.0rc2` changed no released symbol, so the only reason to
re-pin is to use what it adds.

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

All consumer deployments MUST pin an exact compatible Fabric tag or immutable
image lock. They MUST NOT pin a branch. A product chooses when to adopt a newer
compatible tag and must demonstrate its own integration tests before claiming
support.

## Observed consumer declarations

| Consumer | Observed declaration | Interpretation |
|---|---|---|
| Azazel-Edge | `v0.9.0rc2` in `requirements/fabric.txt` | Current reference authority consumer. An **optional** extra: Edge's arbiter runs with no Fabric installed |
| Azazel-Gadget | `v0.4.0` in `requirements.txt` | Earlier consumer baseline; no automatic upgrade implied |
| Azazel-Knowledge | `v0.9.0rc2` in the `api` optional dependency (`pyproject.toml`) | Advisory API boundary only; core stays dependency-minimal |
| Azazel-Deception | `v0.9.0rc2` in `pyproject.toml` | Current AZ-06 runtime declaration |
| Azazel-Nexus | **no declaration** | No longer documentation-only — it carries code with deliberately zero dependencies. Its absence from this table is a design choice, not an omission |
| Azazel-Boot | `v0.9.0rc1` in the `fabric` optional extra (`pyproject.toml`, ADR-0004) | Exact-tag source pin, one release behind. An image lock is still required before a Boot implementation release |

Verification note (2026-09-20): the Edge, Knowledge, Deception, Boot, and Nexus
rows were read directly from each repository's dependency declaration at the
commits named in the adoption matrix below. The Gadget row is carried forward
from an earlier audit and has **not** been re-verified from the Gadget
repository in this pass.

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
| `effect_contracts` | — | — | not met |
| `engagement_contracts` | Azazel-Edge:`py/azazel_edge/engagement/candidate.py`, Azazel-Knowledge:`src/azazel_knowledge/api/contracts.py` | — | not met |
| `mio_contracts` | — | — | not met |
| `outcome_contracts` | Azazel-Edge:`py/azazel_edge/outcome/shared_export.py` | — | not met |
| `provisioning_contracts` | — | — | not met |

`deception_contracts` is the only family that clears the gate, and it does so
on a real round trip rather than a count: Edge constructs and signs an
`EnvironmentTransitionDecision` that Deception verifies, and Deception emits
`InteractionObservation` records that Knowledge validates at its API boundary.
Producer and consumer are different products in both directions, which is what
the gate is asking about.

Two patterns in that table are worth naming rather than leaving to be noticed.

**`engagement_contracts` has two producers and no consumer.** Both Edge and
Knowledge write the Engage-aligned types; nobody reads one the other wrote. A
contract that has only ever been serialized is not known to interoperate — the
first read is where a disagreement surfaces.

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
