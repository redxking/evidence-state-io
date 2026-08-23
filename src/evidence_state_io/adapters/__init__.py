"""Read-only source adapters.

An adapter's entire job is to translate what a source actually returned into
coverage facts that can be checked. The interesting work is not fetching
results; it is reporting the ways in which the fetch was incomplete, because
those are exactly the facts a bare empty result hides.

Adapters here are read-only by construction. None of them writes, deletes, or
mutates anything at a source, and the contract has no method that could.
"""

from .base import (
    ADAPTER_CONTRACT,
    AdapterError,
    ReadOnlyAdapter,
    SearchTransport,
    TransportResponse,
)
from .github_search import (
    GITHUB_SEARCH_RESULT_CAP,
    GitHubSearchAdapter,
    RecordedTransport,
)

__all__ = [
    "ADAPTER_CONTRACT",
    "GITHUB_SEARCH_RESULT_CAP",
    "AdapterError",
    "GitHubSearchAdapter",
    "ReadOnlyAdapter",
    "RecordedTransport",
    "SearchTransport",
    "TransportResponse",
]
