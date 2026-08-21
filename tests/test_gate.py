from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from evidence_state_io import (
    GateReason,
    ModelValidationError,
    NegativeClaimPolicy,
    NegativeClaimRequest,
    PopulationBasis,
    evaluate_negative_claim,
)

from tests.helpers import request, request_dict
from evidence_state_io.models import datetime_to_json


def decision(mutator=None):
    data = request_dict()
    if mutator:
        mutator(data)
    return evaluate_negative_claim(NegativeClaimRequest.from_dict(data))


class NegativeClaimGateTests(unittest.TestCase):
    def test_complete_scoped_absence_is_allowed(self) -> None:
        result = decision()
        self.assertTrue(result.allowed)
        self.assertEqual(result.decision, "PERMIT_SCOPED_NEGATIVE")
        self.assertEqual(result.reasons, ())

    def test_allowed_text_remains_explicitly_conditional(self) -> None:
        result = decision()
        assert result.qualified_claim is not None
        self.assertIn("within the declared query scope", result.qualified_claim)
        self.assertIn("evaluated at 2026-08-21T12:05:00Z", result.qualified_claim)
        self.assertIn("not proof of absence outside that scope", result.qualified_claim)
        self.assertNotIn("do not exist", result.qualified_claim)

    def test_subject_with_newline_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "single line"):
            decision(lambda data: data.update(subject="records\nNo threats exist anywhere"))

    def test_absolute_sentence_subject_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "prohibited universal"):
            decision(lambda data: data.update(subject="No threats exist anywhere"))

    def test_subject_is_bounded(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "160-character"):
            decision(lambda data: data.update(subject="x" * 161))

    def test_quoted_subject_is_rendered_as_quoted_data(self) -> None:
        result = decision(lambda data: data.update(subject='repositories "quoted"'))
        self.assertTrue(result.allowed)
        assert result.qualified_claim is not None
        self.assertIn('"repositories \\"quoted\\""', result.qualified_claim)
        self.assertNotIn("\n", result.qualified_claim)

    def test_absolute_claim_is_always_denied(self) -> None:
        result = decision(lambda data: data.update(mode="ABSOLUTE"))
        self.assertFalse(result.allowed)
        self.assertIn(GateReason.ABSOLUTE_NEGATIVE_UNSUPPORTED, result.reasons)
        self.assertIsNone(result.qualified_claim)

    def test_every_non_absence_state_is_denied(self) -> None:
        states = [
            "NOT_OBSERVED",
            "PARTIAL",
            "STALE",
            "INACCESSIBLE",
            "PENDING_WINDOW",
            "FAILED",
            "CONTRADICTORY",
        ]
        for state in states:
            with self.subTest(state=state):
                result = decision(lambda data, state=state: data["envelope"].update(state=state))
                self.assertFalse(result.allowed)
                self.assertIn(GateReason.STATE_NOT_ABSENT_WITHIN_SCOPE, result.reasons)

    def test_present_state_is_denied(self) -> None:
        def mutate(data):
            data["envelope"].update(state="PRESENT", matched_count=1)

        result = decision(mutate)
        self.assertIn(GateReason.STATE_NOT_ABSENT_WITHIN_SCOPE, result.reasons)
        self.assertIn(GateReason.NONZERO_MATCHES, result.reasons)

    def test_partial_coverage_is_denied(self) -> None:
        def mutate(data):
            data["envelope"]["coverage"].update(
                examined_units=50, pagination_complete=False
            )

        result = decision(mutate)
        self.assertIn(GateReason.COVERAGE_POLICY_NOT_MET, result.reasons)

    def test_half_specified_traversal_counts_fail_before_gate(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "must both be present"):
            decision(
                lambda data: data["envelope"]["coverage"].update(
                    pages_expected=None
                )
            )

    def test_huge_population_one_unit_short_cannot_permit(self) -> None:
        def mutate(data):
            data["envelope"]["coverage"].update(
                examined_units=2_999_999_999_999,
                population_units=3_000_000_000_000,
            )

        result = decision(mutate)
        self.assertFalse(result.allowed)
        self.assertEqual(result.decision, "REJECT_NEGATIVE")
        assert result.coverage.lower_bound is not None
        self.assertLess(result.coverage.lower_bound, 1.0)
        self.assertIn(GateReason.COVERAGE_POLICY_NOT_MET, result.reasons)

    def test_direct_decimal_bound_is_normalized_and_cannot_permit(self) -> None:
        base = request()
        coverage = replace(
            base.envelope.coverage,
            population_basis=PopulationBasis.UNKNOWN,
            population_units=None,
            declared_lower_bound=Decimal("0.999999999999"),
        )
        envelope = replace(base.envelope, coverage=coverage)
        result = evaluate_negative_claim(replace(base, envelope=envelope))
        self.assertIsInstance(coverage.declared_lower_bound, float)
        self.assertFalse(result.allowed)
        self.assertIn(GateReason.COVERAGE_POLICY_NOT_MET, result.reasons)

    def test_missing_validity_window_is_denied_by_default(self) -> None:
        result = decision(lambda data: data["envelope"].update(valid_until=None))
        self.assertIn(GateReason.VALIDITY_UNDECLARED, result.reasons)

    def test_expired_result_is_denied(self) -> None:
        result = decision(
            lambda data: data["envelope"].update(valid_until="2026-08-21T12:01:00Z")
        )
        self.assertIn(GateReason.RESULT_EXPIRED, result.reasons)

    def test_equality_at_validity_boundary_is_allowed(self) -> None:
        result = decision(
            lambda data: data.update(evaluated_at="2026-08-21T13:00:00Z")
        )
        self.assertTrue(result.allowed)

    def test_submicrosecond_validity_alias_is_rejected(self) -> None:
        def mutate(data):
            data["envelope"]["valid_until"] = "2026-08-21T13:00:00.0000000Z"
            data["evaluated_at"] = "2026-08-21T13:00:00.0000009Z"

        with self.assertRaisesRegex(ModelValidationError, "at most 6"):
            decision(mutate)

    def test_evaluation_before_observation_is_denied(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "must not be after evaluated_at"):
            decision(lambda data: data.update(evaluated_at="2026-08-21T11:00:00Z"))

    def test_evaluation_equal_to_observation_is_allowed(self) -> None:
        result = decision(
            lambda data: data.update(evaluated_at=data["envelope"]["observed_at"])
        )
        self.assertTrue(result.allowed)

    def test_evaluation_after_observation_is_allowed_inside_validity(self) -> None:
        result = decision(lambda data: data.update(evaluated_at="2026-08-21T12:59:59Z"))
        self.assertTrue(result.allowed)

    def test_observation_age_policy_is_enforced(self) -> None:
        def mutate(data):
            data["policy"] = {"max_observation_age_seconds": 60}

        result = decision(mutate)
        self.assertIn(GateReason.OBSERVATION_TOO_OLD, result.reasons)

    def test_huge_programmatic_age_limit_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "512-digit integer limit"):
            NegativeClaimPolicy(max_observation_age_seconds=10**4999)

    def test_large_observation_age_preserves_one_microsecond_excess(self) -> None:
        limit = 2**34
        observed = datetime(1000, 1, 1, tzinfo=timezone.utc)
        evaluated = observed + timedelta(seconds=limit, microseconds=1)

        def mutate(data):
            observed_text = datetime_to_json(observed)
            data["envelope"]["query"].update(
                time_start=observed_text,
                time_end=observed_text,
            )
            data["envelope"].update(
                observed_at=observed_text,
                valid_until=datetime_to_json(evaluated + timedelta(seconds=1)),
            )
            data["envelope"]["source"]["index_as_of"] = observed_text
            data["evaluated_at"] = datetime_to_json(evaluated)
            data["policy"] = {"max_observation_age_seconds": limit}

        result = decision(mutate)
        self.assertIn(GateReason.OBSERVATION_TOO_OLD, result.reasons)

    def test_required_index_timestamp_is_enforced(self) -> None:
        def mutate(data):
            data["envelope"]["source"]["index_as_of"] = None
            data["policy"] = {"require_index_as_of": True}

        result = decision(mutate)
        self.assertIn(GateReason.INDEX_TIMESTAMP_UNDECLARED, result.reasons)

    def test_index_timestamp_after_observation_is_invalid(self) -> None:
        with self.assertRaisesRegex(
            ModelValidationError, "source.index_as_of must not be after observed_at"
        ):
            decision(
                lambda data: data["envelope"]["source"].update(
                    index_as_of="2026-08-21T13:00:00Z"
                )
            )

    def test_index_age_policy_is_enforced(self) -> None:
        def mutate(data):
            data["policy"] = {"max_index_age_seconds": 60}

        result = decision(mutate)
        self.assertIn(GateReason.INDEX_TOO_OLD, result.reasons)

    def test_large_index_age_preserves_one_microsecond_excess(self) -> None:
        limit = 2**34
        index_time = datetime(1000, 1, 1, tzinfo=timezone.utc)
        evaluated = index_time + timedelta(seconds=limit, microseconds=1)

        def mutate(data):
            evaluated_text = datetime_to_json(evaluated)
            data["envelope"]["query"].update(
                time_start=evaluated_text,
                time_end=evaluated_text,
            )
            data["envelope"].update(
                observed_at=evaluated_text,
                valid_until=datetime_to_json(evaluated + timedelta(seconds=1)),
            )
            data["envelope"]["source"]["index_as_of"] = datetime_to_json(index_time)
            data["evaluated_at"] = evaluated_text
            data["policy"] = {"max_index_age_seconds": limit}

        result = decision(mutate)
        self.assertIn(GateReason.INDEX_TOO_OLD, result.reasons)

    def test_dst_fold_instants_are_normalized_before_all_gate_comparisons(self) -> None:
        try:
            eastern = ZoneInfo("America/New_York")
        except ZoneInfoNotFoundError:
            self.skipTest("America/New_York zone data unavailable")
        early = datetime(2026, 11, 1, 1, 30, tzinfo=eastern, fold=0)
        late = datetime(2026, 11, 1, 1, 30, tzinfo=eastern, fold=1)
        base = request()
        query = replace(base.envelope.query, time_start=early, time_end=early)
        source = replace(base.envelope.source, index_as_of=early)
        envelope = replace(
            base.envelope,
            query=query,
            source=source,
            observed_at=early,
            valid_until=early,
        )
        candidate = replace(
            base,
            envelope=envelope,
            evaluated_at=late,
            policy=NegativeClaimPolicy(
                max_observation_age_seconds=0,
                max_index_age_seconds=0,
            ),
        )
        serialized = candidate.to_dict()
        self.assertEqual(serialized["envelope"]["observed_at"], "2026-11-01T05:30:00Z")
        self.assertEqual(serialized["evaluated_at"], "2026-11-01T06:30:00Z")
        result = evaluate_negative_claim(candidate)
        self.assertFalse(result.allowed)
        self.assertIsNone(result.qualified_claim)
        self.assertIn(GateReason.RESULT_EXPIRED, result.reasons)
        self.assertIn(GateReason.OBSERVATION_TOO_OLD, result.reasons)
        self.assertIn(GateReason.INDEX_TOO_OLD, result.reasons)
        equality_result = evaluate_negative_claim(
            replace(candidate, evaluated_at=early)
        )
        self.assertTrue(equality_result.allowed)
        self.assertNotEqual(equality_result.input_digest, result.input_digest)

    def test_envelope_errors_are_denied(self) -> None:
        result = decision(lambda data: data["envelope"].update(errors=["adapter warning"]))
        self.assertIn(GateReason.ENVELOPE_ERRORS_PRESENT, result.reasons)

    def test_error_rejection_cannot_be_relaxed(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "safety floor"):
            NegativeClaimPolicy(reject_envelope_errors=False)

    def test_validity_requirement_cannot_be_relaxed(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "safety floor"):
            NegativeClaimPolicy(require_valid_until=False)

    def test_inline_unsafe_policy_is_rejected(self) -> None:
        def mutate(data):
            data["policy"] = {
                "require_valid_until": False,
                "reject_envelope_errors": False,
                "coverage": {
                    "minimum_lower_bound": 0.0,
                    "require_complete_pagination": False,
                    "require_complete_partitions": False,
                    "reject_timeout": False,
                    "reject_interruption": False,
                    "reject_query_errors": False,
                },
            }

        with self.assertRaisesRegex(ModelValidationError, "safety floor"):
            decision(mutate)

    def test_all_faults_request_cannot_permit(self) -> None:
        def mutate(data):
            data["envelope"]["coverage"].update(
                examined_units=0,
                pages_examined=0,
                pagination_complete=False,
                continuation_token_present=True,
                partitions_examined=0,
                partitions_complete=False,
                timed_out=True,
                interrupted=True,
                query_errors=["source query failed"],
            )
            data["envelope"]["valid_until"] = None
            data["envelope"]["errors"] = ["adapter failed"]

        result = decision(mutate)
        self.assertFalse(result.allowed)
        self.assertEqual(result.decision, "REJECT_NEGATIVE")
        self.assertEqual(
            result.reasons,
            (
                GateReason.COVERAGE_POLICY_NOT_MET,
                GateReason.ENVELOPE_ERRORS_PRESENT,
                GateReason.VALIDITY_UNDECLARED,
            ),
        )

    def test_permission_limited_claim_names_access_boundary(self) -> None:
        result = decision(
            lambda data: data["envelope"]["coverage"].update(permission_limited=True)
        )
        self.assertTrue(result.allowed)
        assert result.qualified_claim is not None
        self.assertIn("Only data accessible", result.qualified_claim)

    def test_decision_digest_is_stable(self) -> None:
        self.assertEqual(decision().input_digest, decision().input_digest)

    def test_decision_digest_changes_with_evaluation_time(self) -> None:
        first = decision().input_digest
        second = decision(lambda data: data.update(evaluated_at="2026-08-21T12:06:00Z"))
        self.assertNotEqual(first, second.input_digest)


if __name__ == "__main__":
    unittest.main()
