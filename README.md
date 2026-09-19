# AZ-05 Azazel-Fabric - Shared Contracts and Interoperability Foundation

> **Codename:** `COVENANT`

![Azazel-Fabric Banner](assets/branding/Azazel-Fabric_Banner.png)

Shared contracts and interoperability foundation for the Azazel System.

> Formal series name **Azazel-Fabric Contract** (**AZ-05**), ratified
> 2026-07-10; formerly **Azazel-Common**. The codename `COVENANT` follows the
> series convention (Edge: `SENTINEL`, Gadget: `TACMOD`, Deception: `THEATRE`):
> the binding agreement the series' products sign — used for changelogs and
> release names, never formal external naming.

Thin, shared contract package for the Azazel series (`Azazel-Edge`,
`Azazel-Gadget`, `Azazel-Knowledge`, `Azazel-Deception`, and future tools such
as `Azazel-Boot`).

Azazel-Fabric is not the decision core of any Azazel product. It is the
series' common language. Each product's own judgment stays in its own
repository: Edge owns deterministic decisions and enforcement, Knowledge
analyzes/advises, Gadget owns its local mode control, and Deception
materializes only Edge-approved environments.

## Status

**Latest stable release: `v0.8.0` — canonical Edge-decision transport
signatures.** The first canonical AZ-06 deception-environment contract baseline
shipped in `v0.5.0`; subsequent `v0.6.0`, `v0.7.0`, and `v0.8.0` releases are
additive. See [release compatibility](docs/release-compatibility.md) for the
supported contract families and observed consumer pins.

`v0.9.0rc1` is a **release candidate** adding `azazel_fabric.outcome_contracts`,
`azazel_fabric.provisioning_contracts`, and `azazel_fabric.mio_contracts`. It is
pinnable but not stable: adopt it to produce the downstream evidence `v0.9.0`
requires, and expect to re-pin. A consumer that needs stability stays on
`v0.8.0`.

Stable `v0.5.0` also ships everything from `v0.4.0`:

- `azazel_fabric.schema` / `azazel_fabric.cti_contracts` — shared schema and advisory-only CTI contract.
- `azazel_fabric.view` — shared `StatusView` view model.
- `azazel_fabric.paths` — non-authoritative candidate-path hints and dry-run migration planning.
- `azazel_fabric.audit` — shared `AuditEvent` projection and JSONL formatters.
- `azazel_fabric.api` — framework-neutral fail-closed API helpers.
- `azazel_fabric.notify` — notification payloads/mappers; no network send.
- `azazel_fabric.testing` — shared factories and invariant assertions.

`v0.5.0` introduced `azazel_fabric.deception_contracts`:

- `DeceptionPackage`, `NarrativeManifest`, `NarrativeConsistencyReport`
- `HostCapabilities`, `RuntimeRequirements`, `DeploymentTier`
- `ImageManifest`, per-platform OCI digests, provenance/SBOM references
- `PlacementPlan` with explicit `descriptive_only` authority
- Edge-owned activation/transition/termination decision contracts
- environment event/outcome contracts
- static rejection of directive-bearing Fabric payloads
- unrepresentable unrestricted egress/production access in the canonical safety model

`v0.6.0` adds effectiveness observation and finite-state transition catalog
contracts; `v0.7.0` adds advisory-only engagement contracts; `v0.8.0` adds the
canonical decision-envelope signing helpers. All remain descriptive contracts:
a valid signature proves transport origin and integrity, never action authority.

See [`docs/deception-contracts.md`](docs/deception-contracts.md).

## Consumer status

