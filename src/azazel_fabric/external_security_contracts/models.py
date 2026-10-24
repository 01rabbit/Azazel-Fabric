"""Descriptive external-security contracts (Fabric#25). **Experimental.**

Four records, each with one owner and one meaning (see
``docs/adr/0001-external-security-contract-ownership.md``):

``ExternalObservationEnvelope/v0.1``
    A fact an external EDR, firewall, router, switch, DNS system, NDR, SIEM,
    asset or vulnerability system observed, normalized into a bounded
    projection. ``authority_class`` is pinned ``observed_fact``.
``AdvisoryContextEnvelope/v0.1``
    Knowledge's advice about such facts. ``advisory_only``, never executable,
    and its recommended actions are a closed advisory vocabulary that cannot
    carry a command, a rule, a target locator, an override or an execute flag.
``ExposureChangeProposal/v0.1``
    A bounded, reviewable request to expose, redirect, withdraw or observe a
    deception surface through an owning product's adapter. ``proposal_only``:
    not an approval and not a command. Its ``decision_ref`` is opaque and is
    validated only by the owning Edge/Nexus or external change process.
``DeviceChangeObservation/v0.1``
    What a device adapter observed after a separately approved action. Its
    status vocabulary distinguishes requested / accepted_by_device / applied /
    observed / released / failed / stale / unknown, and **none of them means
    the change achieved anything**: ``tactical_outcome_claimed`` is pinned
    ``False``.

Signatures and mTLS identity, recorded in :class:`ExternalProvenance`, prove
transport origin and integrity only. ``confers_authority`` is pinned ``False``.

This family is **experimental** (Fabric#23 program decision): it has no real
producer or consumer yet, makes no compatibility promise, and is outside the
R1c stable gate. It is also optional -- nothing else in Fabric imports it.
"""

from __future__ import annotations

import re
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from azazel_fabric.external_security_contracts.validation import (
    FACT_PROJECTION_MAX_BYTES,
    FACT_PROJECTION_MAX_DEPTH,
    FACT_PROJECTION_MAX_ITEMS,
    VENDOR_EXTENSION_MAX_BYTES,
    VENDOR_EXTENSION_MAX_COUNT,
    VENDOR_EXTENSION_MAX_DEPTH,
    VENDOR_EXTENSION_MAX_ITEMS,
    assert_bounded_opaque,
    assert_free_text,
    assert_identity_name,
    assert_no_external_security_directives,
    assert_no_locator_values,
    assert_no_secret_material,
    assert_no_target_locators,
    assert_opaque_map,
    assert_tenant_confined,
    assert_version,
    canonical_digest,
    is_reserved_key,
    is_sha256_digest,
    parse_ref,
    parse_timestamp,
    require_ref_kind,
)

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

#: What kind of fact an external system observed. Closed. ``unknown`` is the
#: landing place for anything else and is the *weakest* reading: it is not a
#: fact class Fabric maps to any defensive state, effect, or containment.
FactClass = Literal[
    "endpoint_process",
    "endpoint_file",
    "network_flow",
    "network_policy_event",
    "dns_event",
    "identity_event",
    "asset_posture",
    "vulnerability_posture",
    "siem_case",
    "unknown",
]
FACT_CLASSES: tuple[str, ...] = get_args(FactClass)
UNKNOWN_FACT_CLASS = "unknown"

#: What kind of external system produced the fact.
SourceSystemClass = Literal[
    "edr",
    "firewall",
    "router",
    "switch",
    "dns",
    "ndr",
    "siem",
    "asset_inventory",
    "vulnerability_scanner",
    "unknown",
]

#: Closed and policy-evaluable. A consumer rejects or sanitizes a class it is
#: not admitted to receive (``assert_privacy_admitted``).
PrivacyClass = Literal["public", "internal", "sensitive", "restricted"]

FreshnessState = Literal["fresh", "aging", "stale", "unknown"]

ConfidenceBand = Literal["low", "moderate", "high", "unknown"]

#: Closed advisory action vocabulary. Each value names something a product's
#: own authority may *consider*; none names an action Fabric or Knowledge
#: performs, and none is a DefensiveState or EffectClass value.
AdvisoryActionClass = Literal[
    "observe_more",
    "notify_operator",
    "review_exposure",
    "review_containment",
    "review_deception_redirect",
    "review_rate_limit",
    "no_change",
]

RecommendedObservationClass = Literal[
    "collect_telemetry",
    "watch_subject",
    "correlate_sources",
    "verify_coverage",
]

