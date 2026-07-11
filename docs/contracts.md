# Azazel-Fabric (formerly Azazel-Common): Contracts

Status: **Mixed — see per-section status lines.** §1 (`azazel_fabric.schema`)
and §2 (`azazel_fabric.cti_contracts`) SHIPPED in `v0.1.0`; §2's
advisory-only invariants and the `view.StatusView` model referenced
alongside them SHIPPED in `v0.2.0` (see `CHANGELOG.md`). §3–§5
(`api`/`notify`/`paths`) are now **ratified and implemented in `v0.4.0`**
(Phase 5); each section carries a status line noting deviations from the
original proposal. Consult the source and `tests/` for exact, current field
signatures — the tables below are a readable reference, not the authoritative
schema.

Schemas in §1/§2 are implemented as Pydantic v2 models under
`azazel_fabric.schema` and `azazel_fabric.cti_contracts`; consult the
source and `tests/` for exact, current field signatures — the tables below
are a readable reference, not the authoritative schema.

## 1. State / mode / action contracts (`azazel_fabric.schema`)

**Status: SHIPPED (`v0.1.0`).** No consumer has adopted `StateSnapshot`
end-to-end yet — see `migration-plan.md` for per-product adoption status.

### `StateSnapshot`

The single shape that Web UI, TUI, E-Paper, and any status API read to
render "what is the system doing right now."

| field | type | notes |
|---|---|---|
| `schema_version` | str | e.g. `"1.0"` |
| `product` | Literal[`"edge"`, `"gadget"`, `"cti"`, ...] | which Azazel product emitted this |
| `mode` | `ModeState` | current operating mode |
| `generated_at` | str (ISO 8601) | snapshot timestamp |
| `trace_id` | str | correlates with `AuditEvent`/`TrustCapsule` |
| `summary` | dict[str, Any] | product-specific, loosely-typed payload for fields that don't warrant their own shared schema yet |

### `ModeState`

| field | type | notes |
|---|---|---|
| `name` | Literal[`"portal"`, `"shield"`, `"scapegoat"`, `"observe"`, `"lockdown"`, ...] | open enum — products may register additional values via a documented extension list, not by breaking the base type |
| `since` | str (ISO 8601) | when this mode was entered |
| `reason` | str \| None | human-readable, optional |

### `ActionIntent`

Describes an *intended* action shape — not an executor, not a command to
nft/tc/OpenCanary. See `architecture.md` §4 and `migration-plan.md` for why
execution stays out of Fabric.

| field | type | notes |
|---|---|---|
| `kind` | Literal[`"observe"`, `"notify"`, `"throttle"`, `"redirect"`, `"isolate"`, `"decoy"`, `"release"`] | |
| `target` | str | opaque identifier (IP, session id, device id — product-defined) |
| `issued_by` | str | which component/product issued this intent |
| `evidence` | list[`EvidenceRef`] | |
| `trace_id` | str | |

### `EvidenceRef`

| field | type | notes |
|---|---|---|
| `evidence_id` | str | |
| `source` | str | e.g. `"noc_evaluator"`, `"soc_evaluator"`, `"cti_advisory"` |
| `trace_id` | str | |
| `observed_at` | str (ISO 8601) | |

### `DecisionExplanation`

The shared shape for "why did the system do this," independent of which
product's arbiter produced it.

| field | type | notes |
|---|---|---|
| `selected_action` | `ActionIntent` | |
| `why_chosen` | str | |
| `why_not_others` | list[str] | |
| `release_condition` | str \| None | condition under which this decision should be revisited/released |
| `confidence` | float \| None | 0.0–1.0, optional |
| `trace_id` | str | |

### `AuditEvent`

Standard JSONL audit-log record shape.

| field | type | notes |
|---|---|---|
| `event_id` | str | |
| `trace_id` | str | |
| `timestamp` | str (ISO 8601) | |
| `product` | str | |
| `event_type` | str | |
| `payload` | dict[str, Any] | product-defined body |
| `config_hash` | str \| None | |
| `hmac` | str \| None | tamper-evidence signature, optional |

**`azazel_fabric.audit` helpers — Status: implemented (`v0.4.0`).** The module
ships the shared-`AuditEvent` **projection** (`project_audit_event`,
`make_event_id`) and **JSONL formatters** (`to_jsonl_line` / `from_jsonl_line` /
`iter_jsonl` / `write_jsonl` / `read_jsonl`) — the *envelope* an audit event is
written in. **Explicit non-goal (owner decision, 2026-07-10/11): no hash chain
and no chain verification.** Edge's P0 hash-chain / tamper-evidence audit is
deliberately product-local and out of Fabric's scope; the `config_hash`/`hmac`
fields above are carried verbatim if a product supplies them, but Fabric neither
computes nor verifies them, and ships no chain-of-custody linkage. (This
supersedes the "(future) chain-of-custody helper" note in
`design-principles.md` §2, which is not built and, per this decision, will not
be.)

