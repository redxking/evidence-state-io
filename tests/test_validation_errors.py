from __future__ import annotations

import json
import unittest
from io import StringIO
from pathlib import Path

from evidence_state_io import (
    VALIDATION_ERROR_SCHEMA,
    ModelValidationError,
    ValidationErrorCode,
    public_validation_error,
)
from evidence_state_io.cli import MAX_INPUT_BYTES, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ValidationErrorContractTests(unittest.TestCase):
    def invoke(
        self,
        argv: list[str],
        stdin_text: str = "",
    ) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        code = main(
            argv,
            stdin=StringIO(stdin_text),
            stdout=stdout,
            stderr=stderr,
        )
        return code, stdout.getvalue(), stderr.getvalue()

    def test_contract_identifier_and_code_vocabulary_are_locked(self) -> None:
        self.assertEqual(
            VALIDATION_ERROR_SCHEMA,
            "esio-validation-error/1.0-candidate.1",
        )
        self.assertEqual(
            [code.value for code in ValidationErrorCode],
            [
                "MODEL_INVALID",
                "UNSUPPORTED_CONTRACT",
                "STATE_TRANSITION_INVALID",
                "CREDENTIAL_LIKE_IDENTIFIER",
                "JSON_SYNTAX_INVALID",
                "JSON_DUPLICATE_KEY",
                "JSON_NUMBER_INVALID",
                "JSON_DEPTH_EXCEEDED",
                "INPUT_SIZE_EXCEEDED",
                "INPUT_ENCODING_INVALID",
                "INPUT_READ_FAILED",
                "CLI_ARGUMENT_INVALID",
                "OUTPUT_ENCODING_FAILED",
            ],
        )

    def test_default_model_error_keeps_internal_detail_but_redacts_public_message(self) -> None:
        error = ModelValidationError("safe operator detail")
        self.assertEqual(error.code, ValidationErrorCode.MODEL_INVALID)
        self.assertEqual(str(error), "safe operator detail")
        self.assertEqual(
            public_validation_error(error),
            {
                "error": {
                    "validation_error_schema": VALIDATION_ERROR_SCHEMA,
                    "code": "MODEL_INVALID",
                    "type": "ModelValidationError",
                    "message": "Input does not satisfy the active model contract",
                }
            },
        )

    def test_json_syntax_failure_has_stable_code_and_no_partial_stdout(self) -> None:
        code, stdout, stderr = self.invoke(
            ["coverage", "--input", "-"],
            "{",
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)["error"]
        self.assertEqual(payload["validation_error_schema"], VALIDATION_ERROR_SCHEMA)
        self.assertEqual(payload["code"], "JSON_SYNTAX_INVALID")
        self.assertEqual(payload["type"], "JSONDecodeError")
        self.assertIn("line 1, column 2", payload["message"])

    def test_duplicate_key_failure_has_specific_code(self) -> None:
        code, stdout, stderr = self.invoke(
            ["coverage", "--input", "-"],
            '{"coverage":{},"coverage":{}}',
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)["error"]
        self.assertEqual(payload["code"], "JSON_DUPLICATE_KEY")
        self.assertEqual(payload["message"], "JSON contains a duplicate object key")

    def test_model_validation_failure_has_stable_default_code(self) -> None:
        code, stdout, stderr = self.invoke(
            ["coverage", "--input", "-"],
            '{"unexpected":true}',
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)["error"]
        self.assertEqual(payload["code"], "MODEL_INVALID")
        self.assertEqual(payload["type"], "ModelValidationError")
        self.assertEqual(
            payload["message"],
            "Input does not satisfy the active model contract",
        )

    def test_cli_credential_rejection_has_specific_code_without_echo(self) -> None:
        request = json.loads((EXAMPLES / "covered_request.json").read_text())
        credential_like = "bearer:redacted"
        request["envelope"]["query"]["source_requirements"][0]["authorization_context_id"] = (
            credential_like
        )
        code, stdout, stderr = self.invoke(
            [
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
            json.dumps(request),
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)["error"]
        self.assertEqual(payload["code"], "CREDENTIAL_LIKE_IDENTIFIER")
        self.assertNotIn(credential_like, payload["message"])

    def test_oversized_input_has_specific_code_without_echo(self) -> None:
        oversized = "x" * (MAX_INPUT_BYTES + 1)
        code, stdout, stderr = self.invoke(
            ["coverage", "--input", "-"],
            oversized,
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)["error"]
        self.assertEqual(payload["code"], "INPUT_SIZE_EXCEEDED")
        self.assertLess(len(stderr), 500)

    def test_invalid_cli_arguments_use_json_contract(self) -> None:
        code, stdout, stderr = self.invoke(["coverage"])
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)["error"]
        self.assertEqual(payload["code"], "CLI_ARGUMENT_INVALID")
        self.assertEqual(payload["type"], "ModelValidationError")
        self.assertEqual(payload["message"], "Command arguments are invalid")
        self.assertNotIn("usage:", stderr)

    def test_duplicate_key_and_invalid_choice_do_not_echo_sensitive_text(self) -> None:
        marker = "bearer:do-not-echo-this-value"
        code, stdout, stderr = self.invoke(
            ["coverage", "--input", "-"],
            json.dumps({marker: 1, "safe": 2}).replace('"safe": 2', f'"{marker}": 2'),
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertNotIn(marker, stderr)

        code, stdout, stderr = self.invoke(
            [
                "evaluate",
                "--input",
                "-",
                "--registry",
                "registry.json",
                "--trust",
                "trust.json",
                "--issued-at",
                "2026-08-21T12:06:00Z",
                "--origin",
                marker,
            ]
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertNotIn(marker, stderr)

    def test_closed_stdin_is_a_structured_input_read_failure(self) -> None:
        stdin = StringIO("{}")
        stdin.close()
        stdout = StringIO()
        stderr = StringIO()
        code = main(
            ["coverage", "--input", "-"],
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(json.loads(stderr.getvalue())["error"]["code"], "INPUT_READ_FAILED")

    def test_broken_stdout_is_classified_as_output_failure(self) -> None:
        class BrokenOutput(StringIO):
            def write(self, value: str) -> int:
                raise BrokenPipeError("do-not-echo-output-target")

        request = json.loads((EXAMPLES / "covered_request.json").read_text())
        stderr = StringIO()
        code = main(
            ["coverage", "--input", "-"],
            stdin=StringIO(json.dumps({"coverage": request["envelope"]["coverage"], "policy": {}})),
            stdout=BrokenOutput(),
            stderr=stderr,
        )
        self.assertEqual(code, 2)
        payload = json.loads(stderr.getvalue())["error"]
        self.assertEqual(payload["code"], "OUTPUT_ENCODING_FAILED")
        self.assertNotIn("do-not-echo-output-target", payload["message"])

    def test_error_serialization_is_deterministic(self) -> None:
        first = self.invoke(["coverage", "--input", "-"], "{")[2]
        second = self.invoke(["coverage", "--input", "-"], "{")[2]
        self.assertEqual(first, second)

    def test_io_failure_message_does_not_disclose_local_path(self) -> None:
        candidate_path = "/private/secret/customer-input.json"
        payload = public_validation_error(FileNotFoundError(candidate_path))["error"]
        self.assertEqual(payload["code"], "INPUT_READ_FAILED")
        self.assertEqual(payload["message"], "JSON input could not be read")
        self.assertNotIn(candidate_path, payload["message"])


if __name__ == "__main__":
    unittest.main()
