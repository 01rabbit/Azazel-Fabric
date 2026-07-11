# Azazel-Fabric (formerly Azazel-Common): Repository and Package Layout

Status: **Implemented.** `src/azazel_fabric/schema/`, `cti_contracts/`, and
`view/` shipped in `v0.1.0`/`v0.2.0` (under the `azazel_common` import path at
the time; `v0.3.0` renamed the package to `azazel_fabric` with no change to this
layout — see `CHANGELOG.md`). `paths/`, `audit/`, `api/`, `notify/`, and
`testing/` are now scaffolded and real as of `v0.4.0` (Phase 5/6). The tree
below reflects the actual files on disk; a few leaf filenames differ from the
original proposal (noted inline) where the real implementation consolidated or
renamed a file.

## Repository name

```
01rabbit/Azazel-Fabric
```

(Not `Azazel-Core` — see `architecture.md` §1 and `design-principles.md`
§4.6 for why. Not `Azazel-Common` either, as of `v0.3.0` — same section.)

## Repository layout

```
Azazel-Fabric/
├── README.md
├── LICENSE
├── pyproject.toml
├── CHANGELOG.md
├── src/
│   └── azazel_fabric/
│       ├── __init__.py
│       ├── version.py
│       ├── schema/
│       │   ├── __init__.py
│       │   ├── state.py            # StateSnapshot
│       │   ├── mode.py             # ModeState
│       │   ├── action.py           # ActionIntent, ObservePlan..ReleasePlan (abstract only)
│       │   ├── evidence.py         # EvidenceRef
│       │   ├── decision.py         # DecisionExplanation
│       │   ├── audit.py            # AuditEvent
│       │   └── trust.py            # TrustCapsule
│       ├── cti_contracts/
│       │   ├── __init__.py
│       │   ├── ingest.py           # CtiEventBatch, CtiFlowBatch, CtiReactionBatch
│       │   ├── reactions.py        # (reaction-specific sub-shapes, if they diverge from ingest.py)
│       │   ├── context.py          # CtiContextRequest, CtiContextResponse, IocMatch
│       │   └── advisory.py         # BehavioralCtiBlock, advisory_notice / limitations helpers
│       ├── paths/                  # Phase 5 (v0.4.0)
│       │   ├── __init__.py
│       │   ├── schema.py           # candidate-path hints + legacy-alias resolution
│       │   └── migration.py        # dry-run-only legacy-path migration planner
│       ├── audit/                  # Phase 5 (v0.4.0)
│       │   ├── __init__.py
│       │   ├── jsonl.py            # JSONL formatters (to/from line, read/write stream)
│       │   └── events.py           # AuditEvent projection + event_id convention
│       │                           # (no chain.py — no hash chain/verification, owner decision)
│       ├── api/                    # Phase 5 (v0.4.0)
│       │   ├── __init__.py
│       │   ├── auth.py             # token extraction (X-AZAZEL-TOKEN / X-Auth-Token)
│       │   ├── roles.py            # viewer/operator/responder/admin, fail-closed
│       │   └── errors.py           # standard JSON error model, fail-closed default
│       ├── notify/                 # Phase 5 (v0.4.0)
│       │   ├── __init__.py
│       │   ├── model.py            # shared NotificationEvent schema
│       │   └── transports.py       # pure ntfy/Mattermost payload mappers (no send)
│       │                           # (consolidates the proposed ntfy.py + mattermost.py)
│       ├── view/                    # v0.2.0 — shared status view-model
│       │   ├── __init__.py
│       │   ├── status.py            # StatusView, HealthDimension (Edge-lineage superset)
│       │   └── build.py             # build_status_view helper (shared derivation)
│       └── testing/                 # Phase 6 (v0.4.0)
│           ├── __init__.py
│           ├── factories.py        # make_*/minimal_* builders (no pytest dependency)
│           └── invariants.py       # assert_advisory_only + friends (plain functions)
├── tests/
│   ├── test_schema_state.py
│   ├── test_schema_decision.py
│   ├── test_schema_records.py
│   ├── test_cti_contracts.py
│   ├── test_view_status.py
│   ├── test_paths.py
│   ├── test_audit.py
│   ├── test_api.py
│   ├── test_notify.py
│   └── test_testing_module.py
└── docs/
    ├── architecture.md
    ├── design-principles.md
    ├── migration-plan.md
    └── contracts.md
```

Notes:

- The `docs/` files listed above already exist in this repository as the
  design record; they are kept in sync as implementation lands under
  `src/`.
- **Implemented as of `v0.2.0`:** `schema/` (seven modules, `v0.1.0`),
  `cti_contracts/` (four modules, `v0.1.0`), and `view/` (`status.py` +
  `build.py`, `v0.2.0` — added a phase ahead of its originally-planned
  slot; see `migration-plan.md` Phase 4). `tests/` correspondingly has
  `test_schema_state.py`, `test_schema_decision.py`,
  `test_schema_records.py`, `test_cti_contracts.py`, and
  `test_view_status.py`.
- **Implemented as of `v0.4.0` (Phase 5/6):** `paths/`, `audit/`, `api/`,
  `notify/`, and `testing/`, with matching `test_paths.py`, `test_audit.py`,
  `test_api.py`, `test_notify.py`, and `test_testing_module.py`. A few leaf
  filenames diverged from the original proposal, reconciled in the tree above:
  `audit/` has `jsonl.py` + `events.py` and **no `chain.py`** (no hash chain or
  verification — owner decision; chains stay product-local); `notify/`
  consolidates the proposed `ntfy.py` + `mattermost.py` into a single pure
  `transports.py` (payload mappers, no network send); `testing/` ships
  `factories.py` + `invariants.py` (plain functions, no pytest dependency)
  rather than `fixtures.py` + `contract_cases.py`.
- `action.py`'s `ObservePlan`..`ReleasePlan` are abstract, data-only plan
  descriptions (see `architecture.md`'s Action Plan section) — they carry
  no execution logic and no adapter to nft/tc/OpenCanary. Converting a
  plan into an actual firewall rule, traffic-control action, or canary
  deployment remains entirely inside Edge/Gadget adapters.

## `pyproject.toml` shape (illustrative)

```toml
[project]
name = "azazel-fabric"
version = "0.1.0"
description = "Shared contracts for the Azazel series (schema, CTI advisory contract, audit/path/api/notify helpers)"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2,<3",
]

[project.optional-dependencies]
flask = ["flask>=2"]
fastapi = ["fastapi>=0.100"]
test = ["pytest>=7"]

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

Kept intentionally minimal: Pydantic is the only hard runtime dependency,
consistent with the Raspberry Pi weight constraint in
`design-principles.md` §5. Flask/FastAPI adapters are opt-in extras.

## Consumption pattern from a product repository

```toml
# in Azazel-Edge / Azazel-Gadget / Azazel-Knowledge's own requirements
azazel-fabric @ git+https://github.com/01rabbit/Azazel-Fabric.git@v0.3.0
```

Tag-pinned, not branch-pinned, not a submodule (see
`design-principles.md` §6). Tags `v0.1.0`/`v0.2.0` predate the `v0.3.0`
rename and use the old `azazel-common` distribution name against the same,
redirected repository URL — see `README.md`'s Install section and
`CHANGELOG.md`.
