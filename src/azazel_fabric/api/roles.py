"""Role vocabulary + fail-closed comparison (`contracts.md` §3).

The four series roles, ordered least->most privileged::

    viewer < operator < responder < admin

Comparison is fail-closed: an unknown role never satisfies a requirement, and
never out-ranks a known one. This module encodes the ordering only; *which*
endpoint needs *which* role is product-owned policy, not a Fabric concern.
"""

from __future__ import annotations

# Ordered least -> most privileged (contracts.md §3). Index == privilege rank.
ROLES: tuple[str, ...] = ("viewer", "operator", "responder", "admin")

_RANK: dict[str, int] = {role: i for i, role in enumerate(ROLES)}


def is_known_role(role: str) -> bool:
    """True only for one of the four canonical roles."""
    return role in _RANK


def role_rank(role: str) -> int:
    """Privilege rank of ``role`` (0 = viewer .. 3 = admin).

    Returns ``-1`` for an unknown role so it sorts below every known role —
    the fail-closed default. Callers should treat ``-1`` as "no privilege",
    never as a valid low rank to grant on.
    """
    return _RANK.get(role, -1)


def role_allows(actual: str, required: str) -> bool:
    """True iff ``actual`` is a known role at least as privileged as ``required``.

    Fail-closed on every ambiguity: an unknown ``actual`` role is denied, and an
    unknown ``required`` role denies everything (nobody satisfies a requirement
    the series does not recognize). Never default-allows.
    """
    if actual not in _RANK or required not in _RANK:
        return False
    return _RANK[actual] >= _RANK[required]
