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
`Azazel-Gadget`, `Azazel-Knowledge`, `Azazel-Deception`).

Azazel-Fabric is not the decision core of any Azazel product. It is the
series' common language. Each product's own judgment stays in its own
repository: Edge owns deterministic decisions and enforcement, Knowledge
analyzes/advises, Gadget owns its local mode control, and Deception
materializes only Edge-approved environments. Fabric owns the shared wire
contracts; it does not decide, enforce, or execute.

## Status

**Latest stable release: `v0.8.0`** — canonical Edge-decision transport
signatures. A consumer that needs stability pins this tag.

The stable install command is under [Install](#install); development checks are under [Development checks](#development-checks).

Release state, as recorded in [`src/azazel_fabric/version.py`](src/azazel_fabric/version.py)
and [release compatibility](docs/release-compatibility.md):

| Channel | State |
|---|---|
| Latest stable | `v0.8.0` (a `vX.Y.Z` tag with a GitHub Release). |
| Published candidates | `v0.9.0rc1` through `v0.9.0rc5`. Each is an exact, pinnable tag with no stability promise. `v0.9.0rc5` is the latest published tag. |
| `main` | `0.9.0rc6.dev0`. Explicitly unreleased; it is not any tag. `v0.9.0rc6` is **not** cut. |
| `v0.7.0` | **Never tagged or released.** Its advisory-only engagement contracts shipped inside `v0.8.0`, so `v0.6.0` → `v0.8.0` is the only upgrade path. |
| `v0.9.0` | Not cut. It waits on downstream evidence. |

Candidate contract changes, all on top of `v0.8.0`:

- `v0.9.0rc1` — `azazel_fabric.outcome_contracts`, and the R1a
  `provisioning_contracts` and `mio_contracts` families.
- `v0.9.0rc2` — the canonical `DefensiveState` vocabulary
  (`azazel_fabric.schema.defensive_state`) and the cross-series
  `effect_contracts` family.
- `v0.9.0rc3` — a typed cross-series reference may carry further colons in its
  body. Required for any `effect_contracts` adopter.
- `v0.9.0rc4` — **non-additive:** an `EffectObservation` may claim only
  `observed_fact` or `active_materialized`. Input accepted at `rc3` is refused.
- `v0.9.0rc5` — presented-terrain provenance fields (`source_effect_ref`,
  `trace_id`, `synthetic_identity_refs`, `synthetic_credential_refs`), and
  `activation_decision_ref` becomes optional. Additive.

A consumer adopting a candidate pins an exact candidate tag, never a branch,
and expects to re-pin to `v0.9.0`. See the
[release compatibility](docs/release-compatibility.md) document for the
supported contract families and the observed consumer pins.

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

Consumer pins checked on **2026-11-04** against each consumer's dependency
declaration. Each consumer's own declaration is the authority for what it
currently pins.

| Product | Observed pin | Last observed | Status |
|---|---|---|---|
| Azazel-Edge (AZ-01) | `v0.9.0rc4` in `requirements/fabric.txt` (candidate) | 2026-11-04 | Fabric remains optional for baseline Edge runtime. |
| Azazel-Gadget (AZ-02) | `v0.8.0` (stable) | 2026-11-04 | Stable tag. |
| Azazel-Knowledge (AZ-04) | `v0.9.0rc5` in the API optional dependency (candidate) | 2026-11-04 | Core remains dependency-minimal and advisory-only. |
| Azazel-Deception (AZ-06) | `v0.9.0rc5` in `pyproject.toml` (candidate) | 2026-11-04 | Live exposure remains disabled by default. |

The consumers do not all pin the same release: Edge is on `v0.9.0rc4`,
Knowledge and Deception are on `v0.9.0rc5`, and Gadget is on the stable
`v0.8.0`. There is therefore no single "reference release" until `v0.9.0` is
cut.
[`docs/release-compatibility.md`](docs/release-compatibility.md) is the
authority for this table and carries the reasoning behind each row.

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

## Development checks

Contributors run the suite from a checkout, as CI does:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
pytest -q
```

Dependencies, as declared in `pyproject.toml`:

- **Runtime:** `pydantic>=2,<3` only. This is the only permitted runtime
  dependency.
- **Optional extras:** `flask>=2` and `fastapi>=0.100`, for their adapters only.
- **`test` extra:** `pytest>=7`.

CI runs Python 3.10, 3.11 and 3.12 on Ubuntu. Two things the install command
does not provide:

- CI also installs `pynacl`. It is not declared, because it is needed only to
  verify release signatures (`tools/rc_signature.py`) and is not part of the
  installable surface. Without it the signature guards skip, and a skipped
  guard would look like a pass.
- The feature-minimum test compares each feature against the release tags, so
  a local checkout needs them: `git fetch --tags`. CI fetches full history and
  tags, and fails rather than skips when there are none.

The test count recorded in `CONTRIBUTING.md` (687) is the `0.9.0rc1` baseline,
not a current figure. Contributions must not reduce it.

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
makes no stability promise. A `.dev0` value on `main` is explicitly unreleased
(`main` is `0.9.0rc6.dev0` today). The Release workflow validates that a pushed
tag matches the packaged version and runs the test suite before publishing. A
releasable (non-`.dev`) version additionally carries
`release/v<version>.digest.json`, a reproducible sha256 manifest of the
packaged surface generated by `tools/rc_digest.py` and enforced by
`tests/test_release_candidate_digest.py`. The digest is signed; the git tag
itself is not signed and is not a trust boundary.

## Documentation

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Azazel-Fabric's position in the series and responsibility boundaries |
| [`docs/design-principles.md`](docs/design-principles.md) | What goes in Fabric vs. what never does, and why |
| [`docs/contracts.md`](docs/contracts.md) | Stable shared schema and Edge/Gadget ↔ CTI contracts |
| [`docs/deception-contracts.md`](docs/deception-contracts.md) | Canonical AZ-06 contract family (`v0.5.0`), authority and migration rules |
| [`docs/release-signing.md`](docs/release-signing.md) | R1b: how a release-candidate digest is signed (Ed25519, detached) and verified |
| [`docs/provisioning-contracts.md`](docs/provisioning-contracts.md) | Provisioning and M.I.O. contract families (R1a), authority rules, feature-to-minimum-version matrix |
| [`docs/release-compatibility.md`](docs/release-compatibility.md) | Current release truth, supported contract families, and observed consumer pins |
| [`docs/adoption-guide.md`](docs/adoption-guide.md) | Day-1 adoption playbook for a series product |
| [`docs/migration-plan.md`](docs/migration-plan.md) | Phased, additive, reversible rollout plan |
| [`docs/repository-layout.md`](docs/repository-layout.md) | Package layout |
| [`docs/issue-breakdown.md`](docs/issue-breakdown.md) | GitHub implementation work |

## License

MIT. See [`LICENSE`](LICENSE).
