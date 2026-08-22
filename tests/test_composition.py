"""More sources must buy robustness, never permission.

The property tests here are the point of the file. A composition that let
extra sources raise coverage, pull a horizon earlier, or freshen a stale
observation would let a caller reach a permit by adding sources rather than by
observing more.
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from itertools import permutations

from evidence_state_io.composition import (
    MAX_REQUIRED_SOURCES,
    CompositionIssueCode,
    CompositionMode,
    SourceContribution,
    compose_sources,
)
from evidence_state_io.coverage import CoverageAssessment
from evidence_state_io.errors import ModelValidationError
from evidence_state_io.models import EvidenceState

BASE = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def hours(count: float) -> timedelta:
    return timedelta(hours=count)


def contribution(
    source_id: str,
    *,
    lower_bound: float | None = 1.0,
    coverage_ok: bool = True,
    state: EvidenceState = EvidenceState.ABSENT_WITHIN_SCOPE,
    matched_count: int = 0,
    observed_at: datetime | None = None,
    index_offset: float = 2.0,
    horizon_offset: float = 1.0,
    valid_offset: float | None = 8.0,
) -> SourceContribution:
    """Build a source that supports an in-scope absence unless told otherwise."""

    return SourceContribution(
        source_id=source_id,
        state=state,
        matched_count=matched_count,
        coverage=CoverageAssessment(lower_bound=lower_bound, meets_policy=coverage_ok),
        observed_at=BASE if observed_at is None else observed_at,
        index_as_of=BASE + hours(index_offset),
        finality_horizon=BASE + hours(horizon_offset),
        valid_until=None if valid_offset is None else BASE + hours(valid_offset),
    )


class CompositionBasicsTests(unittest.TestCase):
    def test_agreeing_sources_support_an_in_scope_absence(self) -> None:
        assessment = compose_sources([contribution("a"), contribution("b")])
        self.assertEqual(assessment.issues, ())
        self.assertTrue(assessment.meets_policy)
        self.assertIs(assessment.composed_state, EvidenceState.ABSENT_WITHIN_SCOPE)
        self.assertEqual(assessment.source_ids, ("a", "b"))

    def test_a_single_source_composes_to_itself(self) -> None:
        assessment = compose_sources([contribution("a", lower_bound=0.9)])
        self.assertTrue(assessment.meets_policy)
        self.assertEqual(assessment.composed_lower_bound, 0.9)

    def test_an_empty_composition_is_refused(self) -> None:
        with self.assertRaises(ModelValidationError):
            compose_sources([])

    def test_more_sources_than_the_cap_are_refused(self) -> None:
        many = [contribution(f"s{index}") for index in range(MAX_REQUIRED_SOURCES + 1)]
        assessment = compose_sources(many)
        self.assertIn(
            CompositionIssueCode.TOO_MANY_REQUIRED_SOURCES,
            [issue.code for issue in assessment.issues],
        )
        self.assertFalse(assessment.meets_policy)

    def test_duplicate_source_ids_are_refused(self) -> None:
        assessment = compose_sources([contribution("a"), contribution("a")])
        self.assertIn(
            CompositionIssueCode.DUPLICATE_SOURCE_ID,
            [issue.code for issue in assessment.issues],
        )

    def test_composition_rejects_wrong_types(self) -> None:
        with self.assertRaises(ModelValidationError):
            compose_sources([contribution("a")], mode="CORROBORATION")  # type: ignore[arg-type]
        with self.assertRaises(ModelValidationError):
            compose_sources("not-a-sequence")  # type: ignore[arg-type]
        with self.assertRaises(ModelValidationError):
            compose_sources([{"source_id": "a"}])  # type: ignore[list-item]


class CoverageCompositionTests(unittest.TestCase):
    """Corroborated coverage composes by maximum, never by sum."""

    def test_two_partial_sources_do_not_add_up(self) -> None:
        assessment = compose_sources(
            [
                contribution("a", lower_bound=0.6, coverage_ok=False),
                contribution("b", lower_bound=0.6, coverage_ok=False),
            ]
        )
        self.assertEqual(
            assessment.composed_lower_bound,
            0.6,
            "0.6 and 0.6 over the same population is 0.6, not 1.2 and not 0.8",
        )
        self.assertFalse(assessment.meets_policy)

    def test_composed_bound_is_the_maximum_of_its_inputs(self) -> None:
        for bounds in ((0.2, 0.9), (0.9, 0.2), (0.5, 0.5), (0.1, 0.4, 0.7)):
            with self.subTest(bounds=bounds):
                assessment = compose_sources(
                    [
                        contribution(f"s{index}", lower_bound=bound, coverage_ok=False)
                        for index, bound in enumerate(bounds)
                    ]
                )
                self.assertEqual(assessment.composed_lower_bound, max(bounds))
                self.assertLessEqual(assessment.composed_lower_bound or 0.0, 1.0)

    def test_adding_a_source_never_increases_composed_coverage_above_the_best(self) -> None:
        """The property that stops coverage being bought by adding sources."""

        best = contribution("best", lower_bound=0.8, coverage_ok=False)
        alone = compose_sources([best]).composed_lower_bound
        for extra_count in range(1, MAX_REQUIRED_SOURCES):
            group = [best] + [
                contribution(f"extra{index}", lower_bound=0.79, coverage_ok=False)
                for index in range(extra_count)
            ]
            composed = compose_sources(group).composed_lower_bound
            self.assertEqual(
                composed,
                alone,
                f"{extra_count} weaker corroborating sources changed the floor",
            )

    def test_an_unquantified_source_does_not_lower_a_known_floor(self) -> None:
        assessment = compose_sources(
            [
                contribution("known", lower_bound=0.75, coverage_ok=False),
                contribution("unquantified", lower_bound=None, coverage_ok=False),
            ]
        )
        self.assertEqual(assessment.composed_lower_bound, 0.75)

    def test_coverage_is_unquantified_only_when_no_source_quantifies_it(self) -> None:
        assessment = compose_sources(
            [
                contribution("a", lower_bound=None, coverage_ok=False),
                contribution("b", lower_bound=None, coverage_ok=False),
            ]
        )
        self.assertIsNone(assessment.composed_lower_bound)
        self.assertIn(
            CompositionIssueCode.COMPOSED_COVERAGE_UNQUANTIFIED,
            [issue.code for issue in assessment.issues],
        )


class FinalityCompositionTests(unittest.TestCase):
    def test_the_binding_horizon_is_the_latest_not_the_earliest(self) -> None:
        assessment = compose_sources(
            [
                contribution("fast", horizon_offset=1.0, index_offset=5.0),
                contribution("slow", horizon_offset=4.0, index_offset=5.0),
            ]
        )
        self.assertEqual(assessment.binding_finality_horizon, BASE + hours(4.0))
        self.assertTrue(assessment.meets_policy)

    def test_each_source_must_reach_its_own_horizon_not_the_earliest(self) -> None:
        """The trap a shared-horizon implementation falls into.

        `slow` has an index past the earliest horizon in the set but short of
        its own, so a composition that used one shared horizon would permit a
        claim while `slow` could still receive a late arrival.
        """

        assessment = compose_sources(
            [
                contribution("fast", horizon_offset=1.0, index_offset=1.5),
                contribution("slow", horizon_offset=4.0, index_offset=2.0),
            ]
        )
        codes = [(issue.code, issue.source_id) for issue in assessment.issues]
        self.assertIn(
            (CompositionIssueCode.SOURCE_INDEX_PRECEDES_OWN_HORIZON, "slow"),
            codes,
        )
        self.assertNotIn(
            (CompositionIssueCode.SOURCE_INDEX_PRECEDES_OWN_HORIZON, "fast"),
            codes,
            "fast reached its own horizon and must not be faulted for the group's latest",
        )
        self.assertFalse(assessment.meets_policy)

    def test_adding_a_source_never_moves_the_binding_horizon_earlier(self) -> None:
        group = [contribution("a", horizon_offset=3.0, index_offset=5.0)]
        previous = compose_sources(group).binding_finality_horizon
        for index, offset in enumerate((1.0, 2.0, 0.5)):
            group.append(contribution(f"later{index}", horizon_offset=offset, index_offset=5.0))
            current = compose_sources(group).binding_finality_horizon
            assert current is not None and previous is not None
            self.assertGreaterEqual(current, previous)
            previous = current

    def test_an_undeclared_horizon_or_index_is_faulted_per_source(self) -> None:
        no_horizon = SourceContribution(
            source_id="a",
            state=EvidenceState.ABSENT_WITHIN_SCOPE,
            matched_count=0,
            coverage=CoverageAssessment(lower_bound=1.0, meets_policy=True),
            observed_at=BASE,
            index_as_of=BASE + hours(2),
            finality_horizon=None,
        )
        no_index = SourceContribution(
            source_id="b",
            state=EvidenceState.ABSENT_WITHIN_SCOPE,
            matched_count=0,
            coverage=CoverageAssessment(lower_bound=1.0, meets_policy=True),
            observed_at=BASE,
            index_as_of=None,
            finality_horizon=BASE + hours(1),
        )
        codes = [
            (issue.code, issue.source_id)
            for issue in compose_sources([no_horizon, no_index]).issues
        ]
        self.assertIn((CompositionIssueCode.SOURCE_FINALITY_HORIZON_UNDECLARED, "a"), codes)
        self.assertIn((CompositionIssueCode.SOURCE_INDEX_UNDECLARED, "b"), codes)


class FreshnessCompositionTests(unittest.TestCase):
    def test_a_composed_claim_is_as_fresh_as_its_stalest_source(self) -> None:
        assessment = compose_sources(
            [
                contribution("fresh", observed_at=BASE + hours(3)),
                contribution("stale", observed_at=BASE - hours(9)),
            ]
        )
        self.assertEqual(assessment.stalest_observed_at, BASE - hours(9))

    def test_adding_a_source_never_makes_the_composition_fresher(self) -> None:
        group = [contribution("a", observed_at=BASE)]
        previous = compose_sources(group).stalest_observed_at
        for index, offset in enumerate((2.0, -4.0, 6.0)):
            group.append(contribution(f"more{index}", observed_at=BASE + hours(offset)))
            current = compose_sources(group).stalest_observed_at
            self.assertLessEqual(current, previous)
            previous = current

    def test_validity_binds_on_the_earliest_boundary(self) -> None:
        assessment = compose_sources(
            [
                contribution("long", valid_offset=20.0),
                contribution("short", valid_offset=5.0),
            ]
        )
        self.assertEqual(assessment.earliest_valid_until, BASE + hours(5.0))

    def test_the_weakest_index_is_reported_not_the_strongest(self) -> None:
        assessment = compose_sources(
            [
                contribution("ahead", index_offset=9.0),
                contribution("behind", index_offset=2.0),
            ]
        )
        self.assertEqual(assessment.weakest_index_as_of, BASE + hours(2.0))


class DisagreementTests(unittest.TestCase):
    def test_presence_against_absence_is_contradictory_not_a_vote(self) -> None:
        assessment = compose_sources(
            [
                contribution("absent1"),
                contribution("absent2"),
                contribution("present", state=EvidenceState.PRESENT, matched_count=4),
            ]
        )
        self.assertIs(assessment.composed_state, EvidenceState.CONTRADICTORY)
        self.assertFalse(
            assessment.meets_policy,
            "two absent sources must not outvote one that found something",
        )
        self.assertIn(
            CompositionIssueCode.SOURCE_STATES_DISAGREE,
            [issue.code for issue in assessment.issues],
        )

    def test_contradiction_does_not_depend_on_which_side_is_larger(self) -> None:
        majority_absent = compose_sources(
            [
                contribution("a"),
                contribution("b"),
                contribution("c", state=EvidenceState.PRESENT, matched_count=1),
            ]
        )
        majority_present = compose_sources(
            [
                contribution("a"),
                contribution("b", state=EvidenceState.PRESENT, matched_count=1),
                contribution("c", state=EvidenceState.PRESENT, matched_count=1),
            ]
        )
        self.assertIs(majority_absent.composed_state, EvidenceState.CONTRADICTORY)
        self.assertIs(majority_present.composed_state, EvidenceState.CONTRADICTORY)

    def test_matches_alone_contradict_a_reported_absence(self) -> None:
        assessment = compose_sources(
            [
                contribution("absent"),
                contribution("counted", matched_count=2),
            ]
        )
        self.assertIs(assessment.composed_state, EvidenceState.CONTRADICTORY)

    def test_indeterminate_states_compose_to_the_worst_one(self) -> None:
        assessment = compose_sources(
            [
                contribution("partial", state=EvidenceState.PARTIAL),
                contribution("failed", state=EvidenceState.FAILED),
            ]
        )
        self.assertIs(assessment.composed_state, EvidenceState.FAILED)
        self.assertFalse(assessment.meets_policy)


class DeterminismTests(unittest.TestCase):
    def _group(self) -> list[SourceContribution]:
        return [
            contribution("a", lower_bound=0.4, coverage_ok=False, horizon_offset=1.0),
            contribution("b", lower_bound=0.7, coverage_ok=False, horizon_offset=3.0),
            contribution("c", lower_bound=None, coverage_ok=False, observed_at=BASE - hours(2)),
        ]

    def test_the_assessment_is_a_property_of_the_set_not_the_order(self) -> None:
        rendered = {
            json.dumps(compose_sources(list(order)).to_dict(), sort_keys=True)
            for order in permutations(self._group())
        }
        self.assertEqual(len(rendered), 1, "composition depends on input order")

    def test_repeated_composition_is_byte_identical(self) -> None:
        group = self._group()
        rendered = {
            json.dumps(compose_sources(group).to_dict(), sort_keys=True) for _ in range(100)
        }
        self.assertEqual(len(rendered), 1)

    def test_the_public_form_round_trips_through_json(self) -> None:
        payload = compose_sources(self._group()).to_dict()
        self.assertEqual(json.loads(json.dumps(payload)), payload)
        self.assertEqual(payload["mode"], CompositionMode.CORROBORATION.value)
        self.assertIn("composition_schema", payload)


class ContributionValidationTests(unittest.TestCase):
    def test_contributions_reject_malformed_fields(self) -> None:
        good = contribution("a")
        for field, value in (
            ("source_id", "  "),
            ("state", "ABSENT_WITHIN_SCOPE"),
            ("matched_count", -1),
            ("coverage", {"lower_bound": 1.0}),
            ("observed_at", None),
            ("index_as_of", datetime(2026, 8, 21, 12, 0)),
        ):
            with self.subTest(field=field):
                payload = {
                    "source_id": good.source_id,
                    "state": good.state,
                    "matched_count": good.matched_count,
                    "coverage": good.coverage,
                    "observed_at": good.observed_at,
                    "index_as_of": good.index_as_of,
                    "finality_horizon": good.finality_horizon,
                    "valid_until": good.valid_until,
                }
                payload[field] = value
                with self.assertRaises(ModelValidationError):
                    SourceContribution(**payload)  # type: ignore[arg-type]

    def test_contribution_renders_its_public_form(self) -> None:
        payload = contribution("a").to_dict()
        self.assertEqual(payload["source_id"], "a")
        self.assertEqual(payload["state"], "ABSENT_WITHIN_SCOPE")
        self.assertEqual(json.loads(json.dumps(payload)), payload)


if __name__ == "__main__":
    unittest.main()
