"""Deterministic insufficiency remedies for rejected negative claims.

A rejection tells the caller that the evidence is insufficient.  It does not
tell them what would have to become true.  Every constraint needed to answer
that is already resolved during evaluation, so the answer is a pure function of
a decision that has already been computed.

Two properties make this safe rather than a fabrication recipe, and both come
from ADR-0014:

* An item states a condition on the world or on observed evidence.  It never
  instructs the caller to change a request field, and it never echoes a value
  the caller did not already supply unless the relying application explicitly
  asks for governed values.
* A remedy is not a decision and never becomes one.  It is bound to the
  decision it explains by that decision's evaluation-input digest, it is
  excluded from the decision payload, and no remedy is produced for a permit.

Nothing here consults the wall clock, the network, the filesystem, the
environment, or any mutable global state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .certificates import EvidenceCertificate, verify_evidence_certificate
from .errors import ModelValidationError
from .gate import (
    EVALUATOR_VERSION,
    GateDecision,
    GateReason,
    NegativeClaimRequest,
    evaluate_negative_claim,
)
from .models import EvidenceState, SourceRole
from .profiles import CoverageFinalityProfile, TrustedProfileContext

INSUFFICIENCY_REMEDY_SCHEMA = "esio-insufficiency-remedy/1.0-candidate.2"


class DisclosureLevel(str, Enum):
    """Who may see the governed values behind a failing constraint."""

    CONSTRAINT_ONLY = "CONSTRAINT_ONLY"
    WITH_GOVERNED_VALUES = "WITH_GOVERNED_VALUES"


class RemedyClass(str, Enum):
    AWAIT_SOURCE_STATE = "AWAIT_SOURCE_STATE"
    OBTAIN_FRESH_OBSERVATION = "OBTAIN_FRESH_OBSERVATION"
    OBTAIN_COMPLETE_ENUMERATION = "OBTAIN_COMPLETE_ENUMERATION"
    OBTAIN_MISSING_DECLARATION = "OBTAIN_MISSING_DECLARATION"
    RESOLVE_SOURCE_AVAILABILITY = "RESOLVE_SOURCE_AVAILABILITY"
    USE_GOVERNED_SCOPE = "USE_GOVERNED_SCOPE"
    RESOLVE_GOVERNANCE_TRUST = "RESOLVE_GOVERNANCE_TRUST"
    UNSATISFIABLE = "UNSATISFIABLE"


_R = GateReason
_C = RemedyClass

# Reason -> (class, condition).  A condition describes what must become true.
# It never names a field to edit and never contains a governed value; governed
# values travel separately and only under WITH_GOVERNED_VALUES.
_REMEDY_TABLE: dict[GateReason, tuple[RemedyClass, str]] = {
    _R.ABSOLUTE_NEGATIVE_UNSUPPORTED: (
        _C.UNSATISFIABLE,
        "an absolute or universal negative is never supportable; the claim must be bounded to a declared population, query, source, and interval",
    ),
    _R.NONZERO_MATCHES: (
        _C.UNSATISFIABLE,
        "the observation reports in-scope matches, which is evidence of presence rather than an evidence shortfall",
    ),
    _R.REQUIRED_SOURCE_CONTRADICTORY: (
        _C.UNSATISFIABLE,
        "the required source reported internally contradictory evidence; the contradiction must be resolved at the source before any negative claim is assessable",
    ),
    _R.STATE_NOT_ABSENT_WITHIN_SCOPE: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "the observation must report ABSENT_WITHIN_SCOPE rather than an indeterminate state",
    ),
    _R.COVERAGE_POLICY_NOT_MET: (
        _C.OBTAIN_COMPLETE_ENUMERATION,
        "enumeration must be complete against the declared denominator and reach the governed coverage floor",
    ),
    _R.ENVELOPE_ERRORS_PRESENT: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "the reported envelope errors must be resolved at the source and the observation retaken",
    ),
    _R.EVALUATION_PRECEDES_OBSERVATION: (
        _C.OBTAIN_FRESH_OBSERVATION,
        "the evaluation time must not precede the observation it evaluates",
    ),
    _R.VALIDITY_UNDECLARED: (
        _C.OBTAIN_MISSING_DECLARATION,
        "the source must report a validity boundary for the result",
    ),
    _R.RESULT_EXPIRED: (
        _C.OBTAIN_FRESH_OBSERVATION,
        "the result is past its declared validity boundary; a fresh observation is required",
    ),
    _R.OBSERVATION_TOO_OLD: (
        _C.OBTAIN_FRESH_OBSERVATION,
        "the observation is older than the governed observation-age limit; a fresh observation is required",
    ),
    _R.FINALITY_HORIZON_UNDECLARED: (
        _C.OBTAIN_MISSING_DECLARATION,
        "the required source must carry a declared finality horizon",
    ),
    _R.INDEX_TIMESTAMP_UNDECLARED: (
        _C.OBTAIN_MISSING_DECLARATION,
        "the source must report the time its index was current as of",
    ),
    _R.INDEX_TIME_AFTER_EVALUATION: (
        _C.OBTAIN_MISSING_DECLARATION,
        "the source-reported index time must not be later than the evaluation time",
    ),
    _R.INDEX_PRECEDES_QUERY_END: (
        _C.AWAIT_SOURCE_STATE,
        "the source index must reach the end of the queried interval",
    ),
    _R.INDEX_PRECEDES_FINALITY_HORIZON: (
        _C.AWAIT_SOURCE_STATE,
        "the source index must reach the finality horizon derived from the governed late-arrival and reopen bounds",
    ),
    _R.INDEX_TOO_OLD: (
        _C.OBTAIN_FRESH_OBSERVATION,
        "the source index is older than the governed index-age limit; the source must re-index and be re-observed",
    ),
    _R.REQUIRED_SOURCE_MISSING: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "every source the query declares as required must appear in the observations",
    ),
    _R.REQUIRED_SOURCE_NOT_OBSERVED: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "the required source must actually be observed rather than declared and skipped",
    ),
    _R.REQUIRED_SOURCE_INACCESSIBLE: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "access to the required source must be restored within the declared authorization boundary",
    ),
    _R.REQUIRED_SOURCE_PENDING: (
        _C.AWAIT_SOURCE_STATE,
        "the required source's pending observation must complete",
    ),
    _R.REQUIRED_SOURCE_STALE: (
        _C.OBTAIN_FRESH_OBSERVATION,
        "the required source's observation is stale and must be retaken",
    ),
    _R.REQUIRED_SOURCE_FAILED: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "the required source's failed observation must succeed",
    ),
    _R.REQUIRED_SOURCE_STATUS_UNKNOWN: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "the required source must report a status the contract recognises",
    ),
    _R.REQUIRED_SOURCE_ERRORS_PRESENT: (
        _C.RESOLVE_SOURCE_AVAILABILITY,
        "the errors the required source reported must be resolved and the observation retaken",
    ),
    _R.REQUIRED_SOURCE_IDENTITY_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the observed source identity must be the one the query requires",
    ),
    _R.REQUIRED_SOURCE_ADAPTER_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the observing adapter must be the one the query requires",
    ),
    _R.REQUIRED_SOURCE_AUTHORIZATION_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the observation must be made under the authorization context the query requires",
    ),
    _R.REQUIRED_SOURCE_POPULATION_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the observed accessible population must be the one the query requires",
    ),
    _R.PROFILE_SOURCE_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the request must address the source the governed profile covers",
    ),
    _R.PROFILE_ADAPTER_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the request must use an adapter the governed profile covers",
    ),
    _R.PROFILE_AUTHORIZATION_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the request must run under an authorization context the governed profile covers",
    ),
    _R.PROFILE_POPULATION_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the request must target the accessible population the governed profile declares",
    ),
    _R.PROFILE_QUERY_APPLICABILITY_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the query target, predicate, and required exclusions must match what the governed profile declares it covers",
    ),
    _R.PROFILE_DETECTION_ASSUMPTIONS_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the declared detection assumptions must match those the governed profile was approved under",
    ),
    _R.PROFILE_COVERAGE_BASIS_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the coverage basis, denominator, and any page or partition counts must match the governed profile",
    ),
    _R.PROFILE_RETENTION_EXCEEDED: (
        _C.UNSATISFIABLE,
        "the queried interval reaches beyond the governed retention window, so the source cannot hold evidence for it; only a query inside retention is assessable",
    ),
    _R.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY: (
        _C.UNSATISFIABLE,
        "the queried interval intersects an interval the governed profile declares the source blind to; no observation of that interval can support a negative",
    ),
    _R.PROFILE_OBSERVATION_TOO_OLD: (
        _C.OBTAIN_FRESH_OBSERVATION,
        "the observation is older than the governed profile's observation-age limit",
    ),
    _R.PROFILE_INDEX_TOO_OLD: (
        _C.OBTAIN_FRESH_OBSERVATION,
        "the source index is older than the governed profile's index-age limit",
    ),
    _R.FINALITY_HORIZON_PROFILE_MISMATCH: (
        _C.USE_GOVERNED_SCOPE,
        "the declared finality horizon must equal the one the governed profile derives from the queried interval",
    ),
    _R.PROFILE_REFERENCE_UNDECLARED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the request must carry an exact governed profile reference",
    ),
    _R.PROFILE_TRUST_SELECTION_MISMATCH: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the profile the request references must be the one the relying application selected",
    ),
    _R.REGISTRY_SNAPSHOT_UNDECLARED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the relying application must supply a registry snapshot",
    ),
    _R.REGISTRY_SNAPSHOT_IDENTITY_MISMATCH: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the supplied snapshot must be the one the trust selection pins",
    ),
    _R.REGISTRY_SNAPSHOT_DIGEST_MISMATCH: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the supplied snapshot's content must match the digest the trust selection pins",
    ),
    _R.REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the snapshot issuer must be one the relying application trusts",
    ),
    _R.REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the snapshot must be in force at the evaluation time",
    ),
    _R.REGISTRY_SNAPSHOT_EXPIRED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the relying application must supply a snapshot that is still in force",
    ),
    _R.PROFILE_NOT_FOUND: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the referenced profile must exist in the supplied snapshot",
    ),
    _R.PROFILE_DIGEST_MISMATCH: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the resolved profile's content must match the digest the request references",
    ),
    _R.PROFILE_ISSUER_UNTRUSTED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the profile issuer must be one the relying application trusts",
    ),
    _R.PROFILE_AUTHORITY_UNTRUSTED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the profile's approval authority must be one the relying application trusts",
    ),
    _R.PROFILE_NOT_YET_EFFECTIVE: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the profile must be in force at the evaluation time",
    ),
    _R.PROFILE_EXPIRED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "an unexpired governed profile must be selected",
    ),
    _R.PROFILE_REVOKED: (
        _C.RESOLVE_GOVERNANCE_TRUST,
        "the selected profile is revoked; an unrevoked governed profile must be selected",
    ),
}

_UNIVERSAL_LIMITATIONS = (
    "A remedy is not a decision, an authorization, or a prediction. Only new evidence, re-evaluated through the same gate, produces a decision.",
    "A satisfiable remedy does not establish that its conditions can be met, or that the underlying fact is true.",
    "A remedy describes conditions on the world and on observed evidence. It never instructs a caller to edit a request field.",
    "The gate has no authenticated adapter evidence, so a remedy cannot make it safe against a self-consistent malicious producer.",
)

_DISCLOSURE_LIMITATION = (
    "This remedy was produced at WITH_GOVERNED_VALUES and carries governed threshold values. "
    "Returning it to the party that produced the result hands that party the values it would "
    "need to construct a self-consistent fabrication, which the P0 gate cannot detect."
)


def _isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class RemedyItem:
    reason: GateReason
    remedy_class: RemedyClass
    condition: str
    governed_value: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reason, GateReason):
            raise ModelValidationError("remedy_item.reason must be a GateReason")
        if not isinstance(self.remedy_class, RemedyClass):
            raise ModelValidationError("remedy_item.remedy_class must be a RemedyClass")
        if not isinstance(self.condition, str) or not self.condition.strip():
            raise ModelValidationError("remedy_item.condition must be a non-empty string")
        if self.governed_value is not None and not isinstance(self.governed_value, str):
            raise ModelValidationError("remedy_item.governed_value must be a string or null")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason.value,
            "remedy_class": self.remedy_class.value,
            "condition": self.condition,
            "governed_value": self.governed_value,
        }


@dataclass(frozen=True)
class InsufficiencyRemedy:
    disclosure: DisclosureLevel
    input_digest: str
    evaluated_at: datetime
    items: tuple[RemedyItem, ...]
    limitations: tuple[str, ...]
    certificate_digest: str | None = None
    remedy_schema: str = INSUFFICIENCY_REMEDY_SCHEMA
    decision: str = "REJECT_NEGATIVE"
    evaluator_version: str = EVALUATOR_VERSION

    @property
    def satisfiable(self) -> bool:
        """False when any reason cannot be removed by further evidence."""

        return not any(item.remedy_class is RemedyClass.UNSATISFIABLE for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "remedy_schema": self.remedy_schema,
            "decision": self.decision,
            "disclosure": self.disclosure.value,
            "evaluator_version": self.evaluator_version,
            "evaluated_at": _isoformat(self.evaluated_at),
            "input_digest": self.input_digest,
            "certificate_digest": self.certificate_digest,
            "satisfiable": self.satisfiable,
            "items": [item.to_dict() for item in self.items],
            "limitations": list(self.limitations),
        }


def _selected_profile(context: TrustedProfileContext | None) -> CoverageFinalityProfile | None:
    """Return the profile the trust selection pins, or None.

    This is a best-effort lookup used only to disclose governed values.  It
    never influences a decision, so a lookup that does not resolve simply
    withholds the value.
    """

    if context is None:
        return None
    reference = context.trust_selection.selected_profile_reference
    for record in context.snapshot.records:
        profile = record.profile
        if (
            profile.profile_id == reference.profile_id
            and profile.profile_version == reference.profile_version
        ):
            return profile
    return None


def _governed_value(
    reason: GateReason,
    request: NegativeClaimRequest,
    profile: CoverageFinalityProfile | None,
) -> str | None:
    """Return the value the failing constraint compares against, if any."""

    envelope = request.envelope
    policy = request.policy
    if reason is _R.INDEX_PRECEDES_QUERY_END:
        return _isoformat(envelope.query.time_end)
    if reason is _R.INDEX_PRECEDES_FINALITY_HORIZON:
        for requirement in envelope.query.source_requirements:
            if requirement.role is SourceRole.REQUIRED and requirement.finality_horizon is not None:
                return _isoformat(requirement.finality_horizon)
        return None
    if reason is _R.RESULT_EXPIRED and envelope.valid_until is not None:
        return _isoformat(envelope.valid_until)
    if reason is _R.OBSERVATION_TOO_OLD and policy.max_observation_age_seconds is not None:
        return f"{policy.max_observation_age_seconds}s maximum observation age"
    if reason is _R.INDEX_TOO_OLD and policy.max_index_age_seconds is not None:
        return f"{policy.max_index_age_seconds}s maximum index age"
    if reason is _R.COVERAGE_POLICY_NOT_MET and policy.coverage is not None:
        coverage_policy = policy.coverage
        parts = [f"minimum coverage lower bound {coverage_policy.minimum_lower_bound}"]
        if coverage_policy.require_complete_pagination:
            parts.append("complete pagination")
        if coverage_policy.require_complete_partitions:
            parts.append("complete partitions")
        if coverage_policy.require_exact_population:
            parts.append("an exact population")
        return "; ".join(parts)
    if profile is None:
        return None
    if reason is _R.PROFILE_RETENTION_EXCEEDED:
        return f"{profile.coverage.retention_seconds}s governed retention window"
    if reason is _R.PROFILE_OBSERVATION_TOO_OLD:
        return f"{profile.coverage.max_observation_age_seconds}s governed observation age"
    if reason is _R.PROFILE_INDEX_TOO_OLD:
        return f"{profile.coverage.max_index_age_seconds}s governed index age"
    if reason is _R.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY:
        intervals = "; ".join(
            f"{_isoformat(interval.start)}/{_isoformat(interval.end)}"
            for interval in profile.coverage.blind_intervals
        )
        return intervals or None
    if reason is _R.FINALITY_HORIZON_PROFILE_MISMATCH:
        return (
            f"query.time_end plus max({profile.finality.late_arrival_bound_seconds}s "
            f"late arrival, {profile.finality.reopen_bound_seconds}s reopen)"
        )
    if reason is _R.PROFILE_POPULATION_MISMATCH:
        return f"{profile.coverage.population_units} governed population units"
    return None


def _classify(reason: GateReason, request: NegativeClaimRequest) -> tuple[RemedyClass, str]:
    """Return the class and condition for one reason.

    Most reasons map directly.  Where the class depends on the observed
    evidence rather than the code alone it is computed, so the record reflects
    what was actually reported instead of a lookup default.
    """

    if reason is _R.STATE_NOT_ABSENT_WITHIN_SCOPE:
        if request.envelope.state is EvidenceState.PRESENT:
            return (
                _C.UNSATISFIABLE,
                "the observation reports PRESENT, which is evidence of presence rather than an evidence shortfall",
            )
        return _REMEDY_TABLE[reason]
    entry = _REMEDY_TABLE.get(reason)
    if entry is None:
        raise ModelValidationError(f"no remedy classification for gate reason {reason.value}")
    return entry


def derive_remedy(
    decision: GateDecision,
    request: NegativeClaimRequest,
    context: TrustedProfileContext | None = None,
    *,
    disclosure: DisclosureLevel = DisclosureLevel.CONSTRAINT_ONLY,
) -> InsufficiencyRemedy:
    """Explain a rejection as conditions that would have to become true.

    Pure and deterministic: identical inputs produce an identical record.  No
    remedy is produced for a permit, because a permit has nothing to remedy and
    an accompanying remedy would invite reading it as conditional.
    """

    if type(decision) is not GateDecision:
        raise ModelValidationError("decision must be a GateDecision")
    if type(request) is not NegativeClaimRequest:
        raise ModelValidationError("request must be NegativeClaimRequest")
    if context is not None and type(context) is not TrustedProfileContext:
        raise ModelValidationError("context must be TrustedProfileContext or null")
    if type(disclosure) is not DisclosureLevel:
        raise ModelValidationError("disclosure must be a DisclosureLevel")
    if decision.allowed:
        raise ModelValidationError(
            "a permitted decision has no insufficiency to remedy; remedies are derived only from REJECT_NEGATIVE"
        )
    if not decision.reasons:
        raise ModelValidationError("a rejected decision must carry at least one reason")

    profile = (
        _selected_profile(context) if disclosure is DisclosureLevel.WITH_GOVERNED_VALUES else None
    )
    items: list[RemedyItem] = []
    for reason in decision.reasons:
        remedy_class, condition = _classify(reason, request)
        value = (
            _governed_value(reason, request, profile)
            if disclosure is DisclosureLevel.WITH_GOVERNED_VALUES
            else None
        )
        items.append(
            RemedyItem(
                reason=reason,
                remedy_class=remedy_class,
                condition=condition,
                governed_value=value,
            )
        )

    limitations: tuple[str, ...] = _UNIVERSAL_LIMITATIONS
    if disclosure is DisclosureLevel.WITH_GOVERNED_VALUES:
        limitations = limitations + (_DISCLOSURE_LIMITATION,)

    return InsufficiencyRemedy(
        disclosure=disclosure,
        input_digest=decision.input_digest,
        evaluated_at=request.evaluated_at,
        items=tuple(items),
        limitations=limitations,
    )


# Dimensions that must hold before a certificate may be explained.  Explaining a
# record whose bindings do not hold would attribute conditions to a claim that
# is not what the record says it is.
_REQUIRED_CERTIFICATE_DIMENSIONS = (
    "structural_support",
    "certificate_digest_integrity",
    "embedded_digest_integrity",
    "deterministic_replay",
)


def derive_remedy_from_certificate(
    certificate: EvidenceCertificate,
    *,
    disclosure: DisclosureLevel = DisclosureLevel.CONSTRAINT_ONLY,
) -> InsufficiencyRemedy:
    """Explain the rejection a certificate records.

    A certificate is the artifact a relying party actually holds, so this is
    the path that matters in practice.  The record's own bindings are verified
    first: a certificate whose digest, embedded bindings, or deterministic
    replay do not hold is refused rather than explained, because conditions
    derived from a record that is not what it claims would be attributed to a
    claim nobody made.
    """

    if type(certificate) is not EvidenceCertificate:
        raise ModelValidationError("certificate must be an EvidenceCertificate")
    if type(disclosure) is not DisclosureLevel:
        raise ModelValidationError("disclosure must be a DisclosureLevel")

    verification = verify_evidence_certificate(certificate)
    failed = [
        name for name in _REQUIRED_CERTIFICATE_DIMENSIONS if getattr(verification, name) is not True
    ]
    if failed:
        raise ModelValidationError(
            "a certificate whose bindings do not hold cannot be explained; failed dimensions: "
            + ", ".join(failed)
        )

    payload = certificate.certificate
    request = payload.request
    context = payload.trusted_profile_context
    decision = evaluate_negative_claim(request, context)
    remedy = derive_remedy(decision, request, context, disclosure=disclosure)
    return InsufficiencyRemedy(
        disclosure=remedy.disclosure,
        input_digest=remedy.input_digest,
        evaluated_at=remedy.evaluated_at,
        items=remedy.items,
        limitations=remedy.limitations
        + (
            "This remedy explains a replayed certificate. Replay establishes that the record "
            "reproduces its own decision; it does not authenticate the issuer, prove source "
            "truth, or establish current reliance eligibility.",
        ),
        certificate_digest=certificate.certificate_digest,
    )