| Product | Current status |
|---|---|
| Azazel-Edge (AZ-01) | Observed dependency pin: `v0.8.0`. Fabric remains optional for baseline Edge runtime. |
| Azazel-Gadget (AZ-02) | Shipping Fabric integration; current Gadget documentation reports `azazel-fabric` v0.4.0 for StatusView. AZ-06 compatibility remains a constrained future `gadget-lite` subset. |
| Azazel-Knowledge (AZ-04) | Observed API optional-dependency pin: `v0.8.0`; core remains dependency-minimal and advisory-only. |
| Azazel-Deception (AZ-06) | Observed dependency pin: `v0.8.0`; live exposure remains disabled by default. |
| Azazel-Boot (AZ-03) | Observed `fabric` optional-extra pin: `v0.8.0`; an image lock is still required before a Boot implementation release. |
| Azazel-Nexus | No pin yet — documentation-only repository. |

## Install

Stable consumers should use the latest compatible exact tag, currently:

```bash
pip install "azazel-fabric @ git+https://github.com/01rabbit/Azazel-Fabric.git@v0.8.0"
```

Consumers pin an exact tag for field deployment (see
[`docs/design-principles.md`](docs/design-principles.md) §6).

```python
from azazel_fabric.schema import StateSnapshot, DecisionExplanation
from azazel_fabric.cti_contracts import CtiContextResponse
from azazel_fabric.deception_contracts import (
    DeceptionPackage,
    HostCapabilities,
    PlacementPlan,
    EnvironmentActivationDecision,
)
from azazel_fabric.view import StatusView, build_status_view
from azazel_fabric.api import error_payload, role_allows, extract_token
from azazel_fabric.notify import NotificationEvent, to_ntfy_payload
from azazel_fabric.paths import candidate_runtime_dirs, plan_migration
from azazel_fabric.audit import project_audit_event, to_jsonl_line
from azazel_fabric.testing import make_status_view, assert_advisory_only
```

Adopting Fabric in a new series product? Start with the
[day-1 adoption guide](docs/adoption-guide.md).

## Authority rule for AZ-06

> Fabric describes. Edge decides and enforces. Deception Host materializes,
> transitions, records, and resets. Knowledge analyzes and advises.

Capability reports, packages, placement plans, and advisories never grant
activation authority. In the initial architecture only an explicit,
unexpired Azazel-Edge decision may authorize an AZ-06 live runtime change.

## Versioning

Version management is tag-driven on GitHub. The single source of truth is
`src/azazel_fabric/version.py`; each release is a `vX.Y.Z` git tag plus a
matching GitHub Release, and a `vX.Y.ZrcN` tag is a pinnable candidate that
makes no stability promise. A `.dev0` value on `main` is explicitly unreleased.
The Release workflow validates that a pushed tag matches the packaged version
and runs the test suite before publishing. A releasable (non-`.dev`) version
additionally carries `release/v<version>.digest.json`, a reproducible sha256
manifest of the packaged surface generated by `tools/rc_digest.py` and enforced
by `tests/test_release_candidate_digest.py`.

## Documentation

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Azazel-Fabric's position in the series and responsibility boundaries |
| [`docs/design-principles.md`](docs/design-principles.md) | What goes in Fabric vs. what never does, and why |
| [`docs/contracts.md`](docs/contracts.md) | Stable shared schema and Edge/Gadget ↔ CTI contracts |
| [`docs/deception-contracts.md`](docs/deception-contracts.md) | Canonical AZ-06 contract family (`v0.5.0`), authority and migration rules |
| [`docs/provisioning-contracts.md`](docs/provisioning-contracts.md) | Provisioning and M.I.O. contract families (R1a), authority rules, feature-to-minimum-version matrix |
| [`docs/release-compatibility.md`](docs/release-compatibility.md) | Current release truth, supported contract families, and observed consumer pins |
| [`docs/adoption-guide.md`](docs/adoption-guide.md) | Day-1 adoption playbook for a series product |
| [`docs/migration-plan.md`](docs/migration-plan.md) | Phased, additive, reversible rollout plan |
| [`docs/repository-layout.md`](docs/repository-layout.md) | Package layout |
| [`docs/issue-breakdown.md`](docs/issue-breakdown.md) | GitHub implementation work |

## License

MIT. See [`LICENSE`](LICENSE).
