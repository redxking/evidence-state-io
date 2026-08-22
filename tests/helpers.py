from __future__ import annotations

from copy import deepcopy
from typing import Any

from evidence_state_io.canonical import canonical_digest
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


COMPOSED_PRIMARY_ID = "github-public-repositories"


def _clock(minute: int) -> str:
    return f"2026-08-21T12:{minute:02d}:00Z"


def composed_fixture(mirrors: int = 1) -> tuple[dict[str, Any], TrustedProfileContext]:
    """Build a CORROBORATION request over ``1 + mirrors`` required sources.

    Each mirror is a distinct governed source with its own registry profile and
    a later late-arrival bound, so the composed claim binds on a horizon that
    no single source establishes.  A test that only ever exercised the primary
    source would therefore pass with the wrong horizon and be visibly wrong.

    The request and the trust context are built together because the mirror
    profiles change both the snapshot digest and the trust selection digest.
    """

    raw = deepcopy(trusted_context().to_dict())
    snapshot = raw["registry_snapshot"]["snapshot"]
    trust = raw["trust_selection"]
    template = deepcopy(snapshot["records"][0])

    data = request_dict()
    envelope = data["envelope"]
    envelope["schema_version"] = "1.1"
    envelope["query"]["composition"] = "CORROBORATION"

    primary_requirement = envelope["query"]["source_requirements"][0]
    primary_observation = envelope["source_observations"][0]
    primary_observation["coverage"] = deepcopy(envelope["coverage"])
    primary_observation["state"] = "ABSENT_WITHIN_SCOPE"
    primary_observation["matched_count"] = 0
    primary_observation["observed_at"] = _clock(4)
    primary_observation["valid_until"] = envelope["valid_until"]

    references: list[dict[str, Any]] = []
    for index in range(1, mirrors + 1):
        name = f"mirror-{index}"
        horizon = _clock(4 + index)

        record = deepcopy(template)
        profile = record["profile"]
        profile["profile_id"] = f"{name}-search-p0"
        profile["source"]["source_id"] = f"{name}-public-repositories"
        profile["source"]["system"] = f"{name}-search"
        profile["source"]["adapter_id"] = f"{name}-search-adapter"
        profile["finality"]["late_arrival_bound_seconds"] = 240 + 60 * index
        record["profile_digest"] = canonical_digest(profile)
        snapshot["records"].append(record)

        reference = {
            "registry_id": snapshot["registry_id"],
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
            "profile_digest": record["profile_digest"],
        }
        references.append(reference)

        requirement = deepcopy(primary_requirement)
        requirement["source_id"] = profile["source"]["source_id"]
        requirement["system"] = profile["source"]["system"]
        requirement["adapter_id"] = profile["source"]["adapter_id"]
        requirement["finality_horizon"] = horizon
        requirement["profile_ref"] = reference
        envelope["query"]["source_requirements"].append(requirement)

        observation = deepcopy(primary_observation)
        observation["source_id"] = requirement["source_id"]
        observation["descriptor"]["system"] = requirement["system"]
        observation["descriptor"]["adapter_id"] = requirement["adapter_id"]
        observation["descriptor"]["index_as_of"] = horizon
        observation["observed_at"] = horizon
        envelope["source_observations"].append(observation)

    snapshot["records"].sort(
        key=lambda item: (
            item["profile"]["profile_id"],
            item["profile"]["profile_version"],
            item["profile_digest"],
        )
    )
    raw["registry_snapshot"]["snapshot_digest"] = canonical_digest(snapshot)
    trust["snapshot_digest"] = raw["registry_snapshot"]["snapshot_digest"]
    trust["additional_selected_profile_references"] = references
    trust["trust_selection_digest"] = canonical_digest(
        {key: value for key, value in trust.items() if key != "trust_selection_digest"}
    )

    envelope["observed_at"] = _clock(4 + mirrors)
    data["evaluated_at"] = _clock(5 + mirrors)
    refresh_query_fingerprints(data)
    return data, TrustedProfileContext.from_dict(raw)


def mirror_observation(data: dict[str, Any], index: int = 1) -> dict[str, Any]:
    """Return the mirror observation dict so a test can weaken exactly one source."""

    source_id = f"mirror-{index}-public-repositories"
    for observation in data["envelope"]["source_observations"]:
        if observation["source_id"] == source_id:
            return observation
    raise AssertionError(f"no observation for {source_id}")
