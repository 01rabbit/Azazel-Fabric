"""Descriptive external-security interoperability profile (Fabric#25, R2). **Experimental.**

Four descriptive-only records for external security telemetry producers,
Knowledge advisory consumers, Deception observation producers, and
Nexus/Edge device adapters:

* ``ExternalObservationEnvelope/v0.1`` -- a fact an external system observed;
* ``AdvisoryContextEnvelope/v0.1`` -- ``advisory_only`` context about facts;
* ``ExposureChangeProposal/v0.1`` -- a ``proposal_only`` bounded request;
* ``DeviceChangeObservation/v0.1`` -- what a device adapter observed.

    **Fabric describes. Knowledge advises. The owning product decides.**

``executable`` is pinned ``False`` on every record. Nothing here implements a
vendor API, a network client, an adapter, or any execution behaviour, and
nothing here decides, admits, or approves.

**Experimental** under the Fabric#23 program decision: there is no real
producer or consumer yet, so the family makes no compatibility promise and is
outside the R1c stable gate. It is **optional**: no other Fabric module
imports it, so Edge, Knowledge, Deception, Nexus and Boot are unaffected when
they do not import it themselves.

See ``docs/external-security-contracts.md`` and
``docs/adr/0001-external-security-contract-ownership.md``.
"""

from azazel_fabric.external_security_contracts.models import (
    CORRELATION_REF_KINDS,
    EVIDENCE_REF_KINDS,
    FACT_REF_KINDS,
    SUBJECT_REF_KINDS,
    DEVICE_CHANGE_STATUSES,
    EXPOSURE_EFFECTS,
    FACT_CLASSES,
    MAX_PROPOSAL_WINDOW_SECONDS,
    UNKNOWN_DEVICE_CHANGE_STATUS,
    UNKNOWN_FACT_CLASS,
    WEAKEST_EXPOSURE_EFFECT,
    AdvisoryActionClass,
    AdvisoryContextEnvelope,
    ConfidenceBand,
    DeviceChangeObservation,
    DeviceChangeStatus,
    EventWindow,
    ExposureChangeProposal,
    ExposureEffect,
    ExternalObservationEnvelope,
    ExternalProvenance,
    FactClass,
    FreshnessState,
    FreshnessStatement,
    PrivacyClass,
    ProvenanceHop,
    RecommendedAction,
    RecommendedObservation,
    RollbackRequirement,
    SafetyConstraint,
    SourceSystemClass,
    TelemetryCoverage,
    VendorExtension,
    coerce_device_change_status,
    coerce_exposure_effect,
    coerce_fact_class,
)
from azazel_fabric.external_security_contracts.validation import (
    BANNED_EXTERNAL_SECURITY_FIELDS,
    BANNED_TARGET_LOCATOR_FIELDS,
    CREDENTIAL_LOCATOR_KINDS,
    OPAQUE_KEY_DENY_TOKENS,
    OPAQUE_VALUE_DENY_WORDS,
    PRIVACY_CLASSES,
    as_record,
    assert_free_text,
    assert_no_long_token,
    assert_opaque_map,
    assert_device_observation_within_proposal,
    assert_no_external_security_directives,
    assert_no_replay_extension,
    assert_no_secret_material,
    assert_no_target_locators,
    assert_not_expired,
    assert_privacy_admitted,
    assert_tenant_confined,
    canonical_digest,
    canonical_external_security_json,
    contains_external_security_directive,
)

#: Maturity, stated in code as well as in the docs. Not a version: a family
#: whose shape may change without a candidate bump (Fabric#23).
MATURITY = "experimental"

__all__ = [
    "MATURITY",
    # models
    "CORRELATION_REF_KINDS",
    "EVIDENCE_REF_KINDS",
    "FACT_REF_KINDS",
    "SUBJECT_REF_KINDS",
    "AdvisoryActionClass",
    "AdvisoryContextEnvelope",
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
    # validation
    "BANNED_EXTERNAL_SECURITY_FIELDS",
    "BANNED_TARGET_LOCATOR_FIELDS",
    "CREDENTIAL_LOCATOR_KINDS",
    "OPAQUE_KEY_DENY_TOKENS",
    "OPAQUE_VALUE_DENY_WORDS",
    "PRIVACY_CLASSES",
    "as_record",
    "assert_free_text",
    "assert_no_long_token",
    "assert_opaque_map",
    "assert_device_observation_within_proposal",
    "assert_no_external_security_directives",
    "assert_no_replay_extension",
    "assert_no_secret_material",
    "assert_no_target_locators",
    "assert_not_expired",
    "assert_privacy_admitted",
    "assert_tenant_confined",
    "canonical_digest",
    "canonical_external_security_json",
    "contains_external_security_directive",
]
