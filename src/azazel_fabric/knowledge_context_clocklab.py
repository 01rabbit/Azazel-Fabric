"""Explicit lab-only finite-clock contract. Stable v1 remains unchanged."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
from typing import Annotated, Literal

from pydantic import StringConstraints

from .knowledge_context import (
    KnowledgeContextRequestV1, KnowledgeContextResponseV1,
    canonical_knowledge_context_bytes, EntityRef, SnapshotInfo, SourceReportedFact, InferenceClaim,
)

Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^sha256:[0-9a-f]{64}$")]


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class ClockContract:
    skew_budget_us: int = 0
    max_observation_age_ms: int = 5000

    def __post_init__(self) -> None:
        if type(self.skew_budget_us) is not int or self.skew_budget_us not in (0, 5000):
            raise ValueError("clocklab budget must be 0 or 5000us")
        if type(self.max_observation_age_ms) is not int or self.max_observation_age_ms != 5000:
            raise ValueError("clocklab age must be 5000ms")

    def _body(self) -> dict:
        return {"schema": "azazel-clocklab-policy/2", "skew_budget_us": self.skew_budget_us,
                "max_observation_age_ms": self.max_observation_age_ms}

    @property
    def contract_id(self) -> str:
        return "sha256:" + hashlib.sha256(_canonical(self._body())).hexdigest()

    def as_dict(self) -> dict:
        return {**self._body(), "contract_id": self.contract_id}

    @classmethod
    def from_dict(cls, value: dict) -> ClockContract:
        if type(value) is not dict or set(value) != {
            "schema", "skew_budget_us", "max_observation_age_ms", "contract_id"
        } or value["schema"] != "azazel-clocklab-policy/2":
            raise ValueError("clocklab policy malformed")
        result = cls(value["skew_budget_us"], value["max_observation_age_ms"])
        if value["contract_id"] != result.contract_id:
            raise ValueError("clocklab policy digest mismatch")
        return result


class KnowledgeContextRequestV2(KnowledgeContextRequestV1):
    schema_version: Literal["knowledge-context-request/v2"]
    contract_id: Digest


class KnowledgeContextResponseV2(KnowledgeContextResponseV1):
    schema_version: Literal["knowledge-context-response/v2"]
    contract_id: Digest


def request_v1_projection(request: KnowledgeContextRequestV2) -> KnowledgeContextRequestV1:
    if type(request) is not KnowledgeContextRequestV2:
        raise TypeError("exact clocklab request required")
    if any(type(entity) is not EntityRef for entity in request.entities):
        raise TypeError("exact request entities required")
    data = request.model_dump(mode="python")
    data.pop("contract_id")
    data["schema_version"] = "knowledge-context-request/v1"
    result = KnowledgeContextRequestV1.model_validate(data)
    canonical_knowledge_context_bytes(result)
    return result


def response_v1_projection(response: KnowledgeContextResponseV2) -> KnowledgeContextResponseV1:
    if type(response) is not KnowledgeContextResponseV2:
        raise TypeError("exact clocklab response required")
    if (type(response.snapshot) is not SnapshotInfo
            or any(type(item) is not SourceReportedFact for item in response.facts)
            or any(type(item) is not InferenceClaim for item in response.inferences)
            or any(type(item.subject) is not EntityRef for item in (*response.facts, *response.inferences))):
        raise TypeError("exact response nested models required")
    data = response.model_dump(mode="python")
    data.pop("contract_id")
    data["schema_version"] = "knowledge-context-response/v1"
    result = KnowledgeContextResponseV1.model_validate(data)
    canonical_knowledge_context_bytes(result)
    return result


def canonical_clocklab_bytes(payload: KnowledgeContextRequestV2 | KnowledgeContextResponseV2) -> bytes:
    if type(payload) is KnowledgeContextRequestV2:
        request_v1_projection(payload)
    elif type(payload) is KnowledgeContextResponseV2:
        response_v1_projection(payload)
    else:
        raise TypeError("exact clocklab model required")
    checked = type(payload).model_validate(payload.model_dump(mode="python"))
    return _canonical(checked.model_dump(mode="json"))


def assert_response_correlates_v2(request: KnowledgeContextRequestV2,
                                 response: KnowledgeContextResponseV2, *,
                                 contract: ClockContract) -> None:
    if type(contract) is not ClockContract:
        raise TypeError("exact clock contract required")
    canonical_clocklab_bytes(request)
    canonical_clocklab_bytes(response)
    for obj in (request, response):
        if obj.contract_id != contract.contract_id:
            raise ValueError("clocklab policy mismatch")
    for field in ("request_id", "correlation_id", "source_product", "source_ref"):
        if getattr(request, field) != getattr(response, field):
            raise ValueError("clocklab response correlation mismatch")
    if response.generated_at - request.requested_at < -timedelta(microseconds=contract.skew_budget_us):
        raise ValueError("clocklab response generated before request budget")
    subjects = {(e.entity_type, e.value) for e in request.entities}
    for claim in (*response.facts, *response.inferences):
        if (claim.subject.entity_type, claim.subject.value) not in subjects:
            raise ValueError("clocklab response subject not requested")
