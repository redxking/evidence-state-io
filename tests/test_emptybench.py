from __future__ import annotations

import json
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from evidence_state_io import ModelValidationError
from evidence_state_io.canonical import canonical_digest
from evidence_state_io.emptybench import (
    EMPTYBENCH_CORPUS_SCHEMA,
    EMPTYBENCH_ORACLE_SCHEMA,
    EMPTYBENCH_REPORT_SCHEMA,
    SEED_ORACLE_DIGEST,
    EmptyBenchCase,
    demo_cases,
    parse_corpus,
    parse_oracle,
    run_emptybench,
    run_seed_emptybench,
    seed_benchmark,
    seed_case_dicts,
    seed_cases,
    seed_profile_context,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGED_BENCHMARKS = PROJECT_ROOT / "src" / "evidence_state_io" / "benchmarks"
CORPUS_PATH = PACKAGED_BENCHMARKS / "emptybench-p0-corpus.json"
ORACLE_PATH = PACKAGED_BENCHMARKS / "emptybench-p0-oracle.json"


def load_corpus_dict() -> dict:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def load_oracle_dict() -> dict:
    return json.loads(ORACLE_PATH.read_text(encoding="utf-8"))


def refresh_digest(value: dict, field: str) -> str:
    payload = deepcopy(value)
    payload.pop(field)
    digest = canonical_digest(payload)
    value[field] = digest
    return digest


class EmptyBenchTests(unittest.TestCase):
    def test_seed_suite_has_twelve_matched_fault_control_pairs(self) -> None:
        corpus, oracle = seed_benchmark()
        self.assertEqual(len(corpus.cases), 24)
        self.assertEqual(len({case.pair_id for case in corpus.cases}), 12)
        self.assertEqual(
            {case.fault_class for case in corpus.cases},
            {
                "PAGINATION",
                "PARTITIONING",
                "AUTHORIZATION",
                "FRESHNESS",
                "FINALITY",
                "ERROR_HANDLING",
                "POPULATION",
                "SOURCE_AGREEMENT",
                "POSITIVE_CONTROL",
                "QUERY_SEMANTICS",
                "SNAPSHOT",
                "ENVELOPE_HONESTY",
            },
        )
        self.assertEqual(len(oracle.assignments), 24)

    def test_corpus_cases_do_not_embed_oracle_expectations(self) -> None:
        raw = load_corpus_dict()
        for case in raw["cases"]:
            self.assertNotIn("expected_allowed", case)
            self.assertNotIn("expected_reasons", case)
            self.assertNotIn("rule_id", case)

    def test_contracts_and_digests_are_explicit(self) -> None:
        corpus, oracle = seed_benchmark()
        self.assertEqual(corpus.corpus_schema, EMPTYBENCH_CORPUS_SCHEMA)
        self.assertEqual(oracle.oracle_schema, EMPTYBENCH_ORACLE_SCHEMA)
        self.assertEqual(oracle.oracle_digest, SEED_ORACLE_DIGEST)
        self.assertEqual(oracle.corpus_digest, corpus.corpus_digest)

    def test_all_seed_expectations_pass_without_unsafe_permits(self) -> None:
        report = run_seed_emptybench(all_cases=True)
        self.assertTrue(report.all_passed)
        self.assertEqual(report.passed, 24)
        self.assertEqual(report.benchmark, "EmptyBench-P0-seed")
        payload = report.to_dict()
        self.assertEqual(payload["report_schema"], EMPTYBENCH_REPORT_SCHEMA)
        self.assertEqual(payload["summary"]["unsafe_permits"], 0)
        self.assertEqual(payload["summary"]["false_rejections"], 0)
        self.assertEqual(payload["summary"]["pairs_total"], 12)
        self.assertEqual(payload["summary"]["pairs_discriminated"], 12)

    def test_scoring_is_byte_deterministic(self) -> None:
        first = run_seed_emptybench(all_cases=True).to_dict()
        second = run_seed_emptybench(all_cases=True).to_dict()
        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )

    def test_demo_is_the_pagination_control_fault_pair(self) -> None:
        cases = demo_cases()
        self.assertEqual([case.variant for case in cases], ["control", "fault"])
        self.assertEqual({case.pair_id for case in cases}, {"pagination"})
        report = run_seed_emptybench()
        self.assertEqual(report.total, 2)
        self.assertTrue(report.all_passed)

    def test_finality_pair_crosses_exact_horizon_boundary(self) -> None:
        cases = [case for case in seed_cases() if case.pair_id == "finality"]
        self.assertEqual(len(cases), 2)
        control, fault = cases
        self.assertEqual(
            control.request.envelope.source_observations[0].descriptor.to_dict()["index_as_of"],
            "2026-08-21T12:04:00Z",
        )
        self.assertEqual(
            fault.request.envelope.source_observations[0].descriptor.to_dict()["index_as_of"],
            "2026-08-21T12:03:59.999999Z",
        )
        corpus, oracle = seed_benchmark()
        report = run_emptybench(
            corpus,
            oracle,
            seed_profile_context(),
            expected_oracle_digest=SEED_ORACLE_DIGEST,
            case_ids=[case.case_id for case in cases],
        )
        self.assertEqual(
            report.outcomes[1].actual_reasons,
            ("STATE_NOT_ABSENT_WITHIN_SCOPE", "INDEX_PRECEDES_FINALITY_HORIZON"),
        )

    def test_seed_case_compatibility_view_contains_inputs_only(self) -> None:
        cases = seed_case_dicts()
        self.assertEqual(len(cases), 24)
        self.assertIn("request", cases[0])
        self.assertNotIn("expected_allowed", cases[0])
        self.assertNotIn("expected_reasons", cases[0])

    def test_expanded_case_rejects_embedded_expectation(self) -> None:
        raw = deepcopy(seed_case_dicts()[0])
        raw["expected_allowed"] = True
        with self.assertRaisesRegex(ModelValidationError, "unknown fields"):
            EmptyBenchCase.from_dict(raw)

    def test_tampered_corpus_fails_internal_digest(self) -> None:
        raw = load_corpus_dict()
        raw["cases"][1]["description"] = "tampered"
        with self.assertRaisesRegex(ModelValidationError, "corpus digest"):
            parse_corpus(raw)

    def test_recomputed_tampered_corpus_fails_oracle_binding(self) -> None:
        raw = load_corpus_dict()
        raw["cases"][1]["description"] = "tampered and re-digested"
        refresh_digest(raw, "corpus_digest")
        corpus = parse_corpus(raw)
        with self.assertRaisesRegex(ModelValidationError, "bind the supplied corpus"):
            parse_oracle(
                load_oracle_dict(),
                corpus,
                expected_digest=SEED_ORACLE_DIGEST,
            )

    def test_swapped_case_mutations_fail_corpus_digest(self) -> None:
        raw = load_corpus_dict()
        raw["cases"][1]["mutations"], raw["cases"][3]["mutations"] = (
            raw["cases"][3]["mutations"],
            raw["cases"][1]["mutations"],
        )
        with self.assertRaisesRegex(ModelValidationError, "corpus digest"):
            parse_corpus(raw)

    def test_tampered_oracle_fails_internal_digest(self) -> None:
        corpus = parse_corpus(load_corpus_dict())
        raw = load_oracle_dict()
        raw["rules"][1]["expected_reasons"] = ["RESULT_EXPIRED"]
        with self.assertRaisesRegex(ModelValidationError, "oracle digest"):
            parse_oracle(raw, corpus, expected_digest=SEED_ORACLE_DIGEST)

    def test_recomputed_tampered_oracle_fails_retained_digest(self) -> None:
        corpus = parse_corpus(load_corpus_dict())
        raw = load_oracle_dict()
        raw["rules"][1]["expected_reasons"] = ["RESULT_EXPIRED"]
        refresh_digest(raw, "oracle_digest")
        with self.assertRaisesRegex(ModelValidationError, "retained expected digest"):
            parse_oracle(raw, corpus, expected_digest=SEED_ORACLE_DIGEST)

    def test_missing_oracle_assignment_is_rejected_after_valid_digest(self) -> None:
        corpus = parse_corpus(load_corpus_dict())
        raw = load_oracle_dict()
        raw["assignments"].pop()
        expected = refresh_digest(raw, "oracle_digest")
        with self.assertRaisesRegex(ModelValidationError, "missing cases"):
            parse_oracle(raw, corpus, expected_digest=expected)

    def test_duplicate_oracle_assignment_is_rejected(self) -> None:
        corpus = parse_corpus(load_corpus_dict())
        raw = load_oracle_dict()
        raw["assignments"][-1] = deepcopy(raw["assignments"][0])
        expected = refresh_digest(raw, "oracle_digest")
        with self.assertRaisesRegex(ModelValidationError, "duplicate case_id"):
            parse_oracle(raw, corpus, expected_digest=expected)

    def test_swapped_control_fault_oracle_assignments_fail_retained_digest(self) -> None:
        corpus = parse_corpus(load_corpus_dict())
        raw = load_oracle_dict()
        raw["assignments"][0]["rule_id"], raw["assignments"][1]["rule_id"] = (
            raw["assignments"][1]["rule_id"],
            raw["assignments"][0]["rule_id"],
        )
        refresh_digest(raw, "oracle_digest")
        with self.assertRaisesRegex(ModelValidationError, "retained expected digest"):
            parse_oracle(raw, corpus, expected_digest=SEED_ORACLE_DIGEST)

    def test_duplicate_oracle_rule_is_rejected(self) -> None:
        corpus = parse_corpus(load_corpus_dict())
        raw = load_oracle_dict()
        raw["rules"][1]["rule_id"] = raw["rules"][0]["rule_id"]
        expected = refresh_digest(raw, "oracle_digest")
        with self.assertRaisesRegex(ModelValidationError, "rule_id values must be unique"):
            parse_oracle(raw, corpus, expected_digest=expected)

    def test_corpus_contract_downgrade_is_rejected(self) -> None:
        raw = load_corpus_dict()
        raw["corpus_schema"] = "esio-emptybench-corpus/1.0-candidate.0"
        refresh_digest(raw, "corpus_digest")
        with self.assertRaisesRegex(ModelValidationError, "corpus_schema"):
            parse_corpus(raw)

    def test_oracle_contract_downgrade_is_rejected(self) -> None:
        corpus = parse_corpus(load_corpus_dict())
        raw = load_oracle_dict()
        raw["oracle_schema"] = "esio-emptybench-oracle/1.0-candidate.0"
        expected = refresh_digest(raw, "oracle_digest")
        with self.assertRaisesRegex(ModelValidationError, "oracle_schema"):
            parse_oracle(raw, corpus, expected_digest=expected)

    def test_duplicate_case_ids_are_rejected_after_valid_digest(self) -> None:
        raw = load_corpus_dict()
        raw["cases"][1]["case_id"] = raw["cases"][0]["case_id"]
        refresh_digest(raw, "corpus_digest")
        with self.assertRaisesRegex(ModelValidationError, "case_id values must be unique"):
            parse_corpus(raw)

    def test_missing_case_is_rejected_after_valid_digest(self) -> None:
        raw = load_corpus_dict()
        raw["cases"].pop()
        refresh_digest(raw, "corpus_digest")
        with self.assertRaisesRegex(ModelValidationError, "exactly two cases"):
            parse_corpus(raw)

    def test_duplicate_mutation_pointer_is_rejected(self) -> None:
        raw = load_corpus_dict()
        raw["cases"][1]["mutations"].append(deepcopy(raw["cases"][1]["mutations"][0]))
        refresh_digest(raw, "corpus_digest")
        with self.assertRaisesRegex(ModelValidationError, "must not repeat"):
            parse_corpus(raw)

    def test_nonexistent_mutation_path_is_rejected(self) -> None:
        raw = load_corpus_dict()
        raw["cases"][1]["mutations"][0]["pointer"] = "/envelope/not-a-field"
        refresh_digest(raw, "corpus_digest")
        with self.assertRaisesRegex(ModelValidationError, "existing object field"):
            parse_corpus(raw)

    def test_case_selection_rejects_duplicates_and_unknown_ids(self) -> None:
        corpus, oracle = seed_benchmark()
        context = seed_profile_context()
        with self.assertRaisesRegex(ModelValidationError, "must not contain duplicates"):
            run_emptybench(
                corpus,
                oracle,
                context,
                expected_oracle_digest=SEED_ORACLE_DIGEST,
                case_ids=["pagination-covered", "pagination-covered"],
            )
        with self.assertRaisesRegex(ModelValidationError, "unknown cases"):
            run_emptybench(
                corpus,
                oracle,
                context,
                expected_oracle_digest=SEED_ORACLE_DIGEST,
                case_ids=["does-not-exist"],
            )
        with self.assertRaisesRegex(ModelValidationError, "complete pairs"):
            run_emptybench(
                corpus,
                oracle,
                context,
                expected_oracle_digest=SEED_ORACLE_DIGEST,
                case_ids=["pagination-covered"],
            )

    def test_scoring_reparses_typed_oracle_and_requires_retained_digest(self) -> None:
        corpus, oracle = seed_benchmark()
        downgraded = replace(
            oracle,
            oracle_schema="esio-emptybench-oracle/1.0-candidate.0",
            oracle_digest="sha256:" + "0" * 64,
        )
        with self.assertRaisesRegex(ModelValidationError, "oracle_schema"):
            run_emptybench(
                corpus,
                downgraded,
                seed_profile_context(),
                expected_oracle_digest=SEED_ORACLE_DIGEST,
            )
        with self.assertRaisesRegex(ModelValidationError, "retained expected digest"):
            run_emptybench(
                corpus,
                oracle,
                seed_profile_context(),
                expected_oracle_digest="sha256:" + "0" * 64,
            )

    def test_scoring_reparses_mutated_cases_and_oracle_assignments(self) -> None:
        corpus, oracle = seed_benchmark()
        cases = list(corpus.cases)
        object.__setattr__(cases[1], "request", cases[0].request)
        object.__setattr__(oracle.assignments[1], "rule_id", oracle.assignments[0].rule_id)
        object.__setattr__(oracle, "oracle_digest", "sha256:" + "0" * 64)

        with self.assertRaisesRegex(ModelValidationError, "expanded cases"):
            run_emptybench(
                corpus,
                oracle,
                seed_profile_context(),
                expected_oracle_digest=SEED_ORACLE_DIGEST,
            )

    def test_scoring_rejects_mutated_corpus_payload(self) -> None:
        corpus, oracle = seed_benchmark()
        corpus.base_request["subject"] = "mutated after parsing"
        with self.assertRaisesRegex(ModelValidationError, "corpus digest"):
            run_emptybench(
                corpus,
                oracle,
                seed_profile_context(),
                expected_oracle_digest=SEED_ORACLE_DIGEST,
            )

    def test_scoring_rejects_post_parse_expanded_request_mutation(self) -> None:
        corpus, oracle = seed_benchmark()
        object.__setattr__(corpus.cases[1], "request", corpus.cases[0].request)
        with self.assertRaisesRegex(ModelValidationError, "expanded cases"):
            run_emptybench(
                corpus,
                oracle,
                seed_profile_context(),
                expected_oracle_digest=SEED_ORACLE_DIGEST,
            )

    def test_report_cannot_pass_without_pair_discrimination(self) -> None:
        report = run_seed_emptybench()
        outcomes = tuple(
            replace(
                outcome,
                expected_allowed=True,
                actual_allowed=True,
                expected_reasons=(),
                actual_reasons=(),
                passed=True,
            )
            for outcome in report.outcomes
        )
        non_discriminating = replace(report, outcomes=outcomes)
        self.assertEqual(non_discriminating.passed, 2)
        self.assertEqual(non_discriminating.pairs_discriminated, 0)
        self.assertFalse(non_discriminating.all_passed)


if __name__ == "__main__":
    unittest.main()
