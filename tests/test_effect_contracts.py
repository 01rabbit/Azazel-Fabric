"""Fabric#15: the shared effect/outcome/terrain family describes, never decides.

Organized by the question each group answers, because a contract test that
reads as a list of field assertions stops catching the thing it was written
for. The adversarial section maps one-to-one onto the cases issue #15
enumerates; each test names the case it covers.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from azazel_fabric.effect_contracts import (
    BANNED_EFFECT_AUTHORITY_FIELDS,
    UNKNOWN_AUTHORITY_FALLBACK,
    UNKNOWN_EFFECT_CLASS_FALLBACK,
    WEAKEST_AUTHORITY,
    AuthorityClass,
    DefensiveEffectRef,
    EffectClass,
    EffectObservation,
    OBSERVABLE_AUTHORITY_CLASSES,
    OutcomeObservationEnvelope,
    PresentedTerrainRef,
    RefKind,
    ReplayProvenance,
    assert_effect_chain_consistent,
    assert_observation_within_effect_window,
    canonical_fact_json,
    coerce_authority_class,
    coerce_effect_class,
    is_authoritative_decision_reference,
    parse_ref,
    require_ref_kind,
)
from azazel_fabric.schema.defensive_state import DefensiveState

T0 = "2026-08-20T00:00:00+00:00"
T1 = "2026-08-20T00:05:00+00:00"
T2 = "2026-08-20T00:30:00+00:00"
T3 = "2026-08-22T00:00:00+00:00"
LATER = "2026-09-01T00:00:00+00:00"
DIGEST = "sha256:" + "c" * 64


def effect_ref(**overrides):
    fields = dict(
        effect_id="effect:e1",
        effect_class=EffectClass.REDIRECT_TO_PRESENTED_TERRAIN,
        producer_product="edge",
        producer_node="edge-1",
        trace_id="trace-1",
        decision_ref="decision-1",
        target_scope_ref="scope:session-1",
        policy_ref="policy-1",
        created_at=T0,
        expires_at=T3,
        authority_class=AuthorityClass.PRODUCER_DECISION_REF,
    )
    fields.update(overrides)
    return DefensiveEffectRef(**fields)


def observation(**overrides):
    fields = dict(
        observation_id="effect_observation:o1",
        effect_ref="effect:e1",
        trace_id="trace-1",
        status="active",
        observed_at=T1,
        materialization_producer="deception",
        authority_class=AuthorityClass.ACTIVE_MATERIALIZED,
    )
    fields.update(overrides)
    return EffectObservation(**fields)


def terrain(**overrides):
    fields = dict(
        presentation_id="presentation:p1",
        presentation_version=1,
        producer_product="deception",
        activation_decision_ref="decision-1",
        lifecycle_state_ref="lifecycle:env-1.active",
        isolation_assertion_ref="evidence:iso-1",
        created_at=T0,
        expires_at=T3,
        authority_class=AuthorityClass.ACTIVE_MATERIALIZED,
    )
    fields.update(overrides)
    return PresentedTerrainRef(**fields)


def envelope(**overrides):
    fields = dict(
        envelope_id="envelope:v1",
        producer_product="knowledge",
        producer_node="kn-1",
        producer_version="1",
        trace_id="trace-1",
        decision_ref="decision-1",
        effect_ref="effect:e1",
        presentation_ref="presentation:p1",
        window_start=T0,
        window_end=T2,
        observation_class="engagement",
        coverage_complete=True,
        observed_at=T2,
        authority_class=AuthorityClass.OBSERVED_FACT,
    )
    fields.update(overrides)
    return OutcomeObservationEnvelope(**fields)


def provenance(**overrides):
    fields = dict(
        software_revision="rev-1",
        runtime_profile="pi4-2gb",
        policy_config_digest=DIGEST,
        capture_generation=0,
        as_of=T0,
    )
    fields.update(overrides)
    return ReplayProvenance(**fields)


# --------------------------------------------------------------------------
# The core invariant: Fabric describes; products decide.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build", [effect_ref, observation, terrain, envelope], ids=lambda f: f.__name__
)
def test_every_shared_record_is_frozen_and_closed(build):
    """Frozen so a consumer cannot edit authority in flight; closed so a
    producer cannot append a field the contract never agreed to."""
    record = build()
    with pytest.raises(ValidationError):
        record.trace_id = "somewhere-else"
    with pytest.raises(ValidationError):
        build(an_additive_field_nobody_agreed_to="x")


@pytest.mark.parametrize(
    "build", [effect_ref, observation, terrain, envelope], ids=lambda f: f.__name__
)
def test_no_shared_record_can_carry_a_directive_flag(build):
    """`directive` is pinned False. A record that could set it would be an
    execution token wearing a description's name."""
    assert build().directive is False
    with pytest.raises(ValidationError):
        build(directive=True)


