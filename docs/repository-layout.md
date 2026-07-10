# Azazel-Covenant (formerly Azazel-Common): Repository and Package Layout

Status: **Partially implemented.** `src/azazel_covenant/schema/`,
`cti_contracts/`, and `view/` exist on disk exactly as laid out below and
shipped in `v0.1.0`/`v0.2.0` (under the `azazel_common` import path at the
time; `v0.3.0` renamed the package to `azazel_covenant` with no change to
this layout — see `CHANGELOG.md`). `paths/`, `audit/`, `api/`, `notify/`,
and `testing/` remain proposal only — not yet scaffolded, per the Phase-5
note below.

## Repository name

```
01rabbit/Azazel-Covenant
```

(Not `Azazel-Core` — see `architecture.md` §1 and `design-principles.md`
§4.6 for why. Not `Azazel-Common` either, as of `v0.3.0` — same section.)

## Repository layout

```
Azazel-Covenant/
├── README.md
├── LICENSE
├── pyproject.toml
├── CHANGELOG.md
├── src/
│   └── azazel_covenant/
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
│       ├── paths/                  # Phase 5
│       │   ├── __init__.py
│       │   ├── schema.py           # runtime/config/log dir resolution
│       │   └── migration.py        # legacy-path dry-run migration helper
│       ├── audit/                  # Phase 5
│       │   ├── __init__.py
│       │   ├── jsonl.py            # JSONL writer, trace_id generator, config_hash helper
│       │   └── chain.py            # HMAC / chain-of-custody helper (future extension point)
│       ├── api/                    # Phase 5
│       │   ├── __init__.py
│       │   ├── auth.py             # token auth helper (X-AZAZEL-TOKEN / X-Auth-Token)
│       │   ├── roles.py            # viewer/operator/responder/admin
│       │   └── errors.py           # standard JSON error model, fail-closed default
│       ├── notify/                 # Phase 5
│       │   ├── __init__.py
│       │   ├── model.py            # shared notification event schema
│       │   ├── ntfy.py             # thin ntfy send helper
│       │   └── mattermost.py       # thin Mattermost send helper
│       ├── view/                    # v0.2.0 — shared status view-model
│       │   ├── __init__.py
│       │   ├── status.py            # StatusView, HealthDimension (Edge-lineage superset)
│       │   └── build.py             # build_status_view helper (shared derivation)
│       └── testing/
│           ├── __init__.py
│           ├── fixtures.py         # shared pytest fixtures for consumer contract tests
│           └── contract_cases.py   # canonical valid/invalid payload examples per schema
├── tests/
│   ├── test_schema_state.py
│   ├── test_schema_decision.py
│   ├── test_cti_contracts.py
│   ├── test_audit_jsonl.py
│   ├── test_paths.py
│   └── test_api_auth_models.py
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
- `azazel_covenant.paths`, `.audit`, `.api`, `.notify`, and `.testing`
  directories are shown now for completeness of the target layout, but
  remain **not scaffolded** — they are added when their phase starts (see
  `migration-plan.md` Phase 5), so released code has no dead code.
- `action.py`'s `ObservePlan`..`ReleasePlan` are abstract, data-only plan
  descriptions (see `architecture.md`'s Action Plan section) — they carry
  no execution logic and no adapter to nft/tc/OpenCanary. Converting a
  plan into an actual firewall rule, traffic-control action, or canary
  deployment remains entirely inside Edge/Gadget adapters.

## `pyproject.toml` shape (illustrative)

```toml
[project]
name = "azazel-covenant"
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
# in Azazel-Edge / Azazel-Gadget / Azazel-Grimoire's own requirements
azazel-covenant @ git+https://github.com/01rabbit/Azazel-Covenant.git@v0.3.0
```

Tag-pinned, not branch-pinned, not a submodule (see
`design-principles.md` §6). Tags `v0.1.0`/`v0.2.0` predate the `v0.3.0`
rename and use the old `azazel-common` distribution name against the same,
redirected repository URL — see `README.md`'s Install section and
`CHANGELOG.md`.
