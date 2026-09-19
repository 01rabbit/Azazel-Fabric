"""An unknown state never escalates, and the word is never a warrant.

Azazel-Fabric#14. Two properties carry the security weight here, and the rest
of the file is about keeping concepts that belong on separate axes from being
merged into one record.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from azazel_fabric.schema import (
    ESCALATION_ORDER,
    KNOWN_LEGACY_MODE_NAMES,
    UNKNOWN_FALLBACK,
    ActionKind,
    DefensiveState,
    DefensiveStateProjection,
    coerce_defensive_state,
    defensive_state_of_action,
    rank,
)
from azazel_fabric.schema.defensive_state import (
    DIRECTIVE_FIELDS,
    SEPARATE_CONCEPT_FIELDS,
)


def _projection(**overrides):
    fields = {
        "product": "azazel-edge",
        "node_id": "edge-1",
        "defensive_state": DefensiveState.THROTTLE,
        "state_source_ref": "arbiter:decision-log",
        "decision_ref": "decision-4711",
        "observed_at": "2026-09-19T00:00:00Z",
    }
    fields.update(overrides)
    return DefensiveStateProjection(**fields)


# --------------------------------------------------------------------------
# The vocabulary itself.
# --------------------------------------------------------------------------


def test_the_canonical_vocabulary_is_exactly_the_five_states():
    assert [s.value for s in DefensiveState] == [
        "OBSERVE", "NOTIFY", "THROTTLE", "REDIRECT", "ISOLATE",
    ]


def test_the_escalation_order_covers_every_state_once():
    assert set(ESCALATION_ORDER) == set(DefensiveState)
    assert len(ESCALATION_ORDER) == len(DefensiveState)
    assert [rank(s) for s in ESCALATION_ORDER] == list(range(len(DefensiveState)))


def test_the_fallback_is_the_weakest_state():
    assert rank(UNKNOWN_FALLBACK) == 0


# --------------------------------------------------------------------------
# Forward compatibility that fails safe. This is the one that matters.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "ISOLATE_NOW", "isolate", "Isolate", "ISOLATE ", " ISOLATE",
        "QUARANTINE", "BLOCK", "SHUTDOWN", "", "OBSERVE\n",
        "portal", "shield", "scapegoat", "lockdown",
    ],
)
def test_an_unrecognized_value_never_resolves_to_a_stronger_state(hostile):
    """A newer vocabulary, a typo, or a crafted payload must not widen a response."""

    state, recognized = coerce_defensive_state(hostile)

    assert recognized is False
    assert state is UNKNOWN_FALLBACK
    assert rank(state) == 0


@pytest.mark.parametrize("wrong_type", [None, 3, 3.5, [], {}, object(), True])
def test_a_non_string_value_also_fails_to_the_weakest_state(wrong_type):
    state, recognized = coerce_defensive_state(wrong_type)
    assert recognized is False
    assert state is UNKNOWN_FALLBACK


@pytest.mark.parametrize("state", list(DefensiveState))
def test_a_canonical_value_round_trips_and_is_marked_recognized(state):
    assert coerce_defensive_state(state) == (state, True)
    assert coerce_defensive_state(state.value) == (state, True)


def test_case_variants_are_not_silently_accepted():
    """Two spellings of one state on the wire is how a vocabulary drifts."""

    for variant in ("isolate", "Isolate", "iSoLaTe"):
        state, recognized = coerce_defensive_state(variant)
        assert recognized is False
        assert state is UNKNOWN_FALLBACK


# --------------------------------------------------------------------------
# Defensive state is not the other axes.
# --------------------------------------------------------------------------


def test_decoy_and_release_are_not_defensive_states():
    """A decoy belongs to the engagement axis; a release is a lifecycle step."""

    assert defensive_state_of_action("decoy") is None
    assert defensive_state_of_action("release") is None


def test_the_other_five_action_kinds_do_correspond():
    for kind in ("observe", "notify", "throttle", "redirect", "isolate"):
        assert defensive_state_of_action(kind) is DefensiveState(kind.upper())


def test_every_action_kind_is_accounted_for():
    """A new ActionKind must be classified deliberately, not left to chance."""

    kinds = set(ActionKind.__args__)
    mapped = {k for k in kinds if defensive_state_of_action(k) is not None}
    unmapped = kinds - mapped

    assert mapped == {"observe", "notify", "throttle", "redirect", "isolate"}
    assert unmapped == {"decoy", "release"}


def test_redirect_is_a_posture_not_a_deception_lifecycle_state():
    """Stated in the module and checked here: they are different axes.

    A product in REDIRECT may have no engagement environment at all, so the
    projection carries nothing about one.
    """

    projection = _projection(defensive_state=DefensiveState.REDIRECT)
    payload = projection.model_dump(mode="json")
    for lifecycle_word in ("engagement_state", "environment_id", "lifecycle_state"):
        assert lifecycle_word not in payload


# --------------------------------------------------------------------------
# The record describes; it does not instruct, and it does not merge axes.
# --------------------------------------------------------------------------


def test_authority_and_provenance_are_separate_from_the_value():
    """Merging them would make the word itself look like a warrant."""

    projection = _projection()
    payload = projection.model_dump(mode="json")

    assert payload["defensive_state"] == "THROTTLE"
    assert payload["state_source_ref"] == "arbiter:decision-log"
    assert payload["decision_ref"] == "decision-4711"
    assert payload["authority"] == "descriptive_only"


@pytest.mark.parametrize("directive", sorted(DIRECTIVE_FIELDS))
def test_a_directive_shaped_field_is_refused(directive):
    with pytest.raises(ValidationError, match="instructs nothing"):
        _projection(product_view={directive: "anything"})


@pytest.mark.parametrize("separate", sorted(SEPARATE_CONCEPT_FIELDS))
def test_a_separate_concept_cannot_ride_inside_this_record(separate):
    """Threat level, policy profile, runtime tier, engagement and presentation
    state each have their own owner. So does capability. A generic `mode` is
    refused for the same reason: it is where those meanings get lost."""

    with pytest.raises(ValidationError, match="separate concepts"):
        _projection(product_view={separate: "anything"})


#: The separations Azazel-Fabric#14 names, pinned independently of the module's
#: own constant. Parametrising over `SEPARATE_CONCEPT_FIELDS` follows whatever
#: that constant happens to say, so it cannot notice a name being dropped from
#: it — which is the change that would quietly re-merge two axes.
REQUIRED_SEPARATIONS = (
    "threat_level",
    "severity",
    "risk",
    "policy_profile",
    "ai_runtime_tier",
    "engagement_state",
    "presentation_state",
    "mode",
)


@pytest.mark.parametrize("concept", REQUIRED_SEPARATIONS)
def test_each_separation_the_contract_names_is_actually_refused(concept):
    """Pinned by name, so dropping one from the module's set fails here."""

    assert concept in SEPARATE_CONCEPT_FIELDS, (
        f"{concept!r} is named as a separate concept but is no longer refused"
    )
    with pytest.raises(ValidationError, match="separate concepts"):
        _projection(product_view={concept: "anything"})