@pytest.mark.parametrize("banned", sorted(BANNED_EFFECT_AUTHORITY_FIELDS))
def test_product_owned_authority_concepts_are_refused_in_a_nested_payload(banned):
    """Issue #15 case: a future additive field accidentally creates directive
    semantics. The walk is recursive, so nesting does not help."""
    with pytest.raises(ValidationError):
        envelope(impact_observations={"noc": {banned: "anything"}})


def test_the_banned_set_actually_names_the_concepts_the_issue_excludes():
    """Pinned by name, not derived from the constant.

    A test that iterates the constant to check the constant is blind to a
    removal from it. These are the concepts issue #15 assigns to owning
    products; losing one silently is the failure worth catching.
    """
    required = {
        "adversary_belief",
        "belief_state",
        "council_vote",
        "council_synthesis",
        "counterfactual_ranking",
        "utility_score",
        "initiative_score",
        "operator_doctrine_acceptance",
        "model_confidence_probability",
        "must_apply",
        "authorize",
        "enforce",
        "tool_calls",
        "nft_command",
        "docker_command",
        "kvm_command",
        "edr_command",
        "tc_command",
    }
    missing = required - set(BANNED_EFFECT_AUTHORITY_FIELDS)
    assert missing == set(), f"banned concept list lost: {sorted(missing)}"


def test_no_envelope_can_declare_success():
    """There is no universal success field, by design: the shared walk rejects
    one wherever it appears."""
    with pytest.raises(ValidationError):
        envelope(impact_observations={"success": True})


# --------------------------------------------------------------------------
# Three vocabularies, kept distinct (issue #15 versioning rules)
# --------------------------------------------------------------------------


def test_an_effect_class_is_never_a_defensive_state_name():
    overlap = {member.value for member in EffectClass} & {
        member.value for member in DefensiveState
    }
    assert overlap == set(), f"effect and state vocabularies collided on {overlap}"


@pytest.mark.parametrize("state", [member.value for member in DefensiveState])
def test_a_defensive_state_value_is_rejected_where_an_effect_class_belongs(state):
    """Fabric#14's posture vocabulary cannot be poured into #15's effect slot."""
    with pytest.raises(ValidationError):
        effect_ref(effect_class=state)


def test_fabric_publishes_no_function_from_an_effect_class_to_a_defensive_state():
    """Deliberate absence, asserted so it cannot be added without a decision.

    A mapping would let anything that followed it read an effect as a posture.
    The two answer different questions and issue #15 requires them to stay
    distinct types.
    """
    import azazel_fabric.effect_contracts as module

    offenders = [
        name
        for name in dir(module)
        if "defensive_state" in name.lower() and callable(getattr(module, name, None))
    ]
    assert offenders == [], f"an effect->state mapping appeared: {offenders}"


def test_a_lifecycle_reference_is_not_an_effect_reference():
    with pytest.raises(ValidationError):
        observation(effect_ref="lifecycle:env-1.active")


# --------------------------------------------------------------------------
# Fail-safe coercion: unknown never escalates
# --------------------------------------------------------------------------


def test_the_weakest_authority_is_where_an_unknown_value_lands():
    assert UNKNOWN_AUTHORITY_FALLBACK is WEAKEST_AUTHORITY
    assert UNKNOWN_AUTHORITY_FALLBACK is AuthorityClass.STALE_OR_UNKNOWN


@pytest.mark.parametrize(
    "hostile",
    [
        "active_materialized ",
        "ACTIVE_MATERIALIZED",
        "producer_decision_ref;",
        "",
        None,
        17,
        ["active_materialized"],
    ],
)
def test_an_unrecognized_authority_value_never_escalates(hostile):
    """Issue #15 case: unknown enum must fail safely, never map to stronger."""
    coerced, recognized = coerce_authority_class(hostile)
    assert recognized is False
    assert coerced is UNKNOWN_AUTHORITY_FALLBACK
    assert is_authoritative_decision_reference(hostile) is False


