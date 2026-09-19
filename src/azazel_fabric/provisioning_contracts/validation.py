"""Static authority-boundary validation for provisioning contracts.

These checks are deliberately generic so a consumer can validate a raw mapping
at an ingest boundary *before* constructing a Pydantic model. They are pure
functions: no clock, no filesystem, no network, no randomness.

Three separate bans are enforced, because they protect three different things:

1. :func:`assert_no_provisioning_directives` — a descriptive provisioning object
   may not carry a **command, unit, route, firewall, device-path, executor,
   boolean-authorization, or trust-decision** field. Those are the shapes that
   would turn "here is what this host looks like" into "here is what to run",
   which is the exact failure the program plan's AR-01 finding names.
2. :func:`assert_no_resource_tier_claim` — an admission-dimension record may not
   carry a **tier, capability state, or authority level**. Effective capability
   is the intersection of resource n topology n verified assets n trust/health;
   no single record may imply it, and no unratified threshold table may be
   baked into a contract.
3. :func:`assert_no_role_inference` — an interface role may not be **inferred**
   from a kernel name, a link state, or a default route. A role comes from
   read-only inventory plus an explicit operator confirmation against a
   composite identity, and zero or multiple matches fail closed
   (:func:`resolve_interface_assignment`).

``bus_path`` is deliberately **not** treated as a device path: the program plan
mandates it as a component of the composite interface identity, and a PCI/USB
topology address is not an actionable device node.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Key normalization
# --------------------------------------------------------------------------
# A ban that only matched exact snake_case names would be trivially evaded by
# `deviceNode`, `device-node`, or `Device Node`. Normalize first, then match.


def normalized_key(raw: str) -> str:
    """Return a snake_case form of ``raw`` (splits camelCase, folds separators)."""

    parts: list[str] = []
    previous_is_lower_or_digit = False
    for char in raw.strip():
        if char.isupper() and previous_is_lower_or_digit:
            parts.append("_")
        parts.append(char.lower() if char.isalnum() else "_")
        previous_is_lower_or_digit = char.islower() or char.isdigit()
    normalized = "".join(parts)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


# --------------------------------------------------------------------------
# 1. Runtime-directive / authority ban
# --------------------------------------------------------------------------

_COMMAND_FIELDS = frozenset(
    {
        "command", "commands", "cmd", "argv", "args", "shell", "shell_command",
        "runtime_command", "docker_command", "podman_command", "entrypoint",
        "exec", "execute", "execute_now", "must_execute", "script",
    }
)
_UNIT_FIELDS = frozenset(
    {
        "unit", "units", "unit_file", "unit_name", "systemd_unit", "service_unit",
        "service_file", "timer_unit", "socket_unit", "target_unit", "drop_in",
    }
)
_ROUTE_FIELDS = frozenset(
    {
        "route", "routes", "default_route", "ip_route", "static_route", "gateway",
        "default_gateway", "next_hop", "nexthop", "routing_table",
    }
)
_FIREWALL_FIELDS = frozenset(
    {
        "firewall_rule", "firewall_rules", "nft_rule", "nftables_rule",
        "iptables_rule", "ruleset", "nft_ruleset", "chain_rule",
    }
)
_DEVICE_PATH_FIELDS = frozenset(
    {
        "device_path", "device_node", "dev_node", "devnode", "block_device",
        "char_device", "device_file", "disk_path", "mount_point", "mount_path",
    }
)
_EXECUTOR_FIELDS = frozenset(
    {
        "executor", "executors", "executor_ref", "runner", "invoke", "invocation",
        "callable", "subprocess", "process_spec", "handler",
    }
)
_AUTHORIZATION_FIELDS = frozenset(
    {
        "authorized", "authorised", "authorization", "authorisation", "authorize",
        "approved", "approval", "permitted", "permission", "permissions",
        "granted", "grant", "allow", "allowed", "allow_activation", "activate",
        "activate_now", "may_activate", "can_activate", "override",
        "override_authority", "bypass_arbiter", "auto_execute",
    }
)
_TRUST_DECISION_FIELDS = frozenset(
    {
        "trusted", "is_trusted", "trust", "trust_decision", "trust_verdict",
        "trust_level", "verdict", "verified", "is_verified", "verification_result",
        "signature_valid", "signature_verified", "admitted", "admission_decision",
        "admission_result", "accepted", "rejected", "valid", "is_valid",
    }
)

BANNED_PROVISIONING_FIELDS = frozenset(
    _COMMAND_FIELDS
    | _UNIT_FIELDS
    | _ROUTE_FIELDS
    | _FIREWALL_FIELDS
    | _DEVICE_PATH_FIELDS
    | _EXECUTOR_FIELDS
    | _AUTHORIZATION_FIELDS
    | _TRUST_DECISION_FIELDS
)

# Suffix/prefix patterns so a prefixed variant (`nexus_shell_command`,
# `edge_firewall_rule`) cannot slip past the exact-name set.
_BANNED_SUFFIXES = (
    "_command", "_cmd", "_script", "_argv", "_entrypoint",
    "_unit", "_unit_file",
    "_route", "_gateway", "_nexthop",
    "_rule", "_rules", "_ruleset",
    "_device_path", "_device_node", "_dev_node", "_mount_point",
    "_executor",
    "_authorized", "_approved", "_granted", "_permitted",
    "_trusted", "_verified", "_verdict",
)
_BANNED_PREFIXES = ("command_", "exec_", "run_", "systemd_", "nft_", "iptables_")


def _is_banned_provisioning_key(raw: str) -> bool:
    key = normalized_key(raw)
    if key in BANNED_PROVISIONING_FIELDS:
        return True
    if any(key.endswith(suffix) for suffix in _BANNED_SUFFIXES):
        return True
    return any(key.startswith(prefix) for prefix in _BANNED_PREFIXES)


# --------------------------------------------------------------------------
# 2. Tier / capability-state / authority-level ban
# --------------------------------------------------------------------------
# The program plan's RAM-tier selector (a nominal 16 GB host measures 16095 MiB
# usable and therefore selects `core`, not `lite`) is an OPEN program decision.
# A ResourceProfile records the measured envelope; the threshold table that turns
# MiB into a tier stays product-local and unratified, so no contract may carry
# the tier it produced. `CAPABILITY_STATES` (CORE/LITE/FULL) are capability
# states, never authority levels, and are computed from the intersection of all
# admission dimensions -- never from one record.

BANNED_TIER_CLAIM_FIELDS = frozenset(
    {
        "tier", "tiers", "resource_tier", "profile_tier", "capability_tier",
        "deployment_tier", "ram_tier", "memory_tier", "selected_tier",
        "selected_profile", "capability_state", "capability_states",
        "capability_level", "effective_capability", "effective_capabilities",
        "authority_level", "privilege_level", "admission_tier",
    }
)
_BANNED_TIER_SUFFIXES = ("_tier", "_capability_state", "_capability_level", "_authority_level")
_BANNED_TIER_PREFIXES = ("tier_", "effective_capability")


def _is_banned_tier_key(raw: str) -> bool:
    key = normalized_key(raw)
    if key in BANNED_TIER_CLAIM_FIELDS:
        return True
    if any(key.endswith(suffix) for suffix in _BANNED_TIER_SUFFIXES):
        return True
    return any(key.startswith(prefix) for prefix in _BANNED_TIER_PREFIXES)


# --------------------------------------------------------------------------
# 3. Role-inference ban
# --------------------------------------------------------------------------

BANNED_ROLE_INFERENCE_FIELDS = frozenset(
    {
        "inferred_role", "role_inferred", "inferred_from", "inferred_from_name",
        "name_based_role", "guessed_role", "heuristic_role", "autodetected_role",
        "auto_assigned_role", "auto_assigned", "link_state", "link_state_role",
        "carrier", "carrier_state", "operstate", "has_default_route",
        "is_default_route", "default_route_role", "detected_role",
    }
)
_BANNED_INFERENCE_PREFIXES = ("inferred_", "guessed_", "heuristic_", "autodetect", "auto_assign")
_BANNED_INFERENCE_SUFFIXES = ("_inferred", "_guessed", "_autodetected", "_auto_assigned")


def _is_banned_inference_key(raw: str) -> bool:
    key = normalized_key(raw)
    if key in BANNED_ROLE_INFERENCE_FIELDS:
        return True
    if any(key.startswith(prefix) for prefix in _BANNED_INFERENCE_PREFIXES):
        return True
    return any(key.endswith(suffix) for suffix in _BANNED_INFERENCE_SUFFIXES)


# --------------------------------------------------------------------------
# Recursive, bounded walker
# --------------------------------------------------------------------------

_MAX_DEPTH = 8
_MAX_MAP_ITEMS = 128
_MAX_SEQUENCE_ITEMS = 512
_MAX_STRING = 4096
_MAX_KEY = 128


def _walk(value: Any, predicate: Any, message: str, *, path: tuple[str, ...] = (), depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        raise ValueError("provisioning payload exceeds maximum nesting depth")
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            raise ValueError("provisioning payload contains oversized string")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAP_ITEMS:
            raise ValueError("provisioning payload map exceeds maximum item count")
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("provisioning payload map keys must be strings")
            if len(raw_key) > _MAX_KEY:
                raise ValueError("provisioning payload contains oversized key")
            if predicate(raw_key):
                location = ".".join((*path, raw_key))
                raise ValueError(f"{message}: {location}")
            _walk(child, predicate, message, path=(*path, raw_key), depth=depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if len(value) > _MAX_SEQUENCE_ITEMS:
            raise ValueError("provisioning payload sequence exceeds maximum item count")
        for index, child in enumerate(value):
            _walk(child, predicate, message, path=(*path, str(index)), depth=depth + 1)
        return
    raise ValueError(f"unsupported provisioning payload type: {type(value).__name__}")


def _as_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _contains_banned_key(value: Any, predicate: Any) -> bool:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if isinstance(raw_key, str) and predicate(raw_key):
                return True
            if _contains_banned_key(child, predicate):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_banned_key(item, predicate) for item in value)
    return False


def contains_provisioning_directive(value: Any) -> bool:
    """Return True when a nested payload carries a directive/authority field.

    A pure predicate: unlike :func:`assert_no_provisioning_directives` it does
    not also enforce the payload bounds, so an oversized-but-clean payload
    answers False here and still fails the assertion.
    """

    return _contains_banned_key(_as_payload(value), _is_banned_provisioning_key)


def assert_no_provisioning_directives(value: Any) -> None:
    """Fail closed on command/unit/route/firewall/device-path/executor/
    authorization/trust-decision fields anywhere in a provisioning payload."""

    _walk(
        _as_payload(value),
        _is_banned_provisioning_key,
        "provisioning authority invariant violated: command/unit/route/firewall/"
        "device-path/executor/authorization/trust-decision field is forbidden",
    )


def assert_no_resource_tier_claim(value: Any) -> None:
    """Fail closed on a tier, capability-state, or authority-level field.

    A resource or topology record states what was measured. Turning that into a
    tier requires thresholds that are a product-local, currently unratified
    decision, and turning it into a capability requires every other admission
    dimension as well.
    """

    _walk(
        _as_payload(value),
        _is_banned_tier_key,
        "admission-dimension invariant violated: a tier / capability state / "
        "authority level may not be recorded on a single descriptive record",
    )


def assert_no_role_inference(value: Any) -> None:
    """Fail closed on a field that would derive an interface role from a name,
    a link state, or a default route."""

    _walk(
        _as_payload(value),
        _is_banned_inference_key,
        "interface-role invariant violated: a role may not be inferred from a "
        "name, link state, or default route",
    )


# --------------------------------------------------------------------------
# Composite interface identity matching (fail-closed)
# --------------------------------------------------------------------------

# The plan's composite identity. `kernel_name_observed` is deliberately absent:
# a kernel interface name is unstable across reboots and driver reloads and is
# exactly the inference source the plan forbids (AR-12).
COMPOSITE_IDENTITY_FIELDS: tuple[str, ...] = (
    "bus_path",
    "permanent_mac",
    "pci_id",
    "usb_vid_pid",
    "serial",
    "driver",
    "firmware_version",
    "wireless_phy",
    "physical_label",
)

# MAC-only matching is insufficient (AR-12): a selector must pin the topology
# address and at least one hardware-specific discriminator as well.
_REQUIRED_SELECTOR_FIELDS: tuple[str, ...] = ("bus_path", "permanent_mac")
_DISCRIMINATOR_FIELDS: tuple[str, ...] = ("pci_id", "usb_vid_pid", "serial")


class InterfaceResolutionError(ValueError):
    """Zero or multiple interfaces matched a selector — fail closed."""


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def interface_composite_key(value: Any) -> tuple[Any, ...]:
    """Return the composite identity tuple used for matching.

    Ignores every observed-but-unstable attribute (notably the kernel interface
    name), so a rename can never change which physical interface a commissioned
    assignment refers to.
    """

    return tuple(_field(value, name) for name in COMPOSITE_IDENTITY_FIELDS)


def assert_selector_is_composite(selector: Any) -> None:
    """Fail closed on a selector that is not a composite identity."""

    for name in _REQUIRED_SELECTOR_FIELDS:
        if not _field(selector, name):
            raise InterfaceResolutionError(
                f"interface selector must pin {name}; MAC-only matching is insufficient"
            )
    if not any(_field(selector, name) for name in _DISCRIMINATOR_FIELDS):
        raise InterfaceResolutionError(
            "interface selector must pin at least one of "
            f"{list(_DISCRIMINATOR_FIELDS)}; MAC-only matching is insufficient"
        )


def matching_interfaces(interfaces: Iterable[Any], selector: Any) -> tuple[Any, ...]:
    """Return every inventory interface every specified selector field matches."""

    assert_selector_is_composite(selector)
    matches = []
    for interface in interfaces:
        for name in COMPOSITE_IDENTITY_FIELDS:
            wanted = _field(selector, name)
            if wanted is None:
                continue
            if _field(interface, name) != wanted:
                break
        else:
            matches.append(interface)
    return tuple(matches)


def resolve_interface_assignment(inventory: Any, assignment: Any) -> Any:
    """Return the one inventory interface an assignment refers to, or fail closed.

    Zero matches and multiple matches are both errors: the plan requires an
    ambiguous or absent interface identity to stop commissioning rather than
    pick one. The inventory is read-only input; nothing is mutated.
    """

    interfaces = _field(inventory, "interfaces") or ()
    selector = _field(assignment, "selector")
    if selector is None:
        raise InterfaceResolutionError("assignment carries no interface selector")
    matches = matching_interfaces(interfaces, selector)
    if len(matches) == 0:
        raise InterfaceResolutionError(
            "no inventory interface matches the assignment selector (fail closed)"
        )
    if len(matches) > 1:
        raise InterfaceResolutionError(
            f"{len(matches)} inventory interfaces match the assignment selector; "
            "an ambiguous composite identity fails closed"
        )
    return matches[0]


# --------------------------------------------------------------------------
# Expiry (explicit reference time — Fabric never reads a clock)
# --------------------------------------------------------------------------


def assert_not_expired(value: Any, *, as_of: datetime, field: str = "expires_at") -> None:
    """Fail closed when ``value[field]`` is at or before ``as_of``.

    ``as_of`` is required and explicit: Fabric holds no wall clock, so the
    caller supplies the reference time and the result is deterministic and
    replayable.
    """

    raw = _field(value, field)
    if raw is None:
        raise ValueError(f"record carries no {field}; expiry cannot be evaluated")
    expires_at = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if expires_at <= as_of:
        raise ValueError(f"record expired at {expires_at.isoformat()} (as_of {as_of.isoformat()})")


__all__ = [
    "BANNED_PROVISIONING_FIELDS",
    "BANNED_ROLE_INFERENCE_FIELDS",
    "BANNED_TIER_CLAIM_FIELDS",
    "COMPOSITE_IDENTITY_FIELDS",
    "InterfaceResolutionError",
    "assert_no_provisioning_directives",
    "assert_no_resource_tier_claim",
    "assert_no_role_inference",
    "assert_not_expired",
    "assert_selector_is_composite",
    "contains_provisioning_directive",
    "interface_composite_key",
    "matching_interfaces",
    "normalized_key",
    "resolve_interface_assignment",
]
