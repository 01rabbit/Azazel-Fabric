"""Canonical M.I.O. dual-cognition contracts (R1a).

These types describe the four things two cognition paths have to agree on: the
**local situation frame** a router builds, the **sanitized remote frame** that
may leave the node, the **advisory result** either model returns, and the
**provenance-preserving merge output** an operator finally reads.

Authority rule, unchanged:

    Fabric describes. Knowledge advises. Edge decides and enforces.

Encoded structurally rather than stated in prose:

* An advisory result is ``advisory_only``, ``executable`` is pinned ``False``,
  ``rendering`` is pinned ``inert_text``, it cannot carry links, and it cannot
  request a follow-up disclosure — every follow-up must be a new, locally
  constructed, audited sanitized frame.
* A sanitized remote frame pins ``contains_raw_evidence`` to ``False``, declares
  ``deny_on_ambiguity``, carries a per-field redaction record, and is rejected
  outright when classified ``sensitive``/``restricted``.
* A merge keeps its claims separate: a :class:`ClaimSet` is frozen before any
  narrative text exists, each claim keeps source / model / generation / inputs /
  freshness / confidence / limitations, and a contradiction is recorded as a
  :class:`Disagreement` whose resolution is pinned to "presented separately" —
  a merger may never resolve a disagreement by dropping a claim.

What Fabric explicitly does **not** do: judge the prose. ``narrative_text`` is
model output, and no schema can prove it is non-imperative. The contract makes
sure nothing downstream can *act* on it — see
:mod:`azazel_fabric.mio_contracts.validation`.

The initial wire family is ``*/v0.1`` and is additive to existing Fabric
contracts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from azazel_fabric.mio_contracts.validation import (
    assert_bounded_mio_payload,
    assert_claim_provenance_preserved,
    assert_no_mio_directives,
)

# Privacy classification applied per field before anything may be considered for
# remote egress. ``sensitive``/``restricted`` never leave the node.
PrivacyClass = Literal["public", "internal", "sensitive", "restricted"]

# Where a claim came from. A deterministic Core explanation and a model answer
# are different sources and stay distinguishable after a merge.
ClaimSource = Literal["deterministic_core", "knowledge_advisory", "local_model", "remote_model"]

# What cognition was actually available when the operator-facing text was built.
CognitionState = Literal["core_only", "local", "hybrid"]


class _Descriptive(BaseModel):
    """Base for every M.I.O. record: closed, immutable, describe-only."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AliasScope(_Descriptive):
    """The lifetime within which an alias is stable, and outside which it is not.

    An alias is deterministic only inside its declared mission/request scope and
    key generation; rotating the generation must produce a different mapping, so
    cross-mission correlation is not possible.
    """

    schema_version: Literal["mio-alias-scope/v0.1"] = "mio-alias-scope/v0.1"
    scope_kind: Literal["mission", "request"]
    scope_id: str = Field(min_length=1, max_length=128)
    key_generation: int = Field(ge=0)
    expires_at: datetime


class RedactionRecord(_Descriptive):
    """What the sanitizer did to one field, and why."""

    schema_version: Literal["mio-redaction-record/v0.1"] = "mio-redaction-record/v0.1"
    field_ref: str = Field(min_length=1, max_length=256)
    privacy_class: PrivacyClass
    action: Literal["removed", "aliased", "bucketed", "truncated", "generalized"]
    alias_ref: str | None = Field(default=None, max_length=128)
    reason: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def _alias_needs_ref(self) -> "RedactionRecord":
        if self.action == "aliased" and not self.alias_ref:
            raise ValueError("an aliased field must record its alias_ref")
        if self.action != "aliased" and self.alias_ref is not None:
            raise ValueError("alias_ref is only meaningful for an aliased field")
        return self


class SituationFrame(_Descriptive):
    """The local situation a cognitive router assembled. Never leaves the node as-is.

    Content is a bounded fact payload of evidence *references* and summary
    values, not raw evidence. The deadline and resource budget are recorded
    because the router had them, not because anything here enforces them.
    """

    schema_version: Literal["mio-situation-frame/v0.1"] = "mio-situation-frame/v0.1"
    frame_id: str = Field(min_length=1, max_length=128)
    product: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    created_at: datetime
    deadline_budget_ms: int = Field(ge=0)
    memory_budget_mib: int | None = Field(default=None, ge=0)
    privacy_class: PrivacyClass
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    content: dict[str, Any] = Field(default_factory=dict)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "SituationFrame":
        assert_no_mio_directives(self.model_dump(mode="json"))
        assert_bounded_mio_payload(self.content)
        return self


class SanitizedRemoteFrame(_Descriptive):
    """The only shape that may be sent to a remote model.

    It names the local frame it came from, the alias scope its identifiers are
    valid in, and every redaction applied. ``contains_raw_evidence`` is pinned
    ``False`` and ``ambiguity_resolution`` is pinned ``deny_on_ambiguity``: a
    field the sanitizer could not classify was dropped before this record
    existed, never forwarded with a guess.
    """

    schema_version: Literal["mio-sanitized-remote-frame/v0.1"] = (
        "mio-sanitized-remote-frame/v0.1"
    )
    frame_id: str = Field(min_length=1, max_length=128)
    source_frame_ref: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    created_at: datetime
    alias_scope: AliasScope
    privacy_class: Literal["public", "internal"]
    redactions: tuple[RedactionRecord, ...] = Field(default_factory=tuple, max_length=128)
    content: dict[str, Any] = Field(default_factory=dict)
    content_size_bytes: int = Field(ge=0)
    sanitizer_ref: str = Field(min_length=1, max_length=128)
    contains_raw_evidence: Literal[False] = False
    ambiguity_resolution: Literal["deny_on_ambiguity"] = "deny_on_ambiguity"
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "SanitizedRemoteFrame":
        assert_no_mio_directives(self.model_dump(mode="json"))
        assert_bounded_mio_payload(self.content)
        refs = [item.field_ref for item in self.redactions]
        if len(set(refs)) != len(refs):
            raise ValueError("a redaction record must not repeat a field_ref")
        aliases = [item.alias_ref for item in self.redactions if item.alias_ref is not None]
        if len(set(aliases)) != len(aliases):
            raise ValueError(
                "two fields share one alias_ref; distinct subjects must not collapse "
                "into one alias within a scope"
            )
        return self


