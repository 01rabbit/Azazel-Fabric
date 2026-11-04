"""Knowledge Context semantic request/response profile (v1).

Fabric describes; it does not authenticate, sign, route, admit, infer or
enforce. This module fixes only the **semantic payload** exchanged between a
consumer adapter and a Knowledge provider, plus a deterministic canonical
serialization of that payload. A separate transport layer (outside Fabric) may
sign or authenticate the canonical bytes; nothing here carries credentials,
key identifiers, signatures, routes or network locations.

Trust posture:

* ``source_product``, ``provider_id`` and every ``*_ref`` are **claims**, used
  for correlation only. They are never authenticated identity.
* Every free-text field is untrusted data. It is bounded and must be printable,
  but its meaning is not policed here.
* A ``SourceReportedFact`` says "a source reported this"; it does not say it is
  true. An ``InferenceClaim`` is a different type and must cite the facts it
  rests on. Neither carries authority: the response is ``advisory_only``.
* ``expires_at`` is the *semantic* freshness bound of the snapshot answer. It is
  not transport expiry and Fabric never consults a clock.

Pure functions only: no clock, no filesystem, no network, no randomness.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    model_validator,
)

from azazel_fabric.mio_contracts.validation import (
    assert_bounded_mio_payload,
    assert_no_mio_directives,
)

REQUEST_SCHEMA_VERSION = "knowledge-context-request/v1"
RESPONSE_SCHEMA_VERSION = "knowledge-context-response/v1"
ADVISORY_AUTHORITY = "advisory_only"

# Structural bounds. Counts are per list; lengths are in characters.
MAX_ID_LENGTH = 128
MAX_PRODUCT_LENGTH = 64
MAX_TOKEN_LENGTH = 64
MAX_REF_LENGTH = 256
MAX_ENTITY_VALUE_LENGTH = 256
MAX_TEXT_LENGTH = 512
MAX_ENTITIES = 32
MAX_FACTS = 64
MAX_INFERENCES = 32
MAX_PROVENANCE_REFS = 8
MAX_METHOD_REFS = 8
MAX_BASIS_FACTS = 16
MAX_UNKNOWNS = 16
MAX_LIMITATIONS = 16

_IDENT_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.:/@+\-]*")
_ISO_WITH_OFFSET_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})"
)


def _check_ident(value: str) -> str:
    if not _IDENT_RE.fullmatch(value):
        raise ValueError(
            "identifier must match [A-Za-z0-9_][A-Za-z0-9_.:/@+\\-]*"
        )
    return value


def _check_printable(value: str) -> str:
    if not all(ch.isprintable() for ch in value):
        raise ValueError("text must not contain control or invisible characters")
    return value


def _check_opaque_ref(value: str) -> str:
    if "://" in value:
        raise ValueError("opaque reference must not contain the URL delimiter '://'")
    return value


def _ident(max_length: int) -> Any:
    return Annotated[
        str,
        StringConstraints(strict=True, min_length=1, max_length=max_length),
        AfterValidator(_check_ident),
    ]


def _text(max_length: int) -> Any:
    return Annotated[
        str,
        StringConstraints(strict=True, min_length=1, max_length=max_length),
        AfterValidator(_check_printable),
    ]


Identifier = _ident(MAX_ID_LENGTH)
ProductName = _ident(MAX_PRODUCT_LENGTH)
Token = _ident(MAX_TOKEN_LENGTH)
OpaqueRef = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=MAX_REF_LENGTH),
    AfterValidator(_check_ident),
    AfterValidator(_check_opaque_ref),
]
EntityValue = _text(MAX_ENTITY_VALUE_LENGTH)
Text = _text(MAX_TEXT_LENGTH)


def _require_iso_with_offset(value: Any) -> Any:
    """No numeric or date-only coercion: a string must be a full instant with offset."""

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and _ISO_WITH_OFFSET_RE.fullmatch(value):
        iso_text = value[:-1] + "+00:00" if value.endswith("Z") else value
        fraction = re.search(r"\.([0-9]{1,6})(?=(?:Z|[+-][0-9]{2}:[0-9]{2})$)", value)
        if fraction:
            padded = fraction.group(1).ljust(6, "0")
            iso_text = (
                value[: fraction.start()]
                + "."
                + padded
                + value[fraction.end() :]
            )
            if iso_text.endswith("Z"):
                iso_text = iso_text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(iso_text)
    else:
        raise ValueError("timestamp must be an ISO 8601 date-time with an explicit UTC offset")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    try:
        parsed.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("timestamp is outside the supported UTC range") from exc
    return value


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    utc = value.astimezone(timezone.utc)
    text = utc.isoformat(timespec="microseconds" if utc.microsecond else "seconds")
    return text[: -len("+00:00")] + "Z"


Instant = Annotated[
    AwareDatetime,
    BeforeValidator(_require_iso_with_offset),
    PlainSerializer(_utc_text, return_type=str, when_used="json"),
]


def _keys_only(value: Any, depth: int = 0) -> Any:
    """Skeleton of ``value`` that keeps mapping keys and drops leaf values."""

    if depth > 8:
        raise ValueError("knowledge-context payload exceeds maximum nesting depth")
    if isinstance(value, Mapping):
        return {key: _keys_only(child, depth + 1) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_keys_only(child, depth + 1) for child in value]
    return None


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class _DirectiveGuarded(_StrictFrozenModel):
    @model_validator(mode="before")
    @classmethod
    def _reject_directive_shaped_fields(cls, data: Any) -> Any:
        if isinstance(data, Mapping):
            assert_no_mio_directives(_keys_only(data))
        return data


class EntityRef(_StrictFrozenModel):
    """A bounded reference to something the consumer asks about. Data, not a locator to fetch."""

    entity_type: Token
    value: EntityValue


class KnowledgeContextRequestV1(_DirectiveGuarded):
    """Consumer adapter -> Knowledge provider. Carries no raw event, frame or metadata map."""

    schema_version: Literal["knowledge-context-request/v1"]
    request_id: Identifier
    correlation_id: Identifier
    source_product: ProductName
    source_ref: OpaqueRef
    requested_at: Instant
    entities: tuple[EntityRef, ...] = Field(min_length=1, max_length=MAX_ENTITIES)

    @model_validator(mode="after")
    def _entities_are_distinct(self) -> "KnowledgeContextRequestV1":
        keys = [(e.entity_type, e.value) for e in self.entities]
        if len(set(keys)) != len(keys):
            raise ValueError("entities must not repeat")
        assert_bounded_mio_payload(self.model_dump(mode="json"))
        return self


class SnapshotInfo(_StrictFrozenModel):
    """Which knowledge snapshot answered, what condition it was in, and as of when."""

    ref: OpaqueRef
    # An unavailable provider has no response envelope. Consumers represent
    # that transport outcome outside this semantic success payload.
    state: Literal["complete", "partial", "stale"]
    as_of: Instant


class SourceReportedFact(_StrictFrozenModel):
    """A statement a source reported. Not verified truth; provenance is a bounded reference list."""

    claim_class: Literal["source_reported_fact"] = "source_reported_fact"
    fact_id: Identifier
    subject: EntityRef
    predicate: Token
    value: Text
    provenance: tuple[OpaqueRef, ...] = Field(min_length=1, max_length=MAX_PROVENANCE_REFS)

    @model_validator(mode="after")
    def _provenance_is_distinct(self) -> "SourceReportedFact":
        if len(set(self.provenance)) != len(self.provenance):
            raise ValueError("provenance refs must not repeat")
        return self


class InferenceClaim(_StrictFrozenModel):
    """A provider's inference. Cites method references and the fact IDs it rests on."""

    claim_class: Literal["inference"] = "inference"
    inference_id: Identifier
    subject: EntityRef
    statement: Text
    method_refs: tuple[OpaqueRef, ...] = Field(min_length=1, max_length=MAX_METHOD_REFS)
    basis_fact_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=MAX_BASIS_FACTS)

    @model_validator(mode="after")
    def _basis_is_distinct(self) -> "InferenceClaim":
        if len(set(self.basis_fact_ids)) != len(self.basis_fact_ids):
            raise ValueError("basis_fact_ids must not repeat")
        if len(set(self.method_refs)) != len(self.method_refs):
            raise ValueError("method_refs must not repeat")
        return self


