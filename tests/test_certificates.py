from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
import unittest

from evidence_state_io.canonical import canonical_digest
from evidence_state_io.certificates import (
    CERTIFICATE_FORMAT,
    EvidenceCertificate,
    EvidenceOrigin,
    ImplementationIdentity,
    WorkingTreeState,
    build_evidence_certificate,
    verify_evidence_certificate,
)
from evidence_state_io.gate import NegativeClaimRequest
from evidence_state_io.models import ClaimMode, ModelValidationError, PopulationBasis
from evidence_state_io.profiles import (
    COVERAGE_FINALITY_PROFILE_SCHEMA,
    FINALITY_METHOD,
    PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
    PROFILE_TRUST_SELECTION_SCHEMA,
    CoverageFinalityProfile,
    ProfileApplicability,
    ProfileCoverage,
    ProfileFinality,
    ProfileRegistryRecord,
    ProfileRegistrySnapshot,
    ProfileRegistryStatus,
    ProfileSource,
    ProfileTrustSelection,
    TrustedProfileContext,
)

from tests.helpers import refresh_query_fingerprints, request_dict


UTC = timezone.utc
EVALUATED_AT = datetime(2026, 8, 21, 12, 5, tzinfo=UTC)
ISSUED_AT = datetime(2026, 8, 21, 12, 6, tzinfo=UTC)
REVISION = "a" * 40


def implementation(
    *,
    version: str = "0.5.0",
    state: WorkingTreeState = WorkingTreeState.CLEAN,
) -> ImplementationIdentity:
    return ImplementationIdentity(
        package_name="evidence-state-io",
        package_version=version,
        repository_revision=None if state is WorkingTreeState.UNBOUND else REVISION,
        working_tree_state=state,
    )


def governed_inputs() -> tuple[NegativeClaimRequest, TrustedProfileContext]:
    data = request_dict()
    query = data["envelope"]["query"]
    requirement = query["source_requirements"][0]
    coverage = data["envelope"]["coverage"]
    profile = CoverageFinalityProfile(
        profile_schema=COVERAGE_FINALITY_PROFILE_SCHEMA,
        profile_id="github-public-search",
        profile_version="1.0.0",
        source_owner_id="github-source-owner",
        approval_authority_id="local-assurance-authority",
        issuer_id="local-profile-publisher",
        issued_at=datetime(2026, 8, 20, 0, 0, tzinfo=UTC),
        effective_at=datetime(2026, 8, 21, 0, 0, tzinfo=UTC),
        expires_at=datetime(2026, 8, 21, 14, 0, tzinfo=UTC),
        source=ProfileSource(
            source_id=requirement["source_id"],
            system=requirement["system"],
            locator=requirement["locator"],
            adapter_id=requirement["adapter_id"],
            adapter_version=requirement["adapter_version"],
            authorization_context_id=requirement["authorization_context_id"],
            accessible_population=requirement["accessible_population"],
        ),
        applicability=ProfileApplicability(
            target=query["target"],
            predicate=query["predicate"],
            authorization_boundary=query["authorization_boundary"],
            required_exclusions=tuple(query["exclusions"]),
            detection_assumptions=tuple(requirement["detection_assumptions"]),
        ),
        coverage=ProfileCoverage(
            population_basis=PopulationBasis(coverage["population_basis"]),
            population_units=coverage["population_units"],
            pages_expected=coverage["pages_expected"],
            partitions_expected=coverage["partitions_expected"],
            permission_limited=coverage["permission_limited"],
            retention_seconds=86_400,
            blind_intervals=(),
            max_observation_age_seconds=3_600,
            max_index_age_seconds=3_600,
        ),
        finality=ProfileFinality(
            method=FINALITY_METHOD,
            late_arrival_bound_seconds=240,
            reopen_bound_seconds=60,
        ),
    )
    requirement["profile_ref"] = {
        "registry_id": "local-coverage-registry",
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "profile_digest": profile.profile_digest,
    }
    refresh_query_fingerprints(data)
    request = NegativeClaimRequest.from_dict(data)
    record = ProfileRegistryRecord(
        profile=profile,
        profile_digest=None,
        status=ProfileRegistryStatus.ACTIVE,
        revoked_at=None,
        revocation_effective_at=None,
        revocation_reason_code=None,
    )
    snapshot = ProfileRegistrySnapshot(
        snapshot_schema=PROFILE_REGISTRY_SNAPSHOT_SCHEMA,
        registry_id="local-coverage-registry",
        snapshot_id="snapshot-2026-08-21",
        snapshot_version="1.0.0",
        issuer_id="local-registry-publisher",
        as_of=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        next_update_at=datetime(2026, 8, 21, 13, 30, tzinfo=UTC),
        records=(record,),
    )
    assert snapshot.snapshot_digest is not None
    trust = ProfileTrustSelection(
        trust_schema=PROFILE_TRUST_SELECTION_SCHEMA,
        registry_id=snapshot.registry_id,
        snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.snapshot_version,
        snapshot_digest=snapshot.snapshot_digest,
        trusted_snapshot_issuer_ids=(snapshot.issuer_id,),
        trusted_profile_issuer_ids=(profile.issuer_id,),
        trusted_approval_authority_ids=(profile.approval_authority_id,),
    )
    return request, TrustedProfileContext(snapshot=snapshot, trust_selection=trust)


