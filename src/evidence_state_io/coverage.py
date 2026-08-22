"""Conservative, deterministic coverage evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Any, Mapping

from .models import (
    CoverageEvidence,
    ModelValidationError,
    PopulationBasis,
    _conservative_ratio_float,
    _exact_ratio,
    _normalized_float_fraction,
    _optional_fraction,
)


class CoverageIssue(str, Enum):
    UNKNOWN_COVERAGE = "UNKNOWN_COVERAGE"
    BELOW_MINIMUM = "BELOW_MINIMUM"
    EXACT_POPULATION_REQUIRED = "EXACT_POPULATION_REQUIRED"
    PAGINATION_INCOMPLETE = "PAGINATION_INCOMPLETE"
    CONTINUATION_PRESENT = "CONTINUATION_PRESENT"
    PARTITIONS_INCOMPLETE = "PARTITIONS_INCOMPLETE"
    TIMEOUT = "TIMEOUT"
    INTERRUPTED = "INTERRUPTED"
    QUERY_ERROR = "QUERY_ERROR"
    PERMISSION_LIMITED = "PERMISSION_LIMITED"


def _fraction(value: Any, path: str) -> float:
    if value is None:
        raise ModelValidationError(f"{path} must be a number between 0 and 1")
    result = _optional_fraction(value, path)
    assert result is not None
    return result


def _bool(value: Any, path: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ModelValidationError(f"{path} must be a boolean")
    return value


@dataclass(frozen=True, slots=True)
class CoveragePolicy:
    """Policy thresholds used by the negative-claim gate.

    The defaults are intentionally fail-closed: full declared coverage,
    completed pagination/partitions, and no timeout, interruption, or query
    error.  Permission-limited results may pass only because the authorization
    boundary is required in :class:`QueryScope`; the resulting claim remains
    explicitly limited to that accessible population.
    """

    minimum_lower_bound: float = 1.0
    require_exact_population: bool = False
    require_complete_pagination: bool = True
    require_complete_partitions: bool = True
    reject_timeout: bool = True
    reject_interruption: bool = True
    reject_query_errors: bool = True
    allow_permission_limited_scope: bool = True

    def __post_init__(self) -> None:
        normalized_minimum = _fraction(
            self.minimum_lower_bound, "policy.coverage.minimum_lower_bound"
        )
        object.__setattr__(self, "minimum_lower_bound", normalized_minimum)
        for name in (
            "require_exact_population",
            "require_complete_pagination",
            "require_complete_partitions",
            "reject_timeout",
            "reject_interruption",
            "reject_query_errors",
            "allow_permission_limited_scope",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ModelValidationError(f"policy.coverage.{name} must be a boolean")
        if normalized_minimum != 1.0:
            raise ModelValidationError(
                "policy.coverage.minimum_lower_bound cannot relax the P0 safety floor of 1.0"
            )
        required_true = (
            "require_complete_pagination",
            "require_complete_partitions",
            "reject_timeout",
            "reject_interruption",
            "reject_query_errors",
        )
        relaxed = [name for name in required_true if getattr(self, name) is not True]
        if relaxed:
            raise ModelValidationError(
                "policy.coverage cannot relax the P0 safety floor: " + ", ".join(relaxed)
            )

    @classmethod
    def from_dict(cls, value: Any) -> "CoveragePolicy":
        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise ModelValidationError("policy.coverage must be a JSON object")
        allowed = {
            "minimum_lower_bound",
            "require_exact_population",
            "require_complete_pagination",
            "require_complete_partitions",
            "reject_timeout",
            "reject_interruption",
            "reject_query_errors",
            "allow_permission_limited_scope",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ModelValidationError(f"policy.coverage has unknown fields: {', '.join(unknown)}")
        return cls(
            minimum_lower_bound=value.get("minimum_lower_bound", 1.0),
            require_exact_population=_bool(
                value.get("require_exact_population"),
                "policy.coverage.require_exact_population",
                False,
            ),
            require_complete_pagination=_bool(
                value.get("require_complete_pagination"),
                "policy.coverage.require_complete_pagination",
                True,
            ),
            require_complete_partitions=_bool(
                value.get("require_complete_partitions"),
                "policy.coverage.require_complete_partitions",
                True,
            ),
            reject_timeout=_bool(
                value.get("reject_timeout"), "policy.coverage.reject_timeout", True
            ),
            reject_interruption=_bool(
                value.get("reject_interruption"),
                "policy.coverage.reject_interruption",
                True,
            ),
            reject_query_errors=_bool(
                value.get("reject_query_errors"),
                "policy.coverage.reject_query_errors",
                True,
            ),
            allow_permission_limited_scope=_bool(
                value.get("allow_permission_limited_scope"),
                "policy.coverage.allow_permission_limited_scope",
                True,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum_lower_bound": self.minimum_lower_bound,
            "require_exact_population": self.require_exact_population,
            "require_complete_pagination": self.require_complete_pagination,
            "require_complete_partitions": self.require_complete_partitions,
            "reject_timeout": self.reject_timeout,
            "reject_interruption": self.reject_interruption,
            "reject_query_errors": self.reject_query_errors,
            "allow_permission_limited_scope": self.allow_permission_limited_scope,
        }


@dataclass(frozen=True, slots=True)
class CoverageComponent:
    name: str
    lower_bound: float
    basis: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "lower_bound": self.lower_bound,
            "basis": self.basis,
        }


@dataclass(frozen=True, slots=True)
class CoverageAssessment:
    lower_bound: float | None
    meets_policy: bool
    issues: tuple[CoverageIssue, ...] = field(default_factory=tuple)
    components: tuple[CoverageComponent, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lower_bound": self.lower_bound,
            "meets_policy": self.meets_policy,
            "issues": [issue.value for issue in self.issues],
            "components": [component.to_dict() for component in self.components],
        }


def evaluate_coverage(
    evidence: CoverageEvidence,
    policy: CoveragePolicy | None = None,
) -> CoverageAssessment:
    """Evaluate coverage using only supplied evidence and policy.

    No wall clock, network call, or mutable global state participates.  A
    population estimate is not silently promoted to a lower-bound guarantee;
    estimated and unknown populations require an explicit declared lower
    bound from the adapter/source.
    """

    if not isinstance(evidence, CoverageEvidence):
        raise ModelValidationError("evidence must be CoverageEvidence")
    if policy is not None and not isinstance(policy, CoveragePolicy):
        raise ModelValidationError("policy must be CoveragePolicy")
    effective_policy = CoveragePolicy() if policy is None else policy
    components: list[CoverageComponent] = []
    population_bound: Fraction | None = None
    traversal_bounds: list[Fraction] = []

    if evidence.population_basis is PopulationBasis.EXACT:
        assert evidence.population_units is not None  # enforced by the model
        population_bound = _exact_ratio(evidence.examined_units, evidence.population_units)
        components.append(
            CoverageComponent(
                name="population",
                lower_bound=_conservative_ratio_float(population_bound),
                basis="examined_units / exact_population_units",
            )
        )

    if evidence.declared_lower_bound is not None:
        declared_bound = _normalized_float_fraction(evidence.declared_lower_bound)
        if population_bound is None:
            population_bound = declared_bound
        else:
            population_bound = min(population_bound, declared_bound)
        components.append(
            CoverageComponent(
                name="declared",
                lower_bound=evidence.declared_lower_bound,
                basis="source_or_adapter_attestation",
            )
        )

    if evidence.pages_examined is not None and evidence.pages_expected is not None:
        pages_bound = _exact_ratio(evidence.pages_examined, evidence.pages_expected)
        traversal_bounds.append(pages_bound)
        components.append(
            CoverageComponent(
                name="pages",
                lower_bound=_conservative_ratio_float(pages_bound),
                basis="pages_examined / pages_expected",
            )
        )

    if evidence.partitions_examined is not None and evidence.partitions_expected is not None:
        partitions_bound = _exact_ratio(evidence.partitions_examined, evidence.partitions_expected)
        traversal_bounds.append(partitions_bound)
        components.append(
            CoverageComponent(
                name="partitions",
                lower_bound=_conservative_ratio_float(partitions_bound),
                basis="partitions_examined / partitions_expected",
            )
        )

    exact_lower_bound: Fraction | None = None
    lower_bound: float | None = None
    if population_bound is not None:
        exact_lower_bound = min([population_bound, *traversal_bounds])
        lower_bound = _conservative_ratio_float(exact_lower_bound)
    issues: list[CoverageIssue] = []

    if exact_lower_bound is None:
        issues.append(CoverageIssue.UNKNOWN_COVERAGE)
    elif exact_lower_bound < _normalized_float_fraction(effective_policy.minimum_lower_bound):
        issues.append(CoverageIssue.BELOW_MINIMUM)

    if (
        effective_policy.require_exact_population
        and evidence.population_basis is not PopulationBasis.EXACT
    ):
        issues.append(CoverageIssue.EXACT_POPULATION_REQUIRED)

    if effective_policy.require_complete_pagination and not evidence.pagination_complete:
        issues.append(CoverageIssue.PAGINATION_INCOMPLETE)
    if evidence.continuation_token_present:
        issues.append(CoverageIssue.CONTINUATION_PRESENT)
    if effective_policy.require_complete_partitions and not evidence.partitions_complete:
        issues.append(CoverageIssue.PARTITIONS_INCOMPLETE)
    if effective_policy.reject_timeout and evidence.timed_out:
        issues.append(CoverageIssue.TIMEOUT)
    if effective_policy.reject_interruption and evidence.interrupted:
        issues.append(CoverageIssue.INTERRUPTED)
    if effective_policy.reject_query_errors and evidence.query_errors:
        issues.append(CoverageIssue.QUERY_ERROR)
    if evidence.permission_limited and not effective_policy.allow_permission_limited_scope:
        issues.append(CoverageIssue.PERMISSION_LIMITED)

    return CoverageAssessment(
        lower_bound=lower_bound,
        meets_policy=not issues,
        issues=tuple(issues),
        components=tuple(components),
    )
