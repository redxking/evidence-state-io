"""The producer-side envelope builder.

The builder's job is to make the honest path the easy one. Most of these tests
check that the dishonest path is not available: that no completeness fact has an
optimistic default, that the caller cannot declare the evidence state, and that
the derivation never reaches in-scope absence from facts that do not support it.
"""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone

from evidence_state_io.builder import EvidenceBuilder, SourceReading
from evidence_state_io.emptybench import seed_profile_context
from evidence_state_io.errors import ModelValidationError
from evidence_state_io.gate import evaluate_negative_claim
from evidence_state_io.models import (
    CompositionMode,
    CoverageProfileReference,
    EvidenceState,
    PopulationBasis,
    SourceObservationStatus,
)

UTC = timezone.utc
TIME_START = datetime(2026, 8, 21, 0, 0, tzinfo=UTC)
TIME_END = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
HORIZON = datetime(2026, 8, 21, 12, 4, tzinfo=UTC)
READ_AT = datetime(2026, 8, 21, 12, 4, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 8, 21, 12, 5, tzinfo=UTC)
VALID_UNTIL = datetime(2026, 8, 21, 13, 0, tzinfo=UTC)


def _profile_reference() -> CoverageProfileReference:
    context = seed_profile_context()
    profile = context.snapshot.records[0].profile
    return CoverageProfileReference(
        registry_id=context.snapshot.registry_id,
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        profile_digest=profile.profile_digest,
    )


def _seed_builder() -> EvidenceBuilder:
    """A builder configured to match the packaged governed profile."""

    return EvidenceBuilder(
        target="GitHub repository search",
        predicate="topic:evidence-state language:Python",
        authorization_boundary="public repositories visible to the adapter token",
        authorization_context_id="public-search-adapter-context",
        time_start=TIME_START,
        time_end=TIME_END,
        exclusions=("deleted repositories", "unindexed content"),
    ).require_source(
        source_id="github-public-repositories",
        system="github-search",
        locator="repositories/search",
        adapter_id="github-search-adapter",
        adapter_version="example-0.4",
        accessible_population="public-repositories-visible-to-adapter",
        detection_assumptions=("repository is indexed by the declared search endpoint",),
        finality_horizon=HORIZON,
        profile_ref=_profile_reference(),
    )


def _complete_reading(source_id: str = "github-public-repositories") -> SourceReading:
    return SourceReading(
        source_id=source_id,
        matched_count=0,
        examined_units=100,
        population_basis=PopulationBasis.EXACT,
        population_units=100,
        pages_examined=5,
        pages_expected=5,
        partitions_examined=2,
        partitions_expected=2,
        pagination_complete=True,
        continuation_token_present=False,
        partitions_complete=True,
        timed_out=False,
        interrupted=False,
        permission_limited=False,
        observed_at=READ_AT,
        index_as_of=READ_AT,
        valid_until=VALID_UNTIL,
    )


class EndToEndTests(unittest.TestCase):
    def test_a_complete_reading_reaches_a_permit(self) -> None:
        """The whole point: describe what you did, get an assessable claim."""

        request = (
            _seed_builder()
            .record(_complete_reading())
            .request(
                subject="repositories matching the query",
                evaluated_at=EVALUATED_AT,
            )
        )
        decision = evaluate_negative_claim(request, seed_profile_context())

        self.assertTrue(decision.allowed, [reason.value for reason in decision.reasons])
        self.assertEqual(decision.decision, "PERMIT_SCOPED_NEGATIVE")

    def test_the_envelope_binds_its_own_query_fingerprint(self) -> None:
        envelope = _seed_builder().record(_complete_reading()).build()
        expected = envelope.query.fingerprint()

        self.assertEqual(envelope.coverage_query_fingerprint, expected)
        for observation in envelope.source_observations:
            self.assertEqual(observation.query_fingerprint, expected)


