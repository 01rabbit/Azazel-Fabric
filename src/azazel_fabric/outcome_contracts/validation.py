"""Validation helpers for Outcome-as-Evidence shared facts."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

_BANNED_KEYS = {
    "execute",
    "execution_command",
    "provider_command",
    "command",
    "commands",
    "approve",
    "approval",
    "override",
    "arbiter_override",
    "auto_execute",
    "select_action",
    "selected_action",
    "model_recommendation",
    "attacker_belief",
    "success",
    "successful",
}

_MAX_DEPTH = 6
_MAX_MAP_ITEMS = 64
_MAX_SEQUENCE_ITEMS = 128
_MAX_STRING = 2048
_MAX_CANONICAL_BYTES = 64 * 1024


def _walk(value: Any, *, path: tuple[str, ...] = (), depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        raise ValueError("fact payload exceeds maximum nesting depth")
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            raise ValueError("fact payload contains oversized string")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAP_ITEMS:
            raise ValueError("fact payload map exceeds maximum item count")
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("fact payload map keys must be strings")
            key = raw_key.strip().lower()
            if key in _BANNED_KEYS:
                location = ".".join((*path, raw_key))
                raise ValueError(f"runtime/authority field is forbidden: {location}")
            if len(raw_key) > 128:
                raise ValueError("fact payload contains oversized key")
            _walk(child, path=(*path, raw_key), depth=depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if len(value) > _MAX_SEQUENCE_ITEMS:
            raise ValueError("fact payload sequence exceeds maximum item count")
        for index, child in enumerate(value):
            _walk(child, path=(*path, str(index)), depth=depth + 1)
        return
    raise ValueError(f"unsupported fact payload type: {type(value).__name__}")


def assert_no_runtime_directives(value: Any) -> None:
    """Reject executable, authority-bearing, or overclaim fields recursively."""

    _walk(value)


def assert_bounded_fact_payload(value: Any) -> None:
    """Enforce bounded JSON-compatible fact payloads."""

    _walk(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > _MAX_CANONICAL_BYTES:
        raise ValueError("fact payload exceeds maximum canonical size")


def canonical_fact_json(value: Any) -> str:
    """Return deterministic JSON after applying the shared fact safety bounds."""

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    assert_no_runtime_directives(value)
    assert_bounded_fact_payload(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def assert_evidence_chain_consistent(
    execution: Any,
    mechanism: Any | None = None,
    outcomes: Sequence[Any] = (),
    assessment: Any | None = None,
) -> None:
    """Reject cross-trace/cross-decision joins without creating authority."""

    expected = (execution.trace_id, execution.decision_ref, execution.execution_ref)
    for item in ([mechanism] if mechanism is not None else []):
        current = (item.trace_id, item.decision_ref, item.execution_ref)
        if current != expected:
            raise ValueError("mechanism does not belong to execution evidence chain")
    for outcome in outcomes:
        current = (outcome.trace_id, outcome.decision_ref, outcome.execution_ref)
        if current != expected:
            raise ValueError("outcome does not belong to execution evidence chain")
        if mechanism is not None and outcome.mechanism_observation_ref not in (
            None,
            mechanism.observation_id,
        ):
            raise ValueError("outcome references a different mechanism observation")
    if assessment is not None:
        current = (assessment.trace_id, assessment.decision_ref, assessment.execution_ref)
        if current != expected:
            raise ValueError("assessment does not belong to execution evidence chain")
        if mechanism is not None and assessment.mechanism_observation_ref != mechanism.observation_id:
            raise ValueError("assessment references a different mechanism observation")
        outcome_ids = {item.observation_id for item in outcomes}
        if not set(assessment.outcome_observation_refs).issubset(outcome_ids):
            raise ValueError("assessment references an outcome outside the supplied evidence chain")
