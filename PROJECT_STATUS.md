# Project Status

**Status date:** 2026-08-22

**Lifecycle stage:** public Apache-2.0 pre-alpha; package `0.6.0` acceptance and custody verification open

**Claim level:** local research prototype only; schema `1.0` is unfrozen

## Current objective

Bind one stable `0.6.0` revision to a complete local acceptance record. The
implementation now binds application-selected profiles, emits deterministic
replay records, defines versioned evidence-state transitions and validation
errors, rejects credential-like authorization-context identifiers, and carries
a separated 24-case EmptyBench seed corpus and declarative oracle. The public
repository, Apache-2.0 license, community controls, and delivery automation do
not change its pre-alpha evidence status.

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

## Interim verification evidence

The following results were observed during the moving-tree hardening and adversarial-review cycle:

- `./scripts/test.sh -q` — `367 passed` against the integrated moving tree on
  2026-08-22; all 24 seed cases and all 12 pairs passed with zero unsafe
  permits and zero false rejections.
- `./scripts/test.sh -q tests/test_profiles.py` — `40 passed`, including exact selected-profile trust, unsupported contracts, direct applicability mutations, and microsecond boundary cases.
- Independent read-only attack attempts did not reproduce the weak/strong dual-profile downgrade once the trust selection pinned the exact profile reference.
- Rehashed replacement profile/snapshot content rejected against the original fixed trust context. Replacing and rehashing both configuration files remained possible, correctly exposing the configuration-custody boundary rather than claiming cryptographic trust.
- Untrusted snapshot or profile content with extreme finality values returned the trust failure without using the untrusted content for applicability or horizon calculations.
- `git diff --check` was clean at the interim review point.

These are useful implementation observations, not the final acceptance record. The worktree was still moving, the installed package and supported-runtime matrix had not yet been rerun against a frozen revision, and no independent external party held the oracle or expected digests.

## Open final acceptance and custody work

The `0.6.0` handoff must remain open until one stable revision completes and records all of the following:

1. freeze or commit the intended implementation and documentation state;
2. run `./scripts/setup.sh` and confirm project, imported module, and installed distribution all report `0.6.0`;
3. run `./scripts/check.sh` with `PYTHONPATH` unset and preserve its source-versus-installed package and deterministic-demo parity result;
4. rerun the full source and installed-package suites plus supported Python
   3.11, 3.12, and 3.13 source tests;
5. rerun the seed, operator, and custom paired demonstrations and compare cross-runtime output byte-for-byte where specified;
6. issue and verify the checked-in synthetic certificate using issue time `2026-08-21T12:06:00Z`, relying-party time `2026-08-21T12:30:00Z`, and expected digest `sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17`;
7. record the exact revision, commands, runtime versions, counts, generated-vector equality, and any environment limitations; and
8. obtain a final independent read-only review of the frozen state before calling the local handoff accepted.

Completion of this list may establish a locally tested, hash-bound candidate. It does not freeze schema `1.0`, freeze EmptyBench, authenticate configuration or evidence, demonstrate market demand, authorize deployment, or establish production readiness.

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
