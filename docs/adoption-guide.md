# Azazel-Fabric: Day-1 Adoption Guide for a New Series Product

Status: **Ratified (Phase 6, `v0.4.0`).** This guide is the standing day-1
playbook for any *new* Azazel-series product — the reserved `Azazel-Boot`, or
any future AZ-0x tool — so it speaks the series' shared language from its first
commit instead of re-inventing state/audit/CTI/notify formats. Existing products
(Edge, Gadget, Knowledge) adopt Fabric incrementally per `migration-plan.md`;
this guide is aimed at a green-field repository.

> **Naming first.** Before you name your product, its codename, or its role
> suffix, the series **naming spec governs** — `docs/specs/naming.md` in the
> umbrella `Azazel` (Doctrine Hub) repository. Fabric does not assign product
> names or codenames; it only holds the shared *shapes* those products exchange.
> Register your name/codename there first, then come back here.

## 0. The one doctrine that outranks everything below

**Advisory-only.** Fabric holds contracts, not judgment (design-principles §1).
Nothing you adopt from Fabric decides anything for your product. In particular,
the Knowledge Plane's CTI response is *advice*: a missing, malformed, or
timed-out CTI response must **never** block your product's own decision path —
it degrades to "decide alone," never to "wait." If adopting Fabric ever makes
your product wait on, or defer authority to, another product, you have adopted
it wrong. Re-read design-principles §4.

## 1. Pin Fabric to a tag (never a branch)

Consumers pin an **exact git tag**, never a branch, never `main`, never a
submodule (design-principles §6). In your product's dependency file:

```toml
# pyproject.toml  (or requirements.txt line)
azazel-fabric @ git+https://github.com/01rabbit/Azazel-Fabric.git@v0.4.0
```

Bump the pin deliberately when you choose to, on your own release schedule — a
Fabric release never forces itself on you. Breaking schema changes arrive only
on a major bump with a migration note in Fabric's `CHANGELOG.md`.

## 2. Guarded-import pattern (copy the Gadget/Edge idiom)

Import Fabric behind a guard so your product still boots if the dependency is
absent (e.g. a minimal field build, or a contributor who has not installed it
yet). Fabric is *additive*: your product must run without it, then emit
*alongside* its own data when it is present. This is exactly the idiom Edge and
Gadget use.

```python
# azazel_boot/fabric_bridge.py
try:
    from azazel_fabric.view import build_status_view
    from azazel_fabric.schema import ModeState
    _FABRIC = True
except ImportError:  # Fabric not installed — degrade, never crash
    _FABRIC = False


def status_view_or_none(product_state):
    """Return a Fabric StatusView, or None if Fabric is unavailable."""
    if not _FABRIC:
        return None
    return build_status_view(
        product="boot",
        mode=ModeState(name=product_state.mode, since=product_state.since),
        generated_at=product_state.now_iso,
        state_word=product_state.stage,
    )
```

Keep the guard narrow: import Fabric, and on `ImportError` fall back to your
product's own path. Never wrap real logic in the `try`.

## 3. Which module to adopt first: `view` / `StatusView`

Adopt **`azazel_fabric.view`** first. `StatusView` is the shared view-model a
status surface reads (mode, posture, headline, reasons, next actions, current
action, health dimensions, evidence), and `build_status_view` is the one shared
builder that derives it — so your product presents status the same way Edge and
Gadget do. It is the highest-value, lowest-risk first adoption because:

- it touches only how status is *described*, never how anything is *decided*;
- it is a **generalized superset** — anything product-specific rides in
  `product_view` and is never dropped, so `Azazel-Boot` is never narrowed to
  "Edge minus features" (design-principles §3.1, §4.4);
- Fabric owns the view-model; **your renderer stays yours** (Web/TUI/E-Paper).

```python
from azazel_fabric.view import build_status_view

view = build_status_view(
    product="boot",
    mode=mode_state,
    generated_at=now_iso,
    state_word="NORMAL",
    product_view={"boot": {"stage": "provisioning"}},  # your fields, preserved
)
# hand `view.model_dump()` to your own renderer — Fabric never renders.
```

## 4. Emit-alongside, without coupling

The rule for every Fabric shape you adopt (`StateSnapshot`, `AuditEvent`,
`NotificationEvent`, the CTI contract): **emit the Fabric projection *alongside*
your product's own record — never replace your working path with it until a
contract test proves equivalence** (design-principles §6). Concretely:

- Keep your product's native state/audit/notify objects exactly as they are.
- Add a thin projection function (like §2) that also produces the Fabric shape.
- Surface the Fabric shape additively (e.g. a `status_view` key on your
  `/api/state`, the pattern Edge and Gadget both use), not by rewriting the
  existing payload.
- **Audit note:** adopt `azazel_fabric.audit` for the shared `AuditEvent`
  *projection and JSONL format* only. Fabric ships **no hash chain and no chain
  verification** — that integrity mechanism stays product-local (owner decision;
  see `contracts.md` §1 and the `azazel_fabric.audit` module docstring). If your
  product needs a tamper-evident chain, build it in your own repository over the
  shared `AuditEvent` shape; do not expect Fabric to provide or verify it.

For CTI (`azazel_fabric.cti_contracts`), remember §0: parse a `CtiContextResponse`
as optional advice, treat validation failure / timeout / unreachable as "no
context," and never raise out of that path.

## 5. Use `azazel_fabric.testing` from day one

`azazel_fabric.testing` gives your CI valid Fabric objects and the shared safety
assertions without depending on any other product's test suite. Every export is
a **plain function — no pytest dependency** — so it works from pytest, unittest,
or a bare script. (A `test` extra exists if you want pytest itself:
`azazel-fabric[test]`.)

```python
from azazel_fabric.testing import (
    make_status_view, minimal_cti_context_response,
    assert_advisory_only, assert_behavioral_absent_not_null,
)

def test_boot_status_projection_is_valid():
    view = make_status_view(product="boot")   # a valid StatusView to assert against
    assert view.product == "boot"

def test_boot_treats_cti_as_advisory():
    resp = minimal_cti_context_response()      # the "Knowledge said nothing" shape
    assert_advisory_only(resp)                 # no directive fields
    assert_behavioral_absent_not_null(resp)    # absent, never null
```

Factories come in two flavours: `make_*` (fully populated) and `minimal_*`
(required fields only). Both accept keyword overrides. Output is deterministic
(fixed timestamps), so your golden tests do not flake.

## 6. Checklist for a new product's first Fabric commit

1. Register the product/codename in the umbrella naming spec
   (`docs/specs/naming.md`) — Fabric does not govern names.
2. Pin `azazel-fabric` to an exact tag in your dependency file (§1).
3. Add a guarded-import bridge module (§2) — your product still boots without
   Fabric.
4. Adopt `azazel_fabric.view` first; emit `StatusView` alongside your own state
   (§3–§4).
5. Wire `azazel_fabric.testing` into your CI to assert you satisfy the contract
   (§5).
6. Hold the advisory-only line everywhere the CTI contract is used (§0).

Everything beyond this — audit projection, notify payloads, api error/role/token
helpers, path hints — is adopted the same additive way, only where it removes
real duplication, never as a mandate to touch code that is not already
duplicated (`migration-plan.md` Phase 5).
