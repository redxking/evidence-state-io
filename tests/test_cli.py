from __future__ import annotations

from io import StringIO
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from evidence_state_io.cli import MAX_INPUT_BYTES, main
from tests.helpers import refresh_query_fingerprints


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"


class CliTests(unittest.TestCase):
    def invoke(self, argv, stdin_text=""):
        argv = list(argv)
        if argv and argv[0] in {"evaluate", "emptybench"}:
            if "--registry" not in argv:
                argv.extend(
                    ["--registry", str(EXAMPLES / "profile_registry.json")]
                )
            if "--trust" not in argv:
                argv.extend(["--trust", str(EXAMPLES / "profile_trust.json")])
        stdout = StringIO()
        stderr = StringIO()
        code = main(argv, stdin=StringIO(stdin_text), stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_demo_runs_p0_pair(self) -> None:
        code, stdout, stderr = self.invoke(["demo"])
        payload = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["summary"]["total"], 2)
        self.assertTrue(payload["summary"]["all_passed"])

    def test_demo_all_runs_seed_suite(self) -> None:
        code, stdout, _ = self.invoke(["demo", "--all"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["summary"]["total"], 14)

    def test_evaluate_full_request_allows_covered_case(self) -> None:
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", str(EXAMPLES / "covered_request.json")]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["allowed"])

    def test_evaluate_full_request_denies_partial_case(self) -> None:
        code, stdout, _ = self.invoke(
            ["evaluate", "--input", str(EXAMPLES / "partial_request.json")]
        )
        payload = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertFalse(payload["allowed"])
        self.assertIn("COVERAGE_POLICY_NOT_MET", payload["reasons"])

    def test_evaluate_missing_finality_horizon_fails_closed(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        del full["envelope"]["query"]["source_requirements"][0][
            "finality_horizon"
        ]
        refresh_query_fingerprints(full)
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full)
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["allowed"])
        self.assertIn("FINALITY_HORIZON_UNDECLARED", payload["reasons"])

    def test_evaluate_pre_horizon_index_fails_closed_without_process_error(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["source_observations"][0]["descriptor"][
            "index_as_of"
        ] = "2026-08-21T12:03:59.999999Z"
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full)
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["allowed"])
        self.assertIn("INDEX_PRECEDES_FINALITY_HORIZON", payload["reasons"])

    def test_finality_horizon_before_query_end_is_invalid_input(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["query"]["source_requirements"][0][
            "finality_horizon"
        ] = "2026-08-21T11:59:59.999999Z"
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full)
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("finality_horizon must not precede", stderr)

    def test_bare_envelope_requires_explicit_evaluation_time(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full["envelope"])
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("never falls back to wall-clock time", stderr)

    def test_bare_envelope_with_time_is_supported(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        code, stdout, stderr = self.invoke(
            [
                "evaluate",
                "--input",
                "-",
                "--evaluated-at",
                "2026-08-21T12:05:00Z",
            ],
            json.dumps(full["envelope"]),
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["allowed"])

    def test_bare_envelope_explicit_empty_subject_is_rejected(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        code, stdout, stderr = self.invoke(
            [
                "evaluate",
                "--input",
                "-",
                "--evaluated-at",
                "2026-08-21T12:05:00Z",
                "--subject",
                "",
            ],
            json.dumps(full["envelope"]),
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("subject must be a non-empty string", stderr)

    def test_full_request_rejects_cli_time_override(self) -> None:
        code, _, stderr = self.invoke(
            [
                "evaluate",
                "--input",
                str(EXAMPLES / "covered_request.json"),
                "--evaluated-at",
                "2026-08-21T12:05:00Z",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("cannot be combined with CLI overrides", stderr)

    def test_full_request_rejects_subject_override(self) -> None:
        code, _, stderr = self.invoke(
            [
                "evaluate",
                "--input",
                str(EXAMPLES / "covered_request.json"),
                "--subject",
                "other records",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("--subject", stderr)

    def test_full_request_rejects_mode_override(self) -> None:
        code, _, stderr = self.invoke(
            [
                "evaluate",
                "--input",
                str(EXAMPLES / "covered_request.json"),
                "--mode",
                "ABSOLUTE",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("--mode", stderr)

    def test_emptybench_accepts_example_pair(self) -> None:
        code, stdout, stderr = self.invoke(
            ["emptybench", "--input", str(EXAMPLES / "emptybench_pair.json")]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["summary"]["passed"], 2)

    def test_emptybench_rejects_unsafe_case_metadata_without_partial_stdout(self) -> None:
        raw = json.loads((EXAMPLES / "emptybench_pair.json").read_text())
        mutations = (
            ("case_id", "\udcff", "control characters"),
            ("pair_id", "pair\u0000suffix", "control characters"),
            ("description", "line one\nline two", "single line"),
            ("variant", "v" * 129, "128-character limit"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                candidate = deepcopy(raw)
                candidate["cases"][0][field] = value
                code, stdout, stderr = self.invoke(
                    ["emptybench", "--input", "-"], json.dumps(candidate)
                )
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertIn(message, stderr)
                json.loads(stderr)

    def test_coverage_command(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        input_data = {"coverage": full["envelope"]["coverage"], "policy": {}}
        code, stdout, stderr = self.invoke(
            ["coverage", "--input", "-"], json.dumps(input_data)
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["meets_policy"])

    def test_invalid_json_is_machine_readable_error(self) -> None:
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], "{")
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "JSONDecodeError")

    def test_duplicate_json_keys_are_rejected(self) -> None:
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"],
            '{"state":"PARTIAL","state":"ABSENT_WITHIN_SCOPE"}',
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("duplicate JSON object key: state", stderr)

    def test_nonstandard_json_constants_are_rejected(self) -> None:
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], '{"value":NaN}'
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("non-standard JSON numeric constant", stderr)

    def test_excessive_json_integer_is_a_structured_error(self) -> None:
        source = '{"value":' + "9" * 5000 + "}"
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], source)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertIn("numeric token exceeds", payload["error"]["message"])
        self.assertNotIn("Traceback", stderr)

    def test_excessive_json_fraction_is_a_structured_error(self) -> None:
        source = '{"value":0.' + "1" * 600 + "}"
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], source)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("numeric token exceeds", stderr)

    def test_surrogateescaped_stdin_is_a_structured_error(self) -> None:
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], '{"value":"\udcff"}'
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertIn("valid UTF-8", payload["error"]["message"])

    def test_raw_invalid_utf8_stdin_has_no_traceback(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "evidence_state_io",
                "evaluate",
                "--input",
                "-",
                "--registry",
                str(EXAMPLES / "profile_registry.json"),
                "--trust",
                str(EXAMPLES / "profile_trust.json"),
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            input=b'{"value":"\xff"}',
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, b"")
        payload = json.loads(completed.stderr.decode("ascii"))
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertIn("valid UTF-8", payload["error"]["message"])
        self.assertNotIn(b"Traceback", completed.stderr)

    def test_accepted_precise_declared_bound_below_one_is_not_promoted(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        coverage = full["envelope"]["coverage"]
        coverage.update(population_basis="UNKNOWN", population_units=None)
        source = json.dumps({"coverage": coverage, "policy": {}})
        source = source.replace(
            '"declared_lower_bound": null',
            '"declared_lower_bound": 0.999999999999',
        )
        code, stdout, stderr = self.invoke(["coverage", "--input", "-"], source)
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertFalse(payload["meets_policy"])
        self.assertLess(payload["lower_bound"], 1.0)
        self.assertIn("BELOW_MINIMUM", payload["issues"])

    def test_overprecise_declared_bound_is_rejected(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        coverage = full["envelope"]["coverage"]
        coverage.update(population_basis="UNKNOWN", population_units=None)
        source = json.dumps({"coverage": coverage, "policy": {}})
        source = source.replace(
            '"declared_lower_bound": null',
            '"declared_lower_bound": 0.9999999999996',
        )
        code, stdout, stderr = self.invoke(["coverage", "--input", "-"], source)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("at most 12 decimal places", stderr)

    def test_lexical_fraction_above_one_is_rejected(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        coverage = full["envelope"]["coverage"]
        coverage.update(population_basis="UNKNOWN", population_units=None)
        source = json.dumps({"coverage": coverage, "policy": {}})
        source = source.replace(
            '"declared_lower_bound": null',
            '"declared_lower_bound": 1.00000000000000001',
        )
        code, stdout, stderr = self.invoke(["coverage", "--input", "-"], source)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("between 0 and 1", stderr)

    def test_half_specified_page_counts_are_rejected_by_cli(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["coverage"]["pages_expected"] = None
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full)
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("must both be present or both be null", stderr)

    def test_submicrosecond_timestamp_is_rejected_by_cli(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["valid_until"] = "2026-08-21T13:00:00.0000000Z"
        full["evaluated_at"] = "2026-08-21T13:00:00.0000009Z"
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full)
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("at most 6 fractional-second digits", stderr)

    def test_utc_normalization_overflow_is_a_structured_cli_error(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["evaluated_at"] = "0001-01-01T00:00:00+23:59"
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full)
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertIn("representable in UTC", payload["error"]["message"])
        self.assertNotIn("Traceback", stderr)

    def test_deep_nesting_is_a_structured_error(self) -> None:
        nested = "[" * 5000 + "0" + "]" * 5000
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], nested)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertIn("nesting", payload["error"]["message"])

    def test_oversized_stdin_is_rejected_without_echoing_input(self) -> None:
        oversized = "x" * (MAX_INPUT_BYTES + 1)
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], oversized)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("exceeds", stderr)
        self.assertLess(len(stderr), 500)

    def test_module_entrypoint_runs_in_clean_subprocess(self) -> None:
        environment = os.environ.copy()
        source_path = str(PROJECT_ROOT / "src")
        environment["PYTHONPATH"] = source_path
        completed = subprocess.run(
            [sys.executable, "-m", "evidence_state_io", "demo"],
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["summary"]["all_passed"])


if __name__ == "__main__":
    unittest.main()
