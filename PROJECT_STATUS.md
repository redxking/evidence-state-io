# Project Status

**Status date:** 2026-08-22

**Lifecycle stage:** public Apache-2.0 pre-alpha; package `0.6.0` locally accepted at a hash-bound implementation checkpoint

**Claim level:** local research prototype only; schema `1.0` is unfrozen

## Current objective

Prepare the first implementation-owned campaign preregistration for owner
review without silently converting the accepted local regression record into a
frozen benchmark. The implementation binds application-selected profiles,
emits deterministic replay records, defines versioned evidence-state
transitions and validation errors, rejects credential-like
authorization-context identifiers, and carries a separate 24-case EmptyBench
seed corpus and declarative oracle. The public repository, Apache-2.0 license,
community controls, and delivery automation do not change its pre-alpha
evidence status.

## Continuation mechanism

- Active goal: complete the runnable handoff and advance the MVP until its defined acceptance criteria are met.
- Active daily heartbeat: `advance-evidence-state-i-o`, scheduled for 9:00 AM in the task's local timezone.
- The heartbeat is bounded by `HANDOFF.md` and `docs/AUTOMATION.md`. It may
  maintain the authorized public repository but may not create a versioned
  release/tag, change licensing, deploy externally, use sensitive data, incur
  material cost, or expand external claims without owner authority.
- `TASKS.md` contains the active bounded work. Every increment must leave the repository recoverable and update the evidence record in the same change.

## Active contract set

| Boundary | Active identifier |
|---|---|
| Package | `0.6.0` |
| Wire schema | `1.0` candidate, unfrozen |
| Policy | `esio-p0-safety-floor/1.0-candidate.4` |
| Evaluator | `esio-evaluator-1.0-candidate.5` |
| Coverage/finality profile | `esio-coverage-finality-profile/1.0-candidate.2` |
| Registry snapshot | `esio-profile-registry-snapshot/1.0-candidate.2` |
| Trust selection | `esio-profile-trust-selection/1.0-candidate.2` |
| Evaluation input | `esio-evaluation-input/1.0-candidate.2` |
| Evidence certificate | `esio-evidence-certificate/1.0-candidate.2` |
| Evidence-state transitions | `esio-evidence-state-transition-model/1.0-candidate.1` |
| Authorization-context identifier | `esio-authorization-context-identifier/1.0-candidate.1` |
| Validation error | `esio-validation-error/1.0-candidate.1` |
| EmptyBench corpus | `esio-emptybench-corpus/1.0-candidate.1` |
| EmptyBench oracle | `esio-emptybench-oracle/1.0-candidate.1` |
| EmptyBench report | `esio-emptybench-report/1.0-candidate.1` |
| Canonicalization | `esio-canonical-json-0.1` |
| Digest | SHA-256 |

These identifiers are exact boundaries, not a negotiation mechanism. Older, newer, floating, ranged, or aliased active versions fail closed. Package version does not silently select another schema or policy.

## Current implementation

