"""Deterministic policy gate for scoped negative claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import re
from typing import Any, Mapping

from .canonical import CANONICALIZATION_PROFILE, DIGEST_ALGORITHM, canonical_digest
from .coverage import CoverageAssessment, CoveragePolicy, evaluate_coverage
from .models import (
    ClaimMode,
    EvidenceEnvelope,
    EvidenceState,
    ModelValidationError,
    _nonnegative_int,
    _validate_aware_datetime,
    bounded_single_line,
    datetime_to_json,
    parse_datetime,
)


MAX_SUBJECT_LENGTH = 160
_ABSOLUTE_SUBJECT_PATTERN = re.compile(
    r"\b(?:nothing|none|anywhere|everywhere|always|never)\b"
    r"|\bno\b.{0,80}\bexists?\b"
    r"|\bdo(?:es)?\s+not\s+exist\b",
    re.IGNORECASE,
)


class GateReason(str, Enum):
    ABSOLUTE_NEGATIVE_UNSUPPORTED = "ABSOLUTE_NEGATIVE_UNSUPPORTED"
    STATE_NOT_ABSENT_WITHIN_SCOPE = "STATE_NOT_ABSENT_WITHIN_SCOPE"
    NONZERO_MATCHES = "NONZERO_MATCHES"
    COVERAGE_POLICY_NOT_MET = "COVERAGE_POLICY_NOT_MET"
    ENVELOPE_ERRORS_PRESENT = "ENVELOPE_ERRORS_PRESENT"
    EVALUATION_PRECEDES_OBSERVATION = "EVALUATION_PRECEDES_OBSERVATION"
    VALIDITY_UNDECLARED = "VALIDITY_UNDECLARED"
    RESULT_EXPIRED = "RESULT_EXPIRED"
    OBSERVATION_TOO_OLD = "OBSERVATION_TOO_OLD"
    INDEX_TIMESTAMP_UNDECLARED = "INDEX_TIMESTAMP_UNDECLARED"
    INDEX_TIME_AFTER_EVALUATION = "INDEX_TIME_AFTER_EVALUATION"
    INDEX_TOO_OLD = "INDEX_TOO_OLD"


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
    return whole_seconds > limit or (
        whole_seconds == limit and value.microseconds > 0
    )


@dataclass(frozen=True, slots=True)
class NegativeClaimPolicy:
    coverage: CoveragePolicy = field(default_factory=CoveragePolicy)
    require_valid_until: bool = True
    max_observation_age_seconds: int | None = None
    require_index_as_of: bool = False
    max_index_age_seconds: int | None = None
    reject_envelope_errors: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.coverage, CoveragePolicy):
            raise ModelValidationError("policy.coverage must be a CoveragePolicy")
        for name in ("require_valid_until", "require_index_as_of", "reject_envelope_errors"):
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
        _optional_seconds(
            self.max_observation_age_seconds, "policy.max_observation_age_seconds"
        )
        _optional_seconds(self.max_index_age_seconds, "policy.max_index_age_seconds")

    @classmethod
    def from_dict(cls, value: Any) -> "NegativeClaimPolicy":
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise ModelValidationError("policy must be a JSON object")
        allowed = {
            "coverage",
            "require_valid_until",
            "max_observation_age_seconds",
            "require_index_as_of",
            "max_index_age_seconds",
            "reject_envelope_errors",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ModelValidationError(f"policy has unknown fields: {', '.join(unknown)}")
        return cls(
            coverage=CoveragePolicy.from_dict(value.get("coverage")),
            require_valid_until=_strict_bool(
                value.get("require_valid_until"), "policy.require_valid_until", True
            ),
            max_observation_age_seconds=_optional_seconds(
                value.get("max_observation_age_seconds"),
                "policy.max_observation_age_seconds",
            ),
            require_index_as_of=_strict_bool(
                value.get("require_index_as_of"), "policy.require_index_as_of", False
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
            "coverage": self.coverage.to_dict(),
            "require_valid_until": self.require_valid_until,
            "max_observation_age_seconds": self.max_observation_age_seconds,
            "require_index_as_of": self.require_index_as_of,
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
        normalized_subject = bounded_single_line(
            self.subject, "subject", max_length=MAX_SUBJECT_LENGTH
        )
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
        subject = bounded_single_line(
            value.get("subject"), "request.subject", max_length=MAX_SUBJECT_LENGTH
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
    qualified_claim: str | None
    limitations: tuple[str, ...]
    input_digest: str
    canonicalization_profile: str = CANONICALIZATION_PROFILE
    digest_algorithm: str = DIGEST_ALGORITHM

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "decision": self.decision,
            "reasons": [reason.value for reason in self.reasons],
            "coverage": self.coverage.to_dict(),
            "qualified_claim": self.qualified_claim,
            "limitations": list(self.limitations),
            "input_digest": self.input_digest,
            "canonicalization_profile": self.canonicalization_profile,
            "digest_algorithm": self.digest_algorithm,
        }


def _digest_request(request: NegativeClaimRequest) -> str:
    return canonical_digest(request.to_dict())


def _qualified_claim(
    request: NegativeClaimRequest, assessment: CoverageAssessment
) -> str:
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
            " and the evidence is declared valid through "
            f"{datetime_to_json(envelope.valid_until)}."
        )
    return (
        f"The subject {json.dumps(request.subject, ensure_ascii=False)} had zero observed "
        "matches within the declared query scope "
        f"({envelope.query.qualification()}) as observed at "
        f"{datetime_to_json(envelope.observed_at)}, with coverage {coverage_text}."
        f" The claim was evaluated at {datetime_to_json(request.evaluated_at)}"
        f"{validity_text}"
        f"{permission_text} This conclusion is conditional on the declared scope, "
        "coverage, source state, and validity window; it is not proof of absence "
        "outside that scope."
    )


def evaluate_negative_claim(request: NegativeClaimRequest) -> GateDecision:
    """Return a deterministic allow/deny decision for a negative claim.

    Absolute claims are never authorized.  A scoped claim is authorized only
    when every explicit state, coverage, error, and freshness condition passes.
    The function never consults the wall clock; ``request.evaluated_at`` is a
    mandatory input and part of the decision digest.
    """

    if not isinstance(request, NegativeClaimRequest):
        raise ModelValidationError("request must be NegativeClaimRequest")
    envelope = request.envelope
    policy = request.policy
    assessment = evaluate_coverage(envelope.coverage, policy.coverage)
    reasons: list[GateReason] = []

    if request.mode is ClaimMode.ABSOLUTE:
        reasons.append(GateReason.ABSOLUTE_NEGATIVE_UNSUPPORTED)
    if envelope.state is not EvidenceState.ABSENT_WITHIN_SCOPE:
        reasons.append(GateReason.STATE_NOT_ABSENT_WITHIN_SCOPE)
    if envelope.matched_count != 0:
        reasons.append(GateReason.NONZERO_MATCHES)
    if not assessment.meets_policy:
        reasons.append(GateReason.COVERAGE_POLICY_NOT_MET)
    if policy.reject_envelope_errors and envelope.errors:
        reasons.append(GateReason.ENVELOPE_ERRORS_PRESENT)

    if request.evaluated_at < envelope.observed_at:
        reasons.append(GateReason.EVALUATION_PRECEDES_OBSERVATION)
    else:
        observation_age = request.evaluated_at - envelope.observed_at
        if (
            policy.max_observation_age_seconds is not None
            and _timedelta_exceeds_seconds(
                observation_age, policy.max_observation_age_seconds
            )
        ):
            reasons.append(GateReason.OBSERVATION_TOO_OLD)

    if envelope.valid_until is None:
        if policy.require_valid_until:
            reasons.append(GateReason.VALIDITY_UNDECLARED)
    elif request.evaluated_at > envelope.valid_until:
        reasons.append(GateReason.RESULT_EXPIRED)

    index_as_of = envelope.source.index_as_of
    if index_as_of is None:
        if policy.require_index_as_of or policy.max_index_age_seconds is not None:
            reasons.append(GateReason.INDEX_TIMESTAMP_UNDECLARED)
    elif index_as_of > request.evaluated_at:
        reasons.append(GateReason.INDEX_TIME_AFTER_EVALUATION)
    elif (
        policy.max_index_age_seconds is not None
        and _timedelta_exceeds_seconds(
            request.evaluated_at - index_as_of,
            policy.max_index_age_seconds,
        )
    ):
        reasons.append(GateReason.INDEX_TOO_OLD)

    allowed = not reasons
    limitations = (
        "The decision is conditional on source-declared scope and coverage evidence.",
        "ABSENT_WITHIN_SCOPE never proves global or absolute absence.",
        "The gate does not independently verify source honesty or inaccessible data.",
        "The SHA-256 input digest is integrity metadata, not a signature; mutation detection requires a trusted expected digest.",
    )
    return GateDecision(
        allowed=allowed,
        decision="PERMIT_SCOPED_NEGATIVE" if allowed else "REJECT_NEGATIVE",
        reasons=tuple(reasons),
        coverage=assessment,
        qualified_claim=_qualified_claim(request, assessment) if allowed else None,
        limitations=limitations,
        input_digest=_digest_request(request),
    )
