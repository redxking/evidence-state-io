"""Typed evidence-state models with strict JSON decoding.

The models deliberately separate a source's reported state from the policy
decision about whether that state can support a negative claim.  In
particular, ``ABSENT_WITHIN_SCOPE`` never represents global or absolute
absence; it is meaningful only together with the declared query scope and
coverage evidence carried by the same envelope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from fractions import Fraction
import json
from math import isfinite, nextafter
import re
from typing import Any, Mapping, Sequence
import unicodedata


MAX_EVIDENCE_STRING_LENGTH = 512
MAX_FRACTION_DECIMAL_PLACES = 12
MAX_INTEGER_DECIMAL_DIGITS = 512
_MAX_INTEGER_VALUE = 10**MAX_INTEGER_DECIMAL_DIGITS - 1
_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


class ModelValidationError(ValueError):
    """Raised when JSON input cannot be represented without ambiguity."""


class EvidenceState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT_WITHIN_SCOPE = "ABSENT_WITHIN_SCOPE"
    NOT_OBSERVED = "NOT_OBSERVED"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    INACCESSIBLE = "INACCESSIBLE"
    PENDING_WINDOW = "PENDING_WINDOW"
    FAILED = "FAILED"
    CONTRADICTORY = "CONTRADICTORY"


class PopulationBasis(str, Enum):
    """How the denominator behind a coverage assertion was established."""

    EXACT = "EXACT"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class ClaimMode(str, Enum):
    """The semantic strength of the requested negative claim."""

    SCOPED = "SCOPED"
    ABSOLUTE = "ABSOLUTE"


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelValidationError(f"{path} must be a JSON object")
    return value


def _reject_unknown(data: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ModelValidationError(f"{path} has unknown fields: {', '.join(unknown)}")


def _require_fields(data: Mapping[str, Any], required: set[str], path: str) -> None:
    missing = sorted(required - set(data))
    if missing:
        raise ModelValidationError(f"{path} is missing required fields: {', '.join(missing)}")


def bounded_single_line(
    value: Any,
    path: str,
    *,
    max_length: int = MAX_EVIDENCE_STRING_LENGTH,
) -> str:
    """Validate data that may later appear in operator-facing output."""

    if not isinstance(value, str) or not value.strip():
        raise ModelValidationError(f"{path} must be a non-empty string")
    result = value.strip()
    if len(result) > max_length:
        raise ModelValidationError(f"{path} exceeds the {max_length}-character limit")
    if len(result.splitlines()) != 1 or any(
        unicodedata.category(character).startswith("C") for character in result
    ):
        raise ModelValidationError(f"{path} must be a single line without control characters")
    return result


def _required_string(data: Mapping[str, Any], key: str, path: str) -> str:
    if key not in data:
        raise ModelValidationError(f"{path}.{key} is required")
    return bounded_single_line(data[key], f"{path}.{key}")


def _optional_string(data: Mapping[str, Any], key: str, path: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    return bounded_single_line(value, f"{path}.{key}")


def _nonnegative_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ModelValidationError(f"{path} must be a non-negative integer")
    if value > _MAX_INTEGER_VALUE:
        raise ModelValidationError(
            f"{path} exceeds the supported {MAX_INTEGER_DECIMAL_DIGITS}-digit integer limit"
        )
    return value


def _optional_nonnegative_int(value: Any, path: str) -> int | None:
    if value is None:
        return None
    return _nonnegative_int(value, path)


def _optional_fraction(value: Any, path: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ModelValidationError(f"{path} must be null or a number between 0 and 1")
    if isinstance(value, Decimal):
        exact = value
    elif isinstance(value, float):
        if not isfinite(value):
            raise ModelValidationError(f"{path} must be between 0 and 1")
        exact = Decimal(str(value))
    else:
        exact = Decimal(value)
    if not exact.is_finite() or not Decimal(0) <= exact <= Decimal(1):
        raise ModelValidationError(f"{path} must be between 0 and 1")
    if exact == 0:
        decimal_places = 0
    else:
        decimal_tuple = exact.as_tuple()
        trailing_zeros = 0
        for digit in reversed(decimal_tuple.digits):
            if digit != 0:
                break
            trailing_zeros += 1
        normalized_exponent = decimal_tuple.exponent + trailing_zeros
        decimal_places = max(0, -normalized_exponent)
    if decimal_places > MAX_FRACTION_DECIMAL_PLACES:
        raise ModelValidationError(
            f"{path} supports at most {MAX_FRACTION_DECIMAL_PLACES} decimal places"
        )
    result = float(exact)
    return 0.0 if result == 0.0 else result


def _normalized_float_fraction(value: float) -> Fraction:
    """Recover the accepted decimal semantics of a normalized fraction float."""

    return Fraction(Decimal(str(value)))


def _exact_ratio(numerator: int, denominator: int) -> Fraction:
    """Return an exact bounded ratio using the empty-population convention."""

    if denominator == 0:
        return Fraction(1, 1)
    return Fraction(numerator, denominator)


def _conservative_ratio_float(value: Fraction) -> float:
    """Serialize a fraction as a float that never exceeds the exact value."""

    result = float(value)
    if Fraction.from_float(result) > value:
        result = nextafter(result, 0.0)
    return 0.0 if result == 0.0 else result


def _required_bool(data: Mapping[str, Any], key: str, path: str) -> bool:
    if key not in data:
        raise ModelValidationError(f"{path}.{key} is required")
    value = data[key]
    if not isinstance(value, bool):
        raise ModelValidationError(f"{path}.{key} must be a boolean")
    return value


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ModelValidationError(f"{path} must be an array of strings")
    output: list[str] = []
    for index, item in enumerate(value):
        output.append(bounded_single_line(item, f"{path}[{index}]"))
    return tuple(output)


def _required_string_tuple(
    data: Mapping[str, Any], key: str, path: str
) -> tuple[str, ...]:
    if key not in data:
        raise ModelValidationError(f"{path}.{key} is required")
    if data[key] is None:
        raise ModelValidationError(f"{path}.{key} must be an array, not null")
    return _string_tuple(data[key], f"{path}.{key}")


def parse_datetime(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ModelValidationError(f"{path} must be an ISO-8601 timestamp")
    candidate = value.strip()
    if candidate != value:
        raise ModelValidationError(
            f"{path} must use ISO-8601 without surrounding whitespace"
        )
    if not _TIMESTAMP_PATTERN.fullmatch(candidate):
        raise ModelValidationError(
            f"{path} must use ISO-8601 with a UTC offset and at most 6 fractional-second digits"
        )
    if candidate.endswith("-00:00"):
        raise ModelValidationError(f"{path} must not use the RFC 3339 unknown offset -00:00")
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(candidate)
    except (OverflowError, ValueError) as exc:
        raise ModelValidationError(f"{path} must be an ISO-8601 timestamp") from exc
    return _validate_aware_datetime(result, path)


def optional_datetime(value: Any, path: str) -> datetime | None:
    if value is None:
        return None
    return parse_datetime(value, path)


def _validate_aware_datetime(value: Any, path: str) -> datetime:
    if not isinstance(value, datetime):
        raise ModelValidationError(f"{path} must be a datetime")
    try:
        offset = value.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise ModelValidationError(f"{path} has an invalid UTC offset") from exc
    if value.tzinfo is None or offset is None:
        raise ModelValidationError(f"{path} must include a UTC offset")
    try:
        normalized = value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ModelValidationError(f"{path} must be representable in UTC") from exc
    return normalized


def datetime_to_json(value: datetime) -> str:
    normalized = _validate_aware_datetime(value, "timestamp")
    return normalized.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class QueryScope:
    """The exact population and predicate a query attempted to inspect."""

    target: str
    predicate: str
    authorization_boundary: str
    time_start: datetime
    time_end: datetime
    exclusions: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("target", "predicate", "authorization_boundary"):
            object.__setattr__(
                self,
                name,
                bounded_single_line(getattr(self, name), f"query.{name}"),
            )
        if self.authorization_boundary.casefold() in {
            "unknown",
            "unspecified",
            "none",
            "n/a",
            "*",
            "all",
        }:
            raise ModelValidationError(
                "query.authorization_boundary must identify the accessible population"
            )
        object.__setattr__(
            self,
            "time_start",
            _validate_aware_datetime(self.time_start, "query.time_start"),
        )
        object.__setattr__(
            self,
            "time_end",
            _validate_aware_datetime(self.time_end, "query.time_end"),
        )
        if self.time_end < self.time_start:
            raise ModelValidationError("query.time_end must not precede query.time_start")
        if self.exclusions is None:
            raise ModelValidationError("query.exclusions must be an array, not null")
        object.__setattr__(
            self, "exclusions", _string_tuple(self.exclusions, "query.exclusions")
        )

    @classmethod
    def from_dict(cls, value: Any) -> "QueryScope":
        data = _mapping(value, "query")
        _reject_unknown(
            data,
            {
                "target",
                "predicate",
                "authorization_boundary",
                "time_start",
                "time_end",
                "exclusions",
            },
            "query",
        )
        _require_fields(
            data,
            {
                "target",
                "predicate",
                "authorization_boundary",
                "time_start",
                "time_end",
                "exclusions",
            },
            "query",
        )
        return cls(
            target=_required_string(data, "target", "query"),
            predicate=_required_string(data, "predicate", "query"),
            authorization_boundary=_required_string(data, "authorization_boundary", "query"),
            time_start=parse_datetime(data["time_start"], "query.time_start"),
            time_end=parse_datetime(data["time_end"], "query.time_end"),
            exclusions=_required_string_tuple(data, "exclusions", "query"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "predicate": self.predicate,
            "authorization_boundary": self.authorization_boundary,
            "time_start": datetime_to_json(self.time_start),
            "time_end": datetime_to_json(self.time_end),
            "exclusions": sorted(self.exclusions),
        }

    def qualification(self) -> str:
        parts = [
            f"target={json.dumps(self.target, ensure_ascii=False)}",
            f"predicate={json.dumps(self.predicate, ensure_ascii=False)}",
            f"authorization={json.dumps(self.authorization_boundary, ensure_ascii=False)}",
            f"from={datetime_to_json(self.time_start)}",
            f"through={datetime_to_json(self.time_end)}",
        ]
        if self.exclusions:
            parts.append(
                "excluding="
                + json.dumps(sorted(self.exclusions), ensure_ascii=False, separators=(",", ":"))
            )
        return ", ".join(parts)


@dataclass(frozen=True, slots=True, kw_only=True)
class CoverageEvidence:
    """Auditable inputs used to calculate a conservative coverage lower bound."""

    examined_units: int
    population_basis: PopulationBasis
    pagination_complete: bool
    continuation_token_present: bool
    partitions_complete: bool
    timed_out: bool
    interrupted: bool
    permission_limited: bool
    query_errors: tuple[str, ...]
    population_units: int | None = None
    declared_lower_bound: float | None = None
    pages_examined: int | None = None
    pages_expected: int | None = None
    partitions_examined: int | None = None
    partitions_expected: int | None = None

    def __post_init__(self) -> None:
        _nonnegative_int(self.examined_units, "coverage.examined_units")
        if not isinstance(self.population_basis, PopulationBasis):
            raise ModelValidationError("coverage.population_basis must be a PopulationBasis")
        for name in (
            "pagination_complete",
            "continuation_token_present",
            "partitions_complete",
            "timed_out",
            "interrupted",
            "permission_limited",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ModelValidationError(f"coverage.{name} must be a boolean")
        if self.population_units is not None:
            _nonnegative_int(self.population_units, "coverage.population_units")
        if self.population_basis is PopulationBasis.EXACT and self.population_units is None:
            raise ModelValidationError(
                "coverage.population_units is required when population_basis is EXACT"
            )
        if self.population_basis is PopulationBasis.UNKNOWN and self.population_units is not None:
            raise ModelValidationError(
                "coverage.population_units must be null when population_basis is UNKNOWN"
            )
        if (
            self.population_basis is PopulationBasis.EXACT
            and self.population_units is not None
            and self.examined_units > self.population_units
        ):
            raise ModelValidationError(
                "coverage.examined_units cannot exceed an exact population_units value"
            )
        normalized_declared_lower_bound = _optional_fraction(
            self.declared_lower_bound, "coverage.declared_lower_bound"
        )
        object.__setattr__(
            self, "declared_lower_bound", normalized_declared_lower_bound
        )
        for name in (
            "pages_examined",
            "pages_expected",
            "partitions_examined",
            "partitions_expected",
        ):
            value = getattr(self, name)
            if value is not None:
                _nonnegative_int(value, f"coverage.{name}")
        if (self.pages_examined is None) != (self.pages_expected is None):
            raise ModelValidationError(
                "coverage.pages_examined and pages_expected must both be present or both be null"
            )
        if (self.partitions_examined is None) != (self.partitions_expected is None):
            raise ModelValidationError(
                "coverage.partitions_examined and partitions_expected must both be present or both be null"
            )
        if (
            self.pages_examined is not None
            and self.pages_expected is not None
            and self.pages_examined > self.pages_expected
        ):
            raise ModelValidationError("coverage.pages_examined cannot exceed pages_expected")
        if (
            self.partitions_examined is not None
            and self.partitions_expected is not None
            and self.partitions_examined > self.partitions_expected
        ):
            raise ModelValidationError(
                "coverage.partitions_examined cannot exceed partitions_expected"
            )
        if self.query_errors is None:
            raise ModelValidationError("coverage.query_errors must be an array, not null")
        object.__setattr__(
            self,
            "query_errors",
            _string_tuple(self.query_errors, "coverage.query_errors"),
        )
        if self.pagination_complete and self.continuation_token_present:
            raise ModelValidationError(
                "coverage.pagination_complete cannot be true while a continuation token remains"
            )
        if (
            self.pagination_complete
            and self.pages_examined is not None
            and self.pages_expected is not None
            and self.pages_examined != self.pages_expected
        ):
            raise ModelValidationError(
                "coverage.pagination_complete contradicts incomplete page counts"
            )
        if (
            self.partitions_complete
            and self.partitions_examined is not None
            and self.partitions_expected is not None
            and self.partitions_examined != self.partitions_expected
        ):
            raise ModelValidationError(
                "coverage.partitions_complete contradicts incomplete partition counts"
            )
        deterministic_bounds: list[Fraction] = []
        if self.population_basis is PopulationBasis.EXACT and self.population_units is not None:
            deterministic_bounds.append(
                _exact_ratio(self.examined_units, self.population_units)
            )
        if self.pages_examined is not None and self.pages_expected is not None:
            deterministic_bounds.append(
                _exact_ratio(self.pages_examined, self.pages_expected)
            )
        if self.partitions_examined is not None and self.partitions_expected is not None:
            deterministic_bounds.append(
                _exact_ratio(self.partitions_examined, self.partitions_expected)
            )
        if (
            self.declared_lower_bound is not None
            and deterministic_bounds
            and _normalized_float_fraction(self.declared_lower_bound)
            > min(deterministic_bounds)
        ):
            raise ModelValidationError(
                "coverage.declared_lower_bound cannot exceed the computed deterministic bound"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "CoverageEvidence":
        data = _mapping(value, "coverage")
        allowed = {
            "examined_units",
            "population_basis",
            "population_units",
            "declared_lower_bound",
            "pages_examined",
            "pages_expected",
            "pagination_complete",
            "continuation_token_present",
            "partitions_examined",
            "partitions_expected",
            "partitions_complete",
            "timed_out",
            "interrupted",
            "permission_limited",
            "query_errors",
        }
        _reject_unknown(data, allowed, "coverage")
        _require_fields(
            data,
            {
                "examined_units",
                "population_basis",
                "pagination_complete",
                "continuation_token_present",
                "partitions_complete",
                "timed_out",
                "interrupted",
                "permission_limited",
                "query_errors",
            },
            "coverage",
        )
        try:
            basis = PopulationBasis(data.get("population_basis"))
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                "coverage.population_basis must be EXACT, ESTIMATED, or UNKNOWN"
            ) from exc
        return cls(
            examined_units=_nonnegative_int(
                data.get("examined_units"), "coverage.examined_units"
            ),
            population_basis=basis,
            population_units=_optional_nonnegative_int(
                data.get("population_units"), "coverage.population_units"
            ),
            declared_lower_bound=data.get("declared_lower_bound"),
            pages_examined=_optional_nonnegative_int(
                data.get("pages_examined"), "coverage.pages_examined"
            ),
            pages_expected=_optional_nonnegative_int(
                data.get("pages_expected"), "coverage.pages_expected"
            ),
            pagination_complete=_required_bool(data, "pagination_complete", "coverage"),
            continuation_token_present=_required_bool(
                data, "continuation_token_present", "coverage"
            ),
            partitions_examined=_optional_nonnegative_int(
                data.get("partitions_examined"), "coverage.partitions_examined"
            ),
            partitions_expected=_optional_nonnegative_int(
                data.get("partitions_expected"), "coverage.partitions_expected"
            ),
            partitions_complete=_required_bool(data, "partitions_complete", "coverage"),
            timed_out=_required_bool(data, "timed_out", "coverage"),
            interrupted=_required_bool(data, "interrupted", "coverage"),
            permission_limited=_required_bool(data, "permission_limited", "coverage"),
            query_errors=_required_string_tuple(data, "query_errors", "coverage"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "examined_units": self.examined_units,
            "population_basis": self.population_basis.value,
            "population_units": self.population_units,
            "declared_lower_bound": self.declared_lower_bound,
            "pages_examined": self.pages_examined,
            "pages_expected": self.pages_expected,
            "pagination_complete": self.pagination_complete,
            "continuation_token_present": self.continuation_token_present,
            "partitions_examined": self.partitions_examined,
            "partitions_expected": self.partitions_expected,
            "partitions_complete": self.partitions_complete,
            "timed_out": self.timed_out,
            "interrupted": self.interrupted,
            "permission_limited": self.permission_limited,
            "query_errors": sorted(self.query_errors),
        }


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    """Identity and currentness metadata for the queried source."""

    system: str
    locator: str
    adapter_version: str | None = None
    index_as_of: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("system", "locator"):
            object.__setattr__(
                self,
                name,
                bounded_single_line(getattr(self, name), f"source.{name}"),
            )
        if self.adapter_version is not None and (
            not isinstance(self.adapter_version, str)
        ):
            raise ModelValidationError("source.adapter_version must be a non-empty string or null")
        if self.adapter_version is not None:
            object.__setattr__(
                self,
                "adapter_version",
                bounded_single_line(
                    self.adapter_version, "source.adapter_version"
                ),
            )
        if self.index_as_of is not None:
            object.__setattr__(
                self,
                "index_as_of",
                _validate_aware_datetime(self.index_as_of, "source.index_as_of"),
            )

    @classmethod
    def from_dict(cls, value: Any) -> "SourceDescriptor":
        data = _mapping(value, "source")
        _reject_unknown(
            data, {"system", "locator", "adapter_version", "index_as_of"}, "source"
        )
        return cls(
            system=_required_string(data, "system", "source"),
            locator=_required_string(data, "locator", "source"),
            adapter_version=_optional_string(data, "adapter_version", "source"),
            index_as_of=optional_datetime(data.get("index_as_of"), "source.index_as_of"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "locator": self.locator,
            "adapter_version": self.adapter_version,
            "index_as_of": datetime_to_json(self.index_as_of) if self.index_as_of else None,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceEnvelope:
    """A tool result plus the evidence needed to interpret its epistemic state."""

    schema_version: str
    state: EvidenceState
    query: QueryScope
    coverage: CoverageEvidence
    matched_count: int
    observed_at: datetime
    source: SourceDescriptor
    errors: tuple[str, ...]
    valid_until: datetime | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.state, EvidenceState):
            raise ModelValidationError("state must be an EvidenceState")
        if not isinstance(self.query, QueryScope):
            raise ModelValidationError("query must be a QueryScope")
        if not isinstance(self.coverage, CoverageEvidence):
            raise ModelValidationError("coverage must be CoverageEvidence")
        if not isinstance(self.source, SourceDescriptor):
            raise ModelValidationError("source must be a SourceDescriptor")
        _nonnegative_int(self.matched_count, "matched_count")
        if self.state is EvidenceState.PRESENT and self.matched_count == 0:
            raise ModelValidationError("PRESENT requires matched_count greater than zero")
        if self.state is EvidenceState.ABSENT_WITHIN_SCOPE and self.matched_count != 0:
            raise ModelValidationError("ABSENT_WITHIN_SCOPE requires matched_count equal to zero")
        object.__setattr__(
            self,
            "observed_at",
            _validate_aware_datetime(self.observed_at, "observed_at"),
        )
        if (
            self.source.index_as_of is not None
            and self.source.index_as_of > self.observed_at
        ):
            raise ModelValidationError(
                "source.index_as_of must not be after observed_at"
            )
        if self.query.time_end > self.observed_at:
            raise ModelValidationError("query.time_end must not be after observed_at")
        if self.valid_until is not None:
            object.__setattr__(
                self,
                "valid_until",
                _validate_aware_datetime(self.valid_until, "valid_until"),
            )
            if self.valid_until < self.observed_at:
                raise ModelValidationError("valid_until must not precede observed_at")
        if self.errors is None:
            raise ModelValidationError("errors must be an array, not null")
        object.__setattr__(self, "errors", _string_tuple(self.errors, "errors"))
        object.__setattr__(self, "notes", _string_tuple(self.notes, "notes"))
        if self.schema_version != "0.1":
            raise ModelValidationError("schema_version must be the supported string value '0.1'")

    @classmethod
    def from_dict(cls, value: Any) -> "EvidenceEnvelope":
        data = _mapping(value, "envelope")
        allowed = {
            "state",
            "query",
            "coverage",
            "matched_count",
            "observed_at",
            "valid_until",
            "source",
            "errors",
            "notes",
            "schema_version",
        }
        _reject_unknown(data, allowed, "envelope")
        _require_fields(data, {"schema_version", "errors"}, "envelope")
        try:
            state = EvidenceState(data.get("state"))
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                "envelope.state must be a recognized evidence state"
            ) from exc
        if "matched_count" not in data:
            raise ModelValidationError("envelope.matched_count is required")
        schema_version = data["schema_version"]
        if not isinstance(schema_version, str):
            raise ModelValidationError("envelope.schema_version must be the string '0.1'")
        return cls(
            state=state,
            query=QueryScope.from_dict(data.get("query")),
            coverage=CoverageEvidence.from_dict(data.get("coverage")),
            matched_count=_nonnegative_int(data.get("matched_count"), "envelope.matched_count"),
            observed_at=parse_datetime(data.get("observed_at"), "envelope.observed_at"),
            valid_until=optional_datetime(data.get("valid_until"), "envelope.valid_until"),
            source=SourceDescriptor.from_dict(data.get("source")),
            errors=_required_string_tuple(data, "errors", "envelope"),
            notes=_string_tuple(data.get("notes"), "envelope.notes"),
            schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "state": self.state.value,
            "query": self.query.to_dict(),
            "coverage": self.coverage.to_dict(),
            "matched_count": self.matched_count,
            "observed_at": datetime_to_json(self.observed_at),
            "valid_until": datetime_to_json(self.valid_until) if self.valid_until else None,
            "source": self.source.to_dict(),
            "errors": sorted(self.errors),
            "notes": sorted(self.notes),
        }
