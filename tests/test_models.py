from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import unittest

from evidence_state_io import EvidenceEnvelope, EvidenceState, ModelValidationError
from evidence_state_io.models import datetime_to_json, parse_datetime

from tests.helpers import refresh_query_fingerprints, request_dict


class EvidenceStateModelTests(unittest.TestCase):
    def test_public_state_taxonomy_is_locked(self) -> None:
        self.assertEqual(
            [state.value for state in EvidenceState],
            [
                "PRESENT",
                "ABSENT_WITHIN_SCOPE",
                "NOT_OBSERVED",
                "PARTIAL",
                "STALE",
                "INACCESSIBLE",
                "PENDING_WINDOW",
                "FAILED",
                "CONTRADICTORY",
            ],
        )

    def test_envelope_round_trip_is_lossless(self) -> None:
        data = request_dict()["envelope"]
        parsed = EvidenceEnvelope.from_dict(data)
        reparsed = EvidenceEnvelope.from_dict(parsed.to_dict())
        self.assertEqual(parsed, reparsed)

    def test_direct_envelope_component_types_fail_with_model_errors(self) -> None:
        envelope = EvidenceEnvelope.from_dict(request_dict()["envelope"])
        for field in ("query", "coverage", "source_observations"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ModelValidationError, field):
                    replace(envelope, **{field: None})

    def test_optional_programmatic_notes_none_normalizes_to_empty_tuple(self) -> None:
        envelope = EvidenceEnvelope.from_dict(request_dict()["envelope"])
        normalized = replace(envelope, notes=None)
        self.assertEqual(normalized.notes, ())

    def test_programmatic_model_strings_are_trimmed(self) -> None:
        envelope = EvidenceEnvelope.from_dict(request_dict()["envelope"])
        query = replace(envelope.query, target="  repository search  ")
        source = replace(
            envelope.source_observations[0].descriptor,
            system="  github-search  ",
        )
        self.assertEqual(query.target, "repository search")
        self.assertEqual(source.system, "github-search")

    def test_all_nine_states_round_trip(self) -> None:
        for state in EvidenceState:
            with self.subTest(state=state.value):
                data = request_dict()["envelope"]
                data["state"] = state.value
                data["matched_count"] = 1 if state is EvidenceState.PRESENT else 0
                parsed = EvidenceEnvelope.from_dict(data)
                self.assertEqual(EvidenceEnvelope.from_dict(parsed.to_dict()).state, state)

    def test_numeric_schema_version_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["schema_version"] = 0.1
        with self.assertRaisesRegex(ModelValidationError, "string '1.0'"):
            EvidenceEnvelope.from_dict(data)

    def test_omitted_schema_version_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        del data["schema_version"]
        with self.assertRaisesRegex(ModelValidationError, "schema_version"):
            EvidenceEnvelope.from_dict(data)

    def test_legacy_and_unknown_schema_versions_are_rejected(self) -> None:
        for version in ("0.1", "0.2", "1.1", "2.0"):
            with self.subTest(version=version):
                data = request_dict()["envelope"]
                data["schema_version"] = version
                with self.assertRaisesRegex(
                    ModelValidationError, "supported string value '1.0'"
                ):
                    EvidenceEnvelope.from_dict(data)

    def test_utc_timestamp_is_canonicalized(self) -> None:
        value = parse_datetime("2026-08-21T08:00:00-04:00", "test")
        self.assertEqual(datetime_to_json(value), "2026-08-21T12:00:00Z")

    def test_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "UTC offset"):
            parse_datetime("2026-08-21T12:00:00", "test")

    def test_timestamp_with_more_than_six_fractional_digits_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "at most 6"):
            parse_datetime("2026-08-21T12:00:00.0000009Z", "test")

    def test_rfc3339_unknown_offset_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "unknown offset"):
            parse_datetime("2026-08-21T12:00:00-00:00", "test")

    def test_timestamp_alias_grammars_are_rejected(self) -> None:
        aliases = (
            " 2026-08-21T12:00:00Z",
            "2026-08-21 12:00:00Z",
            "20260821T120000Z",
            "2026-W34-5T12:00:00Z",
            "2026-08-21T12:00:00+00:00:30",
        )
        for value in aliases:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ModelValidationError, "ISO-8601"):
                    parse_datetime(value, "test")

    def test_timestamp_that_underflows_when_normalized_to_utc_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "representable in UTC"):
            parse_datetime("0001-01-01T00:00:00+23:59", "test")

    def test_programmatic_datetime_utc_underflow_is_rejected(self) -> None:
        value = datetime.fromisoformat("0001-01-01T00:00:00+23:59")
        with self.assertRaisesRegex(ModelValidationError, "representable in UTC"):
            datetime_to_json(value)

    def test_programmatic_query_datetime_utc_underflow_is_rejected(self) -> None:
        query = EvidenceEnvelope.from_dict(request_dict()["envelope"]).query
        value = datetime.fromisoformat("0001-01-01T00:00:00+23:59")
        with self.assertRaisesRegex(ModelValidationError, "representable in UTC"):
            replace(query, time_start=value, time_end=value)

    def test_unknown_envelope_field_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["complete"] = True
        with self.assertRaisesRegex(ModelValidationError, "unknown fields: complete"):
            EvidenceEnvelope.from_dict(data)

    def test_unknown_coverage_field_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["coverage_percent"] = 100
        with self.assertRaisesRegex(ModelValidationError, "coverage_percent"):
            EvidenceEnvelope.from_dict(data)

    def test_every_safety_relevant_coverage_fact_is_explicit(self) -> None:
        required = (
            "pagination_complete",
            "continuation_token_present",
            "partitions_complete",
            "timed_out",
            "interrupted",
            "permission_limited",
            "query_errors",
        )
        for field in required:
            with self.subTest(field=field):
                data = request_dict()["envelope"]
                del data["coverage"][field]
                with self.assertRaisesRegex(ModelValidationError, field):
                    EvidenceEnvelope.from_dict(data)

    def test_envelope_errors_must_be_explicit(self) -> None:
        data = request_dict()["envelope"]
        del data["errors"]
        with self.assertRaisesRegex(ModelValidationError, "errors"):
            EvidenceEnvelope.from_dict(data)

    def test_required_error_arrays_cannot_be_null(self) -> None:
        for path in ("coverage", "envelope"):
            with self.subTest(path=path):
                data = request_dict()["envelope"]
                if path == "coverage":
                    data["coverage"]["query_errors"] = None
                else:
                    data["errors"] = None
                with self.assertRaisesRegex(ModelValidationError, "must be an array"):
                    EvidenceEnvelope.from_dict(data)

    def test_present_requires_a_match(self) -> None:
        data = request_dict()["envelope"]
        data["state"] = "PRESENT"
        with self.assertRaisesRegex(ModelValidationError, "PRESENT requires"):
            EvidenceEnvelope.from_dict(data)

    def test_absent_within_scope_requires_zero_matches(self) -> None:
        data = request_dict()["envelope"]
        data["matched_count"] = 1
        with self.assertRaisesRegex(ModelValidationError, "matched_count equal to zero"):
            EvidenceEnvelope.from_dict(data)

    def test_exact_population_requires_denominator(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["population_units"] = None
        with self.assertRaisesRegex(ModelValidationError, "is required"):
            EvidenceEnvelope.from_dict(data)

    def test_unknown_population_rejects_denominator(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["population_basis"] = "UNKNOWN"
        with self.assertRaisesRegex(ModelValidationError, "must be null"):
            EvidenceEnvelope.from_dict(data)

    def test_exact_examined_count_cannot_exceed_population(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["examined_units"] = 101
        with self.assertRaisesRegex(ModelValidationError, "cannot exceed"):
            EvidenceEnvelope.from_dict(data)

    def test_huge_programmatic_count_is_rejected_before_serialization(self) -> None:
        coverage = EvidenceEnvelope.from_dict(request_dict()["envelope"]).coverage
        with self.assertRaisesRegex(ModelValidationError, "512-digit integer limit"):
            replace(coverage, examined_units=10**4999)

    def test_huge_json_model_count_is_rejected_before_serialization(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["examined_units"] = 10**4999
        with self.assertRaisesRegex(ModelValidationError, "512-digit integer limit"):
            EvidenceEnvelope.from_dict(data)

    def test_completion_flag_cannot_contradict_continuation(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["continuation_token_present"] = True
        with self.assertRaisesRegex(ModelValidationError, "continuation token remains"):
            EvidenceEnvelope.from_dict(data)

    def test_complete_page_flag_cannot_contradict_counts(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["pages_examined"] = 4
        with self.assertRaisesRegex(ModelValidationError, "incomplete page counts"):
            EvidenceEnvelope.from_dict(data)

    def test_pages_examined_without_expected_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["pages_expected"] = None
        with self.assertRaisesRegex(ModelValidationError, "pages_examined.*pages_expected"):
            EvidenceEnvelope.from_dict(data)

    def test_pages_expected_without_examined_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["pages_examined"] = None
        with self.assertRaisesRegex(ModelValidationError, "pages_examined.*pages_expected"):
            EvidenceEnvelope.from_dict(data)

    def test_partitions_examined_without_expected_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["partitions_expected"] = None
        with self.assertRaisesRegex(
            ModelValidationError, "partitions_examined.*partitions_expected"
        ):
            EvidenceEnvelope.from_dict(data)

    def test_partitions_expected_without_examined_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"]["partitions_examined"] = None
        with self.assertRaisesRegex(
            ModelValidationError, "partitions_examined.*partitions_expected"
        ):
            EvidenceEnvelope.from_dict(data)

    def test_declared_bound_cannot_exceed_computed_bound(self) -> None:
        data = request_dict()["envelope"]
        data["coverage"].update(
            examined_units=50,
            declared_lower_bound=1.0,
            pages_examined=5,
            pagination_complete=True,
        )
        with self.assertRaisesRegex(ModelValidationError, "cannot exceed"):
            EvidenceEnvelope.from_dict(data)

    def test_query_end_cannot_precede_start(self) -> None:
        data = request_dict()["envelope"]
        data["query"]["time_start"] = "2026-08-22T00:00:00Z"
        with self.assertRaisesRegex(ModelValidationError, "must not precede"):
            EvidenceEnvelope.from_dict(data)

    def test_bounded_interval_fields_are_required(self) -> None:
        for field in ("time_start", "time_end"):
            with self.subTest(field=field):
                data = request_dict()["envelope"]
                del data["query"][field]
                with self.assertRaisesRegex(ModelValidationError, field):
                    EvidenceEnvelope.from_dict(data)

    def test_bounded_interval_fields_cannot_be_null(self) -> None:
        for field in ("time_start", "time_end"):
            with self.subTest(field=field):
                data = request_dict()["envelope"]
                data["query"][field] = None
                with self.assertRaisesRegex(ModelValidationError, "ISO-8601"):
                    EvidenceEnvelope.from_dict(data)

    def test_query_end_before_observation_is_valid(self) -> None:
        data = request_dict()["envelope"]
        data["query"]["time_end"] = "2026-08-21T11:59:59Z"
        wrapper = {"envelope": data}
        refresh_query_fingerprints(wrapper)
        EvidenceEnvelope.from_dict(data)

    def test_query_end_equal_to_observation_is_valid(self) -> None:
        data = request_dict()["envelope"]
        data["query"]["time_end"] = data["observed_at"]
        wrapper = {"envelope": data}
        refresh_query_fingerprints(wrapper)
        EvidenceEnvelope.from_dict(data)

    def test_query_end_after_observation_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["query"]["time_end"] = "2026-08-21T12:04:00.000001Z"
        data["query"]["source_requirements"][0]["finality_horizon"] = (
            "2026-08-21T12:04:00.000001Z"
        )
        with self.assertRaisesRegex(ModelValidationError, "must not be after observed_at"):
            EvidenceEnvelope.from_dict(data)

    def test_source_index_after_observation_is_rejected(self) -> None:
        data = request_dict()["envelope"]
        data["source_observations"][0]["descriptor"]["index_as_of"] = (
            "2026-08-21T12:04:00.000001Z"
        )
        with self.assertRaisesRegex(
            ModelValidationError,
            "source_observations descriptor index_as_of must not be after observed_at",
        ):
            EvidenceEnvelope.from_dict(data)

    def test_source_index_equal_to_observation_is_valid(self) -> None:
        data = request_dict()["envelope"]
        data["source_observations"][0]["descriptor"]["index_as_of"] = data[
            "observed_at"
        ]
        EvidenceEnvelope.from_dict(data)

    def test_submicrosecond_query_end_is_rejected_instead_of_truncated(self) -> None:
        data = request_dict()["envelope"]
        data["query"]["time_end"] = "2026-08-21T12:00:00.0000009Z"
        with self.assertRaisesRegex(ModelValidationError, "at most 6"):
            EvidenceEnvelope.from_dict(data)

    def test_evidence_strings_reject_newlines(self) -> None:
        data = request_dict()["envelope"]
        data["query"]["target"] = "repositories\ninjected line"
        with self.assertRaisesRegex(ModelValidationError, "single line"):
            EvidenceEnvelope.from_dict(data)

        for field in ("target", "predicate"):
            for placeholder in ("unknown", "unspecified", "none", "n/a"):
                with self.subTest(field=field, placeholder=placeholder):
                    data = request_dict()["envelope"]
                    data["query"][field] = placeholder
                    with self.assertRaisesRegex(ModelValidationError, "placeholder"):
                        EvidenceEnvelope.from_dict(data)

        for placeholder in ("unknown", "unspecified", "none", "n/a", "*", "all"):
            with self.subTest(exclusion_placeholder=placeholder):
                data = request_dict()["envelope"]
                data["query"]["exclusions"] = [placeholder]
                with self.assertRaisesRegex(ModelValidationError, "placeholder"):
                    EvidenceEnvelope.from_dict(data)

    def test_scope_qualification_names_authorization_and_exclusions(self) -> None:
        envelope = EvidenceEnvelope.from_dict(request_dict()["envelope"])
        qualification = envelope.query.qualification()
        self.assertIn("authorization=", qualification)
        self.assertIn("unindexed content", qualification)


if __name__ == "__main__":
    unittest.main()