@pytest.mark.parametrize(
    "hostile",
    ["network_isolation ", "NETWORK_ISOLATION", "isolate", "redirect", "", None, 3],
)
def test_an_unrecognized_effect_class_never_escalates(hostile):
    """Issue #15 case: unknown effect enum maps to ISOLATE/REDIRECT."""
    coerced, recognized = coerce_effect_class(hostile)
    assert recognized is False
    assert coerced is UNKNOWN_EFFECT_CLASS_FALLBACK
    assert coerced is EffectClass.OBSERVE_ONLY
    assert coerced not in (
        EffectClass.NETWORK_ISOLATION,
        EffectClass.REDIRECT_TO_PRESENTED_TERRAIN,
        EffectClass.SESSION_TERMINATION,
    )


def test_a_known_value_round_trips_and_is_reported_as_known():
    for member in AuthorityClass:
        assert coerce_authority_class(member.value) == (member, True)
    for member in EffectClass:
        assert coerce_effect_class(member.value) == (member, True)


# --------------------------------------------------------------------------
# Typed references
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected_kind",
    [
        ("effect:abc-1", RefKind.EFFECT),
        ("presentation:p.1", RefKind.PRESENTATION),
        ("decision-golden-redirect-1", None),
        ("/etc/shadow", None),
        ("nope:abc", None),
        ("effect:with space", None),
        ("effect:a/b", None),
        (None, None),
    ],
)
def test_ref_parsing_reports_what_it_can_and_stays_silent_otherwise(raw, expected_kind):
    kind, _ = parse_ref(raw)
    assert kind is expected_kind


#: Reference values the other Azazel repositories mint **today**, copied
#: literally rather than derived.
#:
#: Every one of them was refused by the original colon-free body, which meant
#: the family had no possible producer anywhere in the series. A derived list
#: would go quiet the moment a producer stopped minting one of these; a literal
#: one keeps saying what it was written to say.
REAL_PRODUCER_REFS = (
    # Azazel-Deception, tests/test_presented_terrain_evidence.py
    ("surface:http:8080", RefKind.SURFACE),
    # Azazel-Deception, tests/test_defensive_state_boundary.py
    ("deception:surface:http-8080", None),
    # Azazel-Deception, tests/test_cross_product_golden_outcome.py
    ("artifact:honey:invoice-2026", RefKind.ARTIFACT),
    # A presentation id re-minted from AZ-06's local `presentation-<sha24>`
    ("presentation:c8f1b94314c70a0a8cc13673", RefKind.PRESENTATION),
)


@pytest.mark.parametrize("raw,expected_kind", REAL_PRODUCER_REFS)
def test_a_hierarchical_producer_reference_is_a_reference(raw, expected_kind):
    """The body may carry further colons; only the first one splits.

    `deception:surface:http-8080` parses to no kind for a different reason --
    `deception` is not a `RefKind` -- and that distinction is the point: a
    value is untyped because Fabric does not know its kind, never because it
    was punctuated in a way the grammar happened to exclude.
    """

    assert parse_ref(raw)[0] is expected_kind


def test_the_split_point_is_the_first_colon_and_nothing_else():
    """Unambiguous because the kind group cannot contain a colon itself."""

    kind, body = parse_ref("surface:http:8080")
    assert (kind, body) == (RefKind.SURFACE, "http:8080")
    assert require_ref_kind("surface:http:8080", RefKind.SURFACE, field="surface")


def test_widening_the_body_did_not_widen_what_may_be_mistaken_for_a_decision():
    """The tightening direction, which is the one worth checking.

    `reject_ref_kinds` is the guard for slots that must still accept the
    released family's untyped ids. A hierarchical value it could not parse was
    a value it could not refuse, so `surface:http:8080` in a `trace_id` used to
    pass. It no longer does.
    """

    with pytest.raises(ValueError, match="surface"):
        effect_ref(trace_id="surface:http:8080")

    # ...while an untyped inherited id is exactly as acceptable as before.
    assert effect_ref(trace_id="decision-golden-redirect-1").trace_id


