"""The packaged seed corpus and oracle must not come from the caller's directory.

Defect ESIO-DEF-001: an installed distribution resolved its EmptyBench corpus
and oracle from `Path.cwd() / "benchmarks"`, so the published wheel failed
outside a checkout and, inside one, silently read the artifacts from whatever
directory the caller happened to be in.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

import evidence_state_io
from evidence_state_io.emptybench import (
    SEED_ORACLE_DIGEST,
    _seed_artifact_directory,
    run_seed_emptybench,
    seed_benchmark,
)

CORPUS_FILE = "emptybench-p0-corpus.json"
ORACLE_FILE = "emptybench-p0-oracle.json"


class SeedArtifactResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._origin = Path.cwd()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(os.chdir, self._origin)

    def test_artifacts_are_resolved_from_inside_the_installed_package(self) -> None:
        package = Path(evidence_state_io.__file__).resolve().parent
        directory = _seed_artifact_directory().resolve()
        self.assertEqual(directory, package / "benchmarks")
        self.assertTrue((directory / CORPUS_FILE).is_file())
        self.assertTrue((directory / ORACLE_FILE).is_file())

    def test_seed_benchmark_runs_from_a_directory_that_has_no_benchmarks(self) -> None:
        os.chdir(self.temporary.name)
        summary = run_seed_emptybench(all_cases=True).to_dict()["summary"]
        self.assertTrue(summary["all_passed"])
        self.assertEqual(summary["total"], 24)
        self.assertEqual(summary["passed"], 24)
        self.assertEqual(summary["pairs_discriminated"], 12)
        self.assertEqual(summary["unsafe_permits"], 0)
        self.assertEqual(summary["false_rejections"], 0)

    def test_a_benchmarks_directory_in_the_caller_directory_is_ignored(self) -> None:
        decoy = Path(self.temporary.name) / "benchmarks"
        decoy.mkdir()
        (decoy / CORPUS_FILE).write_text('{"not": "a corpus"}', encoding="utf-8")
        (decoy / ORACLE_FILE).write_text('{"not": "an oracle"}', encoding="utf-8")
        os.chdir(self.temporary.name)

        directory = _seed_artifact_directory().resolve()
        self.assertNotEqual(directory, decoy.resolve())

        corpus, oracle = seed_benchmark()
        self.assertEqual(oracle.oracle_digest, SEED_ORACLE_DIGEST)
        self.assertEqual(len(corpus.cases), 24)

    def test_output_is_identical_whatever_the_caller_directory_is(self) -> None:
        os.chdir(self._origin)
        inside = json.dumps(run_seed_emptybench(all_cases=True).to_dict(), sort_keys=True)
        os.chdir(self.temporary.name)
        outside = json.dumps(run_seed_emptybench(all_cases=True).to_dict(), sort_keys=True)
        self.assertEqual(inside, outside)


if __name__ == "__main__":
    unittest.main()
