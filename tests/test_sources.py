from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import unittest

from evidence_state_io.models import (
    MAX_SOURCE_ACCOUNTING_ENTRIES,
    CoverageEvidence,
    EvidenceEnvelope,
    EvidenceState,
    ModelValidationError,
    PopulationBasis,
    QueryScope,
    SourceDescriptor,
    SourceObservation,
    SourceObservationStatus,
    SourceRequirement,
    SourceRole,
)
from evidence_state_io.sources import SourceIssueCode, evaluate_source_accounting


UTC = timezone.utc
AUTHORIZATION_BOUNDARY = "public repositories visible to the adapter token"
AUTHORIZATION_CONTEXT_ID = "test-public-search-context"
PLACEHOLDER_QUERY_FINGERPRINT = "sha256:" + "0" * 64


def requirement(
    source_id: str = "primary-source",
    *,
    system: str = "synthetic-search",
    locator: str | None = None,
    adapter_id: str = "synthetic-search-adapter",
    adapter_version: str = "test-1.0",
    authorization_context_id: str = AUTHORIZATION_CONTEXT_ID,
    accessible_population: str = "all public repositories visible to the adapter",
    detection_assumptions: tuple[str, ...] | list[str] = (
        "the source indexes repository metadata",
    ),
) -> SourceRequirement:
    return SourceRequirement(
        source_id=source_id,
        role=SourceRole.REQUIRED,
        system=system,
        locator=f"repositories/{source_id}" if locator is None else locator,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        authorization_context_id=authorization_context_id,
        accessible_population=accessible_population,
        detection_assumptions=detection_assumptions,
    )


def observation(
    source_id: str = "primary-source",
    *,
    status: SourceObservationStatus = SourceObservationStatus.OBSERVED,
    system: str = "synthetic-search",
    locator: str | None = None,
    adapter_id: str = "synthetic-search-adapter",
    adapter_version: str = "test-1.0",
    authorization_context_id: str = AUTHORIZATION_CONTEXT_ID,
    query_fingerprint: str = PLACEHOLDER_QUERY_FINGERPRINT,
    accessible_population: str | None = (
        "all public repositories visible to the adapter"
    ),
    errors: tuple[str, ...] | list[str] = (),
) -> SourceObservation:
    return SourceObservation(
        source_id=source_id,
        status=status,
        descriptor=SourceDescriptor(
            system=system,
            locator=f"repositories/{source_id}" if locator is None else locator,
            adapter_id=adapter_id,
            adapter_version=adapter_version,
            index_as_of=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        ),
        authorization_context_id=authorization_context_id,
        query_fingerprint=query_fingerprint,
        accessible_population=accessible_population,
        errors=errors,
    )


def query(requirements) -> QueryScope:
    return QueryScope(
        target="repository search",
        predicate="topic:evidence-state",
        authorization_boundary=AUTHORIZATION_BOUNDARY,
        authorization_context_id=AUTHORIZATION_CONTEXT_ID,
        time_start=datetime(2026, 8, 21, 0, 0, tzinfo=UTC),
        time_end=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        exclusions=(),
        source_requirements=requirements,
    )


def envelope(requirements, observations) -> EvidenceEnvelope:
    declared_query = query(requirements)
    fingerprint = declared_query.fingerprint()
    bound_observations = tuple(
        replace(item, query_fingerprint=fingerprint) for item in observations
    )
    return EvidenceEnvelope(
        schema_version="1.0",
        state=EvidenceState.ABSENT_WITHIN_SCOPE,
        query=declared_query,
        coverage=CoverageEvidence(
            examined_units=1,
            population_basis=PopulationBasis.EXACT,
            population_units=1,
            pagination_complete=True,
            continuation_token_present=False,
            partitions_complete=True,
            timed_out=False,
            interrupted=False,
            permission_limited=False,
            query_errors=(),
        ),
        coverage_query_fingerprint=fingerprint,
        matched_count=0,
        observed_at=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        source_observations=bound_observations,
        errors=(),
        valid_until=datetime(2026, 8, 21, 13, 0, tzinfo=UTC),
        notes=(),
    )


def issue_pairs(assessment) -> tuple[tuple[SourceIssueCode, str | None], ...]:
    return tuple((issue.code, issue.source_id) for issue in assessment.issues)


