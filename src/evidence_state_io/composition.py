"""Deterministic composition of several required sources into one assessment.

ADR-0015. This candidate implements `CORROBORATION` only: every required
source claims to observe the same declared population.

The rule that matters is that corroborated coverage composes by **maximum**,
never by sum. If one source covers 60% of a population and another covers 60%
of the same population, the union is covered somewhere between 60% and 100%,
and which one depends on an overlap nobody measured. Each source's lower bound
is a guarantee about that source alone, so the union is guaranteed to be at
least as covered as the best single source and nothing observed licenses more.
Adding, averaging, or rewarding agreement would manufacture coverage out of
that unmeasured overlap, and would let a caller reach a permit by adding
sources rather than by observing more.

Every other rule takes the conservative branch for the same reason: finality
binds on the slowest source, freshness on the stalest, validity on the
earliest, and disagreement rejects rather than being resolved by counting.

Nothing here consults the wall clock, the network, the filesystem, the
environment, or any mutable global state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Sequence

from .coverage import CoverageAssessment
from .errors import ModelValidationError
from .models import EvidenceState

COMPOSITION_SCHEMA = "esio-multi-source-composition/1.0-candidate.1"

# A fail-closed bound on the composition surface, chosen so the composed
# assessment stays reviewable by hand.  It is not a performance limit.
MAX_REQUIRED_SOURCES = 4


class CompositionMode(str, Enum):
    """Declared composition intent.

    `PARTITION` is deliberately absent from this candidate. It is the only mode
    in which coverage accumulates, and it requires each source to declare a
    disjoint accessible subpopulation whose union equals the queried
    population. Nothing in the governed profile expresses that yet, so
    admitting the mode before it can be checked would mean accepting an
    undeclared partition, which is exactly an uncovered region.
    """

    CORROBORATION = "CORROBORATION"


class CompositionIssueCode(str, Enum):
    NO_REQUIRED_SOURCES = "NO_REQUIRED_SOURCES"
    TOO_MANY_REQUIRED_SOURCES = "TOO_MANY_REQUIRED_SOURCES"
    DUPLICATE_SOURCE_ID = "DUPLICATE_SOURCE_ID"
    SOURCE_STATES_DISAGREE = "SOURCE_STATES_DISAGREE"
    SOURCE_NOT_ABSENT_WITHIN_SCOPE = "SOURCE_NOT_ABSENT_WITHIN_SCOPE"
    SOURCE_REPORTS_MATCHES = "SOURCE_REPORTS_MATCHES"
    SOURCE_COVERAGE_NOT_MET = "SOURCE_COVERAGE_NOT_MET"
    COMPOSED_COVERAGE_UNQUANTIFIED = "COMPOSED_COVERAGE_UNQUANTIFIED"
    SOURCE_FINALITY_HORIZON_UNDECLARED = "SOURCE_FINALITY_HORIZON_UNDECLARED"
    SOURCE_INDEX_UNDECLARED = "SOURCE_INDEX_UNDECLARED"
    SOURCE_INDEX_PRECEDES_OWN_HORIZON = "SOURCE_INDEX_PRECEDES_OWN_HORIZON"


# When sources report different indeterminate states, the composed state is the
# worst one present.  The order is explicit so the composition is reviewable
# and cannot drift with dictionary or input ordering.
_STATE_SEVERITY: tuple[EvidenceState, ...] = (
    EvidenceState.CONTRADICTORY,
    EvidenceState.FAILED,
    EvidenceState.INACCESSIBLE,
    EvidenceState.NOT_OBSERVED,
    EvidenceState.PENDING_WINDOW,
    EvidenceState.STALE,
    EvidenceState.PARTIAL,
    EvidenceState.PRESENT,
    EvidenceState.ABSENT_WITHIN_SCOPE,
)
_SEVERITY_RANK = {state: rank for rank, state in enumerate(_STATE_SEVERITY)}


def _isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class CompositionIssue:
    code: CompositionIssueCode
    source_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, CompositionIssueCode):
            raise ModelValidationError("composition_issue.code must be a CompositionIssueCode")
        if self.source_id is not None and not isinstance(self.source_id, str):
            raise ModelValidationError("composition_issue.source_id must be a string or null")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "source_id": self.source_id}


@dataclass(frozen=True)
class SourceContribution:
    """One required source's independently assessed contribution.

    Each field is that source's own evidence. Nothing here is composed; the
    composition is this module's conclusion, never a producer's assertion.
    """

    source_id: str
    state: EvidenceState
    matched_count: int
    coverage: CoverageAssessment
    observed_at: datetime
    index_as_of: datetime | None = None
    finality_horizon: datetime | None = None
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ModelValidationError("contribution.source_id must be a non-empty string")
        if not isinstance(self.state, EvidenceState):
            raise ModelValidationError("contribution.state must be an EvidenceState")
        if type(self.matched_count) is not int or self.matched_count < 0:
            raise ModelValidationError("contribution.matched_count must be a non-negative integer")
        if not isinstance(self.coverage, CoverageAssessment):
            raise ModelValidationError("contribution.coverage must be a CoverageAssessment")
        for name in ("observed_at", "index_as_of", "finality_horizon", "valid_until"):
            value = getattr(self, name)
            if value is None:
                if name == "observed_at":
                    raise ModelValidationError("contribution.observed_at is required")
                continue
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ModelValidationError(f"contribution.{name} must be a timezone-aware datetime")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "state": self.state.value,
            "matched_count": self.matched_count,
            "coverage": self.coverage.to_dict(),
            "observed_at": _isoformat(self.observed_at),
            "index_as_of": None if self.index_as_of is None else _isoformat(self.index_as_of),
            "finality_horizon": (
                None if self.finality_horizon is None else _isoformat(self.finality_horizon)
            ),
            "valid_until": None if self.valid_until is None else _isoformat(self.valid_until),
        }


@dataclass(frozen=True)
class CompositionAssessment:
    """What several required sources jointly support, and what they do not."""

    mode: CompositionMode
    composed_state: EvidenceState
    composed_lower_bound: float | None
    binding_finality_horizon: datetime | None
    weakest_index_as_of: datetime | None
    stalest_observed_at: datetime
    earliest_valid_until: datetime | None
    source_ids: tuple[str, ...]
    issues: tuple[CompositionIssue, ...]

    @property
    def meets_policy(self) -> bool:
        """True only when every source supports the same in-scope absence."""

        return not self.issues and self.composed_state is EvidenceState.ABSENT_WITHIN_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "composition_schema": COMPOSITION_SCHEMA,
            "mode": self.mode.value,
            "composed_state": self.composed_state.value,
            "composed_lower_bound": self.composed_lower_bound,
            "binding_finality_horizon": (
                None
                if self.binding_finality_horizon is None
                else _isoformat(self.binding_finality_horizon)
            ),
            "weakest_index_as_of": (
                None if self.weakest_index_as_of is None else _isoformat(self.weakest_index_as_of)
            ),
            "stalest_observed_at": _isoformat(self.stalest_observed_at),
            "earliest_valid_until": (
                None if self.earliest_valid_until is None else _isoformat(self.earliest_valid_until)
            ),
            "source_ids": list(self.source_ids),
            "issues": [issue.to_dict() for issue in self.issues],
            "meets_policy": self.meets_policy,
        }


def _composed_state(contributions: Sequence[SourceContribution]) -> EvidenceState:
    """Return the state several sources jointly support.

    Disagreement is never resolved by counting. If any source reports in-scope
    presence while another reports in-scope absence, the composition is
    `CONTRADICTORY`: a majority rule would convert a contradiction into a
    permit whenever the fabricating side brought more sources, and the gate has
    no authenticated adapter evidence with which to tell an honest minority
    from a dishonest majority.
    """

    asserts_absence = any(
        item.state is EvidenceState.ABSENT_WITHIN_SCOPE and item.matched_count == 0
        for item in contributions
    )
    asserts_presence = any(
        item.state is EvidenceState.PRESENT or item.matched_count > 0 for item in contributions
    )
    if asserts_absence and asserts_presence:
        return EvidenceState.CONTRADICTORY
    return min(
        (item.state for item in contributions),
        key=lambda state: _SEVERITY_RANK[state],
    )


def _composed_lower_bound(contributions: Sequence[SourceContribution]) -> float | None:
    """Return the conservative floor across sources: the maximum, never a sum.

    A source whose bound is unquantified contributes nothing and does not drag
    the floor down: the best known bound remains a valid guarantee about the
    union. If no source quantifies its coverage, the composition is
    unquantified.
    """

    known = [
        item.coverage.lower_bound for item in contributions if item.coverage.lower_bound is not None
    ]
    if not known:
        return None
    return max(known)


def compose_sources(
    contributions: Sequence[SourceContribution],
    *,
    mode: CompositionMode = CompositionMode.CORROBORATION,
) -> CompositionAssessment:
    """Compose several required sources into one deterministic assessment.

    Pure and order-independent: the same set of contributions in any order
    produces the same assessment.
    """

    if type(mode) is not CompositionMode:
        raise ModelValidationError("mode must be a CompositionMode")
    if isinstance(contributions, (str, bytes)) or not isinstance(contributions, Sequence):
        raise ModelValidationError("contributions must be a sequence")
    items = tuple(contributions)
    if any(type(item) is not SourceContribution for item in items):
        raise ModelValidationError("contributions must contain SourceContribution values")

    issues: list[CompositionIssue] = []

    def add(code: CompositionIssueCode, source_id: str | None = None) -> None:
        issue = CompositionIssue(code=code, source_id=source_id)
        if issue not in issues:
            issues.append(issue)

    if not items:
        raise ModelValidationError("composition requires at least one required source")
    if len(items) > MAX_REQUIRED_SOURCES:
        add(CompositionIssueCode.TOO_MANY_REQUIRED_SOURCES)

    # Order-independence: evaluate in a canonical order regardless of input
    # order, so the assessment is a property of the set and not of the caller.
    items = tuple(sorted(items, key=lambda item: item.source_id))
    source_ids = tuple(item.source_id for item in items)
    duplicates = sorted({sid for sid in source_ids if source_ids.count(sid) > 1})
    for duplicate in duplicates:
        add(CompositionIssueCode.DUPLICATE_SOURCE_ID, duplicate)

    for item in items:
        if item.matched_count > 0:
            add(CompositionIssueCode.SOURCE_REPORTS_MATCHES, item.source_id)
        if item.state is not EvidenceState.ABSENT_WITHIN_SCOPE:
            add(CompositionIssueCode.SOURCE_NOT_ABSENT_WITHIN_SCOPE, item.source_id)
        if not item.coverage.meets_policy:
            add(CompositionIssueCode.SOURCE_COVERAGE_NOT_MET, item.source_id)
        if item.finality_horizon is None:
            add(CompositionIssueCode.SOURCE_FINALITY_HORIZON_UNDECLARED, item.source_id)
        if item.index_as_of is None:
            add(CompositionIssueCode.SOURCE_INDEX_UNDECLARED, item.source_id)
        elif item.finality_horizon is not None and item.index_as_of < item.finality_horizon:
            # Each source must reach its own horizon.  A shared or earliest
            # horizon would permit a claim during a window in which a lagging
            # source could still receive a late arrival for the queried
            # interval.
            add(CompositionIssueCode.SOURCE_INDEX_PRECEDES_OWN_HORIZON, item.source_id)

    composed_state = _composed_state(items)
    if composed_state is EvidenceState.CONTRADICTORY and len(items) > 1:
        add(CompositionIssueCode.SOURCE_STATES_DISAGREE)

    composed_lower_bound = _composed_lower_bound(items)
    if composed_lower_bound is None:
        add(CompositionIssueCode.COMPOSED_COVERAGE_UNQUANTIFIED)

    horizons = [item.finality_horizon for item in items if item.finality_horizon is not None]
    indexes = [item.index_as_of for item in items if item.index_as_of is not None]
    validities = [item.valid_until for item in items if item.valid_until is not None]

    return CompositionAssessment(
        mode=mode,
        composed_state=composed_state,
        composed_lower_bound=composed_lower_bound,
        # Latest horizon: the claim is not final until the slowest source has
        # settled.
        binding_finality_horizon=max(horizons) if horizons else None,
        # Earliest index: the weakest link, reported so the composition cannot
        # look stronger than its laggard.
        weakest_index_as_of=min(indexes) if indexes else None,
        # Stalest observation and earliest validity: a composed claim is
        # exactly as fresh as its stalest constituent.
        stalest_observed_at=min(item.observed_at for item in items),
        earliest_valid_until=min(validities) if validities else None,
        source_ids=source_ids,
        issues=tuple(issues),
    )