class KnowledgeContextResponseV1(_DirectiveGuarded):
    """Knowledge provider -> consumer adapter. Advisory only; every claim is untrusted data."""

    schema_version: Literal["knowledge-context-response/v1"]
    request_id: Identifier
    correlation_id: Identifier
    source_product: ProductName
    source_ref: OpaqueRef
    provider_id: Identifier
    snapshot: SnapshotInfo
    facts: tuple[SourceReportedFact, ...] = Field(max_length=MAX_FACTS)
    inferences: tuple[InferenceClaim, ...] = Field(max_length=MAX_INFERENCES)
    unknowns: tuple[Text, ...] = Field(max_length=MAX_UNKNOWNS)
    limitations: tuple[Text, ...] = Field(max_length=MAX_LIMITATIONS)
    generated_at: Instant
    expires_at: Instant
    authority: Literal["advisory_only"] = "advisory_only"

    @model_validator(mode="after")
    def _references_and_window(self) -> "KnowledgeContextResponseV1":
        fact_ids = [fact.fact_id for fact in self.facts]
        inference_ids = [item.inference_id for item in self.inferences]
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("duplicate fact_id")
        if len(set(inference_ids)) != len(inference_ids):
            raise ValueError("duplicate inference_id")
        if set(fact_ids) & set(inference_ids):
            raise ValueError("fact_id and inference_id share an identifier")
        known = set(fact_ids)
        for item in self.inferences:
            dangling = [ref for ref in item.basis_fact_ids if ref not in known]
            if dangling:
                raise ValueError(
                    f"inference {item.inference_id!r} cites unknown fact_id(s): {dangling}"
                )
        if self.snapshot.as_of > self.generated_at:
            raise ValueError("snapshot.as_of must not be later than generated_at")
        if self.expires_at <= self.generated_at:
            raise ValueError("expires_at must be later than generated_at")
        assert_bounded_mio_payload(self.model_dump(mode="json"))
        return self


