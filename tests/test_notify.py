"""Tests for `azazel_fabric.notify` — payload model and transport mappers.

Load-bearing properties: the model matches contracts.md §4, severity is a closed
set, and the transport mappers are pure (build a payload, never send).
"""

import pytest
from pydantic import ValidationError

from azazel_fabric.notify import (
    SEVERITIES,
    NotificationEvent,
    to_mattermost_payload,
    to_ntfy_payload,
)


def _event(**over):
    data = dict(
        event_id="n-1",
        product="edge",
        severity="warning",
        title="Containment engaged",
        body="Host 10.0.0.5 isolated.",
        trace_id="trace-1",
        created_at="2026-07-10T00:00:00Z",
    )
    data.update(over)
    return NotificationEvent(**data)


def test_notification_event_round_trip():
    ev = _event()
    assert NotificationEvent.model_validate_json(ev.model_dump_json()) == ev


def test_severity_is_closed_set():
    assert SEVERITIES == ("info", "warning", "critical")
    for sev in SEVERITIES:
        assert _event(severity=sev).severity == sev
    with pytest.raises(ValidationError):
        _event(severity="fatal")


def test_notification_event_forbids_extra_fields():
    with pytest.raises(ValidationError):
        _event(directive="do this")


def test_optional_trace_id():
    ev = _event(trace_id=None)
    assert ev.trace_id is None


def test_to_ntfy_payload_maps_fields_and_priority():
    payload = to_ntfy_payload(_event(severity="critical"))
    assert payload["title"] == "Containment engaged"
    assert payload["message"] == "Host 10.0.0.5 isolated."
    assert payload["priority"] == 5  # critical -> max
    assert "edge" in payload["tags"]
    assert "critical" in payload["tags"]
    assert "trace:trace-1" in payload["tags"]


def test_to_ntfy_priority_scales_with_severity():
    assert to_ntfy_payload(_event(severity="info"))["priority"] == 3
    assert to_ntfy_payload(_event(severity="warning"))["priority"] == 4
    assert to_ntfy_payload(_event(severity="critical"))["priority"] == 5


def test_to_mattermost_payload_conveys_severity_in_text():
    payload = to_mattermost_payload(_event(severity="warning"))
    assert "WARNING" in payload["text"]
    assert "Containment engaged" in payload["text"]
    assert payload["props"]["product"] == "edge"
    assert payload["props"]["severity"] == "warning"
    assert payload["props"]["event_id"] == "n-1"


def test_transport_mappers_are_pure_no_network_import():
    import sys

    to_ntfy_payload(_event())
    to_mattermost_payload(_event())
    # no HTTP client dragged in by importing/using the mappers
    for mod in ("requests", "httpx", "urllib3"):
        assert mod not in sys.modules
