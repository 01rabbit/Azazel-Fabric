"""The directive walkers that had no depth bound now have one (Fabric#23).

`deception_contracts`, `engagement_contracts` and `effect_contracts` walked a
payload as deep as it went. Past the interpreter's recursion limit (~1000
levels) that raised `RecursionError`: the payload did not get through, but a
caller catching `ValueError` -- the refusal every other guard raises -- saw an
unexpected exception instead of a rejection. The provisioning, M.I.O., outcome
and external-security walkers were bounded from the start.

These walkers are now bounded too, at 32 levels. The deepest payload any
contract model or golden fixture in this repository passes to them is 3 levels
(measured over the whole suite), so the bound sits an order of magnitude above
real use while staying well below the recursion limit.

What this file pins, per walker:

* a payload past the bound is refused with `ValueError`, never `RecursionError`,
  at depths up to and far beyond the old recursion limit;
* a clean payload exactly at the bound is still accepted, so the bound is not
  quietly tighter than documented;
* a directive inside the bound is still refused as a directive.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest

from azazel_fabric.deception_contracts import validation as deception
from azazel_fabric.effect_contracts import validation as effect
from azazel_fabric.engagement_contracts import validation as engagement

#: (id, guard, bound, a name the guard refuses). The bound is read from the
#: module so the test follows the constant -- and the constant is pinned below.
WALKERS: tuple[tuple[str, Callable[[Any], None], int, str], ...] = (
    (
        "deception.assert_no_runtime_directives",
        deception.assert_no_runtime_directives,
        deception.MAX_DIRECTIVE_WALK_DEPTH,
        "shell_command",
    ),
    (
        "deception.assert_no_effectiveness_verdict",
        deception.assert_no_effectiveness_verdict,
        deception.MAX_DIRECTIVE_WALK_DEPTH,
        "belief_score",
    ),
    (
        "engagement.assert_no_engagement_directives",
        engagement.assert_no_engagement_directives,
        engagement.MAX_DIRECTIVE_WALK_DEPTH,
        "arbiter_override",
    ),
    (
        "effect.assert_no_effect_authority_fields",
        effect.assert_no_effect_authority_fields,
        effect.MAX_EFFECT_WALK_DEPTH,
        sorted(effect.BANNED_EFFECT_AUTHORITY_FIELDS)[0],
    ),
    (
        "effect.assert_no_secret_material",
        lambda value: effect.assert_no_secret_material(value, field="refs"),
        effect.MAX_EFFECT_WALK_DEPTH,
        None,
    ),
)
_IDS = [w[0] for w in WALKERS]


def _nest(leaf: Any, levels: int, *, in_list: bool = False) -> Any:
    """`levels` containers around `leaf`; the leaf sits at depth `levels`."""
    payload = leaf
    for index in range(levels):
        if in_list and index % 2:
            payload = [payload]
        else:
            payload = {"n": payload}
    return payload


def test_the_bounds_are_the_documented_value():
    """Pinned as literals: loosening a bound is a change someone has to make on purpose."""
    assert deception.MAX_DIRECTIVE_WALK_DEPTH == 32
    assert engagement.MAX_DIRECTIVE_WALK_DEPTH == 32
    assert effect.MAX_EFFECT_WALK_DEPTH == 32


@pytest.mark.parametrize("levels", [33, 64, 999, 1500, 5000], ids=lambda d: f"depth{d}")
@pytest.mark.parametrize(("name", "guard", "bound", "banned"), WALKERS, ids=_IDS)
def test_a_payload_past_the_bound_is_a_value_error_not_a_recursion_error(
    name, guard, bound, banned, levels
):
    payload = _nest("harmless", max(levels, bound + 1))
    try:
        guard(payload)
    except RecursionError:  # pragma: no cover - the regression this file exists for
        pytest.fail(f"{name} overflowed the interpreter at depth {levels}")
    except ValueError as error:
        assert "nesting depth" in str(error), error
    else:
        pytest.fail(f"{name} accepted a payload {levels} levels deep")


@pytest.mark.parametrize("in_list", [False, True], ids=["mapping", "mixed"])
@pytest.mark.parametrize(("name", "guard", "bound", "banned"), WALKERS, ids=_IDS)
def test_a_clean_payload_at_the_bound_is_still_accepted(name, guard, bound, banned, in_list):
    guard(_nest("harmless", bound, in_list=in_list))


@pytest.mark.parametrize(("name", "guard", "bound", "banned"), WALKERS, ids=_IDS)
def test_one_level_past_the_bound_is_refused(name, guard, bound, banned):
    with pytest.raises(ValueError, match="nesting depth"):
        guard(_nest("harmless", bound + 1))


@pytest.mark.parametrize(("name", "guard", "bound", "banned"), WALKERS, ids=_IDS)
def test_a_directive_inside_the_bound_is_still_refused_as_a_directive(name, guard, bound, banned):
    if banned is None:
        leaf_payload: Any = "ghp_examplematerial"
        with pytest.raises(ValueError, match="secret material"):
            guard(_nest(leaf_payload, bound))
        return
    with pytest.raises(ValueError) as caught:
        guard(_nest({banned: "x"}, bound - 1, in_list=True))
    assert "nesting depth" not in str(caught.value), (
        f"{name} refused a directive at depth {bound} for its depth, not its key"
    )


def test_the_boolean_predicates_are_unchanged():
    """`contains_*` answer a question; they were not made to raise.

    The bound applies to the assertions. The public predicates keep their
    documented True/False contract, so a caller using them as a filter sees no
    new exception on a deep-but-clean payload of ordinary size.
    """

    deep_clean = _nest("harmless", 100)
    assert deception.contains_runtime_directive(deep_clean) is False
    assert deception.contains_effectiveness_verdict(deep_clean) is False
    assert deception.contains_runtime_directive(_nest({"shell_command": "x"}, 100)) is True