class SourceAccountingTests(unittest.TestCase):
    def test_source_role_taxonomy_is_single_required_source_only(self) -> None:
        self.assertEqual([role.value for role in SourceRole], ["REQUIRED"])

    def test_source_observation_status_taxonomy_is_locked(self) -> None:
        self.assertEqual(
            [status.value for status in SourceObservationStatus],
            [
                "OBSERVED",
                "NOT_OBSERVED",
                "INACCESSIBLE",
                "PENDING",
                "STALE",
                "FAILED",
                "CONTRADICTORY",
                "UNKNOWN",
            ],
        )

    def test_single_complete_required_source_meets_policy(self) -> None:
        assessment = evaluate_source_accounting(
            (requirement(),),
            (observation(),),
        )

        self.assertTrue(assessment.meets_policy)
        self.assertEqual(assessment.issues, ())
        self.assertEqual(assessment.required_source_ids, ("primary-source",))
        self.assertEqual(assessment.observed_source_ids, ("primary-source",))
        self.assertEqual(assessment.complete_source_ids, ("primary-source",))

    def test_missing_required_source_is_not_vacuously_complete(self) -> None:
        assessment = evaluate_source_accounting((requirement(),), ())

        self.assertFalse(assessment.meets_policy)
        self.assertEqual(
            issue_pairs(assessment),
            ((SourceIssueCode.REQUIRED_SOURCE_MISSING, "primary-source"),),
        )
        self.assertEqual(assessment.observed_source_ids, ())
        self.assertEqual(assessment.complete_source_ids, ())

    def test_each_non_observed_required_status_has_its_own_issue(self) -> None:
        cases = (
            (
                SourceObservationStatus.NOT_OBSERVED,
                SourceIssueCode.REQUIRED_SOURCE_NOT_OBSERVED,
            ),
            (
                SourceObservationStatus.INACCESSIBLE,
                SourceIssueCode.REQUIRED_SOURCE_INACCESSIBLE,
            ),
            (
                SourceObservationStatus.PENDING,
                SourceIssueCode.REQUIRED_SOURCE_PENDING,
            ),
            (
                SourceObservationStatus.STALE,
                SourceIssueCode.REQUIRED_SOURCE_STALE,
            ),
            (
                SourceObservationStatus.CONTRADICTORY,
                SourceIssueCode.REQUIRED_SOURCE_CONTRADICTORY,
            ),
            (
                SourceObservationStatus.UNKNOWN,
                SourceIssueCode.REQUIRED_SOURCE_STATUS_UNKNOWN,
            ),
        )
        for status, expected in cases:
            with self.subTest(status=status.value):
                assessment = evaluate_source_accounting(
                    (requirement(),),
                    (observation(status=status),),
                )
                self.assertFalse(assessment.meets_policy)
                self.assertEqual(issue_pairs(assessment), ((expected, "primary-source"),))
                self.assertEqual(assessment.complete_source_ids, ())

    def test_failed_required_source_preserves_status_and_error_issues(self) -> None:
        assessment = evaluate_source_accounting(
            (requirement(),),
            (
                observation(
                    status=SourceObservationStatus.FAILED,
                    accessible_population=None,
                    errors=("adapter failed",),
                ),
            ),
        )

        self.assertFalse(assessment.meets_policy)
        self.assertEqual(
            issue_pairs(assessment),
            (
                (SourceIssueCode.REQUIRED_SOURCE_FAILED, "primary-source"),
                (SourceIssueCode.REQUIRED_SOURCE_ERRORS_PRESENT, "primary-source"),
            ),
        )
        self.assertEqual(assessment.complete_source_ids, ())

    def test_observed_required_source_with_population_mismatch_is_incomplete(self) -> None:
        assessment = evaluate_source_accounting(
            (requirement(),),
            (observation(accessible_population="only public repositories in one tenant"),),
        )

        self.assertFalse(assessment.meets_policy)
        self.assertEqual(
            issue_pairs(assessment),
            (
                (
                    SourceIssueCode.REQUIRED_SOURCE_POPULATION_MISMATCH,
                    "primary-source",
                ),
            ),
        )
        self.assertEqual(assessment.observed_source_ids, ("primary-source",))
        self.assertEqual(assessment.complete_source_ids, ())

    def test_observed_source_cannot_omit_accessible_population(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "accessible_population"):
            observation(accessible_population=None)

    def test_observed_required_source_errors_cannot_be_ignored(self) -> None:
        assessment = evaluate_source_accounting(
            (requirement(),),
            (observation(errors=("partial adapter failure",)),),
        )

        self.assertFalse(assessment.meets_policy)
        self.assertEqual(
            issue_pairs(assessment),
            (
                (
                    SourceIssueCode.REQUIRED_SOURCE_ERRORS_PRESENT,
                    "primary-source",
                ),
            ),
        )
        self.assertEqual(assessment.complete_source_ids, ())

    def test_multiple_declared_sources_are_rejected_before_composition(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "exactly one REQUIRED"):
            evaluate_source_accounting(
                (requirement("source-a"), requirement("source-b")),
                (observation("source-a"), observation("source-b")),
            )

    def test_source_identity_mismatch_is_incomplete(self) -> None:
        cases = (
            ({"system": "unrelated-cache"},),
            ({"locator": "repositories/unrelated"},),
        )
        for (changes,) in cases:
            with self.subTest(changes=changes):
                assessment = evaluate_source_accounting(
                    (requirement(),),
                    (observation(**changes),),
                )
                self.assertEqual(
                    issue_pairs(assessment),
                    ((SourceIssueCode.REQUIRED_SOURCE_IDENTITY_MISMATCH,
                      "primary-source"),),
                )

    def test_adapter_identity_or_version_mismatch_is_incomplete(self) -> None:
        for changes in (
            {"adapter_id": "other-adapter"},
            {"adapter_version": "test-2.0"},
        ):
            with self.subTest(changes=changes):
                assessment = evaluate_source_accounting(
                    (requirement(),),
                    (observation(**changes),),
                )
                self.assertEqual(
                    issue_pairs(assessment),
                    ((SourceIssueCode.REQUIRED_SOURCE_ADAPTER_MISMATCH,
                      "primary-source"),),
                )

    def test_authorization_context_mismatch_is_incomplete(self) -> None:
        assessment = evaluate_source_accounting(
            (requirement(),),
            (observation(authorization_context_id="other-context"),),
        )
        self.assertEqual(
            issue_pairs(assessment),
            ((SourceIssueCode.REQUIRED_SOURCE_AUTHORIZATION_MISMATCH,
              "primary-source"),),
        )

    def test_duplicate_required_source_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "duplicate"):
            evaluate_source_accounting(
                (requirement(), requirement()),
                (observation(),),
            )

    def test_duplicate_observation_source_ids_are_rejected_even_if_status_differs(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "duplicate"):
            evaluate_source_accounting(
                (requirement(),),
                (
                    observation(),
                    observation(
                        status=SourceObservationStatus.FAILED,
                        accessible_population=None,
                        errors=("adapter failed",),
                    ),
                ),
            )

    def test_undeclared_observation_is_rejected_not_treated_as_substitute(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "undeclared"):
            evaluate_source_accounting(
                (requirement("required-source"),),
                (observation("extra-source"),),
            )

    def test_empty_required_source_collection_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "at least one"):
            evaluate_source_accounting((), ())

    def test_requirement_collection_over_limit_is_rejected(self) -> None:
        requirements = tuple(
            requirement(f"source-{index:03d}")
            for index in range(MAX_SOURCE_ACCOUNTING_ENTRIES + 1)
        )

        with self.assertRaisesRegex(ModelValidationError, "entry limit"):
            evaluate_source_accounting(requirements, ())

    def test_observation_collection_over_limit_is_rejected_before_matching(self) -> None:
        observations = tuple(
            observation() for _ in range(MAX_SOURCE_ACCOUNTING_ENTRIES + 1)
        )

        with self.assertRaisesRegex(ModelValidationError, "entry limit"):
            evaluate_source_accounting((requirement(),), observations)

    def test_query_copies_caller_requirement_list(self) -> None:
        caller_requirements = [requirement("source-a")]
        parsed = query(caller_requirements)
        caller_requirements.clear()

        self.assertEqual(
            tuple(item.source_id for item in parsed.source_requirements),
            ("source-a",),
        )

    def test_nested_programmatic_lists_are_copied_before_use(self) -> None:
        assumptions = ["the source indexes repository metadata"]
        errors = ["bounded diagnostic"]
        declared = requirement(detection_assumptions=assumptions)
        observed = observation(errors=errors)
        assumptions.append("injected after construction")
        errors.append("injected after construction")

        self.assertEqual(
            declared.detection_assumptions,
            ("the source indexes repository metadata",),
        )
        self.assertEqual(observed.errors, ("bounded diagnostic",))

    def test_envelope_copies_caller_observation_list(self) -> None:
        caller_observations = [observation("source-a")]
        parsed = envelope(
            (requirement("source-a"),),
            caller_observations,
        )
        caller_observations.clear()

        self.assertEqual(
            tuple(item.source_id for item in parsed.source_observations),
            ("source-a",),
        )

    def test_explicit_empty_observations_are_valid_model_input(self) -> None:
        parsed = envelope((requirement(),), [])

        self.assertEqual(parsed.source_observations, ())
        self.assertEqual(parsed.to_dict()["source_observations"], [])

    def test_envelope_rejects_duplicate_undeclared_and_over_limit_observations(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "duplicate source_id"):
            envelope((requirement(),), [observation(), observation()])

        with self.assertRaisesRegex(ModelValidationError, "undeclared"):
            envelope((requirement(),), [observation("extra-source")])

        over_limit = [
            observation() for _ in range(MAX_SOURCE_ACCOUNTING_ENTRIES + 1)
        ]
        with self.assertRaisesRegex(ModelValidationError, "entry limit"):
            envelope((requirement(),), over_limit)

    def test_query_rejects_duplicate_and_over_limit_requirements_directly(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "duplicate source_id"):
            query([requirement(), requirement()])

        over_limit = [
            requirement(f"source-{index:03d}")
            for index in range(MAX_SOURCE_ACCOUNTING_ENTRIES + 1)
        ]
        with self.assertRaisesRegex(ModelValidationError, "entry limit"):
            query(over_limit)

    def test_source_identifiers_and_accessible_population_are_strict(self) -> None:
        for source_id in ("Primary-Source", "prímary-source", "primary/source"):
            with self.subTest(source_id=source_id):
                with self.assertRaises(ModelValidationError):
                    requirement(source_id)

        for field in (
            "source_id",
            "system",
            "locator",
            "adapter_id",
            "adapter_version",
            "authorization_context_id",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ModelValidationError, "placeholder"):
                    requirement(**{field: "unknown"})

        for field in (
            "source_id",
            "system",
            "locator",
            "adapter_id",
            "adapter_version",
            "authorization_context_id",
        ):
            with self.subTest(observation_field=field):
                with self.assertRaisesRegex(ModelValidationError, "placeholder"):
                    observation(**{field: "unknown"})

        for population in ("", "unknown", "*", "population\ninjected"):
            with self.subTest(population=population):
                with self.assertRaises(ModelValidationError):
                    requirement(accessible_population=population)

    def test_required_detection_assumptions_are_nonempty_unique_and_sorted(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "must not be empty"):
            requirement(detection_assumptions=())
        for placeholder in ("unknown", "unspecified", "none", "n/a", "*", "all"):
            with self.subTest(placeholder=placeholder):
                with self.assertRaisesRegex(ModelValidationError, "placeholder"):
                    requirement(detection_assumptions=(placeholder,))
        with self.assertRaisesRegex(ModelValidationError, "duplicates"):
            requirement(detection_assumptions=("same", "same"))
        declared = requirement(detection_assumptions=("assumption-b", "assumption-a"))
        self.assertEqual(
            declared.detection_assumptions,
            ("assumption-a", "assumption-b"),
        )

    def test_query_and_requirement_authorization_context_must_match(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "authorization_context_id"):
            query((requirement(authorization_context_id="other-context"),))

    def test_envelope_binds_coverage_and_observation_to_canonical_query(self) -> None:
        declared = requirement()
        declared_query = query((declared,))
        fingerprint = declared_query.fingerprint()
        observed = replace(observation(), query_fingerprint=fingerprint)
        base = envelope((declared,), (observed,))

        with self.assertRaisesRegex(ModelValidationError, "coverage_query_fingerprint"):
            replace(
                base,
                coverage_query_fingerprint="sha256:" + "1" * 64,
            )
        with self.assertRaisesRegex(ModelValidationError, "query_fingerprint"):
            replace(
                base,
                source_observations=(
                    replace(observed, query_fingerprint="sha256:" + "2" * 64),
                ),
            )

    def test_query_mutation_requires_new_coverage_and_observation_bindings(self) -> None:
        base = envelope((requirement(),), (observation(),))
        changed_query = replace(base.query, predicate="topic:other")
        with self.assertRaisesRegex(ModelValidationError, "coverage_query_fingerprint"):
            replace(base, query=changed_query)


if __name__ == "__main__":
    unittest.main()