#: What an exposure proposal asks the owning product's adapter to do with a
#: deception surface. Deliberately not ``redirect``/``observe``: those spell
#: ``DefensiveState`` members, and a proposal value must never read as one.
ExposureEffect = Literal[
    "observe_deception_surface",
    "expose_deception_surface",
    "redirect_to_deception_surface",
    "withdraw_deception_surface",
]
EXPOSURE_EFFECTS: tuple[str, ...] = get_args(ExposureEffect)
#: The effect that does least. Where a consumer's display of an unreadable
#: effect lands; the model itself refuses an unknown effect outright.
WEAKEST_EXPOSURE_EFFECT = "observe_deception_surface"

#: Effects that put something in front of an adversary and so must be
#: rolled back when the proposal expires or the change fails.
_EXPOSING_EFFECTS = frozenset({"expose_deception_surface", "redirect_to_deception_surface"})

SafetyConstraint = Literal[
    "no_production_access",
    "no_outbound_egress",
    "bounded_duration",
    "operator_visible",
    "isolation_verified_before_exposure",
    "synthetic_content_only",
]

RollbackTrigger = Literal["on_expiry", "on_failure", "on_withdraw", "on_stale_observation"]

#: What a device adapter saw. None of these implies tactical success.
DeviceChangeStatus = Literal[
    "requested",
    "accepted_by_device",
    "applied",
    "observed",
    "released",
    "failed",
    "stale",
    "unknown",
]
DEVICE_CHANGE_STATUSES: tuple[str, ...] = get_args(DeviceChangeStatus)
UNKNOWN_DEVICE_CHANGE_STATUS = "unknown"

ProvenanceRole = Literal["observed", "received", "normalized", "inferred", "proposed", "reported", "relayed"]

#: Ref kinds that are never a decision. A proposal's ``decision_ref`` must be
#: typed ``decision:``; these are refused by name so the error says what the
#: value was mistaken for.
_NOT_A_DECISION_KINDS = frozenset(
    {"environment", "lifecycle", "presentation", "advisory", "proposal", "effect", "surface"}
)

#: The longest window an exposure proposal may describe. A proposal is a
#: bounded request; one that ran for a month would be a standing policy.
MAX_PROPOSAL_WINDOW_SECONDS = 7 * 24 * 3600

_NAMESPACE = re.compile(r"[a-z][a-z0-9-]{0,31}(?:\.[a-z0-9][a-z0-9-]{0,31}){1,3}")


def _coerce(raw: object, vocabulary: tuple[str, ...], fallback: str) -> tuple[str, bool]:
    if isinstance(raw, str) and raw in vocabulary:
        return raw, True
    return fallback, False


def coerce_fact_class(raw: object) -> tuple[str, bool]:
    """``(fact_class, recognized)``. Anything unrecognized is ``unknown``."""

    return _coerce(raw, FACT_CLASSES, UNKNOWN_FACT_CLASS)


def coerce_device_change_status(raw: object) -> tuple[str, bool]:
    """``(status, recognized)``. Anything unrecognized is ``unknown``."""

    return _coerce(raw, DEVICE_CHANGE_STATUSES, UNKNOWN_DEVICE_CHANGE_STATUS)


def coerce_exposure_effect(raw: object) -> tuple[str, bool]:
    """``(effect, recognized)``. Anything unrecognized is the weakest effect.

    For display only. :class:`ExposureChangeProposal` refuses an unknown
    effect, because a proposal nobody can read must not be considered at all.
    """

    return _coerce(raw, EXPOSURE_EFFECTS, WEAKEST_EXPOSURE_EFFECT)


# Per-slot ref-kind allowlists. A ref's kind must be one of its slot's kinds,
# and its body is ``[a-z0-9][a-z0-9_-]*`` (validation._TYPED_REF): hostnames,
# addresses, URLs, paths and encoded forms cannot be refs at all.
SUBJECT_REF_KINDS = frozenset(
    {"asset", "account", "user", "identity", "process", "file", "flow", "service", "vulnerability", "case"}
)
EVIDENCE_REF_KINDS = frozenset({"evidence", "artifact"})
FACT_REF_KINDS = frozenset({"fact"})
CORRELATION_REF_KINDS = frozenset(
    {"external_observation", "advisory", "proposal", "device_observation", "evidence", "trace"}
)

_LABEL = re.compile(r"[A-Za-z0-9_.-]{1,128}")


def _label(raw: object) -> str:
    """The source's own label, kept only if it is representable as one."""

    if isinstance(raw, str) and _LABEL.fullmatch(raw[:128]):
        return raw[:128]
    return "unrepresentable"


def _require_typed(values: tuple[str, ...], *, field: str, kinds: frozenset[str]) -> None:
    for value in values:
        require_ref_kind(value, kinds, field=field)


