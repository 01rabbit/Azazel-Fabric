"""Static boundary validation for the external-security profile (Fabric#25).

Every record in this family travels between products that do not trust each
other's authority: an external EDR/firewall/DNS/SIEM feed, Knowledge's
advisory output, Deception's exposure proposal, and a device adapter's report.
What these checks guarantee is structural, not semantic:

* no record carries a command, a route/firewall/DNS rule body, an executor, a
  token/credential/credential locator, an authority override, or an execute
  flag -- at any depth, including inside lists and tuples;
* no advisory or proposal carries a concrete target locator (hostname, IP,
  device-specific object id) -- those stay with the owning product's adapter;
* vendor-specific material is confined to a namespaced, digest-bound,
  size/depth/cardinality-limited opaque extension;
* the walk is **bounded**: a payload too deep to inspect is refused with a
  clean ``ValueError`` rather than a ``RecursionError``.

Pure functions only: no clock, no filesystem, no network, no randomness. A
check that needs "now" takes it as an argument.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

# The canonical runtime-directive names, restated rather than imported: this
# family is on the strict R1 boundary gate, which allows a family to import
# only itself. ``tests/test_external_security_contracts.py`` asserts this set
# stays a superset of ``deception_contracts``' runtime-directive names and of
# the M.I.O. canonical set, so the definitions cannot drift apart silently.
_CANONICAL_RUNTIME_DIRECTIVE_FIELDS = frozenset(
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

#: Names refused anywhere in a record of this family, after key normalization
#: (lower-case, every non-alphanumeric run folded to ``_``).
#:
#: Grouped by what each would let a descriptive record do. The pattern checks
#: in :func:`_is_directive_key` widen the exact names (``*_command``,
#: ``*_rule``, any ``token``/``password``/``secret``/``credential`` segment),
#: so this list is the floor, not the whole rule.
BANNED_EXTERNAL_SECURITY_FIELDS = frozenset(
    _CANONICAL_RUNTIME_DIRECTIVE_FIELDS
    | {
        # commands and provider syntax
        "command",
        "commands",
        "cmd",
        "shell",
        "exec",
        "args",
        "argv",
        "entrypoint",
        "invoke",
        "invocation",
        "cli_command",
        "device_command",
        "provider_command",
        "vendor_command",
        "api_call",
        "script",
        "playbook",
        "config_snippet",
        "device_config",
        "running_config",
        # route / firewall / DNS rule bodies
        "route",
        "routes",
        "route_rule",
        "static_route",
        "routing_rule",
        "firewall_rules",
        "acl",
        "acl_rule",
        "policy_body",
        "rule_body",
        "rule_text",
        "dns_rule",
        "dns_record_body",
        "rpz_rule",
        "sinkhole_rule",
        "ruleset",
        "nft_ruleset",
        "nftables_rule",
        "chain_rule",
        "ip_route",
        "next_hop",
        "nexthop",
        "default_route",
        "routing_table",
        # executors and execute flags
        "executor",
        "executor_ref",
        "execute",
        "auto_execute",
        "execute_flag",
        "executable_payload",
        "run_now",
        "apply_now",
        "must_apply",
        # tokens, credentials, credential locators
        "token",
        "access_token",
        "bearer_token",
        "auth_token",
        "api_key",
        "apikey",
        "password",
        "passwd",
        "secret",
        "client_secret",
        "private_key",
        "credential",
        "credentials",
        "credential_locator",
        "credential_path",
        "secret_ref",
        "secret_locator",
        "keychain_ref",
        "vault_path",
        # overrides and authority claims
        "override",
        "authority_override",
        "arbiter_override",
        "force",
        "approve",
        "approved",
        "approval",
        "authorize",
        "authorized",
        "authorization",
        "admit",
        "admitted",
        "decision_valid",
        "valid_decision",
        "decision_status",
        "grant",
        "granted",
        "permitted",
        "trust_decision",
        "signature_valid",
        "signature_verified",
        # success verdicts: coverage replaces them, see TelemetryCoverage
        "success",
        "successful",
        "succeeded",
        "contained",
        "containment_confirmed",
        "tactical_success",
    }
)

#: Concrete target locators. Refused in advisory and proposal records, where a
#: concrete address would turn a description into an instruction an adapter
#: could follow without its owning product's decision. An observation envelope
#: may carry them inside its bounded fact projection: observing a flow between
#: two addresses is a fact, recommending action against one is not.
BANNED_TARGET_LOCATOR_FIELDS = frozenset(
    {
        "target_ip",
        "target_host",
        "target_hostname",
        "target_address",
        "target_mac",
        "target_fqdn",
        "destination_ip",
        "dest_ip",
        "source_ip",
        "ip",
        "ip_address",
        "ipv4",
        "ipv6",
        "hostname",
        "fqdn",
        "mac_address",
        "device_object_id",
        "vendor_object_id",
        "provider_object_id",
        "object_id",
        "interface_name",
        "port_id",
        "vlan_id",
    }
)

#: Key segments that mark secret material or its locator wherever they occur.
_SECRET_SEGMENTS = frozenset(
    {"token", "tokens", "password", "passwd", "secret", "secrets", "credential", "credentials", "apikey"}
)

#: Recognizable secret material in a *value*. Restated from
#: ``effect_contracts.validation.SECRET_MATERIAL_MARKERS`` (the test suite pins
#: that this stays a superset). It recognizes what it recognizes; the structural
#: rule is that refs are opaque and secrets never travel.
SECRET_MATERIAL_MARKERS = (
    "-----BEGIN",
    "PRIVATE KEY",
    "ssh-rsa",
    "ssh-ed25519",
    "ssh-dss",
    "password=",
    "passwd=",
    "secret=",
    "token=",
    "api_key=",
    "apikey=",
    "aws_secret_access_key",
    "AKIA",
    "xoxb-",
    "ghp_",
)

#: Ref kinds that are, by their kind alone, a credential locator. A typed ref
#: of one of these kinds anywhere in a record is refused: the record would be
#: telling its reader where to fetch a secret.
CREDENTIAL_LOCATOR_KINDS = frozenset(
    {"credential", "secret", "token", "key", "vault", "password", "keychain"}
)

#: Privacy classes. Closed; a consumer rejects or sanitizes a class it is not
#: admitted to receive (:func:`assert_privacy_admitted`).
PRIVACY_CLASSES = ("public", "internal", "sensitive", "restricted")

# Walk bounds for a whole record.
_MAX_DEPTH = 12
_MAX_MAP_ITEMS = 128
_MAX_SEQUENCE_ITEMS = 256
_MAX_STRING = 4096
_MAX_KEY = 128
_MAX_CANONICAL_BYTES = 256 * 1024

# Tighter bounds for an opaque vendor extension body.
VENDOR_EXTENSION_MAX_DEPTH = 4
VENDOR_EXTENSION_MAX_ITEMS = 32
VENDOR_EXTENSION_MAX_STRING = 1024
VENDOR_EXTENSION_MAX_BYTES = 8 * 1024
VENDOR_EXTENSION_MAX_COUNT = 4

# Tighter bounds for the normalized fact projection of an observation.
FACT_PROJECTION_MAX_DEPTH = 4
FACT_PROJECTION_MAX_ITEMS = 64
FACT_PROJECTION_MAX_BYTES = 16 * 1024

#: Keys a vendor extension may not use, because each names a field whose
#: meaning the envelope itself owns. An extension that carried
#: ``authority_class`` would be a second, unvalidated authority claim.
RESERVED_EXTENSION_KEYS = frozenset(
    {
        "authority",
        "authority_class",
        "executable",
        "decision_ref",
        "tenant_ref",
        "schema_version",
        "privacy_class",
        "fact_class",
        "status",
        "provenance",
    }
)

# Used with ``fullmatch`` only: ``$`` would also accept a trailing newline.
_TYPED_REF = re.compile(r"(?P<kind>[a-z][a-z0-9_]{0,31}):(?P<body>[A-Za-z0-9._~@=+:-]{1,200})")
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")

#: A credential locator at the start of a string, in any letter case and with
#: any body grammar (``vault:secret/data/db``, ``TOKEN:abc``, ``Key : x``).
_CREDENTIAL_LOCATOR_PREFIX = re.compile(
    r"^\s*(?:credentials?|secrets?|tokens?|key|vault|passwords?|passwd|keychain)\s*:",
    re.IGNORECASE,
)
#: The same locators *inside* free text. Narrower than the prefix rule (no bare
#: ``key:``, which prose uses), and requires a non-space body.
_CREDENTIAL_LOCATOR_INLINE = re.compile(
    r"\b(?:credentials?|secrets?|tokens?|vault|passwords?|passwd|keychain)\s*:\s*\S",
    re.IGNORECASE,
)
#: A tenant reference anywhere inside a string, any case, any body grammar.
_TENANT_INLINE = re.compile(r"\btenant\s*:\s*([^\s,;\"'()\[\]{}]+)", re.IGNORECASE)

#: Ref kinds that are, by their kind alone, a concrete target locator.
#: Refused as values in advisory and proposal records.
LOCATOR_REF_KINDS = frozenset(
    {"ip", "ipv4", "ipv6", "host", "hostname", "mac", "fqdn", "url", "uri", "domain"}
)
_LOCATOR_REF_PREFIX = re.compile(
    r"^\s*(?:ip|ipv4|ipv6|host|hostname|mac|fqdn|url|uri|domain)\s*:", re.IGNORECASE
)
_IPV4 = re.compile(r"(?<![0-9.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9])")
#: Compressed (``::``) or full eight-group IPv6. Timestamps (``00:05:00``) have
#: neither shape, which is why a looser pattern is not used.
_IPV6 = re.compile(
    r"(?i)(?<![0-9a-f])(?:"
    r"(?:[0-9a-f]{1,4}:){7}[0-9a-f]{1,4}"
    r"|(?:[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,6})?::(?:[0-9a-f]{1,4}(?::[0-9a-f]{1,4}){0,6})?"
    r")(?![0-9a-f:])"
)

#: Command tokens refused in advisory/proposal free text (rationale,
#: constraints, summary, limitations, unknowns). A closed denylist: it will
#: refuse prose that merely *mentions* one of these words (``ssh brute force``),
#: and that loss is accepted -- the alternative is guessing which mention is
#: an instruction. Such context belongs in an observation envelope's fact
#: projection, cited by ref.
COMMAND_TEXT_TOKENS = (
    "iptables",
    "ip6tables",
    "nft",
    "nftables",
    "ufw",
    "firewall-cmd",
    "netsh",
    "ip route",
    "ip rule",
    "route add",
    "ssh",
    "scp",
    "curl",
    "wget",
    "sudo",
    "systemctl",
    "rm",
    "chmod",
    "kubectl",
    "docker",
    "podman",
    "powershell",
    "cmd.exe",
    "bash",
    "sh -c",
)
_COMMAND_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:" + "|".join(re.escape(t) for t in COMMAND_TEXT_TOKENS) + r")(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
#: Shell metacharacter sequences refused in the same text.
SHELL_METACHARACTER_SEQUENCES = ("&&", "||", "`", "$(", "${", " | ", ">>")


def normalized_key(raw: str) -> str:
    """snake_case form of ``raw``: splits camelCase, folds separators.

    Ported from ``provisioning_contracts.validation.normalized_key`` (copied:
    the strict gate forbids the import). Only meaningful for ASCII keys --
    non-ASCII keys are refused before this is consulted (:func:`_check_key`).
    """

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


def _squashed(key: str) -> str:
    return key.replace("_", "")


def _check_key(raw: str, location: str) -> None:
    """Keys are closed to printable ASCII.

    Fullwidth letters, Cyrillic or Greek lookalikes, zero-width and other
    format characters can each spell a banned name that no ASCII comparison
    sees. Mapping confusables would be an open-ended table; refusing them is
    closed. A key outside printable ASCII is therefore refused outright.
    """

    if not (raw.isascii() and raw.isprintable()):
        raise ValueError(
            f"key {location!r} is not printable ASCII; non-ASCII and invisible "
            "characters in keys are refused"
        )


_BANNED_SQUASHED = frozenset(_squashed(name) for name in BANNED_EXTERNAL_SECURITY_FIELDS)
_SECRET_SUBSTRINGS = ("token", "password", "passwd", "secret", "credential", "apikey")


def _is_directive_key(raw: str) -> bool:
    key = normalized_key(raw)
    squashed = _squashed(key)
    if key in BANNED_EXTERNAL_SECURITY_FIELDS or squashed in _BANNED_SQUASHED:
        return True
    segments = set(key.split("_"))
    return (
        squashed.endswith("command")
        or squashed.startswith("command")
        or squashed.endswith("rule")
        or squashed.endswith("rules")
        or squashed.startswith("execute")
        or squashed.endswith("override")
        or squashed.startswith("override")
        or "executor" in squashed
        or bool(segments & _SECRET_SEGMENTS)
        or any(part in squashed for part in _SECRET_SUBSTRINGS)
        or squashed.endswith("success")
        or squashed.startswith("success")
    )


_BANNED_LOCATOR_SQUASHED = frozenset(_squashed(name) for name in BANNED_TARGET_LOCATOR_FIELDS)


def _is_locator_key(raw: str) -> bool:
    key = normalized_key(raw)
    return key in BANNED_TARGET_LOCATOR_FIELDS or _squashed(key) in _BANNED_LOCATOR_SQUASHED


def is_reserved_key(raw: str) -> bool:
    """True when ``raw`` spells a key the envelope owns, in any ASCII spelling."""

    return _squashed(normalized_key(raw)) in {_squashed(k) for k in RESERVED_EXTENSION_KEYS}


def _as_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _walk(
    value: Any,
    *,
    banned: Any,
    message: str,
    path: tuple[str, ...] = (),
    depth: int = 0,
) -> None:
    if depth > _MAX_DEPTH:
        raise ValueError("external-security payload exceeds maximum nesting depth")
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            raise ValueError("external-security payload contains oversized string")
        return
    if isinstance(value, float) and not _is_finite(value):
        raise ValueError("external-security payload contains a non-finite number")
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAP_ITEMS:
            raise ValueError("external-security payload map exceeds maximum item count")
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("external-security payload map keys must be strings")
            if len(raw_key) > _MAX_KEY:
                raise ValueError("external-security payload contains oversized key")
            location = ".".join((*path, raw_key))
            _check_key(raw_key, location)
            if banned(raw_key):
                raise ValueError(f"{message}: {location}")
            # `executable` is pinned False on every record. Anywhere it appears
            # with another value -- nested in a list, inside an extension -- it
            # is an execute flag, whatever the surrounding model says.
            if normalized_key(raw_key) == "executable" and child is not False:
                raise ValueError(f"execute flag is forbidden: {location}")
            _walk(child, banned=banned, message=message, path=(*path, raw_key), depth=depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if len(value) > _MAX_SEQUENCE_ITEMS:
            raise ValueError("external-security payload sequence exceeds maximum item count")
        for index, child in enumerate(value):
            _walk(child, banned=banned, message=message, path=(*path, str(index)), depth=depth + 1)
        return
    raise ValueError(f"unsupported external-security payload type: {type(value).__name__}")


def _is_finite(number: float) -> bool:
    return number == number and number not in (float("inf"), float("-inf"))


def contains_external_security_directive(value: Any) -> bool:
    """True when a nested payload would be refused by the directive guard."""

    try:
        assert_no_external_security_directives(value)
    except ValueError:
        return True
    return False


def assert_no_external_security_directives(value: Any) -> None:
    """Fail closed on a command, rule body, executor, secret, override, or execute flag.

    Recursive and bounded: refused at any depth up to the bound, including
    inside lists and tuples, and refused outright past it.
    """

    _walk(
        _as_payload(value),
        banned=_is_directive_key,
        message=(
            "external-security invariant violated: command/rule-body/executor/"
            "secret/override/execute field is forbidden"
        ),
    )


def assert_no_target_locators(value: Any) -> None:
    """Fail closed on a concrete hostname/IP/device-object locator.

    Applied to advisory and proposal records. Also bounded and recursive.
    """

    _walk(
        _as_payload(value),
        banned=_is_locator_key,
        message=(
            "external-security invariant violated: a concrete target locator is "
            "forbidden in an advisory or proposal; it belongs to the owning "
            "product's adapter"
        ),
    )


def _strings(value: Any, path: tuple[str, ...] = (), depth: int = 0):
    if depth > _MAX_DEPTH:
        raise ValueError("external-security payload exceeds maximum nesting depth")
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                yield (*path, "<key>"), key
            yield from _strings(child, (*path, str(key)), depth + 1)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for index, child in enumerate(value):
            yield from _strings(child, (*path, str(index)), depth + 1)


def assert_no_secret_material(value: Any) -> None:
    """Refuse recognizable secret material and credential locators anywhere.

    Two checks over every string, key or value, at every depth: a recognizable
    secret marker, and a typed ref whose *kind* is a credential locator
    (``credential:``, ``secret:``, ``token:``, ``vault:`` ...).
    """

    for path, text in _strings(_as_payload(value)):
        lowered = text.lower()
        for marker in SECRET_MATERIAL_MARKERS:
            if marker.lower() in lowered:
                raise ValueError(
                    f"{'.'.join(path) or '<root>'} carries recognizable secret material "
                    f"({marker!r}); this family carries opaque references only"
                )
        if _CREDENTIAL_LOCATOR_PREFIX.search(text) or _CREDENTIAL_LOCATOR_INLINE.search(text):
            raise ValueError(
                f"{'.'.join(path) or '<root>'} carries a credential locator; a "
                "contract never says where a secret lives"
            )


def assert_bounded_opaque(
    value: Any,
    *,
    max_depth: int,
    max_items: int,
    max_bytes: int,
    max_string: int = VENDOR_EXTENSION_MAX_STRING,
    what: str = "opaque payload",
) -> None:
    """Fail closed on a payload over the given depth / cardinality / size bounds."""

    def walk(node: Any, depth: int) -> None:
        if depth > max_depth:
            raise ValueError(f"{what} exceeds maximum nesting depth {max_depth}")
        if isinstance(node, str):
            if len(node) > max_string:
                raise ValueError(f"{what} contains a string over {max_string} characters")
            return
        if isinstance(node, float) and not _is_finite(node):
            raise ValueError(f"{what} contains a non-finite number")
        if node is None or isinstance(node, (bool, int, float)):
            return
        if isinstance(node, Mapping):
            if len(node) > max_items:
                raise ValueError(f"{what} has a map over {max_items} items")
            for key, child in node.items():
                if not isinstance(key, str):
                    raise ValueError(f"{what} map keys must be strings")
                walk(child, depth + 1)
            return
        if isinstance(node, Sequence) and not isinstance(node, (bytes, bytearray)):
            if len(node) > max_items:
                raise ValueError(f"{what} has a sequence over {max_items} items")
            for child in node:
                walk(child, depth + 1)
            return
        raise ValueError(f"{what} has unsupported type {type(node).__name__}")

    walk(value, 1)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"{what} exceeds {max_bytes} canonical bytes")


def canonical_external_security_json(value: Any) -> str:
    """Canonical JSON text for a record of this family.

    Byte-identical to the canonicalization the other families use (sorted
    keys, no insignificant whitespace, non-ASCII preserved, NaN refused), so a
    record canonicalized in one repository hashes the same in another. The
    directive and secret guards run first: nothing refused here gets a digest.
    """

    if hasattr(value, "model_validate") and hasattr(value, "model_dump"):
        # Frozen records still hold mutable dicts. Re-validating the dump means
        # a record mutated after construction cannot canonicalize.
        value = type(value).model_validate(value.model_dump(mode="json"))
    payload = _as_payload(value)
    assert_no_external_security_directives(payload)
    assert_no_secret_material(payload)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if len(encoded.encode("utf-8")) > _MAX_CANONICAL_BYTES:
        raise ValueError("external-security record exceeds maximum canonical size")
    return encoded


def canonical_digest(value: Any) -> str:
    """``sha256:<hex>`` of the canonical JSON of ``value`` (no guard run).

    Used for the vendor extension body digest, which is computed over
    vendor material before the surrounding record exists.
    """

    encoded = json.dumps(
        _as_payload(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def is_sha256_digest(raw: object) -> bool:
    return isinstance(raw, str) and _SHA256.fullmatch(raw) is not None


def parse_ref(raw: object) -> tuple[str | None, str]:
    """``(kind, body)`` of an opaque typed ref; ``kind`` is None when untyped."""

    if not isinstance(raw, str):
        return None, ""
    match = _TYPED_REF.fullmatch(raw)
    if match is None:
        return None, raw
    return match.group("kind"), match.group("body")


def require_ref_kind(raw: object, kind: str, *, field: str) -> str:
    """Require an opaque typed ref of exactly ``kind``.

    The body grammar admits no slash, whitespace, quote or newline, so a path,
    a URL, a PEM block or a command fragment cannot occupy a ref slot.
    """

    parsed_kind, _ = parse_ref(raw)
    if parsed_kind != kind:
        raise ValueError(f"{field} must be an opaque typed reference of kind {kind!r}, got {raw!r}")
    return str(raw)


def parse_timestamp(raw: str, *, field: str) -> datetime:
    """Parse an ISO-8601 instant, requiring an explicit offset."""

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field} is not an ISO-8601 timestamp: {raw!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must carry an explicit UTC offset: {raw!r}")
    return parsed


def assert_tenant_confined(value: Any, tenant_ref: str) -> None:
    """Every ``tenant:`` ref anywhere in a record must be the record's own tenant.

    A record naming a second tenant -- in its provenance chain, a subject ref,
    an extension -- is a cross-tenant reference and is refused.
    """

    for path, text in _strings(_as_payload(value)):
        for match in _TENANT_INLINE.finditer(text):
            named = "tenant:" + match.group(1)
            if named != tenant_ref:
                raise ValueError(
                    f"{'.'.join(path) or '<root>'} names {match.group(0)!r} inside a "
                    f"record bound to {tenant_ref!r}; cross-tenant references are refused"
                )


def assert_no_locator_values(value: Any) -> None:
    """Refuse concrete target locators carried as *values* (advisory, proposal).

    A locator-kind ref (``ip:``, ``host:``, ``hostname:``, ``mac:``, ``fqdn:``,
    ``url:``, ``uri:``, ``domain:``, any case) or an IPv4/IPv6-shaped value,
    anywhere in the record. Fields named ``*version`` are exempt from the
    address-shape scan only: ``1.2.3.4`` is a plausible version string.
    """

    for path, text in _strings(_as_payload(value)):
        location = ".".join(path) or "<root>"
        if _LOCATOR_REF_PREFIX.search(text):
            raise ValueError(
                f"{location} is a concrete target locator ({text!r}); an advisory or "
                "proposal names an opaque scope, never an address"
            )
        field = path[-1] if path else ""
        if field.endswith("version") or (len(path) >= 2 and path[-2].endswith("version")):
            continue
        if _IPV4.search(text) or _IPV6.search(text):
            raise ValueError(
                f"{location} carries an IP-address-shaped value; an advisory or "
                "proposal names an opaque scope, never an address"
            )


def assert_no_command_text(texts: Any, *, field: str) -> None:
    """Refuse command-shaped free text: a closed token denylist plus shell metacharacters."""

    if isinstance(texts, str):
        texts = (texts,)
    for text in texts:
        token = _COMMAND_TOKEN.search(text)
        if token is not None:
            raise ValueError(
                f"{field} contains the command token {token.group(0)!r}; advisory and "
                "proposal text describes, it never carries a command"
            )
        for sequence in SHELL_METACHARACTER_SEQUENCES:
            if sequence in text:
                raise ValueError(
                    f"{field} contains the shell metacharacter sequence {sequence!r}"
                )


def _get(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def assert_privacy_admitted(record: Any, admitted: frozenset[str] | set[str]) -> None:
    """Refuse a record whose ``privacy_class`` the consumer is not admitted to.

    The consumer states its own admission set; Fabric does not decide it. A
    class outside the closed vocabulary is refused whatever the admission set.
    """

    privacy_class = _get(record, "privacy_class")
    if privacy_class not in PRIVACY_CLASSES:
        raise ValueError(f"privacy_class {privacy_class!r} is not in the closed vocabulary")
    unknown = set(admitted) - set(PRIVACY_CLASSES)
    if unknown:
        raise ValueError(f"admission set names unknown privacy classes: {sorted(unknown)}")
    if privacy_class not in admitted:
        raise ValueError(
            f"record is classified {privacy_class!r}, which this consumer is not "
            "admitted to receive; reject or sanitize it"
        )


def assert_not_expired(record: Any, *, as_of: str) -> None:
    """Refuse a record whose ``expires_at`` is at or before ``as_of``.

    ``as_of`` is supplied by the caller: this module never reads a clock.
    """

    expires_at = _get(record, "expires_at")
    if expires_at is None:
        raise ValueError("record carries no expires_at; it cannot be judged fresh")
    if parse_timestamp(expires_at, field="expires_at") <= parse_timestamp(as_of, field="as_of"):
        raise ValueError(f"record expired at {expires_at}; a stale record extends nothing")


def assert_no_replay_extension(original: Any, candidate: Any) -> None:
    """A replayed or re-sent proposal must not change what it proposes.

    Two records with the same ``proposal_id`` must be canonically identical. A
    re-sent copy with a later ``expires_at``, a wider scope, or a different
    effect is not a renewal -- it is a new proposal wearing an old id, and a
    renewal is the owning product's decision, never a replay's.
    """

    original_id = _get(original, "proposal_id")
    if original_id is None or original_id != _get(candidate, "proposal_id"):
        return
    if canonical_digest(original) != canonical_digest(candidate):
        raise ValueError(
            f"proposal {original_id!r} was re-sent with different content; a replay "
            "cannot extend, widen, or change a proposal"
        )


def assert_device_observation_within_proposal(proposal: Any, observation: Any) -> None:
    """Bind a device observation to the proposal it reports on, and its window.

    Refused: a different proposal, tenant, or trace (an identifier collision);
    a different decision; and a status that reports the change as in place
    (``accepted_by_device`` / ``applied`` / ``observed``) at an instant outside
    ``[not_before, expires_at]``. After expiry an observation may report that a
    change was ``released``, ``failed``, ``stale`` or ``unknown`` -- never that
    it is still in place. A stale observation cannot keep an exposure alive.
    """

    if _get(observation, "proposal_ref") != _get(proposal, "proposal_id"):
        raise ValueError("device observation reports on a different proposal")
    for field in ("tenant_ref", "trace_ref", "decision_ref"):
        if _get(observation, field) != _get(proposal, field):
            raise ValueError(f"device observation and proposal disagree on {field}")
    status = _get(observation, "status")
    if status not in IN_PLACE_DEVICE_STATUSES:
        return
    observed = parse_timestamp(_get(observation, "observed_at"), field="observed_at")
    not_before = parse_timestamp(_get(proposal, "not_before"), field="not_before")
    expires = parse_timestamp(_get(proposal, "expires_at"), field="expires_at")
    if observed < not_before or observed > expires:
        raise ValueError(
            f"observation at {_get(observation, 'observed_at')} reports {status!r} "
            "outside the proposal window; a stale observation cannot extend an exposure"
        )
    window = _get(observation, "observation_window")
    if window is not None:
        start = parse_timestamp(_get(window, "start"), field="observation_window.start")
        end = parse_timestamp(_get(window, "end"), field="observation_window.end")
        if start < not_before or end > expires:
            raise ValueError(
                f"observation window reports {status!r} outside the proposal window; "
                "a stale observation cannot extend an exposure"
            )


#: Device statuses that report a change as being in place. None of them is a
#: success claim; they are what the device or its telemetry said.
IN_PLACE_DEVICE_STATUSES = frozenset({"accepted_by_device", "applied", "observed"})


__all__ = [
    "BANNED_EXTERNAL_SECURITY_FIELDS",
    "BANNED_TARGET_LOCATOR_FIELDS",
    "COMMAND_TEXT_TOKENS",
    "CREDENTIAL_LOCATOR_KINDS",
    "FACT_PROJECTION_MAX_BYTES",
    "FACT_PROJECTION_MAX_DEPTH",
    "FACT_PROJECTION_MAX_ITEMS",
    "IN_PLACE_DEVICE_STATUSES",
    "LOCATOR_REF_KINDS",
    "PRIVACY_CLASSES",
    "RESERVED_EXTENSION_KEYS",
    "SECRET_MATERIAL_MARKERS",
    "SHELL_METACHARACTER_SEQUENCES",
    "VENDOR_EXTENSION_MAX_BYTES",
    "VENDOR_EXTENSION_MAX_COUNT",
    "VENDOR_EXTENSION_MAX_DEPTH",
    "VENDOR_EXTENSION_MAX_ITEMS",
    "VENDOR_EXTENSION_MAX_STRING",
    "assert_bounded_opaque",
    "assert_device_observation_within_proposal",
    "assert_no_command_text",
    "assert_no_external_security_directives",
    "assert_no_locator_values",
    "assert_no_replay_extension",
    "assert_no_secret_material",
    "assert_no_target_locators",
    "assert_not_expired",
    "assert_privacy_admitted",
    "assert_tenant_confined",
    "canonical_digest",
    "canonical_external_security_json",
    "contains_external_security_directive",
    "is_reserved_key",
    "is_sha256_digest",
    "normalized_key",
    "parse_ref",
    "parse_timestamp",
    "require_ref_kind",
]
