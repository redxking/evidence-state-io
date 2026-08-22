"""Insufficiency remedies must be actionable without becoming a fabrication recipe.

The pairs here hold the decision constant and change only what the remedy is
allowed to say, so a regression that leaks a governed value or converts a
rejection into an instruction fails loudly.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import unittest
from pathlib import Path
from unittest import mock

from evidence_state_io.errors import ModelValidationError
from evidence_state_io.gate import GateReason, NegativeClaimRequest, evaluate_negative_claim
from evidence_state_io.profiles import TrustedProfileContext
from evidence_state_io.remedy import (
    INSUFFICIENCY_REMEDY_SCHEMA,
    DisclosureLevel,
    RemedyClass,
    RemedyItem,
    _governed_value,
    _selected_profile,
    derive_remedy,
)
from tests.helpers import refresh_query_fingerprints

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"

# Wording that would turn a description of a constraint into an instruction for
# editing the request until it passes.
FORBIDDEN_INSTRUCTION_FRAGMENTS = (
    "set ",
    "change the",
    "edit ",
    "update the request",
    "modify the",
    "resubmit with",
)


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _context() -> TrustedProfileContext:
    return TrustedProfileContext.from_dict(
        {
            "registry_snapshot": _load("profile_registry.json"),
            "trust_selection": _load("profile_trust.json"),
        }
    )


class RemedyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = _context()
        self.rejected_data = _load("partial_request.json")
        self.rejected = NegativeClaimRequest.from_dict(self.rejected_data)
        self.rejected_decision = evaluate_negative_claim(self.rejected, self.context)
        self.assertFalse(self.rejected_decision.allowed)

        self.permitted = NegativeClaimRequest.from_dict(_load("covered_request.json"))
        self.permitted_decision = evaluate_negative_claim(self.permitted, self.context)
        self.assertTrue(self.permitted_decision.allowed)

    def _remedy(self, disclosure: DisclosureLevel = DisclosureLevel.CONSTRAINT_ONLY):
        return derive_remedy(
            self.rejected_decision, self.rejected, self.context, disclosure=disclosure
        )

    def test_a_permit_has_no_remedy(self) -> None:
        with self.assertRaises(ModelValidationError):
            derive_remedy(self.permitted_decision, self.permitted, self.context)

    def test_every_gate_reason_is_classified(self) -> None:
        """No reason may fall through to a default; each must be decided."""

        from evidence_state_io.remedy import _classify

        for reason in GateReason:
            remedy_class, condition = _classify(reason, self.rejected)
            self.assertIsInstance(remedy_class, RemedyClass)
            self.assertTrue(condition.strip())

    def test_no_condition_reads_as_an_instruction_to_edit_the_request(self) -> None:
        from evidence_state_io.remedy import _classify

        for reason in GateReason:
            _, condition = _classify(reason, self.rejected)
            lowered = condition.lower()
            for fragment in FORBIDDEN_INSTRUCTION_FRAGMENTS:
                self.assertNotIn(
                    fragment,
                    lowered,
                    f"{reason.value} reads as an instruction to edit the request: {condition}",
                )

    def test_constraint_only_discloses_no_governed_value(self) -> None:
        remedy = self._remedy()
        self.assertEqual(remedy.disclosure, DisclosureLevel.CONSTRAINT_ONLY)
        for item in remedy.items:
            self.assertIsNone(item.governed_value, f"{item.reason.value} leaked a governed value")

    def test_governed_values_are_disclosed_only_on_request_and_are_flagged(self) -> None:
        closed = self._remedy()
        opened = self._remedy(DisclosureLevel.WITH_GOVERNED_VALUES)

        self.assertEqual(
            [item.reason for item in closed.items],
            [item.reason for item in opened.items],
            "disclosure must not change which constraints are reported",
        )
        self.assertTrue(
            any(item.governed_value for item in opened.items),
            "WITH_GOVERNED_VALUES produced no governed value at all",
        )
        self.assertTrue(
            any("WITH_GOVERNED_VALUES" in text for text in opened.limitations),
            "the disclosure limitation must be recorded in the record itself",
        )
        self.assertFalse(any("WITH_GOVERNED_VALUES" in text for text in closed.limitations))

    def test_remedy_is_bound_to_the_decision_it_explains(self) -> None:
        remedy = self._remedy()
        self.assertEqual(remedy.input_digest, self.rejected_decision.input_digest)
        self.assertEqual(remedy.evaluated_at, self.rejected.evaluated_at)
        self.assertEqual(remedy.remedy_schema, INSUFFICIENCY_REMEDY_SCHEMA)

    def test_item_order_follows_the_decision_reason_order(self) -> None:
        remedy = self._remedy()
        self.assertEqual(
            [item.reason for item in remedy.items],
            list(self.rejected_decision.reasons),
        )

    def test_remedy_is_not_part_of_the_decision_payload(self) -> None:
        payload = self.rejected_decision.to_dict()
        self.assertNotIn("remedy", payload)
        self.assertNotIn("insufficiency_remedy", payload)

    def test_matched_pair_present_is_unsatisfiable_and_partial_is_not(self) -> None:
        """Hold everything constant except the reported state."""

        partial = self._remedy()
        self.assertTrue(partial.satisfiable)
        partial_item = next(
            item
            for item in partial.items
            if item.reason is GateReason.STATE_NOT_ABSENT_WITHIN_SCOPE
        )
        self.assertIsNot(partial_item.remedy_class, RemedyClass.UNSATISFIABLE)

        # The envelope model itself requires PRESENT to carry matches, so the
        # pair moves both together; the assertion below is still on the state
        # reason's class rather than on the match count.
        present_data = copy.deepcopy(self.rejected_data)
        present_data["envelope"]["state"] = "PRESENT"
        present_data["envelope"]["matched_count"] = 3
        present = NegativeClaimRequest.from_dict(present_data)
        present_decision = evaluate_negative_claim(present, self.context)
        present_remedy = derive_remedy(present_decision, present, self.context)

        present_item = next(
            item
            for item in present_remedy.items
            if item.reason is GateReason.STATE_NOT_ABSENT_WITHIN_SCOPE
        )
        self.assertIs(present_item.remedy_class, RemedyClass.UNSATISFIABLE)
        self.assertFalse(present_remedy.satisfiable)

    def test_nonzero_matches_are_never_presented_as_remediable(self) -> None:
        data = copy.deepcopy(self.rejected_data)
        data["envelope"]["matched_count"] = 3
        request = NegativeClaimRequest.from_dict(data)
        decision = evaluate_negative_claim(request, self.context)
        remedy = derive_remedy(decision, request, self.context)

        item = next(item for item in remedy.items if item.reason is GateReason.NONZERO_MATCHES)
        self.assertIs(item.remedy_class, RemedyClass.UNSATISFIABLE)
        self.assertFalse(remedy.satisfiable)

    def test_absolute_claims_are_unsatisfiable(self) -> None:
        data = copy.deepcopy(self.rejected_data)
        data["mode"] = "ABSOLUTE"
        request = NegativeClaimRequest.from_dict(data)
        decision = evaluate_negative_claim(request, self.context)
        remedy = derive_remedy(decision, request, self.context)

        item = next(
            item for item in remedy.items if item.reason is GateReason.ABSOLUTE_NEGATIVE_UNSUPPORTED
        )
        self.assertIs(item.remedy_class, RemedyClass.UNSATISFIABLE)
        self.assertFalse(remedy.satisfiable)

    def test_derivation_is_deterministic(self) -> None:
        for disclosure in DisclosureLevel:
            rendered = {
                json.dumps(self._remedy(disclosure).to_dict(), sort_keys=True) for _ in range(100)
            }
            self.assertEqual(len(rendered), 1, f"{disclosure.value} derivation is not stable")

    def test_derivation_rejects_wrong_types(self) -> None:
        with self.assertRaises(ModelValidationError):
            derive_remedy(self.rejected, self.rejected, self.context)  # type: ignore[arg-type]
        with self.assertRaises(ModelValidationError):
            derive_remedy(self.rejected_decision, self.rejected_decision, self.context)  # type: ignore[arg-type]
        with self.assertRaises(ModelValidationError):
            derive_remedy(
                self.rejected_decision,
                self.rejected,
                self.context,
                disclosure="WITH_GOVERNED_VALUES",  # type: ignore[arg-type]
            )

    def test_remedy_survives_a_json_round_trip_unchanged(self) -> None:
        remedy = self._remedy(DisclosureLevel.WITH_GOVERNED_VALUES)
        payload = remedy.to_dict()
        self.assertEqual(json.loads(json.dumps(payload)), payload)
        self.assertEqual(payload["decision"], "REJECT_NEGATIVE")
        self.assertIs(payload["satisfiable"], remedy.satisfiable)


class GovernedValueTests(unittest.TestCase):
    """Every reason that can carry a governed value must actually produce one."""

    def setUp(self) -> None:
        self.context = _context()
        self.request = NegativeClaimRequest.from_dict(_load("partial_request.json"))
        self.profile = _selected_profile(self.context)
        self.assertIsNotNone(self.profile, "the example trust selection must resolve a profile")

    def test_request_side_reasons_disclose_their_comparison_value(self) -> None:
        for reason in (
            GateReason.INDEX_PRECEDES_QUERY_END,
            GateReason.COVERAGE_POLICY_NOT_MET,
            GateReason.RESULT_EXPIRED,
        ):
            with self.subTest(reason=reason.value):
                value = _governed_value(reason, self.request, self.profile)
                self.assertIsInstance(value, str)
                self.assertTrue(value)

    def test_age_limits_disclose_only_when_the_policy_declares_them(self) -> None:
        """An undeclared limit has no value to disclose, and must not invent one."""

        undeclared = self.request
        for reason in (GateReason.OBSERVATION_TOO_OLD, GateReason.INDEX_TOO_OLD):
            with self.subTest(reason=reason.value, declared=False):
                self.assertIsNone(_governed_value(reason, undeclared, self.profile))

        data = copy.deepcopy(_load("partial_request.json"))
        data["policy"]["max_observation_age_seconds"] = 3600
        data["policy"]["max_index_age_seconds"] = 900
        declared = NegativeClaimRequest.from_dict(data)
        for reason, expected in (
            (GateReason.OBSERVATION_TOO_OLD, "3600"),
            (GateReason.INDEX_TOO_OLD, "900"),
        ):
            with self.subTest(reason=reason.value, declared=True):
                value = _governed_value(reason, declared, self.profile)
                self.assertIsInstance(value, str)
                assert value is not None
                self.assertIn(expected, value)

    def test_profile_side_reasons_disclose_their_comparison_value(self) -> None:
        for reason in (
            GateReason.PROFILE_RETENTION_EXCEEDED,
            GateReason.PROFILE_OBSERVATION_TOO_OLD,
            GateReason.PROFILE_INDEX_TOO_OLD,
            GateReason.FINALITY_HORIZON_PROFILE_MISMATCH,
            GateReason.PROFILE_POPULATION_MISMATCH,
        ):
            with self.subTest(reason=reason.value):
                value = _governed_value(reason, self.request, self.profile)
                self.assertIsInstance(value, str)
                self.assertTrue(value)

    def test_profile_side_reasons_withhold_their_value_without_a_profile(self) -> None:
        for reason in (
            GateReason.PROFILE_RETENTION_EXCEEDED,
            GateReason.PROFILE_OBSERVATION_TOO_OLD,
            GateReason.PROFILE_INDEX_TOO_OLD,
            GateReason.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY,
            GateReason.FINALITY_HORIZON_PROFILE_MISMATCH,
            GateReason.PROFILE_POPULATION_MISMATCH,
        ):
            with self.subTest(reason=reason.value):
                self.assertIsNone(_governed_value(reason, self.request, None))

    def test_finality_horizon_value_comes_from_the_required_source(self) -> None:
        value = _governed_value(
            GateReason.INDEX_PRECEDES_FINALITY_HORIZON, self.request, self.profile
        )
        self.assertIsInstance(value, str)

    def test_reasons_without_a_comparison_value_disclose_nothing(self) -> None:
        for reason in (
            GateReason.ABSOLUTE_NEGATIVE_UNSUPPORTED,
            GateReason.NONZERO_MATCHES,
            GateReason.REQUIRED_SOURCE_MISSING,
            GateReason.PROFILE_REVOKED,
            GateReason.REGISTRY_SNAPSHOT_EXPIRED,
        ):
            with self.subTest(reason=reason.value):
                self.assertIsNone(_governed_value(reason, self.request, self.profile))

    def test_blind_intervals_disclose_only_when_the_profile_declares_them(self) -> None:
        value = _governed_value(
            GateReason.PROFILE_BLIND_INTERVAL_INTERSECTS_QUERY, self.request, self.profile
        )
        self.assertTrue(value is None or isinstance(value, str))

    def test_no_profile_resolves_without_a_context(self) -> None:
        self.assertIsNone(_selected_profile(None))

    def test_no_profile_resolves_when_the_selection_matches_no_record(self) -> None:
        data = {
            "registry_snapshot": _load("profile_registry.json"),
            "trust_selection": _load("profile_trust.json"),
        }
        data["trust_selection"]["selected_profile_reference"]["profile_version"] = "9.9.9"
        with self.assertRaises(ModelValidationError):
            # The trust selection pins a digest, so an unknown version is
            # rejected before it can silently resolve to nothing.
            TrustedProfileContext.from_dict(data)


class RemedyItemTests(unittest.TestCase):
    def test_item_rejects_malformed_fields(self) -> None:
        with self.assertRaises(ModelValidationError):
            RemedyItem("NONZERO_MATCHES", RemedyClass.UNSATISFIABLE, "x")  # type: ignore[arg-type]
        with self.assertRaises(ModelValidationError):
            RemedyItem(GateReason.NONZERO_MATCHES, "UNSATISFIABLE", "x")  # type: ignore[arg-type]
        with self.assertRaises(ModelValidationError):
            RemedyItem(GateReason.NONZERO_MATCHES, RemedyClass.UNSATISFIABLE, "   ")
        with self.assertRaises(ModelValidationError):
            RemedyItem(
                GateReason.NONZERO_MATCHES,
                RemedyClass.UNSATISFIABLE,
                "condition",
                governed_value=7,  # type: ignore[arg-type]
            )

    def test_item_renders_its_public_form(self) -> None:
        item = RemedyItem(
            GateReason.NONZERO_MATCHES,
            RemedyClass.UNSATISFIABLE,
            "condition",
            governed_value="value",
        )
        self.assertEqual(
            item.to_dict(),
            {
                "reason": "NONZERO_MATCHES",
                "remedy_class": "UNSATISFIABLE",
                "condition": "condition",
                "governed_value": "value",
            },
        )


class RemedyEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = _context()
        self.request = NegativeClaimRequest.from_dict(_load("partial_request.json"))
        self.decision = evaluate_negative_claim(self.request, self.context)

    def test_an_unclassified_reason_fails_loudly(self) -> None:
        """A new gate reason must not silently acquire a default remedy."""

        from evidence_state_io import remedy as remedy_module

        table = dict(remedy_module._REMEDY_TABLE)
        table.pop(GateReason.NONZERO_MATCHES)
        with mock.patch.object(remedy_module, "_REMEDY_TABLE", table):
            with self.assertRaises(ModelValidationError):
                remedy_module._classify(GateReason.NONZERO_MATCHES, self.request)

    def test_finality_horizon_is_withheld_when_no_required_source_declares_one(self) -> None:
        data = copy.deepcopy(_load("partial_request.json"))
        for requirement in data["envelope"]["query"]["source_requirements"]:
            requirement.pop("finality_horizon", None)
        refresh_query_fingerprints(data)
        request = NegativeClaimRequest.from_dict(data)
        self.assertIsNone(
            _governed_value(
                GateReason.INDEX_PRECEDES_FINALITY_HORIZON,
                request,
                _selected_profile(self.context),
            )
        )

    def test_validity_boundary_is_withheld_when_undeclared(self) -> None:
        data = copy.deepcopy(_load("partial_request.json"))
        data["envelope"]["valid_until"] = None
        request = NegativeClaimRequest.from_dict(data)
        self.assertIsNone(
            _governed_value(GateReason.RESULT_EXPIRED, request, _selected_profile(self.context))
        )

    def test_derivation_rejects_a_non_context_object(self) -> None:
        with self.assertRaises(ModelValidationError):
            derive_remedy(self.decision, self.request, self.request)  # type: ignore[arg-type]

    def test_derivation_rejects_a_rejection_carrying_no_reasons(self) -> None:
        """A rejection with no reasons is incoherent and must not be explained."""

        empty = dataclasses.replace(self.decision, reasons=())
        with self.assertRaises(ModelValidationError):
            derive_remedy(empty, self.request, self.context)


if __name__ == "__main__":
    unittest.main()
