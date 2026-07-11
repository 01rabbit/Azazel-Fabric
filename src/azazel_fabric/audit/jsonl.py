"""JSONL formatters for the shared `AuditEvent` (`contracts.md` §1).

Serialize an :class:`AuditEvent` to a single JSON line and back, and read/write
a stream of them. This is the *format* an audit log is written in — one JSON
object per line — not the log's integrity mechanism.

Non-goals (owner decision): no hash chain, no chain verification. See
:mod:`azazel_fabric.audit.events` for the full non-goal statement. These
functions never link, digest, or verify events across lines; each line stands
alone.
"""

from __future__ import annotations

import json
from typing import IO, Iterable, Iterator

from azazel_fabric.schema.audit import AuditEvent


def to_jsonl_line(event: AuditEvent) -> str:
    """Serialize one :class:`AuditEvent` to a single JSON line (no newline).

    Uses a compact separator and sorted keys so the same event always produces
    byte-identical output — convenient for tests and for a product that wants a
    stable serialization. ``None`` fields are kept (a JSONL reader expects a
    fixed shape), unlike the CTI response's absent-is-omitted rule.
    """
    return json.dumps(event.model_dump(), sort_keys=True, separators=(",", ":"))


def from_jsonl_line(line: str) -> AuditEvent:
    """Parse one JSONL line back into an :class:`AuditEvent`.

    Validation is Pydantic's; a malformed line raises, as a caller reading an
    audit log would want (this is a formatter, not a fail-open advisory path).
    """
    return AuditEvent.model_validate_json(line)


def iter_jsonl(text: str) -> Iterator[AuditEvent]:
    """Yield :class:`AuditEvent` for each non-blank line of ``text``."""
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped:
            yield from_jsonl_line(stripped)


def write_jsonl(events: Iterable[AuditEvent], fp: IO[str]) -> int:
    """Write ``events`` to a text file-like object, one JSON line each.

    Takes an already-open file-like object (e.g. a file handle or
    ``io.StringIO``) rather than a path, so this stays a pure formatter and
    opens nothing itself. Returns the number of events written.
    """
    count = 0
    for event in events:
        fp.write(to_jsonl_line(event))
        fp.write("\n")
        count += 1
    return count


def read_jsonl(fp: IO[str]) -> list[AuditEvent]:
    """Read all :class:`AuditEvent` from a text file-like object."""
    return list(iter_jsonl(fp.read()))
