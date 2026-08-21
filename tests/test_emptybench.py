from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from evidence_state_io import ModelValidationError
from evidence_state_io.emptybench import (
    EmptyBenchCase,
    demo_cases,
    parse_cases,
    run_emptybench,
    run_seed_emptybench,
    seed_case_dicts,
    seed_cases,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class EmptyBenchTests(unittest.TestCase):
    def test_seed_suite_has_five_pairs_and_ten_cases(self) -> None:
        cases = seed_cases()
        self.assertEqual(len(cases), 10)
        self.assertEqual(len({case.pair_id for case in cases}), 5)

    def test_all_seed_expectations_pass(self) -> None:
        report = run_seed_emptybench(all_cases=True)
        self.assertTrue(report.all_passed)
        self.assertEqual(report.passed, 10)
        self.assertEqual(report.benchmark, "EmptyBench-seed")

    def test_demo_is_covered_vs_partial_pair(self) -> None:
        cases = demo_cases()
        self.assertEqual([case.variant for case in cases], ["covered", "partial"])
        self.assertEqual({case.pair_id for case in cases}, {"covered-vs-partial"})

    def test_demo_pair_has_opposite_gate_results(self) -> None:
        report = run_emptybench(demo_cases())
        self.assertEqual(
            [outcome.actual_allowed for outcome in report.outcomes], [True, False]
        )

    def test_parse_cases_accepts_object_or_list(self) -> None:
        raw = seed_case_dicts()[:2]
        self.assertEqual(parse_cases(raw), parse_cases({"cases": raw}))

    def test_duplicate_case_ids_are_rejected(self) -> None:
        raw = deepcopy(seed_case_dicts()[:2])
        raw[1]["case_id"] = raw[0]["case_id"]
        with self.assertRaisesRegex(ModelValidationError, "must be unique"):
            parse_cases(raw)

    def test_direct_case_constructor_rejects_surrogate_identifier(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "control characters"):
            replace(seed_cases()[0], case_id="\udcff")

    def test_case_from_dict_rejects_newline_description(self) -> None:
        raw = deepcopy(seed_case_dicts()[0])
        raw["description"] = "first line\ninjected line"
        with self.assertRaisesRegex(ModelValidationError, "single line"):
            EmptyBenchCase.from_dict(raw)

    def test_case_from_dict_rejects_control_character(self) -> None:
        raw = deepcopy(seed_case_dicts()[0])
        raw["pair_id"] = "pair\u0000suffix"
        with self.assertRaisesRegex(ModelValidationError, "control characters"):
            EmptyBenchCase.from_dict(raw)

    def test_case_from_dict_rejects_oversized_variant(self) -> None:
        raw = deepcopy(seed_case_dicts()[0])
        raw["variant"] = "v" * 129
        with self.assertRaisesRegex(ModelValidationError, "128-character limit"):
            EmptyBenchCase.from_dict(raw)

    def test_empty_case_list_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "at least one"):
            parse_cases([])

    def test_expectation_mismatch_fails_report(self) -> None:
        raw = deepcopy(seed_case_dicts()[:2])
        raw[0]["request"]["envelope"]["coverage"]["timed_out"] = True
        cases = parse_cases(raw)
        report = run_emptybench(cases)
        self.assertFalse(report.all_passed)
        self.assertEqual(report.passed, 1)

    def test_custom_report_is_not_labeled_seed(self) -> None:
        report = run_emptybench(parse_cases(seed_case_dicts()[:2]))
        self.assertEqual(report.to_dict()["benchmark"], "EmptyBench-custom")

    def test_singleton_pair_is_rejected(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "exactly two cases"):
            parse_cases(seed_case_dicts()[:1])

    def test_run_emptybench_cannot_bypass_pair_validation(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "exactly two cases"):
            run_emptybench(case for case in seed_cases()[:1])

    def test_run_emptybench_materializes_valid_generator_once(self) -> None:
        report = run_emptybench(case for case in seed_cases()[:2])
        self.assertTrue(report.all_passed)
        self.assertEqual(report.total, 2)

    def test_pair_with_two_allowed_controls_is_rejected(self) -> None:
        raw = deepcopy(seed_case_dicts()[:2])
        raw[1]["expected_allowed"] = True
        raw[1]["expected_reasons"] = []
        with self.assertRaisesRegex(ModelValidationError, "one allowed control"):
            parse_cases(raw)

    def test_pair_with_changed_visible_question_is_rejected(self) -> None:
        raw = deepcopy(seed_case_dicts()[:2])
        raw[1]["request"]["subject"] = "different records"
        with self.assertRaisesRegex(ModelValidationError, "visible observation and question"):
            parse_cases(raw)

    def test_pair_without_sufficiency_difference_is_rejected(self) -> None:
        raw = deepcopy(seed_case_dicts()[:2])
        raw[1]["request"] = deepcopy(raw[0]["request"])
        raw[1]["expected_allowed"] = False
        raw[1]["expected_reasons"] = ["COVERAGE_POLICY_NOT_MET"]
        with self.assertRaisesRegex(ModelValidationError, "sufficiency fact"):
            parse_cases(raw)

    def test_reason_oracle_requires_exact_equality(self) -> None:
        cases = list(parse_cases(seed_case_dicts()[:2]))
        cases[1] = replace(
            cases[1], expected_reasons=("STATE_NOT_ABSENT_WITHIN_SCOPE",)
        )
        report = run_emptybench(cases)
        self.assertFalse(report.all_passed)
        self.assertFalse(report.outcomes[1].passed)

    def test_example_pair_is_valid_and_passes(self) -> None:
        path = PROJECT_ROOT / "examples" / "emptybench_pair.json"
        with path.open("r", encoding="utf-8") as handle:
            report = run_emptybench(parse_cases(json.load(handle)))
        self.assertTrue(report.all_passed)
        self.assertEqual(report.total, 2)


if __name__ == "__main__":
    unittest.main()
