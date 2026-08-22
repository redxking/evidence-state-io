from __future__ import annotations

import unittest
from io import StringIO
from pathlib import Path

from evidence_state_io.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"
PERMIT_DIGEST = "sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17"
REPETITIONS = 100


def invoke(arguments: list[str]) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    code = main(
        arguments,
        stdin=StringIO(),
        stdout=stdout,
        stderr=stderr,
    )
    return code, stdout.getvalue(), stderr.getvalue()


class DeterminismAcceptanceTests(unittest.TestCase):
    def assert_repeats_exactly(
        self,
        arguments: list[str],
        *,
        expected_output: str | None = None,
    ) -> str:
        baseline: str | None = None
        for _ in range(REPETITIONS):
            code, stdout, stderr = invoke(arguments)
            self.assertEqual(code, 0)
            self.assertEqual(stderr, "")
            if baseline is None:
                baseline = stdout
            self.assertEqual(stdout, baseline)
        assert baseline is not None
        if expected_output is not None:
            self.assertEqual(baseline, expected_output)
        return baseline

    def test_every_active_golden_operation_repeats_one_hundred_times(self) -> None:
        common = [
            "--registry",
            str(EXAMPLES / "profile_registry.json"),
            "--trust",
            str(EXAMPLES / "profile_trust.json"),
            "--issued-at",
            "2026-08-21T12:06:00Z",
            "--origin",
            "SYNTHETIC",
            "--pretty",
        ]
        self.assert_repeats_exactly(
            ["evaluate", "--input", str(EXAMPLES / "covered_request.json"), *common],
            expected_output=(EXAMPLES / "covered_certificate.json").read_text(encoding="utf-8"),
        )
        self.assert_repeats_exactly(
            ["evaluate", "--input", str(EXAMPLES / "partial_request.json"), *common],
            expected_output=(EXAMPLES / "rejected_certificate.json").read_text(encoding="utf-8"),
        )
        self.assert_repeats_exactly(["demo", "--all", "--pretty"])
        self.assert_repeats_exactly(
            [
                "verify-certificate",
                "--input",
                str(EXAMPLES / "covered_certificate.json"),
                "--registry",
                str(EXAMPLES / "profile_registry.json"),
                "--trust",
                str(EXAMPLES / "profile_trust.json"),
                "--expected-digest",
                PERMIT_DIGEST,
                "--relying-party-at",
                "2026-08-21T12:30:00Z",
                "--pretty",
            ]
        )


if __name__ == "__main__":
    unittest.main()