@pytest.mark.parametrize(
    "hostile",
    [
        "artifact:ssh-ed25519:AAAA",
        "artifact:-----BEGIN:KEY",
        "artifact:token=abc",
    ],
)
def test_what_the_wider_grammar_now_admits_is_still_caught_downstream(hostile):
    """The specific hole widening the body could have opened, proved closed.

    Each value below was refused by the *grammar* while a colon was excluded
    from the body, and is admitted by it now. None of them reaches a record:
    the marker scan on presented-terrain reference fields refuses them, which
    is the layer that was always meant to be doing this job. A value rejected
    only as a punctuation accident was never actually being screened.
    """

    with pytest.raises(ValidationError, match="secret material"):
        terrain(synthetic_artifact_refs=(hostile,))


def test_an_opaque_ref_cannot_be_a_path_a_url_or_a_pem_block():
    """Structural opacity is what keeps secret material out of a ref slot."""
    for hostile in (
        "artifact:/etc/shadow",
        "artifact:https://example.invalid/x",
        "artifact:-----BEGIN PRIVATE KEY-----",
        "artifact:line\nbreak",
        'artifact:"quoted"',
    ):
        with pytest.raises(ValueError):
            require_ref_kind(hostile, RefKind.ARTIFACT, field="artifact")


def test_an_untyped_inherited_id_is_still_accepted():
    """Correlation with the released outcome_contracts family must survive.

    Those records use untyped ids such as `decision-golden-redirect-1`. If this
    ever fails, the new family stopped being able to describe the old one.
    """
    assert effect_ref(decision_ref="decision-golden-redirect-1").decision_ref


# --------------------------------------------------------------------------
# Adversarial cases, one per bullet in issue #15
# --------------------------------------------------------------------------


def test_a_model_crafted_payload_cannot_masquerade_as_an_authoritative_effect():
    """Case: model-crafted payload mimics an authoritative effect ref.

    An advisory record cannot reach the function that says "this is a
    producer-local authoritative decision" -- and cannot get there by also
    carrying a decision reference, which is refused outright.
    """
    advisory = effect_ref(
        authority_class=AuthorityClass.ADVISORY_INFERENCE,
        decision_ref=None,
        advisory_ref="advisory:a1",
        producer_product="knowledge",
    )
    assert is_authoritative_decision_reference(advisory.authority_class) is False

    with pytest.raises(ValidationError):
        effect_ref(
            authority_class=AuthorityClass.ADVISORY_INFERENCE,
            advisory_ref="advisory:a1",
            decision_ref="decision-1",
        )


def test_a_decision_claim_must_substantiate_itself():
    with pytest.raises(ValidationError):
        effect_ref(authority_class=AuthorityClass.PRODUCER_DECISION_REF, decision_ref=None)


def test_a_lifecycle_id_cannot_stand_in_for_a_decision_reference():
    """Case: AZ-06 lifecycle ID supplied where Edge decision ID is required."""
    with pytest.raises(ValidationError):
        effect_ref(decision_ref="lifecycle:env-1.active")
    with pytest.raises(ValidationError):
        terrain(activation_decision_ref="lifecycle:env-1.active")
    with pytest.raises(ValidationError):
        envelope(decision_ref="presentation:p1")


def test_a_stale_observation_cannot_report_an_expired_effect_as_live():
    """Case: stale/replayed EffectObservation prolongs an environment."""
    ref = effect_ref()
    replayed = observation(status="active", observed_at=LATER)
    with pytest.raises(ValueError, match="cannot prolong"):
        assert_observation_within_effect_window(ref, replayed)


def test_a_late_observation_may_still_report_that_the_effect_ended():
    """The guard bounds what a stale record may *claim*, not whether it exists.

    An observation arriving after expiry is exactly how a consumer learns the
    effect is over; refusing it outright would lose that.
    """
    ref = effect_ref()
    ended = observation(
        status="terminated",
        observed_at=LATER,
        termination_reason="ttl_expired",
        authority_class=AuthorityClass.OBSERVED_FACT,
    )
    assert_observation_within_effect_window(ref, ended)


def test_only_a_live_observation_may_claim_an_active_materialization():
    with pytest.raises(ValidationError):
        observation(status="completed", authority_class=AuthorityClass.ACTIVE_MATERIALIZED)
    with pytest.raises(ValidationError):
        observation(status="active", authority_class=AuthorityClass.OBSERVED_FACT)


