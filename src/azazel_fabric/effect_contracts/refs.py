"""Typed, opaque cross-series references (Fabric#15).

Why a ref carries its own kind
------------------------------
The failure this exists to prevent is an *identifier in the wrong slot*: an
AZ-06 environment-lifecycle id supplied where an Edge decision reference is
required. Nothing about the two strings distinguishes them, so a consumer that
trusts the field name alone will happily correlate a materialization with a
decision that never happened.

A typed ref is ``"<kind>:<opaque>"``. The kind travels *with* the value, so the
slot can reject a value that announces itself as something else.

What this does not do
---------------------
It cannot discriminate a **bare, untyped** string. The shipped
``outcome_contracts`` family (``v0.9.0rc1``) uses untyped ids such as
``"decision-golden-redirect-1"``, and this family must stay correlatable with
it, so untyped values are accepted where they already exist. The guard is
therefore asymmetric and deliberately so:

* the ids this family *introduces* (effect, presented terrain, envelope) are
  required to be typed;
* the ids it *inherits* (trace, decision, execution) accept the untyped form,
  but reject a value typed as a different kind.

An untyped string in an inherited slot is not validated as belonging there.
That is a known, documented limit, not an oversight — closing it would mean
breaking correlation with the released family.
"""

from __future__ import annotations

import re
from enum import Enum

__all__ = [
    "OPAQUE_REF_PATTERN",
    "RefKind",
    "parse_ref",
    "require_ref_kind",
    "reject_ref_kinds",
]


class RefKind(str, Enum):
    """The kinds a cross-series reference may announce itself as."""

    TRACE = "trace"
    DECISION = "decision"
    EXECUTION = "execution"
    EFFECT = "effect"
    EFFECT_OBSERVATION = "effect_observation"
    LIFECYCLE = "lifecycle"
    PRESENTATION = "presentation"
    ENVIRONMENT = "environment"
    ADVISORY = "advisory"
    EVIDENCE = "evidence"
    SESSION = "session"
    SURFACE = "surface"
    ARTIFACT = "artifact"
    POLICY = "policy"
    PROFILE = "profile"
    SCOPE = "scope"
    OUTCOME = "outcome"
    ENVELOPE = "envelope"
    FIXTURE = "fixture"


#: A typed ref is a kind, the **first** colon, and an opaque body.
#:
#: The body character class is what makes the ref *opaque*: no slash, no
#: backslash, no whitespace, no quote, no newline. That structurally excludes
#: filesystem paths, URLs, PEM blocks and command fragments from every slot
#: that requires a typed ref -- which is the enforcement behind "opaque; no
#: secret material" for presented-terrain artifact references.
#:
#: The body *does* admit further colons, because the kind group cannot contain
#: one: the split point is unambiguously the first colon, whatever follows.
#: Excluding them bought no opacity and cost every producer in the series.
#: Azazel-Deception mints hierarchical references (``surface:http:8080``,
#: ``isolation:proof:1``, ``deception:surface:http-8080``) and Azazel-Edge
#: mints ``edge:nft:1``; under the colon-free body **none of them could be
#: placed in any slot this family requires a typed ref for**, so the family had
#: no possible producer at all. Rewriting a producer's identifier to fit a
#: grammar is not an option -- an identifier that has been rewritten no longer
#: resolves to the thing it named.
#:
#: Widening here is safe in both directions that matter. ``require_ref_kind``
#: only ever accepts more than it did. ``reject_ref_kinds`` only ever rejects
#: more -- and exactly where it should, since a value like ``surface:http:8080``
#: supplied as a ``trace_id`` was previously invisible to it.
OPAQUE_REF_PATTERN = re.compile(r"^(?P<kind>[a-z][a-z0-9_]{0,31}):(?P<body>[A-Za-z0-9._~@=+:-]{1,200})$")


def parse_ref(raw: object) -> tuple[RefKind | None, str]:
    """Return ``(kind, body)``; ``kind`` is ``None`` for an untyped value.

    Never raises for a malformed value -- a caller deciding whether a ref is
    *wrong* is a different question from a caller wanting to know what it is.
    """

    if not isinstance(raw, str):
        return None, ""
    match = OPAQUE_REF_PATTERN.match(raw)
    if match is None:
        return None, raw
    try:
        return RefKind(match.group("kind")), match.group("body")
    except ValueError:
        return None, raw


def require_ref_kind(raw: object, kind: RefKind, *, field: str) -> str:
    """Require a typed ref of exactly ``kind``. Used for ids this family owns."""

    parsed_kind, _ = parse_ref(raw)
    if parsed_kind is not kind:
        raise ValueError(
            f"{field} must be an opaque typed reference of kind {kind.value!r}, got {raw!r}"
        )
    return str(raw)


def reject_ref_kinds(raw: object, forbidden: frozenset[RefKind], *, field: str) -> object:
    """Reject a ref that announces itself as one of ``forbidden``.

    Used for ids inherited from the released ``outcome_contracts`` family,
    where an untyped value must still be accepted.
    """

    if raw is None:
        return raw
    parsed_kind, _ = parse_ref(raw)
    if parsed_kind in forbidden:
        raise ValueError(
            f"{field} must not be a {parsed_kind.value!r} reference; "
            "an identifier from another family cannot stand in for this one"
        )
    return raw
