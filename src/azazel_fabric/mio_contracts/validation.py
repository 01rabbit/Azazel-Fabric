"""Static authority-boundary validation for M.I.O. cognition contracts.

M.I.O. output is text produced by a model. Fabric bounds its **shape** — it
cannot and does not claim to police prose. What these checks guarantee is that
no M.I.O. payload can carry a machine-actionable directive, a tool/function
call, a link, a follow-up request, or raw evidence across the sanitizer
boundary. An operator reading imperative-sounding narrative text is a UI and
policy concern; a consumer that can *execute* something a model said is a
contract failure, and that is what fails closed here.

Pure functions only: no clock, no filesystem, no network, no randomness.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

# The canonical runtime-directive names, restated rather than imported: this
# module stays import-light (importing ``deception_contracts`` for one frozenset
# would drag that whole family onto a Pi). ``test_mio_contracts.py`` asserts this
# set remains a superset of
# ``deception_contracts.validation.BANNED_RUNTIME_DIRECTIVE_FIELDS``, so the two
# definitions cannot drift apart.
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

# Cognition-specific shapes on top: a tool/function call, a follow-up disclosure
# request, and any link a renderer could turn into a fetch.
BANNED_MIO_DIRECTIVE_FIELDS = frozenset(
    _CANONICAL_RUNTIME_DIRECTIVE_FIELDS
    | {
        "tool_call",
        "tool_calls",
        "tool_use",
        "function_call",
        "function_calls",
        "action_required",
        "required_action",
        "instruction",
        "instructions",
        "directive",
        "auto_execute",
        "select_action",
        "selected_action",
        "follow_up_request",
        "followup_request",
        "request_more_data",
        "request_disclosure",
        "fetch_url",
        "url",
        "uri",
        "href",
        "link",
        "links",
        "file_path",
        "open_file",
    }
)

# Privacy classes that may never leave the node in a sanitized remote frame.
NON_EGRESSIBLE_PRIVACY_CLASSES = frozenset({"sensitive", "restricted"})

_MAX_DEPTH = 6
_MAX_MAP_ITEMS = 64
_MAX_SEQUENCE_ITEMS = 128
_MAX_STRING = 8192
_MAX_CANONICAL_BYTES = 128 * 1024


def _as_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _walk(value: Any, *, path: tuple[str, ...] = (), depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        raise ValueError("mio payload exceeds maximum nesting depth")
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            raise ValueError("mio payload contains oversized string")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, Mapping):
        if len(value) > _MAX_MAP_ITEMS:
            raise ValueError("mio payload map exceeds maximum item count")
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("mio payload map keys must be strings")
            if raw_key in BANNED_MIO_DIRECTIVE_FIELDS:
                location = ".".join((*path, raw_key))
                raise ValueError(
                    "mio advisory invariant violated: directive/tool-call/link/"
                    f"follow-up field is forbidden: {location}"
                )
            _walk(child, path=(*path, raw_key), depth=depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if len(value) > _MAX_SEQUENCE_ITEMS:
            raise ValueError("mio payload sequence exceeds maximum item count")
        for index, child in enumerate(value):
            _walk(child, path=(*path, str(index)), depth=depth + 1)
        return
    raise ValueError(f"unsupported mio payload type: {type(value).__name__}")


def contains_mio_directive(value: Any) -> bool:
    """Return True when a nested payload carries a directive/tool-call/link field."""

    payload = _as_payload(value)
    if isinstance(payload, Mapping):
        for key, child in payload.items():
            if isinstance(key, str) and key in BANNED_MIO_DIRECTIVE_FIELDS:
                return True
            if contains_mio_directive(child):
                return True
        return False
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return any(contains_mio_directive(item) for item in payload)
    return False


def assert_no_mio_directives(value: Any) -> None:
    """Fail closed on a directive, tool call, link, or follow-up request."""

    _walk(_as_payload(value))


def assert_bounded_mio_payload(value: Any) -> None:
    """Fail closed on an unbounded model-supplied payload."""

    payload = _as_payload(value)
    _walk(payload)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > _MAX_CANONICAL_BYTES:
        raise ValueError("mio payload exceeds maximum canonical size")


def canonical_mio_json(value: Any) -> str:
    """Return the canonical JSON text for an M.I.O. record.

    Byte-identical to the canonicalization the other contract families use
    (sorted keys, no insignificant whitespace, non-ASCII preserved, NaN
    rejected), so a frame canonicalized in one repository hashes the same in
    another.
    """

    payload = _as_payload(value)
    assert_no_mio_directives(payload)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _get(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def assert_advisory_inert(result: Any) -> None:
    """Reject an M.I.O. result that claims authority or executability.

    ``authority`` must be ``advisory_only``, ``executable`` must be falsey, and
    the rendering contract must stay ``inert_text``. Accepts a model or mapping.
    """

    authority = _get(result, "authority")
    if authority not in (None, "advisory_only"):
        raise ValueError(f"mio result claims non-advisory authority: {authority!r}")
    if _get(result, "executable") not in (None, False):
        raise ValueError("mio result claims to be executable")
    rendering = _get(result, "rendering")
    if rendering not in (None, "inert_text"):
        raise ValueError(f"mio result claims non-inert rendering: {rendering!r}")
    assert_no_mio_directives(_as_payload(result))


def assert_frame_sanitized_for_egress(frame: Any) -> None:
    """Reject a remote frame that could carry restricted content off the node.

    A sanitized frame may not be classified ``sensitive``/``restricted`` and may
    not declare that it contains raw evidence. Deny-on-ambiguity is the declared
    resolution: anything the sanitizer could not classify must have been dropped
    before this record existed.
    """

    privacy_class = _get(frame, "privacy_class")
    if privacy_class in NON_EGRESSIBLE_PRIVACY_CLASSES:
        raise ValueError(
            f"sanitized remote frame is classified {privacy_class!r}; restricted "
            "content must not leave the node (zero remote egress)"
        )
    if _get(frame, "contains_raw_evidence") not in (None, False):
        raise ValueError("sanitized remote frame declares raw evidence")
    if _get(frame, "ambiguity_resolution") not in (None, "deny_on_ambiguity"):
        raise ValueError("sanitized remote frame does not declare deny-on-ambiguity")
    assert_no_mio_directives(_as_payload(frame))


def assert_claim_provenance_preserved(claim_set: Any) -> None:
    """Reject a claim set that lost per-claim provenance.

    Every claim keeps its source; a claim attributed to a model keeps that
    model's reference and generation. A merge that flattens provenance is
    exactly the failure the program plan's AR-14 finding names.
    """

    claims = _get(claim_set, "claims") or ()
    seen: set[str] = set()
    for claim in claims:
        claim_id = _get(claim, "claim_id")
        if claim_id in seen:
            raise ValueError(f"claim set repeats claim_id {claim_id!r}")
        seen.add(claim_id)
        source = _get(claim, "source")
        if not source:
            raise ValueError(f"claim {claim_id!r} has no source; provenance is required")
        if source in ("local_model", "remote_model") and not _get(claim, "model_ref"):
            raise ValueError(
                f"claim {claim_id!r} is model-sourced but names no model_ref; "
                "provenance must survive the merge"
            )


__all__ = [
    "BANNED_MIO_DIRECTIVE_FIELDS",
    "NON_EGRESSIBLE_PRIVACY_CLASSES",
    "assert_advisory_inert",
    "assert_bounded_mio_payload",
    "assert_claim_provenance_preserved",
    "assert_frame_sanitized_for_egress",
    "assert_no_mio_directives",
    "canonical_mio_json",
    "contains_mio_directive",
]
