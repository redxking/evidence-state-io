from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import unittest

from evidence_state_io.models import EvidenceEnvelope, ModelValidationError, parse_datetime
from evidence_state_io.profiles import (
    COVERAGE_FINALITY_PROFILE_SCHEMA,
    FINALITY_METHOD,
    PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
    PROFILE_TRUST_SELECTION_SCHEMA,
    BlindInterval,
    CoverageFinalityProfile,
    ProfileCoverage,
    ProfileIssueCode,
    ProfileRegistryRecord,
    ProfileRegistrySnapshot,
    ProfileRegistryStatus,
    ProfileTrustSelection,
    TrustedProfileContext,
    evaluate_profile_governance,
)

from tests.helpers import refresh_query_fingerprints, request_dict


def _profile_dict() -> dict[str, object]:
    return {
        "profile_schema": COVERAGE_FINALITY_PROFILE_SCHEMA,
        "profile_id": "github-public-search-negative-claims",
        "profile_version": "1.0.0",
        "source_owner_id": "github-search-owner",
        "approval_authority_id": "assurance-board",
        "issuer_id": "profile-publisher",
        "issued_at": "2026-08-20T00:00:00Z",
        "effective_at": "2026-08-21T00:00:00Z",
        "expires_at": "2026-08-22T00:00:00Z",
        "source": {
            "source_id": "github-public-repositories",
            "system": "github-search",
            "locator": "repositories/search",
            "adapter_id": "github-search-adapter",
            "adapter_version": "example-0.4",
            "authorization_context_id": "public-search-adapter-context",
            "accessible_population": "public-repositories-visible-to-adapter",
        },
        "applicability": {
            "target": "GitHub repository search",
            "predicate": "topic:evidence-state language:Python",
            "authorization_boundary": "public repositories visible to the adapter token",
            "required_exclusions": ["deleted repositories"],
            "detection_assumptions": [
                "repository is indexed by the declared search endpoint"
            ],
        },
        "coverage": {
            "population_basis": "EXACT",
            "population_units": 100,
            "pages_expected": 5,
            "partitions_expected": 2,
            "permission_limited": False,
            "retention_seconds": 86_400,
            "blind_intervals": [],
            "max_observation_age_seconds": 600,
            "max_index_age_seconds": 600,
        },
        "finality": {
            "method": FINALITY_METHOD,
            "late_arrival_bound_seconds": 240,
            "reopen_bound_seconds": 180,
        },
    }


def _profile() -> CoverageFinalityProfile:
    return CoverageFinalityProfile.from_dict(_profile_dict())


def _context(
    profile: CoverageFinalityProfile,
    *,
    status: ProfileRegistryStatus = ProfileRegistryStatus.ACTIVE,
    revocation_effective_at: str | None = None,
    revoked_at: str | None = None,
    revocation_reason_code: str | None = None,
    pinned_snapshot_digest: str | None = None,
) -> TrustedProfileContext:
    record = ProfileRegistryRecord(
        profile=profile,
        profile_digest=None,
        status=status,
        revoked_at=(
            None if revoked_at is None else parse_datetime(revoked_at, "revoked_at")
        ),
        revocation_effective_at=(
            None
            if revocation_effective_at is None
            else parse_datetime(revocation_effective_at, "revocation_effective_at")
        ),
        revocation_reason_code=revocation_reason_code,
    )
    snapshot = ProfileRegistrySnapshot(
        snapshot_schema=PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
        registry_id="local-assurance-registry",
        snapshot_id="snapshot-2026-08-21-001",
        snapshot_version="1",
        issuer_id="registry-publisher",
        as_of=parse_datetime("2026-08-21T12:00:00Z", "as_of"),
        next_update_at=parse_datetime("2026-08-21T13:00:00Z", "next_update_at"),
        records=(record,),
        snapshot_digest=None,
    )
    assert snapshot.snapshot_digest is not None
    trust = ProfileTrustSelection(
        trust_schema=PROFILE_TRUST_SELECTION_SCHEMA,
        registry_id=snapshot.registry_id,
        snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.snapshot_version,
        snapshot_digest=(
            snapshot.snapshot_digest
            if pinned_snapshot_digest is None
            else pinned_snapshot_digest
        ),
        trusted_snapshot_issuer_ids=("registry-publisher",),
        trusted_profile_issuer_ids=("profile-publisher",),
        trusted_approval_authority_ids=("assurance-board",),
        trust_selection_digest=None,
    )
    return TrustedProfileContext(snapshot=snapshot, trust_selection=trust)


def _envelope(profile: CoverageFinalityProfile | None) -> EvidenceEnvelope:
    data = request_dict()
    requirement = data["envelope"]["query"]["source_requirements"][0]
    if profile is not None:
        requirement["profile_ref"] = {
            "registry_id": "local-assurance-registry",
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "profile_digest": profile.profile_digest,
        }
    else:
        requirement.pop("profile_ref", None)
    refresh_query_fingerprints(data)
    return EvidenceEnvelope.from_dict(data["envelope"])


def _evaluated_at():
    return parse_datetime("2026-08-21T12:05:00Z", "evaluated_at")


