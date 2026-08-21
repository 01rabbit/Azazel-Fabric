"""Static authority-boundary validation for engagement contracts.

Generic checks consumers can run at an API boundary before constructing the
Pydantic models. They enforce the authority rule structurally: an engagement
candidate is a request, an advisory is context, and neither may smuggle an
executable/runtime directive or an authority-bearing field.
"""

from __future__ import annotations

from typing import Any

# Reuse the canonical runtime-directive ban from the deception family so the two
# contract families share one definition of "this is an execution command".
from azazel_fabric.deception_contracts.validation import (
    BANNED_RUNTIME_DIRECTIVE_FIELDS,
    contains_runtime_directive,
)

# Engagement-specific authority-bearing fields that must never appear in a
# candidate or advisory: they would let a describe-only payload pre-authorize or
# self-execute an action, bypassing the product arbiter.
BANNED_ENGAGEMENT_AUTHORITY_FIELDS = frozenset(
    BANNED_RUNTIME_DIRECTIVE_FIELDS
    | {
        "auto_execute",
        "select_action",
        "selected_action",
        "force_action",
        "arbiter_override",
        "decision",
        "authorized",
        "deadline",
    }
)


def _contains_banned(value: Any) -> bool:
    from collections.abc import Mapping, Sequence

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in BANNED_ENGAGEMENT_AUTHORITY_FIELDS:
                return True
            if _contains_banned(nested):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_banned(item) for item in value)
    return False


def assert_no_engagement_directives(value: Any) -> None:
    """Raise ``ValueError`` if a payload carries an execution/authority field.

    Covers both the canonical runtime-directive set and the engagement-specific
    authority-bearing fields. Use at an ingest/forwarding boundary before trust.
    """

    if _contains_banned(value):
        raise ValueError(
            "engagement contract authority invariant violated: runtime/directive "
            "or authority-bearing fields are not permitted in Fabric payloads"
        )


def assert_candidate_not_executable(candidate: Any) -> None:
    """Reject a candidate that claims authority or carries a directive.

    ``candidate.authority`` must be ``"candidate_only"`` (a candidate is a
    request, never a command), and no directive/authority field may appear.
    Accepts either a Pydantic model or a raw mapping.
    """

    authority = _get(candidate, "authority")
    if authority not in (None, "candidate_only"):
        raise ValueError(
            f"engagement candidate claims non-candidate authority: {authority!r}"
        )
    assert_no_engagement_directives(_as_mapping(candidate))


def assert_engagement_advisory_only(advisory: Any) -> None:
    """Reject an advisory that claims authority, is executable, or is a directive.

    ``authority`` must be ``"advisory_only"`` and ``executable`` must be falsey.
    Accepts either a Pydantic model or a raw mapping.
    """

    authority = _get(advisory, "authority")
    if authority not in (None, "advisory_only"):
        raise ValueError(
            f"engagement advisory claims non-advisory authority: {authority!r}"
        )
    if _get(advisory, "executable") not in (None, False):
        raise ValueError("engagement advisory claims to be executable")
    assert_no_engagement_directives(_as_mapping(advisory))


def _get(obj: Any, name: str) -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name)
    return None


def _as_mapping(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


__all__ = [
    "BANNED_ENGAGEMENT_AUTHORITY_FIELDS",
    "assert_no_engagement_directives",
    "assert_candidate_not_executable",
    "assert_engagement_advisory_only",
    "contains_runtime_directive",
]
