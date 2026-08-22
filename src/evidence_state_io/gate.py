"""Deterministic policy gate for scoped negative claims."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Mapping

from .canonical import CANONICALIZATION_PROFILE, DIGEST_ALGORITHM, canonical_digest
from .coverage import CoverageAssessment, CoveragePolicy, evaluate_coverage
from .models import (
    ClaimMode,
    EvidenceEnvelope,
    EvidenceState,
    ModelValidationError,
    SourceObservationStatus,
    SourceRole,
    _concrete_declaration,
    _nonnegative_int,
    _validate_aware_datetime,
    bounded_ascii_identifier,
    datetime_to_json,
    parse_datetime,
)
from .profiles import (
    ProfileAssessment,
    ProfileIssueCode,
    TrustedProfileContext,
    evaluate_profile_governance,
)
from .sources import (
    SourceAccountingAssessment,
    SourceIssueCode,
    evaluate_source_accounting,
)

MAX_SUBJECT_LENGTH = 160
DEFAULT_POLICY_ID = "esio-p0-safety-floor"
DEFAULT_POLICY_VERSION = "1.0-candidate.4"
EVALUATOR_VERSION = "esio-evaluator-1.0-candidate.5"
EVALUATION_INPUT_SCHEMA = "esio-evaluation-input/1.0-candidate.2"
_ABSOLUTE_SUBJECT_PATTERN = re.compile(
    r"\b(?:nothing|none|anywhere|everywhere|always|never)\b"
    r"|\bno\b.{0,80}\bexists?\b"
    r"|\bdo(?:es)?\s+not\s+exist\b",
    re.IGNORECASE,
)


class GateReason(str, Enum):
    PROFILE_REFERENCE_UNDECLARED = "PROFILE_REFERENCE_UNDECLARED"
    PROFILE_TRUST_SELECTION_MISMATCH = "PROFILE_TRUST_SELECTION_MISMATCH"
    REGISTRY_SNAPSHOT_UNDECLARED = "REGISTRY_SNAPSHOT_UNDECLARED"
    REGISTRY_SNAPSHOT_IDENTITY_MISMATCH = "REGISTRY_SNAPSHOT_IDENTITY_MISMATCH"
    REGISTRY_SNAPSHOT_DIGEST_MISMATCH = "REGISTRY_SNAPSHOT_DIGEST_MISMATCH"
    REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED = "REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED"
    REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE = "REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE"
    REGISTRY_SNAPSHOT_EXPIRED = "REGISTRY_SNAPSHOT_EXPIRED"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_DIGEST_MISMATCH = "PROFILE_DIGEST_MISMATCH"
    PROFILE_ISSUER_UNTRUSTED = "PROFILE_ISSUER_UNTRUSTED"
    PROFILE_AUTHORITY_UNTRUSTED = "PROFILE_AUTHORITY_UNTRUSTED"
    PROFILE_NOT_YET_EFFECTIVE = "PROFILE_NOT_YET_EFFECTIVE"
    PROFILE_EXPIRED = "PROFILE_EXPIRED"
    PROFILE_REVOKED = "PROFILE_REVOKED"
    PROFILE_SOURCE_MISMATCH = "PROFILE_SOURCE_MISMATCH"
    PROFILE_ADAPTER_MISMATCH = "PROFILE_ADAPTER_MISMATCH"
    PROFILE_AUTHORIZATION_MISMATCH = "PROFILE_AUTHORIZATION_MISMATCH"
    PROFILE_POPULATION_MISMATCH = "PROFILE_POPULATION_MISMATCH"
    PROFILE_QUERY_APPLICABILITY_MISMATCH = "PROFILE_QUERY_APPLICABILITY_MISMATCH"
    PROFILE_DETECTION_ASSUMPTIONS_MISMATCH = "PROFILE_DETECTION_ASSUMPTIONS_MISMATCH"
    PROFILE_COVERAGE_BASIS_MISMATCH = "PROFILE_COVERAGE_BASIS_MISMATCH"
    PROFILE_RETENTION_EXCEEDED = "PROFILE_RETENTION_EXCEEDED"
    PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY = "PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY"
    PROFILE_OBSERVATION_TOO_OLD = "PROFILE_OBSERVATION_TOO_OLD"
    PROFILE_INDEX_TOO_OLD = "PROFILE_INDEX_TOO_OLD"
    FINALITY_HORIZON_PROFILE_MISMATCH = "FINALITY_HORIZON_PROFILE_MISMATCH"
    ABSOLUTE_NEGATIVE_UNSUPPORTED = "ABSOLUTE_NEGATIVE_UNSUPPORTED"
    STATE_NOT_ABSENT_WITHIN_SCOPE = "STATE_NOT_ABSENT_WITHIN_SCOPE"
    NONZERO_MATCHES = "NONZERO_MATCHES"
    COVERAGE_POLICY_NOT_MET = "COVERAGE_POLICY_NOT_MET"
    ENVELOPE_ERRORS_PRESENT = "ENVELOPE_ERRORS_PRESENT"
    EVALUATION_PRECEDES_OBSERVATION = "EVALUATION_PRECEDES_OBSERVATION"
    VALIDITY_UNDECLARED = "VALIDITY_UNDECLARED"
    RESULT_EXPIRED = "RESULT_EXPIRED"
    OBSERVATION_TOO_OLD = "OBSERVATION_TOO_OLD"
    FINALITY_HORIZON_UNDECLARED = "FINALITY_HORIZON_UNDECLARED"
    INDEX_TIMESTAMP_UNDECLARED = "INDEX_TIMESTAMP_UNDECLARED"
    INDEX_TIME_AFTER_EVALUATION = "INDEX_TIME_AFTER_EVALUATION"
    INDEX_PRECEDES_QUERY_END = "INDEX_PRECEDES_QUERY_END"
    INDEX_PRECEDES_FINALITY_HORIZON = "INDEX_PRECEDES_FINALITY_HORIZON"
    INDEX_TOO_OLD = "INDEX_TOO_OLD"
    REQUIRED_SOURCE_MISSING = "REQUIRED_SOURCE_MISSING"
    REQUIRED_SOURCE_NOT_OBSERVED = "REQUIRED_SOURCE_NOT_OBSERVED"
    REQUIRED_SOURCE_INACCESSIBLE = "REQUIRED_SOURCE_INACCESSIBLE"
    REQUIRED_SOURCE_PENDING = "REQUIRED_SOURCE_PENDING"
    REQUIRED_SOURCE_STALE = "REQUIRED_SOURCE_STALE"
    REQUIRED_SOURCE_FAILED = "REQUIRED_SOURCE_FAILED"
    REQUIRED_SOURCE_CONTRADICTORY = "REQUIRED_SOURCE_CONTRADICTORY"
    REQUIRED_SOURCE_STATUS_UNKNOWN = "REQUIRED_SOURCE_STATUS_UNKNOWN"
    REQUIRED_SOURCE_IDENTITY_MISMATCH = "REQUIRED_SOURCE_IDENTITY_MISMATCH"
    REQUIRED_SOURCE_ADAPTER_MISMATCH = "REQUIRED_SOURCE_ADAPTER_MISMATCH"
    REQUIRED_SOURCE_AUTHORIZATION_MISMATCH = "REQUIRED_SOURCE_AUTHORIZATION_MISMATCH"
    REQUIRED_SOURCE_POPULATION_MISMATCH = "REQUIRED_SOURCE_POPULATION_MISMATCH"
    REQUIRED_SOURCE_ERRORS_PRESENT = "REQUIRED_SOURCE_ERRORS_PRESENT"


_SOURCE_REASON_MAP = {
    SourceIssueCode.REQUIRED_SOURCE_MISSING: GateReason.REQUIRED_SOURCE_MISSING,
    SourceIssueCode.REQUIRED_SOURCE_NOT_OBSERVED: GateReason.REQUIRED_SOURCE_NOT_OBSERVED,
    SourceIssueCode.REQUIRED_SOURCE_INACCESSIBLE: GateReason.REQUIRED_SOURCE_INACCESSIBLE,
    SourceIssueCode.REQUIRED_SOURCE_PENDING: GateReason.REQUIRED_SOURCE_PENDING,
    SourceIssueCode.REQUIRED_SOURCE_STALE: GateReason.REQUIRED_SOURCE_STALE,
    SourceIssueCode.REQUIRED_SOURCE_FAILED: GateReason.REQUIRED_SOURCE_FAILED,
    SourceIssueCode.REQUIRED_SOURCE_CONTRADICTORY: GateReason.REQUIRED_SOURCE_CONTRADICTORY,
    SourceIssueCode.REQUIRED_SOURCE_STATUS_UNKNOWN: GateReason.REQUIRED_SOURCE_STATUS_UNKNOWN,
    SourceIssueCode.REQUIRED_SOURCE_IDENTITY_MISMATCH: GateReason.REQUIRED_SOURCE_IDENTITY_MISMATCH,
    SourceIssueCode.REQUIRED_SOURCE_ADAPTER_MISMATCH: GateReason.REQUIRED_SOURCE_ADAPTER_MISMATCH,
    SourceIssueCode.REQUIRED_SOURCE_AUTHORIZATION_MISMATCH: GateReason.REQUIRED_SOURCE_AUTHORIZATION_MISMATCH,
    SourceIssueCode.REQUIRED_SOURCE_POPULATION_MISMATCH: GateReason.REQUIRED_SOURCE_POPULATION_MISMATCH,
    SourceIssueCode.REQUIRED_SOURCE_ERRORS_PRESENT: GateReason.REQUIRED_SOURCE_ERRORS_PRESENT,
}

_PROFILE_REASON_MAP = {code: GateReason(code.value) for code in ProfileIssueCode}


def _strict_bool(value: Any, path: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ModelValidationError(f"{path} must be a boolean")
    return value


def _optional_seconds(value: Any, path: str) -> int | None:
    if value is None:
        return None
    return _nonnegative_int(value, path)


def _timedelta_exceeds_seconds(value: timedelta, limit: int) -> bool:
    """Compare exactly without converting microseconds through binary floats."""

    whole_seconds = value.days * 86_400 + value.seconds
    return whole_seconds > limit or (whole_seconds == limit and value.microseconds > 0)


@dataclass(frozen=True, slots=True)
class NegativeClaimPolicy:
    policy_id: str = DEFAULT_POLICY_ID
    policy_version: str = DEFAULT_POLICY_VERSION
    coverage: CoveragePolicy = field(default_factory=CoveragePolicy)
    require_valid_until: bool = True
    max_observation_age_seconds: int | None = None
    require_index_as_of: bool = True
    require_finality_horizon: bool = True
    max_index_age_seconds: int | None = None
    reject_envelope_errors: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "policy_id", bounded_ascii_identifier(self.policy_id, "policy.policy_id")
        )
        object.__setattr__(
            self,
            "policy_version",
            bounded_ascii_identifier(self.policy_version, "policy.policy_version"),
        )
        if self.policy_id != DEFAULT_POLICY_ID or self.policy_version != DEFAULT_POLICY_VERSION:
            raise ModelValidationError(
                "policy_id and policy_version must identify the supported "
                f"{DEFAULT_POLICY_ID} {DEFAULT_POLICY_VERSION} contract"
            )
        if not isinstance(self.coverage, CoveragePolicy):
            raise ModelValidationError("policy.coverage must be a CoveragePolicy")
        for name in (
            "require_valid_until",
            "require_index_as_of",
            "require_finality_horizon",
            "reject_envelope_errors",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ModelValidationError(f"policy.{name} must be a boolean")
        if self.require_valid_until is not True:
            raise ModelValidationError(
                "policy.require_valid_until cannot relax the P0 safety floor"
            )
        if self.reject_envelope_errors is not True:
            raise ModelValidationError(
                "policy.reject_envelope_errors cannot relax the P0 safety floor"
            )
        if self.require_index_as_of is not True:
            raise ModelValidationError(
                "policy.require_index_as_of cannot relax the P0 safety floor"
            )
        if self.require_finality_horizon is not True:
            raise ModelValidationError(
                "policy.require_finality_horizon cannot relax the P0 safety floor"
            )
        _optional_seconds(self.max_observation_age_seconds, "policy.max_observation_age_seconds")
        _optional_seconds(self.max_index_age_seconds, "policy.max_index_age_seconds")

    @classmethod
    def from_dict(cls, value: Any) -> "NegativeClaimPolicy":
        if not isinstance(value, Mapping):
            raise ModelValidationError("policy must be a JSON object")
        allowed = {
            "policy_id",
            "policy_version",
            "coverage",
            "require_valid_until",
            "max_observation_age_seconds",
            "require_index_as_of",
            "require_finality_horizon",
            "max_index_age_seconds",
            "reject_envelope_errors",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ModelValidationError(f"policy has unknown fields: {', '.join(unknown)}")
        missing = sorted({"policy_id", "policy_version"} - set(value))
        if missing:
            raise ModelValidationError("policy is missing required fields: " + ", ".join(missing))
        return cls(
            policy_id=bounded_ascii_identifier(value.get("policy_id"), "policy.policy_id"),
            policy_version=bounded_ascii_identifier(
                value.get("policy_version"), "policy.policy_version"
            ),
            coverage=CoveragePolicy.from_dict(value.get("coverage")),
            require_valid_until=_strict_bool(
                value.get("require_valid_until"), "policy.require_valid_until", True
            ),
            max_observation_age_seconds=_optional_seconds(
                value.get("max_observation_age_seconds"),
                "policy.max_observation_age_seconds",
            ),
            require_index_as_of=_strict_bool(
                value.get("require_index_as_of"), "policy.require_index_as_of", True
            ),
            require_finality_horizon=_strict_bool(
                value.get("require_finality_horizon"),
                "policy.require_finality_horizon",
                True,
            ),
            max_index_age_seconds=_optional_seconds(
                value.get("max_index_age_seconds"), "policy.max_index_age_seconds"
            ),
            reject_envelope_errors=_strict_bool(
                value.get("reject_envelope_errors"),
                "policy.reject_envelope_errors",
                True,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "coverage": self.coverage.to_dict(),
            "require_valid_until": self.require_valid_until,
            "max_observation_age_seconds": self.max_observation_age_seconds,
            "require_index_as_of": self.require_index_as_of,
            "require_finality_horizon": self.require_finality_horizon,
            "max_index_age_seconds": self.max_index_age_seconds,
            "reject_envelope_errors": self.reject_envelope_errors,
        }


@dataclass(frozen=True, slots=True)
class NegativeClaimRequest:
    envelope: EvidenceEnvelope
    subject: str
    mode: ClaimMode
    evaluated_at: datetime
    policy: NegativeClaimPolicy = field(default_factory=NegativeClaimPolicy)

    def __post_init__(self) -> None:
        if not isinstance(self.envelope, EvidenceEnvelope):
            raise ModelValidationError("envelope must be EvidenceEnvelope")
        if not isinstance(self.policy, NegativeClaimPolicy):
            raise ModelValidationError("policy must be NegativeClaimPolicy")
        normalized_subject = _concrete_declaration(
            self.subject,
            "subject",
            reject_unbounded=True,
        )
        if len(normalized_subject) > MAX_SUBJECT_LENGTH:
            raise ModelValidationError(f"subject exceeds the {MAX_SUBJECT_LENGTH}-character limit")
        if _ABSOLUTE_SUBJECT_PATTERN.search(normalized_subject):
            raise ModelValidationError(
                "subject contains a prohibited universal or absolute-negative formulation"
            )
        object.__setattr__(self, "subject", normalized_subject)
        if not isinstance(self.mode, ClaimMode):
            raise ModelValidationError("mode must be a ClaimMode")
        object.__setattr__(
            self,
            "evaluated_at",
            _validate_aware_datetime(self.evaluated_at, "evaluated_at"),
        )
        if self.envelope.observed_at > self.evaluated_at:
            raise ModelValidationError("envelope.observed_at must not be after evaluated_at")

    @classmethod
    def from_dict(cls, value: Any) -> "NegativeClaimRequest":
        if not isinstance(value, Mapping):
            raise ModelValidationError("request must be a JSON object")
        allowed = {"envelope", "subject", "mode", "evaluated_at", "policy"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ModelValidationError(f"request has unknown fields: {', '.join(unknown)}")
        subject = _concrete_declaration(
            value.get("subject"),
            "request.subject",
            reject_unbounded=True,
        )
        if len(subject) > MAX_SUBJECT_LENGTH:
            raise ModelValidationError(
                f"request.subject exceeds the {MAX_SUBJECT_LENGTH}-character limit"
            )
        try:
            mode = ClaimMode(value.get("mode"))
        except (TypeError, ValueError) as exc:
            raise ModelValidationError("request.mode must be SCOPED or ABSOLUTE") from exc
        return cls(
            envelope=EvidenceEnvelope.from_dict(value.get("envelope")),
            subject=subject,
            mode=mode,
            evaluated_at=parse_datetime(value.get("evaluated_at"), "request.evaluated_at"),
            policy=NegativeClaimPolicy.from_dict(value.get("policy")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope": self.envelope.to_dict(),
            "subject": self.subject,
            "mode": self.mode.value,
            "evaluated_at": datetime_to_json(self.evaluated_at),
            "policy": self.policy.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    decision: str
    reasons: tuple[GateReason, ...]
    coverage: CoverageAssessment
    source_accounting: SourceAccountingAssessment
    profile: ProfileAssessment
    qualified_claim: str | None
    limitations: tuple[str, ...]
    input_digest: str
    canonicalization_profile: str = CANONICALIZATION_PROFILE
    digest_algorithm: str = DIGEST_ALGORITHM
    evaluator_version: str = EVALUATOR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "reasons": [reason.value for reason in self.reasons],
            "coverage": self.coverage.to_dict(),
            "source_accounting": self.source_accounting.to_dict(),
            "profile": self.profile.to_dict(),
            "qualified_claim": self.qualified_claim,
            "limitations": list(self.limitations),
            "input_digest": self.input_digest,
            "canonicalization_profile": self.canonicalization_profile,
            "digest_algorithm": self.digest_algorithm,
            "evaluator_version": self.evaluator_version,
        }


def _digest_evaluation_input(
    request: NegativeClaimRequest,
    context: TrustedProfileContext | None,
) -> str:
    return canonical_digest(
        {
            "evaluation_input_schema": EVALUATION_INPUT_SCHEMA,
            "request": request.to_dict(),
            "trusted_profile_context": (None if context is None else context.to_dict()),
        }
    )


def _qualified_claim(request: NegativeClaimRequest, assessment: CoverageAssessment) -> str:
    envelope = request.envelope
    lower_bound = assessment.lower_bound
    coverage_text = "declared but unquantified"
    if lower_bound is not None:
        coverage_text = f"at least {lower_bound * 100:.3f}%"
    permission_text = ""
    if envelope.coverage.permission_limited:
        permission_text = (
            " Only data accessible within the declared authorization boundary were evaluated."
        )
    validity_text = "."
    if envelope.valid_until:
        validity_text = (
            " and the source-declared envelope boundary is "
            f"{datetime_to_json(envelope.valid_until)}; governed observation "
            "or index freshness may expire earlier and requires reevaluation."
        )
    required_sources = [
        requirement.to_dict()
        for requirement in envelope.query.source_requirements
        if requirement.role is SourceRole.REQUIRED
    ]
    source_text = json.dumps(
        required_sources,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    required_source = next(
        requirement
        for requirement in envelope.query.source_requirements
        if requirement.role is SourceRole.REQUIRED
    )
    source_observation = next(
        observation
        for observation in envelope.source_observations
        if observation.source_id == required_source.source_id
        and observation.status is SourceObservationStatus.OBSERVED
    )
    finality_horizon = required_source.finality_horizon
    index_as_of = source_observation.descriptor.index_as_of
    assert finality_horizon is not None
    assert index_as_of is not None
    finality_text = (
        " The source reported an index state at "
        f"{datetime_to_json(index_as_of)}, which reached the declared finality "
        f"horizon {datetime_to_json(finality_horizon)}."
    )
    return (
        f"The subject {json.dumps(request.subject, ensure_ascii=False)} had zero observed "
        "matches within the declared query scope "
        f"({envelope.query.qualification()}) as observed at "
        f"{datetime_to_json(envelope.observed_at)}, with coverage {coverage_text}."
        f" The declared required-source set was {source_text}."
        f" The claim was evaluated at {datetime_to_json(request.evaluated_at)}"
        f"{validity_text}"
        f"{permission_text}{finality_text} This conclusion is conditional on the declared scope, "
        "coverage, source state, and validity window; it is not proof of absence "
        "outside that scope. The finality horizon was derived from the exact "
        "locally governed profile pinned by the query. That configuration binding "
        "does not authenticate the profile assertions or prove ingestion completeness."
    )


def _insufficient_evidence_statement(
    request: NegativeClaimRequest,
    reasons: tuple[GateReason, ...],
) -> str:
    """Render a rejection without asserting the positive opposite."""

    reason_text = ", ".join(reason.value for reason in reasons)
    return (
        "The evidence is insufficient to support the requested negative claim "
        f"for subject {json.dumps(request.subject, ensure_ascii=False)} within "
        f"the declared query scope. Material reasons: {reason_text}. This "
        "rejection does not establish that the positive opposite is true."
    )


def evaluate_negative_claim(
    request: NegativeClaimRequest,
    context: TrustedProfileContext | None = None,
) -> GateDecision:
    """Return a deterministic allow/deny decision for a negative claim.

    Absolute claims are never authorized.  A scoped claim is authorized only
    when every explicit state, coverage, error, and freshness condition passes.
    The function never consults the wall clock; ``request.evaluated_at`` is a
    mandatory input and part of the decision digest.
    """

    if type(request) is not NegativeClaimRequest:
        raise ModelValidationError("request must be NegativeClaimRequest")
    # Frozen dataclasses are not a security boundary: ``object.__setattr__`` can
    # still corrupt a typed instance.  Reparse its public form before any gate
    # decision so the library and JSON paths enforce the same invariants.
    request = NegativeClaimRequest.from_dict(request.to_dict())
    if context is not None:
        if type(context) is not TrustedProfileContext:
            raise ModelValidationError("context must be TrustedProfileContext or null")
        context = TrustedProfileContext.from_dict(context.to_dict())
    envelope = request.envelope
    policy = request.policy
    assessment = evaluate_coverage(envelope.coverage, policy.coverage)
    source_assessment = evaluate_source_accounting(
        envelope.query.source_requirements,
        envelope.source_observations,
    )
    profile_assessment = evaluate_profile_governance(
        envelope,
        request.evaluated_at,
        context,
    )
    reasons: list[GateReason] = []

    def add_reason(reason: GateReason) -> None:
        if reason not in reasons:
            reasons.append(reason)

    for profile_issue in profile_assessment.issues:
        add_reason(_PROFILE_REASON_MAP[profile_issue.code])

    if request.mode is ClaimMode.ABSOLUTE:
        add_reason(GateReason.ABSOLUTE_NEGATIVE_UNSUPPORTED)
    if envelope.state is not EvidenceState.ABSENT_WITHIN_SCOPE:
        add_reason(GateReason.STATE_NOT_ABSENT_WITHIN_SCOPE)
    if envelope.matched_count != 0:
        add_reason(GateReason.NONZERO_MATCHES)
    if not assessment.meets_policy:
        add_reason(GateReason.COVERAGE_POLICY_NOT_MET)
    if policy.reject_envelope_errors and envelope.errors:
        add_reason(GateReason.ENVELOPE_ERRORS_PRESENT)
    for source_issue in source_assessment.issues:
        add_reason(_SOURCE_REASON_MAP[source_issue.code])

    if request.evaluated_at < envelope.observed_at:
        add_reason(GateReason.EVALUATION_PRECEDES_OBSERVATION)
    else:
        observation_age = request.evaluated_at - envelope.observed_at
        if policy.max_observation_age_seconds is not None and _timedelta_exceeds_seconds(
            observation_age, policy.max_observation_age_seconds
        ):
            add_reason(GateReason.OBSERVATION_TOO_OLD)

    if envelope.valid_until is None:
        if policy.require_valid_until:
            add_reason(GateReason.VALIDITY_UNDECLARED)
    elif request.evaluated_at > envelope.valid_until:
        add_reason(GateReason.RESULT_EXPIRED)

    required_requirements = tuple(
        requirement
        for requirement in envelope.query.source_requirements
        if requirement.role is SourceRole.REQUIRED
    )
    observations_by_id = {
        observation.source_id: observation for observation in envelope.source_observations
    }
    for requirement in required_requirements:
        finality_horizon = requirement.finality_horizon
        if finality_horizon is None and policy.require_finality_horizon:
            add_reason(GateReason.FINALITY_HORIZON_UNDECLARED)

        observation = observations_by_id.get(requirement.source_id)
        if observation is None or observation.status is not SourceObservationStatus.OBSERVED:
            continue
        index_as_of = observation.descriptor.index_as_of
        if index_as_of is None:
            if policy.require_index_as_of or policy.max_index_age_seconds is not None:
                add_reason(GateReason.INDEX_TIMESTAMP_UNDECLARED)
        else:
            if index_as_of < envelope.query.time_end:
                add_reason(GateReason.INDEX_PRECEDES_QUERY_END)
            if finality_horizon is not None and index_as_of < finality_horizon:
                add_reason(GateReason.INDEX_PRECEDES_FINALITY_HORIZON)
            if index_as_of > request.evaluated_at:
                add_reason(GateReason.INDEX_TIME_AFTER_EVALUATION)
            elif policy.max_index_age_seconds is not None and _timedelta_exceeds_seconds(
                request.evaluated_at - index_as_of,
                policy.max_index_age_seconds,
            ):
                add_reason(GateReason.INDEX_TOO_OLD)

    allowed = not reasons
    limitations = (
        "The decision is conditional on source-declared evidence and a separately supplied, locally governed profile registry snapshot.",
        "ABSENT_WITHIN_SCOPE never proves global or absolute absence.",
        "The gate does not independently verify source honesty or inaccessible data.",
        "The current evaluator does not establish multi-source coverage composition.",
        "The gate compares a source-reported index time with a profile-derived finality horizon; profile governance does not attest source behavior and does not prove ingestion completeness.",
        "Profile owner, issuer, and approval identities are declarative under P0 configuration custody and are not cryptographically authenticated.",
        "The SHA-256 composite input digest is integrity metadata, not a signature; mutation detection requires a separately trusted expected digest.",
    )
    return GateDecision(
        allowed=allowed,
        decision="PERMIT_SCOPED_NEGATIVE" if allowed else "REJECT_NEGATIVE",
        reasons=tuple(reasons),
        coverage=assessment,
        source_accounting=source_assessment,
        profile=profile_assessment,
        qualified_claim=(
            _qualified_claim(request, assessment)
            if allowed
            else _insufficient_evidence_statement(request, tuple(reasons))
        ),
        limitations=limitations,
        input_digest=_digest_evaluation_input(request, context),
    )
