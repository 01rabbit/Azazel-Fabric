# Contributing to Azazel-Fabric

## Before you start

Read [`docs/design-principles.md`](docs/design-principles.md) and
[`docs/contracts.md`](docs/contracts.md) first. Fabric holds *contracts*,
not *judgment* — the First Principle. This library ships schemas,
view-models, and thin helpers only. It holds **no arbiter, evaluator,
execution, or rendering logic — ever.** If your change would let a product
lose its ability to decide (rather than only its ability to describe a
decision the same way as its siblings), it does not belong here. Also
review `design-principles.md` §4, the six safety boundaries that must hold
across every phase, before touching `cti_contracts`, `audit`, or `view`.

## Branch naming

`<type>/<short-description>`

## Commit message format

`<type>(<scope>): <summary>`

scope: `schema` / `cti-contracts` / `view` / `paths` / `audit` / `api` /
`notify` / `testing` / `docs`

## Pull request rules

- 1 PR = 1 purpose. Do not mix unrelated changes.
- Every PR must include:
  - [ ] `pip install -e ".[test]" && pytest -q` passes (78 baseline —
        never reduce the test count)
  - [ ] Contract changes shipped in the PR are **additive only**;
        breaking changes require a version bump, a `BREAKING` entry in
        `CHANGELOG.md`, and a migration note
  - [ ] `docs/contracts.md` updated in the same PR when any model changes
  - [ ] `CHANGELOG.md` updated

## What not to do

- No new runtime dependencies. `pydantic` is the only one — this is a
  hard rule (see `docs/design-principles.md` §5).
- No decision or execution logic, in any module.
- No framework imports in core modules — `flask`/`fastapi` stay optional
  extras (`azazel-fabric[flask]`, `azazel-fabric[fastapi]`).
- No chain logic in `audit` — hash chains and chain verification are
  product-local by design (Edge's P0 hash chain), not Fabric's job.

## Testing

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
pytest -q
```

## License

Contributions are accepted under the [MIT License](LICENSE).
