"""Every banned field, every family, at depth and inside collections (#23).

The R1 exit gate asks for adversarial fixtures proving recursive rejection of
"all field categories, at any nesting depth, including inside collections".
The machinery was already sound -- this file found no defect. What was missing
was the proof: the existing tests exercise a handful of field names at nesting
depth two, in mappings only, for one of the six families.

That gap matters in a specific way. These guards are the mechanism behind the
one invariant Fabric cannot bend: a contract carries facts, never a directive.
There are 258 banned names across eight guards, and a guard that stopped
covering one of them -- a predicate narrowed, a family's walker replaced with
a shallower one -- would look exactly like a passing suite.

The cases below enumerate the constants, which covers every name without a
hand-kept list going stale. It does **not**, by itself, notice a name being
deleted from a constant: a deleted name simply stops being enumerated, and the
suite passes with one fewer case. That is the failure mode of every test that
derives its expectation from the thing it checks. `BANNED_FIELD_COUNTS` closes
it with literals, the way a test-count baseline does.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable

import pytest

#: (family, assert function, banned-field constant). Listed rather than
#: discovered, because "every public `assert_no_*` in every family" would also
#: sweep in guards that are not key-name walkers (window checks, chain
#: consistency) and quietly pass by never being exercised.
GUARDS: tuple[tuple[str, str, str], ...] = (
    ("provisioning_contracts", "assert_no_provisioning_directives", "BANNED_PROVISIONING_FIELDS"),
    ("provisioning_contracts", "assert_no_resource_tier_claim", "BANNED_TIER_CLAIM_FIELDS"),
    ("provisioning_contracts", "assert_no_role_inference", "BANNED_ROLE_INFERENCE_FIELDS"),
    ("mio_contracts", "assert_no_mio_directives", "BANNED_MIO_DIRECTIVE_FIELDS"),
    ("deception_contracts", "assert_no_runtime_directives", "BANNED_RUNTIME_DIRECTIVE_FIELDS"),
    ("deception_contracts", "assert_no_effectiveness_verdict", "BANNED_EFFECTIVENESS_VERDICT_FIELDS"),
    ("effect_contracts", "assert_no_effect_authority_fields", "BANNED_EFFECT_AUTHORITY_FIELDS"),
    ("engagement_contracts", "assert_no_engagement_directives", "BANNED_ENGAGEMENT_AUTHORITY_FIELDS"),
)


def _load(family: str, function: str, constant: str) -> tuple[Callable[[Any], None], frozenset[str]]:
    module = importlib.import_module(f"azazel_fabric.{family}.validation")
    return getattr(module, function), frozenset(getattr(module, constant))


#: Shapes a smuggled directive could arrive in. Each nests the payload
#: differently on purpose: a walker that recurses into mappings but not
#: sequences passes the first three and fails the rest.
SHAPES: dict[str, Callable[[dict[str, Any]], Any]] = {
    "bare": lambda payload: payload,
    "in_mapping": lambda payload: {"outer": payload},
    "deep_mapping": lambda payload: {"a": {"b": {"c": payload}}},
    "in_list": lambda payload: {"a": [payload]},
    "in_tuple": lambda payload: {"a": (payload,)},
    "list_of_list": lambda payload: {"a": [[payload]]},
    "mapping_under_list": lambda payload: {"a": [{"b": {"c": payload}}]},
    "alternating": lambda payload: {"a": [{"b": [{"c": [payload]}]}]},
}

_GUARD_IDS = [f"{family}.{function}" for family, function, _ in GUARDS]


#: How many names each guard refuses, as literals. Not derived, on purpose:
#: every other case here enumerates the constant, so a name deleted from one
#: would silently stop being tested. These numbers are the only thing that
#: notices. Adding a name is a deliberate change and updates its number here;
#: so is removing one, and that is the point -- the update is where someone
#: has to say why a name stopped being refused.
BANNED_FIELD_COUNTS: dict[str, int] = {
    "provisioning_contracts.assert_no_provisioning_directives": 107,
    "provisioning_contracts.assert_no_resource_tier_claim": 18,
    "provisioning_contracts.assert_no_role_inference": 19,
    "mio_contracts.assert_no_mio_directives": 36,
    "deception_contracts.assert_no_runtime_directives": 11,
    "deception_contracts.assert_no_effectiveness_verdict": 12,
    "effect_contracts.assert_no_effect_authority_fields": 36,
    "engagement_contracts.assert_no_engagement_directives": 19,
}


@pytest.mark.parametrize(("family", "function", "constant"), GUARDS, ids=_GUARD_IDS)
def test_the_guard_still_refuses_as_many_names_as_it_did(family, function, constant):
    """Non-vacuity, and the one check a deletion cannot slip past."""
    _, fields = _load(family, function, constant)
    name = f"{family}.{function}"

    assert name in BANNED_FIELD_COUNTS, f"{name} has no recorded field count"
    assert len(fields) == BANNED_FIELD_COUNTS[name], (
        f"{family}.{constant} now refuses {len(fields)} names, recorded as "
        f"{BANNED_FIELD_COUNTS[name]}. A name added is fine -- update the number. "
        "A name removed means something Fabric used to refuse it now accepts, "
        "and no other test in this file can see that, because they all "
        "enumerate this constant."
    )


def test_the_recorded_counts_cover_exactly_the_guards_under_test():
    """An entry for a guard that is not tested proves nothing about it."""
    assert set(BANNED_FIELD_COUNTS) == {f"{f}.{fn}" for f, fn, _ in GUARDS}


@pytest.mark.parametrize(("family", "function", "constant"), GUARDS, ids=_GUARD_IDS)
def test_every_banned_field_is_rejected_from_inside_a_collection(family, function, constant):
    """All ~250 names, in the shape a naive walker misses.

    One shape per field rather than the full cross product: the shapes are
    exercised exhaustively against a representative field below, so this asks
    the question that scales with the constant -- is any *name* uncovered --
    without running 2000 cases.
    """

    guard, fields = _load(family, function, constant)
    survivors = []
    for field in sorted(fields):
        payload = SHAPES["alternating"]({field: "x"})
        try:
            guard(payload)
        except ValueError:
            continue
        survivors.append(field)

    assert survivors == [], (
        f"{family}.{function} accepted a payload carrying {survivors} nested "
        "inside lists. A contract carries facts, never a directive -- and a "
        "directive the walker cannot see is one it cannot refuse."
    )


@pytest.mark.parametrize("shape", sorted(SHAPES), ids=sorted(SHAPES))
@pytest.mark.parametrize(("family", "function", "constant"), GUARDS, ids=_GUARD_IDS)
def test_a_directive_is_rejected_in_every_nesting_shape(family, function, constant, shape):
    guard, fields = _load(family, function, constant)
    field = sorted(fields)[0]

    with pytest.raises(ValueError):
        guard(SHAPES[shape]({field: "x"}))


@pytest.mark.parametrize("depth", [1, 2, 3, 5, 8, 9, 12, 20], ids=lambda d: f"depth{d}")
@pytest.mark.parametrize(("family", "function", "constant"), GUARDS, ids=_GUARD_IDS)
def test_a_directive_is_rejected_at_every_depth(family, function, constant, depth):
    """No level is a hole, whether or not the family bounds its walk.

    Two families bound the walk and refuse anything past the bound; the other
    four walk as far as the payload goes. Both refuse a directive at every
    depth, which is the property that matters here -- the difference in *why*
    is the subject of the two tests below.
    """

    guard, fields = _load(family, function, constant)
    field = sorted(fields)[0]

    payload: Any = {field: "x"}
    for _ in range(depth - 1):
        payload = {"n": payload}

    with pytest.raises(ValueError):
        guard(payload)


#: Guards that refuse a payload too deep to inspect, cleanly, with a
#: `ValueError` naming the bound -- whether or not it carries a directive.
#:
#: The other four walk as far as the payload goes. On an *ordinary* deep
#: payload that is the more permissive and arguably more correct answer: depth
#: alone is not a defect. What it costs is at the extreme -- past the
#: interpreter's recursion limit (~1000 levels here, measured) they raise
#: `RecursionError`, which refuses the payload but is not what a caller
#: catching `ValueError` will see as a rejection.
#:
#: Recorded as a fact rather than asserted as a requirement. Making the walk
#: bounded in the other four families changes their public behaviour and is a
#: decision to take deliberately, not a side effect of writing a test. What
#: this pins is that the set does not change silently: a family that gains or
#: loses a bound makes this list wrong, and someone looks.
BOUNDED_GUARDS = frozenset(
    {
        "provisioning_contracts.assert_no_provisioning_directives",
        "provisioning_contracts.assert_no_resource_tier_claim",
        "provisioning_contracts.assert_no_role_inference",
        "mio_contracts.assert_no_mio_directives",
    }
)


def _refusal(guard: Callable[[Any], None], depth: int) -> str:
    payload: Any = {"leaf": "harmless"}
    for _ in range(depth):
        payload = {"n": payload}
    try:
        guard(payload)
    except ValueError as error:
        return "bounded" if "nesting depth" in str(error) else "other_value_error"
    except RecursionError:
        return "recursion_error"
    return "accepted"


def _directive_outcome(guard: Callable[[Any], None], field: str, depth: int) -> str:
    payload: Any = {field: "x"}
    for _ in range(depth - 1):
        payload = {"n": payload}
    try:
        guard(payload)
    except ValueError:
        return "rejected"
    except RecursionError:
        return "recursion_error"
    return "ACCEPTED"


@pytest.mark.parametrize("depth", [64, 256, 2000], ids=lambda d: f"depth{d}")
@pytest.mark.parametrize(("family", "function", "constant"), GUARDS, ids=_GUARD_IDS)
def test_a_directive_is_never_accepted_however_deep_it_is_buried(
    family, function, constant, depth
):
    """The security property, stated so it holds for both designs.

    Past the interpreter's recursion limit an unbounded walker raises
    `RecursionError` rather than a clean `ValueError`. That is a refusal, not
    an acceptance -- the payload does not get through -- so the property to
    assert here is that the guard never *returns* on a directive, whatever
    depth it is at. How cleanly each family refuses is the subject of
    BOUNDED_GUARDS below, and is a robustness question, not this one.
    """

    guard, fields = _load(family, function, constant)
    field = sorted(fields)[0]

    assert _directive_outcome(guard, field, depth) != "ACCEPTED", (
        f"{family}.{function} accepted a directive buried {depth} levels deep. "
        "A directive the walker cannot see is one it cannot refuse."
    )


@pytest.mark.parametrize(("family", "function", "constant"), GUARDS, ids=_GUARD_IDS)
def test_which_guards_bound_their_walk_has_not_changed(family, function, constant):
    """Pins the split above, in both directions."""
    guard, _ = _load(family, function, constant)
    name = f"{family}.{function}"
    bounded = _refusal(guard, 64) == "bounded"

    if name in BOUNDED_GUARDS:
        assert bounded, (
            f"{name} is recorded as bounding its walk but no longer refuses a "
            "64-deep payload with a nesting-depth error. If the bound was "
            "removed deliberately, move it out of BOUNDED_GUARDS and say why."
        )
    else:
        assert not bounded, (
            f"{name} now bounds its walk. That is an improvement -- a caller "
            "catching ValueError sees a clean rejection where it previously "
            "got a RecursionError. Add it to BOUNDED_GUARDS."
        )


@pytest.mark.parametrize(("family", "function", "constant"), GUARDS, ids=_GUARD_IDS)
def test_an_ordinary_payload_still_passes(family, function, constant):
    """The other half of a rejection test.

    A guard that refused everything would pass every case above. This is what
    makes those cases mean "it rejected the directive" rather than "it rejected".
    """

    guard, fields = _load(family, function, constant)
    payload = {"observed_at": "2026-01-01T00:00:00+00:00", "refs": [{"id": "evidence:1"}]}

    assert not (set(payload) & fields), "the benign payload accidentally uses a banned name"
    guard(payload)