def _assert_exact_nested_model_types(
    payload: KnowledgeContextRequestV1 | KnowledgeContextResponseV1,
) -> None:
    """Reject model subclasses before serialization could omit their extra state."""

    if type(payload) is KnowledgeContextRequestV1:
        if any(type(entity) is not EntityRef for entity in payload.entities):
            raise TypeError("request entities must be exact EntityRef instances")
        return
    if type(payload) is KnowledgeContextResponseV1:
        if type(payload.snapshot) is not SnapshotInfo:
            raise TypeError("response snapshot must be an exact SnapshotInfo instance")
        if any(type(fact) is not SourceReportedFact for fact in payload.facts):
            raise TypeError("response facts must be exact SourceReportedFact instances")
        if any(type(item) is not InferenceClaim for item in payload.inferences):
            raise TypeError("response inferences must be exact InferenceClaim instances")
        subjects = [fact.subject for fact in payload.facts]
        subjects.extend(item.subject for item in payload.inferences)
        if any(type(subject) is not EntityRef for subject in subjects):
            raise TypeError("response claim subjects must be exact EntityRef instances")
        return
    raise TypeError("payload must be an exact Knowledge Context v1 model")


def canonical_knowledge_context_bytes(
    payload: KnowledgeContextRequestV1 | KnowledgeContextResponseV1,
) -> bytes:
    """Deterministic UTF-8 JSON for a semantic payload.

    Sorted keys, no insignificant whitespace, non-ASCII preserved, NaN refused,
    instants rendered in UTC with a ``Z`` suffix. The same validated payload
    always yields the same bytes. Fabric does not sign these bytes; a separate
    transport layer may.
    """

    payload_type = type(payload)
    if payload_type not in (KnowledgeContextRequestV1, KnowledgeContextResponseV1):
        raise TypeError("only Knowledge Context v1 request/response models can be canonicalized")
    _assert_exact_nested_model_types(payload)
    # Frozen models can still be copied with unvalidated updates or created via
    # model_construct; revalidate before these bytes are used for a signature.
    payload = payload_type.model_validate(payload.model_dump(mode="python"))
    return json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def assert_response_correlates(
    request: KnowledgeContextRequestV1,
    response: KnowledgeContextResponseV1,
) -> None:
    """Require a semantic response to belong to the exact request.

    This checks semantic correlation only. It does not authenticate a provider,
    verify a signature, or decide whether the response is currently fresh.
    """

    if type(request) is not KnowledgeContextRequestV1:
        raise TypeError("request must be a KnowledgeContextRequestV1")
    if type(response) is not KnowledgeContextResponseV1:
        raise TypeError("response must be a KnowledgeContextResponseV1")
    _assert_exact_nested_model_types(request)
    _assert_exact_nested_model_types(response)
    request = KnowledgeContextRequestV1.model_validate(request.model_dump(mode="python"))
    response = KnowledgeContextResponseV1.model_validate(response.model_dump(mode="python"))
    for field in ("request_id", "correlation_id", "source_product", "source_ref"):
        if getattr(request, field) != getattr(response, field):
            raise ValueError(f"response {field} does not match request")
    if response.generated_at < request.requested_at:
        raise ValueError("response.generated_at must not be earlier than request.requested_at")
    requested_entities = {(item.entity_type, item.value) for item in request.entities}
    for claim in (*response.facts, *response.inferences):
        subject = (claim.subject.entity_type, claim.subject.value)
        if subject not in requested_entities:
            raise ValueError("response claim subject was not requested")


__all__ = [
    "ADVISORY_AUTHORITY",
    "EntityRef",
    "InferenceClaim",
    "KnowledgeContextRequestV1",
    "KnowledgeContextResponseV1",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "SnapshotInfo",
    "SourceReportedFact",
    "assert_response_correlates",
    "canonical_knowledge_context_bytes",
]
