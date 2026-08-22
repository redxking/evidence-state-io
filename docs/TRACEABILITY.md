# P0 Implementation Traceability

**Snapshot date:** 2026-08-22

**Evidence class:** local, synthetic, self-authored, custody-bound implementation

**Development package:** `evidence-state-io 0.6.0`

**Candidate implementation custody:** `PENDING POST-REMEDIATION CUSTODY`

**Documentation custody:** `PENDING POST-REMEDIATION CUSTODY`

**Permit certificate digest:**
`sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17`

**Rejection certificate digest:**
`sha256:9ad778636a8e013081d62d0a62e05e7cc0374a211444e5a951773607468f7462`

This matrix distinguishes implemented candidate behavior from full PRD
acceptance. `TESTED (PARTIAL)` means the behavior has local test evidence bound
to the implementation checkpoint above; it does not close the full requirement.
Schema `1.0` remains unfrozen, and documentation custody is still pending.

## Active contract set

| Contract | Exact 0.6.0 candidate identifier |
|---|---|
| Wire schema | `1.0` (unfrozen) |
| Policy | `esio-p0-safety-floor` / `1.0-candidate.4` |
| Evaluator | `esio-evaluator-1.0-candidate.5` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.2` |
| Coverage/finality profile | `esio-coverage-finality-profile/1.0-candidate.2` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.2` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.2` |
| Evidence certificate | `esio-evidence-certificate/1.0-candidate.2` |
| Evidence-state transitions | `esio-evidence-state-transition-model/1.0-candidate.1` |
| Authorization-context identifier | `esio-authorization-context-identifier/1.0-candidate.1` |
| Validation error | `esio-validation-error/1.0-candidate.1` |
| EmptyBench corpus | `esio-emptybench-corpus/1.0-candidate.1` |
| EmptyBench oracle | `esio-emptybench-oracle/1.0-candidate.1` |
| EmptyBench report | `esio-emptybench-report/1.0-candidate.1` |
| Canonicalization / digest | `esio-canonical-json-0.1` / `sha256` |

| Requirement | Current state | Local candidate evidence | Remaining gap before closure |
|---|---|---|---|
| ESIO-P0-001 Versioned evidence-state model | TESTED (PARTIAL) | `tests/test_models.py` locks all nine states. `tests/test_state_transitions.py` binds explicit same-lineage transitions to `esio-evidence-state-transition-model/1.0-candidate.1`. Unsupported identifiers fail closed. | The transition model does not validate successor evidence or source events. Schema `1.0` and every `candidate.*` contract remain unfrozen pending final custody and acceptance review. |
| ESIO-P0-002 Declared scope and access boundary | TESTED (PARTIAL) | The request binds target, predicate, authorization boundary/context ID, interval, exclusions, exactly one required source, exact immutable adapter version, detection assumptions, profile-derived horizon, and exact profile reference. The application trust selection separately pins the one permitted profile reference. Candidate.1 authorization-context validation rejects defined credential-like shapes. | Independent truth of declarations, exhaustive secret detection, richer field/projection semantics, and authenticated source/access identity remain open. |
| ESIO-P0-003 Coverage, profile, and completion facts | TESTED (PARTIAL) | Coverage and observations bind the normalized-query fingerprint. Candidate.2 profile/snapshot/trust objects bind canonical digests. Resolution checks exact selected reference, source/adapter/population applicability, retention, blind intervals, exclusions, freshness, derived finality, snapshot/profile time windows, and revocation. Snapshot trust failures short-circuit before profile semantics are used. | One source only; no multi-source composition, signed registry, monotonic registry-head check, online revocation check, independent profile validation, or authenticated index watermark. |
| ESIO-P0-004 Fail-closed envelope and artifact validation | TESTED (PARTIAL) | Strict JSON rejects duplicate keys, nonstandard constants, oversized/deep input, invalid UTF-8, unknown fields, malformed time, unsupported versions, invalid digests, lossy Decimal-to-binary64 values, boolean/numeric ambiguity, and out-of-range coverage bounds. Public CLI errors expose stable `esio-validation-error/1.0-candidate.1` codes. Typed certificates are serialized and reparsed through the same strict boundary before verification. | Comprehensive semantic-query, secret-detection, collection-bound, and fuzz coverage remain open. |
| ESIO-P0-005 Deterministic policy and coverage evaluator | TESTED (PARTIAL) | Requests require policy `1.0-candidate.4`; decisions expose evaluator `esio-evaluator-1.0-candidate.5` and evaluation-input `candidate.2`. Tests cover exact chronology, profile-derived finality, policy/profile freshness, retention, blind intervals, expiry, and revocation without ambient time. | Source/profile assertions and clocks remain unauthenticated; correction, reopening, backfill, and cross-page consistency are not independently established. |
| ESIO-P0-006 Negative-claim gate | TESTED (PARTIAL) | Absolute negatives, positive matches, every non-absence state, insufficient coverage, source/profile/trust faults, stale evidence, pre-horizon index, expired/revoked context, and policy failure reject. A request cannot select a weaker profile elsewhere in an otherwise accepted snapshot. | Aggregate state and evidence facts remain producer-declared. Independent state derivation, real adapter evidence, and multi-source finality remain open; full P0 safety is not established. |
| ESIO-P0-007 Qualification-preserving output | TESTED (PARTIAL) | The deterministic decision retains bounded subject/scope, source/profile references, time, coverage, reasons, qualifications, limitations, and non-attestation language. Every rejection renders a deterministic insufficiency statement without asserting the positive opposite. Permit and rejection decisions are first-class certificate payloads. | No governed downstream handoff-retention campaign or general language-policy proof; self-contained records currently require synthetic/non-sensitive inputs. |
| ESIO-P0-008 Deterministic evidence certificate | TESTED (PARTIAL) | Candidate.2 builder owns evaluation and binds the complete request, policy/evaluator/input contracts, trusted context, origin, times, decision, implementation identity, and outer digest. Verification separately reports structural support, outer/embedded integrity, canonical-byte replay, historical reproducibility, expected-context match, expected-digest match, and current-local-reliance eligibility. The effective boundary includes evidence validity, snapshot next update, resolved profile expiry/revocation, and policy/profile observation/index freshness deadlines. Permit and rejection vectors reproduced byte-identically across the recorded source and installed paths. | Unsigned self-digests do not authenticate issuers, authorize action, prove source truth, or provide independent custody. Local vector reproduction is not external verifier interoperability. |
| ESIO-P0-009 JSON CLI and library interface | TESTED (PARTIAL) | `evaluate` requires application registry/trust inputs plus explicit issuance time and evidence origin and emits a certificate. `verify-certificate` distinguishes malformed input (`2`) from failed verification dimensions (`1`), requires registry/trust as a pair, and keeps absent optional reliance evidence unestablished rather than successful. Source and installed permit/rejection outputs matched byte-for-byte at the implementation checkpoint. | No migration command or multi-schema active runtime is intended for this candidate; broader platform and packaging matrices remain open. |
| ESIO-P0-010 Seed EmptyBench corpus and oracle | TESTED (PARTIAL) | Corpus `candidate.1` contains 12 matched control/fault families and no machine-scored expectation fields; experimental role does not determine oracle polarity. Separately stored oracle `candidate.1` binds the exact corpus and requires a separately retained expected digest again at scoring. Typed corpus, oracle, and context are strictly reparsed. The integrated local run passed 24/24 cases and discriminated 12/12 pairs with zero unsafe permits and zero false rejections; tamper, swap, missing/duplicate, downgrade, post-parse mutation, and invalid-mutation regressions fail closed. | Both artifacts remain implementation-owned; this is not a preregistered or frozen held-out campaign, independent adjudication, or external reproduction. |
| ESIO-P0-011 Reproducibility and security baseline | TESTED (PARTIAL) | The integrated moving-tree source and installed suites passed `367/367`; Python 3.11.16, 3.12.14, and 3.13.0 source suites each passed `367/367`; source/runtime/installed 24-case demo outputs were byte-identical. Focused adversarial regressions cover application profile selection, staged trust, freshness-bound current reliance, caller-decision exclusion, typed-object reparsing, primitive-subclass rejection, lossless numeric support, canonical-byte replay, range checks, context/digest separation, contract downgrades, error redaction, and I/O failures. | Final revision and documentation custody, hosted CI/platform execution, broader fuzzing, independent oracle/custody, external security review, and operational validation remain pending. |

## Historical pre-integration adversarial evidence

The following record is historical and is not the current `0.6.0` custody
claim. The earlier hardening review reproduced and regression-bound defects at
rejected checkpoints `f7d8bca` and `e8c3bea`. At implementation checkpoint
`be0774680aa83052eeecab29e1a0ab38824f2860`:

- the application, not the producer, selects the one exact permitted profile;
- snapshot trust failure stops record resolution, and untrusted profile content
  cannot drive finality or freshness semantics;
- the certificate builder cannot accept a caller-created decision;
- decision mutation followed by recomputation of the outer digest fails
  deterministic replay;
- embedded context replacement, even with recomputed self- and outer digests,
  cannot match a separately supplied expected context;
- current-local-reliance eligibility is bounded by evidence validity, snapshot
  next update, profile expiry/revocation, and policy/profile observation/index
  freshness deadlines;
- typed artifacts are reparsed, lossy Decimal normalization is rejected,
  integer/float decision replay is type-strict, and invalid coverage bounds are
  structurally unsupported; and
- policy, evaluator, evaluation-input, profile, registry, trust,
  certificate-format, schema, canonicalization, and digest downgrade/fallback
  attempts reject.

These observations establish only the tested behavior of that named historical
local checkpoint. They are not current acceptance, a release, schema or
benchmark freeze, external reproduction, operational validation, or production
readiness.

## Historical pre-integration verification record

Recorded results for the named historical implementation checkpoint:

- source suite: `325/325` on Python 3.11.16, 3.12.14, and 3.13.15;
- installed-package suite: `325/325` on virtual-environment Python 3.13.0;
- setup: succeeded after network permission was granted;
- source/installed permit output: byte-identical, digest
  `sha256:5f28ba99baf2c45828ffa04bff60c480aa9ccf131e97ad1bb4ed9347b85aff6f`;
- source/installed rejection output: byte-identical, digest
  `sha256:3224...c059` (abbreviated); and
- source/installed `demo --all` 14-case seed-suite output: byte-identical.

The verification command families were:

```bash
env -u PYTHONPATH ./scripts/check.sh
env -u PYTHONPATH ./scripts/test.sh
env -u PYTHONPATH ./scripts/demo.sh --pretty
env -u PYTHONPATH ./.venv/bin/python -m pytest -q
PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -q
env -u PYTHONPATH ./.venv/bin/evidence-state evaluate \
  --input examples/covered_request.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --issued-at 2026-08-21T12:06:00Z \
  --origin SYNTHETIC \
  --pretty
env -u PYTHONPATH ./.venv/bin/evidence-state verify-certificate \
  --input examples/covered_certificate.json \
  --registry examples/profile_registry.json \
  --trust examples/profile_trust.json \
  --expected-digest sha256:5f28ba99baf2c45828ffa04bff60c480aa9ccf131e97ad1bb4ed9347b85aff6f \
  --relying-party-at 2026-08-21T12:30:00Z \
  --pretty
git diff --check
```

The historical evidence above does not satisfy current post-remediation
custody. The successor implementation and documentation hashes, full local
totals, and exact output comparisons must be recorded only after their stable
commits and reruns exist. No local record freezes schema `1.0` or EmptyBench or
establishes external validation or production readiness.

## Historical boundary

The 171-test schema `0.1` snapshot remains the first accepted local historical
freeze at `b6fac87`. Later schema `1.0` development checkpoints, including the
rejected profile/trust checkpoint `f7d8bca` and rejected certificate checkpoint
`e8c3bea`, do not replace that historical custody record. Their findings and
0.6.0 remediation are preserved in `docs/REVIEW_LOG.md`.
