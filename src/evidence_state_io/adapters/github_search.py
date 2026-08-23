"""A read-only adapter over GitHub's public search API.

The adapter's real work is reporting what GitHub's search will not tell you.

*The 1000-result cap.* The API returns at most 1000 results however large
`total_count` is. A query matching 5000 repositories can be paged to exhaustion
and still have examined a fifth of them. Draining pagination is therefore not
the same as completing enumeration, and the two are reported separately.

*`incomplete_results`.* GitHub sets this when its own search timed out. The
result list looks exactly like a complete one. It is reported as a timeout,
which is what it is.

*Rate limiting.* Search is rate limited, and a limited run stops early with a
result list that again looks ordinary. It is reported as an interruption.

*Index state.* GitHub publishes no watermark saying when its index last ingested
for a given query. That is not an omission this adapter can repair, so it
reports no index time at all. Under a policy that requires one — which the P0
safety floor does — a negative claim about GitHub search will not be permitted,
and the remedy will say exactly why. That is the correct outcome. An adapter
that invented a timestamp here would be fabricating the single fact that
separates "the index does not contain it" from "it does not exist".

Nothing in this module writes to GitHub, and the transport contract has no
operation that could.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from ..builder import SourceReading
from ..models import PopulationBasis
from .base import AdapterError, ReadOnlyAdapter, SearchTransport, TransportResponse

#: GitHub returns at most this many results for a search, however many matched.
#: Documented behaviour, not a guess, and the reason draining pagination does
#: not imply complete enumeration.
GITHUB_SEARCH_RESULT_CAP = 1000

#: The API's maximum page size. Fewer requests means fewer chances to be rate
#: limited partway, which is why the default is the maximum.
GITHUB_SEARCH_MAX_PER_PAGE = 100


@dataclass
class RecordedTransport:
    """Replay recorded responses from disk. No network, no credentials.

    Recorded pages are the same evidence a live call produces, frozen. They make
    the interpretation testable, and they make a live adapter a change of
    transport rather than a change of design.
    """

    pages: tuple[TransportResponse, ...]

    @classmethod
    def from_file(cls, path: str | Path, *, retrieved_at: datetime) -> "RecordedTransport":
        """Load a recording: a JSON array of page payloads, in order."""

        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            # An adapter reports its own failures. Letting a filesystem error
            # escape would surface as something other than "this reading could
            # not be made", which is what the caller needs to know.
            raise AdapterError(f"the recording could not be read: {type(exc).__name__}") from exc
        if not isinstance(raw, list) or not raw:
            raise AdapterError("a recording must be a non-empty JSON array of page payloads")
        return cls(
            pages=tuple(TransportResponse(payload=page, retrieved_at=retrieved_at) for page in raw)
        )

    def fetch_page(self, *, query: str, page: int, per_page: int) -> TransportResponse:
        del query, per_page
        if page < 1 or page > len(self.pages):
            raise AdapterError(f"no recorded page {page}")
        return self.pages[page - 1]


@dataclass
class GitHubSearchAdapter(ReadOnlyAdapter):
    """Read GitHub search and report what the reading did and did not cover."""

    def __init__(
        self,
        transport: SearchTransport,
        *,
        source_id: str = "github-public-repositories",
        adapter_version: str = "1.0-candidate.1",
        locator: str = "search/repositories",
        accessible_population: str = "public-repositories-visible-to-the-search-api",
    ) -> None:
        super().__init__(
            adapter_id="github-search-adapter",
            adapter_version=adapter_version,
            system="github-search",
            locator=locator,
            accessible_population=accessible_population,
            detection_assumptions=(
                "the repository is indexed by GitHub's search endpoint",
                "GitHub's search index reflects an ingestion time it does not publish",
                "results are limited to what the supplied authorization can see",
            ),
        )
        self.transport = transport
        self.source_id = source_id

    def read(
        self,
        *,
        query: str,
        observed_at: datetime,
        max_pages: int = 10,
        per_page: int = GITHUB_SEARCH_MAX_PER_PAGE,
        **_unused: Any,
    ) -> SourceReading:
        """Page through a search and report the coverage it actually achieved."""

        if not isinstance(query, str) or not query.strip():
            raise AdapterError("query must be a non-empty string")
        if type(max_pages) is not int or max_pages < 1:
            raise AdapterError("max_pages must be a positive integer")
        if type(per_page) is not int or not 1 <= per_page <= GITHUB_SEARCH_MAX_PER_PAGE:
            raise AdapterError(f"per_page must be between 1 and {GITHUB_SEARCH_MAX_PER_PAGE}")

        examined = 0
        total_count: int | None = None
        timed_out = False
        interrupted = False
        errors: list[str] = []
        pages_examined = 0
        exhausted = False

        for page in range(1, max_pages + 1):
            try:
                response = self.transport.fetch_page(query=query, page=page, per_page=per_page)
            except AdapterError as exc:
                errors.append(str(exc))
                interrupted = True
                break

            pages_examined += 1
            errors.extend(response.errors)
            if response.status_code != 200:
                errors.append(f"search returned HTTP {response.status_code}")
                interrupted = True
                break
            if response.truncated_by_rate_limit:
                interrupted = True

            payload = response.payload
            items = payload.get("items")
            if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
                raise AdapterError("search response is missing an items array")
            if payload.get("incomplete_results") is True:
                # GitHub's own search timed out. The result list looks
                # identical to a complete one, so this is the only signal.
                timed_out = True

            reported = payload.get("total_count")
            if isinstance(reported, int) and not isinstance(reported, bool):
                total_count = reported if total_count is None else max(total_count, reported)

            examined += len(items)
            if response.truncated_by_rate_limit:
                break
            if len(items) < per_page:
                exhausted = True
                break

        return self._interpret(
            observed_at=observed_at,
            per_page=per_page,
            examined=examined,
            total_count=total_count,
            pages_examined=pages_examined,
            exhausted=exhausted,
            timed_out=timed_out,
            interrupted=interrupted,
            errors=tuple(errors),
        )

    def _interpret(
        self,
        *,
        observed_at: datetime,
        per_page: int,
        examined: int,
        total_count: int | None,
        pages_examined: int,
        exhausted: bool,
        timed_out: bool,
        interrupted: bool,
        errors: tuple[str, ...],
    ) -> SourceReading:
        """Turn a completed paging run into coverage facts.

        Separated from paging so the judgement calls are readable and testable
        on their own. Every branch here decides what the reading may claim, and
        the conservative branch is taken wherever the source is ambiguous.
        """

        if total_count is None:
            # Without a reported total there is no denominator, so no fraction
            # and no honest page count either.
            return SourceReading(
                source_id=self.source_id,
                matched_count=examined,
                examined_units=examined,
                population_basis=PopulationBasis.UNKNOWN,
                population_units=None,
                pages_examined=None,
                pages_expected=None,
                partitions_examined=1,
                partitions_expected=1,
                pagination_complete=False,
                continuation_token_present=not timed_out and not interrupted,
                partitions_complete=True,
                timed_out=timed_out,
                interrupted=interrupted,
                permission_limited=True,
                query_errors=errors,
                observed_at=observed_at,
                index_as_of=None,
            )
        if total_count > GITHUB_SEARCH_RESULT_CAP:
            # The cap makes complete enumeration impossible however many pages
            # are drained, and the denominator is real, so the shortfall is
            # reported as a fraction rather than hidden.
            basis = PopulationBasis.EXACT
            population_units = total_count
            complete = False
        else:
            basis = PopulationBasis.EXACT
            population_units = total_count
            complete = exhausted and examined >= total_count

        # How many pages the whole declared population would take, which is not
        # how many the API will serve once the cap applies. Reporting the real
        # denominator is what makes the shortfall visible.
        pages_expected = max(1, -(-total_count // per_page))

        return SourceReading(
            source_id=self.source_id,
            matched_count=examined,
            examined_units=examined,
            population_basis=basis,
            population_units=population_units,
            pages_examined=pages_examined,
            pages_expected=pages_expected,
            partitions_examined=1,
            partitions_expected=1,
            pagination_complete=complete,
            # A drained page budget leaves the next page unfetched, which is the
            # same situation a continuation token describes.
            continuation_token_present=not complete and not timed_out and not interrupted,
            partitions_complete=True,
            timed_out=timed_out,
            interrupted=interrupted,
            # Search returns only what the supplied authorization can see, and
            # it never says what it filtered out.
            permission_limited=True,
            query_errors=errors,
            observed_at=observed_at,
            # GitHub publishes no index watermark. Reporting none is the honest
            # answer and is why a strict policy will refuse the claim.
            index_as_of=None,
        )
