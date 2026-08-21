# Project Status

**Status date:** 2026-08-21
**Lifecycle stage:** initial hardened runnable handoff, locally tested
**Claim level:** local research prototype only

## Current objective

Produce a reproducible laptop-based demonstration in which a deterministic gateway distinguishes a coverage-supported negative from an observationally identical but insufficiently covered case.

## Continuation mechanism

- Active goal: complete the runnable handoff and advance the MVP until its defined acceptance criteria are met.
- Active daily heartbeat: `advance-evidence-state-i-o`, scheduled for 9:00 AM in the task's local timezone.
- The heartbeat is bounded by `HANDOFF.md` and may not cross release, licensing, external-deployment, sensitive-data, or material-cost approval boundaries.

## Current evidence

- Public research establishes that coverage-sensitive negative reasoning is a measurable model failure mode.
- A bounded public scan found theory and benchmark work but no mature, cross-platform evidence-state runtime or adopted query-coverage contract.
- A dependency-free core runtime, explicit fail-closed schema, deterministic coverage evaluator, negative-claim gate, strict JSON CLI, five seed case pairs, and laptop operating package are implemented.
- Multiple green proposed baselines were rejected by read-only adversarial review. The reproduced unsafe paths were converted into regressions, and the unchanged 171-test source/installed snapshot passed the final replay. The full evidence trail is preserved in `docs/REVIEW_LOG.md`.
- The implementation-to-PRD status is recorded in `docs/TRACEABILITY.md`; several P0 requirements remain partial.

## Verification record

On 2026-08-21, the candidate source and repository-local installed package produced the results below. The repository's initial local commit binds the accepted 171-test code, tests, documentation, and review record into the first recoverable snapshot; the package-file comparison establishes source/install parity, not independent custody.

- `env -u PYTHONPATH ./scripts/check.sh` — passed; package compiled, dependencies checked, CLI imported, shell syntax passed, and optional Compose configuration validated.
- The same check compared source and installed package-file snapshots and their deterministic demos; parity passed.
- `env -u PYTHONPATH ./scripts/test.sh` — 171 tests passed on Python 3.13.0.
- `env -u PYTHONPATH ./scripts/demo.sh --pretty` — 2/2 synthetic paired cases passed.
- `PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -q` — 171 tests passed on Python 3.11.
- A fresh copied-project install built successfully and its installed suite passed 168/168 before the final two source regressions were added; the repository-local final install then passed 171/171.
- `env -u PYTHONPATH ./.venv/bin/python -m pytest -q` — 171 tests passed against the installed `site-packages` copy.
- Covered case — `PERMIT_SCOPED_NEGATIVE`.
- Matched incomplete-pagination case — `REJECT_NEGATIVE` with `STATE_NOT_ABSENT_WITHIN_SCOPE` and `COVERAGE_POLICY_NOT_MET`.
- Direct installed-command evaluation of both checked-in examples reproduced those dispositions; the custom pair was labeled `EmptyBench-custom`.
- Independent replay on the unchanged source and installed package passed the 98/98 core CLI exploit replay set across the two execution paths, 30/30 EmptyBench adversarial executions, 38/38 direct-library checks, and 6/6 explicit source-index chronology probes.
- Source and installed seed demonstrations passed at 2/2 and 10/10. The custom example passed 2/2 and retained `EmptyBench-custom` provenance.
- After the files were placed under local version control, `git diff --check` and `git diff --cached --check` passed.

The 79-, 114-, 168-, and 169-test proposed snapshots were not accepted. Review found unsupported permits, source/install drift, numeric and temporal precision defects, parser/output failures, programmatic-model inconsistencies, falsy-input repair, and source/observation chronology defects. Each material finding and its disposition remains recorded in `docs/REVIEW_LOG.md`.

The 171-test snapshot is the first accepted **local** schema `0.1` and canonicalization-profile `0.1` freeze. Earlier snapshots were development proposals, not accepted contracts; none was released, published, benchmark-frozen, or used to issue a certificate. Therefore the hardening changes did not silently revise an accepted `0.1` contract. From this local freeze forward, incompatible contract changes require the version-governance rules in ADR-0002. Policy/certificate version binding remains incomplete.

This is local synthetic evidence. The Python 3.11 check used `unittest`, not the complete CI job. GitHub Actions was not executed, containers were not started, and no external or operational system was evaluated.

## Known limitations

- No design-partner evidence.
- No independently reproduced benchmark.
- No operational or production deployment.
- No demonstrated completeness model for a real SIEM or enterprise search system.
- No complete certificate object, independent oracle, frozen baseline campaign, explicit finality derivation, or multi-source coverage composition.
- Pair validation requires the same visible question and at least one changed sufficiency fact; it does not yet prove that exactly one independent variable changed.
- Credential-like field detection and comprehensive per-collection semantic bounds remain open.
- Source `index_as_of` cannot postdate observation, but it is not yet a completeness/finality watermark. An index timestamp earlier than the query interval end therefore remains part of the explicit finality-model gap.
- The verified digest is integrity metadata only; it is not a signature or independent evidence custody.
- No licensing decision.
- Public-search absence does not establish that no private implementation exists.

## Next decision

Close the remaining P0 evidence-source/finality/certificate gaps, freeze an oracle-separated EmptyBench corpus, then measure whether the gate reduces a preregistered model baseline without collapsing supported negatives into universal abstention.
