"""The read-only adapter contract.

An adapter turns one source's response into a `SourceReading`: the coverage
facts a negative claim needs, stated honestly. The contract is deliberately
narrow, and every method on it reads.

What an adapter must report, and why each one matters:

*Enumeration completeness.* Whether pagination was drained, whether partitions
were all visited, and whether a continuation token remains. An empty page with
an unconsumed token is not an exhausted search.

*Execution faults.* Whether the source timed out internally, whether the run was
interrupted, and whether authorization filtered results out. Each of these means
the enumeration did not finish, and none of them is visible in an empty result
list.

*The denominator.* How many units the source claims exist and how many were
examined. Coverage with no denominator is not a fraction.

*Index state.* When the source's index was last updated for this query. This is
the fact almost no search API publishes, and its absence is the honest reason
most real negative claims are not supportable: an index that lags by an unknown
amount cannot establish that something is absent now.

An adapter that cannot determine one of these must say so rather than guess.
`SourceReading` has no default for any completeness fact precisely so that
guessing requires writing the guess down.

Transport is separated from interpretation. The same adapter serves a recorded
response from disk and a live response from a network client; only the transport
differs. That keeps the interpretation — the part that decides what coverage was
achieved — identical and testable without a network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence

from ..builder import SourceReading
from ..errors import ModelValidationError

ADAPTER_CONTRACT = "esio-read-only-adapter/1.0-candidate.1"


class AdapterError(ModelValidationError):
    """An adapter could not produce an honest reading."""


@dataclass(frozen=True)
class TransportResponse:
    """One page returned by a source, plus what the transport knows about it.

    `retrieved_at` is supplied by the caller rather than read from a clock, for
    the same reason the gate requires `evaluated_at`: evidence that timestamps
    itself cannot be replayed.
    """

    payload: Mapping[str, Any]
    retrieved_at: datetime
    status_code: int = 200
    truncated_by_rate_limit: bool = False
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.payload, Mapping):
            raise AdapterError("transport response payload must be a JSON object")
        if not isinstance(self.retrieved_at, datetime) or self.retrieved_at.tzinfo is None:
            raise AdapterError("transport response retrieved_at must be timezone-aware")
        if type(self.status_code) is not int:
            raise AdapterError("transport response status_code must be an integer")
        if not isinstance(self.truncated_by_rate_limit, bool):
            raise AdapterError("transport response truncated_by_rate_limit must be a boolean")
        if isinstance(self.errors, (str, bytes)) or not isinstance(self.errors, Sequence):
            raise AdapterError("transport response errors must be an array of strings")


class SearchTransport(Protocol):
    """Fetch one page of results. The only operation any adapter needs."""

    def fetch_page(self, *, query: str, page: int, per_page: int) -> TransportResponse:
        """Return the given page. Must not write, delete, or mutate anything."""


@dataclass
class ReadOnlyAdapter:
    """Base class carrying an adapter's declared identity.

    The identity is part of the evidence: a claim is bound to the exact adapter
    and immutable version that produced it, so that a later change in how a
    source is read cannot be mistaken for the same observation.
    """

    adapter_id: str
    adapter_version: str
    system: str
    locator: str
    accessible_population: str
    detection_assumptions: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in (
            "adapter_id",
            "adapter_version",
            "system",
            "locator",
            "accessible_population",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise AdapterError(f"adapter {name} must be a non-empty string")
        if not self.detection_assumptions:
            raise AdapterError(
                "an adapter must declare what it assumes about detection; a source "
                "whose detection assumptions are unstated cannot support a negative "
                "claim, because nobody can say what it would have failed to see"
            )

    def read(self, *args: Any, **kwargs: Any) -> SourceReading:  # pragma: no cover
        """Produce a reading. Signatures differ per source; all of them read."""

        raise NotImplementedError