def test_an_effect_reference_cannot_claim_to_be_an_observation():
    for claimed in (AuthorityClass.OBSERVED_FACT, AuthorityClass.ACTIVE_MATERIALIZED):
        with pytest.raises(ValidationError):
            effect_ref(authority_class=claimed)


@pytest.mark.parametrize(
    "claimed",
    sorted(set(AuthorityClass) - OBSERVABLE_AUTHORITY_CLASSES, key=lambda m: m.value),
)
def test_an_observation_cannot_claim_what_it_did_not_observe(claimed):
    """Fabric#52. The converse of the rule above, which was prose until now.

    ``DefensiveEffectRef`` has refused ``observed_fact`` and
    ``active_materialized`` since the family shipped, on the stated grounds
    that they are "an observation's to make". The other direction was written
    in the docstring and enforced nowhere, so a record reporting an effect
    could arrive claiming authority *over* it.

    Each rejected class fails for its own reason and they are not
    interchangeable: ``producer_decision_ref`` is a report asserting a
    decision; ``advisory_inference`` and ``planned_shadow`` describe records
    where nothing was materialized, so there was nothing to observe; and
    ``stale_or_unknown`` claims nothing, which a consumer must read as a gap
    rather than as a weakly-labelled fact.
    """

    with pytest.raises(ValidationError):
        observation(status="completed", authority_class=claimed)


def test_every_authority_class_belongs_to_exactly_one_record():
    """The two rules are one rule, and this is what keeps them that way.

    An ``AuthorityClass`` member added later has to land on one side. Without
    this, the default would be "accepted by ``DefensiveEffectRef``, rejected by
    ``EffectObservation``" -- a placement nobody chose, arrived at by not
    writing anything. Enumerating from the enum rather than from either
    model's constant is what lets a new member be *seen*.
    """

    effect_only = set(AuthorityClass) - OBSERVABLE_AUTHORITY_CLASSES

    assert effect_only & OBSERVABLE_AUTHORITY_CLASSES == set()
    assert effect_only | OBSERVABLE_AUTHORITY_CLASSES == set(AuthorityClass)

    for member in sorted(OBSERVABLE_AUTHORITY_CLASSES, key=lambda m: m.value):
        with pytest.raises(ValidationError):
            effect_ref(authority_class=member)
    for member in sorted(effect_only, key=lambda m: m.value):
        with pytest.raises(ValidationError):
            observation(status="completed", authority_class=member)


def test_an_observation_still_accepts_both_classes_it_is_meant_to_carry():
    """A rule that rejected everything would pass every test above.

    ``observed_fact`` for an effect that is no longer live, and
    ``active_materialized`` for one that is: the whole accepted set, stated
    positively, so that narrowing it further is a failure rather than a
    tightening nobody notices.
    """

    assert (
        observation(status="completed", authority_class=AuthorityClass.OBSERVED_FACT)
        .authority_class
        is AuthorityClass.OBSERVED_FACT
    )
    assert (
        observation(status="active", authority_class=AuthorityClass.ACTIVE_MATERIALIZED)
        .authority_class
        is AuthorityClass.ACTIVE_MATERIALIZED
    )


@pytest.mark.parametrize(
    "hostile",
    [
        "artifact:AKIAIOSFODNN7EXAMPLE",
        "artifact:ghp_0123456789abcdef",
        "artifact:token=abcdef",
    ],
)
def test_presented_terrain_refuses_recognizable_secret_material(hostile):
    """Case: PresentedTerrainRef contains real credential/path material."""
    with pytest.raises(ValidationError):
        terrain(synthetic_artifact_refs=(hostile,))


def test_presented_terrain_describes_the_defender_not_the_adversary():
    """Case: the record must not become a belief record."""
    assert terrain().describes == "defender_presented_surface"
    with pytest.raises(ValidationError):
        terrain(describes="adversary_perceived_surface")
    with pytest.raises(ValidationError):
        terrain(authority_class=AuthorityClass.ADVISORY_INFERENCE)


def test_an_envelope_that_lost_telemetry_cannot_look_whole():
    """Case: outcome envelope hides telemetry loss and appears successful."""
    with pytest.raises(ValidationError, match="must name the gaps"):
        envelope(coverage_complete=False, telemetry_gaps=())
    with pytest.raises(ValidationError):
        envelope(coverage_complete=True, telemetry_gaps=("netflow_dropped",))
    assert envelope(coverage_complete=False, telemetry_gaps=("netflow_dropped",))