- The application supplies a materialized registry snapshot and trust selection separately from the producer-controlled request. The trust selection pins the exact snapshot identity/version/digest and the exact selected profile reference. A request that selects another active profile from the same snapshot rejects with `PROFILE_TRUST_SELECTION_MISMATCH`.
- Profile, snapshot, trust-selection, request, observation, and adapter version fields accept only exact normalized version forms. Common floating labels, ranges, and abbreviated Git object IDs reject structurally.
- Snapshot identity, digest, issuer, as-of time, and expiry are checked before any contained record is used. Profile digest, issuer, approval authority, effective time, expiry, and revocation are then checked before profile applicability, freshness, or finality content can influence the assessment.
- The selected profile governs exact source and adapter identity, authorization context and boundary, accessible population, target, predicate, required exclusions, detection assumptions, denominator, optional page and partition counts, permission limits, retention, blind intervals, freshness, and late-arrival/reopen bounds.
- The profile supplies the fixed `QUERY_END_PLUS_MAX_DELAY` rule. A permit requires the request horizon to equal `query.time_end + max(late_arrival_bound, reopen_bound)` and the reported source index to reach that horizon. Advancing evaluation time cannot repair an old index.
- Governance intervals are half-open: profile use requires `effective_at <= evaluated_at < expires_at`; snapshot use requires `as_of <= evaluated_at < next_update_at`. Observation and index freshness permit exact equality with their configured age limits and reject one microsecond beyond. Retention, blind-interval, and derived-horizon boundaries have corresponding exact microsecond tests.
- The candidate accepts exactly one declared `REQUIRED` source. Optional or multiple sources reject because cross-source population, overlap, temporal, and finality composition are not defined.
- The CLI builds an `esio-evidence-certificate/1.0-candidate.2` object rather than accepting a caller-supplied decision. The certificate binds the complete request, trusted context, exact resolved references, policy, evaluator, evaluation-input contract, origin classification, implementation assertion, evaluation and issue times, decision, and qualification.
- Certificate verification independently reports structural support, outer digest integrity, embedded binding integrity, deterministic replay, expected-context comparison, expected-certificate-digest comparison, historical reproducibility, and current local-use eligibility.
- `effective_valid_until_exclusive` is the earliest applicable snapshot update, conservative envelope boundary, policy observation/index freshness deadline, resolved-profile expiry or revocation boundary, and resolved-profile observation/index freshness deadline. Current local use additionally requires an explicit relying-party time at or after issue and strictly before that boundary.
- The certificate is unsigned. SHA-256 values are comparison and integrity metadata, not authentication, independent custody, trusted time, non-repudiation, or action authority.
- The schema `0.1` fixture remains historical replay evidence at pinned commit `b6fac87`. The active parser does not relabel or auto-migrate it.
- Evidence-state transitions are explicit, immutable-envelope lifecycle assertions under `esio-evidence-state-transition-model/1.0-candidate.1`; they do not prove the successor evidence or source event.
- Public CLI failures carry stable `esio-validation-error/1.0-candidate.1` codes. Authorization-context fields reject a narrow, versioned set of credential-like shapes; this is a guardrail, not proof that an arbitrary identifier contains no secret.
- Rejection certificates now contain a deterministic insufficiency statement and can never be reinterpreted as evidence for the opposite proposition. Current local reliance remains unestablished unless expected context, a separately retained expected certificate digest, and relying-party time are all supplied.
- EmptyBench now loads a versioned corpus with 12 matched control/fault pairs
  and no embedded expectations, then scores it against a separately stored,
  corpus-bound declarative oracle and separately retained expected oracle
  digest. Tampering, swapping, missing/duplicate assignments, contract
  downgrade, and invalid mutation paths fail closed.

## Hash-bound local acceptance record

Implementation checkpoint
`38f390fdae6870f10e4e5bfc4fabef8db6a7c4c3` was clean when the
following local acceptance evidence was collected:

- `./scripts/setup.sh` rebuilt and installed `evidence-state-io 0.6.0`.
- `./scripts/test.sh -q` and the installed-package pytest path each passed
  `372/372`.
- Python 3.11.16, 3.12.14, and 3.13.0 each passed `372/372` source tests.
- `env -u PYTHONPATH ./scripts/check.sh` passed shell, dashboard, compilation,
  dependency, local-link, source/installed snapshot, installed CLI, and
  deterministic demo checks. Docker Compose was available and its optional
  configuration validation also passed.
- The 24-case seed regression passed with 12/12 matched pairs discriminated,
  zero unsafe permits, and zero false rejections.
- Permit, rejection, `demo --all`, and verifier outputs were byte-identical
  across Python 3.11, 3.12, 3.13, and the installed package. Generated permit
  and rejection output also matched the checked-in certificate vectors.
- The permit and rejection certificate digests remained
  `sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17`
  and
  `sha256:9ad778636a8e013081d62d0a62e05e7cc0374a211444e5a951773607468f7462`.
- At relying-party time `2026-08-21T12:30:00Z`, verification of the checked-in
  permit reported structural support, both integrity dimensions,
  deterministic replay, expected context, expected digest, historical
  reproducibility, and current local reliance eligibility as true. Issuer
  authentication and action authorization remained false.
- A final separate in-project read-only adversarial review found no surviving
  P0 bypass. Wrong retained digests, contract downgrades, post-parse mutation,
  rehashed assignment swaps, hostile container subclasses, credential-like
  context mutation, and non-discriminating reports all failed closed.

