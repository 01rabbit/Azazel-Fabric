"""Tests for the shared status view-model and its builder.

The load-bearing properties are: both products derive posture/headline the same
way, and Gadget's product-specific fields survive as a superset (never narrowed
to an Edge subset).
"""

import pytest

from azazel_common.schema import ActionIntent, ModeState, StateSnapshot
from azazel_common.view import (
    HealthDimension,
    StatusView,
    build_status_view,
    derive_headline,
    derive_posture,
    from_state_snapshot,
)


def _mode(name="shield"):
    return ModeState(name=name, since="2026-07-09T00:00:00Z")


def test_build_status_view_round_trip():
    view = build_status_view(
        product="edge",
        mode=_mode(),
        generated_at="2026-07-09T00:00:01Z",
        state_word="CONTAIN",
        reasons=["policy match"],
        health=[HealthDimension(key="availability", label="degraded", status="warn")],
        current_action=ActionIntent(
            kind="isolate", target="10.0.0.5", issued_by="edge.arbiter", trace_id="t"
        ),
        evidence_ids=["ev-1"],
        trace_id="trace-1",
    )
    restored = StatusView.model_validate_json(view.model_dump_json())
    assert restored == view
    assert restored.posture == "contain"
    assert restored.current_action.kind == "isolate"


def test_posture_derivation_is_shared_and_identical():
    # Same state words classify identically regardless of product.
    assert derive_posture("NORMAL") == "normal"
    assert derive_posture("DEGRADED") == "degraded"
    assert derive_posture("CONTAIN") == "contain"
    # Gadget-specific words still classify — deception is not Edge-only.
    assert derive_posture("DECEPTION") == "deception"
    assert derive_posture("scapegoat") == "deception"


def test_posture_falls_back_to_mode_then_unknown():
    assert derive_posture(None, "lockdown") == "lockdown"
    # Unknown is a normal, expected value — not an error.
    assert derive_posture("nonsense", "alsononsense") == "unknown"


def test_headline_defaults_but_is_overridable():
    mode = _mode("portal")
    assert derive_headline("gadget", mode, "normal") == "gadget · portal · normal"
    overridden = build_status_view(
        product="gadget",
        mode=mode,
        generated_at="t",
        headline="custom copy",
    )
    assert overridden.headline == "custom copy"


def test_gadget_superset_preserved_via_product_view():
    # Gadget-only fields must survive round-tripping, not be dropped.
    snap = StateSnapshot(
        schema_version="1.0",
        product="gadget",
        mode=ModeState(name="scapegoat", since="t"),
        generated_at="t2",
        trace_id="",
        summary={"attack": {"canary_delay_active": True}, "stage": "DECEPTION"},
    )
    view = from_state_snapshot(snap, state_word="DECEPTION")
    assert view.posture == "deception"
    assert view.product_view["attack"]["canary_delay_active"] is True
    assert view.product_view["stage"] == "DECEPTION"
    # snapshot with empty trace_id maps through; view keeps it optional
    assert view.trace_id == ""


def test_from_state_snapshot_explicit_product_view_takes_precedence():
    snap = StateSnapshot(
        schema_version="1.0",
        product="gadget",
        mode=_mode(),
        generated_at="t",
        trace_id="x",
        summary={"a": 1, "b": 2},
    )
    view = from_state_snapshot(snap, product_view={"b": 99, "c": 3})
    assert view.product_view == {"a": 1, "b": 99, "c": 3}


def test_open_enums_accept_product_specific_values():
    # posture and health status are open str enums.
    view = build_status_view(
        product="boot",
        mode=_mode("some_future_mode"),
        generated_at="t",
        posture="some_future_posture",
        health=[HealthDimension(key="x", label="y", status="some_future_status")],
    )
    assert view.posture == "some_future_posture"
    assert view.health[0].status == "some_future_status"
