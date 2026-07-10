# Azazel-Covenant (formerly Azazel-Common)

Thin, shared contract package for the Azazel series (`Azazel-Edge`,
`Azazel-Gadget`, `Azazel-Grimoire`, and future tools such as `Azazel-Boot`).

Azazel-Covenant is not the decision core of any Azazel product. It is the
series' common language: shared state/action/audit schema, the Edge/Gadget
↔ CTI advisory contract, and thin path/audit/API/notify helpers. Each
product's own judgment — Edge's Deterministic Arbiter, Grimoire's correlation
engine, Gadget's device control — stays in its own repository. A covenant is
a binding agreement — precisely what a contracts library holds.

## Status

**`v0.3.0` — renamed to Azazel-Covenant.** The distribution and import
namespace changed from `azazel-common`/`azazel_common` to
`azazel-covenant`/`azazel_covenant`; this is a breaking change (see
`CHANGELOG.md`). Functionally, `azazel_covenant` still ships the shared
schema and CTI advisory contract (`v0.1.0`), plus `azazel_covenant.view` —
the shared `StatusView` view-model and `build_status_view` builder that let
Edge and Gadget present the same status the same way. Covenant owns the
view-model; each product keeps its own renderer (see
[`docs/design-principles.md`](docs/design-principles.md) §3.1). The
`paths`/`audit`/`api`/`notify` helpers are later phases and are not present yet.

## Consumer status

| Product | Status |
|---|---|
| Azazel-Gadget (AZ-02) | Shipping — currently pins `v0.2.0` under the old `azazel-common` name, emits and reads back `StatusView` (`/api/state` `status_view` key). Migration path: bump the pin to `v0.3.0` and switch imports to `azazel_covenant` |
| Azazel-Edge (AZ-01) | Design stage — adapter plan doc in the Edge repository, no code or dependency pin yet |
| Azazel-Grimoire (AZ-04, formerly Azazel-CTI) | Not adopted — gated on Azazel-Grimoire's dependency-minimality policy (stdlib + PyYAML + idna + PyNaCl core; no `pydantic`), pending a `pyproject.toml`/ADR decision on that side |

See `docs/migration-plan.md` for the phase-by-phase detail behind this
table.

## Install

```bash
pip install "azazel-covenant @ git+https://github.com/01rabbit/Azazel-Covenant.git@v0.3.0"
```

`v0.2.0` and earlier remain installable under the old `azazel-common` /
`azazel_common` names by pinning that tag (old repository URLs redirect to
`01rabbit/Azazel-Covenant`); new consumers should install `v0.3.0` or later.

Consumers pin an exact tag, never a branch (see
[`docs/design-principles.md`](docs/design-principles.md) §6).

```python
from azazel_covenant.schema import StateSnapshot, DecisionExplanation
from azazel_covenant.cti_contracts import CtiContextResponse
from azazel_covenant.view import StatusView, build_status_view
```

## Versioning

Version management is tag-driven on GitHub. The single source of truth is
`src/azazel_covenant/version.py`; each release is a `vX.Y.Z` git tag plus a
matching GitHub Release. The `Release` workflow validates that a pushed tag
matches the packaged version and runs the test suite before publishing. See
[`CHANGELOG.md`](CHANGELOG.md) and `docs/migration-plan.md` for the SemVer
progression.

## Documentation

See [`docs/architecture.md`](docs/architecture.md) for the full picture,
and start there before reading the rest:

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Azazel-Covenant's position in the series and responsibility boundaries |
| [`docs/design-principles.md`](docs/design-principles.md) | What goes in Covenant vs. what never does, and why |
| [`docs/contracts.md`](docs/contracts.md) | Proposed schema and the Edge/Gadget ↔ CTI advisory contract |
| [`docs/migration-plan.md`](docs/migration-plan.md) | Phased, additive, reversible rollout plan |
| [`docs/repository-layout.md`](docs/repository-layout.md) | Proposed package layout |
| [`docs/issue-breakdown.md`](docs/issue-breakdown.md) | Proposed GitHub issues for implementation |

## License

TBD.
