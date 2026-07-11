# Security Policy

Azazel-Fabric is the shared contracts library for the Azazel series (Edge,
Gadget, Knowledge, and future series products). It ships schemas, validators,
and thin helpers — deliberately **no decision or execution logic**. Security
issues here are almost always a contract silently failing to hold, not a
running service being compromised.

## Reporting

Report privately via GitHub Security Advisory:
<https://github.com/01rabbit/Azazel-Fabric/security/advisories/new>

Do not open a public issue. Include the affected version/tag (e.g.
`v0.4.0`), a minimal repro (model + payload), and the impact you believe
this has. No bounty program; credit is offered in the advisory/release
notes unless you ask to stay anonymous.

## Response

- Acknowledgement within 7 days; initial assessment within 14 days.
- Coordinated disclosure: date agreed with the reporter before publishing.
- Fixes ship as a new tag, never a silent change to an existing one.
  Consumers pin an exact tag, so a fix implies every consumer must bump
  its pin — the advisory will say so and name the fixed tag.

## Scope

**In:** validation bypass in `cti_contracts` (a directive-shaped field —
`directive`/`must_execute`/`override`/`required_action` or equivalent —
passing validation is a vulnerability here even if consumers have their
own checks); parsing-level DoS (pathological inputs); anything that lets a
consumer silently violate a documented invariant; release/tag
supply-chain integrity.

**Out:** misuse contrary to documented non-goals (treating `paths` hints
as authoritative; expecting `audit` to provide chain integrity — chains
are product-local by design, e.g. Edge's P0 hash chain); vulnerabilities
in Pydantic itself (report upstream; a heads-up here is still welcome).

## Supported versions

Latest tagged release and `main`. Older tags (`v0.2.0` and earlier,
including pre-rename `azazel_common` names) receive no fixes — bump your
pin.
