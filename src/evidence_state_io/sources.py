"""Deterministic required-versus-observed source accounting.

The evaluator in this module proves only that every P0-required source has a
usable runtime observation for the same explicitly declared accessible
population.  It does not infer source honesty or compose coverage across
multiple required sources; multi-source composition remains fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

from .models import (
    MAX_SOURCE_ACCOUNTING_ENTRIES,
    ModelValidationError,
    SourceObservation,
    SourceObservationStatus,
    SourceRequirement,
    SourceRole,
    bounded_ascii_identifier,
)


class SourceIssueCode(str, Enum):
    """Stable source-accounting reasons that can independently block a permit."""

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


@dataclass(frozen=True, slots=True)
class SourceIssue:
    """One deterministic issue, optionally attributed to a specific source."""

    code: SourceIssueCode
    source_id: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.code, SourceIssueCode):
            raise ModelValidationError("source issue code must be a SourceIssueCode")
        if self.source_id is not None:
            object.__setattr__(
                self,
                "source_id",
                bounded_ascii_identifier(self.source_id, "source_issue.source_id"),
            )
        if self.source_id is None:
            raise ModelValidationError(
                "required-source issue must identify the affected source"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "source_id": self.source_id,
        }


@dataclass(frozen=True, slots=True)
class SourceAccountingAssessment:
    """Deterministic summary of required-source presence and sufficiency."""

    required_source_ids: tuple[str, ...]
    observed_source_ids: tuple[str, ...]
    complete_source_ids: tuple[str, ...]
    issues: tuple[SourceIssue, ...]
    meets_policy: bool

    def __post_init__(self) -> None:
        for name in (
            "required_source_ids",
            "observed_source_ids",
            "complete_source_ids",
        ):
            value = getattr(self, name)
            if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
                raise ModelValidationError(f"source assessment {name} must be an array")
            normalized = tuple(
                bounded_ascii_identifier(item, f"source_assessment.{name}[{index}]")
                for index, item in enumerate(value)
            )
            if len(set(normalized)) != len(normalized):
                raise ModelValidationError(
                    f"source assessment {name} must not contain duplicates"
                )
            object.__setattr__(self, name, tuple(sorted(normalized)))
        if isinstance(self.issues, (str, bytes)) or not isinstance(
            self.issues, Sequence
        ):
            raise ModelValidationError("source assessment issues must be an array")
        normalized_issues = tuple(self.issues)
        if any(not isinstance(issue, SourceIssue) for issue in normalized_issues):
            raise ModelValidationError(
                "source assessment issues must contain only SourceIssue values"
            )
        if len({(issue.code, issue.source_id) for issue in normalized_issues}) != len(
            normalized_issues
        ):
            raise ModelValidationError("source assessment issues must not contain duplicates")
        issue_order = {code: index for index, code in enumerate(SourceIssueCode)}
        normalized_issues = tuple(
            sorted(
                normalized_issues,
                key=lambda issue: (
                    issue.source_id is None,
                    issue.source_id or "",
                    issue_order[issue.code],
                ),
            )
        )
        object.__setattr__(self, "issues", normalized_issues)
        required_ids = set(self.required_source_ids)
        observed_ids = set(self.observed_source_ids)
        complete_ids = set(self.complete_source_ids)
        if not required_ids:
            raise ModelValidationError(
                "source assessment required_source_ids must not be empty"
            )
        if not observed_ids <= required_ids:
            raise ModelValidationError(
                "source assessment observed_source_ids must be required sources"
            )
        if not complete_ids <= observed_ids:
            raise ModelValidationError(
                "source assessment complete_source_ids must be observed sources"
            )
        invalid_issue_ids = sorted(
            {
                issue.source_id
                for issue in normalized_issues
                if issue.source_id is not None and issue.source_id not in required_ids
            }
        )
        if invalid_issue_ids:
            raise ModelValidationError(
                "source assessment issues identify non-required sources: "
                + ", ".join(invalid_issue_ids)
            )
        if not isinstance(self.meets_policy, bool):
            raise ModelValidationError("source assessment meets_policy must be a boolean")
        if self.meets_policy != (not normalized_issues):
            raise ModelValidationError(
                "source assessment meets_policy must be true exactly when issues is empty"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_source_ids": list(self.required_source_ids),
            "observed_source_ids": list(self.observed_source_ids),
            "complete_source_ids": list(self.complete_source_ids),
            "issues": [issue.to_dict() for issue in self.issues],
            "meets_policy": self.meets_policy,
        }


_STATUS_ISSUE = {
    SourceObservationStatus.NOT_OBSERVED: SourceIssueCode.REQUIRED_SOURCE_NOT_OBSERVED,
    SourceObservationStatus.INACCESSIBLE: SourceIssueCode.REQUIRED_SOURCE_INACCESSIBLE,
    SourceObservationStatus.PENDING: SourceIssueCode.REQUIRED_SOURCE_PENDING,
    SourceObservationStatus.STALE: SourceIssueCode.REQUIRED_SOURCE_STALE,
    SourceObservationStatus.FAILED: SourceIssueCode.REQUIRED_SOURCE_FAILED,
    SourceObservationStatus.CONTRADICTORY: SourceIssueCode.REQUIRED_SOURCE_CONTRADICTORY,
    SourceObservationStatus.UNKNOWN: SourceIssueCode.REQUIRED_SOURCE_STATUS_UNKNOWN,
}


def _materialize_inputs(
    requirements: Sequence[SourceRequirement],
    observations: Sequence[SourceObservation],
) -> tuple[tuple[SourceRequirement, ...], tuple[SourceObservation, ...]]:
    if isinstance(requirements, (str, bytes)) or not isinstance(requirements, Sequence):
        raise ModelValidationError("source requirements must be an array")
    if isinstance(observations, (str, bytes)) or not isinstance(observations, Sequence):
        raise ModelValidationError("source observations must be an array")
    declared = tuple(requirements)
    observed = tuple(observations)
    if not declared:
        raise ModelValidationError("source requirements must contain at least one source")
    if len(declared) > MAX_SOURCE_ACCOUNTING_ENTRIES:
        raise ModelValidationError(
            f"source requirements exceeds the {MAX_SOURCE_ACCOUNTING_ENTRIES}-entry limit"
        )
    if len(observed) > MAX_SOURCE_ACCOUNTING_ENTRIES:
        raise ModelValidationError(
            f"source observations exceeds the {MAX_SOURCE_ACCOUNTING_ENTRIES}-entry limit"
        )
    if any(not isinstance(item, SourceRequirement) for item in declared):
        raise ModelValidationError(
            "source requirements must contain only SourceRequirement values"
        )
    if any(not isinstance(item, SourceObservation) for item in observed):
        raise ModelValidationError(
            "source observations must contain only SourceObservation values"
        )
    declared_ids = [item.source_id for item in declared]
    observed_ids = [item.source_id for item in observed]
    if len(set(declared_ids)) != len(declared_ids):
        raise ModelValidationError("source requirements must not contain duplicate IDs")
    if len(set(observed_ids)) != len(observed_ids):
        raise ModelValidationError("source observations must not contain duplicate IDs")
    if len(declared) != 1:
        raise ModelValidationError(
            "source requirements must contain exactly one REQUIRED source "
            "in the schema 1.0 candidate"
        )
    if declared[0].role is not SourceRole.REQUIRED:
        raise ModelValidationError("source requirements must contain a REQUIRED source")
    undeclared = sorted(set(observed_ids) - set(declared_ids))
    if undeclared:
        raise ModelValidationError(
            "source observations contains undeclared source IDs: "
            + ", ".join(undeclared)
        )
    return (
        tuple(sorted(declared, key=lambda item: item.source_id)),
        tuple(sorted(observed, key=lambda item: item.source_id)),
    )


def evaluate_source_accounting(
    requirements: Sequence[SourceRequirement],
    observations: Sequence[SourceObservation],
) -> SourceAccountingAssessment:
    """Compare explicit requirements with runtime observations, fail closed.

    The schema 1.0 candidate accepts one declared required source. Multi-source
    coverage remains outside the candidate until a separately versioned
    composition method exists.
    """

    declared, reported = _materialize_inputs(requirements, observations)
    required = declared
    observations_by_id = {item.source_id: item for item in reported}
    observed_source_ids: list[str] = []
    complete_source_ids: list[str] = []
    issues: list[SourceIssue] = []

    for requirement in required:
        observation = observations_by_id.get(requirement.source_id)
        if observation is None:
            issues.append(
                SourceIssue(
                    code=SourceIssueCode.REQUIRED_SOURCE_MISSING,
                    source_id=requirement.source_id,
                )
            )
            continue

        population_matches = (
            observation.accessible_population == requirement.accessible_population
        )
        identity_matches = (
            observation.descriptor.system == requirement.system
            and observation.descriptor.locator == requirement.locator
        )
        adapter_matches = (
            observation.descriptor.adapter_id == requirement.adapter_id
            and observation.descriptor.adapter_version == requirement.adapter_version
        )
        authorization_matches = (
            observation.authorization_context_id
            == requirement.authorization_context_id
        )
        if observation.status is SourceObservationStatus.OBSERVED:
            observed_source_ids.append(requirement.source_id)
        else:
            issues.append(
                SourceIssue(
                    code=_STATUS_ISSUE[observation.status],
                    source_id=requirement.source_id,
                )
            )

        if (
            observation.status is SourceObservationStatus.OBSERVED
            and not identity_matches
        ):
            issues.append(
                SourceIssue(
                    code=SourceIssueCode.REQUIRED_SOURCE_IDENTITY_MISMATCH,
                    source_id=requirement.source_id,
                )
            )

        if (
            observation.status is SourceObservationStatus.OBSERVED
            and not adapter_matches
        ):
            issues.append(
                SourceIssue(
                    code=SourceIssueCode.REQUIRED_SOURCE_ADAPTER_MISMATCH,
                    source_id=requirement.source_id,
                )
            )

        if (
            observation.status is SourceObservationStatus.OBSERVED
            and not authorization_matches
        ):
            issues.append(
                SourceIssue(
                    code=SourceIssueCode.REQUIRED_SOURCE_AUTHORIZATION_MISMATCH,
                    source_id=requirement.source_id,
                )
            )

        if (
            observation.status is SourceObservationStatus.OBSERVED
            and not population_matches
        ):
            issues.append(
                SourceIssue(
                    code=SourceIssueCode.REQUIRED_SOURCE_POPULATION_MISMATCH,
                    source_id=requirement.source_id,
                )
            )
        if observation.errors:
            issues.append(
                SourceIssue(
                    code=SourceIssueCode.REQUIRED_SOURCE_ERRORS_PRESENT,
                    source_id=requirement.source_id,
                )
            )
        if (
            observation.status is SourceObservationStatus.OBSERVED
            and identity_matches
            and adapter_matches
            and authorization_matches
            and population_matches
            and not observation.errors
        ):
            complete_source_ids.append(requirement.source_id)

    return SourceAccountingAssessment(
        required_source_ids=tuple(item.source_id for item in required),
        observed_source_ids=tuple(observed_source_ids),
        complete_source_ids=tuple(complete_source_ids),
        issues=tuple(issues),
        meets_policy=not issues,
    )
