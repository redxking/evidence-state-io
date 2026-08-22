from __future__ import annotations

import json
import unittest
from dataclasses import replace

from evidence_state_io import ModelValidationError
from evidence_state_io.canonical import canonical_digest, verify_canonical_digest
from evidence_state_io.coverage import CoveragePolicy, evaluate_coverage
from evidence_state_io.errors import (
    public_validation_error,
)
from evidence_state_io.gate import (
    NegativeClaimPolicy,
    NegativeClaimRequest,
    evaluate_negative_claim,
)
from evidence_state_io.sources import (
    SourceAccountingAssessment,
    SourceIssue,
    SourceIssueCode,
    evaluate_source_accounting,
)
from tests.helpers import request, trusted_context


class DefensiveContractTests(unittest.TestCase):
    def test_public_error_mapping_covers_every_supported_runtime_class(self) -> None:
        syntax = json.JSONDecodeError("bad", "{", 1)
        cases = (
            (syntax, "JSON_SYNTAX_INVALID"),
            (OSError("private path"), "INPUT_READ_FAILED"),
            (UnicodeError("private bytes"), "INPUT_ENCODING_INVALID"),
            (RecursionError(), "JSON_DEPTH_EXCEEDED"),
            (OverflowError(), "JSON_NUMBER_INVALID"),
        )
        for exception, code in cases:
            with self.subTest(code=code):
                payload = public_validation_error(exception)
                self.assertEqual(payload["error"]["code"], code)
                self.assertNotIn("private", payload["error"]["message"])
        with self.assertRaisesRegex(TypeError, "unsupported"):
            public_validation_error(RuntimeError())
        with self.assertRaisesRegex(TypeError, "ValidationErrorCode"):
            ModelValidationError("bad", code="MODEL_INVALID")  # type: ignore[arg-type]

    def test_canonical_expected_digest_type_is_exact(self) -> None:
        payload = {"value": 1}
        self.assertTrue(verify_canonical_digest(payload, canonical_digest(payload)))
        self.assertFalse(verify_canonical_digest(payload, None))  # type: ignore[arg-type]

    def test_coverage_defensive_types_and_declared_bound(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "must be a boolean"):
            CoveragePolicy(require_exact_population=None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelValidationError, "unknown fields"):
            CoveragePolicy.from_dict({"unknown": True})
        with self.assertRaisesRegex(ModelValidationError, "must be CoverageEvidence"):
            evaluate_coverage(object())  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelValidationError, "must be CoveragePolicy"):
            evaluate_coverage(request().envelope.coverage, object())  # type: ignore[arg-type]
        evidence = replace(request().envelope.coverage, declared_lower_bound=0.5)
        assessment = evaluate_coverage(evidence)
        self.assertEqual(assessment.lower_bound, 0.5)
        self.assertFalse(assessment.meets_policy)

    def test_source_issue_and_assessment_defensive_invariants(self) -> None:
        source_id = request().envelope.query.source_requirements[0].source_id
        issue = SourceIssue(SourceIssueCode.REQUIRED_SOURCE_FAILED, source_id)
        with self.assertRaisesRegex(ModelValidationError, "SourceIssueCode"):
            SourceIssue("bad", source_id)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelValidationError, "identify"):
            SourceIssue(SourceIssueCode.REQUIRED_SOURCE_FAILED, None)

        valid = {
            "required_source_ids": (source_id,),
            "observed_source_ids": (source_id,),
            "complete_source_ids": (source_id,),
            "issues": (),
            "meets_policy": True,
        }
        invalid_cases = (
            ({**valid, "required_source_ids": source_id}, "must be an array"),
            ({**valid, "required_source_ids": (source_id, source_id)}, "duplicates"),
            ({**valid, "issues": source_id}, "issues must be an array"),
            ({**valid, "issues": (object(),)}, "SourceIssue values"),
            ({**valid, "issues": (issue, issue), "meets_policy": False}, "duplicates"),
            ({**valid, "required_source_ids": ()}, "must not be empty"),
            ({**valid, "observed_source_ids": ("other-source",)}, "required sources"),
            ({**valid, "complete_source_ids": ("other-source",)}, "observed sources"),
            (
                {
                    **valid,
                    "issues": (
                        SourceIssue(SourceIssueCode.REQUIRED_SOURCE_FAILED, "other-source"),
                    ),
                    "meets_policy": False,
                },
                "non-required",
            ),
            ({**valid, "meets_policy": 1}, "must be a boolean"),
            ({**valid, "issues": (issue,), "meets_policy": True}, "true exactly"),
        )
        for values, message in invalid_cases:
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ModelValidationError, message),
            ):
                SourceAccountingAssessment(**values)  # type: ignore[arg-type]

    def test_source_materialization_rejects_hostile_types_and_roles(self) -> None:
        candidate = request()
        requirements = candidate.envelope.query.source_requirements
        observations = candidate.envelope.source_observations
        invalid_role_requirement = replace(requirements[0])
        object.__setattr__(invalid_role_requirement, "role", "OPTIONAL")
        cases = (
            ("bad", observations, "requirements must be an array"),
            (requirements, "bad", "observations must be an array"),
            ((object(),), observations, "only SourceRequirement"),
            (requirements, (object(),), "only SourceObservation"),
            (
                (invalid_role_requirement,),
                observations,
                "REQUIRED source",
            ),
        )
        for declared, observed, message in cases:
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ModelValidationError, message),
            ):
                evaluate_source_accounting(declared, observed)  # type: ignore[arg-type]

    def test_gate_defensive_constructor_and_entry_types(self) -> None:
        candidate = request()
        with self.assertRaisesRegex(ModelValidationError, "CoveragePolicy"):
            NegativeClaimPolicy(coverage=object())  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelValidationError, "must be a boolean"):
            NegativeClaimPolicy(require_valid_until=1)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelValidationError, "unknown fields"):
            NegativeClaimPolicy.from_dict(
                {
                    "policy_id": "esio-p0-safety-floor",
                    "policy_version": "1.0-candidate.4",
                    "unknown": True,
                }
            )
        with self.assertRaisesRegex(ModelValidationError, "must be EvidenceEnvelope"):
            NegativeClaimRequest(
                envelope=object(),  # type: ignore[arg-type]
                subject="bounded subject",
                mode=candidate.mode,
                evaluated_at=candidate.evaluated_at,
            )
        with self.assertRaisesRegex(ModelValidationError, "must be NegativeClaimPolicy"):
            NegativeClaimRequest(
                envelope=candidate.envelope,
                subject="bounded subject",
                mode=candidate.mode,
                evaluated_at=candidate.evaluated_at,
                policy=object(),  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(ModelValidationError, "must be a ClaimMode"):
            NegativeClaimRequest(
                envelope=candidate.envelope,
                subject="bounded subject",
                mode="SCOPED",  # type: ignore[arg-type]
                evaluated_at=candidate.evaluated_at,
            )
        with self.assertRaisesRegex(ModelValidationError, "request must be"):
            evaluate_negative_claim(object())  # type: ignore[arg-type]
        with self.assertRaisesRegex(ModelValidationError, "context must be"):
            evaluate_negative_claim(candidate, object())  # type: ignore[arg-type]
        self.assertTrue(evaluate_negative_claim(candidate, trusted_context()).allowed)


if __name__ == "__main__":
    unittest.main()
