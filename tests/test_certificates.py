from __future__ import annotations

import inspect
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

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
from evidence_state_io.models import (
    ClaimMode,
    CoverageProfileReference,
    ModelValidationError,
    PopulationBasis,
)
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
    version: str = "0.6.0",
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
        selected_profile_reference=CoverageProfileReference(
            registry_id=snapshot.registry_id,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_digest=profile.profile_digest,
        ),
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


def with_profile_age_limits(
    request: NegativeClaimRequest,
    context: TrustedProfileContext,
    *,
    observation_seconds: int,
    index_seconds: int,
) -> tuple[NegativeClaimRequest, TrustedProfileContext]:
    profile = context.snapshot.records[0].profile
    constrained_profile = replace(
        profile,
        coverage=replace(
            profile.coverage,
            max_observation_age_seconds=observation_seconds,
            max_index_age_seconds=index_seconds,
        ),
    )
    record = ProfileRegistryRecord(
        profile=constrained_profile,
        profile_digest=None,
        status=ProfileRegistryStatus.ACTIVE,
        revoked_at=None,
        revocation_effective_at=None,
        revocation_reason_code=None,
    )
    snapshot = replace(
        context.snapshot,
        records=(record,),
        snapshot_digest=None,
    )
    assert snapshot.snapshot_digest is not None
    reference = CoverageProfileReference(
        registry_id=snapshot.registry_id,
        profile_id=constrained_profile.profile_id,
        profile_version=constrained_profile.profile_version,
        profile_digest=constrained_profile.profile_digest,
    )
    trust = replace(
        context.trust_selection,
        snapshot_digest=snapshot.snapshot_digest,
        selected_profile_reference=reference,
        trust_selection_digest=None,
    )
    data = request.to_dict()
    data["envelope"]["query"]["source_requirements"][0]["profile_ref"] = reference.to_dict()
    refresh_query_fingerprints(data)
    return (
        NegativeClaimRequest.from_dict(data),
        TrustedProfileContext(snapshot=snapshot, trust_selection=trust),
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

    def test_effective_boundary_includes_profile_freshness_deadlines(self) -> None:
        request, context = governed_inputs()
        request, context = with_profile_age_limits(
            request,
            context,
            observation_seconds=600,
            index_seconds=600,
        )
        artifact = certificate(request=request, context=context)
        self.assertEqual(
            artifact.certificate.effective_valid_until_exclusive,
            datetime(2026, 8, 21, 12, 14, tzinfo=UTC),
        )
        before = verify_evidence_certificate(
            artifact,
            expected_context=context,
            expected_certificate_digest=artifact.certificate_digest,
            relying_party_at=datetime(2026, 8, 21, 12, 13, 59, 999999, tzinfo=UTC),
        )
        at_boundary = verify_evidence_certificate(
            artifact,
            expected_context=context,
            expected_certificate_digest=artifact.certificate_digest,
            relying_party_at=datetime(2026, 8, 21, 12, 14, tzinfo=UTC),
        )
        self.assertTrue(before.current_local_reliance_eligible)
        self.assertFalse(at_boundary.current_local_reliance_eligible)

    def test_effective_boundary_includes_policy_freshness_deadlines(self) -> None:
        request, context = governed_inputs()
        request = replace(
            request,
            policy=replace(
                request.policy,
                max_observation_age_seconds=300,
                max_index_age_seconds=300,
            ),
        )
        artifact = certificate(request=request, context=context)
        self.assertEqual(
            artifact.certificate.effective_valid_until_exclusive,
            datetime(2026, 8, 21, 12, 9, tzinfo=UTC),
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

    def test_lossy_decimal_cannot_collapse_to_original_certificate_digest(self) -> None:
        artifact = certificate()
        data = artifact.to_dict()
        data["certificate"]["decision"]["coverage"]["lower_bound"] = Decimal(
            "0.999999999999999999999999999999999999"
        )
        report = verify_evidence_certificate(
            data,
            expected_certificate_digest=artifact.certificate_digest,
        )
        self.assertFalse(report.structural_support)
        self.assertFalse(report.historical_reproducibility)

    def test_typed_artifact_cannot_bypass_nested_boolean_validation(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(request=request, context=context)
        artifact.certificate.decision["coverage"]["meets_policy"] = 1
        mutated = EvidenceCertificate(
            certificate=artifact.certificate,
            certificate_digest=artifact.recomputed_digest,
        )
        report = verify_evidence_certificate(
            mutated,
            expected_context=context,
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        self.assertFalse(report.structural_support)
        self.assertIsNone(report.current_local_reliance_eligible)

    def test_replay_comparison_is_json_type_strict_for_numeric_values(self) -> None:
        data = certificate().to_dict()
        data["certificate"]["decision"]["coverage"]["lower_bound"] = 1
        data["certificate_digest"] = canonical_digest(data["certificate"])
        report = verify_evidence_certificate(data)
        self.assertTrue(report.structural_support)
        self.assertFalse(report.deterministic_replay)

    def test_coverage_bounds_outside_unit_interval_are_structurally_unsupported(self) -> None:
        for path, value in (
            (("lower_bound",), -1.0),
            (("lower_bound",), 2.0),
            (("components", 0, "lower_bound"), 1.0000000001),
        ):
            with self.subTest(path=path, value=value):
                data = certificate().to_dict()
                target = data["certificate"]["decision"]["coverage"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                data["certificate_digest"] = canonical_digest(data["certificate"])
                report = verify_evidence_certificate(data)
                self.assertFalse(report.structural_support)
                self.assertFalse(report.historical_reproducibility)

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
        data["certificate"]["decision"]["limitations"].append("Caller-injected limitation.")
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

    def test_known_expected_digest_mismatch_blocks_current_local_reliance(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(request=request, context=context)
        report = verify_evidence_certificate(
            artifact,
            expected_context=context,
            expected_certificate_digest="sha256:" + "0" * 64,
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        self.assertTrue(report.certificate_digest_integrity)
        self.assertTrue(report.deterministic_replay)
        self.assertTrue(report.expected_context_match)
        self.assertFalse(report.expected_certificate_digest_match)
        self.assertFalse(report.current_local_reliance_eligible)

    def test_different_but_sufficient_context_is_not_expected_context(self) -> None:
        request, context = governed_inputs()
        original_artifact = certificate(request=request, context=context)
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
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        self.assertNotEqual(context.context_digest, different_context.context_digest)
        self.assertNotEqual(
            original_artifact.certificate_digest,
            artifact.certificate_digest,
        )
        self.assertEqual(
            artifact.certificate.context_binding.context_digest,
            different_context.context_digest,
        )
        self.assertTrue(report.embedded_digest_integrity)
        self.assertTrue(report.deterministic_replay)
        self.assertFalse(report.expected_context_match)
        self.assertFalse(report.current_local_reliance_eligible)

    def test_current_local_reliance_requires_external_context_and_time(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(request=request, context=context)
        current = verify_evidence_certificate(
            artifact,
            expected_context=context,
            expected_certificate_digest=artifact.certificate_digest,
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        expired = verify_evidence_certificate(
            artifact,
            expected_context=context,
            expected_certificate_digest=artifact.certificate_digest,
            relying_party_at=datetime(2026, 8, 21, 13, 0, tzinfo=UTC),
        )
        self.assertTrue(current.current_local_reliance_eligible)
        self.assertFalse(expired.current_local_reliance_eligible)
        self.assertTrue(expired.historical_reproducibility)

    def test_current_local_reliance_requires_retained_expected_digest(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(request=request, context=context)
        report = verify_evidence_certificate(
            artifact,
            expected_context=context,
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        self.assertIsNone(report.expected_certificate_digest_match)
        self.assertIsNone(report.current_local_reliance_eligible)

    def test_rejection_can_never_become_current_local_reliance(self) -> None:
        request, context = governed_inputs()
        artifact = certificate(
            request=replace(request, mode=ClaimMode.ABSOLUTE),
            context=context,
        )
        report = verify_evidence_certificate(
            artifact,
            expected_context=context,
            expected_certificate_digest=artifact.certificate_digest,
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )
        self.assertFalse(report.current_local_reliance_eligible)
        self.assertTrue(report.historical_reproducibility)

    def test_unknown_certificate_contract_is_structurally_unsupported(self) -> None:
        data = certificate().to_dict()
        data["certificate"]["certificate_format"] = "esio-evidence-certificate/1.0-candidate.0"
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

    def test_every_certificate_payload_leaf_is_digest_bound(self) -> None:
        payload = certificate().certificate.to_dict()
        baseline = canonical_digest(payload)

        def leaf_paths(value, prefix=()):
            if isinstance(value, dict):
                if not value:
                    yield prefix
                for key, item in value.items():
                    yield from leaf_paths(item, (*prefix, key))
            elif isinstance(value, list):
                if not value:
                    yield prefix
                for index, item in enumerate(value):
                    yield from leaf_paths(item, (*prefix, index))
            else:
                yield prefix

        def replacement(value):
            if value is None:
                return "digest-mutation"
            if isinstance(value, bool):
                return not value
            if isinstance(value, int):
                return value + 1
            if isinstance(value, float):
                return value + 0.125
            if isinstance(value, str):
                return value + "x"
            if isinstance(value, list):
                return ["digest-mutation"]
            if isinstance(value, dict):
                return {"digest-mutation": True}
            self.fail(f"unhandled certificate leaf type: {type(value)!r}")

        paths = tuple(leaf_paths(payload))
        self.assertGreater(len(paths), 100)
        for path in paths:
            with self.subTest(path=path):
                mutated = deepcopy(payload)
                target = mutated
                for key in path[:-1]:
                    target = target[key]
                key = path[-1]
                target[key] = replacement(target[key])
                self.assertNotEqual(canonical_digest(mutated), baseline)

    def test_unknown_and_downgraded_contract_identifiers_never_fallback(self) -> None:
        mutations = (
            (("certificate_format",), "esio-evidence-certificate/1.0-candidate.1"),
            (("certificate_format",), "esio-evidence-certificate/1.0-candidate.999"),
            (("wire_schema_version",), "0.1"),
            (("wire_schema_version",), "2.0"),
            (("evaluation_input_schema",), "esio-evaluation-input/1.0-candidate.1"),
            (("evaluation_input_schema",), "esio-evaluation-input/1.0-candidate.999"),
            (("policy_id",), "other-policy"),
            (("policy_version",), "1.0-candidate.3"),
            (("policy_version",), "1.0-candidate.999"),
            (("evaluator_version",), "esio-evaluator-1.0-candidate.3"),
            (("evaluator_version",), "esio-evaluator-1.0-candidate.4"),
            (("evaluator_version",), "esio-evaluator-1.0-candidate.999"),
            (("canonicalization_profile",), "esio-canonical-json-0.0"),
            (("digest_algorithm",), "sha512"),
            (
                ("trusted_profile_context", "registry_snapshot", "snapshot", "snapshot_schema"),
                "esio-profile-registry-snapshot/1.0-candidate.1",
            ),
            (
                ("trusted_profile_context", "registry_snapshot", "snapshot", "snapshot_schema"),
                "esio-profile-registry-snapshot/1.0-candidate.999",
            ),
            (
                (
                    "trusted_profile_context",
                    "registry_snapshot",
                    "snapshot",
                    "records",
                    0,
                    "profile",
                    "profile_schema",
                ),
                "esio-coverage-finality-profile/1.0-candidate.1",
            ),
            (
                (
                    "trusted_profile_context",
                    "registry_snapshot",
                    "snapshot",
                    "records",
                    0,
                    "profile",
                    "profile_schema",
                ),
                "esio-coverage-finality-profile/1.0-candidate.999",
            ),
            (
                ("trusted_profile_context", "trust_selection", "trust_schema"),
                "esio-profile-trust-selection/1.0-candidate.1",
            ),
            (
                ("trusted_profile_context", "trust_selection", "trust_schema"),
                "esio-profile-trust-selection/1.0-candidate.999",
            ),
        )
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                data = certificate().to_dict()
                target = data["certificate"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                data["certificate_digest"] = canonical_digest(data["certificate"])
                report = verify_evidence_certificate(data)
                self.assertFalse(report.structural_support)
                self.assertFalse(report.historical_reproducibility)

    def test_overloaded_string_cannot_downgrade_mapping_certificate(self) -> None:
        class EqualityBypass(str):
            def __eq__(self, other: object) -> bool:
                return True

            def __ne__(self, other: object) -> bool:
                return False

        request, context = governed_inputs()
        data = certificate(request=request, context=context).to_dict()
        data["certificate"]["evaluator_version"] = EqualityBypass("esio-evaluator-1.0-candidate.4")
        data["certificate_digest"] = canonical_digest(data["certificate"])

        report = verify_evidence_certificate(
            data,
            expected_context=context,
            expected_certificate_digest=data["certificate_digest"],
            relying_party_at=datetime(2026, 8, 21, 12, 30, tzinfo=UTC),
        )

        self.assertFalse(report.structural_support)
        self.assertFalse(report.historical_reproducibility)
        self.assertIsNone(report.current_local_reliance_eligible)

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
