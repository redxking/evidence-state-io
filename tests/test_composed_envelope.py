"""The composed evaluation path, exercised end to end through the gate.

These tests are written against the rules that make composition safe rather
than against the implementation: coverage composes by maximum, finality binds
on the slowest source, freshness on the stalest, validity on the earliest, and
disagreement is never resolved by counting. Each test is arranged so that an
implementation which took the convenient branch instead would fail it.
"""

from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from evidence_state_io.composition import CompositionMode
from evidence_state_io.errors import ModelValidationError
from evidence_state_io.gate import (
    GateDecision,
    GateReason,
    NegativeClaimRequest,
    evaluate_negative_claim,
)
from evidence_state_io.models import EvidenceState
from evidence_state_io.profiles import TrustedProfileContext
from tests.helpers import composed_fixture, mirror_observation, request, trusted_context


def _decide(data: dict[str, Any], context: TrustedProfileContext) -> GateDecision:
    return evaluate_negative_claim(NegativeClaimRequest.from_dict(data), context)


def _reasons(decision: GateDecision) -> set[str]:
    return {reason.value for reason in decision.reasons}


class ComposedPermitTests(unittest.TestCase):
    def test_a_composed_claim_can_be_permitted(self) -> None:
        """Semantics nothing can reach are not a capability."""

        data, context = composed_fixture()
        decision = _decide(data, context)

        self.assertTrue(decision.allowed, sorted(_reasons(decision)))
        self.assertIsNotNone(decision.composition)
        assert decision.composition is not None
        self.assertIs(decision.composition.mode, CompositionMode.CORROBORATION)
        self.assertIs(
            decision.composition.composed_state,
            EvidenceState.ABSENT_WITHIN_SCOPE,
        )
        self.assertEqual(len(decision.composition.source_ids), 2)
        self.assertEqual(decision.composition.issues, ())

    def test_the_permit_states_that_corroboration_did_not_accumulate_coverage(self) -> None:
        data, context = composed_fixture()
        decision = _decide(data, context)
        claim = decision.qualified_claim or ""

        self.assertIn("not a sum", claim)
        self.assertIn("corroboration", claim)
        assert decision.composition is not None
        for source_id in decision.composition.source_ids:
            self.assertIn(source_id, claim)
        self.assertTrue(
            any("does not establish independence" in item for item in decision.limitations),
            "a composed decision must state that agreement is not independence",
        )
        self.assertFalse(
            any("does not establish multi-source" in item for item in decision.limitations),
            "a composed decision must not still claim composition is unimplemented",
        )


class ComposedRuleTests(unittest.TestCase):
    def test_the_binding_horizon_is_the_latest_source_horizon(self) -> None:
        """Finality binds on the slowest source, not the first or the fastest."""

        data, context = composed_fixture(mirrors=3)
        decision = _decide(data, context)
        self.assertTrue(decision.allowed, sorted(_reasons(decision)))
        assert decision.composition is not None

        horizons = sorted(
            requirement["finality_horizon"]
            for requirement in data["envelope"]["query"]["source_requirements"]
        )
        binding = decision.composition.binding_finality_horizon
        assert binding is not None
        self.assertEqual(
            binding,
            datetime.fromisoformat(horizons[-1].replace("Z", "+00:00")),
        )
        self.assertNotEqual(
            binding,
            datetime.fromisoformat(horizons[0].replace("Z", "+00:00")),
            "binding on the earliest horizon would permit a claim a lagging source could still overturn",
        )

    def test_coverage_composes_by_maximum_and_never_by_sum(self) -> None:
        """Two 60% sources cover at least 60%, not 120% and not 100%."""

        data, context = composed_fixture()
        for observation in data["envelope"]["source_observations"]:
            observation["coverage"]["examined_units"] = 60
            observation["coverage"]["pages_examined"] = 3
            observation["coverage"]["pagination_complete"] = False

        decision = _decide(data, context)
        assert decision.composition is not None
        bound = decision.composition.composed_lower_bound
        assert bound is not None

        self.assertAlmostEqual(bound, 0.6)
        self.assertLessEqual(bound, 1.0)
        self.assertFalse(decision.allowed)
        self.assertIn(GateReason.COMPOSED_SOURCE_COVERAGE_NOT_MET.value, _reasons(decision))
        self.assertIn(GateReason.COMPOSED_COVERAGE_OVERSTATED.value, _reasons(decision))

    def test_an_envelope_may_not_claim_more_coverage_than_its_sources_support(self) -> None:
        data, context = composed_fixture()
        weakened = mirror_observation(data)
        weakened["coverage"]["examined_units"] = 60
        weakened["coverage"]["pages_examined"] = 3
        weakened["coverage"]["pagination_complete"] = False

        decision = _decide(data, context)
        assert decision.composition is not None
        # The strongest single source still guarantees 100%, so the composed
        # floor stays there; the rejection comes from the weak source itself.
        self.assertAlmostEqual(decision.composition.composed_lower_bound or 0.0, 1.0)
        self.assertNotIn(GateReason.COMPOSED_COVERAGE_OVERSTATED.value, _reasons(decision))
        self.assertIn(GateReason.COMPOSED_SOURCE_COVERAGE_NOT_MET.value, _reasons(decision))
        self.assertFalse(decision.allowed)

    def test_a_dissenting_source_is_not_outvoted_by_a_majority(self) -> None:
        """Three agreeing sources do not convert a contradiction into a permit."""

        data, context = composed_fixture(mirrors=3)
        dissenter = mirror_observation(data, index=3)
        dissenter["state"] = EvidenceState.PRESENT.value
        dissenter["matched_count"] = 1

        decision = _decide(data, context)
        assert decision.composition is not None

        self.assertIs(decision.composition.composed_state, EvidenceState.CONTRADICTORY)
        self.assertFalse(decision.allowed)
        self.assertIn(GateReason.COMPOSED_SOURCE_STATES_DISAGREE.value, _reasons(decision))
        self.assertIn(GateReason.COMPOSED_SOURCE_REPORTS_MATCHES.value, _reasons(decision))

    def test_freshness_binds_on_the_stalest_source(self) -> None:
        """A late-sealed envelope may not hide a source that was read long before."""

        data, context = composed_fixture()
        envelope = data["envelope"]
        envelope["observed_at"] = "2026-08-21T13:30:00Z"
        envelope["valid_until"] = "2026-08-21T14:00:00Z"
        for observation in envelope["source_observations"]:
            observation["valid_until"] = "2026-08-21T14:00:00Z"
        data["evaluated_at"] = "2026-08-21T13:31:00Z"
        data["policy"] = dict(data["policy"], max_observation_age_seconds=3600)

        decision = _decide(data, context)

        envelope_age = datetime(2026, 8, 21, 13, 31, tzinfo=timezone.utc) - datetime(
            2026, 8, 21, 13, 30, tzinfo=timezone.utc
        )
        self.assertLess(
            envelope_age,
            timedelta(seconds=3600),
            "the envelope's own age must be inside the limit, or this test proves nothing",
        )
        self.assertFalse(decision.allowed)
        self.assertIn(GateReason.OBSERVATION_TOO_OLD.value, _reasons(decision))

    def test_validity_binds_on_the_earliest_source(self) -> None:
        data, context = composed_fixture()
        mirror_observation(data)["valid_until"] = "2026-08-21T12:30:00Z"

        decision = _decide(data, context)
        assert decision.composition is not None
        self.assertEqual(
            decision.composition.earliest_valid_until,
            datetime(2026, 8, 21, 12, 30, tzinfo=timezone.utc),
        )
        self.assertFalse(decision.allowed)
        self.assertIn(GateReason.COMPOSED_VALIDITY_OVERSTATED.value, _reasons(decision))

    def test_source_order_does_not_change_the_decision(self) -> None:
        """The assessment is a property of the source set, not of the caller."""

        data, context = composed_fixture(mirrors=2)
        reversed_data = deepcopy(data)
        reversed_data["envelope"]["source_observations"].reverse()
        reversed_data["envelope"]["query"]["source_requirements"].reverse()

        self.assertEqual(
            _decide(data, context).to_dict(),
            _decide(reversed_data, context).to_dict(),
        )


