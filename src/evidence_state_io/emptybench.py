"""Deterministic EmptyBench corpus/oracle loading and scoring.

The corpus contains synthetic inputs, not expected decisions. Expected
decisions live in a separately versioned oracle artifact whose digest must be
retained independently by the caller. This is an integrity and custody
boundary, not authentication or proof that the oracle is correct.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hmac import compare_digest
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .canonical import (
    CANONICALIZATION_PROFILE,
    DIGEST_ALGORITHM,
    verify_canonical_digest,
)
from .gate import GateDecision, GateReason, NegativeClaimRequest, evaluate_negative_claim
from .models import (
    CoverageProfileReference,
    ModelValidationError,
    PopulationBasis,
    bounded_single_line,
    parse_datetime,
)
from .profiles import (
    COVERAGE_FINALITY_PROFILE_SCHEMA,
    FINALITY_METHOD,
    PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
    PROFILE_TRUST_SELECTION_SCHEMA,
    CoverageFinalityProfile,
    ProfileApplicability,
    ProfileCoverage,
    ProfileFinality,
    ProfileRegistryRecord,
    ProfileRegistrySnapshot,
    ProfileRegistryStatus,
    ProfileSource,
    ProfileTrustSelection,
    TrustedProfileContext,
)


EMPTYBENCH_CORPUS_SCHEMA = "esio-emptybench-corpus/1.0-candidate.1"
EMPTYBENCH_ORACLE_SCHEMA = "esio-emptybench-oracle/1.0-candidate.1"
EMPTYBENCH_REPORT_SCHEMA = "esio-emptybench-report/1.0-candidate.1"
SEED_BENCHMARK_ID = "EmptyBench-P0-seed"
SEED_BENCHMARK_VERSION = "1.0-candidate.1"
SEED_ORACLE_DIGEST = "sha256:543bf22c308ed1ee1436f6bd8bb9cc7353680c09d41b849c1af9216a8c730339"

MAX_BENCHMARK_ID_LENGTH = 128
MAX_BENCHMARK_DESCRIPTION_LENGTH = 512
MAX_BENCHMARK_CASES = 256
MAX_MUTATIONS_PER_CASE = 32
MAX_JSON_POINTER_LENGTH = 512
_SEED_CORPUS_FILE = "emptybench-p0-corpus.json"
_SEED_ORACLE_FILE = "emptybench-p0-oracle.json"


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelValidationError(f"{path} must be a JSON object")
    return value


def _exact_fields(value: Any, *, path: str, fields: set[str]) -> Mapping[str, Any]:
    data = _mapping(value, path)
    if any(not isinstance(key, str) for key in data):
        raise ModelValidationError(f"{path} field names must be strings")
    unknown = sorted(set(data) - fields)
    if unknown:
        raise ModelValidationError(f"{path} has unknown fields: {', '.join(unknown)}")
    missing = sorted(fields - set(data))
    if missing:
        raise ModelValidationError(f"{path} is missing fields: {', '.join(missing)}")
    return data


def _array(value: Any, path: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ModelValidationError(f"{path} must be an array")
    return value


def _identifier(value: Any, path: str) -> str:
    return bounded_single_line(value, path, max_length=MAX_BENCHMARK_ID_LENGTH)


def _description(value: Any, path: str) -> str:
    return bounded_single_line(value, path, max_length=MAX_BENCHMARK_DESCRIPTION_LENGTH)


def _sha256_digest(value: Any, path: str) -> str:
    candidate = _identifier(value, path)
    if len(candidate) != 71 or not candidate.startswith("sha256:"):
        raise ModelValidationError(f"{path} must be a lowercase SHA-256 digest")
    suffix = candidate.removeprefix("sha256:")
    if any(character not in "0123456789abcdef" for character in suffix):
        raise ModelValidationError(f"{path} must be a lowercase SHA-256 digest")
    return candidate


def _without_digest(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    payload = dict(value)
    payload.pop(field, None)
    return payload


def _decode_json_pointer(pointer: Any, path: str) -> tuple[str, ...]:
    normalized = bounded_single_line(pointer, path, max_length=MAX_JSON_POINTER_LENGTH)
    if not normalized.startswith("/") or normalized == "/":
        raise ModelValidationError(f"{path} must identify a non-root JSON value")
    segments: list[str] = []
    for raw_segment in normalized[1:].split("/"):
        index = 0
        decoded: list[str] = []
        while index < len(raw_segment):
            character = raw_segment[index]
            if character != "~":
                decoded.append(character)
                index += 1
                continue
            if index + 1 >= len(raw_segment) or raw_segment[index + 1] not in "01":
                raise ModelValidationError(f"{path} contains an invalid JSON Pointer escape")
            decoded.append("~" if raw_segment[index + 1] == "0" else "/")
            index += 2
        segment = "".join(decoded)
        if not segment:
            raise ModelValidationError(f"{path} must not contain an empty path segment")
        segments.append(segment)
    return tuple(segments)


def _replace_at_pointer(document: Any, pointer: tuple[str, ...], value: Any) -> None:
    current = document
    for depth, segment in enumerate(pointer[:-1]):
        location = "/" + "/".join(pointer[: depth + 1])
        if isinstance(current, Mapping):
            if segment not in current:
                raise ModelValidationError(f"case mutation path does not exist at {location}")
            current = current[segment]
            continue
        if isinstance(current, list):
            if not segment.isdigit() or (len(segment) > 1 and segment.startswith("0")):
                raise ModelValidationError(
                    f"case mutation path has an invalid array index at {location}"
                )
            item_index = int(segment)
            if item_index >= len(current):
                raise ModelValidationError(
                    f"case mutation array index is out of range at {location}"
                )
            current = current[item_index]
            continue
        raise ModelValidationError(f"case mutation path traverses a scalar at {location}")

    final = pointer[-1]
    if isinstance(current, Mapping):
        if final not in current:
            raise ModelValidationError("case mutation may replace only an existing object field")
        current[final] = deepcopy(value)
        return
    if isinstance(current, list):
        if not final.isdigit() or (len(final) > 1 and final.startswith("0")):
            raise ModelValidationError("case mutation has an invalid final array index")
        item_index = int(final)
        if item_index >= len(current):
            raise ModelValidationError("case mutation final array index is out of range")
        current[item_index] = deepcopy(value)
        return
    raise ModelValidationError("case mutation final parent must be an object or array")


@dataclass(frozen=True, slots=True)
class EmptyBenchMutation:
    pointer: str
    value: Any

    @classmethod
    def from_dict(cls, value: Any, path: str) -> "EmptyBenchMutation":
        data = _exact_fields(value, path=path, fields={"pointer", "value"})
        pointer = bounded_single_line(
            data["pointer"],
            f"{path}.pointer",
            max_length=MAX_JSON_POINTER_LENGTH,
        )
        _decode_json_pointer(pointer, f"{path}.pointer")
        return cls(pointer=pointer, value=deepcopy(data["value"]))

    def to_dict(self) -> dict[str, Any]:
        return {"pointer": self.pointer, "value": deepcopy(self.value)}


@dataclass(frozen=True, slots=True)
class EmptyBenchCase:
    case_id: str
    pair_id: str
    fault_class: str
    variant: str
    description: str
    request: NegativeClaimRequest
    mutations: tuple[EmptyBenchMutation, ...] = ()

    def __post_init__(self) -> None:
        for name in ("case_id", "pair_id", "fault_class", "variant"):
            object.__setattr__(self, name, _identifier(getattr(self, name), f"case.{name}"))
        object.__setattr__(self, "description", _description(self.description, "case.description"))
        if self.variant not in {"control", "fault"}:
            raise ModelValidationError("case.variant must be control or fault")
        if not isinstance(self.request, NegativeClaimRequest):
            raise ModelValidationError("case.request must be a NegativeClaimRequest")
        if any(not isinstance(item, EmptyBenchMutation) for item in self.mutations):
            raise ModelValidationError(
                "case.mutations must contain only EmptyBenchMutation values"
            )

    @classmethod
    def from_definition(
        cls,
        value: Any,
        *,
        base_request: Mapping[str, Any],
        path: str,
    ) -> "EmptyBenchCase":
        fields = {
            "case_id",
            "pair_id",
            "fault_class",
            "variant",
            "description",
            "mutations",
        }
        data = _exact_fields(value, path=path, fields=fields)
        raw_mutations = _array(data["mutations"], f"{path}.mutations")
        if len(raw_mutations) > MAX_MUTATIONS_PER_CASE:
            raise ModelValidationError(
                f"{path}.mutations exceeds the {MAX_MUTATIONS_PER_CASE}-entry limit"
            )
        mutations = tuple(
            EmptyBenchMutation.from_dict(item, f"{path}.mutations[{index}]")
            for index, item in enumerate(raw_mutations)
        )
        pointers = [mutation.pointer for mutation in mutations]
        if len(set(pointers)) != len(pointers):
            raise ModelValidationError(f"{path}.mutations must not repeat a JSON Pointer")
        request_payload = deepcopy(dict(base_request))
        for mutation in mutations:
            _replace_at_pointer(
                request_payload,
                _decode_json_pointer(mutation.pointer, f"{path}.mutations.pointer"),
                mutation.value,
            )
        return cls(
            case_id=_identifier(data["case_id"], f"{path}.case_id"),
            pair_id=_identifier(data["pair_id"], f"{path}.pair_id"),
            fault_class=_identifier(data["fault_class"], f"{path}.fault_class"),
            variant=_identifier(data["variant"], f"{path}.variant"),
            description=_description(data["description"], f"{path}.description"),
            request=NegativeClaimRequest.from_dict(request_payload),
            mutations=mutations,
        )

    @classmethod
    def from_dict(cls, value: Any) -> "EmptyBenchCase":
        """Parse one expanded case without accepting an embedded expectation."""

        fields = {
            "case_id",
            "pair_id",
            "fault_class",
            "variant",
            "description",
            "request",
        }
        data = _exact_fields(value, path="case", fields=fields)
        return cls(
            case_id=_identifier(data["case_id"], "case.case_id"),
            pair_id=_identifier(data["pair_id"], "case.pair_id"),
            fault_class=_identifier(data["fault_class"], "case.fault_class"),
            variant=_identifier(data["variant"], "case.variant"),
            description=_description(data["description"], "case.description"),
            request=NegativeClaimRequest.from_dict(data["request"]),
        )

    def definition_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "pair_id": self.pair_id,
            "fault_class": self.fault_class,
            "variant": self.variant,
            "description": self.description,
            "mutations": [mutation.to_dict() for mutation in self.mutations],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "pair_id": self.pair_id,
            "fault_class": self.fault_class,
            "variant": self.variant,
            "description": self.description,
            "request": self.request.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class EmptyBenchCorpus:
    corpus_schema: str
    benchmark_id: str
    benchmark_version: str
    canonicalization_profile: str
    digest_algorithm: str
    base_request: Mapping[str, Any]
    cases: tuple[EmptyBenchCase, ...]
    corpus_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "corpus_schema": self.corpus_schema,
            "benchmark_id": self.benchmark_id,
            "benchmark_version": self.benchmark_version,
            "canonicalization_profile": self.canonicalization_profile,
            "digest_algorithm": self.digest_algorithm,
            "base_request": deepcopy(dict(self.base_request)),
            "cases": [case.definition_dict() for case in self.cases],
            "corpus_digest": self.corpus_digest,
        }


@dataclass(frozen=True, slots=True)
class EmptyBenchOracleRule:
    rule_id: str
    expected_allowed: bool
    expected_reasons: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Any, path: str) -> "EmptyBenchOracleRule":
        data = _exact_fields(
            value,
            path=path,
            fields={"rule_id", "expected_allowed", "expected_reasons"},
        )
        expected_allowed = data["expected_allowed"]
        if not isinstance(expected_allowed, bool):
            raise ModelValidationError(f"{path}.expected_allowed must be a boolean")
        raw_reasons = _array(data["expected_reasons"], f"{path}.expected_reasons")
        reasons = tuple(
            _identifier(reason, f"{path}.expected_reasons[{index}]")
            for index, reason in enumerate(raw_reasons)
        )
        if len(set(reasons)) != len(reasons):
            raise ModelValidationError(f"{path}.expected_reasons must not contain duplicates")
        unknown = sorted(set(reasons) - {reason.value for reason in GateReason})
        if unknown:
            raise ModelValidationError(
                f"{path}.expected_reasons contains unknown reason codes: {', '.join(unknown)}"
            )
        if expected_allowed and reasons:
            raise ModelValidationError(f"{path} permit rule must not declare rejection reasons")
        if not expected_allowed and not reasons:
            raise ModelValidationError(f"{path} reject rule must declare at least one reason")
        return cls(
            rule_id=_identifier(data["rule_id"], f"{path}.rule_id"),
            expected_allowed=expected_allowed,
            expected_reasons=reasons,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "expected_allowed": self.expected_allowed,
            "expected_reasons": list(self.expected_reasons),
        }


@dataclass(frozen=True, slots=True)
class EmptyBenchOracleAssignment:
    case_id: str
    rule_id: str

    @classmethod
    def from_dict(cls, value: Any, path: str) -> "EmptyBenchOracleAssignment":
        data = _exact_fields(value, path=path, fields={"case_id", "rule_id"})
        return cls(
            case_id=_identifier(data["case_id"], f"{path}.case_id"),
            rule_id=_identifier(data["rule_id"], f"{path}.rule_id"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"case_id": self.case_id, "rule_id": self.rule_id}


@dataclass(frozen=True, slots=True)
class EmptyBenchOracle:
    oracle_schema: str
    oracle_id: str
    oracle_version: str
    benchmark_id: str
    benchmark_version: str
    corpus_schema: str
    corpus_digest: str
    canonicalization_profile: str
    digest_algorithm: str
    rules: tuple[EmptyBenchOracleRule, ...]
    assignments: tuple[EmptyBenchOracleAssignment, ...]
    oracle_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "oracle_schema": self.oracle_schema,
            "oracle_id": self.oracle_id,
            "oracle_version": self.oracle_version,
            "benchmark_id": self.benchmark_id,
            "benchmark_version": self.benchmark_version,
            "corpus_schema": self.corpus_schema,
            "corpus_digest": self.corpus_digest,
            "canonicalization_profile": self.canonicalization_profile,
            "digest_algorithm": self.digest_algorithm,
            "rules": [rule.to_dict() for rule in self.rules],
            "assignments": [assignment.to_dict() for assignment in self.assignments],
            "oracle_digest": self.oracle_digest,
        }


@dataclass(frozen=True, slots=True)
class EmptyBenchOutcome:
    case_id: str
    pair_id: str
    fault_class: str
    variant: str
    oracle_rule_id: str
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
            "fault_class": self.fault_class,
            "variant": self.variant,
            "oracle_rule_id": self.oracle_rule_id,
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
    benchmark_version: str
    corpus_schema: str
    corpus_digest: str
    oracle_schema: str
    oracle_id: str
    oracle_version: str
    oracle_digest: str
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

    @property
    def pairs_total(self) -> int:
        return len({outcome.pair_id for outcome in self.outcomes})

    @property
    def pairs_discriminated(self) -> int:
        pairs: dict[str, list[EmptyBenchOutcome]] = {}
        for outcome in self.outcomes:
            pairs.setdefault(outcome.pair_id, []).append(outcome)
        return sum(
            len(pair) == 2
            and all(outcome.passed for outcome in pair)
            and {outcome.actual_allowed for outcome in pair} == {False, True}
            for pair in pairs.values()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_schema": EMPTYBENCH_REPORT_SCHEMA,
            "benchmark": self.benchmark,
            "benchmark_version": self.benchmark_version,
            "corpus": {"schema": self.corpus_schema, "digest": self.corpus_digest},
            "oracle": {
                "schema": self.oracle_schema,
                "oracle_id": self.oracle_id,
                "version": self.oracle_version,
                "digest": self.oracle_digest,
            },
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.total - self.passed,
                "unsafe_permits": sum(
                    not outcome.expected_allowed and outcome.actual_allowed
                    for outcome in self.outcomes
                ),
                "false_rejections": sum(
                    outcome.expected_allowed and not outcome.actual_allowed
                    for outcome in self.outcomes
                ),
                "pairs_total": self.pairs_total,
                "pairs_discriminated": self.pairs_discriminated,
                "all_passed": self.all_passed,
            },
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }


def _validate_case_structure(cases: Iterable[EmptyBenchCase]) -> tuple[EmptyBenchCase, ...]:
    materialized = tuple(cases)
    if not materialized:
        raise ModelValidationError("benchmark corpus must contain at least one case")
    if len(materialized) > MAX_BENCHMARK_CASES:
        raise ModelValidationError(
            f"benchmark corpus exceeds the {MAX_BENCHMARK_CASES}-case limit"
        )
    if any(not isinstance(case, EmptyBenchCase) for case in materialized):
        raise ModelValidationError("benchmark corpus must contain EmptyBenchCase values")
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
        if {case.variant for case in pair} != {"control", "fault"}:
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must contain one control and one fault"
            )
        if len({case.fault_class for case in pair}) != 1:
            raise ModelValidationError(f"benchmark pair {pair_id!r} must use one fault_class")
        control = next(case for case in pair if case.variant == "control")
        fault = next(case for case in pair if case.variant == "fault")
        if _common_signature(control) != _common_signature(fault):
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must preserve its common observation context"
            )
        if control.fault_class != "QUERY_SEMANTICS" and (
            control.request.envelope.query.to_dict() != fault.request.envelope.query.to_dict()
        ):
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} changes the query outside QUERY_SEMANTICS"
            )
        if control.fault_class != "POSITIVE_CONTROL" and (
            control.request.envelope.matched_count != fault.request.envelope.matched_count
        ):
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} changes matched_count outside POSITIVE_CONTROL"
            )
        if control.request.to_dict() == fault.request.to_dict():
            raise ModelValidationError(
                f"benchmark pair {pair_id!r} must differ in at least one evidence fact"
            )
    return materialized


def _common_signature(case: EmptyBenchCase) -> dict[str, Any]:
    request = case.request.to_dict()
    envelope = request["envelope"]
    return {
        "subject": request["subject"],
        "mode": request["mode"],
        "evaluated_at": request["evaluated_at"],
        "schema_version": envelope["schema_version"],
        "observed_at": envelope["observed_at"],
        "notes": envelope["notes"],
    }


def parse_corpus(value: Any, *, expected_digest: str | None = None) -> EmptyBenchCorpus:
    fields = {
        "corpus_schema",
        "benchmark_id",
        "benchmark_version",
        "canonicalization_profile",
        "digest_algorithm",
        "base_request",
        "cases",
        "corpus_digest",
    }
    data = _exact_fields(value, path="corpus", fields=fields)
    if data["corpus_schema"] != EMPTYBENCH_CORPUS_SCHEMA:
        raise ModelValidationError(f"corpus.corpus_schema must be {EMPTYBENCH_CORPUS_SCHEMA}")
    if data["canonicalization_profile"] != CANONICALIZATION_PROFILE:
        raise ModelValidationError("corpus canonicalization_profile is unsupported")
    if data["digest_algorithm"] != DIGEST_ALGORITHM:
        raise ModelValidationError("corpus digest_algorithm is unsupported")
    corpus_digest = _sha256_digest(data["corpus_digest"], "corpus.corpus_digest")
    if not verify_canonical_digest(_without_digest(data, "corpus_digest"), corpus_digest):
        raise ModelValidationError("corpus digest does not match its canonical payload")
    if expected_digest is not None and not compare_digest(
        corpus_digest, _sha256_digest(expected_digest, "expected corpus digest")
    ):
        raise ModelValidationError("corpus digest does not match the retained expected digest")
    base_request = _mapping(data["base_request"], "corpus.base_request")
    NegativeClaimRequest.from_dict(base_request)
    raw_cases = _array(data["cases"], "corpus.cases")
    cases = _validate_case_structure(
        EmptyBenchCase.from_definition(
            case, base_request=base_request, path=f"corpus.cases[{index}]"
        )
        for index, case in enumerate(raw_cases)
    )
    return EmptyBenchCorpus(
        corpus_schema=EMPTYBENCH_CORPUS_SCHEMA,
        benchmark_id=_identifier(data["benchmark_id"], "corpus.benchmark_id"),
        benchmark_version=_identifier(data["benchmark_version"], "corpus.benchmark_version"),
        canonicalization_profile=CANONICALIZATION_PROFILE,
        digest_algorithm=DIGEST_ALGORITHM,
        base_request=deepcopy(dict(base_request)),
        cases=cases,
        corpus_digest=corpus_digest,
    )


def parse_cases(value: Any) -> tuple[EmptyBenchCase, ...]:
    """Parse expanded case records; this helper alone cannot score them."""

    raw_cases = value.get("cases") if isinstance(value, Mapping) else value
    return _validate_case_structure(
        EmptyBenchCase.from_dict(case) for case in _array(raw_cases, "benchmark cases")
    )


def parse_oracle(
    value: Any,
    corpus: EmptyBenchCorpus,
    *,
    expected_digest: str,
) -> EmptyBenchOracle:
    if not isinstance(corpus, EmptyBenchCorpus):
        raise ModelValidationError("oracle requires a parsed EmptyBenchCorpus")
    fields = {
        "oracle_schema",
        "oracle_id",
        "oracle_version",
        "benchmark_id",
        "benchmark_version",
        "corpus_schema",
        "corpus_digest",
        "canonicalization_profile",
        "digest_algorithm",
        "rules",
        "assignments",
        "oracle_digest",
    }
    data = _exact_fields(value, path="oracle", fields=fields)
    if data["oracle_schema"] != EMPTYBENCH_ORACLE_SCHEMA:
        raise ModelValidationError(f"oracle.oracle_schema must be {EMPTYBENCH_ORACLE_SCHEMA}")
    if data["canonicalization_profile"] != CANONICALIZATION_PROFILE:
        raise ModelValidationError("oracle canonicalization_profile is unsupported")
    if data["digest_algorithm"] != DIGEST_ALGORITHM:
        raise ModelValidationError("oracle digest_algorithm is unsupported")
    oracle_digest = _sha256_digest(data["oracle_digest"], "oracle.oracle_digest")
    if not verify_canonical_digest(_without_digest(data, "oracle_digest"), oracle_digest):
        raise ModelValidationError("oracle digest does not match its canonical payload")
    retained_digest = _sha256_digest(expected_digest, "expected oracle digest")
    if not compare_digest(oracle_digest, retained_digest):
        raise ModelValidationError("oracle digest does not match the retained expected digest")
    bindings = {
        "benchmark_id": corpus.benchmark_id,
        "benchmark_version": corpus.benchmark_version,
        "corpus_schema": corpus.corpus_schema,
        "corpus_digest": corpus.corpus_digest,
    }
    for field, expected in bindings.items():
        if data[field] != expected:
            raise ModelValidationError(f"oracle {field} does not bind the supplied corpus")
    rules = tuple(
        EmptyBenchOracleRule.from_dict(rule, f"oracle.rules[{index}]")
        for index, rule in enumerate(_array(data["rules"], "oracle.rules"))
    )
    if not rules:
        raise ModelValidationError("oracle.rules must contain at least one rule")
    rule_ids = [rule.rule_id for rule in rules]
    if len(set(rule_ids)) != len(rule_ids):
        raise ModelValidationError("oracle rule_id values must be unique")
    rules_by_id = {rule.rule_id: rule for rule in rules}
    assignments = tuple(
        EmptyBenchOracleAssignment.from_dict(assignment, f"oracle.assignments[{index}]")
        for index, assignment in enumerate(
            _array(data["assignments"], "oracle.assignments")
        )
    )
    assigned_case_ids = [assignment.case_id for assignment in assignments]
    if len(set(assigned_case_ids)) != len(assigned_case_ids):
        raise ModelValidationError("oracle assignments must not duplicate case_id values")
    unknown_rules = sorted(
        {assignment.rule_id for assignment in assignments} - set(rules_by_id)
    )
    if unknown_rules:
        raise ModelValidationError(
            "oracle assignments reference unknown rules: " + ", ".join(unknown_rules)
        )
    corpus_case_ids = {case.case_id for case in corpus.cases}
    assigned_ids = set(assigned_case_ids)
    missing = sorted(corpus_case_ids - assigned_ids)
    extra = sorted(assigned_ids - corpus_case_ids)
    if missing or extra:
        details = []
        if missing:
            details.append("missing cases: " + ", ".join(missing))
        if extra:
            details.append("unknown cases: " + ", ".join(extra))
        raise ModelValidationError("oracle assignment set mismatch; " + "; ".join(details))

    assignments_by_case = {assignment.case_id: assignment for assignment in assignments}
    pairs: dict[str, list[EmptyBenchCase]] = {}
    for case in corpus.cases:
        pairs.setdefault(case.pair_id, []).append(case)
    for pair_id, pair in sorted(pairs.items()):
        results = [
            rules_by_id[assignments_by_case[case.case_id].rule_id].expected_allowed
            for case in pair
        ]
        if sorted(results) != [False, True]:
            raise ModelValidationError(
                f"oracle pair {pair_id!r} must assign one permit and one rejection"
            )
        for case in pair:
            expectation = rules_by_id[assignments_by_case[case.case_id].rule_id]
            if (case.variant == "control") is not expectation.expected_allowed:
                raise ModelValidationError(
                    f"oracle assignment for {case.case_id!r} contradicts its case variant"
                )

    return EmptyBenchOracle(
        oracle_schema=EMPTYBENCH_ORACLE_SCHEMA,
        oracle_id=_identifier(data["oracle_id"], "oracle.oracle_id"),
        oracle_version=_identifier(data["oracle_version"], "oracle.oracle_version"),
        benchmark_id=corpus.benchmark_id,
        benchmark_version=corpus.benchmark_version,
        corpus_schema=corpus.corpus_schema,
        corpus_digest=corpus.corpus_digest,
        canonicalization_profile=CANONICALIZATION_PROFILE,
        digest_algorithm=DIGEST_ALGORITHM,
        rules=rules,
        assignments=assignments,
        oracle_digest=oracle_digest,
    )


def run_emptybench(
    corpus: EmptyBenchCorpus,
    oracle: EmptyBenchOracle,
    context: TrustedProfileContext,
    *,
    case_ids: Iterable[str] | None = None,
) -> EmptyBenchReport:
    """Score a parsed corpus against its separately parsed decision oracle."""

    if not isinstance(corpus, EmptyBenchCorpus):
        raise ModelValidationError("EmptyBench requires an EmptyBenchCorpus")
    if not isinstance(oracle, EmptyBenchOracle):
        raise ModelValidationError("EmptyBench requires an EmptyBenchOracle")
    if not isinstance(context, TrustedProfileContext):
        raise ModelValidationError(
            "EmptyBench requires an application-controlled TrustedProfileContext"
        )
    if (
        oracle.benchmark_id != corpus.benchmark_id
        or oracle.benchmark_version != corpus.benchmark_version
        or oracle.corpus_schema != corpus.corpus_schema
        or oracle.corpus_digest != corpus.corpus_digest
    ):
        raise ModelValidationError("EmptyBench oracle is not bound to the supplied corpus")

    cases_by_id = {case.case_id: case for case in corpus.cases}
    selected_ids = tuple(cases_by_id) if case_ids is None else tuple(case_ids)
    if not selected_ids:
        raise ModelValidationError("EmptyBench selection must contain at least one case")
    if len(set(selected_ids)) != len(selected_ids):
        raise ModelValidationError("EmptyBench selection must not contain duplicates")
    unknown_cases = sorted(set(selected_ids) - set(cases_by_id))
    if unknown_cases:
        raise ModelValidationError(
            "EmptyBench selection contains unknown cases: " + ", ".join(unknown_cases)
        )
    selected_pair_counts: dict[str, int] = {}
    for case_id in selected_ids:
        pair_id = cases_by_id[case_id].pair_id
        selected_pair_counts[pair_id] = selected_pair_counts.get(pair_id, 0) + 1
    incomplete_pairs = sorted(
        pair_id for pair_id, count in selected_pair_counts.items() if count != 2
    )
    if incomplete_pairs:
        raise ModelValidationError(
            "EmptyBench selection must include complete pairs: "
            + ", ".join(incomplete_pairs)
        )
    rules_by_id = {rule.rule_id: rule for rule in oracle.rules}
    assignments_by_case = {assignment.case_id: assignment for assignment in oracle.assignments}
    outcomes: list[EmptyBenchOutcome] = []
    for case_id in selected_ids:
        case = cases_by_id[case_id]
        assignment = assignments_by_case[case.case_id]
        expectation = rules_by_id[assignment.rule_id]
        decision = evaluate_negative_claim(case.request, context)
        actual_reasons = tuple(reason.value for reason in decision.reasons)
        passed = (
            decision.allowed is expectation.expected_allowed
            and actual_reasons == expectation.expected_reasons
        )
        outcomes.append(
            EmptyBenchOutcome(
                case_id=case.case_id,
                pair_id=case.pair_id,
                fault_class=case.fault_class,
                variant=case.variant,
                oracle_rule_id=expectation.rule_id,
                expected_allowed=expectation.expected_allowed,
                actual_allowed=decision.allowed,
                expected_reasons=expectation.expected_reasons,
                actual_reasons=actual_reasons,
                passed=passed,
                decision=decision,
            )
        )
    return EmptyBenchReport(
        benchmark=corpus.benchmark_id,
        benchmark_version=corpus.benchmark_version,
        corpus_schema=corpus.corpus_schema,
        corpus_digest=corpus.corpus_digest,
        oracle_schema=oracle.oracle_schema,
        oracle_id=oracle.oracle_id,
        oracle_version=oracle.oracle_version,
        oracle_digest=oracle.oracle_digest,
        outcomes=tuple(outcomes),
    )


def _seed_artifact_directory() -> Path:
    candidates = (
        Path(__file__).resolve().parents[2] / "benchmarks",
        Path.cwd().resolve() / "benchmarks",
    )
    for candidate in candidates:
        if (candidate / _SEED_CORPUS_FILE).is_file() and (
            candidate / _SEED_ORACLE_FILE
        ).is_file():
            return candidate
    raise ModelValidationError(
        "seed EmptyBench artifacts were not found; run from the repository or supply explicit corpus and oracle files"
    )


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ModelValidationError(f"duplicate JSON object key in benchmark artifact: {key}")
        result[key] = value
    return result


def _read_seed_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ModelValidationError(f"non-standard JSON constant in benchmark artifact: {value}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ModelValidationError("seed EmptyBench artifact could not be read") from exc


def seed_benchmark() -> tuple[EmptyBenchCorpus, EmptyBenchOracle]:
    directory = _seed_artifact_directory()
    corpus = parse_corpus(_read_seed_json(directory / _SEED_CORPUS_FILE))
    oracle = parse_oracle(
        _read_seed_json(directory / _SEED_ORACLE_FILE),
        corpus,
        expected_digest=SEED_ORACLE_DIGEST,
    )
    return corpus, oracle


def run_seed_emptybench(*, all_cases: bool = False) -> EmptyBenchReport:
    corpus, oracle = seed_benchmark()
    selected = None
    if not all_cases:
        selected = tuple(case.case_id for case in corpus.cases if case.pair_id == "pagination")
    return run_emptybench(corpus, oracle, seed_profile_context(), case_ids=selected)


def seed_cases() -> tuple[EmptyBenchCase, ...]:
    return seed_benchmark()[0].cases


def seed_case_dicts() -> list[dict[str, Any]]:
    return [case.to_dict() for case in seed_cases()]


def demo_cases() -> tuple[EmptyBenchCase, ...]:
    return tuple(case for case in seed_cases() if case.pair_id == "pagination")


def seed_profile_context() -> TrustedProfileContext:
    """Return the package-owned deterministic profile context for synthetic cases."""

    profile = CoverageFinalityProfile(
        profile_schema=COVERAGE_FINALITY_PROFILE_SCHEMA,
        profile_id="github-search-p0",
        profile_version="1.0.0",
        source_owner_id="example-source-owner",
        approval_authority_id="example-assurance-board",
        issuer_id="example-profile-publisher",
        issued_at=parse_datetime("2026-08-20T00:00:00Z", "seed_profile.issued_at"),
        effective_at=parse_datetime("2026-08-21T00:00:00Z", "seed_profile.effective_at"),
        expires_at=parse_datetime("2027-01-01T00:00:00Z", "seed_profile.expires_at"),
        source=ProfileSource(
            source_id="github-public-repositories",
            system="github-search",
            locator="repositories/search",
            adapter_id="github-search-adapter",
            adapter_version="example-0.4",
            authorization_context_id="public-search-adapter-context",
            accessible_population="public-repositories-visible-to-adapter",
        ),
        applicability=ProfileApplicability(
            target="GitHub repository search",
            predicate="topic:evidence-state language:Python",
            authorization_boundary="public repositories visible to the adapter token",
            required_exclusions=("deleted repositories", "unindexed content"),
            detection_assumptions=("repository is indexed by the declared search endpoint",),
        ),
        coverage=ProfileCoverage(
            population_basis=PopulationBasis.EXACT,
            population_units=100,
            pages_expected=5,
            partitions_expected=2,
            permission_limited=False,
            retention_seconds=86_400,
            blind_intervals=(),
            max_observation_age_seconds=3_600,
            max_index_age_seconds=3_600,
        ),
        finality=ProfileFinality(
            method=FINALITY_METHOD,
            late_arrival_bound_seconds=240,
            reopen_bound_seconds=0,
        ),
    )
    record = ProfileRegistryRecord(
        profile=profile,
        profile_digest=None,
        status=ProfileRegistryStatus.ACTIVE,
        revoked_at=None,
        revocation_effective_at=None,
        revocation_reason_code=None,
    )
    snapshot = ProfileRegistrySnapshot(
        snapshot_schema=PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
        registry_id="example-coverage-registry",
        snapshot_id="seed-2026-08-21",
        snapshot_version="1",
        issuer_id="example-registry-publisher",
        as_of=parse_datetime("2026-08-21T00:00:00Z", "seed_snapshot.as_of"),
        next_update_at=parse_datetime("2027-01-01T00:00:00Z", "seed_snapshot.next_update_at"),
        records=(record,),
        snapshot_digest=None,
    )
    assert snapshot.snapshot_digest is not None
    trust = ProfileTrustSelection(
        trust_schema=PROFILE_TRUST_SELECTION_SCHEMA,
        registry_id=snapshot.registry_id,
        snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.snapshot_version,
        snapshot_digest=snapshot.snapshot_digest,
        selected_profile_reference=CoverageProfileReference(
            registry_id=snapshot.registry_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_digest=profile.profile_digest,
        ),
        trusted_snapshot_issuer_ids=(snapshot.issuer_id,),
        trusted_profile_issuer_ids=(profile.issuer_id,),
        trusted_approval_authority_ids=(profile.approval_authority_id,),
        trust_selection_digest=None,
    )
    return TrustedProfileContext(snapshot=snapshot, trust_selection=trust)
