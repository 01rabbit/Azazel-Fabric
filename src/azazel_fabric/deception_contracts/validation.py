"""Static authority-boundary validation for deception contracts.

These checks are intentionally generic so consumers can validate mappings at
an API boundary before constructing specific Pydantic models.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

#: How deep the assertions below look before refusing a payload outright.
#: Without a bound a deep enough payload raised ``RecursionError`` -- a refusal,
#: but not the ``ValueError`` a caller catches -- so the walk is bounded, as the
#: provisioning, M.I.O., outcome and external-security walkers already are. The
#: value is far above the deepest record any contract model dumps, and below
#: the 64 levels at which an unbounded walker is distinguishable in the tests.
MAX_DIRECTIVE_WALK_DEPTH = 32


def _find_banned_key(value: Any, banned: frozenset[str], *, depth: int = 0) -> bool:
    """Bounded walk shared by the assertions. A payload too deep is refused."""

    if depth > MAX_DIRECTIVE_WALK_DEPTH:
        raise ValueError(
            "deception payload exceeds maximum nesting depth "
            f"{MAX_DIRECTIVE_WALK_DEPTH}; it is refused rather than inspected"
        )
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in banned:
                return True
            if _find_banned_key(nested, banned, depth=depth + 1):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_find_banned_key(item, banned, depth=depth + 1) for item in value)
    return False

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
    """Raise ValueError if a nested contract payload carries execution fields.

    Also raises ``ValueError`` for a payload nested deeper than
    :data:`MAX_DIRECTIVE_WALK_DEPTH`, whether or not it carries a directive.
    """

    if _find_banned_key(value, BANNED_RUNTIME_DIRECTIVE_FIELDS):
        raise ValueError(
            "deception contract authority invariant violated: runtime/directive "
            "fields are not permitted in Fabric payloads"
        )


# Effectiveness-observation honesty invariant: a fact-only observation emitted by
# the Deception Host must never assert attacker belief, deception success, or an
# effectiveness verdict. That is a layer-4 inference and belongs to Knowledge's
# advisory output, not to the observed fact (Azazel-Deception#6,
# Azazel-Knowledge#58: "do not claim that interaction proves attacker belief").
# ``confidence`` is banned here too: an observation is a fact, not a scored
# estimate — confidence lives on ``EffectivenessAdvisory``, not on an observation.
BANNED_EFFECTIVENESS_VERDICT_FIELDS = frozenset(
    {
        "attacker_believed",
        "believed",
        "belief",
        "belief_score",
        "deceived",
        "fooled",
        "convinced",
        "is_effective",
        "effective",
        "effectiveness_score",
        "success_score",
        "confidence",
    }
)


def contains_effectiveness_verdict(value: Any) -> bool:
    """Return True when a nested value contains a belief/effectiveness field."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in BANNED_EFFECTIVENESS_VERDICT_FIELDS:
                return True
            if contains_effectiveness_verdict(nested):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(contains_effectiveness_verdict(item) for item in value)
    return False


def assert_no_effectiveness_verdict(value: Any) -> None:
    """Raise ValueError if a fact-only observation payload asserts belief/verdict.

    Apply this to interaction-observation payloads at the API boundary before
    constructing :class:`InteractionObservation`. It does not apply to
    :class:`EffectivenessAdvisory`, whose ``confidence`` is a legitimate,
    named layer-4 field.

    Also raises ``ValueError`` for a payload nested deeper than
    :data:`MAX_DIRECTIVE_WALK_DEPTH`.
    """

    if _find_banned_key(value, BANNED_EFFECTIVENESS_VERDICT_FIELDS):
        raise ValueError(
            "effectiveness observation honesty invariant violated: belief/"
            "deception-success/effectiveness-verdict fields are not permitted on "
            "a fact-only observation (interaction does not prove attacker belief)"
        )
