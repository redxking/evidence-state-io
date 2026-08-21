# P0 Implementation Traceability

**Snapshot:** 2026-08-21
**Evidence class:** local, synthetic, self-authored
**Verified runtime:** macOS; Python 3.13.0 with pytest 8.4.2; Python 3.11 with unittest
**Candidate implementation:** `7deaea1dd79eacd2c4f3ebbef87a314e5293f1f6`

This matrix distinguishes the breadth of the PRD from the smaller behavior currently implemented and locally tested. A row marked `TESTED (PARTIAL)` means the named behavior exists for the current model, while one or more acceptance criteria remain backlog work. It does not mean the entire requirement has passed.

| Requirement | Current state | Local evidence | Remaining gap before the requirement is closed |
|---|---|---|---|
| ESIO-P0-001 Versioned evidence-state model | TESTED (PARTIAL) | `tests/test_models.py` locks all nine states. `tests/test_schema_compatibility.py` preserves the hash-bound schema `0.1` fixture/digests, proves active schema `1.0` parsing, rejects legacy/relabel/downgrade/numeric/unknown versions, and proves an actual pre-finality schema `1.0` fingerprint is diagnosed without rebinding. | No allowed-transition model; schema `1.0` remains a non-frozen candidate pending ADR-0007 profile/certificate/oracle criteria. |
| ESIO-P0-002 Declared scope and access boundary | TESTED (PARTIAL) | Query target, predicate, descriptive authorization boundary, non-secret authorization-context ID, interval, exclusions, and exactly one required source are explicit. Requirement/observation checks bind source ID, system, locator, adapter ID/version, authorization context, accessible population, and nonempty unique detection assumptions. Literal placeholder values reject across these safety-bearing declarations and the claim subject. | Credential-like identifier detection, broader semantic correctness, field/projection semantics, profile governance, and independent truth of declarations are not implemented. |
| ESIO-P0-003 Coverage and completion facts | TESTED (PARTIAL) | Coverage and the source observation must match the canonical normalized-query fingerprint, including a declared horizon. Required-source missing/status/identity/adapter/auth/population/error and missing/pre-horizon finality faults reject. Exact/estimated/unknown population, rational bounds, page/partition counts, continuation, permission limit, timeout, interruption, and query errors are tested. | Candidate supports one source only. Per-source/multi-source coverage, governed horizon profiles, blind intervals, snapshot consistency, and richer structured errors remain open. |
| ESIO-P0-004 Fail-closed envelope validation | TESTED (PARTIAL) | Existing malformed-input controls plus duplicate/undeclared sources, optional or multi-source declarations, invalid IDs/digests, empty/duplicate assumptions, and query/coverage/observation fingerprint mismatches reject with structured CLI errors. | Validation errors are stable messages, not a versioned structured reason-code contract; comprehensive credential-like-data and semantic-query limits remain incomplete. |
| ESIO-P0-005 Deterministic policy and coverage evaluator | TESTED (PARTIAL) | Parsed requests require candidate.2 policy; decisions expose candidate.2 evaluator. Exact tests cover validity/freshness and the inclusive `query.end <= horizon <= index <= observed <= evaluated <= valid` chronology. Missing/null horizons and pre-horizon indexes reject; waiting cannot repair an old index; no ambient clock is read. | Policy/evaluator are not yet bound into a complete self-describing certificate. Horizon authority, index authenticity, source clock calibration, and correction/reopen behavior are not established. |
| ESIO-P0-006 Negative-claim gate | TESTED (PARTIAL) | Absolute negatives, positive matches, every non-absence state, insufficient coverage, envelope errors, source-accounting faults, invalid time, stale observations, undeclared finality, pre-horizon indexes, and policy failures reject; the bounded single-source covered/final case permits. Reproduced identity, binding, chronology, wait-only, and downgrade permits fail closed. | The aggregate state and facts remain producer-declared; independent state derivation, authenticated adapter evidence, registry-backed profiles, and multi-source finality composition do not exist. Full P0 safety is not established. |
| ESIO-P0-007 Qualification-preserving output | TESTED (PARTIAL) | Permitted output names target, predicate, descriptive/stable authorization context, time, exclusions, required source identity/adapter/population/assumptions/horizon, reported index, evaluation time, validity, coverage, and conditional limitations. It disclaims attestation/profile governance and ingestion completeness. Subjects remain bounded, screened, and JSON-quoted. | The phrase screen is narrow rather than governed language policy; no downstream handoff-retention test exists. |
| ESIO-P0-008 Deterministic evidence certificate | IMPLEMENTED (PARTIAL) | Canonical request bytes, SHA-256 input digest, ordering invariance, one-field mutation, trusted-digest verification, and non-signature wording are tested. | No complete certificate object/digest binding evaluator version, policy version, result, evidence origin, and issued artifact. No signature or independent custody is claimed. |
| ESIO-P0-009 JSON CLI and library interface | TESTED (PARTIAL) | Existing CLI/library checks plus exact active rejection of schema `0.1`, structured exit `2`, and current schema `1.0` examples are tested in source and installed paths. | Comprehensive per-field/collection resource bounds remain incomplete; no migration command or multi-schema runtime is intended for the candidate. |
| ESIO-P0-010 Seed EmptyBench corpus and oracle | TESTED (PARTIAL) | Seven matched pairs/fourteen cases include required-source observed versus missing and a same-query/horizon/evaluation finality pair whose index differs by one microsecond; validation is unavoidable in CLI/library paths; controls/faults oppose and exact reason sets are scored. | Corpus lacks identity/adapter/auth and other P0 families, permits one-or-more changed sufficiency facts in older pairs, is not frozen, and keeps expected outcomes beside implementation-owned fixtures rather than a separately governed oracle. |
| ESIO-P0-011 Reproducibility and security baseline | TESTED (PARTIAL) | The current 244-test schema `1.0` candidate passed from source and the installed package on Python 3.13 and against checked-out source via unittest on Python 3.11. Source/installed package snapshots matched. The Python 3.11 source and Python 3.13 installed seed outputs passed 14/14 and matched byte-for-byte; the operator demo passed 2/2. `scripts/check.sh` verifies package-file and deterministic-demo parity, local links, shell syntax, and Compose configuration. `scripts/setup.sh` verifies project/module/distribution version equality. The 171-test schema `0.1` baseline remains separately hash-bound at `b6fac87`. | GitHub Actions was not executed; containers were not started; broad fuzzing, comprehensive semantic bounds, dependency review, an independent oracle/frozen campaign, and external security review remain open. The `1.0` candidate is not frozen, and a local commit is not independent custody. |

