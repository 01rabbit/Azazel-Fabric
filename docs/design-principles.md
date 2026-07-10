# Azazel-Covenant (formerly Azazel-Common): Design Principles

Status: **Governing charter for shipped code (`v0.3.0`).** §2/§3.1 reflect
the `schema`/`cti_contracts`/`view` modules as actually implemented and
released; the `paths`/`api`/`notify`/`testing` rows in §2 are still design
proposal — not yet built (see `migration-plan.md` Phase 5). `v0.3.0` renamed
the repository and package from `Azazel-Common`/`azazel_common` to
`Azazel-Covenant`/`azazel_covenant`; the principles below are unchanged by
the rename — see §4.6.

## 1. First principle

> Azazel-Covenant holds contracts. It does not hold judgment.

Anything that decides — what action to take, whether to escalate, whether
an IOC is credible, whether a device is trusted — stays in the owning
product. Anything that merely *describes* — a state, a message, a log
line's shape, a directory path — is eligible for Covenant.

A useful test before adding anything to Covenant: **"If this code were
deleted, would a product lose its ability to decide, or only its ability
to describe that decision the same way as its siblings?"** If the former,
it does not belong in Covenant.

## 2. What goes in, and why

| Module | Contents | Why it's safe to share |
|---|---|---|
| `azazel_covenant.schema` | `StateSnapshot`, `ModeState`, `ActionIntent`, `EvidenceRef`, `DecisionExplanation`, `AuditEvent`, `TrustCapsule` | Pure data shape. Describing a decision that already happened is not the same as making it. |
| `azazel_covenant.cti_contracts` | `CtiEventBatch`, `CtiFlowBatch`, `CtiReactionBatch`, `CtiContextRequest`, `CtiContextResponse` | Wire format for an advisory exchange. Fixing the *shape* of advice does not grant the Knowledge Plane (Azazel-Grimoire) authority over Edge/Gadget. |
| `azazel_covenant.paths` | runtime/config/log dir schema, legacy-path compatibility, migration dry-run helper, active-schema discovery | Directory naming convention only; no product logic depends on where a log file happens to sit. |
| `azazel_covenant.audit` | JSONL writer, trace-id generator, config-hash helper, HMAC helper, (future) chain-of-custody helper | Standardizes the *envelope* audit events are written in. The content and triggering of an audit event stays product-owned. |
| `azazel_covenant.api` | token-auth helper, role helper (viewer/operator/responder/admin), fail-closed default response, standard JSON error model | Security posture conventions, not endpoint logic. Framework-neutral; Flask/FastAPI adapters are separate optional modules. |
| `azazel_covenant.notify` | notification event schema, thin ntfy/Mattermost send helpers, SSE bridge model | Payload shape and transport plumbing only. No product-specific copy, tone, or UI. |
| `azazel_covenant.view` | `StatusView` display view-model + `build_status_view` helper | A shared *data contract* for what a status surface shows, plus one shared builder that derives it. It is the shape a display *reads*, not a renderer — standardizing it lets Edge and Gadget render the same status the same way without moving any product's UI into Covenant. Edge-lineage but a generalized superset (Gadget-only fields ride in `product_view`), so Gadget is never narrowed to "Edge minus features." |
| `azazel_covenant.testing` | shared fixtures and contract test cases | Lets each product's CI assert it still satisfies the shared contract, without depending on another product's test suite. |

Everything in this list is chosen because it is safe to be wrong about in
the same way across all products — a naming/format detail, not a security
or arbitration decision.

## 3. What must never go in, and why

| Excluded | Reason |
|---|---|
| Azazel-Edge's Action Arbiter | AZ-01's final decision authority must stay singular and local. Moving it to Covenant would let a shared library's release cycle gate Edge's core safety behavior, and would blur which repository "owns" the decision that matters most. |
| Azazel-Edge's NOC/SOC Evaluator | Edge-specific judgment logic tuned to Edge's evidence model; not reusable without dragging Edge's threat model into Covenant. |
| Azazel-Grimoire's Correlation Engine | Knowledge-Plane-specific processing; Grimoire's analytic method is not a cross-product concern. |
| Behavioral CTI Generator | Same reasoning — Grimoire-specific generation logic, not a shared shape. |
| Azazel-Gadget's Wi-Fi connection control | Tightly coupled to `wlan0` / captive-portal / USB gadget specifics that do not generalize to Edge or Grimoire. |
| Azazel-Gadget's USB gadget control | Gadget-hardware-specific; Edge has no USB gadget role. |
| nft / tc / OpenCanary execution | Execution adapters differ by network topology and deployment target; a shared executor would either be too generic to be useful or would silently encode one product's assumptions into the others. |
| AI Assist (as a decision subject) | Each product's safety boundary around AI-assisted suggestions differs; Covenant must never let AI Assist output be treated as authoritative across products. |
| Web UI **rendering** (templates, widgets, routes, CSS) | The rendered UI is product-specific (Edge dashboard vs. Gadget portable UX vs. Grimoire console). Only the *view-model* it reads (`azazel_covenant.view`, §2) is shared; the rendering stays product-side. |
| E-Paper **rendering** | Device/screen-specific drawing stays product-side. The *status data* a panel shows comes from the shared `StatusView`; turning that data into pixels does not. |

