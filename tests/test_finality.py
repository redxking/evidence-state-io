from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from evidence_state_io import (
    GateReason,
    ModelValidationError,
    NegativeClaimPolicy,
    NegativeClaimRequest,
    evaluate_negative_claim,
)
from evidence_state_io.models import datetime_to_json

from tests.helpers import (
    refresh_query_fingerprints,
    request,
    request_dict,
    trusted_context,
)


UTC = timezone.utc


def policy_dict(**changes):
    return {
        "policy_id": "esio-p0-safety-floor",
        "policy_version": "1.0-candidate.4",
        **changes,
    }


def source_requirement(data):
    return data["envelope"]["query"]["source_requirements"][0]


def source_descriptor(data):
    return data["envelope"]["source_observations"][0]["descriptor"]


def bind_horizon(data, value):
    source_requirement(data)["finality_horizon"] = value
    return refresh_query_fingerprints(data)


def evaluate(data):
    return evaluate_negative_claim(
        NegativeClaimRequest.from_dict(data), trusted_context()
    )


def set_timeline(
    data,
    *,
    query_end: datetime,
    horizon: datetime | None,
    index_as_of: datetime,
    observed_at: datetime,
    evaluated_at: datetime,
    valid_until: datetime,
):
    data["envelope"]["query"]["time_end"] = datetime_to_json(query_end)
    source_requirement(data)["finality_horizon"] = (
        datetime_to_json(horizon) if horizon is not None else None
    )
    source_descriptor(data)["index_as_of"] = datetime_to_json(index_as_of)
    data["envelope"]["observed_at"] = datetime_to_json(observed_at)
    data["envelope"]["valid_until"] = datetime_to_json(valid_until)
    data["evaluated_at"] = datetime_to_json(evaluated_at)
    refresh_query_fingerprints(data)
    return data


