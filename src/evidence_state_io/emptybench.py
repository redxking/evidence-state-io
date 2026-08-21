"""Seed EmptyBench cases for ambiguous empty-result handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .gate import GateDecision, GateReason, NegativeClaimRequest, evaluate_negative_claim
from .models import ModelValidationError, bounded_single_line


MAX_BENCHMARK_ID_LENGTH = 128
MAX_BENCHMARK_DESCRIPTION_LENGTH = 512


@dataclass(frozen=True, slots=True)
class EmptyBenchCase:
    case_id: str
    pair_id: str
    variant: str
    description: str
    request: NegativeClaimRequest
    expected_allowed: bool
    expected_reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("case_id", "pair_id", "variant", "description"):
            limit = (
                MAX_BENCHMARK_DESCRIPTION_LENGTH
                if name == "description"
                else MAX_BENCHMARK_ID_LENGTH
            )
            normalized = bounded_single_line(
                getattr(self, name), f"case.{name}", max_length=limit
            )
            object.__setattr__(self, name, normalized)
        if not isinstance(self.request, NegativeClaimRequest):
            raise ModelValidationError("case.request must be a NegativeClaimRequest")
        if not isinstance(self.expected_allowed, bool):
            raise ModelValidationError("case.expected_allowed must be a boolean")
        if isinstance(self.expected_reasons, (str, bytes)) or not isinstance(
            self.expected_reasons, Sequence
        ):
            raise ModelValidationError("case.expected_reasons must be an array of strings")
        normalized_reasons = tuple(
            bounded_single_line(
                item,
                f"case.expected_reasons[{index}]",
                max_length=MAX_BENCHMARK_ID_LENGTH,
            )
            for index, item in enumerate(self.expected_reasons)
        )
        object.__setattr__(self, "expected_reasons", normalized_reasons)
        if len(set(self.expected_reasons)) != len(self.expected_reasons):
            raise ModelValidationError("case.expected_reasons must not contain duplicates")
        valid_reasons = {reason.value for reason in GateReason}
        unknown_reasons = sorted(set(self.expected_reasons) - valid_reasons)
        if unknown_reasons:
            raise ModelValidationError(
                "case.expected_reasons contains unknown reason codes: "
                + ", ".join(unknown_reasons)
            )

    @classmethod
    def from_dict(cls, value: Any) -> "EmptyBenchCase":
        if not isinstance(value, Mapping):
            raise ModelValidationError("case must be a JSON object")
        allowed = {
            "case_id",
            "pair_id",
            "variant",
            "description",
            "request",
            "expected_allowed",
            "expected_reasons",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ModelValidationError(f"case has unknown fields: {', '.join(unknown)}")
        strings: dict[str, str] = {}
        for name in ("case_id", "pair_id", "variant", "description"):
            limit = (
                MAX_BENCHMARK_DESCRIPTION_LENGTH
                if name == "description"
                else MAX_BENCHMARK_ID_LENGTH
            )
            strings[name] = bounded_single_line(
                value.get(name), f"case.{name}", max_length=limit
            )
        expected_allowed = value.get("expected_allowed")
        if not isinstance(expected_allowed, bool):
            raise ModelValidationError("case.expected_allowed must be a boolean")
        if "expected_reasons" not in value:
            raise ModelValidationError("case.expected_reasons is required")
        raw_reasons = value["expected_reasons"]
        if isinstance(raw_reasons, (str, bytes)) or not isinstance(raw_reasons, Sequence):
            raise ModelValidationError("case.expected_reasons must be an array of strings")
        reasons: list[str] = []
        for index, item in enumerate(raw_reasons):
            if not isinstance(item, str) or not item.strip():
                raise ModelValidationError(
                    f"case.expected_reasons[{index}] must be a non-empty string"
                )
            reasons.append(item.strip())
        return cls(
            **strings,
            request=NegativeClaimRequest.from_dict(value.get("request")),
            expected_allowed=expected_allowed,
            expected_reasons=tuple(reasons),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "pair_id": self.pair_id,
            "variant": self.variant,
            "description": self.description,
            "request": self.request.to_dict(),
            "expected_allowed": self.expected_allowed,
            "expected_reasons": list(self.expected_reasons),
        }


@dataclass(frozen=True, slots=True)
class EmptyBenchOutcome:
    case_id: str
    pair_id: str
    variant: str
    expected_allowed: bool
    actual_allowed: bool
    expected_reasons: tuple[str, ...]
    actual_reasons: tuple[str, ...]
    passed: bool
    decision: GateDecision

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "pair_id": self.pair_id,
            "variant": self.variant,
            "expected_allowed": self.expected_allowed,
            "actual_allowed": self.actual_allowed,
            "expected_reasons": list(self.expected_reasons),
            "actual_reasons": list(self.actual_reasons),
            "passed": self.passed,
            "decision": self.decision.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EmptyBenchReport:
    benchmark: str
    outcomes: tuple[EmptyBenchOutcome, ...]

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(outcome.passed for outcome in self.outcomes)

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.passed == self.total

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.total - self.passed,
                "all_passed": self.all_passed,
            },
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }


def parse_cases(value: Any) -> tuple[EmptyBenchCase, ...]:
    raw_cases: Any
    if isinstance(value, Mapping):
        unknown = sorted(set(value) - {"cases"})
        if unknown:
            raise ModelValidationError(
                f"benchmark input has unknown fields: {', '.join(unknown)}"
            )
        raw_cases = value.get("cases")
    else:
        raw_cases = value
    if isinstance(raw_cases, (str, bytes)) or not isinstance(raw_cases, Sequence):
        raise ModelValidationError("benchmark input must be an array or an object with cases")
    cases = tuple(EmptyBenchCase.from_dict(case) for case in raw_cases)
    return _validate_case_pairs(cases)


def _validate_case_pairs(
    cases: Iterable[EmptyBenchCase],
) -> tuple[EmptyBenchCase, ...]:
    """Materialize and validate the pair contract for every execution path."""

    materialized = tuple(cases)
    if any(not isinstance(case, EmptyBenchCase) for case in materialized):
        raise ModelValidationError(
            "benchmark cases must contain only EmptyBenchCase values"
        )
    if not materialized:
        raise ModelValidationError("benchmark input must contain at least one case")
    case_ids = [case.case_id for case in materialized]
    if len(set(case_ids)) != len(case_ids):
        raise ModelValidationError("benchmark case_id values must be unique")
    pairs: dict[str, list[EmptyBenchCase]] = {}
    for case in materialized:
        pairs.setdefault(case.pair_id, []).append(case)
    for pair_id in sorted(pairs):
        pair = pairs[pair_id]
        if len(pair) != 2:
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must contain exactly two cases"
            )
        if len({case.variant for case in pair}) != 2:
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must use two distinct variants"
            )
        allowed_cases = [case for case in pair if case.expected_allowed]
        rejected_cases = [case for case in pair if not case.expected_allowed]
        if len(allowed_cases) != 1 or len(rejected_cases) != 1:
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must have one allowed control and one rejected fault"
            )
        if allowed_cases[0].expected_reasons:
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} allowed control must expect no rejection reasons"
            )
        if not rejected_cases[0].expected_reasons:
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} rejected fault must declare exact expected reasons"
            )
        if _visible_signature(pair[0]) != _visible_signature(pair[1]):
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must preserve the visible observation and question"
            )
        if _sufficiency_signature(pair[0]) == _sufficiency_signature(pair[1]):
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must differ in at least one sufficiency fact"
            )
    return materialized


def _visible_signature(case: EmptyBenchCase) -> dict[str, Any]:
    request = case.request.to_dict()
    envelope = request["envelope"]
    source = envelope["source"]
    return {
        "subject": request["subject"],
        "mode": request["mode"],
        "evaluated_at": request["evaluated_at"],
        "schema_version": envelope["schema_version"],
        "query": envelope["query"],
        "matched_count": envelope["matched_count"],
        "observed_at": envelope["observed_at"],
        "source": {
            "system": source["system"],
            "locator": source["locator"],
            "adapter_version": source["adapter_version"],
        },
        "notes": envelope["notes"],
    }


def _sufficiency_signature(case: EmptyBenchCase) -> dict[str, Any]:
    request = case.request.to_dict()
    envelope = request["envelope"]
    return {
        "state": envelope["state"],
        "coverage": envelope["coverage"],
        "valid_until": envelope["valid_until"],
        "errors": envelope["errors"],
        "index_as_of": envelope["source"]["index_as_of"],
        "policy": request["policy"],
    }


def _run_validated_emptybench(
    cases: tuple[EmptyBenchCase, ...],
    *,
    benchmark: str,
) -> EmptyBenchReport:
    outcomes: list[EmptyBenchOutcome] = []
    for case in cases:
        decision = evaluate_negative_claim(case.request)
        actual_reasons = tuple(reason.value for reason in decision.reasons)
        passed = (
            decision.allowed is case.expected_allowed
            and actual_reasons == case.expected_reasons
        )
        outcomes.append(
            EmptyBenchOutcome(
                case_id=case.case_id,
                pair_id=case.pair_id,
                variant=case.variant,
                expected_allowed=case.expected_allowed,
                actual_allowed=decision.allowed,
                expected_reasons=case.expected_reasons,
                actual_reasons=actual_reasons,
                passed=passed,
                decision=decision,
            )
        )
    return EmptyBenchReport(benchmark=benchmark, outcomes=tuple(outcomes))


def run_emptybench(cases: Iterable[EmptyBenchCase]) -> EmptyBenchReport:
    """Run a caller-supplied corpus after enforcing the paired-case contract."""

    validated = _validate_case_pairs(cases)
    return _run_validated_emptybench(validated, benchmark="EmptyBench-custom")


def run_seed_emptybench(*, all_cases: bool = False) -> EmptyBenchReport:
    """Run only the package-owned seed corpus under the seed benchmark label."""

    cases = seed_cases() if all_cases else demo_cases()
    validated = _validate_case_pairs(cases)
    return _run_validated_emptybench(validated, benchmark="EmptyBench-seed")


def _request_dict(
    *,
    state: str = "ABSENT_WITHIN_SCOPE",
    examined_units: int = 100,
    population_basis: str = "EXACT",
    population_units: int | None = 100,
    declared_lower_bound: float | None = None,
    pages_examined: int | None = 5,
    pages_expected: int | None = 5,
    pagination_complete: bool = True,
    continuation_token_present: bool = False,
    partitions_examined: int | None = 2,
    partitions_expected: int | None = 2,
    partitions_complete: bool = True,
    timed_out: bool = False,
    permission_limited: bool = False,
    valid_until: str | None = "2026-08-21T13:00:00Z",
    index_as_of: str | None = "2026-08-21T11:59:00Z",
    mode: str = "SCOPED",
    authorization_boundary: str = "public repositories visible to the adapter token",
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "subject": "repositories matching the query",
        "mode": mode,
        "evaluated_at": "2026-08-21T12:05:00Z",
        "policy": dict({} if policy is None else policy),
        "envelope": {
            "schema_version": "0.1",
            "state": state,
            "query": {
                "target": "GitHub repository search",
                "predicate": "topic:evidence-state language:Python",
                "authorization_boundary": authorization_boundary,
                "time_start": "2026-08-21T00:00:00Z",
                "time_end": "2026-08-21T12:00:00Z",
                "exclusions": ["deleted repositories", "unindexed content"],
            },
            "coverage": {
                "examined_units": examined_units,
                "population_basis": population_basis,
                "population_units": population_units,
                "declared_lower_bound": declared_lower_bound,
                "pages_examined": pages_examined,
                "pages_expected": pages_expected,
                "pagination_complete": pagination_complete,
                "continuation_token_present": continuation_token_present,
                "partitions_examined": partitions_examined,
                "partitions_expected": partitions_expected,
                "partitions_complete": partitions_complete,
                "timed_out": timed_out,
                "interrupted": False,
                "permission_limited": permission_limited,
                "query_errors": [],
            },
            "matched_count": 0,
            "observed_at": "2026-08-21T12:00:00Z",
            "valid_until": valid_until,
            "source": {
                "system": "github-search",
                "locator": "repositories/search",
                "adapter_version": "seed-0.1",
                "index_as_of": index_as_of,
            },
            "errors": [],
            "notes": ["Synthetic EmptyBench seed case; not an external observation."],
        },
    }


def seed_case_dicts() -> list[dict[str, Any]]:
    """Return deterministic paired cases; no external data is implied."""

    return [
        {
            "case_id": "covered-complete",
            "pair_id": "covered-vs-partial",
            "variant": "covered",
            "description": "Zero matches after complete exact-population traversal.",
            "request": _request_dict(),
            "expected_allowed": True,
            "expected_reasons": [],
        },
        {
            "case_id": "partial-continuation",
            "pair_id": "covered-vs-partial",
            "variant": "partial",
            "description": "Zero matches before remaining result pages were traversed.",
            "request": _request_dict(
                state="PARTIAL",
                examined_units=60,
                pages_examined=3,
                pagination_complete=False,
                continuation_token_present=True,
            ),
            "expected_allowed": False,
            "expected_reasons": [
                "STATE_NOT_ABSENT_WITHIN_SCOPE",
                "COVERAGE_POLICY_NOT_MET",
            ],
        },
        {
            "case_id": "fresh-valid",
            "pair_id": "fresh-vs-stale",
            "variant": "fresh",
            "description": "Complete result remains inside its declared validity window.",
            "request": _request_dict(),
            "expected_allowed": True,
            "expected_reasons": [],
        },
        {
            "case_id": "expired-result",
            "pair_id": "fresh-vs-stale",
            "variant": "stale",
            "description": "The same empty result is evaluated after its validity window.",
            "request": _request_dict(valid_until="2026-08-21T12:01:00Z"),
            "expected_allowed": False,
            "expected_reasons": ["RESULT_EXPIRED"],
        },
        {
            "case_id": "declared-complete",
            "pair_id": "declared-vs-unknown-coverage",
            "variant": "declared",
            "description": "Unknown population has an explicit source-attested lower bound.",
            "request": _request_dict(
                population_basis="UNKNOWN",
                population_units=None,
                declared_lower_bound=1.0,
            ),
            "expected_allowed": True,
            "expected_reasons": [],
        },
        {
            "case_id": "unknown-coverage",
            "pair_id": "declared-vs-unknown-coverage",
            "variant": "unknown",
            "description": "Zero matches with no population denominator or coverage bound.",
            "request": _request_dict(
                population_basis="UNKNOWN",
                population_units=None,
                declared_lower_bound=None,
            ),
            "expected_allowed": False,
            "expected_reasons": ["COVERAGE_POLICY_NOT_MET"],
        },
        {
            "case_id": "authorized-scope-declared",
            "pair_id": "declared-vs-rejected-access-limit",
            "variant": "declared-access",
            "description": "Permission-limited search is qualified to a declared boundary.",
            "request": _request_dict(permission_limited=True),
            "expected_allowed": True,
            "expected_reasons": [],
        },
        {
            "case_id": "access-limit-rejected",
            "pair_id": "declared-vs-rejected-access-limit",
            "variant": "strict-policy",
            "description": "Local policy rejects even explicitly declared access limitations.",
            "request": _request_dict(
                permission_limited=True,
                policy={
                    "coverage": {"allow_permission_limited_scope": False},
                },
            ),
            "expected_allowed": False,
            "expected_reasons": ["COVERAGE_POLICY_NOT_MET"],
        },
        {
            "case_id": "completed-without-timeout",
            "pair_id": "complete-vs-timeout",
            "variant": "completed",
            "description": "A fully covered query completed without timeout.",
            "request": _request_dict(),
            "expected_allowed": True,
            "expected_reasons": [],
        },
        {
            "case_id": "timed-out-query",
            "pair_id": "complete-vs-timeout",
            "variant": "timeout",
            "description": "The same empty result is paired with a timeout fact.",
            "request": _request_dict(timed_out=True),
            "expected_allowed": False,
            "expected_reasons": ["COVERAGE_POLICY_NOT_MET"],
        },
    ]


def seed_cases() -> tuple[EmptyBenchCase, ...]:
    return tuple(EmptyBenchCase.from_dict(case) for case in seed_case_dicts())


def demo_cases() -> tuple[EmptyBenchCase, ...]:
    """Return the P0 operator pair: covered versus partial traversal."""

    return tuple(case for case in seed_cases() if case.pair_id == "covered-vs-partial")
