# Adversarial Review Log

This log preserves material review outcomes, including superseded green test
runs. A passing local suite is evidence about the cases it executes; it is not
evidence that the fail-closed contract is complete.

## 2026-08-21 — Initial handoff rejected

**Review disposition:** changes required
**Evidence class:** local, synthetic, self-authored implementation with an
independent read-only code and adversarial-input review
**Pre-review verification:** 79/79 tests and 2/2 operator demonstration cases
passed

The reviewer reproduced reachable paths that could emit
`PERMIT_SCOPED_NEGATIVE` without adequate evidence. The green suite was
therefore rejected as insufficient for the published contract.

### Material findings

1. Omitted evidence facts were normalized to benign false or empty values.
2. Caller-controlled inline policy could weaken the P0 safety floor.
3. Free-form subject text could inject an absolute claim into qualified output.
4. Query time bounds were optional and could extend beyond observation time.
5. EmptyBench accepted singleton or weakly paired custom corpora and mislabeled
   them as the seed benchmark.
6. Missing schema versions were silently defaulted.
7. Expected EmptyBench reasons were checked as a subset rather than exactly.
8. Unknown populations could receive full coverage without an explicit declared
   lower-bound attestation.
9. Duplicate JSON keys, silently ignored full-request CLI overrides, and deeply
   nested input created ambiguity or unstructured failure.

### Required remediation

- Make safety-relevant evidence facts and schema version explicitly required.
- Enforce a non-relaxable P0 policy floor in both parsed and programmatic paths.
- Bound and safely render claim subjects.
- Require coherent query, observation, and evaluation times.
- Strengthen benchmark pairing, provenance labels, and exact oracle comparison.
- Require explicit lower-bound attestation for unknown or estimated populations.
- Reject ambiguous JSON and conflicting CLI input; return structured failures.

The initial 79-test result is retained here for traceability and must not be
presented as the accepted baseline.

## 2026-08-21 — Delivery mismatch rejected and repaired

After the hardened source suite reached 114 passing tests, a direct invocation
of the repository `.venv` imported a pre-hardening `site-packages` copy. The
source-overlay wrappers were green while the installed operator command still
used the old renderer and retained the old unsafe behavior. This state was not
accepted.

The candidate package was reinstalled into the repository virtual environment.
With `PYTHONPATH` unset, the installed interpreter then imported the package
from `.venv/lib/python3.13/site-packages`, passed 114/114 tests, and reproduced
the hardened demo, covered request, partial request, and custom benchmark.

## 2026-08-21 — Second proposed baseline rejected

**Review disposition:** rejected after expanded numeric and parser-bound review
**Evidence class:** local, synthetic, self-authored; independent read-only
review within the project team, not external reproduction

Verification before rejection:

- Source suite: 114/114 on Python 3.13.
- Installed suite with `PYTHONPATH` unset: 114/114 on Python 3.13.
- Python 3.11 unittest discovery: 114/114.
- Focused adversarial selection: 27/27.
- Operator demonstration: 2/2; complete seed: 10/10.
- Covered example: `PERMIT_SCOPED_NEGATIVE`.
- Partial example: `REJECT_NEGATIVE`.
- Custom example: 2/2 and labeled `EmptyBench-custom`.

The original exploit families—omitted facts, policy relaxation, subject
injection, missing or future time scope, unversioned input, unknown coverage,
ambiguous JSON, conflicting overrides, weak reason comparison, and singleton
benchmark bypass—were rerun and did not reproduce. The expanded review then
found additional defects across the numeric, temporal, parser, model, and
benchmark boundaries:

1. Coverage ratios were rounded to 12 decimal places. With
   `2,999,999,999,999` examined units out of `3,000,000,000,000`, the
   one-unit-short ratio rounded to `1.0`, satisfied the exact safety floor, and
   emitted `PERMIT_SCOPED_NEGATIVE` with a 100.000% rendering.