class DerivationTests(unittest.TestCase):
    """The caller supplies facts. The state is derived from them."""

    def test_the_builder_takes_no_state_from_the_caller(self) -> None:
        self.assertNotIn("state", SourceReading.__dataclass_fields__)

    def test_no_completeness_fact_has_an_optimistic_default(self) -> None:
        """A caller who has not thought about these must not inherit 'yes'."""

        required = {
            "pagination_complete",
            "continuation_token_present",
            "partitions_complete",
            "timed_out",
            "interrupted",
            "permission_limited",
            "examined_units",
            "matched_count",
            "population_basis",
            "observed_at",
        }
        for name in sorted(required):
            with self.subTest(field=name):
                field = SourceReading.__dataclass_fields__[name]
                self.assertIs(
                    field.default,
                    field.default_factory,  # type: ignore[comparison-overlap]
                    f"{name} has a default and must not",
                )

    def test_a_complete_unfaulted_zero_match_reading_is_in_scope_absence(self) -> None:
        self.assertIs(_complete_reading().derived_state(), EvidenceState.ABSENT_WITHIN_SCOPE)

    def test_a_match_is_presence_whatever_else_went_wrong(self) -> None:
        reading = replace(
            _complete_reading(),
            matched_count=3,
            timed_out=True,
            pagination_complete=False,
            query_errors=("partial failure",),
        )
        self.assertIs(reading.derived_state(), EvidenceState.PRESENT)

    def test_a_faulted_run_never_reports_absence(self) -> None:
        """An enumeration that broke partway is not a search that found nothing."""

        cases = {
            "errors": (replace(_complete_reading(), query_errors=("boom",)), EvidenceState.FAILED),
            "timeout": (replace(_complete_reading(), timed_out=True), EvidenceState.NOT_OBSERVED),
            "interrupted": (
                replace(_complete_reading(), interrupted=True),
                EvidenceState.NOT_OBSERVED,
            ),
        }
        for label, (reading, expected) in cases.items():
            with self.subTest(case=label):
                self.assertIs(reading.derived_state(), expected)

    def test_an_incomplete_enumeration_is_partial(self) -> None:
        for name in ("pagination_complete", "partitions_complete"):
            with self.subTest(field=name):
                reading = replace(_complete_reading(), **{name: False})
                self.assertIs(reading.derived_state(), EvidenceState.PARTIAL)
        with self.subTest(field="continuation_token_present"):
            reading = replace(_complete_reading(), continuation_token_present=True)
            self.assertIs(reading.derived_state(), EvidenceState.PARTIAL)

    def test_a_failed_reading_declares_no_accessible_population(self) -> None:
        envelope = (
            _seed_builder().record(replace(_complete_reading(), query_errors=("boom",))).build()
        )
        observation = envelope.source_observations[0]

        self.assertIs(observation.status, SourceObservationStatus.FAILED)
        self.assertIsNone(observation.accessible_population)
        self.assertIs(envelope.state, EvidenceState.FAILED)


class TimeBoundaryTests(unittest.TestCase):
    def test_observed_at_defaults_to_the_last_reading(self) -> None:
        envelope = _seed_builder().record(_complete_reading()).build()
        self.assertEqual(envelope.observed_at, READ_AT)

    def test_an_envelope_cannot_be_sealed_before_its_last_reading(self) -> None:
        builder = _seed_builder().record(_complete_reading())
        with self.assertRaisesRegex(ModelValidationError, "precedes the last source reading"):
            builder.build(observed_at=TIME_END)

    def test_valid_until_defaults_to_the_earliest_boundary(self) -> None:
        envelope = _seed_builder().record(_complete_reading()).build()
        self.assertEqual(envelope.valid_until, VALID_UNTIL)

    def test_an_envelope_cannot_outlive_its_sources(self) -> None:
        builder = _seed_builder().record(_complete_reading())
        with self.assertRaisesRegex(ModelValidationError, "outlives the earliest boundary"):
            builder.build(valid_until=datetime(2026, 8, 21, 23, 0, tzinfo=UTC))


