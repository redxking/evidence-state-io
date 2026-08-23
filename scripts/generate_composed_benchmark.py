#!/usr/bin/env python3
"""Generate the packaged composed EmptyBench corpus and oracle.

The expected outcome of every case is written here by hand. The generator then
runs the gate and refuses to write anything if the gate disagrees. An oracle
derived from whatever the implementation happens to do would agree with the
implementation by construction and would measure nothing; this one is a claim
about what the gate *should* do, and generation fails when it does not.

Deterministic: no clock, no network, no randomness. Re-running it on an
unchanged tree reproduces the artifacts byte for byte, which
`test_composed_benchmark.py` asserts.

Usage:
    PYTHONPATH=src python3 scripts/generate_composed_benchmark.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from evidence_state_io.canonical import (  # noqa: E402
    CANONICALIZATION_PROFILE,
    DIGEST_ALGORITHM,
    canonical_digest,
)
from evidence_state_io.emptybench import (  # noqa: E402
    COMPOSED_BENCHMARK_ID,
    COMPOSED_BENCHMARK_VERSION,
    COMPOSED_MIRROR_SOURCE_ID,
    EMPTYBENCH_CORPUS_SCHEMA,
    EMPTYBENCH_ORACLE_SCHEMA,
    composed_profile_context,
    seed_case_dicts,
)
from evidence_state_io.gate import NegativeClaimRequest, evaluate_negative_claim  # noqa: E402
from evidence_state_io.models import QueryScope  # noqa: E402

BENCHMARK_DIR = REPO_ROOT / "src" / "evidence_state_io" / "benchmarks"
CORPUS_PATH = BENCHMARK_DIR / "emptybench-p1-composed-corpus.json"
ORACLE_PATH = BENCHMARK_DIR / "emptybench-p1-composed-oracle.json"

PRIMARY_SOURCE_ID = "github-public-repositories"
PRIMARY_HORIZON = "2026-08-21T12:04:00Z"
MIRROR_HORIZON = "2026-08-21T12:05:00Z"
#: A read taken shortly before a late-sealed envelope, used by the freshness
#: pair so that control and fault differ only in when one source looked.
FRESH_READ = "2026-08-21T12:49:00Z"


def _composed_base_request() -> dict[str, Any]:
    """Build the composed control request: two sources that corroborate a permit."""

    data = deepcopy(seed_case_dicts()[0]["request"])
    envelope = data["envelope"]
    envelope["schema_version"] = "1.1"
    envelope["query"]["composition"] = "CORROBORATION"

    primary_requirement = envelope["query"]["source_requirements"][0]
    primary_observation = envelope["source_observations"][0]
    primary_observation["coverage"] = deepcopy(envelope["coverage"])
    primary_observation["state"] = "ABSENT_WITHIN_SCOPE"
    primary_observation["matched_count"] = 0
    primary_observation["observed_at"] = PRIMARY_HORIZON
    primary_observation["valid_until"] = envelope["valid_until"]

    context = composed_profile_context()
    mirror_profile = next(
        record.profile
        for record in context.snapshot.records
        if record.profile.source.source_id == COMPOSED_MIRROR_SOURCE_ID
    )

    mirror_requirement = deepcopy(primary_requirement)
    mirror_requirement["source_id"] = COMPOSED_MIRROR_SOURCE_ID
    mirror_requirement["system"] = mirror_profile.source.system
    mirror_requirement["adapter_id"] = mirror_profile.source.adapter_id
    mirror_requirement["finality_horizon"] = MIRROR_HORIZON
    mirror_requirement["profile_ref"] = {
        "registry_id": context.snapshot.registry_id,
        "profile_id": mirror_profile.profile_id,
        "profile_version": mirror_profile.profile_version,
        "profile_digest": mirror_profile.profile_digest,
    }
    envelope["query"]["source_requirements"].append(mirror_requirement)

    mirror_observation = deepcopy(primary_observation)
    mirror_observation["source_id"] = COMPOSED_MIRROR_SOURCE_ID
    mirror_observation["descriptor"]["system"] = mirror_profile.source.system
    mirror_observation["descriptor"]["adapter_id"] = mirror_profile.source.adapter_id
    mirror_observation["descriptor"]["index_as_of"] = MIRROR_HORIZON
    mirror_observation["observed_at"] = MIRROR_HORIZON
    envelope["source_observations"].append(mirror_observation)

    envelope["observed_at"] = MIRROR_HORIZON
    data["evaluated_at"] = "2026-08-21T12:06:00Z"

    fingerprint = QueryScope.from_dict(envelope["query"]).fingerprint()
    envelope["coverage_query_fingerprint"] = fingerprint
    for observation in envelope["source_observations"]:
        observation["query_fingerprint"] = fingerprint
    return data


# Index of the mirror source inside the canonically sorted collections.  The
# model sorts both by source_id, and "github-..." sorts before "mirror-...".
MIRROR = 1

# (pair_id, fault_class, description, control mutations, fault description,
#  fault mutations, expected reasons)
_PAIRS: tuple[tuple[str, str, str, list, str, list, tuple[str, ...]], ...] = (
    (
        "dissent",
        "COMPOSITION_DISSENT",
        "Both required sources independently report in-scope absence.",
        [],
        "One required source reports an in-scope match while the other reports absence.",
        [
            {"pointer": f"/envelope/source_observations/{MIRROR}/state", "value": "PRESENT"},
            {"pointer": f"/envelope/source_observations/{MIRROR}/matched_count", "value": 1},
        ],
        (
            "COMPOSED_SOURCE_NOT_ABSENT_WITHIN_SCOPE",
            "COMPOSED_SOURCE_REPORTS_MATCHES",
            "COMPOSED_SOURCE_STATES_DISAGREE",
        ),
    ),
    (
        "source-coverage",
        "COMPOSITION_COVERAGE",
        "Every required source independently reaches the governed coverage floor.",
        [],
        "One required source enumerated only part of the declared population.",
        [
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/coverage/examined_units",
                "value": 60,
            },
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/coverage/pages_examined",
                "value": 3,
            },
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/coverage/pagination_complete",
                "value": False,
            },
        ],
        ("COMPOSED_SOURCE_COVERAGE_NOT_MET",),
    ),
    (
        "composed-floor",
        "COMPOSITION_FLOOR",
        "The composed floor equals the coverage each source independently reached.",
        [],
        "Two sources each covering 60% do not compose to the 100% the envelope declares.",
        [
            {"pointer": "/envelope/source_observations/0/coverage/examined_units", "value": 60},
            {"pointer": "/envelope/source_observations/0/coverage/pages_examined", "value": 3},
            {
                "pointer": "/envelope/source_observations/0/coverage/pagination_complete",
                "value": False,
            },
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/coverage/examined_units",
                "value": 60,
            },
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/coverage/pages_examined",
                "value": 3,
            },
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/coverage/pagination_complete",
                "value": False,
            },
        ],
        ("COMPOSED_COVERAGE_OVERSTATED", "COMPOSED_SOURCE_COVERAGE_NOT_MET"),
    ),
    (
        "own-horizon",
        "COMPOSITION_FINALITY",
        "Every required source reached its own profile-derived finality horizon.",
        [],
        "One source reached the earliest horizon in the set but not its own later one.",
        [
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/descriptor/index_as_of",
                "value": PRIMARY_HORIZON,
            },
        ],
        (
            "COMPOSED_SOURCE_INDEX_PRECEDES_OWN_HORIZON",
            "INDEX_PRECEDES_FINALITY_HORIZON",
        ),
    ),
    (
        # The sharpest form of the rule: the envelope, the evaluation time, and
        # the visible result are identical across the pair.  The only
        # difference is when one source actually looked.
        "stalest-observation",
        "COMPOSITION_FRESHNESS",
        "Both sources were read shortly before the envelope was sealed.",
        [
            {"pointer": "/policy/max_observation_age_seconds", "value": 2400},
            {"pointer": "/envelope/observed_at", "value": "2026-08-21T12:50:00Z"},
            {"pointer": "/evaluated_at", "value": "2026-08-21T12:51:00Z"},
            {"pointer": "/envelope/source_observations/0/observed_at", "value": FRESH_READ},
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/observed_at",
                "value": FRESH_READ,
            },
        ],
        "A late-sealed envelope looks fresh while one source was read long before it.",
        [
            {"pointer": "/policy/max_observation_age_seconds", "value": 2400},
            {"pointer": "/envelope/observed_at", "value": "2026-08-21T12:50:00Z"},
            {"pointer": "/evaluated_at", "value": "2026-08-21T12:51:00Z"},
            {"pointer": "/envelope/source_observations/0/observed_at", "value": FRESH_READ},
        ],
        ("OBSERVATION_TOO_OLD",),
    ),
    (
        "earliest-validity",
        "COMPOSITION_VALIDITY",
        "The envelope does not outlive any contributing source's declared boundary.",
        [],
        "The envelope claims validity past the earliest boundary a source declared.",
        [
            {
                "pointer": f"/envelope/source_observations/{MIRROR}/valid_until",
                "value": "2026-08-21T12:30:00Z",
            },
        ],
        ("COMPOSED_VALIDITY_OVERSTATED",),
    ),
)


def _apply(request: dict[str, Any], mutations: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply JSON-pointer mutations the way the benchmark runner does."""

    data = deepcopy(request)
    for mutation in mutations:
        target: Any = data
        tokens = mutation["pointer"].split("/")[1:]
        for token in tokens[:-1]:
            key = token.replace("~1", "/").replace("~0", "~")
            target = target[int(key)] if isinstance(target, list) else target[key]
        last = tokens[-1].replace("~1", "/").replace("~0", "~")
        if isinstance(target, list):
            target[int(last)] = mutation["value"]
        else:
            target[last] = mutation["value"]
    return data


