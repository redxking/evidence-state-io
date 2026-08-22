from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path

from evidence_state_io.cli import MAX_INPUT_BYTES, main
from evidence_state_io.emptybench import SEED_ORACLE_DIGEST
from evidence_state_io.remedy import INSUFFICIENCY_REMEDY_SCHEMA
from tests.helpers import refresh_query_fingerprints

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"
BENCHMARKS = PROJECT_ROOT / "src" / "evidence_state_io" / "benchmarks"


class CliTests(unittest.TestCase):
    def invoke(self, argv, stdin_text=""):
        argv = list(argv)
        if argv and argv[0] in {"evaluate", "emptybench", "explain"}:
            if "--registry" not in argv:
                argv.extend(["--registry", str(EXAMPLES / "profile_registry.json")])
            if "--trust" not in argv:
                argv.extend(["--trust", str(EXAMPLES / "profile_trust.json")])
        if argv and argv[0] == "emptybench":
            if "--oracle" not in argv:
                argv.extend(["--oracle", str(BENCHMARKS / "emptybench-p0-oracle.json")])
            if "--expected-oracle-digest" not in argv:
                argv.extend(["--expected-oracle-digest", SEED_ORACLE_DIGEST])
        if argv and argv[0] == "evaluate":
            if "--issued-at" not in argv:
                argv.extend(["--issued-at", "2026-08-21T12:06:00Z"])
            if "--origin" not in argv:
                argv.extend(["--origin", "SYNTHETIC"])
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
        self.assertEqual(json.loads(stdout)["summary"]["total"], 24)

    def test_evaluate_full_request_allows_covered_case(self) -> None:
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", str(EXAMPLES / "covered_request.json")]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertTrue(payload["certificate"]["decision"]["allowed"])
        self.assertEqual(payload["certificate"]["evidence_origin"], "SYNTHETIC")
        self.assertEqual(
            payload["certificate"]["implementation"]["package_version"],
            "0.6.0",
        )
        expected = json.loads((EXAMPLES / "covered_certificate.json").read_text())
        self.assertEqual(payload, expected)
        self.assertEqual(
            payload["certificate_digest"],
            "sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17",
        )

    def test_evaluate_full_request_denies_partial_case(self) -> None:
        code, stdout, _ = self.invoke(
            ["evaluate", "--input", str(EXAMPLES / "partial_request.json")]
        )
        payload = json.loads(stdout)
        self.assertEqual(code, 0)
        decision = payload["certificate"]["decision"]
        self.assertFalse(decision["allowed"])
        self.assertIn("COVERAGE_POLICY_NOT_MET", decision["reasons"])
        self.assertEqual(
            payload,
            json.loads((EXAMPLES / "rejected_certificate.json").read_text()),
        )
        self.assertEqual(
            payload["certificate_digest"],
            "sha256:9ad778636a8e013081d62d0a62e05e7cc0374a211444e5a951773607468f7462",
        )

    def test_verify_certificate_reports_replay_and_context_dimensions(self) -> None:
        evaluate_code, certificate_json, _ = self.invoke(
            ["evaluate", "--input", str(EXAMPLES / "covered_request.json")]
        )
        self.assertEqual(evaluate_code, 0)
        code, stdout, stderr = self.invoke(
            [
                "verify-certificate",
                "--input",
                "-",
                "--registry",
                str(EXAMPLES / "profile_registry.json"),
                "--trust",
                str(EXAMPLES / "profile_trust.json"),
                "--relying-party-at",
                "2026-08-21T12:30:00Z",
                "--expected-digest",
                "sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17",
            ],
            certificate_json,
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        report = json.loads(stdout)
        self.assertTrue(report["certificate_digest_integrity"])
        self.assertTrue(report["deterministic_replay"])
        self.assertTrue(report["expected_context_match"])
        self.assertTrue(report["current_local_reliance_eligible"])
        self.assertFalse(report["issuer_authenticated"])
        self.assertFalse(report["authorization_established"])

    def test_verify_certificate_tamper_is_exit_1_not_authentication(self) -> None:
        _, certificate_json, _ = self.invoke(
            ["evaluate", "--input", str(EXAMPLES / "covered_request.json")]
        )
        artifact = json.loads(certificate_json)
        artifact["certificate_digest"] = "sha256:" + "0" * 64
        code, stdout, stderr = self.invoke(
            ["verify-certificate", "--input", "-"],
            json.dumps(artifact),
        )
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        report = json.loads(stdout)
        self.assertFalse(report["certificate_digest_integrity"])
        self.assertTrue(report["deterministic_replay"])
        self.assertFalse(report["issuer_authenticated"])

    def test_verify_certificate_expected_digest_mismatch_is_exit_1(self) -> None:
        code, stdout, stderr = self.invoke(
            [
                "verify-certificate",
                "--input",
                str(EXAMPLES / "covered_certificate.json"),
                "--expected-digest",
                "sha256:" + "0" * 64,
            ]
        )
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        report = json.loads(stdout)
        self.assertFalse(report["expected_certificate_digest_match"])
        self.assertTrue(report["deterministic_replay"])

    def test_verify_certificate_unsupported_contract_is_exit_1(self) -> None:
        artifact = json.loads((EXAMPLES / "covered_certificate.json").read_text())
        artifact["certificate"]["certificate_format"] = (
            "esio-evidence-certificate/1.0-candidate.999"
        )
        code, stdout, stderr = self.invoke(
            ["verify-certificate", "--input", "-"],
            json.dumps(artifact),
        )
        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertFalse(json.loads(stdout)["structural_support"])

    def test_verify_certificate_malformed_json_is_exit_2(self) -> None:
        code, stdout, stderr = self.invoke(
            ["verify-certificate", "--input", "-"],
            "{",
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["type"], "JSONDecodeError")

    def test_verify_certificate_duplicate_nested_key_is_exit_2(self) -> None:
        raw = (EXAMPLES / "covered_certificate.json").read_text()
        raw = raw.replace(
            '"allowed": true',
            '"allowed": true, "allowed": true',
            1,
        )
        code, stdout, stderr = self.invoke(
            ["verify-certificate", "--input", "-"],
            raw,
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "JSON_DUPLICATE_KEY")

    def test_verify_certificate_requires_registry_and_trust_as_a_pair(self) -> None:
        code, stdout, stderr = self.invoke(
            [
                "verify-certificate",
                "--input",
                str(EXAMPLES / "covered_certificate.json"),
                "--registry",
                str(EXAMPLES / "profile_registry.json"),
            ]
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "CLI_ARGUMENT_INVALID")

    def test_relying_party_time_without_expected_context_is_unestablished(self) -> None:
        code, stdout, stderr = self.invoke(
            [
                "verify-certificate",
                "--input",
                str(EXAMPLES / "covered_certificate.json"),
                "--relying-party-at",
                "2026-08-21T12:30:00Z",
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        report = json.loads(stdout)
        self.assertIsNone(report["expected_context_match"])
        self.assertIsNone(report["current_local_reliance_eligible"])

    def test_evaluate_missing_finality_horizon_fails_closed(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        del full["envelope"]["query"]["source_requirements"][0]["finality_horizon"]
        refresh_query_fingerprints(full)
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], json.dumps(full))
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        decision = payload["certificate"]["decision"]
        self.assertFalse(decision["allowed"])
        self.assertIn("FINALITY_HORIZON_UNDECLARED", decision["reasons"])

    def test_evaluate_pre_horizon_index_fails_closed_without_process_error(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["source_observations"][0]["descriptor"]["index_as_of"] = (
            "2026-08-21T12:03:59.999999Z"
        )
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], json.dumps(full))
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        decision = payload["certificate"]["decision"]
        self.assertFalse(decision["allowed"])
        self.assertIn("INDEX_PRECEDES_FINALITY_HORIZON", decision["reasons"])

    def test_finality_horizon_before_query_end_is_invalid_input(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["query"]["source_requirements"][0]["finality_horizon"] = (
            "2026-08-21T11:59:59.999999Z"
        )
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], json.dumps(full))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

    def test_bare_envelope_requires_explicit_evaluation_time(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        code, stdout, stderr = self.invoke(
            ["evaluate", "--input", "-"], json.dumps(full["envelope"])
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "CLI_ARGUMENT_INVALID")

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
        self.assertTrue(json.loads(stdout)["certificate"]["decision"]["allowed"])

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
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

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
        self.assertEqual(json.loads(stderr)["error"]["code"], "CLI_ARGUMENT_INVALID")

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
        self.assertEqual(json.loads(stderr)["error"]["code"], "CLI_ARGUMENT_INVALID")

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
        self.assertEqual(json.loads(stderr)["error"]["code"], "CLI_ARGUMENT_INVALID")

    def test_emptybench_accepts_versioned_corpus_and_independent_oracle(self) -> None:
        code, stdout, stderr = self.invoke(
            [
                "emptybench",
                "--input",
                str(BENCHMARKS / "emptybench-p0-corpus.json"),
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["summary"]["passed"], 24)
        self.assertEqual(payload["summary"]["unsafe_permits"], 0)

    def test_emptybench_rejects_tampered_corpus_without_partial_stdout(self) -> None:
        raw = json.loads((BENCHMARKS / "emptybench-p0-corpus.json").read_text())
        raw["cases"][0]["description"] = "tampered"
        code, stdout, stderr = self.invoke(["emptybench", "--input", "-"], json.dumps(raw))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

    def test_emptybench_requires_external_oracle_digest(self) -> None:
        code, stdout, stderr = self.invoke(
            [
                "emptybench",
                "--input",
                str(BENCHMARKS / "emptybench-p0-corpus.json"),
                "--expected-oracle-digest",
                "sha256:" + "0" * 64,
            ]
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

    def test_coverage_command(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        input_data = {"coverage": full["envelope"]["coverage"], "policy": {}}
        code, stdout, stderr = self.invoke(["coverage", "--input", "-"], json.dumps(input_data))
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
        self.assertEqual(json.loads(stderr)["error"]["code"], "JSON_DUPLICATE_KEY")

    def test_nonstandard_json_constants_are_rejected(self) -> None:
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], '{"value":NaN}')
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "JSON_NUMBER_INVALID")

    def test_excessive_json_integer_is_a_structured_error(self) -> None:
        source = '{"value":' + "9" * 5000 + "}"
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], source)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertEqual(payload["error"]["code"], "JSON_NUMBER_INVALID")
        self.assertNotIn("Traceback", stderr)

    def test_excessive_json_fraction_is_a_structured_error(self) -> None:
        source = '{"value":0.' + "1" * 600 + "}"
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], source)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "JSON_NUMBER_INVALID")

    def test_surrogateescaped_stdin_is_a_structured_error(self) -> None:
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], '{"value":"\udcff"}')
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
                "--issued-at",
                "2026-08-21T12:06:00Z",
                "--origin",
                "SYNTHETIC",
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
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

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
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

    def test_half_specified_page_counts_are_rejected_by_cli(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["coverage"]["pages_expected"] = None
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], json.dumps(full))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

    def test_submicrosecond_timestamp_is_rejected_by_cli(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["envelope"]["valid_until"] = "2026-08-21T13:00:00.0000000Z"
        full["evaluated_at"] = "2026-08-21T13:00:00.0000009Z"
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], json.dumps(full))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

    def test_utc_normalization_overflow_is_a_structured_cli_error(self) -> None:
        full = json.loads((EXAMPLES / "covered_request.json").read_text())
        full["evaluated_at"] = "0001-01-01T00:00:00+23:59"
        code, stdout, stderr = self.invoke(["evaluate", "--input", "-"], json.dumps(full))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertEqual(payload["error"]["code"], "MODEL_INVALID")
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
        self.assertEqual(json.loads(stderr)["error"]["code"], "INPUT_SIZE_EXCEEDED")
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

    def test_explain_reports_conditions_for_a_rejection(self) -> None:
        code, stdout, _ = self.invoke(
            ["explain", "--input", str(EXAMPLES / "partial_request.json")]
        )
        payload = json.loads(stdout)
        self.assertEqual(code, 0, "explaining a rejection is not a program failure")
        self.assertEqual(payload["remedy_schema"], INSUFFICIENCY_REMEDY_SCHEMA)
        self.assertEqual(payload["decision"], "REJECT_NEGATIVE")
        self.assertEqual(payload["disclosure"], "CONSTRAINT_ONLY")
        self.assertTrue(payload["items"])
        for item in payload["items"]:
            self.assertIsNone(item["governed_value"])
            self.assertTrue(item["condition"].strip())

    def test_explain_withholds_governed_values_unless_asked(self) -> None:
        _, closed_out, _ = self.invoke(
            ["explain", "--input", str(EXAMPLES / "partial_request.json")]
        )
        _, open_out, _ = self.invoke(
            [
                "explain",
                "--input",
                str(EXAMPLES / "partial_request.json"),
                "--disclosure",
                "WITH_GOVERNED_VALUES",
            ]
        )
        closed = json.loads(closed_out)
        opened = json.loads(open_out)
        self.assertEqual(
            [item["reason"] for item in closed["items"]],
            [item["reason"] for item in opened["items"]],
        )
        self.assertTrue(any(item["governed_value"] for item in opened["items"]))
        self.assertTrue(any("WITH_GOVERNED_VALUES" in text for text in opened["limitations"]))

    def test_explain_refuses_a_permitted_request(self) -> None:
        code, stdout, stderr = self.invoke(
            ["explain", "--input", str(EXAMPLES / "covered_request.json")]
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "", "a refused explain must not emit a partial record")
        self.assertEqual(json.loads(stderr)["error"]["code"], "CLI_ARGUMENT_INVALID")

    def test_explain_is_byte_identical_across_repeated_invocations(self) -> None:
        outputs = set()
        for _ in range(5):
            _, stdout, _ = self.invoke(
                ["explain", "--input", str(EXAMPLES / "partial_request.json")]
            )
            outputs.add(stdout)
        self.assertEqual(len(outputs), 1)

    def test_explain_accepts_a_rejection_certificate_without_a_registry(self) -> None:
        code, stdout, _ = self.invoke(
            ["explain", "--input", str(EXAMPLES / "rejected_certificate.json")]
        )
        payload = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(payload["decision"], "REJECT_NEGATIVE")
        self.assertTrue(payload["certificate_digest"])
        self.assertTrue(payload["items"])
        self.assertTrue(any("replayed certificate" in t for t in payload["limitations"]))

    def test_explain_refuses_a_certificate_whose_digest_does_not_hold(self) -> None:
        data = json.loads((EXAMPLES / "rejected_certificate.json").read_text(encoding="utf-8"))
        data["certificate_digest"] = "sha256:" + "0" * 64
        code, stdout, stderr = self.invoke(["explain", "--input", "-"], stdin_text=json.dumps(data))
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")

    def test_explain_refuses_a_permit_certificate(self) -> None:
        code, _, stderr = self.invoke(
            ["explain", "--input", str(EXAMPLES / "covered_certificate.json")]
        )
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr)["error"]["code"], "MODEL_INVALID")


if __name__ == "__main__":
    unittest.main()
