# AZ-05 Azazel-Fabric - Shared Contracts and Interoperability Foundation

> **Codename:** `COVENANT`

Shared contracts and interoperability foundation for the Azazel System.

> Formal series name **Azazel-Fabric Contract** (**AZ-05**), ratified
> 2026-07-10; formerly **Azazel-Common**. The codename `COVENANT` follows the
> series convention (Edge: `SENTINEL`, Gadget: `TACMOD`): the binding
> agreement the series' products sign — used for changelogs and release
> names, never formal external naming.

Thin, shared contract package for the Azazel series (`Azazel-Edge`,
`Azazel-Gadget`, `Azazel-Knowledge`, and future tools such as `Azazel-Boot`).

Azazel-Fabric is not the decision core of any Azazel product. It is the
series' common language: shared state/action/audit schema, the Edge/Gadget
↔ CTI advisory contract, and thin path/audit/API/notify helpers. Each
product's own judgment — Edge's Deterministic Arbiter, Knowledge's correlation
engine, Gadget's device control — stays in its own repository. `Fabric` names
the shared foundation connecting the Azazel products; `Contract` names the
shared schemas, state representations, audit/notification formats, and
exchange contracts between Edge/Gadget and the Knowledge Plane that this
repository holds — it holds no product's decision logic, which is exactly
why `Core` was avoided as a name.

## Status

**`v0.4.0` — Phase 5 helpers + Phase 6 adoption tooling.** Additive, no
breaking change from `v0.3.0` (the rename release). `azazel_fabric` ships:

- `azazel_fabric.schema` / `azazel_fabric.cti_contracts` — shared schema and
  the advisory-only CTI contract (`v0.1.0`).
- `azazel_fabric.view` — the shared `StatusView` view-model + `build_status_view`
  builder so Edge and Gadget present the same status the same way; Fabric owns
  the view-model, each product keeps its own renderer (see
  [`docs/design-principles.md`](docs/design-principles.md) §3.1) (`v0.2.0`).
- `azazel_fabric.paths` — candidate-path **hints** (never authoritative) +
  dry-run-only legacy-migration planner (`v0.4.0`).
- `azazel_fabric.audit` — shared `AuditEvent` projection + JSONL formatters.
  **No hash chain, no chain verification** — that integrity mechanism stays
  product-local (Edge's P0 hash chain) by owner decision (`v0.4.0`).
- `azazel_fabric.api` — framework-neutral error/role/token helpers, fail-closed
  (`v0.4.0`).
- `azazel_fabric.notify` — the shared `NotificationEvent` payload + pure
  ntfy/Mattermost payload mappers (no network send) (`v0.4.0`).
- `azazel_fabric.testing` — shared factories + invariant assertions for consumer
  CI, with no pytest dependency (`v0.4.0`).

`v0.3.0` renamed the distribution and import namespace from
`azazel-common`/`azazel_common` to `azazel-fabric`/`azazel_fabric` (breaking;
see [`CHANGELOG.md`](CHANGELOG.md)). New series products should start from the
[day-1 adoption guide](docs/adoption-guide.md).

## Consumer status

| Product | Status |
|---|---|
| Azazel-Gadget (AZ-02) | Shipping — currently pins `v0.2.0` under the old `azazel-common` name, emits and reads back `StatusView` (`/api/state` `status_view` key). Migration path: bump the pin to `v0.3.0` and switch imports to `azazel_fabric` |
| Azazel-Edge (AZ-01) | Shipping (merged 2026-07-10, Azazel-Edge#309) — commit-pinned `azazel-fabric`; emits `DecisionExplanation`/`TrustCapsule`/`AuditEvent` projections plus `StatusView` (`/api/state` `status_view` key). The series' largest Fabric consumer |
| Azazel-Knowledge (AZ-04, formerly Azazel-CTI) | Not adopted — gated on Azazel-Knowledge's dependency-minimality policy (stdlib + PyYAML + idna + PyNaCl core; no `pydantic`), pending a `pyproject.toml`/ADR decision on that side |

See `docs/migration-plan.md` for the phase-by-phase detail behind this
table.

## Install

```bash
pip install "azazel-fabric @ git+https://github.com/01rabbit/Azazel-Fabric.git@v0.3.0"
```

`v0.2.0` and earlier remain installable under the old `azazel-common` /
`azazel_common` names by pinning that tag (old repository URLs redirect to
`01rabbit/Azazel-Fabric`); new consumers should install `v0.3.0` or later.

Consumers pin an exact tag, never a branch (see
[`docs/design-principles.md`](docs/design-principles.md) §6).

```python
from azazel_fabric.schema import StateSnapshot, DecisionExplanation
from azazel_fabric.cti_contracts import CtiContextResponse
from azazel_fabric.view import StatusView, build_status_view
from azazel_fabric.api import error_payload, role_allows, extract_token
from azazel_fabric.notify import NotificationEvent, to_ntfy_payload
from azazel_fabric.paths import candidate_runtime_dirs, plan_migration
from azazel_fabric.audit import project_audit_event, to_jsonl_line
from azazel_fabric.testing import make_status_view, assert_advisory_only
```

Adopting Fabric in a new series product? Start with the
[day-1 adoption guide](docs/adoption-guide.md).

## Versioning

Version management is tag-driven on GitHub. The single source of truth is
`src/azazel_fabric/version.py`; each release is a `vX.Y.Z` git tag plus a
matching GitHub Release. The `Release` workflow validates that a pushed tag
matches the packaged version and runs the test suite before publishing. See
[`CHANGELOG.md`](CHANGELOG.md) and `docs/migration-plan.md` for the SemVer
progression.

## Documentation

See [`docs/architecture.md`](docs/architecture.md) for the full picture,
and start there before reading the rest:

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Azazel-Fabric's position in the series and responsibility boundaries |
| [`docs/design-principles.md`](docs/design-principles.md) | What goes in Fabric vs. what never does, and why |
| [`docs/contracts.md`](docs/contracts.md) | The shared schema and the Edge/Gadget ↔ CTI advisory contract (§3–§5 ratified/implemented in `v0.4.0`) |
| [`docs/adoption-guide.md`](docs/adoption-guide.md) | Day-1 adoption playbook for a new series product |
| [`docs/migration-plan.md`](docs/migration-plan.md) | Phased, additive, reversible rollout plan |
| [`docs/repository-layout.md`](docs/repository-layout.md) | Package layout (real as of `v0.4.0`) |
| [`docs/issue-breakdown.md`](docs/issue-breakdown.md) | Proposed GitHub issues for implementation |

## License

TBD.