def _actual_reasons(request: dict[str, Any], mutations: list[dict[str, Any]]) -> tuple[str, ...]:
    mutated = _apply(request, mutations)
    decision = evaluate_negative_claim(
        NegativeClaimRequest.from_dict(mutated),
        composed_profile_context(),
    )
    return tuple(reason.value for reason in decision.reasons)


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    base = _composed_base_request()

    cases: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    failures: list[str] = []

    for (
        pair_id,
        fault_class,
        control_text,
        control_mutations,
        fault_text,
        mutations,
        expected,
    ) in _PAIRS:
        control_id = f"{pair_id}-corroborated"
        fault_id = f"{pair_id}-fault"

        control_reasons = _actual_reasons(base, control_mutations)
        if control_reasons:
            failures.append(
                f"{control_id}: expected a permit, gate rejected for {', '.join(control_reasons)}"
            )
        fault_reasons = _actual_reasons(base, mutations)
        if set(fault_reasons) != set(expected):
            failures.append(
                f"{fault_id}: expected reasons {sorted(expected)}, gate gave {sorted(fault_reasons)}"
            )

        cases.append(
            {
                "case_id": control_id,
                "pair_id": pair_id,
                "fault_class": fault_class,
                "variant": "control",
                "description": control_text,
                "mutations": control_mutations,
            }
        )
        cases.append(
            {
                "case_id": fault_id,
                "pair_id": pair_id,
                "fault_class": fault_class,
                "variant": "fault",
                "description": fault_text,
                "mutations": mutations,
            }
        )
        # The hand-written expectation above is the claim: exactly these
        # reasons and no others.  The oracle records them in the gate's own
        # deterministic emission order, which is a stronger assertion than the
        # set: a reordering becomes a visible benchmark failure rather than an
        # invisible change.
        rules.append(
            {
                "rule_id": f"REJECT_{pair_id.upper().replace('-', '_')}",
                "expected_allowed": False,
                "expected_reasons": list(fault_reasons),
            }
        )
        assignments.append({"case_id": control_id, "rule_id": "PERMIT_COMPOSED_CONTROL"})
        assignments.append(
            {"case_id": fault_id, "rule_id": f"REJECT_{pair_id.upper().replace('-', '_')}"}
        )

    if failures:
        raise SystemExit(
            "the gate disagrees with the hand-written oracle; refusing to write "
            "artifacts:\n  " + "\n  ".join(failures)
        )

    rules.insert(
        0, {"rule_id": "PERMIT_COMPOSED_CONTROL", "expected_allowed": True, "expected_reasons": []}
    )

    corpus: dict[str, Any] = {
        "corpus_schema": EMPTYBENCH_CORPUS_SCHEMA,
        "benchmark_id": COMPOSED_BENCHMARK_ID,
        "benchmark_version": COMPOSED_BENCHMARK_VERSION,
        "canonicalization_profile": CANONICALIZATION_PROFILE,
        "digest_algorithm": DIGEST_ALGORITHM,
        "base_request": base,
        "cases": cases,
    }
    corpus["corpus_digest"] = canonical_digest(
        {key: value for key, value in corpus.items() if key != "corpus_digest"}
    )

    oracle: dict[str, Any] = {
        "oracle_schema": EMPTYBENCH_ORACLE_SCHEMA,
        "corpus_schema": EMPTYBENCH_CORPUS_SCHEMA,
        "oracle_id": f"{COMPOSED_BENCHMARK_ID}-oracle",
        "oracle_version": COMPOSED_BENCHMARK_VERSION,
        "benchmark_id": COMPOSED_BENCHMARK_ID,
        "benchmark_version": COMPOSED_BENCHMARK_VERSION,
        "canonicalization_profile": CANONICALIZATION_PROFILE,
        "digest_algorithm": DIGEST_ALGORITHM,
        "corpus_digest": corpus["corpus_digest"],
        "rules": rules,
        "assignments": assignments,
    }
    oracle["oracle_digest"] = canonical_digest(
        {key: value for key, value in oracle.items() if key != "oracle_digest"}
    )
    return corpus, oracle


def _serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the packaged artifacts differ",
    )
    args = parser.parse_args()

    corpus, oracle = build()
    written = {CORPUS_PATH: _serialize(corpus), ORACLE_PATH: _serialize(oracle)}

    if args.check:
        for path, content in written.items():
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"{path.name} differs from the generator output", file=sys.stderr)
                return 1
        print("packaged composed benchmark artifacts match the generator")
        return 0

    for path, content in written.items():
        path.write_text(content, encoding="utf-8")
    print(f"corpus_digest: {corpus['corpus_digest']}")
    print(f"oracle_digest: {oracle['oracle_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