### 3.1 The view-model boundary (in) vs. the renderer (out)

Sharing display was originally excluded wholesale. It is now split along the
one line that keeps the First Principle intact: **the view-model is a shared
contract; the renderer is product behavior.**

- **In Covenant:** `StatusView` — the normalized data a status surface shows
  (mode, posture, headline, reasons, next actions, current action, health
  dimensions, evidence), plus `build_status_view`, the single shared function
  that derives it. Two products calling one builder is exactly the "shared
  mechanism, not just a shared shape" that makes Covenant worth having.
- **Never in Covenant:** how those fields become a Web page, a TUI, or an
  E-Paper frame. Each product owns its renderer, its layout, its device
  quirks, and its copy.
- **Superset, not subset:** `StatusView` takes Edge's more mature status model
  as its base *vocabulary*, but every Gadget-only field (`DECEPTION` posture,
  `scapegoat` decoy state, canary-delay telemetry) is preserved via
  `product_view`. "Edge-based" means Edge-lineage, not Edge-only — §4.4 still
  holds.

## 4. Safety boundaries that must hold across every phase

1. **Edge's Deterministic Arbiter is never relocated to Covenant.** Not in
   v0.1.0, not in v1.0.0, not ever, unless a future, separately-approved
   design explicitly revisits this — which this document does not
   authorize.
2. **The Knowledge Plane (Azazel-Grimoire) is advisory-only.**
   `CtiContextResponse` may include `recommended_action` /
   `suggested_posture`-shaped fields, but the schema must never include a
   field that reads as a command (no `directive`, no `must_execute`, no
   `override`). Consuming products treat every CTI field as optional input
   to their own arbiter.
3. **A missing, malformed, or timed-out CTI response must never block a
   decision.** Contract schemas define `CtiContextResponse` fields as
   optional/omittable (notably `behavioral_cti`, which is *absent*, not
   `null`, when there is nothing to report) precisely so that "Grimoire said
   nothing" and "Grimoire is down" both degrade to "Edge/Gadget decide
   alone," never to "Edge/Gadget wait."
4. **Gadget is a sibling of Edge, not a subset of it.** Covenant schemas
   must be generic enough to fit both without silently modeling Gadget as
   "Edge minus features." Where a schema needs product-specific extension
   (e.g. Gadget-only mode values), extend via enums/optional fields, not
   by assuming Edge's field set is the baseline.
5. **Covenant ships schema-only in its first release.** No execution logic,
   no nft/tc/OpenCanary bindings, no AI Assist decision logic, ships in
   `v0.1.0`. This is a hard gate, not a preference — see
   `migration-plan.md` Phase 1.
6. **No name implies more than it is.** The repository was named
   `Azazel-Common`, not `Azazel-Core`, specifically so nobody mistakes
   "shared schema library" for "shared decision core." The repository has
   since been renamed again, to `Azazel-Covenant` (AZ-05), per the ratified
   series naming register — libraries take no Role suffix in that register,
   and "Covenant" (a binding agreement) names what this kind of shared,
   held-in-trust contract *is*, without implying it decides anything. The
   underlying constraint this principle protects — the label must never
   overstate the package's authority — is unchanged by either name.

## 5. Dependency-weight principle

Because Covenant's primary runtime targets include a Raspberry Pi (both
AZ-01 and AZ-02), dependencies are kept minimal:

- Pydantic is the preferred base for schema modules (validated, fast
  enough, already familiar to the series), but pinned to a version range
  that avoids heavyweight optional extras.
- `azazel_covenant.api` stays framework-neutral in its core; Flask/FastAPI
  adapters are optional extras (`azazel-covenant[flask]`,
  `azazel-covenant[fastapi]`) so a consumer only pays for what it uses.
- No transitive dependency on any product's runtime stack (no importing
  from Edge, Gadget, or Grimoire source — dependency direction is strictly
  Covenant → nothing, products → Covenant).

## 6. Change-safety principle

Covenant is a dependency of products that have their own release cadence
and their own demo/field commitments (including BHUSA 2026 preparation for
Edge). Therefore:

- Consuming repositories pin Covenant to a **tag**, not a branch or
  `main`, and not a git submodule (submodules are avoided — they are prone
  to CI/local-dev/dependency-update mismatches).
- Covenant follows SemVer; breaking schema changes require a major version
  bump and an explicit migration note (see `migration-plan.md`). The
  `v0.3.0` distribution/import rename is documented as a breaking change in
  `CHANGELOG.md` even though it carries no schema change, precisely because
  it breaks every consumer's import statement.
- Introducing Covenant into a product is additive-only at first (new
  optional call sites), never a rewrite of an existing working path, until
  a contract test suite proves equivalence.