2. A 5,000-digit JSON integer crossed Python's integer-conversion limit and
   escaped the CLI's structured error boundary with a traceback.
3. High-precision declared coverage bounds could be rounded into a different
   semantic value, compare differently under ambient decimal contexts, or
   collide under the canonical digest.
4. Submicrosecond timestamps could be silently truncated; floating-point
   `total_seconds()` calculations lost exact boundary information; extreme
   offsets could overflow during UTC normalization; and permissive timestamp
   grammar accepted ambiguous offset forms including `-00:00`.
5. A direct-library daylight-saving fold case, oversized programmatic integer,
   half-specified page/partition pair, and caller-owned mutable list exposed
   inconsistent behavior between parsed and programmatic paths.
6. Invalid UTF-8 could escape the intended machine-readable failure boundary,
   and output metadata supplied to EmptyBench was not sufficiently bounded and
   sanitized.

The 114-test result is retained as remediation evidence for the first review,
but it is not an accepted project baseline. Hardening introduced exact rational
coverage evaluation, bounded and context-independent numeric handling, strict
timestamp normalization, exact microsecond age evaluation, immutable normalized
models, atomic ASCII-safe CLI output, and aligned parser/library invariants.

## 2026-08-21 — Later proposed baselines rejected

The broadly hardened source reached 168 passing tests. An explicit
bare-envelope command-line override, `--subject ''`, was treated as if the
option had not been supplied. The fallback subject was inserted and the request
could permit. This was a falsy-input repair defect, so the 168-test state was
rejected. The CLI now distinguishes absence from an explicitly supplied empty
value and lets validation reject the latter.

After that repair, the 169-test proposed state still allowed
`source.index_as_of` to postdate `observed_at`. That chronology could make an
earlier observation appear to have a later, favorable source index. The state
was rejected. Validation now requires `index_as_of <= observed_at` and tests the
before, equal, and after boundaries in both source and installed paths.

Mixed source/installed states encountered during this sequence were also not
accepted. Every material reproduction was converted into a regression before
the final replay.

## Accepted baseline

**Review disposition:** accepted as a local runtime baseline with explicit
product and evidence limitations
**Snapshot:** 171 tests; schema `0.1`; canonicalization profile `0.1`
**Evidence class:** local, synthetic, self-authored implementation; independent
read-only adversarial review within the project team

Final unchanged-snapshot results:

- Source suite on Python 3.13: 171/171.
- Installed suite with `PYTHONPATH` unset on Python 3.13: 171/171.
- Python 3.11 unittest discovery: 171/171.
- Source and installed package-file snapshots and deterministic demos matched.
- The 98/98 core CLI exploit replay set passed across source and installed
  execution paths.
- EmptyBench adversarial executions passed 30/30; seed demonstrations passed
  2/2 and 10/10; custom provenance remained `EmptyBench-custom`.
- Direct-library checks passed 38/38.
- Explicit source-index chronology probes passed 6/6: before/equal observation
  were accepted and post-observation input was rejected during validation.
- No unsupported permit or unstructured traceback was reproduced.

This is the first accepted local freeze of schema `0.1` and canonicalization
profile `0.1`. The 79-, 114-, 168-, and 169-test snapshots were development
proposals, not accepted contract versions. None was released, published,
benchmark-frozen, or used to issue a certificate. From this freeze forward,
incompatible changes require governed version evolution.

Acceptance is narrow. Required-versus-observed source accounting, an explicit
finality/completeness model, complete certificate and policy-version binding,
an independent oracle and frozen benchmark campaign, credential-like field
detection, broad fuzzing, real adapters, CI execution, external reproduction,
and operational validation remain open. `index_as_of` currently records source
currentness; it is not a completeness watermark, so `index_as_of` earlier than
the query interval end remains part of the explicit finality gap.

The internal independent review is not an external security assessment,
independent evidence custody, or production-readiness determination. The local
commit makes the snapshot recoverable; it does not authenticate its claims.
