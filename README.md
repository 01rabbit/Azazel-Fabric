# Azazel-Common

Thin, shared contract package for the Azazel series (`Azazel-Edge`,
`Azazel-Gadget`, `Azazel-CTI`, and future tools such as `Azazel-Boot`).

Azazel-Common is not the decision core of any Azazel product. It is the
series' common language: shared state/action/audit schema, the Edge/Gadget
↔ CTI advisory contract, and thin path/audit/API/notify helpers. Each
product's own judgment — Edge's Deterministic Arbiter, CTI's correlation
engine, Gadget's device control — stays in its own repository.

## Status

**Design stage.** This repository currently holds design documents only;
no package code has been written yet.

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
