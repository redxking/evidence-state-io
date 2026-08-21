from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import unittest

from evidence_state_io.models import (
    CoverageProfileReference,
    EvidenceEnvelope,
    ModelValidationError,
    QueryScope,
    parse_datetime,
)
from evidence_state_io.gate import NegativeClaimRequest, evaluate_negative_claim
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
        selected_profile_reference=CoverageProfileReference(
            registry_id=snapshot.registry_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_digest=profile.profile_digest,
        ),
        trusted_snapshot_issuer_ids=("registry-publisher",),
        trusted_profile_issuer_ids=("profile-publisher",),
        trusted_approval_authority_ids=("assurance-board",),
        trust_selection_digest=None,
    )
    return TrustedProfileContext(snapshot=snapshot, trust_selection=trust)


def _envelope(
    profile: CoverageFinalityProfile | None,
    data: dict[str, object] | None = None,
) -> EvidenceEnvelope:
    data = request_dict() if data is None else data
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


def _rebind_snapshot_context(
    context: TrustedProfileContext,
    snapshot: ProfileRegistrySnapshot,
) -> TrustedProfileContext:
    assert snapshot.snapshot_digest is not None
    trust = replace(
        context.trust_selection,
        registry_id=snapshot.registry_id,
        snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.snapshot_version,
        snapshot_digest=snapshot.snapshot_digest,
        trust_selection_digest=None,
    )
    return TrustedProfileContext(snapshot=snapshot, trust_selection=trust)


def _request_for_profile(
    profile: CoverageFinalityProfile,
    data: dict[str, object] | None = None,
) -> NegativeClaimRequest:
    data = request_dict() if data is None else data
    _envelope(profile, data)
    return NegativeClaimRequest.from_dict(data)


def _evaluated_at():
    return parse_datetime("2026-08-21T12:05:00Z", "evaluated_at")