### `TrustCapsule`

| field | type | notes |
|---|---|---|
| `trace_id` | str | |
| `config_hash` | str | |
| `hmac` | str | |
| `issued_at` | str (ISO 8601) | |

Note: `azazel_fabric.view` (`StatusView`, `build_status_view`) shipped in
`v0.2.0` alongside this schema layer; it is not tabulated in this document
— see `design-principles.md` §3.1 and the CHANGELOG for its shape.

## 2. CTI contract (`azazel_fabric.cti_contracts`)

**Status: SHIPPED (`v0.1.0`), advisory-only invariants hardened in
`v0.2.0`.** Despite shipping, this remains, as described below, "the
highest-priority contract" with **no adopting consumer on either side
today**: Azazel-Knowledge has not adopted `cti_contracts` (blocked on its
dependency-minimality constraint — see `migration-plan.md` Phase 2), and
Azazel-Edge's adoption is still at the plan-document stage (Phase 3), which
itself defers real Edge↔Knowledge integration to FY2027+. This is a known
gap, not a regression — the schema shipping ahead of any consumer wiring it
in was Fabric's own choice to keep `v0.1.0` small and reviewable.

This is the highest-priority contract in the initial release: it is the
only place where two *different* repositories (Edge/Gadget and Knowledge)
must agree on wire format across a network boundary today.

### Direction and endpoints

| Direction | Endpoint | Payload schema |
|---|---|---|
| Edge/Gadget → Knowledge | `POST /v1/events` | `CtiEventBatch` |
| Edge/Gadget → Knowledge | `POST /v1/flows` | `CtiFlowBatch` |
| Edge/Gadget → Knowledge | `POST /v1/reactions` | `CtiReactionBatch` |
| Edge/Gadget → Knowledge | `POST /v1/context` | `CtiContextRequest` |
| Knowledge → Edge/Gadget | response to `/v1/context` | `CtiContextResponse` |

### `CtiEventBatch` / `CtiFlowBatch` / `CtiReactionBatch`

Common envelope shape (exact per-event field lists to be finalized against
current Azazel-Knowledge API during Issue 3, without breaking its existing
consumers):

| field | type | notes |
|---|---|---|
| `batch_id` | str | |
| `source_product` | Literal[`"edge"`, `"gadget"`] | |
| `source_device_id` | str | |
| `generated_at` | str (ISO 8601) | |
| `items` | list[dict] | events/flows/reactions; product-typed sub-schema layered on later, not forced in v0.1.0 |

### `CtiContextRequest`

| field | type | notes |
|---|---|---|
| `request_id` | str | |
| `source_product` | Literal[`"edge"`, `"gadget"`] | |
| `indicators` | list[str] | IPs, hashes, domains, etc. being queried |
| `trace_id` | str | |

### `CtiContextResponse`

This schema is the concrete encoding of the advisory-only boundary
described in `design-principles.md` §4.2–§4.3.

| field | type | notes |
|---|---|---|
| `request_id` | str | echoes the request |
| `matches` | list[`IocMatch`] | may be empty |
| `behavioral_cti` | `BehavioralCtiBlock` \| **omitted** | **Not present in the payload when there is nothing to report — never sent as `null`.** Consumers must treat a missing key and an empty object identically: "no behavioral signal available." |
| `advisory_notice` | str \| None | free-text advisory framing, explicitly non-directive |
| `limitations` | list[str] | e.g. `"feed stale > 24h"`, `"partial coverage"` |
| `source_freshness` | str (ISO 8601) \| None | |
| `generated_at` | str (ISO 8601) | |

`IocMatch` (nested):

| field | type | notes |
|---|---|---|
| `indicator` | str | |
| `confidence` | float | 0.0–1.0 |
| `reason` | list[str] | |
| `source_freshness` | str (ISO 8601) \| None | |

**Explicitly excluded fields, by design:** no `directive`, no
`must_execute`, no `override`, no `required_action`. Any field that reads
as an instruction rather than information is out of scope for this schema
and must be rejected in review if proposed later.

### Failure-mode contract

This is a behavioral contract, not just a schema, and must be documented
alongside the schema wherever it is implemented:

- A Knowledge response that fails validation, times out, or is unreachable
  **must** be treated by the caller as "no advisory context available,"
  and must **not** raise an exception that halts the calling product's own
  decision path.
