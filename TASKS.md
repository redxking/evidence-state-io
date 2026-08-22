# Tasks

## Active

- [ ] **Complete the `0.6.0` final acceptance and custody record**
  - Stabilize and bind the intended implementation and documentation revision.
  - Run setup, static/local-link checks, source-versus-installed package parity, the full source and installed suites, supported Python 3.11, 3.12, and 3.13 tests, and every benchmark/operator demonstration against that same revision.
  - Reproduce the checked-in synthetic certificate using issue time `2026-08-21T12:06:00Z`; verify it at `2026-08-21T12:30:00Z` against expected digest `sha256:5683e522aa22f08145658d49452a4c044d7cf562a6a3987da364b3322d4aab17` and the separately supplied expected context.
  - Record exact commands, runtimes, counts, vector equality, revision, worktree state, and limitations. Obtain a final read-only adversarial review of the stable state.
  - Do not call this a schema freeze, benchmark freeze, release, external reproduction, production authorization, or proof that profile/source assertions are true.

## Next

- [ ] **Preregister and owner-approve the first implementation-owned campaign
  freeze** — Freeze the exact corpus, declarative oracle, separately retained
  digests, baseline configurations, scoring, exclusions, environment matrix,
  and stop conditions after stable revision acceptance. This is not independent
  adjudication or external custody.
- [ ] **Run the first preregistered implementation-owned baseline** — Begin only
  after the campaign freeze above. Apply thresholds without reinterpretation
  and do not call it independent reproduction.
- [ ] **Package one read-only adapter design** — Define authority, data, identity, redaction, and verification gates before implementing any real-system access.

## Waiting On

- [ ] **Owner approval for external discovery** — Required before contacting design partners or using any real workflow data.
- [ ] **Owner-approved authority and data boundary for a real read-only adapter** — Required before handling non-synthetic workflow evidence.

## Someday

- [ ] **Specify authenticated registry and adapter evidence** — Define signing roots, source-owner and approval delegation, key rotation/revocation, monotonic registry heads, trusted time, and adapter artifact/attestation identity in a separate versioned design.
- [ ] **Define multi-source composition** — Specify overlapping populations, per-source coverage, temporal alignment, finality, conflicts, and degraded-source behavior before accepting more than one required source.
- [ ] **Evaluate an MCP interoperability profile** — Begin only after the contract survives a real read-only adapter and the frozen benchmark.

## Done

- [x] ~~Separate the minimum EmptyBench seed corpus and scoring oracle~~
  (2026-08-22)
  - Corpus `esio-emptybench-corpus/1.0-candidate.1` contains 12 matched
    control/fault pairs and no machine-scored expectation fields. Experimental
    role does not determine expected verdict. Oracle
    `esio-emptybench-oracle/1.0-candidate.1` is stored separately, binds the
    exact corpus digest, and is checked against a separately retained expected
    digest.
  - The 24-case local regression run discriminated 12/12 pairs with zero
    unsafe permits and zero false rejections. Tamper, swap, missing/duplicate,
    downgrade, and invalid-mutation tests are checked in.
  - This closes seed separation and P0 family coverage only. The authors still
    control the corpus and oracle; no held-out benchmark campaign has been
    frozen, preregistered, independently adjudicated, or externally reproduced.

- [x] ~~Implement exact application-selected profile governance~~ (2026-08-21)
  - Package `0.6.0` uses policy `esio-p0-safety-floor/1.0-candidate.4`, evaluator `esio-evaluator-1.0-candidate.5`, profile `esio-coverage-finality-profile/1.0-candidate.2`, registry snapshot `esio-profile-registry-snapshot/1.0-candidate.2`, trust selection `esio-profile-trust-selection/1.0-candidate.2`, and evaluation input `esio-evaluation-input/1.0-candidate.2`; schema `1.0` remains unfrozen.
  - The producer request carries an exact profile reference. The separately supplied trust selection pins the exact snapshot and exact profile reference selected by the application, closing the weak/strong sibling-profile downgrade.
  - Snapshot failures return before record content is used; profile digest, issuer, authority, time, and revocation failures return before applicability, freshness, or finality content is used.
  - Exact source, adapter, authorization, population, query, assumptions, coverage, retention, blind-interval, freshness, and finality mutations fail closed. Floating/alias/range version tokens and abbreviated Git object IDs reject.
  - Focused profile tests passed `40/40`; the pre-benchmark moving-tree source suite passed `357/357`. Final installed-package and revision custody remain active above.

- [x] ~~Define P0 transition, validation-error, and authorization-identifier contracts~~ (2026-08-22)
  - `esio-evidence-state-transition-model/1.0-candidate.1` defines deterministic same-lineage state transitions without claiming source truth or successor-evidence validity.
  - `esio-validation-error/1.0-candidate.1` gives public CLI failures stable machine-readable codes.
  - `esio-authorization-context-identifier/1.0-candidate.1` rejects a narrow set of credential-like identifiers; it is not a general secret detector.

- [x] ~~Adopt an open-source license and public collaboration model~~ (2026-08-22)
  - Apache License 2.0 and NOTICE are present. Governance, conduct, support, security, contribution, issue, pull-request, CI, security-analysis, dependency, Pages, release, wiki-source, and roadmap materials are version controlled.
  - Public availability does not establish a stable release, frozen protocol, production readiness, external validation, or authorization for consequential use.

- [x] ~~Implement the complete deterministic unsigned certificate~~ (2026-08-21)
  - `esio-evidence-certificate/1.0-candidate.2` binds the request, trusted context, resolved profile references, policy/evaluator/evaluation-input identities, origin, implementation assertion, evaluation and issue times, complete decision, and qualification.
  - The builder derives the decision internally. Verification reparses typed or JSON input and separates structural support, digest integrity, embedded binding, deterministic replay, expected-context/digest comparison, historical reproducibility, and current local-use eligibility.
  - The exclusive current-use boundary includes snapshot update, conservative envelope validity, policy freshness, resolved-profile expiry/revocation, and resolved-profile observation/index freshness deadlines.
  - Decimal-versus-float equivalence, boolean-as-integer confusion, invalid coverage domains, typed-object mutation, stale context, and freshness-boundary attacks were converted to regressions during review.
  - The record is explicitly unsigned and does not authenticate an issuer or authorize an action. Final frozen-revision acceptance remains active above.

- [x] ~~Derive declared finality chronology explicitly~~ (2026-08-21)
  - A query-bound horizon and source-index closure check prevent waiting alone from upgrading an old snapshot. The governed profile now owns the exact horizon calculation.

- [x] ~~Add required and observed source accounting~~ (2026-08-21)
  - Query requirements and runtime observations are distinct, fingerprint-bound, and fail closed on missing, non-observed, mismatched, or error-bearing required-source states. P0 remains single-source.

- [x] ~~Initial local covered-versus-partial demonstration~~ (2026-08-21)
  - The schema `0.1` baseline at `b6fac87` remains historical local replay evidence. The active schema `1.0` candidate and EmptyBench remain unfrozen and are not external validation.