class FinalityContractTests(unittest.TestCase):
    def test_missing_and_explicit_null_horizon_fail_closed_with_same_reason(self) -> None:
        results = []
        for representation in ("missing", "null"):
            with self.subTest(representation=representation):
                data = request_dict()
                if representation == "missing":
                    source_requirement(data).pop("finality_horizon", None)
                else:
                    source_requirement(data)["finality_horizon"] = None
                refresh_query_fingerprints(data)

                result = evaluate(data)

                self.assertFalse(result.allowed)
                self.assertEqual(
                    result.reasons,
                    (GateReason.FINALITY_HORIZON_UNDECLARED,),
                )
                results.append(result.to_dict())
        self.assertEqual(results[0], results[1])

    def test_horizon_rejects_malformed_naive_and_submicrosecond_timestamps(self) -> None:
        cases = (
            ("not-a-time", "ISO-8601"),
            ("2026-08-21T12:00:00", "UTC offset"),
            ("2026-08-21T12:00:00.0000000Z", "at most 6"),
        )
        for value, message in cases:
            with self.subTest(value=value):
                data = request_dict()
                source_requirement(data)["finality_horizon"] = value
                with self.assertRaisesRegex(ModelValidationError, message):
                    NegativeClaimRequest.from_dict(data)

    def test_horizon_before_query_end_is_invalid_and_equality_is_valid(self) -> None:
        data = request_dict()
        query_end = datetime.fromisoformat(
            data["envelope"]["query"]["time_end"].replace("Z", "+00:00")
        )
        source_requirement(data)["finality_horizon"] = datetime_to_json(
            query_end - timedelta(microseconds=1)
        )
        with self.assertRaisesRegex(
            ModelValidationError,
            "finality_horizon must not precede query.time_end",
        ):
            NegativeClaimRequest.from_dict(data)

        equal = request_dict()
        bind_horizon(equal, datetime_to_json(query_end))
        self.assertEqual(
            NegativeClaimRequest.from_dict(equal)
            .envelope.query.source_requirements[0]
            .finality_horizon,
            query_end,
        )

        above = request_dict()
        bind_horizon(
            above,
            datetime_to_json(query_end + timedelta(microseconds=1)),
        )
        self.assertEqual(
            NegativeClaimRequest.from_dict(above)
            .envelope.query.source_requirements[0]
            .finality_horizon,
            query_end + timedelta(microseconds=1),
        )

    def test_index_below_equal_and_above_finality_horizon(self) -> None:
        query_end = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
        horizon = query_end + timedelta(minutes=4)
        observed = horizon + timedelta(minutes=1)
        evaluated = observed + timedelta(minutes=1)
        valid_until = evaluated + timedelta(minutes=1)

        expected = (
            (-1, False, (GateReason.INDEX_PRECEDES_FINALITY_HORIZON,)),
            (0, True, ()),
            (1, True, ()),
        )
        for delta_microseconds, allowed, reasons in expected:
            with self.subTest(delta_microseconds=delta_microseconds):
                data = set_timeline(
                    request_dict(),
                    query_end=query_end,
                    horizon=horizon,
                    index_as_of=horizon + timedelta(microseconds=delta_microseconds),
                    observed_at=observed,
                    evaluated_at=evaluated,
                    valid_until=valid_until,
                )
                result = evaluate(data)
                self.assertIs(result.allowed, allowed)
                self.assertEqual(result.reasons, reasons)

    def test_evaluation_below_equal_and_above_horizon_uses_only_supplied_time(self) -> None:
        query_end = datetime(2026, 8, 21, 11, 56, tzinfo=UTC)
        horizon = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)

        below = set_timeline(
            request_dict(),
            query_end=query_end,
            horizon=horizon,
            index_as_of=horizon - timedelta(microseconds=1),
            observed_at=horizon - timedelta(microseconds=1),
            evaluated_at=horizon - timedelta(microseconds=1),
            valid_until=horizon + timedelta(minutes=5),
        )
        below_result = evaluate(below)
        self.assertFalse(below_result.allowed)
        self.assertEqual(
            below_result.reasons,
            (GateReason.INDEX_PRECEDES_FINALITY_HORIZON,),
        )

        for delta_microseconds in (0, 1):
            with self.subTest(delta_microseconds=delta_microseconds):
                instant = horizon + timedelta(microseconds=delta_microseconds)
                data = set_timeline(
                    request_dict(),
                    query_end=query_end,
                    horizon=horizon,
                    index_as_of=horizon,
                    observed_at=horizon,
                    evaluated_at=instant,
                    valid_until=horizon + timedelta(minutes=5),
                )
                result = evaluate(data)
                self.assertTrue(result.allowed)
                self.assertEqual(result.reasons, ())

    def test_waiting_does_not_upgrade_an_index_captured_before_horizon(self) -> None:
        query_end = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
        horizon = query_end + timedelta(minutes=4)
        index_time = horizon - timedelta(minutes=1)
        observation_time = index_time

        before = set_timeline(
            request_dict(),
            query_end=query_end,
            horizon=horizon,
            index_as_of=index_time,
            observed_at=observation_time,
            evaluated_at=observation_time,
            valid_until=horizon + timedelta(hours=1),
        )
        after = deepcopy(before)
        after["evaluated_at"] = datetime_to_json(horizon + timedelta(minutes=1))

        for label, data in (("before", before), ("after", after)):
            with self.subTest(label=label):
                result = evaluate(data)
                self.assertFalse(result.allowed)
                self.assertIn(
                    GateReason.INDEX_PRECEDES_FINALITY_HORIZON,
                    result.reasons,
                )

    def test_entire_safe_timeline_accepts_equality_at_every_boundary(self) -> None:
        instant = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
        data = set_timeline(
            request_dict(),
            query_end=instant - timedelta(minutes=4),
            horizon=instant,
            index_as_of=instant,
            observed_at=instant,
            evaluated_at=instant,
            valid_until=instant,
        )

        result = evaluate(data)

        self.assertTrue(result.allowed)
        self.assertEqual(result.reasons, ())

    def test_offset_equivalent_horizons_normalize_to_same_query_and_digest(self) -> None:
        utc_data = request_dict()
        bind_horizon(utc_data, "2026-08-21T12:00:00Z")
        offset_data = request_dict()
        bind_horizon(offset_data, "2026-08-21T08:00:00-04:00")

        utc_request = NegativeClaimRequest.from_dict(utc_data)
        offset_request = NegativeClaimRequest.from_dict(offset_data)
        utc_result = evaluate_negative_claim(utc_request, trusted_context())
        offset_result = evaluate_negative_claim(offset_request, trusted_context())

        self.assertEqual(utc_request, offset_request)
        self.assertEqual(
            utc_request.envelope.query.source_requirements[0].to_dict()[
                "finality_horizon"
            ],
            "2026-08-21T12:00:00Z",
        )
        self.assertEqual(utc_request.envelope.query.fingerprint(), offset_request.envelope.query.fingerprint())
        self.assertEqual(utc_result.input_digest, offset_result.input_digest)

    def test_horizon_mutation_requires_rebinding_and_changes_fingerprint_and_digest(self) -> None:
        original_data = request_dict()
        original = NegativeClaimRequest.from_dict(original_data)
        original_result = evaluate_negative_claim(original, trusted_context())

        stale = deepcopy(original_data)
        source_requirement(stale)["finality_horizon"] = "2026-08-21T12:01:00Z"
        with self.assertRaisesRegex(
            ModelValidationError,
            "coverage_query_fingerprint must match",
        ):
            NegativeClaimRequest.from_dict(stale)

        rebound = deepcopy(stale)
        source_descriptor(rebound)["index_as_of"] = "2026-08-21T12:01:00Z"
        rebound["envelope"]["observed_at"] = "2026-08-21T12:01:00Z"
        refresh_query_fingerprints(rebound)
        rebound_request = NegativeClaimRequest.from_dict(rebound)
        rebound_result = evaluate_negative_claim(rebound_request, trusted_context())

        self.assertTrue(original_result.allowed)
        self.assertFalse(rebound_result.allowed)
        self.assertEqual(
            rebound_result.reasons,
            (GateReason.FINALITY_HORIZON_PROFILE_MISMATCH,),
        )
        self.assertNotEqual(
            original.envelope.query.fingerprint(),
            rebound_request.envelope.query.fingerprint(),
        )
        self.assertNotEqual(original_result.input_digest, rebound_result.input_digest)

    def test_old_policy_version_is_rejected(self) -> None:
        data = request_dict()
        data["policy"]["policy_version"] = "1.0-candidate.1"
        with self.assertRaisesRegex(ModelValidationError, "supported"):
            NegativeClaimRequest.from_dict(data)

    def test_policy_cannot_disable_required_finality(self) -> None:
        with self.assertRaisesRegex(ModelValidationError, "safety floor"):
            NegativeClaimPolicy(require_finality_horizon=False)

        data = request_dict()
        data["policy"] = policy_dict(require_finality_horizon=False)
        with self.assertRaisesRegex(ModelValidationError, "safety floor"):
            NegativeClaimRequest.from_dict(data)

    def test_reason_order_preserves_query_end_and_finality_index_failures(self) -> None:
        query_end = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
        horizon = query_end + timedelta(minutes=4)
        data = set_timeline(
            request_dict(),
            query_end=query_end,
            horizon=horizon,
            index_as_of=query_end - timedelta(microseconds=1),
            observed_at=horizon,
            evaluated_at=horizon,
            valid_until=horizon + timedelta(minutes=1),
        )

        result = evaluate(data)

        self.assertEqual(
            result.reasons,
            (
                GateReason.INDEX_PRECEDES_QUERY_END,
                GateReason.INDEX_PRECEDES_FINALITY_HORIZON,
            ),
        )

    def test_pending_window_state_cannot_hide_finality_failure(self) -> None:
        data = request_dict()
        data["envelope"]["state"] = "PENDING_WINDOW"
        bind_horizon(data, "2026-08-21T12:04:00.000001Z")

        result = evaluate(data)

        self.assertFalse(result.allowed)
        self.assertEqual(
            result.reasons,
            (
                GateReason.FINALITY_HORIZON_PROFILE_MISMATCH,
                GateReason.STATE_NOT_ABSENT_WITHIN_SCOPE,
                GateReason.INDEX_PRECEDES_FINALITY_HORIZON,
            ),
        )

    def test_programmatic_finality_horizon_round_trips_and_is_enforced(self) -> None:
        base = request()
        index_as_of = base.envelope.source_observations[0].descriptor.index_as_of
        assert index_as_of is not None
        horizon = index_as_of + timedelta(microseconds=1)
        declared = replace(
            base.envelope.query.source_requirements[0],
            finality_horizon=horizon,
        )
        query = replace(base.envelope.query, source_requirements=(declared,))
        observation = replace(
            base.envelope.source_observations[0],
            query_fingerprint=query.fingerprint(),
        )
        envelope = replace(
            base.envelope,
            query=query,
            coverage_query_fingerprint=query.fingerprint(),
            source_observations=(observation,),
        )
        candidate = replace(base, envelope=envelope)

        result = evaluate_negative_claim(candidate, trusted_context())

        self.assertFalse(result.allowed)
        self.assertEqual(
            result.reasons,
            (
                GateReason.FINALITY_HORIZON_PROFILE_MISMATCH,
                GateReason.INDEX_PRECEDES_FINALITY_HORIZON,
            ),
        )
        self.assertEqual(
            NegativeClaimRequest.from_dict(candidate.to_dict()),
            candidate,
        )

    def test_programmatic_query_rejects_horizon_before_query_end(self) -> None:
        base = request()
        declared = replace(
            base.envelope.query.source_requirements[0],
            finality_horizon=base.envelope.query.time_end
            - timedelta(microseconds=1),
        )
        with self.assertRaisesRegex(
            ModelValidationError,
            "finality_horizon must not precede query.time_end",
        ):
            replace(base.envelope.query, source_requirements=(declared,))


if __name__ == "__main__":
    unittest.main()
