"""Deterministic, application-controlled coverage and finality profiles.

The producer request carries only an exact ``CoverageProfileReference``.  The
profile body, registry snapshot, and trust selection enter the evaluator on a
separate boundary controlled by the application.  This module performs no
filesystem, network, clock, or signature operations.  Digests provide
canonical integrity bindings; they do not authenticate the declarative issuer
or approval identities contained in these models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from hmac import compare_digest
from typing import Any, Mapping, Sequence

from .canonical import canonical_digest
from .models import (
    CoverageProfileReference,
    EvidenceEnvelope,
    ModelValidationError,
    PopulationBasis,
    SourceObservationStatus,
    _concrete_declaration,
    _mapping,
    _nonnegative_int,
    _reject_unknown,
    _require_fields,
    _sha256_digest,
    _string_tuple,
    _validate_aware_datetime,
    bounded_ascii_identifier,
    datetime_to_json,
    optional_datetime,
    parse_datetime,
)


COVERAGE_FINALITY_PROFILE_SCHEMA = (
    "esio-coverage-finality-profile/1.0-candidate.1"
)
PROFILE_REGISTRY_SNAPSHOT_SCHEMA = (
    "esio-profile-registry-snapshot/1.0-candidate.1"
)
PROFILE_TRUST_SELECTION_SCHEMA = (
    "esio-profile-trust-selection/1.0-candidate.1"
)
FINALITY_METHOD = "QUERY_END_PLUS_MAX_DELAY"


def _identifier(value: Any, path: str) -> str:
    return bounded_ascii_identifier(value, path)


def _declaration(value: Any, path: str) -> str:
    return _concrete_declaration(value, path, reject_unbounded=True)


def _required_identifier_tuple(value: Any, path: str) -> tuple[str, ...]:
    if value is None:
        raise ModelValidationError(f"{path} must be an array, not null")
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ModelValidationError(f"{path} must be an array of identifiers")
    result = tuple(
        _identifier(item, f"{path}[{index}]") for index, item in enumerate(value)
    )
    if not result:
        raise ModelValidationError(f"{path} must not be empty")
    if len(set(result)) != len(result):
        raise ModelValidationError(f"{path} must not contain duplicates")
    return tuple(sorted(result))


def _declaration_tuple(
    value: Any,
    path: str,
    *,
    require_nonempty: bool,
) -> tuple[str, ...]:
    if value is None:
        raise ModelValidationError(f"{path} must be an array, not null")
    result = tuple(
        _declaration(item, f"{path}[{index}]")
        for index, item in enumerate(_string_tuple(value, path))
    )
    if require_nonempty and not result:
        raise ModelValidationError(f"{path} must not be empty")
    if len(set(result)) != len(result):
        raise ModelValidationError(f"{path} must not contain duplicates")
    return tuple(sorted(result))


def _strict_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ModelValidationError(f"{path} must be a boolean")
    return value


def _optional_nonnegative_int(value: Any, path: str) -> int | None:
    if value is None:
        return None
    return _nonnegative_int(value, path)


def _timedelta_exceeds_seconds(value: timedelta, limit: int) -> bool:
    """Compare a non-negative timedelta to an integer without float coercion."""

    if value.days < 0:
        return False
    whole_seconds = value.days * 86_400 + value.seconds
    return whole_seconds > limit or (
        whole_seconds == limit and value.microseconds > 0
    )


@dataclass(frozen=True, slots=True)
class BlindInterval:
    """One governed closed-open interval ``[start, end)``."""

    start: datetime
    end: datetime
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "start", _validate_aware_datetime(self.start, "blind_interval.start")
        )
        object.__setattr__(
            self, "end", _validate_aware_datetime(self.end, "blind_interval.end")
        )
        if self.end <= self.start:
            raise ModelValidationError(
                "blind_interval.end must be after blind_interval.start"
            )
        object.__setattr__(
            self,
            "reason_code",
            _identifier(self.reason_code, "blind_interval.reason_code"),
        )

    @classmethod
    def from_dict(cls, value: Any, path: str = "blind_interval") -> "BlindInterval":
        data = _mapping(value, path)
        allowed = {"start", "end", "reason_code"}
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        return cls(
            start=parse_datetime(data["start"], f"{path}.start"),
            end=parse_datetime(data["end"], f"{path}.end"),
            reason_code=_identifier(data["reason_code"], f"{path}.reason_code"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "start": datetime_to_json(self.start),
            "end": datetime_to_json(self.end),
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class ProfileSource:
    source_id: str
    system: str
    locator: str
    adapter_id: str
    adapter_version: str
    authorization_context_id: str
    accessible_population: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _identifier(self.source_id, "profile.source.source_id"))
        object.__setattr__(self, "system", _declaration(self.system, "profile.source.system"))
        object.__setattr__(self, "locator", _declaration(self.locator, "profile.source.locator"))
        object.__setattr__(self, "adapter_id", _identifier(self.adapter_id, "profile.source.adapter_id"))
        object.__setattr__(
            self,
            "adapter_version",
            _declaration(self.adapter_version, "profile.source.adapter_version"),
        )
        object.__setattr__(
            self,
            "authorization_context_id",
            _identifier(
                self.authorization_context_id,
                "profile.source.authorization_context_id",
            ),
        )
        object.__setattr__(
            self,
            "accessible_population",
            _declaration(
                self.accessible_population, "profile.source.accessible_population"
            ),
        )

    @classmethod
    def from_dict(cls, value: Any, path: str = "profile.source") -> "ProfileSource":
        data = _mapping(value, path)
        allowed = {
            "source_id",
            "system",
            "locator",
            "adapter_id",
            "adapter_version",
            "authorization_context_id",
            "accessible_population",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        return cls(
            source_id=_identifier(data["source_id"], f"{path}.source_id"),
            system=_declaration(data["system"], f"{path}.system"),
            locator=_declaration(data["locator"], f"{path}.locator"),
            adapter_id=_identifier(data["adapter_id"], f"{path}.adapter_id"),
            adapter_version=_declaration(
                data["adapter_version"], f"{path}.adapter_version"
            ),
            authorization_context_id=_identifier(
                data["authorization_context_id"],
                f"{path}.authorization_context_id",
            ),
            accessible_population=_declaration(
                data["accessible_population"], f"{path}.accessible_population"
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "system": self.system,
            "locator": self.locator,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "authorization_context_id": self.authorization_context_id,
            "accessible_population": self.accessible_population,
        }


@dataclass(frozen=True, slots=True)
class ProfileApplicability:
    target: str
    predicate: str
    authorization_boundary: str
    required_exclusions: tuple[str, ...]
    detection_assumptions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "target", _declaration(self.target, "profile.applicability.target"))
        object.__setattr__(
            self, "predicate", _declaration(self.predicate, "profile.applicability.predicate")
        )
        object.__setattr__(
            self,
            "authorization_boundary",
            _declaration(
                self.authorization_boundary,
                "profile.applicability.authorization_boundary",
            ),
        )
        object.__setattr__(
            self,
            "required_exclusions",
            _declaration_tuple(
                self.required_exclusions,
                "profile.applicability.required_exclusions",
                require_nonempty=False,
            ),
        )
        object.__setattr__(
            self,
            "detection_assumptions",
            _declaration_tuple(
                self.detection_assumptions,
                "profile.applicability.detection_assumptions",
                require_nonempty=True,
            ),
        )

    @classmethod
    def from_dict(
        cls, value: Any, path: str = "profile.applicability"
    ) -> "ProfileApplicability":
        data = _mapping(value, path)
        allowed = {
            "target",
            "predicate",
            "authorization_boundary",
            "required_exclusions",
            "detection_assumptions",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        return cls(
            target=_declaration(data["target"], f"{path}.target"),
            predicate=_declaration(data["predicate"], f"{path}.predicate"),
            authorization_boundary=_declaration(
                data["authorization_boundary"], f"{path}.authorization_boundary"
            ),
            required_exclusions=_declaration_tuple(
                data["required_exclusions"],
                f"{path}.required_exclusions",
                require_nonempty=False,
            ),
            detection_assumptions=_declaration_tuple(
                data["detection_assumptions"],
                f"{path}.detection_assumptions",
                require_nonempty=True,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "predicate": self.predicate,
            "authorization_boundary": self.authorization_boundary,
            "required_exclusions": list(self.required_exclusions),
            "detection_assumptions": list(self.detection_assumptions),
        }


@dataclass(frozen=True, slots=True)
class ProfileCoverage:
    population_basis: PopulationBasis
    population_units: int
    pages_expected: int | None
    partitions_expected: int | None
    permission_limited: bool
    retention_seconds: int
    blind_intervals: tuple[BlindInterval, ...]
    max_observation_age_seconds: int
    max_index_age_seconds: int

    def __post_init__(self) -> None:
        if self.population_basis is not PopulationBasis.EXACT:
            raise ModelValidationError(
                "profile.coverage.population_basis must be EXACT"
            )
        _nonnegative_int(self.population_units, "profile.coverage.population_units")
        _optional_nonnegative_int(
            self.pages_expected, "profile.coverage.pages_expected"
        )
        _optional_nonnegative_int(
            self.partitions_expected, "profile.coverage.partitions_expected"
        )
        _strict_bool(self.permission_limited, "profile.coverage.permission_limited")
        _nonnegative_int(self.retention_seconds, "profile.coverage.retention_seconds")
        _nonnegative_int(
            self.max_observation_age_seconds,
            "profile.coverage.max_observation_age_seconds",
        )
        _nonnegative_int(
            self.max_index_age_seconds,
            "profile.coverage.max_index_age_seconds",
        )
        if self.blind_intervals is None:
            raise ModelValidationError(
                "profile.coverage.blind_intervals must be an array, not null"
            )
        if isinstance(self.blind_intervals, (str, bytes)) or not isinstance(
            self.blind_intervals, Sequence
        ):
            raise ModelValidationError(
                "profile.coverage.blind_intervals must be an array"
            )
        intervals = tuple(self.blind_intervals)
        if any(not isinstance(item, BlindInterval) for item in intervals):
            raise ModelValidationError(
                "profile.coverage.blind_intervals must contain BlindInterval values"
            )
        keys = [(item.start, item.end, item.reason_code) for item in intervals]
        if len(set(keys)) != len(keys):
            raise ModelValidationError(
                "profile.coverage.blind_intervals must not contain duplicates"
            )
        object.__setattr__(
            self,
            "blind_intervals",
            tuple(sorted(intervals, key=lambda item: (item.start, item.end, item.reason_code))),
        )

    @classmethod
    def from_dict(
        cls, value: Any, path: str = "profile.coverage"
    ) -> "ProfileCoverage":
        data = _mapping(value, path)
        allowed = {
            "population_basis",
            "population_units",
            "pages_expected",
            "partitions_expected",
            "permission_limited",
            "retention_seconds",
            "blind_intervals",
            "max_observation_age_seconds",
            "max_index_age_seconds",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        try:
            basis = PopulationBasis(data["population_basis"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(
                f"{path}.population_basis must be EXACT"
            ) from exc
        raw_intervals = data["blind_intervals"]
        if isinstance(raw_intervals, (str, bytes)) or not isinstance(
            raw_intervals, Sequence
        ):
            raise ModelValidationError(f"{path}.blind_intervals must be an array")
        return cls(
            population_basis=basis,
            population_units=_nonnegative_int(
                data["population_units"], f"{path}.population_units"
            ),
            pages_expected=_optional_nonnegative_int(
                data["pages_expected"], f"{path}.pages_expected"
            ),
            partitions_expected=_optional_nonnegative_int(
                data["partitions_expected"], f"{path}.partitions_expected"
            ),
            permission_limited=_strict_bool(
                data["permission_limited"], f"{path}.permission_limited"
            ),
            retention_seconds=_nonnegative_int(
                data["retention_seconds"], f"{path}.retention_seconds"
            ),
            blind_intervals=tuple(
                BlindInterval.from_dict(item, f"{path}.blind_intervals[{index}]")
                for index, item in enumerate(raw_intervals)
            ),
            max_observation_age_seconds=_nonnegative_int(
                data["max_observation_age_seconds"],
                f"{path}.max_observation_age_seconds",
            ),
            max_index_age_seconds=_nonnegative_int(
                data["max_index_age_seconds"],
                f"{path}.max_index_age_seconds",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "population_basis": self.population_basis.value,
            "population_units": self.population_units,
            "pages_expected": self.pages_expected,
            "partitions_expected": self.partitions_expected,
            "permission_limited": self.permission_limited,
            "retention_seconds": self.retention_seconds,
            "blind_intervals": [item.to_dict() for item in self.blind_intervals],
            "max_observation_age_seconds": self.max_observation_age_seconds,
            "max_index_age_seconds": self.max_index_age_seconds,
        }


@dataclass(frozen=True, slots=True)
class ProfileFinality:
    method: str
    late_arrival_bound_seconds: int
    reopen_bound_seconds: int

    def __post_init__(self) -> None:
        if self.method != FINALITY_METHOD:
            raise ModelValidationError(
                f"profile.finality.method must be {FINALITY_METHOD}"
            )
        _nonnegative_int(
            self.late_arrival_bound_seconds,
            "profile.finality.late_arrival_bound_seconds",
        )
        _nonnegative_int(
            self.reopen_bound_seconds,
            "profile.finality.reopen_bound_seconds",
        )

    @classmethod
    def from_dict(
        cls, value: Any, path: str = "profile.finality"
    ) -> "ProfileFinality":
        data = _mapping(value, path)
        allowed = {
            "method",
            "late_arrival_bound_seconds",
            "reopen_bound_seconds",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        method = data["method"]
        if not isinstance(method, str) or method != FINALITY_METHOD:
            raise ModelValidationError(f"{path}.method must be {FINALITY_METHOD}")
        return cls(
            method=method,
            late_arrival_bound_seconds=_nonnegative_int(
                data["late_arrival_bound_seconds"],
                f"{path}.late_arrival_bound_seconds",
            ),
            reopen_bound_seconds=_nonnegative_int(
                data["reopen_bound_seconds"], f"{path}.reopen_bound_seconds"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "late_arrival_bound_seconds": self.late_arrival_bound_seconds,
            "reopen_bound_seconds": self.reopen_bound_seconds,
        }


@dataclass(frozen=True, slots=True)
class CoverageFinalityProfile:
    profile_schema: str
    profile_id: str
    profile_version: str
    source_owner_id: str
    approval_authority_id: str
    issuer_id: str
    issued_at: datetime
    effective_at: datetime
    expires_at: datetime
    source: ProfileSource
    applicability: ProfileApplicability
    coverage: ProfileCoverage
    finality: ProfileFinality

    def __post_init__(self) -> None:
        if self.profile_schema != COVERAGE_FINALITY_PROFILE_SCHEMA:
            raise ModelValidationError(
                "profile.profile_schema must identify the supported profile contract"
            )
        for name in (
            "profile_id",
            "profile_version",
            "source_owner_id",
            "approval_authority_id",
            "issuer_id",
        ):
            object.__setattr__(
                self, name, _identifier(getattr(self, name), f"profile.{name}")
            )
        object.__setattr__(
            self, "issued_at", _validate_aware_datetime(self.issued_at, "profile.issued_at")
        )
        object.__setattr__(
            self,
            "effective_at",
            _validate_aware_datetime(self.effective_at, "profile.effective_at"),
        )
        object.__setattr__(
            self,
            "expires_at",
            _validate_aware_datetime(self.expires_at, "profile.expires_at"),
        )
        if not self.issued_at <= self.effective_at < self.expires_at:
            raise ModelValidationError(
                "profile timestamps must satisfy issued_at <= effective_at < expires_at"
            )
        if not isinstance(self.source, ProfileSource):
            raise ModelValidationError("profile.source must be ProfileSource")
        if not isinstance(self.applicability, ProfileApplicability):
            raise ModelValidationError(
                "profile.applicability must be ProfileApplicability"
            )
        if not isinstance(self.coverage, ProfileCoverage):
            raise ModelValidationError("profile.coverage must be ProfileCoverage")
        if not isinstance(self.finality, ProfileFinality):
            raise ModelValidationError("profile.finality must be ProfileFinality")

    @classmethod
    def from_dict(cls, value: Any, path: str = "profile") -> "CoverageFinalityProfile":
        data = _mapping(value, path)
        allowed = {
            "profile_schema",
            "profile_id",
            "profile_version",
            "source_owner_id",
            "approval_authority_id",
            "issuer_id",
            "issued_at",
            "effective_at",
            "expires_at",
            "source",
            "applicability",
            "coverage",
            "finality",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        schema = data["profile_schema"]
        if not isinstance(schema, str) or schema != COVERAGE_FINALITY_PROFILE_SCHEMA:
            raise ModelValidationError(
                f"{path}.profile_schema must be {COVERAGE_FINALITY_PROFILE_SCHEMA}"
            )
        return cls(
            profile_schema=schema,
            profile_id=_identifier(data["profile_id"], f"{path}.profile_id"),
            profile_version=_identifier(
                data["profile_version"], f"{path}.profile_version"
            ),
            source_owner_id=_identifier(
                data["source_owner_id"], f"{path}.source_owner_id"
            ),
            approval_authority_id=_identifier(
                data["approval_authority_id"], f"{path}.approval_authority_id"
            ),
            issuer_id=_identifier(data["issuer_id"], f"{path}.issuer_id"),
            issued_at=parse_datetime(data["issued_at"], f"{path}.issued_at"),
            effective_at=parse_datetime(
                data["effective_at"], f"{path}.effective_at"
            ),
            expires_at=parse_datetime(data["expires_at"], f"{path}.expires_at"),
            source=ProfileSource.from_dict(data["source"], f"{path}.source"),
            applicability=ProfileApplicability.from_dict(
                data["applicability"], f"{path}.applicability"
            ),
            coverage=ProfileCoverage.from_dict(
                data["coverage"], f"{path}.coverage"
            ),
            finality=ProfileFinality.from_dict(
                data["finality"], f"{path}.finality"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_schema": self.profile_schema,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "source_owner_id": self.source_owner_id,
            "approval_authority_id": self.approval_authority_id,
            "issuer_id": self.issuer_id,
            "issued_at": datetime_to_json(self.issued_at),
            "effective_at": datetime_to_json(self.effective_at),
            "expires_at": datetime_to_json(self.expires_at),
            "source": self.source.to_dict(),
            "applicability": self.applicability.to_dict(),
            "coverage": self.coverage.to_dict(),
            "finality": self.finality.to_dict(),
        }

    @property
    def profile_digest(self) -> str:
        return canonical_digest(self.to_dict())


class ProfileRegistryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class ProfileRegistryRecord:
    profile: CoverageFinalityProfile
    profile_digest: str | None
    status: ProfileRegistryStatus
    revoked_at: datetime | None
    revocation_effective_at: datetime | None
    revocation_reason_code: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.profile, CoverageFinalityProfile):
            raise ModelValidationError("registry record profile must be CoverageFinalityProfile")
        expected_digest = self.profile.profile_digest
        if self.profile_digest is None:
            object.__setattr__(self, "profile_digest", expected_digest)
        else:
            supplied = _sha256_digest(
                self.profile_digest, "registry_record.profile_digest"
            )
            if not compare_digest(supplied, expected_digest):
                raise ModelValidationError(
                    "registry_record.profile_digest does not match the canonical profile"
                )
            object.__setattr__(self, "profile_digest", supplied)
        if not isinstance(self.status, ProfileRegistryStatus):
            raise ModelValidationError(
                "registry_record.status must be ACTIVE or REVOKED"
            )
        if self.revoked_at is not None:
            object.__setattr__(
                self,
                "revoked_at",
                _validate_aware_datetime(
                    self.revoked_at, "registry_record.revoked_at"
                ),
            )
        if self.revocation_effective_at is not None:
            object.__setattr__(
                self,
                "revocation_effective_at",
                _validate_aware_datetime(
                    self.revocation_effective_at,
                    "registry_record.revocation_effective_at",
                ),
            )
        if self.revocation_reason_code is not None:
            object.__setattr__(
                self,
                "revocation_reason_code",
                _identifier(
                    self.revocation_reason_code,
                    "registry_record.revocation_reason_code",
                ),
            )
        revocation_values = (
            self.revoked_at,
            self.revocation_effective_at,
            self.revocation_reason_code,
        )
        if self.status is ProfileRegistryStatus.ACTIVE and any(
            item is not None for item in revocation_values
        ):
            raise ModelValidationError(
                "ACTIVE registry records require all revocation fields to be null"
            )
        if self.status is ProfileRegistryStatus.REVOKED and any(
            item is None for item in revocation_values
        ):
            raise ModelValidationError(
                "REVOKED registry records require all revocation fields"
            )
        if (
            self.status is ProfileRegistryStatus.REVOKED
            and self.revocation_effective_at is not None
            and self.revoked_at is not None
            and self.revocation_effective_at > self.revoked_at
        ):
            raise ModelValidationError(
                "REVOKED registry records require revocation_effective_at <= revoked_at"
            )

    @classmethod
    def from_dict(
        cls, value: Any, path: str = "registry_record"
    ) -> "ProfileRegistryRecord":
        data = _mapping(value, path)
        allowed = {
            "profile",
            "profile_digest",
            "status",
            "revoked_at",
            "revocation_effective_at",
            "revocation_reason_code",
        }
        _reject_unknown(data, allowed, path)
        _require_fields(data, allowed, path)
        try:
            status = ProfileRegistryStatus(data["status"])
        except (TypeError, ValueError) as exc:
            raise ModelValidationError(f"{path}.status must be ACTIVE or REVOKED") from exc
        return cls(
            profile=CoverageFinalityProfile.from_dict(
                data["profile"], f"{path}.profile"
            ),
            profile_digest=_sha256_digest(
                data["profile_digest"], f"{path}.profile_digest"
            ),
            status=status,
            revoked_at=optional_datetime(data["revoked_at"], f"{path}.revoked_at"),
            revocation_effective_at=optional_datetime(
                data["revocation_effective_at"],
                f"{path}.revocation_effective_at",
            ),
            revocation_reason_code=(
                None
                if data["revocation_reason_code"] is None
                else _identifier(
                    data["revocation_reason_code"],
                    f"{path}.revocation_reason_code",
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        assert self.profile_digest is not None
        return {
            "profile": self.profile.to_dict(),
            "profile_digest": self.profile_digest,
            "status": self.status.value,
            "revoked_at": (
                datetime_to_json(self.revoked_at) if self.revoked_at is not None else None
            ),
            "revocation_effective_at": (
                datetime_to_json(self.revocation_effective_at)
                if self.revocation_effective_at is not None
                else None
            ),
            "revocation_reason_code": self.revocation_reason_code,
        }


@dataclass(frozen=True, slots=True)
class ProfileRegistrySnapshot:
    snapshot_schema: str
    registry_id: str
    snapshot_id: str
    snapshot_version: str
    issuer_id: str
    as_of: datetime
    next_update_at: datetime
    records: tuple[ProfileRegistryRecord, ...]
    snapshot_digest: str | None = None

    def __post_init__(self) -> None:
        if self.snapshot_schema != PROFILE_REGISTRY_SNAPSHOT_SCHEMA:
            raise ModelValidationError(
                "snapshot.snapshot_schema must identify the supported snapshot contract"
            )
        for name in (
            "registry_id",
            "snapshot_id",
            "snapshot_version",
            "issuer_id",
        ):
            object.__setattr__(
                self, name, _identifier(getattr(self, name), f"snapshot.{name}")
            )
        object.__setattr__(
            self, "as_of", _validate_aware_datetime(self.as_of, "snapshot.as_of")
        )
        object.__setattr__(
            self,
            "next_update_at",
            _validate_aware_datetime(
                self.next_update_at, "snapshot.next_update_at"
            ),
        )
        if self.as_of >= self.next_update_at:
            raise ModelValidationError("snapshot.as_of must precede next_update_at")
        if self.records is None:
            raise ModelValidationError("snapshot.records must be an array, not null")
        if isinstance(self.records, (str, bytes)) or not isinstance(
            self.records, Sequence
        ):
            raise ModelValidationError("snapshot.records must be an array")
        records = tuple(self.records)
        if any(not isinstance(item, ProfileRegistryRecord) for item in records):
            raise ModelValidationError(
                "snapshot.records must contain ProfileRegistryRecord values"
            )
        identities = [
            (item.profile.profile_id, item.profile.profile_version) for item in records
        ]
        if len(set(identities)) != len(identities):
            raise ModelValidationError(
                "snapshot.records must map each profile_id/profile_version exactly once"
            )
        for record in records:
            if (
                record.status is ProfileRegistryStatus.REVOKED
                and record.revoked_at is not None
                and record.revoked_at > self.as_of
            ):
                raise ModelValidationError(
                    "REVOKED registry records require revoked_at <= snapshot.as_of"
                )
        object.__setattr__(
            self,
            "records",
            tuple(
                sorted(
                    records,
                    key=lambda item: (
                        item.profile.profile_id,
                        item.profile.profile_version,
                        item.profile_digest or "",
                    ),
                )
            ),
        )
        expected_digest = canonical_digest(self.payload_dict())
        if self.snapshot_digest is None:
            object.__setattr__(self, "snapshot_digest", expected_digest)
        else:
            supplied = _sha256_digest(
                self.snapshot_digest, "snapshot_digest"
            )
            if not compare_digest(supplied, expected_digest):
                raise ModelValidationError(
                    "snapshot_digest does not match the canonical snapshot payload"
                )
            object.__setattr__(self, "snapshot_digest", supplied)

    @classmethod
    def from_dict(cls, value: Any) -> "ProfileRegistrySnapshot":
        wrapper = _mapping(value, "registry_snapshot")
        _reject_unknown(wrapper, {"snapshot", "snapshot_digest"}, "registry_snapshot")
        _require_fields(wrapper, {"snapshot", "snapshot_digest"}, "registry_snapshot")
        data = _mapping(wrapper["snapshot"], "registry_snapshot.snapshot")
        allowed = {
            "snapshot_schema",
            "registry_id",
            "snapshot_id",
            "snapshot_version",
            "issuer_id",
            "as_of",
            "next_update_at",
            "records",
        }
        _reject_unknown(data, allowed, "registry_snapshot.snapshot")
        _require_fields(data, allowed, "registry_snapshot.snapshot")
        schema = data["snapshot_schema"]
        if not isinstance(schema, str) or schema != PROFILE_REGISTRY_SNAPSHOT_SCHEMA:
            raise ModelValidationError(
                "registry_snapshot.snapshot.snapshot_schema must be "
                f"{PROFILE_REGISTRY_SNAPSHOT_SCHEMA}"
            )
        raw_records = data["records"]
        if isinstance(raw_records, (str, bytes)) or not isinstance(
            raw_records, Sequence
        ):
            raise ModelValidationError(
                "registry_snapshot.snapshot.records must be an array"
            )
        return cls(
            snapshot_schema=schema,
            registry_id=_identifier(
                data["registry_id"], "registry_snapshot.snapshot.registry_id"
            ),
            snapshot_id=_identifier(
                data["snapshot_id"], "registry_snapshot.snapshot.snapshot_id"
            ),
            snapshot_version=_identifier(
                data["snapshot_version"],
                "registry_snapshot.snapshot.snapshot_version",
            ),
            issuer_id=_identifier(
                data["issuer_id"], "registry_snapshot.snapshot.issuer_id"
            ),
            as_of=parse_datetime(data["as_of"], "registry_snapshot.snapshot.as_of"),
            next_update_at=parse_datetime(
                data["next_update_at"],
                "registry_snapshot.snapshot.next_update_at",
            ),
            records=tuple(
                ProfileRegistryRecord.from_dict(
                    item, f"registry_snapshot.snapshot.records[{index}]"
                )
                for index, item in enumerate(raw_records)
            ),
            snapshot_digest=_sha256_digest(
                wrapper["snapshot_digest"], "registry_snapshot.snapshot_digest"
            ),
        )

    def payload_dict(self) -> dict[str, Any]:
        return {
            "snapshot_schema": self.snapshot_schema,
            "registry_id": self.registry_id,
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "issuer_id": self.issuer_id,
            "as_of": datetime_to_json(self.as_of),
            "next_update_at": datetime_to_json(self.next_update_at),
            "records": [record.to_dict() for record in self.records],
        }

    def to_dict(self) -> dict[str, Any]:
        assert self.snapshot_digest is not None
        return {
            "snapshot": self.payload_dict(),
            "snapshot_digest": self.snapshot_digest,
        }


@dataclass(frozen=True, slots=True)
class ProfileTrustSelection:
    trust_schema: str
    registry_id: str
    snapshot_id: str
    snapshot_version: str
    snapshot_digest: str
    trusted_snapshot_issuer_ids: tuple[str, ...]
    trusted_profile_issuer_ids: tuple[str, ...]
    trusted_approval_authority_ids: tuple[str, ...]
    trust_selection_digest: str | None = None

    def __post_init__(self) -> None:
        if self.trust_schema != PROFILE_TRUST_SELECTION_SCHEMA:
            raise ModelValidationError(
                "trust_selection.trust_schema must identify the supported trust contract"
            )
        for name in ("registry_id", "snapshot_id", "snapshot_version"):
            object.__setattr__(
                self,
                name,
                _identifier(getattr(self, name), f"trust_selection.{name}"),
            )
        object.__setattr__(
            self,
            "snapshot_digest",
            _sha256_digest(
                self.snapshot_digest, "trust_selection.snapshot_digest"
            ),
        )
        for name in (
            "trusted_snapshot_issuer_ids",
            "trusted_profile_issuer_ids",
            "trusted_approval_authority_ids",
        ):
            object.__setattr__(
                self,
                name,
                _required_identifier_tuple(
                    getattr(self, name), f"trust_selection.{name}"
                ),
            )
        expected_digest = canonical_digest(self.payload_dict())
        if self.trust_selection_digest is None:
            object.__setattr__(self, "trust_selection_digest", expected_digest)
        else:
            supplied = _sha256_digest(
                self.trust_selection_digest,
                "trust_selection.trust_selection_digest",
            )
            if not compare_digest(supplied, expected_digest):
                raise ModelValidationError(
                    "trust_selection_digest does not match the canonical trust selection"
                )
            object.__setattr__(self, "trust_selection_digest", supplied)

    @classmethod
    def from_dict(cls, value: Any) -> "ProfileTrustSelection":
        data = _mapping(value, "trust_selection")
        allowed = {
            "trust_schema",
            "registry_id",
            "snapshot_id",
            "snapshot_version",
            "snapshot_digest",
            "trusted_snapshot_issuer_ids",
            "trusted_profile_issuer_ids",
            "trusted_approval_authority_ids",
            "trust_selection_digest",
        }
        _reject_unknown(data, allowed, "trust_selection")
        _require_fields(data, allowed, "trust_selection")
        schema = data["trust_schema"]
        if not isinstance(schema, str) or schema != PROFILE_TRUST_SELECTION_SCHEMA:
            raise ModelValidationError(
                f"trust_selection.trust_schema must be {PROFILE_TRUST_SELECTION_SCHEMA}"
            )
        return cls(
            trust_schema=schema,
            registry_id=_identifier(
                data["registry_id"], "trust_selection.registry_id"
            ),
            snapshot_id=_identifier(
                data["snapshot_id"], "trust_selection.snapshot_id"
            ),
            snapshot_version=_identifier(
                data["snapshot_version"], "trust_selection.snapshot_version"
            ),
            snapshot_digest=_sha256_digest(
                data["snapshot_digest"], "trust_selection.snapshot_digest"
            ),
            trusted_snapshot_issuer_ids=_required_identifier_tuple(
                data["trusted_snapshot_issuer_ids"],
                "trust_selection.trusted_snapshot_issuer_ids",
            ),
            trusted_profile_issuer_ids=_required_identifier_tuple(
                data["trusted_profile_issuer_ids"],
                "trust_selection.trusted_profile_issuer_ids",
            ),
            trusted_approval_authority_ids=_required_identifier_tuple(
                data["trusted_approval_authority_ids"],
                "trust_selection.trusted_approval_authority_ids",
            ),
            trust_selection_digest=_sha256_digest(
                data["trust_selection_digest"],
                "trust_selection.trust_selection_digest",
            ),
        )

    def payload_dict(self) -> dict[str, Any]:
        return {
            "trust_schema": self.trust_schema,
            "registry_id": self.registry_id,
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "snapshot_digest": self.snapshot_digest,
            "trusted_snapshot_issuer_ids": list(self.trusted_snapshot_issuer_ids),
            "trusted_profile_issuer_ids": list(self.trusted_profile_issuer_ids),
            "trusted_approval_authority_ids": list(
                self.trusted_approval_authority_ids
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        assert self.trust_selection_digest is not None
        return {
            **self.payload_dict(),
            "trust_selection_digest": self.trust_selection_digest,
        }


@dataclass(frozen=True, slots=True)
class TrustedProfileContext:
    """Application-controlled inputs kept outside the producer request."""

    snapshot: ProfileRegistrySnapshot
    trust_selection: ProfileTrustSelection

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ProfileRegistrySnapshot):
            raise ModelValidationError(
                "trusted_profile_context.snapshot must be ProfileRegistrySnapshot"
            )
        if not isinstance(self.trust_selection, ProfileTrustSelection):
            raise ModelValidationError(
                "trusted_profile_context.trust_selection must be ProfileTrustSelection"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "TrustedProfileContext":
        data = _mapping(value, "trusted_profile_context")
        allowed = {"registry_snapshot", "trust_selection"}
        _reject_unknown(data, allowed, "trusted_profile_context")
        _require_fields(data, allowed, "trusted_profile_context")
        return cls(
            snapshot=ProfileRegistrySnapshot.from_dict(data["registry_snapshot"]),
            trust_selection=ProfileTrustSelection.from_dict(data["trust_selection"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_snapshot": self.snapshot.to_dict(),
            "trust_selection": self.trust_selection.to_dict(),
        }

    @property
    def context_digest(self) -> str:
        return canonical_digest(self.to_dict())


class ProfileIssueCode(str, Enum):
    PROFILE_REFERENCE_UNDECLARED = "PROFILE_REFERENCE_UNDECLARED"
    REGISTRY_SNAPSHOT_UNDECLARED = "REGISTRY_SNAPSHOT_UNDECLARED"
    REGISTRY_SNAPSHOT_IDENTITY_MISMATCH = "REGISTRY_SNAPSHOT_IDENTITY_MISMATCH"
    REGISTRY_SNAPSHOT_DIGEST_MISMATCH = "REGISTRY_SNAPSHOT_DIGEST_MISMATCH"
    REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED = "REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED"
    REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE = "REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE"
    REGISTRY_SNAPSHOT_EXPIRED = "REGISTRY_SNAPSHOT_EXPIRED"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_RESOLUTION_AMBIGUOUS = "PROFILE_RESOLUTION_AMBIGUOUS"
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
    PROFILE_DETECTION_ASSUMPTIONS_MISMATCH = (
        "PROFILE_DETECTION_ASSUMPTIONS_MISMATCH"
    )
    PROFILE_COVERAGE_BASIS_MISMATCH = "PROFILE_COVERAGE_BASIS_MISMATCH"
    PROFILE_RETENTION_EXCEEDED = "PROFILE_RETENTION_EXCEEDED"
    PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY = (
        "PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY"
    )
    PROFILE_OBSERVATION_TOO_OLD = "PROFILE_OBSERVATION_TOO_OLD"
    PROFILE_INDEX_TOO_OLD = "PROFILE_INDEX_TOO_OLD"
    FINALITY_HORIZON_PROFILE_MISMATCH = "FINALITY_HORIZON_PROFILE_MISMATCH"


@dataclass(frozen=True, slots=True)
class ProfileIssue:
    code: ProfileIssueCode
    detail: str
    source_id: str | None = None
    profile_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, ProfileIssueCode):
            raise ModelValidationError("profile_issue.code must be ProfileIssueCode")
        object.__setattr__(
            self, "detail", _declaration(self.detail, "profile_issue.detail")
        )
        if self.source_id is not None:
            object.__setattr__(
                self,
                "source_id",
                _identifier(self.source_id, "profile_issue.source_id"),
            )
        if self.profile_id is not None:
            object.__setattr__(
                self,
                "profile_id",
                _identifier(self.profile_id, "profile_issue.profile_id"),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "detail": self.detail,
            "source_id": self.source_id,
            "profile_id": self.profile_id,
        }


@dataclass(frozen=True, slots=True)
class ProfileAssessment:
    meets_policy: bool
    issues: tuple[ProfileIssue, ...]
    resolved_profile_references: tuple[CoverageProfileReference, ...]
    registry_snapshot_digest: str | None
    trust_selection_digest: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.meets_policy, bool):
            raise ModelValidationError("profile_assessment.meets_policy must be boolean")
        if any(not isinstance(item, ProfileIssue) for item in self.issues):
            raise ModelValidationError(
                "profile_assessment.issues must contain ProfileIssue values"
            )
        if any(
            not isinstance(item, CoverageProfileReference)
            for item in self.resolved_profile_references
        ):
            raise ModelValidationError(
                "profile_assessment.resolved_profile_references must contain CoverageProfileReference values"
            )
        for name in ("registry_snapshot_digest", "trust_selection_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(
                    self,
                    name,
                    _sha256_digest(value, f"profile_assessment.{name}"),
                )
        if self.meets_policy != (not self.issues):
            raise ModelValidationError(
                "profile_assessment.meets_policy must equal the absence of issues"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "meets_policy": self.meets_policy,
            "issues": [item.to_dict() for item in self.issues],
            "resolved_profile_references": [
                item.to_dict() for item in self.resolved_profile_references
            ],
            "registry_snapshot_digest": self.registry_snapshot_digest,
            "trust_selection_digest": self.trust_selection_digest,
        }


def _query_intersects_blind_interval(
    query_start: datetime,
    query_end: datetime,
    interval: BlindInterval,
) -> bool:
    """Return whether inclusive query time intersects ``[start, end)``."""

    return query_start < interval.end and query_end >= interval.start


def evaluate_profile_governance(
    envelope: EvidenceEnvelope,
    evaluated_at: datetime,
    context: TrustedProfileContext | None,
) -> ProfileAssessment:
    """Resolve and assess immutable profiles without external side effects.

    The caller supplies ``evaluated_at`` explicitly.  The full profile and its
    trust selection are separate from the producer-controlled envelope.
    """

    if not isinstance(envelope, EvidenceEnvelope):
        raise ModelValidationError("profile evaluation envelope must be EvidenceEnvelope")
    evaluation_time = _validate_aware_datetime(
        evaluated_at, "profile_evaluation.evaluated_at"
    )
    issues: list[ProfileIssue] = []
    issue_keys: set[tuple[ProfileIssueCode, str | None, str | None]] = set()
    resolved: list[CoverageProfileReference] = []

    def add_issue(
        code: ProfileIssueCode,
        detail: str,
        *,
        source_id: str | None = None,
        profile_id: str | None = None,
    ) -> None:
        key = (code, source_id, profile_id)
        if key in issue_keys:
            return
        issue_keys.add(key)
        issues.append(
            ProfileIssue(
                code=code,
                detail=detail,
                source_id=source_id,
                profile_id=profile_id,
            )
        )

    if context is None:
        add_issue(
            ProfileIssueCode.REGISTRY_SNAPSHOT_UNDECLARED,
            "No application-controlled registry snapshot and trust selection were supplied.",
        )
        for requirement in envelope.query.source_requirements:
            if requirement.profile_ref is None:
                add_issue(
                    ProfileIssueCode.PROFILE_REFERENCE_UNDECLARED,
                    "The required source does not pin an immutable coverage profile.",
                    source_id=requirement.source_id,
                )
        return ProfileAssessment(
            meets_policy=False,
            issues=tuple(issues),
            resolved_profile_references=(),
            registry_snapshot_digest=None,
            trust_selection_digest=None,
        )
    if not isinstance(context, TrustedProfileContext):
        raise ModelValidationError(
            "profile evaluation context must be TrustedProfileContext or null"
        )

    snapshot = context.snapshot
    trust = context.trust_selection
    snapshot_digest = snapshot.snapshot_digest
    trust_digest = trust.trust_selection_digest
    assert snapshot_digest is not None
    assert trust_digest is not None

    identity_matches = (
        trust.registry_id == snapshot.registry_id
        and trust.snapshot_id == snapshot.snapshot_id
        and trust.snapshot_version == snapshot.snapshot_version
    )
    if not identity_matches:
        add_issue(
            ProfileIssueCode.REGISTRY_SNAPSHOT_IDENTITY_MISMATCH,
            "The supplied registry snapshot identity does not match the application trust selection.",
        )
    if not compare_digest(trust.snapshot_digest, snapshot_digest):
        add_issue(
            ProfileIssueCode.REGISTRY_SNAPSHOT_DIGEST_MISMATCH,
            "The supplied registry snapshot digest does not match the application trust selection.",
        )
    if snapshot.issuer_id not in trust.trusted_snapshot_issuer_ids:
        add_issue(
            ProfileIssueCode.REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED,
            "The registry snapshot issuer is not present in the application trust selection.",
        )
    if evaluation_time < snapshot.as_of:
        add_issue(
            ProfileIssueCode.REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE,
            "The evaluation precedes the registry snapshot as-of time.",
        )
    if evaluation_time >= snapshot.next_update_at:
        add_issue(
            ProfileIssueCode.REGISTRY_SNAPSHOT_EXPIRED,
            "The registry snapshot is outside its closed-open validity interval.",
        )

    observations_by_id = {
        observation.source_id: observation
        for observation in envelope.source_observations
    }
    coverage = envelope.coverage
    query = envelope.query

    for requirement in query.source_requirements:
        reference = requirement.profile_ref
        if reference is None:
            add_issue(
                ProfileIssueCode.PROFILE_REFERENCE_UNDECLARED,
                "The required source does not pin an immutable coverage profile.",
                source_id=requirement.source_id,
            )
            continue
        if reference.registry_id != snapshot.registry_id:
            add_issue(
                ProfileIssueCode.REGISTRY_SNAPSHOT_IDENTITY_MISMATCH,
                "The source profile reference names a different registry.",
                source_id=requirement.source_id,
                profile_id=reference.profile_id,
            )
            continue
        matches = tuple(
            record
            for record in snapshot.records
            if record.profile.profile_id == reference.profile_id
            and record.profile.profile_version == reference.profile_version
        )
        if not matches:
            add_issue(
                ProfileIssueCode.PROFILE_NOT_FOUND,
                "No registry record matches the exact profile identifier and version.",
                source_id=requirement.source_id,
                profile_id=reference.profile_id,
            )
            continue
        if len(matches) != 1:
            add_issue(
                ProfileIssueCode.PROFILE_RESOLUTION_AMBIGUOUS,
                "More than one registry record matches the exact profile identifier and version.",
                source_id=requirement.source_id,
                profile_id=reference.profile_id,
            )
            continue
        record = matches[0]
        assert record.profile_digest is not None
        if not compare_digest(reference.profile_digest, record.profile_digest):
            add_issue(
                ProfileIssueCode.PROFILE_DIGEST_MISMATCH,
                "The source profile reference does not match the registry profile digest.",
                source_id=requirement.source_id,
                profile_id=reference.profile_id,
            )
            continue
        resolved.append(reference)
        profile = record.profile

        if profile.issuer_id not in trust.trusted_profile_issuer_ids:
            add_issue(
                ProfileIssueCode.PROFILE_ISSUER_UNTRUSTED,
                "The profile issuer is not present in the application trust selection.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if (
            profile.approval_authority_id
            not in trust.trusted_approval_authority_ids
        ):
            add_issue(
                ProfileIssueCode.PROFILE_AUTHORITY_UNTRUSTED,
                "The profile approval authority is not present in the application trust selection.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if evaluation_time < profile.effective_at:
            add_issue(
                ProfileIssueCode.PROFILE_NOT_YET_EFFECTIVE,
                "The evaluation precedes the profile effective time.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if evaluation_time >= profile.expires_at:
            add_issue(
                ProfileIssueCode.PROFILE_EXPIRED,
                "The profile is outside its closed-open validity interval.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if (
            record.status is ProfileRegistryStatus.REVOKED
            and record.revocation_effective_at is not None
            and evaluation_time >= record.revocation_effective_at
        ):
            add_issue(
                ProfileIssueCode.PROFILE_REVOKED,
                "The profile was revoked at or before the evaluation time.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )

        profile_source = profile.source
        if (
            requirement.source_id != profile_source.source_id
            or requirement.system != profile_source.system
            or requirement.locator != profile_source.locator
        ):
            add_issue(
                ProfileIssueCode.PROFILE_SOURCE_MISMATCH,
                "The required source identity does not exactly match the profile.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if (
            requirement.adapter_id != profile_source.adapter_id
            or requirement.adapter_version != profile_source.adapter_version
        ):
            add_issue(
                ProfileIssueCode.PROFILE_ADAPTER_MISMATCH,
                "The required adapter identity does not exactly match the profile.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if (
            requirement.authorization_context_id
            != profile_source.authorization_context_id
            or query.authorization_context_id
            != profile_source.authorization_context_id
            or query.authorization_boundary
            != profile.applicability.authorization_boundary
            or coverage.permission_limited != profile.coverage.permission_limited
        ):
            add_issue(
                ProfileIssueCode.PROFILE_AUTHORIZATION_MISMATCH,
                "The authorization context, boundary, or permission-limited state does not exactly match the profile.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if requirement.accessible_population != profile_source.accessible_population:
            add_issue(
                ProfileIssueCode.PROFILE_POPULATION_MISMATCH,
                "The required accessible population does not exactly match the profile.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if (
            query.target != profile.applicability.target
            or query.predicate != profile.applicability.predicate
            or not set(profile.applicability.required_exclusions).issubset(
                query.exclusions
            )
        ):
            add_issue(
                ProfileIssueCode.PROFILE_QUERY_APPLICABILITY_MISMATCH,
                "The query target, predicate, or required exclusions do not satisfy the profile.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if (
            tuple(requirement.detection_assumptions)
            != profile.applicability.detection_assumptions
        ):
            add_issue(
                ProfileIssueCode.PROFILE_DETECTION_ASSUMPTIONS_MISMATCH,
                "The required detection assumptions do not exactly match the profile.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )
        if (
            coverage.population_basis is not PopulationBasis.EXACT
            or coverage.population_units != profile.coverage.population_units
            or coverage.pages_expected != profile.coverage.pages_expected
            or coverage.partitions_expected != profile.coverage.partitions_expected
        ):
            add_issue(
                ProfileIssueCode.PROFILE_COVERAGE_BASIS_MISMATCH,
                "The runtime denominator or optional page and partition counts do not exactly match the fixed profile coverage contract.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )

        for interval in profile.coverage.blind_intervals:
            if _query_intersects_blind_interval(
                query.time_start, query.time_end, interval
            ):
                add_issue(
                    ProfileIssueCode.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY,
                    "The inclusive query interval intersects a governed closed-open blind interval.",
                    source_id=requirement.source_id,
                    profile_id=profile.profile_id,
                )
                break

        if evaluation_time >= envelope.observed_at and _timedelta_exceeds_seconds(
            evaluation_time - envelope.observed_at,
            profile.coverage.max_observation_age_seconds,
        ):
            add_issue(
                ProfileIssueCode.PROFILE_OBSERVATION_TOO_OLD,
                "The envelope observation exceeds the profile freshness limit.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )

        observation = observations_by_id.get(requirement.source_id)
        if observation is None:
            index_as_of = None
        else:
            descriptor = observation.descriptor
            if (
                descriptor.system != profile_source.system
                or descriptor.locator != profile_source.locator
            ):
                add_issue(
                    ProfileIssueCode.PROFILE_SOURCE_MISMATCH,
                    "The runtime source descriptor does not exactly match the profile.",
                    source_id=requirement.source_id,
                    profile_id=profile.profile_id,
                )
            if (
                descriptor.adapter_id != profile_source.adapter_id
                or descriptor.adapter_version != profile_source.adapter_version
            ):
                add_issue(
                    ProfileIssueCode.PROFILE_ADAPTER_MISMATCH,
                    "The runtime adapter descriptor does not exactly match the profile.",
                    source_id=requirement.source_id,
                    profile_id=profile.profile_id,
                )
            if (
                observation.authorization_context_id
                != profile_source.authorization_context_id
            ):
                add_issue(
                    ProfileIssueCode.PROFILE_AUTHORIZATION_MISMATCH,
                    "The runtime authorization context does not exactly match the profile.",
                    source_id=requirement.source_id,
                    profile_id=profile.profile_id,
                )
            if (
                observation.status is SourceObservationStatus.OBSERVED
                and observation.accessible_population
                != profile_source.accessible_population
            ):
                add_issue(
                    ProfileIssueCode.PROFILE_POPULATION_MISMATCH,
                    "The runtime accessible population does not exactly match the profile.",
                    source_id=requirement.source_id,
                    profile_id=profile.profile_id,
                )
            index_as_of = descriptor.index_as_of

        if index_as_of is not None:
            if (
                index_as_of >= query.time_start
                and _timedelta_exceeds_seconds(
                    index_as_of - query.time_start,
                    profile.coverage.retention_seconds,
                )
            ):
                add_issue(
                    ProfileIssueCode.PROFILE_RETENTION_EXCEEDED,
                    "The query starts before the source retention boundary derived from index_as_of.",
                    source_id=requirement.source_id,
                    profile_id=profile.profile_id,
                )
            if evaluation_time >= index_as_of and _timedelta_exceeds_seconds(
                evaluation_time - index_as_of,
                profile.coverage.max_index_age_seconds,
            ):
                add_issue(
                    ProfileIssueCode.PROFILE_INDEX_TOO_OLD,
                    "The source index timestamp exceeds the profile freshness limit.",
                    source_id=requirement.source_id,
                    profile_id=profile.profile_id,
                )

        finality_delay = max(
            profile.finality.late_arrival_bound_seconds,
            profile.finality.reopen_bound_seconds,
        )
        try:
            expected_horizon = query.time_end + timedelta(seconds=finality_delay)
        except OverflowError as exc:
            raise ModelValidationError(
                "profile finality horizon is not representable as a timestamp"
            ) from exc
        if (
            requirement.finality_horizon is not None
            and requirement.finality_horizon != expected_horizon
        ):
            add_issue(
                ProfileIssueCode.FINALITY_HORIZON_PROFILE_MISMATCH,
                "The request finality horizon is not the exact horizon derived by the immutable profile.",
                source_id=requirement.source_id,
                profile_id=profile.profile_id,
            )

    return ProfileAssessment(
        meets_policy=not issues,
        issues=tuple(issues),
        resolved_profile_references=tuple(
            sorted(
                resolved,
                key=lambda item: (
                    item.registry_id,
                    item.profile_id,
                    item.profile_version,
                    item.profile_digest,
                ),
            )
        ),
        registry_snapshot_digest=snapshot_digest,
        trust_selection_digest=trust_digest,
    )


__all__ = [
    "COVERAGE_FINALITY_PROFILE_SCHEMA",
    "FINALITY_METHOD",
    "PROFILE_REGISTRY_SNAPSHOT_SCHEMA",
    "PROFILE_TRUST_SELECTION_SCHEMA",
    "BlindInterval",
    "CoverageFinalityProfile",
    "ProfileApplicability",
    "ProfileAssessment",
    "ProfileCoverage",
    "ProfileFinality",
    "ProfileIssue",
    "ProfileIssueCode",
    "ProfileRegistryRecord",
    "ProfileRegistrySnapshot",
    "ProfileRegistryStatus",
    "ProfileSource",
    "ProfileTrustSelection",
    "TrustedProfileContext",
    "evaluate_profile_governance",
]
