from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import unittest

from evidence_state_io import (
    CANONICALIZATION_PROFILE,
    ModelValidationError,
    NegativeClaimRequest,
    canonical_digest,
)
from evidence_state_io.cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = PROJECT_ROOT / "examples"
LEGACY = EXAMPLES / "legacy"
LEGACY_FIXTURE = LEGACY / "schema-0.1-covered-request.json"
LEGACY_BASELINE = LEGACY / "schema-0.1-baseline.json"
ACTIVE_FIXTURE = EXAMPLES / "covered_request.json"

FROZEN_COMMIT = "b6fac8706fc3496ceb46003c0d5b836a3dc23096"
FROZEN_PROFILE = "esio-canonical-json-0.1"
FROZEN_RAW_DIGEST = (
    "sha256:c265c5f2c1b5054cb3a37a88ae833ac781daa196edef04d8074a13dd0864a189"
)
FROZEN_INPUT_DIGEST = (
    "sha256:da688bad283bb84fd88ef6bfba35893f61266d61cf01f07ac9bf852b0255b554"
)

# Schema 0.1 materialized these policy defaults before calculating a decision's
# input digest.  This constant is replay evidence, not an active migration path.
FROZEN_POLICY_DEFAULTS = {
    "coverage": {
        "minimum_lower_bound": 1.0,
        "require_exact_population": False,
        "require_complete_pagination": True,
        "require_complete_partitions": True,
        "reject_timeout": True,
        "reject_interruption": True,
        "reject_query_errors": True,
        "allow_permission_limited_scope": True,
    },
    "require_valid_until": True,
    "max_observation_age_seconds": None,
    "require_index_as_of": False,
    "max_index_age_seconds": None,
    "reject_envelope_errors": True,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class SchemaCompatibilityTests(unittest.TestCase):
    def test_frozen_raw_fixture_and_materialized_input_digests_are_stable(self) -> None:
        raw = load_json(LEGACY_FIXTURE)
        self.assertEqual(canonical_digest(raw), FROZEN_RAW_DIGEST)

        materialized = deepcopy(raw)
        materialized["policy"] = deepcopy(FROZEN_POLICY_DEFAULTS)
        self.assertEqual(canonical_digest(materialized), FROZEN_INPUT_DIGEST)

    def test_baseline_metadata_is_self_consistent_and_explicitly_historical(self) -> None:
        raw = load_json(LEGACY_FIXTURE)
        baseline = load_json(LEGACY_BASELINE)

        self.assertEqual(baseline["artifact_type"], "historical-local-replay-baseline")
        self.assertEqual(baseline["status"], "HISTORICAL_LOCAL_REPLAY_ONLY")
        self.assertEqual(baseline["schema_version"], raw["envelope"]["schema_version"])
        self.assertEqual(baseline["fixture"], LEGACY_FIXTURE.name)
        self.assertEqual(baseline["frozen_implementation"]["commit"], FROZEN_COMMIT)
        self.assertEqual(
            baseline["frozen_implementation"]["source_path"],
            "examples/covered_request.json",
        )
        self.assertEqual(baseline["canonicalization_profile"], FROZEN_PROFILE)
        self.assertEqual(baseline["raw_fixture_digest"], canonical_digest(raw))
        self.assertEqual(
            baseline["expected_decision"],
            {
                "allowed": True,
                "decision": "PERMIT_SCOPED_NEGATIVE",
                "reasons": [],
                "input_digest": FROZEN_INPUT_DIGEST,
            },
        )
        limitations = " ".join(baseline["limitations"]).lower()
        for required_boundary in (
            "historical local replay",
            "not a current permit",
            "certificate",
            "pinned commit",
            "not a migration",
        ):
            self.assertIn(required_boundary, limitations)

    def test_active_parser_rejects_schema_0_1_exactly_and_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            ModelValidationError,
            r"^envelope\.schema_version must be the supported string value '1\.0'$",
        ):
            NegativeClaimRequest.from_dict(load_json(LEGACY_FIXTURE))

    def test_cli_rejects_schema_0_1_with_structured_exit_2(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        code = main(
            ["evaluate", "--input", str(LEGACY_FIXTURE)],
            stdin=StringIO(),
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        payload = json.loads(stderr.getvalue())
        self.assertEqual(payload["error"]["type"], "ModelValidationError")
        self.assertEqual(
            payload["error"]["message"],
            "envelope.schema_version must be the supported string value '1.0'",
        )

    def test_relabeling_schema_0_1_as_1_0_is_not_a_migration(self) -> None:
        relabeled = load_json(LEGACY_FIXTURE)
        relabeled["envelope"]["schema_version"] = "1.0"
        with self.assertRaisesRegex(
            ModelValidationError,
            r"^envelope has unknown fields: source$",
        ):
            NegativeClaimRequest.from_dict(relabeled)

    def test_downgrading_schema_1_0_label_is_rejected_without_conversion(self) -> None:
        downgraded = load_json(ACTIVE_FIXTURE)
        downgraded["envelope"]["schema_version"] = "0.1"
        with self.assertRaisesRegex(
            ModelValidationError,
            r"^envelope\.schema_version must be the supported string value '1\.0'$",
        ):
            NegativeClaimRequest.from_dict(downgraded)

    def test_active_schema_1_0_fixture_parses_under_current_contract(self) -> None:
        request = NegativeClaimRequest.from_dict(load_json(ACTIVE_FIXTURE))
        self.assertEqual(request.envelope.schema_version, "1.0")
        self.assertEqual(CANONICALIZATION_PROFILE, FROZEN_PROFILE)


if __name__ == "__main__":
    unittest.main()
