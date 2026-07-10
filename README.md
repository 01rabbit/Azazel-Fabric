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

**`v0.3.0` — renamed to Azazel-Fabric.** The distribution and import
namespace changed from `azazel-common`/`azazel_common` to
`azazel-fabric`/`azazel_fabric`; this is a breaking change (see
`CHANGELOG.md`). Functionally, `azazel_fabric` still ships the shared
schema and CTI advisory contract (`v0.1.0`), plus `azazel_fabric.view` —
the shared `StatusView` view-model and `build_status_view` builder that let
Edge and Gadget present the same status the same way. Fabric owns the
view-model; each product keeps its own renderer (see
[`docs/design-principles.md`](docs/design-principles.md) §3.1). The
`paths`/`audit`/`api`/`notify` helpers are later phases and are not present yet.

## Consumer status

| Product | Status |
|---|---|
| Azazel-Gadget (AZ-02) | Shipping — currently pins `v0.2.0` under the old `azazel-common` name, emits and reads back `StatusView` (`/api/state` `status_view` key). Migration path: bump the pin to `v0.3.0` and switch imports to `azazel_fabric` |
| Azazel-Edge (AZ-01) | Design stage — adapter plan doc in the Edge repository, no code or dependency pin yet |
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
```

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
| [`docs/contracts.md`](docs/contracts.md) | Proposed schema and the Edge/Gadget ↔ CTI advisory contract |
| [`docs/migration-plan.md`](docs/migration-plan.md) | Phased, additive, reversible rollout plan |
| [`docs/repository-layout.md`](docs/repository-layout.md) | Proposed package layout |
| [`docs/issue-breakdown.md`](docs/issue-breakdown.md) | Proposed GitHub issues for implementation |

## License

TBD.
