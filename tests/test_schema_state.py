"""Tests for StateSnapshot / ModeState construction and round-trip."""

from azazel_fabric.schema import ModeState, StateSnapshot


def _snapshot() -> StateSnapshot:
    return StateSnapshot(
        schema_version="1.0",
        product="edge",
        mode=ModeState(name="shield", since="2026-07-09T00:00:00Z", reason="test"),
        generated_at="2026-07-09T00:00:01Z",
        trace_id="trace-1",
        summary={"connections": 3},
    )


def test_state_snapshot_constructs():
    snap = _snapshot()
    assert snap.product == "edge"
    assert snap.mode.name == "shield"
    assert snap.summary["connections"] == 3


def test_state_snapshot_round_trip():
    snap = _snapshot()
    restored = StateSnapshot.model_validate(snap.model_dump())
    assert restored == snap
    assert StateSnapshot.model_validate_json(snap.model_dump_json()) == snap


def test_mode_name_is_open_enum():
    # A product-specific mode value not in KNOWN_MODE_NAMES is still valid.
    mode = ModeState(name="gadget_only_mode", since="2026-07-09T00:00:00Z")
    assert mode.name == "gadget_only_mode"
    assert mode.reason is None


def test_product_is_open_enum():
    # A future product ("boot") is accepted; product is not a closed set.
    snap = _snapshot()
    future = snap.model_copy(update={"product": "boot"})
    assert future.product == "boot"