class GovernedProfileModelTests(unittest.TestCase):
    def test_profile_round_trip_and_digest_are_deterministic(self) -> None:
        data = _profile_dict()
        data["applicability"]["required_exclusions"] = [
            "unindexed content",
            "deleted repositories",
        ]
        profile = CoverageFinalityProfile.from_dict(data)
        reparsed = CoverageFinalityProfile.from_dict(profile.to_dict())
        self.assertEqual(profile, reparsed)
        self.assertEqual(profile.profile_digest, reparsed.profile_digest)
        self.assertEqual(
            profile.applicability.required_exclusions,
            ("deleted repositories", "unindexed content"),
        )

    def test_context_round_trip_validates_both_integrity_digests(self) -> None:
        context = _context(_profile())
        reparsed = TrustedProfileContext.from_dict(context.to_dict())
        self.assertEqual(context, reparsed)
        self.assertEqual(context.context_digest, reparsed.context_digest)

    def test_profile_mutation_with_stale_record_digest_is_rejected(self) -> None:
        context_data = _context(_profile()).to_dict()
        context_data["registry_snapshot"]["snapshot"]["records"][0]["profile"][
            "profile_version"
        ] = "1.0.1"
        with self.assertRaisesRegex(ModelValidationError, "profile_digest"):
            TrustedProfileContext.from_dict(context_data)

    def test_snapshot_mutation_with_stale_snapshot_digest_is_rejected(self) -> None:
        data = _context(_profile()).snapshot.to_dict()
        data["snapshot"]["next_update_at"] = "2026-08-21T14:00:00Z"
        with self.assertRaisesRegex(ModelValidationError, "snapshot_digest"):
            ProfileRegistrySnapshot.from_dict(data)

    def test_trust_mutation_with_stale_selection_digest_is_rejected(self) -> None:
        data = _context(_profile()).trust_selection.to_dict()
        data["trusted_profile_issuer_ids"] = ["different-publisher"]
        with self.assertRaisesRegex(ModelValidationError, "trust_selection_digest"):
            ProfileTrustSelection.from_dict(data)

    def test_unknown_profile_field_is_rejected(self) -> None:
        data = _profile_dict()
        data["latest"] = True
        with self.assertRaisesRegex(ModelValidationError, "unknown fields: latest"):
            CoverageFinalityProfile.from_dict(data)

    def test_non_exact_profile_population_is_rejected_structurally(self) -> None:
        data = _profile_dict()
        data["coverage"]["population_basis"] = "ESTIMATED"
        with self.assertRaisesRegex(ModelValidationError, "must be EXACT"):
            CoverageFinalityProfile.from_dict(data)

    def test_duplicate_id_version_registry_records_are_rejected(self) -> None:
        profile = _profile()
        record = ProfileRegistryRecord(
            profile=profile,
            profile_digest=None,
            status=ProfileRegistryStatus.ACTIVE,
            revoked_at=None,
            revocation_effective_at=None,
            revocation_reason_code=None,
        )
        with self.assertRaisesRegex(ModelValidationError, "exactly once"):
            ProfileRegistrySnapshot(
                snapshot_schema=PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
                registry_id="local-assurance-registry",
                snapshot_id="snapshot-duplicate",
                snapshot_version="1",
                issuer_id="registry-publisher",
                as_of=parse_datetime("2026-08-21T12:00:00Z", "as_of"),
                next_update_at=parse_datetime(
                    "2026-08-21T13:00:00Z", "next_update_at"
                ),
                records=(record, record),
                snapshot_digest=None,
            )

    def test_active_record_rejects_revocation_metadata(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "ACTIVE"):
            ProfileRegistryRecord(
                profile=_profile(),
                profile_digest=None,
                status=ProfileRegistryStatus.ACTIVE,
                revoked_at=parse_datetime("2026-08-21T12:00:00Z", "revoked_at"),
                revocation_effective_at=None,
                revocation_reason_code=None,
            )