class ComposedBoundaryTests(unittest.TestCase):
    def test_a_required_source_without_its_own_assessment_is_refused(self) -> None:
        data, _ = composed_fixture()
        observation = mirror_observation(data)
        for field in ("state", "matched_count", "observed_at", "coverage", "valid_until"):
            observation.pop(field, None)

        with self.assertRaisesRegex(
            ModelValidationError,
            "composed envelope requires a per-source assessment",
        ):
            NegativeClaimRequest.from_dict(data)

    def test_a_partial_assessment_is_refused(self) -> None:
        """A state without a count cannot be checked against anything."""

        data, _ = composed_fixture()
        del mirror_observation(data)["matched_count"]

        with self.assertRaisesRegex(ModelValidationError, "together; missing"):
            NegativeClaimRequest.from_dict(data)

    def test_a_validity_boundary_alone_is_not_an_assessment(self) -> None:
        """A boundary with no state, count, or coverage bounds nothing."""

        data, _ = composed_fixture()
        observation = mirror_observation(data)
        for field in ("state", "matched_count", "observed_at", "coverage"):
            observation.pop(field, None)

        with self.assertRaisesRegex(ModelValidationError, "together; missing"):
            NegativeClaimRequest.from_dict(data)

    def test_a_source_may_not_relabel_a_failure_as_an_absence(self) -> None:
        data, _ = composed_fixture()
        observation = mirror_observation(data)
        observation["status"] = "FAILED"
        observation["errors"] = ["adapter timed out"]

        with self.assertRaisesRegex(ModelValidationError, "not compatible with"):
            NegativeClaimRequest.from_dict(data)

    def test_more_required_sources_than_the_bound_are_refused(self) -> None:
        with self.assertRaises(ModelValidationError):
            composed_fixture(mirrors=4)


class CompositionReasonMapTests(unittest.TestCase):
    def test_every_emittable_composition_issue_maps_to_a_reason(self) -> None:
        """A missing mapping would raise inside the gate rather than reject."""

        from evidence_state_io.composition import CompositionIssueCode
        from evidence_state_io.gate import _COMPOSITION_REASON_MAP

        emittable = set(CompositionIssueCode) - {CompositionIssueCode.NO_REQUIRED_SOURCES}
        self.assertEqual(emittable, set(_COMPOSITION_REASON_MAP))
        for reason in _COMPOSITION_REASON_MAP.values():
            self.assertIsInstance(reason, GateReason)

    def test_the_excluded_issue_is_unreachable_because_the_composer_raises(self) -> None:
        from evidence_state_io.composition import compose_sources

        with self.assertRaises(ModelValidationError):
            compose_sources(())


class SingleSourceUnchangedTests(unittest.TestCase):
    def test_a_single_source_decision_carries_no_composition(self) -> None:
        decision = evaluate_negative_claim(request(), trusted_context())
        payload = decision.to_dict()

        self.assertTrue(decision.allowed, sorted(_reasons(decision)))
        self.assertIsNone(decision.composition)
        self.assertNotIn(
            "composition",
            payload,
            "adding the key unconditionally would break every recorded certificate digest",
        )
        self.assertTrue(
            any("does not establish multi-source" in item for item in decision.limitations)
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
