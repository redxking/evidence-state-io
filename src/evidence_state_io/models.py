"""Typed evidence-state models with strict JSON decoding.

The models deliberately separate a source's reported state from the policy
decision about whether that state can support a negative claim.  In
particular, ``ABSENT_WITHIN_SCOPE`` never represents global or absolute
absence; it is meaningful only together with the declared query scope and
coverage evidence carried by the same envelope.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from hashlib import sha256
from math import isfinite, nextafter
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .errors import ModelValidationError, ValidationErrorCode

MAX_EVIDENCE_STRING_LENGTH = 512
MAX_FRACTION_DECIMAL_PLACES = 12
MAX_INTEGER_DECIMAL_DIGITS = 512
MAX_SOURCE_ACCOUNTING_ENTRIES = 64
MAX_SOURCE_ID_LENGTH = 128
_MAX_INTEGER_VALUE = 10**MAX_INTEGER_DECIMAL_DIGITS - 1
_SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._:-]{0,126}[a-z0-9])?$")
_IMMUTABLE_VERSION_PATTERN = re.compile(
    r"^(?:"
    r"(?:[a-z][a-z0-9._:-]*-)?\d+\.\d+(?:\.\d+)*"
    r"(?:-[a-z0-9]+(?:[._-][a-z0-9]+)*)?"
    r"|\d+"
    r"|git:[0-9a-f]{40}"
    r"|sha256:[0-9a-f]{64}"
    r")$"
)
_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_DECLARATION_PLACEHOLDERS = frozenset({"unknown", "unspecified", "none", "n/a"})
_UNBOUNDED_DECLARATION_PLACEHOLDERS = frozenset({"*", "all"})
_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)
_EXPLICIT_CREDENTIAL_PATTERN = re.compile(
    r"^(?:authorization|bearer|basic|cookie|password|passwd|secret|session|"
    r"token|access_token|refresh_token|api_key|apikey):.+$"
)
_KNOWN_TOKEN_PATTERN = re.compile(
    r"^(?:"
    r"gh[pousr]_[a-z0-9]{20,}"
    r"|github_pat_[a-z0-9_]{20,}"
    r"|glpat-[a-z0-9_-]{20,}"
    r"|sk-[a-z0-9_-]{20,}"
    r"|xox[baprs]-[a-z0-9-]{10,}"
    r"|ya29\.[a-z0-9_-]{20,}"
    r"|akia[a-z0-9]{16}"
    r")$"
)
_JWT_LIKE_PATTERN = re.compile(r"^eyj[a-z0-9_-]{5,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{16,}$")
_OPAQUE_TOKEN_PATTERN = re.compile(r"^(?=.{48,128}$)(?=[a-z0-9]*[a-z])(?=[a-z0-9]*[0-9])[a-z0-9]+$")


AUTHORIZATION_CONTEXT_IDENTIFIER_PROFILE = "esio-authorization-context-identifier/1.0-candidate.1"
EVIDENCE_STATE_TRANSITION_MODEL = "esio-evidence-state-transition-model/1.0-candidate.1"


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


EVIDENCE_STATE_INTERPRETATIONS: Mapping[EvidenceState, str] = MappingProxyType(
    {
        EvidenceState.PRESENT: (
            "One or more in-scope matches were observed; completeness is not implied."
        ),
        EvidenceState.ABSENT_WITHIN_SCOPE: (
            "Zero matches were observed and every condition required by the named "
            "coverage policy passed for the declared scope and evaluation time."
        ),
        EvidenceState.NOT_OBSERVED: (
            "No match was observed, but sufficient absence conditions were not established."
        ),
        EvidenceState.PARTIAL: (
            "Only a known subset of the required population, pages, partitions, fields, "
            "or time range was evaluated."
        ),
        EvidenceState.STALE: (
            "Evidence exceeded the applicable freshness condition at evaluation time."
        ),
        EvidenceState.INACCESSIBLE: (
            "Required evidence could not be accessed within the declared authorization "
            "or policy boundary."
        ),
        EvidenceState.PENDING_WINDOW: (
            "The applicable observation or finality horizon had not closed."
        ),
        EvidenceState.FAILED: (
            "The observation operation did not complete successfully or returned a "
            "disqualifying error."
        ),
        EvidenceState.CONTRADICTORY: (
            "Required evidence sources or claims are mutually inconsistent under the policy."
        ),
    }
)

_NONINITIAL_EVIDENCE_STATES = tuple(
    state for state in EvidenceState if state is not EvidenceState.NOT_OBSERVED
)
_ALLOWED_EVIDENCE_STATE_TRANSITIONS: Mapping[EvidenceState, tuple[EvidenceState, ...]] = (
    MappingProxyType(
        {
            EvidenceState.PRESENT: (EvidenceState.PRESENT,),
            EvidenceState.ABSENT_WITHIN_SCOPE: _NONINITIAL_EVIDENCE_STATES,
            EvidenceState.NOT_OBSERVED: tuple(EvidenceState),
            EvidenceState.PARTIAL: _NONINITIAL_EVIDENCE_STATES,
            EvidenceState.STALE: _NONINITIAL_EVIDENCE_STATES,
            EvidenceState.INACCESSIBLE: _NONINITIAL_EVIDENCE_STATES,
            EvidenceState.PENDING_WINDOW: _NONINITIAL_EVIDENCE_STATES,
            EvidenceState.FAILED: _NONINITIAL_EVIDENCE_STATES,
            EvidenceState.CONTRADICTORY: _NONINITIAL_EVIDENCE_STATES,
        }
    )
)


def _require_transition_model(value: Any) -> str:
    if type(value) is not str or value != EVIDENCE_STATE_TRANSITION_MODEL:
        raise ModelValidationError(
            "transition_model must identify the exact supported "
            f"{EVIDENCE_STATE_TRANSITION_MODEL} contract",
            code=ValidationErrorCode.UNSUPPORTED_CONTRACT,
        )
    return EVIDENCE_STATE_TRANSITION_MODEL


def allowed_evidence_state_transitions(
    state: EvidenceState,
    *,
    transition_model: str = EVIDENCE_STATE_TRANSITION_MODEL,
) -> tuple[EvidenceState, ...]:
    """Return successors in stable taxonomy order for one claim lineage.

    A lineage fixes the schema, normalized query fingerprint, and declared
    source set.  Each transition is represented by a new immutable envelope;
    this API never mutates or validates the successor evidence itself.
    """

    _require_transition_model(transition_model)
    if not isinstance(state, EvidenceState):
        raise ModelValidationError("state must be an EvidenceState")
    return _ALLOWED_EVIDENCE_STATE_TRANSITIONS[state]


def is_evidence_state_transition_allowed(
    prior_state: EvidenceState,
    next_state: EvidenceState,
    *,
    transition_model: str = EVIDENCE_STATE_TRANSITION_MODEL,
) -> bool:
    """Return whether a successor classification is allowed in the model."""

    if not isinstance(next_state, EvidenceState):
        raise ModelValidationError("next_state must be an EvidenceState")
    return next_state in allowed_evidence_state_transitions(
        prior_state,
        transition_model=transition_model,
    )


@dataclass(frozen=True, slots=True)
class EvidenceStateTransition:
    """Version-bound transition between successive immutable envelopes."""

    transition_model: str
    prior_state: EvidenceState
    next_state: EvidenceState

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_model",
            _require_transition_model(self.transition_model),
        )
        if not isinstance(self.prior_state, EvidenceState):
            raise ModelValidationError("prior_state must be an EvidenceState")
        if not isinstance(self.next_state, EvidenceState):
            raise ModelValidationError("next_state must be an EvidenceState")
        if not is_evidence_state_transition_allowed(
            self.prior_state,
            self.next_state,
            transition_model=self.transition_model,
        ):
            raise ModelValidationError(
                f"transition from {self.prior_state.value} to "
                f"{self.next_state.value} is not allowed by "
                f"{self.transition_model}",
                code=ValidationErrorCode.STATE_TRANSITION_INVALID,
            )

    @classmethod
    def from_dict(
        cls,
        value: Any,
        path: str = "evidence_state_transition",
    ) -> "EvidenceStateTransition":
        if not isinstance(value, Mapping):
            raise ModelValidationError(f"{path} must be a JSON object")
        allowed = {"transition_model", "prior_state", "next_state"}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ModelValidationError(f"{path} has unknown fields: {', '.join(unknown)}")
        missing = sorted(allowed - set(value))
        if missing:
            raise ModelValidationError(f"{path} is missing required fields: {', '.join(missing)}")
        _require_transition_model(value["transition_model"])
        try:
            prior_state = EvidenceState(value["prior_state"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                f"{path}.prior_state must be an exact EvidenceState value"
            ) from exc
        try:
            next_state = EvidenceState(value["next_state"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                f"{path}.next_state must be an exact EvidenceState value"
            ) from exc
        return cls(
            transition_model=EVIDENCE_STATE_TRANSITION_MODEL,
            prior_state=prior_state,
            next_state=next_state,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "transition_model": self.transition_model,
            "prior_state": self.prior_state.value,
            "next_state": self.next_state.value,
        }


class PopulationBasis(str, Enum):
    """How the denominator behind a coverage assertion was established."""

    EXACT = "EXACT"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class ClaimMode(str, Enum):
    """The semantic strength of the requested negative claim."""

    SCOPED = "SCOPED"
    ABSOLUTE = "ABSOLUTE"


# A fail-closed bound on the multi-source composition surface (ADR-0015),
# chosen so a composed assessment stays reviewable by hand.
MAX_REQUIRED_SOURCES = 4

# Schema `1.0` is the single-source contract and never changes. Schema `1.1`
# adds multi-source composition; a `1.0` envelope may not use it, so every
# existing record keeps its exact meaning and canonical form.
SCHEMA_VERSION_SINGLE_SOURCE = "1.0"
SCHEMA_VERSION_COMPOSED = "1.1"
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION_SINGLE_SOURCE, SCHEMA_VERSION_COMPOSED})

#: Fields that carry one source's own assessment rather than its accounting.
#: A schema 1.0 observation carries none of them, so its canonical form is
#: byte-identical to what it was before composition existed.  A composed
#: envelope must supply every one of them except ``valid_until`` for each
#: REQUIRED source, because composition is a conclusion drawn from per-source
#: evidence and cannot be drawn from evidence that was never supplied.
SOURCE_ASSESSMENT_FIELDS: tuple[str, ...] = (
    "coverage",
    "state",
    "matched_count",
    "observed_at",
    "valid_until",
)
REQUIRED_SOURCE_ASSESSMENT_FIELDS: tuple[str, ...] = (
    "coverage",
    "state",
    "matched_count",
    "observed_at",
)


class CompositionMode(str, Enum):
    """Declared intent when a query names more than one required source.

    Absent means single-source, which is the schema 1.0 behaviour and is
    unchanged. `PARTITION` is deliberately not defined: it is the only mode in
    which coverage accumulates, and no governed profile can yet express the
    disjoint accessible subpopulation it would require.
    """

    CORROBORATION = "CORROBORATION"


class SourceRole(str, Enum):
    """The P0 role of the single source declared for a query."""

    REQUIRED = "REQUIRED"


class SourceObservationStatus(str, Enum):
    """Runtime status of one declared source.

    ``OBSERVED`` means that the source produced an observation.  It does not
    imply sufficient coverage, freshness, finality, or error-free execution;
    those facts remain independently evaluated.
    """

    OBSERVED = "OBSERVED"
    NOT_OBSERVED = "NOT_OBSERVED"
    INACCESSIBLE = "INACCESSIBLE"
    PENDING = "PENDING"
    STALE = "STALE"
    FAILED = "FAILED"
    CONTRADICTORY = "CONTRADICTORY"
    UNKNOWN = "UNKNOWN"


#: Which evidence states a given runtime status can honestly carry.
#:
#: A source that failed, was never reached, or is still inside its window has
#: not observed an in-scope absence, and no producer may relabel it as one.
#: Without this table a composed envelope could reach a permit by declaring
#: ABSENT_WITHIN_SCOPE for sources that returned nothing because they broke.
_STATUS_PERMITS_STATES: Mapping[SourceObservationStatus, frozenset[EvidenceState]] = (
    MappingProxyType(
        {
            SourceObservationStatus.OBSERVED: frozenset(
                {
                    EvidenceState.PRESENT,
                    EvidenceState.ABSENT_WITHIN_SCOPE,
                    EvidenceState.PARTIAL,
                }
            ),
            SourceObservationStatus.NOT_OBSERVED: frozenset({EvidenceState.NOT_OBSERVED}),
            SourceObservationStatus.INACCESSIBLE: frozenset({EvidenceState.INACCESSIBLE}),
            SourceObservationStatus.PENDING: frozenset({EvidenceState.PENDING_WINDOW}),
            SourceObservationStatus.STALE: frozenset({EvidenceState.STALE}),
            SourceObservationStatus.FAILED: frozenset({EvidenceState.FAILED}),
            SourceObservationStatus.CONTRADICTORY: frozenset({EvidenceState.CONTRADICTORY}),
            SourceObservationStatus.UNKNOWN: frozenset({EvidenceState.NOT_OBSERVED}),
        }
    )
)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelValidationError(f"{path} must be a JSON object")
    if any(type(key) is not str for key in value):
        raise ModelValidationError(f"{path} object keys must be plain strings")
    return value


def _optional_evidence_state(value: Any, path: str) -> "EvidenceState | None":
    if value is None:
        return None
    try:
        return EvidenceState(value)
    except (TypeError, ValueError) as exc:
        raise ModelValidationError(
            f"{path} must be one of " + ", ".join(f"'{state.value}'" for state in EvidenceState)
        ) from exc


def _optional_composition_mode(value: Any) -> "CompositionMode | None":
    if value is None:
        return None
    try:
        return CompositionMode(value)
    except (TypeError, ValueError) as exc:
        raise ModelValidationError("query.composition must be CORROBORATION or absent") from exc


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

    # The typed Python boundary rejects ``str`` subclasses.  Their comparison,
    # trimming, encoding, or hashing methods are caller-controlled and can turn
    # an apparently validated value into a different trust decision later.
    if type(value) is not str or not value.strip():
        raise ModelValidationError(f"{path} must be a non-empty string")
    result = value.strip()
    if len(result) > max_length:
        raise ModelValidationError(f"{path} exceeds the {max_length}-character limit")
    if len(result.splitlines()) != 1 or any(
        unicodedata.category(character).startswith("C") for character in result
    ):
        raise ModelValidationError(f"{path} must be a single line without control characters")
    return result


def bounded_ascii_identifier(
    value: Any,
    path: str,
    *,
    max_length: int = MAX_SOURCE_ID_LENGTH,
) -> str:
    """Return one canonical, bounded identifier suitable for set matching.

    Source identifiers are intentionally narrower than descriptive strings.
    Lowercase ASCII prevents case folding, Unicode normalization, and visually
    confusable spellings from creating two wire identities for one source.
    """

    result = bounded_single_line(value, path, max_length=max_length)
    if not result.isascii() or not _SOURCE_ID_PATTERN.fullmatch(result):
        raise ModelValidationError(
            f"{path} must be a lowercase ASCII identifier using letters, digits, '.', '_', ':', or '-'"
        )
    if result.casefold() in (_DECLARATION_PLACEHOLDERS | _UNBOUNDED_DECLARATION_PLACEHOLDERS):
        raise ModelValidationError(f"{path} must not use a placeholder identifier")
    return result


def authorization_context_identifier(
    value: Any,
    path: str,
    *,
    identifier_profile: str = AUTHORIZATION_CONTEXT_IDENTIFIER_PROFILE,
) -> str:
    """Validate a stable non-secret authorization-context identifier.

    Candidate.1 rejects only narrowly defined credential representations:
    explicit credential schemes, known provider token prefixes, JWT-like
    compact values, and long unnamespaced opaque alphanumeric values.  The
    check is intentionally applied only to ``authorization_context_id``
    fields; descriptive scope, assumptions, errors, and operator text are not
    scanned or rewritten.

    This is an input invariant, not a general secret scanner or proof that an
    accepted identifier contains no secret.
    """

    if (
        type(identifier_profile) is not str
        or identifier_profile != AUTHORIZATION_CONTEXT_IDENTIFIER_PROFILE
    ):
        raise ModelValidationError(
            "identifier_profile must identify the exact supported "
            f"{AUTHORIZATION_CONTEXT_IDENTIFIER_PROFILE} contract",
            code=ValidationErrorCode.UNSUPPORTED_CONTRACT,
        )
    result = bounded_ascii_identifier(value, path)
    if (
        _EXPLICIT_CREDENTIAL_PATTERN.fullmatch(result)
        or _KNOWN_TOKEN_PATTERN.fullmatch(result)
        or _JWT_LIKE_PATTERN.fullmatch(result)
        or _OPAQUE_TOKEN_PATTERN.fullmatch(result)
    ):
        raise ModelValidationError(
            f"{path} must be a stable non-secret identifier, not a credential "
            "or raw-token-like value",
            code=ValidationErrorCode.CREDENTIAL_LIKE_IDENTIFIER,
        )
    return result


def _sha256_digest(value: Any, path: str) -> str:
    if type(value) is not str or not _SHA256_DIGEST_PATTERN.fullmatch(value):
        raise ModelValidationError(f"{path} must be a lowercase sha256 digest")
    return value


def _concrete_declaration(
    value: Any,
    path: str,
    *,
    reject_unbounded: bool = False,
) -> str:
    result = bounded_single_line(value, path)
    disallowed = _DECLARATION_PLACEHOLDERS
    if reject_unbounded:
        disallowed = disallowed | _UNBOUNDED_DECLARATION_PLACEHOLDERS
    if result.casefold() in disallowed:
        raise ModelValidationError(f"{path} must be a concrete declaration, not a placeholder")
    return result


def _immutable_version(value: Any, path: str) -> str:
    """Reject aliases and range expressions where exact version identity is required."""

    result = _concrete_declaration(value, path, reject_unbounded=True)
    if not result.isascii() or not _SOURCE_ID_PATTERN.fullmatch(result):
        raise ModelValidationError(
            f"{path} must identify one immutable version token using lowercase ASCII letters, digits, '.', '_', ':', or '-'"
        )
    folded = result.casefold()
    floating_labels = {
        "current",
        "default",
        "dev",
        "development",
        "head",
        "latest",
        "lts",
        "main",
        "master",
        "nightly",
        "prod",
        "release",
        "rolling",
        "stable",
        "tip",
        "trunk",
    }
    floating_component = any(
        component in floating_labels | {"x", "snapshot"}
        for component in re.split(r"[._:-]", folded)
    )
    if (
        folded in floating_labels
        or floating_component
        or not _IMMUTABLE_VERSION_PATTERN.fullmatch(result)
        or any(marker in result for marker in ("*", "<", ">", "^", "~", ","))
    ):
        raise ModelValidationError(
            f"{path} must identify one immutable version, not an alias or range"
        )
    return result


def _declared_population(value: Any, path: str) -> str:
    return _concrete_declaration(value, path, reject_unbounded=True)


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
        if not isinstance(decimal_tuple.exponent, int):
            raise ModelValidationError(f"{path} must be a finite number")
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


def _required_string_tuple(data: Mapping[str, Any], key: str, path: str) -> tuple[str, ...]:
    if key not in data:
        raise ModelValidationError(f"{path}.{key} is required")
    if data[key] is None:
        raise ModelValidationError(f"{path}.{key} must be an array, not null")
    return _string_tuple(data[key], f"{path}.{key}")


def parse_datetime(value: Any, path: str) -> datetime:
    if type(value) is not str or not value.strip():
        raise ModelValidationError(f"{path} must be an ISO-8601 timestamp")
    candidate = value.strip()
    if candidate != value:
        raise ModelValidationError(f"{path} must use ISO-8601 without surrounding whitespace")
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
class CoverageProfileReference:
    """Exact immutable profile identity pinned into one source requirement."""

    registry_id: str
    profile_id: str
    profile_version: str
    profile_digest: str

    def __post_init__(self) -> None:
        for name in ("registry_id", "profile_id"):
            object.__setattr__(
                self,
                name,
                bounded_ascii_identifier(getattr(self, name), f"profile_ref.{name}"),
            )
        object.__setattr__(
            self,
            "profile_version",
            _immutable_version(self.profile_version, "profile_ref.profile_version"),
        )
        object.__setattr__(
            self,
            "profile_digest",
            _sha256_digest(self.profile_digest, "profile_ref.profile_digest"),
        )

    @classmethod
    def from_dict(
        cls,
        value: Any,
        path: str = "profile_ref",
    ) -> "CoverageProfileReference":
        data = _mapping(value, path)
        allowed = {
            "registry_id",
            "profile_id",
            "profile_version",
            "profile_digest",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        return cls(
            registry_id=bounded_ascii_identifier(data["registry_id"], f"{path}.registry_id"),
            profile_id=bounded_ascii_identifier(data["profile_id"], f"{path}.profile_id"),
            profile_version=_immutable_version(data["profile_version"], f"{path}.profile_version"),
            profile_digest=_sha256_digest(data["profile_digest"], f"{path}.profile_digest"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "registry_id": self.registry_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "profile_digest": self.profile_digest,
        }


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    """A versioned declaration of one source's role and accessible scope."""

    source_id: str
    role: SourceRole
    system: str
    locator: str
    adapter_id: str
    adapter_version: str
    authorization_context_id: str
    accessible_population: str
    detection_assumptions: tuple[str, ...]
    finality_horizon: datetime | None = None
    profile_ref: CoverageProfileReference | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_id",
            bounded_ascii_identifier(self.source_id, "source_requirement.source_id"),
        )
        if not isinstance(self.role, SourceRole):
            raise ModelValidationError("source_requirement.role must be a SourceRole")
        for name in ("system", "locator"):
            object.__setattr__(
                self,
                name,
                _concrete_declaration(
                    getattr(self, name),
                    f"source_requirement.{name}",
                    reject_unbounded=True,
                ),
            )
        object.__setattr__(
            self,
            "adapter_version",
            _immutable_version(self.adapter_version, "source_requirement.adapter_version"),
        )
        object.__setattr__(
            self,
            "adapter_id",
            bounded_ascii_identifier(self.adapter_id, "source_requirement.adapter_id"),
        )
        object.__setattr__(
            self,
            "authorization_context_id",
            authorization_context_identifier(
                self.authorization_context_id,
                "source_requirement.authorization_context_id",
            ),
        )
        object.__setattr__(
            self,
            "accessible_population",
            _declared_population(
                self.accessible_population,
                "source_requirement.accessible_population",
            ),
        )
        if self.detection_assumptions is None:
            raise ModelValidationError(
                "source_requirement.detection_assumptions must be an array, not null"
            )
        object.__setattr__(
            self,
            "detection_assumptions",
            _string_tuple(
                self.detection_assumptions,
                "source_requirement.detection_assumptions",
            ),
        )
        if not self.detection_assumptions:
            raise ModelValidationError(
                "required source_requirement.detection_assumptions must not be empty"
            )
        object.__setattr__(
            self,
            "detection_assumptions",
            tuple(
                _concrete_declaration(
                    item,
                    f"source_requirement.detection_assumptions[{index}]",
                    reject_unbounded=True,
                )
                for index, item in enumerate(self.detection_assumptions)
            ),
        )
        if len(set(self.detection_assumptions)) != len(self.detection_assumptions):
            raise ModelValidationError(
                "source_requirement.detection_assumptions must not contain duplicates"
            )
        object.__setattr__(
            self,
            "detection_assumptions",
            tuple(sorted(self.detection_assumptions)),
        )
        if self.finality_horizon is not None:
            object.__setattr__(
                self,
                "finality_horizon",
                _validate_aware_datetime(
                    self.finality_horizon,
                    "source_requirement.finality_horizon",
                ),
            )
        if self.profile_ref is not None and not isinstance(
            self.profile_ref, CoverageProfileReference
        ):
            raise ModelValidationError(
                "source_requirement.profile_ref must be a CoverageProfileReference"
            )

    @classmethod
    def from_dict(
        cls,
        value: Any,
        path: str = "source_requirement",
    ) -> "SourceRequirement":
        data = _mapping(value, path)
        allowed = {
            "source_id",
            "role",
            "system",
            "locator",
            "adapter_id",
            "adapter_version",
            "authorization_context_id",
            "accessible_population",
            "detection_assumptions",
            "finality_horizon",
            "profile_ref",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed - {"finality_horizon", "profile_ref"}, path)
        try:
            role = SourceRole(data["role"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(f"{path}.role must be REQUIRED") from exc
        assumptions = data["detection_assumptions"]
        if assumptions is None:
            raise ModelValidationError(f"{path}.detection_assumptions must be an array, not null")
        return cls(
            source_id=bounded_ascii_identifier(data["source_id"], f"{path}.source_id"),
            role=role,
            system=_required_string(data, "system", path),
            locator=_required_string(data, "locator", path),
            adapter_id=bounded_ascii_identifier(data["adapter_id"], f"{path}.adapter_id"),
            adapter_version=_immutable_version(
                data.get("adapter_version"), f"{path}.adapter_version"
            ),
            authorization_context_id=authorization_context_identifier(
                data["authorization_context_id"],
                f"{path}.authorization_context_id",
            ),
            accessible_population=_declared_population(
                data["accessible_population"],
                f"{path}.accessible_population",
            ),
            detection_assumptions=_string_tuple(
                assumptions,
                f"{path}.detection_assumptions",
            ),
            finality_horizon=optional_datetime(
                data.get("finality_horizon"),
                f"{path}.finality_horizon",
            ),
            profile_ref=(
                None
                if data.get("profile_ref") is None
                else CoverageProfileReference.from_dict(data["profile_ref"], f"{path}.profile_ref")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_id": self.source_id,
            "role": self.role.value,
            "system": self.system,
            "locator": self.locator,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "authorization_context_id": self.authorization_context_id,
            "accessible_population": self.accessible_population,
            "detection_assumptions": sorted(self.detection_assumptions),
        }
        if self.finality_horizon is not None:
            payload["finality_horizon"] = datetime_to_json(self.finality_horizon)
        if self.profile_ref is not None:
            payload["profile_ref"] = self.profile_ref.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class QueryScope:
    """The exact population and predicate a query attempted to inspect."""

    target: str
    predicate: str
    authorization_boundary: str
    authorization_context_id: str
    time_start: datetime
    time_end: datetime
    exclusions: tuple[str, ...]
    source_requirements: tuple[SourceRequirement, ...]
    composition: CompositionMode | None = None

    def __post_init__(self) -> None:
        if self.composition is not None and not isinstance(self.composition, CompositionMode):
            raise ModelValidationError("query.composition must be a CompositionMode or null")
        for name in ("target", "predicate"):
            object.__setattr__(
                self,
                name,
                _concrete_declaration(getattr(self, name), f"query.{name}"),
            )
        object.__setattr__(
            self,
            "authorization_boundary",
            _declared_population(
                self.authorization_boundary,
                "query.authorization_boundary",
            ),
        )
        object.__setattr__(
            self,
            "authorization_context_id",
            authorization_context_identifier(
                self.authorization_context_id, "query.authorization_context_id"
            ),
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
        object.__setattr__(self, "exclusions", _string_tuple(self.exclusions, "query.exclusions"))
        object.__setattr__(
            self,
            "exclusions",
            tuple(
                _concrete_declaration(
                    item,
                    f"query.exclusions[{index}]",
                    reject_unbounded=True,
                )
                for index, item in enumerate(self.exclusions)
            ),
        )
        if self.source_requirements is None:
            raise ModelValidationError("query.source_requirements must be an array, not null")
        if isinstance(self.source_requirements, (str, bytes)) or not isinstance(
            self.source_requirements, Sequence
        ):
            raise ModelValidationError("query.source_requirements must be an array")
        requirements = tuple(self.source_requirements)
        if not requirements:
            raise ModelValidationError("query.source_requirements must contain at least one source")
        if len(requirements) > MAX_SOURCE_ACCOUNTING_ENTRIES:
            raise ModelValidationError(
                f"query.source_requirements exceeds the {MAX_SOURCE_ACCOUNTING_ENTRIES}-entry limit"
            )
        if any(not isinstance(item, SourceRequirement) for item in requirements):
            raise ModelValidationError(
                "query.source_requirements must contain only SourceRequirement values"
            )
        source_ids = [item.source_id for item in requirements]
        duplicate_ids = sorted(
            source_id for source_id in set(source_ids) if source_ids.count(source_id) > 1
        )
        if duplicate_ids:
            raise ModelValidationError(
                "query.source_requirements contains duplicate source_id values: "
                + ", ".join(duplicate_ids)
            )
        if any(item.role is not SourceRole.REQUIRED for item in requirements):
            raise ModelValidationError(
                "query.source_requirements must declare every source as REQUIRED; "
                "OPTIONAL sources are not defined in this candidate"
            )
        if self.composition is None:
            if len(requirements) != 1:
                raise ModelValidationError(
                    "query.source_requirements must contain exactly one REQUIRED source "
                    "unless query.composition declares a multi-source mode"
                )
        elif not 1 <= len(requirements) <= MAX_REQUIRED_SOURCES:
            raise ModelValidationError(
                "a composed query must declare between one and "
                f"{MAX_REQUIRED_SOURCES} REQUIRED sources"
            )
        invalid_finality_horizons = sorted(
            item.source_id
            for item in requirements
            if item.finality_horizon is not None and item.finality_horizon < self.time_end
        )
        if invalid_finality_horizons:
            raise ModelValidationError(
                "query.source_requirements finality_horizon must not precede "
                "query.time_end for: " + ", ".join(invalid_finality_horizons)
            )
        context_mismatches = sorted(
            item.source_id
            for item in requirements
            if item.authorization_context_id != self.authorization_context_id
        )
        if context_mismatches:
            raise ModelValidationError(
                "query.source_requirements authorization_context_id must match "
                "query.authorization_context_id for: " + ", ".join(context_mismatches)
            )
        object.__setattr__(
            self,
            "source_requirements",
            tuple(sorted(requirements, key=lambda item: item.source_id)),
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
                "authorization_context_id",
                "time_start",
                "time_end",
                "exclusions",
                "source_requirements",
                "composition",
            },
            "query",
        )
        _require_fields(
            data,
            {
                "target",
                "predicate",
                "authorization_boundary",
                "authorization_context_id",
                "time_start",
                "time_end",
                "exclusions",
                "source_requirements",
            },
            "query",
        )
        raw_requirements = data["source_requirements"]
        if isinstance(raw_requirements, (str, bytes)) or not isinstance(raw_requirements, Sequence):
            raise ModelValidationError("query.source_requirements must be an array")
        return cls(
            target=_required_string(data, "target", "query"),
            predicate=_required_string(data, "predicate", "query"),
            authorization_boundary=_required_string(data, "authorization_boundary", "query"),
            authorization_context_id=authorization_context_identifier(
                data["authorization_context_id"],
                "query.authorization_context_id",
            ),
            time_start=parse_datetime(data["time_start"], "query.time_start"),
            time_end=parse_datetime(data["time_end"], "query.time_end"),
            exclusions=_required_string_tuple(data, "exclusions", "query"),
            source_requirements=tuple(
                SourceRequirement.from_dict(
                    item,
                    f"query.source_requirements[{index}]",
                )
                for index, item in enumerate(raw_requirements)
            ),
            composition=_optional_composition_mode(data.get("composition")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "target": self.target,
            "predicate": self.predicate,
            "authorization_boundary": self.authorization_boundary,
            "authorization_context_id": self.authorization_context_id,
            "time_start": datetime_to_json(self.time_start),
            "time_end": datetime_to_json(self.time_end),
            "exclusions": sorted(self.exclusions),
            "source_requirements": [
                requirement.to_dict() for requirement in self.source_requirements
            ],
        }
        # Omitted rather than emitted as null when absent: a single-source query
        # must canonicalize exactly as it did before this field existed, so
        # every schema 1.0 fingerprint, digest, and certificate is unchanged.
        if self.composition is not None:
            payload["composition"] = self.composition.value
        return payload

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return f"sha256:{sha256(payload).hexdigest()}"

    def qualification(self) -> str:
        parts = [
            f"target={json.dumps(self.target, ensure_ascii=False)}",
            f"predicate={json.dumps(self.predicate, ensure_ascii=False)}",
            f"authorization={json.dumps(self.authorization_boundary, ensure_ascii=False)}",
            f"authorization_context={json.dumps(self.authorization_context_id)}",
            f"from={datetime_to_json(self.time_start)}",
            f"through={datetime_to_json(self.time_end)}",
        ]
        if self.exclusions:
            parts.append(
                "excluding="
                + json.dumps(sorted(self.exclusions), ensure_ascii=False, separators=(",", ":"))
            )
        parts.append(
            "sources="
            + json.dumps(
                [requirement.to_dict() for requirement in self.source_requirements],
                ensure_ascii=False,
                separators=(",", ":"),
            )
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
        object.__setattr__(self, "declared_lower_bound", normalized_declared_lower_bound)
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
            deterministic_bounds.append(_exact_ratio(self.examined_units, self.population_units))
        if self.pages_examined is not None and self.pages_expected is not None:
            deterministic_bounds.append(_exact_ratio(self.pages_examined, self.pages_expected))
        if self.partitions_examined is not None and self.partitions_expected is not None:
            deterministic_bounds.append(
                _exact_ratio(self.partitions_examined, self.partitions_expected)
            )
        if (
            self.declared_lower_bound is not None
            and deterministic_bounds
            and _normalized_float_fraction(self.declared_lower_bound) > min(deterministic_bounds)
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
            examined_units=_nonnegative_int(data.get("examined_units"), "coverage.examined_units"),
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
    adapter_id: str
    adapter_version: str
    index_as_of: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("system", "locator"):
            object.__setattr__(
                self,
                name,
                _concrete_declaration(
                    getattr(self, name),
                    f"source.{name}",
                    reject_unbounded=True,
                ),
            )
        object.__setattr__(
            self,
            "adapter_id",
            bounded_ascii_identifier(self.adapter_id, "source.adapter_id"),
        )
        object.__setattr__(
            self,
            "adapter_version",
            _immutable_version(self.adapter_version, "source.adapter_version"),
        )
        if self.index_as_of is not None:
            object.__setattr__(
                self,
                "index_as_of",
                _validate_aware_datetime(self.index_as_of, "source.index_as_of"),
            )

    @classmethod
    def from_dict(
        cls,
        value: Any,
        path: str = "source",
    ) -> "SourceDescriptor":
        data = _mapping(value, path)
        _reject_unknown(
            data,
            {"system", "locator", "adapter_id", "adapter_version", "index_as_of"},
            path,
        )
        return cls(
            system=_required_string(data, "system", path),
            locator=_required_string(data, "locator", path),
            adapter_id=bounded_ascii_identifier(data.get("adapter_id"), f"{path}.adapter_id"),
            adapter_version=_immutable_version(
                data.get("adapter_version"), f"{path}.adapter_version"
            ),
            index_as_of=optional_datetime(data.get("index_as_of"), f"{path}.index_as_of"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "locator": self.locator,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "index_as_of": datetime_to_json(self.index_as_of) if self.index_as_of else None,
        }


@dataclass(frozen=True, slots=True)
class SourceObservation:
    """Runtime accounting record for one source declared by the query."""

    source_id: str
    status: SourceObservationStatus
    descriptor: SourceDescriptor
    authorization_context_id: str
    query_fingerprint: str
    accessible_population: str | None
    errors: tuple[str, ...]
    coverage: "CoverageEvidence | None" = None
    state: EvidenceState | None = None
    matched_count: int | None = None
    observed_at: datetime | None = None
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        if self.coverage is not None and not isinstance(self.coverage, CoverageEvidence):
            raise ModelValidationError(
                "source_observation.coverage must be CoverageEvidence or null"
            )
        object.__setattr__(
            self,
            "source_id",
            bounded_ascii_identifier(self.source_id, "source_observation.source_id"),
        )
        if not isinstance(self.status, SourceObservationStatus):
            raise ModelValidationError(
                "source_observation.status must be a SourceObservationStatus"
            )
        if not isinstance(self.descriptor, SourceDescriptor):
            raise ModelValidationError("source_observation.descriptor must be a SourceDescriptor")
        object.__setattr__(
            self,
            "authorization_context_id",
            authorization_context_identifier(
                self.authorization_context_id,
                "source_observation.authorization_context_id",
            ),
        )
        object.__setattr__(
            self,
            "query_fingerprint",
            _sha256_digest(
                self.query_fingerprint,
                "source_observation.query_fingerprint",
            ),
        )
        if self.accessible_population is not None:
            object.__setattr__(
                self,
                "accessible_population",
                _declared_population(
                    self.accessible_population,
                    "source_observation.accessible_population",
                ),
            )
        if self.status is SourceObservationStatus.OBSERVED and (self.accessible_population is None):
            raise ModelValidationError(
                "source_observation.accessible_population is required when status is OBSERVED"
            )
        if self.errors is None:
            raise ModelValidationError("source_observation.errors must be an array, not null")
        object.__setattr__(
            self,
            "errors",
            _string_tuple(self.errors, "source_observation.errors"),
        )
        if self.status is SourceObservationStatus.FAILED and not self.errors:
            raise ModelValidationError(
                "source_observation.errors must contain at least one error when status is FAILED"
            )
        self._validate_assessment()

    @property
    def declared_assessment_fields(self) -> tuple[str, ...]:
        """Return which per-source assessment fields this observation carries."""

        return tuple(name for name in SOURCE_ASSESSMENT_FIELDS if getattr(self, name) is not None)

    def _validate_assessment(self) -> None:
        """Validate one source's own assessment, or its complete absence.

        These fields are what makes a source's contribution checkable: without
        a state and a match count, two sources cannot be seen to disagree, and
        without an observation time the composition cannot report its stalest
        source. They are validated here rather than in the composer so that an
        incoherent observation cannot be constructed at all.
        """

        if self.state is not None and not isinstance(self.state, EvidenceState):
            raise ModelValidationError("source_observation.state must be an EvidenceState or null")
        if self.matched_count is not None:
            _nonnegative_int(self.matched_count, "source_observation.matched_count")
        for name in ("observed_at", "valid_until"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _validate_aware_datetime(value, f"source_observation.{name}"),
                )

        declared = set(self.declared_assessment_fields)
        if not declared:
            return

        # A state without a count, or a count without a state, cannot be
        # checked against anything, so neither is accepted alone.
        missing = [name for name in REQUIRED_SOURCE_ASSESSMENT_FIELDS if name not in declared]
        if missing:
            raise ModelValidationError(
                "source_observation assessment requires "
                + ", ".join(REQUIRED_SOURCE_ASSESSMENT_FIELDS)
                + " together; missing: "
                + ", ".join(missing)
            )

        assert self.state is not None  # narrowed by the completeness check above
        permitted = _STATUS_PERMITS_STATES[self.status]
        if self.state not in permitted:
            raise ModelValidationError(
                f"source_observation.state '{self.state.value}' is not compatible with "
                f"status '{self.status.value}'; permitted: "
                + ", ".join(sorted(item.value for item in permitted))
            )
        if self.state is EvidenceState.PRESENT and self.matched_count == 0:
            raise ModelValidationError(
                "source_observation PRESENT requires matched_count greater than zero"
            )
        if self.state is EvidenceState.ABSENT_WITHIN_SCOPE and self.matched_count != 0:
            raise ModelValidationError(
                "source_observation ABSENT_WITHIN_SCOPE requires matched_count equal to zero"
            )
        if self.valid_until is not None and self.observed_at is not None:
            if self.valid_until < self.observed_at:
                raise ModelValidationError(
                    "source_observation.valid_until must not precede source_observation.observed_at"
                )
        index_as_of = self.descriptor.index_as_of
        if index_as_of is not None and self.observed_at is not None:
            if index_as_of > self.observed_at:
                raise ModelValidationError(
                    "source_observation.descriptor.index_as_of must not be after "
                    "source_observation.observed_at"
                )

    @classmethod
    def from_dict(
        cls,
        value: Any,
        path: str = "source_observation",
    ) -> "SourceObservation":
        data = _mapping(value, path)
        allowed = {
            "source_id",
            "status",
            "descriptor",
            "authorization_context_id",
            "query_fingerprint",
            "accessible_population",
            "errors",
        }
        # The assessment fields are accepted but not required: a schema 1.0
        # observation carries none of them, and its canonical form must not
        # change.  The envelope decides which schema version may declare them.
        _reject_unknown(data, allowed | set(SOURCE_ASSESSMENT_FIELDS), path)
        _require_fields(data, allowed, path)
        try:
            status = SourceObservationStatus(data["status"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                f"{path}.status must be OBSERVED, NOT_OBSERVED, INACCESSIBLE, "
                "PENDING, STALE, FAILED, CONTRADICTORY, or UNKNOWN"
            ) from exc
        accessible_population = data["accessible_population"]
        if accessible_population is not None:
            accessible_population = _declared_population(
                accessible_population,
                f"{path}.accessible_population",
            )
        raw_errors = data["errors"]
        if raw_errors is None:
            raise ModelValidationError(f"{path}.errors must be an array, not null")
        return cls(
            source_id=bounded_ascii_identifier(data["source_id"], f"{path}.source_id"),
            status=status,
            descriptor=SourceDescriptor.from_dict(data["descriptor"], f"{path}.descriptor"),
            authorization_context_id=authorization_context_identifier(
                data["authorization_context_id"],
                f"{path}.authorization_context_id",
            ),
            query_fingerprint=_sha256_digest(
                data["query_fingerprint"], f"{path}.query_fingerprint"
            ),
            accessible_population=accessible_population,
            errors=_string_tuple(raw_errors, f"{path}.errors"),
            coverage=(
                None
                if data.get("coverage") is None
                else CoverageEvidence.from_dict(data["coverage"])
            ),
            state=_optional_evidence_state(data.get("state"), f"{path}.state"),
            matched_count=(
                None
                if data.get("matched_count") is None
                else _nonnegative_int(data["matched_count"], f"{path}.matched_count")
            ),
            observed_at=optional_datetime(data.get("observed_at"), f"{path}.observed_at"),
            valid_until=optional_datetime(data.get("valid_until"), f"{path}.valid_until"),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_id": self.source_id,
            "status": self.status.value,
            "descriptor": self.descriptor.to_dict(),
            "authorization_context_id": self.authorization_context_id,
            "query_fingerprint": self.query_fingerprint,
            "accessible_population": self.accessible_population,
            "errors": sorted(self.errors),
        }
        # Omitted when absent for the same reason as query.composition: a
        # schema 1.0 observation must serialise to exactly the bytes it did
        # before these fields existed, so every recorded digest still verifies.
        if self.coverage is not None:
            payload["coverage"] = self.coverage.to_dict()
        if self.state is not None:
            payload["state"] = self.state.value
        if self.matched_count is not None:
            payload["matched_count"] = self.matched_count
        if self.observed_at is not None:
            payload["observed_at"] = datetime_to_json(self.observed_at)
        if self.valid_until is not None:
            payload["valid_until"] = datetime_to_json(self.valid_until)
        return payload


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceEnvelope:
    """A tool result plus the evidence needed to interpret its epistemic state."""

    schema_version: str
    state: EvidenceState
    query: QueryScope
    coverage: CoverageEvidence
    coverage_query_fingerprint: str
    matched_count: int
    observed_at: datetime
    source_observations: tuple[SourceObservation, ...]
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
        object.__setattr__(
            self,
            "observed_at",
            _validate_aware_datetime(self.observed_at, "observed_at"),
        )
        if self.query.time_end > self.observed_at:
            raise ModelValidationError("query.time_end must not be after observed_at")
        object.__setattr__(
            self,
            "coverage_query_fingerprint",
            _sha256_digest(
                self.coverage_query_fingerprint,
                "coverage_query_fingerprint",
            ),
        )
        expected_query_fingerprint = self.query.fingerprint()
        if self.coverage_query_fingerprint != expected_query_fingerprint:
            raise ModelValidationError(
                "coverage_query_fingerprint must match the canonical query fingerprint"
            )
        _nonnegative_int(self.matched_count, "matched_count")
        if self.state is EvidenceState.PRESENT and self.matched_count == 0:
            raise ModelValidationError("PRESENT requires matched_count greater than zero")
        if self.state is EvidenceState.ABSENT_WITHIN_SCOPE and self.matched_count != 0:
            raise ModelValidationError("ABSENT_WITHIN_SCOPE requires matched_count equal to zero")
        if self.source_observations is None:
            raise ModelValidationError("source_observations must be an array, not null")
        if isinstance(self.source_observations, (str, bytes)) or not isinstance(
            self.source_observations, Sequence
        ):
            raise ModelValidationError("source_observations must be an array")
        observations = tuple(self.source_observations)
        if len(observations) > MAX_SOURCE_ACCOUNTING_ENTRIES:
            raise ModelValidationError(
                f"source_observations exceeds the {MAX_SOURCE_ACCOUNTING_ENTRIES}-entry limit"
            )
        if any(not isinstance(item, SourceObservation) for item in observations):
            raise ModelValidationError(
                "source_observations must contain only SourceObservation values"
            )
        observation_ids = [item.source_id for item in observations]
        duplicate_observation_ids = sorted(
            source_id for source_id in set(observation_ids) if observation_ids.count(source_id) > 1
        )
        if duplicate_observation_ids:
            raise ModelValidationError(
                "source_observations contains duplicate source_id values: "
                + ", ".join(duplicate_observation_ids)
            )
        declared_source_ids = {
            requirement.source_id for requirement in self.query.source_requirements
        }
        undeclared_source_ids = sorted(set(observation_ids) - declared_source_ids)
        if undeclared_source_ids:
            raise ModelValidationError(
                "source_observations contains undeclared source_id values: "
                + ", ".join(undeclared_source_ids)
            )
        for observation in observations:
            if observation.query_fingerprint != expected_query_fingerprint:
                raise ModelValidationError(
                    "source_observation.query_fingerprint must match the canonical query fingerprint"
                )
            index_as_of = observation.descriptor.index_as_of
            if index_as_of is not None and index_as_of > self.observed_at:
                raise ModelValidationError(
                    "source_observations descriptor index_as_of must not be after observed_at"
                )
        object.__setattr__(
            self,
            "source_observations",
            tuple(sorted(observations, key=lambda item: item.source_id)),
        )
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
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ModelValidationError(
                "schema_version must be one of the supported string values "
                + ", ".join(f"'{version}'" for version in sorted(SUPPORTED_SCHEMA_VERSIONS))
            )
        self._validate_composition_boundary()

    def _validate_composition_boundary(self) -> None:
        """Keep multi-source strictly inside schema 1.1.

        A schema 1.0 record must mean exactly what it meant before composition
        existed, so it may neither declare a composition mode nor carry
        per-source coverage. A composed record must do both, and must supply
        coverage for every required source: composition is the evaluator's
        conclusion from per-source evidence, and it cannot be drawn from
        evidence that was never supplied.
        """

        composed = self.query.composition is not None
        assessed = {
            observation.source_id: set(observation.declared_assessment_fields)
            for observation in self.source_observations
            if observation.declared_assessment_fields
        }
        if self.schema_version == SCHEMA_VERSION_SINGLE_SOURCE:
            if composed:
                raise ModelValidationError(
                    "envelope.query.composition requires schema_version "
                    f"'{SCHEMA_VERSION_COMPOSED}'"
                )
            if assessed:
                raise ModelValidationError(
                    "per-source assessment fields require schema_version "
                    f"'{SCHEMA_VERSION_COMPOSED}'; supplied for: " + ", ".join(sorted(assessed))
                )
            return

        if not composed:
            raise ModelValidationError(
                f"schema_version '{SCHEMA_VERSION_COMPOSED}' requires "
                "envelope.query.composition to declare a composition mode"
            )
        required_ids = {
            requirement.source_id
            for requirement in self.query.source_requirements
            if requirement.role is SourceRole.REQUIRED
        }
        missing = sorted(required_ids - set(assessed))
        if missing:
            raise ModelValidationError(
                "a composed envelope requires a per-source assessment for every required "
                "source; missing for: " + ", ".join(missing)
            )
        # A source that reports its own observation time may not claim to have
        # looked after the envelope was sealed.
        late = sorted(
            observation.source_id
            for observation in self.source_observations
            if observation.observed_at is not None and observation.observed_at > self.observed_at
        )
        if late:
            raise ModelValidationError(
                "source_observation.observed_at must not be after envelope observed_at "
                "for: " + ", ".join(late)
            )

    @classmethod
    def from_dict(cls, value: Any) -> "EvidenceEnvelope":
        data = _mapping(value, "envelope")
        _require_fields(data, {"schema_version"}, "envelope")
        schema_version = data["schema_version"]
        if type(schema_version) is not str:
            raise ModelValidationError("envelope.schema_version must be the string '1.0'")
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ModelValidationError(
                "envelope.schema_version must be one of the supported string values "
                + ", ".join(f"'{version}'" for version in sorted(SUPPORTED_SCHEMA_VERSIONS))
            )
        allowed = {
            "state",
            "query",
            "coverage",
            "coverage_query_fingerprint",
            "matched_count",
            "observed_at",
            "valid_until",
            "source_observations",
            "errors",
            "notes",
            "schema_version",
        }
        _reject_unknown(data, allowed, "envelope")
        _require_fields(
            data,
            {
                "schema_version",
                "coverage_query_fingerprint",
                "source_observations",
                "errors",
            },
            "envelope",
        )
        try:
            state = EvidenceState(data.get("state"))
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                "envelope.state must be a recognized evidence state"
            ) from exc
        if "matched_count" not in data:
            raise ModelValidationError("envelope.matched_count is required")
        raw_observations = data["source_observations"]
        if isinstance(raw_observations, (str, bytes)) or not isinstance(raw_observations, Sequence):
            raise ModelValidationError("envelope.source_observations must be an array")
        return cls(
            state=state,
            query=QueryScope.from_dict(data.get("query")),
            coverage=CoverageEvidence.from_dict(data.get("coverage")),
            coverage_query_fingerprint=_sha256_digest(
                data["coverage_query_fingerprint"],
                "envelope.coverage_query_fingerprint",
            ),
            matched_count=_nonnegative_int(data.get("matched_count"), "envelope.matched_count"),
            observed_at=parse_datetime(data.get("observed_at"), "envelope.observed_at"),
            valid_until=optional_datetime(data.get("valid_until"), "envelope.valid_until"),
            source_observations=tuple(
                SourceObservation.from_dict(
                    item,
                    f"envelope.source_observations[{index}]",
                )
                for index, item in enumerate(raw_observations)
            ),
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
            "coverage_query_fingerprint": self.coverage_query_fingerprint,
            "matched_count": self.matched_count,
            "observed_at": datetime_to_json(self.observed_at),
            "valid_until": datetime_to_json(self.valid_until) if self.valid_until else None,
            "source_observations": [
                observation.to_dict() for observation in self.source_observations
            ],
            "errors": sorted(self.errors),
            "notes": sorted(self.notes),
        }
