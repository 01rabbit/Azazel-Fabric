"""Token-header extraction, framework-neutral (`contracts.md` §3).

Header convention::

    X-AZAZEL-TOKEN   (primary)
    X-Auth-Token     (compat alias)

This module reads a token out of a header mapping and compares it, fail-closed.
It imports no web framework: ``headers`` is any ``Mapping[str, str]`` (a
Flask/FastAPI/Werkzeug/plain-dict headers object all satisfy this), so the core
stays Pi-friendly and the framework adapters remain optional extras. It does not
issue, sign, or store tokens — only reads and compares what a product supplies.
"""

from __future__ import annotations

import hmac as _hmac
from typing import Mapping

# Header names (contracts.md §3). Lookup is case-insensitive because HTTP header
# names are case-insensitive and different frameworks normalize them differently.
TOKEN_HEADER = "X-AZAZEL-TOKEN"
COMPAT_TOKEN_HEADER = "X-Auth-Token"


def extract_token(headers: Mapping[str, str]) -> str | None:
    """Return the bearer token from the primary header, then the compat alias.

    Case-insensitive. Returns ``None`` when neither header is present or the
    value is blank — an absent token is a normal, expected input for a
    fail-closed caller, not an error to raise here.
    """
    lowered = {str(k).lower(): v for k, v in headers.items()}
    for name in (TOKEN_HEADER, COMPAT_TOKEN_HEADER):
        value = lowered.get(name.lower())
        if value and value.strip():
            return value.strip()
    return None


def token_matches(headers: Mapping[str, str], expected: str) -> bool:
    """True iff a token is present and equals ``expected``. Fail-closed.

    Uses a constant-time comparison to avoid leaking the token via timing, and
    denies when no token is present or ``expected`` is empty — never
    default-allows. This checks equality only; issuing and rotating tokens is
    the product's responsibility.
    """
    token = extract_token(headers)
    if not token or not expected:
        return False
    return _hmac.compare_digest(token, expected)
