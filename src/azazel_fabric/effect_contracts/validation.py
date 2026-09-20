"""Validation helpers for the cross-series effect/outcome/terrain family (#15).

The recursive directive walk is reused from ``outcome_contracts.validation``
rather than re-implemented: one walk, one set of depth/size limits, one place
where a bypass would have to be introduced.
"""

from __future__ import annotations

from typing import Any, Sequence

from azazel_fabric.outcome_contracts.validation import (
    assert_bounded_fact_payload,
    assert_no_runtime_directives,
    canonical_fact_json,
)

__all__ = [
    "BANNED_EFFECT_AUTHORITY_FIELDS",
    "SECRET_MATERIAL_MARKERS",
    "assert_bounded_fact_payload",
    "assert_effect_chain_consistent",
    "assert_no_effect_authority_fields",
    "assert_no_runtime_directives",
    "assert_no_secret_material",
    "assert_observation_within_effect_window",
    "canonical_fact_json",
]


#: Concepts issue #15 names as belonging to owning products, never to Fabric.
#:
#: These are not merely "fields we dislike". Each one, if it were shared and
#: authoritative, would move a product decision into the contract layer:
#: belief modelling, council synthesis, counterfactual ranking, utility
#: scoring, doctrine acceptance, model confidence as probability, and
#: provider-specific execution.
BANNED_EFFECT_AUTHORITY_FIELDS = frozenset(
    {
        "must_apply",
        "apply_now",
        "activate_now",
        "auto_apply",
        "authorize",
        "authorized",
        "authorization",
        "enforce",
        "enforcement",
        "adversary_belief",
        "belief_state",
        "perceived_state",
        "counterfactual",
        "counterfactual_rank",
        "counterfactual_ranking",
        "utility_score",
        "initiative_score",
        "council_vote",
        "council_synthesis",
        "vote",
        "votes",
        "operator_doctrine_acceptance",
        "doctrine_acceptance",
        "model_confidence_probability",
        "confidence_probability",
        "tool_call",
        "tool_calls",
        "tc_command",
        "nft_command",
        "nftables_command",
        "docker_command",
        "kvm_command",
        "edr_command",
        "ranked_effects",
        "recommended_effect",
        "best_effect",
    }
)

#: Recognizable secret material. Defence in depth behind the structural
#: opacity of a typed ref, which already excludes newlines, slashes and
#: whitespace -- and therefore PEM blocks, paths and URLs.
#:
#: This list recognizes what it recognizes. It cannot tell that ``cred:hunter2``
#: is a password, and nothing at this layer can. The contract is that these
#: fields carry *references*; the marker scan catches the obvious violations of
#: it and says so loudly rather than silently accepting them.
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


