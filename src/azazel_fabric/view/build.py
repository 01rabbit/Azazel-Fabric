"""Shared derivation of `StatusView`.

`build_status_view` is the one function Edge and Gadget both call to turn their
state into the shared view-model — this is the "shared mechanism, not just a
shared shape" that gives Common its value. Posture classification and the
default headline live here so both products classify and phrase status
identically instead of each re-implementing it.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from azazel_fabric.schema.action import ActionIntent
from azazel_fabric.schema.mode import ModeState
from azazel_fabric.schema.state import StateSnapshot
from azazel_fabric.view.status import HealthDimension, StatusView

# Maps a raw state/stage/mode word (lower-cased) to a shared posture. Both Edge
# (NORMAL/DEGRADED/CONTAIN/DECEPTION) and Gadget (same FSM stages) feed this, so
# the classification is identical across products.
_POSTURE_BY_WORD = {
    "normal": "normal",
    "ok": "normal",
    "degraded": "degraded",
    "degrade": "degraded",
    "contain": "contain",
    "containment": "contain",
    "deception": "deception",
    "decoy": "deception",
    "scapegoat": "deception",
    "lockdown": "lockdown",
}


def derive_posture(state_word: str | None, mode_name: str | None = None) -> str:
    """Classify an overall posture from a raw state word (falling back to mode).

    Returns ``"unknown"`` when nothing matches — an unknown posture is a normal,
    expected value, never an error.
    """
    for candidate in (state_word, mode_name):
        if candidate:
            hit = _POSTURE_BY_WORD.get(str(candidate).strip().lower())
            if hit:
                return hit
    return "unknown"


def derive_headline(product: str, mode: ModeState, posture: str) -> str:
    """A minimal, render-agnostic one-line status. Products may override it.

    This is a neutral default, not product copy — each renderer is free to pass
    its own ``headline`` instead.
    """
    return f"{product} · {mode.name} · {posture}"


def build_status_view(
    *,
    product: str,
    mode: ModeState,
    generated_at: str,
    schema_version: str = "1.0",
    trace_id: str | None = None,
    posture: str | None = None,
    state_word: str | None = None,
    headline: str | None = None,
    reasons: Iterable[str] = (),
    operator_wording: str | None = None,
    current_action: ActionIntent | None = None,
    next_actions: Iterable[str] = (),
    health: Iterable[HealthDimension] = (),
    evidence_ids: Iterable[str] = (),
    product_view: Mapping[str, Any] | None = None,
) -> StatusView:
    """Build a `StatusView` the same way for every product.

    ``posture`` is derived from ``state_word``/``mode`` when not given;
    ``headline`` is derived from product/mode/posture when not given. Everything
    a product cannot express in the shared fields belongs in ``product_view`` so
    nothing is lost.
    """
    resolved_posture = posture or derive_posture(state_word, mode.name)
    resolved_headline = (
        headline if headline is not None else derive_headline(product, mode, resolved_posture)
    )
    return StatusView(
        schema_version=schema_version,
        product=product,
        generated_at=generated_at,
        trace_id=trace_id,
        mode=mode,
        posture=resolved_posture,
        headline=resolved_headline,
        reasons=list(reasons),
        operator_wording=operator_wording,
        current_action=current_action,
        next_actions=list(next_actions),
        health=list(health),
        evidence_ids=list(evidence_ids),
        product_view=dict(product_view or {}),
    )


def from_state_snapshot(
    snapshot: StateSnapshot,
    *,
    state_word: str | None = None,
    posture: str | None = None,
    headline: str | None = None,
    reasons: Iterable[str] = (),
    operator_wording: str | None = None,
    current_action: ActionIntent | None = None,
    next_actions: Iterable[str] = (),
    health: Iterable[HealthDimension] = (),
    evidence_ids: Iterable[str] = (),
    product_view: Mapping[str, Any] | None = None,
) -> StatusView:
    """Build a `StatusView` from a `StateSnapshot`, carrying its `summary`.

    The snapshot's `product`/`mode`/`generated_at`/`trace_id`/`schema_version`
    seed the view; its loosely-typed `summary` is carried into `product_view`
    (an explicit `product_view` argument, if given, takes precedence). This is
    the one-call path for a product that already builds a `StateSnapshot`.
    """
    carried = dict(snapshot.summary)
    if product_view:
        carried.update(product_view)
    return build_status_view(
        product=snapshot.product,
        mode=snapshot.mode,
        generated_at=snapshot.generated_at,
        schema_version=snapshot.schema_version,
        trace_id=snapshot.trace_id,
        posture=posture,
        state_word=state_word,
        headline=headline,
        reasons=reasons,
        operator_wording=operator_wording,
        current_action=current_action,
        next_actions=next_actions,
        health=health,
        evidence_ids=evidence_ids,
        product_view=carried,
    )
