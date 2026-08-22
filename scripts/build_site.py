from __future__ import annotations

import argparse
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from evidence_state_io import NegativeClaimRequest, canonical_digest, evaluate_negative_claim
from evidence_state_io.profiles import (
    ProfileRegistrySnapshot,
    ProfileTrustSelection,
    TrustedProfileContext,
)

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
EXAMPLES = ROOT / "examples"


def load(name: str) -> dict[str, Any]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def expected(request_data: dict[str, Any], context: TrustedProfileContext) -> dict[str, Any]:
    request = NegativeClaimRequest.from_dict(request_data)
    decision = evaluate_negative_claim(request, context)
    return {
        "disposition": decision.decision,
        "evidence_state": request.envelope.state.value,
        "input_digest": canonical_digest(request.to_dict()),
        "reasons": [reason.value for reason in decision.reasons],
    }


def scenario_data() -> dict[str, Any]:
    context = TrustedProfileContext(
        snapshot=ProfileRegistrySnapshot.from_dict(load("profile_registry.json")),
        trust_selection=ProfileTrustSelection.from_dict(load("profile_trust.json")),
    )
    covered = load("covered_request.json")
    partial = load("partial_request.json")
    stale = deepcopy(covered)
    stale["envelope"]["valid_until"] = "2026-08-21T12:04:59Z"
    ambiguous = deepcopy(covered)
    ambiguous["envelope"]["state"] = "NOT_OBSERVED"
    conflicting = deepcopy(covered)
    conflicting["envelope"]["state"] = "CONTRADICTORY"
    conflicting["envelope"]["source_observations"][0]["status"] = "CONTRADICTORY"
    tampered = deepcopy(covered)
    tampered["subject"] = "tampered subject outside retained input custody"
    invalid = deepcopy(covered)
    invalid["envelope"]["schema_version"] = "latest"

    scenarios: list[dict[str, Any]] = []
    for identifier, label, description, data in (
        (
            "valid",
            "Valid bounded absence",
            "Complete synthetic evidence permits only the scoped negative.",
            covered,
        ),
        (
            "incomplete",
            "Incomplete pagination",
            "The same empty result fails closed when coverage is partial.",
            partial,
        ),
        (
            "stale",
            "Expired evidence",
            "Evidence at its exclusive validity boundary rejects.",
            stale,
        ),
        (
            "ambiguous",
            "Not observed",
            "An ambiguous evidence state cannot become absence.",
            ambiguous,
        ),
        (
            "conflicting",
            "Contradictory source",
            "A contradictory required source rejects the negative.",
            conflicting,
        ),
    ):
        observed = expected(data, context)
        scenarios.append(
            {
                "description": description,
                "expected": observed,
                "expected_input_digest": observed["input_digest"],
                "id": identifier,
                "input": json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                "label": label,
            }
        )

    covered_digest = expected(covered, context)["input_digest"]
    scenarios.extend(
        [
            {
                "description": "The content is structurally valid but no longer matches the retained input digest.",
                "expected": {
                    "disposition": "REJECT_UNVERIFIED_INPUT",
                    "evidence_state": "ABSENT_WITHIN_SCOPE",
                    "reasons": ["EXPECTED_INPUT_DIGEST_MISMATCH"],
                },
                "expected_input_digest": covered_digest,
                "id": "tampered",
                "input": json.dumps(tampered, indent=2, ensure_ascii=False) + "\n",
                "label": "Tampered after custody",
            },
            {
                "description": "An unsupported schema never reaches the deterministic gate.",
                "expected": {
                    "disposition": "REJECT_INVALID_INPUT",
                    "evidence_state": "INVALID",
                    "reasons": ["MODEL_INVALID"],
                },
                "expected_input_digest": None,
                "id": "invalid",
                "input": json.dumps(invalid, indent=2, ensure_ascii=False) + "\n",
                "label": "Unsupported schema",
            },
        ]
    )
    return {
        "generated_from": {
            "canonicalization_profile": "esio-canonical-json-0.1",
            "evaluator": "esio-evaluator-1.0-candidate.5",
            "policy": "esio-p0-safety-floor/1.0-candidate.4",
            "schema": "1.0",
        },
        "scenario_schema": "esio-browser-demo-scenarios/1.0",
        "scenarios": scenarios,
    }


def build(output: Path) -> None:
    output = output.resolve()
    if (
        output == SITE.resolve()
        or ROOT.resolve() in output.parents
        and output.name != ".site-build"
    ):
        raise SystemExit("refusing an unsafe site output path")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SITE, output)
    (output / "demo-fixtures.json").write_text(
        json.dumps(scenario_data(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / ".site-build")
    arguments = parser.parse_args()
    build(arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