class DeclarationTests(unittest.TestCase):
    def test_an_undeclared_source_cannot_report(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "was not declared"):
            _seed_builder().record(_complete_reading("some-other-source"))

    def test_a_source_cannot_report_twice(self) -> None:
        builder = _seed_builder().record(_complete_reading())
        with self.assertRaisesRegex(ModelValidationError, "already reported"):
            builder.record(_complete_reading())

    def test_a_source_cannot_be_declared_twice(self) -> None:
        builder = _seed_builder()
        with self.assertRaisesRegex(ModelValidationError, "already declared"):
            builder.require_source(
                source_id="github-public-repositories",
                system="x",
                locator="y",
                adapter_id="z",
                adapter_version="1.0",
                accessible_population="p",
                detection_assumptions=("a",),
            )

    def test_every_declared_source_must_report(self) -> None:
        builder = _seed_builder().require_source(
            source_id="mirror-public-repositories",
            system="mirror-search",
            locator="repositories/search",
            adapter_id="mirror-search-adapter",
            adapter_version="example-0.4",
            accessible_population="public-repositories-visible-to-adapter",
            detection_assumptions=("repository is indexed by the declared search endpoint",),
            finality_horizon=HORIZON,
        )
        builder.record(_complete_reading())
        with self.assertRaisesRegex(ModelValidationError, "must report"):
            builder.build(composition=CompositionMode.CORROBORATION)

    def test_record_rejects_a_non_reading(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "expects a SourceReading"):
            _seed_builder().record({"source_id": "github-public-repositories"})  # type: ignore[arg-type]


class CompositionTests(unittest.TestCase):
    def _two_source_builder(self) -> EvidenceBuilder:
        return _seed_builder().require_source(
            source_id="mirror-public-repositories",
            system="mirror-search",
            locator="repositories/search",
            adapter_id="mirror-search-adapter",
            adapter_version="example-0.4",
            accessible_population="public-repositories-visible-to-adapter",
            detection_assumptions=("repository is indexed by the declared search endpoint",),
            finality_horizon=HORIZON,
        )

    def test_several_sources_need_a_declared_composition_mode(self) -> None:
        builder = self._two_source_builder()
        builder.record(_complete_reading())
        builder.record(_complete_reading("mirror-public-repositories"))

        with self.assertRaisesRegex(ModelValidationError, "declared composition mode"):
            builder.build()

    def test_aggregate_coverage_is_the_strongest_source_and_never_a_sum(self) -> None:
        """Anything larger claims coverage out of an overlap nobody measured."""

        builder = self._two_source_builder()
        builder.record(_complete_reading())
        builder.record(
            replace(
                _complete_reading("mirror-public-repositories"),
                examined_units=60,
                pages_examined=3,
                pagination_complete=False,
            )
        )
        envelope = builder.build(composition=CompositionMode.CORROBORATION)

        self.assertEqual(envelope.coverage.examined_units, 100)
        self.assertEqual(envelope.schema_version, "1.1")
        self.assertIs(envelope.state, EvidenceState.PARTIAL, "the weak source must show")

    def test_each_source_carries_its_own_assessment_when_composed(self) -> None:
        builder = self._two_source_builder()
        builder.record(_complete_reading())
        builder.record(_complete_reading("mirror-public-repositories"))
        envelope = builder.build(composition=CompositionMode.CORROBORATION)

        for observation in envelope.source_observations:
            self.assertIsNotNone(observation.coverage)
            self.assertIsNotNone(observation.state)
            self.assertIsNotNone(observation.observed_at)
            self.assertEqual(observation.matched_count, 0)

    def test_a_single_source_envelope_carries_no_per_source_assessment(self) -> None:
        envelope = _seed_builder().record(_complete_reading()).build()

        self.assertEqual(envelope.schema_version, "1.0")
        for observation in envelope.source_observations:
            self.assertIsNone(observation.coverage)
            self.assertIsNone(observation.state)

    def test_presence_at_any_source_is_presence_for_the_set(self) -> None:
        builder = self._two_source_builder()
        builder.record(_complete_reading())
        builder.record(replace(_complete_reading("mirror-public-repositories"), matched_count=2))
        envelope = builder.build(composition=CompositionMode.CORROBORATION)

        self.assertIs(envelope.state, EvidenceState.PRESENT)
        self.assertEqual(envelope.matched_count, 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