def test_an_envelope_never_carries_a_decisions_authority():
    with pytest.raises(ValidationError):
        envelope(authority_class=AuthorityClass.PRODUCER_DECISION_REF)


def test_a_cross_trace_collision_breaks_the_chain():
    """Case: cross-tenant/cross-trace ID collision."""
    ref = effect_ref()
    with pytest.raises(ValueError, match="different trace"):
        assert_effect_chain_consistent(ref, [observation(trace_id="trace-other")])
    with pytest.raises(ValueError, match="different effect"):
        assert_effect_chain_consistent(ref, [observation(effect_ref="effect:other")])
    with pytest.raises(ValueError, match="different trace"):
        assert_effect_chain_consistent(ref, envelope=envelope(trace_id="trace-other"))


def test_a_terrain_activated_by_another_decision_breaks_the_chain():
    ref = effect_ref()
    with pytest.raises(ValueError, match="different decision"):
        assert_effect_chain_consistent(ref, terrain=terrain(activation_decision_ref="decision-2"))


def test_an_envelope_pointing_at_another_terrain_breaks_the_chain():
    ref = effect_ref()
    with pytest.raises(ValueError, match="different presented terrain"):
        assert_effect_chain_consistent(
            ref, envelope=envelope(presentation_ref="presentation:other"), terrain=terrain()
        )


def test_a_consistent_chain_passes():
    assert_effect_chain_consistent(effect_ref(), [observation()], envelope(), terrain())


def test_provenance_is_structurally_incapable_of_conferring_authority():
    """Case: signature/provenance presence is mistaken for authorization."""
    assert provenance().confers_authority is False
    with pytest.raises(ValidationError):
        provenance(confers_authority=True)


def test_provenance_carrying_a_model_reference_grants_the_model_nothing():
    """A model locator makes a run reproducible. It is not the model's vote."""
    record = provenance(model_ref="model:advisor-v1")
    assert record.confers_authority is False
    assert is_authoritative_decision_reference(record.model_dump()) is False


# --------------------------------------------------------------------------
# Bounds and serialization
# --------------------------------------------------------------------------


def test_an_effect_must_be_bounded_in_time():
    with pytest.raises(ValidationError):
        effect_ref(expires_at=T0)
    with pytest.raises(ValidationError):
        terrain(expires_at=T0)


def test_a_naive_timestamp_is_refused():
    """Two products in different zones writing naive instants produce an
    ordering that validates and is wrong."""
    with pytest.raises(ValidationError):
        effect_ref(created_at="2026-08-20T00:00:00")


def test_a_termination_must_say_why():
    for status in ("terminated", "failed"):
        with pytest.raises(ValidationError):
            observation(
                status=status,
                termination_reason=None,
                authority_class=AuthorityClass.OBSERVED_FACT,
            )


def test_a_window_cannot_run_backwards():
    with pytest.raises(ValidationError):
        envelope(window_start=T2, window_end=T0)


@pytest.mark.parametrize(
    "build", [effect_ref, observation, terrain, envelope, provenance], ids=lambda f: f.__name__
)
def test_canonical_serialization_is_stable_and_round_trips(build):
    record = build()
    first = canonical_fact_json(record)
    assert first == canonical_fact_json(record)
    restored = type(record).model_validate(json.loads(first))
    assert restored == record
    assert canonical_fact_json(restored) == first


# ---------------------------------------------------------------------------
# Presented terrain provenance (Fabric#51)
# ---------------------------------------------------------------------------


def shadow_effect(**overrides):
    """An effect with no decision behind it. AZ-06's ordinary mode."""

    fields = dict(
        effect_id="effect:e-shadow",
        effect_class="redirect_to_presented_terrain",
        producer_product="deception",
        producer_node="az06-1",
        trace_id="trace-1",
        target_scope_ref="scope:s1",
        policy_ref="policy-1",
        created_at=T0,
        expires_at=T3,
        authority_class=AuthorityClass.PLANNED_SHADOW,
    )
    fields.update(overrides)
    return DefensiveEffectRef(**fields)


