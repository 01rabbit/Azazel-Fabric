"""Audit-event projection + JSONL formatters for the Azazel series.

Standardizes the *envelope* an :class:`~azazel_fabric.schema.audit.AuditEvent`
is written in — a projection builder, an ``event_id`` convention, and JSONL
serialization — so every product writes the shared audit shape the same way.

**Explicit non-goals (owner decision, 2026-07-10/11):** this package ships
**no hash chain and no chain verification**. Edge's P0 hash-chain /
tamper-evidence audit is deliberately product-local and out of scope for
Fabric; Fabric standardizes only the shared ``AuditEvent`` *projection*, not
the integrity mechanism that protects an audit log. See
:mod:`azazel_fabric.audit.events` for the full statement.
"""

from azazel_fabric.audit.events import make_event_id, project_audit_event
from azazel_fabric.audit.jsonl import (
    from_jsonl_line,
    iter_jsonl,
    read_jsonl,
    to_jsonl_line,
    write_jsonl,
)

__all__ = [
    "make_event_id",
    "project_audit_event",
    "to_jsonl_line",
    "from_jsonl_line",
    "iter_jsonl",
    "write_jsonl",
    "read_jsonl",
]
