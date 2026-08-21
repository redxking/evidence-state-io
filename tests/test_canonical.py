from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import unittest

from evidence_state_io import (
    ModelValidationError,
    canonical_digest,
    canonical_json_bytes,
    verify_canonical_digest,
)
from evidence_state_io.gate import NegativeClaimRequest, evaluate_negative_claim

from tests.helpers import request_dict


class CanonicalDigestTests(unittest.TestCase):
    def test_object_key_order_does_not_change_canonical_bytes(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"b": 2, "a": 1}),
            canonical_json_bytes({"a": 1, "b": 2}),
        )

    def test_semantically_unordered_exclusions_do_not_change_digest(self) -> None:
        first = request_dict()
        second = deepcopy(first)
        second["envelope"]["query"]["exclusions"].reverse()
        first_decision = evaluate_negative_claim(NegativeClaimRequest.from_dict(first))
        second_decision = evaluate_negative_claim(NegativeClaimRequest.from_dict(second))
        self.assertEqual(first_decision.input_digest, second_decision.input_digest)
        self.assertEqual(first_decision.to_dict(), second_decision.to_dict())

    def test_one_field_mutation_changes_digest(self) -> None:
        original = request_dict()
        mutated = deepcopy(original)
        mutated["envelope"]["query"]["predicate"] = "topic:other"
        self.assertNotEqual(canonical_digest(original), canonical_digest(mutated))

    def test_distinct_accepted_decimal_bounds_have_distinct_digests(self) -> None:
        first = request_dict()
        second = deepcopy(first)
        for data, bound in (
            (first, Decimal("0.123456789011")),
            (second, Decimal("0.123456789012")),
        ):
            data["envelope"]["coverage"].update(
                population_basis="UNKNOWN",
                population_units=None,
                declared_lower_bound=bound,
            )
        first_request = NegativeClaimRequest.from_dict(first)
        second_request = NegativeClaimRequest.from_dict(second)
        self.assertNotEqual(
            evaluate_negative_claim(first_request).input_digest,
            evaluate_negative_claim(second_request).input_digest,
        )

    def test_accepted_decimal_requests_round_trip_with_stable_digests(self) -> None:
        bounds = (
            Decimal("0.1"),
            Decimal("0.2"),
            Decimal("0.9"),
            Decimal("0.123456789012"),
            Decimal("0.999999999999"),
        )
        for bound in bounds:
            with self.subTest(bound=str(bound)):
                data = request_dict()
                data["envelope"]["coverage"].update(
                    population_basis="UNKNOWN",
                    population_units=None,
                    declared_lower_bound=bound,
                )
                original = NegativeClaimRequest.from_dict(data)
                replayed = NegativeClaimRequest.from_dict(original.to_dict())
                self.assertEqual(original, replayed)
                self.assertEqual(
                    evaluate_negative_claim(original).input_digest,
                    evaluate_negative_claim(replayed).input_digest,
                )

    def test_mutating_caller_lists_cannot_change_request_digest(self) -> None:
        base = NegativeClaimRequest.from_dict(request_dict())
        exclusions = list(base.envelope.query.exclusions)
        query_errors = list(base.envelope.coverage.query_errors)
        errors = list(base.envelope.errors)
        notes = list(base.envelope.notes)
        query = replace(base.envelope.query, exclusions=exclusions)
        coverage = replace(base.envelope.coverage, query_errors=query_errors)
        envelope = replace(
            base.envelope,
            query=query,
            coverage=coverage,
            errors=errors,
            notes=notes,
        )
        candidate = replace(base, envelope=envelope)
        before = evaluate_negative_claim(candidate).input_digest
        exclusions.append("later exclusion")
        query_errors.append("later query error")
        errors.append("later envelope error")
        notes.append("later note")
        after = evaluate_negative_claim(candidate).input_digest
        self.assertEqual(before, after)
        self.assertIsInstance(candidate.envelope.query.exclusions, tuple)
        self.assertIsInstance(candidate.envelope.coverage.query_errors, tuple)
        self.assertIsInstance(candidate.envelope.errors, tuple)
        self.assertIsInstance(candidate.envelope.notes, tuple)

    def test_canonical_huge_integer_failure_uses_project_error(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "unsupported value"):
            canonical_json_bytes({"value": 10**4999})

    def test_verifier_detects_payload_mutation_against_trusted_digest(self) -> None:
        original = request_dict()
        expected = canonical_digest(original)
        self.assertTrue(verify_canonical_digest(original, expected))
        mutated = deepcopy(original)
        mutated["policy"] = {"coverage": {"minimum_lower_bound": 0.5}}
        self.assertFalse(verify_canonical_digest(mutated, expected))

    def test_digest_is_integrity_metadata_not_a_signature(self) -> None:
        decision = evaluate_negative_claim(NegativeClaimRequest.from_dict(request_dict()))
        self.assertEqual(decision.digest_algorithm, "sha256")
        self.assertIn("canonical-json", decision.canonicalization_profile)
        self.assertIn("not a signature", decision.limitations[-1])
        self.assertIn("trusted expected digest", decision.limitations[-1])


if __name__ == "__main__":
    unittest.main()