This accepts only the named implementation checkpoint as a locally tested
candidate. It does not freeze schema `1.0` or EmptyBench, authenticate the
configuration or evidence, establish independent custody or adjudication,
demonstrate market demand, authorize deployment, or establish production
readiness.

## MVP publication gate (2026-08-22)

The machine-readable MVP acceptance ledger in `project/acceptance.json` is the
authoritative record for the 27 publication criteria. The narrative record above
describes checkpoint `38f390f` and is retained as history; it is not a claim
about the current candidate.

Observed at implementation checkpoint
`cf03ffd032620afe244d5410dd84cfb10f46ce4f` on a clean worktree:

- `./scripts/setup.sh` refreshed the repository-local package snapshot and
  changed no tracked content.
- `./scripts/acceptance.sh` completed with exit status `0`.
- The fresh isolated Python 3.11 environment passed `397` tests; `ruff check`,
  `ruff format --check`, and `mypy` reported no findings.
- Branch coverage over the frozen deterministic core was `90%` against the
  `--fail-under=90` boundary.
- Python 3.11.16, 3.12.14, and 3.13.0 each passed `397/397` source tests, and
  the isolated wheel installation passed `397/397`.
- The dashboard lossless/safe-render regression and the browser-demo parity and
  fail-closed regression passed.
- `scripts/public_release_gate.py` returned `PASS` with no findings across
  `165` tracked files.
- EmptyBench reported `24/24` cases passed, `12/12` matched pairs
  discriminated, zero unsafe permits, and zero false rejections.

Two defects were then found by running the documented continuation and CI
entry points rather than by reading them: the controller's reconcile step
invalidated the clean-worktree precondition of its own verification command,
and the CI `quality` job invoked `scripts/check.sh` without the
repository-local environment that script requires. Both are recorded with their
reproduction and remediation in `docs/REVIEW_LOG.md`. The successor commit must
be verified in its own right; exact hash-bound evidence for it is written to
`project/acceptance.json` and `project/progress.jsonl` by the bounded
controller.

This records a local gate result only. It does not establish remote
publication, CI success, Pages availability, Wiki completeness, benchmark
custody, independent adjudication, external reproduction, or production
readiness.

## Next evidence gates

Local package acceptance is complete. Advancement beyond it requires distinct,
non-implied decisions and evidence:

1. complete an owner-reviewed campaign preregistration;
2. record owner approval before freezing or executing that campaign;
3. run the implementation-owned baseline without reinterpretation;
4. obtain independently governed oracle custody and external reproduction;
5. define and authorize one real read-only adapter boundary before handling any
   non-synthetic evidence; and
6. make separate security, privacy/legal, reliability, operational, deployment,
   and support decisions before any production claim.

## Known limitations

- Registry, trust-selection, profile, owner, issuer, approval, adapter, evidence, and watermark identities remain declarative under local configuration custody. A party able to replace and rehash both registry and trust files can select another profile.
- Profile digests bind exact content but do not prove the truth of population, retention, blind-interval, freshness, late-arrival, reopen, or source-behavior assertions.
- The producer-supplied aggregate state and evidence facts are internally checked but not independently derived. Query fingerprints and exact matching do not stop a self-consistent malicious producer without authenticated adapter evidence.
- No monotonic registry head, signed trust selection, issuer authentication, trusted timestamp, nonce/replay store, operational revocation distribution, or independent custody exists.
- No source-clock calibration or empirical validation of exceptional late arrivals, backfill, corrections, retractions, deletions, reopening, or ingestion completeness exists.
- The certificate is a deterministic unsigned replay record. It is not an authorization token, signature, proof of source truth, or durable custody mechanism.
- EmptyBench corpus/oracle separation and minimum P0 fault-family coverage are
  implemented and locally tested. The authors still control both artifacts;
  no held-out campaign is frozen, independently adjudicated, preregistered, or
  externally reproduced.
- No real adapter, design-partner evidence, independently reproduced benchmark, operational deployment, or external security assessment exists.
- Public-search absence does not prove that no private implementation exists.

## Next decision

Commit the integrated state, run the full source, installed-package,
supported-runtime, vector, deterministic-output, and final read-only review
matrix against that stable revision, and bind the exact evidence to it. Only
that can close local `0.6.0` acceptance; it cannot establish production
readiness or external validation.