class GovernedProfileEvaluationTests(unittest.TestCase):
    def test_exact_profile_and_external_trust_context_pass(self) -> None:
        profile = _profile()
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), _context(profile)
        )
        self.assertTrue(assessment.meets_policy)
        self.assertEqual(assessment.issues, ())
        self.assertEqual(
            [item.profile_digest for item in assessment.resolved_profile_references],
            [profile.profile_digest],
        )

    def test_missing_context_and_reference_fail_closed(self) -> None:
        assessment = evaluate_profile_governance(
            _envelope(None), _evaluated_at(), None
        )
        self.assertEqual(
            [item.code for item in assessment.issues],
            [
                ProfileIssueCode.REGISTRY_SNAPSHOT_UNDECLARED,
                ProfileIssueCode.PROFILE_REFERENCE_UNDECLARED,
            ],
        )

    def test_trust_selection_must_pin_exact_snapshot_digest(self) -> None:
        profile = _profile()
        assessment = evaluate_profile_governance(
            _envelope(profile),
            _evaluated_at(),
            _context(profile, pinned_snapshot_digest="sha256:" + "0" * 64),
        )
        self.assertIn(
            ProfileIssueCode.REGISTRY_SNAPSHOT_DIGEST_MISMATCH,
            [item.code for item in assessment.issues],
        )

    def test_later_caller_selected_finality_horizon_is_rejected(self) -> None:
        profile = _profile()
        data = request_dict()
        requirement = data["envelope"]["query"]["source_requirements"][0]
        requirement["profile_ref"] = {
            "registry_id": "local-assurance-registry",
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "profile_digest": profile.profile_digest,
        }
        requirement["finality_horizon"] = "2026-08-21T12:05:00Z"
        refresh_query_fingerprints(data)
        assessment = evaluate_profile_governance(
            EvidenceEnvelope.from_dict(data["envelope"]),
            _evaluated_at(),
            _context(profile),
        )
        self.assertIn(
            ProfileIssueCode.FINALITY_HORIZON_PROFILE_MISMATCH,
            [item.code for item in assessment.issues],
        )

    def test_fixed_profile_denominator_must_match_runtime_coverage(self) -> None:
        profile = replace(
            _profile(),
            coverage=replace(_profile().coverage, population_units=101),
        )
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), _context(profile)
        )
        self.assertIn(
            ProfileIssueCode.PROFILE_COVERAGE_BASIS_MISMATCH,
            [item.code for item in assessment.issues],
        )

    def test_required_exclusions_are_a_subset_not_an_exact_list(self) -> None:
        profile = _profile()
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), _context(profile)
        )
        self.assertNotIn(
            ProfileIssueCode.PROFILE_QUERY_APPLICABILITY_MISMATCH,
            [item.code for item in assessment.issues],
        )

    def test_blind_interval_starting_at_inclusive_query_end_intersects(self) -> None:
        profile = _profile()
        interval = BlindInterval(
            start=parse_datetime("2026-08-21T12:00:00Z", "start"),
            end=parse_datetime("2026-08-21T12:01:00Z", "end"),
            reason_code="maintenance",
        )
        profile = replace(
            profile,
            coverage=replace(profile.coverage, blind_intervals=(interval,)),
        )
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), _context(profile)
        )
        self.assertIn(
            ProfileIssueCode.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY,
            [item.code for item in assessment.issues],
        )

    def test_blind_interval_ending_at_query_start_does_not_intersect(self) -> None:
        profile = _profile()
        interval = BlindInterval(
            start=parse_datetime("2026-08-20T23:00:00Z", "start"),
            end=parse_datetime("2026-08-21T00:00:00Z", "end"),
            reason_code="maintenance",
        )
        profile = replace(
            profile,
            coverage=replace(profile.coverage, blind_intervals=(interval,)),
        )
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), _context(profile)
        )
        self.assertNotIn(
            ProfileIssueCode.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY,
            [item.code for item in assessment.issues],
        )

    def test_retention_and_freshness_caps_are_profile_enforced(self) -> None:
        profile = _profile()
        constrained = ProfileCoverage(
            population_basis=profile.coverage.population_basis,
            population_units=profile.coverage.population_units,
            pages_expected=profile.coverage.pages_expected,
            partitions_expected=profile.coverage.partitions_expected,
            permission_limited=profile.coverage.permission_limited,
            retention_seconds=3_600,
            blind_intervals=(),
            max_observation_age_seconds=30,
            max_index_age_seconds=30,
        )
        profile = replace(profile, coverage=constrained)
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), _context(profile)
        )
        codes = [item.code for item in assessment.issues]
        self.assertIn(ProfileIssueCode.PROFILE_RETENTION_EXCEEDED, codes)
        self.assertIn(ProfileIssueCode.PROFILE_OBSERVATION_TOO_OLD, codes)
        self.assertIn(ProfileIssueCode.PROFILE_INDEX_TOO_OLD, codes)

    def test_profile_and_snapshot_validity_are_half_open(self) -> None:
        profile = replace(_profile(), expires_at=_evaluated_at())
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), _context(profile)
        )
        self.assertIn(
            ProfileIssueCode.PROFILE_EXPIRED,
            [item.code for item in assessment.issues],
        )

    def test_revocation_is_effective_inclusively(self) -> None:
        profile = _profile()
        context = _context(
            profile,
            status=ProfileRegistryStatus.REVOKED,
            revocation_effective_at="2026-08-21T12:00:00Z",
            revoked_at="2026-08-21T12:00:00Z",
            revocation_reason_code="coverage-contract-invalid",
        )
        assessment = evaluate_profile_governance(
            _envelope(profile), _evaluated_at(), context
        )
        self.assertIn(
            ProfileIssueCode.PROFILE_REVOKED,
            [item.code for item in assessment.issues],
        )

    def test_finality_arithmetic_overflow_is_structural_error(self) -> None:
        profile = _profile()
        profile = replace(
            profile,
            finality=replace(
                profile.finality,
                late_arrival_bound_seconds=10**20,
            ),
        )
        with self.assertRaisesRegex(ModelValidationError, "not representable"):
            evaluate_profile_governance(
                _envelope(profile), _evaluated_at(), _context(profile)
            )


if __name__ == "__main__":
    unittest.main()
