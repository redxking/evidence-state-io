from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Iterator

from evidence_state_io import ModelValidationError, NegativeClaimRequest
from evidence_state_io.certificates import EvidenceCertificate
from evidence_state_io.emptybench import SEED_ORACLE_DIGEST, parse_corpus, parse_oracle
from evidence_state_io.profiles import ProfileRegistrySnapshot, ProfileTrustSelection

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def paths(value: Any, prefix: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    yield prefix
    if type(value) is dict:
        for key, child in value.items():
            yield from paths(child, (*prefix, key))
    elif type(value) is list:
        for index, child in enumerate(value):
            yield from paths(child, (*prefix, index))


def at(value: Any, path: tuple[Any, ...]) -> Any:
    current = value
    for part in path:
        current = current[part]
    return current


def replace(value: Any, path: tuple[Any, ...], replacement: Any) -> Any:
    if not path:
        return deepcopy(replacement)
    result = deepcopy(value)
    parent = at(result, path[:-1])
    parent[path[-1]] = deepcopy(replacement)
    return result


def delete(value: Any, path: tuple[Any, ...]) -> Any:
    result = deepcopy(value)
    parent = at(result, path[:-1])
    del parent[path[-1]]
    return result


def wrong_types(value: Any) -> tuple[Any, ...]:
    candidates = (None, True, 0, 1.5, "", [], {})
    return tuple(candidate for candidate in candidates if type(candidate) is not type(value))


def mutations(value: Any) -> Iterator[Any]:
    for path in paths(value):
        original = at(value, path) if path else value
        for replacement in wrong_types(original):
            yield replace(value, path, replacement)
        if path:
            yield delete(value, path)


class ContractMutationMatrixTests(unittest.TestCase):
    def exercise(
        self,
        payload: dict[str, Any],
        parser: Callable[[Any], Any],
        serializer: Callable[[Any], dict[str, Any]],
    ) -> None:
        rejected = 0
        accepted = 0
        for candidate in mutations(payload):
            try:
                parsed = parser(candidate)
            except ModelValidationError:
                rejected += 1
                continue
            accepted += 1
            reparsed = parser(serializer(parsed))
            self.assertEqual(serializer(parsed), serializer(reparsed))
        self.assertGreater(rejected, accepted)
        self.assertGreater(rejected, 100)

    def test_request_contract_mutation_matrix(self) -> None:
        self.exercise(
            load("examples/covered_request.json"),
            NegativeClaimRequest.from_dict,
            NegativeClaimRequest.to_dict,
        )

    def test_registry_contract_mutation_matrix(self) -> None:
        self.exercise(
            load("examples/profile_registry.json"),
            ProfileRegistrySnapshot.from_dict,
            ProfileRegistrySnapshot.to_dict,
        )

    def test_trust_contract_mutation_matrix(self) -> None:
        self.exercise(
            load("examples/profile_trust.json"),
            ProfileTrustSelection.from_dict,
            ProfileTrustSelection.to_dict,
        )

    def test_certificate_contract_mutation_matrix(self) -> None:
        self.exercise(
            load("examples/covered_certificate.json"),
            EvidenceCertificate.from_dict,
            EvidenceCertificate.to_dict,
        )

    def test_emptybench_corpus_contract_mutation_matrix(self) -> None:
        self.exercise(
            load("src/evidence_state_io/benchmarks/emptybench-p0-corpus.json"),
            parse_corpus,
            lambda corpus: corpus.to_dict(),
        )

    def test_emptybench_oracle_contract_mutation_matrix(self) -> None:
        corpus = parse_corpus(load("src/evidence_state_io/benchmarks/emptybench-p0-corpus.json"))

        def parser(value: Any) -> Any:
            return parse_oracle(value, corpus, expected_digest=SEED_ORACLE_DIGEST)

        self.exercise(
            load("src/evidence_state_io/benchmarks/emptybench-p0-oracle.json"),
            parser,
            lambda oracle: oracle.to_dict(),
        )


if __name__ == "__main__":
    unittest.main()
