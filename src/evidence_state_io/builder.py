"""Producer-side construction of an evidence envelope from observed facts.

Authoring an envelope by hand is roughly a hundred lines of JSON, and the
hardest part of adoption should not be describing what you already did. This
builder takes the facts a source actually reported and assembles the envelope.

It is built so that the easy path is the honest one.

Nothing here has a default for a completeness fact. `pagination_complete`,
`partitions_complete`, `timed_out`, `interrupted`, and `permission_limited` have
no default value, so a caller who has not thought about them cannot silently
inherit the optimistic answer. A builder whose defaults were all `True` would
manufacture exactly the coverage this project exists to refuse.

The caller does not declare the evidence state; it is derived from the facts.
A producer that could both report an incomplete enumeration and label it
`ABSENT_WITHIN_SCOPE` would be asserting the conclusion the gate is supposed to
reach on its own, so the builder derives conservatively and the gate still
checks the result. The derivation never reaches `ABSENT_WITHIN_SCOPE` from
facts that do not support it, and it cannot be persuaded to.

Nothing here consults the wall clock, the network, the filesystem, the
environment, or any mutable global state. Observation times are inputs, because
a producer that timestamps its own evidence from the clock cannot be replayed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .errors import ModelValidationError
from .gate import ClaimMode, NegativeClaimPolicy, NegativeClaimRequest
from .models import (
    SCHEMA_VERSION_COMPOSED,
    SCHEMA_VERSION_SINGLE_SOURCE,
    CompositionMode,
    CoverageEvidence,
    CoverageProfileReference,
    EvidenceEnvelope,
    EvidenceState,
    PopulationBasis,
    QueryScope,
    SourceDescriptor,
    SourceObservation,
    SourceObservationStatus,
    SourceRequirement,
    SourceRole,
)


@dataclass(frozen=True)
class SourceReading:
    """What one source reported, as facts rather than as a conclusion.

    Every field that bears on completeness is required. That is the point: an
    adapter that does not know whether it drained its pagination has to say so
    rather than inherit an optimistic default.
    """

    source_id: str
    matched_count: int
    examined_units: int
    population_basis: PopulationBasis
    pagination_complete: bool
    continuation_token_present: bool
    partitions_complete: bool
    timed_out: bool
    interrupted: bool
    permission_limited: bool
    observed_at: datetime
    index_as_of: datetime | None = None
    population_units: int | None = None
    pages_examined: int | None = None
    pages_expected: int | None = None
    partitions_examined: int | None = None
    partitions_expected: int | None = None
    query_errors: tuple[str, ...] = ()
    valid_until: datetime | None = None

    def coverage(self) -> CoverageEvidence:
        return CoverageEvidence(
            examined_units=self.examined_units,
            population_basis=self.population_basis,
            pagination_complete=self.pagination_complete,
            continuation_token_present=self.continuation_token_present,
            partitions_complete=self.partitions_complete,
            timed_out=self.timed_out,
            interrupted=self.interrupted,
            permission_limited=self.permission_limited,
            query_errors=tuple(self.query_errors),
            population_units=self.population_units,
            pages_examined=self.pages_examined,
            pages_expected=self.pages_expected,
            partitions_examined=self.partitions_examined,
            partitions_expected=self.partitions_expected,
        )

    @property
    def enumeration_complete(self) -> bool:
        return (
            self.pagination_complete
            and self.partitions_complete
            and not self.continuation_token_present
        )

    @property
    def execution_faulted(self) -> bool:
        return bool(self.query_errors) or self.timed_out or self.interrupted

    def derived_state(self) -> EvidenceState:
        """Return the strongest state these facts support, and no stronger.

        The order matters. A source that saw a match reports presence whatever
        else went wrong. A source whose run faulted reports nothing about
        absence, because an enumeration that broke partway is not a search that
        finished and found nothing. Only a complete, unfaulted enumeration of a
        quantified population reaches in-scope absence.
        """

        if self.matched_count > 0:
            return EvidenceState.PRESENT
        if self.query_errors:
            return EvidenceState.FAILED
        if self.timed_out or self.interrupted:
            return EvidenceState.NOT_OBSERVED
        if not self.enumeration_complete:
            return EvidenceState.PARTIAL
        return EvidenceState.ABSENT_WITHIN_SCOPE

    def derived_status(self) -> SourceObservationStatus:
        state = self.derived_state()
        if state is EvidenceState.FAILED:
            return SourceObservationStatus.FAILED
        if state is EvidenceState.NOT_OBSERVED:
            return SourceObservationStatus.NOT_OBSERVED
        return SourceObservationStatus.OBSERVED

    def quantified_fraction(self) -> float | None:
        """Return examined over declared population, or None when unquantified."""

        if self.population_units is None or self.population_units == 0:
            return None
        return self.examined_units / self.population_units


@dataclass
class _Declared:
    requirement: SourceRequirement
    reading: SourceReading | None = None


class EvidenceBuilder:
    """Assemble an envelope from declared sources and what they reported."""

    def __init__(
        self,
        *,
        target: str,
        predicate: str,
        authorization_boundary: str,
        authorization_context_id: str,
        time_start: datetime,
        time_end: datetime,
        exclusions: Sequence[str],
    ) -> None:
        self._target = target
        self._predicate = predicate
        self._authorization_boundary = authorization_boundary
        self._authorization_context_id = authorization_context_id
        self._time_start = time_start
        self._time_end = time_end
        self._exclusions = tuple(exclusions)
        self._sources: dict[str, _Declared] = {}
        self._order: list[str] = []

    def require_source(
        self,
        *,
        source_id: str,
        system: str,
        locator: str,
        adapter_id: str,
        adapter_version: str,
        accessible_population: str,
        detection_assumptions: Sequence[str],
        finality_horizon: datetime | None = None,
        profile_ref: CoverageProfileReference | None = None,
    ) -> "EvidenceBuilder":
        """Declare a source the query requires, before anything is observed."""

        if source_id in self._sources:
            raise ModelValidationError(f"source {source_id!r} is already declared")
        self._sources[source_id] = _Declared(
            requirement=SourceRequirement(
                source_id=source_id,
                role=SourceRole.REQUIRED,
                system=system,
                locator=locator,
                adapter_id=adapter_id,
                adapter_version=adapter_version,
                authorization_context_id=self._authorization_context_id,
                accessible_population=accessible_population,
                detection_assumptions=tuple(detection_assumptions),
                finality_horizon=finality_horizon,
                profile_ref=profile_ref,
            )
        )
        self._order.append(source_id)
        return self

    def record(self, reading: SourceReading) -> "EvidenceBuilder":
        """Record what a declared source reported."""

        if type(reading) is not SourceReading:
            raise ModelValidationError("record expects a SourceReading")
        declared = self._sources.get(reading.source_id)
        if declared is None:
            raise ModelValidationError(
                f"source {reading.source_id!r} was not declared; declare every source "
                "the query requires before recording what it reported"
            )
        if declared.reading is not None:
            raise ModelValidationError(
                f"source {reading.source_id!r} already reported; a second reading would "
                "silently replace evidence rather than add to it"
            )
        declared.reading = reading
        return self

    # ------------------------------------------------------------- assembly

    def _query(self, composition: CompositionMode | None) -> QueryScope:
        return QueryScope(
            target=self._target,
            predicate=self._predicate,
            authorization_boundary=self._authorization_boundary,
            authorization_context_id=self._authorization_context_id,
            time_start=self._time_start,
            time_end=self._time_end,
            exclusions=self._exclusions,
            source_requirements=tuple(
                self._sources[source_id].requirement for source_id in self._order
            ),
            composition=composition,
        )

    def _readings(self) -> tuple[SourceReading, ...]:
        missing = [
            source_id for source_id in self._order if self._sources[source_id].reading is None
        ]
        if missing:
            raise ModelValidationError(
                "every declared source must report before an envelope can be built; "
                "missing: " + ", ".join(sorted(missing))
            )
        return tuple(
            reading
            for reading in (self._sources[source_id].reading for source_id in self._order)
            if reading is not None
        )

    @staticmethod
    def _aggregate_state(readings: Sequence[SourceReading]) -> EvidenceState:
        """Return the state the whole set supports.

        Corroborating sources observe the same declared population, so the
        aggregate is not a tally. Any source that saw a match means presence was
        observed; absence requires every source to support it.
        """

        states = [reading.derived_state() for reading in readings]
        if any(state is EvidenceState.PRESENT for state in states):
            return EvidenceState.PRESENT
        for weaker in (
            EvidenceState.FAILED,
            EvidenceState.NOT_OBSERVED,
            EvidenceState.PARTIAL,
        ):
            if any(state is weaker for state in states):
                return weaker
        return EvidenceState.ABSENT_WITHIN_SCOPE

    @staticmethod
    def _strongest(readings: Sequence[SourceReading]) -> SourceReading:
        """Return the best-covered reading, ties broken by source_id.

        Corroborated coverage composes by maximum, so the envelope's aggregate
        coverage is the best single source's and never a sum. Anything larger
        would claim coverage out of an overlap nobody measured, and the gate
        rejects it as overstated.
        """

        return sorted(
            readings,
            key=lambda item: (
                item.quantified_fraction() is not None,
                item.quantified_fraction() or 0.0,
                item.source_id,
            ),
            reverse=True,
        )[0]

    def build(
        self,
        *,
        observed_at: datetime | None = None,
        valid_until: datetime | None = None,
        composition: CompositionMode | None = None,
    ) -> EvidenceEnvelope:
        """Assemble the envelope.

        `observed_at` defaults to the moment the last source was read, which is
        derived from the readings rather than from a clock. A later value may be
        supplied when the envelope is genuinely sealed later; an earlier one is
        refused, because a source cannot have looked after the envelope closed.

        `valid_until` defaults to the earliest boundary any source declared. A
        later value would let the envelope outlive a source's own result.
        """

        readings = self._readings()
        if composition is None and len(readings) > 1:
            raise ModelValidationError(
                "more than one required source needs a declared composition mode; "
                "without one there is no rule for what several sources jointly mean"
            )

        last_read = max(reading.observed_at for reading in readings)
        sealed_at = last_read if observed_at is None else observed_at
        if sealed_at < last_read:
            raise ModelValidationError(
                "observed_at precedes the last source reading; a source cannot have "
                "looked after the envelope was sealed"
            )

        declared_validity = [
            reading.valid_until for reading in readings if reading.valid_until is not None
        ]
        earliest_validity = min(declared_validity) if declared_validity else None
        if valid_until is None:
            boundary = earliest_validity
        else:
            boundary = valid_until
            if earliest_validity is not None and boundary > earliest_validity:
                raise ModelValidationError(
                    "valid_until outlives the earliest boundary a source declared"
                )

        composed = composition is not None
        query = self._query(composition)
        fingerprint = query.fingerprint()
        aggregate = self._strongest(readings)
        state = self._aggregate_state(readings)
        matched = max(reading.matched_count for reading in readings)

        observations = tuple(
            SourceObservation(
                source_id=reading.source_id,
                status=reading.derived_status(),
                descriptor=SourceDescriptor(
                    system=self._sources[reading.source_id].requirement.system,
                    locator=self._sources[reading.source_id].requirement.locator,
                    adapter_id=self._sources[reading.source_id].requirement.adapter_id,
                    adapter_version=self._sources[reading.source_id].requirement.adapter_version,
                    index_as_of=reading.index_as_of,
                ),
                authorization_context_id=self._authorization_context_id,
                query_fingerprint=fingerprint,
                accessible_population=(
                    self._sources[reading.source_id].requirement.accessible_population
                    if reading.derived_status() is SourceObservationStatus.OBSERVED
                    else None
                ),
                errors=tuple(reading.query_errors),
                coverage=reading.coverage() if composed else None,
                state=reading.derived_state() if composed else None,
                matched_count=reading.matched_count if composed else None,
                observed_at=reading.observed_at if composed else None,
                valid_until=reading.valid_until if composed else None,
            )
            for reading in readings
        )

        return EvidenceEnvelope(
            schema_version=(SCHEMA_VERSION_COMPOSED if composed else SCHEMA_VERSION_SINGLE_SOURCE),
            state=state,
            query=query,
            coverage=aggregate.coverage(),
            coverage_query_fingerprint=fingerprint,
            matched_count=matched,
            observed_at=sealed_at,
            valid_until=boundary,
            source_observations=observations,
            errors=(),
            notes=(),
        )

    def request(
        self,
        *,
        subject: str,
        evaluated_at: datetime,
        policy: NegativeClaimPolicy | None = None,
        mode: ClaimMode = ClaimMode.SCOPED,
        observed_at: datetime | None = None,
        valid_until: datetime | None = None,
        composition: CompositionMode | None = None,
    ) -> NegativeClaimRequest:
        """Assemble the envelope and wrap it in a claim request.

        `evaluated_at` is required and is never defaulted from a clock, for the
        same reason the gate requires it: a decision that cannot be replayed is
        not evidence.
        """

        return NegativeClaimRequest(
            subject=subject,
            mode=mode,
            evaluated_at=evaluated_at,
            policy=NegativeClaimPolicy() if policy is None else policy,
            envelope=self.build(
                observed_at=observed_at,
                valid_until=valid_until,
                composition=composition,
            ),
        )


__all__ = ["EvidenceBuilder", "SourceReading"]