def _hostile_semantics_envelope(
    profile: CoverageFinalityProfile,
    *,
    reference: CoverageProfileReference | None = None,
) -> EvidenceEnvelope:
    """Return valid input whose profile semantics would emit several issues."""
    data = request_dict()
    query = data["envelope"]["query"]
    requirement = query["source_requirements"][0]
    observation = data["envelope"]["source_observations"][0]
    selected = reference or CoverageProfileReference(
        registry_id="local-assurance-registry",
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        profile_digest=profile.profile_digest,
    )
    requirement["profile_ref"] = selected.to_dict()
    query["predicate"] = "hostile predicate outside the governed profile"
    requirement["adapter_version"] = "example-9.0"
    observation["descriptor"]["adapter_version"] = "example-9.0"
    requirement["finality_horizon"] = "2026-08-21T12:05:00Z"
    refresh_query_fingerprints(data)
    return EvidenceEnvelope.from_dict(data["envelope"])


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

    def test_unsupported_profile_snapshot_and_trust_contracts_reject(self) -> None:
        context = _context(_profile())
        for suffix in ("candidate.1", "candidate.999"):
            with self.subTest(contract="profile", suffix=suffix):
                profile_data = _profile_dict()
                profile_data["profile_schema"] = (
                    f"esio-coverage-finality-profile/1.0-{suffix}"
                )
                with self.assertRaisesRegex(ModelValidationError, "profile_schema"):
                    CoverageFinalityProfile.from_dict(profile_data)

            with self.subTest(contract="snapshot", suffix=suffix):
                snapshot_data = context.snapshot.to_dict()
                snapshot_data["snapshot"]["snapshot_schema"] = (
                    f"esio-profile-registry-snapshot/1.0-{suffix}"
                )
                with self.assertRaisesRegex(ModelValidationError, "snapshot_schema"):
                    ProfileRegistrySnapshot.from_dict(snapshot_data)

            with self.subTest(contract="trust", suffix=suffix):
                trust_data = context.trust_selection.to_dict()
                trust_data["trust_schema"] = (
                    f"esio-profile-trust-selection/1.0-{suffix}"
                )
                with self.assertRaisesRegex(ModelValidationError, "trust_schema"):
                    ProfileTrustSelection.from_dict(trust_data)

    def test_non_exact_profile_population_is_rejected_structurally(self) -> None:
        data = _profile_dict()
        data["coverage"]["population_basis"] = "ESTIMATED"
        with self.assertRaisesRegex(ModelValidationError, "must be EXACT"):
            CoverageFinalityProfile.from_dict(data)

    def test_floating_profile_and_adapter_versions_are_rejected(self) -> None:
        for field_path, value in (
            (("profile_version",), "latest"),
            (("source", "adapter_version"), "1.*"),
            (("source", "adapter_version"), ">=1"),
            (("source", "adapter_version"), "main"),
            (("source", "adapter_version"), "release"),
            (("source", "adapter_version"), "default"),
            (("source", "adapter_version"), "prod"),
            (("source", "adapter_version"), "lts"),
            (("source", "adapter_version"), "rolling"),
            (("source", "adapter_version"), "1-2"),
            (("source", "adapter_version"), "1 || 2"),
            (("source", "adapter_version"), "!=1.2"),
            (("source", "adapter_version"), "[1.0,2.0)"),
            (("source", "adapter_version"), "git:deadbee"),
        ):
            with self.subTest(field_path=field_path, value=value):
                data = _profile_dict()
                target = data
                for key in field_path[:-1]:
                    target = target[key]
                target[field_path[-1]] = value
                with self.assertRaisesRegex(ModelValidationError, "immutable version"):
                    CoverageFinalityProfile.from_dict(data)

    def test_request_and_observation_reject_floating_adapter_version(self) -> None:
        data = request_dict()
        data["envelope"]["query"]["source_requirements"][0][
            "adapter_version"
        ] = "latest"
        data["envelope"]["source_observations"][0]["descriptor"][
            "adapter_version"
        ] = "latest"
        with self.assertRaisesRegex(ModelValidationError, "immutable version"):
            QueryScope.from_dict(data["envelope"]["query"])

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

    def test_snapshot_cannot_contain_a_profile_issued_after_as_of(self) -> None:
        profile = replace(
            _profile(),
            issued_at=parse_datetime("2026-08-21T12:00:00.000001Z", "issued_at"),
            effective_at=parse_datetime("2026-08-21T12:00:00.000001Z", "effective_at"),
        )
        record = ProfileRegistryRecord(
            profile=profile,
            profile_digest=None,
            status=ProfileRegistryStatus.ACTIVE,
            revoked_at=None,
            revocation_effective_at=None,
            revocation_reason_code=None,
        )
        with self.assertRaisesRegex(ModelValidationError, "issued_at <= snapshot.as_of"):
            ProfileRegistrySnapshot(
                snapshot_schema=PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
                registry_id="local-assurance-registry",
                snapshot_id="snapshot-inconsistent",
                snapshot_version="1",
                issuer_id="registry-publisher",
                as_of=parse_datetime("2026-08-21T12:00:00Z", "as_of"),
                next_update_at=parse_datetime("2026-08-21T13:00:00Z", "next"),
                records=(record,),
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

    def test_explicit_null_profile_reference_uses_fail_closed_transition(self) -> None:
        profile = _profile()
        data = request_dict()
        data["envelope"]["query"]["source_requirements"][0]["profile_ref"] = None
        refresh_query_fingerprints(data)
        assessment = evaluate_profile_governance(
            EvidenceEnvelope.from_dict(data["envelope"]),
            _evaluated_at(),
            _context(profile),
        )
        self.assertEqual(
            [item.code for item in assessment.issues],
            [ProfileIssueCode.PROFILE_REFERENCE_UNDECLARED],
        )

    def test_producer_request_cannot_embed_governance_context(self) -> None:
        data = request_dict()
        data["trusted_profile_context"] = _context(_profile()).to_dict()
        with self.assertRaisesRegex(ModelValidationError, "unknown fields"):
            NegativeClaimRequest.from_dict(data)

    def test_snapshot_trust_failures_short_circuit_record_resolution(self) -> None:
        profile = _profile()
        envelope = _envelope(profile)
        base = _context(profile)
        variants = (
            (
                replace(
                    base.trust_selection,
                    snapshot_id="different-snapshot",
                    trust_selection_digest=None,
                ),
                _evaluated_at(),
                ProfileIssueCode.REGISTRY_SNAPSHOT_IDENTITY_MISMATCH,
            ),
            (
                replace(
                    base.trust_selection,
                    trusted_snapshot_issuer_ids=("different-registry-publisher",),
                    trust_selection_digest=None,
                ),
                _evaluated_at(),
                ProfileIssueCode.REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED,
            ),
            (
                base.trust_selection,
                parse_datetime("2026-08-21T11:59:59.999999Z", "evaluated_at"),
                ProfileIssueCode.REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE,
            ),
            (
                base.trust_selection,
                parse_datetime("2026-08-21T13:00:00Z", "evaluated_at"),
                ProfileIssueCode.REGISTRY_SNAPSHOT_EXPIRED,
            ),
        )
        for trust, evaluated_at, expected in variants:
            with self.subTest(expected=expected):
                assessment = evaluate_profile_governance(
                    envelope,
                    evaluated_at,
                    TrustedProfileContext(
                        snapshot=base.snapshot,
                        trust_selection=trust,
                    ),
                )
                self.assertEqual(
                    [item.code for item in assessment.issues],
                    [expected],
                )
                self.assertEqual(assessment.resolved_profile_references, ())

    def test_profile_resolution_and_trust_failures_do_not_use_semantics(self) -> None:
        profile = _profile()
        base = _context(profile)
        empty_snapshot = replace(
            base.snapshot,
            records=(),
            snapshot_digest=None,
        )
        not_found_context = _rebind_snapshot_context(base, empty_snapshot)
        untrusted_authority = TrustedProfileContext(
            snapshot=base.snapshot,
            trust_selection=replace(
                base.trust_selection,
                trusted_approval_authority_ids=("different-authority",),
                trust_selection_digest=None,
            ),
        )
        future_profile = replace(
            profile,
            effective_at=parse_datetime("2026-08-21T12:10:00Z", "effective_at"),
        )
        variants = (
            (
                _envelope(profile),
                not_found_context,
                ProfileIssueCode.PROFILE_NOT_FOUND,
            ),
            (
                _envelope(profile),
                untrusted_authority,
                ProfileIssueCode.PROFILE_AUTHORITY_UNTRUSTED,
            ),
            (
                _envelope(future_profile),
                _context(future_profile),
                ProfileIssueCode.PROFILE_NOT_YET_EFFECTIVE,
            ),
        )
        for envelope, context, expected in variants:
            with self.subTest(expected=expected):
                assessment = evaluate_profile_governance(
                    envelope,
                    _evaluated_at(),
                    context,
                )
                self.assertEqual(
                    [item.code for item in assessment.issues],
                    [expected],
                )
                self.assertEqual(assessment.resolved_profile_references, ())

    def test_every_pre_semantics_failure_short_circuits_hostile_content(self) -> None:
        profile = _profile()
        base = _context(profile)
        empty_snapshot = replace(base.snapshot, records=(), snapshot_digest=None)
        not_found = _rebind_snapshot_context(base, empty_snapshot)

        wrong_reference = CoverageProfileReference(
            registry_id=base.snapshot.registry_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_digest="sha256:" + "0" * 64,
        )
        wrong_digest_context = TrustedProfileContext(
            snapshot=base.snapshot,
            trust_selection=replace(
                base.trust_selection,
                selected_profile_reference=wrong_reference,
                trust_selection_digest=None,
            ),
        )
        future_profile = replace(
            profile,
            effective_at=parse_datetime("2026-08-21T12:10:00Z", "effective_at"),
        )
        expired_profile = replace(
            profile,
            expires_at=parse_datetime("2026-08-21T12:05:00Z", "expires_at"),
        )
        revoked = _context(
            profile,
            status=ProfileRegistryStatus.REVOKED,
            revocation_effective_at="2026-08-21T11:58:00Z",
            revoked_at="2026-08-21T11:59:00Z",
            revocation_reason_code="profile_withdrawn",
        )

        cases = (
            (
                _hostile_semantics_envelope(profile),
                TrustedProfileContext(
                    snapshot=base.snapshot,
                    trust_selection=replace(
                        base.trust_selection,
                        snapshot_id="different-snapshot",
                        trust_selection_digest=None,
                    ),
                ),
                _evaluated_at(),
                ProfileIssueCode.REGISTRY_SNAPSHOT_IDENTITY_MISMATCH,
            ),
            (
                _hostile_semantics_envelope(profile),
                _context(profile, pinned_snapshot_digest="sha256:" + "0" * 64),
                _evaluated_at(),
                ProfileIssueCode.REGISTRY_SNAPSHOT_DIGEST_MISMATCH,
            ),
            (
                _hostile_semantics_envelope(profile),
                TrustedProfileContext(
                    snapshot=base.snapshot,
                    trust_selection=replace(
                        base.trust_selection,
                        trusted_snapshot_issuer_ids=("different-publisher",),
                        trust_selection_digest=None,
                    ),
                ),
                _evaluated_at(),
                ProfileIssueCode.REGISTRY_SNAPSHOT_ISSUER_UNTRUSTED,
            ),
            (
                _hostile_semantics_envelope(profile),
                base,
                parse_datetime("2026-08-21T11:59:59.999999Z", "evaluated_at"),
                ProfileIssueCode.REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE,
            ),
            (
                _hostile_semantics_envelope(profile),
                base,
                parse_datetime("2026-08-21T13:00:00Z", "evaluated_at"),
                ProfileIssueCode.REGISTRY_SNAPSHOT_EXPIRED,
            ),
            (
                _hostile_semantics_envelope(profile),
                not_found,
                _evaluated_at(),
                ProfileIssueCode.PROFILE_NOT_FOUND,
            ),
            (
                _hostile_semantics_envelope(profile, reference=wrong_reference),
                wrong_digest_context,
                _evaluated_at(),
                ProfileIssueCode.PROFILE_DIGEST_MISMATCH,
            ),
            (
                _hostile_semantics_envelope(profile),
                TrustedProfileContext(
                    snapshot=base.snapshot,
                    trust_selection=replace(
                        base.trust_selection,
                        trusted_profile_issuer_ids=("different-publisher",),
                        trust_selection_digest=None,
                    ),
                ),
                _evaluated_at(),
                ProfileIssueCode.PROFILE_ISSUER_UNTRUSTED,
            ),
            (
                _hostile_semantics_envelope(profile),
                TrustedProfileContext(
                    snapshot=base.snapshot,
                    trust_selection=replace(
                        base.trust_selection,
                        trusted_approval_authority_ids=("different-authority",),
                        trust_selection_digest=None,
                    ),
                ),
                _evaluated_at(),
                ProfileIssueCode.PROFILE_AUTHORITY_UNTRUSTED,
            ),
            (
                _hostile_semantics_envelope(future_profile),
                _context(future_profile),
                _evaluated_at(),
                ProfileIssueCode.PROFILE_NOT_YET_EFFECTIVE,
            ),
            (
                _hostile_semantics_envelope(expired_profile),
                _context(expired_profile),
                _evaluated_at(),
                ProfileIssueCode.PROFILE_EXPIRED,
            ),
            (
                _hostile_semantics_envelope(profile),
                revoked,
                _evaluated_at(),
                ProfileIssueCode.PROFILE_REVOKED,
            ),
        )
        for envelope, context, evaluated_at, expected in cases:
            with self.subTest(expected=expected):
                assessment = evaluate_profile_governance(
                    envelope,
                    evaluated_at,
                    context,
                )
                self.assertEqual(
                    [item.code for item in assessment.issues],
                    [expected],
                )
                self.assertEqual(assessment.resolved_profile_references, ())

    def test_selected_reference_digest_must_match_exact_registry_record(self) -> None:
        profile = _profile()
        context = _context(profile)
        wrong_reference = CoverageProfileReference(
            registry_id=context.snapshot.registry_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_digest="sha256:" + "0" * 64,
        )
        trust = replace(
            context.trust_selection,
            selected_profile_reference=wrong_reference,
            trust_selection_digest=None,
        )
        data = request_dict()
        data["envelope"]["query"]["source_requirements"][0][
            "profile_ref"
        ] = wrong_reference.to_dict()
        refresh_query_fingerprints(data)
        assessment = evaluate_profile_governance(
            EvidenceEnvelope.from_dict(data["envelope"]),
            _evaluated_at(),
            TrustedProfileContext(
                snapshot=context.snapshot,
                trust_selection=trust,
            ),
        )
        self.assertEqual(
            [item.code for item in assessment.issues],
            [ProfileIssueCode.PROFILE_DIGEST_MISMATCH],
        )
        self.assertEqual(assessment.resolved_profile_references, ())

    def test_exact_profile_applicability_mutations_reject(self) -> None:
        profile = _profile()
        mutations = (
            (
                lambda data: data["envelope"]["query"]["source_requirements"][0].update(
                    system="different-search-system"
                ),
                ProfileIssueCode.PROFILE_SOURCE_MISMATCH,
            ),
            (
                lambda data: (
                    data["envelope"]["query"]["source_requirements"][0].update(
                        source_id="different-source"
                    ),
                    data["envelope"]["source_observations"][0].update(
                        source_id="different-source"
                    ),
                ),
                ProfileIssueCode.PROFILE_SOURCE_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"]["source_requirements"][0].update(
                    locator="different/search/locator"
                ),
                ProfileIssueCode.PROFILE_SOURCE_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"]["source_requirements"][0].update(
                    adapter_version="other-9.9"
                ),
                ProfileIssueCode.PROFILE_ADAPTER_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"]["source_requirements"][0].update(
                    adapter_id="other-adapter"
                ),
                ProfileIssueCode.PROFILE_ADAPTER_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"].update(
                    target="Different repository search"
                ),
                ProfileIssueCode.PROFILE_QUERY_APPLICABILITY_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"].update(
                    predicate="topic:other language:Python"
                ),
                ProfileIssueCode.PROFILE_QUERY_APPLICABILITY_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"]["source_requirements"][0].update(
                    detection_assumptions=["different indexed population assumption"]
                ),
                ProfileIssueCode.PROFILE_DETECTION_ASSUMPTIONS_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"].update(
                    exclusions=["unindexed content"]
                ),
                ProfileIssueCode.PROFILE_QUERY_APPLICABILITY_MISMATCH,
            ),
            (
                lambda data: (
                    data["envelope"]["query"].update(
                        authorization_context_id="other-context"
                    ),
                    data["envelope"]["query"]["source_requirements"][0].update(
                        authorization_context_id="other-context"
                    ),
                    data["envelope"]["source_observations"][0].update(
                        authorization_context_id="other-context"
                    ),
                ),
                ProfileIssueCode.PROFILE_AUTHORIZATION_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["query"].update(
                    authorization_boundary="different public authorization boundary"
                ),
                ProfileIssueCode.PROFILE_AUTHORIZATION_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["coverage"].update(
                    permission_limited=True
                ),
                ProfileIssueCode.PROFILE_AUTHORIZATION_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["source_observations"][0].update(
                    authorization_context_id="other-context"
                ),
                ProfileIssueCode.PROFILE_AUTHORIZATION_MISMATCH,
            ),
            (
                lambda data: (
                    data["envelope"]["query"]["source_requirements"][0].update(
                        accessible_population="different bounded population"
                    ),
                    data["envelope"]["source_observations"][0].update(
                        accessible_population="different bounded population"
                    ),
                ),
                ProfileIssueCode.PROFILE_POPULATION_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["source_observations"][0][
                    "descriptor"
                ].update(system="different-search-system"),
                ProfileIssueCode.PROFILE_SOURCE_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["source_observations"][0][
                    "descriptor"
                ].update(locator="different/search/locator"),
                ProfileIssueCode.PROFILE_SOURCE_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["source_observations"][0][
                    "descriptor"
                ].update(adapter_id="other-adapter"),
                ProfileIssueCode.PROFILE_ADAPTER_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["source_observations"][0][
                    "descriptor"
                ].update(adapter_version="other-9.9"),
                ProfileIssueCode.PROFILE_ADAPTER_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["coverage"].update(
                    pages_examined=6,
                    pages_expected=6,
                ),
                ProfileIssueCode.PROFILE_COVERAGE_BASIS_MISMATCH,
            ),
            (
                lambda data: data["envelope"]["coverage"].update(
                    partitions_examined=3,
                    partitions_expected=3,
                ),
                ProfileIssueCode.PROFILE_COVERAGE_BASIS_MISMATCH,
            ),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                data = request_dict()
                mutate(data)
                assessment = evaluate_profile_governance(
                    _envelope(profile, data),
                    _evaluated_at(),
                    _context(profile),
                )
                self.assertIn(expected, [item.code for item in assessment.issues])

    def test_retention_boundary_is_exact_to_one_microsecond(self) -> None:
        base = _profile()
        profile = replace(
            base,
            coverage=replace(base.coverage, retention_seconds=43_440),
        )
        starts = (
            ("2026-08-20T23:59:59.999999Z", True),
            ("2026-08-21T00:00:00Z", False),
            ("2026-08-21T00:00:00.000001Z", False),
        )
        for start, rejected in starts:
            with self.subTest(start=start):
                data = request_dict()
                data["envelope"]["query"]["time_start"] = start
                assessment = evaluate_profile_governance(
                    _envelope(profile, data),
                    _evaluated_at(),
                    _context(profile),
                )
                self.assertEqual(
                    ProfileIssueCode.PROFILE_RETENTION_EXCEEDED
                    in [item.code for item in assessment.issues],
                    rejected,
                )

    def test_blind_interval_boundaries_are_exact_to_one_microsecond(self) -> None:
        base = _profile()
        cases = (
            (
                "starts-before-query-end",
                "2026-08-21T11:59:59.999999Z",
                "2026-08-21T12:01:00Z",
                True,
            ),
            (
                "starts-at-query-end",
                "2026-08-21T12:00:00Z",
                "2026-08-21T12:01:00Z",
                True,
            ),
            (
                "starts-after-query-end",
                "2026-08-21T12:00:00.000001Z",
                "2026-08-21T12:01:00Z",
                False,
            ),
            (
                "ends-before-query-start",
                "2026-08-20T23:00:00Z",
                "2026-08-20T23:59:59.999999Z",
                False,
            ),
            (
                "ends-at-query-start",
                "2026-08-20T23:00:00Z",
                "2026-08-21T00:00:00Z",
                False,
            ),
            (
                "ends-after-query-start",
                "2026-08-20T23:00:00Z",
                "2026-08-21T00:00:00.000001Z",
                True,
            ),
        )
        for name, start, end, intersects in cases:
            with self.subTest(name=name):
                interval = BlindInterval(
                    start=parse_datetime(start, "start"),
                    end=parse_datetime(end, "end"),
                    reason_code="boundary-test",
                )
                profile = replace(
                    base,
                    coverage=replace(base.coverage, blind_intervals=(interval,)),
                )
                assessment = evaluate_profile_governance(
                    _envelope(profile),
                    _evaluated_at(),
                    _context(profile),
                )
                self.assertEqual(
                    ProfileIssueCode.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY
                    in [item.code for item in assessment.issues],
                    intersects,
                )

    def test_profile_freshness_boundaries_are_exact_to_one_microsecond(self) -> None:
        base = _profile()
        variants = (
            ("observation", replace(base.coverage, max_observation_age_seconds=60)),
            ("index", replace(base.coverage, max_index_age_seconds=60)),
        )
        times = (
            ("2026-08-21T12:04:59.999999Z", False),
            ("2026-08-21T12:05:00Z", False),
            ("2026-08-21T12:05:00.000001Z", True),
        )
        for dimension, coverage in variants:
            profile = replace(base, coverage=coverage)
            expected = (
                ProfileIssueCode.PROFILE_OBSERVATION_TOO_OLD
                if dimension == "observation"
                else ProfileIssueCode.PROFILE_INDEX_TOO_OLD
            )
            for timestamp, rejected in times:
                with self.subTest(dimension=dimension, timestamp=timestamp):
                    assessment = evaluate_profile_governance(
                        _envelope(profile),
                        parse_datetime(timestamp, "evaluated_at"),
                        _context(profile),
                    )
                    self.assertEqual(
                        expected in [item.code for item in assessment.issues],
                        rejected,
                    )

    def test_derived_horizon_boundary_requires_exact_equality(self) -> None:
        profile = _profile()
        horizons = (
            ("2026-08-21T12:03:59.999999Z", True),
            ("2026-08-21T12:04:00Z", False),
            ("2026-08-21T12:04:00.000001Z", True),
        )
        for horizon, rejected in horizons:
            with self.subTest(horizon=horizon):
                data = request_dict()
                data["envelope"]["query"]["source_requirements"][0][
                    "finality_horizon"
                ] = horizon
                assessment = evaluate_profile_governance(
                    _envelope(profile, data),
                    _evaluated_at(),
                    _context(profile),
                )
                self.assertEqual(
                    ProfileIssueCode.FINALITY_HORIZON_PROFILE_MISMATCH
                    in [item.code for item in assessment.issues],
                    rejected,
                )

    def test_profile_and_snapshot_validity_boundaries_are_half_open(self) -> None:
        base = _profile()
        profile = replace(
            base,
            effective_at=parse_datetime("2026-08-21T12:00:00Z", "effective_at"),
            expires_at=parse_datetime("2026-08-21T12:10:00Z", "expires_at"),
        )
        profile_context = _context(profile)
        earlier_snapshot = replace(
            profile_context.snapshot,
            as_of=parse_datetime("2026-08-21T11:50:00Z", "as_of"),
            snapshot_digest=None,
        )
        profile_context = _rebind_snapshot_context(
            profile_context,
            earlier_snapshot,
        )
        profile_cases = (
            ("2026-08-21T11:59:59.999999Z", ProfileIssueCode.PROFILE_NOT_YET_EFFECTIVE),
            ("2026-08-21T12:00:00Z", None),
            ("2026-08-21T12:09:59.999999Z", None),
            ("2026-08-21T12:10:00Z", ProfileIssueCode.PROFILE_EXPIRED),
            ("2026-08-21T12:10:00.000001Z", ProfileIssueCode.PROFILE_EXPIRED),
        )
        for timestamp, expected in profile_cases:
            with self.subTest(profile_time=timestamp):
                assessment = evaluate_profile_governance(
                    _envelope(profile),
                    parse_datetime(timestamp, "evaluated_at"),
                    profile_context,
                )
                codes = [item.code for item in assessment.issues]
                if expected is None:
                    self.assertNotIn(ProfileIssueCode.PROFILE_NOT_YET_EFFECTIVE, codes)
                    self.assertNotIn(ProfileIssueCode.PROFILE_EXPIRED, codes)
                else:
                    self.assertIn(expected, codes)

        snapshot_context = _context(base)
        snapshot_cases = (
            ("2026-08-21T11:59:59.999999Z", ProfileIssueCode.REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE),
            ("2026-08-21T12:00:00Z", None),
            ("2026-08-21T12:59:59.999999Z", None),
            ("2026-08-21T13:00:00Z", ProfileIssueCode.REGISTRY_SNAPSHOT_EXPIRED),
            ("2026-08-21T13:00:00.000001Z", ProfileIssueCode.REGISTRY_SNAPSHOT_EXPIRED),
        )
        for timestamp, expected in snapshot_cases:
            with self.subTest(snapshot_time=timestamp):
                assessment = evaluate_profile_governance(
                    _envelope(base),
                    parse_datetime(timestamp, "evaluated_at"),
                    snapshot_context,
                )
                codes = [item.code for item in assessment.issues]
                if expected is None:
                    self.assertNotIn(ProfileIssueCode.REGISTRY_SNAPSHOT_NOT_YET_EFFECTIVE, codes)
                    self.assertNotIn(ProfileIssueCode.REGISTRY_SNAPSHOT_EXPIRED, codes)
                else:
                    self.assertIn(expected, codes)

    def test_composite_digest_changes_for_request_profile_registry_and_trust(self) -> None:
        profile = _profile()
        request = _request_for_profile(profile)
        context = _context(profile)
        baseline = evaluate_negative_claim(request, context).input_digest

        query_data = request_dict()
        query_data["envelope"]["query"]["exclusions"].append(
            "archived repositories"
        )
        query_request = _request_for_profile(profile, query_data)

        changed_profile = replace(
            profile,
            coverage=replace(profile.coverage, max_index_age_seconds=601),
        )
        profile_request = _request_for_profile(changed_profile)
        profile_context = _context(changed_profile)

        changed_snapshot = replace(
            context.snapshot,
            snapshot_id="snapshot-2026-08-21-002",
            snapshot_digest=None,
        )
        snapshot_context = _rebind_snapshot_context(context, changed_snapshot)

        trust_context = TrustedProfileContext(
            snapshot=context.snapshot,
            trust_selection=replace(
                context.trust_selection,
                trusted_profile_issuer_ids=(
                    *context.trust_selection.trusted_profile_issuer_ids,
                    "alternate-profile-publisher",
                ),
                trust_selection_digest=None,
            ),
        )
        revoked_record = ProfileRegistryRecord(
            profile=profile,
            profile_digest=None,
            status=ProfileRegistryStatus.REVOKED,
            revoked_at=parse_datetime("2026-08-21T12:00:00Z", "revoked_at"),
            revocation_effective_at=parse_datetime(
                "2026-08-21T11:59:00Z", "revocation_effective_at"
            ),
            revocation_reason_code="superseded",
        )
        revoked_snapshot = replace(
            context.snapshot,
            records=(revoked_record,),
            snapshot_digest=None,
        )
        revoked_context = _rebind_snapshot_context(context, revoked_snapshot)
        policy_request = replace(
            request,
            policy=replace(request.policy, max_observation_age_seconds=601),
        )
        observation_data = request.to_dict()
        observation_data["envelope"]["source_observations"][0]["descriptor"][
            "index_as_of"
        ] = "2026-08-21T12:03:59.999999Z"
        observation_request = NegativeClaimRequest.from_dict(observation_data)
        evaluated_request = replace(
            request,
            evaluated_at=parse_datetime(
                "2026-08-21T12:05:00.000001Z", "evaluated_at"
            ),
        )
        variants = (
            evaluate_negative_claim(query_request, context).input_digest,
            evaluate_negative_claim(profile_request, profile_context).input_digest,
            evaluate_negative_claim(request, snapshot_context).input_digest,
            evaluate_negative_claim(request, trust_context).input_digest,
            evaluate_negative_claim(request, revoked_context).input_digest,
            evaluate_negative_claim(policy_request, context).input_digest,
            evaluate_negative_claim(observation_request, context).input_digest,
            evaluate_negative_claim(evaluated_request, context).input_digest,
        )
        self.assertTrue(all(item != baseline for item in variants))
        self.assertEqual(len(set(variants)), len(variants))

    def test_composite_digest_normalizes_order_and_equivalent_offsets(self) -> None:
        profile = _profile()
        request = _request_for_profile(profile)
        context = _context(profile)
        reordered_a = replace(
            context.trust_selection,
            trusted_profile_issuer_ids=("z-publisher", "profile-publisher"),
            trust_selection_digest=None,
        )
        reordered_b = replace(
            context.trust_selection,
            trusted_profile_issuer_ids=("profile-publisher", "z-publisher"),
            trust_selection_digest=None,
        )
        context_a = TrustedProfileContext(
            snapshot=context.snapshot,
            trust_selection=reordered_a,
        )
        context_b = TrustedProfileContext(
            snapshot=context.snapshot,
            trust_selection=reordered_b,
        )
        self.assertEqual(
            evaluate_negative_claim(request, context_a).input_digest,
            evaluate_negative_claim(request, context_b).input_digest,
        )

        offset_data = request.to_dict()
        offset_data["evaluated_at"] = "2026-08-21T08:05:00-04:00"
        offset_request = NegativeClaimRequest.from_dict(offset_data)
        self.assertEqual(
            evaluate_negative_claim(request, context).input_digest,
            evaluate_negative_claim(offset_request, context).input_digest,
        )

        offset_profile_data = _profile_dict()
        offset_profile_data["issued_at"] = "2026-08-19T20:00:00-04:00"
        offset_profile_data["effective_at"] = "2026-08-20T20:00:00-04:00"
        offset_profile_data["expires_at"] = "2026-08-21T20:00:00-04:00"
        offset_profile = CoverageFinalityProfile.from_dict(offset_profile_data)
        self.assertEqual(profile.profile_digest, offset_profile.profile_digest)

        reordered_context_data = context.to_dict()
        reordered_context_data = dict(reversed(tuple(reordered_context_data.items())))
        reparsed_context = TrustedProfileContext.from_dict(reordered_context_data)
        self.assertEqual(context.context_digest, reparsed_context.context_digest)

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

    def test_untrusted_snapshot_content_cannot_drive_finality_diagnostics(self) -> None:
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
            _context(profile, pinned_snapshot_digest="sha256:" + "0" * 64),
        )

        self.assertEqual(
            [item.code for item in assessment.issues],
            [ProfileIssueCode.REGISTRY_SNAPSHOT_DIGEST_MISMATCH],
        )
        self.assertEqual(assessment.resolved_profile_references, ())

    def test_untrusted_profile_content_cannot_drive_finality_diagnostics(self) -> None:
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
        context = _context(profile)
        untrusted_selection = replace(
            context.trust_selection,
            trusted_profile_issuer_ids=("different-profile-publisher",),
            trust_selection_digest=None,
        )

        assessment = evaluate_profile_governance(
            EvidenceEnvelope.from_dict(data["envelope"]),
            _evaluated_at(),
            TrustedProfileContext(
                snapshot=context.snapshot,
                trust_selection=untrusted_selection,
            ),
        )

        self.assertEqual(
            [item.code for item in assessment.issues],
            [ProfileIssueCode.PROFILE_ISSUER_UNTRUSTED],
        )
        self.assertEqual(assessment.resolved_profile_references, ())

    def test_producer_cannot_select_weaker_profile_from_trusted_snapshot(self) -> None:
        strong = _profile()
        weak = replace(
            strong,
            profile_version="0.9.0",
            finality=replace(
                strong.finality,
                late_arrival_bound_seconds=0,
                reopen_bound_seconds=0,
            ),
        )
        records = tuple(
            ProfileRegistryRecord(
                profile=item,
                profile_digest=None,
                status=ProfileRegistryStatus.ACTIVE,
                revoked_at=None,
                revocation_effective_at=None,
                revocation_reason_code=None,
            )
            for item in (strong, weak)
        )
        snapshot = ProfileRegistrySnapshot(
            snapshot_schema=PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
            registry_id="local-assurance-registry",
            snapshot_id="snapshot-two-active-profiles",
            snapshot_version="2",
            issuer_id="registry-publisher",
            as_of=parse_datetime("2026-08-21T12:00:00Z", "as_of"),
            next_update_at=parse_datetime("2026-08-21T13:00:00Z", "next"),
            records=records,
            snapshot_digest=None,
        )
        assert snapshot.snapshot_digest is not None
        selected = CoverageProfileReference(
            registry_id=snapshot.registry_id,
            profile_id=strong.profile_id,
            profile_version=strong.profile_version,
            profile_digest=strong.profile_digest,
        )
        trust = ProfileTrustSelection(
            trust_schema=PROFILE_TRUST_SELECTION_SCHEMA,
            registry_id=snapshot.registry_id,
            snapshot_id=snapshot.snapshot_id,
            snapshot_version=snapshot.snapshot_version,
            snapshot_digest=snapshot.snapshot_digest,
            selected_profile_reference=selected,
            trusted_snapshot_issuer_ids=(snapshot.issuer_id,),
            trusted_profile_issuer_ids=(strong.issuer_id,),
            trusted_approval_authority_ids=(strong.approval_authority_id,),
            trust_selection_digest=None,
        )
        data = request_dict()
        requirement = data["envelope"]["query"]["source_requirements"][0]
        requirement["profile_ref"] = CoverageProfileReference(
            registry_id=snapshot.registry_id,
            profile_id=weak.profile_id,
            profile_version=weak.profile_version,
            profile_digest=weak.profile_digest,
        ).to_dict()
        requirement["finality_horizon"] = "2026-08-21T12:00:00Z"
        refresh_query_fingerprints(data)

        assessment = evaluate_profile_governance(
            EvidenceEnvelope.from_dict(data["envelope"]),
            _evaluated_at(),
            TrustedProfileContext(snapshot=snapshot, trust_selection=trust),
        )

        self.assertEqual(
            [item.code for item in assessment.issues],
            [ProfileIssueCode.PROFILE_TRUST_SELECTION_MISMATCH],
        )
        self.assertEqual(assessment.resolved_profile_references, ())

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