@pytest.mark.parametrize(
    "directive", ["execute", "command", "approve", "override", "authorize", "enforce"]
)
def test_each_directive_shape_the_contract_names_is_actually_refused(directive):
    """Same reasoning: pinned by name rather than by the module's own set."""

    assert directive in DIRECTIVE_FIELDS
    with pytest.raises(ValidationError, match="instructs nothing"):
        _projection(product_view={directive: "anything"})


def test_the_two_refused_sets_do_not_overlap():
    """Each refusal must give the reason that actually applies."""

    assert not (DIRECTIVE_FIELDS & SEPARATE_CONCEPT_FIELDS)


def test_an_unknown_top_level_field_is_refused():
    with pytest.raises(ValidationError):
        _projection(escalate=True)


def test_the_record_is_frozen():
    projection = _projection()
    with pytest.raises(ValidationError):
        projection.defensive_state = DefensiveState.ISOLATE


# --------------------------------------------------------------------------
# Legacy vocabulary: carried, never made canonical.
# --------------------------------------------------------------------------


def test_a_legacy_mode_is_carried_as_context_not_as_a_state():
    projection = _projection(legacy_mode="scapegoat")

    assert projection.legacy_mode == "scapegoat"
    assert projection.defensive_state is DefensiveState.THROTTLE
    assert "scapegoat" not in {s.value for s in DefensiveState}


def test_no_legacy_name_is_a_defensive_state():
    for name in KNOWN_LEGACY_MODE_NAMES:
        assert name.upper() not in {s.value for s in DefensiveState}
        assert coerce_defensive_state(name)[1] is False


def test_fabric_defines_no_legacy_to_canonical_mapping():
    """Inventing what `portal` means as a posture would make a product-local
    word canonical by the back door. A product that needs a mapping owns it."""

    import azazel_fabric.schema.defensive_state as module

    source = module.__doc__ or ""
    exported = [name for name in dir(module) if "legacy" in name.lower()]
    assert exported == ["KNOWN_LEGACY_MODE_NAMES"], (
        f"{exported}: a translation helper here would make legacy canonical"
    )
    assert "portal" not in source


def test_an_empty_legacy_mode_is_refused():
    with pytest.raises(ValidationError, match="non-empty"):
        _projection(legacy_mode="   ")


# --------------------------------------------------------------------------
# Cross-product round trip.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("product", ["azazel-edge", "azazel-gadget", "azazel-boot"])
@pytest.mark.parametrize("state", list(DefensiveState))
def test_any_product_round_trips_any_state_byte_identically(product, state):
    original = _projection(product=product, defensive_state=state)
    wire = json.dumps(original.model_dump(mode="json"), sort_keys=True)
    restored = DefensiveStateProjection.model_validate(json.loads(wire))

    assert restored == original
    assert json.dumps(restored.model_dump(mode="json"), sort_keys=True) == wire


def test_a_projection_can_record_that_it_did_not_understand_the_producer():
    """The translation is visible rather than inferred as agreement."""

    state, recognized = coerce_defensive_state("SOME_FUTURE_STATE")
    projection = _projection(defensive_state=state, state_recognized=recognized)

    assert projection.state_recognized is False
    assert projection.defensive_state is UNKNOWN_FALLBACK


def test_product_specific_capability_limits_need_no_schema_change():
    """Not every product implements every state; the record does not insist."""

    for state in DefensiveState:
        assert _projection(product="azazel-boot", defensive_state=state)
