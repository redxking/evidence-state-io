#!/usr/bin/env python3
"""A real negative claim about a real system, in one file.

Your agent searched GitHub, got nothing back, and is about to tell someone that
no such repository exists. This is what happens when that claim is checked.

    python3 examples/quickstart.py           # recorded response, no network
    python3 examples/quickstart.py --live    # one read-only call to GitHub

The recorded run and the live run produce the same evidence. That is the point
of separating transport from interpretation: what the adapter concludes about
coverage does not depend on where the bytes came from.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from evidence_state_io.adapters import GitHubSearchAdapter, RecordedTransport
from evidence_state_io.builder import EvidenceBuilder
from evidence_state_io.gate import evaluate_negative_claim
from evidence_state_io.remedy import derive_remedy

UTC = timezone.utc
QUERY = "topic:evidence-state-io-no-such-topic-9f3a"
RECORDING = Path(__file__).resolve().parent / "recorded" / "github-search-zero-results.json"

# Every time is an input. Nothing in this library reads a clock, because a
# decision that cannot be replayed is not evidence.
OBSERVED_AT = datetime(2026, 8, 23, 12, 47, tzinfo=UTC)
EVALUATED_AT = OBSERVED_AT + timedelta(minutes=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make one read-only call to GitHub's public search API instead of replaying",
    )
    args = parser.parse_args()

    if args.live:
        from evidence_state_io.adapters.live import GitHubHttpTransport

        transport = GitHubHttpTransport(retrieved_at=OBSERVED_AT)
    else:
        transport = RecordedTransport.from_file(RECORDING, retrieved_at=OBSERVED_AT)

    # 1. Read the source, and record how complete the reading actually was.
    adapter = GitHubSearchAdapter(transport)
    reading = adapter.read(query=QUERY, observed_at=OBSERVED_AT, max_pages=1)

    print("What the source reported")
    print(f"  matches found        : {reading.matched_count}")
    print(f"  enumeration complete : {reading.pagination_complete}")
    print(f"  source timed out     : {reading.timed_out}")
    print(f"  run interrupted      : {reading.interrupted}")
    print(f"  index current as of  : {reading.index_as_of or 'not published by this source'}")
    print(f"  state these support  : {reading.derived_state().value}")

    # 2. Describe the scope the claim is about. This is the part a bare empty
    #    result never carries, and it is what makes the claim checkable.
    request = (
        EvidenceBuilder(
            target="GitHub public repository search",
            predicate=QUERY,
            authorization_boundary="public repositories visible to an unauthenticated search",
            authorization_context_id="public-unauthenticated-search",
            time_start=datetime(2026, 8, 1, tzinfo=UTC),
            time_end=datetime(2026, 8, 23, 12, 45, tzinfo=UTC),
            exclusions=("private repositories", "content GitHub has not indexed"),
        )
        .require_source(
            source_id=reading.source_id,
            system=adapter.system,
            locator=adapter.locator,
            adapter_id=adapter.adapter_id,
            adapter_version=adapter.adapter_version,
            accessible_population=adapter.accessible_population,
            detection_assumptions=adapter.detection_assumptions,
            finality_horizon=datetime(2026, 8, 23, 12, 46, tzinfo=UTC),
        )
        .record(reading)
        .request(
            subject="public repositories carrying that topic",
            evaluated_at=EVALUATED_AT,
        )
    )

    # 3. Ask whether that evidence supports the claim.
    decision = evaluate_negative_claim(request)

    print(f"\nDecision: {decision.decision}")
    if decision.allowed:
        print(f"\n{decision.qualified_claim}")
        return 0

    print("\nWhat would have to become true:")
    for item in derive_remedy(decision, request).items:
        print(f"  [{item.remedy_class.value}]")
        print(f"    {item.condition}")

    print(
        "\nThe last one is the one that matters. GitHub publishes no watermark\n"
        "saying when its index last ingested, so nothing here can distinguish\n"
        "'the index does not contain it' from 'it does not exist'. That is a\n"
        "property of the source, not a gap in this request, and inventing a\n"
        "timestamp to get past it would be fabricating the only fact that\n"
        "separates those two statements.\n"
        "\n"
        "A rejection does not mean the repository exists. It means absence was\n"
        "not established, which is a different and more honest thing to say."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