## Verification commands

All of the following exited `0` in the repository-local environment:

```bash
env -u PYTHONPATH ./scripts/check.sh
env -u PYTHONPATH ./scripts/test.sh
env -u PYTHONPATH ./scripts/demo.sh --pretty
env -u PYTHONPATH ./.venv/bin/python -m pytest -q
PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -q
env -u PYTHONPATH ./.venv/bin/evidence-state evaluate --input examples/covered_request.json --pretty
env -u PYTHONPATH ./.venv/bin/evidence-state evaluate --input examples/partial_request.json --pretty
git diff --check
```

Observed results:

- `244 passed` in the full Python 3.13 source and installed-package test suites.
- `244 tests, OK` against checked-out source under Python 3.11 unittest discovery.
- Source and installed package-file snapshots matched. The Python 3.11 source and Python 3.13 installed seed output was byte-identical.
- Covered synthetic request: `PERMIT_SCOPED_NEGATIVE`.
- Matched partial synthetic request: `REJECT_NEGATIVE` with incomplete-coverage reasons.
- Built-in seed: 14/14; operator demo: 2/2; custom example: 2/2 and labeled `EmptyBench-custom`.
- Project, module, and installed-distribution versions matched at `0.3.0`.
- Optional Compose configuration validated without starting containers.

The 79-, 114-, 168-, and 169-test schema `0.1` proposals and the 215-test schema `1.0` proposal, plus stale installed-command, package-metadata, wait-only finality, and unconditional-null compatibility states, were rejected during review. Remediation and installed-command retesting are preserved in `docs/REVIEW_LOG.md`. The 171-test snapshot is the first accepted local schema `0.1` and canonicalization-profile `0.1` freeze at `b6fac87`; the current 244-test schema `1.0` source-accounting/finality state is a locally tested candidate, not a schema or benchmark freeze.

These results establish local behavior in the recorded environment only. The review was independent of implementation within the project team but was still internal and read-only. These results are not a frozen benchmark campaign, independent external reproduction, operational evaluation, external security assessment, or production-readiness determination.