def _normalized_key(raw: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in raw.strip())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def _walk_keys(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            if isinstance(raw_key, str):
                key = _normalized_key(raw_key)
                if key in BANNED_EFFECT_AUTHORITY_FIELDS:
                    location = ".".join((*path, raw_key))
                    raise ValueError(
                        f"product-owned authority concept is forbidden in a shared "
                        f"contract: {location}"
                    )
            _walk_keys(child, (*path, str(raw_key)))
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _walk_keys(child, (*path, str(index)))


def assert_no_effect_authority_fields(value: Any) -> None:
    """Reject the product-owned concepts of #15 anywhere in a payload.

    Applied recursively, so a future additive field cannot smuggle one in via
    a nested map -- the case issue #15 lists as "future schema field
    accidentally creates directive semantics".
    """

    _walk_keys(value)


def assert_no_secret_material(value: Any, *, field: str) -> None:
    """Reject recognizable secret material in a reference-only field."""

    if isinstance(value, str):
        for marker in SECRET_MATERIAL_MARKERS:
            if marker.lower() in value.lower():
                raise ValueError(
                    f"{field} carries recognizable secret material ({marker!r}); "
                    "presented-terrain fields carry opaque references only"
                )
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            assert_no_secret_material(item, field=field)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert_no_secret_material(key, field=field)
            assert_no_secret_material(item, field=field)


def assert_effect_chain_consistent(
    effect_ref: Any,
    observations: Sequence[Any] = (),
    envelope: Any | None = None,
    terrain: Any | None = None,
) -> None:
    """Every record in a chain must name the same trace and the same effect.

    This is the guard against a cross-trace or cross-tenant identifier
    collision producing a chain that validates field-by-field while describing
    two unrelated events.
    """

    expected_trace = effect_ref.trace_id
    expected_effect = effect_ref.effect_id

    for observation in observations:
        if observation.trace_id != expected_trace:
            raise ValueError("effect observation belongs to a different trace")
        if observation.effect_ref != expected_effect:
            raise ValueError("effect observation belongs to a different effect")

    if envelope is not None:
        if envelope.trace_id != expected_trace:
            raise ValueError("outcome envelope belongs to a different trace")
        if envelope.effect_ref not in (None, expected_effect):
            raise ValueError("outcome envelope belongs to a different effect")

    if terrain is not None:
        _assert_terrain_binds_to_effect(effect_ref, terrain)
        if envelope is not None and envelope.presentation_ref not in (
            None,
            terrain.presentation_id,
        ):
            raise ValueError("outcome envelope references a different presented terrain")


def _assert_terrain_binds_to_effect(effect_ref: Any, terrain: Any) -> None:
    """How a presented terrain is tied to the effect it was presented for.

    Two cases, and keeping them apart is the point (Fabric#51).

    **The effect names a decision.** The terrain names the same one. This is
    the rule that has always been here.

    **The effect names no decision** -- a shadow run, an observation, a record
    that claims nothing. Until `v0.9.0rc5` this compared the terrain's
    `activation_decision_ref` against the effect's `None` and therefore
    *always* raised: a `planned_shadow` effect, which is AZ-06's ordinary
    mode, could not be chained to a terrain at all. The fix is not to skip the
    comparison, which would leave the terrain attached to nothing. It is a
    binding of its own: the terrain names the effect and the incident, and
    both must match.

    What is still refused in that case is a terrain naming a decision. The
    effect has none, so whatever the terrain names is not the decision that
    activated it, and a chain that accepted it would be asserting an authority
    nobody exercised.

    The three failures raise three different messages on purpose. "A different
    decision", "a decision that does not exist", and "the binding is missing"
    lead to three different corrections, and a caller told only that the chain
    is inconsistent has to work out which.
    """

    if effect_ref.decision_ref is not None:
        if terrain.activation_decision_ref is None:
            raise ValueError(
                "the effect names a decision and the presented terrain names "
                "none; a terrain activated by a decision must say which"
            )
        if terrain.activation_decision_ref != effect_ref.decision_ref:
            raise ValueError(
                "presented terrain was activated by a different decision than the effect"
            )
    else:
        if terrain.activation_decision_ref is not None:
            raise ValueError(
                "presented terrain names an activation decision but the effect "
                "has none; the effect claims "
                f"{effect_ref.authority_class.value!r}, so the named decision "
                "did not activate this terrain"
            )
        if terrain.source_effect_ref is None:
            raise ValueError(
                "the effect names no decision, so the presented terrain must "
                "bind to it through source_effect_ref and trace_id; it carries "
                "neither, and a terrain bound to nothing is not a chain"
            )

    # Checked whenever the terrain supplies it, in both cases. Optional on a
    # decision-activated terrain so that a producer pinned to `v0.9.0rc4`
    # keeps working; when it is there it is checked, because a trace that is
    # carried and not compared is a field that reads as a guarantee.
    if terrain.trace_id is not None and terrain.trace_id != effect_ref.trace_id:
        raise ValueError("presented terrain belongs to a different trace")
    # Likewise `source_effect_ref`, and in one place rather than two. It was
    # written twice -- once in the decision-less branch and once here -- and a
    # mutation removing the branch copy changed nothing, because this one
    # still caught it. A check duplicated is a check whose removal is
    # invisible, so only the general one is kept: it covers the
    # decision-bearing case too, where a terrain may name the effect and must
    # then name the right one.
    if (
        terrain.source_effect_ref is not None
        and terrain.source_effect_ref != effect_ref.effect_id
    ):
        raise ValueError("presented terrain was presented for a different effect")


def assert_observation_within_effect_window(effect_ref: Any, observation: Any) -> None:
    """A replayed observation must not be able to report an expired effect live.

    An ``EffectObservation`` arriving after the effect's ``expires_at`` may
    report that the effect ended; it may not report that it is running. Without
    this, replaying a stale ``active`` observation is enough to make a consumer
    believe a bounded environment is still up -- which is how a time-boxed
    effect silently becomes an unbounded one.
    """

    from .models import parse_timestamp

    live_states = {"started", "active"}
    if observation.status not in live_states:
        return
    observed = parse_timestamp(observation.observed_at, field="observed_at")
    expires = parse_timestamp(effect_ref.expires_at, field="expires_at")
    if observed > expires:
        raise ValueError(
            f"observation at {observation.observed_at} reports status "
            f"{observation.status!r} after the effect expired at "
            f"{effect_ref.expires_at}; a stale observation cannot prolong an effect"
        )
