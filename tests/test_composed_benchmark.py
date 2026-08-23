"""The packaged composed EmptyBench benchmark.

Unit tests pin the composition rules. This benchmark measures something they
cannot: whether the gate *discriminates*. Each pair presents the same visible
result and the same evaluation time, and differs only in one evidence fact, so
a pair that both permits or both rejects proves the gate is not reading the
evidence at all.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from evidence_state_io.emptybench import (
    COMPOSED_BENCHMARK_ID,
    COMPOSED_ORACLE_DIGEST,
    composed_benchmark,
    composed_profile_context,
    run_composed_emptybench,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = REPO_ROOT / "src" / "evidence_state_io" / "benchmarks"
EXPECTED_PAIRS = {
    "dissent",
    "source-coverage",
    "composed-floor",
    "own-horizon",
    "stalest-observation",
    "earliest-validity",
}


class ComposedBenchmarkTests(unittest.TestCase):
    def test_every_case_matches_its_oracle_rule(self) -> None:
        report = run_composed_emptybench()
        summary = report.to_dict()["summary"]

        self.assertTrue(report.all_passed, summary)
        self.assertEqual(summary["unsafe_permits"], 0)
        self.assertEqual(summary["false_rejections"], 0)

    def test_every_pair_discriminates(self) -> None:
        """A pair that does not discriminate measures nothing."""

        report = run_composed_emptybench()
        summary = report.to_dict()["summary"]

        self.assertEqual(summary["pairs_total"], len(EXPECTED_PAIRS))
        self.assertEqual(summary["pairs_discriminated"], summary["pairs_total"])

    def test_the_corpus_covers_each_composition_rule(self) -> None:
        corpus, _ = composed_benchmark()
        self.assertEqual({case.pair_id for case in corpus.cases}, EXPECTED_PAIRS)
        self.assertEqual(corpus.benchmark_id, COMPOSED_BENCHMARK_ID)

    def test_the_operator_pair_is_the_one_a_majority_rule_would_get_wrong(self) -> None:
        report = run_composed_emptybench(all_cases=False)
        summary = report.to_dict()["summary"]

        self.assertEqual(summary["total"], 2)
        self.assertTrue(report.all_passed)
        self.assertEqual(
            {outcome.case_id for outcome in report.outcomes},
            {"dissent-corroborated", "dissent-fault"},
        )

    def test_the_oracle_digest_is_pinned_outside_the_oracle(self) -> None:
        """A benchmark whose oracle can be edited with it measures nothing."""

        oracle_path = BENCHMARK_DIR / "emptybench-p1-composed-oracle.json"
        recorded = json.loads(oracle_path.read_text(encoding="utf-8"))["oracle_digest"]
        self.assertEqual(recorded, COMPOSED_ORACLE_DIGEST)

    def test_the_context_selects_one_governed_profile_per_source(self) -> None:
        context = composed_profile_context()
        corpus, _ = composed_benchmark()
        required = {
            requirement["source_id"]
            for requirement in corpus.base_request["envelope"]["query"]["source_requirements"]
        }

        self.assertEqual(len(required), 2)
        self.assertEqual(
            {record.profile.source.source_id for record in context.snapshot.records},
            required,
        )
        self.assertEqual(len(context.trust_selection.selected_profile_references), 2)

    def test_the_sources_have_different_horizons(self) -> None:
        """A mirror of the first source would corroborate nothing."""

        corpus, _ = composed_benchmark()
        horizons = {
            requirement["finality_horizon"]
            for requirement in corpus.base_request["envelope"]["query"]["source_requirements"]
        }
        self.assertEqual(len(horizons), 2, "both sources settle at the same time")


class GeneratorDriftTests(unittest.TestCase):
    """The packaged artifacts must be what the generator produces.

    The generator states the expected outcome of every case by hand and refuses
    to write when the gate disagrees. If the artifacts could drift from it, that
    check would stop meaning anything.
    """

    def test_the_packaged_artifacts_match_the_generator(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "generate_composed_benchmark.py"),
                "--check",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"regenerate with scripts/generate_composed_benchmark.py\n{result.stdout}{result.stderr}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
