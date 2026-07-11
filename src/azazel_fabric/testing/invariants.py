"""Reusable invariant assertions for consumer contract tests.

Plain functions — **no pytest dependency**. They raise ``AssertionError`` on
violation (usable from pytest, unittest, or a bare script) and return ``None``
on success. The load-bearing one is :func:`assert_advisory_only` — the safety
invariant that keeps the Knowledge Plane advisory-only (design-principles §4.2).
"""

from __future__ import annotations

from typing import Any, Mapping

from azazel_fabric.cti_contracts.advisory import BANNED_DIRECTIVE_FIELDS
from azazel_fabric.cti_contracts.context import CtiContextResponse


def assert_advisory_only(response: CtiContextResponse | Mapping[str, Any]) -> None:
    """Assert a CTI context response carries no directive-shaped field.

    Accepts a :class:`CtiContextResponse` or a raw mapping (e.g. a decoded wire
    payload). Raises ``AssertionError`` if any banned directive field
    (``directive`` / ``must_execute`` / ``override`` / ``required_action``) is
    present — the invariant that keeps Knowledge advisory, never commanding.
    """
    if isinstance(response, CtiContextResponse):
        data: Mapping[str, Any] = response.model_dump()
    else:
        data = response
    present = [f for f in BANNED_DIRECTIVE_FIELDS if f in data]
    assert not present, (
        "advisory-only invariant violated: directive-shaped field(s) "
        f"{present} present in a CTI context response"
    )


def assert_behavioral_absent_not_null(response: CtiContextResponse) -> None:
    """Assert an absent behavioral signal serializes as a missing key, never null.

    Enforces the "absent, never ``null``, never empty object" rule from
    contracts.md §2 for a response with no behavioral signal. Raises
    ``AssertionError`` if the key is present or a ``null`` appears on the wire.
    """
    assert response.has_behavioral_cti is False, (
        "expected no behavioral signal on this response"
    )
    dumped = response.model_dump()
    assert "behavioral_cti" not in dumped, (
        "behavioral_cti must be omitted (absent), not present, when empty"
    )
    assert "null" not in response.model_dump_json(), (
        "absent behavioral_cti must never serialize as null"
    )
