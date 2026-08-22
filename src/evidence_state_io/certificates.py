"""Deterministic unsigned evidence certificates and replay verification.

The candidate certificate is a self-contained replay record.  Its SHA-256
digest is integrity metadata, not a signature, issuer authentication,
authorization token, trusted timestamp, or proof that a source declaration is
true.  Construction owns evaluation and performs no filesystem, Git, network,
or wall-clock reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from hmac import compare_digest
import json
import math
import re
from typing import Any, Mapping, Sequence

from .canonical import (
    CANONICALIZATION_PROFILE,
    DIGEST_ALGORITHM,
    canonical_digest,
    canonical_json_bytes,
)
from .coverage import CoverageIssue
from .gate import (
    DEFAULT_POLICY_ID,
    DEFAULT_POLICY_VERSION,
    EVALUATION_INPUT_SCHEMA,
    EVALUATOR_VERSION,
    GateDecision,
    GateReason,
    NegativeClaimRequest,
    evaluate_negative_claim,
)
from .models import (
    CoverageProfileReference,
    ModelValidationError,
    SourceObservationStatus,
    _mapping,
    _reject_unknown,
    _require_fields,
    _sha256_digest,
    _validate_aware_datetime,
    bounded_ascii_identifier,
    bounded_single_line,
    datetime_to_json,
    parse_datetime,
)
from .profiles import ProfileIssueCode, TrustedProfileContext
from .sources import SourceIssueCode


CERTIFICATE_FORMAT = "esio-evidence-certificate/1.0-candidate.2"
WIRE_SCHEMA_VERSION = "1.0"
IMPLEMENTATION_PACKAGE_NAME = "evidence-state-io"

_REVISION_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_VERSION_PATTERN = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9a-z]+(?:[.-][0-9a-z]+)*)?$"
)


class EvidenceOrigin(str, Enum):
    """Descriptive provenance; no value upgrades the evidence decision."""

    SYNTHETIC = "SYNTHETIC"
    REPLAYED = "REPLAYED"
    LAB_OBSERVED = "LAB_OBSERVED"
    SHADOW_OBSERVED = "SHADOW_OBSERVED"
    EXTERNALLY_REPRODUCED = "EXTERNALLY_REPRODUCED"
    OPERATIONAL = "OPERATIONAL"


class WorkingTreeState(str, Enum):
    """Explicit implementation provenance supplied without an ambient Git read."""

    CLEAN = "CLEAN"
    DIRTY = "DIRTY"
    UNBOUND = "UNBOUND"


@dataclass(frozen=True, slots=True)
class ImplementationIdentity:
    """An asserted implementation identity, not an authenticated signer."""

    package_name: str
    package_version: str
    repository_revision: str | None
    working_tree_state: WorkingTreeState

    def __post_init__(self) -> None:
        package_name = bounded_ascii_identifier(
            self.package_name, "implementation.package_name"
        )
        if package_name != IMPLEMENTATION_PACKAGE_NAME:
            raise ModelValidationError(
                "implementation.package_name must identify evidence-state-io"
            )
        object.__setattr__(self, "package_name", package_name)
        version = bounded_single_line(
            self.package_version,
            "implementation.package_version",
            max_length=64,
        )
        if not version.isascii() or not _VERSION_PATTERN.fullmatch(version):
            raise ModelValidationError(
                "implementation.package_version must be a lowercase semantic version"
            )
        object.__setattr__(self, "package_version", version)
        if not isinstance(self.working_tree_state, WorkingTreeState):
            raise ModelValidationError(
                "implementation.working_tree_state must be CLEAN, DIRTY, or UNBOUND"
            )
        if self.working_tree_state is WorkingTreeState.UNBOUND:
            if self.repository_revision is not None:
                raise ModelValidationError(
                    "an UNBOUND implementation requires a null repository_revision"
                )
        elif type(self.repository_revision) is not str or not _REVISION_PATTERN.fullmatch(
            self.repository_revision
        ):
            raise ModelValidationError(
                "a CLEAN or DIRTY implementation requires a full lowercase Git revision"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "ImplementationIdentity":
        data = _mapping(value, "implementation")
        allowed = {
            "package_name",
            "package_version",
            "repository_revision",
            "working_tree_state",
        }
        _reject_unknown(data, allowed, "implementation")
        _require_fields(data, allowed, "implementation")
        try:
            tree_state = WorkingTreeState(data["working_tree_state"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                "implementation.working_tree_state must be CLEAN, DIRTY, or UNBOUND"
            ) from exc
        revision = data["repository_revision"]
        if revision is not None and type(revision) is not str:
            raise ModelValidationError(
                "implementation.repository_revision must be a string or null"
            )
        return cls(
            package_name=data["package_name"],
            package_version=data["package_version"],
            repository_revision=revision,
            working_tree_state=tree_state,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_name": self.package_name,
            "package_version": self.package_version,
            "repository_revision": self.repository_revision,
            "working_tree_state": self.working_tree_state.value,
        }


@dataclass(frozen=True, slots=True)
class CertificateContextBinding:
    """Repeated governance identifiers that a verifier must cross-check."""

    context_digest: str
    registry_id: str
    snapshot_id: str
    snapshot_version: str
    snapshot_digest: str
    trust_selection_digest: str
    resolved_profile_references: tuple[CoverageProfileReference, ...]

    def __post_init__(self) -> None:
        for name in ("registry_id", "snapshot_id", "snapshot_version"):
            object.__setattr__(
                self,
                name,
                bounded_ascii_identifier(
                    getattr(self, name), f"context_binding.{name}"
                ),
            )
        for name in (
            "context_digest",
            "snapshot_digest",
            "trust_selection_digest",
        ):
            object.__setattr__(
                self,
                name,
                _sha256_digest(getattr(self, name), f"context_binding.{name}"),
            )
        if isinstance(self.resolved_profile_references, (str, bytes)) or not isinstance(
            self.resolved_profile_references, Sequence
        ):
            raise ModelValidationError(
                "context_binding.resolved_profile_references must be an array"
            )
        references = tuple(self.resolved_profile_references)
        if any(not isinstance(item, CoverageProfileReference) for item in references):
            raise ModelValidationError(
                "context_binding.resolved_profile_references must contain profile references"
            )
        identities = [
            (item.registry_id, item.profile_id, item.profile_version, item.profile_digest)
            for item in references
        ]
        if len(set(identities)) != len(identities):
            raise ModelValidationError(
                "context_binding.resolved_profile_references must not contain duplicates"
            )
        object.__setattr__(
            self,
            "resolved_profile_references",
            tuple(
                sorted(
                    references,
                    key=lambda item: (
                        item.registry_id,
                        item.profile_id,
                        item.profile_version,
                        item.profile_digest,
                    ),
                )
            ),
        )

    @classmethod
    def from_dict(cls, value: Any) -> "CertificateContextBinding":
        data = _mapping(value, "context_binding")
        allowed = {
            "context_digest",
            "registry_id",
            "snapshot_id",
            "snapshot_version",
            "snapshot_digest",
            "trust_selection_digest",
            "resolved_profile_references",
        }
        _reject_unknown(data, allowed, "context_binding")
        _require_fields(data, allowed, "context_binding")
        raw_references = data["resolved_profile_references"]
        if isinstance(raw_references, (str, bytes)) or not isinstance(
            raw_references, Sequence
        ):
            raise ModelValidationError(
                "context_binding.resolved_profile_references must be an array"
            )
        return cls(
            context_digest=_sha256_digest(
                data["context_digest"], "context_binding.context_digest"
            ),
            registry_id=data["registry_id"],
            snapshot_id=data["snapshot_id"],
            snapshot_version=data["snapshot_version"],
            snapshot_digest=_sha256_digest(
                data["snapshot_digest"], "context_binding.snapshot_digest"
            ),
            trust_selection_digest=_sha256_digest(
                data["trust_selection_digest"],
                "context_binding.trust_selection_digest",
            ),
            resolved_profile_references=tuple(
                CoverageProfileReference.from_dict(
                    item,
                    f"context_binding.resolved_profile_references[{index}]",
                )
                for index, item in enumerate(raw_references)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_digest": self.context_digest,
            "registry_id": self.registry_id,
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "snapshot_digest": self.snapshot_digest,
            "trust_selection_digest": self.trust_selection_digest,
            "resolved_profile_references": [
                item.to_dict() for item in self.resolved_profile_references
            ],
        }


def _required_sequence(value: Any, path: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ModelValidationError(f"{path} must be an array")
    return value


def _string_array(value: Any, path: str) -> list[str]:
    items = _required_sequence(value, path)
    result: list[str] = []
    for index, item in enumerate(items):
        if type(item) is not str:
            raise ModelValidationError(f"{path}[{index}] must be a string")
        result.append(item)
    return result


def _unit_interval_number(
    value: Any,
    path: str,
    *,
    allow_none: bool,
) -> None:
    if value is None and allow_none:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        suffix = " or null" if allow_none else ""
        raise ModelValidationError(f"{path} must be a number{suffix}")
    try:
        exact = value if isinstance(value, Decimal) else Decimal(str(value))
    except (ValueError, ArithmeticError) as exc:
        raise ModelValidationError(f"{path} must be a finite number in [0,1]") from exc
    if not exact.is_finite() or not Decimal(0) <= exact <= Decimal(1):
        raise ModelValidationError(f"{path} must be a finite number in [0,1]")


def _normalized_json_copy(value: Any, path: str = "decision") -> Any:
    """Copy JSON while rejecting Decimal-to-float precision collapse."""

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ModelValidationError(f"{path} contains a nonfinite number")
        try:
            normalized = float(value)
        except (OverflowError, ValueError) as exc:
            raise ModelValidationError(
                f"{path} contains a number outside the supported binary64 range"
            ) from exc
        if not math.isfinite(normalized) or Decimal(str(normalized)) != value:
            raise ModelValidationError(
                f"{path} contains a number that is not exactly preserved by the certificate JSON model"
            )
        return normalized
    if isinstance(value, str):
        if type(value) is not str:
            raise ModelValidationError(f"{path} must use plain JSON strings")
        return value
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ModelValidationError(f"{path} object keys must be plain strings")
        return {
            key: _normalized_json_copy(item, f"{path}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _normalized_json_copy(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    return value


def _validate_coverage_assessment(value: Any) -> None:
    data = _mapping(value, "decision.coverage")
    allowed = {"lower_bound", "meets_policy", "issues", "components"}
    _reject_unknown(data, allowed, "decision.coverage")
    _require_fields(data, allowed, "decision.coverage")
    _unit_interval_number(
        data["lower_bound"],
        "decision.coverage.lower_bound",
        allow_none=True,
    )
    if not isinstance(data["meets_policy"], bool):
        raise ModelValidationError("decision.coverage.meets_policy must be boolean")
    issues = _string_array(data["issues"], "decision.coverage.issues")
    valid_issues = {item.value for item in CoverageIssue}
    if any(item not in valid_issues for item in issues) or len(set(issues)) != len(issues):
        raise ModelValidationError(
            "decision.coverage.issues contains an unknown or duplicate reason"
        )
    for index, raw_component in enumerate(
        _required_sequence(data["components"], "decision.coverage.components")
    ):
        component = _mapping(raw_component, f"decision.coverage.components[{index}]")
        fields = {"name", "lower_bound", "basis"}
        _reject_unknown(component, fields, f"decision.coverage.components[{index}]")
        _require_fields(component, fields, f"decision.coverage.components[{index}]")
        if type(component["name"]) is not str or type(component["basis"]) is not str:
            raise ModelValidationError(
                "decision coverage component name and basis must be strings"
            )
        _unit_interval_number(
            component["lower_bound"],
            f"decision.coverage.components[{index}].lower_bound",
            allow_none=False,
        )


def _validate_source_assessment(value: Any) -> None:
    data = _mapping(value, "decision.source_accounting")
    allowed = {
        "required_source_ids",
        "observed_source_ids",
        "complete_source_ids",
        "issues",
        "meets_policy",
    }
    _reject_unknown(data, allowed, "decision.source_accounting")
    _require_fields(data, allowed, "decision.source_accounting")
    for name in (
        "required_source_ids",
        "observed_source_ids",
        "complete_source_ids",
    ):
        values = _string_array(data[name], f"decision.source_accounting.{name}")
        if len(set(values)) != len(values):
            raise ModelValidationError(
                f"decision.source_accounting.{name} must not contain duplicates"
            )
        for index, item in enumerate(values):
            bounded_ascii_identifier(
                item, f"decision.source_accounting.{name}[{index}]"
            )
    if not isinstance(data["meets_policy"], bool):
        raise ModelValidationError(
            "decision.source_accounting.meets_policy must be boolean"
        )
    seen: set[tuple[str, str]] = set()
    for index, raw_issue in enumerate(
        _required_sequence(data["issues"], "decision.source_accounting.issues")
    ):
        issue = _mapping(raw_issue, f"decision.source_accounting.issues[{index}]")
        fields = {"code", "source_id"}
        _reject_unknown(issue, fields, f"decision.source_accounting.issues[{index}]")
        _require_fields(issue, fields, f"decision.source_accounting.issues[{index}]")
        if issue["code"] not in {item.value for item in SourceIssueCode}:
            raise ModelValidationError(
                "decision.source_accounting issue has an unknown code"
            )
        source_id = bounded_ascii_identifier(
            issue["source_id"],
            f"decision.source_accounting.issues[{index}].source_id",
        )
        key = (issue["code"], source_id)
        if key in seen:
            raise ModelValidationError(
                "decision.source_accounting.issues must not contain duplicates"
            )
        seen.add(key)


def _validate_profile_assessment(value: Any) -> None:
    data = _mapping(value, "decision.profile")
    allowed = {
        "meets_policy",
        "issues",
        "resolved_profile_references",
        "registry_snapshot_digest",
        "trust_selection_digest",
    }
    _reject_unknown(data, allowed, "decision.profile")
    _require_fields(data, allowed, "decision.profile")
    if not isinstance(data["meets_policy"], bool):
        raise ModelValidationError("decision.profile.meets_policy must be boolean")
    seen_issues: set[tuple[str, str | None, str | None]] = set()
    for index, raw_issue in enumerate(
        _required_sequence(data["issues"], "decision.profile.issues")
    ):
        issue = _mapping(raw_issue, f"decision.profile.issues[{index}]")
        fields = {"code", "detail", "source_id", "profile_id"}
        _reject_unknown(issue, fields, f"decision.profile.issues[{index}]")
        _require_fields(issue, fields, f"decision.profile.issues[{index}]")
        if issue["code"] not in {item.value for item in ProfileIssueCode}:
            raise ModelValidationError("decision.profile issue has an unknown code")
        if type(issue["detail"]) is not str or not issue["detail"]:
            raise ModelValidationError("decision.profile issue detail must be a string")
        for field_name in ("source_id", "profile_id"):
            if issue[field_name] is not None:
                bounded_ascii_identifier(
                    issue[field_name],
                    f"decision.profile.issues[{index}].{field_name}",
                )
        key = (issue["code"], issue["source_id"], issue["profile_id"])
        if key in seen_issues:
            raise ModelValidationError("decision.profile.issues must not contain duplicates")
        seen_issues.add(key)
    references = _required_sequence(
        data["resolved_profile_references"],
        "decision.profile.resolved_profile_references",
    )
    for index, item in enumerate(references):
        CoverageProfileReference.from_dict(
            item, f"decision.profile.resolved_profile_references[{index}]"
        )
    for name in ("registry_snapshot_digest", "trust_selection_digest"):
        if data[name] is not None:
            _sha256_digest(data[name], f"decision.profile.{name}")


def _validated_decision_dict(value: Any) -> dict[str, Any]:
    data = _mapping(value, "decision")
    allowed = {
        "allowed",
        "decision",
        "reasons",
        "coverage",
        "source_accounting",
        "profile",
        "qualified_claim",
        "limitations",
        "input_digest",
        "canonicalization_profile",
        "digest_algorithm",
        "evaluator_version",
    }
    _reject_unknown(data, allowed, "decision")
    _require_fields(data, allowed, "decision")
    if not isinstance(data["allowed"], bool):
        raise ModelValidationError("decision.allowed must be boolean")
    expected_disposition = (
        "PERMIT_SCOPED_NEGATIVE" if data["allowed"] else "REJECT_NEGATIVE"
    )
    if data["decision"] != expected_disposition:
        raise ModelValidationError(
            "decision disposition must agree with the allowed field"
        )
    reasons = _string_array(data["reasons"], "decision.reasons")
    if any(item not in {reason.value for reason in GateReason} for item in reasons):
        raise ModelValidationError("decision.reasons contains an unknown reason code")
    if len(set(reasons)) != len(reasons):
        raise ModelValidationError("decision.reasons must not contain duplicates")
    _validate_coverage_assessment(data["coverage"])
    _validate_source_assessment(data["source_accounting"])
    _validate_profile_assessment(data["profile"])
    if data["qualified_claim"] is not None and not isinstance(
        data["qualified_claim"], str
    ):
        raise ModelValidationError("decision.qualified_claim must be a string or null")
    _string_array(data["limitations"], "decision.limitations")
    _sha256_digest(data["input_digest"], "decision.input_digest")
    if type(data["canonicalization_profile"]) is not str or not compare_digest(
        data["canonicalization_profile"], CANONICALIZATION_PROFILE
    ):
        raise ModelValidationError(
            "decision.canonicalization_profile is not supported"
        )
    if type(data["digest_algorithm"]) is not str or not compare_digest(
        data["digest_algorithm"], DIGEST_ALGORITHM
    ):
        raise ModelValidationError("decision.digest_algorithm is not supported")
    if type(data["evaluator_version"]) is not str or not compare_digest(
        data["evaluator_version"], EVALUATOR_VERSION
    ):
        raise ModelValidationError("decision.evaluator_version is not supported")
    normalized = _normalized_json_copy(data)
    canonical_json_bytes(normalized)
    return normalized


@dataclass(frozen=True, slots=True)
class EvidenceCertificatePayload:
    """The normalized payload covered by the outer certificate digest."""

    certificate_format: str
    canonicalization_profile: str
    digest_algorithm: str
    wire_schema_version: str
    evaluation_input_schema: str
    policy_id: str
    policy_version: str
    policy_digest: str
    evaluator_version: str
    request: NegativeClaimRequest
    evaluation_input_digest: str
    trusted_profile_context: TrustedProfileContext
    context_binding: CertificateContextBinding
    evaluated_at: datetime
    issued_at: datetime
    effective_valid_until_exclusive: datetime
    evidence_origin: EvidenceOrigin
    decision: Mapping[str, Any]
    implementation: ImplementationIdentity

    def __post_init__(self) -> None:
        exact_identifiers = {
            "certificate_format": CERTIFICATE_FORMAT,
            "canonicalization_profile": CANONICALIZATION_PROFILE,
            "digest_algorithm": DIGEST_ALGORITHM,
            "wire_schema_version": WIRE_SCHEMA_VERSION,
            "evaluation_input_schema": EVALUATION_INPUT_SCHEMA,
            "policy_id": DEFAULT_POLICY_ID,
            "policy_version": DEFAULT_POLICY_VERSION,
            "evaluator_version": EVALUATOR_VERSION,
        }
        for name, expected in exact_identifiers.items():
            value = getattr(self, name)
            if type(value) is not str or not compare_digest(value, expected):
                raise ModelValidationError(
                    f"certificate.{name} must be the supported value {expected}"
                )
        object.__setattr__(
            self,
            "policy_digest",
            _sha256_digest(self.policy_digest, "certificate.policy_digest"),
        )
        object.__setattr__(
            self,
            "evaluation_input_digest",
            _sha256_digest(
                self.evaluation_input_digest,
                "certificate.evaluation_input_digest",
            ),
        )
        if type(self.request) is not NegativeClaimRequest:
            raise ModelValidationError("certificate.request must be NegativeClaimRequest")
        if type(self.trusted_profile_context) is not TrustedProfileContext:
            raise ModelValidationError(
                "certificate.trusted_profile_context must be TrustedProfileContext"
            )
        if type(self.context_binding) is not CertificateContextBinding:
            raise ModelValidationError(
                "certificate.context_binding must be CertificateContextBinding"
            )
        for name in (
            "evaluated_at",
            "issued_at",
            "effective_valid_until_exclusive",
        ):
            object.__setattr__(
                self,
                name,
                _validate_aware_datetime(getattr(self, name), f"certificate.{name}"),
            )
        if self.issued_at < self.evaluated_at:
            raise ModelValidationError(
                "certificate.issued_at must not precede evaluated_at"
            )
        if type(self.evidence_origin) is not EvidenceOrigin:
            raise ModelValidationError(
                "certificate.evidence_origin must be an EvidenceOrigin"
            )
        object.__setattr__(self, "decision", _validated_decision_dict(self.decision))
        if type(self.implementation) is not ImplementationIdentity:
            raise ModelValidationError(
                "certificate.implementation must be ImplementationIdentity"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "EvidenceCertificatePayload":
        data = _mapping(value, "certificate")
        allowed = {
            "certificate_format",
            "canonicalization_profile",
            "digest_algorithm",
            "wire_schema_version",
            "evaluation_input_schema",
            "policy_id",
            "policy_version",
            "policy_digest",
            "evaluator_version",
            "request",
            "evaluation_input_digest",
            "trusted_profile_context",
            "context_binding",
            "evaluated_at",
            "issued_at",
            "effective_valid_until_exclusive",
            "evidence_origin",
            "decision",
            "implementation",
        }
        _reject_unknown(data, allowed, "certificate")
        _require_fields(data, allowed, "certificate")
        try:
            origin = EvidenceOrigin(data["evidence_origin"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                "certificate.evidence_origin is not supported"
            ) from exc
        return cls(
            certificate_format=data["certificate_format"],
            canonicalization_profile=data["canonicalization_profile"],
            digest_algorithm=data["digest_algorithm"],
            wire_schema_version=data["wire_schema_version"],
            evaluation_input_schema=data["evaluation_input_schema"],
            policy_id=data["policy_id"],
            policy_version=data["policy_version"],
            policy_digest=_sha256_digest(
                data["policy_digest"], "certificate.policy_digest"
            ),
            evaluator_version=data["evaluator_version"],
            request=NegativeClaimRequest.from_dict(data["request"]),
            evaluation_input_digest=_sha256_digest(
                data["evaluation_input_digest"],
                "certificate.evaluation_input_digest",
            ),
            trusted_profile_context=TrustedProfileContext.from_dict(
                data["trusted_profile_context"]
            ),
            context_binding=CertificateContextBinding.from_dict(
                data["context_binding"]
            ),
            evaluated_at=parse_datetime(data["evaluated_at"], "certificate.evaluated_at"),
            issued_at=parse_datetime(data["issued_at"], "certificate.issued_at"),
            effective_valid_until_exclusive=parse_datetime(
                data["effective_valid_until_exclusive"],
                "certificate.effective_valid_until_exclusive",
            ),
            evidence_origin=origin,
            decision=data["decision"],
            implementation=ImplementationIdentity.from_dict(data["implementation"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_format": self.certificate_format,
            "canonicalization_profile": self.canonicalization_profile,
            "digest_algorithm": self.digest_algorithm,
            "wire_schema_version": self.wire_schema_version,
            "evaluation_input_schema": self.evaluation_input_schema,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest,
            "evaluator_version": self.evaluator_version,
            "request": self.request.to_dict(),
            "evaluation_input_digest": self.evaluation_input_digest,
            "trusted_profile_context": self.trusted_profile_context.to_dict(),
            "context_binding": self.context_binding.to_dict(),
            "evaluated_at": datetime_to_json(self.evaluated_at),
            "issued_at": datetime_to_json(self.issued_at),
            "effective_valid_until_exclusive": datetime_to_json(
                self.effective_valid_until_exclusive
            ),
            "evidence_origin": self.evidence_origin.value,
            "decision": json.loads(canonical_json_bytes(self.decision).decode("utf-8")),
            "implementation": self.implementation.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EvidenceCertificate:
    """Outer payload-and-digest object; the digest is intentionally unsigned."""

    certificate: EvidenceCertificatePayload
    certificate_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.certificate, EvidenceCertificatePayload):
            raise ModelValidationError(
                "certificate wrapper must contain EvidenceCertificatePayload"
            )
        # Do not compare here.  A syntactically valid, digest-invalid artifact
        # must remain representable so verification can report that dimension.
        object.__setattr__(
            self,
            "certificate_digest",
            _sha256_digest(self.certificate_digest, "certificate_digest"),
        )

    @classmethod
    def from_dict(cls, value: Any) -> "EvidenceCertificate":
        data = _mapping(value, "evidence_certificate")
        allowed = {"certificate", "certificate_digest"}
        _reject_unknown(data, allowed, "evidence_certificate")
        _require_fields(data, allowed, "evidence_certificate")
        return cls(
            certificate=EvidenceCertificatePayload.from_dict(data["certificate"]),
            certificate_digest=_sha256_digest(
                data["certificate_digest"],
                "evidence_certificate.certificate_digest",
            ),
        )

    @property
    def recomputed_digest(self) -> str:
        return canonical_digest(self.certificate.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate": self.certificate.to_dict(),
            "certificate_digest": self.certificate_digest,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def _evaluation_input_digest(
    request: NegativeClaimRequest,
    context: TrustedProfileContext,
) -> str:
    return canonical_digest(
        {
            "evaluation_input_schema": EVALUATION_INPUT_SCHEMA,
            "request": request.to_dict(),
            "trusted_profile_context": context.to_dict(),
        }
    )


def _context_binding(
    context: TrustedProfileContext,
    decision: GateDecision,
) -> CertificateContextBinding:
    snapshot = context.snapshot
    snapshot_digest = snapshot.snapshot_digest
    trust_digest = context.trust_selection.trust_selection_digest
    assert snapshot_digest is not None
    assert trust_digest is not None
    return CertificateContextBinding(
        context_digest=context.context_digest,
        registry_id=snapshot.registry_id,
        snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.snapshot_version,
        snapshot_digest=snapshot_digest,
        trust_selection_digest=trust_digest,
        resolved_profile_references=decision.profile.resolved_profile_references,
    )


def _effective_valid_until_exclusive(
    request: NegativeClaimRequest,
    context: TrustedProfileContext,
    decision: GateDecision,
) -> datetime:
    candidates = [context.snapshot.next_update_at]

    def add_age_deadline(base: datetime, seconds: int | None) -> None:
        if seconds is None:
            return
        try:
            candidates.append(base + timedelta(seconds=seconds))
        except OverflowError:
            # A deadline beyond datetime.max cannot constrain any representable
            # relying-party time and is therefore nonbinding.
            return

    if request.envelope.valid_until is not None:
        # Evidence validity is inclusive in the envelope.  Reusing that same
        # instant as an exclusive certificate boundary is conservative.
        candidates.append(request.envelope.valid_until)
    add_age_deadline(
        request.envelope.observed_at,
        request.policy.max_observation_age_seconds,
    )
    observations_by_id = {
        observation.source_id: observation
        for observation in request.envelope.source_observations
        if observation.status is SourceObservationStatus.OBSERVED
    }
    for requirement in request.envelope.query.source_requirements:
        observation = observations_by_id.get(requirement.source_id)
        if observation is not None and observation.descriptor.index_as_of is not None:
            add_age_deadline(
                observation.descriptor.index_as_of,
                request.policy.max_index_age_seconds,
            )
    resolved = {
        (
            reference.registry_id,
            reference.profile_id,
            reference.profile_version,
            reference.profile_digest,
        )
        for reference in decision.profile.resolved_profile_references
    }
    for record in context.snapshot.records:
        key = (
            context.snapshot.registry_id,
            record.profile.profile_id,
            record.profile.profile_version,
            record.profile_digest,
        )
        if key in resolved:
            candidates.append(record.profile.expires_at)
            if record.revocation_effective_at is not None:
                candidates.append(record.revocation_effective_at)
            add_age_deadline(
                request.envelope.observed_at,
                record.profile.coverage.max_observation_age_seconds,
            )
            observation = observations_by_id.get(record.profile.source.source_id)
            if observation is not None and observation.descriptor.index_as_of is not None:
                add_age_deadline(
                    observation.descriptor.index_as_of,
                    record.profile.coverage.max_index_age_seconds,
                )
    return min(candidates)


def build_evidence_certificate(
    request: NegativeClaimRequest,
    context: TrustedProfileContext,
    *,
    issued_at: datetime,
    origin: EvidenceOrigin,
    implementation: ImplementationIdentity,
) -> EvidenceCertificate:
    """Evaluate and package one deterministic unsigned replay record.

    There is deliberately no ``GateDecision`` parameter: the builder owns the
    evaluation whose complete output it records.
    """

    if type(request) is not NegativeClaimRequest:
        raise ModelValidationError("certificate request must be NegativeClaimRequest")
    if type(context) is not TrustedProfileContext:
        raise ModelValidationError(
            "certificate context must be a separately supplied TrustedProfileContext"
        )
    if type(origin) is not EvidenceOrigin:
        raise ModelValidationError("certificate origin must be an EvidenceOrigin")
    if type(implementation) is not ImplementationIdentity:
        raise ModelValidationError(
            "certificate implementation must be ImplementationIdentity"
        )
    # Reparse typed values before evaluation or emission.  This prevents
    # post-construction mutation from bypassing the strict public contracts and
    # keeps rejected credential-like content out of certificate payloads.
    request = NegativeClaimRequest.from_dict(request.to_dict())
    context = TrustedProfileContext.from_dict(context.to_dict())
    implementation = ImplementationIdentity.from_dict(implementation.to_dict())
    issuance_time = _validate_aware_datetime(issued_at, "certificate.issued_at")
    if issuance_time < request.evaluated_at:
        raise ModelValidationError(
            "certificate.issued_at must not precede request.evaluated_at"
        )
    decision = evaluate_negative_claim(request, context)
    input_digest = _evaluation_input_digest(request, context)
    if not compare_digest(decision.input_digest, input_digest):
        raise ModelValidationError(
            "evaluator input digest does not match the candidate certificate contract"
        )
    payload = EvidenceCertificatePayload(
        certificate_format=CERTIFICATE_FORMAT,
        canonicalization_profile=CANONICALIZATION_PROFILE,
        digest_algorithm=DIGEST_ALGORITHM,
        wire_schema_version=request.envelope.schema_version,
        evaluation_input_schema=EVALUATION_INPUT_SCHEMA,
        policy_id=request.policy.policy_id,
        policy_version=request.policy.policy_version,
        policy_digest=canonical_digest(request.policy.to_dict()),
        evaluator_version=decision.evaluator_version,
        request=request,
        evaluation_input_digest=input_digest,
        trusted_profile_context=context,
        context_binding=_context_binding(context, decision),
        evaluated_at=request.evaluated_at,
        issued_at=issuance_time,
        effective_valid_until_exclusive=_effective_valid_until_exclusive(
            request, context, decision
        ),
        evidence_origin=origin,
        decision=decision.to_dict(),
        implementation=implementation,
    )
    return EvidenceCertificate(
        certificate=payload,
        certificate_digest=canonical_digest(payload.to_dict()),
    )


@dataclass(frozen=True, slots=True)
class CertificateVerification:
    """Independent verification dimensions; intentionally no aggregate valid flag."""

    structural_support: bool
    certificate_digest_integrity: bool
    embedded_digest_integrity: bool
    deterministic_replay: bool
    expected_context_match: bool | None
    expected_certificate_digest_match: bool | None
    historical_reproducibility: bool
    current_local_reliance_eligible: bool | None
    issuer_authenticated: bool
    authorization_established: bool
    recomputed_certificate_digest: str | None
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "structural_support": self.structural_support,
            "certificate_digest_integrity": self.certificate_digest_integrity,
            "embedded_digest_integrity": self.embedded_digest_integrity,
            "deterministic_replay": self.deterministic_replay,
            "expected_context_match": self.expected_context_match,
            "expected_certificate_digest_match": self.expected_certificate_digest_match,
            "historical_reproducibility": self.historical_reproducibility,
            "current_local_reliance_eligible": self.current_local_reliance_eligible,
            "issuer_authenticated": self.issuer_authenticated,
            "authorization_established": self.authorization_established,
            "recomputed_certificate_digest": self.recomputed_certificate_digest,
            "issues": list(self.issues),
        }


def _unsupported_verification(detail: str) -> CertificateVerification:
    return CertificateVerification(
        structural_support=False,
        certificate_digest_integrity=False,
        embedded_digest_integrity=False,
        deterministic_replay=False,
        expected_context_match=None,
        expected_certificate_digest_match=None,
        historical_reproducibility=False,
        current_local_reliance_eligible=None,
        issuer_authenticated=False,
        authorization_established=False,
        recomputed_certificate_digest=None,
        issues=(f"STRUCTURAL_SUPPORT_FAILED: {detail}",),
    )


def _embedded_integrity(payload: EvidenceCertificatePayload) -> bool:
    request = payload.request
    context = payload.trusted_profile_context
    decision = payload.decision
    binding = payload.context_binding
    snapshot = context.snapshot
    trust = context.trust_selection
    snapshot_digest = snapshot.snapshot_digest
    trust_digest = trust.trust_selection_digest
    if snapshot_digest is None or trust_digest is None:
        return False
    expected_input_digest = _evaluation_input_digest(request, context)
    expected_effective = _effective_valid_until_exclusive(
        request,
        context,
        evaluate_negative_claim(request, context),
    )
    profile_data = decision["profile"]
    embedded_references = tuple(
        CoverageProfileReference.from_dict(
            item, f"decision.profile.resolved_profile_references[{index}]"
        )
        for index, item in enumerate(profile_data["resolved_profile_references"])
    )
    checks = (
        compare_digest(payload.policy_digest, canonical_digest(request.policy.to_dict())),
        compare_digest(payload.evaluation_input_digest, expected_input_digest),
        compare_digest(decision["input_digest"], expected_input_digest),
        compare_digest(binding.context_digest, context.context_digest),
        binding.registry_id == snapshot.registry_id,
        binding.snapshot_id == snapshot.snapshot_id,
        binding.snapshot_version == snapshot.snapshot_version,
        compare_digest(binding.snapshot_digest, snapshot_digest),
        compare_digest(binding.trust_selection_digest, trust_digest),
        binding.resolved_profile_references == embedded_references,
        profile_data["registry_snapshot_digest"] == snapshot_digest,
        profile_data["trust_selection_digest"] == trust_digest,
        payload.wire_schema_version == request.envelope.schema_version,
        payload.policy_id == request.policy.policy_id,
        payload.policy_version == request.policy.policy_version,
        payload.evaluated_at == request.evaluated_at,
        payload.effective_valid_until_exclusive == expected_effective,
        decision["canonicalization_profile"] == payload.canonicalization_profile,
        decision["digest_algorithm"] == payload.digest_algorithm,
        decision["evaluator_version"] == payload.evaluator_version,
    )
    return all(checks)


def verify_evidence_certificate(
    value: EvidenceCertificate | Mapping[str, Any],
    *,
    expected_context: TrustedProfileContext | None = None,
    expected_certificate_digest: str | None = None,
    relying_party_at: datetime | None = None,
) -> CertificateVerification:
    """Verify replay, integrity, optional custody, and current-use dimensions.

    This function never reports issuer authentication or action authorization.
    The optional expected values and relying-party time come from outside the
    certificate; absence is represented by ``None`` rather than success.
    """

    if expected_context is not None:
        if type(expected_context) is not TrustedProfileContext:
            raise ModelValidationError(
                "expected_context must be TrustedProfileContext or null"
            )
        expected_context = TrustedProfileContext.from_dict(expected_context.to_dict())
    reliance_time = None
    if relying_party_at is not None:
        reliance_time = _validate_aware_datetime(
            relying_party_at, "relying_party_at"
        )
    try:
        # Typed artifacts contain a nested mapping.  Reparse their public form
        # so mutable nested values cannot bypass the same strict structural and
        # numeric checks applied to JSON-derived mappings.
        artifact = EvidenceCertificate.from_dict(
            value.to_dict() if isinstance(value, EvidenceCertificate) else value
        )
    except (ModelValidationError, TypeError, ValueError) as exc:
        return _unsupported_verification(str(exc))
    payload = artifact.certificate
    recomputed_digest = artifact.recomputed_digest
    outer_integrity = compare_digest(
        recomputed_digest, artifact.certificate_digest
    )
    try:
        embedded_integrity = _embedded_integrity(payload)
    except (ModelValidationError, KeyError, TypeError, ValueError):
        embedded_integrity = False
    try:
        replayed = evaluate_negative_claim(
            payload.request, payload.trusted_profile_context
        )
        deterministic_replay = canonical_json_bytes(
            replayed.to_dict()
        ) == canonical_json_bytes(payload.decision)
    except (ModelValidationError, KeyError, TypeError, ValueError):
        deterministic_replay = False

    context_match: bool | None = None
    if expected_context is not None:
        expected_snapshot_digest = expected_context.snapshot.snapshot_digest
        embedded_snapshot_digest = payload.trusted_profile_context.snapshot.snapshot_digest
        expected_trust_digest = expected_context.trust_selection.trust_selection_digest
        embedded_trust_digest = (
            payload.trusted_profile_context.trust_selection.trust_selection_digest
        )
        context_match = bool(
            expected_snapshot_digest
            and embedded_snapshot_digest
            and expected_trust_digest
            and embedded_trust_digest
            and compare_digest(expected_snapshot_digest, embedded_snapshot_digest)
            and compare_digest(expected_trust_digest, embedded_trust_digest)
        )

    expected_digest_match: bool | None = None
    if expected_certificate_digest is not None:
        try:
            normalized_expected_digest = _sha256_digest(
                expected_certificate_digest, "expected_certificate_digest"
            )
        except ModelValidationError:
            expected_digest_match = False
        else:
            expected_digest_match = compare_digest(
                normalized_expected_digest, recomputed_digest
            )

    historical_reproducibility = deterministic_replay
    current_reliance: bool | None = None
    if (
        reliance_time is not None
        and expected_context is not None
        and expected_certificate_digest is not None
    ):
        current_reliance = bool(
            outer_integrity
            and embedded_integrity
            and deterministic_replay
            and context_match
            and expected_digest_match
            and payload.decision["allowed"] is True
            and payload.issued_at
            <= reliance_time
            < payload.effective_valid_until_exclusive
        )

    issues: list[str] = []
    if not outer_integrity:
        issues.append("CERTIFICATE_DIGEST_MISMATCH")
    if not embedded_integrity:
        issues.append("EMBEDDED_DIGEST_OR_BINDING_MISMATCH")
    if not deterministic_replay:
        issues.append("DETERMINISTIC_REPLAY_MISMATCH")
    if context_match is False:
        issues.append("EXPECTED_CONTEXT_MISMATCH")
    if expected_digest_match is False:
        issues.append("EXPECTED_CERTIFICATE_DIGEST_MISMATCH")
    if current_reliance is False:
        issues.append("CURRENT_LOCAL_RELIANCE_INELIGIBLE")

    return CertificateVerification(
        structural_support=True,
        certificate_digest_integrity=outer_integrity,
        embedded_digest_integrity=embedded_integrity,
        deterministic_replay=deterministic_replay,
        expected_context_match=context_match,
        expected_certificate_digest_match=expected_digest_match,
        historical_reproducibility=historical_reproducibility,
        current_local_reliance_eligible=current_reliance,
        issuer_authenticated=False,
        authorization_established=False,
        recomputed_certificate_digest=recomputed_digest,
        issues=tuple(issues),
    )


__all__ = [
    "CERTIFICATE_FORMAT",
    "CertificateContextBinding",
    "CertificateVerification",
    "EvidenceCertificate",
    "EvidenceCertificatePayload",
    "EvidenceOrigin",
    "ImplementationIdentity",
    "WorkingTreeState",
    "build_evidence_certificate",
    "verify_evidence_certificate",
]