def bound_terrain(**overrides):
    """A terrain bound to an effect rather than to a decision."""

    fields = dict(
        presentation_id="presentation:p-shadow",
        presentation_version=1,
        producer_product="deception",
        source_effect_ref="effect:e-shadow",
        trace_id="trace-1",
        lifecycle_state_ref="lifecycle:env-1.shadow",
        isolation_assertion_ref="evidence:iso-1",
        created_at=T0,
        expires_at=T3,
        authority_class=AuthorityClass.PLANNED_SHADOW,
    )
    fields.update(overrides)
    return PresentedTerrainRef(**fields)


# -- success ----------------------------------------------------------------


def test_a_decision_less_effect_can_now_be_chained_to_a_terrain():
    """The case that was structurally impossible until this change.

    `assert_effect_chain_consistent` compared the terrain's
    `activation_decision_ref` against the effect's `decision_ref`. For a
    `planned_shadow` effect that is `None`, and the terrain's was required and
    non-empty, so the comparison could only ever fail. AZ-06 runs in this mode
    by default, which means the family's own default producer could not
    produce a valid chain.
    """

    assert_effect_chain_consistent(shadow_effect(), terrain=bound_terrain())


def test_the_decision_bearing_chain_is_unchanged():
    """The rule that was already here still holds, and still passes."""

    assert_effect_chain_consistent(effect_ref(), terrain=terrain())


# -- mix-up -----------------------------------------------------------------


def test_a_terrain_bound_to_a_different_effect_is_refused():
    with pytest.raises(ValueError, match="different effect"):
        assert_effect_chain_consistent(
            shadow_effect(), terrain=bound_terrain(source_effect_ref="effect:other")
        )


def test_a_terrain_carrying_a_different_trace_is_refused():
    """The reason `source_effect_ref` is not enough on its own.

    An effect id is an identifier somebody else minted. Two incidents whose
    producers chose the same one would chain cleanly on the effect reference
    alone, which is the collision typed references exist to make visible.
    """

    with pytest.raises(ValueError, match="different trace"):
        assert_effect_chain_consistent(
            shadow_effect(), terrain=bound_terrain(trace_id="trace-other")
        )


def test_a_decision_bearing_chain_also_checks_the_trace_when_it_is_there():
    """Optional to carry; not optional to be right.

    `trace_id` stays optional on a decision-activated terrain so a producer
    pinned to `v0.9.0rc4` keeps working. A field that is carried and never
    compared reads as a guarantee it is not, so when it is present it is
    checked.
    """

    assert_effect_chain_consistent(effect_ref(), terrain=terrain(trace_id="trace-1"))
    with pytest.raises(ValueError, match="different trace"):
        assert_effect_chain_consistent(
            effect_ref(), terrain=terrain(trace_id="trace-other")
        )


def test_a_terrain_naming_a_decision_the_effect_does_not_have_is_refused():
    """Filling the slot with something that is not a decision is the defect.

    The obvious way to make a shadow chain validate was to put *anything* in
    `activation_decision_ref`. A chain that accepted it would assert an
    authority nobody exercised, which is the one thing this family exists to
    keep straight.
    """

    with pytest.raises(ValueError, match="the effect has none"):
        assert_effect_chain_consistent(
            shadow_effect(),
            terrain=bound_terrain(activation_decision_ref="decision-invented"),
        )


# -- missing ----------------------------------------------------------------


def test_a_terrain_that_names_nothing_is_refused_at_construction():
    """Refused by the model, not by the chain check.

    A record that reaches a consumer and only fails when something happens to
    chain it is a record that gets logged, rendered and believed in between.
    """

    with pytest.raises(ValidationError, match="names neither"):
        bound_terrain(source_effect_ref=None, trace_id=None)


def test_an_effect_reference_without_a_trace_is_refused_at_construction():
    with pytest.raises(ValidationError, match="requires trace_id"):
        bound_terrain(trace_id=None)


class _UnboundTerrain:
    """A terrain-shaped object carrying neither binding.

    `PresentedTerrainRef` refuses this at construction, so the chain check's
    branch for it cannot be reached with a validated model -- which would make
    that branch dead code, and this file has spent the day removing those.

    It is reachable, and this is how. `assert_effect_chain_consistent` is
    typed `Any`: it correlates whatever it is handed, including a record a
    caller rebuilt from JSON without going through the model. The branch is
    the backstop for exactly that caller, and this is the measurement showing
    it is one rather than an assumption.
    """

    activation_decision_ref = None
    source_effect_ref = None
    trace_id = None
    presentation_id = "presentation:unbound"