def certificate(
    *,
    request: NegativeClaimRequest | None = None,
    context: TrustedProfileContext | None = None,
    issued_at: datetime = ISSUED_AT,
    origin: EvidenceOrigin = EvidenceOrigin.SYNTHETIC,
    identity: ImplementationIdentity | None = None,
) -> EvidenceCertificate:
    default_request, default_context = governed_inputs()
    return build_evidence_certificate(
        default_request if request is None else request,
        default_context if context is None else context,
        issued_at=issued_at,
        origin=origin,
        implementation=implementation() if identity is None else identity,
    )


class EvidenceCertificateTests(unittest.TestCase):
    def test_builder_owns_evaluation_and_emits_permit_record(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(request=request, context=context)
        self.assertNotIn("decision", inspect.signature(build_evidence_certificate).parameters)
        self.assertEqual(
            artifact.certificate.certificate_format,
            CERTIFICATE_FORMAT,
        )
        self.assertTrue(artifact.certificate.decision["allowed"])
        self.assertEqual(
            artifact.certificate.evaluation_input_digest,
            artifact.certificate.decision["input_digest"],
        )
        self.assertEqual(artifact.certificate_digest, artifact.recomputed_digest)
        self.assertEqual(
            artifact.certificate.context_binding.context_digest,
            context.context_digest,
        )

    def test_rejection_is_a_first_class_replay_record(self) -> None:
        request, context = governed_inputs()
        rejected_request = replace(request, mode=ClaimMode.ABSOLUTE)
        artifact = certificate(request=rejected_request, context=context)
        self.assertFalse(artifact.certificate.decision["allowed"])
        self.assertIn(
            "ABSOLUTE_NEGATIVE_UNSUPPORTED",
            artifact.certificate.decision["reasons"],
        )
        report = verify_evidence_certificate(artifact)
        self.assertTrue(report.deterministic_replay)
        self.assertTrue(report.historical_reproducibility)

    def test_identical_inputs_produce_identical_bytes_and_digest(self) -> None:
        request, context = governed_inputs()
        first = certificate(request=request, context=context)
        second = certificate(request=request, context=context)
        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        self.assertEqual(first.certificate_digest, second.certificate_digest)

    def test_timezone_equivalent_issuance_normalizes_identically(self) -> None:
        request, context = governed_inputs()
        offset = timezone(timedelta(hours=-4))
        equivalent = ISSUED_AT.astimezone(offset)
        first = certificate(request=request, context=context)
        second = certificate(
            request=request,
            context=context,
            issued_at=equivalent,
        )
        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())

    def test_effective_boundary_is_earliest_and_evidence_is_conservative(self) -> None:
        artifact = certificate()
        self.assertEqual(
            artifact.certificate.effective_valid_until_exclusive,
            datetime(2026, 8, 21, 13, 0, tzinfo=UTC),
        )

    def test_round_trip_preserves_canonical_bytes(self) -> None:
        artifact = certificate()
        parsed = EvidenceCertificate.from_dict(deepcopy(artifact.to_dict()))
        self.assertEqual(parsed.canonical_bytes(), artifact.canonical_bytes())
        self.assertEqual(parsed, artifact)

    def test_strict_json_decimal_decision_values_normalize_for_replay(self) -> None:
        artifact = certificate()
        data = artifact.to_dict()
        coverage = data["certificate"]["decision"]["coverage"]
        coverage["lower_bound"] = Decimal(str(coverage["lower_bound"]))
        for component in coverage["components"]:
            component["lower_bound"] = Decimal(str(component["lower_bound"]))
        parsed = EvidenceCertificate.from_dict(data)
        report = verify_evidence_certificate(parsed)
        self.assertTrue(report.certificate_digest_integrity)
        self.assertTrue(report.deterministic_replay)

    def test_wrong_outer_digest_is_parseable_and_reported_separately(self) -> None:
        data = certificate().to_dict()
        data["certificate_digest"] = "sha256:" + "0" * 64
        parsed = EvidenceCertificate.from_dict(data)
        report = verify_evidence_certificate(parsed)
        self.assertTrue(report.structural_support)
        self.assertFalse(report.certificate_digest_integrity)
        self.assertTrue(report.embedded_digest_integrity)
        self.assertTrue(report.deterministic_replay)
        self.assertTrue(report.historical_reproducibility)

    def test_decision_tamper_without_rehash_fails_digest_and_replay(self) -> None:
        data = certificate().to_dict()
        data["certificate"]["decision"]["qualified_claim"] += " forged"
        report = verify_evidence_certificate(data)
        self.assertFalse(report.certificate_digest_integrity)
        self.assertFalse(report.deterministic_replay)

    def test_decision_tamper_with_rehash_still_fails_replay(self) -> None:
        data = certificate().to_dict()
        data["certificate"]["decision"]["limitations"].append(
            "Caller-injected limitation."
        )
        data["certificate_digest"] = canonical_digest(data["certificate"])
        report = verify_evidence_certificate(data)
        self.assertTrue(report.certificate_digest_integrity)
        self.assertFalse(report.deterministic_replay)
        self.assertIn("DETERMINISTIC_REPLAY_MISMATCH", report.issues)

    def test_changed_policy_digest_with_rehash_fails_embedded_integrity(self) -> None:
        data = certificate().to_dict()
        data["certificate"]["policy_digest"] = "sha256:" + "0" * 64
        data["certificate_digest"] = canonical_digest(data["certificate"])
        report = verify_evidence_certificate(data)
        self.assertTrue(report.certificate_digest_integrity)
        self.assertFalse(report.embedded_digest_integrity)
        self.assertTrue(report.deterministic_replay)

    def test_optional_custody_checks_are_unestablished_when_absent(self) -> None:
        report = verify_evidence_certificate(certificate())
        self.assertIsNone(report.expected_context_match)
        self.assertIsNone(report.expected_certificate_digest_match)
        self.assertIsNone(report.current_local_reliance_eligible)
        self.assertFalse(report.issuer_authenticated)
        self.assertFalse(report.authorization_established)
        self.assertNotIn("valid", report.to_dict())

    def test_expected_context_and_digest_match_separate_state(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(request=request, context=context)
        report = verify_evidence_certificate(
            artifact,
            expected_context=context,
            expected_certificate_digest=artifact.certificate_digest,
        )
        self.assertTrue(report.expected_context_match)
        self.assertTrue(report.expected_certificate_digest_match)

    def test_expected_digest_compares_with_recomputed_not_embedded_value(self) -> None:
        artifact = certificate()
        data = artifact.to_dict()
        data["certificate_digest"] = "sha256:" + "0" * 64
        report = verify_evidence_certificate(
            data,
            expected_certificate_digest=artifact.certificate_digest,
        )
        self.assertFalse(report.certificate_digest_integrity)
        self.assertTrue(report.expected_certificate_digest_match)

    def test_different_but_sufficient_context_is_not_expected_context(self) -> None:
        request, context = governed_inputs()
        different_trust = replace(
            context.trust_selection,
            trusted_profile_issuer_ids=(
                *context.trust_selection.trusted_profile_issuer_ids,
                "alternate-profile-publisher",
            ),
            trust_selection_digest=None,
        )
        different_context = TrustedProfileContext(
            snapshot=context.snapshot,
            trust_selection=different_trust,
        )
        artifact = certificate(request=request, context=different_context)
        report = verify_evidence_certificate(
            artifact,
            expected_context=context,
        )
        self.assertTrue(report.deterministic_replay)
        self.assertFalse(report.expected_context_match)

    def test_current_local_reliance_requires_external_context_and_time(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(request=request, context=context)
        current = verify_evidence_certificate(
            artifact,
            expected_context=context,
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        expired = verify_evidence_certificate(
            artifact,
            expected_context=context,
            relying_party_at=datetime(2026, 8, 21, 13, 0, tzinfo=UTC),
        )
        self.assertTrue(current.current_local_reliance_eligible)
        self.assertFalse(expired.current_local_reliance_eligible)
        self.assertTrue(expired.historical_reproducibility)

    def test_rejection_can_never_become_current_local_reliance(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(
            request=replace(request, mode=ClaimMode.ABSOLUTE),
            context=context,
        )
        report = verify_evidence_certificate(
            artifact,
            expected_context=context,
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        self.assertFalse(report.current_local_reliance_eligible)
        self.assertTrue(report.historical_reproducibility)

    def test_unknown_certificate_contract_is_structurally_unsupported(self) -> None:
        data = certificate().to_dict()
        data["certificate"]["certificate_format"] = (
            "esio-evidence-certificate/1.0-candidate.0"
        )
        data["certificate_digest"] = canonical_digest(data["certificate"])
        report = verify_evidence_certificate(data)
        self.assertFalse(report.structural_support)
        self.assertFalse(report.historical_reproducibility)

    def test_unknown_outer_field_is_rejected(self) -> None:
        data = certificate().to_dict()
        data["signature"] = None
        with self.assertRaisesRegex(ModelValidationError, "unknown fields"):
            EvidenceCertificate.from_dict(data)

    def test_origin_time_and_implementation_mutations_change_digest(self) -> None:
        request, context = governed_inputs()
        baseline = certificate(request=request, context=context)
        variants = (
            certificate(
                request=request,
                context=context,
                origin=EvidenceOrigin.REPLAYED,
            ),
            certificate(
                request=request,
                context=context,
                issued_at=ISSUED_AT + timedelta(microseconds=1),
            ),
            certificate(
                request=request,
                context=context,
                identity=implementation(state=WorkingTreeState.DIRTY),
            ),
        )
        for variant in variants:
            self.assertNotEqual(
                baseline.certificate_digest,
                variant.certificate_digest,
            )

    def test_origin_and_issued_time_are_explicit_strict_inputs(self) -> None:
        request, context = governed_inputs()
        with self.assertRaisesRegex(ModelValidationError, "EvidenceOrigin"):
            build_evidence_certificate(
                request,
                context,
                issued_at=ISSUED_AT,
                origin="SYNTHETIC",  # type: ignore[arg-type]
                implementation=implementation(),
            )
        with self.assertRaisesRegex(ModelValidationError, "must not precede"):
            certificate(
                request=request,
                context=context,
                issued_at=EVALUATED_AT - timedelta(microseconds=1),
            )

    def test_working_tree_identity_requires_revision_or_explicit_unbound(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "full lowercase Git revision"):
            ImplementationIdentity(
                package_name="evidence-state-io",
                package_version="0.4.0",
                repository_revision=None,
                working_tree_state=WorkingTreeState.CLEAN,
            )
        unbound = implementation(state=WorkingTreeState.UNBOUND)
        self.assertIsNone(unbound.repository_revision)
        self.assertEqual(unbound.working_tree_state, WorkingTreeState.UNBOUND)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
