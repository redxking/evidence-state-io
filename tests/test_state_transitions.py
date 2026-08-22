from __future__ import annotations

import unittest

from evidence_state_io import (
    EVIDENCE_STATE_INTERPRETATIONS,
    EVIDENCE_STATE_TRANSITION_MODEL,
    EvidenceState,
    EvidenceStateTransition,
    ModelValidationError,
    ValidationErrorCode,
    allowed_evidence_state_transitions,
    is_evidence_state_transition_allowed,
)


class EvidenceStateTransitionTests(unittest.TestCase):
    def test_contract_identifier_is_exact_and_versioned(self) -> None:
        self.assertEqual(
            EVIDENCE_STATE_TRANSITION_MODEL,
            "esio-evidence-state-transition-model/1.0-candidate.1",
        )

    def test_every_state_has_one_normative_interpretation(self) -> None:
        self.assertEqual(tuple(EVIDENCE_STATE_INTERPRETATIONS), tuple(EvidenceState))
        expected_fragments = {
            EvidenceState.PRESENT: "One or more in-scope matches",
            EvidenceState.ABSENT_WITHIN_SCOPE: "every condition required",
            EvidenceState.NOT_OBSERVED: "sufficient absence conditions were not established",
            EvidenceState.PARTIAL: "known subset",
            EvidenceState.STALE: "freshness condition",
            EvidenceState.INACCESSIBLE: "could not be accessed",
            EvidenceState.PENDING_WINDOW: "horizon had not closed",
            EvidenceState.FAILED: "did not complete successfully",
            EvidenceState.CONTRADICTORY: "mutually inconsistent",
        }
        for state, fragment in expected_fragments.items():
            with self.subTest(state=state.value):
                self.assertIn(fragment, EVIDENCE_STATE_INTERPRETATIONS[state])

    def test_complete_nine_by_nine_transition_matrix(self) -> None:
        noninitial = tuple(
            state for state in EvidenceState if state is not EvidenceState.NOT_OBSERVED
        )
        expected = {
            state: (
                (EvidenceState.PRESENT,)
                if state is EvidenceState.PRESENT
                else tuple(EvidenceState)
                if state is EvidenceState.NOT_OBSERVED
                else noninitial
            )
            for state in EvidenceState
        }

        for prior_state in EvidenceState:
            self.assertEqual(
                allowed_evidence_state_transitions(prior_state),
                expected[prior_state],
            )
            for next_state in EvidenceState:
                with self.subTest(
                    prior_state=prior_state.value,
                    next_state=next_state.value,
                ):
                    self.assertEqual(
                        is_evidence_state_transition_allowed(
                            prior_state,
                            next_state,
                        ),
                        next_state in expected[prior_state],
                    )

    def test_present_is_absorbing_within_one_fixed_claim_lineage(self) -> None:
        self.assertEqual(
            allowed_evidence_state_transitions(EvidenceState.PRESENT),
            (EvidenceState.PRESENT,),
        )

    def test_not_observed_is_the_only_entry_state(self) -> None:
        self.assertEqual(
            allowed_evidence_state_transitions(EvidenceState.NOT_OBSERVED),
            tuple(EvidenceState),
        )
        for prior_state in EvidenceState:
            if prior_state is EvidenceState.NOT_OBSERVED:
                continue
            with self.subTest(prior_state=prior_state.value):
                self.assertFalse(
                    is_evidence_state_transition_allowed(
                        prior_state,
                        EvidenceState.NOT_OBSERVED,
                    )
                )

    def test_indeterminate_states_can_resolve_or_remain_fail_closed(self) -> None:
        for prior_state in (
            EvidenceState.PARTIAL,
            EvidenceState.STALE,
            EvidenceState.INACCESSIBLE,
            EvidenceState.PENDING_WINDOW,
            EvidenceState.FAILED,
            EvidenceState.CONTRADICTORY,
        ):
            with self.subTest(prior_state=prior_state.value):
                allowed = allowed_evidence_state_transitions(prior_state)
                self.assertIn(EvidenceState.PRESENT, allowed)
                self.assertIn(EvidenceState.ABSENT_WITHIN_SCOPE, allowed)
                self.assertIn(prior_state, allowed)

    def test_absence_can_be_invalidated_by_later_evidence_or_conditions(self) -> None:
        allowed = allowed_evidence_state_transitions(
            EvidenceState.ABSENT_WITHIN_SCOPE
        )
        self.assertIn(EvidenceState.PRESENT, allowed)
        self.assertIn(EvidenceState.STALE, allowed)
        self.assertIn(EvidenceState.PENDING_WINDOW, allowed)
        self.assertNotIn(EvidenceState.NOT_OBSERVED, allowed)

    def test_transition_round_trip_is_exact(self) -> None:
        transition = EvidenceStateTransition(
            transition_model=EVIDENCE_STATE_TRANSITION_MODEL,
            prior_state=EvidenceState.PARTIAL,
            next_state=EvidenceState.ABSENT_WITHIN_SCOPE,
        )
        self.assertEqual(
            EvidenceStateTransition.from_dict(transition.to_dict()),
            transition,
        )

    def test_disallowed_transition_fails_with_stable_code(self) -> None:
        with self.assertRaises(ModelValidationError) as caught:
            EvidenceStateTransition(
                transition_model=EVIDENCE_STATE_TRANSITION_MODEL,
                prior_state=EvidenceState.PRESENT,
                next_state=EvidenceState.ABSENT_WITHIN_SCOPE,
            )
        self.assertEqual(
            caught.exception.code,
            ValidationErrorCode.STATE_TRANSITION_INVALID,
        )

    def test_unknown_transition_model_fails_closed_without_fallback(self) -> None:
        for model in (
            "esio-evidence-state-transition-model/1.0-candidate.0",
            "esio-evidence-state-transition-model/latest",
            "1.0-candidate.1",
            None,
        ):
            with self.subTest(model=model):
                with self.assertRaises(ModelValidationError) as caught:
                    allowed_evidence_state_transitions(
                        EvidenceState.PARTIAL,
                        transition_model=model,  # type: ignore[arg-type]
                    )
                self.assertEqual(
                    caught.exception.code,
                    ValidationErrorCode.UNSUPPORTED_CONTRACT,
                )

    def test_overloaded_string_equality_cannot_bypass_model_identity(self) -> None:
        class EqualityBypass(str):
            def __eq__(self, other: object) -> bool:
                return True

            def __ne__(self, other: object) -> bool:
                return False

        with self.assertRaises(ModelValidationError) as caught:
            allowed_evidence_state_transitions(
                EvidenceState.PARTIAL,
                transition_model=EqualityBypass("attacker-selected"),
            )
        self.assertEqual(
            caught.exception.code,
            ValidationErrorCode.UNSUPPORTED_CONTRACT,
        )

    def test_unknown_or_aliased_json_state_is_rejected(self) -> None:
        base = {
            "transition_model": EVIDENCE_STATE_TRANSITION_MODEL,
            "prior_state": "PARTIAL",
            "next_state": "PRESENT",
        }
        for field, value in (
            ("prior_state", "partial"),
            ("next_state", "UNKNOWN"),
            ("next_state", None),
        ):
            with self.subTest(field=field, value=value):
                candidate = dict(base)
                candidate[field] = value
                with self.assertRaises(ModelValidationError) as caught:
                    EvidenceStateTransition.from_dict(candidate)
                self.assertEqual(
                    caught.exception.code,
                    ValidationErrorCode.MODEL_INVALID,
                )


if __name__ == "__main__":
    unittest.main()
