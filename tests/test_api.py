"""Tests for `azazel_fabric.api` — error shape, roles, token auth.

Load-bearing properties: the error envelope matches contracts.md §3, the role
comparison is fail-closed, token extraction honors the primary+compat headers
case-insensitively, and comparison is fail-closed. Framework-neutral throughout.
"""

import sys

from azazel_fabric.api import (
    COMPAT_TOKEN_HEADER,
    FORBIDDEN,
    ROLES,
    TOKEN_HEADER,
    UNAUTHENTICATED,
    ErrorEnvelope,
    error_payload,
    extract_token,
    fail_closed_error,
    is_known_role,
    role_allows,
    role_rank,
    token_matches,
)


def test_error_payload_matches_contract_shape():
    payload = error_payload("bad", "nope", trace_id="t-1")
    assert payload == {"error": {"code": "bad", "message": "nope", "trace_id": "t-1"}}
    # validates against the model
    ErrorEnvelope.model_validate(payload)


def test_error_payload_omits_none_trace_id():
    payload = error_payload("bad", "nope")
    assert payload == {"error": {"code": "bad", "message": "nope"}}
    assert "trace_id" not in payload["error"]


def test_fail_closed_error_defaults_to_unauthenticated():
    payload = fail_closed_error()
    assert payload["error"]["code"] == UNAUTHENTICATED
    assert "message" in payload["error"]


def test_roles_are_ordered_least_to_most_privileged():
    assert ROLES == ("viewer", "operator", "responder", "admin")
    assert role_rank("viewer") < role_rank("operator") < role_rank("responder") < role_rank("admin")


def test_role_allows_is_fail_closed():
    assert role_allows("admin", "viewer") is True
    assert role_allows("operator", "operator") is True
    assert role_allows("viewer", "admin") is False
    # unknown roles never satisfy and never out-rank
    assert role_allows("wizard", "viewer") is False
    assert role_allows("admin", "wizard") is False
    assert is_known_role("wizard") is False
    assert role_rank("wizard") == -1


def test_extract_token_primary_and_compat_case_insensitive():
    assert extract_token({TOKEN_HEADER: "abc"}) == "abc"
    assert extract_token({COMPAT_TOKEN_HEADER: "def"}) == "def"
    # case-insensitive header lookup
    assert extract_token({"x-azazel-token": "abc"}) == "abc"
    # primary wins over compat
    assert extract_token({TOKEN_HEADER: "primary", COMPAT_TOKEN_HEADER: "compat"}) == "primary"
    # absent/blank -> None
    assert extract_token({}) is None
    assert extract_token({TOKEN_HEADER: "  "}) is None


def test_token_matches_is_fail_closed():
    assert token_matches({TOKEN_HEADER: "secret"}, "secret") is True
    assert token_matches({TOKEN_HEADER: "wrong"}, "secret") is False
    assert token_matches({}, "secret") is False
    assert token_matches({TOKEN_HEADER: "secret"}, "") is False


def test_api_core_imports_no_web_framework():
    # Framework-neutral: importing the api package pulls in neither flask nor
    # fastapi (they are optional extras, design-principles §5).
    import azazel_fabric.api  # noqa: F401

    assert "flask" not in sys.modules
    assert "fastapi" not in sys.modules
