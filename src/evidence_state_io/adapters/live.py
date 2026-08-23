"""A live, read-only HTTPS transport for GitHub's public search API.

This is the only module in the package that opens a network connection, and it
is never imported by the core. The evaluator, the models, the gate, the
certificates, and the benchmarks stay network-free: importing
`evidence_state_io` does not import this file, and nothing here is reachable
unless a caller asks for it by name.

Read-only by construction. The transport issues `GET` and nothing else, and the
adapter contract it satisfies has no operation that could write.

Everything that could hide incompleteness is surfaced rather than swallowed. A
rate-limited response, an error status, and a transport failure each come back
as a fact on the response instead of as an empty result list, because an empty
list that means "we were throttled" is precisely the failure this project
exists to stop.

A token is read from the environment only if the caller opts in, is used solely
to raise the rate limit, and is never logged, stored, echoed, or included in any
evidence record.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base import AdapterError, TransportResponse

GITHUB_SEARCH_ENDPOINT = "https://api.github.com/search/repositories"
GITHUB_API_VERSION = "2022-11-28"

#: Environment variable consulted only when `use_token_from_environment` is set.
GITHUB_TOKEN_VARIABLE = "GITHUB_TOKEN"

#: Where a system trust store is commonly installed. Consulted only when the
#: interpreter's own default verify paths resolve to nothing, which is the
#: usual state of a freshly installed macOS Python.
_TRUST_STORE_CANDIDATES = (
    "/etc/ssl/cert.pem",
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/usr/local/etc/ca-certificates/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
)


def resolve_trust_store(explicit: str | None = None) -> ssl.SSLContext:
    """Return a verifying TLS context, or explain why one cannot be built.

    Certificate verification is never disabled and there is no option to
    disable it. An adapter that accepted an unverified connection would let
    anyone on the path supply the "no results were found" answer, which is the
    exact claim this project exists to make checkable.
    """

    if explicit is not None:
        if not os.path.isfile(explicit):
            raise AdapterError("the supplied CA bundle path does not exist")
        return ssl.create_default_context(cafile=explicit)

    context = ssl.create_default_context()
    if context.cert_store_stats().get("x509_ca", 0) > 0:
        return context

    for candidate in _TRUST_STORE_CANDIDATES:
        if os.path.isfile(candidate):
            return ssl.create_default_context(cafile=candidate)

    raise AdapterError(
        "no certificate authority bundle was found, so the connection cannot be "
        "verified. Install certificates for this interpreter, or set SSL_CERT_FILE, "
        "or pass ca_bundle. Verification is not optional: an unverified connection "
        "would let anyone on the path supply the absence being claimed."
    )


@dataclass
class GitHubHttpTransport:
    """Fetch one page of public repository search results over HTTPS.

    `retrieved_at` is supplied by the caller rather than read from a clock, so a
    recorded run and a live run produce comparable evidence and neither
    timestamps itself.
    """

    retrieved_at: datetime
    endpoint: str = GITHUB_SEARCH_ENDPOINT
    timeout_seconds: float = 20.0
    user_agent: str = "evidence-state-io"
    use_token_from_environment: bool = False
    ca_bundle: str | None = None
    recorded_pages: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.retrieved_at, datetime) or self.retrieved_at.tzinfo is None:
            raise AdapterError("retrieved_at must be a timezone-aware datetime")
        if not self.endpoint.startswith("https://"):
            raise AdapterError("the search endpoint must be https")
        self._context = resolve_trust_store(self.ca_bundle)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": self.user_agent,
        }
        if self.use_token_from_environment:
            token = os.environ.get(GITHUB_TOKEN_VARIABLE, "").strip()
            if token:
                # Used only to raise the rate limit. Never recorded, never
                # echoed, and never part of any evidence record.
                headers["Authorization"] = f"Bearer {token}"
        return headers

    def fetch_page(self, *, query: str, page: int, per_page: int) -> TransportResponse:
        url = (
            self.endpoint
            + "?"
            + urllib.parse.urlencode({"q": query, "page": page, "per_page": per_page})
        )
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds, context=self._context
            ) as response:
                body = response.read().decode("utf-8")
                remaining = response.headers.get("X-RateLimit-Remaining")
                status = response.status
        except urllib.error.HTTPError as exc:
            # A 403 with an exhausted budget is throttling, not absence.
            throttled = exc.code in (403, 429)
            payload: dict[str, Any] = {"items": [], "incomplete_results": True}
            return TransportResponse(
                payload=payload,
                retrieved_at=self.retrieved_at,
                status_code=exc.code,
                truncated_by_rate_limit=throttled,
                errors=(f"search returned HTTP {exc.code}",),
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", None)
            detail = f"{type(exc).__name__}: {reason}" if reason is not None else type(exc).__name__
            raise AdapterError(f"search transport failed: {detail}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AdapterError("search response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise AdapterError("search response was not a JSON object")

        self.recorded_pages.append(payload)
        exhausted_budget = remaining is not None and remaining.strip() == "0"
        return TransportResponse(
            payload=payload,
            retrieved_at=self.retrieved_at,
            status_code=status,
            truncated_by_rate_limit=exhausted_budget,
        )


__all__ = [
    "GITHUB_API_VERSION",
    "GITHUB_SEARCH_ENDPOINT",
    "GITHUB_TOKEN_VARIABLE",
    "GitHubHttpTransport",
    "resolve_trust_store",
]
