from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone

from evidence_state_io import (
    AUTHORIZATION_CONTEXT_IDENTIFIER_PROFILE,
    EvidenceEnvelope,
    EvidenceOrigin,
    ImplementationIdentity,
    ModelValidationError,
    NegativeClaimRequest,
    ProfileSource,
    ValidationErrorCode,
    WorkingTreeState,
    authorization_context_identifier,
    build_evidence_certificate,
    evaluate_negative_claim,
)
from tests.helpers import refresh_query_fingerprints, request_dict, trusted_context


class AuthorizationContextIdentifierTests(unittest.TestCase):
    @staticmethod
    def credential_like_values() -> tuple[str, ...]:
        return (
            "bearer:redacted",
            "token:redacted",
            "api_key:redacted",
            "gh" + "p_" + "ab12" * 6,
            "github_" + "pat_" + "ab12" * 6,
            "gl" + "pat-" + "ab12" * 6,
            "s" + "k-" + "ab12" * 6,
            "xo" + "xb-" + "ab12" * 4,
            "ya" + "29." + "ab12" * 6,
            "ak" + "ia" + "ab12" * 4,
            "eyjabcde.abcdefgh.abcdefghijklmnop",
            "ab12" * 12,
        )

    def test_profile_identifier_is_exact_and_versioned(self) -> None:
        self.assertEqual(
            AUTHORIZATION_CONTEXT_IDENTIFIER_PROFILE,
            "esio-authorization-context-identifier/1.0-candidate.1",
        )

    def test_unknown_identifier_profile_fails_closed_without_scanning(self) -> None:
        for profile in (
            "esio-authorization-context-identifier/1.0-candidate.0",
            "esio-authorization-context-identifier/latest",
            None,
        ):
            with self.subTest(profile=profile):
                with self.assertRaises(ModelValidationError) as caught:
                    authorization_context_identifier(
                        "public-search-adapter-context",
                        "authorization_context_id",
                        identifier_profile=profile,  # type: ignore[arg-type]
                    )
                self.assertEqual(
                    caught.exception.code,
                    ValidationErrorCode.UNSUPPORTED_CONTRACT,
                )

    def test_overloaded_string_equality_cannot_bypass_identifier_profile(self) -> None:
        class EqualityBypass(str):
            def __eq__(self, other: object) -> bool:
                return True

            def __ne__(self, other: object) -> bool:
                return False

        with self.assertRaises(ModelValidationError) as caught:
            authorization_context_identifier(
                "public-search-adapter-context",
                "authorization_context_id",
                identifier_profile=EqualityBypass("attacker-selected"),
            )
        self.assertEqual(
            caught.exception.code,
            ValidationErrorCode.UNSUPPORTED_CONTRACT,
        )

    def test_narrow_credential_classes_fail_with_stable_code_and_safe_message(self) -> None:
        for value in self.credential_like_values():
            with self.subTest(value_class=value[:4]):
                with self.assertRaises(ModelValidationError) as caught:
                    authorization_context_identifier(value, "authorization_context_id")
                self.assertEqual(
                    caught.exception.code,
                    ValidationErrorCode.CREDENTIAL_LIKE_IDENTIFIER,
                )
                self.assertNotIn(value, str(caught.exception))

    def test_semantic_and_namespaced_non_secret_identifiers_remain_valid(self) -> None:
        accepted = (
            "public-search-adapter-context",
            "tenant:alpha-reader-role",
            "context-with-token-label",
            "session-scope-reader",
            "sha256:" + "a" * 64,
            "550e8400-e29b-41d4-a716-446655440000",
        )
        for value in accepted:
            with self.subTest(value=value):
                self.assertEqual(
                    authorization_context_identifier(value, "authorization_context_id"),
                    value,
                )

    def test_all_four_authorization_context_model_fields_enforce_profile(self) -> None:
        envelope = EvidenceEnvelope.from_dict(request_dict()["envelope"])
        requirement = envelope.query.source_requirements[0]
        observation = envelope.source_observations[0]
        profile_source = trusted_context().snapshot.records[0].profile.source
        value = "bearer:redacted"

        mutations = (
            lambda: replace(requirement, authorization_context_id=value),
            lambda: replace(envelope.query, authorization_context_id=value),
            lambda: replace(observation, authorization_context_id=value),
            lambda: replace(profile_source, authorization_context_id=value),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(field_index=index):
                with self.assertRaises(ModelValidationError) as caught:
                    mutation()
                self.assertEqual(
                    caught.exception.code,
                    ValidationErrorCode.CREDENTIAL_LIKE_IDENTIFIER,
                )

    def test_profile_source_json_boundary_enforces_profile(self) -> None:
        profile_source = trusted_context().snapshot.records[0].profile.source
        candidate = profile_source.to_dict()
        candidate["authorization_context_id"] = "token:redacted"
        with self.assertRaises(ModelValidationError) as caught:
            ProfileSource.from_dict(candidate)
        self.assertEqual(
            caught.exception.code,
            ValidationErrorCode.CREDENTIAL_LIKE_IDENTIFIER,
        )

    def test_gate_and_certificate_reparse_all_mutated_authorization_identifiers(self) -> None:
        def mutate_query(request: NegativeClaimRequest, context: object) -> None:
            object.__setattr__(
                request.envelope.query,
                "authorization_context_id",
                "bearer:mutated-query-secret",
            )

        def mutate_requirement(request: NegativeClaimRequest, context: object) -> None:
            object.__setattr__(
                request.envelope.query.source_requirements[0],
                "authorization_context_id",
                "bearer:mutated-requirement-secret",
            )

        def mutate_observation(request: NegativeClaimRequest, context: object) -> None:
            object.__setattr__(
                request.envelope.source_observations[0],
                "authorization_context_id",
                "bearer:mutated-observation-secret",
            )

        def mutate_profile(request: NegativeClaimRequest, context: object) -> None:
            assert hasattr(context, "snapshot")
            object.__setattr__(
                context.snapshot.records[0].profile.source,
                "authorization_context_id",
                "bearer:mutated-profile-secret",
            )

        implementation = ImplementationIdentity(
            package_name="evidence-state-io",
            package_version="0.6.0",
            repository_revision=None,
            working_tree_state=WorkingTreeState.UNBOUND,
        )
        for mutation in (
            mutate_query,
            mutate_requirement,
            mutate_observation,
            mutate_profile,
        ):
            for operation in ("evaluate", "certificate"):
                with self.subTest(mutation=mutation.__name__, operation=operation):
                    request = NegativeClaimRequest.from_dict(request_dict())
                    context = trusted_context()
                    mutation(request, context)
                    with self.assertRaises(ModelValidationError) as caught:
                        if operation == "evaluate":
                            evaluate_negative_claim(request, context)
                        else:
                            build_evidence_certificate(
                                request,
                                context,
                                issued_at=datetime(2026, 8, 21, 12, 6, tzinfo=timezone.utc),
                                origin=EvidenceOrigin.SYNTHETIC,
                                implementation=implementation,
                            )
                    self.assertEqual(
                        caught.exception.code,
                        ValidationErrorCode.CREDENTIAL_LIKE_IDENTIFIER,
                    )

    def test_descriptive_content_is_not_scanned_as_an_identifier(self) -> None:
        request = request_dict()
        data = request["envelope"]
        data["query"]["authorization_boundary"] = "bearer:redacted"
        data["query"]["source_requirements"][0]["detection_assumptions"] = [
            "a bearer:redacted marker may appear in descriptive source output"
        ]
        refresh_query_fingerprints(request)
        envelope = EvidenceEnvelope.from_dict(data)
        self.assertEqual(envelope.query.authorization_boundary, "bearer:redacted")
        self.assertIn(
            "bearer:redacted",
            envelope.query.source_requirements[0].detection_assumptions[0],
        )


if __name__ == "__main__":
    unittest.main()
