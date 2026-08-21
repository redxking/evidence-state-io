# P0 Implementation Traceability

**Snapshot:** 2026-08-21
**Evidence class:** local, synthetic, self-authored
**Verified runtime:** macOS; Python 3.13.0 with pytest 8.4.2; Python 3.11 with unittest

This matrix distinguishes the breadth of the PRD from the smaller behavior currently implemented and locally tested. A row marked `TESTED (PARTIAL)` means the named behavior exists for the current model, while one or more acceptance criteria remain backlog work. It does not mean the entire requirement has passed.

| Requirement | Current state | Local evidence | Remaining gap before the requirement is closed |
|---|---|---|---|
| ESIO-P0-001 Versioned evidence-state model | TESTED | `tests/test_models.py` locks all nine states, round trips them, and rejects omitted, numeric, or unsupported schema versions. | No allowed-transition model or compatibility suite beyond schema `0.1`. |
| ESIO-P0-002 Declared scope and access boundary | TESTED (PARTIAL) | Query target, predicate, authorization boundary, start/end interval, and exclusions are explicit strict fields; `time_end <= observed_at <= evaluated_at` is enforced. | Required/observed source identifiers, accessible-population structure, field/projection semantics, detection assumptions, and credential-like identifier rejection are not implemented. |
| ESIO-P0-003 Coverage and completion facts | TESTED (PARTIAL) | Safety-relevant booleans and error arrays are mandatory. Exact/estimated/unknown population handling, rational lower bounds, paired page/partition counts, continuation, permission limit, timeout, interruption, and query errors are tested. Estimated/unknown populations require an explicit lower-bound attestation, and exact integer arithmetic prevents rounding a one-unit coverage deficit into completion. | Multi-source coverage, required-source status, blind intervals, explicit finality, snapshot consistency, and richer structured errors are not implemented. |
| ESIO-P0-004 Fail-closed envelope validation | TESTED (PARTIAL) | Omitted facts, null error arrays, unknown fields, state/count conflicts, incoherent intervals, population contradictions, continuation/completion conflicts, overstated bounds, control-line strings, duplicate JSON keys, non-standard constants, oversized/deep input, excessive numeric tokens/integers, invalid UTF-8, invalid or ambiguous RFC3339 timestamps, unrepresentable UTC conversions, and source-index dates after observation are rejected with structured CLI errors. | Validation errors are stable messages, not a versioned structured reason-code contract; comprehensive per-field, collection, credential-like-data, and semantic-query limits remain incomplete. |
| ESIO-P0-005 Deterministic policy and coverage evaluator | TESTED (PARTIAL) | Explicit evaluation time, freshness/validity boundaries, exact microsecond age comparisons, UTC-normalized timestamps, index chronology, exact rational thresholds, context-independent decimal parsing, non-relaxable P0 safety floors, canonical ordering, and deterministic replay tests pass. | Policy version is not a first-class certificate-bound identifier; `index_as_of` is currentness metadata rather than a completeness watermark, so finality-horizon derivation and multi-source composition remain open. |
| ESIO-P0-006 Negative-claim gate | TESTED (PARTIAL) | Absolute negatives, positive matches, every non-absence state, partial/unknown coverage, errors, invalid time, staleness, and policy failures reject; the covered scoped case permits. The original unsafe-permit probes now fail closed. | Current result still depends on producer-declared evidence facts; required-source accounting, independent adapter evidence, and registry-backed policy do not exist. Full P0 safety is therefore not established. |
| ESIO-P0-007 Qualification-preserving output | TESTED (PARTIAL) | Permitted output names target, predicate, authorization boundary, time, exclusions, evaluation time, validity, coverage, and conditional limitations. Subjects are bounded single-line data, screened for absolute formulations, JSON-quoted, and covered by injection tests. | The phrase screen is narrow rather than a governed configurable language policy; no downstream handoff-retention test exists. |
| ESIO-P0-008 Deterministic evidence certificate | IMPLEMENTED (PARTIAL) | Canonical request bytes, SHA-256 input digest, ordering invariance, one-field mutation, trusted-digest verification, and non-signature wording are tested. | No complete certificate object/digest binding evaluator version, policy version, result, evidence origin, and issued artifact. No signature or independent custody is claimed. |
| ESIO-P0-009 JSON CLI and library interface | TESTED (PARTIAL) | `evaluate`, `demo`, `emptybench`, and `coverage` commands; stdin/file input; explicit time; 1 MiB ceiling; duplicate/non-finite/depth/numeric-token/UTF-8 rejection; conflicting override rejection; atomic ASCII-safe JSON output; explicit preservation of caller-supplied empty values for validation; immutable normalized sequences; structured errors; and module/console entry points are tested in source and installed paths. | Comprehensive per-field/collection resource bounds are not implemented. Exit-code and schema compatibility beyond the first local `0.1` freeze require governed evolution before external use. |
| ESIO-P0-010 Seed EmptyBench corpus and oracle | TESTED (PARTIAL) | Five matched pairs/ten cases exist; validation is unavoidable in CLI and library execution, including generators; visible questions must match, controls/faults must oppose, exact reason sets are scored, and custom corpora cannot claim seed provenance. | The corpus does not cover every P0 fault class, enforces one-or-more rather than exactly one changed sufficiency fact, has not been frozen, and does not yet use a separately governed independent oracle or model baselines. |
| ESIO-P0-011 Reproducibility and security baseline | TESTED (PARTIAL) | The 171-test suite passed from source and the installed package on Python 3.13 and via unittest on Python 3.11. The final independent replay passed the 98/98 core CLI exploit set across source/installed paths, 30/30 EmptyBench adversarial executions, 38/38 direct-library checks, and 6/6 source-index chronology probes. `scripts/check.sh` verifies package-file and deterministic-demo parity, local links, shell syntax, and Compose configuration. The initial local commit binds the first accepted snapshot. | GitHub Actions was not executed; containers were not started; broad fuzzing, comprehensive semantic bounds, dependency review, an independent oracle/frozen campaign, and external security review remain open. A local commit is not independent custody. |

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

- `171 passed` in the full Python 3.13 source and installed-package test suites.
- `171 tests, OK` under Python 3.11 unittest discovery.
- Final independent replay passed the 98/98 core CLI exploit set across source and installed paths, 30/30 EmptyBench adversarial executions, 38/38 direct-library checks, and 6/6 source-index chronology probes.
- Covered synthetic request: `PERMIT_SCOPED_NEGATIVE`.
- Matched partial synthetic request: `REJECT_NEGATIVE` with incomplete-coverage reasons.
- Built-in seed: 10/10; operator demo: 2/2; custom example: 2/2 and labeled `EmptyBench-custom`.
- Optional Compose configuration validated without starting containers.

The 79-, 114-, 168-, and 169-test proposed baselines, plus a stale installed-command state, were rejected during review. Remediation and installed-command retesting are preserved in `docs/REVIEW_LOG.md`. The 171-test snapshot is the first accepted local schema `0.1` and canonicalization-profile `0.1` freeze; no earlier candidate was released or certificate-bearing.

These results establish local behavior in the recorded environment only. The review was independent of implementation within the project team but was still internal and read-only. These results are not a frozen benchmark campaign, independent external reproduction, operational evaluation, external security assessment, or production-readiness determination.
