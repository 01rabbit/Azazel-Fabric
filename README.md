# Azazel-Common

Thin, shared contract package for the Azazel series (`Azazel-Edge`,
`Azazel-Gadget`, `Azazel-CTI`, and future tools such as `Azazel-Boot`).

Azazel-Common is not the decision core of any Azazel product. It is the
series' common language: shared state/action/audit schema, the Edge/Gadget
↔ CTI advisory contract, and thin path/audit/API/notify helpers. Each
product's own judgment — Edge's Deterministic Arbiter, CTI's correlation
engine, Gadget's device control — stays in its own repository.

## Status

**`v0.1.0` — schema-only.** The `azazel_common` package now ships the shared
schema and the CTI advisory contract, per
[`docs/migration-plan.md`](docs/migration-plan.md) Phase 1. The
`paths`/`audit`/`api`/`notify` helpers are later phases and are not present
yet. No existing Azazel product depends on this package yet.

## Install

```bash
pip install "azazel-common @ git+https://github.com/01rabbit/Azazel-Common.git@v0.1.0"
```

Consumers pin an exact tag, never a branch (see
[`docs/design-principles.md`](docs/design-principles.md) §6).

```python
from azazel_common.schema import StateSnapshot, DecisionExplanation
from azazel_common.cti_contracts import CtiContextResponse
```

## Versioning

Version management is tag-driven on GitHub. The single source of truth is
`src/azazel_common/version.py`; each release is a `vX.Y.Z` git tag plus a
matching GitHub Release. The `Release` workflow validates that a pushed tag
matches the packaged version and runs the test suite before publishing. See
[`CHANGELOG.md`](CHANGELOG.md) and `docs/migration-plan.md` for the SemVer
progression.

## Documentation

See [`docs/architecture.md`](docs/architecture.md) for the full picture,
and start there before reading the rest:

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Azazel-Common's position in the series and responsibility boundaries |
| [`docs/design-principles.md`](docs/design-principles.md) | What goes in Common vs. what never does, and why |
| [`docs/contracts.md`](docs/contracts.md) | Proposed schema and the Edge/Gadget ↔ CTI advisory contract |
| [`docs/migration-plan.md`](docs/migration-plan.md) | Phased, additive, reversible rollout plan |
| [`docs/repository-layout.md`](docs/repository-layout.md) | Proposed package layout |
| [`docs/issue-breakdown.md`](docs/issue-breakdown.md) | Proposed GitHub issues for implementation |

## License

TBD.