def _free_texts(values: Any, *, field: str, command_words: bool = False) -> None:
    if isinstance(values, str):
        values = (values,)
    for index, text in enumerate(values):
        assert_free_text(text, field=f"{field}.{index}", command_words=command_words)


def _require_unique(values: tuple[str, ...], *, field: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{field} repeats an entry")


def _window(start: str, end: str, *, start_field: str, end_field: str, strict: bool) -> float:
    begin = parse_timestamp(start, field=start_field)
    finish = parse_timestamp(end, field=end_field)
    if finish < begin or (strict and finish == begin):
        raise ValueError(f"{end_field} must be after {start_field}")
    return (finish - begin).total_seconds()


class _Descriptive(BaseModel):
    """Base for every record here: closed, immutable, describe-only."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Shared parts
# ---------------------------------------------------------------------------


class EventWindow(_Descriptive):
    """The interval a fact or a device observation covers."""

    schema_version: Literal["external-event-window/v0.1"] = "external-event-window/v0.1"
    start: str = Field(min_length=1, max_length=64)
    end: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _validate(self) -> "EventWindow":
        _window(self.start, self.end, start_field="start", end_field="end", strict=False)
        return self


class FreshnessStatement(_Descriptive):
    """How fresh the producer says the record is, and until when.

    The producer's statement, not a consumer verdict: a consumer compares
    ``stale_after`` against its own clock (``assert_not_expired``-style), and
    Fabric never reads one.
    """

    schema_version: Literal["external-freshness/v0.1"] = "external-freshness/v0.1"
    state: FreshnessState
    as_of: str = Field(min_length=1, max_length=64)
    stale_after: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _validate(self) -> "FreshnessStatement":
        _window(self.as_of, self.stale_after, start_field="as_of", end_field="stale_after", strict=True)
        return self


class TelemetryCoverage(_Descriptive):
    """What the producer could see. Replaces any notion of "success".

    ``coverage_complete`` is required and never inferred from an empty gap
    list. Incomplete coverage must name its gaps; complete coverage may not
    name any, and may not report fewer sources than it expected. Telemetry
    loss therefore cannot serialize as a clean result.
    """

    schema_version: Literal["external-telemetry-coverage/v0.1"] = "external-telemetry-coverage/v0.1"
    coverage_complete: StrictBool
    gaps: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    sources_expected: StrictInt | None = Field(default=None, ge=0)
    sources_reporting: StrictInt | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate(self) -> "TelemetryCoverage":
        _free_texts(self.gaps, field="gaps")
        if not self.coverage_complete and not self.gaps:
            raise ValueError(
                "incomplete coverage must name its gaps; unnamed telemetry loss is how "
                "a partial observation reads as a whole one"
            )
        if self.coverage_complete and self.gaps:
            raise ValueError("coverage cannot be complete and also name gaps")
        if (
            self.sources_expected is not None
            and self.sources_reporting is not None
            and self.sources_reporting > self.sources_expected
        ):
            raise ValueError("sources_reporting cannot exceed sources_expected")
        if self.coverage_complete and (
            self.sources_expected is None
            or self.sources_reporting is None
            or self.sources_reporting < 1
        ):
            raise ValueError(
                "complete coverage must state how many sources were expected and "
                "reported, and at least one must have reported; 'complete' with "
                "nothing reporting is telemetry loss serialized as a clean result"
            )
        if (
            self.coverage_complete
            and self.sources_reporting is not None
            and self.sources_expected is not None
            and self.sources_reporting < self.sources_expected
        ):
            raise ValueError(
                "coverage claims to be complete while fewer sources reported than "
                "were expected"
            )
        return self


class ProvenanceHop(_Descriptive):
    """One product/node that handled the record, in order."""

    schema_version: Literal["external-provenance-hop/v0.1"] = "external-provenance-hop/v0.1"
    product: str = Field(min_length=1, max_length=64)
    node_ref: str = Field(min_length=1, max_length=256)
    product_version: str = Field(min_length=1, max_length=64)
    tenant_ref: str = Field(min_length=1, max_length=256)
    role: ProvenanceRole
    at: str = Field(min_length=1, max_length=64)
    #: The mTLS / transport identity the hop presented, as an opaque ref. It
    #: says who sent the bytes. It does not say anyone may act on them.
    transport_identity_ref: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def _validate(self) -> "ProvenanceHop":
        assert_identity_name(self.product, field="product")
        assert_version(self.product_version, field="product_version")
        require_ref_kind(self.node_ref, "node", field="node_ref")
        require_ref_kind(self.tenant_ref, "tenant", field="tenant_ref")
        if self.transport_identity_ref is not None:
            require_ref_kind(self.transport_identity_ref, "transport", field="transport_identity_ref")
        parse_timestamp(self.at, field="at")
        return self


class ExternalProvenance(_Descriptive):
    """The provenance chain. Origin and integrity, never authority.

    ``signature_ref`` names a detached signature over the canonical bytes.
    Verifying it is the consumer's business and proves who produced the
    record; ``confers_authority`` is pinned ``False`` so that the presence of a
    signature or an mTLS identity can never be read as authorization.
    """

    schema_version: Literal["external-provenance/v0.1"] = "external-provenance/v0.1"
    chain: tuple[ProvenanceHop, ...] = Field(min_length=1, max_length=16)
    signature_ref: str | None = Field(default=None, max_length=256)
    confers_authority: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "ExternalProvenance":
        if self.signature_ref is not None:
            require_ref_kind(self.signature_ref, "signature", field="signature_ref")
        instants = [parse_timestamp(hop.at, field="at") for hop in self.chain]
        if instants != sorted(instants):
            raise ValueError("provenance chain hops must be in time order")
        return self


class VendorExtension(_Descriptive):
    """Vendor-specific detail, confined and bound to a digest.

    The envelope carries a bounded normalized projection; anything vendor
    specific goes here instead, under a dotted namespace, with hard limits on
    depth, cardinality and size, and with ``body_digest`` equal to the
    canonical digest of ``body``. It may not reuse a key whose meaning the
    envelope owns (``authority_class``, ``executable``, ``decision_ref``...),
    and the record-wide directive and secret guards walk it like any other
    field. Raw, unbounded vendor payload never travels: ``evidence_ref`` points
    at it instead.
    """

    schema_version: Literal["external-vendor-extension/v0.1"] = "external-vendor-extension/v0.1"
    namespace: str = Field(min_length=3, max_length=131)
    body: dict[str, Any] = Field(default_factory=dict)
    body_digest: str = Field(min_length=1, max_length=80)
    evidence_ref: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def _validate(self) -> "VendorExtension":
        if _NAMESPACE.fullmatch(self.namespace) is None:
            raise ValueError(f"namespace {self.namespace!r} must be dotted lower-case (vendor.product)")
        assert_bounded_opaque(
            self.body,
            max_depth=VENDOR_EXTENSION_MAX_DEPTH,
            max_items=VENDOR_EXTENSION_MAX_ITEMS,
            max_bytes=VENDOR_EXTENSION_MAX_BYTES,
            what=f"vendor extension {self.namespace!r}",
        )
        _reject_reserved_keys(self.body, namespace=f"vendor extension {self.namespace!r}")
        assert_opaque_map(self.body, what=f"vendor extension {self.namespace!r}")
        if not is_sha256_digest(self.body_digest):
            raise ValueError("body_digest must be a sha256:<64 hex> digest")
        if canonical_digest(self.body) != self.body_digest:
            raise ValueError(
                f"vendor extension {self.namespace!r} body does not match body_digest"
            )
        if self.evidence_ref is not None:
            require_ref_kind(self.evidence_ref, EVIDENCE_REF_KINDS, field="evidence_ref")
        return self


def _reject_reserved_keys(value: Any, *, namespace: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if is_reserved_key(key):
                raise ValueError(
                    f"{namespace} reuses the reserved key {key!r}; an opaque map "
                    "cannot restate what the envelope owns"
                )
            _reject_reserved_keys(child, namespace=namespace)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_reserved_keys(child, namespace=namespace)


def _check_extensions(extensions: tuple[VendorExtension, ...]) -> None:
    if len(extensions) > VENDOR_EXTENSION_MAX_COUNT:
        raise ValueError(f"at most {VENDOR_EXTENSION_MAX_COUNT} vendor extensions")
    _require_unique(tuple(ext.namespace for ext in extensions), field="vendor_extensions.namespace")


class _Envelope(_Descriptive):
    """Identity, tenancy and provenance every record of this family carries."""

    producer_product: str = Field(min_length=1, max_length=64)
    producer_node_ref: str = Field(min_length=1, max_length=256)
    producer_version: str = Field(min_length=1, max_length=64)
    tenant_ref: str = Field(min_length=1, max_length=256)
    privacy_class: PrivacyClass
    provenance: ExternalProvenance

    def _check_envelope(self, *, forbid_target_locators: bool) -> None:
        payload = self.model_dump(mode="json")
        assert_no_external_security_directives(payload)
        assert_no_secret_material(payload)
        if forbid_target_locators:
            assert_no_target_locators(payload)
            assert_no_locator_values(payload)
        assert_identity_name(self.producer_product, field="producer_product")
        assert_version(self.producer_version, field="producer_version")
        require_ref_kind(self.producer_node_ref, "node", field="producer_node_ref")
        require_ref_kind(self.tenant_ref, "tenant", field="tenant_ref")
        assert_tenant_confined(payload, self.tenant_ref)
        last = self.provenance.chain[-1]
        if last.product != self.producer_product or last.node_ref != self.producer_node_ref:
            raise ValueError(
                "the last provenance hop must be the producer itself; a chain that "
                "ends elsewhere does not say who produced this record"
            )


# ---------------------------------------------------------------------------
# ExternalObservationEnvelope/v0.1
# ---------------------------------------------------------------------------


class ExternalObservationEnvelope(_Envelope):
    """A fact an external security system observed. Never a request."""

    schema_version: Literal["external-observation-envelope/v0.1"] = (
        "external-observation-envelope/v0.1"
    )
    observation_id: str = Field(min_length=1, max_length=256)
    source_system: SourceSystemClass
    source_product_version: str = Field(min_length=1, max_length=64)
    source_event_ref: str = Field(min_length=1, max_length=256)
    trace_ref: str | None = Field(default=None, max_length=256)
    observed_at: str = Field(min_length=1, max_length=64)
    received_at: str = Field(min_length=1, max_length=64)
    fact_class: FactClass
    #: The source's own label when it did not map onto the closed vocabulary.
    #: Kept so nothing is lost; never read as a fact class.
    source_fact_label: str | None = Field(default=None, max_length=128)
    subject_refs: tuple[str, ...] = Field(min_length=1, max_length=64)
    event_window: EventWindow
    #: Digest of the raw vendor payload, which does not travel.
    payload_digest: str = Field(min_length=1, max_length=80)
    #: Bounded normalized projection of the fact.
    normalized_fact: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    freshness: FreshnessStatement
    telemetry_coverage: TelemetryCoverage
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    vendor_extensions: tuple[VendorExtension, ...] = Field(default_factory=tuple)
    authority_class: Literal["observed_fact"] = "observed_fact"
    executable: Literal[False] = False

    @model_validator(mode="before")
    @classmethod
    def _unknown_fact_stays_unknown(cls, data: Any) -> Any:
        if isinstance(data, dict) and "fact_class" in data:
            fact_class, recognized = coerce_fact_class(data["fact_class"])
            if not recognized:
                data = dict(data)
                raw = data["fact_class"]
                data["fact_class"] = fact_class
                if data.get("source_fact_label") is None:
                    data["source_fact_label"] = _label(raw)
        return data

    @model_validator(mode="after")
    def _validate(self) -> "ExternalObservationEnvelope":
        self._check_envelope(forbid_target_locators=False)
        require_ref_kind(self.observation_id, "external_observation", field="observation_id")
        require_ref_kind(self.source_event_ref, "source_event", field="source_event_ref")
        if self.trace_ref is not None:
            require_ref_kind(self.trace_ref, "trace", field="trace_ref")
        _require_typed(self.subject_refs, field="subject_refs", kinds=SUBJECT_REF_KINDS)
        _require_unique(self.subject_refs, field="subject_refs")
        _require_typed(self.evidence_refs, field="evidence_refs", kinds=EVIDENCE_REF_KINDS)
        if not is_sha256_digest(self.payload_digest):
            raise ValueError("payload_digest must be a sha256:<64 hex> digest")
        _window(self.observed_at, self.received_at, start_field="observed_at", end_field="received_at", strict=False)
        if parse_timestamp(self.event_window.end, field="event_window.end") > parse_timestamp(
            self.received_at, field="received_at"
        ):
            raise ValueError("event_window ends after the envelope was received")
        assert_bounded_opaque(
            self.normalized_fact,
            max_depth=FACT_PROJECTION_MAX_DEPTH,
            max_items=FACT_PROJECTION_MAX_ITEMS,
            max_bytes=FACT_PROJECTION_MAX_BYTES,
            what="normalized_fact",
        )
        _reject_reserved_keys(self.normalized_fact, namespace="normalized_fact")
        assert_opaque_map(self.normalized_fact, what="normalized_fact")
        assert_version(self.source_product_version, field="source_product_version")
        _free_texts(self.limitations, field="limitations")
        if self.source_fact_label is not None and _LABEL.fullmatch(self.source_fact_label) is None:
            raise ValueError("source_fact_label must match [A-Za-z0-9_.-]{1,128}")
        _check_extensions(self.vendor_extensions)
        return self


# ---------------------------------------------------------------------------
# AdvisoryContextEnvelope/v0.1
# ---------------------------------------------------------------------------


class RecommendedObservation(_Descriptive):
    """Something the advisor suggests looking at. Not a collection order."""

    schema_version: Literal["external-recommended-observation/v0.1"] = (
        "external-recommended-observation/v0.1"
    )
    observation_class: RecommendedObservationClass
    subject_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=32)
    rationale: str = Field(min_length=1, max_length=1024)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=32)

    @model_validator(mode="after")
    def _validate(self) -> "RecommendedObservation":
        _require_typed(self.subject_refs, field="subject_refs", kinds=SUBJECT_REF_KINDS)
        _require_typed(self.evidence_refs, field="evidence_refs", kinds=EVIDENCE_REF_KINDS)
        return self


class RecommendedAction(_Descriptive):
    """An action a product's own authority may consider. Never a command.

    The vocabulary is closed; the only free text is rationale and constraints,
    and the record-wide guards refuse a command, rule body, target locator,
    override or execute flag anywhere in it.
    """

    schema_version: Literal["external-recommended-action/v0.1"] = (
        "external-recommended-action/v0.1"
    )
    action_class: AdvisoryActionClass
    rationale: str = Field(min_length=1, max_length=1024)
    constraints: tuple[str, ...] = Field(default_factory=tuple, max_length=16)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=32)

    @model_validator(mode="after")
    def _validate(self) -> "RecommendedAction":
        _require_typed(self.evidence_refs, field="evidence_refs", kinds=EVIDENCE_REF_KINDS)
        return self


class AdvisoryContextEnvelope(_Envelope):
    """Knowledge's advice for Edge/Nexus or an external consumer.

    ``advisory_only`` and ``executable=False`` are pinned. There is no
    ``decision_ref`` field to fill: advice that names a decision is how advice
    gets mistaken for one.
    """

    schema_version: Literal["advisory-context-envelope/v0.1"] = "advisory-context-envelope/v0.1"
    advisory_id: str = Field(min_length=1, max_length=256)
    trace_ref: str | None = Field(default=None, max_length=256)
    subject_refs: tuple[str, ...] = Field(min_length=1, max_length=64)
    generated_at: str = Field(min_length=1, max_length=64)
    expires_at: str = Field(min_length=1, max_length=64)
    source_fact_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    normalized_fact_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    inference_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    assessment_summary: str = Field(min_length=1, max_length=2048)
    confidence_band: ConfidenceBand
    recommended_observations: tuple[RecommendedObservation, ...] = Field(
        default_factory=tuple, max_length=32
    )
    recommended_actions: tuple[RecommendedAction, ...] = Field(default_factory=tuple, max_length=32)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    unknowns: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    freshness: FreshnessStatement
    authority_class: Literal["advisory_only"] = "advisory_only"
    executable: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "AdvisoryContextEnvelope":
        self._check_envelope(forbid_target_locators=True)
        require_ref_kind(self.advisory_id, "advisory", field="advisory_id")
        if self.trace_ref is not None:
            require_ref_kind(self.trace_ref, "trace", field="trace_ref")
        _require_typed(self.subject_refs, field="subject_refs", kinds=SUBJECT_REF_KINDS)
        _require_typed(self.source_fact_refs, field="source_fact_refs", kinds=frozenset({"external_observation"}))
        _require_typed(self.normalized_fact_refs, field="normalized_fact_refs", kinds=FACT_REF_KINDS)
        _require_typed(self.inference_refs, field="inference_refs", kinds=frozenset({"inference"}))
        if not self.source_fact_refs and not self.normalized_fact_refs:
            raise ValueError(
                "an advisory must cite the facts it is about; advice grounded in "
                "nothing is indistinguishable from an instruction"
            )
        _window(self.generated_at, self.expires_at, start_field="generated_at", end_field="expires_at", strict=True)
        _free_texts(self.assessment_summary, field="assessment_summary", command_words=True)
        _free_texts(self.limitations, field="limitations", command_words=True)
        _free_texts(self.unknowns, field="unknowns", command_words=True)
        for index, action in enumerate(self.recommended_actions):
            _free_texts(action.rationale, field=f"recommended_actions.{index}.rationale", command_words=True)
            _free_texts(action.constraints, field=f"recommended_actions.{index}.constraints", command_words=True)
        for index, observation in enumerate(self.recommended_observations):
            _free_texts(
                observation.rationale, field=f"recommended_observations.{index}.rationale", command_words=True
            )
        return self


# ---------------------------------------------------------------------------
# ExposureChangeProposal/v0.1
# ---------------------------------------------------------------------------


class RollbackRequirement(_Descriptive):
    """What must undo the change, and when. A requirement, not a plan."""

    schema_version: Literal["external-rollback-requirement/v0.1"] = (
        "external-rollback-requirement/v0.1"
    )
    required: StrictBool
    triggers: tuple[RollbackTrigger, ...] = Field(default_factory=tuple, max_length=4)
    max_rollback_seconds: StrictInt | None = Field(default=None, ge=1, le=86400)

    @model_validator(mode="after")
    def _validate(self) -> "RollbackRequirement":
        _require_unique(tuple(self.triggers), field="triggers")
        if self.required and (not self.triggers or self.max_rollback_seconds is None):
            raise ValueError("a required rollback must name its triggers and its time bound")
        if not self.required and (self.triggers or self.max_rollback_seconds is not None):
            raise ValueError("a rollback that is not required names no triggers or bound")
        return self


class ExposureChangeProposal(_Envelope):
    """A bounded, reviewable request about a deception surface. Not an approval.

    ``proposal_only`` and ``executable=False`` are pinned. ``decision_ref`` is
    an opaque ``decision:`` reference; Fabric checks only its shape, and its
    validity is verified only by the owning Edge/Nexus or external change
    process. An environment-lifecycle reference cannot stand in for it.
    Provider command syntax, credentials, rule bodies and device-specific
    object ids are refused anywhere in the record.
    """

    schema_version: Literal["exposure-change-proposal/v0.1"] = "exposure-change-proposal/v0.1"
    proposal_id: str = Field(min_length=1, max_length=256)
    trace_ref: str = Field(min_length=1, max_length=256)
    environment_ref: str = Field(min_length=1, max_length=256)
    decision_ref: str = Field(min_length=1, max_length=256)
    requested_effect: ExposureEffect
    target_scope_ref: str = Field(min_length=1, max_length=256)
    adapter_capability_ref: str = Field(min_length=1, max_length=256)
    not_before: str = Field(min_length=1, max_length=64)
    expires_at: str = Field(min_length=1, max_length=64)
    rollback_requirement: RollbackRequirement
    safety_constraints: tuple[SafetyConstraint, ...] = Field(min_length=1, max_length=8)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority_class: Literal["proposal_only"] = "proposal_only"
    executable: Literal[False] = False

    @model_validator(mode="after")
    def _validate(self) -> "ExposureChangeProposal":
        self._check_envelope(forbid_target_locators=True)
        require_ref_kind(self.proposal_id, "proposal", field="proposal_id")
        require_ref_kind(self.trace_ref, "trace", field="trace_ref")
        require_ref_kind(self.environment_ref, "environment", field="environment_ref")
        kind, _ = parse_ref(self.decision_ref)
        if kind in _NOT_A_DECISION_KINDS:
            raise ValueError(
                f"decision_ref is a {kind!r} reference; an environment or lifecycle "
                "identifier cannot replace the owning product's decision reference"
            )
        require_ref_kind(self.decision_ref, "decision", field="decision_ref")
        require_ref_kind(self.target_scope_ref, "scope", field="target_scope_ref")
        require_ref_kind(self.adapter_capability_ref, "capability", field="adapter_capability_ref")
        _require_typed(self.evidence_refs, field="evidence_refs", kinds=EVIDENCE_REF_KINDS)
        _require_unique(tuple(self.safety_constraints), field="safety_constraints")
        duration = _window(self.not_before, self.expires_at, start_field="not_before", end_field="expires_at", strict=True)
        if duration > MAX_PROPOSAL_WINDOW_SECONDS:
            raise ValueError(
                f"a proposal window of {int(duration)}s exceeds the "
                f"{MAX_PROPOSAL_WINDOW_SECONDS}s bound; a proposal is bounded"
            )
        if self.requested_effect in _EXPOSING_EFFECTS:
            rollback = self.rollback_requirement
            if not rollback.required or not {"on_expiry", "on_failure"} <= set(rollback.triggers):
                raise ValueError(
                    f"{self.requested_effect!r} puts a surface in front of an adversary "
                    "and must require rollback on_expiry and on_failure"
                )
            if "bounded_duration" not in self.safety_constraints:
                raise ValueError(f"{self.requested_effect!r} must carry the bounded_duration constraint")
        return self


# ---------------------------------------------------------------------------
# DeviceChangeObservation/v0.1
# ---------------------------------------------------------------------------


class DeviceChangeObservation(_Envelope):
    """What a device adapter observed after a separately approved action.

    A report, never a request, and never a success claim: no status here means
    the change achieved its tactical purpose, and ``tactical_outcome_claimed``
    is pinned ``False``. An unrecognized status lands on ``unknown``.
    """

    schema_version: Literal["device-change-observation/v0.1"] = "device-change-observation/v0.1"
    observation_id: str = Field(min_length=1, max_length=256)
    trace_ref: str = Field(min_length=1, max_length=256)
    decision_ref: str = Field(min_length=1, max_length=256)
    proposal_ref: str | None = Field(default=None, max_length=256)
    adapter_ref: str = Field(min_length=1, max_length=256)
    target_scope_ref: str = Field(min_length=1, max_length=256)
    status: DeviceChangeStatus
    source_status_label: str | None = Field(default=None, max_length=128)
    observed_at: str = Field(min_length=1, max_length=64)
    observation_window: EventWindow
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    correlation_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    telemetry_coverage: TelemetryCoverage
    confounders: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    failure_reason: str | None = Field(default=None, max_length=512)
    vendor_extensions: tuple[VendorExtension, ...] = Field(default_factory=tuple)
    authority_class: Literal["observed_fact"] = "observed_fact"
    executable: Literal[False] = False
    tactical_outcome_claimed: Literal[False] = False

    @model_validator(mode="before")
    @classmethod
    def _unknown_status_stays_unknown(cls, data: Any) -> Any:
        if isinstance(data, dict) and "status" in data:
            status, recognized = coerce_device_change_status(data["status"])
            if not recognized:
                data = dict(data)
                raw = data["status"]
                data["status"] = status
                if data.get("source_status_label") is None:
                    data["source_status_label"] = _label(raw)
        return data

    @model_validator(mode="after")
    def _validate(self) -> "DeviceChangeObservation":
        self._check_envelope(forbid_target_locators=False)
        require_ref_kind(self.observation_id, "device_observation", field="observation_id")
        require_ref_kind(self.trace_ref, "trace", field="trace_ref")
        kind, _ = parse_ref(self.decision_ref)
        if kind in _NOT_A_DECISION_KINDS:
            raise ValueError(f"decision_ref is a {kind!r} reference, not a decision")
        require_ref_kind(self.decision_ref, "decision", field="decision_ref")
        if self.proposal_ref is not None:
            require_ref_kind(self.proposal_ref, "proposal", field="proposal_ref")
        require_ref_kind(self.adapter_ref, "adapter", field="adapter_ref")
        require_ref_kind(self.target_scope_ref, "scope", field="target_scope_ref")
        _require_typed(self.evidence_refs, field="evidence_refs", kinds=EVIDENCE_REF_KINDS)
        _require_typed(self.correlation_refs, field="correlation_refs", kinds=CORRELATION_REF_KINDS)
        parse_timestamp(self.observed_at, field="observed_at")
        if parse_timestamp(self.observation_window.end, field="observation_window.end") > parse_timestamp(
            self.observed_at, field="observed_at"
        ):
            raise ValueError("observation_window ends after the observation was made")

        _free_texts(self.confounders, field="confounders")
        _free_texts(self.limitations, field="limitations")
        if self.failure_reason is not None:
            _free_texts(self.failure_reason, field="failure_reason")
        if self.source_status_label is not None and _LABEL.fullmatch(self.source_status_label) is None:
            raise ValueError("source_status_label must match [A-Za-z0-9_.-]{1,128}")
        if self.status == "failed" and not self.failure_reason:
            raise ValueError("a failed change must say why; an unexplained failure reads as a lost report")
        if self.status != "failed" and self.failure_reason is not None:
            raise ValueError("failure_reason is only meaningful for a failed change")
        if self.status == "observed" and not self.evidence_refs:
            raise ValueError("'observed' must cite the evidence it was observed in")
        if self.status in ("stale", "unknown") and not (self.limitations or self.source_status_label):
            raise ValueError(f"{self.status!r} must state its limitation or the source's own label")
        _check_extensions(self.vendor_extensions)
        return self


__all__ = [
    "AdvisoryActionClass",
    "AdvisoryContextEnvelope",
    "CORRELATION_REF_KINDS",
    "EVIDENCE_REF_KINDS",
    "FACT_REF_KINDS",
    "SUBJECT_REF_KINDS",
    "ConfidenceBand",
    "DEVICE_CHANGE_STATUSES",
    "DeviceChangeObservation",
    "DeviceChangeStatus",
    "EXPOSURE_EFFECTS",
    "EventWindow",
    "ExposureChangeProposal",
    "ExposureEffect",
    "ExternalObservationEnvelope",
    "ExternalProvenance",
    "FACT_CLASSES",
    "FactClass",
    "FreshnessState",
    "FreshnessStatement",
    "MAX_PROPOSAL_WINDOW_SECONDS",
    "PrivacyClass",
    "ProvenanceHop",
    "RecommendedAction",
    "RecommendedObservation",
    "RollbackRequirement",
    "SafetyConstraint",
    "SourceSystemClass",
    "TelemetryCoverage",
    "UNKNOWN_DEVICE_CHANGE_STATUS",
    "UNKNOWN_FACT_CLASS",
    "VendorExtension",
    "WEAKEST_EXPOSURE_EFFECT",
    "coerce_device_change_status",
    "coerce_exposure_effect",
    "coerce_fact_class",
]