def test_a_decision_less_effect_with_an_unbound_terrain_is_refused():
    """The chain-level half, reachable only for an unvalidated record."""

    with pytest.raises(ValueError, match="bind to it through source_effect_ref"):
        assert_effect_chain_consistent(shadow_effect(), terrain=_UnboundTerrain())


def test_a_decision_bearing_effect_with_an_unbound_terrain_is_refused():
    with pytest.raises(ValueError, match="names none"):
        assert_effect_chain_consistent(effect_ref(), terrain=bound_terrain())


def test_the_three_refusals_say_three_different_things():
    """Each one leads to a different correction (Fabric#51 §5).

    "A different decision" means fix the reference. "A decision the effect
    does not have" means remove it. "The binding is missing" means add one.
    A caller told only that the chain is inconsistent has to work out which,
    and the three are not interchangeable.
    """

    messages = []
    for effect, built in (
        (effect_ref(), terrain(activation_decision_ref="decision-other")),
        (shadow_effect(), bound_terrain(activation_decision_ref="decision-x")),
        (shadow_effect(), _UnboundTerrain()),
    ):
        with pytest.raises(ValueError) as caught:
            assert_effect_chain_consistent(effect, terrain=built)
        messages.append(str(caught.value))

    assert len(set(messages)) == 3, messages


# -- old payloads -----------------------------------------------------------


def test_an_rc4_terrain_payload_still_validates():
    """The compatibility claim, checked rather than asserted.

    This is the exact field set `v0.9.0rc4` required, with none of the slots
    added here. If this ever fails, the change stopped being additive and the
    compatibility table is wrong.
    """

    rc4_payload = {
        "presentation_id": "presentation:p1",
        "presentation_version": 1,
        "producer_product": "deception",
        "activation_decision_ref": "decision-1",
        "lifecycle_state_ref": "lifecycle:env-1.active",
        "isolation_assertion_ref": "evidence:iso-1",
        "created_at": T0,
        "expires_at": T3,
        "authority_class": "active_materialized",
    }
    built = PresentedTerrainRef(**rc4_payload)

    assert built.source_effect_ref is None
    assert built.trace_id is None
    assert built.synthetic_identity_refs == ()
    assert built.synthetic_credential_refs == ()
    assert_effect_chain_consistent(effect_ref(), terrain=built)


def test_an_rc4_consumer_reading_a_new_payload_sees_the_slots_it_knows():
    """The other direction: a producer on rc5, a consumer still on rc4.

    A consumer that reads only the rc4 field set gets the same answer it
    always did. The new slots are additions to the record, not a rearrangement
    of it -- which is what makes the rollout orderable in either direction.
    """

    payload = bound_terrain(
        activation_decision_ref="decision-1",
        synthetic_identity_refs=("identity:i1",),
    ).model_dump(mode="json")

    rc4_known = {
        "presentation_id", "presentation_version", "producer_product",
        "activation_decision_ref", "lifecycle_state_ref", "active_surface_refs",
        "synthetic_artifact_refs", "isolation_assertion_ref",
        "isolation_result_ref", "created_at", "expires_at", "evidence_refs",
        "authority_class", "describes", "directive", "schema_version",
    }
    assert rc4_known <= set(payload), sorted(rc4_known - set(payload))
    assert payload["activation_decision_ref"] == "decision-1"


# -- identity and credential slots ------------------------------------------


@pytest.mark.parametrize(
    "field,kind",
    [("synthetic_identity_refs", "identity"), ("synthetic_credential_refs", "credential")],
)
def test_the_new_reference_slots_require_their_own_kind(field, kind):
    assert bound_terrain(**{field: (f"{kind}:x1",)})
    with pytest.raises(ValidationError):
        bound_terrain(**{field: ("artifact:x1",)})


@pytest.mark.parametrize(
    "field", ["synthetic_identity_refs", "synthetic_credential_refs"]
)
def test_the_new_slots_refuse_secret_material(field):
    """A credential reference is a reference. The credential never travels.

    The slot exists because a presented terrain exposes synthetic credentials
    and a consumer needs to correlate them; it does not exist to carry one. A
    credential that travelled in a contract would be a real credential
    everywhere the contract went.
    """

    with pytest.raises(ValidationError):
        bound_terrain(**{field: ("credential:ghp_0123456789abcdef",)})
