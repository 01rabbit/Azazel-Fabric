"""Static authority-boundary validation for deception contracts.

These checks are intentionally generic so consumers can validate mappings at
an API boundary before constructing specific Pydantic models.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

BANNED_RUNTIME_DIRECTIVE_FIELDS = frozenset(
    {
        "docker_command",
        "podman_command",
        "shell_command",
        "runtime_command",
        "firewall_rule",
        "nft_rule",
        "iptables_rule",
        "execute_now",
        "must_execute",
        "override_authority",
        "bypass_arbiter",
    }
)


def contains_runtime_directive(value: Any) -> bool:
    """Return True when a nested value contains a runtime-directive field."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in BANNED_RUNTIME_DIRECTIVE_FIELDS:
                return True
            if contains_runtime_directive(nested):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(contains_runtime_directive(item) for item in value)
    return False


def assert_no_runtime_directives(value: Any) -> None:
    """Raise ValueError if a nested contract payload carries execution fields."""

    if contains_runtime_directive(value):
        raise ValueError(
            "deception contract authority invariant violated: runtime/directive "
            "fields are not permitted in Fabric payloads"
        )