class Claim(_Descriptive):
    """One structured claim with its full provenance.

    Frozen before narrative text exists, so what a merge presents can always be
    traced back to who said it, from which model generation, over which inputs.
    """

    schema_version: Literal["mio-claim/v0.1"] = "mio-claim/v0.1"
    claim_id: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=1, max_length=4096)
    source: ClaimSource
    model_ref: str | None = Field(default=None, max_length=128)
    model_generation: str | None = Field(default=None, max_length=64)
    input_refs: tuple[str, ...] = Field(default_factory=tuple, max_length=128)
    freshness: str | None = Field(default=None, max_length=64)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)

    @model_validator(mode="after")
    def _model_claims_name_their_model(self) -> "Claim":
        if self.source in ("local_model", "remote_model") and not self.model_ref:
            raise ValueError("a model-sourced claim must name its model_ref")
        return self


class ClaimSet(_Descriptive):
    """A frozen set of claims. Provenance survives every later step."""

    schema_version: Literal["mio-claim-set/v0.1"] = "mio-claim-set/v0.1"
    claim_set_id: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    frozen_at: datetime
    claims: tuple[Claim, ...] = Field(min_length=1, max_length=256)
    authority: Literal["descriptive_only"] = "descriptive_only"

    @model_validator(mode="after")
    def _validate(self) -> "ClaimSet":
        assert_no_mio_directives(self.model_dump(mode="json"))
        assert_claim_provenance_preserved(self)
        return self


class Disagreement(_Descriptive):
    """Two or more claims that contradict each other, kept apart on purpose.

    ``resolution`` is pinned: a merger presents a contradiction, it never
    silently picks a winner.
    """

    schema_version: Literal["mio-disagreement/v0.1"] = "mio-disagreement/v0.1"
    topic: str = Field(min_length=1, max_length=256)
    claim_refs: tuple[str, ...] = Field(min_length=2, max_length=32)
    resolution: Literal["presented_separately"] = "presented_separately"


class AdvisoryResult(_Descriptive):
    """One cognition path's answer. Inert by construction.

    ``executable``, ``may_request_followup``, and ``contains_links`` are all
    pinned ``False`` in the wire shape, so no well-formed result can ask a
    consumer to do anything, and any follow-up must be a new locally constructed
    and audited sanitized frame.
    """

    schema_version: Literal["mio-advisory-result/v0.1"] = "mio-advisory-result/v0.1"
    result_id: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    request_ref: str = Field(min_length=1, max_length=128)
    origin: Literal["local", "remote"]
    model_ref: str = Field(min_length=1, max_length=128)
    model_generation: str | None = Field(default=None, max_length=64)
    produced_at: datetime
    claim_set: ClaimSet
    narrative_text: str = Field(default="", max_length=8192)
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    rendering: Literal["inert_text"] = "inert_text"
    executable: Literal[False] = False
    may_request_followup: Literal[False] = False
    contains_links: Literal[False] = False
    authority: Literal["advisory_only"] = "advisory_only"

    @model_validator(mode="after")
    def _validate(self) -> "AdvisoryResult":
        assert_no_mio_directives(self.model_dump(mode="json"))
        return self


class MergedAdvisory(_Descriptive):
    """Provenance-preserving merge output. Still advisory, still inert.

    Every disagreement must reference claims that are actually in the merged
    claim set, so a contradiction cannot be recorded against a claim the reader
    can no longer see. ``cognition_state`` records what was available
    (``core_only`` / ``local`` / ``hybrid``); losing the remote path degrades the
    state, it never degrades the authority boundary.
    """

    schema_version: Literal["mio-merged-advisory/v0.1"] = "mio-merged-advisory/v0.1"
    merge_id: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=256)
    merged_at: datetime
    input_result_refs: tuple[str, ...] = Field(min_length=1, max_length=32)
    claim_set: ClaimSet
    disagreements: tuple[Disagreement, ...] = Field(default_factory=tuple, max_length=64)
    narrative_text: str = Field(default="", max_length=8192)
    cognition_state: CognitionState
    limitations: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    rendering: Literal["inert_text"] = "inert_text"
    executable: Literal[False] = False
    authority: Literal["advisory_only"] = "advisory_only"

    @model_validator(mode="after")
    def _validate(self) -> "MergedAdvisory":
        assert_no_mio_directives(self.model_dump(mode="json"))
        assert_claim_provenance_preserved(self.claim_set)
        known = {claim.claim_id for claim in self.claim_set.claims}
        for disagreement in self.disagreements:
            missing = [ref for ref in disagreement.claim_refs if ref not in known]
            if missing:
                raise ValueError(
                    f"disagreement {disagreement.topic!r} references claims outside the "
                    f"merged claim set: {missing}"
                )
        return self
