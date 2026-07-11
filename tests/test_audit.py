"""Tests for `azazel_fabric.audit` — AuditEvent projection + JSONL formatters.

Load-bearing properties: round-trip through a JSONL line, stable/deterministic
serialization, projection builder produces a valid AuditEvent, and the module
ships no chain/verification API (owner decision).
"""

import io

import azazel_fabric.audit as audit_pkg
from azazel_fabric.audit import (
    from_jsonl_line,
    iter_jsonl,
    make_event_id,
    project_audit_event,
    read_jsonl,
    to_jsonl_line,
    write_jsonl,
)
from azazel_fabric.schema import AuditEvent


def _event(**over):
    data = dict(
        event_id="e-1",
        trace_id="trace-1",
        timestamp="2026-07-10T00:00:00Z",
        product="edge",
        event_type="decision.recorded",
        payload={"action": "isolate"},
        config_hash="cfg-1",
    )
    data.update(over)
    return AuditEvent(**data)


def test_make_event_id_convention_and_determinism():
    a = make_event_id("edge", "decision.recorded", "2026-07-10T00:00:00Z")
    assert a == "edge:decision.recorded:2026-07-10T00:00:00Z"
    # deterministic
    assert a == make_event_id("edge", "decision.recorded", "2026-07-10T00:00:00Z")
    # optional suffix
    withsuffix = make_event_id("edge", "x", "t", suffix="7")
    assert withsuffix == "edge:x:t:7"


def test_project_audit_event_builds_valid_event():
    ev = project_audit_event(
        product="edge",
        event_type="decision.recorded",
        timestamp="2026-07-10T00:00:00Z",
        trace_id="trace-1",
        payload={"action": "isolate"},
    )
    assert isinstance(ev, AuditEvent)
    assert ev.event_id == "edge:decision.recorded:2026-07-10T00:00:00Z"
    assert ev.payload == {"action": "isolate"}
    # passthrough of integrity fields — not computed here
    assert ev.config_hash is None
    assert ev.hmac is None


def test_project_audit_event_passes_through_integrity_fields():
    ev = project_audit_event(
        product="edge",
        event_type="x",
        timestamp="t",
        trace_id="tr",
        config_hash="cfg",
        hmac="sig",
        event_id="custom-id",
    )
    assert ev.event_id == "custom-id"
    assert ev.config_hash == "cfg"
    assert ev.hmac == "sig"


def test_jsonl_line_round_trip():
    ev = _event()
    line = to_jsonl_line(ev)
    assert "\n" not in line
    assert from_jsonl_line(line) == ev


def test_jsonl_serialization_is_stable():
    # Sorted keys + compact separators => byte-identical for equal events.
    assert to_jsonl_line(_event()) == to_jsonl_line(_event())


def test_write_and_read_jsonl_stream():
    events = [_event(event_id="e-1"), _event(event_id="e-2")]
    buf = io.StringIO()
    n = write_jsonl(events, buf)
    assert n == 2
    text = buf.getvalue()
    assert text.count("\n") == 2
    assert read_jsonl(io.StringIO(text)) == events


def test_iter_jsonl_skips_blank_lines():
    line = to_jsonl_line(_event())
    text = f"{line}\n\n{line}\n"
    assert len(list(iter_jsonl(text))) == 2


def test_audit_ships_no_chain_or_verification_api():
    # Owner decision: no hash chain, no chain verification in Fabric.
    exported = set(audit_pkg.__all__)
    for banned in ("chain", "verify", "verify_chain", "hash_chain", "link"):
        assert not any(banned in name for name in exported), (
            f"unexpected chain-like export {banned!r} in azazel_fabric.audit"
        )
