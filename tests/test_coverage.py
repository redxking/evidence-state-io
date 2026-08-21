from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
import unittest

from evidence_state_io import (
    CoverageEvidence,
    CoverageIssue,
    CoveragePolicy,
    ModelValidationError,
    PopulationBasis,
    evaluate_coverage,
)

from tests.helpers import request_dict


def coverage_data() -> dict:
    return deepcopy(request_dict()["envelope"]["coverage"])


class CoverageEvaluationTests(unittest.TestCase):
    def test_complete_exact_population_passes(self) -> None:
        assessment = evaluate_coverage(CoverageEvidence.from_dict(coverage_data()))
        self.assertTrue(assessment.meets_policy)
        self.assertEqual(assessment.lower_bound, 1.0)
        self.assertEqual(assessment.issues, ())

    def test_partial_population_uses_conservative_minimum(self) -> None:
        data = coverage_data()
        data.update(
            examined_units=60,
            pages_examined=3,
            pagination_complete=False,
            continuation_token_present=True,
        )
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertEqual(assessment.lower_bound, 0.6)
        self.assertEqual(
            assessment.issues,
            (
                CoverageIssue.BELOW_MINIMUM,
                CoverageIssue.PAGINATION_INCOMPLETE,
                CoverageIssue.CONTINUATION_PRESENT,
            ),
        )

    def test_empty_exact_population_is_fully_covered(self) -> None:
        data = coverage_data()
        data.update(examined_units=0, population_units=0, pages_examined=0, pages_expected=0)
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertEqual(assessment.lower_bound, 1.0)
        self.assertTrue(assessment.meets_policy)

    def test_huge_exact_population_equality_is_fully_covered(self) -> None:
        data = coverage_data()
        data.update(
            examined_units=3_000_000_000_000,
            population_units=3_000_000_000_000,
        )
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertEqual(assessment.lower_bound, 1.0)
        self.assertTrue(assessment.meets_policy)

    def test_huge_exact_population_one_unit_short_is_not_promoted(self) -> None:
        data = coverage_data()
        data.update(
            examined_units=2_999_999_999_999,
            population_units=3_000_000_000_000,
        )
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        assert assessment.lower_bound is not None
        self.assertLess(assessment.lower_bound, 1.0)
        self.assertFalse(assessment.meets_policy)
        self.assertIn(CoverageIssue.BELOW_MINIMUM, assessment.issues)

    def test_serialized_ratio_never_exceeds_exact_fraction(self) -> None:
        data = coverage_data()
        data.update(examined_units=1, population_units=10)
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        assert assessment.lower_bound is not None
        self.assertLessEqual(
            Fraction.from_float(assessment.lower_bound), Fraction(1, 10)
        )

    def test_declared_full_bound_cannot_override_one_unit_short_ratio(self) -> None:
        data = coverage_data()
        data.update(
            examined_units=2_999_999_999_999,
            population_units=3_000_000_000_000,
            declared_lower_bound=1.0,
        )
        with self.assertRaisesRegex(ModelValidationError, "cannot exceed"):
            CoverageEvidence.from_dict(data)

    def test_high_precision_declared_bound_below_one_is_not_promoted(self) -> None:
        data = coverage_data()
        data.update(
            population_basis="UNKNOWN",
            population_units=None,
            declared_lower_bound=Decimal("0.999999999999"),
        )
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        assert assessment.lower_bound is not None
        self.assertLess(assessment.lower_bound, 1.0)
        self.assertFalse(assessment.meets_policy)
        self.assertIn(CoverageIssue.BELOW_MINIMUM, assessment.issues)

    def test_direct_decimal_constructor_normalizes_and_round_trips(self) -> None:
        base = CoverageEvidence.from_dict(coverage_data())
        evidence = replace(
            base,
            population_basis=PopulationBasis.UNKNOWN,
            population_units=None,
            declared_lower_bound=Decimal("0.123456789012"),
        )
        self.assertIsInstance(evidence.declared_lower_bound, float)
        self.assertEqual(CoverageEvidence.from_dict(evidence.to_dict()), evidence)

    def test_overprecise_declared_bound_is_rejected_not_rounded(self) -> None:
        data = coverage_data()
        data.update(
            population_basis="UNKNOWN",
            population_units=None,
            declared_lower_bound=Decimal("0.9999999999996"),
        )
        with self.assertRaisesRegex(ModelValidationError, "at most 12 decimal places"):
            CoverageEvidence.from_dict(data)

    def test_fraction_precision_validation_ignores_decimal_context(self) -> None:
        for precision in (1, 2, 5):
            with self.subTest(precision=precision), localcontext() as context:
                context.prec = precision
                data = coverage_data()
                data.update(
                    population_basis="UNKNOWN",
                    population_units=None,
                    declared_lower_bound=Decimal("0.1234567890123"),
                )
                with self.assertRaisesRegex(
                    ModelValidationError, "at most 12 decimal places"
                ):
                    CoverageEvidence.from_dict(data)

    def test_accepted_fraction_normalization_is_decimal_context_invariant(self) -> None:
        normalized = []
        for precision in (1, 2, 5):
            with localcontext() as context:
                context.prec = precision
                data = coverage_data()
                data.update(
                    population_basis="UNKNOWN",
                    population_units=None,
                    declared_lower_bound=Decimal("0.123456789012"),
                )
                normalized.append(
                    CoverageEvidence.from_dict(data).declared_lower_bound
                )
        self.assertEqual(normalized, [normalized[0]] * 3)

    def test_extreme_decimal_exponent_is_rejected_without_underflow(self) -> None:
        data = coverage_data()
        data.update(
            population_basis="UNKNOWN",
            population_units=None,
            declared_lower_bound=Decimal("1e-1000027"),
        )
        with self.assertRaisesRegex(ModelValidationError, "at most 12 decimal places"):
            CoverageEvidence.from_dict(data)

    def test_unknown_population_without_attestation_is_unknown(self) -> None:
        data = coverage_data()
        data.update(population_basis="UNKNOWN", population_units=None)
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertIsNone(assessment.lower_bound)
        self.assertFalse(assessment.meets_policy)
        self.assertIn(CoverageIssue.UNKNOWN_COVERAGE, assessment.issues)

    def test_estimated_population_needs_explicit_declared_bound(self) -> None:
        data = coverage_data()
        data.update(population_basis="ESTIMATED", population_units=100)
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertIsNone(assessment.lower_bound)
        self.assertIn(CoverageIssue.UNKNOWN_COVERAGE, assessment.issues)

    def test_unknown_population_without_any_bound_is_rejected(self) -> None:
        data = coverage_data()
        data.update(
            population_basis="UNKNOWN",
            population_units=None,
            pages_examined=None,
            pages_expected=None,
            partitions_examined=None,
            partitions_expected=None,
        )
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertIsNone(assessment.lower_bound)
        self.assertIn(CoverageIssue.UNKNOWN_COVERAGE, assessment.issues)

    def test_declared_lower_bound_supports_unknown_population(self) -> None:
        data = coverage_data()
        data.update(
            population_basis="UNKNOWN",
            population_units=None,
            declared_lower_bound=1.0,
            pages_examined=None,
            pages_expected=None,
            partitions_examined=None,
            partitions_expected=None,
        )
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertTrue(assessment.meets_policy)
        self.assertEqual(assessment.lower_bound, 1.0)

    def test_estimated_population_is_not_silently_used_as_lower_bound(self) -> None:
        data = coverage_data()
        data.update(
            population_basis="ESTIMATED",
            pages_examined=None,
            pages_expected=None,
            partitions_examined=None,
            partitions_expected=None,
        )
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertIsNone(assessment.lower_bound)

    def test_timeout_blocks_coverage(self) -> None:
        data = coverage_data()
        data["timed_out"] = True
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertIn(CoverageIssue.TIMEOUT, assessment.issues)

    def test_query_error_blocks_coverage(self) -> None:
        data = coverage_data()
        data["query_errors"] = ["partition 2 returned 503"]
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertIn(CoverageIssue.QUERY_ERROR, assessment.issues)

    def test_permission_limited_scope_is_allowed_by_default(self) -> None:
        data = coverage_data()
        data["permission_limited"] = True
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertTrue(assessment.meets_policy)

    def test_permission_limited_scope_can_be_rejected(self) -> None:
        data = coverage_data()
        data["permission_limited"] = True
        policy = CoveragePolicy(allow_permission_limited_scope=False)
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data), policy)
        self.assertIn(CoverageIssue.PERMISSION_LIMITED, assessment.issues)

    def test_exact_population_policy_rejects_attested_unknown(self) -> None:
        data = coverage_data()
        data.update(population_basis="UNKNOWN", population_units=None, declared_lower_bound=1.0)
        policy = CoveragePolicy(require_exact_population=True)
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data), policy)
        self.assertIn(CoverageIssue.EXACT_POPULATION_REQUIRED, assessment.issues)

    def test_continuation_token_blocks_when_pagination_is_incomplete(self) -> None:
        data = coverage_data()
        data["pagination_complete"] = False
        data["continuation_token_present"] = True
        assessment = evaluate_coverage(CoverageEvidence.from_dict(data))
        self.assertIn(CoverageIssue.CONTINUATION_PRESENT, assessment.issues)

    def test_policy_rejects_invalid_fraction(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "between 0 and 1"):
            CoveragePolicy.from_dict({"minimum_lower_bound": 1.1})

    def test_policy_rejects_any_minimum_below_safety_floor(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "safety floor of 1.0"):
            CoveragePolicy(minimum_lower_bound=0.999)

    def test_policy_rejects_overprecise_minimum_before_rounding(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "at most 12 decimal places"):
            CoveragePolicy(
                minimum_lower_bound=Decimal("0.9999999999996")
            )

    def test_programmatic_policy_cannot_disable_required_checks(self) -> None:
        unsafe = {
            "require_complete_pagination": False,
            "require_complete_partitions": False,
            "reject_timeout": False,
            "reject_interruption": False,
            "reject_query_errors": False,
        }
        for field, value in unsafe.items():
            with self.subTest(field=field):
                with self.assertRaisesRegex(ModelValidationError, "safety floor"):
                    CoveragePolicy(**{field: value})

    def test_evaluation_is_deterministic(self) -> None:
        evidence = CoverageEvidence.from_dict(coverage_data())
        self.assertEqual(evaluate_coverage(evidence), evaluate_coverage(evidence))


if __name__ == "__main__":
    unittest.main()
