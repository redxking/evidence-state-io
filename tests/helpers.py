from __future__ import annotations

from copy import deepcopy
from typing import Any

from evidence_state_io.emptybench import seed_case_dicts, seed_profile_context
from evidence_state_io.gate import NegativeClaimRequest
from evidence_state_io.models import QueryScope
from evidence_state_io.profiles import TrustedProfileContext


def request_dict() -> dict[str, Any]:
    return deepcopy(seed_case_dicts()[0]["request"])


def request(**changes: Any) -> NegativeClaimRequest:
    data = request_dict()
    for key, value in changes.items():
        data[key] = value
    return NegativeClaimRequest.from_dict(data)


def trusted_context() -> TrustedProfileContext:
    return seed_profile_context()


def refresh_query_fingerprints(data: dict[str, Any]) -> str:
    """Rebind test-owned coverage and observations after a valid query mutation."""

    envelope = data["envelope"]
    fingerprint = QueryScope.from_dict(envelope["query"]).fingerprint()
    envelope["coverage_query_fingerprint"] = fingerprint
    for observation in envelope["source_observations"]:
        observation["query_fingerprint"] = fingerprint
    return fingerprint