- `CtiContextResponse.behavioral_cti` being absent is a normal, expected
  state, not an error state.

## 3. API / auth contracts (`azazel_fabric.api`)

**Status: ratified / implemented (`v0.4.0`, Phase 5).** Framework-neutral
security-posture helpers, not endpoint specs — just the shared vocabulary, now
built:

| concept | shape |
|---|---|
| token header | `X-AZAZEL-TOKEN` (primary), `X-Auth-Token` (compat alias) |
| roles | `viewer`, `operator`, `responder`, `admin` (ordered, least→most privileged) |
| default posture | fail-closed: missing/invalid credentials → reject, never default-allow |
| error shape | `{"error": {"code": str, "message": str, "trace_id": str | None}}` |

Implemented as: `ErrorEnvelope`/`ErrorBody` models + `error_payload` /
`fail_closed_error` builders (`errors.py`); `ROLES` / `role_rank` / `role_allows`
/ `is_known_role` (`roles.py`, fail-closed — an unknown role never satisfies or
out-ranks); `TOKEN_HEADER` / `COMPAT_TOKEN_HEADER` / `extract_token` (primary
then compat, case-insensitive) / `token_matches` (constant-time, fail-closed)
(`auth.py`). No Flask/FastAPI import in core — adapters stay optional extras
(design-principles §5).

**Deviations from the proposal:** (a) `error_payload`/`fail_closed_error` omit
`trace_id` from the payload when it is `None` (absent, not `null`), matching the
series' absent-not-null convention elsewhere in this document; the model still
*permits* `trace_id: str | None`. (b) The proposal named "fail-closed default
response" abstractly; it is realized as `fail_closed_error()` returning the
standard error payload with code `unauthenticated` — Fabric returns the payload,
a framework adapter attaches the HTTP status.

## 4. Notification contract (`azazel_fabric.notify`)

**Status: ratified / implemented (`v0.4.0`, Phase 5).** `NotificationEvent`
(`model.py`) ships exactly as tabulated:

| field | type | notes |
|---|---|---|
| `event_id` | str | |
| `product` | str | |
| `severity` | Literal[`"info"`, `"warning"`, `"critical"`] | |
| `title` | str | |
| `body` | str | |
| `trace_id` | str \| None | |
| `created_at` | str (ISO 8601) | |

Transport-specific adapters (ntfy, Mattermost, SSE) consume this shape;
they do not define their own competing payload shape.

**Deviation from the proposal:** the transport helpers are implemented as pure
payload *mappers* — `to_ntfy_payload` / `to_mattermost_payload`
(`transports.py`) — that build and return a transport-shaped `dict` but **do not
send** anything. No HTTP client or socket is imported; actual delivery (endpoint,
auth, retry) stays product-side, consistent with the dependency-weight and
offline-first principles. The SSE "bridge" from design-principles §2 is not a
separate model — `NotificationEvent` is itself the SSE payload shape.

## 5. Path contract (`azazel_fabric.paths`)

**Status: ratified / implemented (`v0.4.0`, Phase 5).** Implemented as pure
candidate-path **hints**, never authority — a product keeps its own path schema
(Edge's legacy-compat paths are not forced through this).

| concept | convention |
|---|---|
| runtime dir | `/run/azazel-<product>` (e.g. `/run/azazel-edge`) |
| config dir | `/etc/azazel-<product>` |
| log dir | `/var/log/azazel-<product>` |
| legacy compatibility | `azazel-pi` → maps to `azazel-edge` path schema; `azazel-zero` → maps to `azazel-gadget` path schema |
| migration | dry-run-first helper; never silently moves/deletes files |

Implemented as: `candidate_runtime_dirs` / `candidate_config_dirs` /
`candidate_log_dirs` / `candidate_dirs` / `preferred_dir`, `normalize_product`
(legacy-alias resolution), and `plan_migration` → `MigrationPlan`/`MigrationStep`
(`schema.py`, `migration.py`). All pure and deterministic — no filesystem,
environment, or clock access.

**Deviations from the proposal:** (a) The runtime/config/log rows describe a
single conventional directory; the helpers return **candidate *lists*** (best
canonical path first, any legacy-alias path after) rather than one authoritative
path — per the owner's Phase-5 decision that these are hints returning candidate
lists, so a caller can discover a legacy sibling's directory while preferring the
modern one. `preferred_dir` returns just the first (canonical) candidate for
callers that want a single string. (b) The migration helper is **plan-only**:
`plan_migration` returns a described `MigrationPlan` (`dry_run=True` always) and
there is deliberately **no `execute` function** — stronger than "dry-run-first,"
since Fabric never performs a move at all; executing the plan is the product's
choice.
